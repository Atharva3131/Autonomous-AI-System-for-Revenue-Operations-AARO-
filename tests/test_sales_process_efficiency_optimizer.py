"""
Unit tests for Sales Process Efficiency Optimizer.

Tests the SalesProcessEfficiencyOptimizer class and its components for
rep performance analysis, resource allocation optimization, and process
efficiency improvements.

Implements Requirements 8.3, 8.5, 8.7.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aboa.decision.sales_process_efficiency_optimizer import (
    SalesProcessEfficiencyOptimizer,
    RepPerformanceAnalyzer,
    ResourceAllocationOptimizer,
    ProcessEfficiencyAutomator
)
from aboa.models.enums import (
    ActivityType, DealStage, LeadStatus
)
from aboa.models.revenue_entities import (
    ContactInfo, Deal, Lead, SalesActivity, SalesRep
)


class TestRepPerformanceAnalyzer:
    """Test suite for RepPerformanceAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = RepPerformanceAnalyzer()
        self.now = datetime.utcnow()
        
        # Create test contact info
        self.contact_info = ContactInfo(
            email="test@example.com",
            phone="555-123-4567",
            company="Test Company",
            title="CEO",
            first_name="John",
            last_name="Doe"
        )
        
        # Create test sales rep
        self.sales_rep = SalesRep(
            id="rep_1",
            name="Jane Smith",
            email="jane@company.com",
            quota=Decimal('100000'),
            quota_attainment=75.0,
            pipeline_value=Decimal('250000'),
            activities_this_week=15,
            avg_deal_velocity=45.0,
            conversion_rates={'prospecting_to_qualification': 25.0}
        )
    
    def test_analyze_rep_performance_basic(self):
        """Test basic rep performance analysis."""
        # Create test deals
        deals = [
            Deal(
                id="deal_1",
                stage=DealStage.PROSPECTING,
                value=Decimal('25000'),
                probability=50.0,
                close_date=self.now + timedelta(days=30),
                assigned_rep="rep_1",
                days_in_current_stage=5,
                contact_info=self.contact_info
            ),
            Deal(
                id="deal_2",
                stage=DealStage.QUALIFICATION,
                value=Decimal('35000'),
                probability=70.0,
                close_date=self.now + timedelta(days=45),
                assigned_rep="rep_1",
                days_in_current_stage=10,
                contact_info=self.contact_info
            )
        ]
        
        # Create test activities
        activities = [
            SalesActivity(
                id="activity_1",
                deal_id="deal_1",
                activity_type=ActivityType.CALL,
                completed_at=self.now - timedelta(days=1),
                rep_id="rep_1",
                next_action_scheduled=True
            ),
            SalesActivity(
                id="activity_2",
                deal_id="deal_2",
                activity_type=ActivityType.MEETING,
                completed_at=self.now - timedelta(days=2),
                rep_id="rep_1",
                next_action_scheduled=False
            )
        ]
        
        analysis = self.analyzer.analyze_rep_performance(
            self.sales_rep, deals, activities, time_period_days=30
        )
        
        # Verify analysis structure
        assert analysis['rep_id'] == "rep_1"
        assert analysis['analysis_period_days'] == 30
        assert 'performance_score' in analysis
        assert 'activity_metrics' in analysis
        assert 'deal_metrics' in analysis
        assert 'conversion_metrics' in analysis
        assert 'velocity_metrics' in analysis
        assert 'coaching_recommendations' in analysis
        assert 'improvement_areas' in analysis
        
        # Verify performance score is calculated
        assert 0 <= analysis['performance_score'] <= 100
    
    def test_activity_metrics_calculation(self):
        """Test activity metrics calculation."""
        activities = []
        # Create 25 activities over 30 days (should be ~6 per week)
        for i in range(25):
            activities.append(
                SalesActivity(
                    id=f"activity_{i}",
                    deal_id="deal_1",
                    activity_type=ActivityType.CALL if i % 2 == 0 else ActivityType.EMAIL,
                    completed_at=self.now - timedelta(days=i),
                    rep_id="rep_1",
                    next_action_scheduled=i % 3 == 0  # 33% have next actions
                )
            )
        
        metrics = self.analyzer._calculate_activity_metrics(activities, 30)
        
        assert metrics['total_activities'] == 25
        assert abs(metrics['activities_per_week'] - 5.83) < 0.1  # 25/30*7 ≈ 5.83
        assert metrics['next_action_scheduling_rate'] == pytest.approx(36.0, abs=1)  # 9/25 activities have next actions
        assert not metrics['meets_activity_threshold']  # Below 20/week threshold
    
    def test_deal_metrics_calculation(self):
        """Test deal metrics calculation."""
        deals = [
            Deal(
                id="deal_1",
                stage=DealStage.PROSPECTING,
                value=Decimal('25000'),
                probability=50.0,
                close_date=self.now + timedelta(days=30),
                assigned_rep="rep_1",
                contact_info=self.contact_info
            ),
            Deal(
                id="deal_2",
                stage=DealStage.CLOSED_WON,
                value=Decimal('35000'),
                probability=100.0,
                close_date=self.now - timedelta(days=5),
                assigned_rep="rep_1",
                contact_info=self.contact_info
            ),
            Deal(
                id="deal_3",
                stage=DealStage.CLOSED_LOST,
                value=Decimal('15000'),
                probability=0.0,
                close_date=self.now - timedelta(days=10),
                assigned_rep="rep_1",
                contact_info=self.contact_info
            )
        ]
        
        metrics = self.analyzer._calculate_deal_metrics(deals, self.sales_rep)
        
        assert metrics['total_deals'] == 3
        assert metrics['total_pipeline_value'] == 25000.0  # Only active deals
        assert metrics['pipeline_coverage_ratio'] == 0.25  # 25k/100k quota
        assert metrics['won_deals_count'] == 1
        assert metrics['lost_deals_count'] == 1
        assert metrics['won_deals_value'] == 35000.0
        assert not metrics['meets_pipeline_coverage']  # Below 3.0x threshold
    
    def test_coaching_recommendations_generation(self):
        """Test coaching recommendations generation."""
        # Create scenario with low activity and poor next action scheduling
        activity_metrics = {
            'activities_per_week': 10,  # Below 20 threshold
            'meets_activity_threshold': False,
            'next_action_scheduling_rate': 60.0  # Below 80% threshold
        }
        
        deal_metrics = {
            'pipeline_coverage_ratio': 2.0,  # Below 3.0 threshold
            'meets_pipeline_coverage': False
        }
        
        conversion_metrics = {
            'overall_conversion_rate': 10.0,  # Below 15% threshold
            'meets_conversion_threshold': False
        }
        
        velocity_metrics = {
            'avg_days_in_current_stage': 100,  # Above 90 day threshold
            'meets_velocity_threshold': False,
            'stalled_deals_percentage': 25.0  # Above 20% threshold
        }
        
        recommendations = self.analyzer._generate_coaching_recommendations(
            activity_metrics, deal_metrics, conversion_metrics, velocity_metrics, self.sales_rep
        )
        
        # Should generate multiple recommendations
        assert len(recommendations) >= 4
        
        # Check for specific recommendation categories
        categories = [rec['category'] for rec in recommendations]
        assert 'activity_management' in categories
        assert 'process_adherence' in categories
        assert 'pipeline_management' in categories
        assert 'conversion_optimization' in categories
        assert 'velocity_improvement' in categories
        assert 'deal_management' in categories


