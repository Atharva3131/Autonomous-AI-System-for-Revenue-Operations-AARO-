"""
Unit tests for the pipeline risk detection engine.

Tests the PipelineRiskDetector class and its specific risk detection methods
to ensure compliance with Requirements 3.1, 3.2, 3.3, 3.4.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aboa.decision.pipeline_risk_detector import PipelineRiskDetector
from aboa.models.enums import (
    ActivityType, DealStage, LeadStatus, RiskType, Severity
)
from aboa.models.revenue_entities import (
    ContactInfo, Deal, Lead, SalesActivity, SalesRep
)


class TestPipelineRiskDetector:
    """Test suite for PipelineRiskDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PipelineRiskDetector()
        self.now = datetime.now(timezone.utc)
        
        # Create test contact info
        self.contact_info = ContactInfo(
            email="test@example.com",
            phone="555-123-4567",
            company="Test Company",
            title="CEO",
            first_name="John",
            last_name="Doe"
        )
        
        # Create test sales rep
        self.sales_rep = SalesRep(
            id="rep_1",
            name="Jane Smith",
            email="jane@company.com",
            quota=Decimal('100000'),
            quota_attainment=75.0,
            pipeline_value=Decimal('250000')
        )
    
    def test_detect_stalled_deals(self):
        """Test detection of stalled deals (Requirement 3.1)."""
        # Create a deal that's been stalled for 20 days in prospecting stage
        stalled_deal = Deal(
            id="deal_1",
            stage=DealStage.PROSPECTING,
            value=Decimal('15000'),
            probability=50.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            days_in_current_stage=20,  # Exceeds 14-day threshold
            contact_info=self.contact_info
        )
        
        # Create a normal deal
        normal_deal = Deal(
            id="deal_2",
            stage=DealStage.PROSPECTING,
            value=Decimal('10000'),
            probability=60.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            days_in_current_stage=10,  # Within threshold
            contact_info=self.contact_info
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[stalled_deal, normal_deal],
            leads=[],
            activities=[],
            reps=[self.sales_rep]
        )
        
        # Should detect one stalled deal risk
        stalled_risks = [r for r in risks if r.risk_type == RiskType.STALLED_DEAL]
        assert len(stalled_risks) == 1
        assert stalled_risks[0].affected_deals == ["deal_1"]
        assert stalled_risks[0].severity == Severity.MEDIUM
        assert "stalled in prospecting stage for 20 days" in stalled_risks[0].description
    
    def test_detect_missed_followups_deals(self):
        """Test detection of missed follow-ups for deals (Requirement 3.2)."""
        deal = Deal(
            id="deal_1",
            stage=DealStage.QUALIFICATION,
            value=Decimal('25000'),
            probability=70.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            contact_info=self.contact_info
        )
        
        # Create a meeting activity without next action scheduled
        meeting_activity = SalesActivity(
            id="activity_1",
            deal_id="deal_1",
            activity_type=ActivityType.MEETING,
            completed_at=self.now - timedelta(days=1),
            rep_id="rep_1",
            next_action_scheduled=False,  # This should trigger the risk
            notes="Had a good meeting but no follow-up scheduled"
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[deal],
            leads=[],
            activities=[meeting_activity],
            reps=[self.sales_rep]
        )
        
        # Should detect missed follow-up risk
        followup_risks = [r for r in risks if r.risk_type == RiskType.MISSED_FOLLOWUP]
        assert len(followup_risks) == 1
        assert followup_risks[0].affected_deals == ["deal_1"]
        assert "recent meetings without scheduled follow-up" in followup_risks[0].description
    
    def test_detect_missed_followups_leads(self):
        """Test detection of missed follow-ups for leads (Requirement 3.2)."""
        lead = Lead(
            id="lead_1",
            source="website",
            contact_info=self.contact_info,
            status=LeadStatus.CONTACTED,
            estimated_value=Decimal('20000'),
            assigned_rep="rep_1"
        )
        
        # Create a call activity without next action scheduled
        call_activity = SalesActivity(
            id="activity_1",
            lead_id="lead_1",
            activity_type=ActivityType.CALL,
            completed_at=self.now - timedelta(days=1),
            rep_id="rep_1",
            next_action_scheduled=False,
            notes="Initial qualification call completed"
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[],
            leads=[lead],
            activities=[call_activity],
            reps=[self.sales_rep]
        )
        
        # Should detect missed follow-up risk for lead
        followup_risks = [r for r in risks if r.risk_type == RiskType.MISSED_FOLLOWUP]
        assert len(followup_risks) == 1
        assert "recent interactions without scheduled follow-up" in followup_risks[0].description
    
    def test_detect_inactive_high_value_deals(self):
        """Test detection of inactive high-value deals (Requirement 3.3)."""
        # Create high-value deal with no recent activity
        high_value_deal = Deal(
            id="deal_1",
            stage=DealStage.PROPOSAL,
            value=Decimal('50000'),  # Above high_value_threshold
            probability=80.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            last_activity=self.now - timedelta(days=10),  # 10 days ago, exceeds 7-day threshold
            contact_info=self.contact_info
        )
        
        # Create low-value deal (should not trigger)
        low_value_deal = Deal(
            id="deal_2",
            stage=DealStage.PROPOSAL,
            value=Decimal('5000'),  # Below threshold
            probability=80.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            last_activity=self.now - timedelta(days=10),
            contact_info=self.contact_info
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[high_value_deal, low_value_deal],
            leads=[],
            activities=[],
            reps=[self.sales_rep]
        )
        
        # Should detect only the high-value inactive deal
        inactive_risks = [r for r in risks if r.risk_type == RiskType.INACTIVE_HIGH_VALUE]
        assert len(inactive_risks) == 1
        assert inactive_risks[0].affected_deals == ["deal_1"]
        assert inactive_risks[0].severity == Severity.CRITICAL  # $50k is critical threshold
        assert "no activity for 10 days" in inactive_risks[0].description
    
    def test_detect_insufficient_lead_touchpoints(self):
        """Test detection of leads with insufficient touchpoints (Requirement 3.4)."""
        # Lead with insufficient touchpoints
        low_touch_lead = Lead(
            id="lead_1",
            source="website",
            contact_info=self.contact_info,
            status=LeadStatus.NEW,
            contact_attempts=1,  # Only 1 attempt, below minimum of 3
            assigned_rep="rep_1"
        )
        
        # Lead with sufficient touchpoints
        high_touch_lead = Lead(
            id="lead_2",
            source="referral",
            contact_info=self.contact_info,
            status=LeadStatus.CONTACTED,
            contact_attempts=2,  # 2 attempts + 2 activities = 4 total (above minimum)
            assigned_rep="rep_1"
        )
        
        # Activities for high_touch_lead
        activities = [
            SalesActivity(
                id="activity_1",
                lead_id="lead_2",
                activity_type=ActivityType.CALL,
                completed_at=self.now - timedelta(days=1),
                rep_id="rep_1"
            ),
            SalesActivity(
                id="activity_2",
                lead_id="lead_2",
                activity_type=ActivityType.EMAIL,
                completed_at=self.now - timedelta(days=2),
                rep_id="rep_1"
            )
        ]
        
        risks = self.detector.detect_pipeline_risks(
            deals=[],
            leads=[low_touch_lead, high_touch_lead],
            activities=activities,
            reps=[self.sales_rep]
        )
        
        # Should detect only the low-touch lead
        low_activity_risks = [r for r in risks if r.risk_type == RiskType.LOW_ACTIVITY]
        assert len(low_activity_risks) == 1
        assert "only 1 touchpoints" in low_activity_risks[0].description
    
    def test_severity_classification(self):
        """Test risk severity classification based on deal values."""
        # Critical value deal
        critical_deal = Deal(
            id="deal_1",
            stage=DealStage.NEGOTIATION,
            value=Decimal('75000'),  # Above critical threshold (50k)
            probability=90.0,
            close_date=self.now + timedelta(days=15),
            assigned_rep="rep_1",
            days_in_current_stage=10,  # Exceeds 5-day threshold for negotiation
            contact_info=self.contact_info
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[critical_deal],
            leads=[],
            activities=[],
            reps=[self.sales_rep]
        )
        
        stalled_risks = [r for r in risks if r.risk_type == RiskType.STALLED_DEAL]
        assert len(stalled_risks) == 1
        assert stalled_risks[0].severity == Severity.CRITICAL
    
    def test_confidence_calculation(self):
        """Test confidence level calculation for risk detection."""
        # Deal stalled for a long time should have high confidence
        very_stalled_deal = Deal(
            id="deal_1",
            stage=DealStage.PROSPECTING,
            value=Decimal('15000'),
            probability=50.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            days_in_current_stage=30,  # Way over 14-day threshold
            contact_info=self.contact_info
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[very_stalled_deal],
            leads=[],
            activities=[],
            reps=[self.sales_rep]
        )
        
        stalled_risks = [r for r in risks if r.risk_type == RiskType.STALLED_DEAL]
        assert len(stalled_risks) == 1
        assert stalled_risks[0].confidence > 85.0  # Should have high confidence
    
    def test_no_risks_for_closed_deals(self):
        """Test that closed deals don't generate risks."""
        closed_won_deal = Deal(
            id="deal_1",
            stage=DealStage.CLOSED_WON,
            value=Decimal('50000'),
            probability=100.0,
            close_date=self.now - timedelta(days=5),
            assigned_rep="rep_1",
            days_in_current_stage=100,  # Would normally trigger stalled risk
            contact_info=self.contact_info
        )
        
        closed_lost_deal = Deal(
            id="deal_2",
            stage=DealStage.CLOSED_LOST,
            value=Decimal('30000'),
            probability=0.0,
            close_date=self.now - timedelta(days=3),
            assigned_rep="rep_1",
            days_in_current_stage=50,
            contact_info=self.contact_info
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[closed_won_deal, closed_lost_deal],
            leads=[],
            activities=[],
            reps=[self.sales_rep]
        )
        
        # Should not detect any risks for closed deals
        assert len(risks) == 0
    
    def test_recommended_actions_generation(self):
        """Test that appropriate recommended actions are generated."""
        stalled_deal = Deal(
            id="deal_1",
            stage=DealStage.QUALIFICATION,
            value=Decimal('20000'),
            probability=60.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            days_in_current_stage=15,  # Exceeds 10-day threshold
            contact_info=self.contact_info
        )
        
        risks = self.detector.detect_pipeline_risks(
            deals=[stalled_deal],
            leads=[],
            activities=[],
            reps=[self.sales_rep]
        )
        
        stalled_risks = [r for r in risks if r.risk_type == RiskType.STALLED_DEAL]
        assert len(stalled_risks) == 1
        
        # Check that recommended actions are generated
        actions = stalled_risks[0].recommended_actions
        assert len(actions) > 0
        assert any("followup_task" in action for action in actions)
        assert any("manager_review" in action for action in actions)
    
    def test_custom_configuration(self):
        """Test that custom configuration affects risk detection."""
        # Create detector with custom thresholds
        custom_config = {
            'stalled_deal_thresholds': {
                DealStage.PROSPECTING: 5,  # Much lower threshold
            },
            'no_activity_threshold_days': 3,
            'high_value_threshold': Decimal('5000'),  # Lower threshold
            'minimum_lead_touchpoints': 5,  # Higher threshold
            'missed_followup_threshold_days': 1,
            'critical_deal_value': Decimal('20000'),
            'high_risk_deal_value': Decimal('10000'),
            'medium_risk_deal_value': Decimal('5000'),
        }
        
        custom_detector = PipelineRiskDetector(config=custom_config)
        
        # Deal that wouldn't trigger with default config but should with custom
        deal = Deal(
            id="deal_1",
            stage=DealStage.PROSPECTING,
            value=Decimal('8000'),
            probability=50.0,
            close_date=self.now + timedelta(days=30),
            assigned_rep="rep_1",
            days_in_current_stage=7,  # Would be OK with default (14) but not custom (5)
            contact_info=self.contact_info
        )
        
        risks = custom_detector.detect_pipeline_risks(
            deals=[deal],
            leads=[],
            activities=[],
            reps=[self.sales_rep]
        )
        
        # Should detect stalled deal with custom config
        stalled_risks = [r for r in risks if r.risk_type == RiskType.STALLED_DEAL]
        assert len(stalled_risks) == 1