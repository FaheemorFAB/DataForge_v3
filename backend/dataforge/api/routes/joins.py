"""
dataforge/api/routes/joins.py
─────────────────────────────
REST endpoints for multi-table relational modeling, schema relationship inference,
DuckDB pushdown preview, and workspace materialization.
"""

from __future__ import annotations

import io
import json as pyjson
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from dataforge.api.deps import CurrentUser, require_upload_access
from dataforge.api.schemas.joins import (
    ColumnSummary,
    DrillDownRequest,
    ExecuteCustomSqlRequest,
    InferredRelationship,
    IntegrityAuditRequest,
    JoinMaterializeRequest,
    JoinPreviewRequest,
    MaterializeCustomSqlRequest,
    PresetLoadRequest,
    SheetsImportRequest,
    SheetsInspectRequest,
    TableSummary,
    TablesListResponse,
)
from dataforge.api.storage.manager import STORE_DIR, exists, load, save
from dataforge.api.utils.json import parse_json_to_dataframe, safe_jsonable
from dataforge.join_engine import DuckDBJoinEngine, _sanitize_table_name
from dataforge.sheets_inspector import WorkbookInspector

log = logging.getLogger(__name__)
router = APIRouter(prefix="/joins", tags=["joins"])


def _build_tables_response(upload_id: str) -> Dict[str, Any]:
    """Helper to assemble TableSummary list and inferred relationships."""
    tables = DuckDBJoinEngine.get_workspace_tables(upload_id)
    table_summaries: List[Dict[str, Any]] = []

    profile = load(upload_id, "profile") or {}
    raw_filename = profile.get("filename", "primary")
    primary_name = _sanitize_table_name(Path(raw_filename).stem)

    for name, df in tables.items():
        is_primary = (name == primary_name) or (len(tables) == 1)
        col_summaries: List[Dict[str, Any]] = []

        for col in df.columns:
            series = df[col]
            # Grab top 3 non-null sample values safely formatted
            non_null = series.dropna()
            samples = [
                str(v) if not pd.isna(v) else None
                for v in non_null.head(3).tolist()
            ]

            col_summaries.append({
                "name": str(col),
                "dtype": str(series.dtype),
                "null_count": int(series.isna().sum()),
                "unique_count": int(series.nunique()),
                "sample_values": samples,
            })

        table_summaries.append({
            "name": name,
            "is_primary": is_primary,
            "row_count": len(df),
            "col_count": df.shape[1],
            "columns": col_summaries,
        })

    # Infer candidate relations
    inferred = DuckDBJoinEngine.infer_relationships(tables)

    return {
        "ok": True,
        "tables": table_summaries,
        "relationships": inferred,
    }


@router.get("/tables", response_model=TablesListResponse, summary="List all workspace tables and inferred relations")
async def list_workspace_tables(
    current_user: CurrentUser,
    upload_id: str = Query(..., description="Workspace upload ID"),
):
    """Returns primary dataset and all registered secondary tables with inferred FK links."""
    await require_upload_access(upload_id, current_user)
    resp = _build_tables_response(upload_id)
    return JSONResponse(content=safe_jsonable(resp))


