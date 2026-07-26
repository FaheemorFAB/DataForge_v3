"""
routes/dashboard.py — Dashboard Blueprint
Handles dashboard page, stats, reports, alerts, schedules, metrics, and sources.
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard_bp", __name__)


def _is_financial(col_name: str) -> bool:
    if not col_name:
        return False
    cl = str(col_name).lower()
    return any(kw in cl for kw in ["price", "revenue", "cost", "sales", "spend", "profit"])


def _format_stat_val(col_name: str, val: float) -> str:
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    
    is_fin = _is_financial(col_name)
    prefix = "$" if is_fin else ""
    
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        formatted = f"{val / 1_000_000:.2f}M"
    elif abs_val >= 1_000:
        formatted = f"{val / 1_000:.1f}K"
    else:
        if is_fin:
            formatted = f"{val:,.2f}"
        else:
            if val.is_integer():
                formatted = f"{val:,.0f}"
            else:
                formatted = f"{val:,.2f}"
    
    if formatted.endswith(".00M"):
        formatted = formatted[:-4] + "M"
    elif formatted.endswith(".0M"):
        formatted = formatted[:-3] + "M"
    elif formatted.endswith(".0K"):
        formatted = formatted[:-3] + "K"
        
    return f"{prefix}{formatted}"


# Keywords that indicate a numeric column is an ID/code/ordinal — not a true metric
_ID_KEYWORDS = (
    "id", "no", "num", "number", "code", "roll", "batch",
    "year", "reg", "serial", "seq", "rank", "index", "ref",
    "emp", "student", "class", "section", "grade",
    "date", "time", "timestamp",
)


def _is_id_like_col(col_name: str, series: pd.Series) -> bool:
    """Return True when a numeric column looks like a roll-no / batch / code."""
    cl = col_name.lower().replace("_", " ").replace("-", " ")
    # keyword match
    if any(kw in cl.split() or cl.startswith(kw) or cl.endswith(kw)
           for kw in _ID_KEYWORDS):
        return True
    # Structural check: integers with very low cardinality relative to rows,
    # or integers that look like years (1900-2100)
    if pd.api.types.is_integer_dtype(series):
        unique_vals = series.dropna().unique()
        if len(unique_vals) <= max(20, len(series) * 0.05):
            return True  # low-cardinality integer
        if all(1900 <= v <= 2100 for v in unique_vals[:50]):
            return True  # looks like year
    return False



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


@dashboard_bp.route("/api/dashboard/init")
@login_required
def api_dashboard_init():
    from dataforge.db import db_client, db_all, db_count
    
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

    return jsonify({
        "user": {
            "name": user.name,
            "email": user.email,
            "avatar": user.avatar,
            "id": user.id,
        },
        "stats": {
            "uploads": Stats.uploads,
            "analyses": Stats.analyses,
            "models": Stats.models,
            "queries": Stats.queries,
        },
        "recent_uploads": uploads_data,
        "recent_analyses": analyses_data,
        "alert_count": alert_count,
        "recent_reports": reports_data,
        "schedule_count": schedule_count,
        "member_since": member_since,
    })


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
    cat_cols = df.select_dtypes(include="object").columns.tolist()

    # Separate true metrics from ID-like columns
    id_like_cols = [c for c in numeric_cols if _is_id_like_col(c, df[c])]
    true_metrics  = [c for c in numeric_cols
                     if c not in id_like_cols
                     and not c.lower().endswith("id")
                     and c.lower() != "id"]
    if not true_metrics and numeric_cols:
        # fall back: use all numeric but prefer non-id-like
        true_metrics = [c for c in numeric_cols if c not in id_like_cols] or numeric_cols

    # Dims = object columns + id-like numeric columns
    valid_dims = cat_cols + id_like_cols + [
        c for c in numeric_cols if c.lower().endswith("id") or c.lower() == "id"
    ]
    metric = chart_metric if chart_metric in df.columns else (true_metrics[0] if true_metrics else None)
    dim = chart_dim if chart_dim in df.columns else (
        valid_dims[0] if valid_dims else (cat_cols[0] if cat_cols else None)
    )

    # 1. Total Rows Indicator
    rows_val = _format_stat_val(None, len(df))
    stats.append({
        "label": "Total Rows",
        "value": rows_val,
        "sub": f"{len(df):,} total records ({df.shape[1]} columns)",
        "type": "count"
    })

    # 2. Dynamic Metric Stat (true sum-able metric) or ID-like → show mode
    if metric:
        s = df[metric].dropna()
        if len(s) > 0:
            if _is_id_like_col(metric, s):
                # Treat as categorical: show most frequent value
                top_val = str(s.mode().iloc[0]) if not s.mode().empty else "N/A"
                stats.append({
                    "label": f"Most Common {metric}",
                    "value": top_val,
                    "sub": f"{s.nunique():,} unique values",
                    "type": "mode"
                })
            else:
                s_min = float(s.min())
                s_max = float(s.max())
                if s_min >= 0.0 and s_max <= 1.0:
                    mean_val = s.mean()
                    stats.append({
                        "label": f"Avg {metric}",
                        "value": _format_stat_val(metric, mean_val),
                        "sub": f"Min/Max: {_format_stat_val(metric, s_min)} / {_format_stat_val(metric, s_max)}",
                        "type": "avg"
                    })
                else:
                    total_val = s.sum()
                    mean_val = s.mean()
                    stats.append({
                        "label": f"Total {metric}",
                        "value": _format_stat_val(metric, total_val),
                        "sub": f"Avg: {_format_stat_val(metric, mean_val)}",
                        "type": "sum"
                    })
    else:
        stats.append({
            "label": "Metrics",
            "value": "0",
            "sub": "No numeric metrics",
            "type": "metric"
        })

    # 3. Dynamic Dimension Stat
    if dim:
        s = df[dim].dropna()
        if len(s) > 0:
            unique_cnt = s.nunique()
            top_val = str(s.mode().iloc[0]) if not s.mode().empty else "N/A"
            if len(top_val) > 15:
                top_val = top_val[:12] + "..."
            stats.append({
                "label": f"Unique {dim}",
                "value": _format_stat_val(None, unique_cnt),
                "sub": f"Top: {top_val} ({unique_cnt:,} total)",
                "type": "distinct"
            })
    else:
        stats.append({
            "label": "Dimensions",
            "value": "0",
            "sub": "No dimensions",
            "type": "dimension"
        })

    # 4. Data Completeness Card
    missing = int(df.isnull().sum().sum())
    total_cells = df.shape[0] * df.shape[1]
    missing_pct = (missing / total_cells) * 100 if total_cells > 0 else 0.0
    score = 100.0 - missing_pct

    if score >= 95:
        lbl = "Excellent (Ready for Analysis)"
        color = "#10b981"
    elif score >= 85:
        lbl = "Good (Minimal Gaps)"
        color = "#84cc16"
    elif score >= 70:
        lbl = "Fair (Some Gaps)"
        color = "#f59e0b"
    else:
        lbl = "Needs Attention (Significant Gaps)"
        color = "#ef4444"

    stats.append({
        "label": "Data Completeness",
        "value": f"{score:.1f}%",
        "sub": lbl,
        "color": color,
        "type": "completeness"
    })

    schema = _load(upload_id, "last_schema")
    if schema and schema.get("date") and true_metrics:
        try:
            date_col = schema["date"]
            ts_metric = true_metrics[0]
            ts = df[[date_col, ts_metric]].copy()
            ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
            ts = ts.dropna().sort_values(date_col)
            if _is_id_like_col(ts_metric, ts[ts_metric]):
                agg = ts.groupby(ts[date_col].dt.to_period("M"))[ts_metric].count()
                y_label = f"Count of {ts_metric}"
            else:
                agg = ts.groupby(ts[date_col].dt.to_period("M"))[ts_metric].sum()
                y_label = ts_metric
            charts.append({
                "id": "trend", "type": "line",
                "title": f"{y_label} over time",
                "labels": [str(p) for p in agg.index[-24:]],
                "values": [round(float(v), 2) for v in agg.values[-24:]],
                "x_label": date_col, "y_label": y_label,
            })
        except Exception:
            pass

    if dim and metric:
        try:
            # Bar Chart: group by dim. If metric is id-like, count occurrences; else mean.
            if _is_id_like_col(metric, df[metric]):
                grp = df.groupby(dim)[metric].count().sort_values(ascending=False).head(10)
                y_label = f"Count of {metric}"
            else:
                grp = df.groupby(dim)[metric].mean().sort_values(ascending=False).head(10)
                y_label = metric
            charts.append({
                "id": "top_cat", "type": "bar",
                "title": f"Top {dim} by {y_label}",
                "labels": [str(i) for i in grp.index],
                "values": [round(float(v), 2) for v in grp.values],
                "x_label": dim, "y_label": y_label,
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
                if s.nunique() <= 1:
                    labels = [f"Constant ({_format_stat_val(col, s.iloc[0])})"]
                    values = [len(s)]
                else:
                    buckets = pd.cut(s, bins=4, precision=1)
                    vc = buckets.value_counts(sort=False)
                    names = ["Low Range", "Lower-Mid Range", "Upper-Mid Range", "High Range"]
                    labels = []
                    for idx, b in enumerate(vc.index):
                        left_fmt = _format_stat_val(col, b.left)
                        right_fmt = _format_stat_val(col, b.right)
                        labels.append(f"{names[idx]} ({left_fmt} - {right_fmt})")
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

    # ── Guarantee minimum 3 auto-generated charts ─────────────────────────────
    # Chart 3 (if we have < 3 charts): Histogram of the best true metric
    if len(charts) < 3 and true_metrics:
        for m in true_metrics:
            try:
                s = df[m].dropna()
                if len(s) >= 10:
                    counts, edges = np.histogram(s, bins=12)
                    hist_labels = [f"{_format_stat_val(m, edges[i])}-{_format_stat_val(m, edges[i+1])}" for i in range(len(counts))]
                    hist_values = [int(c) for c in counts]
                    charts.append({
                        "id": f"hist_{m}", "type": "histogram",
                        "title": f"{m} — Distribution",
                        "labels": hist_labels, "values": hist_values,
                        "x_label": m, "y_label": "count",
                    })
                    break
            except Exception:
                pass

    # Chart 4 (if we have < 3 charts): Second categorical bar using next dim/metric pair
    if len(charts) < 3 and len(valid_dims) > 1 and true_metrics:
        try:
            dim2 = next((d for d in valid_dims if d != dim), None)
            metric2 = true_metrics[1] if len(true_metrics) > 1 else true_metrics[0]
            if dim2 and metric2 and dim2 in df.columns and metric2 in df.columns:
                grp2 = df.groupby(dim2)[metric2].mean().sort_values(ascending=False).head(8)
                if len(grp2) >= 2:
                    charts.append({
                        "id": f"cat2_{dim2}", "type": "bar",
                        "title": f"Avg {metric2} by {dim2}",
                        "labels": [str(i) for i in grp2.index],
                        "values": [round(float(v), 2) for v in grp2.values],
                        "x_label": dim2, "y_label": metric2,
                    })
        except Exception:
            pass

    # Chart 5 (if we still have < 3): Scatter between two numeric metrics
    if len(charts) < 3 and len(true_metrics) >= 2:
        try:
            mx, my = true_metrics[0], true_metrics[1]
            sub = df[[mx, my]].dropna()
            if len(sub) >= 10:
                if len(sub) > 400:
                    sub = sub.sample(400, random_state=42)
                scatter_vals = [{"x": round(float(r[mx]), 4), "y": round(float(r[my]), 4)} for _, r in sub.iterrows()]
                charts.append({
                    "id": "scatter_auto", "type": "scatter",
                    "title": f"{mx} vs {my}",
                    "labels": [], "values": scatter_vals,
                    "x_label": mx, "y_label": my,
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

    # Load and compute custom charts dynamically
    try:
        custom_configs = _load(upload_id, "custom_charts") or []
        for config in custom_configs:
            computed = _compute_chart_data(df, config)
            if computed:
                charts.append(computed)
    except Exception as e:
        logger.exception("Failed to load and compute custom charts: %s", e)

    return jsonify({
        "ok": True, "stats": stats, "charts": charts,
        "insights": [], "summary": "",
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
                           _tasks, _db_log_analysis, REPORTING_ENABLED,
                           _broker_available, SYNC_FALLBACK_ENABLED, _run_task_sync)
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

    # Use sync execution when no Celery worker is alive
    if not _broker_available():
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (_, _, _, task_generate_report, _) = _tasks()
            _run_task_sync(task_generate_report, [upload_id, current_user.id])
            _db_log_analysis("report", "completed sync fallback")
            return jsonify({"queued": False, "sync": True, "ok": True}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for report: %s", se)
            return jsonify({"error": f"Report generation failed: {se}"}), 500

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
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (_, _, _, task_generate_report, _) = _tasks()
            _run_task_sync(task_generate_report, [upload_id, current_user.id])
            _db_log_analysis("report", "completed sync fallback")
            return jsonify({"queued": False, "sync": True, "ok": True}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for report: %s", se)
            return jsonify({"error": f"Report generation failed: {se}"}), 500


@dashboard_bp.route("/api/reports/<int:report_id>")
@login_required
def api_report_view(report_id):
    from flask import current_app
    from dataforge.db import db_get
    rep = db_get("reports", report_id)
    if not rep or rep.get("user_id") != current_user.id:
        return Response("Not found", status=404)
    
    html = rep.get("report_html", "")
    fmt = (request.args.get("format") or "html").lower()
    if fmt == "pdf":
        pdf = None
        try:
            from weasyprint import HTML
            pdf = HTML(string=html, base_url=request.url_root).write_pdf()
        except Exception as e:
            current_app.logger.error("Failed to compile PDF with WeasyPrint: %s", e)
            
        if not pdf:
            try:
                from .workspace import _render_pdf_with_browser
                pdf = _render_pdf_with_browser(html)
            except Exception as e:
                current_app.logger.error("Failed to render PDF with browser: %s", e)
                
        if pdf:
            return Response(
                pdf,
                mimetype="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=dataforge_report_{report_id}.pdf"},
            )
            
    return Response(html, mimetype="text/html")


@dashboard_bp.route("/api/reports/current")
@login_required
def api_report_current():
    from flask import current_app
    from ..storage import _load
    from ..helpers import _get_upload_id

    upload_id = _get_upload_id()
    if not upload_id:
        return Response("upload_id required", status=400)
    html = _load(upload_id, "report_html")
    if not html:
        try:
            from ..helpers import _tasks, _run_task_sync
            (_, _, _, task_generate_report, _) = _tasks()
            _run_task_sync(task_generate_report, [upload_id, current_user.id])
            html = _load(upload_id, "report_html")
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for report generation in api_report_current: %s", se)

    if not html:
        return Response("No report yet and synchronous generation failed.", status=404)
    
    fmt = (request.args.get("format") or "html").lower()
    if fmt == "pdf":
        pdf = None
        try:
            from weasyprint import HTML
            pdf = HTML(string=html, base_url=request.url_root).write_pdf()
        except Exception as e:
            current_app.logger.error("Failed to compile PDF with WeasyPrint: %s", e)
            
        if not pdf:
            try:
                from .workspace import _render_pdf_with_browser
                pdf = _render_pdf_with_browser(html)
            except Exception as e:
                current_app.logger.error("Failed to render PDF with browser: %s", e)
                
        if pdf:
            return Response(
                pdf,
                mimetype="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=dataforge_report_current_{upload_id}.pdf"},
            )
            
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
                           _tasks, get_alert_status, REPORTING_ENABLED,
                           _broker_available, SYNC_FALLBACK_ENABLED, _run_task_sync)
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

    # Use sync execution when no Celery worker is alive
    if not _broker_available():
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (_, _, _, _, task_check_alerts) = _tasks()
            _run_task_sync(task_check_alerts, [upload_id, current_user.id])
            cached = get_alert_status(upload_id) or {}
            return jsonify({"ok": True, "sync": True, **cached}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for alerts: %s", se)
            return jsonify({"error": f"Alerts check failed: {se}"}), 500

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
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (_, _, _, _, task_check_alerts) = _tasks()
            _run_task_sync(task_check_alerts, [upload_id, current_user.id])
            cached = get_alert_status(upload_id) or {}
            return jsonify({"ok": True, "sync": True, **cached}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for alerts: %s", se)
            return jsonify({"error": f"Alerts check failed: {se}"}), 500


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


# ── Custom Chart Builder ─────────────────────────────────────────────────────

def _compute_chart_data(df, config):
    chart_id = config.get("id")
    chart_type = config.get("chart_type") or config.get("type")
    x_col = config.get("x_col")
    y_col = config.get("y_col")
    agg_type = config.get("agg_type", "none")
    title = config.get("title") or f"{(chart_type or 'Chart').title()} of {x_col}"
    
    if x_col not in df.columns:
        return None
    if y_col and y_col not in df.columns:
        y_col = None
        
    labels = []
    values = []
    formatted_values = None
    
    # 1. SCATTER PLOT
    if chart_type == "scatter":
        if not y_col or not pd.api.types.is_numeric_dtype(df[x_col]) or not pd.api.types.is_numeric_dtype(df[y_col]):
            return None
        
        MAX_POINTS = 500
        sub_df = df[[x_col, y_col]].dropna()
        if len(sub_df) > MAX_POINTS:
            sub_df = sub_df.sample(n=MAX_POINTS, random_state=42)
        
        sub_df = sub_df.sort_values(by=x_col)
        values = [{"x": float(r[x_col]), "y": float(r[y_col])} for _, r in sub_df.iterrows()]
        labels = []
        
    # 2. HISTOGRAM
    elif chart_type == "histogram":
        if not pd.api.types.is_numeric_dtype(df[x_col]):
            return None
        s = df[x_col].dropna()
        if len(s) > 0:
            counts, edges = np.histogram(s, bins=15)
            for i in range(len(counts)):
                left_fmt = _format_stat_val(x_col, edges[i])
                right_fmt = _format_stat_val(x_col, edges[i+1])
                labels.append(f"{left_fmt} - {right_fmt}")
            values = [int(c) for c in counts]
            
    # 3. BOXPLOT
    elif chart_type == "boxplot":
        if not pd.api.types.is_numeric_dtype(df[x_col]):
            return None
        s = df[x_col].dropna()
        if len(s) > 0:
            desc = s.describe()
            q1 = float(desc['25%'])
            median = float(desc['50%'])
            q3 = float(desc['75%'])
            iqr = q3 - q1
            lower_whisker = float(s[s >= q1 - 1.5 * iqr].min()) if not s[s >= q1 - 1.5 * iqr].empty else float(desc['min'])
            upper_whisker = float(s[s <= q3 + 1.5 * iqr].max()) if not s[s <= q3 + 1.5 * iqr].empty else float(desc['max'])
            
            values = {
                "min": lower_whisker,
                "q1": q1,
                "median": median,
                "q3": q3,
                "max": upper_whisker
            }
            formatted_values = {
                "min": _format_stat_val(x_col, lower_whisker),
                "q1": _format_stat_val(x_col, q1),
                "median": _format_stat_val(x_col, median),
                "q3": _format_stat_val(x_col, q3),
                "max": _format_stat_val(x_col, upper_whisker)
            }
            
    # 4. STANDARD CATEGORICAL/AGGREGATION CHARTS (bar, line, area, pie, doughnut)
    else:
        if agg_type == "none":
            MAX_POINTS = 500
            sub_df = df.dropna(subset=[x_col])
            if y_col:
                sub_df = sub_df.dropna(subset=[y_col])
            if len(sub_df) > MAX_POINTS:
                sub_df = sub_df.head(MAX_POINTS)
                
            labels = [str(v) for v in sub_df[x_col]]
            if y_col:
                values = [float(v) if pd.notna(v) else 0.0 for v in sub_df[y_col]]
            else:
                values = [1.0] * len(sub_df)
        else:
            if not y_col:
                agg_type = "count"
                grp = df.groupby(x_col).size()
            else:
                if agg_type == "sum":
                    grp = df.groupby(x_col)[y_col].sum()
                elif agg_type == "mean":
                    grp = df.groupby(x_col)[y_col].mean()
                else:
                    grp = df.groupby(x_col)[y_col].count()
            
            if chart_type in ("pie", "doughnut") and len(grp) > 10:
                grp_sorted = grp.sort_values(ascending=False)
                top_10 = grp_sorted.iloc[:10]
                other_val = grp_sorted.iloc[10:].sum() if agg_type in ("sum", "count") else grp_sorted.iloc[10:].mean()
                labels = [str(x) for x in top_10.index] + ["Other"]
                values = [round(float(v), 2) for v in top_10.values] + [round(float(other_val), 2)]
            else:
                grp = grp.sort_values(ascending=False).head(500)
                labels = [str(x) for x in grp.index]
                values = [round(float(v), 2) for v in grp.values]
                
    return {
        "id": chart_id,
        "type": chart_type,
        "x_col": x_col,
        "y_col": y_col,
        "agg_type": agg_type,
        "title": title,
        "labels": labels,
        "values": values,
        "formatted_values": formatted_values,
        "is_custom": True,
        "is_area": config.get("is_area", False)
    }


@dashboard_bp.route("/api/dashboard/custom-chart", methods=["POST"])
@login_required
def api_dashboard_custom_chart():
    from ..storage import _load, _save
    from ..helpers import _get_upload_id, _get_upload_or_403, _exists
    
    try:
        upload_id = _get_upload_id()
        if upload_id is None:
            return jsonify({"error": "upload_id required"}), 400
        upload, err = _get_upload_or_403(upload_id)
        if err:
            return err
        if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
            return jsonify({"error": "No dataset loaded."}), 400

        payload = request.get_json(silent=True) or {}
        chart_id = payload.get("id")
        chart_type = payload.get("chart_type")
        x_col = payload.get("x_col")
        y_col = payload.get("y_col")
        agg_type = payload.get("agg_type", "none")
        title = payload.get("title")
        is_area = payload.get("is_area", False)
        duplicate_from_id = payload.get("duplicate_from_id")

        if not chart_type or not x_col:
            return jsonify({"error": "chart_type and x_col are required"}), 400

        _dc = _load(upload_id, "df_clean")
        df = _dc if _dc is not None else _load(upload_id, "df_raw")

        if x_col not in df.columns:
            return jsonify({"error": f"Column '{x_col}' does not exist in the dataset"}), 400
        if y_col and y_col not in df.columns:
            return jsonify({"error": f"Column '{y_col}' does not exist in the dataset"}), 400

        # Validation checks
        if chart_type == "scatter":
            if not y_col:
                return jsonify({"error": "Scatter plot requires a Y-axis column"}), 400
            if not pd.api.types.is_numeric_dtype(df[x_col]):
                return jsonify({"error": "Scatter plot X-axis must be numeric"}), 400
            if not pd.api.types.is_numeric_dtype(df[y_col]):
                return jsonify({"error": "Scatter plot Y-axis must be numeric"}), 400

        if chart_type in ("histogram", "boxplot"):
            if not pd.api.types.is_numeric_dtype(df[x_col]):
                return jsonify({"error": f"{chart_type.title()} requires a numeric X-axis column"}), 400

        MAX_POINTS = 500
        if chart_type not in ("scatter", "histogram", "boxplot"):
            if agg_type == "none":
                if len(df) > MAX_POINTS:
                    return jsonify({"error": f"Plotting unaggregated data is limited to {MAX_POINTS} rows (dataset has {len(df)} rows). Please select an aggregation method like mean or sum."}), 400
            else:
                unique_count = df[x_col].nunique()
                if unique_count > MAX_POINTS:
                    return jsonify({"error": f"Column '{x_col}' has {unique_count} unique values. Grouping by it would freeze the dashboard. Please select a category column with fewer unique values (e.g. < 500)."}), 400

        custom_charts = _load(upload_id, "custom_charts") or []

        if duplicate_from_id:
            orig = next((c for c in custom_charts if c.get("id") == duplicate_from_id), None)
            if not orig:
                return jsonify({"error": "Original chart to duplicate not found"}), 404
            new_id = f"custom_{int(datetime.utcnow().timestamp() * 1000)}"
            new_chart_config = {
                "id": new_id,
                "chart_type": orig.get("chart_type"),
                "x_col": orig.get("x_col"),
                "y_col": orig.get("y_col"),
                "agg_type": orig.get("agg_type"),
                "title": f"Copy of {orig.get('title')}",
                "is_custom": True,
                "is_area": orig.get("is_area", False)
            }
            custom_charts.append(new_chart_config)
        elif chart_id:
            idx = next((i for i, c in enumerate(custom_charts) if c.get("id") == chart_id), None)
            if idx is None:
                return jsonify({"error": "Chart to edit not found"}), 404
            new_chart_config = {
                "id": chart_id,
                "chart_type": chart_type,
                "x_col": x_col,
                "y_col": y_col,
                "agg_type": agg_type,
                "title": title or f"{chart_type.upper()} of {x_col}",
                "is_custom": True,
                "is_area": is_area
            }
            custom_charts[idx] = new_chart_config
        else:
            new_id = f"custom_{int(datetime.utcnow().timestamp() * 1000)}"
            new_chart_config = {
                "id": new_id,
                "chart_type": chart_type,
                "x_col": x_col,
                "y_col": y_col,
                "agg_type": agg_type,
                "title": title or f"{chart_type.upper()} of {x_col}",
                "is_custom": True,
                "is_area": is_area
            }
            custom_charts.append(new_chart_config)

        _save(upload_id, "custom_charts", custom_charts)
        computed = _compute_chart_data(df, new_chart_config)
        return jsonify({"ok": True, "chart": computed})

    except Exception as e:
        logger.exception("Failed to create/edit custom chart: %s", e)
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/dashboard/custom-chart/delete", methods=["POST"])
@login_required
def api_dashboard_custom_chart_delete():
    from ..storage import _load, _save
    from ..helpers import _get_upload_id, _get_upload_or_403
    
    try:
        upload_id = _get_upload_id()
        if upload_id is None:
            return jsonify({"error": "upload_id required"}), 400
        upload, err = _get_upload_or_403(upload_id)
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        chart_id = payload.get("chart_id")

        if not chart_id:
            return jsonify({"error": "chart_id is required"}), 400

        custom_charts = _load(upload_id, "custom_charts") or []
        filtered_charts = [c for c in custom_charts if c.get("id") != chart_id]

        _save(upload_id, "custom_charts", filtered_charts)
        return jsonify({"ok": True})

    except Exception as e:
        logger.exception("Failed to delete custom chart: %s", e)
        return jsonify({"error": str(e)}), 500


# ── Assets ────────────────────────────────────────────────────────────────────

def _time_ago_str(dt_str: str) -> str:
    """Convert an ISO datetime string to a human-readable 'X ago' string."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        diff = datetime.now(dt.tzinfo) - dt if dt.tzinfo else datetime.utcnow() - dt
    except Exception:
        return ""
    s = int(diff.total_seconds())
    if s < 60:    return "just now"
    if s < 3600:  return f"{s//60}m ago"
    if s < 86400: return f"{s//3600}h ago"
    return f"{s//86400}d ago"


