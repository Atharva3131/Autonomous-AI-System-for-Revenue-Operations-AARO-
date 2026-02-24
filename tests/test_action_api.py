"""
Unit tests for the Sales Action Execution API.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from aboa.action.api import router
from aboa.action.engine import ExecutionResult, ExecutionContext
from aboa.models.enums import ExecutionStatus, SalesActionType
from aboa.models.revenue_entities import SalesAction

# Create test client
from fastapi import FastAPI
app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def sample_action():
    """Create a sample sales action for testing."""
    return SalesAction(
        action_id="test-action-1",
        action_type=SalesActionType.CREATE_TASK,
        target_system="crm",
        parameters={"task_type": "follow_up", "deal_id": "deal-123"},
        expected_outcome="Follow-up task created",
        max_retries=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_action_dict():
    """Create a sample sales action dictionary for API requests."""
    return {
        "action_id": "test-action-1",
        "action_type": "create_task",
        "target_system": "crm",
        "parameters": {"task_type": "follow_up", "deal_id": "deal-123"},
        "prerequisites": [],
        "expected_outcome": "Follow-up task created",
        "revenue_impact": None,
        "priority": 1,
        "executed": False,
        "executed_at": None,
        "execution_result": None,
        "retry_count": 0,
        "max_retries": 3,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_execution_result():
    """Create a sample execution result for testing."""
    return ExecutionResult(
        execution_id="exec-123",
        status=ExecutionStatus.COMPLETED,
        outputs={"task_id": "task-456", "created_at": datetime.now(timezone.utc).isoformat()},
        errors=[],
        duration=timedelta(seconds=2),
        retry_count=0
    )


class TestActionExecutionAPI:
    """Test the action execution API endpoints."""
    
    @patch('aboa.action.api.get_action_engine')
    def test_execute_action_success(self, mock_get_engine, sample_action, sample_action_dict, sample_execution_result):
        """Test successful action execution via API."""
        # Setup mock
        mock_engine = AsyncMock()
        mock_engine.execute_action.return_value = sample_execution_result
        mock_get_engine.return_value = mock_engine
        
        # Prepare request
        request_data = {
            "action": sample_action_dict,
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "metadata": {"source": "test"},
            "force_execution": False
        }
        
        # Make request
        response = client.post("/api/v1/actions/execute", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["action_id"] == "test-action-1"
        assert data["status"] == "completed"
        assert data["retry_count"] == 0
        assert "execution_id" in data
        assert "outputs" in data
        assert "started_at" in data
    
    @patch('aboa.action.api.get_action_engine')
    def test_execute_action_with_error(self, mock_get_engine, sample_action_dict):
        """Test action execution with error via API."""
        # Setup mock to raise exception
        mock_engine = AsyncMock()
        mock_engine.execute_action.side_effect = Exception("Test error")
        mock_get_engine.return_value = mock_engine
        
        # Prepare request
        request_data = {
            "action": sample_action_dict,
            "tenant_id": "tenant-1",
            "user_id": "user-1"
        }
        
        # Make request
        response = client.post("/api/v1/actions/execute", json=request_data)
        
        # Verify error response
        assert response.status_code == 500
        assert "Action execution failed" in response.json()["detail"]
    
    @patch('aboa.action.api.get_action_engine')
    def test_get_execution_status_success(self, mock_get_engine):
        """Test getting execution status via API."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.execution_id = "exec-123"
        mock_context.action.action_id = "test-action-1"
        mock_context.status = ExecutionStatus.COMPLETED
        mock_context.outputs = {"result": "success"}
        mock_context.errors = []
        mock_context.retry_count = 0
        mock_context.started_at = datetime.now(timezone.utc)
        mock_context.completed_at = datetime.now(timezone.utc)
        mock_context.tenant_id = "tenant-1"
        mock_context.user_id = "user-1"
        mock_context.metadata = {}
        
        mock_engine = AsyncMock()
        mock_engine.get_execution_status.return_value = mock_context
        mock_get_engine.return_value = mock_engine
        
        # Make request
        response = client.get("/api/v1/actions/executions/exec-123/status")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == "exec-123"
        assert data["action_id"] == "test-action-1"
        assert data["status"] == "completed"
    
    @patch('aboa.action.api.get_action_engine')
    def test_get_execution_status_not_found(self, mock_get_engine):
        """Test getting execution status for non-existent execution."""
        mock_engine = AsyncMock()
        mock_engine.get_execution_status.return_value = None
        mock_get_engine.return_value = mock_engine
        
        # Make request
        response = client.get("/api/v1/actions/executions/nonexistent/status")
        
        # Verify error response
        assert response.status_code == 404
        assert "Execution not found" in response.json()["detail"]
    
    @patch('aboa.action.api.get_action_engine')
    def test_cancel_execution_success(self, mock_get_engine):
        """Test cancelling execution via API."""
        mock_engine = AsyncMock()
        mock_engine.cancel_execution.return_value = True
        mock_get_engine.return_value = mock_engine
        
        # Prepare request
        request_data = {
            "reason": "Test cancellation",
            "force": False
        }
        
        # Make request
        response = client.post("/api/v1/actions/executions/exec-123/cancel", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == "exec-123"
        assert data["cancelled"] == True
        assert data["reason"] == "Test cancellation"
    
    @patch('aboa.action.api.get_action_engine')
    def test_get_active_executions(self, mock_get_engine):
        """Test getting active executions via API."""
        # Setup mock contexts
        mock_context1 = MagicMock()
        mock_context1.execution_id = "exec-1"
        mock_context1.action.action_id = "action-1"
        mock_context1.status = ExecutionStatus.IN_PROGRESS
        mock_context1.outputs = {}
        mock_context1.errors = []
        mock_context1.retry_count = 0
        mock_context1.started_at = datetime.now(timezone.utc)
        mock_context1.completed_at = None
        mock_context1.tenant_id = "tenant-1"
        mock_context1.user_id = "user-1"
        mock_context1.metadata = {}
        
        mock_context2 = MagicMock()
        mock_context2.execution_id = "exec-2"
        mock_context2.action.action_id = "action-2"
        mock_context2.status = ExecutionStatus.PENDING
        mock_context2.outputs = {}
        mock_context2.errors = []
        mock_context2.retry_count = 0
        mock_context2.started_at = datetime.now(timezone.utc)
        mock_context2.completed_at = None
        mock_context2.tenant_id = "tenant-1"
        mock_context2.user_id = "user-1"
        mock_context2.metadata = {}
        
        mock_engine = AsyncMock()
        mock_engine.list_active_executions.return_value = [mock_context1, mock_context2]
        mock_get_engine.return_value = mock_engine
        
        # Make request
        response = client.get("/api/v1/actions/active")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["execution_id"] == "exec-1"
        assert data[1]["execution_id"] == "exec-2"
    
    def test_schedule_action_success(self, sample_action_dict):
        """Test scheduling action via API."""
        # Prepare request with future timestamp
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        request_data = {
            "action": sample_action_dict,
            "scheduled_for": future_time.isoformat(),
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "recurring": False
        }
        
        # Make request
        response = client.post("/api/v1/actions/schedule", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["action_id"] == "test-action-1"
        assert data["status"] == "scheduled"
        assert data["recurring"] == False
        assert "schedule_id" in data
    
    def test_schedule_action_past_time(self, sample_action_dict):
        """Test scheduling action with past timestamp."""
        # Prepare request with past timestamp
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        request_data = {
            "action": sample_action_dict,
            "scheduled_for": past_time.isoformat(),
            "tenant_id": "tenant-1",
            "user_id": "user-1"
        }
        
        # Make request
        response = client.post("/api/v1/actions/schedule", json=request_data)
        
        # Verify error response
        assert response.status_code == 400
        assert "Scheduled time must be in the future" in response.json()["detail"]
    
    def test_health_check(self):
        """Test health check endpoint."""
        with patch('aboa.action.api.get_action_engine') as mock_get_engine, \
             patch('aboa.action.api.get_workflow_integration'), \
             patch('aboa.action.api.get_crm_integration'), \
             patch('aboa.action.api.get_alert_system'):
            
            mock_engine = AsyncMock()
            mock_engine.list_active_executions.return_value = []
            mock_get_engine.return_value = mock_engine
            
            # Make request
            response = client.get("/api/v1/actions/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "sales_action_execution"
            assert "components" in data
            assert "metrics" in data


class TestBulkExecutionAPI:
    """Test bulk execution API endpoints."""
    
    @patch('aboa.action.api.get_action_engine')
    def test_bulk_execute_actions_success(self, mock_get_engine, sample_action_dict, sample_execution_result):
        """Test bulk action execution via API."""
        # Setup mock
        mock_engine = AsyncMock()
        mock_engine.execute_action.return_value = sample_execution_result
        mock_get_engine.return_value = mock_engine
        
        # Prepare request with multiple actions
        actions = [sample_action_dict for _ in range(3)]
        request_data = {
            "actions": actions,
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "parallel_execution": True,
            "stop_on_error": False
        }
        
        # Make request
        response = client.post("/api/v1/actions/execute/bulk", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_actions"] == 3
        assert data["successful_executions"] == 3
        assert data["failed_executions"] == 0
        assert len(data["execution_results"]) == 3
        assert "bulk_execution_id" in data


class TestExecutionHistoryAPI:
    """Test execution history API endpoints."""
    
    @patch('aboa.action.api.get_action_engine')
    def test_get_execution_history_with_pagination(self, mock_get_engine):
        """Test getting execution history with pagination."""
        # Setup mock contexts
        mock_contexts = []
        for i in range(25):  # More than one page
            mock_context = MagicMock()
            mock_context.execution_id = f"exec-{i}"
            mock_context.action.action_id = f"action-{i}"
            mock_context.status = ExecutionStatus.COMPLETED
            mock_context.outputs = {}
            mock_context.errors = []
            mock_context.retry_count = 0
            mock_context.started_at = datetime.now(timezone.utc)
            mock_context.completed_at = datetime.now(timezone.utc)
            mock_context.tenant_id = "tenant-1"
            mock_context.user_id = "user-1"
            mock_context.metadata = {}
            mock_contexts.append(mock_context)
        
        mock_engine = AsyncMock()
        mock_engine.list_active_executions.return_value = mock_contexts
        mock_get_engine.return_value = mock_engine
        
        # Make request for first page
        response = client.get("/api/v1/actions/executions?page=1&page_size=20")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["has_more"] == True
        assert len(data["executions"]) == 20
    
    @patch('aboa.action.api.get_action_engine')
    def test_get_execution_history_with_filters(self, mock_get_engine):
        """Test getting execution history with filters."""
        # Setup mock contexts with different action IDs
        mock_contexts = []
        for i in range(5):
            mock_context = MagicMock()
            mock_context.execution_id = f"exec-{i}"
            mock_context.action.action_id = "target-action" if i < 2 else f"other-action-{i}"
            mock_context.status = ExecutionStatus.COMPLETED
            mock_context.outputs = {}
            mock_context.errors = []
            mock_context.retry_count = 0
            mock_context.started_at = datetime.now(timezone.utc)
            mock_context.completed_at = datetime.now(timezone.utc)
            mock_context.tenant_id = "tenant-1"
            mock_context.user_id = "user-1"
            mock_context.metadata = {}
            mock_contexts.append(mock_context)
        
        mock_engine = AsyncMock()
        mock_engine.list_active_executions.return_value = mock_contexts
        mock_get_engine.return_value = mock_engine
        
        # Make request with action_id filter
        response = client.get("/api/v1/actions/executions?action_id=target-action")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["executions"]) == 2
        for execution in data["executions"]:
            assert execution["action_id"] == "target-action"