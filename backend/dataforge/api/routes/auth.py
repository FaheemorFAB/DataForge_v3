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
        if code and ("mismatching_state" in str(exc).lower() or "state" in str(exc).lower()):
            try:
                log.info("State mismatch caught — attempting direct token exchange with code...")
                oauth = request.app.state.oauth
                redirect_uri = get_google_redirect_uri()
                token = await oauth.google.fetch_token(
                    redirect_uri=redirect_uri,
                    code=code,
                )
                userinfo = token.get("userinfo")
                if not userinfo:
                    userinfo = await oauth.google.userinfo(token=token)
            except Exception as exc2:
                log.error("Direct token exchange failed: %s", exc2)

    if not userinfo:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?login=1&error=oauth")

    user = auth_service.get_or_create_google_user(dict(userinfo))
    if not user:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?login=1&error=db")

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
@router.get("/logout", include_in_schema=False)  # legacy compat
async def logout():
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"status": "ok"})
    # Must match the same path/samesite/domain that set_cookie used
    response.delete_cookie(
        key=_COOKIE_KEY,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return response


# ── Current user info ─────────────────────────────────────────────────────────

@router.get("/api/v1/auth/me", summary="Get current user info")
@router.get("/v1/auth/me", summary="Get current user info (alias)")
@router.get("/api/auth/me", summary="Get current user info (alias)")
@router.get("/auth/me", summary="Get current user info (alias)")
async def me(current_user: CurrentUser):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar": current_user.avatar,
        "role": getattr(current_user, "role", "Admin") or "Admin",
        "created_at": current_user.created_at,
    }

