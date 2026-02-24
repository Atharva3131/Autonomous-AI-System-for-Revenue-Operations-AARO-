#!/usr/bin/env python3
"""
Environment validation script for ABOA system.
Validates configuration and environment setup before deployment.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aboa.core.config import get_settings
from aboa.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class EnvironmentValidator:
    """Validates environment configuration and dependencies."""
    
    def __init__(self, environment: str = None):
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.settings = None
        
    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        logger.error(f"Validation Error: {message}")
    
    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)
        logger.warning(f"Validation Warning: {message}")
    
    def validate_python_version(self) -> bool:
        """Validate Python version requirements."""
        logger.info("Validating Python version...")
        
        if sys.version_info < (3, 9):
            self.add_error(f"Python 3.9+ required, found {sys.version_info.major}.{sys.version_info.minor}")
            return False
        
        logger.info(f"✅ Python version {sys.version_info.major}.{sys.version_info.minor} is compatible")
        return True
    
    def validate_dependencies(self) -> bool:
        """Validate required Python dependencies."""
        logger.info("Validating Python dependencies...")
        
        required_packages = [
            "fastapi", "uvicorn", "pydantic", "pydantic-settings",
            "httpx", "pytest", "chromadb", "sentence-transformers"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.add_error(f"Missing required packages: {', '.join(missing_packages)}")
            return False
        
        logger.info("✅ All required dependencies are installed")
        return True
    
    def validate_configuration(self) -> bool:
        """Validate application configuration."""
        logger.info("Validating application configuration...")
        
        try:
            self.settings = get_settings()
        except Exception as e:
            self.add_error(f"Failed to load configuration: {str(e)}")
            return False
        
        # Validate required settings
        if not self.settings.secret_key or self.settings.secret_key == "dev-secret-key":
            if self.environment == "production":
                self.add_error("SECRET_KEY must be set to a secure value in production")
            else:
                self.add_warning("SECRET_KEY is using default value")
        
        # Validate database configuration
        if not self.settings.database_url:
            self.add_warning("DATABASE_URL not configured, using default SQLite")
        elif self.settings.database_url.startswith("postgresql") and self.environment == "production":
            # Validate PostgreSQL connection string format
            if "password" not in self.settings.database_url.lower():
                self.add_warning("PostgreSQL connection string may be missing password")
        
        # Validate vector database
        if not self.settings.vector_db_url:
            self.add_warning("VECTOR_DB_URL not configured")
        
        # Validate external integrations
        if not self.settings.n8n_webhook_url and self.environment != "testing":
            self.add_warning("N8N_WEBHOOK_URL not configured")
        
        # Validate business settings
        if self.settings.high_value_deal_threshold <= 0:
            self.add_error("HIGH_VALUE_DEAL_THRESHOLD must be positive")
        
        if self.settings.max_retries < 1:
            self.add_error("MAX_RETRIES must be at least 1")
        
        logger.info("✅ Configuration validation completed")
        return True
    
    def validate_file_permissions(self) -> bool:
        """Validate file and directory permissions."""
        logger.info("Validating file permissions...")
        
        # Check if log directory is writable
        log_dir = Path("logs")
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                self.add_error("Cannot create logs directory - permission denied")
                return False
        
        if not os.access(log_dir, os.W_OK):
            self.add_error("Logs directory is not writable")
            return False
        
        # Check if data directory is writable
        data_dir = Path("data")
        if not data_dir.exists():
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                self.add_error("Cannot create data directory - permission denied")
                return False
        
        if not os.access(data_dir, os.W_OK):
            self.add_error("Data directory is not writable")
            return False
        
        logger.info("✅ File permissions are correct")
        return True
    
    def validate_network_connectivity(self) -> bool:
        """Validate network connectivity to external services."""
        logger.info("Validating network connectivity...")
        
        if not self.settings:
            return False
        
        # Skip network validation in testing environment
        if self.environment == "testing":
            logger.info("⏭️  Skipping network validation in testing environment")
            return True
        
        import httpx
        
        # Test vector database connectivity
        if self.settings.vector_db_url:
            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(f"{self.settings.vector_db_url}/api/v1/heartbeat")
                    if response.status_code != 200:
                        self.add_warning(f"Vector database returned status {response.status_code}")
            except Exception as e:
                self.add_warning(f"Cannot connect to vector database: {str(e)}")
        
        # Test n8n connectivity
        if self.settings.n8n_webhook_url:
            try:
                base_url = self.settings.n8n_webhook_url.rsplit('/', 1)[0]
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(f"{base_url}/healthz")
                    # n8n might return 404 for healthz, which is OK
                    if response.status_code not in [200, 404]:
                        self.add_warning(f"n8n service returned status {response.status_code}")
            except Exception as e:
                self.add_warning(f"Cannot connect to n8n service: {str(e)}")
        
        logger.info("✅ Network connectivity validation completed")
        return True
    
    async def validate_database_connectivity(self) -> bool:
        """Validate database connectivity."""
        logger.info("Validating database connectivity...")
        
        if not self.settings or not self.settings.database_url:
            self.add_warning("No database URL configured")
            return True
        
        try:
            if self.settings.database_url.startswith("sqlite"):
                # For SQLite, check if file is accessible or can be created
                db_path = self.settings.database_url.replace("sqlite:///", "")
                if db_path != ":memory:":
                    db_file = Path(db_path)
                    db_file.parent.mkdir(parents=True, exist_ok=True)
                    # Try to create/access the file
                    db_file.touch(exist_ok=True)
                logger.info("✅ SQLite database is accessible")
                
            elif self.settings.database_url.startswith("postgresql"):
                import asyncpg
                conn = await asyncio.wait_for(
                    asyncpg.connect(self.settings.database_url),
                    timeout=10.0
                )
                await conn.execute("SELECT 1")
                await conn.close()
                logger.info("✅ PostgreSQL database is accessible")
                
            else:
                self.add_warning("Unknown database type, skipping connectivity test")
                
        except asyncio.TimeoutError:
            self.add_error("Database connection timeout")
            return False
        except Exception as e:
            self.add_error(f"Database connection failed: {str(e)}")
            return False
        
        return True
    
    def validate_security_settings(self) -> bool:
        """Validate security-related settings."""
        logger.info("Validating security settings...")
        
        if not self.settings:
            return False
        
        # Check secret key strength in production
        if self.environment == "production":
            if len(self.settings.secret_key) < 32:
                self.add_error("SECRET_KEY should be at least 32 characters in production")
            
            if self.settings.debug:
                self.add_error("DEBUG should be False in production")
            
            # Check CORS origins
            if "*" in self.settings.allowed_origins:
                self.add_error("CORS origins should not include '*' in production")
        
        logger.info("✅ Security settings validation completed")
        return True
    
    async def run_validation(self) -> Tuple[bool, Dict[str, Any]]:
        """Run all validation checks."""
        logger.info(f"Starting environment validation for: {self.environment}")
        
        # Run all validation checks
        checks = [
            ("Python Version", self.validate_python_version()),
            ("Dependencies", self.validate_dependencies()),
            ("Configuration", self.validate_configuration()),
            ("File Permissions", self.validate_file_permissions()),
            ("Network Connectivity", self.validate_network_connectivity()),
            ("Database Connectivity", await self.validate_database_connectivity()),
            ("Security Settings", self.validate_security_settings()),
        ]
        
        # Compile results
        passed_checks = sum(1 for _, result in checks if result)
        total_checks = len(checks)
        
        results = {
            "environment": self.environment,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": [{"name": name, "passed": result} for name, result in checks],
            "overall_status": "PASS" if len(self.errors) == 0 else "FAIL"
        }
        
        return len(self.errors) == 0, results


async def main():
    """Main validation script entry point."""
    parser = argparse.ArgumentParser(description="ABOA Environment Validation Tool")
    parser.add_argument(
        "-e", "--environment",
        default=None,
        help="Environment to validate (development, staging, production)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging("INFO", "text", None)
    
    # Run validation
    validator = EnvironmentValidator(args.environment)
    success, results = await validator.run_validation()
    
    # Handle strict mode
    if args.strict and results["warnings"]:
        success = False
        results["overall_status"] = "FAIL"
        results["errors"].extend([f"Warning (strict mode): {w}" for w in results["warnings"]])
    
    # Output results
    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"ABOA Environment Validation Results")
        print(f"{'='*60}")
        print(f"Environment: {results['environment']}")
        print(f"Status: {results['overall_status']}")
        print(f"Checks: {results['passed_checks']}/{results['total_checks']} passed")
        
        if results["errors"]:
            print(f"\n❌ Errors ({len(results['errors'])}):")
            for error in results["errors"]:
                print(f"  • {error}")
        
        if results["warnings"]:
            print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
            for warning in results["warnings"]:
                print(f"  • {warning}")
        
        if success:
            print(f"\n✅ Environment validation passed!")
        else:
            print(f"\n❌ Environment validation failed!")
        
        print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())