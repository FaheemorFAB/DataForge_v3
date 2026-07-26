"""
dataforge/api/jobs/registry.py
────────────────────────────────
Job registry: Supabase is the source of truth, memory is a fast local cache.

On startup, the manager calls `bootstrap()` to reload any in-flight jobs from
Supabase so that a process restart doesn't permanently lose job state.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

# In-memory job store: {job_id: job_dict}
_jobs: Dict[str, dict] = {}
_lock = asyncio.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── CRUD helpers ──────────────────────────────────────────────────────────────

async def create_job(
    user_id: int,
    upload_id: Optional[int],
    job_type: str,
    job_id: Optional[str] = None,
) -> str:
    """
    Insert a new job in both memory and Supabase.
    Returns the generated job_id.
    """
    from dataforge.db import db_insert

    jid = job_id or str(uuid.uuid4())
    record = {
        "id": jid,
        "user_id": user_id,
        "upload_id": upload_id,
        "type": job_type,
        "status": "queued",
        "result_ref": None,
        "error": None,
        "created_at": _now_iso(),
        "finished_at": None,
    }

    async with _lock:
        _jobs[jid] = record.copy()

    try:
        db_insert("jobs", record)
    except Exception as exc:
        log.warning("Failed to persist job %s to Supabase: %s", jid, exc)

    return jid


async def mark_started(job_id: str):
    """Mark a job as 'started' in memory and Supabase."""
    from dataforge.db import db_update

    async with _lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "started"

    try:
        db_update("jobs", job_id, {"status": "started"})
    except Exception as exc:
        log.warning("Failed to mark job %s started in Supabase: %s", job_id, exc)


async def mark_success(job_id: str, result_ref: dict):
    """Mark a job as 'success' with result reference."""
    import json
    from dataforge.db import db_update

    finished = _now_iso()
    async with _lock:
        if job_id in _jobs:
            _jobs[job_id].update({
                "status": "success",
                "result_ref": result_ref,
                "finished_at": finished,
            })

    try:
        db_update("jobs", job_id, {
            "status": "success",
            "result_ref": json.dumps(result_ref, default=str),
            "finished_at": finished,
        })
    except Exception as exc:
        log.warning("Failed to mark job %s success in Supabase: %s", job_id, exc)


async def mark_failed(job_id: str, error: str):
    """Mark a job as 'failure' with the error message."""
    from dataforge.db import db_update

    finished = _now_iso()
    error_short = error[:2000]

    async with _lock:
        if job_id in _jobs:
            _jobs[job_id].update({
                "status": "failure",
                "error": error_short,
                "finished_at": finished,
            })

    try:
        db_update("jobs", job_id, {
            "status": "failure",
            "error": error_short,
            "finished_at": finished,
        })
    except Exception as exc:
        log.warning("Failed to mark job %s failed in Supabase: %s", job_id, exc)


def get_job(job_id: str) -> Optional[dict]:
    """Return the in-memory job dict, or None if not found."""
    return _jobs.get(job_id)


def get_jobs_for_user(user_id: int, limit: int = 20) -> list[dict]:
    """Return recent jobs for a user (newest first), from memory."""
    user_jobs = [j for j in _jobs.values() if j.get("user_id") == user_id]
    user_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return user_jobs[:limit]


def get_active_job(upload_id: int, job_type: str) -> Optional[dict]:
    """Return an active (queued/started) job for an upload, if any."""
    for j in _jobs.values():
        if (j.get("upload_id") == upload_id
                and j.get("type") == job_type
                and j.get("status") in ("queued", "started")):
            return j
    return None


# ── Bootstrap ─────────────────────────────────────────────────────────────────

async def bootstrap():
    """
    Reload in-flight jobs from Supabase into memory on process start.
    Also marks any 'started' jobs older than 10 minutes as failed (stale).
    """
    import json
    from dataforge.db import db_client, db_all

    if db_client is None:
        return

    try:
        recent = db_all("jobs", order_by="created_at", limit=500)
        now_ts = datetime.now(timezone.utc)

        async with _lock:
            for j in recent:
                jid = j.get("id")
                if not jid:
                    continue
                # Parse result_ref back to dict
                rr = j.get("result_ref")
                if rr and isinstance(rr, str):
                    try:
                        j["result_ref"] = json.loads(rr)
                    except Exception:
                        pass

                # Auto-expire stale in-flight jobs
                status = j.get("status", "queued")
                if status in ("queued", "started"):
                    created_str = j.get("created_at", "")
                    try:
                        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        age_s = (now_ts - created).total_seconds()
                        stale_after = 120 if status == "queued" else 600
                        if age_s > stale_after:
                            j["status"] = "failure"
                            j["error"] = "Stale job (process restart or worker died)"
                    except Exception:
                        pass

                _jobs[jid] = j

        log.info("Job registry bootstrapped: %d jobs loaded", len(_jobs))
    except Exception as exc:
        log.warning("Job registry bootstrap failed: %s", exc)
