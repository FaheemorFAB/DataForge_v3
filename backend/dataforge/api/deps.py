"""
dataforge/api/deps.py
──────────────────────
FastAPI dependency injection functions.

Every route uses these via Depends():
    current_user = Depends(get_current_user)
    upload_id    = Depends(get_upload_id)
    job_manager  = Depends(get_job_manager_dep)
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import Cookie, Depends, HTTPException, Query, Request, status

from dataforge.api.auth.jwt import get_user_id_from_token
from dataforge.api.config import get_settings
from dataforge.api.jobs.manager import JobManager, get_job_manager
from dataforge.api.repositories.upload import upload_repo
from dataforge.api.services.auth import auth_service
from dataforge.api.storage.manager import exists
from dataforge.api.websocket.manager import ConnectionManager, get_ws_manager
from dataforge.db import User

log = logging.getLogger(__name__)
settings = get_settings()


# ── Authentication ────────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
) -> User:
    """
    Extract and validate the JWT from the 'access_token' HTTP-only cookie.
    Raises 401 if missing or invalid.
    """
    token = access_token

    # Fallback: Bearer token in Authorization header (for API clients)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            user = auth_service.get_user_by_id(user_id)
            if user is not None:
                return user



    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Type alias for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Upload ID ─────────────────────────────────────────────────────────────────

async def get_upload_id(
    request: Request,
    upload_id: Optional[int] = Query(default=None),
) -> Optional[int]:
    """
    Extract upload_id from query string, JSON body, or form data.
    Does NOT validate ownership — use require_upload_access for that.
    """
    if upload_id is not None:
        return upload_id

    # Try JSON body
    try:
        body = await request.json()
        if isinstance(body, dict) and "upload_id" in body:
            return int(body["upload_id"])
    except Exception:
        pass

    # Try form data
    try:
        form = await request.form()
        if "upload_id" in form:
            return int(form["upload_id"])
    except Exception:
        pass

    return None


async def require_upload_access(
    upload_id: int,
    current_user: User,
) -> dict:
    """
    Validate that the upload exists and belongs to the current user.
    Returns the upload record dict.
    Raises 404 or 403 on failure.
    """
    upload = upload_repo.get_by_id(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if upload.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return upload


async def require_upload_with_data(
    upload_id: int,
    current_user: User,
) -> dict:
    """
    Like require_upload_access but also checks that a dataset is loaded.
    """
    upload = await require_upload_access(upload_id, current_user)
    if not exists(upload_id, "df_raw") and not exists(upload_id, "df_clean"):
        raise HTTPException(
            status_code=400,
            detail="No dataset loaded. Please upload a file first.",
        )
    return upload


# ── Infrastructure singletons ─────────────────────────────────────────────────

def get_job_manager_dep() -> JobManager:
    return get_job_manager()


def get_ws_manager_dep() -> ConnectionManager:
    return get_ws_manager()


# ── Rate limiting (via slowapi) ───────────────────────────────────────────────

def get_remote_addr(request: Request) -> str:
    """Extract client IP for rate limiting (proxy-aware)."""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
