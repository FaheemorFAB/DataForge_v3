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
_LOCAL_USERS: dict[int, dict] = {}
_LOCAL_USERS_BY_EMAIL: dict[str, dict] = {}
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
        if not res and user_id in _LOCAL_USERS:
            res = _LOCAL_USERS[user_id]
        _USER_CACHE[user_id] = (now, res)
        return res

    def get_by_google_id(self, google_id: str) -> Optional[dict]:
        return db_first("users", {"google_id": google_id})

    def get_by_email(self, email: str) -> Optional[dict]:
        clean_email = email.strip().lower() if email else ""
        if not clean_email:
            return None
        now = time.time()
        cached = _EMAIL_CACHE.get(clean_email)
        if cached and (now - cached[0] < _CACHE_TTL):
            return cached[1]
        res = db_first("users", {"email": clean_email})
        if not res and clean_email in _LOCAL_USERS_BY_EMAIL:
            res = _LOCAL_USERS_BY_EMAIL[clean_email]
        _EMAIL_CACHE[clean_email] = (now, res)
        return res

    def create(self, data: dict) -> Optional[dict]:
        clean_data = {k: v for k, v in data.items() if k in VALID_USER_COLUMNS}
        res = db_insert("users", clean_data)
        if not res:
            local_id = clean_data.get("id") or int(time.time() * 1000) % 1_000_000
            res = dict(clean_data)
            res["id"] = local_id

        if "role" in data:
            res["role"] = data["role"]
        if "email" in res:
            clean_email = res["email"].strip().lower()
            _EMAIL_CACHE[clean_email] = (time.time(), res)
            _LOCAL_USERS_BY_EMAIL[clean_email] = res
        if "id" in res:
            _USER_CACHE[res["id"]] = (time.time(), res)
            _LOCAL_USERS[res["id"]] = res
        return res

    def update(self, user_id: int, data: dict) -> Optional[dict]:
        clean_data = {k: v for k, v in data.items() if k in VALID_USER_COLUMNS}
        res = db_update("users", user_id, clean_data)
        if not res and user_id in _LOCAL_USERS:
            res = dict(_LOCAL_USERS[user_id])
            res.update(clean_data)
        _USER_CACHE.pop(user_id, None)
        if "email" in clean_data:
            _EMAIL_CACHE.pop(clean_data["email"].strip().lower(), None)
        if res:
            if "role" in data:
                res["role"] = data["role"]
            if "email" in res:
                clean_email = res["email"].strip().lower()
                _EMAIL_CACHE[clean_email] = (time.time(), res)
                _LOCAL_USERS_BY_EMAIL[clean_email] = res
            if "id" in res:
                _USER_CACHE[res["id"]] = (time.time(), res)
                _LOCAL_USERS[res["id"]] = res
            return res
        return None


user_repo = UserRepository()

