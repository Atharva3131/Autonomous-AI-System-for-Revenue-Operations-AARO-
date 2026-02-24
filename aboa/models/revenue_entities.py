"""
Core revenue operations entity models.

This module contains the main data models for revenue operations including
Lead, Deal, SalesActivity, and SalesRep entities with Pydantic validation.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import ActivityType, DealStage, LeadStatus, RiskType, SalesActionType, Severity


class ContactInfo(BaseModel):
    """Contact information for leads and deals."""
    email: Optional[str] = Field(None, description="Primary email address")
    phone: Optional[str] = Field(None, description="Primary phone number")
    company: Optional[str] = Field(None, description="Company name")
    title: Optional[str] = Field(None, description="Job title")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v is not None and '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Basic phone validation if provided."""
        if v is not None and len(v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return v


class Lead(BaseModel):
    """Lead entity representing a potential customer."""
    id: str = Field(..., description="Unique identifier for the lead")
    source: str = Field(..., description="Source of the lead (e.g., website, referral)")
    contact_info: ContactInfo = Field(..., description="Contact information")
    status: LeadStatus = Field(LeadStatus.NEW, description="Current status of the lead")
    last_contact: Optional[datetime] = Field(None, description="Last contact timestamp")
    follow_up_due: Optional[datetime] = Field(None, description="When follow-up is due")
    estimated_value: Optional[Decimal] = Field(None, description="Estimated deal value", ge=0)
    assigned_rep: Optional[str] = Field(None, description="ID of assigned sales rep")
    contact_attempts: int = Field(0, description="Number of contact attempts", ge=0)
    qualification_score: Optional[float] = Field(None, description="Lead qualification score", ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @field_validator('follow_up_due')
    @classmethod
    def validate_follow_up_due(cls, v, info):
        """Ensure follow-up due date is after last contact if both are set."""
        if v is not None and 'last_contact' in info.data and info.data['last_contact'] is not None:
            if v <= info.data['last_contact']:
                raise ValueError('Follow-up due date must be after last contact')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    )


class SalesActivity(BaseModel):
    """Sales activity entity representing interactions with leads/deals."""
    id: str = Field(..., description="Unique identifier for the activity")
    deal_id: Optional[str] = Field(None, description="Associated deal ID")
    lead_id: Optional[str] = Field(None, description="Associated lead ID")
    activity_type: ActivityType = Field(..., description="Type of activity")
    completed_at: datetime = Field(..., description="When the activity was completed")
    rep_id: str = Field(..., description="ID of the sales rep who performed the activity")
    outcome: Optional[str] = Field(None, description="Outcome or result of the activity")
    next_action_scheduled: bool = Field(False, description="Whether a next action was scheduled")
    notes: Optional[str] = Field(None, description="Additional notes about the activity")
    duration_minutes: Optional[int] = Field(None, description="Duration in minutes", ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @model_validator(mode='after')
    def validate_association(self):
        """Ensure activity is associated with either a deal or lead."""
        if self.deal_id is None and self.lead_id is None:
            raise ValueError('Activity must be associated with either a deal or lead')
        return self

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class Deal(BaseModel):
    """Deal entity representing a sales opportunity."""
    id: str = Field(..., description="Unique identifier for the deal")
    lead_id: Optional[str] = Field(None, description="Associated lead ID")
    stage: DealStage = Field(DealStage.PROSPECTING, description="Current stage of the deal")
    value: Decimal = Field(..., description="Deal value", ge=0)
    probability: float = Field(..., description="Probability of closing (0-100)", ge=0, le=100)
    close_date: datetime = Field(..., description="Expected close date")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    activities: List[SalesActivity] = Field(default_factory=list, description="Associated activities")
    assigned_rep: str = Field(..., description="ID of assigned sales rep")
    days_in_current_stage: int = Field(0, description="Days in current stage", ge=0)
    next_action_due: Optional[datetime] = Field(None, description="When next action is due")
    contact_info: Optional[ContactInfo] = Field(None, description="Deal contact information")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @field_validator('probability')
    @classmethod
    def validate_probability_by_stage(cls, v, info):
        """Validate probability makes sense for the deal stage."""
        stage = info.data.get('stage')
        if stage:
            if stage == DealStage.CLOSED_WON and v != 100:
                raise ValueError('Closed won deals must have 100% probability')
            elif stage == DealStage.CLOSED_LOST and v != 0:
                raise ValueError('Closed lost deals must have 0% probability')
        return v

    @field_validator('close_date')
    @classmethod
    def validate_close_date(cls, v, info):
        """Ensure close date is reasonable."""
        # Make both datetimes timezone-aware for comparison
        now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        compare_date = v
        if v.tzinfo is None:
            compare_date = v.replace(tzinfo=timezone.utc)
        
        if compare_date < now:
            stage = info.data.get('stage')
            if stage and stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                raise ValueError('Close date cannot be in the past for open deals')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    )


class SalesRep(BaseModel):
    """Sales representative entity."""
    id: str = Field(..., description="Unique identifier for the sales rep")
    name: str = Field(..., description="Full name of the sales rep")
    email: str = Field(..., description="Email address")
    quota: Decimal = Field(..., description="Sales quota", ge=0)
    quota_attainment: float = Field(0.0, description="Quota attainment percentage", ge=0)
    pipeline_value: Decimal = Field(Decimal('0'), description="Total pipeline value", ge=0)
    activities_this_week: int = Field(0, description="Activities completed this week", ge=0)
    avg_deal_velocity: float = Field(0.0, description="Average deal velocity in days", ge=0)
    conversion_rates: Dict[str, float] = Field(
        default_factory=dict, 
        description="Conversion rates by stage"
    )
    active: bool = Field(True, description="Whether the rep is active")
    hire_date: Optional[datetime] = Field(None, description="Hire date")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @field_validator('conversion_rates')
    @classmethod
    def validate_conversion_rates(cls, v):
        """Validate conversion rates are between 0 and 100."""
        for stage, rate in v.items():
            if not 0 <= rate <= 100:
                raise ValueError(f'Conversion rate for {stage} must be between 0 and 100')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    )


