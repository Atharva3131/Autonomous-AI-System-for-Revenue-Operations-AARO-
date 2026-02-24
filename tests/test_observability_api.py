"""
API tests for the observability endpoints.

Tests the REST API endpoints for revenue observability, metrics collection,
and log search functionality.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from aboa.main import create_app
from aboa.models.enums import (
    DecisionClass, ExecutionStatus, SalesActionType
)
from aboa.observability.activity_logger import (
    ActivityLogEntry, DecisionLogEntry, ActionLogEntry
)
from aboa.observability.metrics_collector import MetricSnapshot


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_activity_logger():
    """Mock activity logger for testing."""
    with patch('aboa.observability.api.get_activity_logger') as mock:
        yield mock.return_value


@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector for testing."""
    with patch('aboa.observability.api.get_metrics_collector') as mock:
        yield mock.return_value


class TestObservabilityHealthEndpoints:
    """Test health and ping endpoints."""
    
    def test_ping_endpoint(self, client):
        """Test ping endpoint."""
        response = client.get("/observability/ping")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["service"] == "observability"
    
    def test_system_health_endpoint(self, client, mock_activity_logger):
        """Test system health endpoint."""
        # Mock health metrics
        mock_health_metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "activities_last_hour": 10,
            "decisions_last_hour": 5,
            "actions_last_hour": 8,
            "failed_actions_last_hour": 1,
            "retrying_actions_last_hour": 0,
            "total_activity_logs": 100,
            "total_decision_logs": 50,
            "total_action_logs": 80
        }
        mock_activity_logger.get_system_health_metrics.return_value = mock_health_metrics
        
        response = client.get("/observability/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "degraded"  # 1/8 = 12.5% > 10% threshold
        assert "timestamp" in data
        assert data["metrics"] == mock_health_metrics
    
    def test_system_health_degraded_status(self, client, mock_activity_logger):
        """Test system health endpoint with degraded status."""
        # Mock health metrics with high failure rate
        mock_health_metrics = {
            "activities_last_hour": 10,
            "actions_last_hour": 10,
            "failed_actions_last_hour": 2  # 20% failure rate
        }
        mock_activity_logger.get_system_health_metrics.return_value = mock_health_metrics
        
        response = client.get("/observability/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "degraded"
    
    def test_system_health_idle_status(self, client, mock_activity_logger):
        """Test system health endpoint with idle status."""
        # Mock health metrics with no actions
        mock_health_metrics = {
            "activities_last_hour": 5,
            "actions_last_hour": 0,
            "failed_actions_last_hour": 0
        }
        mock_activity_logger.get_system_health_metrics.return_value = mock_health_metrics
        
        response = client.get("/observability/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "idle"


class TestLogSearchEndpoints:
    """Test log search endpoints."""
    
    def test_search_activity_logs(self, client, mock_activity_logger):
        """Test activity log search endpoint."""
        # Mock activity logs
        mock_logs = [
            ActivityLogEntry(
                activity_type="lead_created",
                component="data_ingestion",
                entity_type="lead",
                entity_id="lead_123",
                user_id="user_456"
            ),
            ActivityLogEntry(
                activity_type="deal_updated",
                component="decision_engine",
                entity_type="deal",
                entity_id="deal_789"
            )
        ]
        mock_activity_logger.search_activity_logs.return_value = mock_logs
        
        # Test search request
        search_request = {
            "activity_type": "lead_created",
            "component": "data_ingestion",
            "limit": 50
        }
        
        response = client.post("/observability/logs/search", json=search_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_results"] == 2
        assert len(data["results"]) == 2
        assert data["search_params"]["activity_type"] == "lead_created"
        assert data["search_params"]["component"] == "data_ingestion"
        
        # Verify search was called with correct parameters
        mock_activity_logger.search_activity_logs.assert_called_once_with(
            activity_type="lead_created",
            component="data_ingestion",
            entity_type=None,
            entity_id=None,
            user_id=None,
            session_id=None,
            start_time=None,
            end_time=None,
            severity=None,
            limit=50
        )
    
    def test_search_decision_logs(self, client, mock_activity_logger):
        """Test decision log search endpoint."""
        # Mock decision logs
        mock_logs = [
            DecisionLogEntry(
                decision_id="decision_123",
                decision_type=DecisionClass.AUTO_EXECUTABLE,
                confidence=85.5,
                reasoning="High confidence decision"
            )
        ]
        mock_activity_logger.search_decision_logs.return_value = mock_logs
        
        # Test search request
        search_request = {
            "decision_type": "auto_executable",
            "min_confidence": 80.0,
            "limit": 100
        }
        
        response = client.post("/observability/logs/decisions/search", json=search_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["search_params"]["decision_type"] == "auto_executable"
        assert data["search_params"]["min_confidence"] == 80.0
    
    def test_search_action_logs(self, client, mock_activity_logger):
        """Test action log search endpoint."""
        # Mock action logs
        mock_logs = [
            ActionLogEntry(
                action_id="action_123",
                action_type=SalesActionType.CREATE_TASK,
                execution_status=ExecutionStatus.COMPLETED,
                target_system="crm",
                duration_ms=1500
            )
        ]
        mock_activity_logger.search_action_logs.return_value = mock_logs
        
        # Test search request
        search_request = {
            "action_type": "create_task",
            "execution_status": "completed",
            "target_system": "crm"
        }
        
        response = client.post("/observability/logs/actions/search", json=search_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["search_params"]["action_type"] == "create_task"
        assert data["search_params"]["execution_status"] == "completed"
    
    def test_get_audit_trail(self, client, mock_activity_logger):
        """Test audit trail endpoint."""
        # Mock audit trail
        mock_audit_trail = [
            ActivityLogEntry(
                activity_type="lead_created",
                component="data_ingestion",
                entity_type="lead",
                entity_id="lead_123"
            ),
            ActivityLogEntry(
                activity_type="lead_updated",
                component="decision_engine",
                entity_type="lead",
                entity_id="lead_123"
            )
        ]
        mock_activity_logger.get_audit_trail.return_value = mock_audit_trail
        
        response = client.get("/observability/logs/audit/lead/lead_123?limit=50")
        assert response.status_code == 200
        
        data = response.json()
        assert data["entity_type"] == "lead"
        assert data["entity_id"] == "lead_123"
        assert data["total_entries"] == 2
        assert len(data["audit_trail"]) == 2
        
        # Verify audit trail was called with correct parameters
        mock_activity_logger.get_audit_trail.assert_called_once_with(
            entity_type="lead",
            entity_id="lead_123",
            limit=50
        )
    
    def test_export_logs(self, client, mock_activity_logger):
        """Test log export endpoint."""
        # Mock exported logs
        mock_exported_logs = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "activity_logs": [],
            "decision_logs": [],
            "action_logs": []
        }
        mock_activity_logger.export_logs_json.return_value = json.dumps(mock_exported_logs)
        
        # Test with time range
        start_time = datetime.now(timezone.utc) - timedelta(days=7)
        end_time = datetime.now(timezone.utc)
        
        # Format datetime strings properly for URL encoding
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        response = client.get(
            f"/observability/logs/export"
            f"?start_time={start_time_str}"
            f"&end_time={end_time_str}"
            f"&format=json"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["export_format"] == "json"
        # The API returns datetime in ISO format, so we need to compare properly
        assert data["start_time"] is not None
        assert data["end_time"] is not None
        assert "data" in data


class TestMetricsEndpoints:
    """Test metrics collection endpoints."""
    
    def test_collect_metrics(self, client, mock_metrics_collector):
        """Test metrics collection endpoint."""
        # Mock comprehensive snapshot
        mock_snapshot = MetricSnapshot(
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            metrics={
                "pipeline_recovery": {
                    "total_decisions": 10,
                    "automation_rate": 0.8,
                    "pipeline_recovered": 5000.0
                },
                "manual_work_reduction": {
                    "total_time_saved_hours": 20.0
                },
                "system_performance": {
                    "success_rate": 0.95
                }
            }
        )
        mock_metrics_collector.create_comprehensive_snapshot.return_value = mock_snapshot
        
        # Test metrics collection request
        metrics_request = {
            "period_days": 7
        }
        
        response = client.post("/observability/metrics/collect", json=metrics_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "snapshot" in data
        assert "summary" in data
        assert data["summary"]["period_days"] == 7
        assert "key_metrics" in data["summary"]
        
        # Verify snapshot creation was called
        mock_metrics_collector.create_comprehensive_snapshot.assert_called_once_with(7)
    
    def test_collect_metrics_with_time_range(self, client, mock_metrics_collector):
        """Test metrics collection with specific time range."""
        # Mock comprehensive snapshot
        mock_snapshot = MetricSnapshot(
            period_start=datetime.now(timezone.utc) - timedelta(days=3),
            period_end=datetime.now(timezone.utc),
            metrics={"pipeline_recovery": {"total_decisions": 5}}
        )
        mock_metrics_collector.create_comprehensive_snapshot.return_value = mock_snapshot
        
        # Test with specific time range
        start_time = datetime.now(timezone.utc) - timedelta(days=3)
        end_time = datetime.now(timezone.utc)
        
        metrics_request = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = client.post("/observability/metrics/collect", json=metrics_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["summary"]["period_days"] == 3
    
    def test_get_metric_snapshots(self, client, mock_metrics_collector):
        """Test getting metric snapshots."""
        # Mock stored snapshots
        now = datetime.now(timezone.utc)
        mock_snapshots = [
            MetricSnapshot(
                period_start=now - timedelta(days=7),
                period_end=now,
                metrics={"test": "data1"}
            ),
            MetricSnapshot(
                period_start=now - timedelta(days=14),
                period_end=now - timedelta(days=7),
                metrics={"test": "data2"}
            )
        ]
        mock_metrics_collector.metric_snapshots = mock_snapshots
        
        response = client.get("/observability/metrics/snapshots?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_snapshots"] == 2
        assert len(data["snapshots"]) == 2
    
    def test_analyze_metric_trends(self, client, mock_metrics_collector):
        """Test metric trend analysis."""
        # Mock trend analysis
        mock_analysis = {
            "metric_name": "pipeline_recovery.total_decisions",
            "data_points": 3,
            "first_value": 10,
            "last_value": 15,
            "percentage_change": 50.0,
            "trend_direction": "increasing"
        }
        mock_metrics_collector.get_trend_analysis.return_value = mock_analysis
        
        # Test trend analysis request
        trend_request = {
            "metric_name": "pipeline_recovery.total_decisions"
        }
        
        response = client.post("/observability/metrics/trends", json=trend_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["metric_name"] == "pipeline_recovery.total_decisions"
        assert data["analysis"]["trend_direction"] == "increasing"
        assert data["analysis"]["percentage_change"] == 50.0
    
    def test_get_metrics_report(self, client, mock_metrics_collector):
        """Test metrics report generation."""
        # Mock metrics report
        mock_report = "Test metrics report content"
        mock_metrics_collector.export_metrics_report.return_value = mock_report
        
        response = client.get("/observability/metrics/report?format=summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["report"] == mock_report
        assert data["format"] == "summary"
        
        # Verify export was called with correct parameters
        mock_metrics_collector.export_metrics_report.assert_called_once_with(
            snapshot=None,
            format="summary"
        )
    
    def test_get_metrics_report_json_format(self, client, mock_metrics_collector):
        """Test metrics report in JSON format."""
        # Mock JSON report
        mock_report = '{"test": "json_data"}'
        mock_metrics_collector.export_metrics_report.return_value = mock_report
        
        response = client.get("/observability/metrics/report?format=json")
        assert response.status_code == 200
        
        data = response.json()
        assert data["report"] == mock_report
        assert data["format"] == "json"
    
    def test_get_metrics_report_with_snapshot_id(self, client, mock_metrics_collector):
        """Test metrics report for specific snapshot."""
        # Mock snapshot
        mock_snapshot = MetricSnapshot(
            snapshot_id="test_snapshot_123",
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            metrics={"test": "data"}
        )
        mock_metrics_collector.metric_snapshots = [mock_snapshot]
        mock_metrics_collector.export_metrics_report.return_value = "Test report"
        
        response = client.get("/observability/metrics/report?snapshot_id=test_snapshot_123")
        assert response.status_code == 200
        
        # Verify export was called with the specific snapshot
        mock_metrics_collector.export_metrics_report.assert_called_once_with(
            snapshot=mock_snapshot,
            format="summary"
        )
    
    def test_get_metrics_report_snapshot_not_found(self, client, mock_metrics_collector):
        """Test metrics report with non-existent snapshot ID."""
        mock_metrics_collector.metric_snapshots = []
        
        response = client.get("/observability/metrics/report?snapshot_id=nonexistent")
        assert response.status_code == 404
        assert "Snapshot not found" in response.json()["message"]


class TestErrorHandling:
    """Test error handling in observability endpoints."""
    
    def test_health_endpoint_error(self, client, mock_activity_logger):
        """Test health endpoint error handling."""
        # Mock exception
        mock_activity_logger.get_system_health_metrics.side_effect = Exception("Test error")
        
        response = client.get("/observability/health")
        assert response.status_code == 500
        assert "Failed to retrieve system health" in response.json()["message"]
    
    def test_search_logs_error(self, client, mock_activity_logger):
        """Test log search error handling."""
        # Mock exception
        mock_activity_logger.search_activity_logs.side_effect = Exception("Search error")
        
        search_request = {"activity_type": "test"}
        response = client.post("/observability/logs/search", json=search_request)
        assert response.status_code == 500
        assert "Failed to search activity logs" in response.json()["message"]
    
    def test_collect_metrics_error(self, client, mock_metrics_collector):
        """Test metrics collection error handling."""
        # Mock exception
        mock_metrics_collector.create_comprehensive_snapshot.side_effect = Exception("Metrics error")
        
        metrics_request = {"period_days": 7}
        response = client.post("/observability/metrics/collect", json=metrics_request)
        assert response.status_code == 500
        assert "Failed to collect metrics" in response.json()["message"]
    
    def test_export_logs_error(self, client, mock_activity_logger):
        """Test log export error handling."""
        # Mock exception
        mock_activity_logger.export_logs_json.side_effect = Exception("Export error")
        
        response = client.get("/observability/logs/export")
        assert response.status_code == 500
        assert "Failed to export logs" in response.json()["message"]


class TestRequestValidation:
    """Test request validation for observability endpoints."""
    
    def test_log_search_request_validation(self, client):
        """Test log search request validation."""
        # Test invalid limit (too high)
        search_request = {"limit": 2000}  # Max is 1000
        response = client.post("/observability/logs/search", json=search_request)
        assert response.status_code == 422
    
    def test_decision_log_search_validation(self, client):
        """Test decision log search validation."""
        # Test invalid confidence range
        search_request = {"min_confidence": 150.0}  # Max is 100
        response = client.post("/observability/logs/decisions/search", json=search_request)
        assert response.status_code == 422
    
    def test_metrics_request_validation(self, client):
        """Test metrics request validation."""
        # Test invalid period_days (too high)
        metrics_request = {"period_days": 400}  # Max is 365
        response = client.post("/observability/metrics/collect", json=metrics_request)
        assert response.status_code == 422
    
    def test_metrics_report_format_validation(self, client, mock_metrics_collector):
        """Test metrics report format validation."""
        # Test invalid format
        response = client.get("/observability/metrics/report?format=invalid")
        assert response.status_code == 422


class TestIntegrationScenarios:
    """Test integration scenarios for observability API."""
    
    def test_complete_observability_workflow(self, client, mock_activity_logger, mock_metrics_collector):
        """Test complete observability workflow."""
        # 1. Check system health
        mock_activity_logger.get_system_health_metrics.return_value = {
            "activities_last_hour": 10,
            "actions_last_hour": 5,
            "failed_actions_last_hour": 0
        }
        
        health_response = client.get("/observability/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"
        
        # 2. Search for recent activities
        mock_activity_logger.search_activity_logs.return_value = [
            ActivityLogEntry(
                activity_type="deal_updated",
                component="decision_engine",
                entity_type="deal",
                entity_id="deal_123"
            )
        ]
        
        search_response = client.post("/observability/logs/search", json={"limit": 10})
        assert search_response.status_code == 200
        assert search_response.json()["total_results"] == 1
        
        # 3. Collect metrics
        mock_snapshot = MetricSnapshot(
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            metrics={"pipeline_recovery": {"total_decisions": 10}}
        )
        mock_metrics_collector.create_comprehensive_snapshot.return_value = mock_snapshot
        
        metrics_response = client.post("/observability/metrics/collect", json={"period_days": 7})
        assert metrics_response.status_code == 200
        assert "snapshot" in metrics_response.json()
        
        # 4. Generate report
        mock_metrics_collector.export_metrics_report.return_value = "Test report"
        
        report_response = client.get("/observability/metrics/report")
        assert report_response.status_code == 200
        assert report_response.json()["report"] == "Test report"
    
    def test_dashboard_data_retrieval(self, client, mock_activity_logger, mock_metrics_collector):
        """Test retrieving data for dashboard visualization."""
        # Mock recent metrics snapshot
        mock_snapshot = MetricSnapshot(
            period_start=datetime.now(timezone.utc) - timedelta(days=1),
            period_end=datetime.now(timezone.utc),
            metrics={
                "pipeline_recovery": {
                    "total_decisions": 25,
                    "automation_rate": 0.8,
                    "pipeline_recovered": 15000.0
                },
                "velocity_improvement": {
                    "deals_accelerated": 12,
                    "velocity_improvement_percentage": 30.0
                },
                "system_performance": {
                    "success_rate": 0.96,
                    "avg_response_time_ms": 850
                }
            }
        )
        mock_metrics_collector.create_comprehensive_snapshot.return_value = mock_snapshot
        
        # Collect daily metrics for dashboard
        response = client.post("/observability/metrics/collect", json={"period_days": 1})
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        
        # Verify dashboard-relevant metrics are present
        assert summary["key_metrics"]["total_decisions"] == 25
        assert summary["key_metrics"]["automation_rate"] == 0.8
        assert summary["key_metrics"]["pipeline_recovered"] == 15000.0
        assert summary["key_metrics"]["system_success_rate"] == 0.96