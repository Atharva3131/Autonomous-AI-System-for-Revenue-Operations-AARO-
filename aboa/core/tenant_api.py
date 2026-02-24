"""
Tenant management API endpoints.

This module provides REST API endpoints for managing tenants,
configurations, and resource allocation.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
import logging

from .tenant import (
    TenantConfiguration, TenantManager, get_tenant_manager,
    TenantStatus, TenantPlan, ResourceLimits
)
from .auth import get_auth_handler, TenantAwareAuth

logger = logging.getLogger(__name__)

# Request/Response models
class CreateTenantRequest(BaseModel):
    """Request model for creating a new tenant."""
    tenant_id: str = Field(..., description="Unique tenant identifier")
    name: str = Field(..., description="Tenant display name")
    domain: Optional[str] = Field(None, description="Tenant domain")
    plan: TenantPlan = Field(TenantPlan.STARTER, description="Subscription plan")
    admin_email: str = Field(..., description="Administrator email")
    admin_name: str = Field(..., description="Administrator name")
    
    # Optional configuration
    crm_config: Dict[str, Any] = Field(default_factory=dict, description="CRM configuration")
    notification_config: Dict[str, Any] = Field(default_factory=dict, description="Notification configuration")
    custom_limits: Optional[ResourceLimits] = Field(None, description="Custom resource limits")


class UpdateTenantRequest(BaseModel):
    """Request model for updating tenant configuration."""
    name: Optional[str] = Field(None, description="Tenant display name")
    domain: Optional[str] = Field(None, description="Tenant domain")
    plan: Optional[TenantPlan] = Field(None, description="Subscription plan")
    status: Optional[TenantStatus] = Field(None, description="Tenant status")
    resource_limits: Optional[ResourceLimits] = Field(None, description="Resource limits")
    crm_config: Optional[Dict[str, Any]] = Field(None, description="CRM configuration")
    notification_config: Optional[Dict[str, Any]] = Field(None, description="Notification configuration")


class TenantResponse(BaseModel):
    """Response model for tenant information."""
    tenant_id: str
    name: str
    domain: Optional[str]
    status: TenantStatus
    plan: TenantPlan
    resource_limits: ResourceLimits
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime]
    suspended_at: Optional[datetime]


class TenantListResponse(BaseModel):
    """Response model for tenant list."""
    tenants: List[TenantResponse]
    total: int
    page: int
    page_size: int


class TenantStatsResponse(BaseModel):
    """Response model for tenant statistics."""
    tenant_id: str
    current_usage: Dict[str, int]
    resource_limits: ResourceLimits
    usage_percentage: Dict[str, float]
    last_updated: datetime


class AdminAuthDependency:
    """Dependency for admin-only endpoints."""
    
    def __init__(self):
        self.auth_handler = get_auth_handler()
    
    def __call__(self, admin_token: str = Depends(lambda: "admin")) -> bool:
        """Validate admin access (simplified for demo)."""
        # In production, this would validate admin JWT tokens
        return True


# Create router
router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Management"])

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: CreateTenantRequest,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    _: bool = Depends(AdminAuthDependency())
):
    """
    Create a new tenant.
    
    This endpoint creates a new tenant with the specified configuration
    and resource limits. Only system administrators can create tenants.
    """
    try:
        # Check if tenant already exists
        existing_tenant = tenant_manager.get_tenant(request.tenant_id)
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tenant '{request.tenant_id}' already exists"
            )
        
        # Create tenant configuration
        tenant_config = tenant_manager.create_tenant(
            tenant_id=request.tenant_id,
            name=request.name,
            domain=request.domain,
            plan=request.plan,
            crm_config=request.crm_config,
            notification_config=request.notification_config
        )
        
        # Apply custom limits if provided
        if request.custom_limits:
            tenant_config.resource_limits = request.custom_limits
        
        logger.info(
            f"Created new tenant: {request.tenant_id}",
            extra={
                "tenant_id": request.tenant_id,
                "plan": request.plan.value,
                "admin_email": request.admin_email
            }
        )
        
        return TenantResponse(
            tenant_id=tenant_config.tenant_id,
            name=tenant_config.name,
            domain=tenant_config.domain,
            status=tenant_config.status,
            plan=tenant_config.plan,
            resource_limits=tenant_config.resource_limits,
            created_at=tenant_config.created_at,
            updated_at=tenant_config.updated_at,
            activated_at=tenant_config.activated_at,
            suspended_at=tenant_config.suspended_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create tenant")


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    status_filter: Optional[TenantStatus] = Query(None, description="Filter by tenant status"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(50, description="Page size", ge=1, le=100),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    _: bool = Depends(AdminAuthDependency())
):
    """
    List all tenants with optional filtering and pagination.
    
    This endpoint returns a paginated list of all tenants in the system.
    Only system administrators can access this endpoint.
    """
    try:
        # Get filtered tenants
        tenants = tenant_manager.list_tenants(status=status_filter)
        
        # Apply pagination
        total = len(tenants)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tenants = tenants[start_idx:end_idx]
        
        # Convert to response format
        tenant_responses = [
            TenantResponse(
                tenant_id=tenant.tenant_id,
                name=tenant.name,
                domain=tenant.domain,
                status=tenant.status,
                plan=tenant.plan,
                resource_limits=tenant.resource_limits,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                activated_at=tenant.activated_at,
                suspended_at=tenant.suspended_at
            )
            for tenant in paginated_tenants
        ]
        
        return TenantListResponse(
            tenants=tenant_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing tenants: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list tenants")


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    _: bool = Depends(AdminAuthDependency())
):
    """
    Get detailed information about a specific tenant.
    
    This endpoint returns complete configuration and status information
    for the specified tenant.
    """
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )
    
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        domain=tenant.domain,
        status=tenant.status,
        plan=tenant.plan,
        resource_limits=tenant.resource_limits,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        activated_at=tenant.activated_at,
        suspended_at=tenant.suspended_at
    )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    _: bool = Depends(AdminAuthDependency())
):
    """
    Update tenant configuration.
    
    This endpoint allows updating various aspects of tenant configuration
    including plan, limits, and settings.
    """
    try:
        # Prepare update data
        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.domain is not None:
            update_data['domain'] = request.domain
        if request.plan is not None:
            update_data['plan'] = request.plan
        if request.status is not None:
            update_data['status'] = request.status
        if request.resource_limits is not None:
            update_data['resource_limits'] = request.resource_limits
        if request.crm_config is not None:
            update_data['crm_config'] = request.crm_config
        if request.notification_config is not None:
            update_data['notification_config'] = request.notification_config
        
        # Update tenant
        updated_tenant = tenant_manager.update_tenant(tenant_id, **update_data)
        
        logger.info(
            f"Updated tenant: {tenant_id}",
            extra={"tenant_id": tenant_id, "updates": list(update_data.keys())}
        )
        
        return TenantResponse(
            tenant_id=updated_tenant.tenant_id,
            name=updated_tenant.name,
            domain=updated_tenant.domain,
            status=updated_tenant.status,
            plan=updated_tenant.plan,
            resource_limits=updated_tenant.resource_limits,
            created_at=updated_tenant.created_at,
            updated_at=updated_tenant.updated_at,
            activated_at=updated_tenant.activated_at,
            suspended_at=updated_tenant.suspended_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update tenant")


@router.post("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(
    tenant_id: str,
    reason: Optional[str] = Query(None, description="Reason for suspension"),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    _: bool = Depends(AdminAuthDependency())
):
    """
    Suspend a tenant.
    
    This endpoint suspends a tenant, preventing access to the system
    while preserving data and configuration.
    """
    try:
        suspended_tenant = tenant_manager.suspend_tenant(tenant_id, reason)
        
        logger.warning(
            f"Suspended tenant: {tenant_id}",
            extra={"tenant_id": tenant_id, "reason": reason}
        )
        
        return TenantResponse(
            tenant_id=suspended_tenant.tenant_id,
            name=suspended_tenant.name,
            domain=suspended_tenant.domain,
            status=suspended_tenant.status,
            plan=suspended_tenant.plan,
            resource_limits=suspended_tenant.resource_limits,
            created_at=suspended_tenant.created_at,
            updated_at=suspended_tenant.updated_at,
            activated_at=suspended_tenant.activated_at,
            suspended_at=suspended_tenant.suspended_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error suspending tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to suspend tenant")


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    _: bool = Depends(AdminAuthDependency())
):
    """
    Activate a tenant.
    
    This endpoint activates a suspended or inactive tenant,
    restoring access to the system.
    """
    try:
        activated_tenant = tenant_manager.activate_tenant(tenant_id)
        
        logger.info(
            f"Activated tenant: {tenant_id}",
            extra={"tenant_id": tenant_id}
        )
        
        return TenantResponse(
            tenant_id=activated_tenant.tenant_id,
            name=activated_tenant.name,
            domain=activated_tenant.domain,
            status=activated_tenant.status,
            plan=activated_tenant.plan,
            resource_limits=activated_tenant.resource_limits,
            created_at=activated_tenant.created_at,
            updated_at=activated_tenant.updated_at,
            activated_at=activated_tenant.activated_at,
            suspended_at=activated_tenant.suspended_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to activate tenant")


@router.get("/{tenant_id}/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    _: bool = Depends(AdminAuthDependency())
):
    """
    Get tenant resource usage statistics.
    
    This endpoint returns current resource usage and limits
    for the specified tenant.
    """
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found"
        )
    
    # Get current usage (placeholder - would query actual usage from database)
    current_usage = {
        "deals": 0,
        "leads": 0,
        "sales_reps": 0,
        "api_calls": 0,
        "storage": 0,
        "knowledge_documents": 0
    }
    
    # Calculate usage percentages
    usage_percentage = {}
    limits = tenant.resource_limits
    limit_map = {
        "deals": limits.max_deals,
        "leads": limits.max_leads,
        "sales_reps": limits.max_sales_reps,
        "api_calls": limits.max_api_calls_per_hour,
        "storage": limits.max_storage_mb,
        "knowledge_documents": limits.max_knowledge_documents
    }
    
    for resource, usage in current_usage.items():
        limit = limit_map.get(resource)
        if limit and limit > 0:
            usage_percentage[resource] = (usage / limit) * 100
        else:
            usage_percentage[resource] = 0
    
    return TenantStatsResponse(
        tenant_id=tenant_id,
        current_usage=current_usage,
        resource_limits=tenant.resource_limits,
        usage_percentage=usage_percentage,
        last_updated=datetime.utcnow()
    )