"""
Unit tests for the observability system.

Tests the sales activity logging, metrics collection, and API functionality
of the comprehensive observability system.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from aboa.models.enums import (
    DecisionClass, ExecutionStatus, SalesActionType, ActivityType
)
from aboa.observability.activity_logger import (
    SalesActivityLogger, ActivityLogEntry, DecisionLogEntry, ActionLogEntry
)
from aboa.observability.metrics_collector import (
    RevenueMetricsCollector, MetricSnapshot
)


class TestSalesActivityLogger:
    """Test cases for SalesActivityLogger."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = SalesActivityLogger("test_logger")
    
    def test_log_sales_activity(self):
        """Test logging sales activities."""
        log_id = self.logger.log_sales_activity(
            activity_type="lead_created",
            component="data_ingestion",
            entity_type="lead",
            entity_id="lead_123",
            user_id="user_456",
            details={"source": "website"},
            revenue_impact=1000.0
        )
        
        assert log_id is not None
        assert len(self.logger.activity_logs) == 1
        
        log_entry = self.logger.activity_logs[0]
        assert log_entry.activity_type == "lead_created"
        assert log_entry.component == "data_ingestion"
        assert log_entry.entity_type == "lead"
        assert log_entry.entity_id == "lead_123"
        assert log_entry.user_id == "user_456"
        assert log_entry.details["source"] == "website"
        assert log_entry.revenue_impact == 1000.0
    
    def test_log_revenue_decision(self):
        """Test logging revenue decisions."""
        log_id = self.logger.log_revenue_decision(
            decision_id="decision_123",
            decision_type=DecisionClass.AUTO_EXECUTABLE,
            pipeline_risk_id="risk_456",
            confidence=85.5,
            reasoning="High confidence automated decision",
            revenue_impact=2500.0
        )
        
        assert log_id is not None
        assert len(self.logger.decision_logs) == 1
        
        log_entry = self.logger.decision_logs[0]
        assert log_entry.decision_id == "decision_123"
        assert log_entry.decision_type == DecisionClass.AUTO_EXECUTABLE
        assert log_entry.pipeline_risk_id == "risk_456"
        assert log_entry.confidence == 85.5
        assert log_entry.reasoning == "High confidence automated decision"
        assert log_entry.revenue_impact == 2500.0
    
    def test_log_sales_action(self):
        """Test logging sales actions."""
        log_id = self.logger.log_sales_action(
            action_id="action_123",
            action_type=SalesActionType.CREATE_TASK,
            execution_status=ExecutionStatus.COMPLETED,
            target_system="crm",
            parameters={"task_type": "follow_up"},
            duration_ms=1500,
            revenue_impact=500.0
        )
        
        assert log_id is not None
        assert len(self.logger.action_logs) == 1
        
        log_entry = self.logger.action_logs[0]
        assert log_entry.action_id == "action_123"
        assert log_entry.action_type == SalesActionType.CREATE_TASK
        assert log_entry.execution_status == ExecutionStatus.COMPLETED
        assert log_entry.target_system == "crm"
        assert log_entry.parameters["task_type"] == "follow_up"
        assert log_entry.duration_ms == 1500
        assert log_entry.revenue_impact == 500.0
    
    def test_log_business_entity_change(self):
        """Test logging business entity changes."""
        log_id = self.logger.log_business_entity_change(
            entity_type="deal",
            entity_id="deal_123",
            change_type="updated",
            old_values={"stage": "qualification"},
            new_values={"stage": "proposal"},
            user_id="user_456"
        )
        
        assert log_id is not None
        assert len(self.logger.activity_logs) == 1
        
        log_entry = self.logger.activity_logs[0]
        assert log_entry.activity_type == "deal_updated"
        assert log_entry.entity_type == "deal"
        assert log_entry.entity_id == "deal_123"
        assert log_entry.details["change_type"] == "updated"
        assert log_entry.details["old_values"]["stage"] == "qualification"
        assert log_entry.details["new_values"]["stage"] == "proposal"
    
    def test_search_activity_logs(self):
        """Test searching activity logs."""
        # Create test logs
        self.logger.log_sales_activity("lead_created", "ingestion", "lead", "lead_1")
        self.logger.log_sales_activity("deal_updated", "decision", "deal", "deal_1")
        self.logger.log_sales_activity("lead_updated", "ingestion", "lead", "lead_2")
        
        # Search by activity type
        results = self.logger.search_activity_logs(activity_type="lead_created")
        assert len(results) == 1
        assert results[0].activity_type == "lead_created"
        
        # Search by component
        results = self.logger.search_activity_logs(component="ingestion")
        assert len(results) == 2
        
        # Search by entity type
        results = self.logger.search_activity_logs(entity_type="lead")
        assert len(results) == 2
        
        # Search with limit
        results = self.logger.search_activity_logs(limit=1)
        assert len(results) == 1
    
    def test_search_decision_logs(self):
        """Test searching decision logs."""
        # Create test logs
        self.logger.log_revenue_decision("dec_1", DecisionClass.AUTO_EXECUTABLE, confidence=90.0)
        self.logger.log_revenue_decision("dec_2", DecisionClass.APPROVAL_REQUIRED, confidence=60.0)
        self.logger.log_revenue_decision("dec_3", DecisionClass.AUTO_EXECUTABLE, confidence=95.0)
        
        # Search by decision type
        results = self.logger.search_decision_logs(decision_type=DecisionClass.AUTO_EXECUTABLE)
        assert len(results) == 2
        
        # Search by minimum confidence
        results = self.logger.search_decision_logs(min_confidence=80.0)
        assert len(results) == 2
        
        # Search with limit
        results = self.logger.search_decision_logs(limit=1)
        assert len(results) == 1
    
    def test_search_action_logs(self):
        """Test searching action logs."""
        # Create test logs
        self.logger.log_sales_action("act_1", SalesActionType.CREATE_TASK, ExecutionStatus.COMPLETED, "crm")
        self.logger.log_sales_action("act_2", SalesActionType.SEND_ALERT, ExecutionStatus.FAILED, "email")
        self.logger.log_sales_action("act_3", SalesActionType.CREATE_TASK, ExecutionStatus.COMPLETED, "crm")
        
        # Search by action type
        results = self.logger.search_action_logs(action_type=SalesActionType.CREATE_TASK)
        assert len(results) == 2
        
        # Search by execution status
        results = self.logger.search_action_logs(execution_status=ExecutionStatus.COMPLETED)
        assert len(results) == 2
        
        # Search by target system
        results = self.logger.search_action_logs(target_system="crm")
        assert len(results) == 2
    
    def test_get_audit_trail(self):
        """Test getting audit trail for an entity."""
        # Create test logs for specific entity
        self.logger.log_sales_activity("lead_created", "ingestion", "lead", "lead_123")
        self.logger.log_sales_activity("lead_updated", "decision", "lead", "lead_123")
        self.logger.log_sales_activity("deal_created", "ingestion", "deal", "deal_456")
        
        # Get audit trail for lead_123
        audit_trail = self.logger.get_audit_trail("lead", "lead_123")
        assert len(audit_trail) == 2
        
        for entry in audit_trail:
            assert entry.entity_type == "lead"
            assert entry.entity_id == "lead_123"
    
    def test_get_system_health_metrics(self):
        """Test getting system health metrics."""
        # Create some test logs
        self.logger.log_sales_activity("test_activity", "test_component")
        self.logger.log_revenue_decision("test_decision", DecisionClass.AUTO_EXECUTABLE)
        self.logger.log_sales_action("test_action", SalesActionType.CREATE_TASK, ExecutionStatus.COMPLETED, "test")
        
        metrics = self.logger.get_system_health_metrics()
        
        assert "timestamp" in metrics
        assert "total_activity_logs" in metrics
        assert "total_decision_logs" in metrics
        assert "total_action_logs" in metrics
        assert metrics["total_activity_logs"] == 1
        assert metrics["total_decision_logs"] == 1
        assert metrics["total_action_logs"] == 1
    
    def test_export_logs_json(self):
        """Test exporting logs as JSON."""
        # Create test logs
        self.logger.log_sales_activity("test_activity", "test_component")
        self.logger.log_revenue_decision("test_decision", DecisionClass.AUTO_EXECUTABLE)
        self.logger.log_sales_action("test_action", SalesActionType.CREATE_TASK, ExecutionStatus.COMPLETED, "test")
        
        # Export logs
        exported_json = self.logger.export_logs_json()
        
        # Parse and validate JSON
        exported_data = json.loads(exported_json)
        
        assert "export_timestamp" in exported_data
        assert "activity_logs" in exported_data
        assert "decision_logs" in exported_data
        assert "action_logs" in exported_data
        assert len(exported_data["activity_logs"]) == 1
        assert len(exported_data["decision_logs"]) == 1
        assert len(exported_data["action_logs"]) == 1


