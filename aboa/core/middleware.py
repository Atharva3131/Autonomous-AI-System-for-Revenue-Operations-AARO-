"""
Tenant-aware middleware for request processing and data isolation.

This module provides middleware for tenant routing, data isolation,
and resource management in multi-tenant deployments.
"""

import time
import logging
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .tenant import TenantManager, get_tenant_manager, TenantStatus, TenantContext
from .auth import get_auth_handler
from .config import get_settings

logger = logging.getLogger(__name__)


class TenantRoutingMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant-aware request routing and validation."""
    
    def __init__(self, app, tenant_manager: Optional[TenantManager] = None):
        super().__init__(app)
        self.tenant_manager = tenant_manager or get_tenant_manager()
        self.auth_handler = get_auth_handler()
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with tenant routing and validation."""
        start_time = time.time()
        
        # Skip tenant validation for system endpoints
        if self._is_system_endpoint(request.url.path):
            return await call_next(request)
        
        # Skip tenant validation in development mode
        if self.settings.is_development() or self.settings.environment.lower() == "testing":
            # Set default tenant context for development
            request.state.tenant_id = "dev_tenant"
            request.state.tenant_context = TenantContext.create("dev_tenant", "dev_user")
            return await call_next(request)
        
        try:
            # Extract tenant information from request
            tenant_id = self.auth_handler.extract_tenant_from_request(request)
            
            if not tenant_id:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error_code": "TENANT_NOT_SPECIFIED",
                        "message": "Tenant ID must be specified in header, subdomain, or path",
                        "details": {
                            "supported_methods": [
                                "X-Tenant-ID header",
                                "Subdomain routing (tenant.domain.com)",
                                "Path prefix (/tenant/{tenant_id}/...)"
                            ]
                        },
                        "type": "TenantRoutingError"
                    }
                )
            
            # Validate tenant exists and is active
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if not tenant:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "error_code": "TENANT_NOT_FOUND",
                        "message": f"Tenant '{tenant_id}' not found",
                        "details": {"tenant_id": tenant_id},
                        "type": "TenantNotFoundError"
                    }
                )
            
            if tenant.status != TenantStatus.ACTIVE:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error_code": "TENANT_INACTIVE",
                        "message": f"Tenant '{tenant_id}' is not active",
                        "details": {
                            "tenant_id": tenant_id,
                            "status": tenant.status.value
                        },
                        "type": "TenantAccessError"
                    }
                )
            
            # Set tenant context in request state
            request.state.tenant_id = tenant_id
            request.state.tenant_config = tenant
            
            # Process request
            response = await call_next(request)
            
            # Add tenant information to response headers
            response.headers["X-Tenant-ID"] = tenant_id
            response.headers["X-Tenant-Plan"] = tenant.plan.value
            
            # Log tenant request
            process_time = time.time() - start_time
            logger.info(
                f"Tenant request processed: {request.method} {request.url.path}",
                extra={
                    "tenant_id": tenant_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4)
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Tenant routing error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error_code": "TENANT_ROUTING_ERROR",
                    "message": "Internal error processing tenant request",
                    "details": {},
                    "type": "InternalError"
                }
            )
    
    def _is_system_endpoint(self, path: str) -> bool:
        """Check if the path is a system endpoint that doesn't require tenant context."""
        system_paths = [
            "/health",
            "/info",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/system",
            "/api/v1/tenants"  # Tenant management endpoints
        ]
        
        return any(path.startswith(sys_path) for sys_path in system_paths)


class TenantResourceMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant resource monitoring and rate limiting."""
    
    def __init__(self, app, tenant_manager: Optional[TenantManager] = None):
        super().__init__(app)
        self.tenant_manager = tenant_manager or get_tenant_manager()
        self.request_counts: Dict[str, Dict[str, int]] = {}  # tenant_id -> {hour: count}
    
    async def dispatch(self, request: Request, call_next):
        """Process request with resource monitoring and rate limiting."""
        # Skip for system endpoints or development mode
        if (self._is_system_endpoint(request.url.path) or 
            get_settings().is_development()):
            return await call_next(request)
        
        tenant_id = getattr(request.state, 'tenant_id', None)
        if not tenant_id:
            return await call_next(request)
        
        try:
            # Check rate limits
            if not self._check_rate_limit(tenant_id):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "API rate limit exceeded for tenant",
                        "details": {"tenant_id": tenant_id},
                        "type": "RateLimitError"
                    }
                )
            
            # Increment request count
            self._increment_request_count(tenant_id)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if tenant and tenant.resource_limits.max_api_calls_per_hour:
                current_count = self._get_current_count(tenant_id)
                response.headers["X-RateLimit-Limit"] = str(tenant.resource_limits.max_api_calls_per_hour)
                response.headers["X-RateLimit-Remaining"] = str(
                    max(0, tenant.resource_limits.max_api_calls_per_hour - current_count)
                )
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 3600)
            
            return response
            
        except Exception as e:
            logger.error(f"Resource middleware error: {str(e)}", exc_info=True)
            return await call_next(request)
    
    def _check_rate_limit(self, tenant_id: str) -> bool:
        """Check if tenant is within rate limits."""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant or not tenant.resource_limits.max_api_calls_per_hour:
            return True  # No limit set
        
        current_count = self._get_current_count(tenant_id)
        return current_count < tenant.resource_limits.max_api_calls_per_hour
    
    def _get_current_count(self, tenant_id: str) -> int:
        """Get current request count for the tenant in the current hour."""
        current_hour = int(time.time()) // 3600
        return self.request_counts.get(tenant_id, {}).get(str(current_hour), 0)
    
    def _increment_request_count(self, tenant_id: str):
        """Increment request count for the tenant."""
        current_hour = int(time.time()) // 3600
        hour_key = str(current_hour)
        
        if tenant_id not in self.request_counts:
            self.request_counts[tenant_id] = {}
        
        self.request_counts[tenant_id][hour_key] = (
            self.request_counts[tenant_id].get(hour_key, 0) + 1
        )
        
        # Clean up old hour data (keep only last 2 hours)
        tenant_data = self.request_counts[tenant_id]
        old_hours = [h for h in tenant_data.keys() if int(h) < current_hour - 1]
        for old_hour in old_hours:
            del tenant_data[old_hour]
    
    def _is_system_endpoint(self, path: str) -> bool:
        """Check if the path is a system endpoint."""
        system_paths = ["/health", "/info", "/docs", "/redoc", "/openapi.json"]
        return any(path.startswith(sys_path) for sys_path in system_paths)


class TenantDataIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware for ensuring tenant data isolation."""
    
    def __init__(self, app, tenant_manager: Optional[TenantManager] = None):
        super().__init__(app)
        self.tenant_manager = tenant_manager or get_tenant_manager()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with data isolation context."""
        tenant_id = getattr(request.state, 'tenant_id', None)
        
        if tenant_id:
            # Set database context for tenant isolation
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if tenant:
                request.state.database_schema = tenant.database_schema
                request.state.vector_collection = tenant.vector_db_collection
        
        return await call_next(request)


class TenantAuditMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant audit logging."""
    
    def __init__(self, app, tenant_manager: Optional[TenantManager] = None):
        super().__init__(app)
        self.tenant_manager = tenant_manager or get_tenant_manager()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with audit logging."""
        start_time = time.time()
        tenant_id = getattr(request.state, 'tenant_id', None)
        
        # Check if audit logging is enabled for tenant
        audit_enabled = True
        if tenant_id:
            tenant = self.tenant_manager.get_tenant(tenant_id)
            audit_enabled = tenant.enable_audit_logging if tenant else True
        
        if not audit_enabled:
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Log audit information
        if tenant_id:
            process_time = time.time() - start_time
            
            audit_data = {
                "tenant_id": tenant_id,
                "user_id": getattr(request.state, 'user_id', None),
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "timestamp": time.time(),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
            
            logger.info(
                f"Tenant audit log: {request.method} {request.url.path}",
                extra={"audit_data": audit_data}
            )
        
        return response