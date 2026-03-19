"""
services/web/cache.py
─────────────────────
Redis read-through cache layer for DataForge.

Design principles
─────────────────
• NEVER cache large binary blobs (DataFrames, models) — those stay on disk.
• Cache only small JSON-serialisable dicts (profile, schema, metadata, etc.).
• Always use orjson (not stdlib json) for speed + correct numpy/datetime handling.
• Graceful degradation: if Redis is unreachable, every function returns None /
  falls through to the disk/DB path so the app keeps working.
"""

import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

# ── Redis client (lazy singleton) ─────────────────────────────────────────────
_redis_client = None


def _r():
    """Return the shared Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.Redis.from_url(url, decode_responses=True,
                                                  socket_connect_timeout=2,
                                                  socket_timeout=2)
            _redis_client.ping()  # fail fast if Redis is not available
        except Exception as exc:
            log.warning("Redis unavailable — cache disabled: %s", exc)
            _redis_client = None
    return _redis_client


def _get(key: str) -> Optional[dict]:
    """Return a cached value (already parsed JSON) or None."""
    try:
        client = _r()
        if client is None:
            return None
        raw = client.get(key)
        if raw is None:
            return None
        import orjson
        return orjson.loads(raw)
    except Exception as exc:
        log.debug("Cache GET failed for %s: %s", key, exc)
        return None


def _set(key: str, value, ttl_seconds: int):
    """Serialise value and store in Redis with a TTL."""
    try:
        client = _r()
        if client is None:
            return
        import orjson
        client.setex(key, ttl_seconds, orjson.dumps(value).decode())
    except Exception as exc:
        log.debug("Cache SET failed for %s: %s", key, exc)


def _delete(*keys: str):
    """Delete one or more keys from the cache."""
    try:
        client = _r()
        if client is None:
            return
        client.delete(*keys)
    except Exception as exc:
        log.debug("Cache DELETE failed: %s", exc)


# ── TTLs (seconds) ────────────────────────────────────────────────────────────
_TTL = {
    "profile":        3_600,   # 1 hour
    "clean_meta":     3_600,   # 1 hour
    "schema":         1_800,   # 30 min
    "user_metrics":     300,   # 5 min
    "insight_count":    600,   # 10 min
    "alert_status":     900,   # 15 min
}


# ── Public read-through helpers ───────────────────────────────────────────────

def get_profile(upload_id: int) -> Optional[dict]:
    key = f"profile:{upload_id}"
    cached = _get(key)
    if cached is not None:
        return cached
    # Caller is responsible for populating the cache if result is available
    return None


def set_profile(upload_id: int, profile: dict):
    _set(f"profile:{upload_id}", profile, _TTL["profile"])


def get_schema(upload_id: int) -> Optional[dict]:
    return _get(f"schema:{upload_id}")


def set_schema(upload_id: int, schema: dict):
    _set(f"schema:{upload_id}", schema, _TTL["schema"])


def get_clean_meta(upload_id: int) -> Optional[dict]:
    return _get(f"clean_meta:{upload_id}")


def set_clean_meta(upload_id: int, meta: dict):
    _set(f"clean_meta:{upload_id}", meta, _TTL["clean_meta"])


def get_alert_status(upload_id: int) -> Optional[dict]:
    return _get(f"alert_status:{upload_id}")


def set_alert_status(upload_id: int, status: dict):
    _set(f"alert_status:{upload_id}", status, _TTL["alert_status"])


def get_user_metrics(user_id: int) -> Optional[list]:
    return _get(f"user_metrics:{user_id}")


def set_user_metrics(user_id: int, metrics: list):
    _set(f"user_metrics:{user_id}", metrics, _TTL["user_metrics"])


def invalidate_upload(upload_id: int):
    """Nuke all cache keys associated with a dataset (call after any mutation)."""
    _delete(
        f"profile:{upload_id}",
        f"schema:{upload_id}",
        f"clean_meta:{upload_id}",
        f"alert_status:{upload_id}",
        f"insight_count:{upload_id}",
    )


def invalidate_user(user_id: int):
    """Nuke user-level caches."""
    _delete(f"user_metrics:{user_id}")


# ── Rate limiter ──────────────────────────────────────────────────────────────

def rate_limit(user_id: int, action: str, limit: int = 3, window_s: int = 60) -> bool:
    """
    Sliding-window rate limiter.
    Returns True when the request is ALLOWED, False when the limit is exceeded.
    Falls back to True (allow) when Redis is unavailable.
    """
    try:
        client = _r()
        if client is None:
            return True  # graceful degradation
        key   = f"rate_limit:{user_id}:{action}"
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_s)
        return count <= limit
    except Exception:
        return True  # never block the user due to Redis failure
