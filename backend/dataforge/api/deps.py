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

def _resolve_supabase_user(token: str) -> Optional[User]:
    """Resolve a User instance from a Supabase JWT token or header."""
    import time
    from jose import jwt
    from dataforge.api.repositories.user import user_repo
    from dataforge.db import db_client

    email: Optional[str] = None
    # Method A: Use Supabase client if connected
    if db_client:
        try:
            resp = db_client.auth.get_user(token)
            if resp and resp.user and resp.user.email:
                email = resp.user.email
            else:
                return None
        except Exception:
            return None

    # Method B: Fallback to token claims only if db_client is not configured
    if not email:
        try:
            claims = jwt.get_unverified_claims(token)
            # Verify expiration
            exp = claims.get("exp")
            if exp and float(exp) < time.time():
                return None
            email = claims.get("email")
        except Exception:
            return None

    if email:
        user_dict = user_repo.get_by_email(email)
        if user_dict:
            return User(**user_dict)
        # Create user record if missing
        new_data = {
            "email": email,
            "name": email.split("@")[0],
            "avatar": "/avatars/avatar-1.svg",
        }
        res = user_repo.create(new_data)
        if res:
            user_obj = User(**res)
            user_obj.role = "Admin"
            return user_obj
        return User(id=abs(hash(email)) % 100000 + 100, email=email, name=email.split("@")[0], role="Admin")

    return None


async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
) -> User:
    """
    Extract and validate the JWT from Authorization header, query token, or cookies.
    Raises 401 if token is invalid or expired.
    If no token is supplied, falls back to dev user ONLY when ENABLE_DEV_AUTH is True and not in production.
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    query_token = request.query_params.get("token")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif query_token:
        token = query_token.strip()
    elif isinstance(access_token, str) and access_token:
        token = access_token.strip()
    elif hasattr(request, "cookies"):
        token = (
            request.cookies.get("access_token")
            or request.cookies.get("df_access_token")
            or request.cookies.get("token")
        )
        if token:
            token = token.strip()

    if token in ("null", "undefined", '""', "''", ""):
        token = None

    if token:
        # 1. Standard DataForge JWT
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            user = auth_service.get_user_by_id(user_id)
            if user is not None:
                request.state.user_id = user.id
                return user

        # 2. Supabase JWT
        supa_user = _resolve_supabase_user(token)
        if supa_user is not None:
            request.state.user_id = supa_user.id
            return supa_user

        # Token was explicitly provided but failed validation — must reject fail-closed!
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Development / Local environment fallback (must be explicitly enabled and only when NO token provided)
    if not settings.PRODUCTION and settings.ENABLE_DEV_AUTH:
        dev_user = auth_service.get_user_by_id(1) or auth_service.get_mock_user()
        if not dev_user:
            dev_user = User(id=1, email="9256fa@gmail.com", name="DataForge Developer", role="Admin")
        request.state.user_id = dev_user.id
        return dev_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
) -> Optional[User]:
    """
    Extract and validate JWT if present (Bearer header, query token, or cookie).
    Returns User if valid, or dev user if in development and no token was provided, otherwise None.
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    query_token = request.query_params.get("token")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif query_token:
        token = query_token.strip()
    elif isinstance(access_token, str) and access_token:
        token = access_token.strip()
    elif hasattr(request, "cookies"):
        token = (
            request.cookies.get("access_token")
            or request.cookies.get("df_access_token")
            or request.cookies.get("token")
        )
        if token:
            token = token.strip()

    if token in ("null", "undefined", '""', "''", ""):
        token = None

    if token:
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            user = auth_service.get_user_by_id(user_id)
            if user is not None:
                request.state.user_id = user.id
                return user

        supa_user = _resolve_supabase_user(token)
        if supa_user is not None:
            request.state.user_id = supa_user.id
            return supa_user

        # Token was invalid/expired
        return None

    if not settings.PRODUCTION and settings.ENABLE_DEV_AUTH:
        dev_user = auth_service.get_user_by_id(1) or auth_service.get_mock_user()
        if not dev_user:
            dev_user = User(id=1, email="9256fa@gmail.com", name="DataForge Developer", role="Admin")
        request.state.user_id = dev_user.id
        return dev_user

    return None


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[Optional[User], Depends(get_optional_current_user)]


# ── Upload ID ─────────────────────────────────────────────────────────────────

