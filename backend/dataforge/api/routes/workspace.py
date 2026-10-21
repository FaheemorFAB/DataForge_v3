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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from dataforge.api.deps import CurrentUser, get_job_manager_dep, get_upload_id, require_upload_with_data
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.workspace import (
    AiConsentRequest, ChatSessionRequest, CleanRequest,
    CustomChartDeleteRequest, CustomChartRequest, EDARequest,
    QueryRequest, SyncSheetsRequest, TransformRequest,
    GranularCleanRequest, RuleDiffRequest,
    ShareInviteRequest, ShareGeneralRequest, ShareRemoveRequest,
)
from dataforge.api.services.sharing import DatasetSharingService
from dataforge.api.storage.manager import exists, load, persist, save, upath
from dataforge.api.storage.snapshots import ConcurrencyConflictError, SnapshotManager
from dataforge.api.utils.helpers import df_profile, df_to_json_rows, resolve_column
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import db_all, db_get, db_update

log = logging.getLogger(__name__)
router = APIRouter(tags=["workspace"])


def _normalize_chat_data(raw_data) -> tuple[dict, bool]:
    """
    Normalizes any chat_history format into a multi-session structure.
    Returns (normalized_dict, was_migrated_bool).
    Ensures previous messages are never lost or wiped out.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    migrated = False

    if isinstance(raw_data, list):
        migrated = True
        has_msgs = len(raw_data) > 0
        first_q = ""
        for m in raw_data:
            if isinstance(m, dict) and m.get("role") == "user" and m.get("content"):
                first_q = m["content"][:28] + ("..." if len(m["content"]) > 28 else "")
                break
        sess_name = first_q or ("Previous Chat" if has_msgs else "New Chat")
        return {
            "active_session_id": "default",
            "sessions": [{
                "id": "default",
                "name": sess_name,
                "created_at": now_iso,
                "updated_at": now_iso,
                "messages": raw_data,
            }],
        }, migrated

    if isinstance(raw_data, dict):
        sessions = raw_data.get("sessions")
        if isinstance(sessions, list) and len(sessions) > 0:
            active_id = raw_data.get("active_session_id")
            if not any(s.get("id") == active_id for s in sessions):
                raw_data["active_session_id"] = sessions[0].get("id", "default")
                migrated = True
            return raw_data, migrated
        elif "messages" in raw_data and isinstance(raw_data["messages"], list):
            migrated = True
            msgs = raw_data["messages"]
            return {
                "active_session_id": "default",
                "sessions": [{
                    "id": "default",
                    "name": raw_data.get("name") or "Previous Chat",
                    "created_at": raw_data.get("created_at") or now_iso,
                    "updated_at": raw_data.get("updated_at") or now_iso,
                    "messages": msgs,
                }],
            }, migrated

    return {
        "active_session_id": "default",
        "sessions": [{
            "id": "default",
            "name": "New Chat",
            "created_at": now_iso,
            "updated_at": now_iso,
            "messages": [],
        }],
    }, False


# ── Workspace state ───────────────────────────────────────────────────────────

@router.get("/workspace/state", summary="Return full workspace state for an upload")
async def api_workspace_state(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
    share_token: Optional[str] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    up = await require_upload_with_data(upload_id, current_user, share_token=share_token)

    profile      = load(upload_id, "profile") or {}
    df_raw       = load(upload_id, "df_raw")
    df_clean     = load(upload_id, "df_clean")
    clean_meta   = load(upload_id, "clean_meta")
    automl_meta  = load(upload_id, "automl_meta")
    from dataforge.settings import PROJECTS_DIR
    has_eda      = (upath(upload_id, "eda_html").exists()
                   or upath(upload_id, "eda_html").with_suffix(".json").exists()
                   or (PROJECTS_DIR / str(upload_id) / "eda_html").exists())
    ai_consent   = bool(load(upload_id, "ai_consent"))

    chat_raw = load(upload_id, "chat_history")
    chat_data, was_migrated = _normalize_chat_data(chat_raw)
    if was_migrated:
        save(upload_id, "chat_history", chat_data)

    active_session_id = chat_data.get("active_session_id", "default")
    chat_sessions = chat_data.get("sessions", [])
    active_sess = next((s for s in chat_sessions if s["id"] == active_session_id), None)
    if not active_sess and chat_sessions:
        active_sess = chat_sessions[0]
        active_session_id = active_sess.get("id", "default")
        chat_data["active_session_id"] = active_session_id
    active_msgs = active_sess.get("messages", []) if active_sess else []

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
        if src == "sheets":
            try:
                sc = up_row.get("source_config") or up_row.get("storage_path")
                if isinstance(sc, str) and sc.strip():
                    try:
                        src_cfg = json.loads(sc)
                    except Exception:
                        src_cfg = {}
                elif isinstance(sc, dict):
                    src_cfg = sc
                else:
                    src_cfg = {}
                sid = (src_cfg.get("sheet_id") or "").strip()
                if not sid and src_cfg.get("url"):
                    m = re.search(r"/spreadsheets/d/(?:e/)?([a-zA-Z0-9_-]+)", src_cfg.get("url", ""))
                    if m:
                        sid = m.group(1)
                if sid:
                    from dataforge.sheets_connector import SheetsConnector
                    df_raw = SheetsConnector().load_public(sid, gid=str(src_cfg.get("gid") or "0"), sheet_name=src_cfg.get("sheet_name"))
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

    version_id = SnapshotManager.get_version(upload_id)
    snapshot_id = load(upload_id, "active_snapshot_id")

    # Compute shared access & owner profile metadata
    owner_id = up.get("user_id") if isinstance(up, dict) else None
    shares = DatasetSharingService.get_shares(upload_id, owner_id=owner_id)
    _, eff_role = DatasetSharingService.check_access(
        upload_id=upload_id,
        user=current_user,
        owner_id=owner_id,
        share_token=share_token,
    )
    is_shared = bool(owner_id is not None and owner_id != current_user.id)
    share_meta = {
        "is_shared": is_shared,
        "effective_role": eff_role,
        "general_access": shares.get("general_access", "restricted"),
        "link_role": shares.get("link_role", "Viewer"),
        "owner_name": shares.get("owner_name", "Dataset Owner"),
        "owner_email": shares.get("owner_email", ""),
        "owner_avatar": shares.get("owner_avatar", "/avatars/avatar-6.svg"),
    }

    return JSONResponse(
        content=safe_jsonable({
            "has_df": df_raw is not None,
            "has_clean": df_clean is not None,
            "has_eda": has_eda,
            "has_biz_report": exists(upload_id, "report_html") or exists(upload_id, "data_report_html") or (PROJECTS_DIR / str(upload_id) / "report_html").exists(),
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
            "version_id": version_id,
            "snapshot_id": snapshot_id,
            "share_meta": share_meta,
        }),
        headers={"ETag": f'"{version_id}"'},
    )


# ── Preview ───────────────────────────────────────────────────────────────────

@router.get("/preview", summary="Paginated dataset preview (DuckDB-accelerated)")
async def api_preview(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
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

    storage_path = up_row.get("storage_path")
    source_config = up_row.get("source_config")

    src_cfg = {}
    if isinstance(source_config, dict):
        src_cfg = source_config
    elif isinstance(storage_path, dict):
        src_cfg = storage_path
    elif isinstance(storage_path, str) and storage_path.strip():
        try:
            src_cfg = json.loads(storage_path)
        except Exception:
            pass
    elif isinstance(source_config, str) and source_config.strip():
        try:
            src_cfg = json.loads(source_config)
        except Exception:
            pass

    sheet_id = (src_cfg.get("sheet_id") or "").strip()
    if not sheet_id and src_cfg.get("url"):
        m = re.search(r"/spreadsheets/d/(?:e/)?([a-zA-Z0-9_-]+)", src_cfg.get("url", ""))
        if m:
            sheet_id = m.group(1)

    if not sheet_id:
        fn = up_row.get("filename", "")
        m = re.search(r"sheet_([a-zA-Z0-9_-]+)", fn)
        if m:
            sheet_id = m.group(1)

    if not sheet_id:
        raise HTTPException(400, "Sheet ID not found. Re-connect the Google Sheet once.")

    gid = str(src_cfg.get("gid") or "0")
    sheet_name = src_cfg.get("sheet_name")
    url = src_cfg.get("url")

    try:
        from dataforge.sheets_connector import SheetsConnector
        conn = SheetsConnector()
        if url:
            try:
                df = conn.load_from_url(url, sheet_name=sheet_name, gid=gid)
            except Exception:
                df = conn.load_public(sheet_id, gid=gid, sheet_name=sheet_name)
        else:
            df = conn.load_public(sheet_id, gid=gid, sheet_name=sheet_name)
    except Exception as exc:
        raise HTTPException(400, f"Could not sync with Google Sheets: {exc}")

    # ── Snapshot state before sync to compute deltas ──────────────────────────
    old_df = load(upload_id, "df_raw")
    old_rows = int(len(old_df)) if old_df is not None else int(up_row.get("rows") or 0)
    old_cols = int(len(old_df.columns)) if old_df is not None else int(up_row.get("cols") or 0)
    old_cols_set = set(str(c) for c in (old_df.columns if old_df is not None else []))

    filename = up_row.get("filename", "sheet.csv")
    profile = df_profile(df, filename)

    new_rows = int(len(df))
    new_cols = int(len(df.columns))
    new_cols_set = set(str(c) for c in df.columns)

    rows_delta = new_rows - old_rows
    cols_delta = new_cols - old_cols
    added_cols = [str(c) for c in df.columns if str(c) not in old_cols_set]
    removed_cols = [str(c) for c in (old_df.columns if old_df is not None else []) if str(c) not in new_cols_set]

    values_changed = False
    if old_df is not None:
        try:
            values_changed = not old_df.equals(df)
        except Exception:
            values_changed = True
    else:
        values_changed = True

    has_changes = (rows_delta != 0) or (cols_delta != 0) or bool(added_cols) or bool(removed_cols) or values_changed

    if not has_changes:
        summary_msg = "Google Sheet is already in sync. No changes detected."
    else:
        change_parts = []
        if rows_delta > 0:
            change_parts.append(f"{rows_delta:,} row{'s' if rows_delta != 1 else ''} added")
        elif rows_delta < 0:
            change_parts.append(f"{abs(rows_delta):,} row{'s' if abs(rows_delta) != 1 else ''} removed")

        if cols_delta > 0:
            change_parts.append(f"{cols_delta} column{'s' if cols_delta != 1 else ''} added")
        elif cols_delta < 0:
            change_parts.append(f"{abs(cols_delta)} column{'s' if abs(cols_delta) != 1 else ''} removed")

        if not change_parts and values_changed:
            change_parts.append("Cell values updated")

        summary_msg = f"Synced with Google Sheets: {', '.join(change_parts)}."

        # Invalidate stale clean/automl caches when raw dataset changes
        for key in ("df_clean", "clean_meta", "automl_meta", "eda_html"):
            p = upath(upload_id, key)
            for suffix in (".parquet", ".json", ".joblib", ".html", ""):
                f = p.with_suffix(suffix) if suffix else p
                if f.exists() and not f.is_dir():
                    try:
                        f.unlink()
                    except Exception:
                        pass

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
            "storage_path": json.dumps(src_cfg) if src_cfg else (storage_path if isinstance(storage_path, str) else None),
            "source_config": src_cfg,
        })
    except Exception:
        pass

    if has_changes:
        try:
            author_name = getattr(current_user, "name", None) or getattr(current_user, "email", "User")
            SnapshotManager.commit_snapshot(
                upload_id=upload_id,
                description=f"Synced Google Sheet: {summary_msg}",
                author=author_name,
            )
        except Exception:
            pass

    changes_info = {
        "has_changes": has_changes,
        "old_rows": old_rows,
        "new_rows": new_rows,
        "rows_delta": rows_delta,
        "rows_added": max(0, rows_delta),
        "rows_removed": max(0, -rows_delta),
        "old_cols": old_cols,
        "new_cols": new_cols,
        "cols_delta": cols_delta,
        "added_cols": added_cols,
        "removed_cols": removed_cols,
        "values_changed": values_changed,
        "summary": summary_msg,
    }

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "profile": profile,
        "changes": changes_info,
    }))


# ── Clean ─────────────────────────────────────────────────────────────────────

@router.post("/clean", summary="Run auto-cleaning pipeline on raw dataset")
async def api_clean(
    body: CleanRequest,
    current_user: CurrentUser,
    request: Request,
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user, min_role="Analyst")

    df_raw = load(upload_id, "df_raw")
    if df_raw is None:
        raise HTTPException(400, "No raw dataset loaded")

    def _clean():
        from dataforge.data_cleaner import run_cleaning_pipeline
        return run_cleaning_pipeline(df_raw)

    try:
        result = await run_in_executor(_clean)
    except Exception as exc:
        raise HTTPException(500, f"Cleaning failed: {exc}")

    if body.preview_only:
        up_row = db_get("uploads", upload_id) or {}
        clean_profile = df_profile(result["df_clean"], up_row.get("filename", ""))
        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "preview_only": True,
                "stats": result["stats"],
                "missing_log": result["missing_log"],
                "imputed_cells": result.get("imputed_cells", {}),
                "struct_actions": result["struct_actions"],
                "clean_profile": clean_profile,
            })
        )

    df_clean = result["df_clean"]

    # Optimistic Concurrency Control (OCC) and Immutable Snapshot Commit
    if_match = request.headers.get("if-match") or body.expected_version_id
    try:
        new_version_id, snapshot_id = SnapshotManager.commit_snapshot(
            upload_id=upload_id,
            df=df_clean,
            expected_version=if_match,
            action="clean",
            metadata={"stats": result["stats"], "imputed_cells": result.get("imputed_cells", {})},
        )
    except ConcurrencyConflictError as err:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: dataset has been modified by another operation.",
                "current_version_id": err.current_version,
                "expected_version_id": err.expected_version,
            },
            headers={"ETag": f'"{err.current_version}"'},
        )

    up_row = db_get("uploads", upload_id) or {}
    clean_profile = df_profile(df_clean, up_row.get("filename", ""))
    meta = {
        "stats": result["stats"],
        "missing_log": result["missing_log"],
        "imputed_cells": result.get("imputed_cells", {}),
        "struct_actions": result["struct_actions"],
        "clean_profile": clean_profile,
        "version_id": new_version_id,
        "snapshot_id": snapshot_id,
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

    return JSONResponse(
        content=safe_jsonable({
            "ok": True,
            "version_id": new_version_id,
            "snapshot_id": snapshot_id,
            "stats": result["stats"],
            "missing_log": result["missing_log"],
            "struct_actions": result["struct_actions"],
            "clean_profile": clean_profile,
        }),
        headers={"ETag": f'"{new_version_id}"'},
    )


@router.post("/clean/dynamic", summary="Run interactive dynamic cleaning with custom column rules")
async def api_clean_dynamic(
    body: dict,
    current_user: CurrentUser,
    request: Request,
):
    upload_id = body.get("upload_id")
    rules = body.get("rules", [])
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user, min_role="Analyst")

    df_raw = load(upload_id, "df_raw")
    if df_raw is None:
        raise HTTPException(400, "No raw dataset loaded")

    def _dynamic_clean():
        from dataforge.data_cleaner import run_dynamic_cleaning_pipeline
        return run_dynamic_cleaning_pipeline(df_raw, rules)

    try:
        result = await run_in_executor(_dynamic_clean)
    except Exception as exc:
        raise HTTPException(500, f"Dynamic cleaning failed: {exc}")

    df_clean = result["df_clean"]

    # Optimistic Concurrency Control (OCC) and Immutable Snapshot Commit
    if_match = request.headers.get("if-match") or body.get("expected_version_id")
    try:
        new_version_id, snapshot_id = SnapshotManager.commit_snapshot(
            upload_id=upload_id,
            df=df_clean,
            expected_version=if_match,
            action="clean_dynamic",
            metadata={"rules_count": len(rules), "stats": result["stats"]},
        )
    except ConcurrencyConflictError as err:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: dataset has been modified by another operation.",
                "current_version_id": err.current_version,
                "expected_version_id": err.expected_version,
            },
            headers={"ETag": f'"{err.current_version}"'},
        )

    up_row = db_get("uploads", upload_id) or {}
    clean_profile = df_profile(df_clean, up_row.get("filename", ""))
    meta = {
        "stats": result["stats"],
        "missing_log": result["missing_log"],
        "struct_actions": result["struct_actions"],
        "clean_profile": clean_profile,
        "rules_applied": rules,
        "pipeline_script": result.get("pipeline_script", ""),
        "version_id": new_version_id,
        "snapshot_id": snapshot_id,
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

    return JSONResponse(
        content=safe_jsonable({
            "ok": True,
            "version_id": new_version_id,
            "snapshot_id": snapshot_id,
            "stats": result["stats"],
            "missing_log": result["missing_log"],
            "struct_actions": result["struct_actions"],
            "clean_profile": clean_profile,
            "pipeline_script": result.get("pipeline_script", ""),
        }),
        headers={"ETag": f'"{new_version_id}"'},
    )


@router.get("/workspace/snapshots", summary="List immutable content-addressed dataset snapshots")
async def api_snapshots_list(
    current_user: CurrentUser,
    upload_id: str = Query(...),
):
    await require_upload_with_data(upload_id, current_user)
    manifest = SnapshotManager.get_manifest(upload_id)
    current_v = SnapshotManager.get_version(upload_id)
    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "upload_id": upload_id,
        "current_version_id": current_v,
        "snapshots": manifest,
    }))


@router.post("/clean/diff", summary="Preview live statistical before/after diff for a proposed cleaning rule")
async def api_clean_diff(
    body: RuleDiffRequest,
    current_user: CurrentUser,
):
    upload_id = body.upload_id
    rule = body.rule
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    # Use df_clean if it exists, otherwise df_raw
    df = load(upload_id, "df_clean")
    if df is None:
        df = load(upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    def _diff():
        from dataforge.data_cleaner import compute_rule_diff
        return compute_rule_diff(df, rule)

    try:
        diff_res = await run_in_executor(_diff)
        return JSONResponse(content=safe_jsonable({"ok": True, "diff": diff_res}))
    except Exception as exc:
        raise HTTPException(500, f"Diff preview failed: {exc}")


@router.get("/clean/export-script", summary="Download reproducible Python cleaning pipeline script")
async def api_clean_export_script(
    current_user: CurrentUser,
    upload_id: str = Query(...),
):
    await require_upload_with_data(upload_id, current_user)
    meta = load(upload_id, "clean_meta") or {}
    script = meta.get("pipeline_script")

    if not script:
        rules = meta.get("rules_applied", [])
        from dataforge.data_cleaner import generate_python_script
        up_row = db_get("uploads", upload_id) or {}
        fname = up_row.get("filename", "raw_dataset.csv")
        script = generate_python_script(rules, fname)

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=script,
        media_type="text/x-python",
        headers={"Content-Disposition": f"attachment; filename=clean_pipeline_{upload_id[:8]}.py"}
    )


# ── EDA ───────────────────────────────────────────────────────────────────────

@router.post("/eda", summary="Dispatch async EDA report generation")
async def api_eda(
    body: EDARequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    job_manager: JobManager = Depends(get_job_manager_dep),
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    job_id = await job_manager.dispatch_eda(
        background_tasks, upload_id, current_user.id, minimal=body.minimal, sample_n=body.sample_n
    )
    return {"task_id": job_id, "queued": True}


@router.get("/eda/report", summary="Return or download the EDA HTML report")
async def api_eda_report(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
    format: str = Query(default="html"),
    download: str = Query(default="0"),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    from dataforge.api.storage.manager import load as _load
    from dataforge.settings import PROJECTS_DIR

    # Try file path first (large HTML), then disk storage, then database
    html = None
    html_path = PROJECTS_DIR / str(upload_id) / "eda_html"
    if html_path.exists():
        try:
            html = html_path.read_text(encoding="utf-8")
        except Exception:
            pass
    if not html:
        html = _load(upload_id, "eda_html")
    if not html:
        try:
            from dataforge.db import db_query
            rows = db_query("reports", {"upload_id": upload_id})
            if rows:
                for r in reversed(rows):
                    if r.get("eda_html"):
                        html = r.get("eda_html")
                        break
        except Exception:
            pass
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


# ── Business Data Report ──────────────────────────────────────────────────────

@router.post("/data-report", summary="Dispatch a background business report generation job")
async def api_data_report_generate(
    body: dict,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    upload_id: Optional[str] = Query(default=None),
):
    target_upload_id = body.get("upload_id") or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    from dataforge.api.jobs.manager import get_job_manager
    job_manager = get_job_manager()
    job_id = await job_manager.dispatch_report(background_tasks, target_upload_id, current_user.id)
    return {"task_id": job_id, "queued": True}


@router.get("/reports/latest", summary="Get the latest generated HTML business report")
async def api_reports_latest(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    from dataforge.api.storage.manager import load as _load
    from dataforge.settings import PROJECTS_DIR

    html = None
    html_path = PROJECTS_DIR / str(upload_id) / "report_html"
    if html_path.exists():
        try:
            html = html_path.read_text(encoding="utf-8")
        except Exception:
            pass
    if not html:
        html = _load(upload_id, "report_html") or _load(upload_id, "data_report_html")
    if not html:
        try:
            from dataforge.db import db_query
            rows = db_query("reports", {"upload_id": upload_id})
            if rows:
                for r in reversed(rows):
                    if r.get("report_html"):
                        html = r.get("report_html")
                        break
        except Exception:
            pass
    if not html:
        raise HTTPException(404, "No business report generated yet. Please generate one first.")
    
    _ancestors = ["'self'"]
    if settings.FRONTEND_URL:
        _ancestors.append(settings.FRONTEND_URL.rstrip("/"))
    if settings.BACKEND_URL:
        _ancestors.append(settings.BACKEND_URL.rstrip("/"))
    _ancestors.extend(["http://localhost:3000", "http://localhost:5000"])
    _csp = f"frame-ancestors {' '.join(dict.fromkeys(_ancestors))}"

    headers = {
        "Content-Disposition": "inline; filename=business_report.html",
        "X-Frame-Options": "SAMEORIGIN",
        "Content-Security-Policy": _csp,
    }
    return Response(content=html, media_type="text/html", headers=headers)


@router.get("/data-report/download", summary="Download the business report as PDF or Printable Document")
async def api_data_report_download(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
    print_pdf: Optional[bool] = Query(default=False, alias="print"),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    from dataforge.api.storage.manager import load as _load
    from dataforge.settings import PROJECTS_DIR

    html = None
    html_path = PROJECTS_DIR / str(upload_id) / "report_html"
    if html_path.exists():
        try:
            html = html_path.read_text(encoding="utf-8")
        except Exception:
            pass
    if not html:
        html = _load(upload_id, "report_html") or _load(upload_id, "data_report_html")
    if not html:
        try:
            from dataforge.db import db_query
            rows = db_query("reports", {"upload_id": upload_id})
            if rows:
                for r in reversed(rows):
                    if r.get("report_html"):
                        html = r.get("report_html")
                        break
        except Exception:
            pass
    if not html:
        raise HTTPException(404, "No report generated yet")

    # 1. Try WeasyPrint PDF compilation
    pdf = None
    try:
        from weasyprint import HTML as WP_HTML
        pdf = WP_HTML(string=html).write_pdf()
    except Exception as e:
        log.warning("WeasyPrint PDF compilation bypassed: %s", e)
    
    if pdf:
        return StreamingResponse(
            iter([pdf]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=business_report_{upload_id}.pdf"},
        )

    # 2. High-Fidelity Vector Fallback: Auto-Printable HTML for Browser PDF Export
    printable_html = html
    if "window.print()" not in printable_html:
        print_script = """
        <script>
          window.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() { window.print(); }, 500);
          });
        </script>
        </body>"""
        if "</body>" in printable_html:
            printable_html = printable_html.replace("</body>", print_script)
        else:
            printable_html += print_script

    _ancestors = ["'self'"]
    if settings.FRONTEND_URL:
        _ancestors.append(settings.FRONTEND_URL.rstrip("/"))
    if settings.BACKEND_URL:
        _ancestors.append(settings.BACKEND_URL.rstrip("/"))
    _ancestors.extend(["http://localhost:3000", "http://localhost:5000"])
    _csp = f"frame-ancestors {' '.join(dict.fromkeys(_ancestors))}"

    if print_pdf or not pdf:
        return Response(
            content=printable_html,
            media_type="text/html",
            headers={
                "Content-Disposition": f"inline; filename=business_report_{upload_id}.html",
                "X-Frame-Options": "SAMEORIGIN",
                "Content-Security-Policy": _csp,
            }
        )

    return Response(
        content=printable_html,
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename=business_report_{upload_id}.html",
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": _csp,
        },
    )


# ── AI Query (chat) ───────────────────────────────────────────────────────────

@router.post("/query", summary="Ask an AI question about the dataset")
async def api_query(
    body: QueryRequest,
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
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

    # Load/update chat session structure safely
    chat_raw = load(target_upload_id, "chat_history")
    chat_data, _ = _normalize_chat_data(chat_raw)

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

    from dataforge.api.services.entitlements import EntitlementService
    allowed, reason = EntitlementService.check_entitlement(current_user.id, "ai_queries", 1)
    if not allowed:
        raise HTTPException(status_code=402, detail=reason)
    EntitlementService.record_usage(current_user.id, "ai_queries", 1)

    def _run():
        from dataforge.gemini_pipeline import run_query_pipeline
        return run_query_pipeline(query_str, df, metric_context=metric_context, upload_id=target_upload_id)

    try:
        result = await run_in_executor(_run)
    except Exception as exc:
        log.exception("AI query failed: %s", exc)
        return JSONResponse(content={"error": str(exc)}, status_code=500)

    session["messages"].append({"role": "user", "content": query_str})
    msg_text = result.get("answer") or result.get("error") or "Analysis complete."
    msg = {"role": "assistant", "content": msg_text}
    r = result.get("result") or {}
    if r.get("type") in ("bar_chart", "line_chart", "histogram", "scatter_chart", "pie_chart", "doughnut_chart", "box_plot"):
        msg["chartData"] = r
    elif r.get("type") == "table":
        msg["tableData"] = r
    if result.get("insight"):
        msg["insight"] = result["insight"]
    if result.get("agent_actions"):
        msg["agent_actions"] = result["agent_actions"]
    if result.get("system_notice"):
        msg["system_notice"] = result["system_notice"]
    if result.get("suggested_actions"):
        msg["suggested_actions"] = result["suggested_actions"]
    if result.get("download_links"):
        msg["download_links"] = result["download_links"]
    session["messages"].append(msg)
    session["updated_at"] = datetime.now(timezone.utc).isoformat()

    save(target_upload_id, "chat_history", chat_data)

    try:
        db_update("uploads", target_upload_id, {
            "chat_history": json.dumps(chat_data, default=str)
        })
    except Exception:
        pass

    result["chat_sessions"] = chat_data["sessions"]
    result["active_session_id"] = session_id
    result["chat_history"] = session["messages"]
    result["reply"] = msg

    return JSONResponse(content=safe_jsonable(result))


# ── AI Consent ────────────────────────────────────────────────────────────────

@router.post("/workspace/consent", summary="Set AI data-sharing consent for an upload")
@router.post("/workspace/ai-consent", summary="Set AI data-sharing consent for an upload (alias)")
async def api_ai_consent(
    current_user: CurrentUser,
    body: Optional[AiConsentRequest] = None,
    upload_id: Optional[str] = Query(default=None),
):
    target_upload_id = (body.upload_id if body else None) or upload_id
    consent_val = body.consent if body else True
    if target_upload_id:
        save(target_upload_id, "ai_consent", {"consent": consent_val})
    return {"ok": True, "consent": consent_val}


# ── Chat sessions ─────────────────────────────────────────────────────────────

@router.post("/workspace/chat/session", summary="Create a new chat session")
@router.post("/workspace/chat/session/new", summary="Create a new chat session (alias)")
async def api_chat_session_create(
    current_user: CurrentUser,
    body: Optional[ChatSessionRequest] = None,
    upload_id: Optional[str] = Query(default=None),
):
    import uuid
    target_upload_id = (body.upload_id if body else None) or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    chat_raw = load(target_upload_id, "chat_history")
    chat_data, _ = _normalize_chat_data(chat_raw)

    new_session = {
        "id": str(uuid.uuid4()),
        "name": (body.name if body and body.name else "New Chat"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
    }
    chat_data["sessions"].append(new_session)
    chat_data["active_session_id"] = new_session["id"]
    save(target_upload_id, "chat_history", chat_data)

    try:
        db_update("uploads", target_upload_id, {
            "chat_history": json.dumps(chat_data, default=str)
        })
    except Exception:
        pass

    return {
        "ok": True,
        "session": new_session,
        "chat_sessions": chat_data["sessions"],
        "active_session": new_session["id"],
        "active_session_id": new_session["id"],
        "chat_history": []
    }


@router.post("/workspace/chat/session/select", summary="Select active chat session")
async def api_chat_session_select(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
    id: Optional[str] = Query(default=None),
    session_id: Optional[str] = Query(default=None),
    body: Optional[dict] = None,
):
    target_upload_id = (body.get("upload_id") if isinstance(body, dict) else None) or upload_id
    target_session_id = (
        (body.get("session_id") if isinstance(body, dict) else None)
        or (body.get("id") if isinstance(body, dict) else None)
        or session_id
        or id
    )

    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    if not target_session_id:
        raise HTTPException(400, "session_id required")
    await require_upload_with_data(target_upload_id, current_user)

    chat_raw = load(target_upload_id, "chat_history")
    chat_data, _ = _normalize_chat_data(chat_raw)

    session_ids = [s["id"] for s in chat_data["sessions"]]
    if target_session_id not in session_ids:
        chat_data["sessions"].append({
            "id": target_session_id,
            "name": "New Chat",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        })

    chat_data["active_session_id"] = target_session_id
    save(target_upload_id, "chat_history", chat_data)

    try:
        db_update("uploads", target_upload_id, {
            "chat_history": json.dumps(chat_data, default=str)
        })
    except Exception:
        pass

    active_history = next((s["messages"] for s in chat_data["sessions"] if s["id"] == target_session_id), [])

    return {
        "ok": True,
        "chat_sessions": chat_data["sessions"],
        "active_session": target_session_id,
        "active_session_id": target_session_id,
        "chat_history": active_history,
    }


@router.post("/workspace/chat/session/rename", summary="Rename a chat session")
async def api_chat_session_rename(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
    id: Optional[str] = Query(default=None),
    session_id: Optional[str] = Query(default=None),
    body: Optional[dict] = None,
):
    target_upload_id = (body.get("upload_id") if isinstance(body, dict) else None) or upload_id
    target_session_id = (
        (body.get("session_id") if isinstance(body, dict) else None)
        or (body.get("id") if isinstance(body, dict) else None)
        or session_id
        or id
    )
    name = (body.get("name") if isinstance(body, dict) else None) or ""

    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    if not target_session_id:
        raise HTTPException(400, "session_id required")
    if not name.strip():
        raise HTTPException(400, "name required")
    await require_upload_with_data(target_upload_id, current_user)

    chat_raw = load(target_upload_id, "chat_history")
    chat_data, _ = _normalize_chat_data(chat_raw)

    target_sess = next((s for s in chat_data["sessions"] if s["id"] == target_session_id), None)
    if not target_sess:
        raise HTTPException(404, "Session not found")

    target_sess["name"] = name.strip()
    target_sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    save(target_upload_id, "chat_history", chat_data)

    try:
        db_update("uploads", target_upload_id, {
            "chat_history": json.dumps(chat_data, default=str)
        })
    except Exception:
        pass

    return {
        "ok": True,
        "chat_sessions": chat_data["sessions"],
        "active_session": chat_data.get("active_session_id"),
        "active_session_id": chat_data.get("active_session_id"),
    }


@router.delete("/workspace/chat/session/{session_id}", summary="Delete a chat session")
@router.post("/workspace/chat/session/delete", summary="Delete a chat session (POST alias)")
async def api_chat_session_delete(
    current_user: CurrentUser,
    session_id: Optional[str] = None,
    upload_id: Optional[str] = Query(default=None),
    body: Optional[dict] = None,
):
    target_upload_id = (body.get("upload_id") if isinstance(body, dict) else None) or upload_id
    target_session_id = (
        session_id
        or (body.get("session_id") if isinstance(body, dict) else None)
        or (body.get("id") if isinstance(body, dict) else None)
    )

    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    if not target_session_id:
        raise HTTPException(400, "session_id required")
    await require_upload_with_data(target_upload_id, current_user)

    chat_raw = load(target_upload_id, "chat_history")
    chat_data, _ = _normalize_chat_data(chat_raw)

    sessions = chat_data.get("sessions", [])
    if len(sessions) <= 1:
        # Reset the only session rather than breaking the workspace
        sessions[0]["messages"] = []
        sessions[0]["name"] = "New Chat"
        sessions[0]["updated_at"] = datetime.now(timezone.utc).isoformat()
        chat_data["active_session_id"] = sessions[0]["id"]
    else:
        chat_data["sessions"] = [s for s in sessions if s["id"] != target_session_id]
        if chat_data.get("active_session_id") == target_session_id:
            chat_data["active_session_id"] = chat_data["sessions"][0]["id"]

    save(target_upload_id, "chat_history", chat_data)

    try:
        db_update("uploads", target_upload_id, {
            "chat_history": json.dumps(chat_data, default=str)
        })
    except Exception:
        pass

    active_id = chat_data.get("active_session_id", "default")
    active_history = next((s["messages"] for s in chat_data["sessions"] if s["id"] == active_id), [])

    return {
        "ok": True,
        "chat_sessions": chat_data["sessions"],
        "active_session": active_id,
        "active_session_id": active_id,
        "chat_history": active_history,
    }


# ── Transform ─────────────────────────────────────────────────────────────────

@router.post("/transform", summary="Apply column operations to the dataset")
async def api_transform(
    body: TransformRequest,
    current_user: CurrentUser,
    request: Request,
    upload_id: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user, min_role="Analyst")

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    def _transform():
        from dataforge.transform_engine import apply_transforms
        return apply_transforms(df, body.operations)

    try:
        raw_res = await run_in_executor(_transform)
        result_df = getattr(raw_res, "df", raw_res) if not isinstance(raw_res, dict) else raw_res.get("df", raw_res)
    except Exception as exc:
        raise HTTPException(400, f"Transform failed: {exc}")

    # Optimistic Concurrency Control (OCC) and Immutable Snapshot Commit
    if_match = request.headers.get("if-match") or body.expected_version_id
    try:
        new_version_id, snapshot_id = SnapshotManager.commit_snapshot(
            upload_id=target_upload_id,
            df=result_df,
            expected_version=if_match,
            action="transform",
            metadata={"operations": body.operations},
        )
    except ConcurrencyConflictError as err:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: dataset has been modified by another operation.",
                "current_version_id": err.current_version,
                "expected_version_id": err.expected_version,
            },
            headers={"ETag": f'"{err.current_version}"'},
        )

    up_row = db_get("uploads", target_upload_id) or {}
    profile = df_profile(result_df, up_row.get("filename", ""))
    return JSONResponse(
        content=safe_jsonable({
            "ok": True,
            "version_id": new_version_id,
            "snapshot_id": snapshot_id,
            "profile": profile,
        }),
        headers={"ETag": f'"{new_version_id}"'},
    )


# ── Custom chart ──────────────────────────────────────────────────────────────

@router.post("/workspace/custom-chart", summary="Create or edit a custom chart")
async def api_custom_chart(
    body: CustomChartRequest,
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        print("DEBUG: 400 - upload_id required")
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        print("DEBUG: 400 - No dataset loaded")
        raise HTTPException(400, "No dataset loaded")

    x_col_res = resolve_column(body.x_col, df.columns)
    if not x_col_res:
        print(f"DEBUG: 400 - x_col not found: '{body.x_col}', cols: {df.columns.tolist()}")
        raise HTTPException(400, f"Column '{body.x_col}' not found in dataset")

    y_col_res = None
    if body.y_col:
        y_col_res = resolve_column(body.y_col, df.columns)
        if not y_col_res:
            print(f"DEBUG: 400 - y_col not found: '{body.y_col}', cols: {df.columns.tolist()}")
            raise HTTPException(400, f"Column '{body.y_col}' not found in dataset")

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
        new_cfg["x_col"] = x_col_res
        new_cfg["y_col"] = y_col_res
        custom_charts[idx] = new_cfg
    else:
        new_cfg = {
            "id": f"custom_{_ts()}",
            "type": body.chart_type,
            "chart_type": body.chart_type,
            "x_col": x_col_res,
            "y_col": y_col_res,
            "agg_type": body.agg_type or "none",
            "title": body.title or f"{body.chart_type.title()} of {x_col_res}",
            "is_custom": True,
            "is_area": body.is_area,
            "top_n": body.top_n,
        }
        custom_charts.append(new_cfg)

    save(target_upload_id, "custom_charts", custom_charts)
    return JSONResponse(content=safe_jsonable({"ok": True, "chart": new_cfg}))


@router.post("/workspace/custom-chart/delete", summary="Delete a custom chart")
async def api_custom_chart_delete(
    body: CustomChartDeleteRequest,
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    custom_charts = load(target_upload_id, "custom_charts") or []
    custom_charts = [c for c in custom_charts if c.get("id") != body.chart_id]
    save(target_upload_id, "custom_charts", custom_charts)
    return {"ok": True, "charts": custom_charts}


# ── Google Sheets-Style Dataset Sharing & User-Level Access Control ─────────────

@router.get("/workspace/{upload_id}/share", summary="Get dataset sharing permissions and members")
async def api_get_dataset_share(
    upload_id: str,
    current_user: CurrentUser,
    share_token: Optional[str] = Query(default=None),
):
    upload = await require_upload_with_data(upload_id, current_user, min_role="Viewer", share_token=share_token)
    owner_id = upload.get("user_id")
    owner_email = upload.get("user_email")
    if current_user and current_user.id == owner_id and getattr(current_user, "email", None):
        owner_email = current_user.email
    shares = DatasetSharingService.get_shares(upload_id, owner_id=owner_id, owner_email=owner_email)
    
    # Calculate caller's effective role
    _, eff_role = DatasetSharingService.check_access(
        upload_id=upload_id,
        user=current_user,
        owner_id=owner_id,
        share_token=share_token,
    )
    
    from dataforge.api.services.entitlements import EntitlementService
    target_user_id = owner_id or current_user.id
    target_email = owner_email or getattr(current_user, "email", None)
    sub = EntitlementService.get_subscription(target_user_id, email=target_email)
    user_tier = sub.get("plan", "free")
    has_team_collaboration = sub.get("has_team_collaboration", False)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "shares": shares,
        "current_user_role": eff_role,
        "is_owner": eff_role in ("Owner", "Admin"),
        "user_tier": user_tier,
        "has_team_collaboration": has_team_collaboration,
    }))


@router.post("/workspace/{upload_id}/share/invite", summary="Invite or update a collaborator by email")
async def api_invite_collaborator(
    upload_id: str,
    body: ShareInviteRequest,
    current_user: CurrentUser,
):
    upload = await require_upload_with_data(upload_id, current_user, min_role="Admin")
    try:
        updated = DatasetSharingService.invite_collaborator(
            upload_id=upload_id,
            operator_id=current_user.id,
            email=body.email,
            role=body.role,
        )
        return JSONResponse(content=safe_jsonable({"ok": True, "shares": updated}))
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/workspace/{upload_id}/share/collaborators", summary="Remove collaborator access")
async def api_remove_collaborator(
    upload_id: str,
    body: ShareRemoveRequest,
    current_user: CurrentUser,
):
    upload = await require_upload_with_data(upload_id, current_user, min_role="Admin")
    try:
        updated = DatasetSharingService.remove_collaborator(
            upload_id=upload_id,
            operator_id=current_user.id,
            email=body.email,
        )
        return JSONResponse(content=safe_jsonable({"ok": True, "shares": updated}))
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspace/{upload_id}/share/general", summary="Update general link access settings")
async def api_update_general_share(
    upload_id: str,
    body: ShareGeneralRequest,
    current_user: CurrentUser,
):
    upload = await require_upload_with_data(upload_id, current_user, min_role="Admin")
    try:
        updated = DatasetSharingService.update_general_access(
            upload_id=upload_id,
            operator_id=current_user.id,
            general_access=body.general_access,
            link_role=body.link_role,
        )
        return JSONResponse(content=safe_jsonable({"ok": True, "shares": updated}))
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspace/{upload_id}/share/regenerate", summary="Regenerate secret share token")
async def api_regenerate_share_token(
    upload_id: str,
    current_user: CurrentUser,
):
    upload = await require_upload_with_data(upload_id, current_user, min_role="Owner")
    try:
        updated = DatasetSharingService.regenerate_share_token(
            upload_id=upload_id,
            operator_id=current_user.id,
        )
        return JSONResponse(content=safe_jsonable({"ok": True, "shares": updated}))
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

