"""
dataforge/api/routes/workspace.py
──────────────────────────────────
Workspace routes: state, preview, clean, EDA, query, transform, chat, etc.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from dataforge.api.deps import CurrentUser, get_job_manager_dep, get_upload_id, require_upload_with_data
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.workspace import (
    AiConsentRequest, ChatSessionRequest, CleanRequest,
    CustomChartDeleteRequest, CustomChartRequest, EDARequest,
    QueryRequest, SyncSheetsRequest, TransformRequest,
)
from dataforge.api.storage.manager import exists, load, persist, save, upath
from dataforge.api.utils.helpers import df_profile, df_to_json_rows
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import db_all, db_get, db_update

log = logging.getLogger(__name__)
router = APIRouter(tags=["workspace"])


# ── Workspace state ───────────────────────────────────────────────────────────

@router.get("/workspace/state", summary="Return full workspace state for an upload")
async def api_workspace_state(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    up = await require_upload_with_data(upload_id, current_user)

    profile      = load(upload_id, "profile") or {}
    df_raw       = load(upload_id, "df_raw")
    df_clean     = load(upload_id, "df_clean")
    clean_meta   = load(upload_id, "clean_meta")
    automl_meta  = load(upload_id, "automl_meta")
    chat_history = load(upload_id, "chat_history") or []
    has_eda      = (upath(upload_id, "eda_html").exists()
                   or upath(upload_id, "eda_html").with_suffix(".json").exists())
    ai_consent   = bool(load(upload_id, "ai_consent"))

    now_iso = datetime.now(timezone.utc).isoformat()

    # Normalise chat history structure
    if isinstance(chat_history, list):
        chat_data = {
            "active_session_id": "default",
            "sessions": [{
                "id": "default", "name": "Previous Chat" if chat_history else "New Chat",
                "created_at": now_iso, "updated_at": now_iso,
                "messages": chat_history,
            }],
        }
    elif isinstance(chat_history, dict) and "sessions" in chat_history:
        chat_data = chat_history
    else:
        chat_data = {
            "active_session_id": "default",
            "sessions": [{"id": "default", "name": "New Chat",
                          "created_at": now_iso, "updated_at": now_iso, "messages": []}],
        }

    active_session_id = chat_data.get("active_session_id", "default")
    chat_sessions = chat_data.get("sessions", [])
    active_msgs = next((s["messages"] for s in chat_sessions if s["id"] == active_session_id), [])

    clean_profile = None
    if df_clean is not None:
        up_row = db_get("uploads", upload_id)
        clean_profile = df_profile(df_clean, (up_row or {}).get("filename", ""))

    # Handle Sheets re-fetch on missing data
    needs_reupload = False
    reupload_message = ""
    up_row = db_get("uploads", upload_id) or {}
    src = up_row.get("source_type", "csv") or "csv"
    filename = up_row.get("filename", "")

    if df_raw is None and df_clean is None:
        if src == "sheets" and up_row.get("storage_path"):
            try:
                src_cfg = json.loads(up_row.get("storage_path", "{}"))
                sid = src_cfg.get("sheet_id", "")
                if sid:
                    from dataforge.sheets_connector import SheetsConnector
                    df_raw = SheetsConnector().load_public(sid)
                    save(upload_id, "df_raw", df_raw)
                    profile = df_profile(df_raw, filename)
                    save(upload_id, "profile", profile)
                    persist(upload_id, "df_raw", df_raw)
            except Exception:
                pass

        if df_raw is None:
            needs_reupload = True
            if src == "sheets":
                reupload_message = (
                    f"Could not re-fetch '{filename}' from Google Sheets. "
                    "The sheet may be private or the URL changed."
                )
            else:
                reupload_message = (
                    f"'{filename}' could not be restored from saved storage. "
                    "Re-upload the original file to continue."
                )

    return JSONResponse(content=safe_jsonable({
        "has_df": df_raw is not None,
        "has_clean": df_clean is not None,
        "has_eda": has_eda,
        "has_biz_report": exists(upload_id, "data_report_html"),
        "profile": profile,
        "clean_profile": clean_profile,
        "columns": profile.get("columns", []),
        "clean_meta": clean_meta,
        "automl_meta": automl_meta,
        "chat_history": active_msgs,
        "chat_sessions": chat_sessions,
        "active_session_id": active_session_id,
        "ai_consent": ai_consent,
        "filename": filename,
        "needs_reupload": needs_reupload,
        "reupload_filename": filename,
        "reupload_message": reupload_message,
        "source_type": src,
    }))


# ── Preview ───────────────────────────────────────────────────────────────────

@router.get("/preview", summary="Paginated dataset preview (DuckDB-accelerated)")
async def api_preview(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
    limit: int = Query(default=500, ge=50, le=5000),
    clean: bool = Query(default=False),
    columns: Optional[str] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    key = "df_clean" if clean else "df_raw"
    p = upath(upload_id, key).with_suffix(".parquet")
    if not p.exists():
        p = upath(upload_id, "df_raw").with_suffix(".parquet")

    if p.exists():
        try:
            import duckdb

            def _duck():
                if columns:
                    cols_list = [f'"{c.strip()}"' for c in columns.split(",") if c.strip()]
                    sel = ", ".join(cols_list)
                else:
                    sel = "*"
                total = duckdb.execute(f"SELECT COUNT(*) FROM '{p}'").fetchone()[0]
                df = duckdb.execute(f"SELECT {sel} FROM '{p}' LIMIT {limit}").df()
                return total, df

            total, preview_df = await run_in_executor(_duck)
            payload = df_to_json_rows(preview_df, limit)
            payload["total"] = int(total)
            payload["preview_only"] = int(total) > len(preview_df)
            return JSONResponse(content=safe_jsonable(payload))
        except Exception as exc:
            log.warning("DuckDB preview failed, falling back to pandas: %s", exc)

    df = load(upload_id, "df_clean") if clean else None
    df = df if df is not None else load(upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")
    return JSONResponse(content=safe_jsonable(df_to_json_rows(df, limit)))


# ── Sync Sheets ───────────────────────────────────────────────────────────────

@router.post("/workspace/sync-sheets", summary="Re-sync dataset from Google Sheets")
async def api_sync_sheets(
    body: SyncSheetsRequest,
    current_user: CurrentUser,
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    up_row = db_get("uploads", upload_id) or {}
    if up_row.get("source_type") != "sheets":
        raise HTTPException(400, "This project was not loaded from Google Sheets")

    storage_path = up_row.get("storage_path", "")
    try:
        src_cfg = json.loads(storage_path) if storage_path else {}
    except Exception:
        raise HTTPException(400, "Google Sheets config not available. Re-connect the sheet first.")

    sheet_id = (src_cfg.get("sheet_id") or "").strip()
    if not sheet_id and src_cfg.get("url"):
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", src_cfg.get("url", ""))
        if m:
            sheet_id = m.group(1)
    if not sheet_id:
        raise HTTPException(400, "Sheet ID not found. Re-connect the Google Sheet once.")

    try:
        from dataforge.sheets_connector import SheetsConnector
        df = SheetsConnector().load_public(sheet_id)
    except Exception as exc:
        raise HTTPException(400, f"Could not sync with Google Sheets: {exc}")

    filename = up_row.get("filename", "sheet.csv")
    profile = df_profile(df, filename)

    save(upload_id, "df_raw", df)
    save(upload_id, "profile", profile)
    try:
        persist(upload_id, "df_raw", df)
    except Exception:
        pass

    try:
        db_update("uploads", upload_id, {
            "rows": profile.get("rows", 0),
            "cols": profile.get("cols", 0),
            "missing_pct": profile.get("missing_pct", 0.0),
        })
    except Exception:
        pass

    return JSONResponse(content=safe_jsonable({"ok": True, "profile": profile}))


# ── Clean ─────────────────────────────────────────────────────────────────────

@router.post("/clean", summary="Run auto-cleaning pipeline on raw dataset")
async def api_clean(
    body: CleanRequest,
    current_user: CurrentUser,
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    df_raw = load(upload_id, "df_raw")
    if df_raw is None:
        raise HTTPException(400, "No raw dataset loaded")

    def _clean():
        from dataforge.web.helpers import run_cleaning_pipeline
        return run_cleaning_pipeline(df_raw)

    try:
        result = await run_in_executor(_clean)
    except Exception as exc:
        raise HTTPException(500, f"Cleaning failed: {exc}")

    df_clean = result["df_clean"]
    save(upload_id, "df_clean", df_clean)

    up_row = db_get("uploads", upload_id) or {}
    clean_profile = df_profile(df_clean, up_row.get("filename", ""))
    meta = {
        "stats": result["stats"],
        "missing_log": result["missing_log"],
        "struct_actions": result["struct_actions"],
        "clean_profile": clean_profile,
    }
    save(upload_id, "clean_meta", meta)

    try:
        persist(upload_id, "df_clean", df_clean)
    except Exception:
        pass

    try:
        db_update("uploads", upload_id, {"clean_meta_json": json.dumps(meta, default=str)})
    except Exception:
        pass

    from dataforge.api.cache.manager import invalidate_upload
    invalidate_upload(upload_id)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "stats": result["stats"],
        "missing_log": result["missing_log"],
        "struct_actions": result["struct_actions"],
        "clean_profile": clean_profile,
    }))


# ── EDA ───────────────────────────────────────────────────────────────────────

@router.post("/eda", summary="Dispatch async EDA report generation")
async def api_eda(
    body: EDARequest,
    current_user: CurrentUser,
    job_manager: JobManager = Depends(get_job_manager_dep),
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    job_id = await job_manager.dispatch_eda(
        upload_id, current_user.id, minimal=body.minimal, sample_n=body.sample_n
    )
    return {"task_id": job_id, "queued": True}


@router.get("/eda/report", summary="Return or download the EDA HTML report")
async def api_eda_report(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
    format: str = Query(default="html"),
    download: str = Query(default="0"),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    from dataforge.api.storage.manager import load as _load
    from dataforge.settings import PROJECTS_DIR

    # Try file path first (large HTML), then disk storage
    html = None
    html_path = PROJECTS_DIR / str(upload_id) / "eda_html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
    if not html:
        html = _load(upload_id, "eda_html")
    if not html:
        raise HTTPException(404, "No EDA report generated yet")

    wants_download = download in ("1", "true", "yes")
    wants_pdf = format.lower() == "pdf"

    if wants_pdf:
        pdf = None
        try:
            from weasyprint import HTML as WP_HTML
            pdf = WP_HTML(string=html).write_pdf()
        except Exception:
            pass
        if pdf:
            return StreamingResponse(
                iter([pdf]),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=eda_report_{upload_id}.pdf"},
            )

    headers = {}
    if wants_download:
        headers["Content-Disposition"] = f"attachment; filename=eda_report_{upload_id}.html"
    return Response(content=html, media_type="text/html", headers=headers)


# ── AI Query (chat) ───────────────────────────────────────────────────────────

@router.post("/query", summary="Ask an AI question about the dataset")
async def api_query(
    body: QueryRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    query_str = (body.question or body.query or "").strip()
    if not query_str:
        raise HTTPException(400, "Empty query")

    # Load/update chat session structure
    chat_data = load(upload_id, "chat_history")
    if isinstance(chat_data, list):
        if len(chat_data) > 0:
            default_session = {
                "id": "default",
                "name": "Previous Chat",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "messages": chat_data,
            }
            chat_data = {
                "active_session_id": "default",
                "sessions": [default_session],
            }
        else:
            chat_data = {
                "active_session_id": "default",
                "sessions": [{
                    "id": "default",
                    "name": "New Chat",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "messages": [],
                }],
            }

    if not isinstance(chat_data, dict) or "sessions" not in chat_data or not chat_data.get("sessions"):
        chat_data = {
            "active_session_id": "default",
            "sessions": [{
                "id": "default",
                "name": "New Chat",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "messages": [],
            }],
        }

    session_id = body.session_id or chat_data.get("active_session_id") or "default"
    session = next((s for s in chat_data["sessions"] if s["id"] == session_id), None)
    if not session:
        session = {
            "id": session_id,
            "name": "New Chat",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }
        chat_data["sessions"].append(session)

    chat_data["active_session_id"] = session_id

    if session.get("name") in ("New Chat", "New Chat Session"):
        session["name"] = query_str[:30] + "..." if len(query_str) > 30 else query_str

    metric_context = ""
    if current_user and getattr(current_user, "id", None):
        try:
            user_metrics = db_all("metric_definitions", {"user_id": current_user.id})
            if user_metrics:
                lines = ["Defined business metrics:"]
                for m in user_metrics:
                    l = f"  {m.get('name')} = {m.get('formula')}"
                    if m.get("description"):
                        l += f"  # {m.get('description')}"
                    lines.append(l)
                metric_context = "\n".join(lines)
        except Exception:
            pass

    def _run():
        from dataforge.gemini_pipeline import run_query_pipeline
        return run_query_pipeline(query_str, df, metric_context=metric_context)

    try:
        result = await run_in_executor(_run)
    except Exception as exc:
        log.exception("AI query failed: %s", exc)
        return JSONResponse(content={"error": str(exc)}, status_code=500)

    session["messages"].append({"role": "user", "content": query_str})
    msg = {"role": "assistant", "content": result.get("answer", "")}
    r = result.get("result") or {}
    if r.get("type") in ("bar_chart", "line_chart", "histogram", "scatter_chart"):
        msg["chartData"] = r
    elif r.get("type") == "table":
        msg["tableData"] = r
    if result.get("insight"):
        msg["insight"] = result["insight"]
    session["messages"].append(msg)
    session["updated_at"] = datetime.now(timezone.utc).isoformat()

    save(upload_id, "chat_history", chat_data)

    try:
        db_update("uploads", upload_id, {
            "chat_history": json.dumps(chat_data, default=str)
        })
    except Exception:
        pass

    result["chat_sessions"] = chat_data["sessions"]
    result["active_session_id"] = session_id

    return JSONResponse(content=safe_jsonable(result))


# ── AI Consent ────────────────────────────────────────────────────────────────

@router.post("/workspace/consent", summary="Set AI data-sharing consent for an upload")
@router.post("/workspace/ai-consent", summary="Set AI data-sharing consent for an upload (alias)")
async def api_ai_consent(
    current_user: CurrentUser,
    body: Optional[AiConsentRequest] = None,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = (body.upload_id if body else None) or upload_id
    consent_val = body.consent if body else True
    if target_upload_id:
        save(target_upload_id, "ai_consent", {"consent": consent_val})
    return {"ok": True, "consent": consent_val}


# ── Chat sessions ─────────────────────────────────────────────────────────────

@router.post("/workspace/chat/session", summary="Create a new chat session")
async def api_chat_session_create(
    body: ChatSessionRequest,
    current_user: CurrentUser,
):
    import uuid
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    chat_data = load(upload_id, "chat_history")
    if not isinstance(chat_data, dict):
        chat_data = {"active_session_id": "default", "sessions": []}

    new_session = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
    }
    chat_data["sessions"].append(new_session)
    chat_data["active_session_id"] = new_session["id"]
    save(upload_id, "chat_history", chat_data)
    return {"ok": True, "session": new_session}


@router.delete("/workspace/chat/session/{session_id}", summary="Delete a chat session")
async def api_chat_session_delete(
    session_id: str,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    chat_data = load(upload_id, "chat_history")
    if not isinstance(chat_data, dict):
        raise HTTPException(404, "No chat history found")

    sessions = chat_data.get("sessions", [])
    if len(sessions) <= 1:
        raise HTTPException(400, "Cannot delete the only chat session")

    chat_data["sessions"] = [s for s in sessions if s["id"] != session_id]
    if chat_data.get("active_session_id") == session_id:
        chat_data["active_session_id"] = chat_data["sessions"][0]["id"]
    save(upload_id, "chat_history", chat_data)
    return {"ok": True}


# ── Transform ─────────────────────────────────────────────────────────────────

@router.post("/transform", summary="Apply column operations to the dataset")
async def api_transform(
    body: TransformRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    def _transform():
        from dataforge.web.helpers import apply_transforms
        return apply_transforms(df, body.operations)

    try:
        raw_res = await run_in_executor(_transform)
        result_df = getattr(raw_res, "df", raw_res) if not isinstance(raw_res, dict) else raw_res.get("df", raw_res)
    except Exception as exc:
        raise HTTPException(400, f"Transform failed: {exc}")

    save(target_upload_id, "df_clean", result_df)
    up_row = db_get("uploads", target_upload_id) or {}
    profile = df_profile(result_df, up_row.get("filename", ""))
    return JSONResponse(content=safe_jsonable({"ok": True, "profile": profile}))


# ── Custom chart ──────────────────────────────────────────────────────────────

@router.post("/workspace/custom-chart", summary="Create or edit a custom chart")
async def api_custom_chart(
    body: CustomChartRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    if body.x_col not in df.columns:
        raise HTTPException(400, f"Column '{body.x_col}' not found")
    if body.y_col and body.y_col not in df.columns:
        raise HTTPException(400, f"Column '{body.y_col}' not found")

    custom_charts = load(target_upload_id, "custom_charts") or []

    def _ts():
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    if body.duplicate_from_id:
        orig = next((c for c in custom_charts if c.get("id") == body.duplicate_from_id), None)
        if not orig:
            raise HTTPException(404, "Original chart not found")
        new_cfg = {**orig, "id": f"custom_{_ts()}", "title": f"Copy of {orig.get('title', '')}"}
        custom_charts.append(new_cfg)
    elif body.id:
        idx = next((i for i, c in enumerate(custom_charts) if c.get("id") == body.id), None)
        if idx is None:
            raise HTTPException(404, "Chart to edit not found")
        new_cfg = body.model_dump(exclude_none=True)
        new_cfg.pop("upload_id", None)
        custom_charts[idx] = new_cfg
    else:
        new_cfg = {
            "id": f"custom_{_ts()}",
            "type": body.chart_type,
            "chart_type": body.chart_type,
            "x_col": body.x_col,
            "y_col": body.y_col,
            "agg_type": body.agg_type or "none",
            "title": body.title or f"{body.chart_type.title()} of {body.x_col}",
            "is_custom": True,
            "is_area": body.is_area,
        }
        custom_charts.append(new_cfg)

    save(target_upload_id, "custom_charts", custom_charts)
    return JSONResponse(content=safe_jsonable({"ok": True, "chart": new_cfg}))


@router.post("/workspace/custom-chart/delete", summary="Delete a custom chart")
async def api_custom_chart_delete(
    body: CustomChartDeleteRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    custom_charts = load(target_upload_id, "custom_charts") or []
    custom_charts = [c for c in custom_charts if c.get("id") != body.id]
    save(target_upload_id, "custom_charts", custom_charts)
    return {"ok": True, "charts": custom_charts}
