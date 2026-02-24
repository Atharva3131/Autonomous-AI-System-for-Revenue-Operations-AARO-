# Sales data ingestion API endpoints
"""
FastAPI router for sales data ingestion endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import logging

from aboa.core.exceptions import DataIngestionError, ExternalIntegrationError
from aboa.core.auth import TenantContext, get_current_tenant_context
from aboa.data_ingestion.service import SalesDataIngestionService, IngestionConfig, IngestionStats
from aboa.core.logging import log_business_event

logger = logging.getLogger(__name__)

# Global service instances per tenant
_tenant_services: Dict[str, SalesDataIngestionService] = {}

def get_ingestion_service(tenant_context: TenantContext = Depends(get_current_tenant_context)) -> SalesDataIngestionService:
    """Get or create the ingestion service instance for the current tenant."""
    tenant_id = tenant_context.tenant_id
    
    if tenant_id not in _tenant_services:
        # Create tenant-specific service instance
        _tenant_services[tenant_id] = SalesDataIngestionService(tenant_id=tenant_id)
    
    return _tenant_services[tenant_id]

# Request/Response models
class IngestionRequest(BaseModel):
    """Request model for data ingestion operations."""
    since: Optional[datetime] = Field(None, description="Only ingest data updated since this timestamp")
    limit_per_source: Optional[int] = Field(None, description="Limit number of records per source", ge=1, le=10000)
    sources: Optional[List[str]] = Field(None, description="Specific sources to ingest from")

class IngestionResponse(BaseModel):
    """Response model for data ingestion operations."""
    success: bool = Field(..., description="Whether the ingestion was successful")
    stats: Dict[str, Any] = Field(..., description="Ingestion statistics")
    message: str = Field(..., description="Human-readable message")
    request_id: str = Field(..., description="Unique request identifier")

class ServiceStatusResponse(BaseModel):
    """Response model for service status."""
    service_running: bool = Field(..., description="Whether the service is running")
    scheduler_enabled: bool = Field(..., description="Whether scheduling is enabled")
    scheduler_running: bool = Field(..., description="Whether the scheduler is active")
    connectors: Dict[str, Any] = Field(..., description="Connector status information")
    config: Dict[str, Any] = Field(..., description="Service configuration")

class ConnectorStatusResponse(BaseModel):
    """Response model for connector status."""
    connectors: Dict[str, Dict[str, Any]] = Field(..., description="Status of all connectors")

# Create router
router = APIRouter(prefix="/api/v1/ingestion", tags=["Sales Data Ingestion"])

@router.post("/start", response_model=Dict[str, str])
async def start_ingestion_service(
    background_tasks: BackgroundTasks,
    tenant_context: TenantContext = Depends(get_current_tenant_context),
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Start the sales data ingestion service for the current tenant.
    
    This endpoint starts the ingestion service and optionally the scheduler
    for periodic data ingestion.
    """
    try:
        if service.is_running:
            return {"message": "Service is already running", "status": "running"}
        
        # Start service in background
        background_tasks.add_task(service.start_service)
        
        log_business_event(
            logger,
            "service_start_requested",
            "ingestion_service",
            "service",
            details={
                "tenant_id": tenant_context.tenant_id,
                "scheduler_enabled": service.config.enable_scheduling
            }
        )
        
        return {"message": "Service start initiated", "status": "starting"}
        
    except Exception as e:
        logger.error(f"Failed to start ingestion service for tenant {tenant_context.tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start service: {str(e)}")


