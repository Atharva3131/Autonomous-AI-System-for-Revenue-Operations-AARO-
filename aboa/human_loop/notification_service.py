"""
Notification service for approval workflow routing and notifications.

This module handles the routing and delivery of approval notifications
through multiple channels (email, SMS, Slack) based on user preferences
and escalation rules.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import ABOAException
from .models import ApprovalRequest, NotificationConfig

logger = logging.getLogger(__name__)


class NotificationError(ABOAException):
    """Exception raised for notification errors."""
    pass


class NotificationService:
    """
    Service for handling approval notification routing and delivery.
    
    Manages notification preferences, delivery channels, and retry logic
    for approval workflow notifications.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the notification service.
        
        Args:
            config: Configuration dictionary for notifications
        """
        self.config = config or self._get_default_config()
        self.notification_configs: Dict[str, NotificationConfig] = {}
        self.delivery_log: List[Dict] = []
        
        logger.info("NotificationService initialized")
    
    def _get_default_config(self) -> Dict:
        """Get default notification configuration."""
        return {
            'max_retry_attempts': 3,
            'retry_delay_minutes': 5,
            'email_enabled': True,
            'sms_enabled': False,
            'slack_enabled': False,
            'batch_notifications': False,
            'quiet_hours_enabled': True,
            'emergency_override': True
        }
    
    def register_user_config(self, user_config: NotificationConfig) -> None:
        """
        Register notification configuration for a user.
        
        Args:
            user_config: User's notification preferences
        """
        self.notification_configs[user_config.user_id] = user_config
        logger.info("Registered notification config for user: %s", user_config.user_id)
    
    def send_approval_notification(
        self,
        request: ApprovalRequest,
        notification_type: str = "approval_request"
    ) -> bool:
        """
        Send approval notification to the assigned approver.
        
        Args:
            request: The approval request
            notification_type: Type of notification (approval_request, escalation, reminder)
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            user_config = self.notification_configs.get(request.approver_id)
            
            if not user_config:
                # Use default notification method
                return self._send_default_notification(request, notification_type)
            
            # Check quiet hours
            if self._is_quiet_hours(user_config) and not self._is_emergency(request):
                logger.info(
                    "Delaying notification for user %s due to quiet hours",
                    request.approver_id
                )
                return self._schedule_notification(request, notification_type, user_config)
            
            # Send through preferred channels
            success = False
            
            if user_config.email_enabled and user_config.email_address:
                success |= self._send_email_notification(request, user_config, notification_type)
            
            if user_config.sms_enabled and user_config.phone_number:
                success |= self._send_sms_notification(request, user_config, notification_type)
            
            if user_config.slack_enabled and user_config.slack_user_id:
                success |= self._send_slack_notification(request, user_config, notification_type)
            
            # Log delivery attempt
            self._log_delivery_attempt(request, notification_type, success, user_config)
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to send notification for request %s: %s",
                request.request_id, str(e)
            )
            return False
    
    def _send_default_notification(
        self,
        request: ApprovalRequest,
        notification_type: str
    ) -> bool:
        """Send notification using default method when no user config exists."""
        # In a real implementation, this would use a default notification channel
        logger.info(
            "Sending default notification to %s for request %s (%s)",
            request.approver_id, request.request_id, notification_type
        )
        
        # Simulate successful delivery
        self._log_delivery_attempt(request, notification_type, True, None)
        return True
    
    def _send_email_notification(
        self,
        request: ApprovalRequest,
        user_config: NotificationConfig,
        notification_type: str
    ) -> bool:
        """Send email notification."""
        try:
            # In a real implementation, this would integrate with an email service
            email_content = self._generate_email_content(request, notification_type)
            
            logger.info(
                "Sending email notification to %s for request %s",
                user_config.email_address, request.request_id
            )
            
            # Simulate email sending
            # In production: email_service.send(to=user_config.email_address, content=email_content)
            
            return True
            
        except Exception as e:
            logger.error("Failed to send email notification: %s", str(e))
            return False
    
    def _send_sms_notification(
        self,
        request: ApprovalRequest,
        user_config: NotificationConfig,
        notification_type: str
    ) -> bool:
        """Send SMS notification."""
        try:
            # In a real implementation, this would integrate with an SMS service
            sms_content = self._generate_sms_content(request, notification_type)
            
            logger.info(
                "Sending SMS notification to %s for request %s",
                user_config.phone_number, request.request_id
            )
            
            # Simulate SMS sending
            # In production: sms_service.send(to=user_config.phone_number, message=sms_content)
            
            return True
            
        except Exception as e:
            logger.error("Failed to send SMS notification: %s", str(e))
            return False
    
    def _send_slack_notification(
        self,
        request: ApprovalRequest,
        user_config: NotificationConfig,
        notification_type: str
    ) -> bool:
        """Send Slack notification."""
        try:
            # In a real implementation, this would integrate with Slack API
            slack_content = self._generate_slack_content(request, notification_type)
            
            logger.info(
                "Sending Slack notification to %s for request %s",
                user_config.slack_user_id, request.request_id
            )
            
            # Simulate Slack sending
            # In production: slack_client.send_dm(user=user_config.slack_user_id, content=slack_content)
            
            return True
            
        except Exception as e:
            logger.error("Failed to send Slack notification: %s", str(e))
            return False
    
    def _generate_email_content(self, request: ApprovalRequest, notification_type: str) -> Dict:
        """Generate email content for approval notification."""
        risk = request.pipeline_risk
        action = request.recommended_action
        
        subject = f"[AARO] {notification_type.replace('_', ' ').title()}: {risk.risk_type.value.replace('_', ' ').title()}"
        
        body = f"""
        Revenue Operations Approval Required
        
        Request ID: {request.request_id}
        Priority: {request.priority} (1=highest)
        Timeout: {request.timeout_minutes} minutes
        
        Pipeline Risk Details:
        - Type: {risk.risk_type.value.replace('_', ' ').title()}
        - Severity: {risk.severity.value.title()}
        - Confidence: {risk.confidence:.1f}%
        - Description: {risk.description}
        - Affected Deals: {len(risk.affected_deals)}
        - Affected Leads: {len(risk.affected_leads)}
        
        Recommended Action:
        - Type: {action.action_type.value.replace('_', ' ').title()}
        - Target System: {action.target_system}
        - Expected Outcome: {action.expected_outcome}
        - Revenue Impact: ${action.revenue_impact or 0:,.2f}
        
        Revenue Context:
        - Deal History: {len(request.revenue_context.deal_history)} deals
        - Confidence Score: {request.revenue_context.confidence_score:.1f}%
        
        Please review and approve/deny this request within {request.timeout_minutes} minutes.
        
        Created: {request.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
        Expires: {request.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        
        return {
            'subject': subject,
            'body': body,
            'html_body': body.replace('\n', '<br>'),
            'priority': 'high' if request.priority <= 2 else 'normal'
        }
    
    def _generate_sms_content(self, request: ApprovalRequest, notification_type: str) -> str:
        """Generate SMS content for approval notification."""
        risk = request.pipeline_risk
        action = request.recommended_action
        
        return (
            f"AARO Approval: {risk.risk_type.value.replace('_', ' ').title()} "
            f"({risk.severity.value}) - {action.action_type.value.replace('_', ' ').title()}. "
            f"Timeout: {request.timeout_minutes}min. ID: {request.request_id[:8]}"
        )
    
    def _generate_slack_content(self, request: ApprovalRequest, notification_type: str) -> Dict:
        """Generate Slack content for approval notification."""
        risk = request.pipeline_risk
        action = request.recommended_action
        
        return {
            'text': f"Revenue Operations Approval Required",
            'blocks': [
                {
                    'type': 'header',
                    'text': {
                        'type': 'plain_text',
                        'text': f"🚨 {notification_type.replace('_', ' ').title()}"
                    }
                },
                {
                    'type': 'section',
                    'fields': [
                        {
                            'type': 'mrkdwn',
                            'text': f"*Request ID:*\n{request.request_id[:8]}..."
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f"*Priority:*\n{request.priority} (1=highest)"
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f"*Risk Type:*\n{risk.risk_type.value.replace('_', ' ').title()}"
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f"*Severity:*\n{risk.severity.value.title()}"
                        }
                    ]
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f"*Recommended Action:* {action.action_type.value.replace('_', ' ').title()}\n*Expected Outcome:* {action.expected_outcome}"
                    }
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f"⏰ *Timeout:* {request.timeout_minutes} minutes\n📅 *Expires:* {request.expires_at.strftime('%Y-%m-%d %H:%M UTC')}"
                    }
                }
            ]
        }
    
    def _is_quiet_hours(self, user_config: NotificationConfig) -> bool:
        """Check if current time is within user's quiet hours."""
        if not user_config.quiet_hours_start or not user_config.quiet_hours_end:
            return False
        
        # In a real implementation, this would consider the user's timezone
        current_hour = datetime.utcnow().hour
        
        start = user_config.quiet_hours_start
        end = user_config.quiet_hours_end
        
        if start <= end:
            return start <= current_hour < end
        else:
            # Quiet hours span midnight
            return current_hour >= start or current_hour < end
    
    def _is_emergency(self, request: ApprovalRequest) -> bool:
        """Check if request qualifies as emergency (overrides quiet hours)."""
        return (
            request.priority == 1 or
            request.pipeline_risk.severity.value == 'critical' or
            request.timeout_minutes <= 30
        )
    
    def _schedule_notification(
        self,
        request: ApprovalRequest,
        notification_type: str,
        user_config: NotificationConfig
    ) -> bool:
        """Schedule notification for after quiet hours."""
        # In a real implementation, this would schedule the notification
        # for delivery after quiet hours end
        
        logger.info(
            "Scheduled notification for user %s after quiet hours end",
            request.approver_id
        )
        
        return True
    
    def _log_delivery_attempt(
        self,
        request: ApprovalRequest,
        notification_type: str,
        success: bool,
        user_config: Optional[NotificationConfig]
    ) -> None:
        """Log notification delivery attempt."""
        log_entry = {
            'log_id': str(uuid4()),
            'request_id': request.request_id,
            'approver_id': request.approver_id,
            'notification_type': notification_type,
            'success': success,
            'timestamp': datetime.utcnow(),
            'channels_used': [],
            'user_config_exists': user_config is not None
        }
        
        if user_config:
            if user_config.email_enabled:
                log_entry['channels_used'].append('email')
            if user_config.sms_enabled:
                log_entry['channels_used'].append('sms')
            if user_config.slack_enabled:
                log_entry['channels_used'].append('slack')
        else:
            log_entry['channels_used'].append('default')
        
        self.delivery_log.append(log_entry)
        
        logger.debug(
            "Logged notification delivery: %s for request %s (success: %s)",
            notification_type, request.request_id, success
        )
    
    def send_escalation_notification(
        self,
        request: ApprovalRequest,
        escalated_to: str,
        escalation_reason: str
    ) -> bool:
        """
        Send escalation notification to new approver.
        
        Args:
            request: The approval request being escalated
            escalated_to: ID of the new approver
            escalation_reason: Reason for escalation
            
        Returns:
            True if notification sent successfully
        """
        # Update approver for notification
        original_approver = request.approver_id
        request.approver_id = escalated_to
        
        try:
            success = self.send_approval_notification(request, "escalation")
            
            logger.info(
                "Sent escalation notification from %s to %s for request %s",
                original_approver, escalated_to, request.request_id
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to send escalation notification: %s", str(e)
            )
            return False
        finally:
            # Restore original approver
            request.approver_id = original_approver
    
    def send_reminder_notification(self, request: ApprovalRequest) -> bool:
        """
        Send reminder notification for pending approval.
        
        Args:
            request: The approval request
            
        Returns:
            True if reminder sent successfully
        """
        return self.send_approval_notification(request, "reminder")
    
    def get_delivery_stats(self, user_id: Optional[str] = None) -> Dict:
        """
        Get notification delivery statistics.
        
        Args:
            user_id: Optional user ID to filter stats
            
        Returns:
            Dictionary with delivery statistics
        """
        logs = self.delivery_log
        if user_id:
            logs = [log for log in logs if log['approver_id'] == user_id]
        
        if not logs:
            return {'total': 0, 'success_rate': 0.0}
        
        total = len(logs)
        successful = sum(1 for log in logs if log['success'])
        
        return {
            'total': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': (successful / total) * 100 if total > 0 else 0.0,
            'channels_used': list(set(
                channel for log in logs 
                for channel in log['channels_used']
            ))
        }