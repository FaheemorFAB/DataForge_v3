"""
dataforge/api/middleware/logging.py
─────────────────────────────────────
Request logging middleware: attaches a request_id to every request and
logs method, path, status code, and duration with structured fields.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("dataforge.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Adds X-Request-ID header to every response and logs:
        - Method, path, status, duration
        - user_id (from JWT cookie) when available
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        # Best-effort user_id extraction (don't fail the request for logging)
        user_id = getattr(request.state, "user_id", None)

        log.info(
            "%s %s → %d  [%dms] req_id=%s user=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
            user_id or "anon",
        )
        return response
