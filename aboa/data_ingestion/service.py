# Sales data ingestion service
"""
Main sales data ingestion service with error handling, retry logic, and batch processing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from uuid import uuid4

from aboa.core.config import get_settings
from aboa.core.exceptions import (
    DataIngestionError, 
    ExternalIntegrationError, 
    RetryableError,
    handle_exception
)
from aboa.core.logging import log_business_event, log_system_event
from aboa.data_ingestion.connectors import (
    SalesDataConnector,
    CRMDealConnector,
    SalesActivityConnector,
    RepPerformanceConnector,
    LeadManagementConnector,
    SalesDataNormalizer,
    SalesDataValidator,
    AuthConfig,
    RateLimitConfig,
    DataIngestionResult,
    ConnectionStatus
)
from aboa.models.revenue_entities import Deal, Lead, SalesActivity, SalesRep
from aboa.models.enums import LeadStatus, DealStage

logger = logging.getLogger(__name__)

@dataclass
class IngestionConfig:
    """Configuration for data ingestion operations."""
    batch_size: int = 100
    max_concurrent_connectors: int = 4
    retry_delay_seconds: int = 5
    max_retries: int = 3
    use_mock_data: bool = True
    enable_validation: bool = True
    enable_scheduling: bool = False
    schedule_interval_minutes: int = 60

@dataclass
class IngestionStats:
    """Statistics for ingestion operations."""
    total_records_processed: int = 0
    total_records_failed: int = 0
    deals_processed: int = 0
    leads_processed: int = 0
    activities_processed: int = 0
    reps_processed: int = 0
    execution_time_seconds: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class SalesDataIngestionService:
    """
    Main service for ingesting sales data from CRM systems with error handling,
    retry logic, batch processing capabilities, and tenant isolation.
    """
    
    def __init__(self, config: Optional[IngestionConfig] = None, tenant_id: Optional[str] = None):
        """Initialize the sales data ingestion service with optional tenant context."""
        self.config = config or IngestionConfig()
        self.settings = get_settings()
        self.tenant_id = tenant_id
        self.connectors: Dict[str, SalesDataConnector] = {}
        self.normalizer = SalesDataNormalizer()
        self.validator = SalesDataValidator()
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Setup tenant-specific configuration
        if tenant_id:
            self._setup_tenant_isolation()
        
        # Initialize connectors
        self._initialize_connectors()
    
    def _setup_tenant_isolation(self) -> None:
        """Setup tenant-specific data isolation and configuration."""
        logger.info(f"Setting up data ingestion for tenant: {self.tenant_id}")
        
        # In a real implementation, this would:
        # 1. Configure database schema/namespace for tenant
        # 2. Set up tenant-specific CRM connections
        # 3. Configure data validation rules per tenant
        # 4. Set up tenant-specific storage paths
        # 5. Apply tenant resource limits
        
        # For now, we'll just add tenant context to logging
        self._tenant_log_context = {"tenant_id": self.tenant_id}
        
    def _initialize_connectors(self) -> None:
        """Initialize all sales data connectors."""
        try:
            # Default auth config for mock data
            auth_config = AuthConfig(auth_type="none")
            rate_limit_config = RateLimitConfig()
            
            # Initialize connectors with mock data capability
            self.connectors = {
                "deals": CRMDealConnector(
                    auth_config=auth_config,
                    rate_limit_config=rate_limit_config,
                    use_mock_data=self.config.use_mock_data
                ),
                "activities": SalesActivityConnector(
                    auth_config=auth_config,
                    rate_limit_config=rate_limit_config,
                    use_mock_data=self.config.use_mock_data
                ),
                "reps": RepPerformanceConnector(
                    auth_config=auth_config,
                    rate_limit_config=rate_limit_config,
                    use_mock_data=self.config.use_mock_data
                ),
                "leads": LeadManagementConnector(
                    auth_config=auth_config,
                    rate_limit_config=rate_limit_config,
                    use_mock_data=self.config.use_mock_data
                )
            }
            
            logger.info(
                f"Initialized {len(self.connectors)} sales data connectors",
                extra={
                    "use_mock_data": self.config.use_mock_data,
                    "tenant_id": self.tenant_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize connectors: {str(e)}")
            raise DataIngestionError(f"Connector initialization failed: {str(e)}")
    
    async def start_service(self) -> None:
        """Start the ingestion service and optional scheduler."""
        if self.is_running:
            logger.warning("Service is already running")
            return
            
        try:
            self.is_running = True
            
            # Connect all connectors
            await self._connect_all_connectors()
            
            # Start scheduler if enabled
            if self.config.enable_scheduling:
                await self._start_scheduler()
                
            log_system_event(
                logger, 
                "service_started", 
                "sales_data_ingestion",
                {"scheduling_enabled": self.config.enable_scheduling}
            )
            
        except Exception as e:
            self.is_running = False
            log_system_event(
                logger, 
                "service_start_failed", 
                "sales_data_ingestion",
                error=e
            )
            raise
    
    async def stop_service(self) -> None:
        """Stop the ingestion service and scheduler."""
        if not self.is_running:
            return
            
        try:
            self.is_running = False
            
            # Stop scheduler
            if self.scheduler_task and not self.scheduler_task.done():
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
                    
            # Disconnect all connectors
            await self._disconnect_all_connectors()
            
            log_system_event(
                logger, 
                "service_stopped", 
                "sales_data_ingestion"
            )
            
        except Exception as e:
            log_system_event(
                logger, 
                "service_stop_failed", 
                "sales_data_ingestion",
                error=e
            )
            raise
    
    async def ingest_all_data(
        self, 
        since: Optional[datetime] = None,
        limit_per_source: Optional[int] = None
    ) -> IngestionStats:
        """
        Ingest data from all configured sources with error handling and retry logic.
        
        Args:
            since: Only ingest data updated since this timestamp
            limit_per_source: Limit number of records per source
            
        Returns:
            IngestionStats with processing results
        """
        start_time = datetime.utcnow()
        stats = IngestionStats()
        
        try:
            logger.info(
                "Starting comprehensive sales data ingestion",
                extra={
                    "since": since.isoformat() if since else None,
                    "limit_per_source": limit_per_source,
                    "sources": list(self.connectors.keys())
                }
            )
            
            # Process all connectors concurrently with semaphore for rate limiting
            semaphore = asyncio.Semaphore(self.config.max_concurrent_connectors)
            tasks = []
            
            for source_name, connector in self.connectors.items():
                task = self._ingest_from_source_with_retry(
                    semaphore, source_name, connector, since, limit_per_source
                )
                tasks.append(task)
            
            # Wait for all ingestion tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            for i, result in enumerate(results):
                source_name = list(self.connectors.keys())[i]
                
                if isinstance(result, Exception):
                    error_msg = f"Failed to ingest from {source_name}: {str(result)}"
                    stats.errors.append(error_msg)
                    logger.error(error_msg)
                elif isinstance(result, DataIngestionResult):
                    stats.total_records_processed += result.records_processed
                    stats.total_records_failed += result.records_failed
                    stats.errors.extend(result.errors)
                    
                    # Update source-specific counters
                    if source_name == "deals":
                        stats.deals_processed = result.records_processed
                    elif source_name == "leads":
                        stats.leads_processed = result.records_processed
                    elif source_name == "activities":
                        stats.activities_processed = result.records_processed
                    elif source_name == "reps":
                        stats.reps_processed = result.records_processed
            
            # Calculate execution time
            stats.execution_time_seconds = (datetime.utcnow() - start_time).total_seconds()
            
            log_business_event(
                logger,
                "data_ingestion_completed",
                "sales_data",
                "batch",
                details={
                    "total_processed": stats.total_records_processed,
                    "total_failed": stats.total_records_failed,
                    "execution_time": stats.execution_time_seconds,
                    "sources": {
                        "deals": stats.deals_processed,
                        "leads": stats.leads_processed,
                        "activities": stats.activities_processed,
                        "reps": stats.reps_processed
                    }
                }
            )
            
            return stats
            
        except Exception as e:
            stats.execution_time_seconds = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Data ingestion failed: {str(e)}"
            stats.errors.append(error_msg)
            
            log_system_event(
                logger,
                "data_ingestion_failed",
                "sales_data_ingestion",
                error=e
            )
            
            return stats
    
    async def ingest_from_source(
        self,
        source_name: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> DataIngestionResult:
        """
        Ingest data from a specific source with error handling.
        
        Args:
            source_name: Name of the data source (deals, leads, activities, reps)
            since: Only ingest data updated since this timestamp
            limit: Maximum number of records to ingest
            
        Returns:
            DataIngestionResult with processing details
        """
        if source_name not in self.connectors:
            raise DataIngestionError(f"Unknown data source: {source_name}")
            
        connector = self.connectors[source_name]
        semaphore = asyncio.Semaphore(1)  # Single source, no concurrency limit needed
        
        return await self._ingest_from_source_with_retry(
            semaphore, source_name, connector, since, limit
        )
    
    async def _ingest_from_source_with_retry(
        self,
        semaphore: asyncio.Semaphore,
        source_name: str,
        connector: SalesDataConnector,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> DataIngestionResult:
        """
        Ingest data from a source with retry logic and error handling.
        """
        async with semaphore:
            start_time = datetime.utcnow()
            
            for attempt in range(self.config.max_retries + 1):
                try:
                    logger.info(
                        f"Ingesting data from {source_name} (attempt {attempt + 1})",
                        extra={
                            "source": source_name,
                            "attempt": attempt + 1,
                            "max_retries": self.config.max_retries
                        }
                    )
                    
                    # Ensure connection is valid
                    if not await connector.validate_connection():
                        await connector.connect()
                    
                    # Fetch raw data
                    raw_data = await connector.fetch_data(since=since, limit=limit)
                    
                    # Process and normalize data
                    processed_count, failed_count, errors = await self._process_raw_data(
                        source_name, raw_data
                    )
                    
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    return DataIngestionResult(
                        success=True,
                        records_processed=processed_count,
                        records_failed=failed_count,
                        errors=errors,
                        execution_time=execution_time,
                        source=source_name,
                        timestamp=datetime.utcnow()
                    )
                    
                except RetryableError as e:
                    if attempt < self.config.max_retries:
                        wait_time = self.config.retry_delay_seconds * (2 ** attempt)
                        logger.warning(
                            f"Retryable error in {source_name}, retrying in {wait_time}s: {str(e)}",
                            extra={
                                "source": source_name,
                                "attempt": attempt + 1,
                                "wait_time": wait_time
                            }
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {source_name}: {str(e)}")
                        raise DataIngestionError(f"Max retries exceeded: {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Non-retryable error in {source_name}: {str(e)}")
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    return DataIngestionResult(
                        success=False,
                        records_processed=0,
                        records_failed=0,
                        errors=[str(e)],
                        execution_time=execution_time,
                        source=source_name,
                        timestamp=datetime.utcnow()
                    )
            
            # Should not reach here, but handle gracefully
            raise DataIngestionError(f"Unexpected error in retry logic for {source_name}")
    
    async def _process_raw_data(
        self, 
        source_name: str, 
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        """
        Process and normalize raw data from a source.
        
        Returns:
            Tuple of (processed_count, failed_count, errors)
        """
        processed_count = 0
        failed_count = 0
        errors = []
        
        # Process data in batches
        for i in range(0, len(raw_data), self.config.batch_size):
            batch = raw_data[i:i + self.config.batch_size]
            
            for record in batch:
                try:
                    # Normalize based on source type
                    normalized_entity = await self._normalize_record(source_name, record)
                    
                    # Validate if enabled
                    if self.config.enable_validation:
                        validation_errors = await self._validate_record(source_name, normalized_entity)
                        if validation_errors:
                            errors.extend(validation_errors)
                            failed_count += 1
                            continue
                    
                    # TODO: Store normalized entity (will be implemented in future tasks)
                    # For now, just count as processed
                    processed_count += 1
                    
                except Exception as e:
                    error_msg = f"Failed to process {source_name} record {record.get('id', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    failed_count += 1
                    logger.warning(error_msg)
        
        return processed_count, failed_count, errors
    
    async def _normalize_record(self, source_name: str, record: Dict[str, Any]) -> Any:
        """Normalize a record based on its source type."""
        if source_name == "deals":
            return self.normalizer.normalize_deal(record)
        elif source_name == "leads":
            return self.normalizer.normalize_lead(record)
        elif source_name == "activities":
            return self.normalizer.normalize_activity(record)
        elif source_name == "reps":
            return self.normalizer.normalize_rep(record)
        else:
            raise DataIngestionError(f"Unknown source type for normalization: {source_name}")
    
    async def _validate_record(self, source_name: str, entity: Any) -> List[str]:
        """Validate a normalized entity."""
        if source_name == "deals" and isinstance(entity, Deal):
            return self.validator.validate_deal(entity)
        elif source_name == "leads" and isinstance(entity, Lead):
            return self.validator.validate_lead(entity)
        elif source_name == "activities" and isinstance(entity, SalesActivity):
            return self.validator.validate_activity(entity)
        elif source_name == "reps" and isinstance(entity, SalesRep):
            return self.validator.validate_rep(entity)
        else:
            return [f"Unknown entity type for validation: {type(entity)}"]
    
    async def _connect_all_connectors(self) -> None:
        """Connect all configured connectors."""
        connection_tasks = []
        
        for name, connector in self.connectors.items():
            task = self._connect_connector_with_retry(name, connector)
            connection_tasks.append(task)
        
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        failed_connections = []
        for i, result in enumerate(results):
            connector_name = list(self.connectors.keys())[i]
            if isinstance(result, Exception):
                failed_connections.append(connector_name)
                logger.error(f"Failed to connect {connector_name}: {str(result)}")
        
        if failed_connections:
            raise ExternalIntegrationError(
                f"Failed to connect to connectors: {failed_connections}"
            )
    
    async def _connect_connector_with_retry(
        self, 
        name: str, 
        connector: SalesDataConnector
    ) -> None:
        """Connect a single connector with retry logic."""
        for attempt in range(self.config.max_retries + 1):
            try:
                status = await connector.connect()
                if status == ConnectionStatus.CONNECTED:
                    logger.info(f"Successfully connected to {name}")
                    return
                else:
                    raise ExternalIntegrationError(f"Connection failed with status: {status}")
                    
            except Exception as e:
                if attempt < self.config.max_retries:
                    wait_time = self.config.retry_delay_seconds * (2 ** attempt)
                    logger.warning(f"Retrying connection to {name} in {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    raise
    
    async def _disconnect_all_connectors(self) -> None:
        """Disconnect all connectors."""
        disconnect_tasks = []
        
        for name, connector in self.connectors.items():
            task = connector.disconnect()
            disconnect_tasks.append(task)
        
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        logger.info("Disconnected all connectors")
    
    async def _start_scheduler(self) -> None:
        """Start the scheduled ingestion task."""
        if self.scheduler_task and not self.scheduler_task.done():
            logger.warning("Scheduler is already running")
            return
            
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            f"Started ingestion scheduler with {self.config.schedule_interval_minutes} minute intervals"
        )
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop for periodic data ingestion."""
        while self.is_running:
            try:
                # Calculate since timestamp for incremental ingestion
                since = datetime.utcnow() - timedelta(minutes=self.config.schedule_interval_minutes * 2)
                
                logger.info("Starting scheduled data ingestion")
                stats = await self.ingest_all_data(since=since)
                
                logger.info(
                    f"Scheduled ingestion completed: {stats.total_records_processed} processed, "
                    f"{stats.total_records_failed} failed"
                )
                
                # Wait for next interval
                await asyncio.sleep(self.config.schedule_interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def get_connector_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connectors."""
        status = {}
        
        for name, connector in self.connectors.items():
            try:
                is_connected = await connector.validate_connection()
                status[name] = {
                    "connected": is_connected,
                    "status": connector.connection_status.value,
                    "source_name": getattr(connector, 'source_name', name),
                    "use_mock_data": getattr(connector, 'use_mock_data', False)
                }
            except Exception as e:
                status[name] = {
                    "connected": False,
                    "status": "error",
                    "error": str(e)
                }
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the ingestion service."""
        connector_status = await self.get_connector_status()
        
        healthy_connectors = sum(1 for status in connector_status.values() if status.get("connected", False))
        total_connectors = len(connector_status)
        
        return {
            "service_running": self.is_running,
            "scheduler_enabled": self.config.enable_scheduling,
            "scheduler_running": self.scheduler_task is not None and not self.scheduler_task.done(),
            "connectors": {
                "total": total_connectors,
                "healthy": healthy_connectors,
                "status": connector_status
            },
            "config": {
                "use_mock_data": self.config.use_mock_data,
                "batch_size": self.config.batch_size,
                "max_retries": self.config.max_retries
            }
        }