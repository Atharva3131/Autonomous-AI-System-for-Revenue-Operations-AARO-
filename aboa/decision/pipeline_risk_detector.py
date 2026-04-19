"""
Pipeline risk detection engine for identifying revenue risks.

This module implements the PipelineRiskDetector class and specific risk detectors
for stalled deals, missed follow-ups, and SOP deviations as specified in
Requirements 3.1, 3.2, 3.3, 3.4.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from ..core.logging import get_logger
from ..models.enums import DealStage, RiskType, Severity
from ..models.revenue_entities import Deal, Lead, PipelineRisk, SalesActivity, SalesRep

logger = get_logger(__name__)


class PipelineRiskDetector:
    """
    Main pipeline risk detection engine that identifies revenue risks
    across deals, leads, and sales activities.

    - Detects deals stalled in a stage beyond defined thresholds
    - Identifies meetings completed without scheduled next actions
    - Detects deals with no recent sales activity
    - Identifies leads contacted fewer than defined minimum touchpoints
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the pipeline risk detector with configuration.
        
        Args:
            config: Configuration dictionary with risk detection thresholds
        """
        self.config = config or self._get_default_config()
        self.logger = logger
        
    def _get_default_config(self) -> Dict:
        """Get default configuration for risk detection thresholds."""
        return {
            # Stalled deal thresholds by stage (in days)
            'stalled_deal_thresholds': {
                DealStage.PROSPECTING: 14,
                DealStage.QUALIFICATION: 10,
                DealStage.NEEDS_ANALYSIS: 14,
                DealStage.PROPOSAL: 7,
                DealStage.NEGOTIATION: 5,
            },
            # Activity thresholds
            'no_activity_threshold_days': 7,
            'high_value_threshold': Decimal('10000'),
            'minimum_lead_touchpoints': 3,
            'missed_followup_threshold_days': 2,
            # Severity thresholds
            'critical_deal_value': Decimal('50000'),
            'high_risk_deal_value': Decimal('25000'),
            'medium_risk_deal_value': Decimal('10000'),
        }
    
    def detect_pipeline_risks(
        self, 
        deals: List[Deal], 
        leads: List[Lead], 
        activities: List[SalesActivity],
        reps: List[SalesRep]
    ) -> List[PipelineRisk]:
        """
        Detect all pipeline risks across the provided data.
        
        Args:
            deals: List of deals to analyze
            leads: List of leads to analyze
            activities: List of sales activities
            reps: List of sales representatives
            
        Returns:
            List of detected pipeline risks
        """
        risks = []
        
        # Create activity lookup for efficiency
        deal_activities = self._group_activities_by_deal(activities)
        lead_activities = self._group_activities_by_lead(activities)
        
        # Detect stalled deals (Requirement 3.1)
        risks.extend(self._detect_stalled_deals(deals, deal_activities))
        
        # Detect missed follow-ups (Requirement 3.2)
        risks.extend(self._detect_missed_followups(deals, leads, deal_activities, lead_activities))
        
        # Detect inactive high-value opportunities (Requirement 3.3)
        risks.extend(self._detect_inactive_high_value_deals(deals, deal_activities))
        
        # Detect leads with insufficient touchpoints (Requirement 3.4)
        risks.extend(self._detect_insufficient_lead_touchpoints(leads, lead_activities))
        
        self.logger.info(f"Detected {len(risks)} pipeline risks")
        return risks
    
    def _group_activities_by_deal(self, activities: List[SalesActivity]) -> Dict[str, List[SalesActivity]]:
        """Group activities by deal ID for efficient lookup."""
        deal_activities = {}
        for activity in activities:
            if activity.deal_id:
                if activity.deal_id not in deal_activities:
                    deal_activities[activity.deal_id] = []
                deal_activities[activity.deal_id].append(activity)
        return deal_activities
    
    def _group_activities_by_lead(self, activities: List[SalesActivity]) -> Dict[str, List[SalesActivity]]:
        """Group activities by lead ID for efficient lookup."""
        lead_activities = {}
        for activity in activities:
            if activity.lead_id:
                if activity.lead_id not in lead_activities:
                    lead_activities[activity.lead_id] = []
                lead_activities[activity.lead_id].append(activity)
        return lead_activities
    
    def _detect_stalled_deals(
        self, 
        deals: List[Deal], 
        deal_activities: Dict[str, List[SalesActivity]]
    ) -> List[PipelineRisk]:
        """
        Detect deals stalled in a stage beyond defined thresholds.
        
        Implements Requirement 3.1: WHEN analyzing pipeline data, 
        THE Decision_Engine SHALL detect deals stalled in a stage beyond defined thresholds
        """
        risks = []
        now = datetime.now(timezone.utc)
        
        for deal in deals:
            # Skip closed deals
            if deal.stage in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                continue
                
            threshold_days = self.config['stalled_deal_thresholds'].get(deal.stage, 14)
            
            # Check if deal has been in current stage too long
            if deal.days_in_current_stage > threshold_days:
                severity = self._calculate_deal_severity(deal)
                confidence = self._calculate_stalled_deal_confidence(deal, deal_activities.get(deal.id, []))
                
                risk = PipelineRisk(
                    risk_id=str(uuid.uuid4()),
                    risk_type=RiskType.STALLED_DEAL,
                    detected_at=now,
                    confidence=confidence,
                    affected_deals=[deal.id],
                    severity=severity,
                    description=f"Deal {deal.id} has been stalled in {deal.stage.value} stage for {deal.days_in_current_stage} days (threshold: {threshold_days} days)",
                    recommended_actions=self._get_stalled_deal_actions(deal)
                )
                risks.append(risk)
                
        return risks
    
    def _detect_missed_followups(
        self,
        deals: List[Deal],
        leads: List[Lead], 
        deal_activities: Dict[str, List[SalesActivity]],
        lead_activities: Dict[str, List[SalesActivity]]
    ) -> List[PipelineRisk]:
        """
        Detect meetings completed without scheduled next actions.
        
        Implements Requirement 3.2: WHEN reviewing activity data, 
        THE Decision_Engine SHALL identify meetings completed without scheduled next actions
        """
        risks = []
        now = datetime.now(timezone.utc)
        threshold_days = self.config['missed_followup_threshold_days']
        
        # Check deals for missed follow-ups
        for deal in deals:
            if deal.stage in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                continue
                
            activities = deal_activities.get(deal.id, [])
            recent_meetings = [
                a for a in activities 
                if a.activity_type.value in ['meeting', 'demo'] 
                and (now - a.completed_at).days <= threshold_days
                and not a.next_action_scheduled
            ]
            
            if recent_meetings:
                severity = self._calculate_deal_severity(deal)
                confidence = 85.0  # High confidence for clear pattern
                
                risk = PipelineRisk(
                    risk_id=str(uuid.uuid4()),
                    risk_type=RiskType.MISSED_FOLLOWUP,
                    detected_at=now,
                    confidence=confidence,
                    affected_deals=[deal.id],
                    severity=severity,
                    description=f"Deal {deal.id} has {len(recent_meetings)} recent meetings without scheduled follow-up actions",
                    recommended_actions=self._get_missed_followup_actions(deal)
                )
                risks.append(risk)
        
        # Check leads for missed follow-ups
        for lead in leads:
            if lead.status.value in ['converted', 'lost', 'unqualified']:
                continue
                
            activities = lead_activities.get(lead.id, [])
            recent_meetings = [
                a for a in activities 
                if a.activity_type.value in ['meeting', 'demo', 'call']
                and (now - a.completed_at).days <= threshold_days
                and not a.next_action_scheduled
            ]
            
            if recent_meetings:
                severity = self._calculate_lead_severity(lead)
                confidence = 80.0
                
                risk = PipelineRisk(
                    risk_id=str(uuid.uuid4()),
                    risk_type=RiskType.MISSED_FOLLOWUP,
                    detected_at=now,
                    confidence=confidence,
                    affected_deals=[],  # No deals for leads
                    affected_leads=[lead.id],  # Track affected lead
                    severity=severity,
                    description=f"Lead {lead.id} has {len(recent_meetings)} recent interactions without scheduled follow-up actions",
                    recommended_actions=self._get_missed_followup_lead_actions(lead)
                )
                risks.append(risk)
                
        return risks
    
    def _detect_inactive_high_value_deals(
        self,
        deals: List[Deal],
        deal_activities: Dict[str, List[SalesActivity]]
    ) -> List[PipelineRisk]:
        """
        Detect high-value deals with no recent sales activity.
        
        Implements Requirement 3.3: WHEN examining high-value opportunities, 
        THE Decision_Engine SHALL detect deals with no recent sales activity
        """
        risks = []
        now = datetime.now(timezone.utc)
        threshold_days = self.config['no_activity_threshold_days']
        high_value_threshold = self.config['high_value_threshold']
        
        for deal in deals:
            # Skip closed deals and low-value deals
            if deal.stage in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                continue
            if deal.value < high_value_threshold:
                continue
                
            # Check for recent activity
            activities = deal_activities.get(deal.id, [])
            if activities:
                last_activity = max(activities, key=lambda a: a.completed_at)
                days_since_activity = (now - last_activity.completed_at).days
            else:
                # Use deal's last_activity if no activities found
                if deal.last_activity:
                    days_since_activity = (now - deal.last_activity).days
                else:
                    days_since_activity = threshold_days + 1  # Force detection
            
            if days_since_activity > threshold_days:
                severity = self._calculate_deal_severity(deal)
                confidence = self._calculate_inactive_deal_confidence(deal, days_since_activity)
                
                risk = PipelineRisk(
                    risk_id=str(uuid.uuid4()),
                    risk_type=RiskType.INACTIVE_HIGH_VALUE,
                    detected_at=now,
                    confidence=confidence,
                    affected_deals=[deal.id],
                    severity=severity,
                    description=f"High-value deal {deal.id} (${deal.value}) has no activity for {days_since_activity} days (threshold: {threshold_days} days)",
                    recommended_actions=self._get_inactive_deal_actions(deal)
                )
                risks.append(risk)
                
        return risks
    
    def _detect_insufficient_lead_touchpoints(
        self,
        leads: List[Lead],
        lead_activities: Dict[str, List[SalesActivity]]
    ) -> List[PipelineRisk]:
        """
        Detect leads contacted fewer than defined minimum touchpoints.
        
        Implements Requirement 3.4: WHEN monitoring lead engagement, 
        THE Decision_Engine SHALL identify leads contacted fewer than defined minimum touchpoints
        """
        risks = []
        now = datetime.now(timezone.utc)
        min_touchpoints = self.config['minimum_lead_touchpoints']
        
        for lead in leads:
            # Skip converted, lost, or unqualified leads
            if lead.status.value in ['converted', 'lost', 'unqualified']:
                continue
                
            # Count touchpoints (activities + contact_attempts)
            activities = lead_activities.get(lead.id, [])
            total_touchpoints = len(activities) + lead.contact_attempts
            
            if total_touchpoints < min_touchpoints:
                severity = self._calculate_lead_severity(lead)
                confidence = 75.0  # Medium-high confidence
                
                risk = PipelineRisk(
                    risk_id=str(uuid.uuid4()),
                    risk_type=RiskType.LOW_ACTIVITY,
                    detected_at=now,
                    confidence=confidence,
                    affected_deals=[],  # No deals for leads
                    affected_leads=[lead.id],  # Track affected lead
                    severity=severity,
                    description=f"Lead {lead.id} has only {total_touchpoints} touchpoints (minimum: {min_touchpoints})",
                    recommended_actions=self._get_low_activity_lead_actions(lead)
                )
                risks.append(risk)
                
        return risks
    
    def _calculate_deal_severity(self, deal: Deal) -> Severity:
        """Calculate severity level based on deal value and stage."""
        if deal.value >= self.config['critical_deal_value']:
            return Severity.CRITICAL
        elif deal.value >= self.config['high_risk_deal_value']:
            return Severity.HIGH
        elif deal.value >= self.config['medium_risk_deal_value']:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    def _calculate_lead_severity(self, lead: Lead) -> Severity:
        """Calculate severity level for leads based on estimated value."""
        if lead.estimated_value:
            if lead.estimated_value >= self.config['critical_deal_value']:
                return Severity.HIGH
            elif lead.estimated_value >= self.config['high_risk_deal_value']:
                return Severity.MEDIUM
            else:
                return Severity.LOW
        else:
            return Severity.LOW
    
    def _calculate_stalled_deal_confidence(
        self, 
        deal: Deal, 
        activities: List[SalesActivity]
    ) -> float:
        """Calculate confidence level for stalled deal detection."""
        base_confidence = 70.0
        
        # Increase confidence based on how long it's been stalled
        threshold = self.config['stalled_deal_thresholds'].get(deal.stage, 14)
        days_over = deal.days_in_current_stage - threshold
        confidence_boost = min(days_over * 2, 25.0)  # Max 25% boost
        
        # Decrease confidence if there's recent activity
        if activities:
            recent_activities = [
                a for a in activities 
                if (datetime.now(timezone.utc) - a.completed_at).days <= 3
            ]
            if recent_activities:
                confidence_boost -= 10.0
        
        return min(base_confidence + confidence_boost, 95.0)
    
    def _calculate_inactive_deal_confidence(self, deal: Deal, days_inactive: int) -> float:
        """Calculate confidence level for inactive deal detection."""
        base_confidence = 80.0
        threshold = self.config['no_activity_threshold_days']
        
        # Increase confidence based on how long it's been inactive
        days_over = days_inactive - threshold
        confidence_boost = min(days_over * 3, 15.0)  # Max 15% boost
        
        return min(base_confidence + confidence_boost, 95.0)
    
    def _get_stalled_deal_actions(self, deal: Deal) -> List[str]:
        """Get recommended actions for stalled deals."""
        return [
            f"create_followup_task_{deal.id}",
            f"schedule_manager_review_{deal.id}",
            f"update_deal_priority_{deal.id}"
        ]
    
    def _get_missed_followup_actions(self, deal: Deal) -> List[str]:
        """Get recommended actions for missed follow-ups on deals."""
        return [
            f"create_followup_task_{deal.id}",
            f"schedule_next_meeting_{deal.id}",
            f"send_followup_email_{deal.id}"
        ]
    
    def _get_missed_followup_lead_actions(self, lead: Lead) -> List[str]:
        """Get recommended actions for missed follow-ups on leads."""
        return [
            f"create_followup_task_{lead.id}",
            f"schedule_lead_call_{lead.id}",
            f"send_followup_email_{lead.id}"
        ]
    
    def _get_inactive_deal_actions(self, deal: Deal) -> List[str]:
        """Get recommended actions for inactive high-value deals."""
        return [
            f"urgent_followup_task_{deal.id}",
            f"manager_intervention_{deal.id}",
            f"deal_health_check_{deal.id}",
            f"schedule_urgent_meeting_{deal.id}"
        ]
    
    def _get_low_activity_lead_actions(self, lead: Lead) -> List[str]:
        """Get recommended actions for leads with low activity."""
        return [
            f"increase_touchpoints_{lead.id}",
            f"schedule_qualification_call_{lead.id}",
            f"send_nurture_sequence_{lead.id}"
        ]
    
    def classify_risk_severity(self, risk: PipelineRisk, deals: List[Deal]) -> Severity:
        """
        Classify the severity of a detected risk.
        
        Args:
            risk: The pipeline risk to classify
            deals: List of all deals for context
            
        Returns:
            Severity level of the risk
        """
        if not risk.affected_deals:
            return Severity.LOW
            
        # Find the highest value deal affected
        affected_deal_values = []
        for deal in deals:
            if deal.id in risk.affected_deals:
                affected_deal_values.append(deal.value)
        
        if not affected_deal_values:
            return Severity.LOW
            
        max_value = max(affected_deal_values)
        
        # Classify based on deal value and risk type
        if risk.risk_type == RiskType.INACTIVE_HIGH_VALUE:
            if max_value >= self.config['critical_deal_value']:
                return Severity.CRITICAL
            else:
                return Severity.HIGH
        elif risk.risk_type == RiskType.STALLED_DEAL:
            if max_value >= self.config['critical_deal_value']:
                return Severity.CRITICAL
            elif max_value >= self.config['high_risk_deal_value']:
                return Severity.HIGH
            elif max_value >= self.config['medium_risk_deal_value']:
                return Severity.MEDIUM
            else:
                return Severity.LOW
        else:
            # For other risk types, use standard classification
            if max_value >= self.config['high_risk_deal_value']:
                return Severity.HIGH
            elif max_value >= self.config['medium_risk_deal_value']:
                return Severity.MEDIUM
            else:
                return Severity.LOW