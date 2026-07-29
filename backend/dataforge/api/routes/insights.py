"""
dataforge/api/routes/insights.py
──────────────────────────────────
Insights routes: run, list, current, root-cause, forecast.
"""

from __future__ import annotations

import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from dataforge.api.deps import CurrentUser, get_job_manager_dep, get_upload_id, require_upload_with_data
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.automl import ForecastRequest, InsightsRunRequest, RootCauseRequest
from dataforge.api.storage.manager import load
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import db_all, db_client

log = logging.getLogger(__name__)
router = APIRouter(tags=["insights"])


@router.post("/insights/run", summary="Start an async insights analysis job")
async def api_insights_run(
    body: InsightsRunRequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    job_manager: JobManager = Depends(get_job_manager_dep),
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    job_id = await job_manager.dispatch_insights(background_tasks, target_upload_id, current_user.id, top_n=body.top_n)
    return {"task_id": job_id, "queued": True, "upload_id": target_upload_id}


@router.get("/insights/list", summary="List saved insight records for an upload")
async def api_insights_list(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    if upload_id is None:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    if db_client:
        try:
            res = (db_client.table("insight_records")
                   .select("*")
                   .eq("upload_id", upload_id)
                   .order("importance", desc=True)
                   .limit(20)
                   .execute())
            data = res.data if res and res.data else []
            return JSONResponse(content=safe_jsonable(data))
        except Exception as exc:
            log.warning("insight_records DB query failed: %s", exc)

    # Fallback to disk
    insights = load(upload_id, "last_insights") or []
    return JSONResponse(content=safe_jsonable(insights))


@router.get("/insights/current", summary="Return the latest cached insight results")
async def api_insights_current(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    if upload_id is None:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    insights = load(upload_id, "last_insights") or []
    summary  = load(upload_id, "last_summary") or ""
    schema   = load(upload_id, "last_schema") or {}
    return JSONResponse(content=safe_jsonable({
        "insights": insights,
        "summary": summary,
        "schema": schema,
        "count": len(insights),
    }))


@router.post("/insights/root-cause", summary="Run root-cause analysis on a metric")
async def api_root_cause(
    body: RootCauseRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    try:
        from dataforge.insight_engine import run_root_cause
        result = run_root_cause(
            df,
            metric=body.metric,
            dimensions=body.dimensions,
            date_col=body.date_col,
            top_n=body.top_n,
        )
        return JSONResponse(content=safe_jsonable(result))
    except Exception as exc:
        log.exception("Root cause analysis failed: %s", exc)
        raise HTTPException(500, f"Root cause analysis failed: {exc}")


@router.post("/insights/forecast", summary="Run advanced time-series forecasting on a metric")
async def api_forecast(
    body: ForecastRequest,
    current_user: CurrentUser,
    upload_id_q: Optional[int] = Query(default=None, alias="upload_id"),
):
    """
    Run the full forecasting pipeline (Holt-Winters, ARIMA, Ridge-Lag ensemble)
    and return predictions, 80%/95% confidence intervals, seasonal decomposition,
    and summary growth metrics.

    If `date_col` or `metric_col` are omitted, they are auto-detected from the
    dataset schema.
    """
    target_upload_id = body.upload_id or upload_id_q
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    try:
        # Auto-detect date / metric columns when not provided
        date_col   = body.date_col
        metric_col = body.metric_col

        if not date_col or not metric_col:
            from dataforge.insight_engine import InsightEngine
            schema = InsightEngine().detect_schema(df)
            if not date_col:
                date_col = schema.get("date")
            if not metric_col and schema.get("metrics"):
                metric_col = schema["metrics"][0]

        if not date_col:
            raise HTTPException(400, "Could not auto-detect a date column. Please supply date_col.")
        if not metric_col:
            raise HTTPException(400, "Could not auto-detect a metric column. Please supply metric_col.")

        if date_col not in df.columns:
            raise HTTPException(400, f"date_col '{date_col}' not found in dataset")
        if metric_col not in df.columns:
            raise HTTPException(400, f"metric_col '{metric_col}' not found in dataset")

        from dataforge.api.jobs.executor import run_in_executor
        from dataforge.forecast_engine import run_forecast

        result = await run_in_executor(
            lambda: run_forecast(
                df,
                date_col=date_col,
                metric_col=metric_col,
                horizon=body.horizon,
                freq_override=body.freq_override,
                include_decomposition=body.include_decomposition,
            )
        )

        if "error" in result:
            raise HTTPException(422, result["error"])

        return JSONResponse(content=safe_jsonable(result))

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Forecast failed: %s", exc)
        raise HTTPException(500, f"Forecast failed: {exc}")