class PipelineRisk(BaseModel):
    """Pipeline risk entity representing detected revenue risks."""
    risk_id: str = Field(..., description="Unique identifier for the risk")
    risk_type: RiskType = Field(..., description="Type of pipeline risk")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When the risk was detected")
    confidence: float = Field(..., description="Confidence level of risk detection (0-100)", ge=0, le=100)
    affected_deals: List[str] = Field(default_factory=list, description="List of deal IDs affected by this risk")
    affected_leads: List[str] = Field(default_factory=list, description="List of lead IDs affected by this risk")
    severity: Severity = Field(..., description="Severity level of the risk")
    description: str = Field(..., description="Human-readable description of the risk")
    recommended_actions: List[str] = Field(default_factory=list, description="List of recommended action IDs")
    resolved: bool = Field(False, description="Whether the risk has been resolved")
    resolved_at: Optional[datetime] = Field(None, description="When the risk was resolved")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @model_validator(mode='after')
    def validate_affected_entities(self):
        """Ensure at least one deal or lead is affected by the risk."""
        if not self.affected_deals and not self.affected_leads:
            raise ValueError('At least one deal or lead must be affected by the risk')
        return self

    @model_validator(mode='after')
    def validate_resolved_at(self):
        """Ensure resolved_at is set only when resolved is True."""
        if self.resolved and self.resolved_at is None:
            raise ValueError('resolved_at must be set when risk is resolved')
        elif not self.resolved and self.resolved_at is not None:
            raise ValueError('resolved_at should not be set when risk is not resolved')
        return self

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class SalesAction(BaseModel):
    """Sales action entity representing executable revenue operations actions."""
    action_id: str = Field(..., description="Unique identifier for the action")
    action_type: SalesActionType = Field(..., description="Type of sales action")
    target_system: str = Field(..., description="Target system for action execution")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    prerequisites: List[str] = Field(default_factory=list, description="List of prerequisite action IDs")
    expected_outcome: str = Field(..., description="Expected outcome of the action")
    revenue_impact: Optional[Decimal] = Field(None, description="Expected revenue impact", ge=0)
    priority: int = Field(1, description="Action priority (1=highest)", ge=1)
    executed: bool = Field(False, description="Whether the action has been executed")
    executed_at: Optional[datetime] = Field(None, description="When the action was executed")
    execution_result: Optional[str] = Field(None, description="Result of action execution")
    retry_count: int = Field(0, description="Number of retry attempts", ge=0)
    max_retries: int = Field(3, description="Maximum retry attempts", ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @model_validator(mode='after')
    def validate_executed_at(self):
        """Ensure executed_at is set only when executed is True."""
        if self.executed and self.executed_at is None:
            raise ValueError('executed_at must be set when action is executed')
        elif not self.executed and self.executed_at is not None:
            raise ValueError('executed_at should not be set when action is not executed')
        return self

    @field_validator('retry_count')
    @classmethod
    def validate_retry_count(cls, v, info):
        """Ensure retry count doesn't exceed max retries."""
        max_retries = info.data.get('max_retries', 3)
        if v > max_retries:
            raise ValueError(f'Retry count ({v}) cannot exceed max retries ({max_retries})')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    )


