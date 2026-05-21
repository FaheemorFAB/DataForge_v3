"""
routes/tasks_api.py — Task Status Blueprint
"""
import json
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

tasks_api_bp = Blueprint("tasks_api_bp", __name__)


@tasks_api_bp.route("/api/task/<task_id>")
@login_required
def api_task_status(task_id):
    from datetime import datetime, timezone
    from ..helpers import _tasks
    from dataforge.db import db_get, db_client as _dbc

    # When no DB client (local only), no task records exist — treat as missing
    if _dbc is None:
        return jsonify({"error": "Not found"}), 404

    job = db_get("jobs", task_id)
    if not job or job.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404

    celery_status = job.get("status", "queued")

    # Detect stale PENDING tasks: if still "queued"/"started" and > 15 s old,
    # no worker is processing it — return failure so the UI stops polling.
    STALE_THRESHOLD_S = 15
    if celery_status in ("queued", "started"):
        try:
            created_str = job.get("created_at")
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_s = (datetime.now(timezone.utc) - created_dt).total_seconds()
                if age_s > STALE_THRESHOLD_S:
                    celery_status = "failure"
        except Exception:
            pass

    # Also check Celery result backend for SUCCESS/FAILURE transitions
    if celery_status not in ("failure", "success"):
        try:
            from celery.result import AsyncResult
            res = AsyncResult(task_id)
            if res.state == "FAILURE":
                celery_status = "failure"
            elif res.state == "SUCCESS":
                celery_status = "success"
        except Exception:
            pass

    result_ref = None
    try:
        result_ref = json.loads(job.get("result_ref")) if job.get("result_ref") else None
    except Exception:
        pass

    return jsonify({
        "id":          job.get("id"),
        "type":        job.get("type"),
        "status":      celery_status,
        "result_ref":  result_ref,
        "error":       job.get("error") or ("No worker available — task was not executed." if celery_status == "failure" else None),
        "created_at":  job.get("created_at"),
        "finished_at": job.get("finished_at"),
    })


@tasks_api_bp.route("/api/tasks")
@login_required
def api_tasks_list():
    from dataforge.db import db_all
    jobs = db_all("jobs", {"user_id": current_user.id}, order_by="created_at", limit=20)
    return jsonify([{
        "id": j.get("id"), "type": j.get("type"), "status": j.get("status"),
        "error": j.get("error"), "created_at": j.get("created_at")
    } for j in jobs])