class TestResourceAllocationOptimizer:
    """Test suite for ResourceAllocationOptimizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = ResourceAllocationOptimizer()
        self.now = datetime.utcnow()
        
        # Create test reps with different workloads
        self.rep_overloaded = SalesRep(
            id="rep_1",
            name="Overloaded Rep",
            email="overloaded@company.com",
            quota=Decimal('100000'),
            quota_attainment=60.0,
            pipeline_value=Decimal('400000')
        )
        
        self.rep_underloaded = SalesRep(
            id="rep_2",
            name="Underloaded Rep",
            email="underloaded@company.com",
            quota=Decimal('100000'),
            quota_attainment=90.0,
            pipeline_value=Decimal('150000')
        )
    
    def test_workload_distribution_analysis(self):
        """Test workload distribution analysis."""
        reps = [self.rep_overloaded, self.rep_underloaded]
        
        # Create deals with uneven distribution
        deals = []
        # 15 deals for overloaded rep
        for i in range(15):
            deals.append(
                Deal(
                    id=f"deal_{i}",
                    stage=DealStage.PROSPECTING,
                    value=Decimal('20000'),
                    probability=50.0,
                    close_date=self.now + timedelta(days=30),
                    assigned_rep="rep_1"
                )
            )
        
        # 3 deals for underloaded rep
        for i in range(3):
            deals.append(
                Deal(
                    id=f"deal_{i+15}",
                    stage=DealStage.QUALIFICATION,
                    value=Decimal('25000'),
                    probability=60.0,
                    close_date=self.now + timedelta(days=30),
                    assigned_rep="rep_2"
                )
            )
        
        leads = []
        activities = []
        
        analysis = self.optimizer._analyze_workload_distribution(reps, deals, leads, activities)
        
        assert 'rep_workloads' in analysis
        assert len(analysis['rep_workloads']) == 2
        assert analysis['distribution_balance'] == 'imbalanced'
        
        # Overloaded rep should have higher workload score
        rep1_workload = analysis['rep_workloads']['rep_1']['workload_score']
        rep2_workload = analysis['rep_workloads']['rep_2']['workload_score']
        assert rep1_workload > rep2_workload
    
    def test_capacity_constraints_analysis(self):
        """Test capacity constraints analysis."""
        reps = [self.rep_overloaded, self.rep_underloaded]
        deals = []
        
        # Create high activity for overloaded rep
        activities = []
        for i in range(300):  # 10 activities per day for 30 days
            activities.append(
                SalesActivity(
                    id=f"activity_{i}",
                    deal_id="deal_1",
                    activity_type=ActivityType.CALL,
                    completed_at=self.now - timedelta(days=i % 30),
                    rep_id="rep_1"
                )
            )
        
        # Low activity for underloaded rep
        for i in range(30):  # 1 activity per day for 30 days
            activities.append(
                SalesActivity(
                    id=f"activity_{i+300}",
                    deal_id="deal_2",
                    activity_type=ActivityType.EMAIL,
                    completed_at=self.now - timedelta(days=i % 30),
                    rep_id="rep_2"
                )
            )
        
        analysis = self.optimizer._analyze_capacity_constraints(reps, deals, activities)
        
        assert len(analysis) == 2
        
        # Rep 1 should be overutilized
        rep1_analysis = analysis['rep_1']
        assert rep1_analysis['utilization_rate'] > 90
        assert 'overutilized' in rep1_analysis['constraints']
        
        # Rep 2 should be underutilized
        rep2_analysis = analysis['rep_2']
        assert rep2_analysis['utilization_rate'] < 50
        assert 'underutilized' in rep2_analysis['constraints']
    
    def test_reallocation_recommendations(self):
        """Test reallocation recommendations generation."""
        reps = [self.rep_overloaded, self.rep_underloaded]
        
        # Create deals for overloaded rep
        deals = []
        for i in range(10):
            deals.append(
                Deal(
                    id=f"deal_{i}",
                    stage=DealStage.PROSPECTING,
                    value=Decimal('15000'),
                    probability=40.0,  # Lower probability for reallocation
                    close_date=self.now + timedelta(days=30),
                    assigned_rep="rep_1"
                )
            )
        
        leads = []
        
        # Mock workload and capacity analysis
        workload_analysis = {
            'rep_workloads': {
                'rep_1': {'workload_score': 90},
                'rep_2': {'workload_score': 30}
            }
        }
        
        capacity_analysis = {
            'rep_1': {'constraints': ['overutilized']},
            'rep_2': {'constraints': ['underutilized']}
        }
        
        recommendations = self.optimizer._generate_reallocation_recommendations(
            reps, deals, leads, workload_analysis, capacity_analysis
        )
        
        # Should generate reallocation recommendations
        assert len(recommendations) > 0
        
        # Check for deal reallocations
        deal_reallocations = [r for r in recommendations if r['type'] == 'deal_reallocation']
        assert len(deal_reallocations) > 0
        
        # Verify reallocation is from overloaded to underloaded rep
        for rec in deal_reallocations:
            assert rec['from_rep_id'] == 'rep_1'
            assert rec['to_rep_id'] == 'rep_2'


class TestProcessEfficiencyAutomator:
    """Test suite for ProcessEfficiencyAutomator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.automator = ProcessEfficiencyAutomator()
        self.now = datetime.utcnow()
    
    def test_process_adherence_analysis(self):
        """Test process adherence analysis."""
        # Create deals with various stage durations
        deals = [
            Deal(
                id="deal_1",
                stage=DealStage.PROSPECTING,
                value=Decimal('25000'),
                probability=50.0,
                close_date=self.now + timedelta(days=30),
                assigned_rep="rep_1",
                days_in_current_stage=20  # Exceeds 14-day threshold
            ),
            Deal(
                id="deal_2",
                stage=DealStage.QUALIFICATION,
                value=Decimal('35000'),
                probability=70.0,
                close_date=self.now + timedelta(days=45),
                assigned_rep="rep_1",
                days_in_current_stage=10  # Within 21-day threshold
            )
        ]
        
        # Create activities with mixed next action scheduling
        activities = [
            SalesActivity(
                id="activity_1",
                deal_id="deal_1",
                activity_type=ActivityType.CALL,
                completed_at=self.now - timedelta(days=1),
                rep_id="rep_1",
                next_action_scheduled=True
            ),
            SalesActivity(
                id="activity_2",
                deal_id="deal_2",
                activity_type=ActivityType.MEETING,
                completed_at=self.now - timedelta(days=2),
                rep_id="rep_1",
                next_action_scheduled=False
            ),
            SalesActivity(
                id="activity_3",
                deal_id="deal_1",
                activity_type=ActivityType.EMAIL,
                completed_at=self.now - timedelta(days=10),  # Old activity
                rep_id="rep_1",
                next_action_scheduled=True
            )
        ]
        
        adherence = self.automator._analyze_process_adherence(deals, activities)
        
        assert 'next_action_scheduling_rate' in adherence
        assert adherence['next_action_scheduling_rate'] == pytest.approx(66.67, abs=1)  # 2/3 activities
        assert not adherence['next_action_adherence']  # Below 80% threshold
        
        assert 'stage_duration_violations' in adherence
        assert len(adherence['stage_duration_violations']) == 1  # One deal exceeds threshold
        
        assert 'activity_frequency_violations' in adherence
        assert len(adherence['activity_frequency_violations']) == 0  # Both deals have recent activity
        
        assert 'overall_adherence_score' in adherence
        assert 0 <= adherence['overall_adherence_score'] <= 100
    
    def test_automation_opportunities_identification(self):
        """Test automation opportunities identification."""
        # Create deals without next actions
        deals = [
            Deal(
                id="deal_1",
                stage=DealStage.PROSPECTING,
                value=Decimal('25000'),
                probability=50.0,
                close_date=self.now + timedelta(days=30),
                assigned_rep="rep_1",
                next_action_due=None  # Missing next action
            ),
            Deal(
                id="deal_2",
                stage=DealStage.QUALIFICATION,
                value=Decimal('35000'),
                probability=70.0,
                close_date=self.now + timedelta(days=45),
                assigned_rep="rep_1",
                days_in_current_stage=35  # Stalled
            )
        ]
        
        # Create uncontacted leads
        leads = [
            Lead(
                id="lead_1",
                source="website",
                contact_info=ContactInfo(email="test1@example.com"),
                status=LeadStatus.NEW,
                last_contact=None,  # Uncontacted
                assigned_rep="rep_1"
            )
        ]
        
        # Create activities without outcomes
        activities = [
            SalesActivity(
                id="activity_1",
                deal_id="deal_1",
                activity_type=ActivityType.CALL,
                completed_at=self.now - timedelta(days=1),
                rep_id="rep_1",
                outcome=None  # Missing outcome
            ),
            SalesActivity(
                id="activity_2",
                deal_id="deal_2",
                activity_type=ActivityType.MEETING,
                completed_at=self.now - timedelta(days=2),
                rep_id="rep_1",
                outcome=""  # Empty outcome
            )
        ]
        
        opportunities = self.automator._identify_automation_opportunities(deals, leads, activities)
        
        # Should identify multiple automation opportunities
        assert len(opportunities) >= 3
        
        opportunity_types = [opp['type'] for opp in opportunities]
        assert 'automated_followup_scheduling' in opportunity_types
        assert 'automated_lead_response' in opportunity_types
        assert 'stalled_deal_intervention' in opportunity_types
    
    def test_efficiency_improvements_generation(self):
        """Test efficiency improvements generation."""
        # Mock poor process adherence
        process_adherence = {
            'next_action_scheduling_rate': 60.0,
            'next_action_adherence': False,
            'stage_duration_violations': [{'deal_id': 'deal_1'}],
            'activity_frequency_violations': [{'deal_id': 'deal_2'}],
            'overall_adherence_score': 55.0
        }
        
        # Mock automation opportunities
        automation_opportunities = [
            {
                'type': 'automated_followup_scheduling',
                'priority': 'high',
                'title': 'Automated Follow-up Scheduling',
                'description': 'Missing follow-ups',
                'potential_impact': 'improved_deal_progression',
                'implementation_effort': 'medium'
            }
        ]
        
        improvements = self.automator._generate_efficiency_improvements(
            [], [], [], process_adherence, automation_opportunities
        )
        
        # Should generate multiple improvements
        assert len(improvements) >= 4
        
        improvement_categories = [imp['category'] for imp in improvements]
        assert 'process_adherence' in improvement_categories
        assert 'stage_management' in improvement_categories
        assert 'activity_management' in improvement_categories
        assert 'automation' in improvement_categories