def _load_labels(project_dir) -> dict:
    """Load user-defined labels from labels.json inside a project dir."""
    p = project_dir / "labels.json"
    if p.exists():
        try:
            import json as _json
            return _json.loads(p.read_text("utf-8"))
        except Exception:
            pass
    return {}


def _save_labels(project_dir, labels: dict):
    """Persist labels.json inside a project dir."""
    import json as _json
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "labels.json").write_text(_json.dumps(labels, ensure_ascii=False), "utf-8")


@dashboard_bp.route("/api/assets", methods=["GET"])
@login_required
def api_assets():
    """Return all of the user's saved assets: cleaned datasets, ML models, EDA reports."""
    from dataforge.db import db_client
    from dataforge.settings import PROJECTS_DIR

    # ── Uploads (for datasets + EDA) ─────────────────────────────────────────
    try:
        up_res = (db_client.table("uploads")
                  .select("*")
                  .eq("user_id", current_user.id)
                  .order("uploaded_at", desc=True)
                  .limit(200)
                  .execute())
        uploads = up_res.data if up_res and up_res.data else []
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    datasets = []
    reports  = []

    for u in uploads:
        uid  = u.get("id")
        d    = PROJECTS_DIR / str(uid)
        lbls = _load_labels(d)

        has_clean = (d / "df_clean.parquet").exists() or (d / "df_clean").exists()
        has_eda   = (d / "eda_html.json").exists() or (d / "eda_html").exists()

        base = {
            "id":          uid,
            "filename":    u.get("filename", ""),
            "rows":        u.get("rows", 0) or 0,
            "cols":        u.get("cols", 0) or 0,
            "source_type": u.get("source_type", "csv") or "csv",
            "time_ago":    _time_ago_str(u.get("uploaded_at")),
        }

        if has_clean:
            datasets.append({**base, "label": lbls.get("dataset_label", "")})

        if has_eda:
            reports.append({
                "id":        uid,
                "upload_id": uid,
                "filename":  u.get("filename", ""),
                "label":     lbls.get("report_label", ""),
                "time_ago":  _time_ago_str(u.get("uploaded_at")),
            })

    # ── AutoML analyses (models) ──────────────────────────────────────────────
    try:
        ml_res = (db_client.table("analyses")
                  .select("*, uploads(filename)")
                  .eq("user_id", current_user.id)
                  .eq("type", "automl")
                  .order("created_at", desc=True)
                  .limit(100)
                  .execute())
        analyses = ml_res.data if ml_res and ml_res.data else []
    except Exception:
        analyses = []

    models = []
    for a in analyses:
        uid  = a.get("upload_id")
        d    = PROJECTS_DIR / str(uid)
        lbls = _load_labels(d)
        up   = a.get("uploads") or {}

        # Peek at result JSON for model info
        result = a.get("result") or {}
        if isinstance(result, str):
            try:
                import json as _json
                result = _json.loads(result)
            except Exception:
                result = {}

        model_key = f"model_label_{a.get('id')}"
        models.append({
            "id":         a.get("id"),
            "upload_id":  uid,
            "filename":   up.get("filename", ""),
            "model_name": result.get("best_model") or result.get("model_name") or "Model",
            "task_type":  result.get("task_type") or a.get("summary", "")[:30] or "—",
            "best_score": result.get("best_score"),
            "label":      lbls.get(model_key, ""),
            "time_ago":   _time_ago_str(a.get("created_at")),
        })

    return jsonify({"datasets": datasets, "models": models, "reports": reports})


