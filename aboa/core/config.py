"""
Configuration management for different environments.
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment-specific configuration."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application settings
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    
    # Security settings
    secret_key: str = Field(default="dev-secret-key", validation_alias="SECRET_KEY")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        validation_alias="ALLOWED_ORIGINS"
    )
    
    # Logging settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")  # json or text
    log_file: Optional[str] = Field(default=None, validation_alias="LOG_FILE")
    
    # Database settings (for future use)
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")
    
    # Vector database settings (for future use)
    vector_db_url: Optional[str] = Field(default=None, validation_alias="VECTOR_DB_URL")
    vector_db_collection: str = Field(default="aboa_knowledge", validation_alias="VECTOR_DB_COLLECTION")
    
    # External integrations (for future use)
    n8n_webhook_url: Optional[str] = Field(default=None, validation_alias="N8N_WEBHOOK_URL")
    n8n_api_key: Optional[str] = Field(default=None, validation_alias="N8N_API_KEY")
    
    # Business settings
    default_follow_up_days: int = Field(default=3, validation_alias="DEFAULT_FOLLOW_UP_DAYS")
    sla_breach_threshold_hours: int = Field(default=24, validation_alias="SLA_BREACH_THRESHOLD_HOURS")
    high_value_deal_threshold: float = Field(default=10000.0, validation_alias="HIGH_VALUE_DEAL_THRESHOLD")
    
    # Retry and timeout settings
    max_retries: int = Field(default=3, validation_alias="MAX_RETRIES")
    retry_delay_seconds: int = Field(default=1, validation_alias="RETRY_DELAY_SECONDS")
    action_timeout_seconds: int = Field(default=300, validation_alias="ACTION_TIMEOUT_SECONDS")
    approval_timeout_hours: int = Field(default=24, validation_alias="APPROVAL_TIMEOUT_HOURS")
        
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() == "testing"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()