"""
Sales Process Efficiency Optimizer.

This module implements rep performance analysis, coaching recommendations,
sales resource allocation optimization, and process efficiency improvements
for the ABOA system.

Implements Requirements 8.3, 8.5, 8.7.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from ..core.logging import get_logger
from ..models.enums import ActivityType, DealStage, LeadStatus, Severity
from ..models.revenue_entities import Deal, Lead, SalesActivity, SalesRep

logger = get_logger(__name__)


class RepPerformanceAnalyzer:
    """Analyzes sales rep performance and generates coaching recommendations."""
    
    def __init__(self):
        self.performance_thresholds = {
            'min_activities_per_week': 20,
            'min_conversion_rate': 15.0,  # percentage
            'max_avg_deal_velocity': 90,  # days
            'min_quota_attainment': 80.0,  # percentage
            'min_pipeline_coverage': 3.0   # pipeline to quota ratio
        }
    
    def analyze_rep_performance(
        self, 
        rep: SalesRep, 
        deals: List[Deal], 
        activities: List[SalesActivity],
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze comprehensive rep performance metrics.
        
        Args:
            rep: Sales representative to analyze
            deals: Deals associated with the rep
            activities: Activities performed by the rep
            time_period_days: Analysis time period in days
            
        Returns:
            Dict containing performance analysis and recommendations
        """
        logger.info(f"Analyzing performance for rep {rep.id}")
        
        # Filter data for the time period
        cutoff_date = datetime.utcnow() - timedelta(days=time_period_days)
        recent_activities = [a for a in activities if a.rep_id == rep.id and a.completed_at >= cutoff_date]
        rep_deals = [d for d in deals if d.assigned_rep == rep.id]
        
        # Calculate performance metrics
        activity_metrics = self._calculate_activity_metrics(recent_activities, time_period_days)
        deal_metrics = self._calculate_deal_metrics(rep_deals, rep)
        conversion_metrics = self._calculate_conversion_metrics(rep_deals, recent_activities)
        velocity_metrics = self._calculate_velocity_metrics(rep_deals)
        
        # Generate performance score
        performance_score = self._calculate_performance_score(
            activity_metrics, deal_metrics, conversion_metrics, velocity_metrics, rep
        )
        
        # Generate coaching recommendations
        coaching_recommendations = self._generate_coaching_recommendations(
            activity_metrics, deal_metrics, conversion_metrics, velocity_metrics, rep
        )
        
        # Identify improvement areas
        improvement_areas = self._identify_improvement_areas(
            activity_metrics, deal_metrics, conversion_metrics, velocity_metrics, rep
        )
        
        return {
            'rep_id': rep.id,
            'analysis_period_days': time_period_days,
            'performance_score': performance_score,
            'activity_metrics': activity_metrics,
            'deal_metrics': deal_metrics,
            'conversion_metrics': conversion_metrics,
            'velocity_metrics': velocity_metrics,
            'coaching_recommendations': coaching_recommendations,
            'improvement_areas': improvement_areas,
            'analyzed_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_activity_metrics(self, activities: List[SalesActivity], period_days: int) -> Dict[str, Any]:
        """Calculate activity-based performance metrics."""
        total_activities = len(activities)
        activities_per_week = (total_activities / period_days) * 7
        
        # Activity type distribution
        activity_distribution = {}
        for activity in activities:
            activity_type = activity.activity_type.value
            activity_distribution[activity_type] = activity_distribution.get(activity_type, 0) + 1
        
        # Next action scheduling rate
        scheduled_next_actions = sum(1 for a in activities if a.next_action_scheduled)
        next_action_rate = (scheduled_next_actions / total_activities * 100) if total_activities > 0 else 0
        
        return {
            'total_activities': total_activities,
            'activities_per_week': round(activities_per_week, 2),
            'activity_distribution': activity_distribution,
            'next_action_scheduling_rate': round(next_action_rate, 2),
            'meets_activity_threshold': activities_per_week >= self.performance_thresholds['min_activities_per_week']
        }
    
    def _calculate_deal_metrics(self, deals: List[Deal], rep: SalesRep) -> Dict[str, Any]:
        """Calculate deal-based performance metrics."""
        total_deals = len(deals)
        total_pipeline_value = sum(deal.value for deal in deals if deal.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST])
        
        # Deal stage distribution
        stage_distribution = {}
        for deal in deals:
            stage = deal.stage.value
            stage_distribution[stage] = stage_distribution.get(stage, 0) + 1
        
        # Pipeline coverage ratio
        pipeline_coverage = float(total_pipeline_value / rep.quota) if rep.quota > 0 else 0
        
        # Won/lost analysis
        won_deals = [d for d in deals if d.stage == DealStage.CLOSED_WON]
        lost_deals = [d for d in deals if d.stage == DealStage.CLOSED_LOST]
        won_value = sum(deal.value for deal in won_deals)
        
        return {
            'total_deals': total_deals,
            'total_pipeline_value': float(total_pipeline_value),
            'pipeline_coverage_ratio': round(pipeline_coverage, 2),
            'stage_distribution': stage_distribution,
            'won_deals_count': len(won_deals),
            'lost_deals_count': len(lost_deals),
            'won_deals_value': float(won_value),
            'quota_attainment': rep.quota_attainment,
            'meets_pipeline_coverage': pipeline_coverage >= self.performance_thresholds['min_pipeline_coverage']
        }
    
    def _calculate_conversion_metrics(self, deals: List[Deal], activities: List[SalesActivity]) -> Dict[str, Any]:
        """Calculate conversion rate metrics."""
        # Stage-to-stage conversion rates
        stage_conversions = {}
        stages = list(DealStage)
        
        for i, stage in enumerate(stages[:-2]):  # Exclude closed stages
            current_stage_deals = [d for d in deals if d.stage == stage]
            if i < len(stages) - 3:  # Has next stage
                next_stage = stages[i + 1]
                progressed_deals = [d for d in deals if d.stage.value in [s.value for s in stages[i+1:]]]
                conversion_rate = (len(progressed_deals) / len(current_stage_deals) * 100) if current_stage_deals else 0
                stage_conversions[f"{stage.value}_to_{next_stage.value}"] = round(conversion_rate, 2)
        
        # Overall conversion rate (prospecting to closed won)
        prospecting_deals = [d for d in deals if d.stage == DealStage.PROSPECTING]
        won_deals = [d for d in deals if d.stage == DealStage.CLOSED_WON]
        overall_conversion = (len(won_deals) / len(prospecting_deals) * 100) if prospecting_deals else 0
        
        return {
            'stage_conversions': stage_conversions,
            'overall_conversion_rate': round(overall_conversion, 2),
            'meets_conversion_threshold': overall_conversion >= self.performance_thresholds['min_conversion_rate']
        }
    
    def _calculate_velocity_metrics(self, deals: List[Deal]) -> Dict[str, Any]:
        """Calculate deal velocity metrics."""
        # Average days in current stage
        active_deals = [d for d in deals if d.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]]
        avg_days_in_stage = sum(deal.days_in_current_stage for deal in active_deals) / len(active_deals) if active_deals else 0
        
        # Stalled deals (in stage > 30 days)
        stalled_deals = [d for d in active_deals if d.days_in_current_stage > 30]
        stalled_percentage = (len(stalled_deals) / len(active_deals) * 100) if active_deals else 0
        
        # Deal velocity by stage
        stage_velocities = {}
        for stage in DealStage:
            if stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                stage_deals = [d for d in deals if d.stage == stage]
                if stage_deals:
                    avg_velocity = sum(d.days_in_current_stage for d in stage_deals) / len(stage_deals)
                    stage_velocities[stage.value] = round(avg_velocity, 2)
        
        return {
            'avg_days_in_current_stage': round(avg_days_in_stage, 2),
            'stalled_deals_count': len(stalled_deals),
            'stalled_deals_percentage': round(stalled_percentage, 2),
            'stage_velocities': stage_velocities,
            'meets_velocity_threshold': avg_days_in_stage <= self.performance_thresholds['max_avg_deal_velocity']
        }
    
    def _calculate_performance_score(
        self, 
        activity_metrics: Dict[str, Any],
        deal_metrics: Dict[str, Any],
        conversion_metrics: Dict[str, Any],
        velocity_metrics: Dict[str, Any],
        rep: SalesRep
    ) -> float:
        """Calculate overall performance score (0-100)."""
        score = 0.0
        
        # Activity score (25%)
        if activity_metrics['meets_activity_threshold']:
            score += 25
        else:
            activity_ratio = activity_metrics['activities_per_week'] / self.performance_thresholds['min_activities_per_week']
            score += min(25, 25 * activity_ratio)
        
        # Deal management score (25%)
        if deal_metrics['meets_pipeline_coverage']:
            score += 25
        else:
            coverage_ratio = deal_metrics['pipeline_coverage_ratio'] / self.performance_thresholds['min_pipeline_coverage']
            score += min(25, 25 * coverage_ratio)
        
        # Conversion score (25%)
        if conversion_metrics['meets_conversion_threshold']:
            score += 25
        else:
            conversion_ratio = conversion_metrics['overall_conversion_rate'] / self.performance_thresholds['min_conversion_rate']
            score += min(25, 25 * conversion_ratio)
        
        # Velocity score (25%)
        if velocity_metrics['meets_velocity_threshold']:
            score += 25
        else:
            velocity_ratio = self.performance_thresholds['max_avg_deal_velocity'] / max(1, velocity_metrics['avg_days_in_current_stage'])
            score += min(25, 25 * velocity_ratio)
        
        return round(score, 2)
    
    def _generate_coaching_recommendations(
        self,
        activity_metrics: Dict[str, Any],
        deal_metrics: Dict[str, Any],
        conversion_metrics: Dict[str, Any],
        velocity_metrics: Dict[str, Any],
        rep: SalesRep
    ) -> List[Dict[str, Any]]:
        """Generate specific coaching recommendations based on performance gaps."""
        recommendations = []
        
        # Activity coaching
        if not activity_metrics['meets_activity_threshold']:
            recommendations.append({
                'category': 'activity_management',
                'priority': 'high',
                'title': 'Increase Sales Activity Volume',
                'description': f"Current activity level ({activity_metrics['activities_per_week']}/week) is below target ({self.performance_thresholds['min_activities_per_week']}/week)",
                'action_items': [
                    'Schedule dedicated prospecting blocks daily',
                    'Set daily activity targets and track progress',
                    'Use CRM automation to streamline activity logging'
                ]
            })
        
        # Next action scheduling
        if activity_metrics['next_action_scheduling_rate'] < 80:
            recommendations.append({
                'category': 'process_adherence',
                'priority': 'medium',
                'title': 'Improve Next Action Scheduling',
                'description': f"Only {activity_metrics['next_action_scheduling_rate']}% of activities have scheduled next actions",
                'action_items': [
                    'Always schedule next action before ending calls/meetings',
                    'Use calendar blocking for follow-up activities',
                    'Review and update deal next actions weekly'
                ]
            })
        
        # Pipeline coverage
        if not deal_metrics['meets_pipeline_coverage']:
            recommendations.append({
                'category': 'pipeline_management',
                'priority': 'high',
                'title': 'Build Pipeline Coverage',
                'description': f"Pipeline coverage ratio ({deal_metrics['pipeline_coverage_ratio']}x) is below target ({self.performance_thresholds['min_pipeline_coverage']}x)",
                'action_items': [
                    'Increase prospecting activities by 30%',
                    'Focus on higher-value opportunities',
                    'Review and qualify existing pipeline for accuracy'
                ]
            })
        
        # Conversion rate improvement
        if not conversion_metrics['meets_conversion_threshold']:
            recommendations.append({
                'category': 'conversion_optimization',
                'priority': 'high',
                'title': 'Improve Conversion Rates',
                'description': f"Overall conversion rate ({conversion_metrics['overall_conversion_rate']}%) is below target ({self.performance_thresholds['min_conversion_rate']}%)",
                'action_items': [
                    'Review qualification criteria and process',
                    'Practice objection handling techniques',
                    'Analyze lost deals for common patterns'
                ]
            })
        
        # Deal velocity improvement
        if not velocity_metrics['meets_velocity_threshold']:
            recommendations.append({
                'category': 'velocity_improvement',
                'priority': 'medium',
                'title': 'Accelerate Deal Velocity',
                'description': f"Average time in stage ({velocity_metrics['avg_days_in_current_stage']} days) exceeds target ({self.performance_thresholds['max_avg_deal_velocity']} days)",
                'action_items': [
                    'Create urgency in prospect communications',
                    'Identify and address deal blockers proactively',
                    'Set clear next steps with specific timelines'
                ]
            })
        
        # Stalled deals
        if velocity_metrics['stalled_deals_percentage'] > 20:
            recommendations.append({
                'category': 'deal_management',
                'priority': 'high',
                'title': 'Address Stalled Deals',
                'description': f"{velocity_metrics['stalled_deals_percentage']}% of deals are stalled (>30 days in stage)",
                'action_items': [
                    'Review stalled deals weekly with manager',
                    'Re-qualify stalled opportunities',
                    'Create action plans to move deals forward'
                ]
            })
        
        return recommendations
    
    def _identify_improvement_areas(
        self,
        activity_metrics: Dict[str, Any],
        deal_metrics: Dict[str, Any],
        conversion_metrics: Dict[str, Any],
        velocity_metrics: Dict[str, Any],
        rep: SalesRep
    ) -> List[str]:
        """Identify key areas for improvement."""
        areas = []
        
        if not activity_metrics['meets_activity_threshold']:
            areas.append('activity_volume')
        
        if activity_metrics['next_action_scheduling_rate'] < 80:
            areas.append('process_adherence')
        
        if not deal_metrics['meets_pipeline_coverage']:
            areas.append('pipeline_building')
        
        if not conversion_metrics['meets_conversion_threshold']:
            areas.append('conversion_optimization')
        
        if not velocity_metrics['meets_velocity_threshold']:
            areas.append('deal_velocity')
        
        if velocity_metrics['stalled_deals_percentage'] > 20:
            areas.append('deal_management')
        
        return areas


