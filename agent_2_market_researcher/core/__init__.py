"""
Core modules for Agent 2: Target Market Researcher
"""

from .schemas import (
    BusinessModelType,
    NeedSignal,
    DiscoveredProspect,
    ClientBrief,
    IdealCustomerProfile,
    BuyerPersona,
    MarketSegment,
    CompetitorInsight,
    TargetMarketDossier,
)
from .query_planner import QueryPlanner, QueryType, TargetedQuery
from .exporters import export_sales_lead_tracker_csv, export_marketing_handoff_json

__all__ = [
    "BusinessModelType",
    "NeedSignal",
    "DiscoveredProspect",
    "ClientBrief",
    "IdealCustomerProfile",
    "BuyerPersona",
    "MarketSegment",
    "CompetitorInsight",
    "TargetMarketDossier",
    "QueryPlanner",
    "QueryType",
    "TargetedQuery",
    "export_sales_lead_tracker_csv",
    "export_marketing_handoff_json",
]
