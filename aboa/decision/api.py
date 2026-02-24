"""
Revenue Decision API endpoints.

This module provides FastAPI endpoints for revenue intelligence, pipeline risk
detection, and pipeline velocity optimization functionality.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..core.auth import get_current_tenant_context
from ..core.logging import get_logger
from ..models.enums import RiskType, Severity
from ..models.revenue_entities import Deal, Lead, SalesActivity, SalesRep, PipelineRisk
from .pipeline_risk_detector import PipelineRiskDetector
from .revenue_decision_engine import RevenueDecisionEngine
from .pipeline_velocity_optimizer import PipelineVelocityOptimizer
from .sales_process_efficiency_optimizer import SalesProcessEfficiencyOptimizer

logger = get_logger(__name__)

router = APIRouter(prefix="/decision", tags=["Revenue Decision"])


# Request/Response Models
class PipelineAnalysisRequest(BaseModel):
    """Request model for pipeline analysis."""
    deals: List[Deal] = Field(..., description="List of deals to analyze")
    leads: List[Lead] = Field(default_factory=list, description="List of leads to analyze")
    activities: List[SalesActivity] = Field(default_factory=list, description="List of sales activities")
    reps: List[SalesRep] = Field(default_factory=list, description="List of sales representatives")


class PipelineRiskResponse(BaseModel):
    """Response model for pipeline risk detection."""
    risks: List[PipelineRisk] = Field(..., description="Detected pipeline risks")
    total_risks: int = Field(..., description="Total number of risks detected")
    risk_distribution: Dict[str, int] = Field(..., description="Distribution of risks by type")
    severity_distribution: Dict[str, int] = Field(..., description="Distribution of risks by severity")


class VelocityOptimizationRequest(BaseModel):
    """Request model for pipeline velocity optimization."""
    deals: List[Deal] = Field(..., description="List of deals to optimize")
    leads: List[Lead] = Field(default_factory=list, description="List of leads to optimize")
    activities: List[SalesActivity] = Field(default_factory=list, description="List of sales activities")
    reps: List[SalesRep] = Field(default_factory=list, description="List of sales representatives")
    enable_auto_followup: bool = Field(True, description="Enable automated follow-up scheduling")
    enable_sop_monitoring: bool = Field(True, description="Enable SOP compliance monitoring")
    max_actions: int = Field(50, description="Maximum number of actions to return", ge=1, le=100)


class VelocityOptimizationResponse(BaseModel):
    """Response model for pipeline velocity optimization."""
    status: str = Field(..., description="Optimization status")
    timestamp: str = Field(..., description="Optimization timestamp")
    pipeline_risks: List[Dict[str, Any]] = Field(..., description="Detected pipeline risks")
    sop_violations: List[Dict[str, Any]] = Field(..., description="SOP compliance violations")
    followup_actions: List[Dict[str, Any]] = Field(..., description="Automated follow-up actions")
    prioritized_interventions: List[Dict[str, Any]] = Field(..., description="Prioritized interventions")
    compliance_scores: Dict[str, float] = Field(..., description="Compliance scores by entity")
    summary: Dict[str, Any] = Field(..., description="Optimization summary statistics")


class SalesEfficiencyRequest(BaseModel):
    """Request model for sales process efficiency optimization."""
    reps: List[SalesRep] = Field(..., description="List of sales representatives")
    deals: List[Deal] = Field(..., description="List of deals")
    leads: List[Lead] = Field(default_factory=list, description="List of leads")
    activities: List[SalesActivity] = Field(default_factory=list, description="List of sales activities")
    analysis_period_days: int = Field(30, description="Analysis period in days", ge=1, le=365)
    include_coaching: bool = Field(True, description="Include coaching recommendations")
    include_resource_optimization: bool = Field(True, description="Include resource allocation optimization")
    include_process_improvements: bool = Field(True, description="Include process efficiency improvements")


class SalesEfficiencyResponse(BaseModel):
    """Response model for sales process efficiency optimization."""
    status: str = Field(..., description="Optimization status")
    timestamp: str = Field(..., description="Optimization timestamp")
    rep_performance_analysis: Dict[str, Any] = Field(..., description="Rep performance analysis results")
    resource_allocation_optimization: Dict[str, Any] = Field(..., description="Resource allocation optimization")
    process_efficiency_improvements: Dict[str, Any] = Field(..., description="Process efficiency improvements")
    coaching_recommendations: List[Dict[str, Any]] = Field(..., description="Coaching recommendations")
    performance_tracking: Dict[str, Any] = Field(..., description="Performance tracking metrics")
    summary: Dict[str, Any] = Field(..., description="Optimization summary")


# Initialize components
risk_detector = PipelineRiskDetector()
decision_engine = RevenueDecisionEngine()
velocity_optimizer = PipelineVelocityOptimizer(
    risk_detector=risk_detector,
    decision_engine=decision_engine
)
efficiency_optimizer = SalesProcessEfficiencyOptimizer()


@router.post("/analyze-pipeline-risks", response_model=PipelineRiskResponse)
async def analyze_pipeline_risks(
    request: PipelineAnalysisRequest,
    tenant_context = Depends(get_current_tenant_context)
) -> PipelineRiskResponse:
    """
    Analyze pipeline data to detect revenue risks.
    
    This endpoint analyzes deals, leads, and activities to identify:
    - Stalled deals beyond stage thresholds
    - Meetings without scheduled follow-ups
    - High-value opportunities with no recent activity
    - Leads with insufficient touchpoints
    """
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Analyzing pipeline risks for tenant {tenant_id}")
        
        # Detect pipeline risks
        risks = risk_detector.detect_pipeline_risks(
            deals=request.deals,
            leads=request.leads,
            activities=request.activities,
            reps=request.reps
        )
        
        # Calculate distributions
        risk_distribution = {}
        severity_distribution = {}
        
        for risk in risks:
            # Risk type distribution
            risk_type = risk.risk_type.value
            risk_distribution[risk_type] = risk_distribution.get(risk_type, 0) + 1
            
            # Severity distribution
            severity = risk.severity.value
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        logger.info(f"Detected {len(risks)} pipeline risks for tenant {tenant_id}")
        
        return PipelineRiskResponse(
            risks=risks,
            total_risks=len(risks),
            risk_distribution=risk_distribution,
            severity_distribution=severity_distribution
        )
        
    except Exception as e:
        logger.error(f"Pipeline risk analysis failed for tenant {tenant_id}: {str(e)}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Pipeline risk analysis failed: {str(e)}")


@router.post("/optimize-pipeline-velocity", response_model=VelocityOptimizationResponse)
async def optimize_pipeline_velocity(
    request: VelocityOptimizationRequest,
    tenant_context = Depends(get_current_tenant_context)
) -> VelocityOptimizationResponse:
    """
    Perform comprehensive pipeline velocity optimization.
    
    This endpoint provides:
    - Automated follow-up scheduling for stalled deals
    - Revenue impact prioritization algorithms
    - Pipeline risk detection and intervention
    - SOP compliance monitoring and enforcement
    
    Implements Requirements 8.1, 8.2, 8.4.
    """
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Optimizing pipeline velocity for tenant {tenant_id}")
        
        # Configure optimizer based on request
        config = {
            'optimization_enabled': True,
            'auto_followup_enabled': request.enable_auto_followup,
            'sop_monitoring_enabled': request.enable_sop_monitoring,
            'max_actions_per_run': request.max_actions,
            'min_confidence_threshold': 70.0,
            'batch_processing': True
        }
        
        # Update optimizer configuration
        velocity_optimizer.config.update(config)
        
        # Perform optimization
        optimization_results = velocity_optimizer.optimize_pipeline_velocity(
            deals=request.deals,
            leads=request.leads,
            activities=request.activities,
            reps=request.reps,
            context=None  # Could be enhanced to accept context
        )
        
        logger.info(f"Pipeline velocity optimization completed for tenant {tenant_id}")
        
        return VelocityOptimizationResponse(**optimization_results)
        
    except Exception as e:
        logger.error(f"Pipeline velocity optimization failed for tenant {tenant_id}: {str(e)}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Pipeline velocity optimization failed: {str(e)}")


@router.get("/pipeline-risks/{risk_id}")
async def get_pipeline_risk(
    risk_id: str,
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get details for a specific pipeline risk."""
    try:
        tenant_id = tenant_context.tenant_id
        # In a real implementation, this would fetch from a database
        # For now, return a placeholder response
        logger.info(f"Fetching pipeline risk {risk_id} for tenant {tenant_id}")
        
        return {
            "risk_id": risk_id,
            "status": "active",
            "message": "Risk details would be fetched from database"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch pipeline risk {risk_id} for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pipeline risk: {str(e)}")


@router.get("/compliance-score")
async def get_compliance_score(
    deal_id: Optional[str] = Query(None, description="Deal ID to score"),
    lead_id: Optional[str] = Query(None, description="Lead ID to score"),
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """
    Get SOP compliance score for a deal or lead.
    
    Returns compliance scores across different dimensions:
    - Activity compliance
    - Timing compliance  
    - Process compliance
    - Documentation compliance
    """
    try:
        tenant_id = tenant_context.tenant_id
        if not deal_id and not lead_id:
            raise HTTPException(status_code=400, detail="Either deal_id or lead_id must be provided")
        
        logger.info(f"Calculating compliance score for tenant {tenant_id}")
        
        # In a real implementation, this would:
        # 1. Fetch the deal/lead from database
        # 2. Fetch associated activities
        # 3. Calculate compliance score using SOPComplianceMonitor
        
        # Placeholder response
        compliance_score = 85.5  # Would be calculated by SOPComplianceMonitor
        
        return {
            "entity_id": deal_id or lead_id,
            "entity_type": "deal" if deal_id else "lead",
            "overall_compliance_score": compliance_score,
            "detailed_scores": {
                "activity_compliance": 90.0,
                "timing_compliance": 85.0,
                "process_compliance": 80.0,
                "documentation_compliance": 87.0
            },
            "recommendations": [
                "Schedule next action for deal progression",
                "Complete missing activity documentation"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate compliance score for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate compliance score: {str(e)}")


@router.get("/optimization-status")
async def get_optimization_status(
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get current pipeline velocity optimization status and configuration."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching optimization status for tenant {tenant_id}")
        
        return {
            "tenant_id": tenant_id,
            "optimization_enabled": velocity_optimizer.config.get('optimization_enabled', True),
            "auto_followup_enabled": velocity_optimizer.config.get('auto_followup_enabled', True),
            "sop_monitoring_enabled": velocity_optimizer.config.get('sop_monitoring_enabled', True),
            "max_actions_per_run": velocity_optimizer.config.get('max_actions_per_run', 50),
            "last_optimization": None,  # Would track last optimization run
            "active_risks": 0,  # Would count active risks
            "pending_actions": 0  # Would count pending actions
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch optimization status for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch optimization status: {str(e)}")


@router.post("/configure-optimization")
async def configure_optimization(
    config: Dict[str, Any],
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Configure pipeline velocity optimization settings."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Configuring optimization for tenant {tenant_id}")
        
        # Validate and update configuration
        allowed_keys = {
            'optimization_enabled', 'auto_followup_enabled', 'sop_monitoring_enabled',
            'max_actions_per_run', 'min_confidence_threshold'
        }
        
        filtered_config = {k: v for k, v in config.items() if k in allowed_keys}
        velocity_optimizer.config.update(filtered_config)
        
        logger.info(f"Updated optimization configuration for tenant {tenant_id}")
        
        return {
            "status": "success",
            "message": "Optimization configuration updated",
            "updated_config": filtered_config
        }
        
    except Exception as e:
        logger.error(f"Failed to configure optimization for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to configure optimization: {str(e)}")


@router.post("/optimize-sales-efficiency", response_model=SalesEfficiencyResponse)
async def optimize_sales_efficiency(
    request: SalesEfficiencyRequest,
    tenant_context = Depends(get_current_tenant_context)
) -> SalesEfficiencyResponse:
    """
    Perform comprehensive sales process efficiency optimization.
    
    This endpoint provides:
    - Rep performance analysis and coaching recommendations
    - Sales resource allocation optimization algorithms
    - Process efficiency improvement automation
    - Sales performance tracking
    
    Implements Requirements 8.3, 8.5, 8.7.
    """
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Optimizing sales process efficiency for tenant {tenant_id}")
        
        # Configure optimizer based on request
        efficiency_optimizer.config.update({
            'analysis_enabled': True,
            'coaching_enabled': request.include_coaching,
            'resource_optimization_enabled': request.include_resource_optimization,
            'process_automation_enabled': request.include_process_improvements,
            'performance_tracking_enabled': True
        })
        
        # Perform optimization
        optimization_results = efficiency_optimizer.optimize_sales_process_efficiency(
            reps=request.reps,
            deals=request.deals,
            leads=request.leads,
            activities=request.activities,
            context={'analysis_period_days': request.analysis_period_days}
        )
        
        logger.info(f"Sales process efficiency optimization completed for tenant {tenant_id}")
        
        return SalesEfficiencyResponse(**optimization_results)
        
    except Exception as e:
        logger.error(f"Sales process efficiency optimization failed for tenant {tenant_id}: {str(e)}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Sales process efficiency optimization failed: {str(e)}")


@router.get("/rep-performance/{rep_id}")
async def get_rep_performance(
    rep_id: str,
    analysis_period_days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get detailed performance analysis for a specific sales rep."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching rep performance for {rep_id}, tenant {tenant_id}")
        
        # In a real implementation, this would:
        # 1. Fetch rep data from database
        # 2. Fetch associated deals, leads, and activities
        # 3. Run performance analysis
        
        # Placeholder response
        return {
            "rep_id": rep_id,
            "analysis_period_days": analysis_period_days,
            "performance_score": 75.5,
            "coaching_recommendations": [
                {
                    "category": "activity_management",
                    "priority": "high",
                    "title": "Increase Sales Activity Volume",
                    "description": "Current activity level below target"
                }
            ],
            "improvement_areas": ["activity_volume", "conversion_optimization"],
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch rep performance for {rep_id}, tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch rep performance: {str(e)}")


@router.get("/team-performance-summary")
async def get_team_performance_summary(
    analysis_period_days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get team-level performance summary and insights."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching team performance summary for tenant {tenant_id}")
        
        # In a real implementation, this would:
        # 1. Fetch all reps and their data
        # 2. Run team-level analysis
        # 3. Generate summary insights
        
        # Placeholder response
        return {
            "tenant_id": tenant_id,
            "analysis_period_days": analysis_period_days,
            "team_size": 5,
            "average_performance_score": 72.3,
            "performance_distribution": {
                "high_performers": 2,
                "average_performers": 2,
                "low_performers": 1
            },
            "top_improvement_areas": [
                {"area": "activity_volume", "affected_reps": 3},
                {"area": "conversion_optimization", "affected_reps": 2}
            ],
            "total_coaching_recommendations": 12,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch team performance summary for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch team performance summary: {str(e)}")


@router.get("/resource-allocation-status")
async def get_resource_allocation_status(
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get current resource allocation status and recommendations."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching resource allocation status for tenant {tenant_id}")
        
        # In a real implementation, this would:
        # 1. Analyze current workload distribution
        # 2. Identify capacity constraints
        # 3. Generate reallocation recommendations
        
        # Placeholder response
        return {
            "tenant_id": tenant_id,
            "workload_distribution": "imbalanced",
            "overloaded_reps": 2,
            "underloaded_reps": 1,
            "pending_reallocations": 3,
            "expected_impact": {
                "deals_reallocated": 5,
                "expected_revenue_impact": 125000.0
            },
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch resource allocation status for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch resource allocation status: {str(e)}")


@router.get("/process-efficiency-status")
async def get_process_efficiency_status(
    tenant_context = Depends(get_current_tenant_context)
) -> Dict[str, Any]:
    """Get current process efficiency status and improvement opportunities."""
    try:
        tenant_id = tenant_context.tenant_id
        logger.info(f"Fetching process efficiency status for tenant {tenant_id}")
        
        # In a real implementation, this would:
        # 1. Analyze process adherence
        # 2. Identify automation opportunities
        # 3. Generate improvement recommendations
        
        # Placeholder response
        return {
            "tenant_id": tenant_id,
            "overall_adherence_score": 68.5,
            "next_action_scheduling_rate": 75.2,
            "stage_duration_violations": 8,
            "activity_frequency_violations": 12,
            "automation_opportunities": 4,
            "high_priority_improvements": 3,
            "potential_revenue_impact": 85000.0,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch process efficiency status for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch process efficiency status: {str(e)}")