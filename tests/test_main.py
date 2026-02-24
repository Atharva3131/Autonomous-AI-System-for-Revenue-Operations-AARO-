"""
Tests for main application setup.
"""

import pytest
from fastapi.testclient import TestClient
from aboa.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "aboa"


def test_app_creation():
    """Test that the app can be created successfully."""
    app = create_app()
    assert app is not None
    assert app.title == "Autonomous AI Agent for Revenue Operations (AARO)"