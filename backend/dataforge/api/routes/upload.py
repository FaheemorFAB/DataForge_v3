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
from dataforge.api.utils.json import parse_json_to_dataframe, safe_jsonable
from dataforge.db import User

log = logging.getLogger(__name__)
router = APIRouter(tags=["upload"])
settings = get_settings()


def _assert_no_active_workspace_dataset(upload_id: Optional[str]) -> None:
    if upload_id and str(upload_id).strip():
        from dataforge.api.storage.manager import exists
        uid = str(upload_id).strip()
        if exists(uid, "df_raw") or exists(uid, "meta"):
            raise HTTPException(
                status_code=400,
                detail="A dataset is already loaded in this workspace. Uploading additional datasets is not allowed.",
            )


@router.post("/upload", summary="Upload a CSV, Excel, Parquet or JSON file")
async def api_upload(
    current_user: CurrentUser,
    job_manager: JobManager = Depends(get_job_manager_dep),
    file: UploadFile = File(...),
    upload_id_override: Optional[int] = Form(default=None),
    expected_format: Optional[str] = Form(default=None),
    current_upload_id: Optional[str] = Form(default=None),
    workspace_id: Optional[str] = Form(default=None),
):
    """Accept a file upload, profile it, and persist to disk + Supabase."""
    _assert_no_active_workspace_dataset(current_upload_id)
    filename = file.filename or "upload.csv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"

    if ext not in {"csv", "xls", "xlsx", "parquet", "json", "jsonl", "ndjson"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    if expected_format:
        exp = expected_format.lower().strip()
        format_map = {
            "csv": {"csv"},
            "excel": {"xls", "xlsx"},
            "parquet": {"parquet"},
            "json": {"json", "jsonl", "ndjson"},
        }
        if exp in format_map and ext not in format_map[exp]:
            expected_labels = {
                "csv": "CSV (.csv)",
                "excel": "Excel (.xlsx, .xls)",
                "parquet": "Parquet (.parquet)",
                "json": "JSON (.json, .jsonl, .ndjson)",
            }
            raise HTTPException(
                status_code=400,
                detail=f"File extension mismatch: uploaded file '{filename}' has extension .{ext}, but selected format is {expected_labels.get(exp, exp.upper())}."
            )

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
            df = parse_json_to_dataframe(raw)
        else:
            raise ValueError(f"Unsupported extension: {ext}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    from dataforge.api.services.entitlements import EntitlementService
    size_mb = len(raw) / (1024 * 1024)
    allowed_storage, storage_reason = EntitlementService.check_entitlement(
        current_user.id, "storage_mb", size_mb, email=current_user.email
    )
    if not allowed_storage:
        raise HTTPException(status_code=402, detail=storage_reason)

    allowed_rows, rows_reason = EntitlementService.check_entitlement(
        current_user.id, "rows", len(df), email=current_user.email
    )
    if not allowed_rows:
        raise HTTPException(status_code=402, detail=rows_reason)

    target_org_id = workspace_id if (workspace_id and workspace_id != "personal") else None
    result = upload_service.process_dataframe(
        df, filename, ext if ext in ("json", "parquet") else "csv", current_user, org_id=target_org_id
    )
    if ext in ("xls", "xlsx"):
        try:
            raw_wb_path = STORE_DIR / str(result["upload_id"]) / "raw_workbook.xlsx"
            raw_wb_path.parent.mkdir(parents=True, exist_ok=True)
            raw_wb_path.write_bytes(raw)
        except Exception as e:
            log.warning("Could not cache raw workbook bytes: %s", e)
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
    _assert_no_active_workspace_dataset(req.current_upload_id)
    from dataforge.sheets_connector import SheetsConnector
    from dataforge.excel_online_connector import ExcelOnlineConnector
    from dataforge.api.services.entitlements import EntitlementService

    url = req.url.strip()

    # Automatic routing if an Excel Online / OneDrive / SharePoint link was pasted
    if ExcelOnlineConnector.is_excel_online_url(url) and "docs.google.com" not in url:
        allowed_src, src_reason = EntitlementService.check_source_access(current_user.id, "onedrive_excel")
        if not allowed_src:
            raise HTTPException(status_code=402, detail=src_reason)
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
        df = conn.load_from_url(url, sheet_name=req.sheet_name, gid=req.gid)
        info = conn.parse_sheet_url(url)
        sheet_id = getattr(info, "sheet_id", info[0] if isinstance(info, (tuple, list)) else None)
        gid = req.gid or getattr(info, "gid", info[1] if isinstance(info, (tuple, list)) and len(info) > 1 else "0") or "0"
        sheet_name = req.sheet_name or getattr(info, "sheet_name", None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load Google Sheet: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Google Sheet is empty")

    allowed_rows, rows_reason = EntitlementService.check_entitlement(current_user.id, "rows", len(df))
    if not allowed_rows:
        raise HTTPException(status_code=402, detail=rows_reason)

    clean_id = (sheet_id or "sheet").replace("pub:", "")[:12]
    clean_tab = f"_{sheet_name[:16]}" if sheet_name else ""
    filename = f"sheet_{clean_id}{clean_tab}.csv"
    source_config = {"sheet_id": sheet_id, "gid": gid, "sheet_name": sheet_name, "url": url}
    result = upload_service.process_dataframe(df, filename, "sheets", current_user, source_config)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": result["upload_id"],
        "profile": result["profile"],
        "source_type": "sheets",
    }))


