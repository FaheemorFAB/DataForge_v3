"""
dataforge/api/services/auth.py
────────────────────────────────
Auth service: login, OAuth, token issuance.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional

from dataforge.api.auth.jwt import create_access_token
from dataforge.api.config import get_settings
from dataforge.api.repositories.user import user_repo
from dataforge.db import User

settings = get_settings()


class AuthService:

    def create_token_for_user(self, user: User) -> str:
        """Issue a JWT access token for a User model instance."""
        return create_access_token(user.id)

    def get_or_create_google_user(self, userinfo: dict) -> Optional[User]:
        """
        Look up a user by Google sub ID or email. Creates a new record if not found.
        Links google_id if user exists by email.
        Returns a User model, or None on DB failure.
        """
        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        if not google_id and not email:
            return None

        existing = None
        if google_id:
            existing = user_repo.get_by_google_id(google_id)
        if existing is None and email:
            existing = user_repo.get_by_email(email)

        if existing is None:
            new_data = {
                "google_id": google_id,
                "email": email,
                "name": userinfo.get("name"),
                "avatar": userinfo.get("picture"),
            }
            res = user_repo.create(new_data)
            if not res:
                return None
            return User(**res)

        # Update last-login + profile info + link google_id
        update_fields = {
            "google_id": google_id or existing.get("google_id"),
            "name": userinfo.get("name") or existing.get("name"),
            "avatar": userinfo.get("picture") or existing.get("avatar"),
            "last_login": datetime.now(timezone.utc).isoformat(),
        }
        user_repo.update(existing["id"], update_fields)
        refreshed = user_repo.get_by_id(existing["id"])
        return User(**(refreshed or existing))

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        data = user_repo.get_by_id(user_id)
        return User(**data) if data else None

    def get_mock_user(self) -> Optional[User]:
        """Dev-only: return user with id=1."""
        data = user_repo.get_by_id(1)
        return User(**data) if data else None


auth_service = AuthService()
