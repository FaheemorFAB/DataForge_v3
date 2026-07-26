"""
dataforge/api/repositories/upload.py
──────────────────────────────────────
Upload repository: all DB operations for the uploads table.
"""

from __future__ import annotations
from typing import Optional
from dataforge.db import db_get, db_first, db_all, db_insert, db_update, db_delete, db_count, db_client


class UploadRepository:

    def get_by_id(self, upload_id: int) -> Optional[dict]:
        return db_get("uploads", upload_id)

    def list_for_user(self, user_id: int, limit: int = 50) -> list[dict]:
        return db_all("uploads", {"user_id": user_id}, order_by="uploaded_at", limit=limit)

    def list_recent(self, user_id: int, limit: int = 10) -> list[dict]:
        return db_all("uploads", {"user_id": user_id}, order_by="uploaded_at", limit=limit)

    def find_by_filename(self, user_id: int, filename: str) -> Optional[dict]:
        """Return the most recent upload with the given filename for a user."""
        if not db_client:
            return None
        try:
            res = (db_client.table("uploads")
                   .select("*")
                   .eq("user_id", user_id)
                   .eq("filename", filename)
                   .order("uploaded_at", desc=True)
                   .limit(1)
                   .execute())
            return res.data[0] if res and res.data else None
        except Exception:
            return None

    def create(self, data: dict) -> Optional[dict]:
        res = db_insert("uploads", data)
        return res if res else None

    def update(self, upload_id: int, data: dict) -> Optional[dict]:
        return db_update("uploads", upload_id, data) or None

    def delete(self, upload_id: int) -> bool:
        return db_delete("uploads", upload_id)

    def count_for_user(self, user_id: int) -> int:
        return db_count("uploads", {"user_id": user_id})

    def get_analyses(self, user_id: int, limit: int = 30) -> list[dict]:
        if not db_client:
            return []
        try:
            res = (db_client.table("analyses")
                   .select("*, uploads(filename)")
                   .eq("user_id", user_id)
                   .order("created_at", desc=True)
                   .limit(limit)
                   .execute())
            return res.data if res and res.data else []
        except Exception:
            return []

    def log_analysis(self, user_id: int, upload_id: Optional[int], type_: str, summary: str = "") -> Optional[dict]:
        data = {"user_id": user_id, "upload_id": upload_id, "type": type_, "summary": summary}
        res = db_insert("analyses", data)
        return res if res else None

    def count_analyses(self, user_id: int, type_: Optional[str] = None) -> int:
        match = {"user_id": user_id}
        if type_:
            match["type"] = type_
        return db_count("analyses", match)


upload_repo = UploadRepository()