@router.post("/tables/upload", summary="Upload and register a secondary table into workspace")
async def upload_secondary_table(
    current_user: CurrentUser,
    upload_id: str = Form(...),
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None),
):
    """Uploads CSV, Excel, Parquet, or JSON as a secondary relational table."""
    await require_upload_access(upload_id, current_user)

    filename = file.filename or "table.csv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"
    if ext not in {"csv", "xls", "xlsx", "parquet", "json", "jsonl", "ndjson"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    raw = await file.read()
    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100 MB)")

    try:
        if ext == "csv":
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    df = pd.read_csv(io.BytesIO(raw), encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode CSV with supported encodings")
        elif ext in ("xls", "xlsx"):
            df = pd.read_excel(io.BytesIO(raw))
        elif ext == "parquet":
            df = pd.read_parquet(io.BytesIO(raw))
        elif ext in ("json", "jsonl", "ndjson"):
            df = parse_json_to_dataframe(raw)
        else:
            raise ValueError(f"Unsupported format: {ext}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded table is empty")

    effective_name = table_name or Path(filename).stem
    saved_name = DuckDBJoinEngine.save_workspace_table(upload_id, effective_name, df)

    resp = _build_tables_response(upload_id)
    resp["message"] = f"Table '{saved_name}' ({len(df):,} rows) added successfully."
    return JSONResponse(content=safe_jsonable(resp))


@router.delete("/tables/{table_name}", summary="Delete a secondary table from workspace")
async def delete_secondary_table(
    table_name: str,
    current_user: CurrentUser,
    upload_id: str = Query(...),
):
    """Removes a secondary table from disk."""
    await require_upload_access(upload_id, current_user)
    deleted = DuckDBJoinEngine.delete_workspace_table(upload_id, table_name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found or cannot delete primary table.")

    resp = _build_tables_response(upload_id)
    resp["message"] = f"Table '{table_name}' deleted."
    return JSONResponse(content=safe_jsonable(resp))


@router.post("/preview", summary="Preview DuckDB pushdown join with live SQL generation")
async def preview_join(
    req: JoinPreviewRequest,
    current_user: CurrentUser,
):
    """Executes an in-memory DuckDB pushdown join and returns preview rows + SQL + timing."""
    await require_upload_access(req.upload_id, current_user)

    joins_data = [j.dict() for j in req.joins]
    filters_data = [f.dict() for f in req.filters] if req.filters else None
    rollups_data = [r.dict() for r in req.rollups] if req.rollups else None

    try:
        preview = DuckDBJoinEngine.preview_join(
            upload_id=req.upload_id,
            base_table=req.base_table,
            joins=joins_data,
            selected_columns=req.selected_columns,
            filters=filters_data,
            rollups=rollups_data,
            custom_sql=req.custom_sql,
            limit=req.limit or 50,
        )
        return JSONResponse(content=safe_jsonable(preview))
    except Exception as exc:
        log.exception("DuckDB preview join failed: %s", exc)
        err_msg = str(exc)
        if "Conversion Error" in err_msg or "ConversionException" in err_msg:
            clean_err = err_msg.split("LINE")[0].strip()
            detail = f"Join Data Type Mismatch: {clean_err}. Ensure selected join columns share compatible data types (e.g., both numbers or both text)."
        else:
            detail = f"Join failed: {err_msg.split('LINE')[0].strip()}"
        raise HTTPException(status_code=400, detail=detail)


@router.post("/materialize", summary="Commit and materialize joined dataset into active workspace")
async def materialize_join(
    req: JoinMaterializeRequest,
    current_user: CurrentUser,
):
    """Executes full DuckDB pushdown join and commits result to active workspace dataset."""
    await require_upload_access(req.upload_id, current_user)

    joins_data = [j.dict() for j in req.joins]
    filters_data = [f.dict() for f in req.filters] if req.filters else None
    rollups_data = [r.dict() for r in req.rollups] if req.rollups else None

    try:
        result = DuckDBJoinEngine.materialize_join(
            upload_id=req.upload_id,
            base_table=req.base_table,
            joins=joins_data,
            selected_columns=req.selected_columns,
            filters=filters_data,
            rollups=rollups_data,
            custom_sql=req.custom_sql,
            output_dataset_name=req.output_dataset_name,
        )
        return JSONResponse(content=safe_jsonable(result))
    except Exception as exc:
        log.exception("DuckDB materialize join failed: %s", exc)
        err_msg = str(exc)
        if "Conversion Error" in err_msg or "ConversionException" in err_msg:
            clean_err = err_msg.split("LINE")[0].strip()
            detail = f"Materialization Data Type Mismatch: {clean_err}. Ensure selected join columns share compatible data types."
        else:
            detail = f"Materialization failed: {err_msg.split('LINE')[0].strip()}"
        raise HTTPException(status_code=400, detail=detail)


@router.post("/sql/preview", summary="Preview custom DuckDB SQL query against workspace tables")
async def preview_custom_sql(
    req: ExecuteCustomSqlRequest,
    current_user: CurrentUser,
):
    """Directly executes custom SQL in memory against workspace tables."""
    await require_upload_access(req.upload_id, current_user)
    try:
        preview = DuckDBJoinEngine.execute_custom_sql(
            upload_id=req.upload_id,
            sql=req.sql,
            limit=req.limit or 50,
        )
        return JSONResponse(content=safe_jsonable(preview))
    except Exception as exc:
        log.exception("DuckDB custom SQL execution failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"SQL execution error: {exc}")


@router.post("/sql/materialize", summary="Commit custom DuckDB SQL results into workspace dataset")
async def materialize_custom_sql(
    req: MaterializeCustomSqlRequest,
    current_user: CurrentUser,
):
    """Directly executes custom SQL and commits the result to active workspace dataset."""
    await require_upload_access(req.upload_id, current_user)
    try:
        result = DuckDBJoinEngine.materialize_custom_sql(
            upload_id=req.upload_id,
            sql=req.sql,
            output_dataset_name=req.output_dataset_name,
        )
        return JSONResponse(content=safe_jsonable(result))
    except Exception as exc:
        log.exception("DuckDB custom SQL materialization failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Materialization error: {exc}")


@router.post("/preset", summary="Load 1-click multi-table relational schema preset")
async def load_preset(
    req: PresetLoadRequest,
    current_user: CurrentUser,
):
    """Instantly injects an E-Commerce, SaaS, or Healthcare relational database schema."""
    try:
        await require_upload_access(req.upload_id, current_user)
    except HTTPException as e:
        if e.status_code != 404:
            raise

    try:
        preset_res = DuckDBJoinEngine.load_relational_preset(req.upload_id, req.preset)
        resp = _build_tables_response(req.upload_id)
        resp["preset"] = preset_res["preset"]
        resp["message"] = f"Relational preset '{req.preset}' loaded with {len(preset_res['created_tables'])} tables."
        return JSONResponse(content=safe_jsonable(resp))
    except Exception as exc:
        log.exception("Failed to load preset %s: %s", req.preset, exc)
        raise HTTPException(status_code=400, detail=f"Preset load failed: {exc}")


@router.get("/sheets/workspace-origin", summary="Detect companion sheets from original workspace workbook/link")
async def detect_workspace_origin_sheets(
    current_user: CurrentUser,
    upload_id: str = Query(...),
):
    """Detects whether active workspace came from a multi-sheet file/link and has unimported sheets."""
    await require_upload_access(upload_id, current_user)
    origin_info = WorkbookInspector.detect_workspace_origin(upload_id)
    return JSONResponse(content=safe_jsonable({"ok": True, **origin_info}))


@router.post("/sheets/inspect-file", summary="Inspect an uploaded Excel file for multiple worksheets")
async def inspect_sheets_file(
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """Reads workbook structure of uploaded file without full ingestion."""
    raw = await file.read()
    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100 MB)")
    res = WorkbookInspector.inspect_excel_bytes(raw, file.filename or "workbook.xlsx")
    return JSONResponse(content=safe_jsonable(res))


@router.post("/sheets/inspect-url", summary="Inspect Google Sheets or Excel Online URL for worksheet tabs")
async def inspect_sheets_url(
    req: SheetsInspectRequest,
    current_user: CurrentUser,
):
    """Inspects a public Google Sheets or Microsoft 365 / OneDrive URL for available worksheets."""
    url = req.url.strip()
    if req.source_type == "google_sheets" or "docs.google.com" in url:
        res = WorkbookInspector.inspect_google_sheets(url)
    else:
        res = WorkbookInspector.inspect_excel_online(url)
    return JSONResponse(content=safe_jsonable(res))


@router.post("/sheets/import", summary="Batch import selected sheets into workspace relational tables")
async def import_sheets(
    req: SheetsImportRequest,
    current_user: CurrentUser,
):
    """Imports selected worksheets into DuckDB parquet tables in the workspace."""
    await require_upload_access(req.upload_id, current_user)
    try:
        sheets_data = [s.dict() for s in req.selected_sheets]
        imported = WorkbookInspector.import_selected_sheets(
            upload_id=req.upload_id,
            source_url=req.source_url,
            source_type=req.source_type,
            selected_sheets=sheets_data,
        )
        resp = _build_tables_response(req.upload_id)
        resp["imported_sheets"] = imported
        resp["message"] = f"Successfully imported {len(imported)} worksheet(s) into workspace tables."
        return JSONResponse(content=safe_jsonable(resp))
    except Exception as exc:
        log.exception("Multi-sheet import failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Import failed: {exc}")


@router.post("/analytics/integrity-audit", summary="Deep referential integrity and orphan audit between two tables")
async def audit_integrity(
    req: IntegrityAuditRequest,
    current_user: CurrentUser,
):
    """Analyzes foreign key completeness, orphan counts, uniqueness, cardinality, and fan-out risk."""
    await require_upload_access(req.upload_id, current_user)
    try:
        audit = DuckDBJoinEngine.audit_referential_integrity(
            upload_id=req.upload_id,
            left_table=req.left_table,
            left_column=req.left_column,
            right_table=req.right_table,
            right_column=req.right_column,
        )
        return JSONResponse(content=safe_jsonable(audit))
    except Exception as exc:
        log.exception("Integrity audit failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Audit failed: {exc}")


@router.post("/analytics/drill-down", summary="Interactive drill-down query for parent-child records")
async def drill_down_records(
    req: DrillDownRequest,
    current_user: CurrentUser,
):
    """Instantly retrieves child records corresponding to a selected parent row."""
    await require_upload_access(req.upload_id, current_user)
    try:
        drill = DuckDBJoinEngine.drill_down_query(
            upload_id=req.upload_id,
            parent_table=req.parent_table,
            child_table=req.child_table,
            parent_column=req.parent_column,
            child_column=req.child_column,
            parent_value=req.parent_value,
            limit=req.limit or 100,
        )
        return JSONResponse(content=safe_jsonable(drill))
    except Exception as exc:
        log.exception("Drill down failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Drill down failed: {exc}")

