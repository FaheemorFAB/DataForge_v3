"""
dataforge/api/services/upload.py
──────────────────────────────────
Upload service: file processing, profiling, storage, and DB logging.
"""

from __future__ import annotations
import json
import logging
from typing import Optional

from dataforge.api.repositories.upload import upload_repo
from dataforge.api.storage.manager import save, persist
from dataforge.api.utils.helpers import df_profile
from dataforge.db import User

log = logging.getLogger(__name__)


class UploadService:

    def process_dataframe(self, df, filename: str, source_type: str,
                          user: User, source_config: Optional[dict] = None) -> dict:
        """
        Profile a DataFrame, log it to DB, save to disk.
        Returns: {"upload_id": int, "profile": dict} or raises on error.
        """
        profile = df_profile(df, filename)
        upload_id = self._log_upload(profile, source_type, user, source_config)
        if not upload_id:
            raise RuntimeError("Failed to create upload record in database")

        save(upload_id, "df_raw", df)
        save(upload_id, "profile", profile)

        # Write-through to Supabase Storage (non-blocking, errors suppressed)
        try:
            persist(upload_id, "df_raw", df)
        except Exception as exc:
            log.warning("Supabase write-through failed for upload %d: %s", upload_id, exc)

        return {"upload_id": upload_id, "profile": profile}

    def _log_upload(self, profile: dict, source_type: str, user: User,
                    source_config: Optional[dict] = None) -> Optional[int]:
        data = {
            "user_id": user.id,
            "filename": profile.get("filename", ""),
            "original_name": profile.get("filename", ""),
            "rows": profile.get("rows", 0),
            "cols": profile.get("cols", 0),
            "missing_pct": profile.get("missing_pct", 0.0),
            "source_type": source_type,
            "storage_path": json.dumps(source_config) if source_config and source_type != "csv" else None,
        }
        res = upload_repo.create(data)
        return res.get("id") if res else None

    def check_duplicate(self, user_id: int, filename: str) -> Optional[dict]:
        """Return existing upload info if a file with the same name was already uploaded."""
        from dataforge.api.storage.manager import load
        from dataforge.api.utils.helpers import time_ago

        existing = upload_repo.find_by_filename(user_id, filename)
        if not existing:
            return None

        upload_id = existing.get("id")
        profile = load(upload_id, "profile") or {}
        return {
            "duplicate": True,
            "upload_id": upload_id,
            "filename": existing.get("filename"),
            "rows": existing.get("rows", 0),
            "cols": existing.get("cols", 0),
            "numeric": profile.get("numeric", 0),
            "missing_pct": existing.get("missing_pct", 0),
            "time_ago": time_ago(existing.get("uploaded_at")),
            "has_clean": bool(profile.get("clean_cols") or existing.get("clean_meta_json")),
        }


upload_service = UploadService()
