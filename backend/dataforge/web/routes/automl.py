"""
routes/automl.py — AutoML Blueprint
"""
import io
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user

automl_bp = Blueprint("automl_bp", __name__)


@automl_bp.route("/api/automl/detect-task", methods=["POST"])
@login_required
def api_automl_detect_task():
    from ..storage import _load
    from ..helpers import _get_upload_id, _get_upload_or_403, _exists, _detect_task

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    body = request.get_json(force=True) or {}
    target_col = body.get("target_col", "")
    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")
    if not target_col or target_col not in df.columns:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols     = df.select_dtypes(include=["object","category"]).columns.tolist()
        return jsonify({
            "error":           f"Column '{target_col}' not found" if target_col else "No target column specified",
            "candidates":      numeric_cols + cat_cols,
            "columns":         df.columns.tolist(),
            "needs_selection": True,
        }), 400
    task     = _detect_task(df[target_col])
    n_unique = int(df[target_col].nunique())
    return jsonify({"task": task, "n_unique": n_unique})


@automl_bp.route("/api/automl/train", methods=["POST"])
@login_required
def api_automl_train():
    from flask import current_app
    from ..storage import _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _exists,
                           _rate_limit, _tasks, _run_task_sync, _db_log_analysis,
                           SYNC_FALLBACK_ENABLED)
    from dataforge.db import db_all, db_insert

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    body = request.get_json(force=True) or {}
    target_col  = body.get("target_col", "")
    task_choice = body.get("task_choice", "auto-detect")
    time_budget = max(10, min(int(body.get("time_budget", 60)), 900))
    test_size   = max(0.1, min(float(body.get("test_size", 20)) / 100.0, 0.4))

    if not _rate_limit(current_user.id, "automl", limit=2, window_s=120):
        return jsonify({"error": "Rate limit: max 2 AutoML jobs per 2 minutes"}), 429

    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")
    if not target_col or target_col not in df.columns:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols     = df.select_dtypes(include=["object", "category"]).columns.tolist()
        return jsonify({
            "error":           f"Column '{target_col}' not found" if target_col else "No target column specified",
            "candidates":      numeric_cols + cat_cols,
            "needs_selection": True,
        }), 400

    existing_jobs = db_all("jobs", {"upload_id": upload_id, "type": "automl"}, order_by="created_at", limit=5)
    existing = next((j for j in existing_jobs if j.get("status") in {"queued", "started"}), None)
    if existing:
        return jsonify({"task_id": existing.get("id"), "queued": existing.get("status") == "queued"}), 200

    try:
        (_, task_run_automl, *_) = _tasks()
        job = task_run_automl.apply_async(
            args=[upload_id, current_user.id, target_col, task_choice, time_budget, test_size]
        )
        db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "automl"})
        _db_log_analysis("automl", f"queued · target={target_col} · budget={time_budget}s")
        return jsonify({"task_id": job.id, "queued": True}), 202
    except Exception as e:
        current_app.logger.error("Celery task dispatch failed: %s", e)
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (_, task_run_automl, *_) = _tasks()
            _run_task_sync(task_run_automl, [upload_id, current_user.id, target_col, task_choice, time_budget, test_size])
            meta = _load(upload_id, "automl_meta") or {}
            _db_log_analysis("automl", f"completed sync fallback · target={target_col}")
            return jsonify({"queued": False, "sync": True, **meta}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for automl: %s", se)
            return jsonify({"error": f"AutoML failed: {se}"}), 500


@automl_bp.route("/api/automl/download")
@login_required
def api_automl_download():
    from ..helpers import _get_upload_id, _load_persisted

    upload_id = _get_upload_id()
    model_pkl = None
    if upload_id:
        model_pkl = _load_persisted(upload_id, "model_pkl")
    if model_pkl is None:
        return jsonify({"error": "No trained model found. Run AutoML first."}), 404
    return send_file(
        io.BytesIO(model_pkl),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name="dataforge_model.pkl",
    )


@automl_bp.route("/api/clean/download")
@login_required
def api_clean_download():
    from ..storage import _load
    from ..helpers import _get_upload_id, _get_upload_or_403, _exists, _get_filename

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    df = _load(upload_id, "df_clean")
    if df is None:
        return jsonify({"error": "No cleaned dataset. Run cleaning first."}), 404
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    fname = _get_filename(upload_id).replace(".csv", "_cleaned.csv")
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=fname,
    )
