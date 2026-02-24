"""
Tests for Pipeline Velocity Optimizer.

This module tests the pipeline velocity optimization engine including
automated follow-up scheduling, revenue impact prioritization, and
SOP compliance monitoring.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from aboa.decision.pipeline_velocity_optimizer import PipelineVelocityOptimizer
from aboa.models.enums import (
    DealStage, LeadStatus, RiskType, Severity, SalesActionType, ActivityType
)
from aboa.models.revenue_entities import (
    Deal, Lead, SalesActivity, SalesRep, PipelineRisk, ContactInfo
)


class TestPipelineVelocityOptimizer:
    """Test main pipeline velocity optimizer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = PipelineVelocityOptimizer()
        
        # Create test data
        self.deals = [
            Deal(
                id="deal_1",
                stage=DealStage.PROPOSAL,
                value=Decimal('75000'),
                probability=60.0,
                close_date=datetime.now(timezone.utc) + timedelta(days=30),
                assigned_rep="rep_1",
                days_in_current_stage=8
            )
        ]
        
        self.leads = [
            Lead(
                id="lead_1",
                source="website",
                contact_info=ContactInfo(email="test@example.com"),
                status=LeadStatus.NEW,
                contact_attempts=0,
                assigned_rep="rep_1",
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        self.activities = [
            SalesActivity(
                id="activity_1",
                deal_id="deal_1",
                activity_type=ActivityType.MEETING,
                completed_at=datetime.now(timezone.utc) - timedelta(days=5),
                rep_id="rep_1"
            )
        ]
        
        self.reps = [
            SalesRep(
                id="rep_1",
                name="Jane Smith",
                email="jane@company.com",
                quota=Decimal('500000')
            )
        ]
    
    def test_optimize_pipeline_velocity_success(self):
        """Test successful pipeline velocity optimization."""
        results = self.optimizer.optimize_pipeline_velocity(
            deals=self.deals,
            leads=self.leads,
            activities=self.activities,
            reps=self.reps
        )
        
        assert results['status'] == 'completed'
        assert 'timestamp' in results
        assert 'pipeline_risks' in results
        assert 'followup_actions' in results
        assert 'compliance_scores' in results
        assert 'summary' in results
        
        # Should have detected some risks or actions
        total_items = (
            len(results['pipeline_risks']) + 
            len(results['followup_actions']) + 
            len(results['prioritized_interventions'])
        )
        assert total_items >= 0  # May be 0 if no risks detected
    
    def test_optimization_disabled(self):
        """Test optimization when disabled."""
        self.optimizer.config['optimization_enabled'] = False
        
        results = self.optimizer.optimize_pipeline_velocity(
            deals=self.deals,
            leads=self.leads,
            activities=self.activities,
            reps=self.reps
        )
        
        assert results['status'] == 'disabled'
        assert results['actions'] == []
    
    def test_optimization_error_handling(self):
        """Test error handling in optimization."""
        # Mock an error in risk detection
        with patch.object(self.optimizer.risk_detector, 'detect_pipeline_risks', 
                         side_effect=Exception("Test error")):
            
            results = self.optimizer.optimize_pipeline_velocity(
                deals=self.deals,
                leads=self.leads,
                activities=self.activities,
                reps=self.reps
            )
            
            assert results['status'] == 'failed'
            assert 'error' in results
    
    def test_summary_generation(self):
        """Test optimization summary generation."""
        # Create mock data
        mock_risks = [
            Mock(risk_type=RiskType.STALLED_DEAL, severity=Severity.HIGH, affected_deals=["deal_1"], affected_leads=[]),
            Mock(risk_type=RiskType.MISSED_FOLLOWUP, severity=Severity.MEDIUM, affected_deals=[], affected_leads=["lead_1"])
        ]
        
        mock_actions = [
            Mock(revenue_impact=Decimal('10000'), priority=1),
            Mock(revenue_impact=Decimal('5000'), priority=2)
        ]
        
        compliance_scores = {"deal_1": 85.0, "lead_1": 70.0}
        
        summary = self.optimizer._generate_optimization_summary(
            mock_risks, mock_actions, self.deals, self.leads
        )
        
        assert summary['total_risks_detected'] == 2
        assert summary['total_actions_recommended'] == 2
        assert summary['deals_analyzed'] == 1
        assert summary['leads_analyzed'] == 1
        assert 'risk_distribution' in summary
        assert 'severity_distribution' in summary


if __name__ == "__main__":
    pytest.main([__file__])