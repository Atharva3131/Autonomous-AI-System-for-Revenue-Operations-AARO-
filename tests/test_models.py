"""
Unit tests for ABOA data models.

Tests the core revenue operations entity models including validation logic,
enum values, and model relationships.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from aboa.models import (
    ActivityType,
    ContactInfo,
    Deal,
    DealStage,
    Lead,
    LeadStatus,
    PipelineRisk,
    RevenueContext,
    RevenueDecisionLog,
    RevenueImpact,
    RiskType,
    SalesAction,
    SalesActionType,
    SalesActivity,
    SalesRep,
    Severity,
)


class TestContactInfo:
    """Test ContactInfo model validation."""

    def test_valid_contact_info(self):
        """Test creating valid contact info."""
        contact = ContactInfo(
            email="test@example.com",
            phone="555-123-4567",
            company="Test Corp",
            title="CEO",
            first_name="John",
            last_name="Doe"
        )
        assert contact.email == "test@example.com"
        assert contact.company == "Test Corp"

    def test_invalid_email(self):
        """Test invalid email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            ContactInfo(email="invalid-email")

    def test_invalid_phone(self):
        """Test invalid phone validation."""
        with pytest.raises(ValueError, match="Phone number must be at least 10 digits"):
            ContactInfo(phone="123")


class TestLead:
    """Test Lead model validation."""

    def test_valid_lead(self):
        """Test creating a valid lead."""
        contact = ContactInfo(email="lead@example.com", company="Lead Corp")
        lead = Lead(
            id="lead-123",
            source="website",
            contact_info=contact,
            status=LeadStatus.NEW,
            estimated_value=Decimal("10000")
        )
        assert lead.id == "lead-123"
        assert lead.status == LeadStatus.NEW
        assert lead.contact_attempts == 0

    def test_follow_up_validation(self):
        """Test follow-up due date validation."""
        contact = ContactInfo(email="lead@example.com")
        last_contact = datetime.utcnow()
        
        with pytest.raises(ValueError, match="Follow-up due date must be after last contact"):
            Lead(
                id="lead-123",
                source="website",
                contact_info=contact,
                last_contact=last_contact,
                follow_up_due=last_contact - timedelta(hours=1)
            )

    def test_negative_estimated_value(self):
        """Test negative estimated value validation."""
        contact = ContactInfo(email="lead@example.com")
        
        with pytest.raises(ValueError):
            Lead(
                id="lead-123",
                source="website",
                contact_info=contact,
                estimated_value=Decimal("-1000")
            )


class TestSalesActivity:
    """Test SalesActivity model validation."""

    def test_valid_activity(self):
        """Test creating a valid sales activity."""
        activity = SalesActivity(
            id="activity-123",
            deal_id="deal-456",
            activity_type=ActivityType.CALL,
            completed_at=datetime.utcnow(),
            rep_id="rep-789",
            outcome="Positive response",
            next_action_scheduled=True
        )
        assert activity.activity_type == ActivityType.CALL
        assert activity.next_action_scheduled is True

    def test_missing_association(self):
        """Test validation when neither deal_id nor lead_id is provided."""
        with pytest.raises(ValueError, match="Activity must be associated with either a deal or lead"):
            SalesActivity(
                id="activity-123",
                activity_type=ActivityType.EMAIL,
                completed_at=datetime.utcnow(),
                rep_id="rep-789"
            )

    def test_valid_with_lead_id(self):
        """Test activity with lead_id is valid."""
        activity = SalesActivity(
            id="activity-123",
            lead_id="lead-456",
            activity_type=ActivityType.EMAIL,
            completed_at=datetime.utcnow(),
            rep_id="rep-789"
        )
        assert activity.lead_id == "lead-456"


class TestDeal:
    """Test Deal model validation."""

    def test_valid_deal(self):
        """Test creating a valid deal."""
        deal = Deal(
            id="deal-123",
            stage=DealStage.QUALIFICATION,
            value=Decimal("50000"),
            probability=75.0,
            close_date=datetime.utcnow() + timedelta(days=30),
            assigned_rep="rep-456"
        )
        assert deal.stage == DealStage.QUALIFICATION
        assert deal.value == Decimal("50000")

    def test_closed_won_probability(self):
        """Test closed won deals must have 100% probability."""
        with pytest.raises(ValueError, match="Closed won deals must have 100% probability"):
            Deal(
                id="deal-123",
                stage=DealStage.CLOSED_WON,
                value=Decimal("50000"),
                probability=75.0,
                close_date=datetime.utcnow(),
                assigned_rep="rep-456"
            )

    def test_closed_lost_probability(self):
        """Test closed lost deals must have 0% probability."""
        with pytest.raises(ValueError, match="Closed lost deals must have 0% probability"):
            Deal(
                id="deal-123",
                stage=DealStage.CLOSED_LOST,
                value=Decimal("50000"),
                probability=25.0,
                close_date=datetime.utcnow(),
                assigned_rep="rep-456"
            )

    def test_past_close_date_open_deal(self):
        """Test open deals cannot have past close dates."""
        with pytest.raises(ValueError, match="Close date cannot be in the past for open deals"):
            Deal(
                id="deal-123",
                stage=DealStage.QUALIFICATION,
                value=Decimal("50000"),
                probability=75.0,
                close_date=datetime.utcnow() - timedelta(days=1),
                assigned_rep="rep-456"
            )


