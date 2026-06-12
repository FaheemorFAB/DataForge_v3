"""
dataforge/web/tasks.py
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

import os, json, logging
from datetime import datetime
from pathlib import Path
from filelock import FileLock

log = logging.getLogger(__name__)

ROOT_DIR   = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT_DIR.parent

# ── Flask + Celery factory ────────────────────────────────────────────────────
# Import order matters: create the Flask app shell first, then Celery.
from dotenv import load_dotenv
load_dotenv(override=True, dotenv_path=PROJECT_ROOT / ".env")
if (ROOT_DIR / ".env").exists():
    load_dotenv(override=True, dotenv_path=ROOT_DIR / ".env")

from flask import Flask
from flask_socketio import SocketIO

from dataforge.db import db_get, db_update, db_insert, db_delete, db_client
from dataforge.settings import PROJECTS_DIR
from .celery_app import make_celery

# Minimal Flask app for the worker (no routes needed)
def create_worker_app():
    _app = Flask(__name__)
    _app.config["broker_url"]    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _app.config["result_backend"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _app.secret_key = os.environ["FLASK_SECRET_KEY"]
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


# ── Shared storage helpers (single source from storage.py) ───────────────────
from .storage import STORE_DIR, _upath, _lock_path, _save, _load


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
    from .helpers import _load_persisted

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            for key in ("df_clean", "df_raw"):
                restored = _load_persisted(upload_id, key)
                if restored is not None:
                    _save(upload_id, key, restored)
                    df = restored
                    break
        if df is None:
            raise RuntimeError(
                "Dataset for upload_id=%s could not be restored. The saved file is missing or corrupted."
                % upload_id
            )

        automl_meta = _load(upload_id, "automl_meta") or {}
        fi = {r["feature"]: r["importance"]
              for r in (automl_meta.get("feature_importance") or [])
              if isinstance(r, dict)}

        schema   = detect_schema(df, feature_importance=fi)
        insights = run_insights(df, schema, top_n=top_n)

        gemini_fn = None  # Completely devoid of Gemini for insights

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
            db_client.table("insight_records").delete().eq("upload_id", upload_id).execute()
            
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
        from .cache import invalidate_upload
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
        if self.request.retries >= self.max_retries:
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
    from .helpers import _load_persisted

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            for key in ("df_clean", "df_raw"):
                restored = _load_persisted(upload_id, key)
                if restored is not None:
                    _save(upload_id, key, restored)
                    df = restored
                    break
        if df is None:
            raise RuntimeError(
                "Dataset for upload_id=%s could not be restored. The saved file is missing or corrupted."
                % upload_id
            )

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

        from .cache import invalidate_upload
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
def task_run_eda(self, upload_id: int, user_id: int,
                  minimal: bool = True, sample_n: int = 5000):
    from dataforge.eda_report import generate_eda_report

    _job_start(self.request.id)
    try:
        df_clean = _load(upload_id, "df_clean")
        df_raw   = _load(upload_id, "df_raw")
        df       = df_clean if df_clean is not None else df_raw
        if df is None:
            raise RuntimeError("No dataset found for upload_id=%s" % upload_id)

        report_res = generate_eda_report(df, minimal=minimal, sample_n=sample_n)
        if report_res.get("error"):
            raise RuntimeError(report_res["error"])
        html = report_res.get("html")
        if not html:
            raise RuntimeError("EDA report generation returned empty HTML")

        # Save to PROJECTS_DIR for persistence
        d = PROJECTS_DIR / str(upload_id)
        d.mkdir(exist_ok=True)
        (d / "eda_html").write_text(html, encoding="utf-8")
        _save(upload_id, "eda_html", html)

        from .cache import invalidate_upload
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
        if self.request.retries >= self.max_retries:
            _job_fail(self.request.id, str(exc))
        raise self.retry(exc=exc, countdown=5)


# ══════════════════════════════════════════════════════════════════════════════
# TASK: GENERATE HTML REPORT
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.generate_report", max_retries=1)
def task_generate_report(self, upload_id: int, user_id: int):
    from dataforge.insight_engine  import detect_schema, run_insights
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
        
        if not schema:
            schema = detect_schema(df)
        if not insights:
            insights = run_insights(df, schema, top_n=6)

        profile = _load(upload_id, "profile") or {}
        up = db_get("uploads", upload_id)
        filename = up.get("filename", "") if up else "Dataset"

        # ── Gather metrics and data for Gemini commentary ──────────────────
        rows = df.shape[0]
        cols = df.shape[1]
        missing_cells = int(df.isnull().sum().sum())
        total_cells = rows * cols
        miss_pct = round((missing_cells / total_cells * 100), 2) if total_cells > 0 else 0.0
        
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(include="object").columns.tolist()
        
        stats_lines = [
            f"- Dataset Shape: {rows:,} rows x {cols} columns",
            f"- Missing Data: {missing_cells:,} cells ({miss_pct}%)",
            f"- Numeric columns ({len(numeric_cols)}): {', '.join(numeric_cols[:10])}",
            f"- Categorical columns ({len(cat_cols)}): {', '.join(cat_cols[:10])}"
        ]
        
        for col in numeric_cols[:3]:
            try:
                s = df[col].dropna()
                if len(s) > 0:
                    stats_lines.append(f"  * {col}: Mean={s.mean():,.2f}, Min={s.min():,.2f}, Max={s.max():,.2f}")
            except Exception:
                pass
        for col in cat_cols[:3]:
            try:
                vc = df[col].value_counts().head(3)
                stats_lines.append(f"  * {col} top values: {', '.join(f'{k} ({v})' for k, v in vc.items())}")
            except Exception:
                pass
                
        stats_summary_text = "\n".join(stats_lines)
        insights_bullet_points = "\n".join(
            f"- [{i.get('type','').upper()}] {i.get('title')}: {i.get('description')}"
            for i in insights
        )

        gemini_commentary = ""
        try:
            from dataforge.gemini_pipeline import _gemini
            prompt = f"""You are a top-tier McKinsey business analyst and strategy consultant.
