"""
Observability and metrics system for ABOA.

This module provides comprehensive sales activity logging, revenue metrics collection,
and system health monitoring capabilities for the autonomous revenue operations agent.
"""

from .activity_logger import (
    SalesActivityLogger,
    ActivityLogEntry,
    DecisionLogEntry,
    ActionLogEntry,
    get_activity_logger,
    log_sales_activity,
    log_revenue_decision,
    log_sales_action
)

from .metrics_collector import (
    RevenueMetricsCollector,
    MetricSnapshot,
    get_metrics_collector
)

from .api import router as observability_router

__all__ = [
    # Activity Logger
    "SalesActivityLogger",
    "ActivityLogEntry", 
    "DecisionLogEntry",
    "ActionLogEntry",
    "get_activity_logger",
    "log_sales_activity",
    "log_revenue_decision", 
    "log_sales_action",
    
    # Metrics Collector
    "RevenueMetricsCollector",
    "MetricSnapshot",
    "get_metrics_collector",
    
    # API Router
    "observability_router"
]