@router.get("/status", response_model=Dict[str, Any])
async def get_ingestion_status(
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Get the current status of the sales data ingestion service.
    
    Returns information about service status, last ingestion time,
    and connector health.
    """
    try:
        return {
            "status": "running" if service.is_running else "stopped",
            "service": "sales_data_ingestion",
            "connectors_available": True,
            "last_ingestion": None,
            "message": "Service status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting ingestion status: {str(e)}")
        return {
            "status": "error",
            "service": "sales_data_ingestion", 
            "error": str(e),
            "message": "Failed to retrieve service status"
        }

@router.post("/stop", response_model=Dict[str, str])
async def stop_ingestion_service(
    background_tasks: BackgroundTasks,
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Stop the sales data ingestion service.
    
    This endpoint stops the ingestion service and scheduler.
    """
    try:
        if not service.is_running:
            return {"message": "Service is not running", "status": "stopped"}
        
        # Stop service in background
        background_tasks.add_task(service.stop_service)
        
        log_business_event(
            logger,
            "service_stop_requested",
            "ingestion_service",
            "service"
        )
        
        return {"message": "Service stop initiated", "status": "stopping"}
        
    except Exception as e:
        logger.error(f"Failed to stop ingestion service: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop service: {str(e)}")

@router.post("/ingest", response_model=IngestionResponse)
async def ingest_all_data(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Ingest data from all configured sales data sources.
    
    This endpoint triggers a comprehensive data ingestion from all available
    CRM and sales data sources with error handling and retry logic.
    """
    try:
        import uuid
        request_id = str(uuid.uuid4())
        
        logger.info(
            f"Starting data ingestion request {request_id}",
            extra={
                "request_id": request_id,
                "since": request.since.isoformat() if request.since else None,
                "limit_per_source": request.limit_per_source,
                "sources": request.sources
            }
        )
        
        # Perform ingestion
        stats = await service.ingest_all_data(
            since=request.since,
            limit_per_source=request.limit_per_source
        )
        
        # Determine success based on stats
        success = stats.total_records_processed > 0 or len(stats.errors) == 0
        
        message = (
            f"Ingestion completed: {stats.total_records_processed} records processed, "
            f"{stats.total_records_failed} failed"
        )
        
        if stats.errors:
            message += f", {len(stats.errors)} errors"
        
        log_business_event(
            logger,
            "data_ingestion_requested",
            "sales_data",
            request_id,
            details={
                "processed": stats.total_records_processed,
                "failed": stats.total_records_failed,
                "execution_time": stats.execution_time_seconds
            }
        )
        
        return IngestionResponse(
            success=success,
            stats={
                "total_processed": stats.total_records_processed,
                "total_failed": stats.total_records_failed,
                "deals_processed": stats.deals_processed,
                "leads_processed": stats.leads_processed,
                "activities_processed": stats.activities_processed,
                "reps_processed": stats.reps_processed,
                "execution_time_seconds": stats.execution_time_seconds,
                "errors": stats.errors[:10]  # Limit errors in response
            },
            message=message,
            request_id=request_id
        )
        
    except DataIngestionError as e:
        logger.error(f"Data ingestion error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except ExternalIntegrationError as e:
        logger.error(f"External integration error: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.post("/ingest/{source_name}", response_model=IngestionResponse)
async def ingest_from_source(
    source_name: str,
    since: Optional[datetime] = Query(None, description="Only ingest data updated since this timestamp"),
    limit: Optional[int] = Query(None, description="Maximum number of records to ingest", ge=1, le=10000),
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Ingest data from a specific sales data source.
    
    Available sources: deals, leads, activities, reps
    """
    try:
        import uuid
        request_id = str(uuid.uuid4())
        
        # Validate source name
        valid_sources = ["deals", "leads", "activities", "reps"]
        if source_name not in valid_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid source name. Must be one of: {valid_sources}"
            )
        
        logger.info(
            f"Starting single source ingestion request {request_id}",
            extra={
                "request_id": request_id,
                "source": source_name,
                "since": since.isoformat() if since else None,
                "limit": limit
            }
        )
        
        # Perform single source ingestion
        result = await service.ingest_from_source(
            source_name=source_name,
            since=since,
            limit=limit
        )
        
        message = (
            f"Ingestion from {source_name} completed: {result.records_processed} records processed, "
            f"{result.records_failed} failed"
        )
        
        log_business_event(
            logger,
            "single_source_ingestion_requested",
            "sales_data",
            request_id,
            details={
                "source": source_name,
                "processed": result.records_processed,
                "failed": result.records_failed,
                "execution_time": result.execution_time
            }
        )
        
        return IngestionResponse(
            success=result.success,
            stats={
                "source": source_name,
                "records_processed": result.records_processed,
                "records_failed": result.records_failed,
                "execution_time_seconds": result.execution_time,
                "errors": result.errors[:10]  # Limit errors in response
            },
            message=message,
            request_id=request_id
        )
        
    except DataIngestionError as e:
        logger.error(f"Data ingestion error for {source_name}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during {source_name} ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.get("/status", response_model=ServiceStatusResponse)
async def get_service_status(
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Get the current status of the sales data ingestion service.
    
    Returns information about service state, scheduler, and connector health.
    """
    try:
        health_info = await service.health_check()
        
        return ServiceStatusResponse(
            service_running=health_info["service_running"],
            scheduler_enabled=health_info["scheduler_enabled"],
            scheduler_running=health_info["scheduler_running"],
            connectors=health_info["connectors"],
            config=health_info["config"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get service status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.get("/connectors/status", response_model=ConnectorStatusResponse)
async def get_connector_status(
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Get the status of all sales data connectors.
    
    Returns detailed information about each connector's connection state.
    """
    try:
        connector_status = await service.get_connector_status()
        
        return ConnectorStatusResponse(connectors=connector_status)
        
    except Exception as e:
        logger.error(f"Failed to get connector status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get connector status: {str(e)}")

@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Perform a comprehensive health check of the ingestion service.
    
    This endpoint provides detailed health information for monitoring and debugging.
    """
    try:
        health_info = await service.health_check()
        
        # Add API-specific health info
        health_info["api_status"] = "healthy"
        health_info["timestamp"] = datetime.utcnow().isoformat()
        
        return health_info
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

# Batch processing endpoints
@router.post("/batch/schedule", response_model=Dict[str, str])
async def schedule_batch_ingestion(
    interval_minutes: int = Query(60, description="Interval between ingestions in minutes", ge=1, le=1440),
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Schedule periodic batch ingestion.
    
    This endpoint enables or updates the scheduling interval for automatic data ingestion.
    """
    try:
        # Update configuration
        service.config.enable_scheduling = True
        service.config.schedule_interval_minutes = interval_minutes
        
        # Restart scheduler if service is running
        if service.is_running:
            await service.stop_service()
            await service.start_service()
        
        log_business_event(
            logger,
            "batch_scheduling_configured",
            "ingestion_service",
            "scheduler",
            details={"interval_minutes": interval_minutes}
        )
        
        return {
            "message": f"Batch ingestion scheduled every {interval_minutes} minutes",
            "status": "scheduled"
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule batch ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule: {str(e)}")

@router.delete("/batch/schedule", response_model=Dict[str, str])
async def disable_batch_ingestion(
    service: SalesDataIngestionService = Depends(get_ingestion_service)
):
    """
    Disable scheduled batch ingestion.
    
    This endpoint disables automatic periodic data ingestion.
    """
    try:
        # Update configuration
        service.config.enable_scheduling = False
        
        # Restart service if running to apply changes
        if service.is_running:
            await service.stop_service()
            await service.start_service()
        
        log_business_event(
            logger,
            "batch_scheduling_disabled",
            "ingestion_service",
            "scheduler"
        )
        
        return {
            "message": "Batch ingestion scheduling disabled",
            "status": "disabled"
        }
        
    except Exception as e:
        logger.error(f"Failed to disable batch ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disable scheduling: {str(e)}")