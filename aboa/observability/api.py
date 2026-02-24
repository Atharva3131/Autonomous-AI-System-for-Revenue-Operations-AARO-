"""
API endpoints for revenue observability and metrics system.

This module provides REST API endpoints for accessing sales activity logs,
revenue metrics, and system health information.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..core.logging import get_logger
from ..models.enums import DecisionClass, ExecutionStatus, SalesActionType
from .activity_logger import (
    get_activity_logger, ActivityLogEntry, DecisionLogEntry, ActionLogEntry
)
from .metrics_collector import get_metrics_collector, MetricSnapshot


# API Models
class LogSearchRequest(BaseModel):
    """Request model for log search operations."""
    activity_type: Optional[str] = None
    component: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    severity: Optional[str] = None
    limit: int = Field(default=100, le=1000)


class DecisionLogSearchRequest(BaseModel):
    """Request model for decision log search operations."""
    decision_type: Optional[DecisionClass] = None
    pipeline_risk_id: Optional[str] = None
    execution_status: Optional[ExecutionStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=100)
    limit: int = Field(default=100, le=1000)


class ActionLogSearchRequest(BaseModel):
    """Request model for action log search operations."""
    action_type: Optional[SalesActionType] = None
    execution_status: Optional[ExecutionStatus] = None
    target_system: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_retry_count: Optional[int] = Field(None, ge=0)
    limit: int = Field(default=100, le=1000)


class MetricsRequest(BaseModel):
    """Request model for metrics collection."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    period_days: int = Field(default=7, ge=1, le=365)


class TrendAnalysisRequest(BaseModel):
    """Request model for trend analysis."""
    metric_name: str = Field(..., description="Metric name using dot notation")
    snapshot_ids: Optional[List[str]] = None


# API Response Models
class LogSearchResponse(BaseModel):
    """Response model for log search operations."""
    total_results: int
    results: List[ActivityLogEntry]
    search_params: Dict[str, Any]


class DecisionLogSearchResponse(BaseModel):
    """Response model for decision log search operations."""
    total_results: int
    results: List[DecisionLogEntry]
    search_params: Dict[str, Any]


class ActionLogSearchResponse(BaseModel):
    """Response model for action log search operations."""
    total_results: int
    results: List[ActionLogEntry]
    search_params: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response model for system health metrics."""
    status: str
    timestamp: datetime
    metrics: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Response model for metrics data."""
    snapshot: MetricSnapshot
    summary: Dict[str, Any]


class TrendAnalysisResponse(BaseModel):
    """Response model for trend analysis."""
    metric_name: str
    analysis: Dict[str, Any]


