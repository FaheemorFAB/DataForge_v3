"""
dataforge/api/routes/pages.py
───────────────────────────────
HTML Page routes: renders frontend Jinja2 templates (upload, dashboard, workspace, projects, login).
"""

from __future__ import annotations

import logging
from typing import Optional

import jinja2
from fastapi import APIRouter, Cookie, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from dataforge.api.auth.jwt import get_user_id_from_token
from dataforge.api.config import get_settings
from dataforge.api.repositories.report import alert_repo, report_repo, schedule_repo
from dataforge.api.repositories.upload import upload_repo
from dataforge.api.repositories.user import user_repo
from dataforge.api.storage.manager import load
from dataforge.api.utils.helpers import format_member_since, time_ago
from dataforge.db import User

log = logging.getLogger(__name__)
router = APIRouter(tags=["pages"])
settings = get_settings()

# ── Jinja2 Templates Setup ───────────────────────────────────────────────────
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# Custom url_for to support Flask-style {{ url_for('static', filename='...') }}
_default_url_for = templates.env.globals["url_for"]


@jinja2.pass_context
def _custom_url_for(context, name: str, **path_params):
    if name == "static" and "filename" in path_params and "path" not in path_params:
        path_params["path"] = path_params.pop("filename")
    return _default_url_for(context, name, **path_params)


templates.env.globals["url_for"] = _custom_url_for


class AnonymousUser:
    id = None
    email = ""
    name = "Guest"
    avatar = None
    is_authenticated = False


def _get_user_from_request(request: Request, access_token: Optional[str] = None) -> User | AnonymousUser:
    token = access_token
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        uid = get_user_id_from_token(token)
        if uid is not None:
            udata = user_repo.get_by_id(uid)
            if udata:
                return User(**udata)

    return AnonymousUser()


# ── Page Handlers ─────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def page_index(request: Request, access_token: Optional[str] = Cookie(default=None)):
    user = _get_user_from_request(request, access_token)
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "user": user,
            "current_user": user,
            "google_enabled": settings.GOOGLE_AUTH_ENABLED,
        },
    )


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def page_login(request: Request, access_token: Optional[str] = Cookie(default=None)):
    user = _get_user_from_request(request, access_token)
    if user.is_authenticated:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "user": user,
            "current_user": user,
            "google_enabled": settings.GOOGLE_AUTH_ENABLED,
        },
    )


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def page_dashboard(request: Request, access_token: Optional[str] = Cookie(default=None)):
    user = _get_user_from_request(request, access_token)
    if not user.is_authenticated:
        return RedirectResponse(url="/login/mock", status_code=302)

    uploads = upload_repo.list_recent(user.id, limit=10)
    uploads_data = [{
        "id": u.get("id"),
        "filename": u.get("filename", ""),
        "source_type": u.get("source_type", "csv"),
        "rows": u.get("rows", 0),
        "cols": u.get("cols", 0),
        "missing_pct": u.get("missing_pct", 0.0),
        "time_ago": time_ago(u.get("uploaded_at")),
    } for u in uploads]

    analyses = upload_repo.get_analyses(user.id, limit=10)
    analyses_data = [{
        "id": a.get("id"),
        "upload_id": a.get("upload_id"),
        "type": a.get("type"),
        "summary": a.get("summary", ""),
        "filename": (a.get("uploads") or {}).get("filename", ""),
        "time_ago": time_ago(a.get("created_at")),
    } for a in analyses]

    reports = report_repo.list_for_user(user.id, limit=10)
    reports_data = [{
        "id": r.get("id"),
        "upload_id": r.get("upload_id"),
        "filename": (r.get("uploads") or {}).get("filename", ""),
        "triggered_by": r.get("triggered_by", "manual"),
        "time_ago": time_ago(r.get("created_at")),
    } for r in reports]

    alert_cnt = alert_repo.count_unresolved(user.id)
    sched_cnt = schedule_repo.count_active(user.id)
    member_since = format_member_since(getattr(user, "created_at", None))

    class EmptyStats:
        total_uploads = len(uploads)
        total_analyses = len(analyses)
        total_reports = len(reports)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "current_user": user,
            "stats": EmptyStats(),
            "recent_uploads": uploads_data,
            "recent_analyses": analyses_data,
            "alert_count": alert_cnt,
            "recent_reports": reports_data,
            "schedule_count": sched_cnt,
            "member_since": member_since,
        },
    )


@router.get("/workspace", response_class=HTMLResponse, include_in_schema=False)
async def page_workspace(
    request: Request,
    upload_id: Optional[int] = Query(default=None),
    access_token: Optional[str] = Cookie(default=None),
):
    user = _get_user_from_request(request, access_token)
    if not user.is_authenticated:
        return RedirectResponse(url="/login/mock", status_code=302)

    profile = {}
    if upload_id:
        profile = load(upload_id, "profile") or {}
    else:
        recent = upload_repo.list_recent(user.id, limit=1)
        if recent:
            upload_id = recent[0]["id"]
            profile = load(upload_id, "profile") or {}

    return templates.TemplateResponse(
        request=request,
        name="workspace.html",
        context={
            "user": user,
            "current_user": user,
            "gemini_ok": True,
            "upload_id": upload_id,
            "profile": profile,
        },
    )


@router.get("/projects", response_class=HTMLResponse, include_in_schema=False)
async def page_projects(request: Request, access_token: Optional[str] = Cookie(default=None)):
    user = _get_user_from_request(request, access_token)
    if not user.is_authenticated:
        return RedirectResponse(url="/login/mock", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "user": user,
            "current_user": user,
        },
    )
