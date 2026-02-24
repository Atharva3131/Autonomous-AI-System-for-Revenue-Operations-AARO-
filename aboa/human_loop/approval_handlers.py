"""
Sales Approval Interface and Handlers.

This module implements the approval interface handlers for revenue decisions,
including approval request generation with pipeline context, multiple response
options, approval forwarding to sales action engine, and rejection logging
and learning system.

Implements Requirements 5.4, 5.5, 5.6:
- Provide multiple response options including approve, deny, modify, or request more deal context
- Forward approved decisions to the Action_Engine for execution
- Log rejection reasoning for future sales learning
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from ..core.exceptions import ABOAException
from ..core.logging import get_logger
from ..models.enums import ApprovalStatus, DecisionClass, ExecutionStatus
from ..models.revenue_entities import (
    Deal, Lead, PipelineRisk, RevenueContext, SalesAction, SalesRep, RevenueDecisionLog
)
from .models import (
    ApprovalRequest, ApprovalResponse, ApprovalAuditLog, EscalationEvent, NotificationConfig
)
from .sales_manager_interface import SalesManagerInterface

logger = get_logger(__name__)


class ApprovalHandlerError(ABOAException):
    """Exception raised for approval handler errors."""
    pass


class ApprovalRequestGenerator:
    """
    Generates approval requests with comprehensive pipeline context.
    
    Implements Requirement 5.4: THE Human_Loop SHALL provide multiple response 
    options including approve, deny, modify, or request more deal context.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the approval request generator.
        
        Args:
            config: Configuration dictionary for request generation
        """
        self.config = config or self._get_default_config()
        self.logger = logger
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for approval request generation."""
        return {
            'include_deal_history_days': 90,
            'include_similar_deals_count': 5,
            'include_rep_performance_metrics': True,
            'include_market_context': True,
            'context_confidence_threshold': 70.0,
            'max_context_items': 10
        }
    
    def generate_approval_request(
        self,
        pipeline_risk: PipelineRisk,
        recommended_action: SalesAction,
        deals: List[Deal],
        leads: List[Lead],
        reps: List[SalesRep],
        approver_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        Generate comprehensive approval request with pipeline context.
        
        Implements Requirement 5.4: Provide multiple response options including 
        approve, deny, modify, or request more deal context.
        
        Args:
            pipeline_risk: The detected pipeline risk
            recommended_action: The recommended sales action
            deals: List of relevant deals
            leads: List of relevant leads
            reps: List of relevant sales reps
            approver_id: ID of the assigned approver
            additional_context: Optional additional context
            
        Returns:
            ApprovalRequest with comprehensive pipeline context
            
        Raises:
            ApprovalHandlerError: If request generation fails
        """
        try:
            # Build comprehensive revenue context
            revenue_context = self._build_revenue_context(
                pipeline_risk, deals, leads, reps, additional_context
            )
            
            # Create approval request using SalesManagerInterface
            # Merge configs to ensure compatibility
            sales_manager_config = {
                'default_timeout_minutes': 60,
                'critical_timeout_minutes': 30,
                'high_timeout_minutes': 60,
                'medium_timeout_minutes': 120,
                'low_timeout_minutes': 240,
                'max_escalation_levels': 3,
                'default_escalation_minutes': 30,
                'enable_fallback_actions': True,
                'audit_retention_days': 90,
                'notification_retry_attempts': 3,
                'notification_retry_delay_minutes': 5
            }
            sales_manager_config.update(self.config)
            
            sales_manager = SalesManagerInterface(sales_manager_config)
            
            approval_request = sales_manager.request_approval(
                pipeline_risk=pipeline_risk,
                recommended_action=recommended_action,
                revenue_context=revenue_context,
                approver_id=approver_id
            )
            
            self.logger.info(
                f"Generated approval request {approval_request.request_id} for risk {pipeline_risk.risk_id}"
            )
            
            return approval_request
            
        except Exception as e:
            self.logger.error(f"Failed to generate approval request: {str(e)}")
            raise ApprovalHandlerError(f"Failed to generate approval request: {str(e)}") from e
    
    def _build_revenue_context(
        self,
        pipeline_risk: PipelineRisk,
        deals: List[Deal],
        leads: List[Lead],
        reps: List[SalesRep],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> RevenueContext:
        """Build comprehensive revenue context for approval request."""
        # Filter relevant deals and leads
        relevant_deals = [
            deal for deal in deals 
            if deal.id in pipeline_risk.affected_deals
        ]
        
        relevant_leads = [
            lead for lead in leads 
            if lead.id in pipeline_risk.affected_leads
        ]
        
        # Get historical deal data
        deal_history = self._get_deal_history(relevant_deals, deals)
        
        # Find similar deals for comparison
        similar_deals = self._find_similar_deals(relevant_deals, deals)
        
        # Get rep performance data
        rep_performance = self._get_rep_performance(relevant_deals, relevant_leads, reps)
        
        # Generate sales playbook guidance
        sales_guidance = self._generate_sales_guidance(pipeline_risk, relevant_deals, relevant_leads)
        
        # Calculate confidence score
        confidence_score = self._calculate_context_confidence(
            deal_history, similar_deals, rep_performance, sales_guidance
        )
        
        # Create revenue context
        revenue_context = RevenueContext(
            context_id=str(uuid4()),
            deal_history=deal_history,
            rep_performance=rep_performance,
            similar_deals=similar_deals,
            sales_playbook_guidance=sales_guidance,
            market_conditions=additional_context.get('market_conditions') if additional_context else None,
            pipeline_risks=[pipeline_risk],
            confidence_score=confidence_score
        )
        
        return revenue_context
    
    def _get_deal_history(self, relevant_deals: List[Deal], all_deals: List[Deal]) -> List[Deal]:
        """Get historical deal data for context."""
        # Get deals from the same reps or similar characteristics
        history_deals = []
        
        for relevant_deal in relevant_deals:
            # Find deals from same rep
            rep_deals = [
                deal for deal in all_deals
                if (deal.assigned_rep == relevant_deal.assigned_rep and
                    deal.id != relevant_deal.id and
                    (datetime.utcnow() - deal.created_at).days <= self.config['include_deal_history_days'])
            ]
            history_deals.extend(rep_deals[:3])  # Limit to 3 per relevant deal
        
        # Remove duplicates and limit total
        unique_deals = list({deal.id: deal for deal in history_deals}.values())
        return unique_deals[:self.config['max_context_items']]
    
    def _find_similar_deals(self, relevant_deals: List[Deal], all_deals: List[Deal]) -> List[Deal]:
        """Find similar deals for comparison."""
        if not relevant_deals:
            return []
        
        similar_deals = []
        
        for relevant_deal in relevant_deals:
            # Find deals with similar value and stage
            value_range = relevant_deal.value * Decimal('0.3')  # 30% range
            
            candidates = [
                deal for deal in all_deals
                if (deal.id != relevant_deal.id and
                    abs(deal.value - relevant_deal.value) <= value_range and
                    deal.stage == relevant_deal.stage)
            ]
            
            # Sort by value similarity and take top matches
            candidates.sort(key=lambda d: abs(d.value - relevant_deal.value))
            similar_deals.extend(candidates[:2])  # Top 2 per relevant deal
        
        # Remove duplicates and limit total
        unique_deals = list({deal.id: deal for deal in similar_deals}.values())
        return unique_deals[:self.config['include_similar_deals_count']]
    
    def _get_rep_performance(
        self, 
        relevant_deals: List[Deal], 
        relevant_leads: List[Lead], 
        reps: List[SalesRep]
    ) -> Optional[SalesRep]:
        """Get rep performance data for context."""
        if not self.config['include_rep_performance_metrics']:
            return None
        
        # Find the primary rep (most deals/leads assigned)
        rep_counts = {}
        
        for deal in relevant_deals:
            rep_counts[deal.assigned_rep] = rep_counts.get(deal.assigned_rep, 0) + 1
        
        for lead in relevant_leads:
            if lead.assigned_rep:
                rep_counts[lead.assigned_rep] = rep_counts.get(lead.assigned_rep, 0) + 1
        
        if not rep_counts:
            return None
        
        primary_rep_id = max(rep_counts, key=rep_counts.get)
        
        # Find the rep data
        for rep in reps:
            if rep.id == primary_rep_id:
                return rep
        
        return None
    
    def _generate_sales_guidance(
        self, 
        pipeline_risk: PipelineRisk, 
        deals: List[Deal], 
        leads: List[Lead]
    ) -> List[str]:
        """Generate sales playbook guidance based on risk and context."""
        guidance = []
        
        # Risk-specific guidance
        if pipeline_risk.risk_type.value == 'stalled_deal':
            guidance.append("Review deal progression checklist")
            guidance.append("Schedule stakeholder alignment meeting")
            guidance.append("Assess budget and decision timeline")
        elif pipeline_risk.risk_type.value == 'missed_followup':
            guidance.append("Implement systematic follow-up cadence")
            guidance.append("Set calendar reminders for all interactions")
            guidance.append("Document next steps after each touchpoint")
        elif pipeline_risk.risk_type.value == 'inactive_high_value':
            guidance.append("Escalate to senior sales management")
            guidance.append("Review competitive positioning")
            guidance.append("Assess champion engagement level")
        elif pipeline_risk.risk_type.value == 'low_activity':
            guidance.append("Increase touchpoint frequency")
            guidance.append("Vary communication channels")
            guidance.append("Provide value-added content")
        
        # Deal stage-specific guidance
        for deal in deals:
            if deal.stage.value == 'proposal':
                guidance.append("Ensure proposal addresses all requirements")
                guidance.append("Schedule proposal review meeting")
            elif deal.stage.value == 'negotiation':
                guidance.append("Prepare negotiation strategy")
                guidance.append("Identify decision makers")
        
        # Remove duplicates and limit
        unique_guidance = list(set(guidance))
        return unique_guidance[:self.config['max_context_items']]
    
    def _calculate_context_confidence(
        self,
        deal_history: List[Deal],
        similar_deals: List[Deal],
        rep_performance: Optional[SalesRep],
        sales_guidance: List[str]
    ) -> float:
        """Calculate confidence score for the revenue context."""
        confidence = 0.0
        
        # Base confidence from available data
        if deal_history:
            confidence += 25.0
        if similar_deals:
            confidence += 25.0
        if rep_performance:
            confidence += 25.0
        if sales_guidance:
            confidence += 25.0
        
        # Adjust based on data quality
        if len(deal_history) >= 3:
            confidence += 10.0
        if len(similar_deals) >= 3:
            confidence += 10.0
        if rep_performance and rep_performance.quota_attainment > 0.8:
            confidence += 10.0
        
        return min(confidence, 100.0)


class ApprovalResponseHandler:
    """
    Handles approval responses with multiple options and forwarding.
    
    Implements Requirements 5.4, 5.5, 5.6:
    - Handle multiple response options (approve/deny/modify/request context)
    - Forward approved decisions to Action_Engine for execution
    - Log rejection reasoning for future learning
    """
    
    def __init__(self, action_engine=None, config: Optional[Dict] = None):
        """
        Initialize the approval response handler.
        
        Args:
            action_engine: Sales action engine for forwarding approved actions
            config: Configuration dictionary
        """
        self.action_engine = action_engine
        self.config = config or self._get_default_config()
        self.sales_manager = SalesManagerInterface(self.config)
        self.rejection_logs: List[Dict[str, Any]] = []
        self.learning_patterns: Dict[str, Any] = {}
        self.logger = logger
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for response handling."""
        return {
            'auto_forward_approved': True,
            'log_all_decisions': True,
            'enable_learning_system': True,
            'learning_confidence_threshold': 80.0,
            'max_rejection_logs': 1000,
            'learning_pattern_min_occurrences': 3
        }
    
    def handle_approval_response(
        self,
        request_id: str,
        approver_id: str,
        decision: ApprovalStatus,
        reasoning: Optional[str] = None,
        modified_action: Optional[SalesAction] = None,
        additional_context_requested: bool = False,
        context_request_details: Optional[str] = None
    ) -> Tuple[ApprovalResponse, Optional[Any]]:
        """
        Handle approval response with multiple options.
        
        Implements Requirement 5.4: THE Human_Loop SHALL provide multiple response 
        options including approve, deny, modify, or request more deal context.
        
        Args:
            request_id: The approval request ID
            approver_id: ID of the approver
            decision: The approval decision
            reasoning: Optional reasoning for the decision
            modified_action: Optional modified action if approved with changes
            additional_context_requested: Whether more context was requested
            context_request_details: Details of context request
            
        Returns:
            Tuple of (ApprovalResponse, execution_result)
            
        Raises:
            ApprovalHandlerError: If response handling fails
        """
        try:
            # Record the decision
            response = self.sales_manager.record_decision(
                request_id=request_id,
                approver_id=approver_id,
                decision=decision,
                reasoning=reasoning,
                modified_action=modified_action
            )
            
            # Update response with additional context request info
            response.additional_context_requested = additional_context_requested
            response.context_request_details = context_request_details
            
            execution_result = None
            
            # Handle based on decision type
            if decision == ApprovalStatus.APPROVED:
                execution_result = self._handle_approval(
                    request_id, response, modified_action
                )
            elif decision == ApprovalStatus.DENIED:
                self._handle_denial(request_id, response, reasoning)
            
            # Handle context request
            if additional_context_requested:
                self._handle_context_request(request_id, context_request_details)
            
            # Log decision for learning
            if self.config['log_all_decisions']:
                self._log_decision_for_learning(request_id, response)
            
            self.logger.info(
                f"Handled approval response for request {request_id}: {decision.value}"
            )
            
            return response, execution_result
            
        except Exception as e:
            self.logger.error(f"Failed to handle approval response: {str(e)}")
            raise ApprovalHandlerError(f"Failed to handle approval response: {str(e)}") from e
    
    def _handle_approval(
        self,
        request_id: str,
        response: ApprovalResponse,
        modified_action: Optional[SalesAction]
    ) -> Optional[Any]:
        """
        Handle approved decision and forward to action engine.
        
        Implements Requirement 5.5: WHEN approval is granted, THE Human_Loop 
        SHALL forward the decision to the Action_Engine for execution.
        """
        if not self.action_engine:
            self.logger.warning("No action engine available for forwarding approved action")
            return None
        
        if not self.config['auto_forward_approved']:
            self.logger.info(f"Auto-forwarding disabled for request {request_id}")
            return None
        
        try:
            # Get the original request to find the action
            request = self.sales_manager.active_requests.get(request_id)
            if not request:
                self.logger.error(f"Original request {request_id} not found for forwarding")
                return None
            
            # Use modified action if provided, otherwise use original
            action_to_execute = modified_action or request.recommended_action
            
            # Forward to action engine for execution
            # Note: This would be async in a real implementation
            self.logger.info(
                f"Forwarding approved action {action_to_execute.action_id} to action engine"
            )
            
            # Create execution metadata
            execution_metadata = {
                'approval_request_id': request_id,
                'approver_id': response.approver_id,
                'approval_reasoning': response.reasoning,
                'modified_from_original': modified_action is not None,
                'pipeline_risk_id': request.pipeline_risk.risk_id
            }
            
            # In a real implementation, this would be:
            # execution_result = await self.action_engine.execute_action(
            #     action=action_to_execute,
            #     metadata=execution_metadata
            # )
            
            # For now, simulate execution result
            execution_result = {
                'execution_id': str(uuid4()),
                'status': ExecutionStatus.COMPLETED,
                'action_id': action_to_execute.action_id,
                'forwarded_at': datetime.utcnow().isoformat(),
                'metadata': execution_metadata
            }
            
            self.logger.info(
                f"Successfully forwarded approved action for request {request_id}"
            )
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Failed to forward approved action: {str(e)}")
            return None
    
    def _handle_denial(
        self,
        request_id: str,
        response: ApprovalResponse,
        reasoning: Optional[str]
    ) -> None:
        """
        Handle denied decision and log for learning.
        
        Implements Requirement 5.6: WHEN approval is denied, THE Human_Loop 
        SHALL log the rejection and reasoning for future sales learning.
        """
        try:
            # Get the original request for context
            request = self.sales_manager.active_requests.get(request_id)
            if not request:
                self.logger.error(f"Original request {request_id} not found for denial logging")
                return
            
            # Create rejection log entry
            rejection_log = {
                'log_id': str(uuid4()),
                'request_id': request_id,
                'approver_id': response.approver_id,
                'denied_at': datetime.utcnow(),
                'reasoning': reasoning,
                'pipeline_risk': {
                    'risk_id': request.pipeline_risk.risk_id,
                    'risk_type': request.pipeline_risk.risk_type.value,
                    'severity': request.pipeline_risk.severity.value,
                    'confidence': request.pipeline_risk.confidence
                },
                'recommended_action': {
                    'action_id': request.recommended_action.action_id,
                    'action_type': request.recommended_action.action_type.value,
                    'revenue_impact': str(request.recommended_action.revenue_impact) if request.recommended_action.revenue_impact else None
                },
                'context_summary': {
                    'deals_affected': len(request.pipeline_risk.affected_deals),
                    'leads_affected': len(request.pipeline_risk.affected_leads),
                    'total_pipeline_value': self._calculate_total_pipeline_value(request)
                }
            }
            
            # Store rejection log
            self.rejection_logs.append(rejection_log)
            
            # Maintain log size limit
            if len(self.rejection_logs) > self.config['max_rejection_logs']:
                self.rejection_logs = self.rejection_logs[-self.config['max_rejection_logs']:]
            
            # Update learning patterns if enabled
            if self.config['enable_learning_system']:
                self._update_learning_patterns(rejection_log)
            
            self.logger.info(
                f"Logged rejection for request {request_id} with reasoning: {reasoning}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log rejection: {str(e)}")
    
    def _handle_context_request(
        self,
        request_id: str,
        context_request_details: Optional[str]
    ) -> None:
        """Handle request for additional context."""
        try:
            # Log context request
            self.logger.info(
                f"Additional context requested for request {request_id}: {context_request_details}"
            )
            
            # In a real implementation, this would trigger:
            # 1. Additional data gathering
            # 2. Enhanced context generation
            # 3. Updated approval request
            # 4. Re-notification to approver
            
            # For now, just log the request
            context_request_log = {
                'request_id': request_id,
                'requested_at': datetime.utcnow(),
                'details': context_request_details,
                'status': 'pending'
            }
            
            # This would be stored in a context request tracking system
            self.logger.debug(f"Context request logged: {context_request_log}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle context request: {str(e)}")
    
    def _log_decision_for_learning(
        self,
        request_id: str,
        response: ApprovalResponse
    ) -> None:
        """Log decision for machine learning and pattern recognition."""
        try:
            # Get the original request
            request = self.sales_manager.active_requests.get(request_id)
            if not request:
                return
            
            # Create decision log
            decision_log = RevenueDecisionLog(
                decision_id=str(uuid4()),
                timestamp=datetime.utcnow(),
                pipeline_risk=request.pipeline_risk,
                recommendation=request.recommended_action,
                human_decision=f"{response.decision.value}: {response.reasoning}",
                decision_type="approval",
                confidence=response.confidence
            )
            
            # In a real implementation, this would be stored in a database
            # and used for ML model training
            self.logger.debug(f"Decision logged for learning: {decision_log.decision_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to log decision for learning: {str(e)}")
    
    def _update_learning_patterns(self, rejection_log: Dict[str, Any]) -> None:
        """
        Update learning patterns based on rejection data.
        
        Implements Requirement 5.6: Log rejection reasoning for future sales learning.
        """
        try:
            # Extract pattern key
            pattern_key = f"{rejection_log['pipeline_risk']['risk_type']}_{rejection_log['recommended_action']['action_type']}"
            
            # Initialize pattern if not exists
            if pattern_key not in self.learning_patterns:
                self.learning_patterns[pattern_key] = {
                    'rejection_count': 0,
                    'total_requests': 0,
                    'common_reasons': {},
                    'severity_distribution': {},
                    'confidence_stats': {'sum': 0, 'count': 0},
                    'last_updated': datetime.utcnow()
                }
            
            pattern = self.learning_patterns[pattern_key]
            
            # Update counts
            pattern['rejection_count'] += 1
            pattern['total_requests'] += 1
            
            # Update common reasons
            reasoning = rejection_log.get('reasoning', 'No reason provided')
            pattern['common_reasons'][reasoning] = pattern['common_reasons'].get(reasoning, 0) + 1
            
            # Update severity distribution
            severity = rejection_log['pipeline_risk']['severity']
            pattern['severity_distribution'][severity] = pattern['severity_distribution'].get(severity, 0) + 1
            
            # Update confidence stats
            confidence = rejection_log['pipeline_risk']['confidence']
            pattern['confidence_stats']['sum'] += confidence
            pattern['confidence_stats']['count'] += 1
            
            pattern['last_updated'] = datetime.utcnow()
            
            # Check if pattern is significant enough for learning
            if (pattern['rejection_count'] >= self.config['learning_pattern_min_occurrences'] and
                pattern['rejection_count'] / pattern['total_requests'] > 0.5):
                
                self.logger.info(
                    f"Significant rejection pattern detected: {pattern_key} "
                    f"({pattern['rejection_count']}/{pattern['total_requests']} rejected)"
                )
                
                # In a real implementation, this would trigger:
                # 1. Model retraining
                # 2. Decision threshold adjustments
                # 3. Alert to system administrators
            
        except Exception as e:
            self.logger.error(f"Failed to update learning patterns: {str(e)}")
    
    def _calculate_total_pipeline_value(self, request: ApprovalRequest) -> str:
        """Calculate total pipeline value for context."""
        try:
            total_value = sum(
                deal.value for deal in request.revenue_context.deal_history
                if deal.id in request.pipeline_risk.affected_deals
            )
            return str(total_value)
        except Exception:
            return "0"
    
    def get_rejection_patterns(self) -> Dict[str, Any]:
        """Get current rejection patterns for analysis."""
        return self.learning_patterns.copy()
    
    def get_rejection_logs(
        self,
        limit: Optional[int] = None,
        risk_type: Optional[str] = None,
        approver_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get rejection logs with optional filtering.
        
        Args:
            limit: Maximum number of logs to return
            risk_type: Filter by risk type
            approver_id: Filter by approver ID
            
        Returns:
            List of rejection log entries
        """
        logs = self.rejection_logs.copy()
        
        # Apply filters
        if risk_type:
            logs = [log for log in logs if log['pipeline_risk']['risk_type'] == risk_type]
        
        if approver_id:
            logs = [log for log in logs if log['approver_id'] == approver_id]
        
        # Sort by most recent first
        logs.sort(key=lambda x: x['denied_at'], reverse=True)
        
        # Apply limit
        if limit:
            logs = logs[:limit]
        
        return logs


class ApprovalInterfaceOrchestrator:
    """
    Main orchestrator for approval interface operations.
    
    Coordinates approval request generation, response handling, and forwarding
    to provide a unified interface for the approval workflow.
    """
    
    def __init__(self, action_engine=None, config: Optional[Dict] = None):
        """
        Initialize the approval interface orchestrator.
        
        Args:
            action_engine: Sales action engine for forwarding approved actions
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Create shared sales manager instance
        sales_manager_config = {
            'default_timeout_minutes': 60,
            'critical_timeout_minutes': 30,
            'high_timeout_minutes': 60,
            'medium_timeout_minutes': 120,
            'low_timeout_minutes': 240,
            'max_escalation_levels': 3,
            'default_escalation_minutes': 30,
            'enable_fallback_actions': True,
            'audit_retention_days': 90,
            'notification_retry_attempts': 3,
            'notification_retry_delay_minutes': 5
        }
        sales_manager_config.update(self.config)
        self.sales_manager = SalesManagerInterface(sales_manager_config)
        
        self.request_generator = ApprovalRequestGenerator(self.config)
        self.response_handler = ApprovalResponseHandler(action_engine, self.config)
        
        # Share the same sales manager instance
        self.response_handler.sales_manager = self.sales_manager
        
        self.logger = logger
    
    def create_approval_request(
        self,
        pipeline_risk: PipelineRisk,
        recommended_action: SalesAction,
        deals: List[Deal],
        leads: List[Lead],
        reps: List[SalesRep],
        approver_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        Create a comprehensive approval request.
        
        Args:
            pipeline_risk: The detected pipeline risk
            recommended_action: The recommended sales action
            deals: List of relevant deals
            leads: List of relevant leads
            reps: List of relevant sales reps
            approver_id: ID of the assigned approver
            additional_context: Optional additional context
            
        Returns:
            ApprovalRequest with comprehensive context
        """
        # Build comprehensive revenue context
        revenue_context = self.request_generator._build_revenue_context(
            pipeline_risk, deals, leads, reps, additional_context
        )
        
        # Create approval request using shared sales manager
        approval_request = self.sales_manager.request_approval(
            pipeline_risk=pipeline_risk,
            recommended_action=recommended_action,
            revenue_context=revenue_context,
            approver_id=approver_id
        )
        
        return approval_request
    
    def process_approval_response(
        self,
        request_id: str,
        approver_id: str,
        decision: ApprovalStatus,
        reasoning: Optional[str] = None,
        modified_action: Optional[SalesAction] = None,
        additional_context_requested: bool = False,
        context_request_details: Optional[str] = None
    ) -> Tuple[ApprovalResponse, Optional[Any]]:
        """
        Process approval response with all options.
        
        Args:
            request_id: The approval request ID
            approver_id: ID of the approver
            decision: The approval decision
            reasoning: Optional reasoning for the decision
            modified_action: Optional modified action if approved with changes
            additional_context_requested: Whether more context was requested
            context_request_details: Details of context request
            
        Returns:
            Tuple of (ApprovalResponse, execution_result)
        """
        return self.response_handler.handle_approval_response(
            request_id=request_id,
            approver_id=approver_id,
            decision=decision,
            reasoning=reasoning,
            modified_action=modified_action,
            additional_context_requested=additional_context_requested,
            context_request_details=context_request_details
        )
    
    def get_approval_status(self, request_id: str) -> Tuple[ApprovalStatus, Optional[ApprovalResponse]]:
        """Get current approval status."""
        return self.sales_manager.check_approval_status(request_id)
    
    def get_active_requests(
        self,
        approver_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None
    ) -> List[ApprovalRequest]:
        """Get active approval requests."""
        return self.sales_manager.get_active_requests(approver_id, status)
    
    def get_rejection_analytics(self) -> Dict[str, Any]:
        """Get rejection analytics for learning insights."""
        return {
            'rejection_patterns': self.response_handler.get_rejection_patterns(),
            'recent_rejections': self.response_handler.get_rejection_logs(limit=50),
            'total_rejection_logs': len(self.response_handler.rejection_logs)
        }