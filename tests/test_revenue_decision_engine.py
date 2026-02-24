"""
Unit tests for RevenueDecisionEngine.

Tests the core functionality of revenue decision-making including risk assessment,
decision classification, and recommendation generation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from aboa.decision.revenue_decision_engine import RevenueDecisionEngine
from aboa.models.enums import (
    DecisionClass, RiskType, Severity, DealStage, LeadStatus, 
    ActivityType, SalesActionType
)
from aboa.models.revenue_entities import (
    Deal, Lead, PipelineRisk, SalesRep, ContactInfo
)
from aboa.knowledge.manager import SalesKnowledgeManager, SalesContext, SalesDocument, DocumentType


class TestRevenueDecisionEngine:
    """Test cases for RevenueDecisionEngine."""
    
    @pytest.fixture
    def mock_knowledge_manager(self):
        """Create a mock knowledge manager."""
        mock_km = Mock(spec=SalesKnowledgeManager)
        
        # Mock sales context
        mock_context = SalesContext(
            relevant_playbooks=[
                SalesDocument(
                    id="playbook1",
                    title="Stalled Deal Recovery",
                    content="Follow up within 24 hours",
                    document_type=DocumentType.PLAYBOOK,
                    version="1.0"
                )
            ],
            objection_handling=[],
            successful_patterns=[],
            methodologies=[],
            confidence_score=85.0,
            query="stalled_deal"
        )
        
        mock_km.get_sales_context.return_value = mock_context
        return mock_km
    
    @pytest.fixture
    def decision_engine(self, mock_knowledge_manager):
        """Create a decision engine with mock knowledge manager."""
        return RevenueDecisionEngine(knowledge_manager=mock_knowledge_manager)
    
    @pytest.fixture
    def sample_deal(self):
        """Create a sample deal for testing."""
        return Deal(
            id="deal1",
            stage=DealStage.PROPOSAL,
            value=Decimal('50000'),
            probability=75.0,
            close_date=datetime.now(timezone.utc) + timedelta(days=30),
            assigned_rep="rep1",
            days_in_current_stage=10
        )
    
    @pytest.fixture
    def sample_lead(self):
        """Create a sample lead for testing."""
        return Lead(
            id="lead1",
            source="website",
            contact_info=ContactInfo(email="test@example.com"),
            status=LeadStatus.QUALIFIED,
            estimated_value=Decimal('25000'),
            assigned_rep="rep1",
            contact_attempts=2
        )
    
    @pytest.fixture
    def sample_rep(self):
        """Create a sample sales rep for testing."""
        return SalesRep(
            id="rep1",
            name="John Doe",
            email="john@example.com",
            quota=Decimal('1000000'),
            quota_attainment=75.0,
            pipeline_value=Decimal('500000')
        )
    
    @pytest.fixture
    def sample_risk(self):
        """Create a sample pipeline risk for testing."""
        return PipelineRisk(
            risk_id="risk1",
            risk_type=RiskType.STALLED_DEAL,
            confidence=85.0,
            affected_deals=["deal1"],
            severity=Severity.HIGH,
            description="Deal stalled in proposal stage",
            recommended_actions=["create_followup_task_deal1"]
        )
    
    def test_analyze_and_recommend_basic(self, decision_engine, sample_risk, sample_deal, sample_lead, sample_rep):
        """Test basic analyze and recommend functionality."""
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[sample_risk],
            deals=[sample_deal],
            leads=[sample_lead],
            reps=[sample_rep]
        )
        
        assert len(recommendations) == 1
        risk, action, decision_class = recommendations[0]
        
        assert risk.risk_type == RiskType.STALLED_DEAL
        assert action.action_type == SalesActionType.CREATE_TASK
        assert decision_class in [DecisionClass.AUTO_EXECUTABLE, DecisionClass.APPROVAL_REQUIRED, DecisionClass.INSIGHT_ONLY]
    
    def test_assess_risk_impact(self, decision_engine, sample_risk, sample_deal, sample_lead):
        """Test risk impact assessment."""
        impact = decision_engine.assess_risk_impact(sample_risk, [sample_deal], [sample_lead])
        
        assert impact['total_pipeline_at_risk'] == Decimal('50000')
        assert impact['deals_at_risk_count'] == 1
        assert impact['leads_at_risk_count'] == 0
        assert impact['highest_value_deal'] == Decimal('50000')
        assert impact['urgency_score'] > 0
    
    def test_decision_classification_auto_executable(self, decision_engine):
        """Test auto-executable decision classification."""
        # Low-value, high-confidence risk should be auto-executable
        low_value_deal = Deal(
            id="deal1",
            stage=DealStage.PROSPECTING,
            value=Decimal('15000'),  # Below auto_executable_max_value
            probability=50.0,
            close_date=datetime.now(timezone.utc) + timedelta(days=30),
            assigned_rep="rep1",
            days_in_current_stage=5
        )
        
        high_confidence_risk = PipelineRisk(
            risk_id="risk1",
            risk_type=RiskType.MISSED_FOLLOWUP,
            confidence=90.0,  # Above auto_executable_confidence_threshold
            affected_deals=["deal1"],
            severity=Severity.MEDIUM,
            description="Missed follow-up",
            recommended_actions=["create_task"]
        )
        
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[high_confidence_risk],
            deals=[low_value_deal],
            leads=[],
            reps=[]
        )
        
        assert len(recommendations) == 1
        _, _, decision_class = recommendations[0]
        assert decision_class == DecisionClass.AUTO_EXECUTABLE
    
    def test_decision_classification_approval_required(self, decision_engine):
        """Test approval-required decision classification."""
        # High-value deal should require approval
        high_value_deal = Deal(
            id="deal1",
            stage=DealStage.NEGOTIATION,
            value=Decimal('150000'),  # Above critical_decision_value
            probability=80.0,
            close_date=datetime.now(timezone.utc) + timedelta(days=15),
            assigned_rep="rep1",
            days_in_current_stage=3
        )
        
        critical_risk = PipelineRisk(
            risk_id="risk1",
            risk_type=RiskType.STALLED_DEAL,
            confidence=85.0,
            affected_deals=["deal1"],
            severity=Severity.CRITICAL,
            description="Critical deal stalled",
            recommended_actions=["urgent_action"]
        )
        
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[critical_risk],
            deals=[high_value_deal],
            leads=[],
            reps=[]
        )
        
        assert len(recommendations) == 1
        _, _, decision_class = recommendations[0]
        assert decision_class == DecisionClass.APPROVAL_REQUIRED
    
    def test_risk_consolidation(self, decision_engine, sample_deal, sample_rep):
        """Test consolidation of multiple related risks."""
        # Create two risks affecting the same deal
        risk1 = PipelineRisk(
            risk_id="risk1",
            risk_type=RiskType.STALLED_DEAL,
            confidence=80.0,
            affected_deals=["deal1"],
            severity=Severity.MEDIUM,
            description="Deal stalled",
            recommended_actions=["action1"]
        )
        
        risk2 = PipelineRisk(
            risk_id="risk2",
            risk_type=RiskType.MISSED_FOLLOWUP,
            confidence=75.0,
            affected_deals=["deal1"],
            severity=Severity.HIGH,
            description="Missed follow-up",
            recommended_actions=["action2"]
        )
        
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[risk1, risk2],
            deals=[sample_deal],
            leads=[],
            reps=[sample_rep]
        )
        
        # Should consolidate into single recommendation
        assert len(recommendations) == 1
        consolidated_risk, _, _ = recommendations[0]
        
        # Should take highest severity
        assert consolidated_risk.severity == Severity.HIGH
        # Should combine affected deals
        assert "deal1" in consolidated_risk.affected_deals
        # Should mention consolidation in description
        assert "Consolidated risk" in consolidated_risk.description
    
    def test_knowledge_integration(self, decision_engine, sample_risk, sample_deal, sample_rep, mock_knowledge_manager):
        """Test integration with knowledge manager."""
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[sample_risk],
            deals=[sample_deal],
            leads=[],
            reps=[sample_rep]
        )
        
        # Should have called knowledge manager
        mock_knowledge_manager.get_sales_context.assert_called_once()
        
        # Should include sales guidance in action parameters
        _, action, _ = recommendations[0]
        assert 'sales_guidance' in action.parameters
        assert 'context_confidence' in action.parameters
    
    def test_revenue_impact_estimation(self, decision_engine, sample_risk, sample_deal, sample_lead):
        """Test revenue impact estimation."""
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[sample_risk],
            deals=[sample_deal],
            leads=[sample_lead],
            reps=[]
        )
        
        _, action, _ = recommendations[0]
        
        # Should have estimated revenue impact
        assert action.revenue_impact is not None
        assert action.revenue_impact > 0
        
        # Should be reasonable percentage of deal value
        expected_min = sample_deal.value * Decimal('0.1')  # At least 10%
        expected_max = sample_deal.value * Decimal('0.5')  # At most 50%
        assert expected_min <= action.revenue_impact <= expected_max
    
    def test_action_priority_calculation(self, decision_engine):
        """Test action priority calculation."""
        # Critical risk should get high priority
        critical_risk = PipelineRisk(
            risk_id="risk1",
            risk_type=RiskType.INACTIVE_HIGH_VALUE,
            confidence=95.0,
            affected_deals=["deal1"],
            severity=Severity.CRITICAL,
            description="Critical risk",
            recommended_actions=[]
        )
        
        high_value_deal = Deal(
            id="deal1",
            stage=DealStage.NEGOTIATION,
            value=Decimal('100000'),
            probability=90.0,
            close_date=datetime.now(timezone.utc) + timedelta(days=7),
            assigned_rep="rep1",
            days_in_current_stage=2
        )
        
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[critical_risk],
            deals=[high_value_deal],
            leads=[],
            reps=[]
        )
        
        _, action, _ = recommendations[0]
        
        # Critical risk with high value should get priority 1 or 2
        assert action.priority <= 2
    
    def test_empty_risks_list(self, decision_engine):
        """Test handling of empty risks list."""
        recommendations = decision_engine.analyze_and_recommend(
            pipeline_risks=[],
            deals=[],
            leads=[],
            reps=[]
        )
        
        assert len(recommendations) == 0
    
    def test_no_knowledge_manager(self):
        """Test operation without knowledge manager."""
        engine = RevenueDecisionEngine(knowledge_manager=None)
        
        risk = PipelineRisk(
            risk_id="risk1",
            risk_type=RiskType.STALLED_DEAL,
            confidence=80.0,
            affected_deals=["deal1"],
            severity=Severity.MEDIUM,
            description="Test risk",
            recommended_actions=[]
        )
        
        deal = Deal(
            id="deal1",
            stage=DealStage.PROPOSAL,
            value=Decimal('30000'),
            probability=70.0,
            close_date=datetime.now(timezone.utc) + timedelta(days=20),
            assigned_rep="rep1",
            days_in_current_stage=8
        )
        
        recommendations = engine.analyze_and_recommend(
            pipeline_risks=[risk],
            deals=[deal],
            leads=[],
            reps=[]
        )
        
        # Should still generate recommendations without knowledge manager
        assert len(recommendations) == 1
        _, action, _ = recommendations[0]
        assert 'sales_guidance' not in action.parameters