"""
dataforge/api/routes/insights.py
──────────────────────────────────
Insights routes: run, list, current, root-cause, forecast.
"""

from __future__ import annotations

import logging

import json
import uuid

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from dataforge.api.deps import CurrentUser, OptionalCurrentUser, get_job_manager_dep, get_upload_id, require_upload_with_data
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.automl import ForecastRequest, InsightsRunRequest, RootCauseRequest
from dataforge.api.storage.manager import load, save
from dataforge.api.cache.manager import invalidate_upload
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
    upload_id: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    job_id = await job_manager.dispatch_insights(
        background_tasks,
        target_upload_id,
        current_user.id,
        top_n=body.top_n,
        target_metric=body.target_metric,
        focus_prompt=body.focus_prompt,
    )
    return {"task_id": job_id, "queued": True, "upload_id": target_upload_id}


@router.get("/insights/list", summary="List saved insight records for an upload")
async def api_insights_list(
    current_user: CurrentUser,
    upload_id: Optional[str] = Query(default=None),
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
    upload_id: Optional[str] = Query(default=None),
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
    upload_id: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
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
    upload_id_q: Optional[str] = Query(default=None, alias="upload_id"),
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


# ── Statistical Hypothesis Testing Engine ─────────────────────────────────────

class HypothesisTestRequest(BaseModel):
    upload_id: str
    test_type: str = Field(..., description="t_test, mann_whitney, anova, chi_square")
    col_a: str = Field(..., description="Primary numeric metric or first categorical")
    col_b: str = Field(..., description="Grouping categorical or second numeric metric")
    alpha: float = 0.05


@router.post("/insights/hypothesis-test", summary="Execute rigorous statistical hypothesis testing")
async def api_hypothesis_test(
    body: HypothesisTestRequest,
    current_user: CurrentUser,
):
    """
    Computes statistical hypothesis tests (Student's/Welch's t-test, Mann-Whitney U,
    One-way ANOVA, Chi-Square contingency) with p-value, effect size, and executive interpretation.
    """
    await require_upload_with_data(body.upload_id, current_user)
    df_clean = load(body.upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(body.upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "Dataset not loaded")

    if body.col_a not in df.columns or body.col_b not in df.columns:
        raise HTTPException(400, f"Columns '{body.col_a}' or '{body.col_b}' not found in dataset")

    import scipy.stats as stats
    import numpy as np
    import pandas as pd

    test_type = body.test_type.lower()
    alpha = body.alpha

    try:
        if test_type in ("t_test", "mann_whitney"):
            # Check if col_b is categorical split or if both are numeric
            is_col_a_num = pd.api.types.is_numeric_dtype(df[body.col_a])
            is_col_b_num = pd.api.types.is_numeric_dtype(df[body.col_b])

            if is_col_a_num and not is_col_b_num:
                # Group col_a by top 2 unique values of col_b
                top_cats = df[body.col_b].dropna().unique()[:2]
                if len(top_cats) < 2:
                    raise HTTPException(400, f"Column '{body.col_b}' must have at least 2 distinct categories")
                g1_name, g2_name = str(top_cats[0]), str(top_cats[1])
                g1 = df[df[body.col_b] == top_cats[0]][body.col_a].dropna().astype(float)
                g2 = df[df[body.col_b] == top_cats[1]][body.col_a].dropna().astype(float)
            elif is_col_a_num and is_col_b_num:
                g1_name, g2_name = body.col_a, body.col_b
                g1 = df[body.col_a].dropna().astype(float)
                g2 = df[body.col_b].dropna().astype(float)
            else:
                raise HTTPException(400, f"At least one column must be numeric for {test_type}")

            if len(g1) < 2 or len(g2) < 2:
                raise HTTPException(400, "Insufficient sample size (minimum 2 rows per group)")

            if test_type == "t_test":
                res = stats.ttest_ind(g1, g2, equal_var=False)
                stat_val = float(res.statistic)
                p_val = float(res.pvalue)
                test_name = "Welch's Two-Sample t-Test (Unequal Variance)"
                
                # Cohen's d effect size
                n1, n2 = len(g1), len(g2)
                s1, s2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
                pooled_se = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / max(1, n1 + n2 - 2))
                cohens_d = float(abs(np.mean(g1) - np.mean(g2)) / pooled_se) if pooled_se > 0 else 0.0
                effect_label = "Large" if cohens_d >= 0.8 else "Medium" if cohens_d >= 0.5 else "Small"
                effect_str = f"Cohen's d = {cohens_d:.3f} ({effect_label})"
            else:
                res = stats.mannwhitneyu(g1, g2, alternative="two-sided")
                stat_val = float(res.statistic)
                p_val = float(res.pvalue)
                test_name = "Mann-Whitney U Test (Non-Parametric)"
                effect_str = f"U = {stat_val:.1f}"

            sig = p_val < alpha
            interp = (
                f"Statistically significant difference detected (p = {p_val:.4e} < {alpha}). "
                f"Group '{g1_name}' (Mean: {np.mean(g1):.2f}) differs significantly from '{g2_name}' (Mean: {np.mean(g2):.2f})."
                if sig else
                f"No statistically significant difference detected (p = {p_val:.4e} >= {alpha}). "
                f"The observed variation between '{g1_name}' and '{g2_name}' is consistent with random sampling noise."
            )

            return JSONResponse(content={
                "ok": True,
                "test_name": test_name,
                "statistic": round(stat_val, 4),
                "p_value": round(p_val, 6),
                "alpha": alpha,
                "is_significant": sig,
                "effect_size": effect_str,
                "groups": {
                    g1_name: {"count": len(g1), "mean": round(float(np.mean(g1)), 2), "median": round(float(np.median(g1)), 2), "std": round(float(np.std(g1)), 2)},
                    g2_name: {"count": len(g2), "mean": round(float(np.mean(g2)), 2), "median": round(float(np.median(g2)), 2), "std": round(float(np.std(g2)), 2)},
                },
                "interpretation": interp,
            })

        elif test_type == "anova":
            cats = df[body.col_b].dropna().unique()[:6]
            if len(cats) < 2:
                raise HTTPException(400, f"Column '{body.col_b}' must have at least 2 distinct categories for ANOVA")
            groups = [df[df[body.col_b] == c][body.col_a].dropna().astype(float) for c in cats]
            groups = [g for g in groups if len(g) >= 2]
            if len(groups) < 2:
                raise HTTPException(400, "Insufficient sample rows per category group")

            res = stats.f_oneway(*groups)
            stat_val = float(res.statistic) if not np.isnan(res.statistic) else 0.0
            p_val = float(res.pvalue) if not np.isnan(res.pvalue) else 1.0
            sig = p_val < alpha

            return JSONResponse(content={
                "ok": True,
                "test_name": "One-Way Analysis of Variance (ANOVA)",
                "statistic": round(stat_val, 4),
                "p_value": round(p_val, 6),
                "alpha": alpha,
                "is_significant": sig,
                "effect_size": f"F-Ratio = {stat_val:.3f}",
                "num_groups": len(groups),
                "interpretation": (
                    f"Statistically significant group variance (F = {stat_val:.2f}, p = {p_val:.4e}). "
                    f"At least one category in '{body.col_b}' exhibits a statistically distinct mean."
                    if sig else
                    f"No significant variance across groups in '{body.col_b}' (p = {p_val:.4e} >= {alpha})."
                )
            })

        elif test_type == "chi_square":
            cont_table = pd.crosstab(df[body.col_a], df[body.col_b])
            res = stats.chi2_contingency(cont_table)
            chi2_val = float(res.statistic)
            p_val = float(res.pvalue)
            dof = int(res.dof)
            sig = p_val < alpha

            # Cramér's V
            n = cont_table.sum().sum()
            phi2 = chi2_val / n if n > 0 else 0
            r, k = cont_table.shape
            v = np.sqrt(phi2 / min(k - 1, r - 1)) if min(k - 1, r - 1) > 0 else 0
            v_label = "Strong" if v >= 0.3 else "Moderate" if v >= 0.15 else "Weak"

            return JSONResponse(content={
                "ok": True,
                "test_name": "Pearson's Chi-Square Test of Independence",
                "statistic": round(chi2_val, 4),
                "p_value": round(p_val, 6),
                "degrees_of_freedom": dof,
                "alpha": alpha,
                "is_significant": sig,
                "effect_size": f"Cramér's V = {v:.3f} ({v_label} Association)",
                "interpretation": (
                    f"Statistically significant categorical dependency (Chi2 = {chi2_val:.2f}, p = {p_val:.4e}). "
                    f"'{body.col_a}' and '{body.col_b}' are not independent."
                    if sig else
                    f"Independence supported (p = {p_val:.4e} >= {alpha}). No significant association detected between '{body.col_a}' and '{body.col_b}'."
                )
            })

        else:
            raise HTTPException(400, f"Unsupported test_type '{test_type}'. Allowed: t_test, mann_whitney, anova, chi_square")

    except HTTPException:
        raise
    except Exception as e:
        log.exception("Hypothesis test failed: %s", e)
        raise HTTPException(500, f"Statistical test error: {str(e)}")


# ── Pin AI Insights to Report & Export Pipeline ───────────────────────────────

class PinInsightRequest(BaseModel):
    upload_id: str = Field(..., description="Target dataset upload ID")
    title: str = Field(..., description="Insight headline or chart title")
    description: str = Field(..., description="Executive interpretation or metric summary")
    type: str = Field("ask_ai", description="Insight classification type")
    importance: float = Field(1.0, description="Priority weight (0.0 - 1.0)")
    chart_data: Optional[dict] = Field(None, description="Structured chart specification for rendering")
    table_data: Optional[dict] = Field(None, description="Tabular data snapshot if applicable")


@router.post("/insights/pin", summary="Pin an AI generated insight, chart, or table to the Executive Report & exports")
async def api_pin_insight(
    body: PinInsightRequest,
    current_user: CurrentUser,
):
    """
    Pins an Ask AI generated chart, table, or analytical finding to `last_insights`.
    The pinned insight immediately becomes available in the Insights tab,
    the Executive HTML/PDF Report, and slide deck export generators.
    """
    await require_upload_with_data(body.upload_id, current_user)

    insights = load(body.upload_id, "last_insights") or []
    if not isinstance(insights, list):
        insights = []

    new_id = f"pin_{uuid.uuid4().hex[:8]}"
    new_insight = {
        "id": new_id,
        "type": body.type,
        "title": body.title,
        "description": body.description,
        "importance": float(body.importance),
        "chart_data": body.chart_data,
        "table_data": body.table_data,
        "pinned": True,
        "source": "Ask AI",
    }

    # Prepend pinned insight so it surfaces at the top of reports and views
    insights.insert(0, new_insight)
    save(body.upload_id, "last_insights", insights)

    if db_client:
        try:
            db_client.table("insight_records").insert([{
                "upload_id": body.upload_id,
                "user_id": current_user.id,
                "type": body.type,
                "title": body.title,
                "description": body.description,
                "importance": float(body.importance),
                "chart_data": json.dumps(body.chart_data) if body.chart_data else None,
            }]).execute()
        except Exception as exc:
            log.warning("Failed to persist pinned insight to DB: %s", exc)

    invalidate_upload(body.upload_id)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "pinned": True,
        "insight": new_insight,
        "count": len(insights),
        "message": "Insight successfully pinned to Insights tab and Executive Report.",
    }))


class ColumnRolesUpdateRequest(BaseModel):
    upload_id: str
    column_roles: dict[str, str]


@router.post("/insights/roles", summary="Save user-corrected semantic column roles")
async def api_save_column_roles(
    body: ColumnRolesUpdateRequest,
    current_user: CurrentUser,
):
    await require_upload_with_data(body.upload_id, current_user)
    save(body.upload_id, "user_column_roles", body.column_roles)
    return {"ok": True, "updated_count": len(body.column_roles), "column_roles": body.column_roles}


