"""
services/web/tasks.py
─────────────────────
All Celery background tasks for DataForge.

Each task follows the same pattern:
  1. Validate inputs and mark the Job row as "started"
  2. Execute the expensive operation
  3. Persist the result to disk (PROJECTS_DIR / upload_id / <key>)
  4. Mark the Job row as "success" or "failure"
  5. Push a WebSocket event to the user's room via Flask-SocketIO message_queue

IMPORTANT: Store only a lightweight reference in Celery's result backend —
never put DataFrames or large objects there. Redis isn't a data lake.
"""

import os, sys, json, logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ── Bootstrap path so shared/ modules are importable inside the worker process
ROOT_DIR   = Path(__file__).resolve().parents[2]
SHARED_DIR = ROOT_DIR / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

# ── Flask + Celery factory ────────────────────────────────────────────────────
# Import order matters: create the Flask app shell first, then Celery.
from dotenv import load_dotenv
load_dotenv(override=True, dotenv_path=ROOT_DIR / ".env")

from flask import Flask
from flask_socketio import SocketIO

from dataforge.db import db_get, db_update, db_insert, db_delete, db_client
from dataforge.settings import PROJECTS_DIR, INSTANCE_DIR
from celery_app import make_celery

# Minimal Flask app for the worker (no routes needed)
def create_worker_app():
    _app = Flask(__name__)
    _app.config["CELERY_BROKER_URL"]    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _app.config["CELERY_RESULT_BACKEND"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _app.secret_key = os.getenv("FLASK_SECRET_KEY", "worker-secret")
    return _app


worker_app = create_worker_app()
celery     = make_celery(worker_app)

# SocketIO with message_queue so workers can push WebSocket events across processes
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_sio = None

def _socketio():
    global _sio
    if _sio is None:
        try:
            _sio = SocketIO(message_queue=REDIS_URL)
        except Exception:
            pass
    return _sio


def _ws(event: str, data: dict, user_id: int):
    """Best-effort WebSocket push from a Celery worker via Redis pub/sub."""
    try:
        sio = _socketio()
        if sio:
            sio.emit(event, data, room=f"user_{user_id}", namespace="/")
    except Exception as e:
        log.debug("Worker WS push failed: %s", e)


# ── Shared storage helpers (mirrors app.py _load / _save) ────────────────────
import pandas as pd
from filelock import FileLock

STORE_DIR = Path(os.getenv("DATAFORGE_STORE_DIR",
                            str(Path.home() / ".dataforge_store")))
STORE_DIR.mkdir(parents=True, exist_ok=True)


def _upath(upload_id: int, key: str) -> Path:
    d = STORE_DIR / str(upload_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / key


def _lock_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")


def _load(upload_id: int, key: str):
    path = _upath(upload_id, key)
    p_pq   = path.with_suffix(".parquet")
    p_json = path.with_suffix(".json")
    p_bin  = path.with_suffix(".joblib")
    if p_pq.exists():
        with FileLock(_lock_path(p_pq)):
            return pd.read_parquet(p_pq)
    if p_json.exists():
        with FileLock(_lock_path(p_json)):
            return json.loads(p_json.read_text(encoding="utf-8"))
    if p_bin.exists():
        with FileLock(_lock_path(p_bin)):
            return p_bin.read_bytes()
    return None


def _save(upload_id: int, key: str, obj):
    path = _upath(upload_id, key)
    lock = FileLock(_lock_path(path))
    with lock:
        if isinstance(obj, pd.DataFrame):
            tmp = path.with_suffix(".parquet.tmp")
            obj.to_parquet(tmp, index=False, compression="snappy")
            tmp.replace(path.with_suffix(".parquet"))
        elif isinstance(obj, bytes):
            tmp = path.with_suffix(".joblib.tmp")
            tmp.write_bytes(obj)
            tmp.replace(path.with_suffix(".joblib"))
        else:
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(obj, default=str), encoding="utf-8")
            tmp.replace(path.with_suffix(".json"))


def _job_start(task_id: str):
    job = db_get("jobs", task_id)
    if job:
        db_update("jobs", task_id, {"status": "started"})


def _job_success(task_id: str, result_ref: dict):
    job = db_get("jobs", task_id)
    if job:
        db_update("jobs", task_id, {
            "status": "success",
            "result_ref": json.dumps(result_ref),
            "finished_at": datetime.utcnow().isoformat()
        })


def _job_fail(task_id: str, error: str):
    job = db_get("jobs", task_id)
    if job:
        db_update("jobs", task_id, {
            "status": "failure",
            "error": error[:2000],
            "finished_at": datetime.utcnow().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════════════
# TASK: RUN INSIGHTS + GEMINI SUMMARISE
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.run_insights", max_retries=2)
def task_run_insights(self, upload_id: int, user_id: int,
                      top_n: int = 6, use_gemini: bool = True):
    from dataforge.insight_engine import detect_schema, run_insights, summarise_with_gemini
    from dataforge.gemini_pipeline import is_available as gemini_available

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            raise RuntimeError("No dataset found for upload_id=%s" % upload_id)

        automl_meta = _load(upload_id, "automl_meta") or {}
        fi = {r["feature"]: r["importance"]
              for r in (automl_meta.get("feature_importance") or [])
              if isinstance(r, dict)}

        schema   = detect_schema(df, feature_importance=fi)
        insights = run_insights(df, schema, top_n=top_n)

        gemini_fn = None
        if use_gemini and gemini_available():
            try:
                from dataforge.gemini_pipeline import _call_gemini
                gemini_fn = _call_gemini
            except Exception:
                pass

        up = db_get("uploads", upload_id)
        filename = up.get("filename", "") if up else "Dataset"
        summary = summarise_with_gemini(
            insights, dataset_name=filename,
            dataset_type=schema["dataset_type"], gemini_fn=gemini_fn,
        )

        # Persist results to disk
        _save(upload_id, "last_insights", insights)
        _save(upload_id, "last_schema",   schema)
        _save(upload_id, "last_summary",  summary if isinstance(summary, str)
              else json.dumps(summary))

        # Persist insight rows to DB
        try:
            db_delete("insight_records", upload_id, match_col="upload_id")
            
            insert_data = []
            for ins in insights:
                insert_data.append({
                    "upload_id": upload_id, "user_id": user_id,
                    "type": ins.get("type", ""), "title": ins.get("title", ""),
                    "description": ins.get("description", ""), "importance": ins.get("importance", 0.0),
                    "chart_type": ins.get("chart"), "metric": ins.get("metric", ""),
                    "chart_data": json.dumps(ins.get("chart_data")) if ins.get("chart_data") else None,
                })
            
            if insert_data:
                db_client.table("insight_records").insert(insert_data).execute()
        except Exception as e:
            log.warning("Failed to bulk persist insights inside Celery: %s", e)

        # Invalidate Redis cache
        from cache import invalidate_upload
        invalidate_upload(upload_id)

        _job_success(self.request.id, {"key": "last_insights", "count": len(insights)})

        _ws("insight_ready", {
            "upload_id": upload_id,
            "count":     len(insights),
            "dataset_type": schema["dataset_type"],
            "filename":  filename,
            "ts":        datetime.utcnow().isoformat(),
        }, user_id)

        return {"key": "last_insights", "count": len(insights)}

    except Exception as exc:
        _job_fail(self.request.id, str(exc))
        raise self.retry(exc=exc, countdown=5)


# ══════════════════════════════════════════════════════════════════════════════
# TASK: AUTOML TRAINING
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.run_automl", max_retries=0)
def task_run_automl(self, upload_id: int, user_id: int,
                    target_col: str, task_choice: str = "auto-detect",
                    time_budget: int = 60, test_size: float = 0.2):
    from dataforge.automl_trainer import run_automl

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            raise RuntimeError("No dataset found for upload_id=%s" % upload_id)

        result = run_automl(df, target_col, task_choice=task_choice,
                            time_budget=time_budget, test_size=test_size)
        if result.get("error"):
            raise RuntimeError(result["error"])

        model_pkl = result.pop("model_pkl", None)
        result["target_col"] = target_col

        # Persist meta (no model bytes in Redis result)
        _save(upload_id, "automl_meta", result)

        # Persist model bytes to disk + PROJECTS_DIR
        if model_pkl:
            d = PROJECTS_DIR / str(upload_id)
            d.mkdir(exist_ok=True)
            lock = FileLock(_lock_path(d / "model_pkl.lock"))
            with lock:
                (d / "model_pkl.joblib").write_bytes(model_pkl)

        # Update Upload row
        try:
            db_update("uploads", upload_id, {
                "automl_meta_json": json.dumps(result, default=str)
            })
        except Exception as e:
            log.warning("Failed to save automl_meta_json to DB: %s", e)

        from cache import invalidate_upload
        invalidate_upload(upload_id)

        _job_success(self.request.id, {"key": "automl_meta"})

        up = db_get("uploads", upload_id)
        _ws("automl_ready", {
            "upload_id":     upload_id,
            "best_estimator": result.get("best_estimator", ""),
            "task":          result.get("task", ""),
            "elapsed_s":     result.get("elapsed_s", ""),
            "filename":      up.get("filename", "") if up else "",
            "ts":            datetime.utcnow().isoformat(),
        }, user_id)

        return {"key": "automl_meta"}

    except Exception as exc:
        _job_fail(self.request.id, str(exc))
        raise  # No retry for AutoML (expensive)


# ══════════════════════════════════════════════════════════════════════════════
# TASK: EDA REPORT
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.run_eda", max_retries=1)
def task_run_eda(self, upload_id: int, user_id: int):
    from dataforge.eda_report import generate_eda_report

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            raise RuntimeError("No dataset found for upload_id=%s" % upload_id)

        html = generate_eda_report(df)

        # Save to PROJECTS_DIR for persistence
        d = PROJECTS_DIR / str(upload_id)
        d.mkdir(exist_ok=True)
        (d / "eda_html").write_text(html, encoding="utf-8")
        _save(upload_id, "eda_html", html)

        from cache import invalidate_upload
        invalidate_upload(upload_id)

        _job_success(self.request.id, {"key": "eda_html"})

        up = db_get("uploads", upload_id)
        _ws("eda_ready", {
            "upload_id": upload_id,
            "filename":  up.get("filename", "") if up else "",
            "ts":        datetime.utcnow().isoformat(),
        }, user_id)

        return {"key": "eda_html"}

    except Exception as exc:
        _job_fail(self.request.id, str(exc))
        raise self.retry(exc=exc, countdown=5)


# ══════════════════════════════════════════════════════════════════════════════
# TASK: GENERATE HTML REPORT
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.generate_report", max_retries=1)
def task_generate_report(self, upload_id: int, user_id: int):
    from dataforge.insight_engine  import detect_schema, run_insights, summarise_with_gemini
    from dataforge.report_generator import generate_html_report

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            raise RuntimeError("No dataset found for upload_id=%s" % upload_id)

        insights = _load(upload_id, "last_insights")
        schema   = _load(upload_id, "last_schema")
        summary  = _load(upload_id, "last_summary")

        if not insights:
            schema   = detect_schema(df)
            insights = run_insights(df, schema, top_n=6)
            summary  = summarise_with_gemini(insights, dataset_name="Dataset",
                                             dataset_type=schema["dataset_type"])

        profile = _load(upload_id, "profile") or {}
        up = db_get("uploads", upload_id)
        filename = up.get("filename", "") if up else "Dataset"

        html = generate_html_report(
            insights=insights, summary_text=summary or "",
            dataset_name=filename,
            dataset_type=(schema or {}).get("dataset_type", "general"),
            profile=profile,
        )

        rep = {
            "upload_id": upload_id, "user_id": user_id,
            "report_html": html,
            "report_json": json.dumps({
                "summary": summary,
                "insights": [{k: v for k, v in i.items() if k != "chart_data"}
                             for i in insights],
            }, default=str),
            "triggered_by": "async",
        }
        
        try:
            res = db_insert("reports", rep)
            report_id = res.get("id") if res else None
        except Exception as e:
            log.warning("Failed to insert report to DB: %s", e)
            report_id = None

        _save(upload_id, "report_html", html)

        _job_success(self.request.id, {"report_id": report_id})

        _ws("report_ready", {
            "upload_id": upload_id,
            "report_id": report_id,
            "filename":  filename,
            "ts":        datetime.utcnow().isoformat(),
        }, user_id)

        return {"report_id": report_id}

    except Exception as exc:
        _job_fail(self.request.id, str(exc))
        raise self.retry(exc=exc, countdown=5)


# ══════════════════════════════════════════════════════════════════════════════
# TASK: CHECK ALERTS
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.check_alerts", max_retries=2)
def task_check_alerts(self, upload_id: int, user_id: int):
    from dataforge.alert_engine  import AlertEngine
    from dataforge.insight_engine import detect_schema

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            raise RuntimeError("No dataset for upload_id=%s" % upload_id)

        schema    = _load(upload_id, "last_schema") or detect_schema(df)
        engine    = AlertEngine()
        fired_raw = engine.check(upload_id, df, schema)

        fired = []
        insert_data = []
        for a in fired_raw:
            insert_data.append({
                "upload_id": upload_id, "user_id": user_id,
                "rule": a["rule"], "message": a["message"], "severity": a["severity"],
                "metric": a.get("metric", ""), "pct_change": a.get("pct_change")
            })
            fired.append(a)

        if insert_data:
            try:
                db_client.table("alerts").insert(insert_data).execute()
            except Exception as e:
                log.warning("Failed to bulk insert alerts to DB: %s", e)

        # Cache the alert status
        from cache import set_alert_status
        set_alert_status(upload_id, {"count": len(fired), "alerts": fired})

        for a in fired:
            up = db_get("uploads", upload_id)
            _ws("alert", {**a, "filename": up.get("filename", "") if up else "",
                          "ts": datetime.utcnow().isoformat()}, user_id)

        _job_success(self.request.id, {"fired": len(fired)})
        return {"fired": len(fired)}

    except Exception as exc:
        _job_fail(self.request.id, str(exc))
        raise self.retry(exc=exc, countdown=5)


# ══════════════════════════════════════════════════════════════════════════════
# TASK: SCHEDULED REPORT (Celery Beat)
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.run_scheduled_report")
def task_run_scheduled_report(self, schedule_id: int):
    """Used by Celery Beat for periodic report generation."""
    from dataforge.models import ReportSchedule

    _job_start(self.request.id)
    try:
        sched = db_get("report_schedules", schedule_id)
        if not sched or not sched.get("enabled"):
            _job_success(self.request.id, {"skipped": True})
            return

        # Delegate to generate_report task
        inner = task_generate_report.apply_async(
            args=[sched.get("upload_id"), sched.get("user_id")]
        )

        # Update last_run_at
        now_ts = datetime.utcnow().isoformat()
        db_update("report_schedules", schedule_id, {
            "last_run_at": now_ts,
            "last_run": now_ts
        })

        _job_success(self.request.id, {"delegated_task_id": inner.id})
        return {"delegated_task_id": inner.id}

    except Exception as exc:
        _job_fail(self.request.id, str(exc))
        raise
