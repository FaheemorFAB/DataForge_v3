"""
DataForge AI - Router Module
"""

from .patterns import (
    GREETING_PATTERNS,
    IDENTITY_PATTERNS,
    THANKS_PATTERNS,
    SCHEMA_EXPLORE_PATTERNS,
    CLEAN_KEYWORDS,
    AUTOML_KEYWORDS,
    PIPELINE_KEYWORDS,
    fuzzy_resolve_all_columns,
    fuzzy_resolve_column,
)
from .query_router import check_intercept_queries, route_agent_task, AgentSelectionDecision

__all__ = [
    "GREETING_PATTERNS",
    "IDENTITY_PATTERNS",
    "THANKS_PATTERNS",
    "SCHEMA_EXPLORE_PATTERNS",
    "CLEAN_KEYWORDS",
    "AUTOML_KEYWORDS",
    "PIPELINE_KEYWORDS",
    "fuzzy_resolve_all_columns",
    "fuzzy_resolve_column",
    "check_intercept_queries",
    "route_agent_task",
    "AgentSelectionDecision",
]
