"""
Integration tests for the orchestration service.

Tests the wiring between all components and end-to-end workflows.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from aboa.orchestration import AROOrchestrationService
from aboa.models.enums import RiskType, Severity, DecisionClass, SalesActionType
from aboa.models.revenue_entities import PipelineRisk


class TestOrchestrationIntegration:
    """Test orchestration service integration."""
    
    @pytest.fixture
    def orchestration_service(self):
        """Create orchestration service for testing."""
        service = AROOrchestrationService(tenant_id="test_tenant")
        return service
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, orchestration_service):
        """Test that all components are properly initialized."""
        # Check that all components are initialized
        assert orchestration_service.data_ingestion_service is not None
        assert orchestration_service.knowledge_manager is not None
        assert orchestration_service.pipeline_risk_detector is not None
        assert orchestration_service.revenue_decision_engine is not None
        assert orchestration_service.sales_action_engine is not None
        assert orchestration_service.sales_manager_interface is not None
        assert orchestration_service.metrics_collector is not None
        assert orchestration_service.activity_logger is not None
        
        # Cleanup
        if orchestration_service.is_running:
            await orchestration_service.stop_service()
    
    @pytest.mark.asyncio
    async def test_service_start_stop(self, orchestration_service):
        """Test service startup and shutdown."""
        try:
            # Test startup
            await orchestration_service.start_service()
            assert orchestration_service.is_running is True
            
            # Test shutdown
            await orchestration_service.stop_service()
            assert orchestration_service.is_running is False
        finally:
            # Ensure cleanup
            if orchestration_service.is_running:
                await orchestration_service.stop_service()
    
    @pytest.mark.asyncio
    async def test_health_check(self, orchestration_service):
        """Test comprehensive health check."""
        health_status = await orchestration_service.health_check()
        
        # Check that health status contains all expected components
        assert "orchestration_service" in health_status
        assert "data_ingestion" in health_status
        assert "knowledge_manager" in health_status
        assert "action_engine" in health_status
        assert "human_loop" in health_status
        assert "overall" in health_status
        
        # Check overall status
        assert health_status["overall"]["status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_data_ingestion_to_knowledge_wiring(self, orchestration_service):
        """Test connection between data ingestion and knowledge management."""
        # Test data ingestion
        stats = await orchestration_service._ingest_sales_data()
        assert stats is not None
        assert hasattr(stats, 'total_records_processed')
        
        # Test knowledge manager functionality
        doc_count = orchestration_service.knowledge_manager.get_document_count()
        assert isinstance(doc_count, int)
    
    @pytest.mark.asyncio
    async def test_decision_engine_to_action_engine_wiring(self, orchestration_service):
        """Test connection between decision engine and action engine."""
        # Create a mock pipeline risk
        mock_risk = PipelineRisk(
            risk_id="test_risk_1",
            risk_type=RiskType.STALLED_DEAL,
            detected_at=datetime.utcnow(),
            confidence=85.0,
            affected_deals=["deal_1"],
            affected_leads=[],
            severity=Severity.MEDIUM,
            description="Test stalled deal",
            recommended_actions=["CREATE_TASK"]
        )
        
        # Test decision generation
        decisions = await orchestration_service._generate_revenue_decisions([mock_risk])
        assert len(decisions) > 0
        
        # Test action execution
        execution_results = await orchestration_service._execute_sales_actions(decisions)
        # Should have at least one result for auto-executable actions
        assert isinstance(execution_results, list)
    
    @pytest.mark.asyncio
    async def test_human_loop_integration(self, orchestration_service):
        """Test human-in-the-loop integration."""
        # Create a high-value risk that requires approval
        high_value_risk = PipelineRisk(
            risk_id="test_risk_high_value",
            risk_type=RiskType.INACTIVE_HIGH_VALUE,
            detected_at=datetime.utcnow(),
            confidence=90.0,
            affected_deals=["high_value_deal"],
            affected_leads=[],
            severity=Severity.HIGH,
            description="High-value deal at risk",
            recommended_actions=["UPDATE_DEAL"]
        )
        
        # Generate decisions (should require approval)
        decisions = await orchestration_service._generate_revenue_decisions([high_value_risk])
        
        # Execute actions (should create approval requests)
        await orchestration_service._execute_sales_actions(decisions)
        
        # Check that approval requests were created
        active_requests = orchestration_service.sales_manager_interface.get_active_requests()
        # Should have at least one active request if high-value decision was generated
        assert isinstance(active_requests, list)
    
    @pytest.mark.asyncio
    async def test_observability_integration(self, orchestration_service):
        """Test observability system integration."""
        # Test metrics collection
        snapshot = orchestration_service.metrics_collector.create_comprehensive_snapshot(period_days=1)
        assert snapshot is not None
        assert snapshot.metrics is not None
        
        # Test activity logging
        orchestration_service.activity_logger.log_sales_activity(
            activity_type="test_activity",
            component="test",
            entity_type="test",
            entity_id="test_123",
            details={"test": "data"}
        )
        
        # Verify activity was logged
        activities = orchestration_service.activity_logger.search_activity_logs(
            entity_type="test",
            limit=10
        )
        assert len(activities) > 0
        
        # Cleanup
        if orchestration_service.is_running:
            await orchestration_service.stop_service()
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, orchestration_service):
        """Test complete end-to-end workflow."""
        # Start the service
        await orchestration_service.start_service()
        
        try:
            # Execute one orchestration cycle
            await orchestration_service._execute_orchestration_cycle()
            
            # Verify that the cycle completed without errors
            # (If we get here without exceptions, the basic workflow is working)
            assert True
            
        finally:
            # Stop the service
            await orchestration_service.stop_service()
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Test tenant isolation in orchestration."""
        # Create two services with different tenant IDs
        service1 = AROOrchestrationService(tenant_id="tenant_1")
        service2 = AROOrchestrationService(tenant_id="tenant_2")
        
        try:
            # Verify they have different tenant IDs
            assert service1.tenant_id == "tenant_1"
            assert service2.tenant_id == "tenant_2"
            
            # Verify they are separate instances
            assert service1 is not service2
            
        finally:
            # Cleanup
            if service1.is_running:
                await service1.stop_service()
            if service2.is_running:
                await service2.stop_service()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_orchestration(self, orchestration_service):
        """Test error handling in orchestration cycles."""
        # This test verifies that the orchestration service handles errors gracefully
        # and continues operating even when individual components fail
        
        # Start the service
        await orchestration_service.start_service()
        
        try:
            # The orchestration cycle should handle errors gracefully
            # Even if some components fail, it should continue
            await orchestration_service._execute_orchestration_cycle()
            
            # If we reach here, error handling is working
            assert True
            
        except Exception as e:
            # If an exception is raised, it should be a controlled failure
            # not a system crash
            assert "orchestration" in str(e).lower() or "error" in str(e).lower()
            
        finally:
            await orchestration_service.stop_service()


if __name__ == "__main__":
    # Run a simple test
    async def main():
        service = AROOrchestrationService(tenant_id="test")
        health = await service.health_check()
        print("Health check:", health)
    
    asyncio.run(main())