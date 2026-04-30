"""
routes/dashboard.py — Dashboard Blueprint
Handles dashboard page, stats, reports, alerts, schedules, metrics, and sources.
"""
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    from dataforge.db import db_client, db_all, db_count, db_get
    from dataforge.db import ReportSchedule

    user = current_user

    recent_uploads = db_all("uploads", {"user_id": user.id}, order_by="uploaded_at", limit=10)

    def _time_ago_local(dt_str):
        if not dt_str:
            return ""
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

    _icon_map = {"eda": "📊", "automl": "🤖", "clean": "🧹", "query": "💬",
                 "insights": "💡", "report": "📄"}
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
            "id": r.get("id"),
            "filename": up.get("filename", ""),
            "triggered_by": r.get("triggered_by", ""),
            "time_ago": _time_ago_local(r.get("created_at")),
        })

    schedule_count = db_count("report_schedules", {"user_id": user.id, "enabled": True})

    class Stats:
        uploads  = db_count("uploads", {"user_id": user.id})
        analyses = db_count("analyses", {"user_id": user.id})
        models   = db_count("analyses", {"user_id": user.id, "type": "automl"})
        queries  = db_count("analyses", {"user_id": user.id, "type": "query"})

    def _format_member_since(val) -> str:
        if not val:
            return "—"
        try:
            if hasattr(val, "strftime"):
                return val.strftime("%B %Y")
        except Exception:
            pass
        try:
            dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            return dt.strftime("%B %Y")
        except Exception:
            return "—"

    member_since = _format_member_since(getattr(user, "created_at", None))

    return render_template(
        "dashboard.html",
        user            = user,
        stats           = Stats(),
        recent_uploads  = uploads_data,
        recent_analyses = analyses_data,
        alert_count     = alert_count,
        recent_reports  = reports_data,
        schedule_count  = schedule_count,
        member_since   = member_since,
    )


