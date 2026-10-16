"""
dataforge/api/limiter.py
────────────────────────
Shared SlowAPI rate limiter instance backed by spoof-resistant client IP extraction.
"""

from slowapi import Limiter
from dataforge.api.deps import get_remote_addr

limiter = Limiter(
    key_func=get_remote_addr,
    default_limits=["200/minute"],
    headers_enabled=True,
)
