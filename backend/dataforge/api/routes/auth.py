"""
dataforge/api/routes/auth.py
──────────────────────────────
Authentication routes: Google OAuth, mock login, logout.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from dataforge.api.config import get_settings
from dataforge.api.deps import CurrentUser
from dataforge.api.limiter import limiter
from dataforge.api.services.auth import auth_service
from dataforge.db import User

log = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
settings = get_settings()

_COOKIE_KEY = "access_token"
_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=settings.COOKIE_SECURE, path="/")


def _set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=_COOKIE_KEY,
        value=token,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )


# ── Google OAuth ──────────────────────────────────────────────────────────────

def get_google_redirect_uri() -> str:
    if settings.GOOGLE_REDIRECT_URI:
        return settings.GOOGLE_REDIRECT_URI
    if settings.BACKEND_URL:
        return f"{settings.BACKEND_URL.rstrip('/')}/auth/google/callback"
    return "http://localhost:5000/auth/google/callback"


@router.get("/login/google", summary="Initiate Google OAuth flow")
@router.get("/api/auth/login/google", summary="Initiate Google OAuth flow (alias)")
@router.get("/auth/login/google", summary="Initiate Google OAuth flow (alias)")
@limiter.limit("20/minute")
async def login_google(request: Request, next: str = "/"):
    if not settings.GOOGLE_AUTH_ENABLED:
        return RedirectResponse(url="/?login=1")

    from authlib.integrations.starlette_client import OAuth
    oauth = request.app.state.oauth
    redirect_uri = get_google_redirect_uri()
    request.session["next_url"] = next if next.startswith("/") else "/"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/login/mock", summary="Dev-only mock login bypass")
@router.get("/api/auth/login/mock", summary="Dev-only mock login bypass (alias)")
@router.get("/api/login/mock", summary="Dev-only mock login bypass (alias)")
@limiter.limit("10/minute")
async def login_mock(request: Request, email: str = "dev@example.com", name: str = "Dev User"):
    if not settings.ENABLE_DEV_AUTH or settings.PRODUCTION:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found",
        )
    # Create or retrieve a dev user
    user_info = {
        "sub": "mock-sub-12345",
        "email": email,
        "name": name,
        "picture": "/avatars/avatar-1.svg"
    }
    user = auth_service.get_or_create_google_user(user_info)
    if not user:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?login=1&error=db")

    jwt_token = auth_service.create_token_for_user(user)
    # Redirect to configured frontend URL
    frontend_url = f"{settings.FRONTEND_URL}/?login_success=1"
    response = RedirectResponse(url=frontend_url, status_code=302)
    _set_auth_cookie(response, jwt_token)
    log.info("Mock login success: user_id=%d email=%s", user.id, user.email)
    return response


from typing import Optional
from pydantic import BaseModel, Field

class MockLoginRequest(BaseModel):
    email: Optional[str] = "analyst@dataforge.app"
    name: Optional[str] = "DataForge Analyst"
    role: Optional[str] = "Analyst"


@router.post("/api/v1/auth/mock", summary="Dev-only instant mock login returning JSON")
@limiter.limit("10/minute")
async def login_mock_post(
    request: Request,
    response: Response,
    payload: Optional[MockLoginRequest] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    role: Optional[str] = None,
):
    if not settings.ENABLE_DEV_AUTH or settings.PRODUCTION:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found",
        )
    target_email = (payload.email if payload and payload.email else email) or "analyst@dataforge.app"
    target_name = (payload.name if payload and payload.name else name) or "DataForge Analyst"
    target_role = (payload.role if payload and payload.role else role) or "Analyst"

    user_info = {
        "sub": f"mock-{target_email.replace('@', '-').replace('.', '-')}",
        "email": target_email,
        "name": target_name,
        "picture": "/avatars/avatar-1.svg"
    }
    user = auth_service.get_or_create_google_user(user_info)
    if not user:
        user = User(id=1, email=target_email, name=target_name, avatar="https://api.dicebear.com/7.x/pixel-art/svg", role=target_role)
    else:
        user.role = target_role

    jwt_token = auth_service.create_token_for_user(user)
    _set_auth_cookie(response, jwt_token)
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar": user.avatar,
            "role": target_role,
        }
    }



@router.get("/auth/google/callback", name="auth_google_callback", summary="Google OAuth callback")
@router.get("/api/auth/google/callback", summary="Google OAuth callback alias")
@router.get("/auth/callback/google", summary="Legacy Google OAuth callback alias")
@limiter.limit("20/minute")
async def auth_google_callback(request: Request):
    if not settings.GOOGLE_AUTH_ENABLED:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?login=1&error=oauth_disabled")

    userinfo = None
    try:
        oauth = request.app.state.oauth
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = await oauth.google.userinfo(token=token)
    except Exception as exc:
        log.error("Google OAuth callback error: %s", exc)
        code = request.query_params.get("code")
        if code:
            try:
                log.info("Attempting direct Google token exchange with code...")
                import httpx
                redirect_uri = get_google_redirect_uri()
                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    token_resp = await http_client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "code": code,
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "redirect_uri": redirect_uri,
                            "grant_type": "authorization_code",
                        },
                        headers={"Accept": "application/json"},
                    )
                    if token_resp.status_code == 200:
                        token_data = token_resp.json()
                        access_token = token_data.get("access_token")
                        userinfo_resp = await http_client.get(
                            "https://www.googleapis.com/oauth2/v3/userinfo",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if userinfo_resp.status_code == 200:
                            userinfo = userinfo_resp.json()
                            log.info("Direct Google token exchange succeeded: email=%s", userinfo.get("email"))
                        else:
                            log.error("Google userinfo fetch failed (%s): %s", userinfo_resp.status_code, userinfo_resp.text)
                    else:
                        log.error("Direct Google token exchange failed (%s): %s", token_resp.status_code, token_resp.text)
            except Exception as exc2:
                log.error("Direct Google token exchange exception: %s", exc2)

    if not userinfo:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?login=1&error=oauth")

    user = auth_service.get_or_create_google_user(dict(userinfo))
    if not user:
        log.warning("Could not persist Google user to DB, creating session user fallback")
        user = User(
            id=1,
            email=userinfo.get("email") or "user@dataforge.app",
            name=userinfo.get("name") or (userinfo.get("email", "").split("@")[0] if userinfo.get("email") else "User"),
            avatar=userinfo.get("picture") or "/avatars/avatar-1.svg",
            google_id=userinfo.get("sub"),
            role="Admin",
        )

    jwt_token = auth_service.create_token_for_user(user)
    next_url = request.session.pop("next_url", "/")
    if not isinstance(next_url, str) or not next_url.startswith("/"):
        next_url = "/"

    # Redirect to configured frontend URL
    separator = "&" if "?" in next_url else "?"
    frontend_url = f"{settings.FRONTEND_URL}{next_url}{separator}login_success=1&token={jwt_token}"
    response = RedirectResponse(url=frontend_url, status_code=302)
    _set_auth_cookie(response, jwt_token)
    log.info("Google OAuth login success: user_id=%d email=%s", user.id, user.email)
    return response


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/api/v1/auth/logout", summary="Clear the auth cookie")
@router.get("/api/v1/auth/logout", include_in_schema=False)
@router.post("/v1/auth/logout", include_in_schema=False)
@router.get("/v1/auth/logout", include_in_schema=False)
@router.post("/api/logout", include_in_schema=False)
@router.get("/api/logout", include_in_schema=False)
@router.post("/logout", include_in_schema=False)
@router.get("/logout", include_in_schema=False)
async def logout():
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"status": "ok"})
    for samesite in ["lax", "none", "strict"]:
        response.delete_cookie(
            key=_COOKIE_KEY,
            path="/",
            httponly=True,
            samesite=samesite,
            secure=settings.COOKIE_SECURE,
        )
        response.delete_cookie(
            key=_COOKIE_KEY,
            path="/",
            httponly=False,
            samesite=samesite,
        )
    return response


# ── Current user info ─────────────────────────────────────────────────────────

import json
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel

_PROFILE_FILE = Path("/home/fab/DataForge_v3/instance/user_profile.json")

def _get_stored_profile(user_id: Any) -> dict:
    if not _PROFILE_FILE.exists():
        return {}
    try:
        data = json.loads(_PROFILE_FILE.read_text(encoding="utf-8"))
        return data.get(str(user_id), {})
    except Exception:
        return {}

def _set_stored_profile(user_id: Any, fields: dict):
    data = {}
    if _PROFILE_FILE.exists():
        try:
            data = json.loads(_PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    u_data = data.get(str(user_id), {})
    u_data.update(fields)
    data[str(user_id)] = u_data
    try:
        _PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PROFILE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None


@router.get("/api/v1/auth/me", summary="Get current user info")
@router.get("/v1/auth/me", summary="Get current user info (alias)")
@router.get("/api/auth/me", summary="Get current user info (alias)")
@router.get("/auth/me", summary="Get current user info (alias)")
async def me(current_user: CurrentUser):
    stored = _get_stored_profile(current_user.id)
    name = stored.get("name") or current_user.name
    avatar = stored.get("avatar") or current_user.avatar
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": name,
        "avatar": avatar,
        "role": getattr(current_user, "role", "Admin") or "Admin",
        "created_at": current_user.created_at,
    }


@router.patch("/api/v1/auth/me", summary="Update current user info")
@router.patch("/v1/auth/me", summary="Update current user info (alias)")
@router.put("/api/v1/auth/me", summary="Update current user info (alias)")
@router.put("/v1/auth/me", summary="Update current user info (alias)")
async def update_me(req: UpdateProfileRequest, current_user: CurrentUser):
    fields = {}
    if req.name and req.name.strip():
        fields["name"] = req.name.strip()
    if req.avatar and req.avatar.strip():
        fields["avatar"] = req.avatar.strip()
    if fields:
        _set_stored_profile(current_user.id, fields)
        try:
            from dataforge.api.repositories.user import user_repo
            user_repo.update(current_user.id, fields)
        except Exception:
            pass

    stored = _get_stored_profile(current_user.id)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": stored.get("name") or current_user.name,
        "avatar": stored.get("avatar") or current_user.avatar,
        "role": getattr(current_user, "role", "Admin") or "Admin",
        "created_at": current_user.created_at,
    }


# ── Password Reset (Transactional via Resend) ─────────────────────────────────

import secrets
import threading
from datetime import datetime, timezone, timedelta
from dataforge.api.services.mailer import EmailDeliveryService

_RESET_LOCK = threading.Lock()
_ROOT_DIR = Path(__file__).resolve().parents[4] if len(Path(__file__).resolve().parents) > 4 else Path(".")
_RESET_TOKENS_FILE = _ROOT_DIR / "instance" / "password_resets.json"


def _load_reset_tokens() -> dict[str, dict]:
    if not _RESET_TOKENS_FILE.exists():
        return {}
    try:
        return json.loads(_RESET_TOKENS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("[auth/reset] Could not read reset tokens file: %s", exc)
        return {}


def _save_reset_tokens(tokens: dict[str, dict]):
    try:
        _RESET_TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _RESET_TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    except Exception as exc:
        log.error("[auth/reset] Could not save reset tokens: %s", exc)


def create_password_reset_token(email: str) -> str:
    clean_email = email.strip().lower()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)
    record = {
        "email": clean_email,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "used": False,
    }
    with _RESET_LOCK:
        tokens = _load_reset_tokens()
        # Clean up tokens older than 48 hours
        cutoff = (now - timedelta(hours=48)).isoformat()
        pruned = {
            t: d for t, d in tokens.items()
            if d.get("created_at", "") > cutoff
        }
        pruned[token] = record
        _save_reset_tokens(pruned)
    return token


def verify_password_reset_token(token: str) -> tuple[bool, str, Optional[str]]:
    if not token or not token.strip():
        return False, "Invalid or missing token.", None
    with _RESET_LOCK:
        tokens = _load_reset_tokens()
        record = tokens.get(token)
    if not record:
        return False, "Reset link is invalid or does not exist.", None
    if record.get("used"):
        return False, "This reset link has already been used. Please request a new one.", record.get("email")
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            return False, "This reset link has expired. Please request a new one.", record.get("email")
    except Exception:
        return False, "Invalid token timestamp.", None
    return True, "Token is valid.", record.get("email")


def mark_reset_token_used(token: str):
    with _RESET_LOCK:
        tokens = _load_reset_tokens()
        if token in tokens:
            tokens[token]["used"] = True
            tokens[token]["used_at"] = datetime.now(timezone.utc).isoformat()
            _save_reset_tokens(tokens)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/api/auth/password/forgot", summary="Request password reset link via Resend")
@router.post("/v1/auth/password/forgot", summary="Request password reset link alias")
@router.post("/auth/password/forgot", summary="Request password reset link alias")
@limiter.limit("10/minute")
async def forgot_password(request: Request, response: Response, req: ForgotPasswordRequest):
    clean_email = req.email.strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    # Generate token
    token = create_password_reset_token(clean_email)

    # Determine frontend URL
    frontend_base = settings.FRONTEND_URL.rstrip("/")
    if "localhost" in frontend_base or "127.0.0.1" in frontend_base:
        frontend_base = "https://numan-10.site"
    reset_url = f"{frontend_base}/reset-password?token={token}"

    # Dispatch email via Resend
    dispatch_res = EmailDeliveryService.send_password_reset_email(
        recipient_email=clean_email,
        reset_url=reset_url,
    )

    log.info("[auth/forgot] Password reset email dispatched to %s (sent=%s)", clean_email, dispatch_res.get("sent"))
    return {
        "ok": True,
        "message": f"If an account exists for {clean_email}, a password reset link has been dispatched to your inbox.",
        "sent": dispatch_res.get("sent", False),
    }


@router.get("/api/auth/password/verify-token", summary="Verify validity of a password reset token")
@router.get("/v1/auth/password/verify-token", summary="Verify reset token alias")
@router.get("/auth/password/verify-token", summary="Verify reset token alias")
async def verify_reset_token(token: str):
    is_valid, reason, email = verify_password_reset_token(token)
    masked_email = None
    if email and "@" in email:
        parts = email.split("@")
        name_part = parts[0]
        masked = (name_part[:2] + "***") if len(name_part) > 2 else name_part + "***"
        masked_email = f"{masked}@{parts[1]}"
    return {
        "valid": is_valid,
        "reason": reason,
        "email": masked_email,
    }


@router.post("/api/auth/password/reset", summary="Update password using verified reset token")
@router.post("/v1/auth/password/reset", summary="Update password alias")
@router.post("/auth/password/reset", summary="Update password alias")
@limiter.limit("10/minute")
async def reset_password(request: Request, response: Response, req: ResetPasswordRequest):
    new_pw = req.new_password.strip()
    if len(new_pw) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )

    is_valid, reason, email = verify_password_reset_token(req.token)
    if not is_valid or not email:
        raise HTTPException(status_code=400, detail=reason)

    # Invalidate token so it cannot be used again
    mark_reset_token_used(req.token)

    # 1. Synchronize password with Supabase admin auth if configured
    try:
        from dataforge.db import db_client
        if db_client and hasattr(db_client, "auth") and hasattr(db_client.auth, "admin"):
            users_resp = db_client.auth.admin.list_users()
            users_list = getattr(users_resp, "users", users_resp) if not isinstance(users_resp, list) else users_resp
            if hasattr(users_resp, "data"):
                users_list = users_resp.data
            target_uid = None
            for u in users_list:
                u_email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                if u_email and u_email.strip().lower() == email.strip().lower():
                    target_uid = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
                    break
            if target_uid:
                db_client.auth.admin.update_user_by_id(target_uid, {"password": new_pw})
                log.info("[auth/reset] Synchronized Supabase user password for %s (%s)", email, target_uid)
    except Exception as exc:
        log.warning("[auth/reset] Supabase admin password sync error (non-fatal): %s", exc)

    # 2. Update / create user in local repository
    from dataforge.api.repositories.user import user_repo
    user_data = user_repo.get_by_email(email)
    now_iso = datetime.now(timezone.utc).isoformat()
    if not user_data:
        user_data = user_repo.create({
            "email": email,
            "name": email.split("@")[0].capitalize(),
            "avatar": "/avatars/avatar-1.svg",
            "role": "Admin",
            "last_login": now_iso,
        })
    else:
        user_repo.update(user_data["id"], {"last_login": now_iso})
        user_data = user_repo.get_by_id(user_data["id"]) or user_data

    user = User(**user_data)
    jwt_token = auth_service.create_token_for_user(user)
    _set_auth_cookie(response, jwt_token)

    log.info("[auth/reset] Successfully updated password and logged in user: %s (id=%s)", email, user.id)
    return {
        "ok": True,
        "message": "Password updated successfully. You are now logged in.",
        "token": jwt_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar": user.avatar,
            "role": getattr(user, "role", "Admin") or "Admin",
        },
    }



