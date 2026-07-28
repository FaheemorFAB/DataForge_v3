"""
dataforge/api/routes/upload.py
────────────────────────────────
Upload routes: CSV/Excel file upload, Google Sheets, duplicate check.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from dataforge.api.config import get_settings
from dataforge.api.deps import CurrentUser, get_job_manager_dep
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.upload import DuplicateCheckRequest
from dataforge.api.services.upload import upload_service
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import User

log = logging.getLogger(__name__)
router = APIRouter(tags=["upload"])
settings = get_settings()


@router.post("/upload", summary="Upload a CSV or Excel file")
async def api_upload(
    current_user: CurrentUser,
    job_manager: JobManager = Depends(get_job_manager_dep),
    file: UploadFile = File(...),
    upload_id_override: Optional[int] = Form(default=None),
):
    """Accept a file upload, profile it, and persist to disk + Supabase."""
    filename = file.filename or "upload.csv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"

    if ext not in {"csv", "xls", "xlsx", "parquet"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    raw = await file.read()
    if len(raw) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB} MB)",
        )

    try:
        if ext == "csv":
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    df = pd.read_csv(io.BytesIO(raw), encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode CSV with any supported encoding")
        elif ext in ("xls", "xlsx"):
            df = pd.read_excel(io.BytesIO(raw))
        elif ext == "parquet":
            df = pd.read_parquet(io.BytesIO(raw))
        else:
            raise ValueError(f"Unsupported extension: {ext}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(df) > 2_000_000:
        raise HTTPException(status_code=400, detail="Dataset exceeds 2M rows limit")

    result = upload_service.process_dataframe(df, filename, "csv", current_user)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": result["upload_id"],
        "profile": result["profile"],
    }))


@router.post("/upload/check-duplicate", summary="Check if a filename was previously uploaded")
async def api_check_duplicate(
    body: DuplicateCheckRequest,
    current_user: CurrentUser,
):
    result = upload_service.check_duplicate(current_user.id, body.filename)
    if result:
        return JSONResponse(content=safe_jsonable(result))
    return {"duplicate": False}


@router.post("/upload/sheets", summary="Load data from a public Google Sheets URL")
async def api_upload_sheets(
    current_user: CurrentUser,
    url: str = Form(...),
):
    """Fetch a public Google Sheet and load it as a DataFrame."""
    import re

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Google Sheets URL")
    sheet_id = match.group(1)

    try:
        from dataforge.sheets_connector import SheetsConnector
        df = SheetsConnector().load_public(sheet_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load Google Sheet: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Google Sheet is empty")

    filename = f"sheet_{sheet_id[:8]}.csv"
    source_config = {"sheet_id": sheet_id, "url": url}
    result = upload_service.process_dataframe(df, filename, "sheets", current_user, source_config)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": result["upload_id"],
        "profile": result["profile"],
    }))
