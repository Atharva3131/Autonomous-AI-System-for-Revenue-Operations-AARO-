"""
Data ingestion layer for ABOA system.
"""

# Data ingestion module for ABOA system
from .service import SalesDataIngestionService, IngestionConfig, IngestionStats
from .connectors import (
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

__all__ = [
    "SalesDataIngestionService",
    "IngestionConfig", 
    "IngestionStats",
    "SalesDataConnector",
    "CRMDealConnector",
    "SalesActivityConnector", 
    "RepPerformanceConnector",
    "LeadManagementConnector",
    "SalesDataNormalizer",
    "SalesDataValidator",
    "AuthConfig",
    "RateLimitConfig",
    "DataIngestionResult",
    "ConnectionStatus"
]