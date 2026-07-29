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
from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks
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
from dataforge.api.utils.helpers import format_stat_val, is_id_like_col, resolve_column, time_ago
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import db_client, db_get

log = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


# ── Dashboard initialization ────────────────────────────────────────────────
@router.get("/dashboard/init", summary="Get initialization data for the dashboard")
async def api_dashboard_init(current_user: CurrentUser):
    from dataforge.db import db_client, db_all, db_count
    
    user = current_user
    recent_uploads = db_all("uploads", {"user_id": user.id}, order_by="uploaded_at", limit=10)

    def _time_ago_local(dt_str):
        if not dt_str: return ""
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            diff = datetime.now(dt.tzinfo) - dt if dt.tzinfo else datetime.utcnow() - dt
        except Exception:
            return ""
        s = int(diff.total_seconds())
        if s < 60:       return "just now"
        if s < 3600:     return f"{s//60}m ago"
        if s < 86400:    return f"{s//3600}h ago"
        return f"{s//86400}d ago"

    uploads_data = [{
        "filename":    u.get("filename", ""),
        "rows":        u.get("rows", 0) or 0,
        "cols":        u.get("cols", 0) or 0,
        "missing_pct": u.get("missing_pct", 0) or 0,
        "time_ago":    _time_ago_local(u.get("uploaded_at")),
        "id":          u.get("id"),
        "source_type": u.get("source_type", "csv") or "csv",
    } for u in recent_uploads]

    _icon_map = {"eda": "📊", "automl": "🤖", "clean": "🧹", "query": "💬", "insights": "💡", "report": "📄"}
    _map_labels = {
        "eda":      "EDA Report",
        "automl":   "AutoML Training",
        "clean":    "Data Cleaning",
        "query":    "AI Query",
        "insights": "Insights",
        "report":   "Report Generated",
    }

    analyses_res = db_client.table("analyses").select("*, uploads(filename)").eq("user_id", user.id).order("created_at", desc=True).limit(30).execute()
    recent_analyses = analyses_res.data if analyses_res and analyses_res.data else []
    analyses_data = []
    for a in recent_analyses:
        type_ = a.get("type", "")
        up = a.get("uploads") or {}
        analyses_data.append({
            "type":     type_,
            "label":    _map_labels.get(type_, type_.title()),
            "icon":     _icon_map.get(type_, "⚡"),
            "summary":  a.get("summary") or "",
            "filename": up.get("filename", ""),
            "time_ago": _time_ago_local(a.get("created_at")),
        })

    alert_count = db_count("alerts", {"user_id": user.id, "resolved": False})

    reports_res = db_client.table("reports").select("*, uploads(filename)").eq("user_id", user.id).order("created_at", desc=True).limit(5).execute()
    recent_reports = reports_res.data if reports_res and reports_res.data else []
    reports_data = []
    for r in recent_reports:
        up = r.get("uploads") or {}
        reports_data.append({
            "id":           r.get("id"),
            "filename":     up.get("filename", "Dataset"),
            "time_ago":     _time_ago_local(r.get("created_at")),
            "triggered_by": r.get("triggered_by", "auto"),
        })

    schedule_count = db_count("schedules", {"user_id": user.id})

    member_since = ""
    try:
        created = user.created_at
        if created:
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            member_since = dt.strftime("%B %Y")
    except Exception:
        pass

    return {
        "user": {
            "name": user.name,
            "email": user.email,
            "avatar": user.avatar,
        },
        "recent_uploads": uploads_data,
        "recent_analyses": analyses_data,
        "alert_count": alert_count,
        "recent_reports": reports_data,
        "schedule_count": schedule_count,
        "member_since": member_since,
    }


# ── Local chart helper (self-contained, no Flask dependency) ─────────────────