@router.post("/upload/sheets/worksheets", summary="List worksheet tabs available in a public Google Sheet or Excel Online")
@router.post("/upload/excel-online/worksheets", summary="List worksheet tabs available in an Excel Online workbook")
async def api_sheets_worksheets(
    req: SheetsUploadRequest,
    current_user: CurrentUser,
):
    """Inspect a public Google Sheet or Microsoft 365 / OneDrive Excel workbook and return available worksheet tab names."""
    from dataforge.sheets_connector import SheetsConnector
    from dataforge.excel_online_connector import ExcelOnlineConnector

    url = (req.url or "").strip()
    if not url:
        return {"ok": False, "sheets": []}

    try:
        if "docs.google.com/spreadsheets" in url:
            sheets = SheetsConnector.list_public_worksheets(url)
            return {"ok": True, "sheets": sheets}
        elif ExcelOnlineConnector.is_excel_online_url(url):
            sheets = ExcelOnlineConnector.list_worksheets(url)
            return {"ok": True, "sheets": sheets}
        else:
            # Try Google Sheets first, fallback to Excel Online
            sheets = SheetsConnector.list_public_worksheets(url)
            if not sheets:
                sheets = ExcelOnlineConnector.list_worksheets(url)
            return {"ok": True, "sheets": sheets}
    except Exception as exc:
        log.warning("Could not list worksheets: %s", exc)
        return {"ok": False, "sheets": []}


@router.post("/upload/excel-online", summary="Load dataset from Microsoft Excel Online, OneDrive or SharePoint")
async def api_upload_excel_online(
    req: ExcelOnlineUploadRequest,
    current_user: CurrentUser,
):
    """Fetch an online Excel workbook from OneDrive, SharePoint, Office 365, or direct cloud link."""
    _assert_no_active_workspace_dataset(req.current_upload_id)
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
        allowed_src, src_reason = EntitlementService.check_source_access(current_user.id, "onedrive_excel")
        if not allowed_src:
            raise HTTPException(status_code=402, detail=src_reason)
        df, meta = ExcelOnlineConnector.load_url(url, sheet_name=req.sheet_name)
    except HTTPException:
        raise
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
    _assert_no_active_workspace_dataset(req.current_upload_id)
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

        if req.root_key:
            import json as pyjson
            try:
                parsed = pyjson.loads(raw_bytes.decode("utf-8-sig", errors="replace"))
                if isinstance(parsed, dict) and req.root_key in parsed:
                    target_bytes = pyjson.dumps(parsed[req.root_key]).encode("utf-8")
                    df = parse_json_to_dataframe(target_bytes)
                else:
                    df = parse_json_to_dataframe(raw_bytes)
            except Exception:
                df = parse_json_to_dataframe(raw_bytes)
        else:
            df = parse_json_to_dataframe(raw_bytes)
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
    from dataforge.api.services.entitlements import EntitlementService
    allowed_src, src_reason = EntitlementService.check_source_access(current_user.id, "databases")
    if not allowed_src:
        raise HTTPException(status_code=402, detail=src_reason)
    from dataforge.db_connector import DBConnector
    conn = DBConnector(req.connection_string)
    ok, msg = await run_in_executor(conn.test)
    return {"ok": ok, "message": msg}


@router.post("/upload/database/tables", summary="List tables in external database")
async def api_list_db_tables(
    req: DBListTablesRequest,
    current_user: CurrentUser,
):
    from dataforge.api.services.entitlements import EntitlementService
    allowed_src, src_reason = EntitlementService.check_source_access(current_user.id, "databases")
    if not allowed_src:
        raise HTTPException(status_code=402, detail=src_reason)
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
    from dataforge.api.services.entitlements import EntitlementService
    allowed_src, src_reason = EntitlementService.check_source_access(current_user.id, "databases")
    if not allowed_src:
        raise HTTPException(status_code=402, detail=src_reason)
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
    _assert_no_active_workspace_dataset(req.current_upload_id)
    from dataforge.api.services.entitlements import EntitlementService
    allowed_src, src_reason = EntitlementService.check_source_access(current_user.id, "databases")
    if not allowed_src:
        raise HTTPException(status_code=402, detail=src_reason)
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