class TestSalesProcessEfficiencyOptimizer:
    """Test suite for main SalesProcessEfficiencyOptimizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = SalesProcessEfficiencyOptimizer()
        self.now = datetime.utcnow()
        
        # Create test data
        self.reps = [
            SalesRep(
                id="rep_1",
                name="Test Rep 1",
                email="rep1@company.com",
                quota=Decimal('100000'),
                quota_attainment=75.0,
                pipeline_value=Decimal('250000')
            ),
            SalesRep(
                id="rep_2",
                name="Test Rep 2",
                email="rep2@company.com",
                quota=Decimal('120000'),
                quota_attainment=85.0,
                pipeline_value=Decimal('180000')
            )
        ]
        
        self.deals = [
            Deal(
                id="deal_1",
                stage=DealStage.PROSPECTING,
                value=Decimal('25000'),
                probability=50.0,
                close_date=self.now + timedelta(days=30),
                assigned_rep="rep_1",
                days_in_current_stage=5
            ),
            Deal(
                id="deal_2",
                stage=DealStage.QUALIFICATION,
                value=Decimal('35000'),
                probability=70.0,
                close_date=self.now + timedelta(days=45),
                assigned_rep="rep_2",
                days_in_current_stage=10
            )
        ]
        
        self.leads = [
            Lead(
                id="lead_1",
                source="website",
                contact_info=ContactInfo(email="test1@example.com"),
                status=LeadStatus.NEW,
                assigned_rep="rep_1"
            )
        ]
        
        self.activities = [
            SalesActivity(
                id="activity_1",
                deal_id="deal_1",
                activity_type=ActivityType.CALL,
                completed_at=self.now - timedelta(days=1),
                rep_id="rep_1",
                next_action_scheduled=True
            ),
            SalesActivity(
                id="activity_2",
                deal_id="deal_2",
                activity_type=ActivityType.MEETING,
                completed_at=self.now - timedelta(days=2),
                rep_id="rep_2",
                next_action_scheduled=False
            )
        ]
    
    def test_optimize_sales_process_efficiency_complete(self):
        """Test complete sales process efficiency optimization."""
        results = self.optimizer.optimize_sales_process_efficiency(
            reps=self.reps,
            deals=self.deals,
            leads=self.leads,
            activities=self.activities
        )
        
        # Verify result structure
        assert results['status'] == 'completed'
        assert 'timestamp' in results
        assert 'rep_performance_analysis' in results
        assert 'resource_allocation_optimization' in results
        assert 'process_efficiency_improvements' in results
        assert 'coaching_recommendations' in results
        assert 'performance_tracking' in results
        assert 'summary' in results
        
        # Verify rep performance analysis
        rep_analysis = results['rep_performance_analysis']
        assert 'individual_analyses' in rep_analysis
        assert 'team_summary' in rep_analysis
        assert len(rep_analysis['individual_analyses']) == 2
        
        # Verify team summary
        team_summary = rep_analysis['team_summary']
        assert team_summary['team_size'] == 2
        assert 'average_performance_score' in team_summary
        assert 'performance_distribution' in team_summary
        assert 'top_improvement_areas' in team_summary
        
        # Verify coaching recommendations
        coaching_recs = results['coaching_recommendations']
        assert isinstance(coaching_recs, list)
        
        # Verify resource allocation optimization
        resource_opt = results['resource_allocation_optimization']
        assert 'workload_analysis' in resource_opt
        assert 'capacity_analysis' in resource_opt
        assert 'reallocation_recommendations' in resource_opt
        assert 'expected_impact' in resource_opt
        
        # Verify process efficiency improvements
        process_imp = results['process_efficiency_improvements']
        assert 'process_adherence' in process_imp
        assert 'automation_opportunities' in process_imp
        assert 'efficiency_improvements' in process_imp
        assert 'impact_analysis' in process_imp
        
        # Verify performance tracking
        perf_tracking = results['performance_tracking']
        assert 'baseline_metrics' in perf_tracking
        assert 'projected_improvements' in perf_tracking
        assert 'tracking_recommendations' in perf_tracking
        
        # Verify summary
        summary = results['summary']
        assert summary['optimization_status'] == 'completed'
        assert 'total_reps_analyzed' in summary
        assert 'total_coaching_recommendations' in summary
        assert 'key_findings' in summary
        assert 'next_steps' in summary
    
    def test_optimize_with_selective_features(self):
        """Test optimization with selective feature enablement."""
        # Disable some features
        self.optimizer.config.update({
            'coaching_enabled': False,
            'resource_optimization_enabled': False,
            'process_automation_enabled': True
        })
        
        results = self.optimizer.optimize_sales_process_efficiency(
            reps=self.reps,
            deals=self.deals,
            leads=self.leads,
            activities=self.activities
        )
        
        # Should still complete but with limited analysis
        assert results['status'] == 'completed'
        
        # Coaching should be empty when disabled
        assert len(results['coaching_recommendations']) == 0
        
        # Resource optimization should be empty when disabled
        resource_opt = results['resource_allocation_optimization']
        assert len(resource_opt) == 0
        
        # Process improvements should still be present
        process_imp = results['process_efficiency_improvements']
        assert len(process_imp) > 0
    
    def test_team_performance_summary_generation(self):
        """Test team performance summary generation."""
        # Create mock individual analyses
        rep_analyses = [
            {
                'rep_id': 'rep_1',
                'performance_score': 85.0,
                'improvement_areas': ['activity_volume', 'conversion_optimization'],
                'coaching_recommendations': [{'category': 'activity'}, {'category': 'conversion'}]
            },
            {
                'rep_id': 'rep_2',
                'performance_score': 65.0,
                'improvement_areas': ['pipeline_building', 'activity_volume'],
                'coaching_recommendations': [{'category': 'pipeline'}]
            }
        ]
        
        summary = self.optimizer._generate_team_performance_summary(rep_analyses)
        
        assert summary['team_size'] == 2
        assert summary['average_performance_score'] == 75.0  # (85 + 65) / 2
        
        # Performance distribution
        perf_dist = summary['performance_distribution']
        assert perf_dist['high_performers'] == 1  # rep_1 >= 80
        assert perf_dist['average_performers'] == 1  # rep_2 60-80
        assert perf_dist['low_performers'] == 0  # none < 60
        
        # Top improvement areas
        top_areas = summary['top_improvement_areas']
        assert len(top_areas) > 0
        assert top_areas[0]['area'] == 'activity_volume'  # Most common
        assert top_areas[0]['affected_reps'] == 2
        
        assert summary['total_coaching_recommendations'] == 3
    
    def test_performance_tracking_generation(self):
        """Test performance tracking metrics generation."""
        # Mock optimization results
        optimization_results = {
            'resource_allocation_optimization': {
                'expected_impact': {
                    'expected_revenue_impact': 50000.0
                }
            },
            'process_efficiency_improvements': {
                'impact_analysis': {
                    'estimated_velocity_improvement_percent': 15.0,
                    'estimated_conversion_improvement_percent': 10.0,
                    'estimated_activity_improvement_percent': 20.0
                }
            }
        }
        
        tracking = self.optimizer._generate_performance_tracking(
            self.reps, self.deals, self.activities, optimization_results
        )
        
        # Verify baseline metrics
        baseline = tracking['baseline_metrics']
        assert 'total_pipeline_value' in baseline
        assert 'average_deal_velocity_days' in baseline
        assert 'activities_last_30_days' in baseline
        assert 'active_reps' in baseline
        assert 'average_quota_attainment' in baseline
        
        # Verify projected improvements
        projected = tracking['projected_improvements']
        assert projected['pipeline_value_impact'] == 50000.0
        assert projected['velocity_improvement_percent'] == 15.0
        assert projected['conversion_improvement_percent'] == 10.0
        assert projected['activity_improvement_percent'] == 20.0
        
        # Verify tracking recommendations
        assert len(tracking['tracking_recommendations']) > 0
    
    def test_optimization_summary_generation(self):
        """Test optimization summary generation."""
        # Mock optimization results
        optimization_results = {
            'status': 'completed',
            'rep_performance_analysis': {
                'individual_analyses': [{'rep_id': 'rep_1'}, {'rep_id': 'rep_2'}],
                'team_summary': {
                    'top_improvement_areas': [{'area': 'activity_volume', 'affected_reps': 2}]
                }
            },
            'coaching_recommendations': [{'category': 'activity'}, {'category': 'conversion'}],
            'resource_allocation_optimization': {
                'reallocation_recommendations': [{'type': 'deal_reallocation'}],
                'workload_analysis': {'distribution_balance': 'imbalanced'}
            },
            'process_efficiency_improvements': {
                'efficiency_improvements': [{'category': 'process'}, {'category': 'automation'}],
                'process_adherence': {'overall_adherence_score': 65.0}
            }
        }
        
        summary = self.optimizer._generate_optimization_summary(optimization_results)
        
        assert summary['optimization_status'] == 'completed'
        assert summary['total_reps_analyzed'] == 2
        assert summary['total_coaching_recommendations'] == 2
        assert summary['total_resource_reallocations'] == 1
        assert summary['total_process_improvements'] == 2
        
        # Verify key findings
        key_findings = summary['key_findings']
        assert len(key_findings) > 0
        assert any('activity_volume' in finding for finding in key_findings)
        assert any('imbalanced' in finding for finding in key_findings)
        assert any('adherence' in finding for finding in key_findings)
        
        # Verify next steps
        next_steps = summary['next_steps']
        assert len(next_steps) > 0
        assert any('coaching' in step for step in next_steps)
        assert any('reallocation' in step for step in next_steps)
        assert any('process' in step for step in next_steps)
    
    def test_empty_data_handling(self):
        """Test handling of empty data sets."""
        results = self.optimizer.optimize_sales_process_efficiency(
            reps=[],
            deals=[],
            leads=[],
            activities=[]
        )
        
        # Should complete without errors
        assert results['status'] == 'completed'
        
        # Summary should reflect empty data
        summary = results['summary']
        assert summary['total_reps_analyzed'] == 0
        assert summary['total_coaching_recommendations'] == 0
        assert summary['total_resource_reallocations'] == 0