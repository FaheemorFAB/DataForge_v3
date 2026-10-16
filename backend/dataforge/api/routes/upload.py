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
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.upload import (
    DuplicateCheckRequest,
    SheetsUploadRequest,
    ExcelOnlineUploadRequest,
    JSONUrlUploadRequest,
    DBTestConnectionRequest,
    DBListTablesRequest,
    DBPreviewRequest,
    DBIngestRequest,
)
from dataforge.api.services.upload import upload_service
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import User

log = logging.getLogger(__name__)
router = APIRouter(tags=["upload"])
settings = get_settings()


@router.post("/upload", summary="Upload a CSV, Excel, Parquet or JSON file")
async def api_upload(
    current_user: CurrentUser,
    job_manager: JobManager = Depends(get_job_manager_dep),
    file: UploadFile = File(...),
    upload_id_override: Optional[int] = Form(default=None),
):
    """Accept a file upload, profile it, and persist to disk + Supabase."""
    filename = file.filename or "upload.csv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"

    if ext not in {"csv", "xls", "xlsx", "parquet", "json", "jsonl", "ndjson"}:
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
        elif ext in ("json", "jsonl", "ndjson"):
            import json as pyjson
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
                    raise ValueError("JSON must be a list of records or dictionary object")
            except Exception:
                df = pd.read_json(io.BytesIO(raw), lines=True)
        else:
            raise ValueError(f"Unsupported extension: {ext}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    from dataforge.api.services.entitlements import EntitlementService
    size_mb = len(raw) / (1024 * 1024)
    allowed_storage, storage_reason = EntitlementService.check_entitlement(current_user.id, "storage_mb", size_mb)
    if not allowed_storage:
        raise HTTPException(status_code=402, detail=storage_reason)

    allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
    if not allowed_rows:
        raise HTTPException(status_code=402, detail=rows_reason)

    result = upload_service.process_dataframe(df, filename, ext if ext in ("json", "parquet") else "csv", current_user)
    EntitlementService.record_usage(current_user.id, "storage_mb", size_mb)

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
    req: SheetsUploadRequest,
    current_user: CurrentUser,
):
    """Fetch a public Google Sheet or online spreadsheet and load it as a DataFrame."""
    from dataforge.sheets_connector import SheetsConnector
    from dataforge.excel_online_connector import ExcelOnlineConnector
    from dataforge.api.services.entitlements import EntitlementService

    url = req.url.strip()

    # Automatic routing if an Excel Online / OneDrive / SharePoint link was pasted
    if ExcelOnlineConnector.is_excel_online_url(url) and "docs.google.com" not in url:
        try:
            df, meta = ExcelOnlineConnector.load_url(url)
            filename = f"excel_online_{meta.get('final_url', url).split('/')[-1].split('?')[0] or 'workbook'}.csv"
            if not filename.endswith(".csv"):
                filename += ".csv"
            allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
            if not allowed_rows:
                raise HTTPException(status_code=402, detail=rows_reason)
            result = upload_service.process_dataframe(df, filename, "excel_online", current_user, meta)
            return JSONResponse(content=safe_jsonable({
                "ok": True,
                "upload_id": result["upload_id"],
                "profile": result["profile"],
                "source_type": "excel_online",
            }))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not load Excel Online workbook: {exc}")

    try:
        conn = SheetsConnector()
        df = conn.load_from_url(url)
        sheet_id, gid = conn.parse_sheet_url(url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load Google Sheet: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Google Sheet is empty")

    allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
    if not allowed_rows:
        raise HTTPException(status_code=402, detail=rows_reason)

    clean_id = (sheet_id or "sheet").replace("pub:", "")[:12]
    filename = f"sheet_{clean_id}.csv"
    source_config = {"sheet_id": sheet_id, "gid": gid, "url": url}
    result = upload_service.process_dataframe(df, filename, "sheets", current_user, source_config)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": result["upload_id"],
        "profile": result["profile"],
        "source_type": "sheets",
    }))


@router.post("/upload/excel-online", summary="Load dataset from Microsoft Excel Online, OneDrive or SharePoint")
async def api_upload_excel_online(
    req: ExcelOnlineUploadRequest,
    current_user: CurrentUser,
):
    """Fetch an online Excel workbook from OneDrive, SharePoint, Office 365, or direct cloud link."""
    from dataforge.excel_online_connector import ExcelOnlineConnector
    from dataforge.sheets_connector import SheetsConnector
    from dataforge.api.services.entitlements import EntitlementService

    url = req.url.strip()

    # Automatic routing if a Google Sheet link was provided
    if "docs.google.com/spreadsheets" in url:
        try:
            conn = SheetsConnector()
            df = conn.load_from_url(url)
            sheet_id, gid = conn.parse_sheet_url(url)
            allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
            if not allowed_rows:
                raise HTTPException(status_code=402, detail=rows_reason)
            clean_id = (sheet_id or "sheet").replace("pub:", "")[:12]
            filename = f"sheet_{clean_id}.csv"
            source_config = {"sheet_id": sheet_id, "gid": gid, "url": url}
            result = upload_service.process_dataframe(df, filename, "sheets", current_user, source_config)
            return JSONResponse(content=safe_jsonable({
                "ok": True,
                "upload_id": result["upload_id"],
                "profile": result["profile"],
                "source_type": "sheets",
            }))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not load Google Sheet: {exc}")

    try:
        df, meta = ExcelOnlineConnector.load_url(url, sheet_name=req.sheet_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load Microsoft Excel Online spreadsheet: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Downloaded Excel workbook is empty")

    allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
    if not allowed_rows:
        raise HTTPException(status_code=402, detail=rows_reason)

    raw_name = req.dataset_name or meta.get("final_url", url).split("/")[-1].split("?")[0] or "excel_online"
    clean_name = raw_name.replace(".xlsx", "").replace(".xls", "")
    filename = f"{clean_name}.csv"

    result = upload_service.process_dataframe(df, filename, "excel_online", current_user, meta)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": result["upload_id"],
        "profile": result["profile"],
        "source_type": "excel_online",
        "sheets": meta.get("sheets", []),
    }))