def _compute_chart_data(df, config):
    """Compute chart data for a custom chart config dict."""
    chart_id   = config.get("id")
    chart_type = config.get("chart_type") or config.get("type")
    raw_x      = config.get("x_col")
    raw_y      = config.get("y_col")
    agg_type   = config.get("agg_type", "none")

    x_col = resolve_column(raw_x, df.columns)
    if not x_col:
        return None

    y_col = resolve_column(raw_y, df.columns) if raw_y else None
    title = config.get("title") or f"{(chart_type or 'Chart').title()} of {x_col}"

    labels           = []
    values           = []
    formatted_values = None

    if chart_type == "scatter":
        if not y_col:
            return None
        sub_df = df[[x_col, y_col]].dropna()
        if sub_df.empty:
            return None
        sub_df[x_col] = pd.to_numeric(sub_df[x_col], errors="coerce")
        sub_df[y_col] = pd.to_numeric(sub_df[y_col], errors="coerce")
        sub_df = sub_df.dropna()
        if sub_df.empty:
            return None
        if len(sub_df) > 500:
            sub_df = sub_df.sample(n=500, random_state=42)
        sub_df = sub_df.sort_values(by=x_col)
        values = [{"x": float(r[x_col]), "y": float(r[y_col])} for _, r in sub_df.iterrows()]
        labels = []

    elif chart_type == "histogram":
        s = pd.to_numeric(df[x_col], errors="coerce").dropna()
        if len(s) > 0:
            counts, edges = np.histogram(s, bins=15)
            for i in range(len(counts)):
                labels.append(f"{format_stat_val(x_col, edges[i])} - {format_stat_val(x_col, edges[i+1])}")
            values = [int(c) for c in counts]

    elif chart_type == "boxplot":
        s = pd.to_numeric(df[x_col], errors="coerce").dropna()
        if len(s) > 0:
            desc           = s.describe()
            q1             = float(desc["25%"])
            median         = float(desc["50%"])
            q3             = float(desc["75%"])
            iqr            = q3 - q1
            lower_whisker  = float(s[s >= q1 - 1.5 * iqr].min()) if not s[s >= q1 - 1.5 * iqr].empty else float(desc["min"])
            upper_whisker  = float(s[s <= q3 + 1.5 * iqr].max()) if not s[s <= q3 + 1.5 * iqr].empty else float(desc["max"])
            values         = {"min": lower_whisker, "q1": q1, "median": median, "q3": q3, "max": upper_whisker}
            formatted_values = {
                "min":    format_stat_val(x_col, lower_whisker),
                "q1":     format_stat_val(x_col, q1),
                "median": format_stat_val(x_col, median),
                "q3":     format_stat_val(x_col, q3),
                "max":    format_stat_val(x_col, upper_whisker),
            }

    else:  # bar / line / area / pie / doughnut
        if agg_type == "none":
            sub_df = df.dropna(subset=[x_col])
            if y_col:
                sub_df = sub_df.dropna(subset=[y_col])
            if len(sub_df) > 500:
                sub_df = sub_df.head(500)
            labels = [str(v) for v in sub_df[x_col]]
            if y_col:
                y_nums = pd.to_numeric(sub_df[y_col], errors="coerce").fillna(0.0)
                values = [float(v) for v in y_nums]
            else:
                values = [1.0] * len(sub_df)
        else:
            if not y_col or agg_type == "count":
                grp = df.groupby(x_col).size()
            else:
                num_y = pd.to_numeric(df[y_col], errors="coerce")
                temp_df = pd.DataFrame({x_col: df[x_col], "_y": num_y}).dropna(subset=["_y"])
                if agg_type == "sum":
                    grp = temp_df.groupby(x_col)["_y"].sum()
                elif agg_type == "mean":
                    grp = temp_df.groupby(x_col)["_y"].mean()
                else:
                    grp = temp_df.groupby(x_col)["_y"].count()

            top_n = config.get("top_n", 10)
            if chart_type in ("pie", "doughnut") and len(grp) > top_n:
                grp_sorted  = grp.sort_values(ascending=False)
                top_slices  = grp_sorted.iloc[:top_n]
                other_val   = grp_sorted.iloc[top_n:].sum() if agg_type in ("sum", "count") else grp_sorted.iloc[top_n:].mean()
                labels      = [str(x) for x in top_slices.index] + ["Other"]
                values      = [round(float(v), 2) for v in top_slices.values] + [round(float(other_val), 2)]
            else:
                grp    = grp.sort_values(ascending=False).head(500)
                labels = [str(x) for x in grp.index]
                values = [round(float(v), 2) for v in grp.values]

    return {
        "id":               chart_id,
        "type":             chart_type,
        "x_col":            x_col,
        "y_col":            y_col,
        "agg_type":         agg_type,
        "title":            title,
        "labels":           labels,
        "values":           values,
        "formatted_values": formatted_values,
        "is_custom":        True,
        "is_area":          config.get("is_area", False),
    }


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
                    "value": format_stat_val(metric_col, float(s.sum())),
                    "sub": f"Avg: {format_stat_val(metric_col, float(s.mean()))}",
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
                    "value": format_stat_val(None, unique_cnt),
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
                    "labels": [f"{format_stat_val(col, edges[i])}" for i in range(len(counts))],
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
    background_tasks: BackgroundTasks,
    job_manager: JobManager = Depends(get_job_manager_dep),
):
    upload_id = body.upload_id
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    job_id = await job_manager.dispatch_report(background_tasks, upload_id, current_user.id)
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
    background_tasks: BackgroundTasks,
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

    job_id = await job_manager.dispatch_alerts(background_tasks, upload_id, current_user.id)
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
    from pydantic import ValidationError
    if upload_id and "upload_id" not in body:
        body["upload_id"] = upload_id
    try:
        req = CustomChartRequest(**body)
    except ValidationError as e:
        print(f"DEBUG: 400 - CustomChartRequest Validation Error: {e}")
        raise HTTPException(400, str(e))
    return await api_custom_chart(req, current_user, upload_id=upload_id)


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
