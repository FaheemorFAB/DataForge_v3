"""
DataForge — Shared Storage Module
══════════════════════════════════
Unified read/write helpers for session-local DataFrame & metadata storage.

Previously duplicated across app.py and tasks.py. Now both import from here.
"""

import json
import os
import shutil
from pathlib import Path

import pandas as pd
from filelock import FileLock
from dataforge.settings import PROJECTS_DIR


def _resolve_store_dir() -> Path:
    """Choose a writable primary store directory."""
    configured = os.getenv("DATAFORGE_STORE_DIR") or os.getenv("DATAFORGE_PROJECTS_DIR")
    candidates = [Path(configured).expanduser()] if configured else [PROJECTS_DIR]
    for candidate in candidates:
        try:
            candidate.mkdir(exist_ok=True, parents=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    return PROJECTS_DIR

# ── Storage root (session-local disk) ────────────────────────────────────────
STORE_DIR = _resolve_store_dir()
STORE_DIR.mkdir(exist_ok=True, parents=True)
LEGACY_STORE_DIR = PROJECTS_DIR
LEGACY_STORE_DIR.mkdir(exist_ok=True, parents=True)


def _legacy_upath(upload_id: int, key: str) -> Path:
    """Return the legacy projects-dir path for older uploads."""
    d = LEGACY_STORE_DIR / str(upload_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / key


def _materialized_path(path: Path) -> Path | None:
    """Return the concrete stored file path for a base key, if present."""
    for ext in (".parquet", ".json", ".joblib", ""):
        candidate = path.with_suffix(ext) if ext else path
        if candidate.exists():
            return candidate
    return None


def _load_from_remote(upload_id: int, key: str):
    """Best-effort restore from Supabase storage for persisted uploads."""
    if key not in ("df_raw", "df_clean", "profile", "clean_meta", "automl_meta",
                   "chat_history", "last_insights", "last_schema", "last_summary",
                   "eda_html", "model_pkl"):
        return None
    try:
        from dataforge.db import db_get
        from dataforge.supabase_storage import get_store, STORAGE_OK
    except Exception:
        return None
    if not STORAGE_OK:
        return None

    up = db_get("uploads", upload_id)
    user_id = up.get("user_id") if up else None
    if user_id is None:
        return None

    try:
        store = get_store()
        if key in ("df_raw", "df_clean"):
            remote_key = "raw" if key == "df_raw" else "clean"
            obj = store.download_dataframe(f"users/{user_id}/uploads/{upload_id}/{remote_key}.parquet")
        elif key == "eda_html":
            obj = store.download_html(f"users/{user_id}/uploads/{upload_id}/{key}.html")
        elif key == "model_pkl":
            obj = store.download_joblib(f"users/{user_id}/uploads/{upload_id}/{key}.joblib")
        else:
            obj = store.download_json(f"users/{user_id}/uploads/{upload_id}/{key}.json")
        if obj is not None:
            _save(upload_id, key, obj)
        return obj
    except Exception:
        return None


def _upath(upload_id: int, key: str) -> Path:
    """Return the base path for a given upload_id / key pair."""
    d = STORE_DIR / str(upload_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / key


def _lock_path(path: Path) -> Path:
    """Return the advisory lockfile path for a given data file."""
    return path.with_suffix(path.suffix + ".lock")


def _save(upload_id: int, key: str, obj):
    """Atomically write an object to disk (DataFrame → Parquet, bytes → joblib, else → JSON)."""
    path = _upath(upload_id, key)
    lock = FileLock(_lock_path(path))
    with lock:
        if isinstance(obj, pd.DataFrame):
            if len(obj) > 2_000_000:
                raise ValueError("Dataset too large (exceeds 2M rows limit)")
            tmp = path.with_suffix(".parquet.tmp")
            obj.to_parquet(tmp, index=False, compression="snappy")
            tmp.replace(path.with_suffix(".parquet"))
        elif isinstance(obj, bytes):
            tmp = path.with_suffix(".joblib.tmp")
            tmp.write_bytes(obj)
            tmp.replace(path.with_suffix(".joblib"))
        else:
            tmp = path.with_suffix(".json.tmp")
            path_final = path.with_suffix(".json")
            tmp.write_text(json.dumps(obj, default=str), encoding="utf-8")
            tmp.replace(path_final)


def _load(upload_id: int, key: str):
    """Load an object from disk: tries Parquet, joblib, JSON in order. Returns None on miss."""
    path = _upath(upload_id, key)
    p_pq = path.with_suffix('.parquet')
    if p_pq.exists():
        try:
            with FileLock(_lock_path(p_pq)):
                return pd.read_parquet(p_pq)
        except Exception:
            pass
    p_bin = path.with_suffix('.joblib')
    if p_bin.exists():
        try:
            with FileLock(_lock_path(p_bin)):
                return p_bin.read_bytes()
        except Exception:
            pass
    p_json = path.with_suffix('.json')
    if p_json.exists():
        try:
            with FileLock(_lock_path(p_json)):
                return json.loads(p_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    legacy_path = _legacy_upath(upload_id, key)
    legacy_pq = legacy_path.with_suffix('.parquet')
    if legacy_pq.exists():
        try:
            with FileLock(_lock_path(legacy_pq)):
                obj = pd.read_parquet(legacy_pq)
            _save(upload_id, key, obj)
            return obj
        except Exception:
            pass
    legacy_bin = legacy_path.with_suffix('.joblib')
    if legacy_bin.exists():
        try:
            with FileLock(_lock_path(legacy_bin)):
                obj = legacy_bin.read_bytes()
            _save(upload_id, key, obj)
            return obj
        except Exception:
            pass
    legacy_json = legacy_path.with_suffix('.json')
    if legacy_json.exists():
        try:
            with FileLock(_lock_path(legacy_json)):
                obj = json.loads(legacy_json.read_text(encoding="utf-8"))
            _save(upload_id, key, obj)
            return obj
        except Exception:
            pass

    remote_obj = _load_from_remote(upload_id, key)
    if remote_obj is not None:
        return remote_obj

    # legacy pickle fallback removed (security: RCE risk)
    return None


def _exists(upload_id: int, key: str) -> bool:
    """Check whether any format of a stored object exists on disk."""
    path = _upath(upload_id, key)
    return (path.with_suffix('.parquet').exists()
            or path.with_suffix('.json').exists()
            or path.with_suffix('.joblib').exists()
            or path.exists()
            or _materialized_path(_legacy_upath(upload_id, key)) is not None)


def _clear_store(upload_id: int):
    """Remove all stored data for an upload."""
    d = STORE_DIR / str(upload_id)
    if d.exists():
        shutil.rmtree(d)