@router.post("/upload/json-url", summary="Load dataset from a public JSON URL or REST API")
async def api_upload_json_url(
    req: JSONUrlUploadRequest,
    current_user: CurrentUser,
):
    import json as pyjson
    from dataforge.api.utils.ssrf import safe_fetch_url, SSRFSecurityError

    try:
        status_code, resp_headers, raw_bytes = safe_fetch_url(
            req.url,
            headers=req.headers,
            timeout=15,
            max_bytes=settings.MAX_UPLOAD_BYTES,
        )
        if status_code != 200:
            raise HTTPException(status_code=400, detail=f"Remote server responded with HTTP {status_code}")

        raw_data = raw_bytes.decode("utf-8")
        parsed = pyjson.loads(raw_data)
        
        if req.root_key and isinstance(parsed, dict) and req.root_key in parsed:
            data_target = parsed[req.root_key]
        else:
            data_target = parsed

        if isinstance(data_target, list):
            df = pd.json_normalize(data_target)
        elif isinstance(data_target, dict):
            for key in ("data", "items", "records", "rows", "results"):
                if key in data_target and isinstance(data_target[key], list):
                    df = pd.json_normalize(data_target[key])
                    break
            else:
                df = pd.json_normalize([data_target])
        else:
            raise ValueError("JSON payload must contain an array or object structure")
    except SSRFSecurityError as sec_err:
        raise HTTPException(status_code=403, detail=f"Security violation: {sec_err}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch or parse JSON URL: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Fetched JSON dataset is empty")

    from dataforge.api.services.entitlements import EntitlementService
    allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
    if not allowed_rows:
        raise HTTPException(status_code=402, detail=rows_reason)

    filename = req.dataset_name or (req.url.split("/")[-1].split("?")[0] or "api_feed.json")
    if not filename.endswith((".json", ".csv")):
        filename += ".json"

    result = upload_service.process_dataframe(df, filename, "json", current_user, {"url": req.url})
    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": result["upload_id"],
        "profile": result["profile"],
    }))


@router.post("/upload/database/test", summary="Test connection to external database or warehouse")
async def api_test_db_connection(
    req: DBTestConnectionRequest,
    current_user: CurrentUser,
):
    from dataforge.db_connector import DBConnector
    conn = DBConnector(req.connection_string)
    ok, msg = await run_in_executor(conn.test)
    return {"ok": ok, "message": msg}


@router.post("/upload/database/tables", summary="List tables in external database")
async def api_list_db_tables(
    req: DBListTablesRequest,
    current_user: CurrentUser,
):
    from dataforge.db_connector import DBConnector
    conn = DBConnector(req.connection_string)
    def _list():
        return conn.list_tables(schema=req.db_schema)
    try:
        tables = await run_in_executor(_list)
        return {"ok": True, "tables": tables}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to list tables: {exc}")


@router.post("/upload/database/preview", summary="Preview rows from external database table or SQL query")
async def api_preview_db(
    req: DBPreviewRequest,
    current_user: CurrentUser,
):
    from dataforge.db_connector import DBConnector
    conn = DBConnector(req.connection_string)
    def _preview():
        if req.query:
            q = req.query.strip().rstrip(";")
            if "limit" not in q.lower():
                q += f" LIMIT {req.limit}"
            return conn.query(q)
        elif req.table_name:
            return conn.load_table(req.table_name, limit=req.limit)
        else:
            raise ValueError("Either table_name or query must be provided")
    try:
        df = await run_in_executor(_preview)
        records = df.head(req.limit).fillna("").to_dict(orient="records")
        columns = [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns]
        return {
            "ok": True,
            "columns": columns,
            "rows": records,
            "row_count": len(df),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Query failed: {exc}")


@router.post("/upload/database/ingest", summary="Ingest database table or SQL query into DataForge")
async def api_ingest_db(
    req: DBIngestRequest,
    current_user: CurrentUser,
):
    from dataforge.db_connector import DBConnector
    conn = DBConnector(req.connection_string)
    def _load():
        if req.query:
            return conn.query(req.query)
        elif req.table_name:
            return conn.load_table(req.table_name, limit=req.limit)
        else:
            raise ValueError("Either table_name or query must be provided")
    try:
        df = await run_in_executor(_load)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Database load failed: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Queried database table is empty")

    from dataforge.api.services.entitlements import EntitlementService
    allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
    if not allowed_rows:
        raise HTTPException(status_code=402, detail=rows_reason)

    filename = req.dataset_name or (f"{req.table_name}.csv" if req.table_name else "db_query.csv")
    source_config = {
        "type": "database",
        "table_name": req.table_name,
        "has_query": bool(req.query),
    }
    result = upload_service.process_dataframe(df, filename, "database", current_user, source_config)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": result["upload_id"],
        "profile": result["profile"],
    }))
