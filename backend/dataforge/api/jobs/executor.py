"""
dataforge/api/jobs/executor.py
────────────────────────────────
ThreadPoolExecutor wrapper for CPU-bound work.

Pandas, scikit-learn, FLAML, SHAP are all GIL-holding CPU-heavy operations.
Running them in a ThreadPoolExecutor allows the asyncio event loop to remain
responsive while heavy computation happens in background threads.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Optional

from dataforge.api.config import get_settings

log = logging.getLogger(__name__)

_executor: Optional[ThreadPoolExecutor] = None


def get_executor() -> ThreadPoolExecutor:
    """Return the shared ThreadPoolExecutor (lazily initialized)."""
    global _executor
    if _executor is None:
        settings = get_settings()
        n = settings.RESOLVED_WORKER_THREADS
        _executor = ThreadPoolExecutor(
            max_workers=n,
            thread_name_prefix="dataforge-worker",
        )
        log.info("ThreadPoolExecutor initialized: max_workers=%d", n)
    return _executor


async def run_in_executor(fn: Callable, *args, **kwargs) -> Any:
    """
    Run a synchronous function in the thread pool and await its result.

    Usage:
        result = await run_in_executor(pandas_heavy_fn, df, target_col)
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()
    if kwargs:
        fn = partial(fn, **kwargs)
    return await loop.run_in_executor(executor, fn, *args)


def shutdown_executor():
    """Gracefully shut down the executor (called during app lifespan cleanup)."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
        _executor = None
        log.info("ThreadPoolExecutor shut down")
