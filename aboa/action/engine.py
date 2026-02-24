"""
Sales Action Engine for executing revenue operations actions.

This module implements the core action execution framework with orchestration,
idempotency management, monitoring, and retry logic with exponential backoff.
"""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from ..core.exceptions import ActionExecutionError, RetryableError, NonRetryableError
from ..core.logging import get_logger
from ..models.enums import ExecutionStatus, SalesActionType
from ..models.revenue_entities import SalesAction

logger = get_logger(__name__)


class ExecutionContext:
    """Context for action execution with tracking and metadata."""
    
    def __init__(
        self,
        execution_id: str,
        action: SalesAction,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.execution_id = execution_id
        self.action = action
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.metadata = metadata or {}
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.status = ExecutionStatus.PENDING
        self.outputs: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.retry_count = 0


class ExecutionResult:
    """Result of action execution with status and outputs."""
    
    def __init__(
        self,
        execution_id: str,
        status: ExecutionStatus,
        outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        duration: Optional[timedelta] = None,
        retry_count: int = 0
    ):
        self.execution_id = execution_id
        self.status = status
        self.outputs = outputs or {}
        self.errors = errors or []
        self.duration = duration
        self.retry_count = retry_count
        self.completed_at = datetime.utcnow()


class IdempotencyManager:
    """Manages idempotency to prevent duplicate action execution."""
    
    def __init__(self):
        self._executed_actions: Set[str] = set()
        self._execution_results: Dict[str, ExecutionResult] = {}
        self._lock = asyncio.Lock()
    
    def _generate_idempotency_key(self, action: SalesAction, context: ExecutionContext) -> str:
        """Generate idempotency key based on action and context."""
        # Create a hash of action parameters and context to ensure uniqueness
        key_data = {
            'action_id': action.action_id,
            'action_type': action.action_type.value,
            'target_system': action.target_system,
            'parameters': action.parameters,
            'tenant_id': context.tenant_id
        }
        
        # Convert to string and hash
        key_string = str(sorted(key_data.items()))
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    async def check_already_executed(
        self, 
        action: SalesAction, 
        context: ExecutionContext
    ) -> Optional[ExecutionResult]:
        """Check if action has already been executed successfully."""
        async with self._lock:
            idempotency_key = self._generate_idempotency_key(action, context)
            
            if idempotency_key in self._executed_actions:
                logger.info(
                    f"Action {action.action_id} already executed (idempotency key: {idempotency_key})"
                )
                return self._execution_results.get(idempotency_key)
            
            return None
    
    async def mark_executed(
        self, 
        action: SalesAction, 
        context: ExecutionContext, 
        result: ExecutionResult
    ) -> None:
        """Mark action as executed with result."""
        async with self._lock:
            idempotency_key = self._generate_idempotency_key(action, context)
            
            if result.status == ExecutionStatus.COMPLETED:
                self._executed_actions.add(idempotency_key)
                self._execution_results[idempotency_key] = result
                logger.info(
                    f"Marked action {action.action_id} as executed (idempotency key: {idempotency_key})"
                )


class RetryManager:
    """Manages retry logic with exponential backoff."""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for retry attempt with exponential backoff."""
        delay = self.base_delay * (self.backoff_factor ** retry_count)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add jitter to prevent thundering herd
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, error: Exception, retry_count: int, max_retries: int) -> bool:
        """Determine if error should be retried."""
        if retry_count >= max_retries:
            return False
        
        # Don't retry non-retryable errors
        if isinstance(error, NonRetryableError):
            return False
        
        # Retry retryable errors and certain common exceptions
        if isinstance(error, (RetryableError, ConnectionError, TimeoutError)):
            return True
        
        # Don't retry validation errors or other client errors
        return False


class ExecutionMonitor:
    """Monitors action execution status and provides tracking."""
    
    def __init__(self):
        self._executions: Dict[str, ExecutionContext] = {}
        self._lock = asyncio.Lock()
    
    async def start_execution(self, context: ExecutionContext) -> None:
        """Start monitoring an execution."""
        async with self._lock:
            context.status = ExecutionStatus.IN_PROGRESS
            self._executions[context.execution_id] = context
            logger.info(f"Started monitoring execution {context.execution_id}")
    
    async def update_execution(
        self, 
        execution_id: str, 
        status: ExecutionStatus,
        outputs: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None
    ) -> None:
        """Update execution status and details."""
        async with self._lock:
            if execution_id in self._executions:
                context = self._executions[execution_id]
                context.status = status
                
                if outputs:
                    context.outputs.update(outputs)
                
                if errors:
                    context.errors.extend(errors)
                
                if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                    context.completed_at = datetime.utcnow()
                
                logger.info(f"Updated execution {execution_id} status to {status.value}")
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get current execution status."""
        async with self._lock:
            return self._executions.get(execution_id)
    
    async def list_active_executions(self) -> List[ExecutionContext]:
        """List all active executions."""
        async with self._lock:
            return [
                context for context in self._executions.values()
                if context.status in [ExecutionStatus.PENDING, ExecutionStatus.IN_PROGRESS, ExecutionStatus.RETRYING]
            ]


class SalesActionEngine:
    """
    Core sales action execution engine with orchestration, idempotency, 
    monitoring, and retry capabilities.
    """
    
    def __init__(
        self,
        idempotency_manager: Optional[IdempotencyManager] = None,
        retry_manager: Optional[RetryManager] = None,
        execution_monitor: Optional[ExecutionMonitor] = None
    ):
        self.idempotency_manager = idempotency_manager or IdempotencyManager()
        self.retry_manager = retry_manager or RetryManager()
        self.execution_monitor = execution_monitor or ExecutionMonitor()
        self._action_handlers: Dict[SalesActionType, callable] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self) -> None:
        """Setup default action handlers for different action types."""
        self._action_handlers = {
            SalesActionType.CREATE_TASK: self._handle_create_task,
            SalesActionType.UPDATE_DEAL: self._handle_update_deal,
            SalesActionType.SEND_ALERT: self._handle_send_alert,
            SalesActionType.SCHEDULE_FOLLOWUP: self._handle_schedule_followup,
            SalesActionType.UPDATE_LEAD_STATUS: self._handle_update_lead_status,
            SalesActionType.ASSIGN_REP: self._handle_assign_rep,
            SalesActionType.CREATE_FOLLOWUP_MESSAGE: self._handle_create_followup_message,
            SalesActionType.UPDATE_OPPORTUNITY_FLAG: self._handle_update_opportunity_flag,
        }
    
    def register_action_handler(self, action_type: SalesActionType, handler: callable) -> None:
        """Register a custom action handler."""
        self._action_handlers[action_type] = handler
        logger.info(f"Registered handler for action type {action_type.value}")
    
    async def execute_action(
        self,
        action: SalesAction,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute a sales action with full orchestration, idempotency, and retry logic.
        
        Args:
            action: The sales action to execute
            tenant_id: Optional tenant identifier for multi-tenant support
            user_id: Optional user identifier for audit trail
            metadata: Optional additional metadata for execution context
        
        Returns:
            ExecutionResult with status, outputs, and execution details
        """
        execution_id = str(uuid4())
        context = ExecutionContext(
            execution_id=execution_id,
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=metadata
        )
        
        try:
            # Check idempotency
            existing_result = await self.idempotency_manager.check_already_executed(action, context)
            if existing_result:
                logger.info(f"Returning cached result for action {action.action_id}")
                return existing_result
            
            # Start monitoring
            await self.execution_monitor.start_execution(context)
            
            # Execute with retry logic
            result = await self._execute_with_retry(context)
            
            # Mark as executed for idempotency
            if result.status == ExecutionStatus.COMPLETED:
                await self.idempotency_manager.mark_executed(action, context, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error executing action {action.action_id}: {str(e)}", exc_info=e)
            
            # Update monitoring
            await self.execution_monitor.update_execution(
                execution_id,
                ExecutionStatus.FAILED,
                errors=[f"Unexpected error: {str(e)}"]
            )
            
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                errors=[f"Unexpected error: {str(e)}"],
                duration=datetime.utcnow() - context.started_at,
                retry_count=context.retry_count
            )
    
    async def _execute_with_retry(self, context: ExecutionContext) -> ExecutionResult:
        """Execute action with retry logic."""
        action = context.action
        last_error = None
        
        for attempt in range(action.max_retries + 1):
            context.retry_count = attempt
            
            try:
                if attempt > 0:
                    # Update status to retrying
                    await self.execution_monitor.update_execution(
                        context.execution_id,
                        ExecutionStatus.RETRYING
                    )
                    
                    # Calculate and wait for retry delay
                    delay = self.retry_manager.calculate_delay(attempt - 1)
                    logger.info(f"Retrying action {action.action_id} in {delay:.2f} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                
                # Execute the action
                result = await self._execute_action_handler(context)
                
                # Update monitoring with success
                await self.execution_monitor.update_execution(
                    context.execution_id,
                    ExecutionStatus.COMPLETED,
                    outputs=result.outputs
                )
                
                logger.info(f"Successfully executed action {action.action_id} on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Action {action.action_id} failed on attempt {attempt + 1}: {str(e)}")
                
                # Check if we should retry
                if not self.retry_manager.should_retry(e, attempt, action.max_retries):
                    break
        
        # All retries exhausted
        error_msg = f"Action failed after {action.max_retries + 1} attempts: {str(last_error)}"
        
        await self.execution_monitor.update_execution(
            context.execution_id,
            ExecutionStatus.FAILED,
            errors=[error_msg]
        )
        
        return ExecutionResult(
            execution_id=context.execution_id,
            status=ExecutionStatus.FAILED,
            errors=[error_msg],
            duration=datetime.utcnow() - context.started_at,
            retry_count=context.retry_count
        )
    
    async def _execute_action_handler(self, context: ExecutionContext) -> ExecutionResult:
        """Execute the specific action handler."""
        action = context.action
        
        # Get handler for action type
        handler = self._action_handlers.get(action.action_type)
        if not handler:
            raise ActionExecutionError(
                f"No handler registered for action type {action.action_type.value}",
                error_code="HANDLER_NOT_FOUND"
            )
        
        # Execute handler
        start_time = datetime.utcnow()
        outputs = await handler(action, context)
        duration = datetime.utcnow() - start_time
        
        return ExecutionResult(
            execution_id=context.execution_id,
            status=ExecutionStatus.COMPLETED,
            outputs=outputs,
            duration=duration,
            retry_count=context.retry_count
        )
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get current execution status."""
        return await self.execution_monitor.get_execution_status(execution_id)
    
    async def list_active_executions(self) -> List[ExecutionContext]:
        """List all active executions."""
        return await self.execution_monitor.list_active_executions()
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution."""
        context = await self.execution_monitor.get_execution_status(execution_id)
        if context and context.status in [ExecutionStatus.PENDING, ExecutionStatus.IN_PROGRESS]:
            await self.execution_monitor.update_execution(
                execution_id,
                ExecutionStatus.CANCELLED
            )
            logger.info(f"Cancelled execution {execution_id}")
            return True
        return False
    
    # Default action handlers (placeholder implementations)
    
    async def _handle_create_task(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle task creation action."""
        logger.info(f"Creating task for action {action.action_id}")
        # Placeholder implementation - would integrate with task management system
        return {
            "task_id": str(uuid4()),
            "task_type": "follow_up",
            "created_at": datetime.utcnow().isoformat(),
            "parameters": action.parameters
        }
    
    async def _handle_update_deal(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle deal update action."""
        logger.info(f"Updating deal for action {action.action_id}")
        # Placeholder implementation - would integrate with CRM system
        return {
            "deal_id": action.parameters.get("deal_id"),
            "updated_fields": action.parameters.get("updates", {}),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_send_alert(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle alert sending action."""
        logger.info(f"Sending alert for action {action.action_id}")
        # Placeholder implementation - would integrate with notification system
        return {
            "alert_id": str(uuid4()),
            "recipient": action.parameters.get("recipient"),
            "message": action.parameters.get("message"),
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_schedule_followup(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle follow-up scheduling action."""
        logger.info(f"Scheduling follow-up for action {action.action_id}")
        # Placeholder implementation - would integrate with calendar system
        return {
            "followup_id": str(uuid4()),
            "scheduled_for": action.parameters.get("scheduled_for"),
            "type": action.parameters.get("followup_type"),
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_update_lead_status(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle lead status update action."""
        logger.info(f"Updating lead status for action {action.action_id}")
        # Placeholder implementation - would integrate with CRM system
        return {
            "lead_id": action.parameters.get("lead_id"),
            "old_status": action.parameters.get("old_status"),
            "new_status": action.parameters.get("new_status"),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_assign_rep(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle rep assignment action."""
        logger.info(f"Assigning rep for action {action.action_id}")
        # Placeholder implementation - would integrate with CRM system
        return {
            "entity_id": action.parameters.get("entity_id"),
            "entity_type": action.parameters.get("entity_type"),
            "assigned_rep": action.parameters.get("rep_id"),
            "assigned_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_create_followup_message(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle follow-up message creation action."""
        logger.info(f"Creating follow-up message for action {action.action_id}")
        # Placeholder implementation - would integrate with messaging system
        return {
            "message_id": str(uuid4()),
            "recipient": action.parameters.get("recipient"),
            "message_content": action.parameters.get("message"),
            "channel": action.parameters.get("channel", "email"),
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def _handle_update_opportunity_flag(self, action: SalesAction, context: ExecutionContext) -> Dict[str, Any]:
        """Handle opportunity flag update action."""
        logger.info(f"Updating opportunity flag for action {action.action_id}")
        # Placeholder implementation - would integrate with CRM system
        return {
            "opportunity_id": action.parameters.get("opportunity_id"),
            "flag_type": action.parameters.get("flag_type"),
            "flag_value": action.parameters.get("flag_value"),
            "updated_at": datetime.utcnow().isoformat()
        }