@dashboard_bp.route("/api/dashboard/stats", methods=["GET", "POST"])
@login_required
def api_dashboard_stats():
    import numpy as np
    import pandas as pd
    from ..storage import _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _exists,
                           _df_to_json_rows)

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")
    profile = _load(upload_id, "profile") or {}

    filters = {}
    chart_dim = None
    chart_metric = None
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        filters = payload.get("filters", {})
        chart_dim = payload.get("chart_dim")
        chart_metric = payload.get("chart_metric")

    if filters:
        for fk, fv in filters.items():
            if fk in df.columns:
                if isinstance(fv, list):
                    df = df[df[fk].isin(fv)]
                else:
                    df = df[df[fk] == fv]

    stats = []
    charts = []

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "string", "bool"]).columns.tolist()
    date_like_cols = [
        c for c in df.columns
        if "date" in c.lower() or "time" in c.lower() or "created" in c.lower() or "posted" in c.lower()
    ]

    # Identify valid dimensions and metrics
    # Exclude ID columns from metrics if possible
    valid_metrics = [c for c in numeric_cols if not c.lower().endswith("id") and c.lower() != "id"]
    if not valid_metrics and numeric_cols:
        valid_metrics = numeric_cols

    metric = chart_metric if chart_metric in df.columns else (valid_metrics[0] if valid_metrics else None)
    
    valid_dims = cat_cols + [c for c in numeric_cols if c.lower().endswith("id") or c.lower() == "id"]
    dim = chart_dim if chart_dim in df.columns else (valid_dims[0] if valid_dims else (cat_cols[0] if cat_cols else None))

    # 1. Total Rows Indicator
    stats.append({
        "label": "Total Rows",
        "value": f"{len(df):,}",
        "sub": f"{df.shape[1]} total columns",
        "type": "count"
    })
    
    # 2. Dynamic Metric Stat
    if metric:
        s = df[metric].dropna()
        if len(s) > 0:
            total_val = s.sum()
            mean_val = s.mean()
            formatted_val = round(float(total_val), 2) if abs(total_val) < 1e6 else f"{total_val/1e6:.2f}M"
            stats.append({
                "label": f"{metric} (Total)",
                "value": formatted_val,
                "sub": f"Avg: {round(float(mean_val), 2)}",
                "type": "sum"
            })
            
    # 3. Dynamic Dimension Stat
    if dim:
        s = df[dim].dropna()
        if len(s) > 0:
            unique_cnt = s.nunique()
            top_val = str(s.mode().iloc[0]) if not s.mode().empty else "N/A"
            # truncate top_val if too long
            if len(top_val) > 15: top_val = top_val[:12] + "..."
            stats.append({
                "label": f"Unique {dim}",
                "value": f"{unique_cnt:,}",
                "sub": f"Top: {top_val}",
                "type": "distinct"
            })

    # 4. Additional numeric column or Missing Values
    other_metrics = [c for c in valid_metrics if c != metric]
    if other_metrics:
        col = other_metrics[0]
        s = df[col].dropna()
        if len(s) > 0:
            stats.append({
                "label": f"Avg {col}",
                "value": round(float(s.mean()), 2),
                "sub": f"Max/Min: {round(float(s.max()), 2)} / {round(float(s.min()), 2)}",
                "type": "mean"
            })
    
    # Fill up to 4 if we didn't reach 4
    if len(stats) < 4:
        missing = int(df.isnull().sum().sum())
        missing_pct = (missing / (df.shape[0] * df.shape[1])) * 100 if df.shape[0]*df.shape[1] > 0 else 0
        stats.append({
            "label": "Missing Values",
            "value": f"{missing:,}",
            "sub": f"{missing_pct:.1f}% of dataset",
            "type": "missing"
        })

    schema = _load(upload_id, "last_schema")
    date_col_for_chart = (schema or {}).get("date") or (date_like_cols[0] if date_like_cols else None)
    if date_col_for_chart and (valid_metrics or True):
        try:
            date_col = date_col_for_chart
            ts_metric = valid_metrics[0] if valid_metrics else None
            cols = [date_col] + ([ts_metric] if ts_metric else [])
            ts = df[cols].copy()
            ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
            ts = ts.dropna().sort_values(date_col)
            if len(ts) > 0:
                if ts_metric:
                    agg = ts.groupby(ts[date_col].dt.to_period("M"))[ts_metric].sum()
                    title = f"{ts_metric} over time"
                    y_label = ts_metric
                else:
                    agg = ts.groupby(ts[date_col].dt.to_period("M")).size()
                    title = f"Records over time"
                    y_label = "records"
                charts.append({
                    "id": "trend", "type": "line",
                    "title": title,
                    "labels": [str(p) for p in agg.index[-24:]],
                    "values": [round(float(v), 2) for v in agg.values[-24:]],
                    "x_label": date_col, "y_label": y_label,
                })
        except Exception:
            pass

    if dim and metric:
        try:
            # Bar Chart: Top dimension by metric
            grp = df.groupby(dim)[metric].mean().sort_values(ascending=False).head(10)
            charts.append({
                "id": "top_cat", "type": "bar",
                "title": f"Top {dim} by {metric}",
                "labels": [str(i) for i in grp.index],
                "values": [round(float(v), 2) for v in grp.values],
                "x_label": dim, "y_label": metric,
            })
        except Exception:
            pass
    elif dim:
        try:
            grp = df[dim].dropna().astype(str).value_counts().head(10)
            charts.append({
                "id": "top_cat", "type": "bar",
                "title": f"Top {dim} by record count",
                "labels": [str(i)[:40] for i in grp.index],
                "values": [int(v) for v in grp.values],
                "x_label": dim, "y_label": "records",
            })
        except Exception:
            pass

    if metric:
        try:
            # Fix Pie chart binning
            col = metric
            s = df[col].dropna()
            # bin into 4 ranges for the pie chart
            if len(s) > 0:
                buckets = pd.cut(s, bins=4, precision=1)
                vc = buckets.value_counts(sort=False)
                # Convert categorical intervals to strings
                labels = [f"{b.left}-{b.right}" for b in vc.index]
                values = [int(v) for v in vc.values]
                charts.append({
                    "id": "dist", "type": "pie",
                    "title": f"{col} Distribution",
                    "labels": labels,
                    "values": values,
                    "x_label": col, "y_label": "count",
                })
        except Exception:
            pass
    elif cat_cols:
        try:
            col = dim or cat_cols[0]
            vc = df[col].dropna().astype(str).value_counts().head(6)
            charts.append({
                "id": "dist", "type": "pie",
                "title": f"{col} Distribution",
                "labels": [str(i)[:30] for i in vc.index],
                "values": [int(v) for v in vc.values],
                "x_label": col, "y_label": "records",
            })
        except Exception:
            pass

    if not charts and df.shape[1] > 0:
        try:
            missing_by_col = df.isnull().sum().sort_values(ascending=False)
            missing_by_col = missing_by_col[missing_by_col > 0].head(10)
            if len(missing_by_col) > 0:
                charts.append({
                    "id": "missing_cols", "type": "bar",
                    "title": "Missing Values by Column",
                    "labels": [str(i)[:35] for i in missing_by_col.index],
                    "values": [int(v) for v in missing_by_col.values],
                    "x_label": "column", "y_label": "missing values",
                })
        except Exception:
            pass

    # Extras for Dashboard table views
    try:
        # ID statistics
        id_col_candidates = [c for c in numeric_cols if "id" in c.lower()]
        id_col = id_col_candidates[0] if id_col_candidates else None
        id_stats = None
        if id_col:
            id_stats = {
                "total": int(df[id_col].nunique()),
                "min": float(df[id_col].min()),
                "max": float(df[id_col].max()),
                "col": id_col
            }
        
        # Recent data entries (last 5 rows, dynamic dimension + metric)
        raw_list = []
        if dim and metric:
            for _, row in df.dropna(subset=[dim, metric]).tail(5).iterrows():
                raw_list.append({dim: str(row[dim]), metric: float(row[metric])})
        elif dim:
            for _, row in df.dropna(subset=[dim]).tail(5).iterrows():
                raw_list.append({dim: str(row[dim]), "records": 1})
            if raw_list:
                metric = "records"
    except Exception:
        id_stats = None
        raw_list = []

    insights = _load(upload_id, "last_insights") or []
    summary  = _load(upload_id, "last_summary") or ""
    schema_info = {}
    if schema:
        schema_info = {
            "dataset_type": schema.get("dataset_type", "general"),
            "date_col":     schema.get("date"),
            "metrics":      schema.get("metrics", [])[:5],
            "dimensions":   schema.get("dimensions", [])[:5],
        }

    return jsonify({
        "ok": True, "stats": stats, "charts": charts,
        "insights": insights[:6], "summary": summary,
        "schema": schema_info, "profile": profile,
        "id_stats": id_stats, "recent_data": raw_list,
        "dim": dim, "metric": metric,
        "numeric_cols": numeric_cols, "cat_cols": cat_cols
    })


