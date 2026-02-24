"""
Tests for the Human-in-the-Loop API endpoints.

This module tests the approval request, response, status, history,
escalation, and timeout management API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from uuid import uuid4

from aboa.main import create_app
from aboa.models.enums import ApprovalStatus, RiskType, SalesActionType, Severity
from aboa.human_loop.approval_handlers import ApprovalInterfaceOrchestrator


class TestHumanLoopAPI:
    """Test the Human-in-the-Loop API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock approval orchestrator."""
        return Mock(spec=ApprovalInterfaceOrchestrator)
    
    @pytest.fixture
    def sample_approval_request_data(self):
        """Create sample approval request data."""
        return {
            "pipeline_risk": {
                "risk_id": str(uuid4()),
                "risk_type": "stalled_deal",
                "confidence": 85.0,
                "affected_deals": ["deal_1"],
                "affected_leads": [],
                "severity": "high",
                "description": "Deal has been stalled for 30 days"
            },
            "recommended_action": {
                "action_id": str(uuid4()),
                "action_type": "create_task",
                "target_system": "workflow_engine",
                "parameters": {"task_type": "follow_up"},
                "expected_outcome": "Create follow-up task",
                "revenue_impact": "50000",
                "priority": 2
            },
            "deals": [
                {
                    "id": "deal_1",
                    "stage": "proposal",
                    "value": "75000",
                    "probability": 70.0,
                    "close_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                    "assigned_rep": "rep_1",
                    "days_in_current_stage": 35
                }
            ],
            "leads": [],
            "reps": [
                {
                    "id": "rep_1",
                    "name": "John Sales",
                    "email": "john@company.com",
                    "quota": "1000000",
                    "quota_attainment": 80.0,
                    "pipeline_value": "500000"
                }
            ],
            "approver_id": "manager_1"
        }
    
    @pytest.fixture
    def sample_approval_response_data(self):
        """Create sample approval response data."""
        return {
            "request_id": str(uuid4()),
            "approver_id": "manager_1",
            "decision": "approved",
            "reasoning": "Action looks good, proceed",
            "confidence": 85.0
        }
    
    def test_create_approval_request_success(self, client, sample_approval_request_data):
        """Test successful approval request creation."""
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock the approval request creation
            mock_request = Mock()
            mock_request.request_id = str(uuid4())
            mock_request.approver_id = "manager_1"
            mock_request.status = ApprovalStatus.PENDING
            mock_request.priority = 2
            mock_request.timeout_minutes = 60
            mock_request.created_at = datetime.utcnow()
            mock_request.expires_at = datetime.utcnow() + timedelta(minutes=60)
            mock_request.escalation_rules = []
            
            # Mock pipeline risk and action
            mock_request.pipeline_risk = Mock()
            mock_request.pipeline_risk.risk_id = sample_approval_request_data["pipeline_risk"]["risk_id"]
            mock_request.pipeline_risk.risk_type = RiskType.STALLED_DEAL
            mock_request.pipeline_risk.confidence = 85.0
            mock_request.pipeline_risk.affected_deals = ["deal_1"]
            mock_request.pipeline_risk.affected_leads = []
            mock_request.pipeline_risk.severity = Severity.HIGH
            mock_request.pipeline_risk.description = "Deal has been stalled for 30 days"
            mock_request.pipeline_risk.detected_at = datetime.utcnow()
            
            mock_request.recommended_action = Mock()
            mock_request.recommended_action.action_id = sample_approval_request_data["recommended_action"]["action_id"]
            mock_request.recommended_action.action_type = SalesActionType.CREATE_TASK
            mock_request.recommended_action.target_system = "workflow_engine"
            mock_request.recommended_action.parameters = {"task_type": "follow_up"}
            mock_request.recommended_action.expected_outcome = "Create follow-up task"
            mock_request.recommended_action.revenue_impact = Decimal('50000')
            mock_request.recommended_action.priority = 2
            mock_request.recommended_action.created_at = datetime.utcnow()
            
            mock_request.revenue_context = Mock()
            mock_request.revenue_context.context_id = str(uuid4())
            mock_request.revenue_context.deal_history = []
            mock_request.revenue_context.similar_deals = []
            mock_request.revenue_context.rep_performance = Mock()
            mock_request.revenue_context.rep_performance.id = "rep_1"
            mock_request.revenue_context.rep_performance.name = "John Sales"
            mock_request.revenue_context.rep_performance.quota_attainment = 80.0
            mock_request.revenue_context.sales_playbook_guidance = ["Follow up within 24 hours"]
            mock_request.revenue_context.confidence_score = 85.0
            mock_request.revenue_context.generated_at = datetime.utcnow()
            
            mock_orchestrator.create_approval_request.return_value = mock_request
            
            response = client.post(
                "/api/v1/human-loop/approval-requests",
                json=sample_approval_request_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["request_id"] == mock_request.request_id
            assert data["approver_id"] == "manager_1"
            assert data["status"] == "pending"
            assert data["priority"] == 2
            assert data["timeout_minutes"] == 60
            assert "pipeline_risk" in data
            assert "recommended_action" in data
            assert "revenue_context" in data
    
    def test_create_approval_request_invalid_data(self, client):
        """Test approval request creation with invalid data."""
        invalid_data = {
            "pipeline_risk": {
                "risk_type": "invalid_type"  # Invalid risk type
            },
            "recommended_action": {
                "action_type": "invalid_action"  # Invalid action type
            },
            "approver_id": "manager_1"
        }
        
        response = client.post(
            "/api/v1/human-loop/approval-requests",
            json=invalid_data
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_submit_approval_response_success(self, client, sample_approval_response_data):
        """Test successful approval response submission."""
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock the approval response
            mock_response = Mock()
            mock_response.response_id = str(uuid4())
            mock_response.request_id = sample_approval_response_data["request_id"]
            mock_response.approver_id = "manager_1"
            mock_response.decision = ApprovalStatus.APPROVED
            mock_response.reasoning = "Action looks good, proceed"
            mock_response.additional_context_requested = False
            mock_response.context_request_details = None
            mock_response.responded_at = datetime.utcnow()
            mock_response.confidence = 85.0
            
            mock_execution_result = {
                "execution_id": str(uuid4()),
                "status": "completed",
                "forwarded_at": datetime.utcnow().isoformat()
            }
            
            mock_orchestrator.process_approval_response.return_value = (mock_response, mock_execution_result)
            
            response = client.post(
                "/api/v1/human-loop/approval-responses",
                json=sample_approval_response_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["response_id"] == mock_response.response_id
            assert data["request_id"] == sample_approval_response_data["request_id"]
            assert data["decision"] == "approved"
            assert data["reasoning"] == "Action looks good, proceed"
            assert data["confidence"] == 85.0
            assert data["execution_result"] is not None
    
    def test_submit_approval_response_with_modification(self, client):
        """Test approval response with modified action."""
        response_data = {
            "request_id": str(uuid4()),
            "approver_id": "manager_1",
            "decision": "approved",
            "reasoning": "Approved with modifications",
            "modified_action": {
                "action_id": str(uuid4()),
                "action_type": "send_alert",
                "target_system": "notification_system",
                "parameters": {"alert_type": "urgent"},
                "expected_outcome": "Send urgent alert instead"
            },
            "confidence": 90.0
        }
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            mock_response = Mock()
            mock_response.response_id = str(uuid4())
            mock_response.request_id = response_data["request_id"]
            mock_response.approver_id = "manager_1"
            mock_response.decision = ApprovalStatus.APPROVED
            mock_response.reasoning = "Approved with modifications"
            mock_response.additional_context_requested = False
            mock_response.context_request_details = None
            mock_response.responded_at = datetime.utcnow()
            mock_response.confidence = 90.0
            
            mock_orchestrator.process_approval_response.return_value = (mock_response, None)
            
            response = client.post(
                "/api/v1/human-loop/approval-responses",
                json=response_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["decision"] == "approved"
            assert data["modified_action"] is not None
            assert data["modified_action"]["action_type"] == "send_alert"
    
    def test_get_approval_status_success(self, client):
        """Test getting approval status."""
        request_id = str(uuid4())
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock status response
            mock_orchestrator.get_approval_status.return_value = (ApprovalStatus.PENDING, None)
            
            # Mock active request
            mock_request = Mock()
            mock_request.request_id = request_id
            mock_request.approver_id = "manager_1"
            mock_request.status = ApprovalStatus.PENDING
            mock_request.created_at = datetime.utcnow()
            mock_request.expires_at = datetime.utcnow() + timedelta(minutes=30)
            mock_request.responded_at = None
            mock_request.escalated_at = None
            mock_request.escalated_to = None
            
            mock_orchestrator.get_active_requests.return_value = [mock_request]
            
            response = client.get(f"/api/v1/human-loop/approval-requests/{request_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["request_id"] == request_id
            assert data["status"] == "pending"
            assert data["approver_id"] == "manager_1"
            assert data["time_remaining_minutes"] is not None
    
    def test_get_approval_status_not_found(self, client):
        """Test getting status for non-existent request."""
        request_id = str(uuid4())
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            mock_orchestrator.get_approval_status.return_value = (ApprovalStatus.PENDING, None)
            mock_orchestrator.get_active_requests.return_value = []  # No requests found
            
            response = client.get(f"/api/v1/human-loop/approval-requests/{request_id}/status")
            
            assert response.status_code == 404
    
    def test_get_approval_history_success(self, client):
        """Test getting approval history."""
        request_id = str(uuid4())
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock sales manager with audit trail
            mock_sales_manager = Mock()
            mock_orchestrator.sales_manager = mock_sales_manager
            
            # Mock audit logs
            mock_audit_log = Mock()
            mock_audit_log.log_id = str(uuid4())
            mock_audit_log.event_type = "created"
            mock_audit_log.event_details = {"approver_id": "manager_1"}
            mock_audit_log.user_id = None
            mock_audit_log.timestamp = datetime.utcnow()
            mock_audit_log.system_generated = True
            
            mock_sales_manager.get_audit_trail.return_value = [mock_audit_log]
            mock_sales_manager.escalation_events = []
            
            response = client.get(f"/api/v1/human-loop/approval-requests/{request_id}/history")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["request_id"] == request_id
            assert len(data["audit_logs"]) == 1
            assert data["audit_logs"][0]["event_type"] == "created"
            assert data["total_events"] == 1
    
    def test_escalate_approval_request_success(self, client):
        """Test manual escalation of approval request."""
        request_id = str(uuid4())
        escalation_data = {
            "request_id": request_id,
            "escalate_to": "senior_manager",
            "reason": "High-value deal needs senior approval",
            "urgent": True
        }
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock current request
            mock_request = Mock()
            mock_request.request_id = request_id
            mock_request.approver_id = "manager_1"
            mock_request.status = ApprovalStatus.PENDING
            mock_request.escalated_at = None
            mock_request.escalated_to = None
            
            mock_orchestrator.get_active_requests.return_value = [mock_request]
            
            # Mock sales manager
            mock_sales_manager = Mock()
            mock_orchestrator.sales_manager = mock_sales_manager
            mock_sales_manager.escalation_events = []
            mock_sales_manager._log_audit_event = Mock()
            
            response = client.post(
                f"/api/v1/human-loop/approval-requests/{request_id}/escalate",
                json=escalation_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["request_id"] == request_id
            assert data["original_approver"] == "manager_1"
            assert data["escalated_to"] == "senior_manager"
            assert data["reason"] == "High-value deal needs senior approval"
            assert data["urgent"] is True
    
    def test_escalate_approval_request_not_found(self, client):
        """Test escalation of non-existent request."""
        request_id = str(uuid4())
        escalation_data = {
            "request_id": request_id,
            "escalate_to": "senior_manager",
            "reason": "Test escalation",
            "urgent": False
        }
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            mock_orchestrator.get_active_requests.return_value = []  # No requests found
            
            response = client.post(
                f"/api/v1/human-loop/approval-requests/{request_id}/escalate",
                json=escalation_data
            )
            
            assert response.status_code == 404
    
    def test_manage_approval_timeout_extend(self, client):
        """Test extending approval timeout."""
        request_id = str(uuid4())
        timeout_data = {
            "request_id": request_id,
            "action": "extend",
            "extension_minutes": 30,
            "reason": "Need more time for review"
        }
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock current request
            mock_request = Mock()
            mock_request.request_id = request_id
            mock_request.status = ApprovalStatus.PENDING
            mock_request.expires_at = datetime.utcnow() + timedelta(minutes=30)
            
            mock_orchestrator.get_active_requests.return_value = [mock_request]
            
            # Mock sales manager
            mock_sales_manager = Mock()
            mock_orchestrator.sales_manager = mock_sales_manager
            mock_sales_manager._log_audit_event = Mock()
            
            response = client.post(
                f"/api/v1/human-loop/approval-requests/{request_id}/timeout-management",
                json=timeout_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["request_id"] == request_id
            assert data["action_taken"] == "extend"
            assert data["new_expires_at"] is not None
    
    def test_manage_approval_timeout_escalate(self, client):
        """Test escalating via timeout management."""
        request_id = str(uuid4())
        timeout_data = {
            "request_id": request_id,
            "action": "escalate",
            "escalate_to": "vp_sales",
            "reason": "Timeout reached, escalating to VP"
        }
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock current request
            mock_request = Mock()
            mock_request.request_id = request_id
            mock_request.approver_id = "manager_1"
            mock_request.status = ApprovalStatus.PENDING
            
            mock_orchestrator.get_active_requests.return_value = [mock_request]
            
            # Mock sales manager
            mock_sales_manager = Mock()
            mock_orchestrator.sales_manager = mock_sales_manager
            mock_sales_manager.escalation_events = []
            
            response = client.post(
                f"/api/v1/human-loop/approval-requests/{request_id}/timeout-management",
                json=timeout_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["request_id"] == request_id
            assert data["action_taken"] == "escalate"
            assert data["escalated_to"] == "vp_sales"
    
    def test_list_approval_requests_success(self, client):
        """Test listing approval requests."""
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock requests
            mock_request1 = Mock()
            mock_request1.request_id = str(uuid4())
            mock_request1.approver_id = "manager_1"
            mock_request1.status = ApprovalStatus.PENDING
            mock_request1.priority = 1
            mock_request1.timeout_minutes = 60
            mock_request1.created_at = datetime.utcnow()
            mock_request1.expires_at = datetime.utcnow() + timedelta(minutes=60)
            mock_request1.escalation_rules = []
            
            # Mock nested objects
            mock_request1.pipeline_risk = Mock()
            mock_request1.pipeline_risk.risk_id = str(uuid4())
            mock_request1.pipeline_risk.risk_type = RiskType.STALLED_DEAL
            mock_request1.pipeline_risk.confidence = 85.0
            mock_request1.pipeline_risk.affected_deals = ["deal_1"]
            mock_request1.pipeline_risk.affected_leads = []
            mock_request1.pipeline_risk.severity = Severity.HIGH
            mock_request1.pipeline_risk.description = "Test risk"
            mock_request1.pipeline_risk.detected_at = datetime.utcnow()
            
            mock_request1.recommended_action = Mock()
            mock_request1.recommended_action.action_id = str(uuid4())
            mock_request1.recommended_action.action_type = SalesActionType.CREATE_TASK
            mock_request1.recommended_action.target_system = "workflow_engine"
            mock_request1.recommended_action.parameters = {}
            mock_request1.recommended_action.expected_outcome = "Test action"
            mock_request1.recommended_action.revenue_impact = None
            mock_request1.recommended_action.priority = 2
            mock_request1.recommended_action.created_at = datetime.utcnow()
            
            mock_request1.revenue_context = Mock()
            mock_request1.revenue_context.context_id = str(uuid4())
            mock_request1.revenue_context.deal_history = []
            mock_request1.revenue_context.similar_deals = []
            mock_request1.revenue_context.rep_performance = None
            mock_request1.revenue_context.sales_playbook_guidance = []
            mock_request1.revenue_context.confidence_score = 80.0
            mock_request1.revenue_context.generated_at = datetime.utcnow()
            
            mock_orchestrator.get_active_requests.return_value = [mock_request1]
            
            response = client.get("/api/v1/human-loop/approval-requests")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) == 1
            assert data[0]["request_id"] == mock_request1.request_id
            assert data[0]["status"] == "pending"
    
    def test_list_approval_requests_with_filters(self, client):
        """Test listing approval requests with filters."""
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            mock_orchestrator.get_active_requests.return_value = []
            
            response = client.get(
                "/api/v1/human-loop/approval-requests",
                params={"approver_id": "manager_1", "status": "pending", "limit": 10}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0
            
            # Verify filters were passed
            mock_orchestrator.get_active_requests.assert_called_with("manager_1", ApprovalStatus.PENDING)
    
    def test_get_approval_analytics_success(self, client):
        """Test getting approval analytics."""
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock requests for analytics
            mock_request1 = Mock()
            mock_request1.status = ApprovalStatus.APPROVED
            mock_request1.approver_id = "manager_1"
            mock_request1.created_at = datetime.utcnow() - timedelta(hours=2)
            mock_request1.responded_at = datetime.utcnow() - timedelta(hours=1)
            
            mock_request2 = Mock()
            mock_request2.status = ApprovalStatus.DENIED
            mock_request2.approver_id = "manager_2"
            mock_request2.created_at = datetime.utcnow() - timedelta(hours=3)
            mock_request2.responded_at = datetime.utcnow() - timedelta(hours=2)
            
            mock_orchestrator.get_active_requests.return_value = [mock_request1, mock_request2]
            mock_orchestrator.get_rejection_analytics.return_value = {
                "rejection_patterns": {},
                "recent_rejections": [],
                "total_rejection_logs": 1
            }
            
            response = client.get("/api/v1/human-loop/analytics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_requests"] == 2
            assert data["approved_requests"] == 1
            assert data["denied_requests"] == 1
            assert data["approval_rate"] == 50.0
            assert len(data["top_approvers"]) == 2
    
    def test_health_check_success(self, client):
        """Test health check endpoint."""
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            mock_orchestrator.get_active_requests.return_value = [Mock(), Mock()]  # 2 active requests
            
            response = client.get("/api/v1/human-loop/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["service"] == "human_loop"
            assert data["components"]["approval_orchestrator"] == "operational"
            assert data["metrics"]["active_requests"] == 2
    
    def test_invalid_timeout_action(self, client):
        """Test invalid timeout management action."""
        request_id = str(uuid4())
        timeout_data = {
            "request_id": request_id,
            "action": "invalid_action",
            "reason": "Test invalid action"
        }
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            mock_request = Mock()
            mock_request.request_id = request_id
            mock_request.status = ApprovalStatus.PENDING
            
            mock_orchestrator.get_active_requests.return_value = [mock_request]
            
            response = client.post(
                f"/api/v1/human-loop/approval-requests/{request_id}/timeout-management",
                json=timeout_data
            )
            
            assert response.status_code == 400
            assert "Invalid timeout action" in response.json()["detail"]
    
    def test_escalate_non_pending_request(self, client):
        """Test escalating a non-pending request."""
        request_id = str(uuid4())
        escalation_data = {
            "request_id": request_id,
            "escalate_to": "senior_manager",
            "reason": "Test escalation",
            "urgent": False
        }
        
        with patch('aboa.human_loop.api.get_approval_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = Mock()
            mock_get_orchestrator.return_value = mock_orchestrator
            
            # Mock request with non-pending status
            mock_request = Mock()
            mock_request.request_id = request_id
            mock_request.status = ApprovalStatus.APPROVED  # Already approved
            
            mock_orchestrator.get_active_requests.return_value = [mock_request]
            
            response = client.post(
                f"/api/v1/human-loop/approval-requests/{request_id}/escalate",
                json=escalation_data
            )
            
            assert response.status_code == 400
            assert "Cannot escalate request with status approved" in response.json()["detail"]