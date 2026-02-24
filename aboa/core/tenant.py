"""
Multi-tenant support for the AARO system.

This module provides tenant isolation, configuration management, and
resource allocation for multi-tenant deployments.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import uuid


class TenantStatus(str, Enum):
    """Status of a tenant in the system."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    PENDING = "pending"


class TenantPlan(str, Enum):
    """Tenant subscription plans with different resource limits."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class ResourceLimits(BaseModel):
    """Resource limits for a tenant."""
    max_deals: Optional[int] = Field(None, description="Maximum number of deals", ge=0)
    max_leads: Optional[int] = Field(None, description="Maximum number of leads", ge=0)
    max_sales_reps: Optional[int] = Field(None, description="Maximum number of sales reps", ge=0)
    max_api_calls_per_hour: Optional[int] = Field(None, description="API rate limit per hour", ge=0)
    max_storage_mb: Optional[int] = Field(None, description="Maximum storage in MB", ge=0)
    max_knowledge_documents: Optional[int] = Field(None, description="Maximum knowledge documents", ge=0)
    enable_advanced_analytics: bool = Field(True, description="Enable advanced analytics features")
    enable_custom_integrations: bool = Field(True, description="Enable custom integrations")
    enable_priority_support: bool = Field(False, description="Enable priority support")


class TenantConfiguration(BaseModel):
    """Configuration settings for a tenant."""
    tenant_id: str = Field(..., description="Unique tenant identifier")
    name: str = Field(..., description="Tenant display name")
    domain: Optional[str] = Field(None, description="Tenant domain for routing")
    status: TenantStatus = Field(TenantStatus.ACTIVE, description="Tenant status")
    plan: TenantPlan = Field(TenantPlan.STARTER, description="Subscription plan")
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits, description="Resource limits")
    
    # Database isolation settings
    database_schema: Optional[str] = Field(None, description="Dedicated database schema")
    vector_db_collection: Optional[str] = Field(None, description="Dedicated vector DB collection")
    
    # Integration settings
    crm_config: Dict[str, Any] = Field(default_factory=dict, description="CRM integration configuration")
    workflow_config: Dict[str, Any] = Field(default_factory=dict, description="Workflow integration configuration")
    notification_config: Dict[str, Any] = Field(default_factory=dict, description="Notification configuration")
    
    # Security settings
    allowed_ip_ranges: List[str] = Field(default_factory=list, description="Allowed IP ranges")
    require_mfa: bool = Field(False, description="Require multi-factor authentication")
    session_timeout_minutes: int = Field(480, description="Session timeout in minutes", ge=1)
    
    # Audit and compliance
    enable_audit_logging: bool = Field(True, description="Enable detailed audit logging")
    data_retention_days: int = Field(365, description="Data retention period in days", ge=1)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    activated_at: Optional[datetime] = Field(None, description="Activation timestamp")
    suspended_at: Optional[datetime] = Field(None, description="Suspension timestamp")

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        """Validate domain format if provided."""
        if v is not None:
            if not v.replace('-', '').replace('.', '').isalnum():
                raise ValueError('Domain must contain only alphanumeric characters, hyphens, and dots')
        return v

    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v):
        """Validate tenant ID format."""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Tenant ID must contain only alphanumeric characters, hyphens, and underscores')
        return v


class TenantContext(BaseModel):
    """Runtime context for tenant operations."""
    tenant_id: str = Field(..., description="Current tenant ID")
    user_id: Optional[str] = Field(None, description="Current user ID")
    request_id: Optional[str] = Field(None, description="Current request ID")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    resource_usage: Dict[str, int] = Field(default_factory=dict, description="Current resource usage")
    
    @classmethod
    def create(cls, tenant_id: str, user_id: Optional[str] = None, request_id: Optional[str] = None) -> 'TenantContext':
        """Create a new tenant context."""
        return cls(
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id or str(uuid.uuid4())
        )


class TenantManager:
    """Manager for tenant operations and configuration."""
    
    def __init__(self):
        self._tenants: Dict[str, TenantConfiguration] = {}
        self._default_limits = self._get_default_limits()
    
    def _get_default_limits(self) -> Dict[TenantPlan, ResourceLimits]:
        """Get default resource limits by plan."""
        return {
            TenantPlan.STARTER: ResourceLimits(
                max_deals=100,
                max_leads=500,
                max_sales_reps=5,
                max_api_calls_per_hour=1000,
                max_storage_mb=1024,
                max_knowledge_documents=50,
                enable_advanced_analytics=False,
                enable_custom_integrations=False,
                enable_priority_support=False
            ),
            TenantPlan.PROFESSIONAL: ResourceLimits(
                max_deals=1000,
                max_leads=5000,
                max_sales_reps=25,
                max_api_calls_per_hour=10000,
                max_storage_mb=10240,
                max_knowledge_documents=500,
                enable_advanced_analytics=True,
                enable_custom_integrations=True,
                enable_priority_support=False
            ),
            TenantPlan.ENTERPRISE: ResourceLimits(
                max_deals=10000,
                max_leads=50000,
                max_sales_reps=100,
                max_api_calls_per_hour=100000,
                max_storage_mb=102400,
                max_knowledge_documents=5000,
                enable_advanced_analytics=True,
                enable_custom_integrations=True,
                enable_priority_support=True
            ),
            TenantPlan.CUSTOM: ResourceLimits(
                # Custom plans have no default limits
                enable_advanced_analytics=True,
                enable_custom_integrations=True,
                enable_priority_support=True
            )
        }
    
    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        plan: TenantPlan = TenantPlan.STARTER,
        domain: Optional[str] = None,
        **kwargs
    ) -> TenantConfiguration:
        """Create a new tenant configuration."""
        if tenant_id in self._tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")
        
        # Apply default resource limits based on plan
        resource_limits = self._default_limits.get(plan, ResourceLimits())
        
        tenant_config = TenantConfiguration(
            tenant_id=tenant_id,
            name=name,
            domain=domain,
            plan=plan,
            resource_limits=resource_limits,
            database_schema=f"tenant_{tenant_id}",
            vector_db_collection=f"tenant_{tenant_id}_knowledge",
            **kwargs
        )
        
        self._tenants[tenant_id] = tenant_config
        return tenant_config
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """Get tenant configuration by ID."""
        return self._tenants.get(tenant_id)
    
    def update_tenant(self, tenant_id: str, **updates) -> TenantConfiguration:
        """Update tenant configuration."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Update fields
        for field, value in updates.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)
        
        tenant.updated_at = datetime.utcnow()
        return tenant
    
    def suspend_tenant(self, tenant_id: str, reason: Optional[str] = None) -> TenantConfiguration:
        """Suspend a tenant."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        tenant.status = TenantStatus.SUSPENDED
        tenant.suspended_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()
        
        return tenant
    
    def activate_tenant(self, tenant_id: str) -> TenantConfiguration:
        """Activate a tenant."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        tenant.status = TenantStatus.ACTIVE
        tenant.activated_at = datetime.utcnow()
        tenant.suspended_at = None
        tenant.updated_at = datetime.utcnow()
        
        return tenant
    
    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[TenantConfiguration]:
        """List all tenants, optionally filtered by status."""
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants
    
    def validate_tenant_access(self, tenant_id: str, user_id: Optional[str] = None) -> bool:
        """Validate if a user has access to a tenant."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        if tenant.status != TenantStatus.ACTIVE:
            return False
        
        # Additional access validation logic can be added here
        return True
    
    def check_resource_limits(self, tenant_id: str, resource_type: str, current_usage: int) -> bool:
        """Check if tenant is within resource limits."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        limits = tenant.resource_limits
        limit_map = {
            'deals': limits.max_deals,
            'leads': limits.max_leads,
            'sales_reps': limits.max_sales_reps,
            'api_calls': limits.max_api_calls_per_hour,
            'storage': limits.max_storage_mb,
            'knowledge_documents': limits.max_knowledge_documents
        }
        
        limit = limit_map.get(resource_type)
        if limit is None:
            return True  # No limit set
        
        return current_usage <= limit
    
    def get_database_schema(self, tenant_id: str) -> Optional[str]:
        """Get the database schema for a tenant."""
        tenant = self.get_tenant(tenant_id)
        return tenant.database_schema if tenant else None
    
    def get_vector_collection(self, tenant_id: str) -> Optional[str]:
        """Get the vector database collection for a tenant."""
        tenant = self.get_tenant(tenant_id)
        return tenant.vector_db_collection if tenant else None


# Global tenant manager instance
_tenant_manager: Optional[TenantManager] = None

def get_tenant_manager() -> TenantManager:
    """Get the global tenant manager instance."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager