"""
dataforge/api/app.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FastAPI application factory.

Lifecycle (lifespan):
  startup  â†’ bootstrap JobRegistry, init WebSocket manager, warm executor, setup OAuth
  shutdown â†’ graceful executor shutdown

Registered routers:
  /api/v1/*        (auth, upload, workspace, insights, automl, dashboard, projects, tasks)
  /api/health/*    (health, liveness, readiness)
  /ws              (WebSocket)

Middleware:
  CORS
  SessionMiddleware (for OAuth state only â€” not for auth)
  RequestLoggingMiddleware
  SlowAPI rate limiting
"""

from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from dataforge.api.config import get_settings
from dataforge.api.middleware.logging import RequestLoggingMiddleware

log = logging.getLogger(__name__)
settings = get_settings()


def _setup_logging():
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Silence overly verbose third-party loggers
    for noisy in ("httpx", "httpcore", "charset_normalizer", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager â€” replaces Flask's app.before_first_request."""
    _setup_logging()
    settings.validate_production_environment()
    log.info("Starting DataForge API v%s", settings.APP_VERSION)

    # â”€â”€ Initialize WebSocket manager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    from dataforge.api.websocket.manager import get_ws_manager
    ws_manager = get_ws_manager()
    app.state.ws_manager = ws_manager
    log.info("WebSocket manager initialized")

    # â”€â”€ Warm up ThreadPoolExecutor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    from dataforge.api.jobs.executor import get_executor
    executor = get_executor()
    app.state.executor = executor
    log.info("ThreadPoolExecutor ready: max_workers=%d", executor._max_workers)

    # â”€â”€ Bootstrap JobRegistry from Supabase â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    from dataforge.api.jobs import registry
    await registry.bootstrap()

    # â”€â”€ Initialize JobManager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    from dataforge.api.jobs.manager import get_job_manager
    app.state.job_manager = get_job_manager()

    # â”€â”€ Google OAuth client â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if settings.GOOGLE_AUTH_ENABLED:
        try:
            from authlib.integrations.starlette_client import OAuth
            oauth = OAuth()
            oauth.register(
                name="google",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
            app.state.oauth = oauth
            log.info("Google OAuth registered (client_id=%s...)", settings.GOOGLE_CLIENT_ID[:8])
        except Exception as exc:
            log.warning("Google OAuth setup failed: %s", exc)
            app.state.oauth = None
    else:
        app.state.oauth = None
        log.info("Google OAuth disabled (GOOGLE_CLIENT_ID not set)")

    log.info("DataForge API startup complete")
    yield  # â† Application runs here

    # â”€â”€ Cleanup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    from dataforge.api.jobs.executor import shutdown_executor
    shutdown_executor()
    log.info("DataForge API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="DataForge â€” Intelligent Data Analysis Platform",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # â”€â”€ Middleware stack â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    # CORS (dev: allow all localhost; prod: restrict to FRONTEND_URL / ALLOWED_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session middleware â€” used ONLY for OAuth state (not for auth)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.JWT_SECRET,
        session_cookie="df_session",
        max_age=600,
        https_only=settings.SESSION_HTTPS_ONLY,
        same_site="lax" if not settings.PRODUCTION else "none",
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Security headers (OWASP defense-in-depth)
    from dataforge.api.middleware.security import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Proxy Headers (trust X-Forwarded-Proto only from configured reverse proxies)
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.TRUSTED_PROXIES)

    # Rate limiting (slowapi)
    try:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        from dataforge.api.limiter import limiter

        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
        log.info("SlowAPI rate limiting enabled")
    except ImportError:
        log.warning("slowapi not installed â€” rate limiting disabled")

    # ── Register routers ──────────────────────────────────────────────────────
    from dataforge.api.routes import (
        auth, automl, dashboard, health, insights, models, pipeline, procedures, projects, subscription, tasks, teams, workspace,
    )
    
    @app.get("/health", tags=["health"], summary="Root health check for Render & cloud load balancers")
    async def root_health():
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=settings.FRONTEND_URL)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(procedures.router)

    # Mount API routers under both /api/v1 (REST API) and /api (Web Frontend compatibility)
    api_routers = [
        upload_router(),
        workspace.router,
        automl.router,
        insights.router,
        dashboard.router,
        projects.router,
        tasks.router,
        teams.router,
        models.router,
        pipeline.router,
        subscription.router,
        subscription.subscriptions_router,
    ]
    for r in api_routers:
        app.include_router(r, prefix="/api/v1")
        app.include_router(r, prefix="/api")

    # â”€â”€ WebSocket endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        upload_id: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """
        WebSocket endpoint with JWT authentication.
        Client connects: ws://host/ws?token=<jwt>&upload_id=<id>
        """
        from dataforge.api.auth.jwt import get_user_id_from_token
        from dataforge.api.websocket.manager import get_ws_manager

        # Authenticate via token query param or HTTP-only cookie fallback
        cookie_token = websocket.cookies.get("access_token")
        uid = get_user_id_from_token(token or cookie_token or "")
        if uid is None:
            await websocket.close(code=4001, reason="Unauthorized")
            return

        mgr = get_ws_manager()
        await mgr.connect(websocket, uid, upload_id)

        try:
            # Send welcome event
            await mgr.send_to_user(uid, "connected", {"user_id": uid, "upload_id": upload_id})
            # Keep connection alive â€” wait for disconnect
            while True:
                data = await websocket.receive_text()
                # Echo/ping-pong keepalive
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            await mgr.disconnect(websocket, uid, upload_id)

    # â”€â”€ Global exception handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        log.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc) if settings.DEBUG else None},
        )

    # â”€â”€ Static files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    static_dir = settings.STATIC_DIR
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


def upload_router():
    """Lazy import to avoid circular deps."""
    from dataforge.api.routes.upload import router
    return router


app = create_app()