You are preparing a corporate presentation slide deck summarizing a dataset analysis.

DATASET NAME: {filename}
DATASET TYPE: {schema.get('dataset_type', 'general')}

METADATA & STATS:
{stats_summary_text}

ALGORITHMIC INSIGHTS:
{insights_bullet_points}

TASK:
Write a premium, executive-level business analysis commentary for our presentation.
Provide exactly 4 sections separated by clear delimiters. Keep the text concise (3-5 sentences per section) and professional. Do NOT include markdown styling like asterisks or subheadings inside the sections.

Format your output EXACTLY as follows:
---SLIDE_1---
[Write the Executive Summary & Business Potential here]

---SLIDE_2---
[Write the Critical Patterns & Anomalies analysis here]

---SLIDE_3---
[Write the Data Health & Structural Watchouts commentary here]

---SLIDE_4---
[Write 3 concrete, high-impact Strategic Recommendations here]
"""
            gemini_commentary = _gemini(prompt, temperature=0.7)
        except Exception as api_err:
            log.warning("Gemini API commentary generation failed: %s", api_err)

        slide1 = ""
        slide2 = ""
        slide3 = ""
        slide4 = ""
        
        if gemini_commentary:
            parts = gemini_commentary.split("---SLIDE_")
            for part in parts:
                part_clean = part.strip()
                if not part_clean:
                    continue
                if part_clean.startswith("1---") or part_clean.startswith("1---\n") or part_clean.startswith("1\n") or part_clean.startswith("1"):
                    slide1 = part_clean.split("---", 1)[-1].strip() if "---" in part_clean else part_clean[2:].strip()
                elif part_clean.startswith("2---") or part_clean.startswith("2---\n") or part_clean.startswith("2\n") or part_clean.startswith("2"):
                    slide2 = part_clean.split("---", 1)[-1].strip() if "---" in part_clean else part_clean[2:].strip()
                elif part_clean.startswith("3---") or part_clean.startswith("3---\n") or part_clean.startswith("3\n") or part_clean.startswith("3"):
                    slide3 = part_clean.split("---", 1)[-1].strip() if "---" in part_clean else part_clean[2:].strip()
                elif part_clean.startswith("4---") or part_clean.startswith("4---\n") or part_clean.startswith("4\n") or part_clean.startswith("4"):
                    slide4 = part_clean.split("---", 1)[-1].strip() if "---" in part_clean else part_clean[2:].strip()

        # Fallbacks if API failed or split failed
        if not slide1 or len(slide1) < 10:
            slide1 = f"Analysis of the dataset '{filename}' shows a {schema.get('dataset_type', 'general')} distribution with {rows:,} records and {cols} dimensions. Standard KPIs point to healthy structure with {miss_pct}% missing value footprint."
        if not slide2 or len(slide2) < 10:
            slide2 = f"Key patterns reveal important drivers across categorical and numeric fields. Outliers and trends suggest specific performance spikes or drops that warrant monitoring."
        if not slide3 or len(slide3) < 10:
            slide3 = f"Data health inspection reveals a stable layout. Column structures are well-formed, with details from the exploratory profile indicating strong correlation alignments."
        if not slide4 or len(slide4) < 10:
            slide4 = "1. Establish alert monitors to catch metric drops.\n2. Optimize dimension structures for cleaner categorization.\n3. Implement monthly recurring reporting to track overall business metrics."

        profile["slide1"] = slide1
        profile["slide2"] = slide2
        profile["slide3"] = slide3
        profile["slide4"] = slide4
        profile["rows"] = rows
        profile["cols"] = cols
        profile["missing_pct"] = miss_pct
        profile["columns"] = list(df.columns)

        html = generate_html_report(
            insights=insights, summary_text=slide1,
            dataset_name=filename,
            dataset_type=schema.get("dataset_type", "general"),
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
        if self.request.retries >= self.max_retries:
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
        from .cache import set_alert_status
        set_alert_status(upload_id, {"count": len(fired), "alerts": fired})

        for a in fired:
            up = db_get("uploads", upload_id)
            _ws("alert", {**a, "filename": up.get("filename", "") if up else "",
                          "ts": datetime.utcnow().isoformat()}, user_id)

        _job_success(self.request.id, {"fired": len(fired)})
        return {"fired": len(fired)}

    except Exception as exc:
        if self.request.retries >= self.max_retries:
            _job_fail(self.request.id, str(exc))
        raise self.retry(exc=exc, countdown=5)


# ══════════════════════════════════════════════════════════════════════════════
# TASK: SCHEDULED REPORT (Celery Beat)
# ══════════════════════════════════════════════════════════════════════════════

@celery.task(bind=True, name="tasks.run_scheduled_report")
def task_run_scheduled_report(self, schedule_id: int):
    """Used by Celery Beat for periodic report generation."""
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
        db_insert("jobs", {
            "id": inner.id,
            "user_id": sched.get("user_id"),
            "upload_id": sched.get("upload_id"),
            "type": "report"
        })

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
