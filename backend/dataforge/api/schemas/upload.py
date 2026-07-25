"""
dataforge/api/schemas/upload.py
────────────────────────────────
Pydantic request/response schemas for upload endpoints.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class SheetsUploadRequest(BaseModel):
    url: str = Field(..., min_length=10, description="Google Sheets URL")


class DuplicateCheckRequest(BaseModel):
    filename: str = Field(..., min_length=1)


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_pct: float
    quality: float


class ProfileResponse(BaseModel):
    filename: str
    rows: int
    cols: int
    numeric: int
    missing: int
    missing_pct: float
    columns: List[ColumnInfo]


class UploadResponse(BaseModel):
    ok: bool
    upload_id: int
    profile: ProfileResponse


class DuplicateCheckResponse(BaseModel):
    duplicate: bool
    upload_id: Optional[int] = None
    filename: Optional[str] = None
    rows: Optional[int] = None
    cols: Optional[int] = None
    numeric: Optional[int] = None
    missing_pct: Optional[float] = None
    time_ago: Optional[str] = None
    has_clean: Optional[bool] = None
