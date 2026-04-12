"""
DataForge — Cache Manager
═════════════════════════
Provides a unified cache interface that works even when Redis is offline.

Strategy
────────
1. Try Redis first (fast, shared across workers).
2. On any Redis failure, transparently fall back to an in-process TTL dict.
3. All failures are logged as warnings — never raised to the caller.

Usage::

    from dataforge.cache_manager import cache

    # Store a value (default TTL = 3600 s)
    cache.set("automl_model:upload_42", model_bytes, ttl=7200)

    # Retrieve — returns None on miss or error
    data = cache.get("automl_model:upload_42")

    # Delete
    cache.delete("automl_model:upload_42")

    # Check backend
    print(cache.backend)   # "redis" | "memory"

Flask-Caching integration
─────────────────────────
Replace the hard Redis dependency in your Flask app::

    # services/web/app.py  ← was:
    #   cache = Cache(app, config={"CACHE_TYPE": "redis", "CACHE_REDIS_URL": REDIS_URL})
    # Replace with:
    from dataforge.cache_manager import make_flask_cache_config
    cache = Cache(app, config=make_flask_cache_config(REDIS_URL))

Flask-SocketIO integration
──────────────────────────
Replace the hard Redis message-queue dependency::

    # services/web/app.py  ← was:
    #   socketio = SocketIO(app, message_queue=REDIS_URL)
    # Replace with:
    from dataforge.cache_manager import safe_socketio_kwargs
    socketio = SocketIO(app, **safe_socketio_kwargs(REDIS_URL))
"""

from __future__ import annotations

import io
import joblib
import logging
import threading
import time
from typing import Any, Optional

log = logging.getLogger(__name__)

# ── In-memory fallback store ──────────────────────────────────────────────────

class _MemoryStore:
    """
    Thread-safe in-process key/value store with per-key TTL expiry.
    Used automatically when Redis is unreachable.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}   # key → (value, expires_at)
        self._lock  = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def flush(self) -> None:
        with self._lock:
            self._store.clear()

    def purge_expired(self) -> int:
        """Remove expired entries; returns count removed."""
        now = time.monotonic()
        with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]
        return len(expired)


# ── Unified cache interface ───────────────────────────────────────────────────

class CacheManager:
    """
    Unified cache: tries Redis, falls back silently to in-memory.

    Parameters
    ----------
    redis_url : str | None
        Redis connection URL (e.g. "redis://localhost:6379/0").
        Pass None or omit to use the memory backend directly.
    connect_timeout : float
        Seconds to wait for the initial Redis ping before giving up.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        connect_timeout: float = 2.0,
    ) -> None:
        self._memory   = _MemoryStore()
        self._redis    = None
        self._backend  = "memory"

        if redis_url:
            self._try_connect_redis(redis_url, connect_timeout)

    # ── Backend probing ───────────────────────────────────────────────────────

    def _try_connect_redis(self, url: str, timeout: float) -> None:
        try:
            import redis  # type: ignore
            client = redis.Redis.from_url(
                url,
                socket_connect_timeout=timeout,
                socket_timeout=timeout,
                decode_responses=False,   # we store raw bytes via pickle
            )
            client.ping()                 # raises if Redis is offline
            self._redis   = client
            self._backend = "redis"
            log.info("CacheManager: connected to Redis at %s", url)
        except Exception as exc:
            log.warning(
                "CacheManager: Redis unavailable (%s). "
                "Falling back to in-process memory cache. "
                "All functionality will continue to work — "
                "cache is NOT shared across worker processes in fallback mode.",
                exc,
            )
            self._redis   = None
            self._backend = "memory"

    def _reconnect_if_needed(self) -> bool:
        """Ping Redis; if it fails, mark backend as memory. Returns True if Redis is alive."""
        if self._redis is None:
            return False
        try:
            self._redis.ping()
            self._backend = "redis"
            return True
        except Exception:
            self._backend = "memory"
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def backend(self) -> str:
        """Returns "redis" or "memory"."""
        return self._backend

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or None on miss / error."""
        # Try Redis
        if self._redis is not None and self._reconnect_if_needed():
            try:
                raw = self._redis.get(key)
                if raw is not None:
                    buf = io.BytesIO(raw)
                    return joblib.load(buf)
                return None
            except Exception as exc:
                log.warning("CacheManager.get Redis error for key %r: %s — using memory", key, exc)
                self._backend = "memory"

        # Fallback
        return self._memory.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Store value under key with TTL seconds.
        Returns True on success, False on error (never raises).
        """
        # Try Redis
        if self._redis is not None and self._reconnect_if_needed():
            try:
                buf = io.BytesIO()
                joblib.dump(value, buf)
                self._redis.setex(key, ttl, buf.getvalue())
                return True
            except Exception as exc:
                log.warning("CacheManager.set Redis error for key %r: %s — using memory", key, exc)
                self._backend = "memory"

        # Fallback
        try:
            self._memory.set(key, value, ttl)
            return True
        except Exception as exc:
            log.error("CacheManager.set memory error for key %r: %s", key, exc)
            return False

    def delete(self, key: str) -> None:
        """Delete a key from whichever backend holds it."""
        try:
            if self._redis is not None:
                self._redis.delete(key)
        except Exception:
            pass
        self._memory.delete(key)

    def get_or_set(self, key: str, factory, ttl: int = 3600) -> Any:
        """
        Return cached value if present; otherwise call factory(), cache and return result.

        factory must be a zero-argument callable.

        Example::
            result = cache.get_or_set(
                f"insights:{upload_id}",
                lambda: engine.run_insights(df, schema),
                ttl=600,
            )
        """
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        if value is not None:
            self.set(key, value, ttl)
        return value

    def flush(self) -> None:
        """Clear ALL keys from both backends (use with caution)."""
        try:
            if self._redis is not None:
                self._redis.flushdb()
        except Exception as exc:
            log.warning("CacheManager.flush Redis error: %s", exc)
        self._memory.flush()


