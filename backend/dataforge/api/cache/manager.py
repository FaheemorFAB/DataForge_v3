"""
dataforge/api/cache/manager.py
────────────────────────────────
Cache manager — thin re-export of the existing web/cache.py logic.
Redis is optional; all functions gracefully degrade to no-ops when unavailable.
"""

from __future__ import annotations

# Re-export from original cache module
from dataforge.web.cache import (
    get_profile,
    set_profile,
    get_schema,
    set_schema,
    get_clean_meta,
    set_clean_meta,
    get_alert_status,
    set_alert_status,
    get_user_metrics,
    set_user_metrics,
    invalidate_upload,
    invalidate_user,
    rate_limit,
)

__all__ = [
    "get_profile", "set_profile",
    "get_schema", "set_schema",
    "get_clean_meta", "set_clean_meta",
    "get_alert_status", "set_alert_status",
    "get_user_metrics", "set_user_metrics",
    "invalidate_upload", "invalidate_user",
    "rate_limit",
]