@dashboard_bp.route("/api/assets/rename", methods=["POST"])
@login_required
def api_assets_rename():
    """Save a user-friendly label for a dataset, model, or EDA report."""
    from dataforge.settings import PROJECTS_DIR

    body  = request.get_json(force=True) or {}
    kind  = body.get("type")       # 'dataset' | 'model' | 'report'
    item_id = body.get("id")
    label   = (body.get("label") or "").strip()

    if not kind or not item_id or not label:
        return jsonify({"error": "type, id and label are required"}), 400

    # For models, item_id is the analysis id; we need upload_id to find the dir
    # For datasets/reports item_id IS the upload_id
    if kind == "model":
        from dataforge.db import db_client
        try:
            res = (db_client.table("analyses")
                   .select("upload_id")
                   .eq("id", item_id)
                   .eq("user_id", current_user.id)
                   .single()
                   .execute())
            upload_id = res.data.get("upload_id") if res and res.data else None
        except Exception:
            upload_id = None
        if not upload_id:
            return jsonify({"error": "Model not found"}), 404
        label_key = f"model_label_{item_id}"
    else:
        upload_id = item_id
        label_key = "dataset_label" if kind == "dataset" else "report_label"

    project_dir = PROJECTS_DIR / str(upload_id)
    lbls = _load_labels(project_dir)
    lbls[label_key] = label
    _save_labels(project_dir, lbls)

    return jsonify({"ok": True, "label": label})


