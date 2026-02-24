"""
Enum classes for the ABOA system.

This module defines all the enumeration types used throughout the revenue
operations system for consistent data validation and type safety.
"""

from enum import Enum


class LeadStatus(str, Enum):
    """Status of a lead in the sales pipeline."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"
    LOST = "lost"


class DealStage(str, Enum):
    """Stages of a deal in the sales pipeline."""
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    NEEDS_ANALYSIS = "needs_analysis"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ActivityType(str, Enum):
    """Types of sales activities."""
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    DEMO = "demo"
    FOLLOW_UP = "follow_up"
    PROPOSAL_SENT = "proposal_sent"
    CONTRACT_SENT = "contract_sent"
    OTHER = "other"


class RiskType(str, Enum):
    """Types of pipeline risks that can be detected."""
    STALLED_DEAL = "stalled_deal"
    MISSED_FOLLOWUP = "missed_followup"
    SOP_DEVIATION = "sop_deviation"
    INACTIVE_HIGH_VALUE = "inactive_high_value"
    LOW_ACTIVITY = "low_activity"


class SalesActionType(str, Enum):
    """Types of sales actions that can be executed."""
    CREATE_TASK = "create_task"
    UPDATE_DEAL = "update_deal"
    SEND_ALERT = "send_alert"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    UPDATE_LEAD_STATUS = "update_lead_status"
    ASSIGN_REP = "assign_rep"
    CREATE_FOLLOWUP_MESSAGE = "create_followup_message"
    UPDATE_OPPORTUNITY_FLAG = "update_opportunity_flag"


class Severity(str, Enum):
    """Severity levels for risks and issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionClass(str, Enum):
    """Classification of decisions for execution routing."""
    AUTO_EXECUTABLE = "auto_executable"
    APPROVAL_REQUIRED = "approval_required"
    INSIGHT_ONLY = "insight_only"


class ExecutionStatus(str, Enum):
    """Status of action execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """Status of approval requests."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"
    ESCALATED = "escalated"