@dashboard_bp.route("/api/dashboard/drilldown", methods=["POST"])
@login_required
def api_dashboard_drilldown():
    import pandas as pd
    from ..storage import _load
    from ..helpers import _get_upload_id, _get_upload_or_403, _exists

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")

    payload = request.get_json(silent=True) or {}
    chart_id = payload.get("chart_id")
    x_label = payload.get("x_label")
    col_name = payload.get("col_name")

    if not col_name or x_label is None:
        return jsonify({"error": "Missing parameters"}), 400

    filtered_df = df
    try:
        if chart_id == "dist": # pie chart range drill-down
            # x_label is "left-right", we need to parse it
            if "-" in x_label:
                parts = x_label.split("-")
                if len(parts) >= 2:
                    left = float(parts[0])
                    right = float(parts[1])
                    filtered_df = df[(df[col_name] > left) & (df[col_name] <= right)]
        else:
            # direct exact match
            # convert x_label back to correct dtype
            col_dtype = df[col_name].dtype
            val = x_label
            if pd.api.types.is_numeric_dtype(col_dtype):
                val = float(x_label)
            filtered_df = df[df[col_name] == val]

        raw_rows = filtered_df.head(100).to_dict(orient="records")
        return jsonify({
            "ok": True,
            "total_matches": len(filtered_df),
            "rows": raw_rows,
            "columns": filtered_df.columns.tolist()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Reports ──────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/reports/generate", methods=["POST"])
@login_required
def api_report_generate():
    from flask import current_app
    from ..helpers import (_get_upload_id, _get_upload_or_403, _exists,
                           _tasks, _db_log_analysis, REPORTING_ENABLED)
    from dataforge.db import db_first, db_insert

    if not REPORTING_ENABLED:
        return jsonify({"error": "Reporting engine not installed"}), 503

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    existing = db_first("jobs", {"upload_id": upload_id, "type": "report", "status": "started"})
    if existing:
        return jsonify({"task_id": existing.get("id"), "queued": False}), 200

    try:
        (_, _, _, task_generate_report, _) = _tasks()
        job = task_generate_report.apply_async(args=[upload_id, current_user.id])
        db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "report"})
        _db_log_analysis("report", "queued async")
        return jsonify({"task_id": job.id, "queued": True}), 202
    except Exception as e:
        current_app.logger.error("Celery task dispatch failed: %s", e)
        return jsonify({"error": "Background task system unavailable."}), 503


