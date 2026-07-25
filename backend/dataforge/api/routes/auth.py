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
from dataforge.api.services.auth import auth_service

log = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
settings = get_settings()

_COOKIE_KEY = "access_token"
_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=False)  # set secure=True behind HTTPS


def _set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=_COOKIE_KEY,
        value=token,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/login/google", summary="Initiate Google OAuth flow")
async def login_google(request: Request, next: str = "/dashboard"):
    if not settings.GOOGLE_AUTH_ENABLED:
        return RedirectResponse(url="/?login=1")

    from authlib.integrations.starlette_client import OAuth
    oauth = request.app.state.oauth
    redirect_uri = str(request.url_for("auth_google_callback"))
    request.session["next_url"] = next if next.startswith("/") else "/dashboard"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", name="auth_google_callback", summary="Google OAuth callback")
async def auth_google_callback(request: Request):
    if not settings.GOOGLE_AUTH_ENABLED:
        return RedirectResponse(url="/?login=1&error=oauth_disabled")

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
                redirect_uri = str(request.url_for("auth_google_callback"))
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
        return RedirectResponse(url="/?login=1&error=oauth")

    user = auth_service.get_or_create_google_user(dict(userinfo))
    if not user:
        return RedirectResponse(url="/?login=1&error=db")

    jwt_token = auth_service.create_token_for_user(user)
    next_url = request.session.pop("next_url", "/workspace")
    if not isinstance(next_url, str) or not next_url.startswith("/"):
        next_url = "/workspace"

    response = RedirectResponse(url=next_url, status_code=302)
    _set_auth_cookie(response, jwt_token)
    log.info("Google OAuth login success: user_id=%d email=%s", user.id, user.email)
    return response


# ── Mock login (dev only) ─────────────────────────────────────────────────────

@router.get("/login/mock", summary="[DEV] Log in as user id=1")
async def mock_login():
    user = auth_service.get_mock_user()
    if not user:
        raise HTTPException(status_code=404, detail="Mock user not found in DB")

    token = auth_service.create_token_for_user(user)
    response = RedirectResponse(url="/dashboard", status_code=302)
    _set_auth_cookie(response, token)
    return response


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/api/v1/auth/logout", summary="Clear the auth cookie")
@router.get("/logout", include_in_schema=False)  # legacy compat
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=_COOKIE_KEY)
    return response


# ── Current user info ─────────────────────────────────────────────────────────

@router.get("/api/v1/auth/me", summary="Get current user info")
async def me(current_user: CurrentUser):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar": current_user.avatar,
        "created_at": current_user.created_at,
    }
