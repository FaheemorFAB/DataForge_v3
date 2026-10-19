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
    sheet_name: Optional[str] = Field(default=None, description="Optional worksheet/tab name")
    gid: Optional[str] = Field(default=None, description="Optional worksheet gid")


class ExcelOnlineUploadRequest(BaseModel):
    url: str = Field(..., min_length=5, description="Microsoft Excel Online, OneDrive, or SharePoint URL")
    sheet_name: Optional[str] = Field(default=None, description="Optional sheet/worksheet name or index")
    dataset_name: Optional[str] = Field(default=None, description="Optional custom dataset title")


class JSONUrlUploadRequest(BaseModel):
    url: str = Field(..., min_length=5, description="JSON or REST API endpoint URL")
    headers: Optional[dict[str, str]] = None
    root_key: Optional[str] = None
    dataset_name: Optional[str] = None


class DBTestConnectionRequest(BaseModel):
    connection_string: str = Field(..., min_length=5, description="SQLAlchemy database connection string")


class DBListTablesRequest(BaseModel):
    connection_string: str = Field(..., min_length=5)
    db_schema: Optional[str] = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


class DBPreviewRequest(BaseModel):
    connection_string: str = Field(..., min_length=5)
    table_name: Optional[str] = None
    query: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=1000)


class DBIngestRequest(BaseModel):
    connection_string: str = Field(..., min_length=5)
    table_name: Optional[str] = None
    query: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1, le=2000000)
    dataset_name: Optional[str] = None


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
    upload_id: str
    profile: ProfileResponse


class DuplicateCheckResponse(BaseModel):
    duplicate: bool
    upload_id: Optional[str] = None
    filename: Optional[str] = None
    rows: Optional[int] = None
    cols: Optional[int] = None
    numeric: Optional[int] = None
    missing_pct: Optional[float] = None
    time_ago: Optional[str] = None
    has_clean: Optional[bool] = None
