"""
Sales activity logging system for comprehensive audit trails and observability.

This module provides structured logging capabilities for all sales system activities,
decisions, and actions with timestamp tracking and audit trail maintenance.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from ..core.logging import get_logger
from ..models.enums import (
    ActivityType, DecisionClass, ExecutionStatus, RiskType, 
    SalesActionType, Severity
)
from ..models.revenue_entities import (
    Deal, Lead, PipelineRisk, RevenueDecisionLog, RevenueImpact, 
    SalesAction, SalesActivity, SalesRep
)


class ActivityLogEntry(BaseModel):
    """Structured log entry for sales activities."""
    log_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique log entry ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Log timestamp")
    activity_type: str = Field(..., description="Type of activity being logged")
    component: str = Field(..., description="System component generating the log")
    entity_type: Optional[str] = Field(None, description="Type of business entity (lead, deal, etc.)")
    entity_id: Optional[str] = Field(None, description="ID of the business entity")
    user_id: Optional[str] = Field(None, description="ID of the user performing the activity")
    session_id: Optional[str] = Field(None, description="Session ID for tracking related activities")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional activity details")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="System metadata")
    severity: str = Field("info", description="Log severity level")
    revenue_impact: Optional[float] = Field(None, description="Estimated revenue impact")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class DecisionLogEntry(BaseModel):
    """Structured log entry for revenue decisions."""
    log_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique log entry ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Decision timestamp")
    decision_id: str = Field(..., description="Unique decision identifier")
    decision_type: DecisionClass = Field(..., description="Classification of the decision")
    pipeline_risk_id: Optional[str] = Field(None, description="Associated pipeline risk ID")
    recommended_action_id: Optional[str] = Field(None, description="Recommended action ID")
    human_decision: Optional[str] = Field(None, description="Human decision if approval required")
    execution_status: Optional[ExecutionStatus] = Field(None, description="Execution status")
    confidence: float = Field(0.0, description="Decision confidence score", ge=0, le=100)
    reasoning: Optional[str] = Field(None, description="Decision reasoning")
    context: Dict[str, Any] = Field(default_factory=dict, description="Decision context")
    outcome: Optional[str] = Field(None, description="Decision outcome")
    revenue_impact: Optional[float] = Field(None, description="Measured revenue impact")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class ActionLogEntry(BaseModel):
    """Structured log entry for sales action execution."""
    log_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique log entry ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Action timestamp")
    action_id: str = Field(..., description="Unique action identifier")
    action_type: SalesActionType = Field(..., description="Type of sales action")
    execution_status: ExecutionStatus = Field(..., description="Current execution status")
    target_system: str = Field(..., description="Target system for execution")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retry attempts", ge=0)
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")
    revenue_impact: Optional[float] = Field(None, description="Estimated revenue impact")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class SalesActivityLogger:
    """
    Comprehensive sales activity logging system.
    
    Provides structured logging for all sales system activities, decisions,
    and actions with audit trail maintenance and search capabilities.
    """
    
    def __init__(self, logger_name: str = "sales_activity"):
        """Initialize the sales activity logger."""
        self.logger = get_logger(logger_name)
        self.activity_logs: List[ActivityLogEntry] = []
        self.decision_logs: List[DecisionLogEntry] = []
        self.action_logs: List[ActionLogEntry] = []
    
    def log_sales_activity(
        self,
        activity_type: str,
        component: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        revenue_impact: Optional[float] = None
    ) -> str:
        """
        Log a sales activity with structured data.
        
        Args:
            activity_type: Type of activity (e.g., 'lead_created', 'deal_updated')
            component: System component generating the log
            entity_type: Type of business entity (lead, deal, etc.)
            entity_id: ID of the business entity
            user_id: ID of the user performing the activity
            session_id: Session ID for tracking related activities
            details: Additional activity details
            severity: Log severity level
            revenue_impact: Estimated revenue impact
            
        Returns:
            Log entry ID
        """
        log_entry = ActivityLogEntry(
            activity_type=activity_type,
            component=component,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            session_id=session_id,
            details=details or {},
            severity=severity,
            revenue_impact=revenue_impact
        )
        
        # Store in memory for search capabilities
        self.activity_logs.append(log_entry)
        
        # Log to structured logger
        self.logger.info(
            f"Sales activity: {activity_type}",
            extra={
                "log_id": log_entry.log_id,
                "activity_type": activity_type,
                "component": component,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "session_id": session_id,
                "details": details or {},
                "severity": severity,
                "revenue_impact": revenue_impact,
                "log_category": "sales_activity"
            }
        )
        
        return log_entry.log_id
    
    def log_revenue_decision(
        self,
        decision_id: str,
        decision_type: DecisionClass,
        pipeline_risk_id: Optional[str] = None,
        recommended_action_id: Optional[str] = None,
        human_decision: Optional[str] = None,
        execution_status: Optional[ExecutionStatus] = None,
        confidence: float = 0.0,
        reasoning: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
        revenue_impact: Optional[float] = None
    ) -> str:
        """
        Log a revenue decision with comprehensive tracking.
        
        Args:
            decision_id: Unique decision identifier
            decision_type: Classification of the decision
            pipeline_risk_id: Associated pipeline risk ID
            recommended_action_id: Recommended action ID
            human_decision: Human decision if approval required
            execution_status: Current execution status
            confidence: Decision confidence score
            reasoning: Decision reasoning
            context: Decision context
            outcome: Decision outcome
            revenue_impact: Measured revenue impact
            
        Returns:
            Log entry ID
        """
        log_entry = DecisionLogEntry(
            decision_id=decision_id,
            decision_type=decision_type,
            pipeline_risk_id=pipeline_risk_id,
            recommended_action_id=recommended_action_id,
            human_decision=human_decision,
            execution_status=execution_status,
            confidence=confidence,
            reasoning=reasoning,
            context=context or {},
            outcome=outcome,
            revenue_impact=revenue_impact
        )
        
        # Store in memory for search capabilities
        self.decision_logs.append(log_entry)
        
        # Log to structured logger
        self.logger.info(
            f"Revenue decision: {decision_type.value}",
            extra={
                "log_id": log_entry.log_id,
                "decision_id": decision_id,
                "decision_type": decision_type.value,
                "pipeline_risk_id": pipeline_risk_id,
                "recommended_action_id": recommended_action_id,
                "human_decision": human_decision,
                "execution_status": execution_status.value if execution_status else None,
                "confidence": confidence,
                "reasoning": reasoning,
                "context": context or {},
                "outcome": outcome,
                "revenue_impact": revenue_impact,
                "log_category": "revenue_decision"
            }
        )
        
        return log_entry.log_id
    
    def log_sales_action(
        self,
        action_id: str,
        action_type: SalesActionType,
        execution_status: ExecutionStatus,
        target_system: str,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        duration_ms: Optional[int] = None,
        revenue_impact: Optional[float] = None
    ) -> str:
        """
        Log a sales action execution with detailed tracking.
        
        Args:
            action_id: Unique action identifier
            action_type: Type of sales action
            execution_status: Current execution status
            target_system: Target system for execution
            parameters: Action parameters
            result: Execution result
            error_message: Error message if failed
            retry_count: Number of retry attempts
            duration_ms: Execution duration in milliseconds
            revenue_impact: Estimated revenue impact
            
        Returns:
            Log entry ID
        """
        log_entry = ActionLogEntry(
            action_id=action_id,
            action_type=action_type,
            execution_status=execution_status,
            target_system=target_system,
            parameters=parameters or {},
            result=result,
            error_message=error_message,
            retry_count=retry_count,
            duration_ms=duration_ms,
            revenue_impact=revenue_impact
        )
        
        # Store in memory for search capabilities
        self.action_logs.append(log_entry)
        
        # Determine log level based on execution status
        log_level = "info"
        if execution_status == ExecutionStatus.FAILED:
            log_level = "error"
        elif execution_status == ExecutionStatus.RETRYING:
            log_level = "warning"
        
        # Log to structured logger
        getattr(self.logger, log_level)(
            f"Sales action: {action_type.value} - {execution_status.value}",
            extra={
                "log_id": log_entry.log_id,
                "action_id": action_id,
                "action_type": action_type.value,
                "execution_status": execution_status.value,
                "target_system": target_system,
                "parameters": parameters or {},
                "result": result,
                "error_message": error_message,
                "retry_count": retry_count,
                "duration_ms": duration_ms,
                "revenue_impact": revenue_impact,
                "log_category": "sales_action"
            }
        )
        
        return log_entry.log_id
    
    def log_business_entity_change(
        self,
        entity_type: str,
        entity_id: str,
        change_type: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Log changes to business entities (leads, deals, etc.) for audit trail.
        
        Args:
            entity_type: Type of business entity
            entity_id: ID of the business entity
            change_type: Type of change (created, updated, deleted)
            old_values: Previous values before change
            new_values: New values after change
            user_id: ID of the user making the change
            session_id: Session ID for tracking related changes
            
        Returns:
            Log entry ID
        """
        details = {
            "change_type": change_type,
            "old_values": old_values or {},
            "new_values": new_values or {}
        }
        
        return self.log_sales_activity(
            activity_type=f"{entity_type}_{change_type}",
            component="entity_manager",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            session_id=session_id,
            details=details,
            severity="info"
        )
    
    def search_activity_logs(
        self,
        activity_type: Optional[str] = None,
        component: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[ActivityLogEntry]:
        """
        Search activity logs with various filters.
        
        Args:
            activity_type: Filter by activity type
            component: Filter by component
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            user_id: Filter by user ID
            session_id: Filter by session ID
            start_time: Filter by start time
            end_time: Filter by end time
            severity: Filter by severity level
            limit: Maximum number of results
            
        Returns:
            List of matching activity log entries
        """
        results = []
        
        for log_entry in self.activity_logs:
            # Apply filters
            if activity_type and log_entry.activity_type != activity_type:
                continue
            if component and log_entry.component != component:
                continue
            if entity_type and log_entry.entity_type != entity_type:
                continue
            if entity_id and log_entry.entity_id != entity_id:
                continue
            if user_id and log_entry.user_id != user_id:
                continue
            if session_id and log_entry.session_id != session_id:
                continue
            if severity and log_entry.severity != severity:
                continue
            if start_time and log_entry.timestamp < start_time:
                continue
            if end_time and log_entry.timestamp > end_time:
                continue
            
            results.append(log_entry)
            
            if len(results) >= limit:
                break
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results
    
    def search_decision_logs(
        self,
        decision_type: Optional[DecisionClass] = None,
        pipeline_risk_id: Optional[str] = None,
        execution_status: Optional[ExecutionStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100
    ) -> List[DecisionLogEntry]:
        """
        Search decision logs with various filters.
        
        Args:
            decision_type: Filter by decision type
            pipeline_risk_id: Filter by pipeline risk ID
            execution_status: Filter by execution status
            start_time: Filter by start time
            end_time: Filter by end time
            min_confidence: Filter by minimum confidence score
            limit: Maximum number of results
            
        Returns:
            List of matching decision log entries
        """
        results = []
        
        for log_entry in self.decision_logs:
            # Apply filters
            if decision_type and log_entry.decision_type != decision_type:
                continue
            if pipeline_risk_id and log_entry.pipeline_risk_id != pipeline_risk_id:
                continue
            if execution_status and log_entry.execution_status != execution_status:
                continue
            if start_time and log_entry.timestamp < start_time:
                continue
            if end_time and log_entry.timestamp > end_time:
                continue
            if min_confidence and log_entry.confidence < min_confidence:
                continue
            
            results.append(log_entry)
            
            if len(results) >= limit:
                break
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results
    
    def search_action_logs(
        self,
        action_type: Optional[SalesActionType] = None,
        execution_status: Optional[ExecutionStatus] = None,
        target_system: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_retry_count: Optional[int] = None,
        limit: int = 100
    ) -> List[ActionLogEntry]:
        """
        Search action logs with various filters.
        
        Args:
            action_type: Filter by action type
            execution_status: Filter by execution status
            target_system: Filter by target system
            start_time: Filter by start time
            end_time: Filter by end time
            min_retry_count: Filter by minimum retry count
            limit: Maximum number of results
            
        Returns:
            List of matching action log entries
        """
        results = []
        
        for log_entry in self.action_logs:
            # Apply filters
            if action_type and log_entry.action_type != action_type:
                continue
            if execution_status and log_entry.execution_status != execution_status:
                continue
            if target_system and log_entry.target_system != target_system:
                continue
            if start_time and log_entry.timestamp < start_time:
                continue
            if end_time and log_entry.timestamp > end_time:
                continue
            if min_retry_count and log_entry.retry_count < min_retry_count:
                continue
            
            results.append(log_entry)
            
            if len(results) >= limit:
                break
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results
    
    def get_audit_trail(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> List[ActivityLogEntry]:
        """
        Get complete audit trail for a specific business entity.
        
        Args:
            entity_type: Type of business entity
            entity_id: ID of the business entity
            limit: Maximum number of results
            
        Returns:
            List of activity log entries for the entity
        """
        return self.search_activity_logs(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit
        )
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """
        Get system health metrics from logged activities.
        
        Returns:
            Dictionary containing system health metrics
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now.replace(hour=now.hour-1) if now.hour > 0 else now.replace(day=now.day-1, hour=23)
        
        # Count activities in the last hour
        recent_activities = self.search_activity_logs(start_time=one_hour_ago)
        recent_decisions = self.search_decision_logs(start_time=one_hour_ago)
        recent_actions = self.search_action_logs(start_time=one_hour_ago)
        
        # Count failed actions
        failed_actions = self.search_action_logs(
            execution_status=ExecutionStatus.FAILED,
            start_time=one_hour_ago
        )
        
        # Count retrying actions
        retrying_actions = self.search_action_logs(
            execution_status=ExecutionStatus.RETRYING,
            start_time=one_hour_ago
        )
        
        return {
            "timestamp": now.isoformat(),
            "activities_last_hour": len(recent_activities),
            "decisions_last_hour": len(recent_decisions),
            "actions_last_hour": len(recent_actions),
            "failed_actions_last_hour": len(failed_actions),
            "retrying_actions_last_hour": len(retrying_actions),
            "total_activity_logs": len(self.activity_logs),
            "total_decision_logs": len(self.decision_logs),
            "total_action_logs": len(self.action_logs)
        }
    
    def export_logs_json(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """
        Export logs as JSON for external analysis.
        
        Args:
            start_time: Start time for export
            end_time: End time for export
            
        Returns:
            JSON string containing exported logs
        """
        # Filter logs by time range
        activity_logs = self.search_activity_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        decision_logs = self.search_decision_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        action_logs = self.search_action_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        export_data = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "activity_logs": [log.model_dump() for log in activity_logs],
            "decision_logs": [log.model_dump() for log in decision_logs],
            "action_logs": [log.model_dump() for log in action_logs]
        }
        
        return json.dumps(export_data, indent=2, default=str)


# Global logger instance
_global_activity_logger: Optional[SalesActivityLogger] = None


def get_activity_logger() -> SalesActivityLogger:
    """Get the global sales activity logger instance."""
    global _global_activity_logger
    if _global_activity_logger is None:
        _global_activity_logger = SalesActivityLogger()
    return _global_activity_logger


def log_sales_activity(
    activity_type: str,
    component: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    severity: str = "info",
    revenue_impact: Optional[float] = None
) -> str:
    """Convenience function to log sales activity using global logger."""
    return get_activity_logger().log_sales_activity(
        activity_type=activity_type,
        component=component,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        session_id=session_id,
        details=details,
        severity=severity,
        revenue_impact=revenue_impact
    )


def log_revenue_decision(
    decision_id: str,
    decision_type: DecisionClass,
    pipeline_risk_id: Optional[str] = None,
    recommended_action_id: Optional[str] = None,
    human_decision: Optional[str] = None,
    execution_status: Optional[ExecutionStatus] = None,
    confidence: float = 0.0,
    reasoning: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    outcome: Optional[str] = None,
    revenue_impact: Optional[float] = None
) -> str:
    """Convenience function to log revenue decision using global logger."""
    return get_activity_logger().log_revenue_decision(
        decision_id=decision_id,
        decision_type=decision_type,
        pipeline_risk_id=pipeline_risk_id,
        recommended_action_id=recommended_action_id,
        human_decision=human_decision,
        execution_status=execution_status,
        confidence=confidence,
        reasoning=reasoning,
        context=context,
        outcome=outcome,
        revenue_impact=revenue_impact
    )


def log_sales_action(
    action_id: str,
    action_type: SalesActionType,
    execution_status: ExecutionStatus,
    target_system: str,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    retry_count: int = 0,
    duration_ms: Optional[int] = None,
    revenue_impact: Optional[float] = None
) -> str:
    """Convenience function to log sales action using global logger."""
    return get_activity_logger().log_sales_action(
        action_id=action_id,
        action_type=action_type,
        execution_status=execution_status,
        target_system=target_system,
        parameters=parameters,
        result=result,
        error_message=error_message,
        retry_count=retry_count,
        duration_ms=duration_ms,
        revenue_impact=revenue_impact
    )