# ── Account / Profile ─────────────────────────────────────────────────────────


@dashboard_bp.route("/api/account/update", methods=["POST"])
@login_required
def api_account_update():
    """Update user's display name and/or avatar URL."""
    from dataforge.db import db_update, db_get
    from dataforge.db import User

    body = request.get_json(force=True) or {}
    name   = (body.get("name") or "").strip()
    avatar = body.get("avatar")  # may be data URI — do not strip arbitrarily
    if avatar is not None:
        avatar = (avatar or "").strip()

    update_dict = {}
    if name:
        update_dict["name"] = name
    if avatar is not None:
        update_dict["avatar"] = avatar  # allow empty string to clear

    if not update_dict:
        return jsonify({"error": "Nothing to update"}), 400

    updated = db_update("users", current_user.id, update_dict)
    if not updated:
        return jsonify({"error": "Update failed"}), 500

    # Re-fetch to return fresh data
    fresh = db_get("users", current_user.id)
    return jsonify({"ok": True, "name": fresh.get("name"), "avatar": fresh.get("avatar")})


@dashboard_bp.route("/api/account/datasets", methods=["GET"])
@login_required
def api_account_datasets():
    """Return all cleaned datasets (uploads that have a clean version)."""
    from dataforge.db import db_client
    from dataforge.settings import PROJECTS_DIR

    try:
        res = (db_client.table("uploads")
               .select("*")
               .eq("user_id", current_user.id)
               .order("uploaded_at", desc=True)
               .limit(100)
               .execute())
        uploads = res.data if res and res.data else []
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    def _time_ago(dt_str):
        if not dt_str:
            return ""
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            diff = datetime.now(dt.tzinfo) - dt if dt.tzinfo else datetime.utcnow() - dt
        except Exception:
            return ""
        s = int(diff.total_seconds())
        if s < 60:    return "just now"
        if s < 3600:  return f"{s//60}m ago"
        if s < 86400: return f"{s//3600}h ago"
        return f"{s//86400}d ago"

    result = []
    for u in uploads:
        uid = u.get("id")
        d   = PROJECTS_DIR / str(uid)
        has_clean = (d / "df_clean.parquet").exists() or (d / "df_clean").exists()
        has_eda   = (d / "eda_html.json").exists() or (d / "eda_html").exists()
        result.append({
            "id":          uid,
            "filename":    u.get("filename", ""),
            "rows":        u.get("rows", 0) or 0,
            "cols":        u.get("cols", 0) or 0,
            "missing_pct": u.get("missing_pct", 0) or 0,
            "source_type": u.get("source_type", "csv") or "csv",
            "time_ago":    _time_ago(u.get("uploaded_at")),
            "uploaded_at": u.get("uploaded_at"),
            "has_clean":   has_clean,
            "has_eda":     has_eda,
        })

    return jsonify(result)


