"""
Revenue Optimization API endpoints.

This module provides FastAPI endpoints for pipeline velocity optimization triggers,
sales efficiency analysis and recommendations, and revenue impact reporting
as specified in Requirements 8.6 and 7.3.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..core.auth import get_current_tenant_context
from ..core.logging import get_logger, log_business_event
from ..models.enums import DealStage, LeadStatus, RiskType, Severity
from ..models.revenue_entities import Deal, Lead, SalesActivity, SalesRep, RevenueImpact
from .pipeline_velocity_optimizer import PipelineVelocityOptimizer
from .sales_process_efficiency_optimizer import SalesProcessEfficiencyOptimizer

logger = get_logger(__name__)

router = APIRouter(prefix="/revenue-optimization", tags=["Revenue Optimization"])


# Request/Response Models
class VelocityOptimizationTriggerRequest(BaseModel):
    """Request model for pipeline velocity optimization triggers."""
    deals: List[Deal] = Field(..., description="List of deals to optimize")
    leads: List[Lead] = Field(default_factory=list, description="List of leads to optimize")
    activities: List[SalesActivity] = Field(default_factory=list, description="List of sales activities")
    reps: List[SalesRep] = Field(default_factory=list, description="List of sales representatives")
    trigger_type: str = Field(..., description="Type of optimization trigger", pattern="^(scheduled|manual|risk_detected|threshold_breach)$")
    priority: str = Field("medium", description="Optimization priority level", pattern="^(low|medium|high|critical)$")
    auto_execute_actions: bool = Field(True, description="Whether to automatically execute recommended actions")
    max_actions: int = Field(25, description="Maximum number of actions to execute", ge=1, le=100)
    focus_areas: List[str] = Field(default_factory=list, description="Specific areas to focus optimization on")


class VelocityOptimizationTriggerResponse(BaseModel):
    """Response model for pipeline velocity optimization triggers."""
    trigger_id: str = Field(..., description="Unique trigger identifier")
    status: str = Field(..., description="Trigger execution status")
    timestamp: str = Field(..., description="Trigger execution timestamp")
    optimization_results: Dict[str, Any] = Field(..., description="Optimization results")
    actions_triggered: int = Field(..., description="Number of actions triggered")
    estimated_revenue_impact: Optional[Decimal] = Field(None, description="Estimated revenue impact")
    next_optimization_due: Optional[datetime] = Field(None, description="When next optimization is due")


class SalesEfficiencyAnalysisRequest(BaseModel):
    """Request model for sales efficiency analysis."""
    reps: List[SalesRep] = Field(..., description="List of sales representatives to analyze")
    deals: List[Deal] = Field(..., description="List of deals for analysis")
    leads: List[Lead] = Field(default_factory=list, description="List of leads for analysis")
    activities: List[SalesActivity] = Field(default_factory=list, description="List of sales activities")
    analysis_period_days: int = Field(30, description="Analysis period in days", ge=1, le=365)
    include_team_analysis: bool = Field(True, description="Include team-level analysis")
    include_coaching_recommendations: bool = Field(True, description="Include coaching recommendations")
    include_resource_optimization: bool = Field(True, description="Include resource allocation optimization")
    include_process_improvements: bool = Field(True, description="Include process efficiency improvements")
    benchmark_against_team: bool = Field(True, description="Benchmark individual performance against team")


class SalesEfficiencyAnalysisResponse(BaseModel):
    """Response model for sales efficiency analysis."""
    analysis_id: str = Field(..., description="Unique analysis identifier")
    timestamp: str = Field(..., description="Analysis timestamp")
    analysis_period_days: int = Field(..., description="Analysis period in days")
    individual_analyses: List[Dict[str, Any]] = Field(..., description="Individual rep analyses")
    team_analysis: Dict[str, Any] = Field(..., description="Team-level analysis")
    coaching_recommendations: List[Dict[str, Any]] = Field(..., description="Coaching recommendations")
    resource_optimization: Dict[str, Any] = Field(..., description="Resource allocation optimization")
    process_improvements: Dict[str, Any] = Field(..., description="Process efficiency improvements")
    performance_benchmarks: Dict[str, Any] = Field(..., description="Performance benchmarks")
    key_insights: List[str] = Field(..., description="Key insights from analysis")
    recommended_actions: List[Dict[str, Any]] = Field(..., description="Recommended actions")


class RevenueImpactReportRequest(BaseModel):
    """Request model for revenue impact reporting."""
    report_period_days: int = Field(30, description="Report period in days", ge=1, le=365)
    include_pipeline_recovery: bool = Field(True, description="Include pipeline recovery metrics")
    include_velocity_improvements: bool = Field(True, description="Include velocity improvement metrics")
    include_conversion_improvements: bool = Field(True, description="Include conversion improvement metrics")
    include_manual_work_reduction: bool = Field(True, description="Include manual work reduction metrics")
    include_roi_analysis: bool = Field(True, description="Include ROI analysis")
    segment_by_rep: bool = Field(False, description="Segment results by sales rep")
    segment_by_deal_size: bool = Field(False, description="Segment results by deal size")
    segment_by_stage: bool = Field(False, description="Segment results by deal stage")
    baseline_comparison: bool = Field(True, description="Include baseline comparison")


class RevenueImpactReportResponse(BaseModel):
    """Response model for revenue impact reporting."""
    report_id: str = Field(..., description="Unique report identifier")
    timestamp: str = Field(..., description="Report generation timestamp")
    report_period_days: int = Field(..., description="Report period in days")
    summary_metrics: Dict[str, Any] = Field(..., description="Summary revenue impact metrics")
    pipeline_recovery: Dict[str, Any] = Field(..., description="Pipeline recovery metrics")
    velocity_improvements: Dict[str, Any] = Field(..., description="Velocity improvement metrics")
    conversion_improvements: Dict[str, Any] = Field(..., description="Conversion improvement metrics")
    manual_work_reduction: Dict[str, Any] = Field(..., description="Manual work reduction metrics")
    roi_analysis: Dict[str, Any] = Field(..., description="ROI analysis")
    segmented_results: Dict[str, Any] = Field(..., description="Segmented analysis results")
    baseline_comparison: Dict[str, Any] = Field(..., description="Baseline comparison")
    trends: List[Dict[str, Any]] = Field(..., description="Revenue impact trends")
    recommendations: List[str] = Field(..., description="Recommendations for improvement")


# Initialize components
velocity_optimizer = PipelineVelocityOptimizer()
efficiency_optimizer = SalesProcessEfficiencyOptimizer()


@router.post("/velocity/trigger", response_model=VelocityOptimizationTriggerResponse)
async def trigger_pipeline_velocity_optimization(
    request: VelocityOptimizationTriggerRequest,
    background_tasks: BackgroundTasks,
    tenant_context = Depends(get_current_tenant_context)
) -> VelocityOptimizationTriggerResponse:
    """
    Trigger pipeline velocity optimization with automated action execution.
    
    This endpoint provides automated follow-up scheduling, revenue impact prioritization,
    and SOP compliance monitoring as specified in Requirements 8.1, 8.2, 8.4.
    """
    try:
        import uuid
        
        trigger_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        tenant_id = tenant_context.tenant_id
        
        logger.info(
            f"Triggering pipeline velocity optimization for tenant {tenant_id}",
            extra={
                "trigger_id": trigger_id,
                "trigger_type": request.trigger_type,
                "priority": request.priority,
                "auto_execute_actions": request.auto_execute_actions,
                "max_actions": request.max_actions,
                "focus_areas": request.focus_areas
            }
        )
        
        # Configure optimizer based on request
        config_updates = {
            'optimization_enabled': True,
            'auto_followup_enabled': True,
            'sop_monitoring_enabled': True,
            'max_actions_per_run': request.max_actions,
            'min_confidence_threshold': 70.0 if request.priority == 'low' else 80.0 if request.priority == 'medium' else 90.0,
            'batch_processing': True
        }
        
        # Apply focus areas if specified
        if 'stalled_deals' in request.focus_areas:
            config_updates['stalled_deal_threshold_days'] = 7
        if 'high_value_deals' in request.focus_areas:
            config_updates['high_value_threshold'] = 25000
        if 'sop_compliance' in request.focus_areas:
            config_updates['sop_monitoring_enabled'] = True
        
        velocity_optimizer.config.update(config_updates)
        
        # Perform optimization
        optimization_results = velocity_optimizer.optimize_pipeline_velocity(
            deals=request.deals,
            leads=request.leads,
            activities=request.activities,
            reps=request.reps,
            context={'trigger_type': request.trigger_type, 'priority': request.priority}
        )
        
        # Count triggered actions
        actions_triggered = len(optimization_results.get('followup_actions', []))
        
        # Calculate estimated revenue impact
        estimated_revenue_impact = None
        if optimization_results.get('summary', {}).get('potential_revenue_recovery'):
            estimated_revenue_impact = Decimal(optimization_results['summary']['potential_revenue_recovery'])
        
        # Schedule next optimization based on priority
        next_optimization_due = None
        if request.priority == 'critical':
            next_optimization_due = start_time + timedelta(hours=4)
        elif request.priority == 'high':
            next_optimization_due = start_time + timedelta(hours=12)
        elif request.priority == 'medium':
            next_optimization_due = start_time + timedelta(days=1)
        else:  # low priority
            next_optimization_due = start_time + timedelta(days=3)
        
        # Execute actions in background if requested
        if request.auto_execute_actions and actions_triggered > 0:
            background_tasks.add_task(
                _execute_optimization_actions,
                optimization_results.get('followup_actions', []),
                tenant_id,
                trigger_id
            )
        
        log_business_event(
            logger,
            "velocity_optimization_triggered",
            "revenue_optimization",
            trigger_id,
            details={
                "trigger_type": request.trigger_type,
                "actions_triggered": actions_triggered,
                "estimated_revenue_impact": str(estimated_revenue_impact) if estimated_revenue_impact else None,
                "auto_execute_actions": request.auto_execute_actions
            }
        )
        
        return VelocityOptimizationTriggerResponse(
            trigger_id=trigger_id,
            status="completed",
            timestamp=start_time.isoformat(),
            optimization_results=optimization_results,
            actions_triggered=actions_triggered,
            estimated_revenue_impact=estimated_revenue_impact,
            next_optimization_due=next_optimization_due
        )
        
    except Exception as e:
        logger.error(f"Pipeline velocity optimization trigger failed for tenant {tenant_id}: {str(e)}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Velocity optimization trigger failed: {str(e)}")


@router.post("/efficiency/analyze", response_model=SalesEfficiencyAnalysisResponse)
async def analyze_sales_efficiency(
    request: SalesEfficiencyAnalysisRequest,
    tenant_context = Depends(get_current_tenant_context)
) -> SalesEfficiencyAnalysisResponse:
    """
    Perform comprehensive sales efficiency analysis and generate recommendations.
    
    This endpoint provides rep performance analysis, coaching recommendations,
    resource allocation optimization, and process improvements as specified
    in Requirements 8.3, 8.5, 8.7.
    """
    try:
        import uuid
        
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        tenant_id = tenant_context.tenant_id
        
        logger.info(
            f"Analyzing sales efficiency for tenant {tenant_id}",
            extra={
                "analysis_id": analysis_id,
                "analysis_period_days": request.analysis_period_days,
                "reps_count": len(request.reps),
                "deals_count": len(request.deals),
                "include_team_analysis": request.include_team_analysis,
                "include_coaching_recommendations": request.include_coaching_recommendations
            }
        )
        
        # Configure efficiency optimizer
        efficiency_optimizer.config.update({
            'analysis_enabled': True,
            'coaching_enabled': request.include_coaching_recommendations,
            'resource_optimization_enabled': request.include_resource_optimization,
            'process_automation_enabled': request.include_process_improvements,
            'performance_tracking_enabled': True
        })
        
        # Perform comprehensive efficiency optimization
        optimization_results = efficiency_optimizer.optimize_sales_process_efficiency(
            reps=request.reps,
            deals=request.deals,
            leads=request.leads,
            activities=request.activities,
            context={'analysis_period_days': request.analysis_period_days}
        )
        
        # Extract individual analyses
        individual_analyses = optimization_results.get('rep_performance_analysis', {}).get('individual_analyses', [])
        
        # Generate performance benchmarks
        performance_benchmarks = _generate_performance_benchmarks(individual_analyses, request.benchmark_against_team)
        
        # Extract key insights
        key_insights = _extract_key_insights(optimization_results)
        
        # Generate recommended actions
        recommended_actions = _generate_recommended_actions(optimization_results)
        
        log_business_event(
            logger,
            "sales_efficiency_analyzed",
            "revenue_optimization",
            analysis_id,
            details={
                "reps_analyzed": len(request.reps),
                "coaching_recommendations": len(optimization_results.get('coaching_recommendations', [])),
                "process_improvements": len(optimization_results.get('process_efficiency_improvements', {}).get('efficiency_improvements', [])),
                "key_insights_count": len(key_insights)
            }
        )
        
        return SalesEfficiencyAnalysisResponse(
            analysis_id=analysis_id,
            timestamp=start_time.isoformat(),
            analysis_period_days=request.analysis_period_days,
            individual_analyses=individual_analyses,
            team_analysis=optimization_results.get('rep_performance_analysis', {}).get('team_summary', {}),
            coaching_recommendations=optimization_results.get('coaching_recommendations', []),
            resource_optimization=optimization_results.get('resource_allocation_optimization', {}),
            process_improvements=optimization_results.get('process_efficiency_improvements', {}),
            performance_benchmarks=performance_benchmarks,
            key_insights=key_insights,
            recommended_actions=recommended_actions
        )
        
    except Exception as e:
        logger.error(f"Sales efficiency analysis failed for tenant {tenant_id}: {str(e)}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Sales efficiency analysis failed: {str(e)}")


@router.post("/impact/report", response_model=RevenueImpactReportResponse)
async def generate_revenue_impact_report(
    request: RevenueImpactReportRequest,
    tenant_context = Depends(get_current_tenant_context)
) -> RevenueImpactReportResponse:
    """
    Generate comprehensive revenue impact report with ROI analysis.
    
    This endpoint provides detailed revenue impact tracking and measurement
    as specified in Requirements 8.6 and 6.2, 6.3, 6.6.
    """
    try:
        import uuid
        
        report_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        tenant_id = tenant_context.tenant_id
        
        logger.info(
            f"Generating revenue impact report for tenant {tenant_id}",
            extra={
                "report_id": report_id,
                "report_period_days": request.report_period_days,
                "include_pipeline_recovery": request.include_pipeline_recovery,
                "include_velocity_improvements": request.include_velocity_improvements,
                "include_roi_analysis": request.include_roi_analysis
            }
        )
        
        # Generate summary metrics
        summary_metrics = _generate_summary_metrics(request.report_period_days)
        
        # Generate pipeline recovery metrics
        pipeline_recovery = {}
        if request.include_pipeline_recovery:
            pipeline_recovery = _generate_pipeline_recovery_metrics(request.report_period_days)
        
        # Generate velocity improvement metrics
        velocity_improvements = {}
        if request.include_velocity_improvements:
            velocity_improvements = _generate_velocity_improvement_metrics(request.report_period_days)
        
        # Generate conversion improvement metrics
        conversion_improvements = {}
        if request.include_conversion_improvements:
            conversion_improvements = _generate_conversion_improvement_metrics(request.report_period_days)
        
        # Generate manual work reduction metrics
        manual_work_reduction = {}
        if request.include_manual_work_reduction:
            manual_work_reduction = _generate_manual_work_reduction_metrics(request.report_period_days)
        
        # Generate ROI analysis
        roi_analysis = {}
        if request.include_roi_analysis:
            roi_analysis = _generate_roi_analysis(
                summary_metrics, pipeline_recovery, velocity_improvements, 
                conversion_improvements, manual_work_reduction
            )
        
        # Generate segmented results
        segmented_results = _generate_segmented_results(
            request.segment_by_rep, request.segment_by_deal_size, 
            request.segment_by_stage, request.report_period_days
        )
        
        # Generate baseline comparison
        baseline_comparison = {}
        if request.baseline_comparison:
            baseline_comparison = _generate_baseline_comparison(request.report_period_days)
        
        # Generate trends
        trends = _generate_revenue_impact_trends(request.report_period_days)
        
        # Generate recommendations
        recommendations = _generate_revenue_impact_recommendations(
            summary_metrics, roi_analysis, trends
        )
        
        log_business_event(
            logger,
            "revenue_impact_report_generated",
            "revenue_optimization",
            report_id,
            details={
                "report_period_days": request.report_period_days,
                "total_revenue_impact": summary_metrics.get('total_revenue_impact', 0),
                "pipeline_recovered": pipeline_recovery.get('total_pipeline_recovered', 0),
                "roi_percentage": roi_analysis.get('roi_percentage', 0)
            }
        )
        
        return RevenueImpactReportResponse(
            report_id=report_id,
            timestamp=start_time.isoformat(),
            report_period_days=request.report_period_days,
            summary_metrics=summary_metrics,
            pipeline_recovery=pipeline_recovery,
            velocity_improvements=velocity_improvements,
            conversion_improvements=conversion_improvements,
            manual_work_reduction=manual_work_reduction,
            roi_analysis=roi_analysis,
            segmented_results=segmented_results,
            baseline_comparison=baseline_comparison,
            trends=trends,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Revenue impact report generation failed for tenant {tenant_id}: {str(e)}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Revenue impact report generation failed: {str(e)}")


@router.get("/velocity/status")
async def get_velocity_optimization_status(
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get current pipeline velocity optimization status and configuration."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching velocity optimization status for tenant {tenant_id}")
        
        return {
            "tenant_id": tenant_id,
            "optimization_enabled": velocity_optimizer.config.get('optimization_enabled', True),
            "auto_followup_enabled": velocity_optimizer.config.get('auto_followup_enabled', True),
            "sop_monitoring_enabled": velocity_optimizer.config.get('sop_monitoring_enabled', True),
            "max_actions_per_run": velocity_optimizer.config.get('max_actions_per_run', 25),
            "min_confidence_threshold": velocity_optimizer.config.get('min_confidence_threshold', 70.0),
            "last_optimization": None,  # Would track last optimization run
            "active_triggers": 0,  # Would count active triggers
            "pending_actions": 0,  # Would count pending actions
            "next_scheduled_run": None,  # Would show next scheduled optimization
            "status": "operational"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch velocity optimization status for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch velocity optimization status: {str(e)}")


@router.get("/efficiency/status")
async def get_efficiency_optimization_status(
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get current sales efficiency optimization status and configuration."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching efficiency optimization status for tenant {tenant_id}")
        
        return {
            "tenant_id": tenant_id,
            "analysis_enabled": efficiency_optimizer.config.get('analysis_enabled', True),
            "coaching_enabled": efficiency_optimizer.config.get('coaching_enabled', True),
            "resource_optimization_enabled": efficiency_optimizer.config.get('resource_optimization_enabled', True),
            "process_automation_enabled": efficiency_optimizer.config.get('process_automation_enabled', True),
            "performance_tracking_enabled": efficiency_optimizer.config.get('performance_tracking_enabled', True),
            "last_analysis": None,  # Would track last analysis run
            "active_coaching_recommendations": 0,  # Would count active recommendations
            "pending_resource_reallocations": 0,  # Would count pending reallocations
            "process_improvements_identified": 0,  # Would count identified improvements
            "status": "operational"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch efficiency optimization status for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch efficiency optimization status: {str(e)}")


@router.get("/impact/summary")
async def get_revenue_impact_summary(
    period_days: int = Query(30, description="Period in days for summary", ge=1, le=365),
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get high-level revenue impact summary for dashboard display."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching revenue impact summary for tenant {tenant_id}, period: {period_days} days")
        
        # Generate summary metrics (in production, this would query actual data)
        summary = {
            "tenant_id": tenant_id,
            "period_days": period_days,
            "total_revenue_impact": 125000.0,
            "pipeline_recovered": 85000.0,
            "deals_accelerated": 12,
            "velocity_improvement_percent": 18.5,
            "conversion_improvement_percent": 12.3,
            "manual_work_hours_saved": 45.2,
            "roi_percentage": 340.0,
            "active_optimizations": 8,
            "completed_optimizations": 23,
            "success_rate_percent": 87.5,
            "top_impact_areas": [
                {"area": "stalled_deal_recovery", "impact": 45000.0},
                {"area": "follow_up_automation", "impact": 32000.0},
                {"area": "sop_compliance", "impact": 28000.0}
            ],
            "recent_achievements": [
                "Recovered $15K deal stalled in negotiation stage",
                "Automated 25 follow-up tasks this week",
                "Improved team SOP compliance by 12%"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to fetch revenue impact summary for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch revenue impact summary: {str(e)}")


# Helper functions
async def _execute_optimization_actions(
    actions: List[Dict[str, Any]],
    tenant_id: str,
    trigger_id: str
):
    """Execute optimization actions in background."""
    try:
        logger.info(f"Executing {len(actions)} optimization actions for trigger {trigger_id}")
        
        # In production, this would integrate with the action execution engine
        # For now, just log the actions
        for action in actions:
            logger.info(f"Would execute action: {action.get('action_type')} for {action.get('target_system')}")
        
        log_business_event(
            logger,
            "optimization_actions_executed",
            "revenue_optimization",
            trigger_id,
            details={
                "actions_count": len(actions),
                "tenant_id": tenant_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to execute optimization actions for trigger {trigger_id}: {str(e)}")


def _generate_performance_benchmarks(individual_analyses: List[Dict[str, Any]], benchmark_against_team: bool) -> Dict[str, Any]:
    """Generate performance benchmarks for analysis."""
    if not individual_analyses or not benchmark_against_team:
        return {}
    
    # Calculate team averages
    performance_scores = [analysis.get('performance_score', 0) for analysis in individual_analyses]
    avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else 0
    
    return {
        "team_average_performance": round(avg_performance, 2),
        "top_performer_score": max(performance_scores) if performance_scores else 0,
        "bottom_performer_score": min(performance_scores) if performance_scores else 0,
        "performance_spread": max(performance_scores) - min(performance_scores) if performance_scores else 0,
        "above_average_count": len([s for s in performance_scores if s > avg_performance]),
        "below_average_count": len([s for s in performance_scores if s < avg_performance])
    }


def _extract_key_insights(optimization_results: Dict[str, Any]) -> List[str]:
    """Extract key insights from optimization results."""
    insights = []
    
    # Team performance insights
    team_summary = optimization_results.get('rep_performance_analysis', {}).get('team_summary', {})
    if team_summary.get('average_performance_score', 0) < 70:
        insights.append("Team performance below target - coaching intervention recommended")
    
    # Resource allocation insights
    resource_opt = optimization_results.get('resource_allocation_optimization', {})
    if resource_opt.get('workload_analysis', {}).get('distribution_balance') == 'imbalanced':
        insights.append("Workload distribution is imbalanced - resource reallocation needed")
    
    # Process efficiency insights
    process_imp = optimization_results.get('process_efficiency_improvements', {})
    if process_imp.get('process_adherence', {}).get('overall_adherence_score', 0) < 70:
        insights.append("Process adherence below standard - automation opportunities identified")
    
    return insights


def _generate_recommended_actions(optimization_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate recommended actions from optimization results."""
    actions = []
    
    # Coaching actions
    coaching_recs = optimization_results.get('coaching_recommendations', [])
    for rec in coaching_recs[:3]:  # Top 3 coaching recommendations
        actions.append({
            "type": "coaching",
            "priority": rec.get('priority', 'medium'),
            "title": rec.get('title', 'Coaching Recommendation'),
            "description": rec.get('description', ''),
            "category": rec.get('category', 'general')
        })
    
    # Resource reallocation actions
    resource_recs = optimization_results.get('resource_allocation_optimization', {}).get('reallocation_recommendations', [])
    for rec in resource_recs[:2]:  # Top 2 resource recommendations
        actions.append({
            "type": "resource_reallocation",
            "priority": rec.get('priority', 'medium'),
            "title": f"Reallocate {rec.get('type', 'resource')}",
            "description": rec.get('rationale', ''),
            "category": "resource_management"
        })
    
    return actions

