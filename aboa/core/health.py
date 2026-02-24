"""
Health check and monitoring utilities for ABOA system.
"""

import time
import asyncio
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from aboa.core.config import get_settings
from aboa.core.logging import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a system component."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthChecker:
    """Comprehensive health checking for ABOA system components."""
    
    def __init__(self):
        self.settings = get_settings()
        self.start_time = time.time()
        self._last_health_check = None
        self._cached_health = None
        self._cache_duration = 30  # Cache health results for 30 seconds
    
    async def check_database_health(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            if not self.settings.database_url:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    message="Database URL not configured",
                    response_time_ms=0,
                    last_check=datetime.utcnow()
                )
            
            # For SQLite, just check if file is accessible
            if self.settings.database_url.startswith("sqlite"):
                db_path = self.settings.database_url.replace("sqlite:///", "")
                if db_path == ":memory:":
                    # In-memory database is always healthy if configured
                    response_time = (time.time() - start_time) * 1000
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.HEALTHY,
                        message="In-memory SQLite database ready",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow()
                    )
                else:
                    # Check if SQLite file exists and is accessible
                    import os
                    if os.path.exists(db_path) or os.access(os.path.dirname(db_path), os.W_OK):
                        response_time = (time.time() - start_time) * 1000
                        return ComponentHealth(
                            name="database",
                            status=HealthStatus.HEALTHY,
                            message="SQLite database accessible",
                            response_time_ms=response_time,
                            last_check=datetime.utcnow()
                        )
                    else:
                        return ComponentHealth(
                            name="database",
                            status=HealthStatus.UNHEALTHY,
                            message="SQLite database file not accessible",
                            response_time_ms=0,
                            last_check=datetime.utcnow()
                        )
            
            # For PostgreSQL, attempt connection
            elif self.settings.database_url.startswith("postgresql"):
                try:
                    import asyncpg
                    conn = await asyncio.wait_for(
                        asyncpg.connect(self.settings.database_url),
                        timeout=5.0
                    )
                    await conn.execute("SELECT 1")
                    await conn.close()
                    
                    response_time = (time.time() - start_time) * 1000
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.HEALTHY,
                        message="PostgreSQL database connected",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow()
                    )
                except asyncio.TimeoutError:
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.UNHEALTHY,
                        message="Database connection timeout",
                        response_time_ms=5000,
                        last_check=datetime.utcnow()
                    )
                except Exception as e:
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Database connection failed: {str(e)}",
                        response_time_ms=0,
                        last_check=datetime.utcnow()
                    )
            
            else:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    message="Unsupported database type",
                    response_time_ms=0,
                    last_check=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                response_time_ms=0,
                last_check=datetime.utcnow()
            )
    
    async def check_vector_db_health(self) -> ComponentHealth:
        """Check vector database (ChromaDB) connectivity."""
        start_time = time.time()
        
        try:
            if not self.settings.vector_db_url:
                return ComponentHealth(
                    name="vector_db",
                    status=HealthStatus.DEGRADED,
                    message="Vector database URL not configured",
                    response_time_ms=0,
                    last_check=datetime.utcnow()
                )
            
            # Try to connect to ChromaDB
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.settings.vector_db_url}/api/v1/heartbeat")
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return ComponentHealth(
                        name="vector_db",
                        status=HealthStatus.HEALTHY,
                        message="Vector database connected",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow()
                    )
                else:
                    return ComponentHealth(
                        name="vector_db",
                        status=HealthStatus.DEGRADED,
                        message=f"Vector database returned status {response.status_code}",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow()
                    )
                    
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="vector_db",
                status=HealthStatus.UNHEALTHY,
                message="Vector database connection timeout",
                response_time_ms=5000,
                last_check=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Vector database health check failed: {str(e)}")
            return ComponentHealth(
                name="vector_db",
                status=HealthStatus.UNHEALTHY,
                message=f"Vector database connection failed: {str(e)}",
                response_time_ms=0,
                last_check=datetime.utcnow()
            )
    
    def check_system_resources(self) -> ComponentHealth:
        """Check system resource usage (CPU, memory, disk)."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine health status based on resource usage
            status = HealthStatus.HEALTHY
            messages = []
            
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                messages.append(f"High CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > 70:
                status = HealthStatus.DEGRADED
                messages.append(f"Elevated CPU usage: {cpu_percent:.1f}%")
            
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                messages.append(f"High memory usage: {memory.percent:.1f}%")
            elif memory.percent > 70:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                messages.append(f"Elevated memory usage: {memory.percent:.1f}%")
            
            if disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                messages.append(f"High disk usage: {disk.percent:.1f}%")
            elif disk.percent > 80:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                messages.append(f"Elevated disk usage: {disk.percent:.1f}%")
            
            message = "; ".join(messages) if messages else "System resources normal"
            
            return ComponentHealth(
                name="system_resources",
                status=status,
                message=message,
                last_check=datetime.utcnow(),
                metadata={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3)
                }
            )
            
        except Exception as e:
            logger.error(f"System resource check failed: {str(e)}")
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"Resource check failed: {str(e)}",
                last_check=datetime.utcnow()
            )
    
    async def check_external_integrations(self) -> ComponentHealth:
        """Check external integration health (n8n, CRM connectors)."""
        start_time = time.time()
        
        try:
            if not self.settings.n8n_webhook_url:
                return ComponentHealth(
                    name="external_integrations",
                    status=HealthStatus.DEGRADED,
                    message="External integrations not configured",
                    response_time_ms=0,
                    last_check=datetime.utcnow()
                )
            
            # Try to ping n8n webhook endpoint
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Just check if the base URL is reachable
                base_url = self.settings.n8n_webhook_url.rsplit('/', 1)[0]
                response = await client.get(f"{base_url}/healthz", 
                                          headers={"Authorization": f"Bearer {self.settings.n8n_api_key}"})
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code in [200, 404]:  # 404 is OK, means n8n is running
                    return ComponentHealth(
                        name="external_integrations",
                        status=HealthStatus.HEALTHY,
                        message="External integrations reachable",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow()
                    )
                else:
                    return ComponentHealth(
                        name="external_integrations",
                        status=HealthStatus.DEGRADED,
                        message=f"External integrations returned status {response.status_code}",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow()
                    )
                    
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="external_integrations",
                status=HealthStatus.DEGRADED,
                message="External integrations timeout",
                response_time_ms=5000,
                last_check=datetime.utcnow()
            )
        except Exception as e:
            logger.warning(f"External integrations check failed: {str(e)}")
            return ComponentHealth(
                name="external_integrations",
                status=HealthStatus.DEGRADED,
                message="External integrations unavailable",
                response_time_ms=0,
                last_check=datetime.utcnow()
            )
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all system components."""
        # Check if we have cached results
        now = datetime.utcnow()
        if (self._last_health_check and 
            self._cached_health and 
            (now - self._last_health_check).total_seconds() < self._cache_duration):
            return self._cached_health
        
        start_time = time.time()
        
        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self.check_vector_db_health(),
            self.check_external_integrations(),
            return_exceptions=True
        )
        
        # Add synchronous checks
        system_health = self.check_system_resources()
        health_checks.append(system_health)
        
        # Process results
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for check in health_checks:
            if isinstance(check, Exception):
                logger.error(f"Health check failed with exception: {str(check)}")
                continue
                
            components[check.name] = {
                "status": check.status.value,
                "message": check.message,
                "response_time_ms": check.response_time_ms,
                "last_check": check.last_check.isoformat() if check.last_check else None,
                "metadata": check.metadata
            }
            
            # Determine overall status
            if check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        # Calculate uptime
        uptime_seconds = time.time() - self.start_time
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        
        # Build comprehensive health response
        health_response = {
            "overall": {
                "status": overall_status.value,
                "timestamp": now.isoformat(),
                "uptime": uptime_str,
                "uptime_seconds": int(uptime_seconds),
                "check_duration_ms": (time.time() - start_time) * 1000
            },
            "components": components,
            "system_info": {
                "service": "aboa",
                "version": "0.1.0",
                "environment": self.settings.environment,
                "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
                "process_id": psutil.os.getpid()
            }
        }
        
        # Cache the results
        self._cached_health = health_response
        self._last_health_check = now
        
        return health_response
    
    async def readiness_check(self) -> Dict[str, Any]:
        """Check if the service is ready to accept requests."""
        # For readiness, we only check critical components
        db_health = await self.check_database_health()
        
        ready = db_health.status != HealthStatus.UNHEALTHY
        
        return {
            "ready": ready,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": {
                    "status": db_health.status.value,
                    "message": db_health.message
                }
            }
        }
    
    async def liveness_check(self) -> Dict[str, Any]:
        """Check if the service is alive and responsive."""
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time)
        }


# Global health checker instance
_health_checker = None

def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker