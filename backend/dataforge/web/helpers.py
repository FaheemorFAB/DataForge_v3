"""
DataForge — Shared Helpers
══════════════════════════
Utility functions shared across app.py and route blueprints.
Extracted to avoid circular imports.
"""

import json
import math
import numpy as np
import pandas as pd
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import request, jsonify
from flask_login import current_user

from dataforge.db import (db_client, db_get, db_first, db_all, db_insert,
                          db_update, db_delete, db_count)
from dataforge.db import Upload
from dataforge.settings import PROJECTS_DIR

from .storage import _save, _load, _exists, _upath, _clear_store

# ── Supabase Storage (graceful fallback to local disk) ────────────────────────
try:
    from dataforge.supabase_storage import get_store, STORAGE_OK
except ImportError:
    STORAGE_OK = False
    def get_store(): return None

# ── Redis cache helpers ───────────────────────────────────────────────────────
try:
    from .cache import (
        get_profile, set_profile,
        get_schema, set_schema,
        get_clean_meta, set_clean_meta,
        get_alert_status, set_alert_status,
        get_user_metrics, set_user_metrics,
        invalidate_upload, invalidate_user,
        rate_limit as _rate_limit,
    )
    CACHE_OK = True
except ImportError:
    CACHE_OK = False
    def get_profile(uid): return None
    def set_profile(uid, p): pass
    def get_schema(uid): return None
    def set_schema(uid, s): pass
    def get_clean_meta(uid): return None
    def set_clean_meta(uid, m): pass
    def get_alert_status(uid): return None
    def set_alert_status(uid, s): pass
    def get_user_metrics(uid): return None
    def set_user_metrics(uid, m): pass
    def invalidate_upload(uid): pass
    def invalidate_user(uid): pass
    def _rate_limit(uid, action, limit=3, window_s=60): return True

# ── Module imports ─────────────────────────────────────────────────────────────
from dataforge.data_cleaner   import run_cleaning_pipeline
from dataforge.eda_report     import generate_eda_report
from dataforge.automl_trainer import run_automl, _detect_task
from dataforge.gemini_pipeline import run_query_pipeline, is_available as gemini_available

# ── Reporting engine ────────────────────────────────────────────────────────────
try:
    from dataforge.insight_engine  import detect_schema, run_insights, summarise_with_gemini, build_report_text
    from dataforge.report_generator import generate_html_report
    from dataforge.alert_engine     import AlertEngine
    REPORTING_ENABLED = True
except ImportError as _re:
    REPORTING_ENABLED = False
    print(f"[WARN] Reporting engine not loaded: {_re}")

# ── Transform Engine & Root Cause Analysis ────────────────────────────────────
try:
    from dataforge.transform_engine import apply_transforms
    from dataforge.root_cause import run_root_cause
    TRANSFORM_ENABLED = True
except ImportError as _te:
    TRANSFORM_ENABLED = False
    print(f"[WARN] Transform engine not loaded: {_te}")

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE PERSISTENCE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_upload_user_id(upload_id: int):
    """Return the user_id for an Upload row."""
    try:
        up = db_get("uploads", upload_id)
        return up.get("user_id") if up else None
    except Exception:
        return None


def _get_filename(upload_id: int) -> str:
    """Fetch the filename from the cached profile or DB."""
    p = _load(upload_id, "profile") or {}
    return p.get("filename", "")


def _persist(upload_id: int, key: str, obj):
    """
    Write-through storage: always saves to local disk, also pushes to
    Supabase Storage when configured.
    """
    from flask import current_app
    d = PROJECTS_DIR / str(upload_id)
    d.mkdir(exist_ok=True)
    if isinstance(obj, pd.DataFrame):
        if len(obj) > 2_000_000:
            raise ValueError("Dataset too large (exceeds 2M rows limit)")
        obj.to_parquet(d / f"{key}.parquet", index=False, compression="snappy")
    elif isinstance(obj, bytes):
        (d / f"{key}.joblib").write_bytes(obj)
    else:
        with open(d / f"{key}.json", "w", encoding="utf-8") as f:
            json.dump(obj, f, default=str)

    if STORAGE_OK:
        try:
            user_id = _get_upload_user_id(upload_id)
            if user_id is None:
                return
            store = get_store()
            if key in ("df_raw", "df_clean") and isinstance(obj, pd.DataFrame):
                csv_key = "raw" if key == "df_raw" else "clean"
                path    = store.upload_dataframe(user_id, upload_id, obj, csv_key)
            elif isinstance(obj, bytes):
                path = store.upload_joblib(user_id, upload_id, key, obj)
            else:
                path = store.upload_json(user_id, upload_id, key, obj)

            if key == "df_raw":
                try:
                    db_update("uploads", upload_id, {"storage_path": path})
                except Exception:
                    pass
        except Exception as _exc:
            current_app.logger.warning("Supabase _persist failed (key=%s): %s", key, _exc)