class TestRevenueMetricsCollector:
    """Test cases for RevenueMetricsCollector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = RevenueMetricsCollector("test_metrics")
        
        # Mock the activity logger
        self.mock_activity_logger = Mock()
        self.collector.activity_logger = self.mock_activity_logger
    
    def test_collect_pipeline_recovery_metrics(self):
        """Test collecting pipeline recovery metrics."""
        # Mock decision logs
        mock_decisions = [
            Mock(decision_type=DecisionClass.AUTO_EXECUTABLE, revenue_impact=1000.0),
            Mock(decision_type=DecisionClass.APPROVAL_REQUIRED, revenue_impact=2000.0),
            Mock(decision_type=DecisionClass.INSIGHT_ONLY, revenue_impact=None)
        ]
        
        # Mock action logs
        mock_actions = [
            Mock(execution_status=ExecutionStatus.COMPLETED, revenue_impact=500.0),
            Mock(execution_status=ExecutionStatus.FAILED, revenue_impact=None),
            Mock(execution_status=ExecutionStatus.COMPLETED, revenue_impact=750.0)
        ]
        
        self.mock_activity_logger.search_decision_logs.return_value = mock_decisions
        self.mock_activity_logger.search_action_logs.return_value = mock_actions
        
        start_time = datetime.now(timezone.utc) - timedelta(days=7)
        end_time = datetime.now(timezone.utc)
        
        metrics = self.collector.collect_pipeline_recovery_metrics(start_time, end_time)
        
        assert metrics["total_decisions"] == 3
        assert metrics["auto_decisions"] == 1
        assert metrics["approval_decisions"] == 1
        assert metrics["insight_decisions"] == 1
        assert metrics["successful_actions"] == 2
        assert metrics["failed_actions"] == 1
        assert metrics["action_success_rate"] == 2/3
        assert metrics["automation_rate"] == 1/3
        assert metrics["total_revenue_impact"] == 3000.0
        assert metrics["pipeline_recovered"] == 1250.0
    
    def test_collect_velocity_improvement_metrics(self):
        """Test collecting velocity improvement metrics."""
        # Mock activity logs for deals
        now = datetime.now(timezone.utc)
        mock_activities = [
            Mock(entity_id="deal_1", timestamp=now - timedelta(hours=2), activity_type="deal_updated"),
            Mock(entity_id="deal_1", timestamp=now - timedelta(hours=1), activity_type="follow_up_scheduled"),
            Mock(entity_id="deal_2", timestamp=now - timedelta(hours=3), activity_type="deal_created"),
            Mock(entity_id="deal_2", timestamp=now, activity_type="deal_updated")
        ]
        
        self.mock_activity_logger.search_activity_logs.return_value = mock_activities
        
        start_time = now - timedelta(days=7)
        end_time = now
        
        metrics = self.collector.collect_velocity_improvement_metrics(start_time, end_time)
        
        assert metrics["deals_with_activity"] == 2
        assert metrics["total_deal_activities"] == 4
        assert metrics["deals_accelerated"] == 1  # deal_1 has follow-up activity
        assert "avg_hours_between_activities" in metrics
        assert "velocity_improvement_percentage" in metrics
    
    def test_collect_manual_work_reduction_metrics(self):
        """Test collecting manual work reduction metrics."""
        # Mock action logs
        mock_actions = [
            Mock(action_type=SalesActionType.CREATE_TASK, execution_status=ExecutionStatus.COMPLETED),
            Mock(action_type=SalesActionType.SEND_ALERT, execution_status=ExecutionStatus.COMPLETED),
            Mock(action_type=SalesActionType.CREATE_FOLLOWUP_MESSAGE, execution_status=ExecutionStatus.COMPLETED),
            Mock(action_type=SalesActionType.UPDATE_DEAL, execution_status=ExecutionStatus.FAILED)
        ]
        
        self.mock_activity_logger.search_action_logs.return_value = mock_actions
        
        start_time = datetime.now(timezone.utc) - timedelta(days=7)
        end_time = datetime.now(timezone.utc)
        
        metrics = self.collector.collect_manual_work_reduction_metrics(start_time, end_time)
        
        assert metrics["successful_automations"] == 3
        assert metrics["total_time_saved_minutes"] == 22  # 5 + 2 + 15 minutes
        assert metrics["total_time_saved_hours"] == 22/60
        assert "time_saved_by_action_type" in metrics
        assert metrics["avg_time_saved_per_automation"] == 22/3
    
    def test_collect_system_performance_metrics(self):
        """Test collecting system performance metrics."""
        # Mock action logs with performance data
        mock_actions = [
            Mock(
                execution_status=ExecutionStatus.COMPLETED,
                duration_ms=1000,
                retry_count=0,
                action_type=SalesActionType.CREATE_TASK
            ),
            Mock(
                execution_status=ExecutionStatus.FAILED,
                duration_ms=2000,
                retry_count=2,
                action_type=SalesActionType.SEND_ALERT
            ),
            Mock(
                execution_status=ExecutionStatus.COMPLETED,
                duration_ms=1500,
                retry_count=1,
                action_type=SalesActionType.CREATE_TASK
            )
        ]
        
        self.mock_activity_logger.search_action_logs.return_value = mock_actions
        
        start_time = datetime.now(timezone.utc) - timedelta(days=7)
        end_time = datetime.now(timezone.utc)
        
        metrics = self.collector.collect_system_performance_metrics(start_time, end_time)
        
        assert metrics["total_actions"] == 3
        assert metrics["completed_actions"] == 2
        assert metrics["failed_actions"] == 1
        assert metrics["success_rate"] == 2/3
        assert metrics["failure_rate"] == 1/3
        assert metrics["avg_response_time_ms"] == 1500  # (1000 + 2000 + 1500) / 3
        assert metrics["actions_with_retries"] == 2
        assert metrics["total_retries"] == 3
        assert "error_rates_by_action_type" in metrics
    
    def test_collect_decision_accuracy_metrics(self):
        """Test collecting decision accuracy metrics."""
        # Mock decision logs
        mock_decisions = [
            Mock(
                confidence=90.0,
                decision_type=DecisionClass.AUTO_EXECUTABLE,
                outcome="success",
                human_decision=None
            ),
            Mock(
                confidence=75.0,
                decision_type=DecisionClass.APPROVAL_REQUIRED,
                outcome="success",
                human_decision="approved"
            ),
            Mock(
                confidence=60.0,
                decision_type=DecisionClass.APPROVAL_REQUIRED,
                outcome=None,
                human_decision="denied"
            )
        ]
        
        self.mock_activity_logger.search_decision_logs.return_value = mock_decisions
        
        start_time = datetime.now(timezone.utc) - timedelta(days=7)
        end_time = datetime.now(timezone.utc)
        
        metrics = self.collector.collect_decision_accuracy_metrics(start_time, end_time)
        
        assert metrics["total_decisions"] == 3
        assert metrics["avg_confidence_score"] == 75.0  # (90 + 75 + 60) / 3
        assert metrics["decisions_with_outcomes"] == 2
        assert metrics["positive_outcomes"] == 2
        assert metrics["accuracy_rate"] == 1.0  # 2/2
        assert metrics["human_decisions"] == 2
        assert metrics["approvals"] == 1
        assert metrics["denials"] == 1
        assert metrics["approval_rate"] == 0.5
    
    def test_create_comprehensive_snapshot(self):
        """Test creating comprehensive metrics snapshot."""
        # Mock all the individual metric collection methods
        with patch.object(self.collector, 'collect_pipeline_recovery_metrics') as mock_pipeline, \
             patch.object(self.collector, 'collect_velocity_improvement_metrics') as mock_velocity, \
             patch.object(self.collector, 'collect_manual_work_reduction_metrics') as mock_manual, \
             patch.object(self.collector, 'collect_system_performance_metrics') as mock_performance, \
             patch.object(self.collector, 'collect_decision_accuracy_metrics') as mock_accuracy:
            
            # Set up mock return values
            mock_pipeline.return_value = {"total_decisions": 10}
            mock_velocity.return_value = {"deals_accelerated": 5}
            mock_manual.return_value = {"total_time_saved_hours": 20}
            mock_performance.return_value = {"success_rate": 0.95}
            mock_accuracy.return_value = {"accuracy_rate": 0.85}
            
            # Create snapshot
            snapshot = self.collector.create_comprehensive_snapshot(period_days=7)
            
            # Verify snapshot structure
            assert isinstance(snapshot, MetricSnapshot)
            assert snapshot.period_start is not None
            assert snapshot.period_end is not None
            assert "pipeline_recovery" in snapshot.metrics
            assert "velocity_improvement" in snapshot.metrics
            assert "manual_work_reduction" in snapshot.metrics
            assert "system_performance" in snapshot.metrics
            assert "decision_accuracy" in snapshot.metrics
            assert snapshot.metrics["period_days"] == 7
            
            # Verify snapshot is stored
            assert len(self.collector.metric_snapshots) == 1
            assert self.collector.metric_snapshots[0] == snapshot
    
    def test_get_trend_analysis(self):
        """Test trend analysis functionality."""
        # Create mock snapshots with different metric values
        now = datetime.now(timezone.utc)
        snapshots = [
            MetricSnapshot(
                period_start=now - timedelta(days=14),
                period_end=now - timedelta(days=7),
                metrics={"pipeline_recovery": {"total_decisions": 10}}
            ),
            MetricSnapshot(
                period_start=now - timedelta(days=7),
                period_end=now,
                metrics={"pipeline_recovery": {"total_decisions": 15}}
            )
        ]
        
        # Analyze trend
        analysis = self.collector.get_trend_analysis(
            metric_name="pipeline_recovery.total_decisions",
            snapshots=snapshots
        )
        
        assert analysis["metric_name"] == "pipeline_recovery.total_decisions"
        assert analysis["data_points"] == 2
        assert analysis["first_value"] == 10
        assert analysis["last_value"] == 15
        assert analysis["percentage_change"] == 50.0  # (15-10)/10 * 100
        assert analysis["trend_direction"] == "increasing"
    
    def test_export_metrics_report(self):
        """Test exporting metrics report."""
        # Create a test snapshot
        snapshot = MetricSnapshot(
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
            metrics={
                "pipeline_recovery": {"total_decisions": 10, "automation_rate": 0.8, "action_success_rate": 0.9, "pipeline_recovered": 5000.0},
                "velocity_improvement": {"deals_with_activity": 20, "deals_accelerated": 15, "velocity_improvement_percentage": 25.0},
                "manual_work_reduction": {"successful_automations": 50, "total_time_saved_hours": 30.0, "avg_time_saved_per_automation": 36.0},
                "system_performance": {"success_rate": 0.95, "avg_response_time_ms": 1200, "avg_retries_per_action": 0.1},
                "decision_accuracy": {"avg_confidence_score": 85.0, "accuracy_rate": 0.9, "approval_rate": 0.8}
            }
        )
        
        # Test JSON export
        json_report = self.collector.export_metrics_report(snapshot, format="json")
        assert isinstance(json_report, str)
        
        # Test summary export
        summary_report = self.collector.export_metrics_report(snapshot, format="summary")
        assert isinstance(summary_report, str)
        assert "Revenue Operations Metrics Report" in summary_report
        assert "PIPELINE RECOVERY:" in summary_report
        assert "VELOCITY IMPROVEMENT:" in summary_report
        assert "MANUAL WORK REDUCTION:" in summary_report


class TestActivityLogModels:
    """Test cases for activity log data models."""
    
    def test_activity_log_entry_creation(self):
        """Test creating ActivityLogEntry."""
        entry = ActivityLogEntry(
            activity_type="test_activity",
            component="test_component",
            entity_type="test_entity",
            entity_id="test_123",
            details={"key": "value"}
        )
        
        assert entry.activity_type == "test_activity"
        assert entry.component == "test_component"
        assert entry.entity_type == "test_entity"
        assert entry.entity_id == "test_123"
        assert entry.details["key"] == "value"
        assert entry.log_id is not None
        assert entry.timestamp is not None
    
    def test_decision_log_entry_creation(self):
        """Test creating DecisionLogEntry."""
        entry = DecisionLogEntry(
            decision_id="decision_123",
            decision_type=DecisionClass.AUTO_EXECUTABLE,
            confidence=85.5,
            reasoning="Test reasoning"
        )
        
        assert entry.decision_id == "decision_123"
        assert entry.decision_type == DecisionClass.AUTO_EXECUTABLE
        assert entry.confidence == 85.5
        assert entry.reasoning == "Test reasoning"
        assert entry.log_id is not None
        assert entry.timestamp is not None
    
    def test_action_log_entry_creation(self):
        """Test creating ActionLogEntry."""
        entry = ActionLogEntry(
            action_id="action_123",
            action_type=SalesActionType.CREATE_TASK,
            execution_status=ExecutionStatus.COMPLETED,
            target_system="test_system",
            parameters={"param": "value"}
        )
        
        assert entry.action_id == "action_123"
        assert entry.action_type == SalesActionType.CREATE_TASK
        assert entry.execution_status == ExecutionStatus.COMPLETED
        assert entry.target_system == "test_system"
        assert entry.parameters["param"] == "value"
        assert entry.log_id is not None
        assert entry.timestamp is not None


class TestMetricSnapshot:
    """Test cases for MetricSnapshot model."""
    
    def test_metric_snapshot_creation(self):
        """Test creating MetricSnapshot."""
        start_time = datetime.now(timezone.utc) - timedelta(days=7)
        end_time = datetime.now(timezone.utc)
        
        snapshot = MetricSnapshot(
            period_start=start_time,
            period_end=end_time,
            metrics={"test_metric": 123}
        )
        
        assert snapshot.period_start == start_time
        assert snapshot.period_end == end_time
        assert snapshot.metrics["test_metric"] == 123
        assert snapshot.snapshot_id is not None
        assert snapshot.timestamp is not None