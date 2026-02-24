"""
Human-in-the-loop system for ABOA.

This module provides the sales approval workflow engine for managing
revenue decisions that require human oversight, including approval routing,
timeout handling, escalation procedures, and comprehensive audit trails.
"""

from .models import (
    ApprovalAuditLog,
    ApprovalRequest,
    ApprovalResponse,
    EscalationEvent,
    EscalationRule,
    NotificationConfig
)
from .notification_service import NotificationService
from .sales_manager_interface import SalesManagerInterface

__all__ = [
    "ApprovalAuditLog",
    "ApprovalRequest", 
    "ApprovalResponse",
    "EscalationEvent",
    "EscalationRule",
    "NotificationConfig",
    "NotificationService",
    "SalesManagerInterface"
]