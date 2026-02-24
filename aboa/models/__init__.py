"""
Data models for the Autonomous Business Operations Agent (ABOA).

This module contains all the core data models used throughout the ABOA system,
including revenue operations entities, enums, and validation logic.
"""

from .enums import (
    ActivityType,
    ApprovalStatus,
    DecisionClass,
    DealStage,
    ExecutionStatus,
    LeadStatus,
    RiskType,
    SalesActionType,
    Severity,
)
from .revenue_entities import (
    ContactInfo,
    Deal,
    Lead,
    PipelineRisk,
    RevenueContext,
    RevenueDecisionLog,
    RevenueImpact,
    SalesAction,
    SalesActivity,
    SalesRep,
)

__all__ = [
    # Enums
    "ActivityType",
    "ApprovalStatus",
    "DecisionClass",
    "DealStage", 
    "ExecutionStatus",
    "LeadStatus",
    "RiskType",
    "SalesActionType",
    "Severity",
    # Revenue Entities
    "ContactInfo",
    "Deal",
    "Lead",
    "PipelineRisk",
    "RevenueContext",
    "RevenueDecisionLog",
    "RevenueImpact",
    "SalesAction",
    "SalesActivity",
    "SalesRep",
]