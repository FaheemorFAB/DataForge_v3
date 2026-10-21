"""
dataforge/api/schemas/models.py
───────────────────────────────
Pydantic schemas for Model Registry, Live Online Prediction, and Container Deployment.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RegisterModelRequest(BaseModel):
    org_id: str = Field("default", description="Organization ID owning this model")
    model_name: str = Field(..., min_length=2, max_length=120)
    task_type: str = Field(..., description="classification or regression")
    algorithm: str = Field(..., description="e.g. LightGBM, XGBoost, CatBoost, Random Forest")
    target_column: str = Field(...)
    features: List[str] = Field(..., description="List of expected feature column names")
    metrics: Dict[str, float] = Field(..., description="Validation metrics: roc_auc, f1_score, r2, rmse, etc.")
    upload_id: Optional[str] = None
    version: Optional[str] = "v1.0.0"
    summary: Optional[str] = None


class UpdateModelStatusRequest(BaseModel):
    status: str = Field(..., description="Status promotion: production, staging, archived")


class PredictRequest(BaseModel):
    features: Dict[str, Any] = Field(..., description="Key-value mapping of feature inputs")


class BatchPredictRequest(BaseModel):
    records: List[Dict[str, Any]] = Field(..., description="List of feature records")


class ApplyToWorkspaceRequest(BaseModel):
    upload_id: str = Field(..., description="Target dataset upload ID in workspace")
    target_dataset: Optional[str] = "clean"
    pred_col_name: Optional[str] = None


class PredictionResultResponse(BaseModel):
    ok: bool = True
    model_id: str
    model_name: str
    algorithm: str
    task_type: str
    prediction: Any
    confidence: Optional[float] = None
    predicted_label: Optional[str] = None
    probabilities: Optional[Dict[str, float]] = None
    confidence_interval: Optional[List[float]] = None
    latency_ms: float
    timestamp: str


class ModelRecordResponse(BaseModel):
    id: str
    org_id: str
    model_name: str
    task_type: str
    algorithm: str
    target_column: str
    features: List[str]
    metrics: Dict[str, float]
    version: str
    status: str
    created_by: str
    created_at: str
    summary: Optional[str] = None
    upload_id: Optional[str] = None
