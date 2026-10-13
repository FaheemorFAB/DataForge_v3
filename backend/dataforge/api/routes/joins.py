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
    ExecuteCustomSqlRequest,
    InferredRelationship,
    JoinMaterializeRequest,
    JoinPreviewRequest,
    MaterializeCustomSqlRequest,
    PresetLoadRequest,
    TableSummary,
    TablesListResponse,
)
from dataforge.api.storage.manager import STORE_DIR, exists, load, save
from dataforge.api.utils.json import safe_jsonable
from dataforge.join_engine import DuckDBJoinEngine, _sanitize_table_name

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
            try:
                content_str = raw.decode("utf-8")
                parsed = pyjson.loads(content_str)
                if isinstance(parsed, list):
                    df = pd.json_normalize(parsed)
                elif isinstance(parsed, dict):
                    for key in ("data", "items", "records", "rows", "results"):
                        if key in parsed and isinstance(parsed[key], list):
                            df = pd.json_normalize(parsed[key])
                            break
                    else:
                        df = pd.json_normalize([parsed])
                else:
                    raise ValueError("JSON must be a list of records or dictionary")
            except Exception:
                df = pd.read_json(io.BytesIO(raw), lines=True)
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
        raise HTTPException(status_code=400, detail=f"Join failed: {exc}")


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
        raise HTTPException(status_code=400, detail=f"Materialization failed: {exc}")


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
