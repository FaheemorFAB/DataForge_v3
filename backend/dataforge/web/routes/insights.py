"""
routes/insights.py — Insights & Root Cause Blueprint
"""
import json
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

insights_bp = Blueprint("insights_bp", __name__)


@insights_bp.route("/api/insights/run", methods=["POST"])
@login_required
def api_insights_run():
    from flask import current_app
    from ..storage import _load, _save
    from ..helpers import (_get_upload_id, _get_upload_or_403, _exists,
                           _rate_limit, _tasks, _run_task_sync, _db_log_analysis,
                           _load_persisted, _broker_available,
                           REPORTING_ENABLED, SYNC_FALLBACK_ENABLED)
    from dataforge.db import db_first, db_insert

    if not REPORTING_ENABLED:
        return jsonify({"error": "Reporting engine not installed"}), 503

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err

    df = _load(upload_id, "df_clean")
    if df is None:
        df = _load(upload_id, "df_raw")
    if df is None:
        for key in ("df_clean", "df_raw"):
            restored = _load_persisted(upload_id, key)
            if restored is not None:
                _save(upload_id, key, restored)
                df = restored
                break
    if df is None and not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({
            "error": "Dataset for this upload could not be restored. The saved file is missing or corrupted. Re-upload the original dataset and try again."
        }), 400
    if df is None:
        return jsonify({
            "error": "Dataset for this upload is not readable right now. Try reopening the project or re-upload the original dataset."
        }), 400

    if not _rate_limit(current_user.id, "insights"):
        return jsonify({"error": "Rate limit: max 3 insight jobs per minute"}), 429

    body    = request.get_json(force=True) or {}
    top_n   = int(body.get("top_n", 6))
    use_gem = bool(body.get("use_gemini", True))

    # Use sync execution when no Celery worker is alive (no-docker local mode)
    if not _broker_available():
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (task_run_insights, *_) = _tasks()
            _run_task_sync(task_run_insights, [upload_id, current_user.id, top_n, use_gem])
            insights = _load(upload_id, "last_insights") or []
            summary = _load(upload_id, "last_summary") or ""
            schema = _load(upload_id, "last_schema") or {}
            _db_log_analysis("insights", "completed sync (no worker)")
            return jsonify({"queued": False, "sync": True,
                            "insights": insights, "summary": summary, "schema": schema}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for insights: %s", se)
            return jsonify({"error": f"Insights failed: {se}"}), 500

    existing = db_first("jobs", {"upload_id": upload_id, "type": "insights", "status": "started"})
    if existing:
        return jsonify({"task_id": existing["id"], "queued": False}), 200

    try:
        (task_run_insights, *_) = _tasks()
        job = task_run_insights.apply_async(args=[upload_id, current_user.id, top_n, use_gem])
        db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "insights"})
        _db_log_analysis("insights", "queued async")
        return jsonify({"task_id": job.id, "queued": True}), 202
    except Exception as e:
        current_app.logger.error("Celery task dispatch failed: %s", e)
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (task_run_insights, *_) = _tasks()
            _run_task_sync(task_run_insights, [upload_id, current_user.id, top_n, use_gem])
            insights = _load(upload_id, "last_insights") or []
            summary = _load(upload_id, "last_summary") or ""
            schema = _load(upload_id, "last_schema") or {}
            _db_log_analysis("insights", "completed sync fallback")
            return jsonify({
                "queued": False, "sync": True,
                "insights": insights, "summary": summary, "schema": schema,
            }), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for insights: %s", se)
            return jsonify({"error": f"Insights failed: {se}"}), 500


@insights_bp.route("/api/insights/list")
@login_required
def api_insights_list():
    import json
    from ..helpers import _get_upload_id
    from ..storage import _load
    from dataforge.db import db_all

    upload_id = _get_upload_id()
    if not upload_id:
        return jsonify([])
    recs = db_all("insight_records", {"upload_id": upload_id, "user_id": current_user.id})
    recs.sort(key=lambda x: x.get("importance", 0), reverse=True)
    if not recs:
        return jsonify(_load(upload_id, "last_insights") or [])
    return jsonify([{
        "id": r.get("id"), "type": r.get("type"), "title": r.get("title"),
        "description": r.get("description"), "importance": r.get("importance"),
        "chart_type": r.get("chart_type"), "metric": r.get("metric"),
        "chart_data": json.loads(r["chart_data"]) if r.get("chart_data") and isinstance(r["chart_data"], str) else r.get("chart_data"),
    } for r in recs])


@insights_bp.route("/api/insights/current")
@login_required
def api_insights_current():
    from ..storage import _load
    from ..helpers import _get_upload_id, _get_upload_or_403

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    return jsonify({
        "insights": _load(upload_id, "last_insights") or [],
        "summary": _load(upload_id, "last_summary") or "",
        "schema": _load(upload_id, "last_schema") or {},
    })


@insights_bp.route("/api/insights/root-cause", methods=["POST"])
@login_required
def api_root_cause():
    from ..storage import _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _exists,
                           _db_log_analysis, TRANSFORM_ENABLED, run_root_cause)

    if not TRANSFORM_ENABLED:
        return jsonify({"error": "Transform module not available"}), 503

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    body    = request.get_json(force=True) or {}
    _dc     = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")

    schema    = _load(upload_id, "last_schema") or {}
    metric    = body.get("metric") or (schema.get("metrics") or [None])[0]
    dimensions = body.get("dimensions") or schema.get("dimensions") or []
    date_col  = body.get("date_col") or schema.get("date")
    top_n     = int(body.get("top_n", 6))

    if not metric:
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if num_cols:
            metric = num_cols[0]
        else:
            return jsonify({"error": "No numeric metric column found"}), 400

    if not dimensions:
        obj_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        dimensions = obj_cols[:3]

    try:
        result = run_root_cause(
            df=df, metric=metric, dimensions=dimensions,
            date_col=date_col, top_n=top_n,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _db_log_analysis("insights", f"Root cause: {metric} · {len(result.get('drivers', []))} drivers")
    return jsonify({"ok": True, **result})
