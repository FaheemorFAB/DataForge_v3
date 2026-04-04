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
    from ..helpers import _tasks
    from dataforge.db import db_get

    job = db_get("jobs", task_id)
    if not job or job.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404

    celery_status = job.get("status")
    try:
        from celery.result import AsyncResult
        (task_run_insights, *_) = _tasks()
        res = AsyncResult(task_id)
        if res.state == "FAILURE" and job.get("status") not in ("failure", "success"):
            celery_status = "failure"
        elif res.state == "SUCCESS" and job.get("status") not in ("failure", "success"):
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
        "error":       job.get("error"),
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
