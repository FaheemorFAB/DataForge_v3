"""
dataforge/api/jobs/tasks.py
─────────────────────────────
All background task implementations.

Pattern per task:
  1. mark_started
  2. run_in_executor(cpu_bound_fn, ...)   ← doesn't block the event loop
  3. persist results to disk
  4. update DB
  5. mark_success
  6. ws_manager.send_to_user(...)
  On error: mark_failed + re-raise

These are NOT FastAPI BackgroundTasks — they are plain async coroutines
dispatched via asyncio.create_task() from the JobManager.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# TASK: RUN INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════

async def run_insights_task(
    job_id: str,
    upload_id: int,
    user_id: int,
    top_n: int = 6,
):
    from dataforge.api.jobs import registry
    from dataforge.api.jobs.executor import run_in_executor
    from dataforge.api.storage.manager import load, save
    from dataforge.api.cache.manager import invalidate_upload
    from dataforge.api.websocket.manager import get_ws_manager
    from dataforge.db import db_client, db_get

    await registry.mark_started(job_id)
    try:
        # Load dataframe
        df = await run_in_executor(_load_df, upload_id)
        if df is None:
            raise RuntimeError(f"Dataset for upload_id={upload_id} could not be found or loaded.")

        # Run insights (CPU-bound)
        def _compute():
            from dataforge.insight_engine import detect_schema, run_insights, summarise_with_gemini
            automl_meta = load(upload_id, "automl_meta") or {}
            fi = {r["feature"]: r["importance"]
                  for r in (automl_meta.get("feature_importance") or [])
                  if isinstance(r, dict)}
            schema   = detect_schema(df, feature_importance=fi)
            insights = run_insights(df, schema, top_n=top_n)
            up = db_get("uploads", upload_id)
            filename = up.get("filename", "Dataset") if up else "Dataset"
            summary = summarise_with_gemini(
                insights, dataset_name=filename,
                dataset_type=schema["dataset_type"], gemini_fn=None,
            )
            return schema, insights, summary, filename

        schema, insights, summary, filename = await run_in_executor(_compute)

        # Persist
        save(upload_id, "last_insights", insights)
        save(upload_id, "last_schema",   schema)
        save(upload_id, "last_summary",  summary if isinstance(summary, str) else json.dumps(summary))

        # Bulk-persist insight records to DB
        try:
            if db_client:
                db_client.table("insight_records").delete().eq("upload_id", upload_id).execute()
                insert_data = [{
                    "upload_id": upload_id, "user_id": user_id,
                    "type": ins.get("type", ""), "title": ins.get("title", ""),
                    "description": ins.get("description", ""),
                    "importance": ins.get("importance", 0.0),
                    "chart_type": ins.get("chart"),
                    "metric": ins.get("metric", ""),
                    "chart_data": json.dumps(ins.get("chart_data")) if ins.get("chart_data") else None,
                } for ins in insights]
                if insert_data:
                    db_client.table("insight_records").insert(insert_data).execute()
        except Exception as exc:
            log.warning("Insight DB bulk-persist failed: %s", exc)

        invalidate_upload(upload_id)
        await registry.mark_success(job_id, {"key": "last_insights", "count": len(insights)})

        await get_ws_manager().send_to_user(user_id, "insight_ready", {
            "upload_id": upload_id,
            "count": len(insights),
            "dataset_type": schema["dataset_type"],
            "filename": filename,
            "ts": _now(),
        })

    except Exception as exc:
        log.exception("Insights task %s failed: %s", job_id, exc)
        await registry.mark_failed(job_id, str(exc))
        await get_ws_manager().send_to_user(user_id, "task_failed", {
            "job_id": job_id, "type": "insights", "error": str(exc), "ts": _now()
        })


# ══════════════════════════════════════════════════════════════════════════════
# TASK: AUTOML TRAINING
# ══════════════════════════════════════════════════════════════════════════════

async def run_automl_task(
    job_id: str,
    upload_id: int,
    user_id: int,
    target_col: str,
    task_choice: str = "auto-detect",
    time_budget: int = 60,
    test_size: float = 0.2,
):
    from dataforge.api.jobs import registry
    from dataforge.api.jobs.executor import run_in_executor
    from dataforge.api.storage.manager import load, save
    from dataforge.api.cache.manager import invalidate_upload
    from dataforge.api.websocket.manager import get_ws_manager
    from dataforge.db import db_get, db_update
    from dataforge.settings import PROJECTS_DIR
    from filelock import FileLock

    await registry.mark_started(job_id)
    try:
        df = await run_in_executor(_load_df, upload_id)
        if df is None:
            raise RuntimeError(f"Dataset for upload_id={upload_id} not found.")

        def _train():
            from dataforge.automl_trainer import run_automl
            return run_automl(df, target_col, task_choice=task_choice,
                              time_budget=time_budget, test_size=test_size)

        result = await run_in_executor(_train)
        if result.get("error"):
            raise RuntimeError(result["error"])

        model_pkl = result.pop("model_pkl", None)
        result["target_col"] = target_col
        save(upload_id, "automl_meta", result)

        if model_pkl:
            d = PROJECTS_DIR / str(upload_id)
            d.mkdir(exist_ok=True)
            lock_path = d / "model_pkl.lock"
            with FileLock(str(lock_path)):
                (d / "model_pkl.joblib").write_bytes(model_pkl)

        try:
            db_update("uploads", upload_id, {
                "automl_meta_json": json.dumps(result, default=str)
            })
        except Exception as exc:
            log.warning("Failed to save automl_meta_json to DB: %s", exc)

        invalidate_upload(upload_id)
        await registry.mark_success(job_id, {"key": "automl_meta"})

        up = db_get("uploads", upload_id)
        await get_ws_manager().send_to_user(user_id, "automl_ready", {
            "upload_id": upload_id,
            "best_estimator": result.get("best_estimator", ""),
            "task": result.get("task", ""),
            "elapsed_s": result.get("elapsed_s", ""),
            "filename": up.get("filename", "") if up else "",
            "ts": _now(),
        })

    except Exception as exc:
        log.exception("AutoML task %s failed: %s", job_id, exc)
        await registry.mark_failed(job_id, str(exc))
        await get_ws_manager().send_to_user(user_id, "task_failed", {
            "job_id": job_id, "type": "automl", "error": str(exc), "ts": _now()
        })


# ══════════════════════════════════════════════════════════════════════════════
# TASK: EDA REPORT
# ══════════════════════════════════════════════════════════════════════════════

async def run_eda_task(
    job_id: str,
    upload_id: int,
    user_id: int,
    minimal: bool = True,
    sample_n: int = 5000,
):
    from dataforge.api.jobs import registry
    from dataforge.api.jobs.executor import run_in_executor
    from dataforge.api.storage.manager import load, save
    from dataforge.api.cache.manager import invalidate_upload
    from dataforge.api.websocket.manager import get_ws_manager
    from dataforge.db import db_get
    from dataforge.settings import PROJECTS_DIR

    await registry.mark_started(job_id)
    try:
        df = await run_in_executor(_load_df, upload_id)
        if df is None:
            raise RuntimeError(f"Dataset for upload_id={upload_id} not found.")

        def _generate():
            from dataforge.eda_report import generate_eda_report
            return generate_eda_report(df, minimal=minimal, sample_n=sample_n)

        report_res = await run_in_executor(_generate)
        if report_res.get("error"):
            raise RuntimeError(report_res["error"])
        html = report_res.get("html")
        if not html:
            raise RuntimeError("EDA report returned empty HTML")

        d = PROJECTS_DIR / str(upload_id)
        d.mkdir(exist_ok=True)
        (d / "eda_html").write_text(html, encoding="utf-8")
        save(upload_id, "eda_html", html)

        invalidate_upload(upload_id)
        await registry.mark_success(job_id, {"key": "eda_html"})

        up = db_get("uploads", upload_id)
        await get_ws_manager().send_to_user(user_id, "eda_ready", {
            "upload_id": upload_id,
            "filename": up.get("filename", "") if up else "",
            "ts": _now(),
        })

    except Exception as exc:
        log.exception("EDA task %s failed: %s", job_id, exc)
        await registry.mark_failed(job_id, str(exc))
        await get_ws_manager().send_to_user(user_id, "task_failed", {
            "job_id": job_id, "type": "eda", "error": str(exc), "ts": _now()
        })


# ══════════════════════════════════════════════════════════════════════════════
# TASK: GENERATE HTML REPORT
# ══════════════════════════════════════════════════════════════════════════════

async def generate_report_task(
    job_id: str,
    upload_id: int,
    user_id: int,
):
    from dataforge.api.jobs import registry
    from dataforge.api.jobs.executor import run_in_executor
    from dataforge.api.storage.manager import load, save
    from dataforge.api.websocket.manager import get_ws_manager
    from dataforge.db import db_get, db_insert

    await registry.mark_started(job_id)
    try:
        df = await run_in_executor(_load_df, upload_id)
        if df is None:
            raise RuntimeError(f"Dataset for upload_id={upload_id} not found.")

        def _build_report():
            from dataforge.insight_engine import detect_schema, run_insights
            from dataforge.report_generator import generate_html_report
            from dataforge.gemini_pipeline import _gemini

            insights = load(upload_id, "last_insights")
            schema   = load(upload_id, "last_schema")
            if not schema:
                schema = detect_schema(df)
            if not insights:
                insights = run_insights(df, schema, top_n=6)

            profile = load(upload_id, "profile") or {}
            up = db_get("uploads", upload_id)
            filename = up.get("filename", "Dataset") if up else "Dataset"

            rows, cols = df.shape
            missing_cells = int(df.isnull().sum().sum())
            total_cells = rows * cols
            miss_pct = round((missing_cells / total_cells * 100), 2) if total_cells > 0 else 0.0
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            cat_cols     = df.select_dtypes(include="object").columns.tolist()

            stats_lines = [
                f"- Dataset Shape: {rows:,} rows x {cols} columns",
                f"- Missing Data: {missing_cells:,} cells ({miss_pct}%)",
                f"- Numeric columns ({len(numeric_cols)}): {', '.join(numeric_cols[:10])}",
                f"- Categorical columns ({len(cat_cols)}): {', '.join(cat_cols[:10])}",
            ]
            insights_text = "\n".join(
                f"- [{i.get('type','').upper()}] {i.get('title')}: {i.get('description')}"
                for i in insights
            )

            gemini_commentary = ""
            try:
                prompt = f"""You are a top-tier McKinsey business analyst.