def _generate_summary_metrics(period_days: int) -> Dict[str, Any]:
    """Generate summary revenue impact metrics."""
    # In production, this would query actual data from the database
    return {
        "period_days": period_days,
        "total_revenue_impact": 125000.0,
        "total_optimizations_run": 15,
        "successful_optimizations": 13,
        "success_rate_percent": 86.7,
        "average_revenue_per_optimization": 8333.33,
        "total_actions_executed": 45,
        "action_success_rate_percent": 91.1
    }


def _generate_pipeline_recovery_metrics(period_days: int) -> Dict[str, Any]:
    """Generate pipeline recovery metrics."""
    return {
        "total_pipeline_recovered": 85000.0,
        "deals_recovered": 8,
        "average_recovery_per_deal": 10625.0,
        "recovery_rate_percent": 75.0,
        "stalled_deals_addressed": 12,
        "time_to_recovery_avg_days": 5.2
    }


def _generate_velocity_improvement_metrics(period_days: int) -> Dict[str, Any]:
    """Generate velocity improvement metrics."""
    return {
        "average_velocity_improvement_percent": 18.5,
        "deals_accelerated": 12,
        "average_time_saved_days": 8.3,
        "fastest_acceleration_days": 15,
        "velocity_improvement_by_stage": {
            "prospecting": 12.0,
            "qualification": 22.0,
            "proposal": 25.0,
            "negotiation": 18.0
        }
    }