@dashboard_bp.route("/api/reports/<int:report_id>")
@login_required
def api_report_view(report_id):
    from dataforge.db import db_get
    rep = db_get("reports", report_id)
    if not rep or rep.get("user_id") != current_user.id:
        return Response("Not found", status=404)
    return Response(rep.get("report_html", ""), mimetype="text/html")


@dashboard_bp.route("/api/reports/current")
@login_required
def api_report_current():
    from ..storage import _load
    from ..helpers import _get_upload_id

    upload_id = _get_upload_id()
    if not upload_id:
        return Response("upload_id required", status=400)
    html = _load(upload_id, "report_html")
    if not html:
        return Response("No report yet.", status=404)
    return Response(html, mimetype="text/html")


@dashboard_bp.route("/api/reports")
@login_required
def api_reports_list():
    from dataforge.db import db_client
    res = db_client.table("reports").select("*, uploads(filename)").eq("user_id", current_user.id).order("created_at", desc=True).limit(50).execute()
    reps = res.data if res and res.data else []

    out = []
    for r in reps:
        up = r.get("uploads") or {}
        fname = up.get("filename") or r.get("filename") or ""
        out.append({
            "id": r.get("id"), "upload_id": r.get("upload_id"),
            "filename": fname,
            "triggered_by": r.get("triggered_by"),
            "created_at": r.get("created_at"),
        })
    return jsonify(out)


# ── Alerts ───────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/alerts")
@login_required
def api_alerts_list():
    from dataforge.db import db_client
    res = db_client.table("alerts").select("*, uploads(filename)").eq("user_id", current_user.id).eq("resolved", False).order("triggered_at", desc=True).limit(100).execute()
    alerts = res.data if res and res.data else []

    out = []
    for a in alerts:
        up = a.get("uploads") or {}
        fname = up.get("filename") or a.get("filename") or ""
        out.append({
            "id": a.get("id"), "upload_id": a.get("upload_id"),
            "filename": fname,
            "rule": a.get("rule"), "message": a.get("message"), "severity": a.get("severity"),
            "colour": a.get("colour", a.get("severity_colour", "#F59E0B")),
            "metric": a.get("metric", ""),
            "pct_change": a.get("pct_change", None),
            "triggered_at": a.get("triggered_at"),
        })
    return jsonify(out)


@dashboard_bp.route("/api/alerts/check", methods=["POST"])
@login_required
def api_alerts_check():
    from flask import current_app
    from ..helpers import (_get_upload_id, _get_upload_or_403, _exists,
                           _tasks, get_alert_status, REPORTING_ENABLED)
    from dataforge.db import db_first, db_insert

    if not REPORTING_ENABLED:
        return jsonify({"ok": True, "alerts": []})

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded."}), 400

    cached = get_alert_status(upload_id)
    if cached:
        return jsonify({"ok": True, "from_cache": True, **cached})

    existing = db_first("jobs", {"upload_id": upload_id, "type": "alerts", "status": "started"})
    if existing:
        return jsonify({"task_id": existing.get("id"), "queued": False}), 200

    try:
        (_, _, _, _, task_check_alerts) = _tasks()
        job = task_check_alerts.apply_async(args=[upload_id, current_user.id])
        db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "alerts"})
        return jsonify({"task_id": job.id, "queued": True}), 202
    except Exception as e:
        current_app.logger.error("Celery task dispatch failed: %s", e)
        return jsonify({"error": "Background task system unavailable."}), 503


@dashboard_bp.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def api_alert_resolve(alert_id):
    from dataforge.db import db_get, db_update
    a = db_get("alerts", alert_id)
    if not a or a.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404
    db_update("alerts", alert_id, {
        "resolved": True,
        "resolved_at": datetime.utcnow().isoformat()
    })
    return jsonify({"ok": True})


