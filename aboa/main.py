"""
Main FastAPI application entry point for ABOA system.
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import time
import logging
from typing import Optional

from aboa.core.config import get_settings
from aboa.core.logging import setup_logging, get_logger
from aboa.core.exceptions import setup_exception_handlers
from aboa.core.health import get_health_checker
from aboa.core.monitoring import get_metrics_collector, get_alert_manager
from aboa.core.middleware import (
    TenantRoutingMiddleware, TenantResourceMiddleware,
    TenantDataIsolationMiddleware, TenantAuditMiddleware
)
from aboa.core.auth import get_current_tenant_context, TenantContext
from aboa.core.tenant_api import router as tenant_router
from aboa.data_ingestion.api import router as ingestion_router
from aboa.knowledge.api import router as knowledge_router
from aboa.decision.api import router as decision_router
from aboa.decision.revenue_optimization_api import router as revenue_optimization_router
from aboa.action.api import router as action_router
from aboa.human_loop.api import router as human_loop_router
from aboa.observability.api import router as observability_router
from aboa.orchestration import get_orchestration_service

# Security scheme for API documentation
security = HTTPBearer()
logger = get_logger(__name__)


class AuthenticationMiddleware:
    """Simple authentication middleware for API access."""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        """Process request with authentication check."""
        # Skip authentication for health check and docs
        if request.url.path in ["/health", "/health/detailed", "/health/ready", "/health/live", "/info", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Skip authentication in development mode
        settings = get_settings()
        if settings.is_development() or settings.environment.lower() == "testing":
            return await call_next(request)
        
        # Check for authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error_code": "MISSING_AUTHORIZATION",
                    "message": "Authorization header required",
                    "details": {},
                    "type": "AuthenticationError"
                }
            )
        
        # Extract and validate token (simplified for demo)
        token = auth_header.split(" ")[1]
        if not self._validate_token(token):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error_code": "INVALID_TOKEN",
                    "message": "Invalid or expired token",
                    "details": {},
                    "type": "AuthenticationError"
                }
            )
        
        # Add user context to request state
        request.state.user_id = self._extract_user_id(token)
        request.state.authenticated = True
        
        return await call_next(request)
    
    def _validate_token(self, token: str) -> bool:
        """Validate the provided token."""
        # Simplified validation - in production, verify JWT signature
        # and check expiration, issuer, etc.
        settings = get_settings()
        return token == settings.secret_key or token.startswith("aboa_")
    
    def _extract_user_id(self, token: str) -> str:
        """Extract user ID from token."""
        # Simplified extraction - in production, decode JWT payload
        if token.startswith("aboa_"):
            return token.replace("aboa_", "")
        return "system"


class RequestLoggingMiddleware:
    """Middleware for logging all API requests and responses."""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        """Log request and response details."""
        start_time = time.time()
        
        # Get metrics collector
        metrics_collector = get_metrics_collector()
        
        # Track connection
        async with metrics_collector.track_connection():
            # Log incoming request
            logger.info(
                f"Incoming request: {request.method} {request.url}",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "request_id": id(request)
                }
            )
            
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Record metrics
            metrics_collector.record_request(process_time, response.status_code)
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url} - {response.status_code}",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4),
                    "request_id": id(request),
                    "user_id": getattr(request.state, "user_id", None)
                }
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response


async def get_current_user_or_tenant_context(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependency to get current authenticated user or tenant context.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID string or tenant context
        
    Raises:
        HTTPException: If authentication fails
    """
    settings = get_settings()
    
    # Skip validation in development
    if settings.is_development():
        return "dev_user"
    
    # Validate token
    token = credentials.credentials
    if not token or token != settings.secret_key and not token.startswith("aboa_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user ID
    if token.startswith("aboa_"):
        return token.replace("aboa_", "")
    return "system"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Setup logging
    setup_logging(settings.log_level, settings.log_format, settings.log_file)
    logger.info("Starting ABOA application", extra={"version": "0.1.0"})
    
    # Create FastAPI app with comprehensive configuration
    app = FastAPI(
        title="Autonomous AI Agent for Revenue Operations (AARO)",
        description="""
        A production-ready AI system designed specifically for B2B SaaS and service companies 
        to optimize revenue operations. The system continuously monitors sales pipeline data, 
        detects revenue leakage and execution gaps, enforces sales SOPs using internal knowledge, 
        and executes corrective actions automatically with appropriate human oversight.
        
        ## Features
        
        * **Sales Data Ingestion**: Automated collection and normalization of CRM and sales data
        * **Sales Knowledge Management**: RAG-based system for sales SOPs and playbooks
        * **Revenue Intelligence**: Pipeline risk detection and decision classification
        * **Sales Action Execution**: Automated follow-ups, deal updates, and manager alerts
        * **Human-in-the-Loop**: Approval workflows for high-impact revenue decisions
        * **Revenue Observability**: Comprehensive metrics and activity tracking
        
        ## Authentication
        
        All endpoints (except health check and documentation) require Bearer token authentication.
        In development mode, authentication is disabled for easier testing.
        
        ## Rate Limiting
        
        API requests are subject to rate limiting to ensure system stability.
        """,
        version="0.1.0",
        contact={
            "name": "ABOA Development Team",
            "email": "support@aboa.ai",
        },
        license_info={
            "name": "Proprietary",
        },
        docs_url="/docs" if not settings.is_production() else None,
        redoc_url="/redoc" if not settings.is_production() else None,
        openapi_url="/openapi.json" if not settings.is_production() else None,
        servers=[
            {
                "url": f"http://{settings.host}:{settings.port}",
                "description": f"{settings.environment.title()} server"
            }
        ]
    )
    
    # Add security middleware
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.aboa.ai", "localhost", "127.0.0.1", "testserver"]
        )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"]
    )
    
    # Add tenant-aware middleware (order matters - add in reverse order of execution)
    app.add_middleware(TenantAuditMiddleware)
    app.add_middleware(TenantDataIsolationMiddleware)
    app.add_middleware(TenantResourceMiddleware)
    app.add_middleware(TenantRoutingMiddleware)
    
    # Add custom middleware
    app.middleware("http")(RequestLoggingMiddleware(app))
    app.middleware("http")(AuthenticationMiddleware(app))
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include API routers with proper prefixes and tags
    # Tenant management (admin only, no tenant context required)
    app.include_router(tenant_router)
    
    # Main API routers with tenant-aware authentication
    tenant_auth_dependencies = [] if settings.is_development() or settings.environment.lower() == "testing" else [Depends(get_current_tenant_context)]
    
    app.include_router(
        ingestion_router,
        dependencies=tenant_auth_dependencies
    )
    app.include_router(
        knowledge_router,
        dependencies=tenant_auth_dependencies
    )
    app.include_router(
        decision_router,
        dependencies=tenant_auth_dependencies
    )
    app.include_router(
        revenue_optimization_router,
        dependencies=tenant_auth_dependencies
    )
    app.include_router(
        action_router,
        dependencies=tenant_auth_dependencies
    )
    app.include_router(
        human_loop_router,
        dependencies=tenant_auth_dependencies
    )
    app.include_router(
        observability_router,
        dependencies=tenant_auth_dependencies
    )
    
    # Health check endpoint (no authentication required)
    @app.get(
        "/health",
        tags=["System"],
        summary="Basic Health Check",
        description="Simple health check for load balancers",
        response_description="Basic health status"
    )
    @app.options("/health")
    async def health_check():
        """Basic health check endpoint for monitoring and load balancers."""
        return {
            "status": "healthy",
            "service": "aboa",
            "version": "0.1.0",
            "environment": settings.environment,
            "timestamp": time.time()
        }
    
    # Comprehensive health check endpoint
    @app.get(
        "/health/detailed",
        tags=["System"],
        summary="Detailed Health Check",
        description="Comprehensive health check of all system components",
        response_description="Detailed health status"
    )
    async def detailed_health_check():
        """Comprehensive health check endpoint."""
        health_checker = get_health_checker()
        return await health_checker.comprehensive_health_check()
    
    # Readiness probe endpoint
    @app.get(
        "/health/ready",
        tags=["System"],
        summary="Readiness Check",
        description="Check if the service is ready to accept requests",
        response_description="Readiness status"
    )
    async def readiness_check():
        """Readiness probe endpoint for Kubernetes."""
        health_checker = get_health_checker()
        return await health_checker.readiness_check()
    
    # Liveness probe endpoint
    @app.get(
        "/health/live",
        tags=["System"],
        summary="Liveness Check",
        description="Check if the service is alive and responsive",
        response_description="Liveness status"
    )
    async def liveness_check():
        """Liveness probe endpoint for Kubernetes."""
        health_checker = get_health_checker()
        return await health_checker.liveness_check()
    
    # System info endpoint (no authentication required)
    @app.get(
        "/info",
        tags=["System"],
        summary="System Information",
        description="Get basic system information and configuration",
        response_description="System information"
    )
    async def system_info():
        """System information endpoint."""
        return {
            "name": "Autonomous AI Agent for Revenue Operations",
            "version": "0.1.0",
            "environment": settings.environment,
            "features": [
                "Sales Data Ingestion",
                "Sales Knowledge Management", 
                "Revenue Intelligence",
                "Sales Action Execution",
                "Human-in-the-Loop Approvals",
                "Revenue Observability"
            ],
            "api_version": "v1",
            "documentation_url": "/docs" if not settings.is_production() else None
        }
    
    # Metrics endpoint
    @app.get(
        "/metrics",
        tags=["Monitoring"],
        summary="System Metrics",
        description="Get current system and application metrics",
        response_description="Current metrics"
    )
    async def get_metrics():
        """Get current system metrics."""
        metrics_collector = get_metrics_collector()
        return metrics_collector.collect_metrics()
    
    # Metrics summary endpoint
    @app.get(
        "/metrics/summary",
        tags=["Monitoring"],
        summary="Metrics Summary",
        description="Get metrics summary for specified duration",
        response_description="Metrics summary"
    )
    async def get_metrics_summary(duration_minutes: int = 5):
        """Get metrics summary for the specified duration."""
        metrics_collector = get_metrics_collector()
        return metrics_collector.get_metrics_summary(duration_minutes)
    
    # Alerts endpoint
    @app.get(
        "/alerts",
        tags=["Monitoring"],
        summary="System Alerts",
        description="Get current system alerts",
        response_description="Active alerts"
    )
    async def get_alerts():
        """Get current system alerts."""
        alert_manager = get_alert_manager()
        alerts = alert_manager.check_alerts()
        return {
            "active_alerts": alerts,
            "alert_count": len(alerts),
            "critical_count": len([a for a in alerts if a["level"] == "critical"]),
            "warning_count": len([a for a in alerts if a["level"] == "warning"]),
            "timestamp": time.time()
        }
    
    # Orchestration health check endpoint
    @app.get(
        "/orchestration/health",
        tags=["System"],
        summary="Orchestration Health Check",
        description="Check the health of all orchestration components",
        response_description="Comprehensive health status"
    )
    async def orchestration_health():
        """Orchestration health check endpoint."""
        try:
            orchestration_service = get_orchestration_service()
            health_status = await orchestration_service.health_check()
            return health_status
        except Exception as e:
            return {
                "overall": {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }
            }
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Application startup event handler."""
        logger.info(
            "ABOA application started successfully",
            extra={
                "environment": settings.environment,
                "host": settings.host,
                "port": settings.port,
                "log_level": settings.log_level
            }
        )
        
        # Start orchestration service in development/testing
        if settings.environment in ["development", "testing"]:
            try:
                orchestration_service = get_orchestration_service()
                await orchestration_service.start_service()
                logger.info("Orchestration service started")
            except Exception as e:
                logger.error(f"Failed to start orchestration service: {str(e)}")
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event handler."""
        # Stop orchestration service
        try:
            orchestration_service = get_orchestration_service()
            await orchestration_service.stop_service()
            logger.info("Orchestration service stopped")
        except Exception as e:
            logger.error(f"Failed to stop orchestration service: {str(e)}")
        
        logger.info("ABOA application shutting down")
    
    return app

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "aboa.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )