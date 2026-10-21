"""
dataforge/api/repositories/user.py
────────────────────────────────────
User repository: all DB operations for the users table.
"""

from __future__ import annotations
import time
from dataforge.db import db_get, db_first, db_insert, db_update

_USER_CACHE: dict[int, tuple[float, Optional[dict]]] = {}
_EMAIL_CACHE: dict[str, tuple[float, Optional[dict]]] = {}
_CACHE_TTL = 120.0  # 2 minutes

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
        now = time.time()
        cached = _USER_CACHE.get(user_id)
        if cached and (now - cached[0] < _CACHE_TTL):
            return cached[1]
        res = db_get("users", user_id)
        _USER_CACHE[user_id] = (now, res)
        return res

    def get_by_google_id(self, google_id: str) -> Optional[dict]:
        return db_first("users", {"google_id": google_id})

    def get_by_email(self, email: str) -> Optional[dict]:
        clean_email = email.strip().lower() if email else ""
        now = time.time()
        cached = _EMAIL_CACHE.get(clean_email)
        if cached and (now - cached[0] < _CACHE_TTL):
            return cached[1]
        res = db_first("users", {"email": clean_email})
        _EMAIL_CACHE[clean_email] = (now, res)
        return res

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

