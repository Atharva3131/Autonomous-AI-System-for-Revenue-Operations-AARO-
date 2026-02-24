"""
Revenue metrics collection and analysis system.

This module provides comprehensive metrics collection for revenue operations,
tracking pipeline recovery, velocity improvements, and manual work reduction.
"""

import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from ..core.logging import get_logger
from ..models.enums import DecisionClass, ExecutionStatus, SalesActionType
from ..models.revenue_entities import RevenueImpact
from .activity_logger import get_activity_logger, ActionLogEntry, DecisionLogEntry


class MetricSnapshot(BaseModel):
    """Snapshot of revenue metrics at a specific point in time."""
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique snapshot ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Snapshot timestamp")
    period_start: datetime = Field(..., description="Start of measurement period")
    period_end: datetime = Field(..., description="End of measurement period")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Collected metrics")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class RevenueMetricsCollector:
    """
    Comprehensive revenue metrics collection and analysis system.
    
    Tracks pipeline recovery, velocity improvements, manual work reduction,
    and other key revenue operations metrics.
    """
    
    def __init__(self, logger_name: str = "revenue_metrics"):
        """Initialize the revenue metrics collector."""
        self.logger = get_logger(logger_name)
        self.activity_logger = get_activity_logger()
        self.metric_snapshots: List[MetricSnapshot] = []
    
    def collect_pipeline_recovery_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Collect metrics on pipeline recovery through autonomous interventions.
        
        Args:
            start_time: Start of measurement period
            end_time: End of measurement period
            
        Returns:
            Dictionary containing pipeline recovery metrics
        """
        # Get all decisions in the time period
        decisions = self.activity_logger.search_decision_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Get all actions in the time period
        actions = self.activity_logger.search_action_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Calculate pipeline recovery metrics
        total_decisions = len(decisions)
        auto_decisions = len([d for d in decisions if d.decision_type == DecisionClass.AUTO_EXECUTABLE])
        approval_decisions = len([d for d in decisions if d.decision_type == DecisionClass.APPROVAL_REQUIRED])
        insight_decisions = len([d for d in decisions if d.decision_type == DecisionClass.INSIGHT_ONLY])
        
        successful_actions = len([a for a in actions if a.execution_status == ExecutionStatus.COMPLETED])
        failed_actions = len([a for a in actions if a.execution_status == ExecutionStatus.FAILED])
        
        # Calculate revenue impact
        total_revenue_impact = sum([
            d.revenue_impact for d in decisions 
            if d.revenue_impact is not None
        ])
        
        pipeline_recovered = sum([
            a.revenue_impact for a in actions 
            if a.revenue_impact is not None and a.execution_status == ExecutionStatus.COMPLETED
        ])
        
        return {
            "total_decisions": total_decisions,
            "auto_decisions": auto_decisions,
            "approval_decisions": approval_decisions,
            "insight_decisions": insight_decisions,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "action_success_rate": successful_actions / len(actions) if actions else 0,
            "automation_rate": auto_decisions / total_decisions if total_decisions else 0,
            "total_revenue_impact": total_revenue_impact,
            "pipeline_recovered": pipeline_recovered
        }
    
    def collect_velocity_improvement_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Collect metrics on deal velocity improvements.
        
        Args:
            start_time: Start of measurement period
            end_time: End of measurement period
            
        Returns:
            Dictionary containing velocity improvement metrics
        """
        # Get activity logs for deal updates
        deal_activities = self.activity_logger.search_activity_logs(
            entity_type="deal",
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Group activities by deal
        deal_activity_map = defaultdict(list)
        for activity in deal_activities:
            if activity.entity_id:
                deal_activity_map[activity.entity_id].append(activity)
        
        # Calculate velocity metrics
        deals_with_activity = len(deal_activity_map)
        total_activities = len(deal_activities)
        
        # Calculate average time between activities (proxy for velocity)
        velocity_improvements = []
        for deal_id, activities in deal_activity_map.items():
            if len(activities) > 1:
                # Sort by timestamp
                activities.sort(key=lambda x: x.timestamp)
                
                # Calculate time differences
                time_diffs = []
                for i in range(1, len(activities)):
                    diff = (activities[i].timestamp - activities[i-1].timestamp).total_seconds() / 3600  # hours
                    time_diffs.append(diff)
                
                if time_diffs:
                    avg_time_between_activities = statistics.mean(time_diffs)
                    velocity_improvements.append(avg_time_between_activities)
        
        avg_velocity = statistics.mean(velocity_improvements) if velocity_improvements else 0
        
        # Count deals accelerated (deals with follow-up actions)
        deals_accelerated = len([
            deal_id for deal_id, activities in deal_activity_map.items()
            if any("follow" in activity.activity_type.lower() for activity in activities)
        ])
        
        return {
            "deals_with_activity": deals_with_activity,
            "total_deal_activities": total_activities,
            "avg_hours_between_activities": avg_velocity,
            "deals_accelerated": deals_accelerated,
            "velocity_improvement_percentage": max(0, (24 - avg_velocity) / 24 * 100) if avg_velocity > 0 else 0
        }
    
    def collect_manual_work_reduction_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Collect metrics on manual work reduction through automation.
        
        Args:
            start_time: Start of measurement period
            end_time: End of measurement period
            
        Returns:
            Dictionary containing manual work reduction metrics
        """
        # Get all automated actions
        actions = self.activity_logger.search_action_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Estimate time saved by action type
        time_savings_map = {
            SalesActionType.CREATE_TASK: 5,  # 5 minutes saved per task creation
            SalesActionType.UPDATE_DEAL: 3,  # 3 minutes saved per deal update
            SalesActionType.SEND_ALERT: 2,   # 2 minutes saved per alert
            SalesActionType.SCHEDULE_FOLLOWUP: 10,  # 10 minutes saved per follow-up scheduling
            SalesActionType.UPDATE_LEAD_STATUS: 2,  # 2 minutes saved per status update
            SalesActionType.ASSIGN_REP: 5,   # 5 minutes saved per rep assignment
            SalesActionType.CREATE_FOLLOWUP_MESSAGE: 15,  # 15 minutes saved per message creation
            SalesActionType.UPDATE_OPPORTUNITY_FLAG: 2   # 2 minutes saved per flag update
        }
        
        # Calculate time saved by action type
        time_saved_by_type = defaultdict(int)
        total_time_saved = 0
        
        for action in actions:
            if action.execution_status == ExecutionStatus.COMPLETED:
                time_saved = time_savings_map.get(action.action_type, 5)  # Default 5 minutes
                time_saved_by_type[action.action_type.value] += time_saved
                total_time_saved += time_saved
        
        # Count successful automations
        successful_automations = len([
            a for a in actions 
            if a.execution_status == ExecutionStatus.COMPLETED
        ])
        
        return {
            "successful_automations": successful_automations,
            "total_time_saved_minutes": total_time_saved,
            "total_time_saved_hours": total_time_saved / 60,
            "time_saved_by_action_type": dict(time_saved_by_type),
            "avg_time_saved_per_automation": total_time_saved / successful_automations if successful_automations else 0
        }
    
    def collect_system_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Collect system performance metrics.
        
        Args:
            start_time: Start of measurement period
            end_time: End of measurement period
            
        Returns:
            Dictionary containing system performance metrics
        """
        # Get all actions for performance analysis
        actions = self.activity_logger.search_action_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Calculate performance metrics
        total_actions = len(actions)
        completed_actions = len([a for a in actions if a.execution_status == ExecutionStatus.COMPLETED])
        failed_actions = len([a for a in actions if a.execution_status == ExecutionStatus.FAILED])
        retrying_actions = len([a for a in actions if a.execution_status == ExecutionStatus.RETRYING])
        
        # Calculate response times
        response_times = [a.duration_ms for a in actions if a.duration_ms is not None]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        median_response_time = statistics.median(response_times) if response_times else 0
        
        # Calculate retry rates
        actions_with_retries = len([a for a in actions if a.retry_count > 0])
        total_retries = sum([a.retry_count for a in actions])
        
        # Calculate error rates by action type
        error_rates_by_type = {}
        for action_type in SalesActionType:
            type_actions = [a for a in actions if a.action_type == action_type]
            type_failures = [a for a in type_actions if a.execution_status == ExecutionStatus.FAILED]
            error_rate = len(type_failures) / len(type_actions) if type_actions else 0
            error_rates_by_type[action_type.value] = error_rate
        
        return {
            "total_actions": total_actions,
            "completed_actions": completed_actions,
            "failed_actions": failed_actions,
            "retrying_actions": retrying_actions,
            "success_rate": completed_actions / total_actions if total_actions else 0,
            "failure_rate": failed_actions / total_actions if total_actions else 0,
            "avg_response_time_ms": avg_response_time,
            "median_response_time_ms": median_response_time,
            "actions_with_retries": actions_with_retries,
            "total_retries": total_retries,
            "avg_retries_per_action": total_retries / total_actions if total_actions else 0,
            "error_rates_by_action_type": error_rates_by_type
        }
    
    def collect_decision_accuracy_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Collect metrics on decision accuracy and outcomes.
        
        Args:
            start_time: Start of measurement period
            end_time: End of measurement period
            
        Returns:
            Dictionary containing decision accuracy metrics
        """
        # Get all decisions in the time period
        decisions = self.activity_logger.search_decision_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Calculate confidence metrics
        confidence_scores = [d.confidence for d in decisions if d.confidence > 0]
        avg_confidence = statistics.mean(confidence_scores) if confidence_scores else 0
        
        # Count decisions by type
        decision_type_counts = defaultdict(int)
        for decision in decisions:
            decision_type_counts[decision.decision_type.value] += 1
        
        # Count decisions with outcomes
        decisions_with_outcomes = len([d for d in decisions if d.outcome is not None])
        positive_outcomes = len([
            d for d in decisions 
            if d.outcome and "success" in d.outcome.lower()
        ])
        
        # Calculate accuracy rate (positive outcomes / total outcomes)
        accuracy_rate = positive_outcomes / decisions_with_outcomes if decisions_with_outcomes else 0
        
        # Count human approvals vs denials
        human_decisions = [d for d in decisions if d.human_decision is not None]
        approvals = len([d for d in human_decisions if "approve" in d.human_decision.lower()])
        denials = len([d for d in human_decisions if "deny" in d.human_decision.lower() or "denied" in d.human_decision.lower()])
        
        approval_rate = approvals / len(human_decisions) if human_decisions else 0
        
        return {
            "total_decisions": len(decisions),
            "avg_confidence_score": avg_confidence,
            "decision_type_counts": dict(decision_type_counts),
            "decisions_with_outcomes": decisions_with_outcomes,
            "positive_outcomes": positive_outcomes,
            "accuracy_rate": accuracy_rate,
            "human_decisions": len(human_decisions),
            "approvals": approvals,
            "denials": denials,
            "approval_rate": approval_rate
        }
    
    def create_comprehensive_snapshot(
        self,
        period_days: int = 7
    ) -> MetricSnapshot:
        """
        Create a comprehensive metrics snapshot for the specified period.
        
        Args:
            period_days: Number of days to include in the snapshot
            
        Returns:
            MetricSnapshot containing all collected metrics
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=period_days)
        
        # Collect all metric categories
        pipeline_metrics = self.collect_pipeline_recovery_metrics(start_time, end_time)
        velocity_metrics = self.collect_velocity_improvement_metrics(start_time, end_time)
        manual_work_metrics = self.collect_manual_work_reduction_metrics(start_time, end_time)
        performance_metrics = self.collect_system_performance_metrics(start_time, end_time)
        accuracy_metrics = self.collect_decision_accuracy_metrics(start_time, end_time)
        
        # Combine all metrics
        all_metrics = {
            "pipeline_recovery": pipeline_metrics,
            "velocity_improvement": velocity_metrics,
            "manual_work_reduction": manual_work_metrics,
            "system_performance": performance_metrics,
            "decision_accuracy": accuracy_metrics,
            "period_days": period_days
        }
        
        # Create snapshot
        snapshot = MetricSnapshot(
            period_start=start_time,
            period_end=end_time,
            metrics=all_metrics
        )
        
        # Store snapshot
        self.metric_snapshots.append(snapshot)
        
        # Log snapshot creation
        self.logger.info(
            f"Created comprehensive metrics snapshot for {period_days} day period",
            extra={
                "snapshot_id": snapshot.snapshot_id,
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "metrics_summary": {
                    "total_decisions": pipeline_metrics.get("total_decisions", 0),
                    "successful_actions": pipeline_metrics.get("successful_actions", 0),
                    "pipeline_recovered": pipeline_metrics.get("pipeline_recovered", 0),
                    "time_saved_hours": manual_work_metrics.get("total_time_saved_hours", 0)
                }
            }
        )
        
        return snapshot
    
    def get_trend_analysis(
        self,
        metric_name: str,
        snapshots: Optional[List[MetricSnapshot]] = None
    ) -> Dict[str, Any]:
        """
        Analyze trends for a specific metric across snapshots.
        
        Args:
            metric_name: Name of the metric to analyze (dot notation supported)
            snapshots: List of snapshots to analyze (defaults to all stored snapshots)
            
        Returns:
            Dictionary containing trend analysis
        """
        if snapshots is None:
            snapshots = self.metric_snapshots
        
        if not snapshots:
            return {"error": "No snapshots available for trend analysis"}
        
        # Extract metric values from snapshots
        values = []
        timestamps = []
        
        for snapshot in snapshots:
            # Navigate nested metric structure
            metric_parts = metric_name.split('.')
            value = snapshot.metrics
            
            try:
                for part in metric_parts:
                    value = value[part]
                
                if isinstance(value, (int, float)):
                    values.append(value)
                    timestamps.append(snapshot.timestamp)
            except (KeyError, TypeError):
                continue
        
        if not values:
            return {"error": f"No valid values found for metric: {metric_name}"}
        
        # Calculate trend statistics
        if len(values) > 1:
            # Calculate percentage change
            first_value = values[0]
            last_value = values[-1]
            percentage_change = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0
            
            # Calculate average change per period
            avg_change = (last_value - first_value) / (len(values) - 1)
        else:
            percentage_change = 0
            avg_change = 0
        
        return {
            "metric_name": metric_name,
            "data_points": len(values),
            "first_value": values[0] if values else None,
            "last_value": values[-1] if values else None,
            "min_value": min(values) if values else None,
            "max_value": max(values) if values else None,
            "avg_value": statistics.mean(values) if values else None,
            "percentage_change": percentage_change,
            "avg_change_per_period": avg_change,
            "trend_direction": "increasing" if avg_change > 0 else "decreasing" if avg_change < 0 else "stable",
            "timestamps": [ts.isoformat() for ts in timestamps],
            "values": values
        }
    
    def export_metrics_report(
        self,
        snapshot: Optional[MetricSnapshot] = None,
        format: str = "json"
    ) -> str:
        """
        Export a comprehensive metrics report.
        
        Args:
            snapshot: Specific snapshot to export (defaults to latest)
            format: Export format ("json" or "summary")
            
        Returns:
            Formatted metrics report
        """
        if snapshot is None:
            if not self.metric_snapshots:
                return "No metrics snapshots available"
            snapshot = max(self.metric_snapshots, key=lambda s: s.timestamp)
        
        if format == "json":
            return snapshot.model_dump_json(indent=2)
        
        elif format == "summary":
            metrics = snapshot.metrics
            
            summary = f"""
Revenue Operations Metrics Report
Generated: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
Period: {snapshot.period_start.strftime('%Y-%m-%d')} to {snapshot.period_end.strftime('%Y-%m-%d')}

PIPELINE RECOVERY:
- Total Decisions: {metrics['pipeline_recovery']['total_decisions']}
- Automation Rate: {metrics['pipeline_recovery']['automation_rate']:.1%}
- Action Success Rate: {metrics['pipeline_recovery']['action_success_rate']:.1%}
- Pipeline Recovered: ${metrics['pipeline_recovery']['pipeline_recovered']:,.2f}

VELOCITY IMPROVEMENT:
- Deals with Activity: {metrics['velocity_improvement']['deals_with_activity']}
- Deals Accelerated: {metrics['velocity_improvement']['deals_accelerated']}
- Velocity Improvement: {metrics['velocity_improvement']['velocity_improvement_percentage']:.1f}%

MANUAL WORK REDUCTION:
- Successful Automations: {metrics['manual_work_reduction']['successful_automations']}
- Time Saved: {metrics['manual_work_reduction']['total_time_saved_hours']:.1f} hours
- Avg Time per Automation: {metrics['manual_work_reduction']['avg_time_saved_per_automation']:.1f} minutes

SYSTEM PERFORMANCE:
- Success Rate: {metrics['system_performance']['success_rate']:.1%}
- Avg Response Time: {metrics['system_performance']['avg_response_time_ms']:.0f}ms
- Retry Rate: {metrics['system_performance']['avg_retries_per_action']:.2f}

DECISION ACCURACY:
- Avg Confidence: {metrics['decision_accuracy']['avg_confidence_score']:.1f}%
- Accuracy Rate: {metrics['decision_accuracy']['accuracy_rate']:.1%}
- Human Approval Rate: {metrics['decision_accuracy']['approval_rate']:.1%}
            """.strip()
            
            return summary
        
        else:
            return f"Unsupported format: {format}"


# Global metrics collector instance
_global_metrics_collector: Optional[RevenueMetricsCollector] = None


def get_metrics_collector() -> RevenueMetricsCollector:
    """Get the global revenue metrics collector instance."""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = RevenueMetricsCollector()
    return _global_metrics_collector