class RevenueContext(BaseModel):
    """Revenue context entity providing comprehensive deal and sales context."""
    context_id: str = Field(..., description="Unique identifier for the context")
    deal_history: List[Deal] = Field(default_factory=list, description="Historical deal data")
    rep_performance: Optional[SalesRep] = Field(None, description="Associated sales rep performance")
    similar_deals: List[Deal] = Field(default_factory=list, description="Similar deals for comparison")
    sales_playbook_guidance: List[str] = Field(default_factory=list, description="Relevant playbook guidance")
    market_conditions: Optional[Dict[str, Any]] = Field(None, description="Current market conditions")
    pipeline_risks: List[PipelineRisk] = Field(default_factory=list, description="Associated pipeline risks")
    recommended_actions: List[SalesAction] = Field(default_factory=list, description="Recommended actions")
    confidence_score: float = Field(0.0, description="Overall confidence in context (0-100)", ge=0, le=100)
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When context was generated")
    expires_at: Optional[datetime] = Field(None, description="When context expires")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v, info):
        """Ensure expiration is after generation."""
        generated_at = info.data.get('generated_at')
        if v is not None and generated_at is not None and v <= generated_at:
            raise ValueError('Expiration time must be after generation time')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class RevenueImpact(BaseModel):
    """Revenue impact entity for tracking the business impact of actions."""
    impact_id: str = Field(..., description="Unique identifier for the impact record")
    action_id: Optional[str] = Field(None, description="Associated action ID")
    pipeline_recovered: Optional[Decimal] = Field(None, description="Pipeline value recovered", ge=0)
    velocity_improvement: Optional[float] = Field(None, description="Deal velocity improvement percentage")
    deals_accelerated: int = Field(0, description="Number of deals accelerated", ge=0)
    manual_work_saved: Optional[int] = Field(None, description="Manual work saved in minutes", ge=0)
    conversion_rate_improvement: Optional[float] = Field(None, description="Conversion rate improvement percentage")
    measured_at: datetime = Field(default_factory=datetime.utcnow, description="When impact was measured")
    measurement_period_days: int = Field(30, description="Measurement period in days", ge=1)
    confidence: float = Field(0.0, description="Confidence in impact measurement (0-100)", ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @field_validator('velocity_improvement', 'conversion_rate_improvement')
    @classmethod
    def validate_percentage_improvements(cls, v):
        """Validate percentage improvements are reasonable."""
        if v is not None and (v < -100 or v > 1000):
            raise ValueError('Improvement percentage must be between -100% and 1000%')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    )


class RevenueDecisionLog(BaseModel):
    """Revenue decision log entity for tracking all system decisions."""
    decision_id: str = Field(..., description="Unique identifier for the decision")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Decision timestamp")
    pipeline_risk: Optional[PipelineRisk] = Field(None, description="Associated pipeline risk")
    recommendation: Optional[SalesAction] = Field(None, description="Recommended action")
    human_decision: Optional[str] = Field(None, description="Human decision if approval was required")
    execution_result: Optional[str] = Field(None, description="Result of action execution")
    revenue_impact: Optional[RevenueImpact] = Field(None, description="Measured revenue impact")
    decision_type: str = Field(..., description="Type of decision (auto/approval/insight)")
    confidence: float = Field(0.0, description="Decision confidence (0-100)", ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @field_validator('decision_type')
    @classmethod
    def validate_decision_type(cls, v):
        """Validate decision type is one of the allowed values."""
        allowed_types = ['auto', 'approval', 'insight']
        if v not in allowed_types:
            raise ValueError(f'Decision type must be one of: {allowed_types}')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )