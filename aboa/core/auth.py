"""
Tenant-aware authentication and authorization for the AARO system.

This module provides authentication, authorization, and tenant context
management for multi-tenant deployments.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .tenant import TenantContext, TenantManager, get_tenant_manager, TenantStatus
from .config import get_settings

logger = logging.getLogger(__name__)

# Security scheme for API documentation
security = HTTPBearer()


class TenantAwareAuth:
    """Tenant-aware authentication and authorization handler."""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self.settings = get_settings()
    
    def create_access_token(
        self,
        tenant_id: str,
        user_id: str,
        permissions: List[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token with tenant context."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "permissions": permissions or [],
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access_token"
        }
        
        return jwt.encode(payload, self.settings.secret_key, algorithm="HS256")
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def extract_tenant_from_request(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request (header, subdomain, or path)."""
        # Method 1: Check X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # Method 2: Extract from subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            # Check if subdomain corresponds to a tenant
            tenant = self.tenant_manager.get_tenant(subdomain)
            if tenant:
                return subdomain
        
        # Method 3: Extract from path prefix (e.g., /tenant/{tenant_id}/api/...)
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "tenant":
            return path_parts[1]
        
        return None
    
    def validate_tenant_access(self, tenant_id: str, user_id: Optional[str] = None) -> bool:
        """Validate tenant access and status."""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return False
        
        if tenant.status != TenantStatus.ACTIVE:
            return False
        
        return self.tenant_manager.validate_tenant_access(tenant_id, user_id)
    
    def create_tenant_context(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        permissions: List[str] = None,
        request_id: Optional[str] = None
    ) -> TenantContext:
        """Create a tenant context for the current request."""
        return TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            permissions=permissions or [],
            request_id=request_id
        )


# Global auth instance
_auth_handler: Optional[TenantAwareAuth] = None

def get_auth_handler() -> TenantAwareAuth:
    """Get the global authentication handler."""
    global _auth_handler
    if _auth_handler is None:
        _auth_handler = TenantAwareAuth(get_tenant_manager())
    return _auth_handler


async def get_current_tenant_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TenantContext:
    """
    Dependency to get current tenant context from request.
    
    This function extracts tenant information from the request and validates
    authentication, returning a TenantContext for use in endpoints.
    """
    auth_handler = get_auth_handler()
    settings = get_settings()
    
    # Skip validation in development mode
    if settings.is_development() or settings.environment.lower() == "testing":
        # Extract tenant from request or use default
        tenant_id = auth_handler.extract_tenant_from_request(request) or "dev_tenant"
        return TenantContext.create(tenant_id=tenant_id, user_id="dev_user")
    
    # Decode and validate token
    token_payload = auth_handler.decode_token(credentials.credentials)
    
    # Extract tenant and user information
    token_tenant_id = token_payload.get("tenant_id")
    user_id = token_payload.get("sub")
    permissions = token_payload.get("permissions", [])
    
    # Extract tenant from request
    request_tenant_id = auth_handler.extract_tenant_from_request(request)
    
    # Determine final tenant ID (token takes precedence)
    tenant_id = token_tenant_id or request_tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID not found in token or request"
        )
    
    # Validate tenant access
    if not auth_handler.validate_tenant_access(tenant_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for tenant"
        )
    
    # Create and return tenant context
    return auth_handler.create_tenant_context(
        tenant_id=tenant_id,
        user_id=user_id,
        permissions=permissions,
        request_id=str(id(request))
    )


async def get_optional_tenant_context(request: Request) -> Optional[TenantContext]:
    """
    Optional dependency to get tenant context without requiring authentication.
    
    Used for endpoints that can work with or without tenant context.
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=auth_header.split(" ")[1]
        )
        
        return await get_current_tenant_context(request, credentials)
    except HTTPException:
        return None


def require_permission(permission: str):
    """
    Decorator factory to require specific permissions for endpoints.
    
    Args:
        permission: Required permission string
        
    Returns:
        Dependency function that validates permission
    """
    def permission_dependency(context: TenantContext = Depends(get_current_tenant_context)):
        if permission not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return context
    
    return permission_dependency


def require_tenant_feature(feature: str):
    """
    Decorator factory to require specific tenant features for endpoints.
    
    Args:
        feature: Required feature name
        
    Returns:
        Dependency function that validates feature access
    """
    def feature_dependency(context: TenantContext = Depends(get_current_tenant_context)):
        tenant_manager = get_tenant_manager()
        tenant = tenant_manager.get_tenant(context.tenant_id)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Check feature availability based on tenant plan
        feature_map = {
            "advanced_analytics": tenant.resource_limits.enable_advanced_analytics,
            "custom_integrations": tenant.resource_limits.enable_custom_integrations,
            "priority_support": tenant.resource_limits.enable_priority_support
        }
        
        if feature in feature_map and not feature_map[feature]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' not available for current plan"
            )
        
        return context
    
    return feature_dependency


class TenantResourceValidator:
    """Validator for tenant resource limits."""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
    
    def validate_resource_usage(
        self,
        tenant_id: str,
        resource_type: str,
        requested_amount: int = 1
    ) -> bool:
        """Validate if tenant can use additional resources."""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return False
        
        # Get current usage (this would typically come from a database)
        current_usage = self._get_current_usage(tenant_id, resource_type)
        
        return self.tenant_manager.check_resource_limits(
            tenant_id,
            resource_type,
            current_usage + requested_amount
        )
    
    def _get_current_usage(self, tenant_id: str, resource_type: str) -> int:
        """Get current resource usage for a tenant."""
        # This would typically query the database for current usage
        # For now, return 0 as a placeholder
        return 0


def validate_resource_limit(resource_type: str, amount: int = 1):
    """
    Decorator factory to validate resource limits for endpoints.
    
    Args:
        resource_type: Type of resource to validate
        amount: Amount of resource being requested
        
    Returns:
        Dependency function that validates resource limits
    """
    def resource_dependency(context: TenantContext = Depends(get_current_tenant_context)):
        validator = TenantResourceValidator(get_tenant_manager())
        
        if not validator.validate_resource_usage(context.tenant_id, resource_type, amount):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Resource limit exceeded for {resource_type}"
            )
        
        return context
    
    return resource_dependency