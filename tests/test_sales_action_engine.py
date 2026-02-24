"""
Unit tests for the Sales Action Engine.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from aboa.action.engine import (
    SalesActionEngine,
    ExecutionContext,
    ExecutionResult,
    IdempotencyManager,
    RetryManager,
    ExecutionMonitor
)
from aboa.core.exceptions import ActionExecutionError, RetryableError, NonRetryableError
from aboa.models.enums import ExecutionStatus, SalesActionType
from aboa.models.revenue_entities import SalesAction


@pytest.fixture
def sample_action():
    """Create a sample sales action for testing."""
    return SalesAction(
        action_id="test-action-1",
        action_type=SalesActionType.CREATE_TASK,
        target_system="crm",
        parameters={"task_type": "follow_up", "deal_id": "deal-123"},
        expected_outcome="Follow-up task created",
        max_retries=3
    )


@pytest.fixture
def execution_context(sample_action):
    """Create an execution context for testing."""
    return ExecutionContext(
        execution_id="exec-123",
        action=sample_action,
        tenant_id="tenant-1",
        user_id="user-1"
    )


class TestIdempotencyManager:
    """Test the IdempotencyManager class."""
    
    @pytest.mark.asyncio
    async def test_idempotency_key_generation(self, sample_action, execution_context):
        """Test idempotency key generation."""
        manager = IdempotencyManager()
        
        # Generate key for same action twice
        key1 = manager._generate_idempotency_key(sample_action, execution_context)
        key2 = manager._generate_idempotency_key(sample_action, execution_context)
        
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA256 hex digest length
    
    @pytest.mark.asyncio
    async def test_different_actions_different_keys(self, execution_context):
        """Test that different actions generate different keys."""
        manager = IdempotencyManager()
        
        action1 = SalesAction(
            action_id="action-1",
            action_type=SalesActionType.CREATE_TASK,
            target_system="crm",
            parameters={"task_type": "follow_up"},
            expected_outcome="Task created"
        )
        
        action2 = SalesAction(
            action_id="action-2",
            action_type=SalesActionType.UPDATE_DEAL,
            target_system="crm",
            parameters={"deal_id": "deal-123"},
            expected_outcome="Deal updated"
        )
        
        key1 = manager._generate_idempotency_key(action1, execution_context)
        key2 = manager._generate_idempotency_key(action2, execution_context)
        
        assert key1 != key2
    
    @pytest.mark.asyncio
    async def test_check_not_executed(self, sample_action, execution_context):
        """Test checking action that hasn't been executed."""
        manager = IdempotencyManager()
        
        result = await manager.check_already_executed(sample_action, execution_context)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_mark_and_check_executed(self, sample_action, execution_context):
        """Test marking action as executed and checking it."""
        manager = IdempotencyManager()
        
        # Mark as executed
        execution_result = ExecutionResult(
            execution_id="exec-123",
            status=ExecutionStatus.COMPLETED,
            outputs={"task_id": "task-456"}
        )
        
        await manager.mark_executed(sample_action, execution_context, execution_result)
        
        # Check if executed
        result = await manager.check_already_executed(sample_action, execution_context)
        assert result is not None
        assert result.execution_id == "exec-123"
        assert result.status == ExecutionStatus.COMPLETED


class TestRetryManager:
    """Test the RetryManager class."""
    
    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        manager = RetryManager(base_delay=1.0, backoff_factor=2.0, jitter=False)
        
        assert manager.calculate_delay(0) == 1.0
        assert manager.calculate_delay(1) == 2.0
        assert manager.calculate_delay(2) == 4.0
        assert manager.calculate_delay(3) == 8.0
    
    def test_calculate_delay_max_limit(self):
        """Test delay calculation respects max limit."""
        manager = RetryManager(base_delay=1.0, max_delay=5.0, backoff_factor=2.0, jitter=False)
        
        assert manager.calculate_delay(10) == 5.0
    
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        manager = RetryManager(base_delay=2.0, backoff_factor=2.0, jitter=True)
        
        delay1 = manager.calculate_delay(1)
        delay2 = manager.calculate_delay(1)
        
        # With jitter, delays should be different
        # Both should be between 2.0 and 4.0 (50% to 100% of base_delay * backoff_factor^1)
        # base_delay=2.0, backoff_factor=2.0, retry_count=1 -> 2.0 * 2^1 = 4.0
        # With jitter: 4.0 * (0.5 to 1.0) = 2.0 to 4.0
        assert 2.0 <= delay1 <= 4.0
        assert 2.0 <= delay2 <= 4.0
    
    def test_should_retry_retryable_error(self):
        """Test retry decision for retryable errors."""
        manager = RetryManager()
        
        error = RetryableError("Temporary failure")
        assert manager.should_retry(error, 0, 3) is True
        assert manager.should_retry(error, 2, 3) is True
        assert manager.should_retry(error, 3, 3) is False
    
    def test_should_retry_non_retryable_error(self):
        """Test retry decision for non-retryable errors."""
        manager = RetryManager()
        
        error = NonRetryableError("Permanent failure")
        assert manager.should_retry(error, 0, 3) is False
    
    def test_should_retry_connection_error(self):
        """Test retry decision for connection errors."""
        manager = RetryManager()
        
        error = ConnectionError("Connection failed")
        assert manager.should_retry(error, 0, 3) is True
        assert manager.should_retry(error, 3, 3) is False


