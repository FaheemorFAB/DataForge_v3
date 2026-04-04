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

# ── Storage root (session-local disk) ────────────────────────────────────────
STORE_DIR = Path(os.getenv("DATAFORGE_STORE_DIR",
                            str(Path.home() / ".dataforge_store")))
STORE_DIR.mkdir(exist_ok=True, parents=True)


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
        with FileLock(_lock_path(p_pq)):
            return pd.read_parquet(p_pq)
    p_bin = path.with_suffix('.joblib')
    if p_bin.exists():
        with FileLock(_lock_path(p_bin)):
            return p_bin.read_bytes()
    p_json = path.with_suffix('.json')
    if p_json.exists():
        with FileLock(_lock_path(p_json)):
            return json.loads(p_json.read_text(encoding="utf-8"))
    # legacy pickle fallback removed (security: RCE risk)
    return None


def _exists(upload_id: int, key: str) -> bool:
    """Check whether any format of a stored object exists on disk."""
    path = _upath(upload_id, key)
    return (path.with_suffix('.parquet').exists()
            or path.with_suffix('.json').exists()
            or path.with_suffix('.joblib').exists()
            or path.exists())


def _clear_store(upload_id: int):
    """Remove all stored data for an upload."""
    d = STORE_DIR / str(upload_id)
    if d.exists():
        shutil.rmtree(d)
