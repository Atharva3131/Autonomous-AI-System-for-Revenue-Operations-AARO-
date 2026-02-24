"""
Pipeline Velocity Optimization Engine for automated revenue operations.

This module implements the PipelineVelocityOptimizer class that provides
automated follow-up scheduling, revenue impact prioritization, pipeline risk
detection and intervention, and SOP compliance monitoring as specified in
Requirements 8.1, 8.2, 8.4.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from ..core.logging import get_logger
from ..models.enums import (
    DealStage, LeadStatus, RiskType, Severity, SalesActionType, 
    ActivityType, DecisionClass
)
from ..models.revenue_entities import (
    Deal, Lead, SalesActivity, SalesRep, PipelineRisk, SalesAction, 
    RevenueContext, RevenueImpact
)
from .pipeline_risk_detector import PipelineRiskDetector
from .revenue_decision_engine import RevenueDecisionEngine

logger = get_logger(__name__)


class PipelineVelocityOptimizer:
    """
    Main pipeline velocity optimization engine that coordinates automated follow-up
    scheduling, revenue impact prioritization, and SOP compliance monitoring.
    
    Implements Requirements 8.1, 8.2, 8.4:
    - Automated follow-up scheduling for stalled deals
    - Revenue impact prioritization algorithms
    - SOP compliance monitoring and enforcement
    """
    
    def __init__(
        self,
        risk_detector: Optional[PipelineRiskDetector] = None,
        decision_engine: Optional[RevenueDecisionEngine] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize the pipeline velocity optimizer.
        
        Args:
            risk_detector: Pipeline risk detection engine
            decision_engine: Revenue decision engine
            config: Configuration dictionary
        """
        self.risk_detector = risk_detector or PipelineRiskDetector()
        self.decision_engine = decision_engine or RevenueDecisionEngine()
        self.config = config or self._get_default_config()
        self.logger = logger
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for the optimizer."""
        return {
            'optimization_enabled': True,
            'auto_followup_enabled': True,
            'sop_monitoring_enabled': True,
            'max_actions_per_run': 50,
            'min_confidence_threshold': 70.0,
            'batch_processing': True,
            # Follow-up intervals by deal stage (in hours)
            'followup_intervals': {
                DealStage.PROSPECTING: 48,      # 2 days
                DealStage.QUALIFICATION: 24,    # 1 day
                DealStage.NEEDS_ANALYSIS: 48,   # 2 days
                DealStage.PROPOSAL: 12,         # 12 hours
                DealStage.NEGOTIATION: 6,       # 6 hours
            },
            # Escalation thresholds
            'escalation_thresholds': {
                'high_value_deal': Decimal('50000'),
                'critical_deal': Decimal('100000'),
            }
        }
    
    def optimize_pipeline_velocity(
        self,
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity],
        reps: List[SalesRep],
        context: Optional[RevenueContext] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive pipeline velocity optimization.
        
        Args:
            deals: List of deals to optimize
            leads: List of leads to optimize
            activities: List of sales activities
            reps: List of sales representatives
            context: Optional revenue context
            
        Returns:
            Dictionary containing optimization results and recommended actions
        """
        if not self.config['optimization_enabled']:
            self.logger.info("Pipeline velocity optimization is disabled")
            return {'status': 'disabled', 'actions': []}
        
        optimization_results = {
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'pipeline_risks': [],
            'sop_violations': [],
            'followup_actions': [],
            'prioritized_interventions': [],
            'compliance_scores': {},
            'summary': {}
        }
        
        try:
            # Step 1: Detect pipeline risks
            self.logger.info("Detecting pipeline risks...")
            pipeline_risks = self.risk_detector.detect_pipeline_risks(deals, leads, activities, reps)
            optimization_results['pipeline_risks'] = [
                {
                    'risk_id': risk.risk_id,
                    'risk_type': risk.risk_type.value,
                    'severity': risk.severity.value,
                    'confidence': risk.confidence,
                    'affected_deals': risk.affected_deals,
                    'affected_leads': risk.affected_leads,
                    'description': risk.description
                }
                for risk in pipeline_risks
            ]
            
            # Step 2: Schedule automated follow-ups (Requirement 8.1)
            if self.config['auto_followup_enabled']:
                self.logger.info("Scheduling automated follow-ups...")
                followup_actions = self._schedule_automated_followups(
                    deals, leads, pipeline_risks, reps
                )
                optimization_results['followup_actions'] = [
                    {
                        'action_id': action.action_id,
                        'action_type': action.action_type.value,
                        'target_system': action.target_system,
                        'priority': action.priority,
                        'revenue_impact': str(action.revenue_impact) if action.revenue_impact else None,
                        'expected_outcome': action.expected_outcome
                    }
                    for action in followup_actions
                ]
            else:
                followup_actions = []
            
            # Step 3: Prioritize interventions (Requirement 8.2)
            self.logger.info("Prioritizing interventions...")
            if followup_actions:
                prioritized_interventions = self._prioritize_interventions(
                    pipeline_risks, deals, leads, followup_actions
                )
                optimization_results['prioritized_interventions'] = prioritized_interventions
            
            # Step 4: Monitor SOP compliance (Requirement 8.4)
            if self.config['sop_monitoring_enabled']:
                self.logger.info("Monitoring SOP compliance...")
                compliance_scores = self._monitor_sop_compliance(deals, leads, activities)
                optimization_results['compliance_scores'] = compliance_scores
            
            # Step 5: Generate summary
            optimization_results['summary'] = self._generate_optimization_summary(
                pipeline_risks, followup_actions, deals, leads
            )
            
            self.logger.info(f"Pipeline velocity optimization completed: {len(pipeline_risks)} risks, {len(followup_actions)} actions")
            
        except Exception as e:
            self.logger.error(f"Pipeline velocity optimization failed: {str(e)}", exc_info=e)
            optimization_results['status'] = 'failed'
            optimization_results['error'] = str(e)
        
        return optimization_results
    
    def _schedule_automated_followups(
        self,
        deals: List[Deal],
        leads: List[Lead],
        risks: List[PipelineRisk],
        reps: List[SalesRep]
    ) -> List[SalesAction]:
        """
        Schedule automated follow-ups for stalled deals and inactive leads.
        
        Implements Requirement 8.1: WHEN detecting stalled deals, THE AARO SHALL
        automatically create and assign follow-up tasks with context-aware messaging
        """
        followup_actions = []
        
        # Find stalled deals from risks
        stalled_deal_ids = set()
        for risk in risks:
            if risk.risk_type == RiskType.STALLED_DEAL:
                stalled_deal_ids.update(risk.affected_deals)
        
        # Schedule follow-ups for stalled deals
        for deal in deals:
            if deal.id in stalled_deal_ids:
                actions = self._create_deal_followup_actions(deal)
                followup_actions.extend(actions)
        
        # Find inactive leads from risks
        inactive_lead_ids = set()
        for risk in risks:
            if risk.risk_type == RiskType.LOW_ACTIVITY:
                inactive_lead_ids.update(risk.affected_leads)
        
        # Schedule follow-ups for inactive leads
        for lead in leads:
            if lead.id in inactive_lead_ids:
                actions = self._create_lead_followup_actions(lead)
                followup_actions.extend(actions)
        
        return followup_actions
    
    def _create_deal_followup_actions(self, deal: Deal) -> List[SalesAction]:
        """Create follow-up actions for a stalled deal."""
        actions = []
        
        # Determine urgency based on deal value
        is_high_value = deal.value >= self.config['escalation_thresholds']['high_value_deal']
        is_critical = deal.value >= self.config['escalation_thresholds']['critical_deal']
        
        # Determine follow-up interval
        interval_hours = self.config['followup_intervals'].get(deal.stage, 24)
        followup_time = datetime.now(timezone.utc) + timedelta(hours=interval_hours)
        
        # Create follow-up task
        task_action = SalesAction(
            action_id=str(uuid.uuid4()),
            action_type=SalesActionType.CREATE_TASK,
            target_system="workflow_engine",
            parameters={
                "task_type": "follow_up",
                "deal_id": deal.id,
                "assigned_rep": deal.assigned_rep,
                "due_date": followup_time.isoformat(),
                "priority": "critical" if is_critical else "high" if is_high_value else "medium",
                "title": f"Follow-up: {deal.stage.value.title()} Deal ${deal.value:,.0f}",
                "description": f"Automated follow-up for stalled deal in {deal.stage.value} stage for {deal.days_in_current_stage} days",
                "deal_value": str(deal.value),
                "deal_stage": deal.stage.value,
                "days_stalled": deal.days_in_current_stage
            },
            expected_outcome=f"Re-engage with deal {deal.id} to move from {deal.stage.value} stage",
            revenue_impact=deal.value * Decimal('0.2'),  # Assume 20% recovery potential
            priority=1 if is_critical else 2 if is_high_value else 3
        )
        actions.append(task_action)
        
        # Create follow-up message
        contact_name = "there"  # Default
        if deal.contact_info and deal.contact_info.first_name:
            contact_name = deal.contact_info.first_name
        
        message_action = SalesAction(
            action_id=str(uuid.uuid4()),
            action_type=SalesActionType.CREATE_FOLLOWUP_MESSAGE,
            target_system="email_system",
            parameters={
                "deal_id": deal.id,
                "recipient_email": deal.contact_info.email if deal.contact_info else None,
                "message": f"Hi {contact_name}, I wanted to follow up on our {deal.stage.value} discussion for ${deal.value:,.0f}. Let's schedule a quick call to move this forward.",
                "subject": f"Following up on our {deal.stage.value} discussion",
                "personalization": {
                    "contact_name": contact_name,
                    "deal_value": str(deal.value),
                    "deal_stage": deal.stage.value
                }
            },
            expected_outcome=f"Re-engage contact for deal {deal.id}",
            revenue_impact=deal.value * Decimal('0.15'),  # Assume 15% engagement impact
            priority=2 if is_high_value else 3
        )
        actions.append(message_action)
        
        # Add manager alert for high-value deals
        if is_high_value:
            alert_action = SalesAction(
                action_id=str(uuid.uuid4()),
                action_type=SalesActionType.SEND_ALERT,
                target_system="notification_system",
                parameters={
                    "alert_type": "stalled_high_value_deal",
                    "deal_id": deal.id,
                    "deal_value": str(deal.value),
                    "deal_stage": deal.stage.value,
                    "days_stalled": deal.days_in_current_stage,
                    "assigned_rep": deal.assigned_rep,
                    "urgency": "high",
                    "message": f"High-value deal ${deal.value:,.0f} stalled in {deal.stage.value} for {deal.days_in_current_stage} days"
                },
                expected_outcome=f"Manager intervention for high-value deal {deal.id}",
                revenue_impact=deal.value * Decimal('0.3'),  # Assume 30% manager intervention impact
                priority=1
            )
            actions.append(alert_action)
        
        return actions
    
    def _create_lead_followup_actions(self, lead: Lead) -> List[SalesAction]:
        """Create follow-up actions for an inactive lead."""
        actions = []
        
        # Create follow-up task
        task_action = SalesAction(
            action_id=str(uuid.uuid4()),
            action_type=SalesActionType.CREATE_TASK,
            target_system="workflow_engine",
            parameters={
                "task_type": "lead_follow_up",
                "lead_id": lead.id,
                "assigned_rep": lead.assigned_rep,
                "due_date": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
                "priority": "medium",
                "title": f"Follow-up: {lead.status.value.title()} Lead",
                "description": f"Automated follow-up for lead with {lead.contact_attempts} contact attempts",
                "contact_attempts": lead.contact_attempts,
                "lead_status": lead.status.value
            },
            expected_outcome=f"Re-engage with lead {lead.id} to advance qualification",
            revenue_impact=lead.estimated_value * Decimal('0.1') if lead.estimated_value else None,
            priority=3
        )
        actions.append(task_action)
        
        return actions
    
    def _prioritize_interventions(
        self,
        risks: List[PipelineRisk],
        deals: List[Deal],
        leads: List[Lead],
        actions: List[SalesAction]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize interventions based on revenue impact and deal probability.
        
        Implements Requirement 8.2: WHEN identifying high-value opportunities at risk,
        THE AARO SHALL prioritize interventions based on potential revenue impact and deal probability
        """
        prioritized_interventions = []
        
        # Create lookup dictionaries
        deal_lookup = {deal.id: deal for deal in deals}
        lead_lookup = {lead.id: lead for lead in leads}
        
        for action in actions:
            # Calculate priority score based on revenue impact and urgency
            priority_score = self._calculate_priority_score(action, deal_lookup, lead_lookup)
            
            # Find associated risk
            associated_risk = None
            for risk in risks:
                if self._is_action_relevant_to_risk(action, risk):
                    associated_risk = risk
                    break
            
            if associated_risk:
                prioritized_interventions.append({
                    'risk_id': associated_risk.risk_id,
                    'action_id': action.action_id,
                    'priority_score': priority_score,
                    'action_type': action.action_type.value,
                    'revenue_impact': str(action.revenue_impact) if action.revenue_impact else None,
                    'expected_outcome': action.expected_outcome
                })
        
        # Sort by priority score (highest first)
        prioritized_interventions.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Limit to max actions per run
        max_actions = self.config['max_actions_per_run']
        return prioritized_interventions[:max_actions]
    
    def _calculate_priority_score(
        self,
        action: SalesAction,
        deal_lookup: Dict[str, Deal],
        lead_lookup: Dict[str, Lead]
    ) -> float:
        """Calculate priority score for an action."""
        base_score = 50.0
        
        # Adjust based on action priority
        priority_multipliers = {1: 2.0, 2: 1.5, 3: 1.0, 4: 0.8, 5: 0.6}
        base_score *= priority_multipliers.get(action.priority, 1.0)
        
        # Adjust based on revenue impact
        if action.revenue_impact:
            revenue_factor = min(float(action.revenue_impact) / 50000.0, 2.0)
            base_score *= (1.0 + revenue_factor)
        
        # Adjust based on deal/lead context
        deal_id = action.parameters.get('deal_id')
        lead_id = action.parameters.get('lead_id')
        
        if deal_id and deal_id in deal_lookup:
            deal = deal_lookup[deal_id]
            # Higher score for high-probability deals
            probability_factor = deal.probability / 100.0
            base_score *= (1.0 + probability_factor)
        
        return min(base_score, 100.0)
    
    def _is_action_relevant_to_risk(self, action: SalesAction, risk: PipelineRisk) -> bool:
        """Check if an action is relevant to a specific risk."""
        params = action.parameters
        
        if 'deal_id' in params and params['deal_id'] in risk.affected_deals:
            return True
        
        if 'lead_id' in params and params['lead_id'] in risk.affected_leads:
            return True
        
        return False
    
    def _monitor_sop_compliance(
        self,
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity]
    ) -> Dict[str, float]:
        """
        Monitor SOP compliance across deals and leads.
        
        Implements Requirement 8.4: THE AARO SHALL monitor and enforce sales SOP
        compliance across all pipeline stages
        """
        compliance_scores = {}
        
        # Create activity lookup
        deal_activities = {}
        lead_activities = {}
        
        for activity in activities:
            if activity.deal_id:
                if activity.deal_id not in deal_activities:
                    deal_activities[activity.deal_id] = []
                deal_activities[activity.deal_id].append(activity)
            
            if activity.lead_id:
                if activity.lead_id not in lead_activities:
                    lead_activities[activity.lead_id] = []
                lead_activities[activity.lead_id].append(activity)
        
        # Calculate compliance scores for deals
        for deal in deals:
            if deal.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                activities_for_deal = deal_activities.get(deal.id, [])
                score = self._calculate_deal_compliance_score(deal, activities_for_deal)
                compliance_scores[f"deal_{deal.id}"] = score
        
        # Calculate compliance scores for leads
        for lead in leads:
            if lead.status not in [LeadStatus.CONVERTED, LeadStatus.LOST, LeadStatus.UNQUALIFIED]:
                activities_for_lead = lead_activities.get(lead.id, [])
                score = self._calculate_lead_compliance_score(lead, activities_for_lead)
                compliance_scores[f"lead_{lead.id}"] = score
        
        return compliance_scores
    
    def _calculate_deal_compliance_score(self, deal: Deal, activities: List[SalesActivity]) -> float:
        """Calculate SOP compliance score for a deal."""
        score = 100.0
        
        # Check if next action is scheduled
        if not deal.next_action_due:
            score -= 25.0
        elif deal.next_action_due < datetime.now(timezone.utc):
            score -= 15.0  # Overdue but scheduled
        
        # Check activity recency
        if activities:
            last_activity = max(activities, key=lambda a: a.completed_at)
            days_since_activity = (datetime.now(timezone.utc) - last_activity.completed_at).days
            
            # Penalize based on stage requirements
            max_days_by_stage = {
                DealStage.PROSPECTING: 7,
                DealStage.QUALIFICATION: 5,
                DealStage.NEEDS_ANALYSIS: 7,
                DealStage.PROPOSAL: 3,
                DealStage.NEGOTIATION: 2
            }
            
            max_days = max_days_by_stage.get(deal.stage, 7)
            if days_since_activity > max_days:
                score -= min((days_since_activity - max_days) * 5, 30.0)
        else:
            score -= 40.0  # No activities at all
        
        # Check activity documentation
        documented_activities = [a for a in activities if a.notes and a.outcome]
        if activities:
            doc_ratio = len(documented_activities) / len(activities)
            score -= (1.0 - doc_ratio) * 20.0
        
        return max(score, 0.0)
    
    def _calculate_lead_compliance_score(self, lead: Lead, activities: List[SalesActivity]) -> float:
        """Calculate SOP compliance score for a lead."""
        score = 100.0
        
        # Check contact attempts
        min_attempts_by_status = {
            LeadStatus.NEW: 1,
            LeadStatus.CONTACTED: 2,
            LeadStatus.QUALIFIED: 1
        }
        
        min_attempts = min_attempts_by_status.get(lead.status, 1)
        if lead.contact_attempts < min_attempts:
            score -= (min_attempts - lead.contact_attempts) * 20.0
        
        # Check contact timing for new leads
        if lead.status == LeadStatus.NEW:
            # Handle both timezone-aware and naive datetimes
            lead_created = lead.created_at
            if lead_created.tzinfo is None:
                lead_created = lead_created.replace(tzinfo=timezone.utc)
            
            hours_since_creation = (datetime.now(timezone.utc) - lead_created).total_seconds() / 3600
            if hours_since_creation > 4:  # Should contact within 4 hours
                score -= min((hours_since_creation - 4) * 2, 30.0)
        
        # Check activity documentation
        if activities:
            documented_activities = [a for a in activities if a.notes]
            doc_ratio = len(documented_activities) / len(activities)
            score -= (1.0 - doc_ratio) * 15.0
        
        return max(score, 0.0)
    
    def _generate_optimization_summary(
        self,
        risks: List[PipelineRisk],
        actions: List[SalesAction],
        deals: List[Deal],
        leads: List[Lead]
    ) -> Dict[str, Any]:
        """Generate optimization summary statistics."""
        # Calculate total pipeline value at risk
        total_pipeline_at_risk = Decimal('0')
        deal_lookup = {deal.id: deal for deal in deals}
        lead_lookup = {lead.id: lead for lead in leads}
        
        for risk in risks:
            for deal_id in risk.affected_deals:
                deal = deal_lookup.get(deal_id)
                if deal:
                    total_pipeline_at_risk += deal.value
            
            for lead_id in risk.affected_leads:
                lead = lead_lookup.get(lead_id)
                if lead and lead.estimated_value:
                    total_pipeline_at_risk += lead.estimated_value
        
        # Calculate potential revenue recovery
        total_recovery_potential = sum(
            action.revenue_impact for action in actions 
            if action.revenue_impact
        ) or Decimal('0')
        
        # Risk distribution
        risk_distribution = {}
        for risk in risks:
            risk_type = risk.risk_type.value
            risk_distribution[risk_type] = risk_distribution.get(risk_type, 0) + 1
        
        # Severity distribution
        severity_distribution = {}
        for risk in risks:
            severity = risk.severity.value
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        return {
            'total_risks_detected': len(risks),
            'total_actions_recommended': len(actions),
            'total_pipeline_at_risk': str(total_pipeline_at_risk),
            'potential_revenue_recovery': str(total_recovery_potential),
            'risk_distribution': risk_distribution,
            'severity_distribution': severity_distribution,
            'deals_analyzed': len(deals),
            'leads_analyzed': len(leads),
            'high_priority_actions': len([a for a in actions if a.priority <= 2]),
            'auto_executable_actions': len([a for a in actions if a.priority >= 3])
        }