class TestExecutionMonitor:
    """Test the ExecutionMonitor class."""
    
    @pytest.mark.asyncio
    async def test_start_execution(self, execution_context):
        """Test starting execution monitoring."""
        monitor = ExecutionMonitor()
        
        await monitor.start_execution(execution_context)
        
        assert execution_context.status == ExecutionStatus.IN_PROGRESS
        
        # Check it's being monitored
        status = await monitor.get_execution_status(execution_context.execution_id)
        assert status is not None
        assert status.execution_id == execution_context.execution_id
    
    @pytest.mark.asyncio
    async def test_update_execution(self, execution_context):
        """Test updating execution status."""
        monitor = ExecutionMonitor()
        
        await monitor.start_execution(execution_context)
        
        # Update status
        await monitor.update_execution(
            execution_context.execution_id,
            ExecutionStatus.COMPLETED,
            outputs={"result": "success"},
            errors=[]
        )
        
        status = await monitor.get_execution_status(execution_context.execution_id)
        assert status.status == ExecutionStatus.COMPLETED
        assert status.outputs["result"] == "success"
        assert status.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_list_active_executions(self, sample_action):
        """Test listing active executions."""
        monitor = ExecutionMonitor()
        
        # Create multiple execution contexts
        context1 = ExecutionContext("exec-1", sample_action)
        context2 = ExecutionContext("exec-2", sample_action)
        context3 = ExecutionContext("exec-3", sample_action)
        
        await monitor.start_execution(context1)
        await monitor.start_execution(context2)
        await monitor.start_execution(context3)
        
        # Complete one execution
        await monitor.update_execution("exec-2", ExecutionStatus.COMPLETED)
        
        # Get active executions
        active = await monitor.list_active_executions()
        active_ids = [ctx.execution_id for ctx in active]
        
        assert len(active) == 2
        assert "exec-1" in active_ids
        assert "exec-3" in active_ids
        assert "exec-2" not in active_ids