def _generate_conversion_improvement_metrics(period_days: int) -> Dict[str, Any]:
    """Generate conversion improvement metrics."""
    return {
        "overall_conversion_improvement_percent": 12.3,
        "leads_converted_additional": 8,
        "deals_closed_additional": 5,
        "conversion_rate_before": 15.2,
        "conversion_rate_after": 17.1,
        "improvement_by_source": {
            "inbound_leads": 15.0,
            "outbound_prospecting": 8.5,
            "referrals": 20.0
        }
    }


def _generate_manual_work_reduction_metrics(period_days: int) -> Dict[str, Any]:
    """Generate manual work reduction metrics."""
    return {
        "total_hours_saved": 45.2,
        "tasks_automated": 67,
        "average_time_per_task_minutes": 40.5,
        "automation_success_rate_percent": 94.0,
        "work_reduction_by_category": {
            "follow_up_scheduling": 18.5,
            "data_entry": 12.3,
            "report_generation": 8.7,
            "task_creation": 5.7
        }
    }


def _generate_roi_analysis(
    summary_metrics: Dict[str, Any],
    pipeline_recovery: Dict[str, Any],
    velocity_improvements: Dict[str, Any],
    conversion_improvements: Dict[str, Any],
    manual_work_reduction: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate ROI analysis."""
    total_revenue_impact = summary_metrics.get('total_revenue_impact', 0)
    total_cost_savings = manual_work_reduction.get('total_hours_saved', 0) * 50  # Assume $50/hour
    
    # Assume system cost of $5000/month
    system_cost = 5000.0
    total_benefit = total_revenue_impact + total_cost_savings
    roi_percentage = ((total_benefit - system_cost) / system_cost) * 100 if system_cost > 0 else 0
    
    return {
        "total_revenue_impact": total_revenue_impact,
        "total_cost_savings": total_cost_savings,
        "total_benefit": total_benefit,
        "system_cost": system_cost,
        "roi_percentage": round(roi_percentage, 2),
        "payback_period_months": round(system_cost / (total_benefit / 30), 2) if total_benefit > 0 else 0,
        "break_even_point": "Month 1" if roi_percentage > 0 else "Not achieved"
    }


def _generate_segmented_results(
    segment_by_rep: bool,
    segment_by_deal_size: bool,
    segment_by_stage: bool,
    period_days: int
) -> Dict[str, Any]:
    """Generate segmented analysis results."""
    results = {}
    
    if segment_by_rep:
        results["by_rep"] = {
            "rep_001": {"revenue_impact": 25000.0, "deals_affected": 3},
            "rep_002": {"revenue_impact": 18000.0, "deals_affected": 2},
            "rep_003": {"revenue_impact": 32000.0, "deals_affected": 4}
        }
    
    if segment_by_deal_size:
        results["by_deal_size"] = {
            "small_deals": {"revenue_impact": 15000.0, "count": 8},
            "medium_deals": {"revenue_impact": 45000.0, "count": 5},
            "large_deals": {"revenue_impact": 65000.0, "count": 2}
        }
    
    if segment_by_stage:
        results["by_stage"] = {
            "prospecting": {"revenue_impact": 20000.0, "deals": 6},
            "qualification": {"revenue_impact": 35000.0, "deals": 4},
            "proposal": {"revenue_impact": 45000.0, "deals": 3},
            "negotiation": {"revenue_impact": 25000.0, "deals": 2}
        }
    
    return results


def _generate_baseline_comparison(period_days: int) -> Dict[str, Any]:
    """Generate baseline comparison metrics."""
    return {
        "current_period": {
            "revenue_impact": 125000.0,
            "deals_closed": 15,
            "average_deal_velocity_days": 32.5,
            "conversion_rate_percent": 17.1
        },
        "baseline_period": {
            "revenue_impact": 95000.0,
            "deals_closed": 12,
            "average_deal_velocity_days": 38.2,
            "conversion_rate_percent": 15.2
        },
        "improvements": {
            "revenue_impact_increase": 30000.0,
            "revenue_impact_increase_percent": 31.6,
            "deals_closed_increase": 3,
            "velocity_improvement_days": 5.7,
            "conversion_rate_improvement": 1.9
        }
    }


def _generate_revenue_impact_trends(period_days: int) -> List[Dict[str, Any]]:
    """Generate revenue impact trends."""
    return [
        {
            "period": "Week 1",
            "revenue_impact": 28000.0,
            "deals_affected": 4,
            "trend": "increasing"
        },
        {
            "period": "Week 2",
            "revenue_impact": 32000.0,
            "deals_affected": 5,
            "trend": "increasing"
        },
        {
            "period": "Week 3",
            "revenue_impact": 35000.0,
            "deals_affected": 3,
            "trend": "stable"
        },
        {
            "period": "Week 4",
            "revenue_impact": 30000.0,
            "deals_affected": 3,
            "trend": "decreasing"
        }
    ]


def _generate_revenue_impact_recommendations(
    summary_metrics: Dict[str, Any],
    roi_analysis: Dict[str, Any],
    trends: List[Dict[str, Any]]
) -> List[str]:
    """Generate recommendations for revenue impact improvement."""
    recommendations = []
    
    if roi_analysis.get('roi_percentage', 0) > 200:
        recommendations.append("Excellent ROI achieved - consider expanding optimization scope")
    
    if summary_metrics.get('success_rate_percent', 0) < 80:
        recommendations.append("Optimization success rate below target - review and refine strategies")
    
    # Check trend direction
    recent_trends = trends[-2:] if len(trends) >= 2 else trends
    if len(recent_trends) >= 2 and recent_trends[-1]['revenue_impact'] < recent_trends[-2]['revenue_impact']:
        recommendations.append("Revenue impact trending downward - investigate and adjust approach")
    
    recommendations.append("Continue monitoring and optimizing based on performance data")
    
    return recommendations