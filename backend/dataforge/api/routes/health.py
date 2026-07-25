"""
dataforge/api/routes/health.py
────────────────────────────────
Health check endpoints: /api/health, /api/health/live, /api/health/ready
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from dataforge.api.config import get_settings
from dataforge.api.jobs.executor import get_executor
from dataforge.api.websocket.manager import get_ws_manager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])
settings = get_settings()


@router.get("/health", summary="Full health check")
async def health():
    """Returns status of API, DB, Redis, and WebSocket manager."""
    checks = {
        "api": "ok",
        "database": "ok",
        "redis": "ok",
        "websocket": "ok",
        "executor": "ok",
    }

    # DB check
    try:
        from dataforge.db import db_client
        if db_client is None:
            checks["database"] = "unavailable"
        else:
            db_client.table("uploads").select("id").limit(1).execute()
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # Redis check
    try:
        from dataforge.web.cache import _r
        r = _r()
        if r is None:
            checks["redis"] = "unavailable"
        else:
            r.ping()
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # WebSocket manager
    try:
        mgr = get_ws_manager()
        checks["websocket"] = f"ok (connections={mgr.total_connections()})"
    except Exception as exc:
        checks["websocket"] = f"error: {exc}"

    # Executor
    try:
        executor = get_executor()
        checks["executor"] = f"ok (workers={executor._max_workers})"
    except Exception as exc:
        checks["executor"] = f"error: {exc}"

    overall = "healthy" if all(v.startswith("ok") or v == "unavailable" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "checks": checks,
    }


@router.get("/health/live", summary="Liveness probe (pod is running)")
async def health_live():
    """K8s liveness probe: always returns 200 if the process is alive."""
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe (pod can serve traffic)")
async def health_ready():
    """K8s readiness probe: 200 if DB is reachable, 503 otherwise."""
    try:
        from dataforge.db import db_client
        if db_client:
            db_client.table("uploads").select("id").limit(1).execute()
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": str(exc)})
    return {"status": "ready"}