@dashboard_bp.route("/api/account/eda-reports", methods=["GET"])
@login_required
def api_account_eda_reports():
    """Return list of EDA reports generated for this user's uploads."""
    from dataforge.db import db_client

    try:
        res = (db_client.table("analyses")
               .select("*, uploads(filename)")
               .eq("user_id", current_user.id)
               .eq("type", "eda")
               .order("created_at", desc=True)
               .limit(50)
               .execute())
        analyses = res.data if res and res.data else []
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    def _time_ago(dt_str):
        if not dt_str:
            return ""
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            diff = datetime.now(dt.tzinfo) - dt if dt.tzinfo else datetime.utcnow() - dt
        except Exception:
            return ""
        s = int(diff.total_seconds())
        if s < 60:    return "just now"
        if s < 3600:  return f"{s//60}m ago"
        if s < 86400: return f"{s//3600}h ago"
        return f"{s//86400}d ago"

    result = []
    for a in analyses:
        up = a.get("uploads") or {}
        result.append({
            "id":         a.get("id"),
            "upload_id":  a.get("upload_id"),
            "filename":   up.get("filename", ""),
            "summary":    a.get("summary", ""),
            "time_ago":   _time_ago(a.get("created_at")),
            "created_at": a.get("created_at"),
        })

    return jsonify(result)


