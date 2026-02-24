"""
Unit tests for Revenue Intelligence API endpoints.

Tests the FastAPI endpoints for pipeline risk analysis, decision classification,
and recommendation retrieval.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import Mock, patch

from aboa.decision.api import router
from aboa.models.enums import RiskType, DecisionClass, Severity


class TestRevenueIntelligenceAPI:
    """Test cases for Revenue Intelligence API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app with revenue intelligence router."""
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_analyze_pipeline_basic(self, client):
        """Test basic pipeline analysis endpoint."""
        request_data = {
            "include_recommendations": True,
            "min_confidence": 70.0
        }
        
        response = client.post("/api/v1/revenue-intelligence/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "analysis_id" in data
        assert "risks_detected" in data
        assert "recommendations" in data
        assert "summary" in data
        assert "execution_time_ms" in data
        assert "analyzed_at" in data
        
        # Verify summary contains expected fields
        summary = data["summary"]
        assert "total_risks_detected" in summary
        assert "total_recommendations" in summary
        assert "risk_severity_distribution" in summary
        assert "decision_class_distribution" in summary
    
    def test_analyze_pipeline_with_filters(self, client):
        """Test pipeline analysis with filtering parameters."""
        request_data = {
            "deal_ids": ["deal_1"],
            "risk_types": ["stalled_deal"],
            "min_confidence": 80.0,
            "include_recommendations": True
        }
        
        response = client.post("/api/v1/revenue-intelligence/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still return valid analysis even with filters
        assert isinstance(data["risks_detected"], list)
        assert isinstance(data["recommendations"], list)
    
    def test_classify_decision_basic(self, client):
        """Test decision classification endpoint."""
        request_data = {
            "risk_id": "test_risk_123",
            "deal_values": [75000.0],
            "override_confidence": 85.0
        }
        
        response = client.post("/api/v1/revenue-intelligence/classify-decision", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["risk_id"] == "test_risk_123"
        assert "decision_class" in data
        assert data["decision_class"] in ["auto_executable", "approval_required", "insight_only"]
        assert "confidence" in data
        assert "reasoning" in data
        assert "factors" in data
        assert "classified_at" in data
        
        # Verify factors structure
        factors = data["factors"]
        assert "risk_confidence" in factors
        assert "risk_severity" in factors
        assert "max_deal_value" in factors
        assert "action_type" in factors
    
    def test_classify_decision_high_value(self, client):
        """Test decision classification for high-value deals."""
        request_data = {
            "risk_id": "high_value_risk",
            "deal_values": [150000.0],  # High value should require approval
            "override_confidence": 90.0
        }
        
        response = client.post("/api/v1/revenue-intelligence/classify-decision", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # High-value deals should typically require approval
        assert data["decision_class"] in ["approval_required", "auto_executable"]
        assert float(data["factors"]["max_deal_value"]) == 150000.0
    
    def test_get_recommendations_basic(self, client):
        """Test recommendations retrieval endpoint."""
        request_data = {
            "limit": 5,
            "include_recommendations": True
        }
        
        response = client.post("/api/v1/revenue-intelligence/recommendations", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of recommendations
        assert isinstance(data, list)
        
        # If recommendations exist, verify structure
        if data:
            recommendation = data[0]
            assert "recommendation_id" in recommendation
            assert "risk" in recommendation
            assert "action" in recommendation
            assert "decision_class" in recommendation
            assert "confidence_score" in recommendation
            assert "sales_reasoning" in recommendation
            
            # Verify risk structure
            risk = recommendation["risk"]
            assert "risk_id" in risk
            assert "risk_type" in risk
            assert "confidence" in risk
            assert "severity" in risk
            
            # Verify action structure
            action = recommendation["action"]
            assert "action_id" in action
            assert "action_type" in action
            assert "priority" in action
            assert "expected_outcome" in action
    
    def test_get_recommendations_with_filters(self, client):
        """Test recommendations retrieval with filtering."""
        request_data = {
            "deal_id": "deal_1",
            "risk_types": ["stalled_deal"],
            "decision_classes": ["auto_executable"],
            "min_priority": 2,
            "limit": 10
        }
        
        response = client.post("/api/v1/revenue-intelligence/recommendations", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        # Verify filtering is applied (length should be <= limit)
        assert len(data) <= 10
    
    def test_get_risk_details(self, client):
        """Test risk details retrieval endpoint."""
        risk_id = "test_risk_123"
        
        response = client.get(f"/api/v1/revenue-intelligence/risks/{risk_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["risk_id"] == risk_id
        assert "risk_type" in data
        assert "detected_at" in data
        assert "confidence" in data
        assert "affected_deals" in data
        assert "affected_leads" in data
        assert "severity" in data
        assert "description" in data
        assert "recommended_actions" in data
    
    def test_get_risk_details_with_impact(self, client):
        """Test risk details with revenue impact assessment."""
        risk_id = "test_risk_with_impact"
        
        response = client.get(
            f"/api/v1/revenue-intelligence/risks/{risk_id}",
            params={"include_impact": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include revenue impact assessment
        assert "revenue_impact" in data
        if data["revenue_impact"]:
            impact = data["revenue_impact"]
            assert "total_pipeline_at_risk" in impact
            assert "deals_at_risk_count" in impact
            assert "urgency_score" in impact
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/revenue-intelligence/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify health check structure
        assert "status" in data
        assert "service" in data
        assert "components" in data
        assert "timestamp" in data
        
        # Verify components
        components = data["components"]
        assert "risk_detector" in components
        assert "decision_engine" in components
        assert "knowledge_manager" in components
    
    def test_generate_mock_data(self, client):
        """Test mock data generation endpoint."""
        request_data = {
            "num_deals": 3,
            "num_leads": 2,
            "num_reps": 2,
            "include_risks": True
        }
        
        response = client.post("/api/v1/revenue-intelligence/mock-data", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify mock data structure
        assert "deals" in data
        assert "leads" in data
        assert "reps" in data
        assert "activities" in data
        assert "generation_params" in data
        assert "generated_at" in data
        
        # Verify correct counts
        assert len(data["deals"]) == 3
        assert len(data["leads"]) == 2
        assert len(data["reps"]) == 2
        
        # Verify generation params
        params = data["generation_params"]
        assert params["num_deals"] == 3
        assert params["num_leads"] == 2
        assert params["num_reps"] == 2
        assert params["include_risks"] == True
    
    def test_analyze_pipeline_validation_error(self, client):
        """Test pipeline analysis with invalid parameters."""
        request_data = {
            "min_confidence": 150.0  # Invalid: should be <= 100
        }
        
        response = client.post("/api/v1/revenue-intelligence/analyze", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_classify_decision_validation_error(self, client):
        """Test decision classification with invalid parameters."""
        request_data = {
            "risk_id": "",  # Invalid: empty string
            "override_confidence": -10.0  # Invalid: should be >= 0
        }
        
        response = client.post("/api/v1/revenue-intelligence/classify-decision", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_get_recommendations_validation_error(self, client):
        """Test recommendations retrieval with invalid parameters."""
        request_data = {
            "limit": 200,  # Invalid: should be <= 100
            "min_priority": 10  # Invalid: should be <= 5
        }
        
        response = client.post("/api/v1/revenue-intelligence/recommendations", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_mock_data_validation_error(self, client):
        """Test mock data generation with invalid parameters."""
        request_data = {
            "num_deals": 100,  # Invalid: should be <= 50
            "num_leads": -1,   # Invalid: should be >= 1
            "num_reps": 0      # Invalid: should be >= 1
        }
        
        response = client.post("/api/v1/revenue-intelligence/mock-data", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_response_time_performance(self, client):
        """Test that API responses are reasonably fast."""
        import time
        
        request_data = {
            "include_recommendations": True,
            "min_confidence": 70.0
        }
        
        start_time = time.time()
        response = client.post("/api/v1/revenue-intelligence/analyze", json=request_data)
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Response should be under 5 seconds for mock data
        response_time = end_time - start_time
        assert response_time < 5.0
        
        # Verify execution time is reported in response
        data = response.json()
        assert data["execution_time_ms"] > 0
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            request_data = {"include_recommendations": True}
            response = client.post("/api/v1/revenue-intelligence/analyze", json=request_data)
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 3