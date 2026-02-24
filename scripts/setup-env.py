#!/usr/bin/env python3
"""
Environment setup script for ABOA system.
Automates the setup of development, staging, and production environments.
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aboa.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


class EnvironmentSetup:
    """Handles environment setup for different deployment targets."""
    
    def __init__(self, environment: str, deployment_type: str = "docker"):
        self.environment = environment
        self.deployment_type = deployment_type
        self.project_root = Path(__file__).parent.parent
        
        # Environment-specific configurations
        self.configs = {
            "development": {
                "env_file": "config/development.env",
                "compose_file": "docker-compose.yml",
                "database": "sqlite",
                "services": ["postgres", "chroma", "redis"],
                "features": ["debug", "hot_reload", "test_data"]
            },
            "staging": {
                "env_file": "config/staging.env",
                "compose_file": "docker-compose.yml",
                "database": "postgresql",
                "services": ["postgres", "chroma", "redis"],
                "features": ["monitoring", "load_testing"]
            },
            "production": {
                "env_file": "config/production.env",
                "compose_file": "docker-compose.prod.yml",
                "database": "postgresql",
                "services": ["postgres", "chroma", "redis", "nginx"],
                "features": ["monitoring", "alerting", "backup", "ha"]
            }
        }
    
    def validate_prerequisites(self) -> bool:
        """Validate that all prerequisites are installed."""
        logger.info("Validating prerequisites...")
        
        required_tools = ["python3", "pip"]
        
        if self.deployment_type == "docker":
            required_tools.extend(["docker", "docker-compose"])
        elif self.deployment_type == "k8s":
            required_tools.extend(["kubectl", "helm"])
        
        missing_tools = []
        for tool in required_tools:
            if not shutil.which(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            logger.error(f"Missing required tools: {', '.join(missing_tools)}")
            return False
        
        # Check Docker daemon
        if self.deployment_type == "docker":
            try:
                subprocess.run(["docker", "info"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                logger.error("Docker daemon is not running")
                return False
        
        # Check Kubernetes connection
        if self.deployment_type == "k8s":
            try:
                subprocess.run(["kubectl", "cluster-info"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                logger.error("Cannot connect to Kubernetes cluster")
                return False
        
        logger.info("✅ Prerequisites validation passed")
        return True
    
    def setup_directories(self) -> bool:
        """Create necessary directories."""
        logger.info("Setting up directories...")
        
        directories = [
            "logs",
            "data",
            "data/chroma_db",
            "scripts/migrations",
            "backups",
            "nginx/ssl",
            "k8s/secrets"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
        
        logger.info("✅ Directories setup completed")
        return True
    
    def setup_python_environment(self) -> bool:
        """Setup Python virtual environment and dependencies."""
        logger.info("Setting up Python environment...")
        
        venv_path = self.project_root / "venv"
        
        # Create virtual environment if it doesn't exist
        if not venv_path.exists():
            logger.info("Creating virtual environment...")
            subprocess.run([
                sys.executable, "-m", "venv", str(venv_path)
            ], check=True)
        
        # Determine pip path
        if os.name == 'nt':  # Windows
            pip_path = venv_path / "Scripts" / "pip"
            python_path = venv_path / "Scripts" / "python"
        else:  # Unix-like
            pip_path = venv_path / "bin" / "pip"
            python_path = venv_path / "bin" / "python"
        
        # Upgrade pip
        logger.info("Upgrading pip...")
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
        
        # Install dependencies
        logger.info("Installing dependencies...")
        requirements_file = self.project_root / "requirements.txt"
        subprocess.run([
            str(pip_path), "install", "-r", str(requirements_file)
        ], check=True)
        
        # Install development dependencies if in development
        if self.environment == "development":
            dev_requirements = [
                "black", "isort", "mypy", "pytest-cov", "pre-commit"
            ]
            subprocess.run([
                str(pip_path), "install"
            ] + dev_requirements, check=True)
        
        logger.info("✅ Python environment setup completed")
        return True
    
    def setup_configuration(self) -> bool:
        """Setup environment configuration files."""
        logger.info("Setting up configuration...")
        
        config = self.configs[self.environment]
        
        # Copy environment file to .env
        env_source = self.project_root / config["env_file"]
        env_target = self.project_root / ".env"
        
        if not env_target.exists():
            shutil.copy2(env_source, env_target)
            logger.info(f"Created .env from {config['env_file']}")
        else:
            logger.info(".env file already exists")
        
        # Generate secrets for production
        if self.environment == "production":
            self._generate_production_secrets()
        
        logger.info("✅ Configuration setup completed")
        return True
    
    def _generate_production_secrets(self):
        """Generate secure secrets for production environment."""
        import secrets
        import string
        
        logger.info("Generating production secrets...")
        
        # Generate secret key
        secret_key = ''.join(secrets.choice(
            string.ascii_letters + string.digits + "!@#$%^&*"
        ) for _ in range(64))
        
        # Generate database password
        db_password = ''.join(secrets.choice(
            string.ascii_letters + string.digits
        ) for _ in range(32))
        
        # Generate API keys
        n8n_api_key = ''.join(secrets.choice(
            string.ascii_letters + string.digits
        ) for _ in range(32))
        
        secrets_file = self.project_root / "k8s" / "secrets" / "production-secrets.env"
        with open(secrets_file, 'w') as f:
            f.write(f"SECRET_KEY={secret_key}\n")
            f.write(f"POSTGRES_PASSWORD={db_password}\n")
            f.write(f"N8N_API_KEY={n8n_api_key}\n")
        
        logger.warning(f"Production secrets generated in {secrets_file}")
        logger.warning("Please review and update these secrets before deployment")
    
    def setup_database(self) -> bool:
        """Setup database for the environment."""
        logger.info("Setting up database...")
        
        config = self.configs[self.environment]
        
        if self.deployment_type == "docker":
            # Start database services
            compose_file = config["compose_file"]
            services = ["postgres", "chroma"] if config["database"] == "postgresql" else ["chroma"]
            
            logger.info(f"Starting database services: {services}")
            subprocess.run([
                "docker-compose", "-f", compose_file, "up", "-d"
            ] + services, check=True)
            
            # Wait for services to be ready
            import time
            logger.info("Waiting for database services to be ready...")
            time.sleep(15)
            
            # Run migrations
            logger.info("Running database migrations...")
            subprocess.run([
                "python", "scripts/migrate.py", "migrate"
            ], check=True, cwd=self.project_root)
        
        elif self.deployment_type == "k8s":
            # Apply database manifests
            logger.info("Deploying database to Kubernetes...")
            subprocess.run([
                "kubectl", "apply", "-f", "k8s/namespace.yaml"
            ], check=True)
            subprocess.run([
                "kubectl", "apply", "-f", "k8s/configmap.yaml"
            ], check=True)
            subprocess.run([
                "kubectl", "apply", "-f", "k8s/secret.yaml"
            ], check=True)
            
            # Run migration job
            subprocess.run([
                "kubectl", "apply", "-f", "deployment.yaml"
            ], check=True)
        
        logger.info("✅ Database setup completed")
        return True
    
    def setup_monitoring(self) -> bool:
        """Setup monitoring and observability."""
        if self.environment == "development":
            logger.info("⏭️  Skipping monitoring setup in development")
            return True
        
        logger.info("Setting up monitoring...")
        
        # Create monitoring configuration
        monitoring_config = {
            "metrics": {
                "enabled": True,
                "endpoint": "/metrics",
                "scrape_interval": "30s"
            },
            "alerts": {
                "enabled": True,
                "endpoint": "/alerts",
                "check_interval": "60s"
            },
            "logging": {
                "level": "INFO" if self.environment == "production" else "DEBUG",
                "format": "json",
                "structured": True
            }
        }
        
        # Write monitoring config
        import json
        monitoring_file = self.project_root / "config" / f"monitoring-{self.environment}.json"
        with open(monitoring_file, 'w') as f:
            json.dump(monitoring_config, f, indent=2)
        
        logger.info("✅ Monitoring setup completed")
        return True
    
    def run_validation(self) -> bool:
        """Run environment validation."""
        logger.info("Running environment validation...")
        
        try:
            subprocess.run([
                "python", "scripts/validate-env.py",
                "--environment", self.environment
            ], check=True, cwd=self.project_root)
            
            logger.info("✅ Environment validation passed")
            return True
        except subprocess.CalledProcessError:
            logger.error("❌ Environment validation failed")
            return False
    
    def setup_environment(self) -> bool:
        """Run complete environment setup."""
        logger.info(f"🚀 Setting up {self.environment} environment with {self.deployment_type}")
        
        steps = [
            ("Prerequisites", self.validate_prerequisites),
            ("Directories", self.setup_directories),
            ("Python Environment", self.setup_python_environment),
            ("Configuration", self.setup_configuration),
            ("Database", self.setup_database),
            ("Monitoring", self.setup_monitoring),
            ("Validation", self.run_validation),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"📋 Step: {step_name}")
            try:
                if not step_func():
                    logger.error(f"❌ Step failed: {step_name}")
                    return False
            except Exception as e:
                logger.error(f"❌ Step failed: {step_name} - {str(e)}")
                return False
        
        logger.info("🎉 Environment setup completed successfully!")
        self._print_next_steps()
        return True
    
    def _print_next_steps(self):
        """Print next steps for the user."""
        print("\n" + "="*60)
        print("🎯 Next Steps:")
        print("="*60)
        
        if self.deployment_type == "docker":
            print("1. Review and update .env file with your specific configuration")
            print("2. Start the application:")
            print("   docker-compose up -d")
            print("3. Access the application:")
            print("   API: http://localhost:8000")
            print("   Docs: http://localhost:8000/docs")
        
        elif self.deployment_type == "k8s":
            print("1. Review and update k8s/secrets/ with your specific configuration")
            print("2. Deploy the application:")
            print("   kubectl apply -f k8s/")
            print("3. Check deployment status:")
            print("   kubectl get pods -n aboa")
        
        print("\n📊 Monitoring:")
        print("   Health: http://localhost:8000/health")
        print("   Metrics: http://localhost:8000/metrics")
        print("   Alerts: http://localhost:8000/alerts")
        
        print("\n🔧 Useful Commands:")
        print("   Validate: python scripts/validate-env.py")
        print("   Migrate: python scripts/migrate.py migrate")
        print("   Deploy: bash scripts/deploy.sh")
        
        print("="*60)


def main():
    """Main setup script entry point."""
    parser = argparse.ArgumentParser(description="ABOA Environment Setup Tool")
    parser.add_argument(
        "environment",
        choices=["development", "staging", "production"],
        help="Environment to setup"
    )
    parser.add_argument(
        "--deployment-type",
        choices=["docker", "k8s"],
        default="docker",
        help="Deployment type (default: docker)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, "text", None)
    
    # Run environment setup
    setup = EnvironmentSetup(args.environment, args.deployment_type)
    success = setup.setup_environment()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()