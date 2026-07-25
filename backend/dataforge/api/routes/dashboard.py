"""
dataforge/api/routes/dashboard.py
──────────────────────────────────
Dashboard routes: stats, drilldown, reports, alerts, schedules, metrics, sources, assets.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse

from dataforge.api.deps import CurrentUser, get_job_manager_dep, require_upload_with_data
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.jobs.manager import JobManager
from dataforge.api.repositories.report import (
    alert_repo, metric_repo, report_repo, schedule_repo, source_repo,
)
from dataforge.api.schemas.dashboard import (
    AlertsCheckRequest, AssetLabelRequest, DashboardStatsRequest,
    DrilldownRequest, MetricCreateRequest, ReportGenerateRequest,
    ScheduleCreateRequest,
)
from dataforge.api.storage.manager import exists, load, save, upath
from dataforge.api.utils.helpers import format_stat_val, is_id_like_col, time_ago
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import db_client, db_get

log = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


# ── Dashboard stats ───────────────────────────────────────────────────────────

@router.post("/dashboard/stats", summary="Compute dashboard KPIs and charts")
async def api_dashboard_stats(
    body: DashboardStatsRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    def _compute():
        from dataforge.api.storage.manager import load as _load
        from dataforge.web.routes.dashboard import (
            _compute_chart_data, _format_stat_val, _is_id_like_col as is_id_like_col,
        )

        df_clean = _load(target_upload_id, "df_clean")
        df = df_clean if df_clean is not None else _load(target_upload_id, "df_raw")

        # Apply filters
        filters = body.filters or {}
        for col, val in filters.items():
            if col in df.columns:
                try:
                    df = df[df[col] == val]
                except Exception:
                    pass

        dim    = body.chart_dim
        metric = body.chart_metric

        schema  = _load(target_upload_id, "last_schema") or {}
        profile = _load(target_upload_id, "profile") or {}

        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        cat_cols     = df.select_dtypes(include="object").columns.tolist()

        # KPI stats formatting
        stats = []
        stats.append({
            "label": "Total Records",
            "value": f"{len(df):,}",
            "sub": f"{df.shape[1]} Columns",
            "type": "rows",
        })

        dim_col    = dim or (cat_cols[0] if cat_cols else None)
        metric_col = metric or (numeric_cols[0] if numeric_cols else None)

        if metric_col and metric_col in df.columns:
            s = df[metric_col].dropna()
            if len(s) > 0:
                stats.append({
                    "label": f"Total {metric_col}",
                    "value": _format_stat_val(metric_col, float(s.sum())),
                    "sub": f"Avg: {_format_stat_val(metric_col, float(s.mean()))}",
                    "type": "sum",
                })

        if dim_col and dim_col in df.columns:
            s = df[dim_col].dropna()
            if len(s) > 0:
                unique_cnt = s.nunique()
                top_val = str(s.mode().iloc[0]) if not s.mode().empty else "N/A"
                if len(top_val) > 15:
                    top_val = top_val[:12] + "..."
                stats.append({
                    "label": f"Unique {dim_col}",
                    "value": _format_stat_val(None, unique_cnt),
                    "sub": f"Top: {top_val} ({unique_cnt:,} total)",
                    "type": "distinct",
                })

        # Data Completeness Card
        missing = int(df.isnull().sum().sum())
        total_cells = df.shape[0] * df.shape[1]
        missing_pct = (missing / total_cells) * 100 if total_cells > 0 else 0.0
        score = 100.0 - missing_pct

        lbl = "Excellent" if score >= 95 else "Good" if score >= 85 else "Fair" if score >= 70 else "Needs Attention"
        color = "#10b981" if score >= 95 else "#84cc16" if score >= 85 else "#f59e0b" if score >= 70 else "#ef4444"

        stats.append({
            "label": "Data Completeness",
            "value": f"{score:.1f}%",
            "sub": lbl,
            "color": color,
            "type": "completeness",
        })

        # Charts
        charts = []
        if dim_col and metric_col and dim_col in df.columns and metric_col in df.columns:
            grp = df.groupby(dim_col)[metric_col].sum().sort_values(ascending=False).head(15)
            charts.append({
                "id": "bar", "type": "bar",
                "title": f"{metric_col} by {dim_col}",
                "labels": [str(x) for x in grp.index],
                "values": [round(float(v), 2) for v in grp.values],
                "x_col": dim_col, "y_col": metric_col,
            })

        if numeric_cols:
            col = numeric_cols[0]
            s = df[col].dropna()
            if len(s) > 0:
                counts, edges = np.histogram(s, bins=15)
                charts.append({
                    "id": "dist", "type": "histogram",
                    "title": f"Distribution: {col}",
                    "labels": [f"{_format_stat_val(col, edges[i])}" for i in range(len(counts))],
                    "values": [int(c) for c in counts],
                    "x_col": col, "y_col": "count",
                })

        custom_configs = _load(target_upload_id, "custom_charts") or []
        for config in custom_configs:
            computed = _compute_chart_data(df, config)
            if computed:
                charts.append(computed)

        # ID stats
        id_stats = None
        for col in numeric_cols:
            if is_id_like_col(col, df[col]):
                try:
                    id_stats = {
                        "col": col,
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "total": int(df[col].nunique()),
                    }
                    break
                except Exception:
                    pass

        recent_data = []
        if dim_col and metric_col:
            for _, row in df.dropna(subset=[dim_col, metric_col]).tail(5).iterrows():
                try:
                    m_val = float(row[metric_col])
                except (ValueError, TypeError):
                    m_val = str(row[metric_col])
                recent_data.append({dim_col: str(row[dim_col]), metric_col: m_val})

        insights = _load(target_upload_id, "last_insights") or []
        summary  = _load(target_upload_id, "last_summary") or ""
        schema_info = {
            "dataset_type": schema.get("dataset_type", "general"),
            "date_col": schema.get("date"),
            "metrics": schema.get("metrics", [])[:5],
            "dimensions": schema.get("dimensions", [])[:5],
        }

        return {
            "ok": True, "stats": stats, "charts": charts,
            "insights": insights, "summary": summary,
            "schema": schema_info, "profile": profile,
            "id_stats": id_stats, "recent_data": recent_data,
            "dim": dim_col, "metric": metric_col,
            "numeric_cols": numeric_cols, "cat_cols": cat_cols,
        }

    result = await run_in_executor(_compute)
    return JSONResponse(content=safe_jsonable(result))


# ── Drilldown ─────────────────────────────────────────────────────────────────

@router.post("/dashboard/drilldown", summary="Drill into filtered rows for a chart segment")
async def api_drilldown(
    body: DrilldownRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    col_name = body.col_name
    x_label  = body.x_label
    chart_id = body.chart_id

    if col_name not in df.columns:
        raise HTTPException(400, f"Column '{col_name}' not found")

    try:
        if chart_id == "dist" and "-" in str(x_label):
            parts = str(x_label).split("-")
            left, right = float(parts[0]), float(parts[1])
            filtered = df[(df[col_name] > left) & (df[col_name] <= right)]
        else:
            col_dtype = df[col_name].dtype
            val = float(x_label) if pd.api.types.is_numeric_dtype(col_dtype) else x_label
            filtered = df[df[col_name] == val]

        rows = filtered.head(100).to_dict(orient="records")
        return JSONResponse(content=safe_jsonable({
            "ok": True,
            "total_matches": len(filtered),
            "rows": rows,
            "columns": filtered.columns.tolist(),
        }))
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── Reports ───────────────────────────────────────────────────────────────────

@router.post("/reports/generate", summary="Dispatch async HTML report generation")
async def api_report_generate(
    body: ReportGenerateRequest,
    current_user: CurrentUser,
    job_manager: JobManager = Depends(get_job_manager_dep),
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    job_id = await job_manager.dispatch_report(upload_id, current_user.id)
    return {"task_id": job_id, "queued": True}


@router.get("/reports/current", summary="Return the most recent report for an upload")
async def api_report_current(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
    format: str = Query(default="html"),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    html = load(upload_id, "report_html")
    if not html:
        raise HTTPException(404, "No report generated yet")

    if format.lower() == "pdf":
        try:
            from weasyprint import HTML as WP_HTML
            pdf = WP_HTML(string=html).write_pdf()
            return StreamingResponse(
                iter([pdf]), media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=report_{upload_id}.pdf"},
            )
        except Exception:
            pass

    return Response(content=html, media_type="text/html")


@router.get("/reports/{report_id}", summary="View a saved report by ID")
async def api_report_view(
    current_user: CurrentUser,
    report_id: int = Path(...),
    format: str = Query(default="html"),
):
    rep = report_repo.get_by_id(report_id)
    if not rep or rep.get("user_id") != current_user.id:
        raise HTTPException(404, "Report not found")

    html = rep.get("report_html", "")
    if format.lower() == "pdf":
        try:
            from weasyprint import HTML as WP_HTML
            pdf = WP_HTML(string=html).write_pdf()
            return StreamingResponse(
                iter([pdf]), media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=report_{report_id}.pdf"},
            )
        except Exception:
            pass

    return Response(content=html, media_type="text/html")


@router.get("/reports", summary="List saved reports for current user")
async def api_reports_list(current_user: CurrentUser):
    reps = report_repo.list_for_user(current_user.id, limit=50)
    return JSONResponse(content=safe_jsonable([{
        "id": r.get("id"),
        "upload_id": r.get("upload_id"),
        "filename": (r.get("uploads") or {}).get("filename", ""),
        "triggered_by": r.get("triggered_by"),
        "created_at": r.get("created_at"),
    } for r in reps]))


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts", summary="List unresolved alerts for current user")
async def api_alerts_list(current_user: CurrentUser):
    alerts = alert_repo.list_unresolved(current_user.id)
    return JSONResponse(content=safe_jsonable([{
        "id": a.get("id"), "upload_id": a.get("upload_id"),
        "filename": (a.get("uploads") or {}).get("filename", ""),
        "rule": a.get("rule"), "message": a.get("message"),
        "severity": a.get("severity"),
        "colour": a.get("colour", a.get("severity_colour", "#F59E0B")),
        "metric": a.get("metric", ""),
        "pct_change": a.get("pct_change"),
        "triggered_at": a.get("triggered_at"),
    } for a in alerts]))


@router.post("/alerts/check", summary="Dispatch async alert check")
async def api_alerts_check(
    body: AlertsCheckRequest,
    current_user: CurrentUser,
    job_manager: JobManager = Depends(get_job_manager_dep),
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    from dataforge.api.cache.manager import get_alert_status
    cached = get_alert_status(upload_id)
    if cached:
        return JSONResponse(content=safe_jsonable({"ok": True, "from_cache": True, **cached}))

    job_id = await job_manager.dispatch_alerts(upload_id, current_user.id)
    return {"task_id": job_id, "queued": True}


@router.post("/alerts/{alert_id}/resolve", summary="Mark an alert as resolved")
async def api_alert_resolve(
    current_user: CurrentUser,
    alert_id: int = Path(...),
):
    a = alert_repo.get_by_id(alert_id)
    if not a or a.get("user_id") != current_user.id:
        raise HTTPException(404, "Alert not found")
    alert_repo.resolve(alert_id)
    return {"ok": True}


# ── Schedules ─────────────────────────────────────────────────────────────────

@router.get("/schedules", summary="List active report schedules")
async def api_schedules_list(current_user: CurrentUser):
    scheds = schedule_repo.list_for_user(current_user.id)
    return JSONResponse(content=safe_jsonable([{
        "id": s.get("id"), "upload_id": s.get("upload_id"),
        "filename": (db_get("uploads", s["upload_id"]) or {}).get("filename", "") if s.get("upload_id") else "",
        "cron": s.get("cron_expression"), "cron_human": s.get("cron_human", ""),
        "email": s.get("email"), "enabled": s.get("enabled"),
        "last_run": s.get("last_run_at"),
    } for s in scheds]))


@router.post("/schedules", summary="Create a report schedule")
async def api_schedules_create(
    body: ScheduleCreateRequest,
    current_user: CurrentUser,
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    up = db_get("uploads", upload_id)
    if not up or up.get("user_id") != current_user.id:
        raise HTTPException(404, "Upload not found")

    sched = {
        "upload_id": upload_id, "user_id": current_user.id,
        "cron_expression": body.cron, "email": body.email, "enabled": True,
    }
    res = schedule_repo.create(sched)
    if not res:
        raise HTTPException(500, "Failed to create schedule")
    return {"ok": True, "schedule_id": res.get("id")}


@router.delete("/schedules/{schedule_id}", summary="Disable a report schedule")
async def api_schedules_delete(
    current_user: CurrentUser,
    schedule_id: int = Path(...),
):
    s = schedule_repo.get_by_id(schedule_id)
    if not s or s.get("user_id") != current_user.id:
        raise HTTPException(404, "Schedule not found")
    schedule_repo.disable(schedule_id)
    return {"ok": True}


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics", summary="List custom metric definitions")
async def api_metrics_list(current_user: CurrentUser):
    metrics = metric_repo.list_for_user(current_user.id)
    return JSONResponse(content=safe_jsonable(metrics))


@router.post("/metrics", summary="Create or update a metric definition")
async def api_metrics_create(
    body: MetricCreateRequest,
    current_user: CurrentUser,
):
    existing = metric_repo.find_by_name(current_user.id, body.name)
    data = {
        "user_id": current_user.id,
        "name": body.name, "formula": body.formula,
        "description": body.description or "",
        "category": body.category,
    }
    if existing:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = metric_repo.update(existing["id"], data)
    else:
        res = metric_repo.create(data)

    return JSONResponse(content=safe_jsonable({"ok": True, "metric": res}))


@router.delete("/metrics/{metric_id}", summary="Delete a metric definition")
async def api_metrics_delete(
    current_user: CurrentUser,
    metric_id: int = Path(...),
):
    m = metric_repo.get_by_id(metric_id)
    if not m or m.get("user_id") != current_user.id:
        raise HTTPException(404, "Metric not found")
    metric_repo.delete(metric_id)
    return {"ok": True}


@router.get("/metrics/context", summary="Return metrics context string for AI prompts")
async def api_metrics_context(current_user: CurrentUser):
    metrics = metric_repo.list_for_user(current_user.id)
    if not metrics:
        return {"context": ""}
    lines = ["Defined business metrics:"]
    for m in metrics:
        line = f"  {m.get('name')} = {m.get('formula')}"
        if m.get("description"):
            line += f"  # {m.get('description')}"
        lines.append(line)
    return {"context": "\n".join(lines)}


# ── Data sources ──────────────────────────────────────────────────────────────

@router.get("/sources", summary="List enabled data sources")
async def api_sources_list(current_user: CurrentUser):
    sources = source_repo.list_enabled(current_user.id)
    return JSONResponse(content=safe_jsonable([{
        "id": s.get("id"), "name": s.get("name"),
        "source_type": s.get("source_type"), "last_sync": s.get("last_sync"),
    } for s in sources]))


# ── Assets ────────────────────────────────────────────────────────────────────

@router.get("/assets", summary="List all saved assets (datasets, models, EDA reports)")
async def api_assets(current_user: CurrentUser):
    from dataforge.api.repositories.upload import upload_repo
    from dataforge.settings import PROJECTS_DIR

    uploads = upload_repo.list_for_user(current_user.id, limit=200)

    datasets, reports = [], []
    for u in uploads:
        uid = u.get("id")
        d = PROJECTS_DIR / str(uid)

        has_clean = (d / "df_clean.parquet").exists() or exists(uid, "df_clean")
        has_eda   = (d / "eda_html").exists() or exists(uid, "eda_html")

        base = {
            "id": uid,
            "filename": u.get("filename", ""),
            "rows": u.get("rows", 0) or 0,
            "cols": u.get("cols", 0) or 0,
            "source_type": u.get("source_type", "csv") or "csv",
            "time_ago": time_ago(u.get("uploaded_at")),
        }

        if has_clean:
            datasets.append(base)
        if has_eda:
            reports.append({**base, "upload_id": uid})

    analyses = upload_repo.get_analyses(current_user.id, limit=100)
    models = []
    for a in [x for x in analyses if x.get("type") == "automl"]:
        uid = a.get("upload_id")
        d = PROJECTS_DIR / str(uid)
        has_model = (d / "model_pkl.joblib").exists()
        if not has_model:
            continue
        up = a.get("uploads") or {}
        result = a.get("result") or {}
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except Exception:
                result = {}
        models.append({
            "id": a.get("id"), "upload_id": uid,
            "filename": up.get("filename", ""),
            "best_estimator": result.get("best_estimator", ""),
            "task": result.get("task", ""),
            "test_score": result.get("test_score"),
            "time_ago": time_ago(a.get("created_at")),
        })

    return JSONResponse(content=safe_jsonable({
        "datasets": datasets,
        "models": models,
        "eda_reports": reports,
    }))


@router.post("/assets/label", summary="Set a human-readable label for an asset")
async def api_assets_label(
    body: AssetLabelRequest,
    current_user: CurrentUser,
):
    up = db_get("uploads", body.upload_id)
    if not up or up.get("user_id") != current_user.id:
        raise HTTPException(404, "Upload not found")

    from dataforge.settings import PROJECTS_DIR
    d = PROJECTS_DIR / str(body.upload_id)
    d.mkdir(parents=True, exist_ok=True)
    lbl_path = d / "labels.json"

    labels = {}
    if lbl_path.exists():
        try:
            labels = json.loads(lbl_path.read_text("utf-8"))
        except Exception:
            pass

    key_map = {"dataset": "dataset_label", "model": "model_label", "report": "report_label"}
    key = key_map.get(body.asset_type)
    if not key:
        raise HTTPException(400, f"Unknown asset_type: {body.asset_type}")

    labels[key] = body.label
    lbl_path.write_text(json.dumps(labels, ensure_ascii=False), "utf-8")
    return {"ok": True}


# ── Custom chart builder ──────────────────────────────────────────────────────

@router.post("/dashboard/custom-chart", summary="Build/edit a custom dashboard chart")
async def api_dashboard_custom_chart(
    body: dict,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    from dataforge.api.routes.workspace import api_custom_chart
    from dataforge.api.schemas.workspace import CustomChartRequest
    if upload_id and "upload_id" not in body:
        body["upload_id"] = upload_id
    return await api_custom_chart(CustomChartRequest(**body), current_user, upload_id=upload_id)


@router.post("/dashboard/custom-chart/delete", summary="Delete a custom dashboard chart")
async def api_dashboard_custom_chart_delete(
    body: dict,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    from dataforge.api.routes.workspace import api_custom_chart_delete
    from dataforge.api.schemas.workspace import CustomChartDeleteRequest
    if upload_id and "upload_id" not in body:
        body["upload_id"] = upload_id
    return await api_custom_chart_delete(CustomChartDeleteRequest(**body), current_user, upload_id=upload_id)
