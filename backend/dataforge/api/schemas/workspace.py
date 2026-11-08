"""
dataforge/api/schemas/workspace.py
────────────────────────────────────
Pydantic request/response schemas for workspace endpoints.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CleanRequest(BaseModel):
    upload_id: Optional[str] = None
    expected_version_id: Optional[str] = Field(default=None, description="OCC version token for compare-and-swap")
    preview_only: bool = Field(default=False, description="If True, preview the cleaning operations without mutating dataset state or committing a snapshot")
    share_token: Optional[str] = Field(default=None, description="Share token for link-accessed datasets")


class EDARequest(BaseModel):
    upload_id: Optional[str] = None
    minimal: bool = False
    sample_n: Optional[int] = Field(default=None, description="Max rows to sample, or 0/None for full dataset")
    share_token: Optional[str] = None


class QueryRequest(BaseModel):
    upload_id: Optional[str] = None
    question: Optional[str] = None
    query: Optional[str] = None
    session_id: Optional[str] = None


class TransformRequest(BaseModel):
    upload_id: Optional[str] = None
    operations: List[Dict[str, Any]] = Field(default_factory=list)
    expected_version_id: Optional[str] = Field(default=None, description="OCC version token for compare-and-swap")


class SyncSheetsRequest(BaseModel):
    upload_id: Optional[str] = None


class AiConsentRequest(BaseModel):
    upload_id: Optional[str] = None
    consent: bool


class ChatSessionRequest(BaseModel):
    upload_id: Optional[str] = None
    name: str = Field(default="New Chat", max_length=100)


class CustomChartRequest(BaseModel):
    upload_id: Optional[str] = None
    id: Optional[str] = None
    chart_type: str
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    agg_type: str = "none"
    title: Optional[str] = None
    is_area: bool = False
    duplicate_from_id: Optional[str] = None
    top_n: Optional[int] = 10


class CustomChartDeleteRequest(BaseModel):
    upload_id: Optional[str] = None
    chart_id: str


class PreviewParams(BaseModel):
    upload_id: Optional[str] = None
    limit: int = Field(default=500, ge=50, le=5000)
    clean: bool = False
    columns: Optional[str] = None


class GranularCleanRule(BaseModel):
    columns: Optional[List[str]] = Field(default_factory=list)
    column: Optional[str] = None
    action_type: str
    impute_method: Optional[str] = "median"
    fill_value: Optional[Any] = None
    trim_percent: Optional[float] = 0.1
    interp_method: Optional[str] = "linear"
    interp_order: Optional[int] = 2
    knn_neighbors: Optional[int] = 5
    knn_weights: Optional[str] = "uniform"
    mice_max_iter: Optional[int] = 10
    fill_limit: Optional[int] = None
    outlier_method: Optional[str] = "iqr"
    multiplier_k: Optional[float] = 1.5
    outlier_action: Optional[str] = "clip"
    zscore_threshold: Optional[float] = 3.0
    zscore_method: Optional[str] = "zscore"
    iso_contamination: Optional[float] = 0.05
    iso_estimators: Optional[int] = 100
    lower_percentile: Optional[float] = 0.01
    upper_percentile: Optional[float] = 0.99
    scaler_method: Optional[str] = "robust"
    quantile_low: Optional[float] = 25.0
    quantile_high: Optional[float] = 75.0
    scale_min: Optional[float] = 0.0
    scale_max: Optional[float] = 1.0
    encode_method: Optional[str] = "onehot"
    drop_first: Optional[bool] = False
    min_freq: Optional[float] = 0.0
    text_case: Optional[str] = "trim"
    regex_pattern: Optional[str] = None
    regex_replacement: Optional[str] = ""
    pii_mask: Optional[bool] = False
    pii_entities: Optional[List[str]] = Field(default_factory=lambda: ["email", "phone"])
    fuzzy_dedupe: Optional[bool] = False
    fuzzy_threshold: Optional[float] = 0.85
    cast_type: Optional[str] = "float"


class GranularCleanRequest(BaseModel):
    upload_id: str
    rules: List[GranularCleanRule] = Field(default_factory=list)


class RuleDiffRequest(BaseModel):
    upload_id: str
    rule: Dict[str, Any] = Field(default_factory=dict)
    share_token: Optional[str] = None


class ShareInviteRequest(BaseModel):
    email: str = Field(..., description="Email address of the collaborator")
    role: str = Field(default="Viewer", description="Assigned role: Viewer, Analyst, Editor, Admin")


class ShareGeneralRequest(BaseModel):
    general_access: str = Field(..., description="Access mode: restricted or anyone_with_link")
    link_role: str = Field(default="Viewer", description="Role for anyone with link: Viewer, Analyst, Editor")


class ShareRemoveRequest(BaseModel):
    email: str = Field(..., description="Email of collaborator to remove")