async def get_upload_id(
    request: Request,
    upload_id: Optional[str] = Query(default=None),
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
    upload_id: str,
    current_user: User,
    min_role: str = "Viewer",
    share_token: Optional[str] = None,
    request: Optional[Request] = None,
) -> dict:
    """
    Validate that the upload exists and the user has permission to access it.
    Supports Owner access, invited email collaborators, and share links (Google Sheets parity).
    Raises 401 if unauthenticated, 404 if not found, 403 on permission violation.
    """
    if not share_token and request:
        share_token = request.headers.get("x-share-token") or request.query_params.get("share_token")

    if not current_user:
        if share_token:
            from dataforge.api.services.sharing import DatasetSharingService
            from dataforge.api.storage.manager import load
            upload = upload_repo.get_by_id(upload_id) or load(upload_id, "meta") or {"id": upload_id}
            owner_id = upload.get("user_id") if isinstance(upload, dict) else None
            allowed, eff_role = DatasetSharingService.check_access(
                upload_id=upload_id,
                user=None,
                owner_id=owner_id,
                min_role=min_role,
                share_token=share_token,
            )
            if allowed:
                return upload
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from dataforge.api.services.sharing import DatasetSharingService
    from dataforge.api.storage.manager import STORE_DIR, exists, load

    upload = upload_repo.get_by_id(upload_id)
    if not upload:
        meta = load(upload_id, "meta")
        if meta and isinstance(meta, dict):
            owner_id = meta.get("user_id")
            owner_email = (meta.get("user_email") or "").strip().lower()
            current_email = (getattr(current_user, "email", None) or "").strip().lower()

            is_owner = (
                (str(owner_id) == str(current_user.id))
                or (bool(current_email) and owner_email == current_email)
                or (not settings.PRODUCTION and (current_user.id == 1 or owner_id == 1))
            )
            if is_owner:
                return meta
            # Check sharing permissions
            allowed, eff_role = DatasetSharingService.check_access(
                upload_id=upload_id,
                user=current_user,
                owner_id=owner_id,
                min_role=min_role,
                share_token=share_token,
            )
            if allowed:
                return meta
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: this dataset requires '{min_role}' permission (your access: '{eff_role}')",
            )

        t_dir = STORE_DIR / str(upload_id) / "tables"
        has_local_data = exists(upload_id, "df_raw") or exists(upload_id, "df_clean") or (t_dir.exists() and any(t_dir.glob("*.parquet")))
        if has_local_data:
            if not settings.PRODUCTION:
                return meta if meta and isinstance(meta, dict) else {"id": upload_id, "user_id": current_user.id}
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: unverified dataset ownership",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    owner_id = upload.get("user_id")
    current_email = (getattr(current_user, "email", None) or "").strip().lower()
    meta_for_email = load(upload_id, "meta") if not upload.get("user_email") else upload
    owner_email = (meta_for_email.get("user_email") or "").strip().lower() if meta_for_email else ""
    is_owner = (
        (str(owner_id) == str(current_user.id))
        or (bool(current_email) and owner_email == current_email)
        or (not settings.PRODUCTION and (current_user.id == 1 or owner_id == 1))
    )
    if is_owner:
        return upload

    # Check collaborator / share link access
    allowed, eff_role = DatasetSharingService.check_access(
        upload_id=upload_id,
        user=current_user,
        owner_id=owner_id,
        min_role=min_role,
        share_token=share_token,
    )
    if allowed:
        return upload

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied: this dataset requires '{min_role}' permission (your access: '{eff_role}')",
    )


async def require_upload_with_data(
    upload_id: str,
    current_user: User,
    min_role: str = "Viewer",
    share_token: Optional[str] = None,
    request: Optional[Request] = None,
) -> dict:
    """
    Like require_upload_access but also checks that a dataset is loaded.
    """
    if not share_token and request:
        share_token = request.headers.get("x-share-token") or request.query_params.get("share_token")
    upload = await require_upload_access(upload_id, current_user, min_role=min_role, share_token=share_token, request=request)
    if not exists(upload_id, "df_raw") and not exists(upload_id, "df_clean"):
        from dataforge.api.storage.manager import load
        # Attempt to restore from Supabase if it exists there
        if load(upload_id, "df_raw") is None and load(upload_id, "df_clean") is None:
            print("DEBUG: deps 400 - No dataset loaded (load returned None)")
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

import ipaddress
from functools import lru_cache

@lru_cache(maxsize=32)
def _is_trusted_proxy_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        for proxy_spec in settings.TRUSTED_PROXIES:
            try:
                if "/" in proxy_spec:
                    if ip in ipaddress.ip_network(proxy_spec, strict=False):
                        return True
                elif ip == ipaddress.ip_address(proxy_spec):
                    return True
            except ValueError:
                continue
    except ValueError:
        pass
    return False


def get_remote_addr(request: Request) -> str:
    """
    Extract client IP for rate limiting and security auditing.
    Prevents X-Forwarded-For spoofing:
      1. If direct peer (client.host) is NOT a trusted proxy, return peer IP directly.
      2. If direct peer IS a trusted proxy:
         - Check Cloudflare CF-Connecting-IP first.
         - Otherwise, walk X-Forwarded-For from right to left and return the
           first untrusted hop.
    """
    peer_ip = request.client.host if request.client else "unknown"
    if peer_ip == "unknown" or not _is_trusted_proxy_ip(peer_ip):
        return peer_ip

    # Peer is a verified reverse proxy — check CDN-specific header first
    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip and not _is_trusted_proxy_ip(cf_connecting_ip):
        return cf_connecting_ip.strip()

    # Walk X-Forwarded-For backwards to extract the true client IP
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        hops = [h.strip() for h in xff.split(",") if h.strip()]
        for hop in reversed(hops):
            if not _is_trusted_proxy_ip(hop):
                return hop

    return peer_ip
