"""
DataForge AI Package
Autonomous Multi-Agent Architecture powered by the Google GenAI SDK.
"""

from .client import get_genai_client, is_available
from .schemas import AnalysisResult, QueryResponse, AgentAction

__all__ = [
    "get_genai_client",
    "is_available",
    "AnalysisResult",
    "QueryResponse",
    "AgentAction",
]
