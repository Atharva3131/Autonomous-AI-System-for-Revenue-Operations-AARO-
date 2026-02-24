"""
Integration example demonstrating the observability system.

This module shows how to integrate the sales activity logging and metrics
collection with other ABOA components for comprehensive observability.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from ..models.enums import DecisionClass, ExecutionStatus, SalesActionType
from ..models.revenue_entities import Deal, Lead, SalesAction, PipelineRisk
from .activity_logger import get_activity_logger, log_sales_activity, log_revenue_decision, log_sales_action
from .metrics_collector import get_metrics_collector


class ObservabilityIntegrationExample:
    """
    Example class showing how to integrate observability throughout the AARO system.
    
    This demonstrates logging patterns for different types of sales operations
    and how to collect comprehensive metrics.
    """
    
    def __init__(self):
        """Initialize the integration example."""
        self.activity_logger = get_activity_logger()
        self.metrics_collector = get_metrics_collector()
    
    def simulate_lead_processing_workflow(self) -> Dict[str, Any]:
        """
        Simulate a complete lead processing workflow with comprehensive logging.
        
        Returns:
            Dictionary containing workflow results and metrics
        """
        # Step 1: Lead creation
        lead_id = "lead_example_001"
        log_sales_activity(
            activity_type="lead_created",
            component="data_ingestion",
            entity_type="lead",
            entity_id=lead_id,
            user_id="system",
            details={
                "source": "website_form",
                "campaign": "q1_2024_campaign",
                "lead_score": 85
            },
            revenue_impact=5000.0
        )
        
        # Step 2: Lead qualification decision
        decision_id = "decision_example_001"
        log_revenue_decision(
            decision_id=decision_id,
            decision_type=DecisionClass.AUTO_EXECUTABLE,
            confidence=87.5,
            reasoning="High lead score and matching ICP criteria",
            context={
                "lead_score": 85,
                "company_size": "mid_market",
                "budget_qualified": True
            },
            revenue_impact=5000.0
        )
        
        # Step 3: Automated follow-up action
        action_id = "action_example_001"
        log_sales_action(
            action_id=action_id,
            action_type=SalesActionType.SCHEDULE_FOLLOWUP,
            execution_status=ExecutionStatus.COMPLETED,
            target_system="crm",
            parameters={
                "follow_up_type": "qualification_call",
                "scheduled_time": "2024-02-01T10:00:00Z",
                "assigned_rep": "rep_001"
            },
            duration_ms=1200,
            revenue_impact=5000.0
        )
        
        # Step 4: Lead conversion to deal
        deal_id = "deal_example_001"
        log_sales_activity(
            activity_type="lead_converted",
            component="decision_engine",
            entity_type="lead",
            entity_id=lead_id,
            details={
                "converted_to_deal": deal_id,
                "conversion_reason": "qualified_opportunity"
            },
            revenue_impact=5000.0
        )
        
        # Step 5: Deal creation
        log_sales_activity(
            activity_type="deal_created",
            component="data_ingestion",
            entity_type="deal",
            entity_id=deal_id,
            details={
                "initial_value": 5000.0,
                "stage": "qualification",
                "source_lead": lead_id
            },
            revenue_impact=5000.0
        )
        
        return {
            "workflow_completed": True,
            "lead_id": lead_id,
            "deal_id": deal_id,
            "decision_id": decision_id,
            "action_id": action_id,
            "total_revenue_impact": 5000.0
        }
    
    def simulate_pipeline_risk_detection_workflow(self) -> Dict[str, Any]:
        """
        Simulate pipeline risk detection and remediation workflow.
        
        Returns:
            Dictionary containing risk detection results
        """
        # Step 1: Risk detection
        risk_id = "risk_example_001"
        deal_id = "deal_stalled_001"
        
        log_sales_activity(
            activity_type="pipeline_risk_detected",
            component="pipeline_risk_detector",
            entity_type="deal",
            entity_id=deal_id,
            details={
                "risk_type": "stalled_deal",
                "days_in_stage": 45,
                "last_activity_days_ago": 14,
                "risk_severity": "high"
            },
            severity="warning",
            revenue_impact=25000.0
        )
        
        # Step 2: Risk assessment decision
        decision_id = "decision_risk_001"
        log_revenue_decision(
            decision_id=decision_id,
            decision_type=DecisionClass.APPROVAL_REQUIRED,
            pipeline_risk_id=risk_id,
            confidence=92.0,
            reasoning="High-value deal stalled for 45 days with no recent activity",
            context={
                "deal_value": 25000.0,
                "days_stalled": 45,
                "rep_performance": "below_average",
                "customer_engagement": "low"
            },
            revenue_impact=25000.0
        )
        
        # Step 3: Human approval
        log_revenue_decision(
            decision_id=decision_id,
            decision_type=DecisionClass.APPROVAL_REQUIRED,
            human_decision="approved",
            execution_status=ExecutionStatus.IN_PROGRESS,
            confidence=92.0,
            outcome="approved_for_intervention"
        )
        
        # Step 4: Remediation actions
        action_ids = []
        
        # Action 1: Create urgent follow-up task
        action_id_1 = "action_urgent_followup_001"
        log_sales_action(
            action_id=action_id_1,
            action_type=SalesActionType.CREATE_TASK,
            execution_status=ExecutionStatus.COMPLETED,
            target_system="crm",
            parameters={
                "task_type": "urgent_follow_up",
                "priority": "high",
                "due_date": "2024-01-30T17:00:00Z",
                "assigned_rep": "rep_001"
            },
            duration_ms=800,
            revenue_impact=25000.0
        )
        action_ids.append(action_id_1)
        
        # Action 2: Alert sales manager
        action_id_2 = "action_manager_alert_001"
        log_sales_action(
            action_id=action_id_2,
            action_type=SalesActionType.SEND_ALERT,
            execution_status=ExecutionStatus.COMPLETED,
            target_system="notification_service",
            parameters={
                "alert_type": "stalled_high_value_deal",
                "manager_id": "manager_001",
                "deal_id": deal_id,
                "urgency": "high"
            },
            duration_ms=500,
            revenue_impact=25000.0
        )
        action_ids.append(action_id_2)
        
        return {
            "risk_detected": True,
            "risk_id": risk_id,
            "decision_id": decision_id,
            "action_ids": action_ids,
            "total_revenue_at_risk": 25000.0
        }
    
    def generate_comprehensive_metrics_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive metrics report for the simulated activities.
        
        Returns:
            Dictionary containing comprehensive metrics and analysis
        """
        # Create a metrics snapshot
        snapshot = self.metrics_collector.create_comprehensive_snapshot(period_days=1)
        
        # Get system health metrics
        health_metrics = self.activity_logger.get_system_health_metrics()
        
        # Get recent activity summary
        recent_activities = self.activity_logger.search_activity_logs(limit=10)
        recent_decisions = self.activity_logger.search_decision_logs(limit=10)
        recent_actions = self.activity_logger.search_action_logs(limit=10)
        
        return {
            "metrics_snapshot": snapshot,
            "system_health": health_metrics,
            "recent_activity_count": len(recent_activities),
            "recent_decision_count": len(recent_decisions),
            "recent_action_count": len(recent_actions),
            "summary": {
                "total_revenue_impact": sum([
                    a.revenue_impact for a in recent_activities 
                    if a.revenue_impact is not None
                ]),
                "automation_actions": len([
                    a for a in recent_actions 
                    if a.execution_status == ExecutionStatus.COMPLETED
                ]),
                "high_confidence_decisions": len([
                    d for d in recent_decisions 
                    if d.confidence > 80.0
                ])
            }
        }
    
    def demonstrate_audit_trail(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """
        Demonstrate audit trail functionality for a specific entity.
        
        Args:
            entity_type: Type of entity to audit
            entity_id: ID of the entity to audit
            
        Returns:
            Dictionary containing complete audit trail
        """
        audit_trail = self.activity_logger.get_audit_trail(entity_type, entity_id)
        
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "total_audit_entries": len(audit_trail),
            "audit_trail": audit_trail,
            "timeline": [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "activity": entry.activity_type,
                    "component": entry.component,
                    "details": entry.details
                }
                for entry in audit_trail
            ]
        }
    
    def run_complete_demonstration(self) -> Dict[str, Any]:
        """
        Run a complete demonstration of the observability system.
        
        Returns:
            Dictionary containing all demonstration results
        """
        print("🚀 Starting AARO Observability System Demonstration...")
        
        # Run lead processing workflow
        print("📋 Simulating lead processing workflow...")
        lead_workflow = self.simulate_lead_processing_workflow()
        
        # Run pipeline risk detection workflow
        print("⚠️  Simulating pipeline risk detection workflow...")
        risk_workflow = self.simulate_pipeline_risk_detection_workflow()
        
        # Generate metrics report
        print("📊 Generating comprehensive metrics report...")
        metrics_report = self.generate_comprehensive_metrics_report()
        
        # Demonstrate audit trail
        print("🔍 Demonstrating audit trail functionality...")
        audit_demo = self.demonstrate_audit_trail("lead", lead_workflow["lead_id"])
        
        print("✅ Observability demonstration completed!")
        
        return {
            "lead_workflow": lead_workflow,
            "risk_workflow": risk_workflow,
            "metrics_report": metrics_report,
            "audit_demonstration": audit_demo,
            "demonstration_summary": {
                "total_activities_logged": len(self.activity_logger.activity_logs),
                "total_decisions_logged": len(self.activity_logger.decision_logs),
                "total_actions_logged": len(self.activity_logger.action_logs),
                "total_revenue_tracked": (
                    lead_workflow["total_revenue_impact"] + 
                    risk_workflow["total_revenue_at_risk"]
                )
            }
        }


def run_observability_demo():
    """Run the complete observability system demonstration."""
    demo = ObservabilityIntegrationExample()
    results = demo.run_complete_demonstration()
    
    print("\n" + "="*60)
    print("OBSERVABILITY DEMONSTRATION RESULTS")
    print("="*60)
    print(f"Activities Logged: {results['demonstration_summary']['total_activities_logged']}")
    print(f"Decisions Logged: {results['demonstration_summary']['total_decisions_logged']}")
    print(f"Actions Logged: {results['demonstration_summary']['total_actions_logged']}")
    print(f"Total Revenue Tracked: ${results['demonstration_summary']['total_revenue_tracked']:,.2f}")
    print("="*60)
    
    return results


if __name__ == "__main__":
    run_observability_demo()