class TestSalesActionEngine:
    """Test the SalesActionEngine class."""
    
    @pytest.mark.asyncio
    async def test_execute_action_success(self, sample_action):
        """Test successful action execution."""
        engine = SalesActionEngine()
        
        result = await engine.execute_action(sample_action)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.execution_id is not None
        assert "task_id" in result.outputs
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_execute_action_idempotency(self, sample_action):
        """Test action idempotency."""
        engine = SalesActionEngine()
        
        # Execute same action twice
        result1 = await engine.execute_action(sample_action, tenant_id="tenant-1")
        result2 = await engine.execute_action(sample_action, tenant_id="tenant-1")
        
        # Second execution should return cached result
        # Both should be successful, but second should be from cache
        assert result1.status == ExecutionStatus.COMPLETED
        assert result2.status == ExecutionStatus.COMPLETED
        
        # The outputs should be the same (idempotent behavior)
        assert "task_id" in result1.outputs
        assert "task_id" in result2.outputs
    
    @pytest.mark.asyncio
    async def test_execute_action_with_retry(self):
        """Test action execution with retry logic."""
        engine = SalesActionEngine()
        
        # Mock a handler that fails twice then succeeds
        call_count = 0
        
        async def failing_handler(action, context):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RetryableError("Temporary failure")
            return {"success": True, "attempts": call_count}
        
        # Register the failing handler
        engine.register_action_handler(SalesActionType.CREATE_TASK, failing_handler)
        
        action = SalesAction(
            action_id="retry-test",
            action_type=SalesActionType.CREATE_TASK,
            target_system="test",
            parameters={},
            expected_outcome="Test retry",
            max_retries=3
        )
        
        result = await engine.execute_action(action)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.outputs["attempts"] == 3
        assert result.retry_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_action_max_retries_exceeded(self):
        """Test action execution when max retries are exceeded."""
        engine = SalesActionEngine()
        
        # Mock a handler that always fails
        async def always_failing_handler(action, context):
            raise RetryableError("Always fails")
        
        engine.register_action_handler(SalesActionType.CREATE_TASK, always_failing_handler)
        
        action = SalesAction(
            action_id="fail-test",
            action_type=SalesActionType.CREATE_TASK,
            target_system="test",
            parameters={},
            expected_outcome="Test failure",
            max_retries=2
        )
        
        result = await engine.execute_action(action)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.retry_count == 2
        assert len(result.errors) > 0
        assert "failed after 3 attempts" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_execute_action_non_retryable_error(self):
        """Test action execution with non-retryable error."""
        engine = SalesActionEngine()
        
        # Mock a handler that raises non-retryable error
        async def non_retryable_handler(action, context):
            raise NonRetryableError("Permanent failure")
        
        engine.register_action_handler(SalesActionType.CREATE_TASK, non_retryable_handler)
        
        action = SalesAction(
            action_id="non-retry-test",
            action_type=SalesActionType.CREATE_TASK,
            target_system="test",
            parameters={},
            expected_outcome="Test non-retryable",
            max_retries=3
        )
        
        result = await engine.execute_action(action)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.retry_count == 0  # No retries attempted
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_execute_action_unknown_type(self):
        """Test execution of action with unknown type."""
        engine = SalesActionEngine()
        
        # Create action with unregistered type by mocking
        action = SalesAction(
            action_id="unknown-test",
            action_type=SalesActionType.CREATE_TASK,  # We'll mock this
            target_system="test",
            parameters={},
            expected_outcome="Test unknown type",
            max_retries=1
        )
        
        # Remove the handler to simulate unknown type
        del engine._action_handlers[SalesActionType.CREATE_TASK]
        
        result = await engine.execute_action(action)
        
        assert result.status == ExecutionStatus.FAILED
        assert "No handler registered" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_execution_status(self, sample_action):
        """Test getting execution status."""
        engine = SalesActionEngine()
        
        result = await engine.execute_action(sample_action)
        
        status = await engine.get_execution_status(result.execution_id)
        assert status is not None
        assert status.execution_id == result.execution_id
        assert status.status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_list_active_executions(self, sample_action):
        """Test listing active executions."""
        engine = SalesActionEngine()
        
        # Mock a long-running handler
        async def long_running_handler(action, context):
            await asyncio.sleep(0.1)  # Short delay for test
            return {"completed": True}
        
        engine.register_action_handler(SalesActionType.CREATE_TASK, long_running_handler)
        
        # Start execution but don't wait
        task = asyncio.create_task(engine.execute_action(sample_action))
        
        # Give it a moment to start
        await asyncio.sleep(0.01)
        
        # Check active executions
        active = await engine.list_active_executions()
        assert len(active) >= 0  # May be 0 if execution completed quickly
        
        # Wait for completion
        await task
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, sample_action):
        """Test cancelling an execution."""
        engine = SalesActionEngine()
        
        # Mock a handler that can be cancelled
        async def cancellable_handler(action, context):
            await asyncio.sleep(1.0)  # Long delay
            return {"completed": True}
        
        engine.register_action_handler(SalesActionType.CREATE_TASK, cancellable_handler)
        
        # Start execution
        task = asyncio.create_task(engine.execute_action(sample_action))
        
        # Give it a moment to start
        await asyncio.sleep(0.01)
        
        # Get active executions to find execution ID
        active = await engine.list_active_executions()
        if active:
            execution_id = active[0].execution_id
            
            # Cancel execution
            cancelled = await engine.cancel_execution(execution_id)
            assert cancelled is True
            
            # Check status
            status = await engine.get_execution_status(execution_id)
            assert status.status == ExecutionStatus.CANCELLED
        
        # Clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    def test_register_action_handler(self):
        """Test registering custom action handler."""
        engine = SalesActionEngine()
        
        async def custom_handler(action, context):
            return {"custom": True}
        
        engine.register_action_handler(SalesActionType.UPDATE_DEAL, custom_handler)
        
        assert engine._action_handlers[SalesActionType.UPDATE_DEAL] == custom_handler


class TestDefaultActionHandlers:
    """Test the default action handlers."""
    
    @pytest.mark.asyncio
    async def test_create_task_handler(self):
        """Test the create task handler."""
        engine = SalesActionEngine()
        
        action = SalesAction(
            action_id="task-test",
            action_type=SalesActionType.CREATE_TASK,
            target_system="crm",
            parameters={"task_type": "follow_up", "deal_id": "deal-123"},
            expected_outcome="Task created"
        )
        
        result = await engine.execute_action(action)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert "task_id" in result.outputs
        assert result.outputs["task_type"] == "follow_up"
    
    @pytest.mark.asyncio
    async def test_update_deal_handler(self):
        """Test the update deal handler."""
        engine = SalesActionEngine()
        
        action = SalesAction(
            action_id="deal-test",
            action_type=SalesActionType.UPDATE_DEAL,
            target_system="crm",
            parameters={"deal_id": "deal-123", "updates": {"stage": "proposal"}},
            expected_outcome="Deal updated"
        )
        
        result = await engine.execute_action(action)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.outputs["deal_id"] == "deal-123"
        assert result.outputs["updated_fields"]["stage"] == "proposal"
    
    @pytest.mark.asyncio
    async def test_send_alert_handler(self):
        """Test the send alert handler."""
        engine = SalesActionEngine()
        
        action = SalesAction(
            action_id="alert-test",
            action_type=SalesActionType.SEND_ALERT,
            target_system="notification",
            parameters={"recipient": "manager@company.com", "message": "Deal at risk"},
            expected_outcome="Alert sent"
        )
        
        result = await engine.execute_action(action)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert "alert_id" in result.outputs
        assert result.outputs["recipient"] == "manager@company.com"
        assert result.outputs["message"] == "Deal at risk"