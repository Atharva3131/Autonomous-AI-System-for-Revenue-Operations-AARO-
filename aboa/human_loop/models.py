"""
Human-in-the-loop models for sales approval workflows.

This module contains the data models for managing approval requests,
escalation procedures, and decision tracking in the AARO system.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import ApprovalStatus, Severity
from ..models.revenue_entities import Deal, PipelineRisk, RevenueContext, SalesAction, SalesRep


class EscalationRule(BaseModel):
    """Escalation rule for approval timeouts."""
    rule_id: str = Field(..., description="Unique identifier for the escalation rule")
    trigger_after_minutes: int = Field(..., description="Minutes after which to trigger escalation", ge=1)
    escalate_to: str = Field(..., description="User ID or role to escalate to")
    escalation_type: str = Field(..., description="Type of escalation (user, role, fallback)")
    fallback_action: Optional[str] = Field(None, description="Fallback action if escalation fails")
    active: bool = Field(True, description="Whether this rule is active")

    @field_validator('escalation_type')
    @classmethod
    def validate_escalation_type(cls, v):
        """Validate escalation type."""
        allowed_types = ['user', 'role', 'fallback']
        if v not in allowed_types:
            raise ValueError(f'Escalation type must be one of: {allowed_types}')
        return v


class ApprovalRequest(BaseModel):
    """Approval request for revenue decisions."""
    request_id: str = Field(..., description="Unique identifier for the approval request")
    pipeline_risk: PipelineRisk = Field(..., description="Associated pipeline risk")
    recommended_action: SalesAction = Field(..., description="Recommended sales action")
    revenue_context: RevenueContext = Field(..., description="Complete revenue context")
    approver_id: str = Field(..., description="ID of the assigned approver")
    status: ApprovalStatus = Field(ApprovalStatus.PENDING, description="Current approval status")
    priority: int = Field(1, description="Request priority (1=highest)", ge=1, le=5)
    timeout_minutes: int = Field(60, description="Timeout in minutes", ge=1)
    escalation_rules: List[EscalationRule] = Field(default_factory=list, description="Escalation rules")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    expires_at: datetime = Field(..., description="When the request expires")
    responded_at: Optional[datetime] = Field(None, description="When response was received")
    escalated_at: Optional[datetime] = Field(None, description="When request was escalated")
    escalated_to: Optional[str] = Field(None, description="Who the request was escalated to")

    def __init__(self, **data):
        """Initialize with calculated expiration time."""
        if 'expires_at' not in data and 'timeout_minutes' in data:
            data['expires_at'] = datetime.utcnow() + timedelta(minutes=data['timeout_minutes'])
        super().__init__(**data)

    @field_validator('priority')
    @classmethod
    def validate_priority_by_severity(cls, v, info):
        """Set priority based on pipeline risk severity if not explicitly provided."""
        if 'pipeline_risk' in info.data:
            risk = info.data['pipeline_risk']
            if isinstance(risk, PipelineRisk):
                if risk.severity == Severity.CRITICAL and v > 1:
                    return 1  # Critical risks get highest priority
                elif risk.severity == Severity.HIGH and v > 2:
                    return 2  # High risks get high priority
        return v

    @field_validator('timeout_minutes')
    @classmethod
    def validate_timeout_by_urgency(cls, v, info):
        """Adjust timeout based on deal urgency and value."""
        if 'revenue_context' in info.data and 'pipeline_risk' in info.data:
            context = info.data['revenue_context']
            risk = info.data['pipeline_risk']
            
            if isinstance(context, RevenueContext) and isinstance(risk, PipelineRisk):
                # Critical risks get shorter timeouts
                if risk.severity == Severity.CRITICAL:
                    return min(v, 30)  # Max 30 minutes for critical
                elif risk.severity == Severity.HIGH:
                    return min(v, 60)  # Max 60 minutes for high
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    )


class ApprovalResponse(BaseModel):
    """Response to an approval request."""
    response_id: str = Field(..., description="Unique identifier for the response")
    request_id: str = Field(..., description="Associated approval request ID")
    approver_id: str = Field(..., description="ID of the approver")
    decision: ApprovalStatus = Field(..., description="Approval decision")
    reasoning: Optional[str] = Field(None, description="Reasoning for the decision")
    modified_action: Optional[SalesAction] = Field(None, description="Modified action if applicable")
    additional_context_requested: bool = Field(False, description="Whether more context was requested")
    context_request_details: Optional[str] = Field(None, description="Details of context request")
    responded_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    confidence: float = Field(0.0, description="Approver confidence in decision (0-100)", ge=0, le=100)

    @field_validator('decision')
    @classmethod
    def validate_decision_status(cls, v):
        """Validate decision status is appropriate for responses."""
        valid_decisions = [ApprovalStatus.APPROVED, ApprovalStatus.DENIED]
        if v not in valid_decisions:
            raise ValueError(f'Decision must be one of: {[d.value for d in valid_decisions]}')
        return v

    @field_validator('modified_action')
    @classmethod
    def validate_modified_action(cls, v, info):
        """Ensure modified action is provided when decision is approved with modifications."""
        decision = info.data.get('decision')
        if decision == ApprovalStatus.APPROVED and v is None:
            # Modified action is optional for approved decisions
            pass
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class ApprovalAuditLog(BaseModel):
    """Audit log entry for approval workflow tracking."""
    log_id: str = Field(..., description="Unique identifier for the log entry")
    request_id: str = Field(..., description="Associated approval request ID")
    event_type: str = Field(..., description="Type of event (created, responded, escalated, timeout)")
    event_details: Dict[str, Any] = Field(default_factory=dict, description="Event-specific details")
    user_id: Optional[str] = Field(None, description="User associated with the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    system_generated: bool = Field(False, description="Whether event was system-generated")

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v):
        """Validate event type."""
        allowed_types = [
            'created', 'responded', 'escalated', 'timeout', 'cancelled', 
            'modified', 'context_requested', 'forwarded', 'notification_sent'
        ]
        if v not in allowed_types:
            raise ValueError(f'Event type must be one of: {allowed_types}')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class NotificationConfig(BaseModel):
    """Configuration for approval notifications."""
    config_id: str = Field(..., description="Unique identifier for the config")
    user_id: str = Field(..., description="User ID this config applies to")
    email_enabled: bool = Field(True, description="Whether email notifications are enabled")
    sms_enabled: bool = Field(False, description="Whether SMS notifications are enabled")
    slack_enabled: bool = Field(False, description="Whether Slack notifications are enabled")
    email_address: Optional[str] = Field(None, description="Email address for notifications")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS")
    slack_user_id: Optional[str] = Field(None, description="Slack user ID")
    notification_frequency: str = Field("immediate", description="Notification frequency")
    quiet_hours_start: Optional[int] = Field(None, description="Quiet hours start (24h format)", ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(None, description="Quiet hours end (24h format)", ge=0, le=23)
    timezone: str = Field("UTC", description="User timezone")

    @field_validator('notification_frequency')
    @classmethod
    def validate_notification_frequency(cls, v):
        """Validate notification frequency."""
        allowed_frequencies = ['immediate', 'hourly', 'daily', 'disabled']
        if v not in allowed_frequencies:
            raise ValueError(f'Notification frequency must be one of: {allowed_frequencies}')
        return v

    @field_validator('email_address')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v is not None and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class EscalationEvent(BaseModel):
    """Event representing an escalation in the approval workflow."""
    event_id: str = Field(..., description="Unique identifier for the escalation event")
    request_id: str = Field(..., description="Associated approval request ID")
    escalation_rule: EscalationRule = Field(..., description="Rule that triggered the escalation")
    original_approver: str = Field(..., description="Original approver ID")
    escalated_to: str = Field(..., description="New approver ID")
    escalation_reason: str = Field(..., description="Reason for escalation")
    escalated_at: datetime = Field(default_factory=datetime.utcnow, description="Escalation timestamp")
    resolved: bool = Field(False, description="Whether escalation was resolved")
    resolved_at: Optional[datetime] = Field(None, description="When escalation was resolved")
    fallback_applied: bool = Field(False, description="Whether fallback action was applied")
    fallback_details: Optional[str] = Field(None, description="Details of fallback action")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )