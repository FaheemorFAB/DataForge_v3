"""
dataforge/api/routes/tasks.py
───────────────────────────────
Task status polling endpoints: /api/v1/task/{task_id} and /api/v1/tasks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from dataforge.api.deps import CurrentUser
from dataforge.api.jobs import registry
from dataforge.api.repositories.upload import upload_repo

log = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])


@router.get("/tasks/status/{task_id}", summary="Poll a single job status")
async def get_task_status(
    current_user: CurrentUser,
    task_id: str = Path(...),
):
    """Return current status and result_ref for a job."""
    job = registry.get_job(task_id)

    # Fallback to Supabase for jobs not in memory (cross-restart)
    if job is None:
        from dataforge.db import db_get
        job = db_get("jobs", task_id)
        if job:
            # Parse result_ref if stored as JSON string
            import json
            rr = job.get("result_ref")
            if rr and isinstance(rr, str):
                try:
                    job["result_ref"] = json.loads(rr)
                except Exception:
                    pass

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job.get("status", "queued")

    # Auto-expire stale in-flight jobs in the response
    if status in ("queued", "started"):
        stale_s = 120 if status == "queued" else 600
        try:
            created_str = job.get("created_at", "")
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            age_s = (datetime.now(timezone.utc) - created_dt).total_seconds()
            if age_s > stale_s:
                status = "failure"
        except Exception:
            pass

    return {
        "id": job.get("id"),
        "type": job.get("type"),
        "status": status,
        "result": job.get("result_ref"),
        "result_ref": job.get("result_ref"),
        "error": job.get("error") or (
            "Task timed out or worker crashed" if status == "failure" else None
        ),
        "created_at": job.get("created_at"),
        "finished_at": job.get("finished_at"),
    }


@router.get("/tasks", summary="List recent jobs for the current user")
async def list_tasks(
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
):
    """Return the most recent jobs for the authenticated user."""
    jobs = registry.get_jobs_for_user(current_user.id, limit=limit)

    # Merge with Supabase for completeness (covers jobs from previous restarts)
    if not jobs:
        from dataforge.db import db_all
        db_jobs = db_all("jobs", {"user_id": current_user.id}, order_by="created_at", limit=limit)
        jobs = db_jobs

    return [
        {
            "id": j.get("id"),
            "type": j.get("type"),
            "status": j.get("status"),
            "error": j.get("error"),
            "created_at": j.get("created_at"),
        }
        for j in jobs
    ]