# Initialize router and logger
router = APIRouter(prefix="/api/v1/observability", tags=["observability"])
logger = get_logger(__name__)


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """
    Get current system metrics.
    
    Returns basic system metrics and performance indicators.
    """
    try:
        return {
            "status": "operational",
            "service": "observability",
            "metrics_available": True,
            "message": "Metrics service is running"
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return {
            "status": "error",
            "service": "observability",
            "error": str(e),
            "message": "Failed to retrieve metrics"
        }


@router.get("/health", response_model=HealthResponse)
async def get_system_health():
    """
    Get current system health metrics.
    
    Returns comprehensive health information including recent activity counts,
    error rates, and system performance indicators.
    """
    try:
        activity_logger = get_activity_logger()
        health_metrics = activity_logger.get_system_health_metrics()
        
        # Determine overall health status
        failed_actions = health_metrics.get("failed_actions_last_hour", 0)
        total_actions = health_metrics.get("actions_last_hour", 0)
        
        if total_actions == 0:
            status = "idle"
        elif total_actions > 0 and failed_actions / total_actions > 0.1:
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthResponse(
            status=status,
            timestamp=datetime.now(timezone.utc),
            metrics=health_metrics
        )
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


@router.post("/logs/search", response_model=LogSearchResponse)
async def search_activity_logs(request: LogSearchRequest):
    """
    Search sales activity logs with various filters.
    
    Supports filtering by activity type, component, entity information,
    user, time range, and severity level.
    """
    try:
        activity_logger = get_activity_logger()
        
        results = activity_logger.search_activity_logs(
            activity_type=request.activity_type,
            component=request.component,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            user_id=request.user_id,
            session_id=request.session_id,
            start_time=request.start_time,
            end_time=request.end_time,
            severity=request.severity,
            limit=request.limit
        )
        
        return LogSearchResponse(
            total_results=len(results),
            results=results,
            search_params=request.model_dump(exclude_none=True)
        )
        
    except Exception as e:
        logger.error(f"Error searching activity logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search activity logs")


@router.post("/logs/decisions/search", response_model=DecisionLogSearchResponse)
async def search_decision_logs(request: DecisionLogSearchRequest):
    """
    Search revenue decision logs with various filters.
    
    Supports filtering by decision type, pipeline risk, execution status,
    time range, and confidence level.
    """
    try:
        activity_logger = get_activity_logger()
        
        results = activity_logger.search_decision_logs(
            decision_type=request.decision_type,
            pipeline_risk_id=request.pipeline_risk_id,
            execution_status=request.execution_status,
            start_time=request.start_time,
            end_time=request.end_time,
            min_confidence=request.min_confidence,
            limit=request.limit
        )
        
        return DecisionLogSearchResponse(
            total_results=len(results),
            results=results,
            search_params=request.model_dump(exclude_none=True)
        )
        
    except Exception as e:
        logger.error(f"Error searching decision logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search decision logs")


@router.post("/logs/actions/search", response_model=ActionLogSearchResponse)
async def search_action_logs(request: ActionLogSearchRequest):
    """
    Search sales action logs with various filters.
    
    Supports filtering by action type, execution status, target system,
    time range, and retry count.
    """
    try:
        activity_logger = get_activity_logger()
        
        results = activity_logger.search_action_logs(
            action_type=request.action_type,
            execution_status=request.execution_status,
            target_system=request.target_system,
            start_time=request.start_time,
            end_time=request.end_time,
            min_retry_count=request.min_retry_count,
            limit=request.limit
        )
        
        return ActionLogSearchResponse(
            total_results=len(results),
            results=results,
            search_params=request.model_dump(exclude_none=True)
        )
        
    except Exception as e:
        logger.error(f"Error searching action logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search action logs")


@router.get("/logs/audit/{entity_type}/{entity_id}")
async def get_audit_trail(
    entity_type: str,
    entity_id: str,
    limit: int = Query(default=50, le=200)
):
    """
    Get complete audit trail for a specific business entity.
    
    Returns all logged activities for the specified entity,
    providing a comprehensive history of changes and interactions.
    """
    try:
        activity_logger = get_activity_logger()
        
        audit_trail = activity_logger.get_audit_trail(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit
        )
        
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "total_entries": len(audit_trail),
            "audit_trail": audit_trail
        }
        
    except Exception as e:
        logger.error(f"Error getting audit trail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve audit trail")


