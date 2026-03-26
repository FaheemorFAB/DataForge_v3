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


@dashboard_bp.route("/api/dashboard/stats")
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

    stats = []
    charts = []

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()

    for col in numeric_cols[:4]:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        stats.append({
            "label": col,
            "value": round(float(s.sum()), 2) if s.sum() > 1000 else round(float(s.mean()), 4),
            "sub":   f"mean {round(float(s.mean()), 2)} · {len(s):,} values",
            "type":  "sum" if s.sum() > 1000 else "mean",
        })

    schema = _load(upload_id, "last_schema")
    if schema and schema.get("date") and numeric_cols:
        try:
            date_col = schema["date"]
            metric   = numeric_cols[0]
            ts = df[[date_col, metric]].copy()
            ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
            ts = ts.dropna().sort_values(date_col)
            agg = ts.groupby(ts[date_col].dt.to_period("M"))[metric].sum()
            charts.append({
                "id": "trend", "type": "line",
                "title": f"{metric} over time",
                "labels": [str(p) for p in agg.index[-24:]],
                "values": [round(float(v), 2) for v in agg.values[-24:]],
                "x_label": date_col, "y_label": metric,
            })
        except Exception:
            pass

    if cat_cols and numeric_cols:
        try:
            dim = cat_cols[0]
            metric = numeric_cols[0]
            grp = df.groupby(dim)[metric].sum().sort_values(ascending=False).head(10)
            charts.append({
                "id": "top_cat", "type": "bar",
                "title": f"Top {dim} by {metric}",
                "labels": [str(i) for i in grp.index],
                "values": [round(float(v), 2) for v in grp.values],
                "x_label": dim, "y_label": metric,
            })
        except Exception:
            pass

    if numeric_cols:
        try:
            col = numeric_cols[0]
            s = df[col].dropna()
            hist, edges = np.histogram(s, bins=20)
            charts.append({
                "id": "dist", "type": "bar",
                "title": f"{col} distribution",
                "labels": [f"{round(float(e),1)}" for e in edges[:-1]],
                "values": [int(v) for v in hist],
                "x_label": col, "y_label": "count",
            })
        except Exception:
            pass

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
    })


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
