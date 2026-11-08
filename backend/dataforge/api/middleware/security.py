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
            from dataforge.api.config import get_settings
            _cfg = get_settings()
            _ancestors = ["'self'"]
            if _cfg.FRONTEND_URL:
                _ancestors.append(_cfg.FRONTEND_URL.rstrip("/"))
            if _cfg.BACKEND_URL:
                _ancestors.append(_cfg.BACKEND_URL.rstrip("/"))
            _ancestors.extend(["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:3000", "http://127.0.0.1:5000"])

            # Dynamically permit client origin / referer / host so any deployed domain can embed its own reports
            client_origin = request.headers.get("origin")
            if client_origin:
                _ancestors.append(client_origin.rstrip("/"))
            client_referer = request.headers.get("referer")
            if client_referer:
                try:
                    from urllib.parse import urlparse
                    ref_parsed = urlparse(client_referer)
                    if ref_parsed.scheme and ref_parsed.netloc:
                        _ancestors.append(f"{ref_parsed.scheme}://{ref_parsed.netloc}")
                except Exception:
                    pass
            client_host = request.headers.get("host")
            if client_host:
                _ancestors.append(f"https://{client_host}")
                _ancestors.append(f"http://{client_host}")

            unique_ancestors = list(dict.fromkeys(a for a in _ancestors if a))
            response.headers["Content-Security-Policy"] = f"frame-ancestors {' '.join(unique_ancestors)}"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            response.headers["X-Frame-Options"] = "DENY"

        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response
