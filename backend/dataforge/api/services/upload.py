"""
dataforge/api/services/upload.py
──────────────────────────────────
Upload service: file processing, profiling, storage, and DB logging.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from dataforge.api.repositories.upload import upload_repo
from dataforge.api.storage.manager import save, persist
from dataforge.api.utils.helpers import df_profile
from dataforge.db import User

log = logging.getLogger(__name__)


class UploadService:

    def process_dataframe(self, df, filename: str, source_type: str,
                          user: User, source_config: Optional[dict] = None,
                          org_id: Optional[str] = None) -> dict:
        """
        Profile a DataFrame, log it to DB, save to disk.
        Returns: {"upload_id": int, "profile": dict} or raises on error.
        """
        profile = df_profile(df, filename)
        upload_id = self._log_upload(profile, source_type, user, source_config, org_id=org_id)
        if not upload_id:
            raise RuntimeError("Failed to create upload record in database")

        meta = {
            "id": upload_id,
            "user_id": user.id,
            "user_email": getattr(user, "email", None),
            "user_name": getattr(user, "name", None),
            "filename": filename,
            "source_type": source_type,
            "rows": profile.get("rows", len(df)),
            "cols": profile.get("cols", len(df.columns)),
            "storage_path": json.dumps(source_config) if source_config else None,
            "source_config": source_config,
            "org_id": org_id,
            "workspace_id": org_id if org_id else "personal",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        save(upload_id, "meta", meta)
        save(upload_id, "df_raw", df)
        save(upload_id, "profile", profile)

        # Write-through to Supabase Storage (non-blocking, errors suppressed)
        try:
            persist(upload_id, "df_raw", df)
        except Exception as exc:
            log.warning("Supabase write-through failed for upload %s: %s", upload_id, exc)

        return {"upload_id": upload_id, "profile": profile}

    def _log_upload(self, profile: dict, source_type: str, user: User,
                    source_config: Optional[dict] = None,
                    org_id: Optional[str] = None) -> Optional[str]:
        import uuid
        local_id = f"df_{uuid.uuid4().hex[:10]}"
        user_id = getattr(user, "id", None)
        # If user is local dev user (id=1 or integer), remote Supabase users FK constraint (23503)
        # will fail after a slow HTTPS roundtrip. Use local_id immediately.
        if user_id == 1 or not isinstance(user_id, str):
            return local_id

        data = {
            "user_id": user_id,
            "filename": profile.get("filename", ""),
            "original_name": profile.get("filename", ""),
            "rows": profile.get("rows", 0),
            "cols": profile.get("cols", 0),
            "missing_pct": profile.get("missing_pct", 0.0),
            "source_type": source_type,
            "storage_path": json.dumps(source_config) if source_config and source_type != "csv" else None,
            "org_id": org_id,
            "workspace_id": org_id if org_id else "personal",
        }
        res = upload_repo.create(data)
        if res and res.get("id"):
            return str(res.get("id"))
        return local_id

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
