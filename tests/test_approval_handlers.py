"""
Tests for the Sales Approval Interface and Handlers.

This module tests the approval interface handlers including approval request
generation with pipeline context, multiple response options, approval forwarding
to sales action engine, and rejection logging and learning system.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from aboa.human_loop.approval_handlers import (
    ApprovalRequestGenerator,
    ApprovalResponseHandler,
    ApprovalInterfaceOrchestrator,
    ApprovalHandlerError
)
from aboa.human_loop.models import ApprovalRequest, ApprovalResponse
from aboa.human_loop.sales_manager_interface import SalesManagerInterface
from aboa.models.enums import (
    ApprovalStatus,
    DealStage,
    ExecutionStatus,
    LeadStatus,
    RiskType,
    SalesActionType,
    Severity
)
from aboa.models.revenue_entities import (
    ContactInfo,
    Deal,
    Lead,
    PipelineRisk,
    RevenueContext,
    SalesAction,
    SalesRep
)


class TestApprovalRequestGenerator:
    """Test the ApprovalRequestGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create approval request generator for testing."""
        return ApprovalRequestGenerator()
    
    @pytest.fixture
    def sample_pipeline_risk(self):
        """Create sample pipeline risk for testing."""
        return PipelineRisk(
            risk_id=str(uuid4()),
            risk_type=RiskType.STALLED_DEAL,
            confidence=85.0,
            affected_deals=["deal_1", "deal_2"],
            affected_leads=["lead_1"],
            severity=Severity.HIGH,
            description="Deals have been stalled for over 30 days"
        )
    
    @pytest.fixture
    def sample_recommended_action(self):
        """Create sample recommended action for testing."""
        return SalesAction(
            action_id=str(uuid4()),
            action_type=SalesActionType.CREATE_TASK,
            target_system="workflow_engine",
            parameters={"task_type": "follow_up", "priority": "high"},
            expected_outcome="Schedule follow-up meetings for stalled deals",
            revenue_impact=Decimal('50000')
        )
    
    @pytest.fixture
    def sample_deals(self):
        """Create sample deals for testing."""
        return [
            Deal(
                id="deal_1",
                stage=DealStage.PROPOSAL,
                value=Decimal('75000'),
                probability=60.0,
                close_date=datetime.utcnow() + timedelta(days=30),
                assigned_rep="rep_1",
                days_in_current_stage=35,
                contact_info=ContactInfo(
                    email="client1@example.com",
                    company="Client Corp",
                    first_name="John",
                    last_name="Doe"
                )
            ),
            Deal(
                id="deal_2",
                stage=DealStage.NEGOTIATION,
                value=Decimal('120000'),
                probability=80.0,
                close_date=datetime.utcnow() + timedelta(days=15),
                assigned_rep="rep_1",
                days_in_current_stage=20,
                contact_info=ContactInfo(
                    email="client2@example.com",
                    company="Big Client Inc",
                    first_name="Jane",
                    last_name="Smith"
                )
            )
        ]
    
    @pytest.fixture
    def sample_leads(self):
        """Create sample leads for testing."""
        return [
            Lead(
                id="lead_1",
                source="website",
                contact_info=ContactInfo(
                    email="prospect@example.com",
                    company="Prospect LLC",
                    first_name="Bob",
                    last_name="Johnson"
                ),
                status=LeadStatus.QUALIFIED,
                assigned_rep="rep_1",
                contact_attempts=2,
                estimated_value=Decimal('25000')
            )
        ]
    
    @pytest.fixture
    def sample_reps(self):
        """Create sample sales reps for testing."""
        return [
            SalesRep(
                id="rep_1",
                name="Alice Sales",
                email="alice@company.com",
                quota=Decimal('1000000'),
                quota_attainment=85.0,
                pipeline_value=Decimal('500000'),
                activities_this_week=15,
                avg_deal_velocity=45.0,
                conversion_rates={"qualification": 75.0, "proposal": 60.0}
            )
        ]
    
    def test_generate_approval_request_success(
        self, 
        generator, 
        sample_pipeline_risk, 
        sample_recommended_action,
        sample_deals, 
        sample_leads, 
        sample_reps
    ):
        """Test successful approval request generation."""
        approver_id = "manager_1"
        
        request = generator.generate_approval_request(
            pipeline_risk=sample_pipeline_risk,
            recommended_action=sample_recommended_action,
            deals=sample_deals,
            leads=sample_leads,
            reps=sample_reps,
            approver_id=approver_id
        )
        
        # Verify request structure
        assert isinstance(request, ApprovalRequest)
        assert request.pipeline_risk == sample_pipeline_risk
        assert request.recommended_action == sample_recommended_action
        assert request.approver_id == approver_id
        assert request.status == ApprovalStatus.PENDING
        
        # Verify revenue context is built
        assert request.revenue_context is not None
        assert len(request.revenue_context.deal_history) >= 0
        assert request.revenue_context.rep_performance is not None
        assert len(request.revenue_context.sales_playbook_guidance) > 0
        assert request.revenue_context.confidence_score > 0
    
    def test_build_revenue_context(
        self, 
        generator, 
        sample_pipeline_risk, 
        sample_deals, 
        sample_leads, 
        sample_reps
    ):
        """Test revenue context building."""
        context = generator._build_revenue_context(
            sample_pipeline_risk, sample_deals, sample_leads, sample_reps
        )
        
        assert isinstance(context, RevenueContext)
        assert context.context_id is not None
        assert context.confidence_score > 0
        assert len(context.sales_playbook_guidance) > 0
        
        # Should include rep performance for affected deals
        assert context.rep_performance is not None
        assert context.rep_performance.id == "rep_1"
    
    def test_generate_sales_guidance_by_risk_type(self, generator):
        """Test sales guidance generation for different risk types."""
        # Test stalled deal guidance
        stalled_risk = PipelineRisk(
            risk_id=str(uuid4()),
            risk_type=RiskType.STALLED_DEAL,
            confidence=80.0,
            affected_deals=["deal_1"],
            affected_leads=[],
            severity=Severity.HIGH,
            description="Deal stalled"
        )
        
        guidance = generator._generate_sales_guidance(stalled_risk, [], [])
        assert "Review deal progression checklist" in guidance
        assert "Schedule stakeholder alignment meeting" in guidance
        
        # Test missed follow-up guidance
        followup_risk = PipelineRisk(
            risk_id=str(uuid4()),
            risk_type=RiskType.MISSED_FOLLOWUP,
            confidence=75.0,
            affected_deals=["deal_1"],
            affected_leads=[],
            severity=Severity.MEDIUM,
            description="Missed follow-up"
        )
        
        guidance = generator._generate_sales_guidance(followup_risk, [], [])
        assert "Implement systematic follow-up cadence" in guidance
        assert "Set calendar reminders for all interactions" in guidance
    
    def test_calculate_context_confidence(self, generator, sample_deals, sample_reps):
        """Test context confidence calculation."""
        # Test with full context
        confidence = generator._calculate_context_confidence(
            deal_history=sample_deals,
            similar_deals=sample_deals[:1],
            rep_performance=sample_reps[0],
            sales_guidance=["guidance1", "guidance2"]
        )
        
        assert confidence >= 75.0  # Should be high with all data
        
        # Test with minimal context
        confidence = generator._calculate_context_confidence(
            deal_history=[],
            similar_deals=[],
            rep_performance=None,
            sales_guidance=[]
        )
        
        assert confidence == 0.0  # Should be low with no data


class TestApprovalResponseHandler:
    """Test the ApprovalResponseHandler class."""
    
    @pytest.fixture
    def mock_action_engine(self):
        """Create mock action engine for testing."""
        mock_engine = Mock()
        mock_engine.execute_action = AsyncMock(return_value={
            'execution_id': str(uuid4()),
            'status': ExecutionStatus.COMPLETED
        })
        return mock_engine
    
    @pytest.fixture
    def handler(self, mock_action_engine):
        """Create approval response handler for testing."""
        return ApprovalResponseHandler(action_engine=mock_action_engine)
    
    @pytest.fixture
    def sample_approval_request(self):
        """Create sample approval request for testing."""
        pipeline_risk = PipelineRisk(
            risk_id=str(uuid4()),
            risk_type=RiskType.STALLED_DEAL,
            confidence=85.0,
            affected_deals=["deal_1"],
            affected_leads=[],
            severity=Severity.HIGH,
            description="Deal stalled"
        )
        
        recommended_action = SalesAction(
            action_id=str(uuid4()),
            action_type=SalesActionType.CREATE_TASK,
            target_system="workflow_engine",
            parameters={"task_type": "follow_up"},
            expected_outcome="Create follow-up task",
            revenue_impact=Decimal('25000')
        )
        
        revenue_context = RevenueContext(
            context_id=str(uuid4()),
            deal_history=[],
            confidence_score=80.0
        )
        
        request = ApprovalRequest(
            request_id=str(uuid4()),
            pipeline_risk=pipeline_risk,
            recommended_action=recommended_action,
            revenue_context=revenue_context,
            approver_id="manager_1",
            timeout_minutes=60
        )
        
        # Add to handler's sales manager for testing
        handler = ApprovalResponseHandler(action_engine=Mock())
        handler.sales_manager.active_requests[request.request_id] = request
        
        return request, handler
    
    def test_handle_approval_response_approved(self, sample_approval_request):
        """Test handling approved response."""
        request, handler = sample_approval_request
        
        response, execution_result = handler.handle_approval_response(
            request_id=request.request_id,
            approver_id="manager_1",
            decision=ApprovalStatus.APPROVED,
            reasoning="Action looks good, proceed"
        )
        
        # Verify response
        assert isinstance(response, ApprovalResponse)
        assert response.decision == ApprovalStatus.APPROVED
        assert response.reasoning == "Action looks good, proceed"
        assert response.approver_id == "manager_1"
        
        # Verify execution result (simulated)
        assert execution_result is not None
        assert execution_result['status'] == ExecutionStatus.COMPLETED
    
    def test_handle_approval_response_denied(self, sample_approval_request):
        """Test handling denied response."""
        request, handler = sample_approval_request
        
        response, execution_result = handler.handle_approval_response(
            request_id=request.request_id,
            approver_id="manager_1",
            decision=ApprovalStatus.DENIED,
            reasoning="Risk assessment insufficient"
        )
        
        # Verify response
        assert response.decision == ApprovalStatus.DENIED
        assert response.reasoning == "Risk assessment insufficient"
        
        # Should not have execution result for denied
        assert execution_result is None
        
        # Should have logged rejection
        assert len(handler.rejection_logs) > 0
        rejection_log = handler.rejection_logs[0]
        assert rejection_log['reasoning'] == "Risk assessment insufficient"
        assert rejection_log['request_id'] == request.request_id
    
    def test_handle_approval_response_with_modification(self, sample_approval_request):
        """Test handling approved response with modified action."""
        request, handler = sample_approval_request
        
        # Create modified action
        modified_action = SalesAction(
            action_id=str(uuid4()),
            action_type=SalesActionType.SEND_ALERT,
            target_system="notification_system",
            parameters={"alert_type": "urgent"},
            expected_outcome="Send urgent alert instead"
        )
        
        response, execution_result = handler.handle_approval_response(
            request_id=request.request_id,
            approver_id="manager_1",
            decision=ApprovalStatus.APPROVED,
            reasoning="Approved with modification",
            modified_action=modified_action
        )
        
        # Verify response includes modification
        assert response.decision == ApprovalStatus.APPROVED
        assert response.modified_action == modified_action
        
        # Verify execution result indicates modification
        assert execution_result is not None
        assert execution_result['metadata']['modified_from_original'] is True
    
    def test_handle_context_request(self, sample_approval_request):
        """Test handling additional context request."""
        request, handler = sample_approval_request
        
        response, execution_result = handler.handle_approval_response(
            request_id=request.request_id,
            approver_id="manager_1",
            decision=ApprovalStatus.APPROVED,
            reasoning="Approved",
            additional_context_requested=True,
            context_request_details="Need more competitor analysis"
        )
        
        # Verify context request is recorded
        assert response.additional_context_requested is True
        assert response.context_request_details == "Need more competitor analysis"
    
    def test_update_learning_patterns(self, sample_approval_request):
        """Test learning pattern updates from rejections."""
        request, handler = sample_approval_request
        
        # Create rejection log
        rejection_log = {
            'request_id': request.request_id,
            'reasoning': "Insufficient data",
            'pipeline_risk': {
                'risk_type': 'stalled_deal',
                'severity': 'high',
                'confidence': 85.0
            },
            'recommended_action': {
                'action_type': 'create_task'
            }
        }
        
        # Update learning patterns
        handler._update_learning_patterns(rejection_log)
        
        # Verify pattern was created
        pattern_key = "stalled_deal_create_task"
        assert pattern_key in handler.learning_patterns
        
        pattern = handler.learning_patterns[pattern_key]
        assert pattern['rejection_count'] == 1
        assert pattern['total_requests'] == 1
        assert "Insufficient data" in pattern['common_reasons']
    
    def test_get_rejection_logs_with_filters(self, sample_approval_request):
        """Test getting rejection logs with filters."""
        request, handler = sample_approval_request
        
        # Add some rejection logs
        handler.rejection_logs = [
            {
                'request_id': 'req_1',
                'approver_id': 'manager_1',
                'pipeline_risk': {'risk_type': 'stalled_deal'},
                'denied_at': datetime.utcnow()
            },
            {
                'request_id': 'req_2',
                'approver_id': 'manager_2',
                'pipeline_risk': {'risk_type': 'missed_followup'},
                'denied_at': datetime.utcnow() - timedelta(hours=1)
            }
        ]
        
        # Test filtering by risk type
        stalled_logs = handler.get_rejection_logs(risk_type='stalled_deal')
        assert len(stalled_logs) == 1
        assert stalled_logs[0]['request_id'] == 'req_1'
        
        # Test filtering by approver
        manager1_logs = handler.get_rejection_logs(approver_id='manager_1')
        assert len(manager1_logs) == 1
        assert manager1_logs[0]['approver_id'] == 'manager_1'
        
        # Test limit
        limited_logs = handler.get_rejection_logs(limit=1)
        assert len(limited_logs) == 1
        # Should be most recent first
        assert limited_logs[0]['request_id'] == 'req_1'


class TestApprovalInterfaceOrchestrator:
    """Test the ApprovalInterfaceOrchestrator class."""
    
    @pytest.fixture
    def mock_action_engine(self):
        """Create mock action engine for testing."""
        return Mock()
    
    @pytest.fixture
    def orchestrator(self, mock_action_engine):
        """Create approval interface orchestrator for testing."""
        return ApprovalInterfaceOrchestrator(action_engine=mock_action_engine)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        pipeline_risk = PipelineRisk(
            risk_id=str(uuid4()),
            risk_type=RiskType.STALLED_DEAL,
            confidence=85.0,
            affected_deals=["deal_1"],
            affected_leads=[],
            severity=Severity.HIGH,
            description="Deal stalled"
        )
        
        recommended_action = SalesAction(
            action_id=str(uuid4()),
            action_type=SalesActionType.CREATE_TASK,
            target_system="workflow_engine",
            parameters={"task_type": "follow_up"},
            expected_outcome="Create follow-up task"
        )
        
        deals = [
            Deal(
                id="deal_1",
                stage=DealStage.PROPOSAL,
                value=Decimal('50000'),
                probability=70.0,
                close_date=datetime.utcnow() + timedelta(days=30),
                assigned_rep="rep_1"
            )
        ]
        
        leads = []
        
        reps = [
            SalesRep(
                id="rep_1",
                name="John Sales",
                email="john@company.com",
                quota=Decimal('500000'),
                quota_attainment=80.0
            )
        ]
        
        return pipeline_risk, recommended_action, deals, leads, reps
    
    def test_create_approval_request(self, orchestrator, sample_data):
        """Test creating approval request through orchestrator."""
        pipeline_risk, recommended_action, deals, leads, reps = sample_data
        
        request = orchestrator.create_approval_request(
            pipeline_risk=pipeline_risk,
            recommended_action=recommended_action,
            deals=deals,
            leads=leads,
            reps=reps,
            approver_id="manager_1"
        )
        
        assert isinstance(request, ApprovalRequest)
        assert request.pipeline_risk == pipeline_risk
        assert request.recommended_action == recommended_action
        assert request.approver_id == "manager_1"
    
    def test_process_approval_response(self, orchestrator, sample_data):
        """Test processing approval response through orchestrator."""
        pipeline_risk, recommended_action, deals, leads, reps = sample_data
        
        # First create a request
        request = orchestrator.create_approval_request(
            pipeline_risk=pipeline_risk,
            recommended_action=recommended_action,
            deals=deals,
            leads=leads,
            reps=reps,
            approver_id="manager_1"
        )
        
        # Then process response
        response, execution_result = orchestrator.process_approval_response(
            request_id=request.request_id,
            approver_id="manager_1",
            decision=ApprovalStatus.APPROVED,
            reasoning="Looks good"
        )
        
        assert isinstance(response, ApprovalResponse)
        assert response.decision == ApprovalStatus.APPROVED
        assert response.reasoning == "Looks good"
    
    def test_get_rejection_analytics(self, orchestrator):
        """Test getting rejection analytics."""
        # Add some test data to response handler
        orchestrator.response_handler.rejection_logs = [
            {
                'request_id': 'req_1',
                'reasoning': 'Test rejection',
                'denied_at': datetime.utcnow()
            }
        ]
        
        orchestrator.response_handler.learning_patterns = {
            'test_pattern': {
                'rejection_count': 5,
                'total_requests': 10
            }
        }
        
        analytics = orchestrator.get_rejection_analytics()
        
        assert 'rejection_patterns' in analytics
        assert 'recent_rejections' in analytics
        assert 'total_rejection_logs' in analytics
        assert analytics['total_rejection_logs'] == 1


class TestApprovalHandlerIntegration:
    """Integration tests for approval handlers."""
    
    def test_end_to_end_approval_workflow(self):
        """Test complete approval workflow from request to execution."""
        # Create orchestrator with mock action engine
        mock_action_engine = Mock()
        orchestrator = ApprovalInterfaceOrchestrator(action_engine=mock_action_engine)
        
        # Create test data
        pipeline_risk = PipelineRisk(
            risk_id=str(uuid4()),
            risk_type=RiskType.STALLED_DEAL,
            confidence=90.0,
            affected_deals=["deal_1"],
            affected_leads=[],
            severity=Severity.HIGH,
            description="High-value deal stalled"
        )
        
        recommended_action = SalesAction(
            action_id=str(uuid4()),
            action_type=SalesActionType.CREATE_TASK,
            target_system="workflow_engine",
            parameters={"task_type": "urgent_follow_up"},
            expected_outcome="Create urgent follow-up task",
            revenue_impact=Decimal('100000')
        )
        
        deals = [
            Deal(
                id="deal_1",
                stage=DealStage.NEGOTIATION,
                value=Decimal('100000'),
                probability=85.0,
                close_date=datetime.utcnow() + timedelta(days=15),
                assigned_rep="rep_1",
                days_in_current_stage=25
            )
        ]
        
        reps = [
            SalesRep(
                id="rep_1",
                name="Top Performer",
                email="top@company.com",
                quota=Decimal('1000000'),
                quota_attainment=95.0,
                pipeline_value=Decimal('800000')
            )
        ]
        
        # Step 1: Create approval request
        request = orchestrator.create_approval_request(
            pipeline_risk=pipeline_risk,
            recommended_action=recommended_action,
            deals=deals,
            leads=[],
            reps=reps,
            approver_id="senior_manager"
        )
        
        # Verify request was created with proper context
        assert request.pipeline_risk.severity == Severity.HIGH
        assert request.revenue_context.confidence_score > 0
        assert len(request.revenue_context.sales_playbook_guidance) > 0
        
        # Step 2: Process approval (approved)
        response, execution_result = orchestrator.process_approval_response(
            request_id=request.request_id,
            approver_id="senior_manager",
            decision=ApprovalStatus.APPROVED,
            reasoning="High-value deal needs immediate attention"
        )
        
        # Verify approval was processed
        assert response.decision == ApprovalStatus.APPROVED
        assert execution_result is not None
        assert execution_result['status'] == ExecutionStatus.COMPLETED
        
        # Step 3: Check status
        status, _ = orchestrator.get_approval_status(request.request_id)
        assert status == ApprovalStatus.APPROVED
    
    def test_rejection_learning_workflow(self):
        """Test rejection and learning workflow."""
        orchestrator = ApprovalInterfaceOrchestrator()
        
        # Create multiple similar requests that get rejected
        for i in range(3):
            pipeline_risk = PipelineRisk(
                risk_id=str(uuid4()),
                risk_type=RiskType.LOW_ACTIVITY,
                confidence=60.0,  # Low confidence
                affected_deals=[f"deal_{i}"],
                affected_leads=[],
                severity=Severity.MEDIUM,
                description=f"Low activity detected {i}"
            )
            
            recommended_action = SalesAction(
                action_id=str(uuid4()),
                action_type=SalesActionType.ASSIGN_REP,
                target_system="crm_system",
                parameters={"new_rep": "rep_2"},
                expected_outcome="Reassign to more active rep"
            )
            
            # Create and reject request
            request = orchestrator.create_approval_request(
                pipeline_risk=pipeline_risk,
                recommended_action=recommended_action,
                deals=[],
                leads=[],
                reps=[],
                approver_id="manager_1"
            )
            
            orchestrator.process_approval_response(
                request_id=request.request_id,
                approver_id="manager_1",
                decision=ApprovalStatus.DENIED,
                reasoning="Low confidence, need more data"
            )
        
        # Check learning patterns
        analytics = orchestrator.get_rejection_analytics()
        patterns = analytics['rejection_patterns']
        
        # Should have learned pattern for low_activity + assign_rep rejections
        pattern_key = "low_activity_assign_rep"
        if pattern_key in patterns:
            pattern = patterns[pattern_key]
            assert pattern['rejection_count'] == 3
            assert "Low confidence, need more data" in pattern['common_reasons']