DATASET: {filename} | TYPE: {schema.get('dataset_type', 'general')}
STATS:
{"".join(stats_lines)}
INSIGHTS:
{insights_text}

Write 4 sections:
---SLIDE_1--- Executive Summary
---SLIDE_2--- Critical Patterns
---SLIDE_3--- Data Health
---SLIDE_4--- Strategic Recommendations"""
                gemini_commentary = _gemini(prompt, temperature=0.7)
            except Exception as api_err:
                log.warning("Gemini commentary failed: %s", api_err)

            def _parse_slide(text, n):
                marker = f"---SLIDE_{n}---"
                if marker in text:
                    parts = text.split(marker, 1)[1]
                    next_marker_pos = parts.find("---SLIDE_")
                    return (parts[:next_marker_pos] if next_marker_pos > -1 else parts).strip()
                return ""

            slides = {i: _parse_slide(gemini_commentary, i) for i in range(1, 5)}
            defaults = {
                1: f"Analysis of '{filename}' shows a {schema.get('dataset_type','general')} dataset with {rows:,} records.",
                2: "Key patterns reveal important drivers across categorical and numeric fields.",
                3: "Data health inspection reveals a stable layout with strong column structures.",
                4: "1. Monitor alert metrics.\n2. Optimize dimension structures.\n3. Implement recurring reporting.",
            }
            for k, v in defaults.items():
                if not slides.get(k) or len(slides[k]) < 10:
                    slides[k] = v

            profile.update({
                "slide1": slides[1], "slide2": slides[2],
                "slide3": slides[3], "slide4": slides[4],
                "rows": rows, "cols": cols, "missing_pct": miss_pct,
                "columns": list(df.columns),
            })

            html = generate_html_report(
                insights=insights, summary_text=slides[1],
                dataset_name=filename,
                dataset_type=schema.get("dataset_type", "general"),
                profile=profile,
            )

            rep = {
                "upload_id": upload_id, "user_id": user_id,
                "report_html": html,
                "report_json": json.dumps({
                    "summary": slides[1],
                    "insights": [{k: v for k, v in i.items() if k != "chart_data"} for i in insights],
                }, default=str),
                "triggered_by": "async",
            }
            try:
                res = db_insert("reports", rep)
                report_id = res.get("id") if res else None
            except Exception as exc:
                log.warning("Failed to insert report to DB: %s", exc)
                report_id = None

            save(upload_id, "report_html", html)
            return html, report_id, filename

        html, report_id, filename = await run_in_executor(_build_report)

        await registry.mark_success(job_id, {"report_id": report_id})

        await get_ws_manager().send_to_user(user_id, "report_ready", {
            "upload_id": upload_id,
            "report_id": report_id,
            "filename": filename,
            "ts": _now(),
        })

    except Exception as exc:
        log.exception("Report task %s failed: %s", job_id, exc)
        await registry.mark_failed(job_id, str(exc))
        await get_ws_manager().send_to_user(user_id, "task_failed", {
            "job_id": job_id, "type": "report", "error": str(exc), "ts": _now()
        })


# ══════════════════════════════════════════════════════════════════════════════
# TASK: CHECK ALERTS
# ══════════════════════════════════════════════════════════════════════════════

async def check_alerts_task(
    job_id: str,
    upload_id: int,
    user_id: int,
):
    from dataforge.api.jobs import registry
    from dataforge.api.jobs.executor import run_in_executor
    from dataforge.api.storage.manager import load
    from dataforge.api.cache.manager import set_alert_status
    from dataforge.api.websocket.manager import get_ws_manager
    from dataforge.db import db_get, db_client

    await registry.mark_started(job_id)
    try:
        df = await run_in_executor(_load_df, upload_id)
        if df is None:
            raise RuntimeError(f"Dataset for upload_id={upload_id} not found.")

        def _check():
            from dataforge.alert_engine import AlertEngine
            from dataforge.insight_engine import detect_schema
            schema = load(upload_id, "last_schema") or detect_schema(df)
            engine = AlertEngine()
            fired_raw = engine.check(upload_id, df, schema)
            return fired_raw

        fired_raw = await run_in_executor(_check)
        fired = list(fired_raw)

        if fired and db_client:
            try:
                insert_data = [{
                    "upload_id": upload_id, "user_id": user_id,
                    "rule": a["rule"], "message": a["message"], "severity": a["severity"],
                    "metric": a.get("metric", ""), "pct_change": a.get("pct_change"),
                } for a in fired]
                db_client.table("alerts").insert(insert_data).execute()
            except Exception as exc:
                log.warning("Alert DB insert failed: %s", exc)

        set_alert_status(upload_id, {"count": len(fired), "alerts": fired})
        await registry.mark_success(job_id, {"fired": len(fired)})

        up = db_get("uploads", upload_id)
        for a in fired:
            await get_ws_manager().send_to_user(user_id, "alert", {
                **a,
                "filename": up.get("filename", "") if up else "",
                "ts": _now(),
            })

    except Exception as exc:
        log.exception("Alerts task %s failed: %s", job_id, exc)
        await registry.mark_failed(job_id, str(exc))


# ── Shared helper ─────────────────────────────────────────────────────────────

def _load_df(upload_id: int):
    """
    Synchronous helper to load the best available DataFrame for an upload.
    Tries df_clean first, then df_raw, then attempts Supabase restore.
    """
    from dataforge.api.storage.manager import load

    for key in ("df_clean", "df_raw"):
        df = load(upload_id, key)
        if df is not None:
            return df

    # Try remote restore
    from dataforge.api.storage.manager import load_persisted
    for key in ("df_clean", "df_raw"):
        df = load_persisted(upload_id, key)
        if df is not None:
            from dataforge.api.storage.manager import save
            save(upload_id, key, df)
            return df

    return None
