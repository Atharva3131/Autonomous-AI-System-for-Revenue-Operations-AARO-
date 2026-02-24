"""
Sales Integration Hub for CRM and workflow systems.

This module implements the integration layer that connects the AARO system
with external CRM systems, workflow automation platforms, and notification
systems to execute sales actions.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import IntegrationError, RetryableError
from ..core.logging import get_logger
from ..models.enums import SalesActionType, ActivityType, DealStage, LeadStatus
from ..models.revenue_entities import Deal, Lead, SalesActivity, SalesRep, RevenueContext

logger = get_logger(__name__)


class WorkflowIntegration:
    """
    Integration with workflow automation systems for task creation and scheduling.
    
    Handles follow-up task creation, activity scheduling, and workflow automation
    for sales processes.
    """
    
    def __init__(self, workflow_api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.workflow_api_url = workflow_api_url or "http://localhost:5678"  # n8n default
        self.api_key = api_key
        self._session = None
    
    async def create_follow_up_task(
        self,
        deal_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        assigned_rep: str = "",
        task_type: str = "follow_up",
        due_date: Optional[datetime] = None,
        priority: str = "medium",
        description: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a follow-up task in the workflow system.
        
        Args:
            deal_id: Associated deal ID
            lead_id: Associated lead ID  
            assigned_rep: Sales rep to assign the task to
            task_type: Type of task (follow_up, demo, proposal, etc.)
            due_date: When the task is due
            priority: Task priority (low, medium, high, urgent)
            description: Task description
            context: Additional context for the task
            
        Returns:
            Dict containing task creation result
        """
        try:
            task_data = {
                "id": str(uuid4()),
                "type": task_type,
                "title": f"Follow-up: {task_type.replace('_', ' ').title()}",
                "description": description,
                "assigned_to": assigned_rep,
                "due_date": due_date.isoformat() if due_date else None,
                "priority": priority,
                "deal_id": deal_id,
                "lead_id": lead_id,
                "context": context or {},
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }
            
            # In a real implementation, this would make an API call to the workflow system
            # For now, we'll simulate the task creation
            logger.info(f"Creating follow-up task: {task_data['title']} for rep {assigned_rep}")
            
            # Simulate API response
            result = {
                "task_id": task_data["id"],
                "workflow_id": str(uuid4()),
                "status": "created",
                "created_at": task_data["created_at"],
                "task_data": task_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create follow-up task: {str(e)}")
            raise IntegrationError(f"Workflow task creation failed: {str(e)}")
    
    async def schedule_activity(
        self,
        activity_type: ActivityType,
        scheduled_for: datetime,
        deal_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        assigned_rep: str = "",
        duration_minutes: int = 30,
        notes: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Schedule a sales activity in the workflow system.
        
        Args:
            activity_type: Type of activity to schedule
            scheduled_for: When to schedule the activity
            deal_id: Associated deal ID
            lead_id: Associated lead ID
            assigned_rep: Sales rep to assign the activity to
            duration_minutes: Expected duration in minutes
            notes: Activity notes
            context: Additional context
            
        Returns:
            Dict containing scheduling result
        """
        try:
            activity_data = {
                "id": str(uuid4()),
                "type": activity_type.value,
                "scheduled_for": scheduled_for.isoformat(),
                "duration_minutes": duration_minutes,
                "assigned_to": assigned_rep,
                "deal_id": deal_id,
                "lead_id": lead_id,
                "notes": notes,
                "context": context or {},
                "created_at": datetime.utcnow().isoformat(),
                "status": "scheduled"
            }
            
            logger.info(f"Scheduling {activity_type.value} activity for {scheduled_for}")
            
            # Simulate API response
            result = {
                "activity_id": activity_data["id"],
                "calendar_event_id": str(uuid4()),
                "status": "scheduled",
                "scheduled_for": activity_data["scheduled_for"],
                "activity_data": activity_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to schedule activity: {str(e)}")
            raise IntegrationError(f"Activity scheduling failed: {str(e)}")
    
    async def create_workflow_automation(
        self,
        trigger_type: str,
        trigger_conditions: Dict[str, Any],
        actions: List[Dict[str, Any]],
        name: str = "",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a workflow automation rule.
        
        Args:
            trigger_type: Type of trigger (time_based, event_based, etc.)
            trigger_conditions: Conditions that trigger the workflow
            actions: List of actions to execute
            name: Workflow name
            description: Workflow description
            
        Returns:
            Dict containing workflow creation result
        """
        try:
            workflow_data = {
                "id": str(uuid4()),
                "name": name or f"Auto-generated workflow {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "description": description,
                "trigger_type": trigger_type,
                "trigger_conditions": trigger_conditions,
                "actions": actions,
                "active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Creating workflow automation: {workflow_data['name']}")
            
            # Simulate API response
            result = {
                "workflow_id": workflow_data["id"],
                "status": "created",
                "active": True,
                "created_at": workflow_data["created_at"],
                "workflow_data": workflow_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create workflow automation: {str(e)}")
            raise IntegrationError(f"Workflow automation creation failed: {str(e)}")


class CRMIntegration:
    """
    Integration with CRM systems for deal updates and flag management.
    
    Handles deal stage updates, opportunity flag management, lead status updates,
    and other CRM operations.
    """
    
    def __init__(self, crm_api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.crm_api_url = crm_api_url or "https://api.crm-system.com"
        self.api_key = api_key
        self._session = None
    
    async def update_deal_stage(
        self,
        deal_id: str,
        new_stage: DealStage,
        reason: str = "",
        notes: str = "",
        updated_by: str = "aaro_system"
    ) -> Dict[str, Any]:
        """
        Update a deal's stage in the CRM system.
        
        Args:
            deal_id: ID of the deal to update
            new_stage: New stage for the deal
            reason: Reason for the stage change
            notes: Additional notes
            updated_by: Who made the update
            
        Returns:
            Dict containing update result
        """
        try:
            update_data = {
                "deal_id": deal_id,
                "old_stage": None,  # Would be fetched from current deal data
                "new_stage": new_stage.value,
                "reason": reason,
                "notes": notes,
                "updated_by": updated_by,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Updating deal {deal_id} stage to {new_stage.value}")
            
            # Simulate API response
            result = {
                "deal_id": deal_id,
                "stage_updated": True,
                "old_stage": "qualification",  # Simulated
                "new_stage": new_stage.value,
                "updated_at": update_data["updated_at"],
                "update_data": update_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update deal stage: {str(e)}")
            raise IntegrationError(f"CRM deal update failed: {str(e)}")
    
    async def update_opportunity_flag(
        self,
        opportunity_id: str,
        flag_type: str,
        flag_value: Any,
        notes: str = "",
        updated_by: str = "aaro_system"
    ) -> Dict[str, Any]:
        """
        Update an opportunity flag in the CRM system.
        
        Args:
            opportunity_id: ID of the opportunity
            flag_type: Type of flag (risk, priority, status, etc.)
            flag_value: Value to set for the flag
            notes: Additional notes
            updated_by: Who made the update
            
        Returns:
            Dict containing update result
        """
        try:
            flag_data = {
                "opportunity_id": opportunity_id,
                "flag_type": flag_type,
                "flag_value": flag_value,
                "notes": notes,
                "updated_by": updated_by,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Updating opportunity {opportunity_id} flag {flag_type} to {flag_value}")
            
            # Simulate API response
            result = {
                "opportunity_id": opportunity_id,
                "flag_updated": True,
                "flag_type": flag_type,
                "old_value": None,  # Would be fetched from current data
                "new_value": flag_value,
                "updated_at": flag_data["updated_at"],
                "flag_data": flag_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update opportunity flag: {str(e)}")
            raise IntegrationError(f"CRM flag update failed: {str(e)}")
    
    async def update_lead_status(
        self,
        lead_id: str,
        new_status: LeadStatus,
        reason: str = "",
        notes: str = "",
        updated_by: str = "aaro_system"
    ) -> Dict[str, Any]:
        """
        Update a lead's status in the CRM system.
        
        Args:
            lead_id: ID of the lead to update
            new_status: New status for the lead
            reason: Reason for the status change
            notes: Additional notes
            updated_by: Who made the update
            
        Returns:
            Dict containing update result
        """
        try:
            update_data = {
                "lead_id": lead_id,
                "old_status": None,  # Would be fetched from current lead data
                "new_status": new_status.value,
                "reason": reason,
                "notes": notes,
                "updated_by": updated_by,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Updating lead {lead_id} status to {new_status.value}")
            
            # Simulate API response
            result = {
                "lead_id": lead_id,
                "status_updated": True,
                "old_status": "new",  # Simulated
                "new_status": new_status.value,
                "updated_at": update_data["updated_at"],
                "update_data": update_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update lead status: {str(e)}")
            raise IntegrationError(f"CRM lead update failed: {str(e)}")
    
    async def create_crm_task(
        self,
        title: str,
        description: str,
        assigned_to: str,
        due_date: Optional[datetime] = None,
        deal_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        task_type: str = "follow_up",
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Create a task in the CRM system.
        
        Args:
            title: Task title
            description: Task description
            assigned_to: Who the task is assigned to
            due_date: When the task is due
            deal_id: Associated deal ID
            lead_id: Associated lead ID
            task_type: Type of task
            priority: Task priority
            
        Returns:
            Dict containing task creation result
        """
        try:
            task_data = {
                "id": str(uuid4()),
                "title": title,
                "description": description,
                "assigned_to": assigned_to,
                "due_date": due_date.isoformat() if due_date else None,
                "deal_id": deal_id,
                "lead_id": lead_id,
                "task_type": task_type,
                "priority": priority,
                "status": "open",
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Creating CRM task: {title} for {assigned_to}")
            
            # Simulate API response
            result = {
                "task_id": task_data["id"],
                "status": "created",
                "created_at": task_data["created_at"],
                "task_data": task_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create CRM task: {str(e)}")
            raise IntegrationError(f"CRM task creation failed: {str(e)}")


class SalesManagerAlertSystem:
    """
    Sales manager alert system for generating context-aware notifications.
    
    Handles alert generation, routing, and delivery for sales managers
    based on pipeline risks and revenue opportunities.
    """
    
    def __init__(self, notification_channels: Optional[List[str]] = None):
        self.notification_channels = notification_channels or ["email", "slack", "dashboard"]
        self._alert_templates = self._load_alert_templates()
    
    def _load_alert_templates(self) -> Dict[str, str]:
        """Load alert message templates."""
        return {
            "stalled_deal": "🚨 Deal Alert: {deal_name} (${deal_value:,.0f}) has been stalled in {stage} for {days} days. Rep: {rep_name}. Recommended action: {action}",
            "missed_followup": "⚠️ Follow-up Alert: {entity_type} {entity_name} requires follow-up. Last contact: {last_contact}. Rep: {rep_name}. Action needed: {action}",
            "high_value_risk": "🔥 High-Value Alert: {deal_name} (${deal_value:,.0f}) is at risk. Risk type: {risk_type}. Rep: {rep_name}. Immediate action required: {action}",
            "sop_deviation": "📋 Process Alert: SOP deviation detected for {entity_type} {entity_name}. Deviation: {deviation}. Rep: {rep_name}. Corrective action: {action}",
            "pipeline_summary": "📊 Pipeline Summary: {total_deals} deals worth ${total_value:,.0f}. {at_risk_count} at risk. {action_count} actions recommended.",
            "rep_performance": "👤 Rep Alert: {rep_name} performance issue detected. Metric: {metric}. Current: {current_value}. Target: {target_value}. Support needed: {action}"
        }
    
    async def send_pipeline_risk_alert(
        self,
        manager_id: str,
        risk_type: str,
        deal: Optional[Deal] = None,
        lead: Optional[Lead] = None,
        rep: Optional[SalesRep] = None,
        recommended_action: str = "",
        urgency: str = "medium",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a pipeline risk alert to a sales manager.
        
        Args:
            manager_id: ID of the sales manager to alert
            risk_type: Type of risk detected
            deal: Associated deal if applicable
            lead: Associated lead if applicable
            rep: Associated sales rep
            recommended_action: Recommended action to take
            urgency: Alert urgency (low, medium, high, critical)
            context: Additional context for the alert
            
        Returns:
            Dict containing alert sending result
        """
        try:
            # Determine alert template and entity info
            entity_type = "Deal" if deal else "Lead" if lead else "Unknown"
            entity_name = ""
            entity_value = 0
            
            if deal:
                entity_name = f"Deal {deal.id}"
                entity_value = float(deal.value)
            elif lead:
                entity_name = f"Lead {lead.id}"
                entity_value = float(lead.estimated_value or 0)
            
            # Select appropriate template
            template_key = "high_value_risk" if entity_value > 50000 else risk_type
            if template_key not in self._alert_templates:
                template_key = "stalled_deal"  # Default template
            
            # Format alert message
            alert_message = self._alert_templates[template_key].format(
                deal_name=entity_name,
                deal_value=entity_value,
                entity_type=entity_type,
                entity_name=entity_name,
                stage=deal.stage.value if deal else "unknown",
                days=deal.days_in_current_stage if deal else 0,
                rep_name=rep.name if rep else "Unknown Rep",
                action=recommended_action,
                risk_type=risk_type,
                last_contact=lead.last_contact.strftime("%Y-%m-%d") if lead and lead.last_contact else "Unknown",
                deviation="Process deviation detected"
            )
            
            alert_data = {
                "alert_id": str(uuid4()),
                "manager_id": manager_id,
                "risk_type": risk_type,
                "urgency": urgency,
                "message": alert_message,
                "entity_type": entity_type,
                "entity_id": deal.id if deal else lead.id if lead else None,
                "rep_id": rep.id if rep else None,
                "recommended_action": recommended_action,
                "context": context or {},
                "created_at": datetime.utcnow().isoformat(),
                "channels": self.notification_channels
            }
            
            logger.info(f"Sending {urgency} priority alert to manager {manager_id}: {risk_type}")
            
            # Simulate sending to multiple channels
            delivery_results = {}
            for channel in self.notification_channels:
                delivery_results[channel] = {
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                    "message_id": str(uuid4())
                }
            
            result = {
                "alert_id": alert_data["alert_id"],
                "status": "sent",
                "channels_sent": len(self.notification_channels),
                "delivery_results": delivery_results,
                "alert_data": alert_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send pipeline risk alert: {str(e)}")
            raise IntegrationError(f"Alert sending failed: {str(e)}")
    
    async def send_performance_alert(
        self,
        manager_id: str,
        rep: SalesRep,
        metric: str,
        current_value: float,
        target_value: float,
        recommended_action: str = "",
        urgency: str = "medium"
    ) -> Dict[str, Any]:
        """
        Send a rep performance alert to a sales manager.
        
        Args:
            manager_id: ID of the sales manager to alert
            rep: Sales rep with performance issue
            metric: Performance metric that triggered the alert
            current_value: Current value of the metric
            target_value: Target value for the metric
            recommended_action: Recommended action to take
            urgency: Alert urgency
            
        Returns:
            Dict containing alert sending result
        """
        try:
            alert_message = self._alert_templates["rep_performance"].format(
                rep_name=rep.name,
                metric=metric,
                current_value=current_value,
                target_value=target_value,
                action=recommended_action
            )
            
            alert_data = {
                "alert_id": str(uuid4()),
                "manager_id": manager_id,
                "alert_type": "rep_performance",
                "urgency": urgency,
                "message": alert_message,
                "rep_id": rep.id,
                "metric": metric,
                "current_value": current_value,
                "target_value": target_value,
                "recommended_action": recommended_action,
                "created_at": datetime.utcnow().isoformat(),
                "channels": self.notification_channels
            }
            
            logger.info(f"Sending performance alert for rep {rep.name}: {metric}")
            
            # Simulate sending to multiple channels
            delivery_results = {}
            for channel in self.notification_channels:
                delivery_results[channel] = {
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                    "message_id": str(uuid4())
                }
            
            result = {
                "alert_id": alert_data["alert_id"],
                "status": "sent",
                "channels_sent": len(self.notification_channels),
                "delivery_results": delivery_results,
                "alert_data": alert_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send performance alert: {str(e)}")
            raise IntegrationError(f"Performance alert sending failed: {str(e)}")
    
    async def send_pipeline_summary(
        self,
        manager_id: str,
        total_deals: int,
        total_value: float,
        at_risk_count: int,
        action_count: int,
        urgency: str = "low"
    ) -> Dict[str, Any]:
        """
        Send a pipeline summary alert to a sales manager.
        
        Args:
            manager_id: ID of the sales manager
            total_deals: Total number of deals
            total_value: Total pipeline value
            at_risk_count: Number of deals at risk
            action_count: Number of recommended actions
            urgency: Alert urgency
            
        Returns:
            Dict containing alert sending result
        """
        try:
            alert_message = self._alert_templates["pipeline_summary"].format(
                total_deals=total_deals,
                total_value=total_value,
                at_risk_count=at_risk_count,
                action_count=action_count
            )
            
            alert_data = {
                "alert_id": str(uuid4()),
                "manager_id": manager_id,
                "alert_type": "pipeline_summary",
                "urgency": urgency,
                "message": alert_message,
                "metrics": {
                    "total_deals": total_deals,
                    "total_value": total_value,
                    "at_risk_count": at_risk_count,
                    "action_count": action_count
                },
                "created_at": datetime.utcnow().isoformat(),
                "channels": self.notification_channels
            }
            
            logger.info(f"Sending pipeline summary to manager {manager_id}")
            
            # Simulate sending to multiple channels
            delivery_results = {}
            for channel in self.notification_channels:
                delivery_results[channel] = {
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat(),
                    "message_id": str(uuid4())
                }
            
            result = {
                "alert_id": alert_data["alert_id"],
                "status": "sent",
                "channels_sent": len(self.notification_channels),
                "delivery_results": delivery_results,
                "alert_data": alert_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send pipeline summary: {str(e)}")
            raise IntegrationError(f"Pipeline summary sending failed: {str(e)}")