def _load_persisted(upload_id: int, key: str):
    """
    Load persisted data: tries local disk first, falls back to Supabase Storage.
    On Supabase hit, re-caches locally.
    """
    from flask import current_app
    d = PROJECTS_DIR / str(upload_id)
    p_pq = d / f"{key}.parquet"
    if p_pq.exists():
        try: return pd.read_parquet(p_pq)
        except Exception: pass

    p_bin = d / f"{key}.joblib"
    if p_bin.exists():
        try: return p_bin.read_bytes()
        except Exception: pass

    p_json = d / f"{key}.json"
    if p_json.exists():
        try:
            with open(p_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass

    # legacy pickle fallback removed (security: RCE risk)

    if STORAGE_OK:
        try:
            user_id = _get_upload_user_id(upload_id)
            if user_id is None:
                return None
            store = get_store()
            if key in ("df_raw", "df_clean"):
                csv_key = "raw" if key == "df_raw" else "clean"
                spath   = f"users/{user_id}/uploads/{upload_id}/{csv_key}.parquet"
                obj     = store.download_dataframe(spath)
            else:
                spath_json = f"users/{user_id}/uploads/{upload_id}/{key}.json"
                obj = store.download_json(spath_json)
                if obj is None:
                    spath_joblib = f"users/{user_id}/uploads/{upload_id}/{key}.joblib"
                    obj = store.download_joblib(spath_joblib)

            if obj is not None:
                d.mkdir(exist_ok=True)
                if isinstance(obj, pd.DataFrame):
                    obj.to_parquet(d / f"{key}.parquet", index=False, compression="snappy")
                elif isinstance(obj, bytes):
                    (d / f"{key}.joblib").write_bytes(obj)
                else:
                    with open(d / f"{key}.json", "w", encoding="utf-8") as f:
                        json.dump(obj, f, default=str)
                current_app.logger.info("Restored %s/%s from Supabase Storage.", upload_id, key)
            return obj
        except Exception as _exc:
            current_app.logger.warning("Supabase _load_persisted failed (key=%s): %s", key, _exc)

    return None


def _project_meta(upload_id: int) -> dict:
    d = PROJECTS_DIR / str(upload_id)
    return {
        "has_raw":   (d / "df_raw.parquet").exists() or (d / "df_raw").exists(),
        "has_clean": (d / "df_clean.parquet").exists() or (d / "df_clean").exists(),
        "has_eda":   (d / "eda_html").exists(),
        "has_model": (d / "model_pkl.joblib").exists() or (d / "model_pkl").exists(),
        "has_chat":  (d / "chat_history.json").exists() or (d / "chat_history").exists(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_upload_id() -> int | None:
    if request.is_json:
        body = request.get_json(silent=True)
        if body and "upload_id" in body:
            return int(body["upload_id"])
    if "upload_id" in request.form:
        return int(request.form["upload_id"])
    if "upload_id" in request.args:
        return int(request.args["upload_id"])
    return None


def _get_upload_or_403(upload_id: int):
    data = db_get("uploads", upload_id)
    if not data or data.get("user_id") != current_user.id:
        return None, (jsonify({"error": "Unauthorized"}), 403)
    return Upload(**data), None


def _require_df(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        upload_id = _get_upload_id()
        if upload_id is None:
            return jsonify({"error": "upload_id required"}), 400
        upload, err = _get_upload_or_403(upload_id)
        if err:
            return err
        if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
            return jsonify({"error": "No dataset loaded. Please upload a CSV first."}), 400
        kwargs["upload_id"] = upload_id
        return fn(*args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# DB LOGGING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# ws_push will be set by app.py after the SocketIO object is created
_ws_push_fn = None

def set_ws_push(fn):
    """Called by app.py to inject the _ws_push function."""
    global _ws_push_fn
    _ws_push_fn = fn


def _db_log_upload(profile: dict, source_type: str = "csv", source_config: dict | None = None) -> int | None:
    """Save an upload record to DB. Returns upload.id or None."""
    from flask import current_app
    if not current_user.is_authenticated:
        return None
    try:
        up_dict = {
            "user_id": current_user.id,
            "filename": profile.get("filename", ""),
            "original_name": profile.get("filename", ""),
            "rows": profile.get("rows", 0),
            "cols": profile.get("cols", 0),
            "missing_pct": profile.get("missing_pct", 0.0),
            "source_type": source_type,
            "storage_path": json.dumps(source_config) if source_config and source_type != "csv" else None,
        }
        res = db_insert("uploads", up_dict)
        return res.get("id")
    except Exception as e:
        current_app.logger.warning("Failed to log upload: %s", e)
        return None


def _db_log_analysis(type_: str, summary: str = ""):
    """Save an analysis record to DB and push real-time WS event."""
    from flask import current_app
    if not current_user.is_authenticated:
        return
    try:
        upload_id = _get_upload_id()
        an_dict = {
            "user_id": current_user.id,
            "upload_id": upload_id,
            "type": type_,
            "summary": summary,
        }
        res = db_insert("analyses", an_dict)
        uid = current_user.id
        if _ws_push_fn:
            _ws_push_fn("activity", {
                "type":     type_,
                "summary":  summary,
                "filename": _get_filename(upload_id) if upload_id else "",
                "ts":       datetime.utcnow().isoformat(),
                "analysis_id": res.get("id"),
            }, user_id=uid)
            _ws_push_fn("stats_update", {
                "uploads":  db_count("uploads", {"user_id": uid}),
                "analyses": db_count("analyses", {"user_id": uid}),
                "models":   db_count("analyses", {"user_id": uid, "type": "automl"}),
                "queries":  db_count("analyses", {"user_id": uid, "type": "query"}),
            }, user_id=uid)
    except Exception as e:
        current_app.logger.warning("Failed to log analysis: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# DATAFRAME HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _df_profile(df: pd.DataFrame, filename: str = "") -> dict:
    missing     = int(df.isnull().sum().sum())
    numeric_cnt = int(len(df.select_dtypes(include=np.number).columns))
    total_cells = df.shape[0] * df.shape[1]
    miss_pct    = round(missing / max(total_cells, 1) * 100, 1)
    columns = []
    for col, dtype in zip(df.columns, df.dtypes):
        null_pct = round(df[col].isnull().mean() * 100, 1)
        columns.append({"name": col, "dtype": str(dtype),
                        "null_pct": null_pct, "quality": round(100 - null_pct, 1)})
    return {"filename": filename, "rows": df.shape[0], "cols": df.shape[1],
            "numeric": numeric_cnt, "missing": missing, "missing_pct": miss_pct,
            "columns": columns}


def _safe_json_value(v):
    if isinstance(v, np.integer):   return int(v)
    if isinstance(v, np.floating):  return None if np.isnan(v) else float(v)
    if isinstance(v, np.bool_):     return bool(v)
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return None
    if isinstance(v, pd.Timestamp): return v.isoformat() if not pd.isna(v) else None
    try:
        if pd.isna(v): return None
    except (TypeError, ValueError):
        pass
    return v


def _df_to_json_rows(df: pd.DataFrame, limit: int = 500) -> dict:
    total = len(df)
    preview_df = df.head(limit).replace([np.inf, -np.inf], None)
    headers = [str(c) for c in preview_df.columns]
    rows = [[_safe_json_value(v) for v in row] for _, row in preview_df.iterrows()]
    return {
        "headers": headers,
        "rows": rows,
        "loaded": len(preview_df),
        "total": total,
        "preview_only": total > len(preview_df),
    }


def _time_ago(dt: datetime) -> str:
    diff = datetime.utcnow() - dt
    s = int(diff.total_seconds())
    if s < 60:    return "just now"
    if s < 3600:  return f"{s//60}m ago"
    if s < 86400: return f"{s//3600}h ago"
    if s < 604800: return f"{s//86400}d ago"
    return dt.strftime("%b %d")


# ══════════════════════════════════════════════════════════════════════════════
# CELERY TASK HELPERS
# ══════════════════════════════════════════════════════════════════════════════
_TASKS_CACHE = None
SYNC_FALLBACK_ENABLED = True  # Will be overridden by app.py


def _tasks():
    global _TASKS_CACHE
    if _TASKS_CACHE is not None:
        return _TASKS_CACHE

    try:
        from .tasks import (task_run_insights, task_run_automl,
                            task_run_eda, task_generate_report, task_check_alerts)
    except Exception:
        try:
            from dataforge.web.tasks import (task_run_insights, task_run_automl,
                                             task_run_eda, task_generate_report, task_check_alerts)
        except Exception:
            from tasks import (task_run_insights, task_run_automl,
                               task_run_eda, task_generate_report, task_check_alerts)
    _TASKS_CACHE = (task_run_insights, task_run_automl,
                    task_run_eda, task_generate_report, task_check_alerts)
    return _TASKS_CACHE


def _run_task_sync(task, args: list):
    """Execute a Celery task inline and return its result."""
    eager = task.apply(args=args)
    return eager.get(propagate=True)


def _persist_insights(upload_id, user_id, insights):
    from flask import current_app
    try:
        db_client.table("insight_records").delete().eq("upload_id", upload_id).execute()

        insert_data = []
        for ins in insights:
            insert_data.append({
                "upload_id": upload_id,
                "user_id": user_id,
                "type": ins.get("type", ""),
                "title": ins.get("title", ""),
                "description": ins.get("description", ""),
                "importance": ins.get("importance", 0.0),
                "chart_type": ins.get("chart"),
                "metric": ins.get("metric", ""),
                "chart_data": json.dumps(ins.get("chart_data")) if ins.get("chart_data") else None,
            })
        if insert_data:
            db_client.table("insight_records").insert(insert_data).execute()
    except Exception as e:
        current_app.logger.warning("Failed to bulk persist insights: %s", e)
