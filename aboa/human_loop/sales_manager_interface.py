"""
Sales Manager Interface for approval workflow management.

This module implements the core approval workflow engine for revenue decisions,
including approval routing, timeout handling, escalation procedures, and
decision tracking with comprehensive audit trails.

Implements Requirements 5.1, 5.2, 5.3, 5.7:
- Generate clear recommendations with supporting pipeline data and revenue impact analysis
- Present decision context including deal history, rep performance, and recommended sales actions  
- Set appropriate timeouts for decision responses based on deal urgency
- Handle approval timeouts with escalation to senior sales management or safe fallback actions
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from ..core.exceptions import ABOAException
from ..models.enums import ApprovalStatus, DecisionClass, Severity
from ..models.revenue_entities import Deal, PipelineRisk, RevenueContext, SalesAction, SalesRep
from .models import (
    ApprovalAuditLog,
    ApprovalRequest,
    ApprovalResponse,
    EscalationEvent,
    EscalationRule,
    NotificationConfig
)

logger = logging.getLogger(__name__)


class ApprovalWorkflowError(ABOAException):
    """Exception raised for approval workflow errors."""
    pass


class SalesManagerInterface:
    """
    Sales Manager Interface for approval workflow management.
    
    This class manages the complete approval workflow for revenue decisions,
    including request generation, routing, timeout handling, escalation,
    and comprehensive audit tracking.
    
    Implements Requirements 5.1, 5.2, 5.3, 5.7.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the Sales Manager Interface.
        
        Args:
            config: Configuration dictionary for approval workflows
        """
        self.config = config or self._get_default_config()
        self.active_requests: Dict[str, ApprovalRequest] = {}
        self.audit_logs: List[ApprovalAuditLog] = []
        self.notification_configs: Dict[str, NotificationConfig] = {}
        self.escalation_events: List[EscalationEvent] = []
        
        logger.info("SalesManagerInterface initialized with config: %s", self.config)
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for approval workflows."""
        return {
            'default_timeout_minutes': 60,
            'critical_timeout_minutes': 30,
            'high_timeout_minutes': 60,
            'medium_timeout_minutes': 120,
            'low_timeout_minutes': 240,
            'max_escalation_levels': 3,
            'default_escalation_minutes': 30,
            'enable_fallback_actions': True,
            'audit_retention_days': 90,
            'notification_retry_attempts': 3,
            'notification_retry_delay_minutes': 5
        }
    
    def request_approval(
        self,
        pipeline_risk: PipelineRisk,
        recommended_action: SalesAction,
        revenue_context: RevenueContext,
        approver_id: str,
        priority: Optional[int] = None,
        custom_timeout_minutes: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Generate an approval request with complete revenue context.
        
        Implements Requirement 5.1: WHEN decisions require human approval, 
        THE Human_Loop SHALL generate clear recommendations with supporting 
        pipeline data and revenue impact analysis.
        
        Implements Requirement 5.2: THE Human_Loop SHALL present decision context 
        including deal history, rep performance, and recommended sales actions.
        
        Args:
            pipeline_risk: The detected pipeline risk requiring approval
            recommended_action: The recommended sales action
            revenue_context: Complete revenue context with deal history and rep performance
            approver_id: ID of the assigned approver
            priority: Request priority (1=highest, 5=lowest)
            custom_timeout_minutes: Custom timeout in minutes
            
        Returns:
            ApprovalRequest: The generated approval request
            
        Raises:
            ApprovalWorkflowError: If request generation fails
        """
        try:
            request_id = str(uuid4())
            
            # Determine timeout based on deal urgency and risk severity
            timeout_minutes = self._calculate_timeout(
                pipeline_risk, revenue_context, custom_timeout_minutes
            )
            
            # Determine priority based on risk severity and deal values
            if priority is None:
                priority = self._calculate_priority(pipeline_risk, revenue_context)
            
            # Generate escalation rules based on risk and deal characteristics
            escalation_rules = self._generate_escalation_rules(
                pipeline_risk, revenue_context, approver_id
            )
            
            # Create the approval request
            approval_request = ApprovalRequest(
                request_id=request_id,
                pipeline_risk=pipeline_risk,
                recommended_action=recommended_action,
                revenue_context=revenue_context,
                approver_id=approver_id,
                priority=priority,
                timeout_minutes=timeout_minutes,
                escalation_rules=escalation_rules
            )
            
            # Store the active request
            self.active_requests[request_id] = approval_request
            
            # Log the request creation
            self._log_audit_event(
                request_id=request_id,
                event_type="created",
                event_details={
                    "approver_id": approver_id,
                    "risk_type": pipeline_risk.risk_type.value,
                    "risk_severity": pipeline_risk.severity.value,
                    "action_type": recommended_action.action_type.value,
                    "timeout_minutes": timeout_minutes,
                    "priority": priority,
                    "affected_deals": len(pipeline_risk.affected_deals),
                    "affected_leads": len(pipeline_risk.affected_leads)
                },
                system_generated=True
            )
            
            # Send notification to approver
            self._send_approval_notification(approval_request)
            
            logger.info(
                "Approval request created: %s for approver %s with %d minute timeout",
                request_id, approver_id, timeout_minutes
            )
            
            return approval_request
            
        except Exception as e:
            logger.error("Failed to create approval request: %s", str(e))
            raise ApprovalWorkflowError(f"Failed to create approval request: {str(e)}") from e
    
    def _calculate_timeout(
        self,
        pipeline_risk: PipelineRisk,
        revenue_context: RevenueContext,
        custom_timeout: Optional[int]
    ) -> int:
        """
        Calculate appropriate timeout based on deal urgency and risk severity.
        
        Implements Requirement 5.3: WHEN awaiting approval, THE Human_Loop SHALL 
        set appropriate timeouts for decision responses based on deal urgency.
        """
        if custom_timeout:
            return custom_timeout
        
        # Base timeout on risk severity
        if pipeline_risk.severity == Severity.CRITICAL:
            base_timeout = self.config['critical_timeout_minutes']
        elif pipeline_risk.severity == Severity.HIGH:
            base_timeout = self.config['high_timeout_minutes']
        elif pipeline_risk.severity == Severity.MEDIUM:
            base_timeout = self.config['medium_timeout_minutes']
        else:
            base_timeout = self.config['low_timeout_minutes']
        
        # Adjust based on deal characteristics
        if revenue_context.deal_history:
            max_deal_value = max(deal.value for deal in revenue_context.deal_history)
            
            # High-value deals get shorter timeouts for urgency
            if max_deal_value >= 100000:  # $100k+
                base_timeout = min(base_timeout, self.config['critical_timeout_minutes'])
            elif max_deal_value >= 50000:  # $50k+
                base_timeout = min(base_timeout, self.config['high_timeout_minutes'])
        
        return base_timeout
    
    def _calculate_priority(
        self,
        pipeline_risk: PipelineRisk,
        revenue_context: RevenueContext
    ) -> int:
        """Calculate request priority based on risk and deal characteristics."""
        # Start with severity-based priority
        if pipeline_risk.severity == Severity.CRITICAL:
            priority = 1
        elif pipeline_risk.severity == Severity.HIGH:
            priority = 2
        elif pipeline_risk.severity == Severity.MEDIUM:
            priority = 3
        else:
            priority = 4
        
        # Adjust based on deal values
        if revenue_context.deal_history:
            max_deal_value = max(deal.value for deal in revenue_context.deal_history)
            if max_deal_value >= 100000 and priority > 1:
                priority = 1  # High-value deals get highest priority
            elif max_deal_value >= 50000 and priority > 2:
                priority = 2
        
        return priority
    
    def _generate_escalation_rules(
        self,
        pipeline_risk: PipelineRisk,
        revenue_context: RevenueContext,
        approver_id: str
    ) -> List[EscalationRule]:
        """Generate escalation rules based on risk and deal characteristics."""
        rules = []
        
        # First escalation - to senior manager after timeout
        rules.append(EscalationRule(
            rule_id=str(uuid4()),
            trigger_after_minutes=self.config['default_escalation_minutes'],
            escalate_to="senior_sales_manager",  # Would be configurable
            escalation_type="role",
            active=True
        ))
        
        # Second escalation for critical/high-value deals
        if (pipeline_risk.severity in [Severity.CRITICAL, Severity.HIGH] or
            (revenue_context.deal_history and 
             max(deal.value for deal in revenue_context.deal_history) >= 100000)):
            
            rules.append(EscalationRule(
                rule_id=str(uuid4()),
                trigger_after_minutes=self.config['default_escalation_minutes'] * 2,
                escalate_to="vp_sales",  # Would be configurable
                escalation_type="role",
                fallback_action="safe_default",
                active=True
            ))
        
        return rules
    
    def check_approval_status(self, request_id: str) -> Tuple[ApprovalStatus, Optional[ApprovalResponse]]:
        """
        Check the current status of an approval request.
        
        Args:
            request_id: The approval request ID
            
        Returns:
            Tuple of (status, response) where response is None if still pending
            
        Raises:
            ApprovalWorkflowError: If request not found
        """
        if request_id not in self.active_requests:
            raise ApprovalWorkflowError(f"Approval request {request_id} not found")
        
        request = self.active_requests[request_id]
        
        # Check for timeout
        if datetime.utcnow() > request.expires_at and request.status == ApprovalStatus.PENDING:
            self._handle_timeout(request_id)
        
        # Return current status
        return request.status, None  # Response would be retrieved from storage
    
    def _handle_timeout(self, request_id: str) -> None:
        """
        Handle approval request timeout with escalation or fallback.
        
        Implements Requirement 5.7: WHEN approval timeouts occur, THE Human_Loop 
        SHALL escalate to senior sales management or default to safe fallback actions.
        """
        try:
            request = self.active_requests[request_id]
            
            # Log timeout event
            self._log_audit_event(
                request_id=request_id,
                event_type="timeout",
                event_details={
                    "original_approver": request.approver_id,
                    "timeout_minutes": request.timeout_minutes,
                    "expires_at": request.expires_at.isoformat()
                },
                system_generated=True
            )
            
            # Try escalation first
            escalated = self._try_escalation(request)
            
            if not escalated:
                # Apply fallback action if escalation fails
                self._apply_fallback_action(request)
            
            logger.warning(
                "Approval request %s timed out. Escalated: %s",
                request_id, escalated
            )
            
        except Exception as e:
            logger.error("Failed to handle timeout for request %s: %s", request_id, str(e))
            # Apply safe fallback as last resort
            self._apply_safe_fallback(request_id)
    
    def _try_escalation(self, request: ApprovalRequest) -> bool:
        """Try to escalate the approval request based on escalation rules."""
        for rule in request.escalation_rules:
            if not rule.active:
                continue
            
            # Check if enough time has passed for this escalation
            time_since_creation = datetime.utcnow() - request.created_at
            if time_since_creation.total_seconds() / 60 >= rule.trigger_after_minutes:
                
                # Create escalation event
                escalation_event = EscalationEvent(
                    event_id=str(uuid4()),
                    request_id=request.request_id,
                    escalation_rule=rule,
                    original_approver=request.approver_id,
                    escalated_to=rule.escalate_to,
                    escalation_reason="timeout"
                )
                
                self.escalation_events.append(escalation_event)
                
                # Update request
                request.status = ApprovalStatus.ESCALATED
                request.escalated_at = datetime.utcnow()
                request.escalated_to = rule.escalate_to
                
                # Log escalation
                self._log_audit_event(
                    request_id=request.request_id,
                    event_type="escalated",
                    event_details={
                        "escalated_to": rule.escalate_to,
                        "escalation_type": rule.escalation_type,
                        "rule_id": rule.rule_id
                    },
                    system_generated=True
                )
                
                # Send notification to new approver
                # In a real implementation, this would send actual notifications
                logger.info(
                    "Escalated approval request %s to %s",
                    request.request_id, rule.escalate_to
                )
                
                return True
        
        return False
    
    def _apply_fallback_action(self, request: ApprovalRequest) -> None:
        """Apply fallback action when escalation is not possible."""
        # Check if fallback actions are enabled
        if not self.config.get('enable_fallback_actions', True):
            return
        
        # Apply safe default based on risk severity and action type
        fallback_applied = False
        fallback_details = ""
        
        if request.pipeline_risk.severity in [Severity.LOW, Severity.MEDIUM]:
            # For low/medium risks, we can auto-approve certain safe actions
            safe_actions = ['CREATE_TASK', 'SCHEDULE_FOLLOWUP', 'SEND_ALERT']
            if request.recommended_action.action_type.value in safe_actions:
                request.status = ApprovalStatus.APPROVED
                fallback_applied = True
                fallback_details = f"Auto-approved safe action: {request.recommended_action.action_type.value}"
        
        if not fallback_applied:
            # Default to denial for safety
            request.status = ApprovalStatus.DENIED
            fallback_details = "Auto-denied due to timeout and failed escalation"
        
        # Log fallback action
        self._log_audit_event(
            request_id=request.request_id,
            event_type="fallback_applied",
            event_details={
                "fallback_action": fallback_details,
                "auto_approved": fallback_applied
            },
            system_generated=True
        )
        
        logger.info(
            "Applied fallback action for request %s: %s",
            request.request_id, fallback_details
        )
    
    def _apply_safe_fallback(self, request_id: str) -> None:
        """Apply the safest possible fallback action."""
        if request_id in self.active_requests:
            request = self.active_requests[request_id]
            request.status = ApprovalStatus.DENIED
            
            self._log_audit_event(
                request_id=request_id,
                event_type="safe_fallback",
                event_details={"reason": "emergency_fallback_due_to_error"},
                system_generated=True
            )
    
    def record_decision(
        self,
        request_id: str,
        approver_id: str,
        decision: ApprovalStatus,
        reasoning: Optional[str] = None,
        modified_action: Optional[SalesAction] = None
    ) -> ApprovalResponse:
        """
        Record a human decision on an approval request.
        
        Args:
            request_id: The approval request ID
            approver_id: ID of the approver making the decision
            decision: The approval decision (APPROVED or DENIED)
            reasoning: Optional reasoning for the decision
            modified_action: Optional modified action if approved with changes
            
        Returns:
            ApprovalResponse: The recorded response
            
        Raises:
            ApprovalWorkflowError: If request not found or invalid decision
        """
        if request_id not in self.active_requests:
            raise ApprovalWorkflowError(f"Approval request {request_id} not found")
        
        request = self.active_requests[request_id]
        
        if request.status != ApprovalStatus.PENDING:
            raise ApprovalWorkflowError(
                f"Cannot record decision for request {request_id} with status {request.status}"
            )
        
        # Create response
        response = ApprovalResponse(
            response_id=str(uuid4()),
            request_id=request_id,
            approver_id=approver_id,
            decision=decision,
            reasoning=reasoning,
            modified_action=modified_action
        )
        
        # Update request status
        request.status = decision
        request.responded_at = datetime.utcnow()
        
        # Log the decision
        self._log_audit_event(
            request_id=request_id,
            event_type="responded",
            event_details={
                "approver_id": approver_id,
                "decision": decision.value,
                "reasoning": reasoning,
                "has_modified_action": modified_action is not None
            },
            user_id=approver_id,
            system_generated=False
        )
        
        logger.info(
            "Decision recorded for request %s: %s by %s",
            request_id, decision.value, approver_id
        )
        
        return response
    
    def _send_approval_notification(self, request: ApprovalRequest) -> None:
        """Send notification to approver about pending request."""
        # In a real implementation, this would send actual notifications
        # via email, SMS, Slack, etc. based on user preferences
        
        logger.info(
            "Sending approval notification to %s for request %s (Priority: %d, Timeout: %d min)",
            request.approver_id, request.request_id, request.priority, request.timeout_minutes
        )
        
        # Log notification attempt
        self._log_audit_event(
            request_id=request.request_id,
            event_type="notification_sent",
            event_details={
                "approver_id": request.approver_id,
                "notification_type": "approval_request",
                "priority": request.priority
            },
            system_generated=True
        )
    
    def _log_audit_event(
        self,
        request_id: str,
        event_type: str,
        event_details: Dict,
        user_id: Optional[str] = None,
        system_generated: bool = True
    ) -> None:
        """Log an audit event for the approval workflow."""
        audit_log = ApprovalAuditLog(
            log_id=str(uuid4()),
            request_id=request_id,
            event_type=event_type,
            event_details=event_details,
            user_id=user_id,
            system_generated=system_generated
        )
        
        self.audit_logs.append(audit_log)
        
        logger.debug(
            "Audit event logged: %s for request %s",
            event_type, request_id
        )
    
    def get_audit_trail(self, request_id: str) -> List[ApprovalAuditLog]:
        """
        Get the complete audit trail for an approval request.
        
        Args:
            request_id: The approval request ID
            
        Returns:
            List of audit log entries for the request
        """
        return [
            log for log in self.audit_logs 
            if log.request_id == request_id
        ]
    
    def get_active_requests(
        self,
        approver_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None
    ) -> List[ApprovalRequest]:
        """
        Get active approval requests, optionally filtered by approver or status.
        
        Args:
            approver_id: Optional approver ID to filter by
            status: Optional status to filter by
            
        Returns:
            List of matching approval requests
        """
        requests = list(self.active_requests.values())
        
        if approver_id:
            requests = [r for r in requests if r.approver_id == approver_id]
        
        if status:
            requests = [r for r in requests if r.status == status]
        
        return requests
    
    def cleanup_expired_requests(self, retention_days: Optional[int] = None) -> int:
        """
        Clean up expired and completed requests based on retention policy.
        
        Args:
            retention_days: Number of days to retain completed requests
            
        Returns:
            Number of requests cleaned up
        """
        retention_days = retention_days or self.config.get('audit_retention_days', 90)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Find requests to clean up
        to_remove = []
        for request_id, request in self.active_requests.items():
            if (request.status in [ApprovalStatus.APPROVED, ApprovalStatus.DENIED] and
                request.responded_at and request.responded_at < cutoff_date):
                to_remove.append(request_id)
        
        # Remove expired requests
        for request_id in to_remove:
            del self.active_requests[request_id]
        
        # Clean up old audit logs
        self.audit_logs = [
            log for log in self.audit_logs
            if log.timestamp >= cutoff_date
        ]
        
        logger.info("Cleaned up %d expired approval requests", len(to_remove))
        return len(to_remove)