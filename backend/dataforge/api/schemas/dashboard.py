"""
dataforge/api/schemas/dashboard.py
────────────────────────────────────
Pydantic request/response schemas for dashboard endpoints.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardStatsRequest(BaseModel):
    upload_id: Optional[int] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    chart_dim: Optional[str] = None
    chart_metric: Optional[str] = None


class DrilldownRequest(BaseModel):
    upload_id: Optional[int] = None
    chart_id: Optional[str] = None
    x_label: Any = None
    col_name: str


class ReportGenerateRequest(BaseModel):
    upload_id: Optional[int] = None


class ReportGenerateResponse(BaseModel):
    task_id: Optional[str] = None
    queued: bool


class ScheduleCreateRequest(BaseModel):
    upload_id: Optional[int] = None
    cron: str = "0 9 * * 1"
    email: Optional[str] = None


class MetricCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    formula: str = Field(..., min_length=1)
    description: Optional[str] = None
    category: str = "general"


class AlertsCheckRequest(BaseModel):
    upload_id: Optional[int] = None


class AssetLabelRequest(BaseModel):
    upload_id: int
    asset_type: str  # "dataset" | "model" | "report"
    label: str