class TestSalesRep:
    """Test SalesRep model validation."""

    def test_valid_sales_rep(self):
        """Test creating a valid sales rep."""
        rep = SalesRep(
            id="rep-123",
            name="Jane Smith",
            email="jane@company.com",
            quota=Decimal("1000000"),
            quota_attainment=85.5,
            conversion_rates={"qualification": 75.0, "proposal": 50.0}
        )
        assert rep.name == "Jane Smith"
        assert rep.quota_attainment == 85.5

    def test_invalid_email(self):
        """Test invalid email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            SalesRep(
                id="rep-123",
                name="Jane Smith",
                email="invalid-email",
                quota=Decimal("1000000")
            )

    def test_invalid_conversion_rates(self):
        """Test invalid conversion rates validation."""
        with pytest.raises(ValueError, match="Conversion rate for qualification must be between 0 and 100"):
            SalesRep(
                id="rep-123",
                name="Jane Smith",
                email="jane@company.com",
                quota=Decimal("1000000"),
                conversion_rates={"qualification": 150.0}
            )


class TestPipelineRisk:
    """Test PipelineRisk model validation."""

    def test_valid_pipeline_risk(self):
        """Test creating a valid pipeline risk."""
        risk = PipelineRisk(
            risk_id="risk-123",
            risk_type=RiskType.STALLED_DEAL,
            confidence=85.5,
            affected_deals=["deal-1", "deal-2"],
            severity=Severity.HIGH,
            description="Deals stalled in qualification stage for over 30 days",
            recommended_actions=["action-1", "action-2"]
        )
        assert risk.risk_type == RiskType.STALLED_DEAL
        assert risk.confidence == 85.5
        assert len(risk.affected_deals) == 2
        assert risk.resolved is False

    def test_empty_affected_deals(self):
        """Test validation when no deals or leads are affected."""
        with pytest.raises(ValueError, match="At least one deal or lead must be affected by the risk"):
            PipelineRisk(
                risk_id="risk-123",
                risk_type=RiskType.STALLED_DEAL,
                confidence=85.5,
                affected_deals=[],
                affected_leads=[],  # Also empty
                severity=Severity.HIGH,
                description="Test risk"
            )

    def test_resolved_validation(self):
        """Test resolved_at validation."""
        # Test resolved=True without resolved_at
        with pytest.raises(ValueError, match="resolved_at must be set when risk is resolved"):
            PipelineRisk(
                risk_id="risk-123",
                risk_type=RiskType.STALLED_DEAL,
                confidence=85.5,
                affected_deals=["deal-1"],
                severity=Severity.HIGH,
                description="Test risk",
                resolved=True
            )

        # Test resolved=False with resolved_at
        with pytest.raises(ValueError, match="resolved_at should not be set when risk is not resolved"):
            PipelineRisk(
                risk_id="risk-123",
                risk_type=RiskType.STALLED_DEAL,
                confidence=85.5,
                affected_deals=["deal-1"],
                severity=Severity.HIGH,
                description="Test risk",
                resolved=False,
                resolved_at=datetime.utcnow()
            )


class TestSalesAction:
    """Test SalesAction model validation."""

    def test_valid_sales_action(self):
        """Test creating a valid sales action."""
        action = SalesAction(
            action_id="action-123",
            action_type=SalesActionType.CREATE_TASK,
            target_system="crm",
            parameters={"task_type": "follow_up", "priority": "high"},
            expected_outcome="Follow-up task created for stalled deal",
            revenue_impact=Decimal("25000"),
            priority=1
        )
        assert action.action_type == SalesActionType.CREATE_TASK
        assert action.revenue_impact == Decimal("25000")
        assert action.executed is False
        assert action.retry_count == 0

    def test_executed_validation(self):
        """Test executed_at validation."""
        # Test executed=True without executed_at
        with pytest.raises(ValueError, match="executed_at must be set when action is executed"):
            SalesAction(
                action_id="action-123",
                action_type=SalesActionType.CREATE_TASK,
                target_system="crm",
                expected_outcome="Test outcome",
                executed=True
            )

        # Test executed=False with executed_at
        with pytest.raises(ValueError, match="executed_at should not be set when action is not executed"):
            SalesAction(
                action_id="action-123",
                action_type=SalesActionType.CREATE_TASK,
                target_system="crm",
                expected_outcome="Test outcome",
                executed=False,
                executed_at=datetime.utcnow()
            )

    def test_retry_count_validation(self):
        """Test retry count validation."""
        with pytest.raises(ValueError, match="Retry count \\(5\\) cannot exceed max retries \\(3\\)"):
            SalesAction(
                action_id="action-123",
                action_type=SalesActionType.CREATE_TASK,
                target_system="crm",
                expected_outcome="Test outcome",
                retry_count=5,
                max_retries=3
            )


class TestRevenueContext:
    """Test RevenueContext model validation."""

    def test_valid_revenue_context(self):
        """Test creating a valid revenue context."""
        deal = Deal(
            id="deal-123",
            stage=DealStage.QUALIFICATION,
            value=Decimal("50000"),
            probability=75.0,
            close_date=datetime.utcnow() + timedelta(days=30),
            assigned_rep="rep-456"
        )
        
        rep = SalesRep(
            id="rep-456",
            name="John Doe",
            email="john@company.com",
            quota=Decimal("1000000")
        )

        context = RevenueContext(
            context_id="context-123",
            deal_history=[deal],
            rep_performance=rep,
            sales_playbook_guidance=["Follow up within 24 hours", "Use discovery questions"],
            confidence_score=85.0
        )
        assert context.confidence_score == 85.0
        assert len(context.deal_history) == 1
        assert context.rep_performance.name == "John Doe"

    def test_expires_at_validation(self):
        """Test expires_at validation."""
        generated_at = datetime.utcnow()
        
        with pytest.raises(ValueError, match="Expiration time must be after generation time"):
            RevenueContext(
                context_id="context-123",
                generated_at=generated_at,
                expires_at=generated_at - timedelta(hours=1)
            )


class TestRevenueImpact:
    """Test RevenueImpact model validation."""

    def test_valid_revenue_impact(self):
        """Test creating a valid revenue impact."""
        impact = RevenueImpact(
            impact_id="impact-123",
            action_id="action-456",
            pipeline_recovered=Decimal("100000"),
            velocity_improvement=15.5,
            deals_accelerated=3,
            manual_work_saved=120,
            conversion_rate_improvement=5.2,
            confidence=90.0
        )
        assert impact.pipeline_recovered == Decimal("100000")
        assert impact.velocity_improvement == 15.5
        assert impact.deals_accelerated == 3

    def test_percentage_improvement_validation(self):
        """Test percentage improvement validation."""
        # Test velocity improvement out of range
        with pytest.raises(ValueError, match="Improvement percentage must be between -100% and 1000%"):
            RevenueImpact(
                impact_id="impact-123",
                velocity_improvement=1500.0
            )

        # Test conversion rate improvement out of range
        with pytest.raises(ValueError, match="Improvement percentage must be between -100% and 1000%"):
            RevenueImpact(
                impact_id="impact-123",
                conversion_rate_improvement=-150.0
            )


class TestRevenueDecisionLog:
    """Test RevenueDecisionLog model validation."""

    def test_valid_decision_log(self):
        """Test creating a valid revenue decision log."""
        risk = PipelineRisk(
            risk_id="risk-123",
            risk_type=RiskType.STALLED_DEAL,
            confidence=85.5,
            affected_deals=["deal-1"],
            severity=Severity.HIGH,
            description="Test risk"
        )

        action = SalesAction(
            action_id="action-123",
            action_type=SalesActionType.CREATE_TASK,
            target_system="crm",
            expected_outcome="Test outcome"
        )

        log = RevenueDecisionLog(
            decision_id="decision-123",
            pipeline_risk=risk,
            recommendation=action,
            decision_type="auto",
            confidence=85.0
        )
        assert log.decision_type == "auto"
        assert log.pipeline_risk.risk_id == "risk-123"
        assert log.recommendation.action_id == "action-123"

    def test_decision_type_validation(self):
        """Test decision type validation."""
        with pytest.raises(ValueError, match="Decision type must be one of: \\['auto', 'approval', 'insight'\\]"):
            RevenueDecisionLog(
                decision_id="decision-123",
                decision_type="invalid",
                confidence=85.0
            )