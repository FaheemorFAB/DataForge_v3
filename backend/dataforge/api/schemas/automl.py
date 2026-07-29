"""
dataforge/api/schemas/automl.py
────────────────────────────────
Pydantic request/response schemas for AutoML endpoints.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class AutoMLDetectTaskRequest(BaseModel):
    upload_id: Optional[int] = None
    target_col: str = ""


class AutoMLTrainRequest(BaseModel):
    upload_id: Optional[int] = None
    target_col: str = Field(..., min_length=1)
    task_choice: str = "auto-detect"
    time_budget: int = Field(default=60, ge=10, le=900)
    test_size: float = Field(default=20.0, ge=10.0, le=40.0)


class AutoMLTrainResponse(BaseModel):
    task_id: Optional[str] = None
    queued: bool
    upload_id: Optional[int] = None


class InsightsRunRequest(BaseModel):
    upload_id: Optional[int] = None
    top_n: int = Field(default=6, ge=1, le=20)


class InsightsRunResponse(BaseModel):
    task_id: Optional[str] = None
    queued: bool


class RootCauseRequest(BaseModel):
    upload_id: Optional[int] = None
    metric: Optional[str] = None
    dimensions: Optional[list[str]] = None
    date_col: Optional[str] = None
    top_n: int = Field(default=6, ge=1, le=20)


class ForecastRequest(BaseModel):
    upload_id: Optional[int] = None
    date_col: Optional[str] = None
    metric_col: Optional[str] = None
    horizon: Optional[int] = Field(default=None, ge=1, le=365)
    freq_override: Optional[str] = None
    include_decomposition: bool = True

