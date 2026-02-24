"""
Revenue Decision Engine for intelligent sales decision-making.

This module implements the RevenueDecisionEngine class that analyzes pipeline risks,
classifies decisions, and generates recommendations with sales reasoning as specified
in Requirements 3.5, 3.6, 3.7.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any

from ..core.logging import get_logger
from ..models.enums import DecisionClass, RiskType, Severity, SalesActionType
from ..models.revenue_entities import (
    Deal, Lead, PipelineRisk, SalesAction, SalesRep, RevenueContext
)
from ..knowledge.manager import SalesKnowledgeManager, SalesContext

logger = get_logger(__name__)


class RevenueDecisionEngine:
    """
    Main revenue decision engine that analyzes pipeline risks and generates
    intelligent recommendations with sales reasoning.
    
    Implements Requirements 3.5, 3.6, 3.7:
    - Classifies decisions as auto-executable, requiring human approval, or insight-only
    - References the Knowledge_Layer for sales SOP compliance before making recommendations
    - Consolidates recommendations to avoid duplicate actions when multiple patterns indicate the same pipeline risk
    """
    
    def __init__(self, 
                 knowledge_manager: Optional[SalesKnowledgeManager] = None,
                 config: Optional[Dict] = None):
        """
        Initialize the revenue decision engine.
        
        Args:
            knowledge_manager: Sales knowledge manager for context retrieval
            config: Configuration dictionary with decision thresholds
        """
        self.knowledge_manager = knowledge_manager
        self.config = config or self._get_default_config()
        self.logger = logger
        
    def _get_default_config(self) -> Dict:
        """Get default configuration for decision classification."""
        return {
            # Auto-executable thresholds
            'auto_executable_max_value': Decimal('25000'),
            'auto_executable_confidence_threshold': 80.0,
            
            # Approval required thresholds
            'approval_required_min_value': Decimal('25000'),
            'approval_required_max_value': Decimal('100000'),
            'high_confidence_threshold': 85.0,
            
            # Critical decision thresholds
            'critical_decision_value': Decimal('100000'),
            'critical_confidence_threshold': 90.0,
            
            # Consolidation settings
            'consolidation_time_window_hours': 24,
            'max_actions_per_deal': 3,
            
            # Knowledge retrieval settings
            'knowledge_confidence_threshold': 70.0,
            'max_knowledge_results': 5,
        }
    
    def analyze_and_recommend(self, 
                            pipeline_risks: List[PipelineRisk],
                            deals: List[Deal],
                            leads: List[Lead],
                            reps: List[SalesRep]) -> List[Tuple[PipelineRisk, SalesAction, DecisionClass]]:
        """
        Analyze pipeline risks and generate recommendations with decision classification.
        
        Args:
            pipeline_risks: List of detected pipeline risks
            deals: List of deals for context
            leads: List of leads for context
            reps: List of sales reps for context
            
        Returns:
            List of tuples containing (risk, recommended_action, decision_class)
        """
        if not pipeline_risks:
            self.logger.info("No pipeline risks to analyze")
            return []
        
        # Group risks by affected entities to enable consolidation
        risk_groups = self._group_risks_for_consolidation(pipeline_risks)
        
        recommendations = []
        
        for risk_group in risk_groups:
            # Consolidate overlapping risks (Requirement 3.7)
            consolidated_risk = self._consolidate_risks(risk_group)
            
            # Get sales context from knowledge layer (Requirement 3.6)
            sales_context = self._get_sales_context(consolidated_risk, deals, leads, reps)
            
            # Generate recommendation with sales reasoning
            recommended_action = self._generate_recommendation(
                consolidated_risk, sales_context, deals, leads, reps
            )
            
            # Classify decision (Requirement 3.5)
            decision_class = self._classify_decision(
                consolidated_risk, recommended_action, sales_context, deals
            )
            
            recommendations.append((consolidated_risk, recommended_action, decision_class))
        
        self.logger.info(f"Generated {len(recommendations)} revenue recommendations")
        return recommendations
    
    def assess_risk_impact(self, 
                          risk: PipelineRisk, 
                          deals: List[Deal], 
                          leads: List[Lead]) -> Dict[str, Any]:
        """
        Assess the potential revenue impact of a pipeline risk.
        
        Args:
            risk: Pipeline risk to assess
            deals: List of deals for context
            leads: List of leads for context
            
        Returns:
            Dictionary containing impact assessment details
        """
        impact_assessment = {
            'total_pipeline_at_risk': Decimal('0'),
            'deals_at_risk_count': len(risk.affected_deals),
            'leads_at_risk_count': len(risk.affected_leads),
            'highest_value_deal': Decimal('0'),
            'average_deal_value': Decimal('0'),
            'urgency_score': 0.0,
            'revenue_velocity_impact': 0.0
        }
        
        # Calculate deal-related impact
        if risk.affected_deals:
            affected_deal_values = []
            for deal in deals:
                if deal.id in risk.affected_deals:
                    affected_deal_values.append(deal.value)
            
            if affected_deal_values:
                impact_assessment['total_pipeline_at_risk'] = sum(affected_deal_values)
                impact_assessment['highest_value_deal'] = max(affected_deal_values)
                impact_assessment['average_deal_value'] = sum(affected_deal_values) / len(affected_deal_values)
        
        # Calculate lead-related impact
        if risk.affected_leads:
            estimated_lead_values = []
            for lead in leads:
                if lead.id in risk.affected_leads and lead.estimated_value:
                    estimated_lead_values.append(lead.estimated_value)
            
            if estimated_lead_values:
                impact_assessment['total_pipeline_at_risk'] += sum(estimated_lead_values)
        
        # Calculate urgency score based on risk type and severity
        impact_assessment['urgency_score'] = self._calculate_urgency_score(risk)
        
        # Estimate velocity impact
        impact_assessment['revenue_velocity_impact'] = self._estimate_velocity_impact(risk, deals)
        
        return impact_assessment
    
    def _group_risks_for_consolidation(self, risks: List[PipelineRisk]) -> List[List[PipelineRisk]]:
        """Group risks that affect the same entities for consolidation."""
        risk_groups = []
        processed_risks = set()
        
        for risk in risks:
            if risk.risk_id in processed_risks:
                continue
            
            # Find all risks that affect the same deals or leads
            related_risks = [risk]
            processed_risks.add(risk.risk_id)
            
            for other_risk in risks:
                if other_risk.risk_id in processed_risks:
                    continue
                
                # Check for overlap in affected entities
                if (set(risk.affected_deals) & set(other_risk.affected_deals) or
                    set(risk.affected_leads) & set(other_risk.affected_leads)):
                    
                    # Check if risks were detected within consolidation window
                    time_diff = abs((risk.detected_at - other_risk.detected_at).total_seconds() / 3600)
                    if time_diff <= self.config['consolidation_time_window_hours']:
                        related_risks.append(other_risk)
                        processed_risks.add(other_risk.risk_id)
            
            risk_groups.append(related_risks)
        
        return risk_groups
    
    def _consolidate_risks(self, risk_group: List[PipelineRisk]) -> PipelineRisk:
        """
        Consolidate multiple related risks into a single risk.
        
        Implements Requirement 3.7: WHEN multiple patterns indicate the same pipeline risk,
        THE Decision_Engine SHALL consolidate recommendations to avoid duplicate actions
        """
        if len(risk_group) == 1:
            return risk_group[0]
        
        # Find the highest severity risk as the base
        base_risk = max(risk_group, key=lambda r: ['low', 'medium', 'high', 'critical'].index(r.severity.value))
        
        # Combine affected entities
        all_affected_deals = set()
        all_affected_leads = set()
        all_recommended_actions = set()
        
        for risk in risk_group:
            all_affected_deals.update(risk.affected_deals)
            all_affected_leads.update(risk.affected_leads)
            all_recommended_actions.update(risk.recommended_actions)
        
        # Create consolidated risk
        consolidated_risk = PipelineRisk(
            risk_id=str(uuid.uuid4()),
            risk_type=base_risk.risk_type,
            detected_at=min(risk.detected_at for risk in risk_group),
            confidence=sum(risk.confidence for risk in risk_group) / len(risk_group),
            affected_deals=list(all_affected_deals),
            affected_leads=list(all_affected_leads),
            severity=base_risk.severity,
            description=f"Consolidated risk affecting {len(all_affected_deals)} deals and {len(all_affected_leads)} leads: " +
                       "; ".join(set(risk.description.split(":")[0] for risk in risk_group)),
            recommended_actions=list(all_recommended_actions)
        )
        
        self.logger.debug(f"Consolidated {len(risk_group)} risks into single risk {consolidated_risk.risk_id}")
        return consolidated_risk
    
    def _get_sales_context(self, 
                          risk: PipelineRisk, 
                          deals: List[Deal], 
                          leads: List[Lead], 
                          reps: List[SalesRep]) -> Optional[SalesContext]:
        """
        Retrieve sales context from knowledge layer for decision-making.
        
        Implements Requirement 3.6: THE Decision_Engine SHALL reference the Knowledge_Layer
        for sales SOP compliance before making recommendations
        """
        if not self.knowledge_manager:
            self.logger.warning("No knowledge manager available for context retrieval")
            return None
        
        try:
            # Build context query based on risk type and affected entities
            context_query = self._build_context_query(risk, deals, leads, reps)
            
            # Retrieve sales context
            sales_context = self.knowledge_manager.get_sales_context(
                decision_type=risk.risk_type.value,
                additional_context=context_query
            )
            
            # Only return context if confidence is above threshold
            if sales_context.confidence_score >= self.config['knowledge_confidence_threshold']:
                self.logger.debug(f"Retrieved sales context with confidence {sales_context.confidence_score:.2f}")
                return sales_context
            else:
                self.logger.debug(f"Sales context confidence {sales_context.confidence_score:.2f} below threshold")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve sales context: {str(e)}")
            return None
    
    def _build_context_query(self, 
                           risk: PipelineRisk, 
                           deals: List[Deal], 
                           leads: List[Lead], 
                           reps: List[SalesRep]) -> str:
        """Build context query for knowledge retrieval."""
        query_parts = [risk.risk_type.value]
        
        # Add deal stage information
        for deal in deals:
            if deal.id in risk.affected_deals:
                query_parts.append(f"deal_stage_{deal.stage.value}")
                if deal.value >= Decimal('50000'):
                    query_parts.append("high_value_deal")
                break
        
        # Add severity information
        query_parts.append(f"severity_{risk.severity.value}")
        
        return " ".join(query_parts)
    
    def _generate_recommendation(self, 
                               risk: PipelineRisk, 
                               sales_context: Optional[SalesContext],
                               deals: List[Deal], 
                               leads: List[Lead], 
                               reps: List[SalesRep]) -> SalesAction:
        """Generate sales action recommendation with reasoning."""
        # Determine action type based on risk type and context
        action_type = self._determine_action_type(risk, sales_context)
        
        # Build action parameters
        parameters = self._build_action_parameters(risk, deals, leads, reps, sales_context)
        
        # Generate reasoning
        reasoning = self._generate_sales_reasoning(risk, sales_context, deals, leads)
        
        # Estimate revenue impact
        revenue_impact = self._estimate_revenue_impact(risk, deals, leads)
        
        # Create sales action
        action = SalesAction(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            target_system=self._determine_target_system(action_type),
            parameters=parameters,
            prerequisites=[],
            expected_outcome=reasoning,
            revenue_impact=revenue_impact,
            priority=self._calculate_action_priority(risk, revenue_impact)
        )
        
        return action
    
    def _classify_decision(self, 
                         risk: PipelineRisk, 
                         action: SalesAction, 
                         sales_context: Optional[SalesContext],
                         deals: List[Deal]) -> DecisionClass:
        """
        Classify decision as auto-executable, approval-required, or insight-only.
        
        Implements Requirement 3.5: WHEN patterns are detected, THE Decision_Engine SHALL
        classify decisions as auto-executable, requiring human approval, or insight-only
        """
        # Get maximum deal value affected
        max_deal_value = Decimal('0')
        for deal in deals:
            if deal.id in risk.affected_deals:
                max_deal_value = max(max_deal_value, deal.value)
        
        # Critical decisions require approval
        if (max_deal_value >= self.config['critical_decision_value'] or
            risk.severity == Severity.CRITICAL):
            return DecisionClass.APPROVAL_REQUIRED
        
        # High-value decisions with low confidence require approval
        if (max_deal_value >= self.config['approval_required_min_value'] and
            risk.confidence < self.config['high_confidence_threshold']):
            return DecisionClass.APPROVAL_REQUIRED
        
        # High-risk actions require approval
        if action.action_type in [SalesActionType.UPDATE_DEAL, SalesActionType.ASSIGN_REP]:
            if max_deal_value >= self.config['approval_required_min_value']:
                return DecisionClass.APPROVAL_REQUIRED
        
        # Auto-executable criteria
        if (max_deal_value <= self.config['auto_executable_max_value'] and
            risk.confidence >= self.config['auto_executable_confidence_threshold'] and
            action.action_type in [SalesActionType.CREATE_TASK, SalesActionType.SCHEDULE_FOLLOWUP, 
                                 SalesActionType.SEND_ALERT, SalesActionType.CREATE_FOLLOWUP_MESSAGE]):
            return DecisionClass.AUTO_EXECUTABLE
        
        # Medium-value decisions with high confidence and knowledge backing
        if (max_deal_value <= self.config['approval_required_max_value'] and
            risk.confidence >= self.config['high_confidence_threshold'] and
            sales_context and sales_context.confidence_score >= self.config['knowledge_confidence_threshold']):
            return DecisionClass.AUTO_EXECUTABLE
        
        # Default to insight-only for low-confidence or informational decisions
        return DecisionClass.INSIGHT_ONLY
    
    def _determine_action_type(self, 
                             risk: PipelineRisk, 
                             sales_context: Optional[SalesContext]) -> SalesActionType:
        """Determine the appropriate action type based on risk and context."""
        if risk.risk_type == RiskType.STALLED_DEAL:
            return SalesActionType.CREATE_TASK
        elif risk.risk_type == RiskType.MISSED_FOLLOWUP:
            return SalesActionType.SCHEDULE_FOLLOWUP
        elif risk.risk_type == RiskType.INACTIVE_HIGH_VALUE:
            return SalesActionType.SEND_ALERT
        elif risk.risk_type == RiskType.LOW_ACTIVITY:
            return SalesActionType.CREATE_FOLLOWUP_MESSAGE
        else:
            return SalesActionType.CREATE_TASK
    
    def _build_action_parameters(self, 
                               risk: PipelineRisk, 
                               deals: List[Deal], 
                               leads: List[Lead], 
                               reps: List[SalesRep],
                               sales_context: Optional[SalesContext]) -> Dict[str, Any]:
        """Build action parameters based on risk and context."""
        parameters = {
            'risk_id': risk.risk_id,
            'risk_type': risk.risk_type.value,
            'affected_deals': risk.affected_deals,
            'affected_leads': risk.affected_leads,
            'severity': risk.severity.value,
            'confidence': risk.confidence
        }
        
        # Add deal-specific parameters
        if risk.affected_deals:
            deal_info = []
            for deal in deals:
                if deal.id in risk.affected_deals:
                    deal_info.append({
                        'deal_id': deal.id,
                        'value': str(deal.value),
                        'stage': deal.stage.value,
                        'assigned_rep': deal.assigned_rep,
                        'days_in_stage': deal.days_in_current_stage
                    })
            parameters['deal_info'] = deal_info
        
        # Add lead-specific parameters
        if risk.affected_leads:
            lead_info = []
            for lead in leads:
                if lead.id in risk.affected_leads:
                    lead_info.append({
                        'lead_id': lead.id,
                        'status': lead.status.value,
                        'assigned_rep': lead.assigned_rep,
                        'contact_attempts': lead.contact_attempts
                    })
            parameters['lead_info'] = lead_info
        
        # Add sales context if available
        if sales_context:
            parameters['sales_guidance'] = [
                doc.title for doc in sales_context.relevant_playbooks[:3]
            ]
            parameters['context_confidence'] = sales_context.confidence_score
        
        return parameters
    
    def _generate_sales_reasoning(self, 
                                risk: PipelineRisk, 
                                sales_context: Optional[SalesContext],
                                deals: List[Deal], 
                                leads: List[Lead]) -> str:
        """Generate human-readable sales reasoning for the recommendation."""
        reasoning_parts = []
        
        # Base reasoning from risk
        if risk.risk_type == RiskType.STALLED_DEAL:
            reasoning_parts.append(f"Deal has been stalled for extended period")
        elif risk.risk_type == RiskType.MISSED_FOLLOWUP:
            reasoning_parts.append(f"Recent interactions lack scheduled follow-up actions")
        elif risk.risk_type == RiskType.INACTIVE_HIGH_VALUE:
            reasoning_parts.append(f"High-value opportunity shows no recent activity")
        elif risk.risk_type == RiskType.LOW_ACTIVITY:
            reasoning_parts.append(f"Lead engagement below minimum touchpoint requirements")
        
        # Add value context
        total_value = Decimal('0')
        for deal in deals:
            if deal.id in risk.affected_deals:
                total_value += deal.value
        
        if total_value > 0:
            reasoning_parts.append(f"Total pipeline value at risk: ${total_value:,.2f}")
        
        # Add sales context reasoning
        if sales_context and sales_context.relevant_playbooks:
            playbook_titles = [doc.title for doc in sales_context.relevant_playbooks[:2]]
            reasoning_parts.append(f"Recommended based on sales playbooks: {', '.join(playbook_titles)}")
        
        # Add urgency
        if risk.severity in [Severity.HIGH, Severity.CRITICAL]:
            reasoning_parts.append(f"Immediate action required due to {risk.severity.value} severity")
        
        return ". ".join(reasoning_parts) + "."
    
    def _determine_target_system(self, action_type: SalesActionType) -> str:
        """Determine target system for action execution."""
        system_mapping = {
            SalesActionType.CREATE_TASK: "workflow_engine",
            SalesActionType.UPDATE_DEAL: "crm_system",
            SalesActionType.SEND_ALERT: "notification_system",
            SalesActionType.SCHEDULE_FOLLOWUP: "calendar_system",
            SalesActionType.UPDATE_LEAD_STATUS: "crm_system",
            SalesActionType.ASSIGN_REP: "crm_system",
            SalesActionType.CREATE_FOLLOWUP_MESSAGE: "email_system",
            SalesActionType.UPDATE_OPPORTUNITY_FLAG: "crm_system"
        }
        return system_mapping.get(action_type, "workflow_engine")
    
    def _estimate_revenue_impact(self, 
                               risk: PipelineRisk, 
                               deals: List[Deal], 
                               leads: List[Lead]) -> Optional[Decimal]:
        """Estimate potential revenue impact of addressing the risk."""
        total_impact = Decimal('0')
        
        # Calculate deal impact
        for deal in deals:
            if deal.id in risk.affected_deals:
                # Estimate impact based on risk type
                if risk.risk_type == RiskType.STALLED_DEAL:
                    # Assume 20% of deal value could be recovered
                    total_impact += deal.value * Decimal('0.2')
                elif risk.risk_type == RiskType.INACTIVE_HIGH_VALUE:
                    # Assume 30% of deal value could be recovered
                    total_impact += deal.value * Decimal('0.3')
                elif risk.risk_type == RiskType.MISSED_FOLLOWUP:
                    # Assume 15% of deal value could be recovered
                    total_impact += deal.value * Decimal('0.15')
        
        # Calculate lead impact
        for lead in leads:
            if lead.id in risk.affected_leads and lead.estimated_value:
                # Assume 10% conversion improvement
                total_impact += lead.estimated_value * Decimal('0.1')
        
        return total_impact if total_impact > 0 else None
    
    def _calculate_action_priority(self, 
                                 risk: PipelineRisk, 
                                 revenue_impact: Optional[Decimal]) -> int:
        """Calculate action priority (1=highest)."""
        priority = 5  # Default medium priority
        
        # Adjust based on severity
        if risk.severity == Severity.CRITICAL:
            priority = 1
        elif risk.severity == Severity.HIGH:
            priority = 2
        elif risk.severity == Severity.MEDIUM:
            priority = 3
        
        # Adjust based on revenue impact
        if revenue_impact:
            if revenue_impact >= Decimal('50000'):
                priority = min(priority, 1)
            elif revenue_impact >= Decimal('25000'):
                priority = min(priority, 2)
            elif revenue_impact >= Decimal('10000'):
                priority = min(priority, 3)
        
        # Adjust based on confidence
        if risk.confidence >= 90.0:
            priority = max(priority - 1, 1)
        elif risk.confidence < 70.0:
            priority = min(priority + 1, 5)
        
        return priority
    
    def _calculate_urgency_score(self, risk: PipelineRisk) -> float:
        """Calculate urgency score for risk assessment."""
        base_score = 50.0
        
        # Adjust based on severity
        severity_multipliers = {
            Severity.LOW: 0.5,
            Severity.MEDIUM: 1.0,
            Severity.HIGH: 1.5,
            Severity.CRITICAL: 2.0
        }
        base_score *= severity_multipliers.get(risk.severity, 1.0)
        
        # Adjust based on confidence
        confidence_factor = risk.confidence / 100.0
        base_score *= confidence_factor
        
        # Adjust based on risk type
        risk_type_multipliers = {
            RiskType.INACTIVE_HIGH_VALUE: 1.8,
            RiskType.STALLED_DEAL: 1.5,
            RiskType.MISSED_FOLLOWUP: 1.2,
            RiskType.LOW_ACTIVITY: 1.0,
            RiskType.SOP_DEVIATION: 1.3
        }
        base_score *= risk_type_multipliers.get(risk.risk_type, 1.0)
        
        return min(base_score, 100.0)
    
    def _estimate_velocity_impact(self, risk: PipelineRisk, deals: List[Deal]) -> float:
        """Estimate impact on deal velocity."""
        if not risk.affected_deals:
            return 0.0
        
        # Base velocity impact by risk type
        velocity_impacts = {
            RiskType.STALLED_DEAL: -25.0,  # 25% slower
            RiskType.MISSED_FOLLOWUP: -15.0,  # 15% slower
            RiskType.INACTIVE_HIGH_VALUE: -30.0,  # 30% slower
            RiskType.LOW_ACTIVITY: -10.0,  # 10% slower
            RiskType.SOP_DEVIATION: -20.0  # 20% slower
        }
        
        base_impact = velocity_impacts.get(risk.risk_type, -10.0)
        
        # Adjust based on deal stages affected
        high_impact_stages = ['proposal', 'negotiation']
        affected_high_impact = 0
        
        for deal in deals:
            if deal.id in risk.affected_deals and deal.stage.value in high_impact_stages:
                affected_high_impact += 1
        
        if affected_high_impact > 0:
            base_impact *= 1.5  # 50% more impact for late-stage deals
        
        return base_impact