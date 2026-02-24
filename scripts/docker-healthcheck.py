#!/usr/bin/env python3
"""
Docker health check script for ABOA system.
This script is used by Docker's HEALTHCHECK instruction.
"""

import sys
import time
import requests
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def check_health() -> Dict[str, Any]:
    """
    Perform comprehensive health check for Docker container.
    
    Returns:
        Dict containing health check results
    """
    results = {
        "healthy": False,
        "checks": {},
        "timestamp": time.time()
    }
    
    try:
        # Basic health check
        response = requests.get(
            "http://localhost:8000/health",
            timeout=10,
            headers={"User-Agent": "Docker-HealthCheck/1.0"}
        )
        
        if response.status_code == 200:
            health_data = response.json()
            results["checks"]["basic"] = {
                "status": "healthy",
                "response_time": response.elapsed.total_seconds(),
                "data": health_data
            }
        else:
            results["checks"]["basic"] = {
                "status": "unhealthy",
                "error": f"HTTP {response.status_code}",
                "response_time": response.elapsed.total_seconds()
            }
            return results
        
        # Readiness check
        try:
            ready_response = requests.get(
                "http://localhost:8000/health/ready",
                timeout=5,
                headers={"User-Agent": "Docker-HealthCheck/1.0"}
            )
            
            if ready_response.status_code == 200:
                ready_data = ready_response.json()
                results["checks"]["readiness"] = {
                    "status": "ready" if ready_data.get("ready", False) else "not_ready",
                    "response_time": ready_response.elapsed.total_seconds(),
                    "data": ready_data
                }
            else:
                results["checks"]["readiness"] = {
                    "status": "not_ready",
                    "error": f"HTTP {ready_response.status_code}",
                    "response_time": ready_response.elapsed.total_seconds()
                }
        except Exception as e:
            results["checks"]["readiness"] = {
                "status": "error",
                "error": str(e)
            }
        
        # API responsiveness check
        try:
            info_response = requests.get(
                "http://localhost:8000/info",
                timeout=5,
                headers={"User-Agent": "Docker-HealthCheck/1.0"}
            )
            
            if info_response.status_code == 200:
                results["checks"]["api"] = {
                    "status": "responsive",
                    "response_time": info_response.elapsed.total_seconds()
                }
            else:
                results["checks"]["api"] = {
                    "status": "unresponsive",
                    "error": f"HTTP {info_response.status_code}"
                }
        except Exception as e:
            results["checks"]["api"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Determine overall health
        basic_healthy = results["checks"]["basic"]["status"] == "healthy"
        api_responsive = results["checks"]["api"]["status"] == "responsive"
        
        results["healthy"] = basic_healthy and api_responsive
        
        return results
        
    except requests.exceptions.ConnectionError:
        results["checks"]["basic"] = {
            "status": "connection_error",
            "error": "Cannot connect to application"
        }
        return results
        
    except requests.exceptions.Timeout:
        results["checks"]["basic"] = {
            "status": "timeout",
            "error": "Health check timeout"
        }
        return results
        
    except Exception as e:
        results["checks"]["basic"] = {
            "status": "error",
            "error": str(e)
        }
        return results


def main():
    """Main health check entry point."""
    try:
        health_results = check_health()
        
        if health_results["healthy"]:
            # Log success (minimal output for Docker)
            print("HEALTHY")
            sys.exit(0)
        else:
            # Log failure details
            print("UNHEALTHY")
            for check_name, check_result in health_results["checks"].items():
                if check_result["status"] not in ["healthy", "responsive", "ready"]:
                    print(f"  {check_name}: {check_result.get('error', check_result['status'])}")
            sys.exit(1)
            
    except Exception as e:
        print(f"HEALTH CHECK ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()