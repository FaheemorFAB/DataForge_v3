"""
dataforge/api/repositories/user.py
────────────────────────────────────
User repository: all DB operations for the users table.
"""

from __future__ import annotations
from typing import Optional
from dataforge.db import db_get, db_first, db_insert, db_update


VALID_USER_COLUMNS = {
    "id",
    "email",
    "name",
    "avatar",
    "google_id",
    "oauth_provider",
    "oauth_sub",
    "created_at",
    "last_login",
    "is_active",
    "storage_quota_mb",
}


class UserRepository:

    def get_by_id(self, user_id: int) -> Optional[dict]:
        return db_get("users", user_id)

    def get_by_google_id(self, google_id: str) -> Optional[dict]:
        return db_first("users", {"google_id": google_id})

    def get_by_email(self, email: str) -> Optional[dict]:
        return db_first("users", {"email": email})

    def create(self, data: dict) -> Optional[dict]:
        clean_data = {k: v for k, v in data.items() if k in VALID_USER_COLUMNS}
        res = db_insert("users", clean_data)
        if res:
            if "role" in data:
                res["role"] = data["role"]
            return res
        return None

    def update(self, user_id: int, data: dict) -> Optional[dict]:
        clean_data = {k: v for k, v in data.items() if k in VALID_USER_COLUMNS}
        res = db_update("users", user_id, clean_data)
        if res:
            if "role" in data:
                res["role"] = data["role"]
            return res
        return None


user_repo = UserRepository()

