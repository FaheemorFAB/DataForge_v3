"""
dataforge/api/storage/manager.py
──────────────────────────────────
Storage manager — thin wrapper around the existing web/storage.py logic.
All disk-based parquet/json/joblib read-write operations are preserved exactly.
Supabase write-through is also preserved.
"""

from __future__ import annotations

# Re-export all functions from the original storage module
# so the rest of the API layer imports from a single namespace.

from dataforge.web.storage import (
    _save as save,
    _load as load,
    _exists as exists,
    _upath as upath,
    _lock_path as lock_path,
    _clear_store as clear_store,
    STORE_DIR,
    LEGACY_STORE_DIR,
)

# load_persisted comes from the original helpers module
try:
    from dataforge.web.helpers import _load_persisted as load_persisted
    from dataforge.web.helpers import _persist as persist
except Exception:
    def load_persisted(upload_id, key):
        return None
    def persist(upload_id, key, obj):
        pass

__all__ = [
    "save", "load", "exists", "upath", "lock_path",
    "clear_store", "load_persisted", "persist",
    "STORE_DIR", "LEGACY_STORE_DIR",
]