@router.post("/metrics/collect", response_model=MetricsResponse)
async def collect_metrics(request: MetricsRequest):
    """
    Collect comprehensive revenue operations metrics.
    
    Generates a metrics snapshot for the specified time period,
    including pipeline recovery, velocity improvements, and system performance.
    """
    try:
        metrics_collector = get_metrics_collector()
        
        if request.start_time and request.end_time:
            # Use specific time range
            end_time = request.end_time
            start_time = request.start_time
            period_days = (end_time - start_time).days
        else:
            # Use period_days from request
            period_days = request.period_days
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=period_days)
        
        # Create comprehensive snapshot
        snapshot = metrics_collector.create_comprehensive_snapshot(period_days)
        
        # Generate summary with safe key access
        pipeline_metrics = snapshot.metrics.get("pipeline_recovery", {})
        manual_work_metrics = snapshot.metrics.get("manual_work_reduction", {})
        performance_metrics = snapshot.metrics.get("system_performance", {})
        
        summary = {
            "period_days": period_days,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "key_metrics": {
                "total_decisions": pipeline_metrics.get("total_decisions", 0),
                "automation_rate": pipeline_metrics.get("automation_rate", 0.0),
                "pipeline_recovered": pipeline_metrics.get("pipeline_recovered", 0.0),
                "time_saved_hours": manual_work_metrics.get("total_time_saved_hours", 0.0),
                "system_success_rate": performance_metrics.get("success_rate", 0.0)
            }
        }
        
        return MetricsResponse(
            snapshot=snapshot,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to collect metrics")


@router.get("/metrics/snapshots")
async def get_metric_snapshots(
    limit: int = Query(default=10, le=100),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None)
):
    """
    Get stored metric snapshots.
    
    Returns a list of previously collected metric snapshots,
    optionally filtered by time range.
    """
    try:
        metrics_collector = get_metrics_collector()
        snapshots = metrics_collector.metric_snapshots
        
        # Filter by time range if specified
        if start_time or end_time:
            filtered_snapshots = []
            for snapshot in snapshots:
                if start_time and snapshot.timestamp < start_time:
                    continue
                if end_time and snapshot.timestamp > end_time:
                    continue
                filtered_snapshots.append(snapshot)
            snapshots = filtered_snapshots
        
        # Sort by timestamp (most recent first) and limit
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        snapshots = snapshots[:limit]
        
        return {
            "total_snapshots": len(snapshots),
            "snapshots": snapshots
        }
        
    except Exception as e:
        logger.error(f"Error getting metric snapshots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metric snapshots")


@router.post("/metrics/trends", response_model=TrendAnalysisResponse)
async def analyze_metric_trends(request: TrendAnalysisRequest):
    """
    Analyze trends for a specific metric across snapshots.
    
    Provides trend analysis including percentage change, direction,
    and statistical information for the specified metric.
    """
    try:
        metrics_collector = get_metrics_collector()
        
        # Get snapshots to analyze
        if request.snapshot_ids:
            snapshots = [
                s for s in metrics_collector.metric_snapshots
                if s.snapshot_id in request.snapshot_ids
            ]
        else:
            snapshots = metrics_collector.metric_snapshots
        
        # Perform trend analysis
        analysis = metrics_collector.get_trend_analysis(
            metric_name=request.metric_name,
            snapshots=snapshots
        )
        
        return TrendAnalysisResponse(
            metric_name=request.metric_name,
            analysis=analysis
        )
        
    except Exception as e:
        logger.error(f"Error analyzing metric trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze metric trends")


@router.get("/metrics/report")
async def get_metrics_report(
    snapshot_id: Optional[str] = Query(None),
    format: str = Query(default="summary", pattern="^(json|summary)$")
):
    """
    Get a formatted metrics report.
    
    Returns a comprehensive metrics report in the specified format,
    either as JSON data or a human-readable summary.
    """
    try:
        metrics_collector = get_metrics_collector()
        
        # Find specific snapshot if requested
        snapshot = None
        if snapshot_id:
            snapshot = next(
                (s for s in metrics_collector.metric_snapshots if s.snapshot_id == snapshot_id),
                None
            )
            if not snapshot:
                raise HTTPException(status_code=404, detail="Snapshot not found")
        
        # Generate report
        report = metrics_collector.export_metrics_report(
            snapshot=snapshot,
            format=format
        )
        
        if format == "json":
            return {"report": report, "format": "json"}
        else:
            return {"report": report, "format": "summary"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating metrics report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate metrics report")


@router.get("/logs/export")
async def export_logs(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    format: str = Query(default="json", pattern="^json$")
):
    """
    Export logs for external analysis.
    
    Returns logs in JSON format for the specified time range,
    suitable for external analysis tools or backup purposes.
    """
    try:
        activity_logger = get_activity_logger()
        
        # Export logs as JSON
        exported_logs = activity_logger.export_logs_json(
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "export_format": format,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "data": exported_logs
        }
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export logs")


# Health check endpoint for monitoring
@router.get("/ping")
async def ping():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "observability"
    }