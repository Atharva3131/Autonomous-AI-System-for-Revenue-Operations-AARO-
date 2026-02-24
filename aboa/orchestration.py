"""
Main orchestration service for the AARO system.

This module implements the central orchestration service that wires together
all components of the Autonomous AI Agent for Revenue Operations (AARO).
It connects CRM data ingestion to sales knowledge management, links the revenue
decision engine to sales action execution and sales management loop, and
integrates revenue observability across all components.

Implements Requirements 7.1, 7.2:
- Modular, agent-based architecture with clear separation of concerns
- Distinct layers for data ingestion, reasoning, memory storage, and action execution
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from .core.config import get_settings
from .core.exceptions import ABOAException, handle_exception
from .core.logging import get_logger, log_business_event, log_system_event
from .data_ingestion.service import SalesDataIngestionService, IngestionConfig
from .knowledge.manager import SalesKnowledgeManager
from .knowledge.vector_store import ChromaVectorStore
from .knowledge.config import KnowledgeConfig
from .decision.revenue_decision_engine import RevenueDecisionEngine
from .decision.pipeline_risk_detector import PipelineRiskDetector
from .action.engine import SalesActionEngine
from .human_loop.sales_manager_interface import SalesManagerInterface
from .observability.metrics_collector import get_metrics_collector
from .observability.activity_logger import get_activity_logger
from .models.enums import DecisionClass, ExecutionStatus
from .models.revenue_entities import Deal, Lead, SalesRep, PipelineRisk, SalesAction

logger = get_logger(__name__)


class OrchestrationError(ABOAException):
    """Exception raised for orchestration errors."""
    pass


class AROOrchestrationService:
    """
    Main orchestration service for the AARO system.
    
    This service coordinates all components of the revenue operations system,
    managing the flow from data ingestion through decision-making to action
    execution, with comprehensive observability and human oversight.
    
    Architecture layers:
    1. Data Ingestion Layer - Collects and normalizes sales data
    2. Knowledge Layer - Stores and retrieves sales SOPs and guidance
    3. Decision Layer - Analyzes risks and generates recommendations
    4. Action Layer - Executes approved sales actions
    5. Human Loop - Manages approval workflows
    6. Observability Layer - Tracks metrics and activities
    """
    
    def __init__(self, 
                 tenant_id: Optional[str] = None,
                 config: Optional[Dict] = None):
        """
        Initialize the orchestration service.
        
        Args:
            tenant_id: Optional tenant identifier for multi-tenant support
            config: Optional configuration overrides
        """
        self.tenant_id = tenant_id
        self.config = config or {}
        self.settings = get_settings()
        self.is_running = False
        self.orchestration_tasks: List[asyncio.Task] = []
        
        # Initialize components
        self._initialize_components()
        
        logger.info(f"AROOrchestrationService initialized for tenant: {tenant_id}")
    
    def _initialize_components(self) -> None:
        """Initialize all system components with proper wiring."""
        try:
            # 1. Initialize Data Ingestion Layer
            ingestion_config = IngestionConfig(
                use_mock_data=self.config.get('use_mock_data', True),
                enable_validation=self.config.get('enable_validation', True),
                enable_scheduling=self.config.get('enable_scheduling', False),
                batch_size=self.config.get('batch_size', 100)
            )
            self.data_ingestion_service = SalesDataIngestionService(
                config=ingestion_config,
                tenant_id=self.tenant_id
            )
            
            # 2. Initialize Knowledge Management Layer
            vector_store = ChromaVectorStore(
                collection_name=f"sales_knowledge_{self.tenant_id}" if self.tenant_id else "sales_knowledge",
                persist_directory="./data/chroma_db"
            )
            knowledge_config = KnowledgeConfig()
            self.knowledge_manager = SalesKnowledgeManager(
                vector_store=vector_store,
                config=knowledge_config
            )
            
            # 3. Initialize Decision Layer
            self.pipeline_risk_detector = PipelineRiskDetector()
            self.revenue_decision_engine = RevenueDecisionEngine(
                knowledge_manager=self.knowledge_manager,
                config=self.config.get('decision_engine', {})
            )
            
            # 4. Initialize Action Execution Layer
            self.sales_action_engine = SalesActionEngine()
            
            # 5. Initialize Human-in-the-Loop Layer
            self.sales_manager_interface = SalesManagerInterface(
                config=self.config.get('human_loop', {})
            )
            
            # 6. Initialize Observability Layer
            self.metrics_collector = get_metrics_collector()
            self.activity_logger = get_activity_logger()
            
            logger.info("All system components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            raise OrchestrationError(f"Component initialization failed: {str(e)}")
    
    async def start_service(self) -> None:
        """Start the orchestration service and all components."""
        if self.is_running:
            logger.warning("Orchestration service is already running")
            return
        
        try:
            self.is_running = True
            
            # Start data ingestion service
            await self.data_ingestion_service.start_service()
            
            # Start main orchestration loop
            orchestration_task = asyncio.create_task(self._orchestration_loop())
            self.orchestration_tasks.append(orchestration_task)
            
            # Start periodic metrics collection
            metrics_task = asyncio.create_task(self._metrics_collection_loop())
            self.orchestration_tasks.append(metrics_task)
            
            log_system_event(
                logger,
                "orchestration_service_started",
                "aaro_orchestration",
                {"tenant_id": self.tenant_id}
            )
            
            logger.info("AARO orchestration service started successfully")
            
        except Exception as e:
            self.is_running = False
            log_system_event(
                logger,
                "orchestration_service_start_failed",
                "aaro_orchestration",
                error=e
            )
            raise
    
    async def stop_service(self) -> None:
        """Stop the orchestration service and all components."""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            # Cancel all orchestration tasks
            for task in self.orchestration_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self.orchestration_tasks:
                await asyncio.gather(*self.orchestration_tasks, return_exceptions=True)
            
            # Stop data ingestion service
            await self.data_ingestion_service.stop_service()
            
            log_system_event(
                logger,
                "orchestration_service_stopped",
                "aaro_orchestration"
            )
            
            logger.info("AARO orchestration service stopped")
            
        except Exception as e:
            log_system_event(
                logger,
                "orchestration_service_stop_failed",
                "aaro_orchestration",
                error=e
            )
            raise
    
    async def _orchestration_loop(self) -> None:
        """Main orchestration loop that coordinates all system components."""
        logger.info("Starting main orchestration loop")
        
        while self.is_running:
            try:
                # Execute one complete orchestration cycle
                await self._execute_orchestration_cycle()
                
                # Wait before next cycle
                cycle_interval = self.config.get('orchestration_cycle_minutes', 15)
                await asyncio.sleep(cycle_interval * 60)
                
            except asyncio.CancelledError:
                logger.info("Orchestration loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in orchestration loop: {str(e)}", exc_info=e)
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _execute_orchestration_cycle(self) -> None:
        """Execute one complete orchestration cycle."""
        cycle_start = datetime.utcnow()
        cycle_id = str(uuid4())
        
        logger.info(f"Starting orchestration cycle {cycle_id}")
        
        try:
            # Step 1: Ingest fresh sales data
            ingestion_stats = await self._ingest_sales_data()
            
            # Step 2: Detect pipeline risks
            pipeline_risks = await self._detect_pipeline_risks()
            
            # Step 3: Generate revenue decisions
            decisions = await self._generate_revenue_decisions(pipeline_risks)
            
            # Step 4: Execute approved actions
            execution_results = await self._execute_sales_actions(decisions)
            
            # Step 5: Process human approvals
            await self._process_human_approvals()
            
            # Step 6: Update observability metrics
            await self._update_observability_metrics(cycle_id, ingestion_stats, pipeline_risks, decisions, execution_results)
            
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            
            log_business_event(
                logger,
                "orchestration_cycle_completed",
                "revenue_operations",
                "cycle",
                details={
                    "cycle_id": cycle_id,
                    "duration_seconds": cycle_duration,
                    "ingested_records": ingestion_stats.total_records_processed,
                    "risks_detected": len(pipeline_risks),
                    "decisions_generated": len(decisions),
                    "actions_executed": len(execution_results)
                }
            )
            
        except Exception as e:
            logger.error(f"Orchestration cycle {cycle_id} failed: {str(e)}", exc_info=e)
            raise
    
    async def _ingest_sales_data(self) -> Any:
        """Ingest fresh sales data from all sources."""
        logger.debug("Ingesting sales data")
        
        # Calculate incremental ingestion window
        since = datetime.utcnow() - timedelta(hours=1)  # Last hour of data
        
        # Ingest data from all sources
        stats = await self.data_ingestion_service.ingest_all_data(
            since=since,
            limit_per_source=1000
        )
        
        logger.info(f"Ingested {stats.total_records_processed} records, {stats.total_records_failed} failed")
        return stats
    
    async def _detect_pipeline_risks(self) -> List[PipelineRisk]:
        """Detect pipeline risks from current sales data."""
        logger.debug("Detecting pipeline risks")
        
        # In a real implementation, this would fetch actual data from storage
        # For now, we'll use mock data to demonstrate the flow
        mock_deals = self._get_mock_deals()
        mock_leads = self._get_mock_leads()
        mock_reps = self._get_mock_reps()
        mock_activities = self._get_mock_activities()
        
        # Detect risks using the pipeline risk detector
        risks = self.pipeline_risk_detector.detect_pipeline_risks(
            deals=mock_deals,
            leads=mock_leads,
            activities=mock_activities,
            reps=mock_reps
        )
        
        logger.info(f"Detected {len(risks)} pipeline risks")
        return risks
    
    async def _generate_revenue_decisions(self, pipeline_risks: List[PipelineRisk]) -> List[Tuple[PipelineRisk, SalesAction, DecisionClass]]:
        """Generate revenue decisions for detected risks."""
        logger.debug(f"Generating revenue decisions for {len(pipeline_risks)} risks")
        
        if not pipeline_risks:
            return []
        
        # Get context data
        mock_deals = self._get_mock_deals()
        mock_leads = self._get_mock_leads()
        mock_reps = self._get_mock_reps()
        
        # Generate recommendations using the decision engine
        decisions = self.revenue_decision_engine.analyze_and_recommend(
            pipeline_risks=pipeline_risks,
            deals=mock_deals,
            leads=mock_leads,
            reps=mock_reps
        )
        
        # Log decisions for observability
        for risk, action, decision_class in decisions:
            self.activity_logger.log_revenue_decision(
                decision_id=str(uuid4()),
                decision_type=decision_class,
                confidence=risk.confidence,
                reasoning=action.expected_outcome,
                revenue_impact=action.revenue_impact,
                pipeline_risk_id=risk.risk_id
            )
        
        logger.info(f"Generated {len(decisions)} revenue decisions")
        return decisions
    
    async def _execute_sales_actions(self, decisions: List[Tuple[PipelineRisk, SalesAction, DecisionClass]]) -> List[Any]:
        """Execute approved sales actions."""
        logger.debug(f"Executing sales actions for {len(decisions)} decisions")
        
        execution_results = []
        
        for risk, action, decision_class in decisions:
            try:
                if decision_class == DecisionClass.AUTO_EXECUTABLE:
                    # Execute immediately
                    result = await self.sales_action_engine.execute_action(
                        action=action,
                        tenant_id=self.tenant_id,
                        metadata={"risk_id": risk.risk_id, "auto_executed": True}
                    )
                    execution_results.append(result)
                    
                    # Log action execution
                    self.activity_logger.log_sales_action(
                        action_id=action.action_id,
                        action_type=action.action_type,
                        execution_status=result.status,
                        target_system=action.target_system,
                        duration_ms=int(result.duration.total_seconds() * 1000) if result.duration else None,
                        retry_count=result.retry_count,
                        revenue_impact=action.revenue_impact
                    )
                    
                elif decision_class == DecisionClass.APPROVAL_REQUIRED:
                    # Request human approval
                    await self._request_human_approval(risk, action)
                    
                elif decision_class == DecisionClass.INSIGHT_ONLY:
                    # Log as insight for reporting
                    self.activity_logger.log_sales_activity(
                        activity_type="insight_generated",
                        component="orchestration",
                        entity_type="pipeline_risk",
                        entity_id=risk.risk_id,
                        details={
                            "risk_type": risk.risk_type.value,
                            "severity": risk.severity.value,
                            "recommended_action": action.action_type.value
                        }
                    )
                
            except Exception as e:
                logger.error(f"Failed to process decision for risk {risk.risk_id}: {str(e)}")
                continue
        
        logger.info(f"Executed {len(execution_results)} sales actions")
        return execution_results
    
    async def _request_human_approval(self, risk: PipelineRisk, action: SalesAction) -> None:
        """Request human approval for high-impact decisions."""
        # Create revenue context for approval
        from .models.revenue_entities import RevenueContext
        revenue_context = RevenueContext(
            deal_history=self._get_mock_deals(),
            rep_performance=self._get_mock_reps()[0] if self._get_mock_reps() else None,
            similar_deals=[],
            sales_playbook_guidance=[],
            market_conditions={}
        )
        
        # Request approval
        approval_request = self.sales_manager_interface.request_approval(
            pipeline_risk=risk,
            recommended_action=action,
            revenue_context=revenue_context,
            approver_id="sales_manager_1"  # Would be determined by routing rules
        )
        
        logger.info(f"Requested approval for risk {risk.risk_id}: {approval_request.request_id}")
    
    async def _process_human_approvals(self) -> None:
        """Process pending human approval requests."""
        # Get active approval requests
        active_requests = self.sales_manager_interface.get_active_requests()
        
        for request in active_requests:
            # Check for timeouts and handle escalation
            status, response = self.sales_manager_interface.check_approval_status(request.request_id)
            
            if status in [DecisionClass.APPROVED]:
                # Execute the approved action
                try:
                    result = await self.sales_action_engine.execute_action(
                        action=request.recommended_action,
                        tenant_id=self.tenant_id,
                        metadata={"approval_request_id": request.request_id, "human_approved": True}
                    )
                    
                    # Log execution
                    self.activity_logger.log_sales_action(
                        action_id=request.recommended_action.action_id,
                        action_type=request.recommended_action.action_type,
                        execution_status=result.status,
                        target_system=request.recommended_action.target_system,
                        duration_ms=int(result.duration.total_seconds() * 1000) if result.duration else None,
                        retry_count=result.retry_count,
                        revenue_impact=request.recommended_action.revenue_impact
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to execute approved action for request {request.request_id}: {str(e)}")
    
    async def _update_observability_metrics(self, cycle_id: str, ingestion_stats: Any, 
                                          risks: List[PipelineRisk], decisions: List, 
                                          execution_results: List) -> None:
        """Update observability metrics for the orchestration cycle."""
        # Log cycle metrics
        self.activity_logger.log_sales_activity(
            activity_type="orchestration_cycle",
            component="orchestration",
            entity_type="system",
            entity_id=cycle_id,
            details={
                "ingested_records": ingestion_stats.total_records_processed,
                "failed_records": ingestion_stats.total_records_failed,
                "risks_detected": len(risks),
                "decisions_generated": len(decisions),
                "actions_executed": len(execution_results),
                "execution_time": ingestion_stats.execution_time_seconds
            }
        )
    
    async def _metrics_collection_loop(self) -> None:
        """Periodic metrics collection loop."""
        logger.info("Starting metrics collection loop")
        
        while self.is_running:
            try:
                # Create comprehensive metrics snapshot
                snapshot = self.metrics_collector.create_comprehensive_snapshot(period_days=1)
                
                logger.info(f"Created metrics snapshot: {snapshot.snapshot_id}")
                
                # Wait for next collection cycle
                collection_interval = self.config.get('metrics_collection_hours', 6)
                await asyncio.sleep(collection_interval * 3600)
                
            except asyncio.CancelledError:
                logger.info("Metrics collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {str(e)}", exc_info=e)
                await asyncio.sleep(3600)  # Wait 1 hour before retrying
    
    # Mock data methods (would be replaced with actual data retrieval in production)
    
    def _get_mock_deals(self) -> List[Deal]:
        """Get mock deals for demonstration."""
        from decimal import Decimal
        from .models.enums import DealStage
        
        return [
            Deal(
                id="deal_1",
                lead_id="lead_1",
                stage=DealStage.PROPOSAL,
                value=Decimal("75000"),
                probability=0.7,
                close_date=datetime.utcnow() + timedelta(days=30),
                last_activity=datetime.utcnow() - timedelta(days=5),
                activities=[],
                assigned_rep="rep_1",
                days_in_current_stage=10,
                next_action_due=datetime.utcnow() + timedelta(days=2)
            ),
            Deal(
                id="deal_2",
                lead_id="lead_2",
                stage=DealStage.NEGOTIATION,
                value=Decimal("120000"),
                probability=0.8,
                close_date=datetime.utcnow() + timedelta(days=15),
                last_activity=datetime.utcnow() - timedelta(days=8),
                activities=[],
                assigned_rep="rep_2",
                days_in_current_stage=15,
                next_action_due=None
            )
        ]
    
    def _get_mock_leads(self) -> List[Lead]:
        """Get mock leads for demonstration."""
        from decimal import Decimal
        from .models.enums import LeadStatus
        from .models.revenue_entities import ContactInfo
        
        return [
            Lead(
                id="lead_1",
                source="website",
                contact_info=ContactInfo(
                    email="contact1@example.com",
                    phone="+1234567890",
                    name="John Doe",
                    company="Example Corp"
                ),
                status=LeadStatus.QUALIFIED,
                last_contact=datetime.utcnow() - timedelta(days=3),
                follow_up_due=datetime.utcnow() + timedelta(days=1),
                estimated_value=Decimal("50000"),
                assigned_rep="rep_1",
                contact_attempts=2,
                qualification_score=0.8
            )
        ]
    
    def _get_mock_reps(self) -> List[SalesRep]:
        """Get mock sales reps for demonstration."""
        from decimal import Decimal
        
        return [
            SalesRep(
                id="rep_1",
                name="Alice Johnson",
                email="alice.johnson@company.com",
                quota=Decimal("500000"),
                quota_attainment=0.75,
                pipeline_value=Decimal("400000"),
                activities_this_week=15,
                avg_deal_velocity=25.5,
                conversion_rates={"lead_to_opportunity": 0.3, "opportunity_to_close": 0.25}
            ),
            SalesRep(
                id="rep_2",
                name="Bob Smith",
                email="bob.smith@company.com",
                quota=Decimal("600000"),
                quota_attainment=0.65,
                pipeline_value=Decimal("350000"),
                activities_this_week=12,
                avg_deal_velocity=30.2,
                conversion_rates={"lead_to_opportunity": 0.35, "opportunity_to_close": 0.22}
            )
        ]
    
    def _get_mock_activities(self) -> List[SalesActivity]:
        """Get mock sales activities for demonstration."""
        from .models.enums import ActivityType
        
        return [
            SalesActivity(
                id="activity_1",
                deal_id="deal_1",
                lead_id="lead_1",
                rep_id="rep_1",
                activity_type=ActivityType.CALL,
                timestamp=datetime.utcnow() - timedelta(days=2),
                duration_minutes=30,
                outcome="Positive discussion about requirements",
                next_action="Send proposal",
                next_action_due=datetime.utcnow() + timedelta(days=3)
            ),
            SalesActivity(
                id="activity_2",
                deal_id="deal_2",
                lead_id="lead_2",
                rep_id="rep_2",
                activity_type=ActivityType.EMAIL,
                timestamp=datetime.utcnow() - timedelta(days=1),
                duration_minutes=5,
                outcome="Sent pricing information",
                next_action="Follow up on pricing questions",
                next_action_due=datetime.utcnow() + timedelta(days=2)
            ),
            SalesActivity(
                id="activity_3",
                deal_id="deal_1",
                lead_id="lead_1",
                rep_id="rep_1",
                activity_type=ActivityType.MEETING,
                timestamp=datetime.utcnow() - timedelta(days=5),
                duration_minutes=60,
                outcome="Demo completed successfully",
                next_action="Prepare proposal",
                next_action_due=datetime.utcnow() + timedelta(days=1)
            )
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all components."""
        health_status = {
            "orchestration_service": {
                "status": "healthy" if self.is_running else "stopped",
                "tenant_id": self.tenant_id
            }
        }
        
        try:
            # Check data ingestion service
            ingestion_health = await self.data_ingestion_service.health_check()
            health_status["data_ingestion"] = ingestion_health
            
            # Check knowledge manager
            health_status["knowledge_manager"] = {
                "status": "healthy",
                "document_count": self.knowledge_manager.get_document_count()
            }
            
            # Check action engine
            active_executions = await self.sales_action_engine.list_active_executions()
            health_status["action_engine"] = {
                "status": "healthy",
                "active_executions": len(active_executions)
            }
            
            # Check human loop
            active_approvals = self.sales_manager_interface.get_active_requests()
            health_status["human_loop"] = {
                "status": "healthy",
                "active_approval_requests": len(active_approvals)
            }
            
            # Overall health
            all_healthy = all(
                component.get("status") == "healthy" 
                for component in health_status.values()
                if isinstance(component, dict) and "status" in component
            )
            
            health_status["overall"] = {
                "status": "healthy" if all_healthy else "degraded",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status["overall"] = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return health_status


# Global orchestration service instance
_global_orchestration_service: Optional[AROOrchestrationService] = None


def get_orchestration_service(tenant_id: Optional[str] = None) -> AROOrchestrationService:
    """Get the global orchestration service instance."""
    global _global_orchestration_service
    if _global_orchestration_service is None:
        _global_orchestration_service = AROOrchestrationService(tenant_id=tenant_id)
    return _global_orchestration_service