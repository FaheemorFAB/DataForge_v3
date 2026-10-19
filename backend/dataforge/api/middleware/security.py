"""
dataforge/api/middleware/security.py
────────────────────────────────────
OWASP-recommended HTTP security headers middleware.
Adds defense-in-depth protection against clickjacking, MIME-type sniffing,
and cross-origin information leakage.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"

        # Allow embedding reports from the same origin (e.g. Next.js iframe)
        report_embed_paths = (
            "/eda/report",
            "/data-report",
            "/reports/latest",
            "/reports/current",
        )
        is_report_path = (
            any(p in request.url.path for p in report_embed_paths)
            or (request.url.path.startswith(("/api/reports/", "/api/v1/reports/")) and not request.url.path.endswith("/reports"))
        )
        if is_report_path:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            from dataforge.api.config import get_settings
            _cfg = get_settings()
            _ancestors = ["'self'"]
            if _cfg.FRONTEND_URL:
                _ancestors.append(_cfg.FRONTEND_URL.rstrip("/"))
            if _cfg.BACKEND_URL:
                _ancestors.append(_cfg.BACKEND_URL.rstrip("/"))
            _ancestors.extend(["http://localhost:3000", "http://localhost:5000"])
            response.headers["Content-Security-Policy"] = f"frame-ancestors {' '.join(dict.fromkeys(_ancestors))}"
        else:
            response.headers["X-Frame-Options"] = "DENY"

        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response
