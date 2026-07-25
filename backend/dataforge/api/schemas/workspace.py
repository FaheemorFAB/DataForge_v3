"""
dataforge/api/schemas/workspace.py
────────────────────────────────────
Pydantic request/response schemas for workspace endpoints.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CleanRequest(BaseModel):
    upload_id: Optional[int] = None


class EDARequest(BaseModel):
    upload_id: Optional[int] = None
    minimal: bool = True
    sample_n: int = Field(default=5000, ge=100, le=50_000)


class QueryRequest(BaseModel):
    upload_id: Optional[int] = None
    question: Optional[str] = None
    query: Optional[str] = None
    session_id: Optional[str] = None


class TransformRequest(BaseModel):
    upload_id: Optional[int] = None
    operations: List[Dict[str, Any]] = Field(default_factory=list)


class SyncSheetsRequest(BaseModel):
    upload_id: Optional[int] = None


class AiConsentRequest(BaseModel):
    upload_id: Optional[int] = None
    consent: bool


class ChatSessionRequest(BaseModel):
    upload_id: Optional[int] = None
    name: str = Field(default="New Chat", max_length=100)


class CustomChartRequest(BaseModel):
    upload_id: Optional[int] = None
    id: Optional[str] = None
    chart_type: str
    x_col: str
    y_col: Optional[str] = None
    agg_type: str = "none"
    title: Optional[str] = None
    is_area: bool = False
    duplicate_from_id: Optional[str] = None


class CustomChartDeleteRequest(BaseModel):
    upload_id: Optional[int] = None
    chart_id: str


class PreviewParams(BaseModel):
    upload_id: Optional[int] = None
    limit: int = Field(default=500, ge=50, le=5000)
    clean: bool = False
    columns: Optional[str] = None