class ResourceAllocationOptimizer:
    """Optimizes sales resource allocation across territories, accounts, and opportunities."""
    
    def __init__(self):
        self.allocation_weights = {
            'deal_value': 0.3,
            'probability': 0.25,
            'velocity': 0.2,
            'rep_capacity': 0.15,
            'strategic_importance': 0.1
        }
    
    def optimize_resource_allocation(
        self,
        reps: List[SalesRep],
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity]
    ) -> Dict[str, Any]:
        """
        Optimize resource allocation across sales team.
        
        Args:
            reps: List of sales representatives
            deals: List of deals
            leads: List of leads
            activities: List of activities
            
        Returns:
            Dict containing optimization recommendations
        """
        logger.info("Optimizing sales resource allocation")
        
        # Analyze current workload distribution
        workload_analysis = self._analyze_workload_distribution(reps, deals, leads, activities)
        
        # Identify capacity constraints and opportunities
        capacity_analysis = self._analyze_capacity_constraints(reps, deals, activities)
        
        # Generate reallocation recommendations
        reallocation_recommendations = self._generate_reallocation_recommendations(
            reps, deals, leads, workload_analysis, capacity_analysis
        )
        
        # Calculate expected impact
        expected_impact = self._calculate_reallocation_impact(reallocation_recommendations, deals)
        
        return {
            'workload_analysis': workload_analysis,
            'capacity_analysis': capacity_analysis,
            'reallocation_recommendations': reallocation_recommendations,
            'expected_impact': expected_impact,
            'optimized_at': datetime.utcnow().isoformat()
        }
    
    def _analyze_workload_distribution(
        self,
        reps: List[SalesRep],
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity]
    ) -> Dict[str, Any]:
        """Analyze current workload distribution across reps."""
        rep_workloads = {}
        
        for rep in reps:
            rep_deals = [d for d in deals if d.assigned_rep == rep.id]
            rep_leads = [l for l in leads if l.assigned_rep == rep.id]
            rep_activities = [a for a in activities if a.rep_id == rep.id]
            
            # Calculate workload metrics
            total_pipeline_value = sum(d.value for d in rep_deals if d.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST])
            active_deals_count = len([d for d in rep_deals if d.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]])
            active_leads_count = len([l for l in rep_leads if l.status not in [LeadStatus.CONVERTED, LeadStatus.LOST]])
            
            # Recent activity level (last 7 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_activities = len([a for a in rep_activities if a.completed_at >= recent_cutoff])
            
            rep_workloads[rep.id] = {
                'rep_name': rep.name,
                'total_pipeline_value': float(total_pipeline_value),
                'active_deals_count': active_deals_count,
                'active_leads_count': active_leads_count,
                'recent_activities_count': recent_activities,
                'quota': float(rep.quota),
                'quota_attainment': rep.quota_attainment,
                'workload_score': self._calculate_workload_score(
                    active_deals_count, active_leads_count, total_pipeline_value, rep.quota
                )
            }
        
        # Calculate distribution statistics
        workload_scores = [w['workload_score'] for w in rep_workloads.values()]
        avg_workload = sum(workload_scores) / len(workload_scores) if workload_scores else 0
        workload_variance = sum((score - avg_workload) ** 2 for score in workload_scores) / len(workload_scores) if workload_scores else 0
        
        return {
            'rep_workloads': rep_workloads,
            'average_workload_score': round(avg_workload, 2),
            'workload_variance': round(workload_variance, 2),
            'distribution_balance': 'balanced' if workload_variance < 100 else 'imbalanced'
        }
    
    def _analyze_capacity_constraints(
        self,
        reps: List[SalesRep],
        deals: List[Deal],
        activities: List[SalesActivity]
    ) -> Dict[str, Any]:
        """Analyze capacity constraints and utilization."""
        capacity_analysis = {}
        
        for rep in reps:
            rep_deals = [d for d in deals if d.assigned_rep == rep.id]
            rep_activities = [a for a in activities if a.rep_id == rep.id]
            
            # Calculate capacity metrics
            recent_cutoff = datetime.utcnow() - timedelta(days=30)
            recent_activities = [a for a in rep_activities if a.completed_at >= recent_cutoff]
            
            # Estimate capacity utilization
            activities_per_day = len(recent_activities) / 30
            estimated_capacity = 10  # Assume 10 activities per day capacity
            utilization_rate = (activities_per_day / estimated_capacity) * 100
            
            # Identify constraints
            constraints = []
            if utilization_rate > 90:
                constraints.append('overutilized')
            elif utilization_rate < 50:
                constraints.append('underutilized')
            
            if len(rep_deals) > 20:
                constraints.append('too_many_deals')
            
            capacity_analysis[rep.id] = {
                'rep_name': rep.name,
                'utilization_rate': round(utilization_rate, 2),
                'activities_per_day': round(activities_per_day, 2),
                'estimated_capacity': estimated_capacity,
                'constraints': constraints,
                'available_capacity': max(0, estimated_capacity - activities_per_day)
            }
        
        return capacity_analysis
    
    def _generate_reallocation_recommendations(
        self,
        reps: List[SalesRep],
        deals: List[Deal],
        leads: List[Lead],
        workload_analysis: Dict[str, Any],
        capacity_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate specific reallocation recommendations."""
        recommendations = []
        
        # Identify overloaded and underloaded reps
        overloaded_reps = []
        underloaded_reps = []
        
        for rep_id, capacity in capacity_analysis.items():
            if 'overutilized' in capacity['constraints']:
                overloaded_reps.append(rep_id)
            elif 'underutilized' in capacity['constraints']:
                underloaded_reps.append(rep_id)
        
        # Generate deal reallocation recommendations
        for overloaded_rep_id in overloaded_reps:
            if underloaded_reps:
                overloaded_deals = [d for d in deals if d.assigned_rep == overloaded_rep_id]
                
                # Find deals to reallocate (prioritize lower probability, lower value)
                reallocation_candidates = sorted(
                    [d for d in overloaded_deals if d.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]],
                    key=lambda x: (x.probability, x.value)
                )[:3]  # Top 3 candidates
                
                for deal in reallocation_candidates:
                    target_rep_id = underloaded_reps[0]  # Simple assignment to first available
                    
                    recommendations.append({
                        'type': 'deal_reallocation',
                        'priority': 'medium',
                        'from_rep_id': overloaded_rep_id,
                        'to_rep_id': target_rep_id,
                        'deal_id': deal.id,
                        'deal_value': float(deal.value),
                        'rationale': f"Rebalance workload from overutilized rep to underutilized rep",
                        'expected_benefit': 'improved_focus_and_conversion'
                    })
        
        # Generate lead reallocation recommendations
        for overloaded_rep_id in overloaded_reps:
            if underloaded_reps:
                overloaded_leads = [l for l in leads if l.assigned_rep == overloaded_rep_id]
                
                # Find leads to reallocate (prioritize lower qualification scores)
                reallocation_candidates = sorted(
                    [l for l in overloaded_leads if l.status not in [LeadStatus.CONVERTED, LeadStatus.LOST]],
                    key=lambda x: x.qualification_score or 0
                )[:5]  # Top 5 candidates
                
                for lead in reallocation_candidates:
                    target_rep_id = underloaded_reps[0]
                    
                    recommendations.append({
                        'type': 'lead_reallocation',
                        'priority': 'low',
                        'from_rep_id': overloaded_rep_id,
                        'to_rep_id': target_rep_id,
                        'lead_id': lead.id,
                        'estimated_value': float(lead.estimated_value) if lead.estimated_value else 0,
                        'rationale': f"Distribute lead workload more evenly",
                        'expected_benefit': 'improved_lead_response_time'
                    })
        
        return recommendations
    
    def _calculate_workload_score(
        self,
        active_deals: int,
        active_leads: int,
        pipeline_value: Decimal,
        quota: Decimal
    ) -> float:
        """Calculate a workload score for a rep."""
        # Normalize metrics
        deal_score = min(active_deals / 15, 1.0) * 40  # Max 40 points for deals
        lead_score = min(active_leads / 25, 1.0) * 30  # Max 30 points for leads
        pipeline_score = min(float(pipeline_value / quota), 2.0) * 30 if quota > 0 else 0  # Max 30 points for pipeline
        
        return deal_score + lead_score + pipeline_score
    
    def _calculate_reallocation_impact(
        self,
        recommendations: List[Dict[str, Any]],
        deals: List[Deal]
    ) -> Dict[str, Any]:
        """Calculate expected impact of reallocation recommendations."""
        total_deals_reallocated = len([r for r in recommendations if r['type'] == 'deal_reallocation'])
        total_leads_reallocated = len([r for r in recommendations if r['type'] == 'lead_reallocation'])
        
        total_value_reallocated = sum(
            r['deal_value'] for r in recommendations 
            if r['type'] == 'deal_reallocation'
        )
        
        # Estimate impact
        estimated_conversion_improvement = total_deals_reallocated * 0.05  # 5% improvement per deal
        estimated_velocity_improvement = total_deals_reallocated * 0.1  # 10% velocity improvement
        
        return {
            'deals_reallocated': total_deals_reallocated,
            'leads_reallocated': total_leads_reallocated,
            'total_value_reallocated': total_value_reallocated,
            'estimated_conversion_improvement_percent': round(estimated_conversion_improvement, 2),
            'estimated_velocity_improvement_percent': round(estimated_velocity_improvement, 2),
            'expected_revenue_impact': round(total_value_reallocated * estimated_conversion_improvement, 2)
        }


class ProcessEfficiencyAutomator:
    """Automates process efficiency improvements and tracks performance."""
    
    def __init__(self):
        self.efficiency_rules = {
            'max_days_without_activity': 7,
            'min_next_action_rate': 80.0,
            'max_stage_duration': {
                DealStage.PROSPECTING: 14,
                DealStage.QUALIFICATION: 21,
                DealStage.NEEDS_ANALYSIS: 14,
                DealStage.PROPOSAL: 10,
                DealStage.NEGOTIATION: 7
            }
        }
    
    def identify_process_improvements(
        self,
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity],
        reps: List[SalesRep]
    ) -> Dict[str, Any]:
        """
        Identify and recommend process efficiency improvements.
        
        Args:
            deals: List of deals
            leads: List of leads  
            activities: List of activities
            reps: List of sales reps
            
        Returns:
            Dict containing process improvement recommendations
        """
        logger.info("Identifying process efficiency improvements")
        
        # Analyze process adherence
        process_adherence = self._analyze_process_adherence(deals, activities)
        
        # Identify automation opportunities
        automation_opportunities = self._identify_automation_opportunities(deals, leads, activities)
        
        # Generate efficiency improvements
        efficiency_improvements = self._generate_efficiency_improvements(
            deals, leads, activities, process_adherence, automation_opportunities
        )
        
        # Calculate potential impact
        impact_analysis = self._calculate_efficiency_impact(efficiency_improvements, deals, activities)
        
        return {
            'process_adherence': process_adherence,
            'automation_opportunities': automation_opportunities,
            'efficiency_improvements': efficiency_improvements,
            'impact_analysis': impact_analysis,
            'analyzed_at': datetime.utcnow().isoformat()
        }
    
    def _analyze_process_adherence(
        self,
        deals: List[Deal],
        activities: List[SalesActivity]
    ) -> Dict[str, Any]:
        """Analyze adherence to sales processes."""
        # Next action scheduling adherence
        total_activities = len(activities)
        scheduled_next_actions = sum(1 for a in activities if a.next_action_scheduled)
        next_action_rate = (scheduled_next_actions / total_activities * 100) if total_activities > 0 else 0
        
        # Stage duration adherence
        stage_violations = {}
        for deal in deals:
            if deal.stage in self.efficiency_rules['max_stage_duration']:
                max_duration = self.efficiency_rules['max_stage_duration'][deal.stage]
                if deal.days_in_current_stage > max_duration:
                    stage_violations[deal.id] = {
                        'deal_id': deal.id,
                        'stage': deal.stage.value,
                        'days_in_stage': deal.days_in_current_stage,
                        'max_allowed': max_duration,
                        'violation_days': deal.days_in_current_stage - max_duration
                    }
        
        # Activity frequency adherence
        activity_violations = []
        for deal in deals:
            if deal.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                deal_activities = [a for a in activities if a.deal_id == deal.id]
                if deal_activities:
                    last_activity = max(deal_activities, key=lambda x: x.completed_at)
                    days_since_activity = (datetime.utcnow() - last_activity.completed_at).days
                    if days_since_activity > self.efficiency_rules['max_days_without_activity']:
                        activity_violations.append({
                            'deal_id': deal.id,
                            'days_since_activity': days_since_activity,
                            'max_allowed': self.efficiency_rules['max_days_without_activity']
                        })
        
        return {
            'next_action_scheduling_rate': round(next_action_rate, 2),
            'next_action_adherence': next_action_rate >= self.efficiency_rules['min_next_action_rate'],
            'stage_duration_violations': list(stage_violations.values()),
            'activity_frequency_violations': activity_violations,
            'overall_adherence_score': self._calculate_adherence_score(
                next_action_rate, len(stage_violations), len(activity_violations), len(deals)
            )
        }
    
    def _identify_automation_opportunities(
        self,
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity]
    ) -> List[Dict[str, Any]]:
        """Identify opportunities for process automation."""
        opportunities = []
        
        # Automated follow-up scheduling
        deals_without_next_action = [
            d for d in deals 
            if d.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST] 
            and d.next_action_due is None
        ]
        
        if deals_without_next_action:
            opportunities.append({
                'type': 'automated_followup_scheduling',
                'priority': 'high',
                'title': 'Automated Follow-up Scheduling',
                'description': f"{len(deals_without_next_action)} deals missing scheduled next actions",
                'potential_impact': 'improved_deal_progression',
                'implementation_effort': 'medium',
                'affected_entities': len(deals_without_next_action)
            })
        
        # Lead response automation
        uncontacted_leads = [
            l for l in leads 
            if l.status == LeadStatus.NEW 
            and l.last_contact is None
        ]
        
        if uncontacted_leads:
            opportunities.append({
                'type': 'automated_lead_response',
                'priority': 'high',
                'title': 'Automated Lead Response',
                'description': f"{len(uncontacted_leads)} new leads without initial contact",
                'potential_impact': 'faster_lead_response',
                'implementation_effort': 'low',
                'affected_entities': len(uncontacted_leads)
            })
        
        # Deal stage progression automation
        stalled_deals = [
            d for d in deals 
            if d.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]
            and d.days_in_current_stage > 30
        ]
        
        if stalled_deals:
            opportunities.append({
                'type': 'stalled_deal_intervention',
                'priority': 'medium',
                'title': 'Stalled Deal Intervention',
                'description': f"{len(stalled_deals)} deals stalled for >30 days",
                'potential_impact': 'improved_deal_velocity',
                'implementation_effort': 'medium',
                'affected_entities': len(stalled_deals)
            })
        
        # Activity logging automation
        activities_without_outcomes = [
            a for a in activities 
            if a.outcome is None or a.outcome.strip() == ""
        ]
        
        if len(activities_without_outcomes) > len(activities) * 0.3:  # >30% missing outcomes
            opportunities.append({
                'type': 'activity_outcome_automation',
                'priority': 'low',
                'title': 'Activity Outcome Automation',
                'description': f"{len(activities_without_outcomes)} activities missing outcome documentation",
                'potential_impact': 'better_activity_tracking',
                'implementation_effort': 'high',
                'affected_entities': len(activities_without_outcomes)
            })
        
        return opportunities
    
    def _generate_efficiency_improvements(
        self,
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity],
        process_adherence: Dict[str, Any],
        automation_opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate specific efficiency improvement recommendations."""
        improvements = []
        
        # Process adherence improvements
        if not process_adherence['next_action_adherence']:
            improvements.append({
                'category': 'process_adherence',
                'priority': 'high',
                'title': 'Improve Next Action Scheduling',
                'description': f"Next action scheduling rate ({process_adherence['next_action_scheduling_rate']}%) below target",
                'action_items': [
                    'Implement mandatory next action field in CRM',
                    'Create automated reminders for missing next actions',
                    'Train reps on importance of next action scheduling'
                ],
                'expected_impact': 'improved_deal_progression',
                'implementation_timeline': '2-4 weeks'
            })
        
        # Stage duration improvements
        if process_adherence['stage_duration_violations']:
            improvements.append({
                'category': 'stage_management',
                'priority': 'medium',
                'title': 'Address Stage Duration Violations',
                'description': f"{len(process_adherence['stage_duration_violations'])} deals exceeding stage duration limits",
                'action_items': [
                    'Review and update stage duration thresholds',
                    'Implement automated stage progression alerts',
                    'Create deal review process for stalled opportunities'
                ],
                'expected_impact': 'faster_deal_velocity',
                'implementation_timeline': '3-6 weeks'
            })
        
        # Activity frequency improvements
        if process_adherence['activity_frequency_violations']:
            improvements.append({
                'category': 'activity_management',
                'priority': 'high',
                'title': 'Increase Activity Frequency',
                'description': f"{len(process_adherence['activity_frequency_violations'])} deals with insufficient activity",
                'action_items': [
                    'Implement daily activity targets',
                    'Create automated activity reminders',
                    'Review inactive deals weekly'
                ],
                'expected_impact': 'better_deal_engagement',
                'implementation_timeline': '1-2 weeks'
            })
        
        # Convert automation opportunities to improvements
        for opportunity in automation_opportunities:
            if opportunity['priority'] in ['high', 'medium']:
                improvements.append({
                    'category': 'automation',
                    'priority': opportunity['priority'],
                    'title': opportunity['title'],
                    'description': opportunity['description'],
                    'action_items': [
                        f"Implement {opportunity['type']} automation",
                        'Test automation with pilot group',
                        'Roll out to full sales team'
                    ],
                    'expected_impact': opportunity['potential_impact'],
                    'implementation_timeline': self._estimate_implementation_timeline(opportunity['implementation_effort'])
                })
        
        return improvements
    
    def _calculate_adherence_score(
        self,
        next_action_rate: float,
        stage_violations: int,
        activity_violations: int,
        total_deals: int
    ) -> float:
        """Calculate overall process adherence score."""
        # Next action component (40%)
        next_action_score = min(next_action_rate / self.efficiency_rules['min_next_action_rate'], 1.0) * 40
        
        # Stage duration component (30%)
        stage_violation_rate = (stage_violations / max(total_deals, 1)) * 100
        stage_score = max(0, 30 - stage_violation_rate)
        
        # Activity frequency component (30%)
        activity_violation_rate = (activity_violations / max(total_deals, 1)) * 100
        activity_score = max(0, 30 - activity_violation_rate)
        
        return round(next_action_score + stage_score + activity_score, 2)
    
    def _calculate_efficiency_impact(
        self,
        improvements: List[Dict[str, Any]],
        deals: List[Deal],
        activities: List[SalesActivity]
    ) -> Dict[str, Any]:
        """Calculate potential impact of efficiency improvements."""
        # Estimate impact based on improvement categories
        velocity_improvements = [i for i in improvements if 'velocity' in i.get('expected_impact', '')]
        conversion_improvements = [i for i in improvements if 'conversion' in i.get('expected_impact', '')]
        activity_improvements = [i for i in improvements if 'activity' in i.get('expected_impact', '')]
        
        # Calculate potential improvements
        estimated_velocity_improvement = len(velocity_improvements) * 15  # 15% per improvement
        estimated_conversion_improvement = len(conversion_improvements) * 10  # 10% per improvement
        estimated_activity_improvement = len(activity_improvements) * 20  # 20% per improvement
        
        # Calculate potential revenue impact
        active_pipeline_value = sum(
            deal.value for deal in deals 
            if deal.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]
        )
        
        potential_revenue_impact = float(active_pipeline_value) * (estimated_conversion_improvement / 100)
        
        return {
            'total_improvements_identified': len(improvements),
            'high_priority_improvements': len([i for i in improvements if i['priority'] == 'high']),
            'estimated_velocity_improvement_percent': min(estimated_velocity_improvement, 50),
            'estimated_conversion_improvement_percent': min(estimated_conversion_improvement, 30),
            'estimated_activity_improvement_percent': min(estimated_activity_improvement, 40),
            'potential_revenue_impact': round(potential_revenue_impact, 2),
            'implementation_timeline_weeks': max([
                self._parse_timeline(i.get('implementation_timeline', '4 weeks'))
                for i in improvements
            ], default=4)
        }
    
    def _estimate_implementation_timeline(self, effort: str) -> str:
        """Estimate implementation timeline based on effort level."""
        effort_timelines = {
            'low': '1-2 weeks',
            'medium': '3-4 weeks',
            'high': '6-8 weeks'
        }
        return effort_timelines.get(effort, '4 weeks')
    
    def _parse_timeline(self, timeline: str) -> int:
        """Parse timeline string to weeks."""
        if 'week' in timeline:
            # Extract first number from timeline
            import re
            numbers = re.findall(r'\d+', timeline)
            return int(numbers[-1]) if numbers else 4  # Use last number or default to 4
        return 4