# ── Schedules ────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/schedules", methods=["GET"])
@login_required
def api_schedules_list():
    from dataforge.db import db_all, db_get
    scheds = db_all("report_schedules", {"user_id": current_user.id, "enabled": True},
                    order_by="created_at", limit=50)
    return jsonify([{
        "id": s.get("id"), "upload_id": s.get("upload_id"),
        "filename": (db_get("uploads", s["upload_id"]) or {}).get("filename", "") if s.get("upload_id") else "",
        "cron": s.get("cron_expression"), "cron_human": s.get("cron_human", ""),
        "email": s.get("email"), "enabled": s.get("enabled"),
        "last_run": s.get("last_run_at"),
    } for s in scheds])


@dashboard_bp.route("/api/schedules", methods=["POST"])
@login_required
def api_schedules_create():
    from ..helpers import _get_upload_id
    from dataforge.db import db_get, db_insert, ReportSchedule

    body = request.get_json(force=True) or {}
    upload_id = _get_upload_id()
    cron = body.get("cron", "0 9 * * 1")
    email = (body.get("email") or "").strip()
    if not upload_id:
        return jsonify({"error": "upload_id required — upload a dataset first"}), 400
    upload = db_get("uploads", upload_id)
    if not upload or upload.get("user_id") != current_user.id:
        return jsonify({"error": "Upload not found"}), 404

    sched = {
        "upload_id": upload_id, "user_id": current_user.id,
        "cron_expression": cron, "email": email, "enabled": True
    }
    try:
        res = db_insert("report_schedules", sched)
        return jsonify({"ok": True, "schedule_id": res.get("id"),
                        "cron_human": ReportSchedule(**res).cron_human_text if res else ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
@login_required
def api_schedules_delete(schedule_id):
    from dataforge.db import db_get, db_update
    sched = db_get("report_schedules", schedule_id)
    if not sched or sched.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404
    try:
        db_update("report_schedules", schedule_id, {"enabled": False})
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"error": "Failed to delete"}), 500


# ── Metrics ──────────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/metrics", methods=["GET"])
@login_required
def api_metrics_list():
    from dataforge.db import db_all
    metrics = db_all("metric_definitions", {"user_id": current_user.id}, order_by="created_at")
    return jsonify([{
        "id": m.get("id"), "name": m.get("name"), "formula": m.get("formula"),
        "description": m.get("description"), "category": m.get("category"),
        "created_at": m.get("created_at")
    } for m in metrics])


@dashboard_bp.route("/api/metrics", methods=["POST"])
@login_required
def api_metrics_create():
    from dataforge.db import db_first, db_insert, db_update
    body = request.get_json(force=True) or {}
    name    = (body.get("name") or "").strip()
    formula = (body.get("formula") or "").strip()
    if not name or not formula:
        return jsonify({"error": "name and formula are required"}), 400

    existing = db_first("metric_definitions", {"user_id": current_user.id, "name": name})

    m_dict = {
        "user_id": current_user.id,
        "name": name,
        "formula": formula,
        "description": body.get("description", ""),
        "category": body.get("category", "general"),
    }

    if existing:
        m_dict["updated_at"] = datetime.utcnow().isoformat()
        res = db_update("metric_definitions", existing.get("id"), m_dict)
    else:
        res = db_insert("metric_definitions", m_dict)

    return jsonify({"ok": True, "metric": res})


@dashboard_bp.route("/api/metrics/<int:metric_id>", methods=["DELETE"])
@login_required
def api_metrics_delete(metric_id):
    from dataforge.db import db_get, db_delete
    m = db_get("metric_definitions", metric_id)
    if not m or m.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404
    db_delete("metric_definitions", metric_id)
    return jsonify({"ok": True})


@dashboard_bp.route("/api/metrics/context", methods=["GET"])
@login_required
def api_metrics_context():
    from dataforge.db import db_all
    metrics = db_all("metric_definitions", {"user_id": current_user.id})
    if not metrics:
        return jsonify({"context": ""})
    lines = ["Defined business metrics:"]
    for m in metrics:
        line = f"  {m.get('name')} = {m.get('formula')}"
        if m.get('description'):
            line += f"  # {m.get('description')}"
        lines.append(line)
    return jsonify({"context": "\n".join(lines)})


# ── Data Sources ─────────────────────────────────────────────────────────────

@dashboard_bp.route("/api/sources", methods=["GET"])
@login_required
def api_sources_list():
    from dataforge.db import db_all
    sources = db_all("data_sources", {"user_id": current_user.id, "enabled": True})
    return jsonify([{
        "id": s.get("id"), "name": s.get("name"), "source_type": s.get("source_type"),
        "last_sync": s.get("last_sync"),
    } for s in sources])
