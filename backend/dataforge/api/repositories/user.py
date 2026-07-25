"""
dataforge/api/repositories/user.py
────────────────────────────────────
User repository: all DB operations for the users table.
"""

from __future__ import annotations
from typing import Optional
from dataforge.db import db_get, db_first, db_insert, db_update


class UserRepository:

    def get_by_id(self, user_id: int) -> Optional[dict]:
        return db_get("users", user_id)

    def get_by_google_id(self, google_id: str) -> Optional[dict]:
        return db_first("users", {"google_id": google_id})

    def get_by_email(self, email: str) -> Optional[dict]:
        return db_first("users", {"email": email})

    def create(self, data: dict) -> Optional[dict]:
        return db_insert("users", data) or None

    def update(self, user_id: int, data: dict) -> Optional[dict]:
        return db_update("users", user_id, data) or None


user_repo = UserRepository()