# ── Flask-Caching config helper ───────────────────────────────────────────────

def make_flask_cache_config(redis_url: Optional[str] = None) -> dict:
    """
    Return a Flask-Caching config dict that falls back to SimpleCache if
    Redis is unavailable.

    Usage in services/web/app.py::

        from dataforge.cache_manager import make_flask_cache_config
        cache = Cache(app, config=make_flask_cache_config(REDIS_URL))
    """
    if redis_url:
        try:
            import redis as _redis
            c = _redis.Redis.from_url(redis_url, socket_connect_timeout=2)
            c.ping()
            log.info("Flask-Cache: using RedisCache backend")
            return {
                "CACHE_TYPE":      "RedisCache",
                "CACHE_REDIS_URL": redis_url,
                "CACHE_DEFAULT_TIMEOUT": 300,
            }
        except Exception as exc:
            log.warning(
                "Flask-Cache: Redis ping failed (%s). "
                "Falling back to SimpleCache (in-process).",
                exc,
            )

    log.info("Flask-Cache: using SimpleCache backend")
    return {
        "CACHE_TYPE":            "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }


# ── Flask-SocketIO helper ─────────────────────────────────────────────────────

def safe_socketio_kwargs(redis_url: Optional[str] = None) -> dict:
    """
    Return SocketIO kwargs with message_queue set only when Redis is reachable.
    If Redis is offline, omits message_queue so SocketIO starts in single-process
    mode — real-time events still work, just not across multiple workers.

    Usage in services/web/app.py::

        from dataforge.cache_manager import safe_socketio_kwargs
        socketio = SocketIO(app, **safe_socketio_kwargs(REDIS_URL))
    """
    if redis_url:
        try:
            import redis as _redis
            c = _redis.Redis.from_url(redis_url, socket_connect_timeout=2)
            c.ping()
            log.info("SocketIO: using Redis message queue at %s", redis_url)
            return {"message_queue": redis_url}
        except Exception as exc:
            log.warning(
                "SocketIO: Redis unreachable (%s). "
                "Starting in single-process mode — real-time events will work "
                "but are not shared across gunicorn workers.",
                exc,
            )
    return {}


# ── Module-level singleton (configure once at startup) ────────────────────────

import os as _os

_DEFAULT_REDIS_URL = _os.environ.get("REDIS_URL")   # e.g. redis://localhost:6379/0

cache = CacheManager(redis_url=_DEFAULT_REDIS_URL)