class SalesProcessEfficiencyOptimizer:
    """
    Main class that orchestrates sales process efficiency optimization.
    
    Implements Requirements 8.3, 8.5, 8.7:
    - Rep performance analysis and coaching recommendations (8.3)
    - Sales resource allocation optimization algorithms (8.5) 
    - Process efficiency improvement automation (8.7)
    """
    
    def __init__(self):
        self.performance_analyzer = RepPerformanceAnalyzer()
        self.resource_optimizer = ResourceAllocationOptimizer()
        self.process_automator = ProcessEfficiencyAutomator()
        
        self.config = {
            'analysis_enabled': True,
            'coaching_enabled': True,
            'resource_optimization_enabled': True,
            'process_automation_enabled': True,
            'performance_tracking_enabled': True
        }
    
    def optimize_sales_process_efficiency(
        self,
        reps: List[SalesRep],
        deals: List[Deal],
        leads: List[Lead],
        activities: List[SalesActivity],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive sales process efficiency optimization.
        
        Args:
            reps: List of sales representatives
            deals: List of deals
            leads: List of leads
            activities: List of activities
            context: Optional context for optimization
            
        Returns:
            Dict containing comprehensive optimization results
        """
        logger.info("Starting sales process efficiency optimization")
        
        optimization_results = {
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat(),
            'rep_performance_analysis': {},
            'resource_allocation_optimization': {},
            'process_efficiency_improvements': {},
            'coaching_recommendations': [],
            'performance_tracking': {},
            'summary': {}
        }
        
        try:
            # Rep performance analysis and coaching
            if self.config['analysis_enabled'] and self.config['coaching_enabled']:
                logger.info("Analyzing rep performance and generating coaching recommendations")
                rep_analyses = []
                all_coaching_recommendations = []
                
                for rep in reps:
                    analysis = self.performance_analyzer.analyze_rep_performance(
                        rep, deals, activities
                    )
                    rep_analyses.append(analysis)
                    all_coaching_recommendations.extend(analysis['coaching_recommendations'])
                
                optimization_results['rep_performance_analysis'] = {
                    'individual_analyses': rep_analyses,
                    'team_summary': self._generate_team_performance_summary(rep_analyses)
                }
                optimization_results['coaching_recommendations'] = all_coaching_recommendations
            
            # Resource allocation optimization
            if self.config['resource_optimization_enabled']:
                logger.info("Optimizing resource allocation")
                resource_optimization = self.resource_optimizer.optimize_resource_allocation(
                    reps, deals, leads, activities
                )
                optimization_results['resource_allocation_optimization'] = resource_optimization
            
            # Process efficiency improvements
            if self.config['process_automation_enabled']:
                logger.info("Identifying process efficiency improvements")
                process_improvements = self.process_automator.identify_process_improvements(
                    deals, leads, activities, reps
                )
                optimization_results['process_efficiency_improvements'] = process_improvements
            
            # Performance tracking
            if self.config['performance_tracking_enabled']:
                logger.info("Generating performance tracking metrics")
                performance_tracking = self._generate_performance_tracking(
                    reps, deals, activities, optimization_results
                )
                optimization_results['performance_tracking'] = performance_tracking
            
            # Generate summary
            optimization_results['summary'] = self._generate_optimization_summary(optimization_results)
            
            logger.info("Sales process efficiency optimization completed successfully")
            
        except Exception as e:
            logger.error(f"Sales process efficiency optimization failed: {str(e)}", exc_info=e)
            optimization_results['status'] = 'failed'
            optimization_results['error'] = str(e)
        
        return optimization_results
    
    def _generate_team_performance_summary(self, rep_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate team-level performance summary."""
        if not rep_analyses:
            return {}
        
        # Calculate team averages
        performance_scores = [analysis['performance_score'] for analysis in rep_analyses]
        avg_performance_score = sum(performance_scores) / len(performance_scores)
        
        # Count improvement areas
        all_improvement_areas = []
        for analysis in rep_analyses:
            all_improvement_areas.extend(analysis['improvement_areas'])
        
        improvement_area_counts = {}
        for area in all_improvement_areas:
            improvement_area_counts[area] = improvement_area_counts.get(area, 0) + 1
        
        # Identify top improvement areas
        top_improvement_areas = sorted(
            improvement_area_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            'team_size': len(rep_analyses),
            'average_performance_score': round(avg_performance_score, 2),
            'performance_distribution': {
                'high_performers': len([s for s in performance_scores if s >= 80]),
                'average_performers': len([s for s in performance_scores if 60 <= s < 80]),
                'low_performers': len([s for s in performance_scores if s < 60])
            },
            'top_improvement_areas': [{'area': area, 'affected_reps': count} for area, count in top_improvement_areas],
            'total_coaching_recommendations': sum(len(analysis['coaching_recommendations']) for analysis in rep_analyses)
        }
    
    def _generate_performance_tracking(
        self,
        reps: List[SalesRep],
        deals: List[Deal],
        activities: List[SalesActivity],
        optimization_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate performance tracking metrics."""
        # Current performance baseline
        total_pipeline_value = sum(
            deal.value for deal in deals 
            if deal.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]
        )
        
        avg_deal_velocity = sum(deal.days_in_current_stage for deal in deals) / len(deals) if deals else 0
        total_activities_last_30_days = len([
            a for a in activities 
            if a.completed_at >= datetime.utcnow() - timedelta(days=30)
        ])
        
        # Calculate potential improvements from optimization
        resource_impact = optimization_results.get('resource_allocation_optimization', {}).get('expected_impact', {})
        process_impact = optimization_results.get('process_efficiency_improvements', {}).get('impact_analysis', {})
        
        return {
            'baseline_metrics': {
                'total_pipeline_value': float(total_pipeline_value),
                'average_deal_velocity_days': round(avg_deal_velocity, 2),
                'activities_last_30_days': total_activities_last_30_days,
                'active_reps': len([rep for rep in reps if rep.active]),
                'average_quota_attainment': sum(rep.quota_attainment for rep in reps) / len(reps) if reps else 0
            },
            'projected_improvements': {
                'pipeline_value_impact': resource_impact.get('expected_revenue_impact', 0),
                'velocity_improvement_percent': process_impact.get('estimated_velocity_improvement_percent', 0),
                'conversion_improvement_percent': process_impact.get('estimated_conversion_improvement_percent', 0),
                'activity_improvement_percent': process_impact.get('estimated_activity_improvement_percent', 0)
            },
            'tracking_recommendations': [
                'Monitor deal velocity changes weekly',
                'Track coaching recommendation implementation',
                'Measure resource reallocation impact monthly',
                'Review process adherence scores regularly'
            ]
        }
    
    def _generate_optimization_summary(self, optimization_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level optimization summary."""
        summary = {
            'optimization_status': optimization_results['status'],
            'total_reps_analyzed': 0,
            'total_coaching_recommendations': 0,
            'total_resource_reallocations': 0,
            'total_process_improvements': 0,
            'key_findings': [],
            'next_steps': []
        }
        
        # Count analyzed reps
        rep_analysis = optimization_results.get('rep_performance_analysis', {})
        if 'individual_analyses' in rep_analysis:
            summary['total_reps_analyzed'] = len(rep_analysis['individual_analyses'])
        
        # Count coaching recommendations
        summary['total_coaching_recommendations'] = len(optimization_results.get('coaching_recommendations', []))
        
        # Count resource reallocations
        resource_opt = optimization_results.get('resource_allocation_optimization', {})
        if 'reallocation_recommendations' in resource_opt:
            summary['total_resource_reallocations'] = len(resource_opt['reallocation_recommendations'])
        
        # Count process improvements
        process_imp = optimization_results.get('process_efficiency_improvements', {})
        if 'efficiency_improvements' in process_imp:
            summary['total_process_improvements'] = len(process_imp['efficiency_improvements'])
        
        # Generate key findings
        if rep_analysis.get('team_summary', {}).get('top_improvement_areas'):
            top_area = rep_analysis['team_summary']['top_improvement_areas'][0]
            summary['key_findings'].append(f"Top improvement area: {top_area['area']} affects {top_area['affected_reps']} reps")
        
        if resource_opt.get('workload_analysis', {}).get('distribution_balance') == 'imbalanced':
            summary['key_findings'].append("Workload distribution is imbalanced across team")
        
        if process_imp.get('process_adherence', {}).get('overall_adherence_score', 0) < 70:
            summary['key_findings'].append("Process adherence below target threshold")
        
        # Generate next steps
        if summary['total_coaching_recommendations'] > 0:
            summary['next_steps'].append("Implement coaching recommendations with sales managers")
        
        if summary['total_resource_reallocations'] > 0:
            summary['next_steps'].append("Execute resource reallocation plan")
        
        if summary['total_process_improvements'] > 0:
            summary['next_steps'].append("Prioritize and implement process improvements")
        
        return summary