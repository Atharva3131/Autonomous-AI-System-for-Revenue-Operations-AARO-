"""
Tests for configuration management.
"""

import os
import pytest
from aboa.core.config import Settings, get_settings


def test_default_settings():
    """Test default settings values."""
    settings = Settings()
    assert settings.environment == "development"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"


def test_environment_detection():
    """Test environment detection methods."""
    import os
    
    # Test development environment
    os.environ["ENVIRONMENT"] = "development"
    settings = Settings()
    assert settings.is_development() is True
    assert settings.is_production() is False
    assert settings.is_testing() is False
    
    # Test production environment
    os.environ["ENVIRONMENT"] = "production"
    settings = Settings()
    assert settings.is_development() is False
    assert settings.is_production() is True
    assert settings.is_testing() is False
    
    # Clean up
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]


def test_settings_caching():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2