# ── DiceBear Avatar Generation ────────────────────────────────────────────────

# Style definition cache — loaded once per process per style
_DICEBEAR_CACHE: dict = {}

DICEBEAR_STYLES = [
    "lorelei", "avataaars", "bottts", "thumbs", "notionists",
    "adventurer", "fun-emoji", "pixel-art", "micah", "personas",
    "open-peeps", "shapes", "identicon", "rings", "croodles",
]


def _get_dicebear_style(style_name: str):
    """Load and cache a DiceBear style definition."""
    if style_name not in _DICEBEAR_CACHE:
        import json
        from importlib.resources import files
        from dicebear import Style
        raw = json.loads(
            files("dicebear_styles").joinpath(f"{style_name}.json").read_text("utf-8")
        )
        _DICEBEAR_CACHE[style_name] = Style(raw)
    return _DICEBEAR_CACHE[style_name]


@dashboard_bp.route("/api/account/avatar/generate", methods=["POST"])
@login_required
def api_account_avatar_generate():
    """Generate a DiceBear avatar data URI for the current user."""
    from dicebear import Avatar

    body   = request.get_json(force=True) or {}
    seed   = (body.get("seed") or current_user.name or current_user.email or "user").strip()
    style  = (body.get("style") or "lorelei").strip()

    if style not in DICEBEAR_STYLES:
        style = "lorelei"

    try:
        dicebear_style = _get_dicebear_style(style)
        avatar = Avatar(dicebear_style, {
            "seed":            seed,
            "size":            128,
            "idRandomization": True,
        })
        data_uri = avatar.to_data_uri()
        return jsonify({"ok": True, "data_uri": data_uri, "style": style, "seed": seed})
    except Exception as e:
        logger.exception("DiceBear avatar generation failed: %s", e)
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/account/avatar/styles", methods=["GET"])
@login_required
def api_account_avatar_styles():
    """Return the list of available DiceBear styles."""
    return jsonify({"styles": DICEBEAR_STYLES})
