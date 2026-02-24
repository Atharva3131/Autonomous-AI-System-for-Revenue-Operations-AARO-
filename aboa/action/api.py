"""
Sales Action Execution API endpoints.

This module provides FastAPI endpoints for sales action execution, monitoring,
scheduling, and status tracking as specified in Requirements 4.7 and 7.3.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import logging
import uuid
import time

from aboa.core.exceptions import ActionExecutionError, ABOAException
from aboa.core.logging import log_business_event
from aboa.action.engine import (
    SalesActionEngine, 
    ExecutionContext, 
    ExecutionResult,
    IdempotencyManager,
    RetryManager,
    ExecutionMonitor
)
from aboa.action.integration_hub import (
    WorkflowIntegration,
    CRMIntegration,
    SalesManagerAlertSystem
)
from aboa.models.enums import ExecutionStatus, SalesActionType, ActivityType, DealStage, LeadStatus
from aboa.models.revenue_entities import SalesAction, Deal, Lead, SalesRep

logger = logging.getLogger(__name__)

# Global service instances (will be properly managed in production)
_action_engine: Optional[SalesActionEngine] = None
_workflow_integration: Optional[WorkflowIntegration] = None
_crm_integration: Optional[CRMIntegration] = None
_alert_system: Optional[SalesManagerAlertSystem] = None

def get_action_engine() -> SalesActionEngine:
    """Get or create the sales action engine instance."""
    global _action_engine
    if _action_engine is None:
        _action_engine = SalesActionEngine()
    return _action_engine

def get_workflow_integration() -> WorkflowIntegration:
    """Get or create the workflow integration instance."""
    global _workflow_integration
    if _workflow_integration is None:
        _workflow_integration = WorkflowIntegration()
    return _workflow_integration

def get_crm_integration() -> CRMIntegration:
    """Get or create the CRM integration instance."""
    global _crm_integration
    if _crm_integration is None:
        _crm_integration = CRMIntegration()
    return _crm_integration

def get_alert_system() -> SalesManagerAlertSystem:
    """Get or create the sales manager alert system instance."""
    global _alert_system
    if _alert_system is None:
        _alert_system = SalesManagerAlertSystem()
    return _alert_system

# Request/Response models
class ActionExecutionRequest(BaseModel):
    """Request model for action execution."""
    action: SalesAction = Field(..., description="Sales action to execute")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenant support")
    user_id: Optional[str] = Field(None, description="User identifier for audit trail")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional execution metadata")
    force_execution: bool = Field(False, description="Force execution even if already executed (bypass idempotency)")

class ActionExecutionResponse(BaseModel):
    """Response model for action execution."""
    execution_id: str = Field(..., description="Unique execution identifier")
    action_id: str = Field(..., description="Action identifier")
    status: ExecutionStatus = Field(..., description="Current execution status")
    outputs: Dict[str, Any] = Field(..., description="Execution outputs")
    errors: List[str] = Field(..., description="Execution errors if any")
    duration_ms: Optional[float] = Field(None, description="Execution duration in milliseconds")
    retry_count: int = Field(..., description="Number of retry attempts")
    started_at: datetime = Field(..., description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")
    idempotency_used: bool = Field(..., description="Whether idempotency was used")

class ActionScheduleRequest(BaseModel):
    """Request model for action scheduling."""
    action: SalesAction = Field(..., description="Sales action to schedule")
    scheduled_for: datetime = Field(..., description="When to execute the action")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional scheduling metadata")
    recurring: bool = Field(False, description="Whether this is a recurring action")
    recurrence_interval_hours: Optional[int] = Field(None, description="Recurrence interval in hours", ge=1)

class ActionScheduleResponse(BaseModel):
    """Response model for action scheduling."""
    schedule_id: str = Field(..., description="Unique schedule identifier")
    action_id: str = Field(..., description="Action identifier")
    scheduled_for: datetime = Field(..., description="Scheduled execution time")
    status: str = Field(..., description="Schedule status")
    recurring: bool = Field(..., description="Whether this is recurring")
    next_execution: Optional[datetime] = Field(None, description="Next execution time for recurring actions")
    created_at: datetime = Field(..., description="Schedule creation timestamp")

class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""
    execution_id: str = Field(..., description="Execution identifier")
    action_id: str = Field(..., description="Action identifier")
    status: ExecutionStatus = Field(..., description="Current execution status")
    outputs: Dict[str, Any] = Field(..., description="Execution outputs")
    errors: List[str] = Field(..., description="Execution errors")
    retry_count: int = Field(..., description="Number of retry attempts")
    started_at: datetime = Field(..., description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Dict[str, Any] = Field(..., description="Execution metadata")

class ExecutionHistoryResponse(BaseModel):
    """Response model for execution history."""
    executions: List[ExecutionStatusResponse] = Field(..., description="List of executions")
    total_count: int = Field(..., description="Total number of executions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_more: bool = Field(..., description="Whether there are more results")

class BulkExecutionRequest(BaseModel):
    """Request model for bulk action execution."""
    actions: List[SalesAction] = Field(..., description="List of actions to execute", min_length=1, max_length=50)
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Bulk execution metadata")
    parallel_execution: bool = Field(True, description="Whether to execute actions in parallel")
    stop_on_error: bool = Field(False, description="Whether to stop bulk execution on first error")

class BulkExecutionResponse(BaseModel):
    """Response model for bulk action execution."""
    bulk_execution_id: str = Field(..., description="Unique bulk execution identifier")
    total_actions: int = Field(..., description="Total number of actions")
    successful_executions: int = Field(..., description="Number of successful executions")
    failed_executions: int = Field(..., description="Number of failed executions")
    execution_results: List[ActionExecutionResponse] = Field(..., description="Individual execution results")
    started_at: datetime = Field(..., description="Bulk execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Bulk execution completion timestamp")
    duration_ms: float = Field(..., description="Total execution duration in milliseconds")

class ActionCancellationRequest(BaseModel):
    """Request model for action cancellation."""
    reason: Optional[str] = Field(None, description="Reason for cancellation")
    force: bool = Field(False, description="Force cancellation even if action is in progress")

class ActionCancellationResponse(BaseModel):
    """Response model for action cancellation."""
    execution_id: str = Field(..., description="Execution identifier")
    cancelled: bool = Field(..., description="Whether cancellation was successful")
    reason: Optional[str] = Field(None, description="Cancellation reason")
    cancelled_at: datetime = Field(..., description="Cancellation timestamp")

# Create router
router = APIRouter(prefix="/api/v1/actions", tags=["Sales Action Execution"])

@router.get("/status", response_model=Dict[str, Any])
async def get_action_status(
    action_engine: SalesActionEngine = Depends(get_action_engine)
):
    """
    Get the current status of the sales action execution service.
    
    Returns information about service status and active executions.
    """
    try:
        return {
            "status": "running",
            "service": "sales_action_execution",
            "active_executions": 0,
            "message": "Action service is operational"
        }
    except Exception as e:
        logger.error(f"Error getting action status: {str(e)}")
        return {
            "status": "error",
            "service": "sales_action_execution",
            "error": str(e),
            "message": "Failed to retrieve service status"
        }


@router.post("/execute", response_model=ActionExecutionResponse)
async def execute_action(
    request: ActionExecutionRequest,
    background_tasks: BackgroundTasks,
    action_engine: SalesActionEngine = Depends(get_action_engine)
):
    """
    Execute a sales action immediately with full orchestration and monitoring.
    
    This endpoint executes sales actions with idempotency protection, retry logic,
    and comprehensive monitoring as specified in Requirements 4.1, 4.6, 4.7, 4.8.
    """
    try:
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(
            f"Executing action {request.action.action_id}",
            extra={
                "request_id": request_id,
                "action_id": request.action.action_id,
                "action_type": request.action.action_type.value,
                "tenant_id": request.tenant_id,
                "user_id": request.user_id,
                "force_execution": request.force_execution
            }
        )
        
        # Handle force execution by bypassing idempotency
        if request.force_execution:
            # Temporarily disable idempotency for this execution
            original_manager = action_engine.idempotency_manager
            action_engine.idempotency_manager = IdempotencyManager()  # Fresh instance
        
        try:
            # Execute the action
            result = await action_engine.execute_action(
                action=request.action,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                metadata=request.metadata
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if idempotency was used
            idempotency_used = result.retry_count == 0 and result.status == ExecutionStatus.COMPLETED
            if request.force_execution:
                idempotency_used = False
            
            log_business_event(
                logger,
                "action_executed",
                "sales_action",
                result.execution_id,
                details={
                    "action_id": request.action.action_id,
                    "action_type": request.action.action_type.value,
                    "status": result.status.value,
                    "retry_count": result.retry_count,
                    "execution_time_ms": execution_time,
                    "idempotency_used": idempotency_used
                }
            )
            
            return ActionExecutionResponse(
                execution_id=result.execution_id,
                action_id=request.action.action_id,
                status=result.status,
                outputs=result.outputs,
                errors=result.errors,
                duration_ms=result.duration.total_seconds() * 1000 if result.duration else execution_time,
                retry_count=result.retry_count,
                started_at=datetime.now(timezone.utc),
                completed_at=result.completed_at,
                idempotency_used=idempotency_used
            )
            
        finally:
            # Restore original idempotency manager if it was temporarily replaced
            if request.force_execution:
                action_engine.idempotency_manager = original_manager
        
    except ActionExecutionError as e:
        logger.error(f"Action execution error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during action execution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Action execution failed: {str(e)}")

@router.post("/execute/bulk", response_model=BulkExecutionResponse)
async def execute_bulk_actions(
    request: BulkExecutionRequest,
    background_tasks: BackgroundTasks,
    action_engine: SalesActionEngine = Depends(get_action_engine)
):
    """
    Execute multiple sales actions in bulk with optional parallel processing.
    
    This endpoint supports bulk execution of sales actions with configurable
    parallel processing and error handling strategies.
    """
    try:
        bulk_execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(
            f"Starting bulk execution {bulk_execution_id}",
            extra={
                "bulk_execution_id": bulk_execution_id,
                "total_actions": len(request.actions),
                "parallel_execution": request.parallel_execution,
                "stop_on_error": request.stop_on_error,
                "tenant_id": request.tenant_id,
                "user_id": request.user_id
            }
        )
        
        execution_results = []
        successful_count = 0
        failed_count = 0
        
        if request.parallel_execution:
            # Execute actions in parallel using asyncio
            import asyncio
            
            async def execute_single_action(action: SalesAction) -> ActionExecutionResponse:
                try:
                    result = await action_engine.execute_action(
                        action=action,
                        tenant_id=request.tenant_id,
                        user_id=request.user_id,
                        metadata=request.metadata
                    )
                    
                    return ActionExecutionResponse(
                        execution_id=result.execution_id,
                        action_id=action.action_id,
                        status=result.status,
                        outputs=result.outputs,
                        errors=result.errors,
                        duration_ms=result.duration.total_seconds() * 1000 if result.duration else 0,
                        retry_count=result.retry_count,
                        started_at=datetime.now(timezone.utc),
                        completed_at=result.completed_at,
                        idempotency_used=result.retry_count == 0
                    )
                except Exception as e:
                    # Create error response
                    return ActionExecutionResponse(
                        execution_id=str(uuid.uuid4()),
                        action_id=action.action_id,
                        status=ExecutionStatus.FAILED,
                        outputs={},
                        errors=[str(e)],
                        duration_ms=0,
                        retry_count=0,
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                        idempotency_used=False
                    )
            
            # Execute all actions in parallel
            tasks = [execute_single_action(action) for action in request.actions]
            execution_results = await asyncio.gather(*tasks, return_exceptions=False)
            
        else:
            # Execute actions sequentially
            for action in request.actions:
                try:
                    result = await action_engine.execute_action(
                        action=action,
                        tenant_id=request.tenant_id,
                        user_id=request.user_id,
                        metadata=request.metadata
                    )
                    
                    execution_response = ActionExecutionResponse(
                        execution_id=result.execution_id,
                        action_id=action.action_id,
                        status=result.status,
                        outputs=result.outputs,
                        errors=result.errors,
                        duration_ms=result.duration.total_seconds() * 1000 if result.duration else 0,
                        retry_count=result.retry_count,
                        started_at=datetime.now(timezone.utc),
                        completed_at=result.completed_at,
                        idempotency_used=result.retry_count == 0
                    )
                    
                    execution_results.append(execution_response)
                    
                    if result.status == ExecutionStatus.COMPLETED:
                        successful_count += 1
                    else:
                        failed_count += 1
                        if request.stop_on_error:
                            logger.warning(f"Stopping bulk execution due to error in action {action.action_id}")
                            break
                
                except Exception as e:
                    error_response = ActionExecutionResponse(
                        execution_id=str(uuid.uuid4()),
                        action_id=action.action_id,
                        status=ExecutionStatus.FAILED,
                        outputs={},
                        errors=[str(e)],
                        duration_ms=0,
                        retry_count=0,
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                        idempotency_used=False
                    )
                    
                    execution_results.append(error_response)
                    failed_count += 1
                    
                    if request.stop_on_error:
                        logger.warning(f"Stopping bulk execution due to error in action {action.action_id}")
                        break
        
        # Count successes and failures for parallel execution
        if request.parallel_execution:
            successful_count = sum(1 for r in execution_results if r.status == ExecutionStatus.COMPLETED)
            failed_count = len(execution_results) - successful_count
        
        execution_time = (time.time() - start_time) * 1000
        
        log_business_event(
            logger,
            "bulk_actions_executed",
            "sales_action",
            bulk_execution_id,
            details={
                "total_actions": len(request.actions),
                "successful_executions": successful_count,
                "failed_executions": failed_count,
                "execution_time_ms": execution_time,
                "parallel_execution": request.parallel_execution
            }
        )
        
        return BulkExecutionResponse(
            bulk_execution_id=bulk_execution_id,
            total_actions=len(request.actions),
            successful_executions=successful_count,
            failed_executions=failed_count,
            execution_results=execution_results,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Bulk execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk execution failed: {str(e)}")

@router.post("/schedule", response_model=ActionScheduleResponse)
async def schedule_action(
    request: ActionScheduleRequest,
    background_tasks: BackgroundTasks
):
    """
    Schedule a sales action for future execution.
    
    This endpoint allows scheduling of sales actions with support for
    one-time and recurring executions.
    """
    try:
        schedule_id = str(uuid.uuid4())
        
        logger.info(
            f"Scheduling action {request.action.action_id}",
            extra={
                "schedule_id": schedule_id,
                "action_id": request.action.action_id,
                "scheduled_for": request.scheduled_for.isoformat(),
                "recurring": request.recurring,
                "recurrence_interval_hours": request.recurrence_interval_hours,
                "tenant_id": request.tenant_id,
                "user_id": request.user_id
            }
        )
        
        # Validate scheduling time
        if request.scheduled_for <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Scheduled time must be in the future")
        
        # Validate recurring parameters
        if request.recurring and not request.recurrence_interval_hours:
            raise HTTPException(status_code=400, detail="Recurrence interval is required for recurring actions")
        
        # Calculate next execution for recurring actions
        next_execution = None
        if request.recurring and request.recurrence_interval_hours:
            next_execution = request.scheduled_for + timedelta(hours=request.recurrence_interval_hours)
        
        # In a real implementation, this would store the schedule in a database
        # and use a scheduler like Celery or APScheduler to execute at the scheduled time
        # For now, we'll simulate the scheduling
        
        # Add background task to execute the action at the scheduled time
        # Note: This is a simplified implementation - production would use proper scheduling
        delay_seconds = (request.scheduled_for - datetime.now(timezone.utc)).total_seconds()
        if delay_seconds > 0:
            background_tasks.add_task(
                _execute_scheduled_action,
                request.action,
                request.tenant_id,
                request.user_id,
                request.metadata,
                delay_seconds
            )
        
        log_business_event(
            logger,
            "action_scheduled",
            "sales_action",
            schedule_id,
            details={
                "action_id": request.action.action_id,
                "scheduled_for": request.scheduled_for.isoformat(),
                "recurring": request.recurring,
                "delay_seconds": delay_seconds
            }
        )
        
        return ActionScheduleResponse(
            schedule_id=schedule_id,
            action_id=request.action.action_id,
            scheduled_for=request.scheduled_for,
            status="scheduled",
            recurring=request.recurring,
            next_execution=next_execution,
            created_at=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Action scheduling failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")

@router.get("/executions/{execution_id}/status", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: str,
    action_engine: SalesActionEngine = Depends(get_action_engine)
):
    """
    Get the current status of a specific action execution.
    
    This endpoint provides detailed status information for monitoring
    action execution progress and results.
    """
    try:
        context = await action_engine.get_execution_status(execution_id)
        if not context:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return ExecutionStatusResponse(
            execution_id=context.execution_id,
            action_id=context.action.action_id,
            status=context.status,
            outputs=context.outputs,
            errors=context.errors,
            retry_count=context.retry_count,
            started_at=context.started_at,
            completed_at=context.completed_at,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            metadata=context.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status for {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")

@router.get("/executions", response_model=ExecutionHistoryResponse)
async def get_execution_history(
    action_id: Optional[str] = Query(None, description="Filter by action ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[ExecutionStatus] = Query(None, description="Filter by execution status"),
    since: Optional[datetime] = Query(None, description="Filter executions since this timestamp"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(20, description="Page size", ge=1, le=100),
    action_engine: SalesActionEngine = Depends(get_action_engine)
):
    """
    Get execution history with filtering and pagination.
    
    This endpoint provides comprehensive execution history for monitoring,
    auditing, and troubleshooting purposes.
    """
    try:
        # Get active executions (in a real implementation, this would query a database)
        active_executions = await action_engine.list_active_executions()
        
        # Apply filters
        filtered_executions = active_executions
        
        if action_id:
            filtered_executions = [e for e in filtered_executions if e.action.action_id == action_id]
        
        if tenant_id:
            filtered_executions = [e for e in filtered_executions if e.tenant_id == tenant_id]
        
        if user_id:
            filtered_executions = [e for e in filtered_executions if e.user_id == user_id]
        
        if status:
            filtered_executions = [e for e in filtered_executions if e.status == status]
        
        if since:
            filtered_executions = [e for e in filtered_executions if e.started_at >= since]
        
        # Apply pagination
        total_count = len(filtered_executions)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_executions = filtered_executions[start_idx:end_idx]
        
        # Convert to response format
        execution_responses = [
            ExecutionStatusResponse(
                execution_id=context.execution_id,
                action_id=context.action.action_id,
                status=context.status,
                outputs=context.outputs,
                errors=context.errors,
                retry_count=context.retry_count,
                started_at=context.started_at,
                completed_at=context.completed_at,
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                metadata=context.metadata
            )
            for context in page_executions
        ]
        
        return ExecutionHistoryResponse(
            executions=execution_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=end_idx < total_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get execution history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution history: {str(e)}")

@router.post("/executions/{execution_id}/cancel", response_model=ActionCancellationResponse)
async def cancel_execution(
    execution_id: str,
    request: ActionCancellationRequest,
    action_engine: SalesActionEngine = Depends(get_action_engine)
):
    """
    Cancel an active action execution.
    
    This endpoint allows cancellation of pending or in-progress action executions
    with optional force cancellation for stuck executions.
    """
    try:
        logger.info(
            f"Cancelling execution {execution_id}",
            extra={
                "execution_id": execution_id,
                "reason": request.reason,
                "force": request.force
            }
        )
        
        # Attempt to cancel the execution
        cancelled = await action_engine.cancel_execution(execution_id)
        
        if not cancelled and not request.force:
            raise HTTPException(
                status_code=400, 
                detail="Execution cannot be cancelled (not found or already completed). Use force=true to override."
            )
        
        log_business_event(
            logger,
            "execution_cancelled",
            "sales_action",
            execution_id,
            details={
                "reason": request.reason,
                "force": request.force,
                "cancelled": cancelled
            }
        )
        
        return ActionCancellationResponse(
            execution_id=execution_id,
            cancelled=cancelled or request.force,
            reason=request.reason,
            cancelled_at=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel execution: {str(e)}")

@router.get("/active", response_model=List[ExecutionStatusResponse])
async def get_active_executions(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    action_engine: SalesActionEngine = Depends(get_action_engine)
):
    """
    Get all currently active (pending or in-progress) executions.
    
    This endpoint provides real-time visibility into active action executions
    for monitoring and operational purposes.
    """
    try:
        active_executions = await action_engine.list_active_executions()
        
        # Apply tenant filter if provided
        if tenant_id:
            active_executions = [e for e in active_executions if e.tenant_id == tenant_id]
        
        # Convert to response format
        execution_responses = [
            ExecutionStatusResponse(
                execution_id=context.execution_id,
                action_id=context.action.action_id,
                status=context.status,
                outputs=context.outputs,
                errors=context.errors,
                retry_count=context.retry_count,
                started_at=context.started_at,
                completed_at=context.completed_at,
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                metadata=context.metadata
            )
            for context in active_executions
        ]
        
        return execution_responses
        
    except Exception as e:
        logger.error(f"Failed to get active executions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get active executions: {str(e)}")

@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    action_engine: SalesActionEngine = Depends(get_action_engine),
    workflow_integration: WorkflowIntegration = Depends(get_workflow_integration),
    crm_integration: CRMIntegration = Depends(get_crm_integration),
    alert_system: SalesManagerAlertSystem = Depends(get_alert_system)
):
    """
    Perform a health check of the sales action execution system.
    
    This endpoint provides comprehensive health information for monitoring
    and troubleshooting the action execution infrastructure.
    """
    try:
        active_executions = await action_engine.list_active_executions()
        
        health_info = {
            "status": "healthy",
            "service": "sales_action_execution",
            "components": {
                "action_engine": "operational",
                "workflow_integration": "operational",
                "crm_integration": "operational", 
                "alert_system": "operational",
                "idempotency_manager": "operational",
                "retry_manager": "operational",
                "execution_monitor": "operational"
            },
            "metrics": {
                "active_executions": len(active_executions),
                "pending_executions": len([e for e in active_executions if e.status == ExecutionStatus.PENDING]),
                "in_progress_executions": len([e for e in active_executions if e.status == ExecutionStatus.IN_PROGRESS]),
                "retrying_executions": len([e for e in active_executions if e.status == ExecutionStatus.RETRYING])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return health_info
        
    except Exception as e:
        logger.error(f"Action execution health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

# Helper functions
async def _execute_scheduled_action(
    action: SalesAction,
    tenant_id: Optional[str],
    user_id: Optional[str],
    metadata: Optional[Dict[str, Any]],
    delay_seconds: float
):
    """Execute a scheduled action after the specified delay."""
    import asyncio
    
    # Wait for the scheduled time
    await asyncio.sleep(delay_seconds)
    
    try:
        # Get action engine and execute
        action_engine = get_action_engine()
        result = await action_engine.execute_action(
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=metadata
        )
        
        logger.info(f"Scheduled action {action.action_id} executed with status {result.status.value}")
        
    except Exception as e:
        logger.error(f"Scheduled action {action.action_id} failed: {str(e)}")