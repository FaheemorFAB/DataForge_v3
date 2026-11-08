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
from pydantic import BaseModel

from dataforge.api.deps import CurrentUser, OptionalCurrentUser, get_job_manager_dep, require_upload_with_data
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
from dataforge.api.utils.helpers import canonicalize_series, format_stat_val, is_id_like_col, resolve_column, robust_numeric_series, time_ago
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import db_client, db_get

log = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


# ── Correlation Heatmap Matrix ──────────────────────────────────────────────
@router.get("/dashboard/correlation-matrix", summary="Compute full correlation heatmap matrix")
async def api_correlation_matrix(
    current_user: CurrentUser,
    upload_id: str = Query(..., description="Upload ID"),
):
    await require_upload_with_data(upload_id, current_user)
    from dataforge.api.storage.manager import load as _load
    df_clean = _load(upload_id, "df_clean")
    df = df_clean if df_clean is not None else _load(upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "Dataset not loaded")

    num_cols = [c for c in df.select_dtypes(include=np.number).columns if not is_id_like_col(c, df[c])][:10]
    if len(num_cols) < 2:
        return JSONResponse(content={"ok": True, "columns": [], "matrix": []})

    corr = df[num_cols].corr(method="pearson").fillna(0.0)
    matrix = [[round(float(v), 3) for v in row] for row in corr.values]
    return JSONResponse(content={"ok": True, "columns": num_cols, "matrix": matrix})


# ── Dashboard initialization ────────────────────────────────────────────────
@router.get("/dashboard/init", summary="Get initialization data for the dashboard")
async def api_dashboard_init(
    current_user: CurrentUser,
    workspace_id: Optional[str] = Query(None, description="'personal' or an org_id UUID"),
):
    from dataforge.db import db_client, db_all, db_count
    from dataforge.teams.manager import TeamManager
    from dataforge.models.registry import ModelRegistry
    from dataforge.api.storage.manager import STORE_DIR, load
    from dataforge.api.utils.helpers import format_bytes
    from dataforge.api.config import get_settings
    settings = get_settings()
    
    user = current_user
    is_team_workspace = bool(workspace_id and workspace_id != "personal")

    # If scoped to a specific team/org workspace, verify membership
    if is_team_workspace:
        role = TeamManager.get_user_role(workspace_id, user.id, user_email=user.email)
        if not role:
            raise HTTPException(status_code=403, detail="Access denied: You are not a member of this workspace")

    def _resolve_size(item_id, meta_dict=None):
        if meta_dict and isinstance(meta_dict, dict):
            if meta_dict.get("size_human"):
                return meta_dict.get("size_bytes", 0), meta_dict.get("size_human")
            if meta_dict.get("size_bytes"):
                return meta_dict["size_bytes"], format_bytes(meta_dict["size_bytes"])
        try:
            target_dir = STORE_DIR / str(item_id)
            if target_dir.exists():
                for candidate in ("raw_workbook.xlsx", "df_raw.parquet", "df_raw.csv"):
                    f = target_dir / candidate
                    if f.exists():
                        sz = f.stat().st_size
                        return sz, format_bytes(sz)
                prof = load(str(item_id), "profile")
                if prof and isinstance(prof, dict):
                    if prof.get("size_bytes"):
                        return prof["size_bytes"], format_bytes(prof["size_bytes"])
        except Exception:
            pass
        return 0, "—"

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

    # Fetch uploads according to active workspace scope
    uploads_data = []
    if is_team_workspace:
        seen_ids = set()
        # 1. Query Supabase database uploads table for team
        try:
            db_uploads = db_all("uploads", {"org_id": workspace_id}, order_by="uploaded_at", limit=50)
            if not db_uploads:
                db_uploads = db_all("uploads", {"workspace_id": workspace_id}, order_by="uploaded_at", limit=50)
            for u in db_uploads:
                uid_str = str(u.get("id"))
                seen_ids.add(uid_str)
                m = load(uid_str, "meta")
                sz_bytes, sz_human = _resolve_size(uid_str, m)
                uploads_data.append({
                    "filename":    u.get("filename", ""),
                    "rows":        u.get("rows", 0) or 0,
                    "cols":        u.get("cols", 0) or 0,
                    "size_bytes":  sz_bytes,
                    "size_human":  sz_human,
                    "missing_pct": u.get("missing_pct", 0) or 0,
                    "time_ago":    _time_ago_local(u.get("uploaded_at")),
                    "id":          uid_str,
                    "source_type": u.get("source_type", "csv") or "csv",
                    "timestamp":   u.get("uploaded_at"),
                })
        except Exception as e:
            log.warning("db_all team uploads error: %s", e)

        # 2. Scan local STORE_DIR for team uploads matching workspace_id
        try:
            if STORE_DIR.exists():
                for item in STORE_DIR.iterdir():
                    if item.is_dir() and item.name not in seen_ids and (item / "meta.json").exists():
                        m = load(item.name, "meta")
                        if not m or not isinstance(m, dict):
                            continue
                        m_org = m.get("org_id")
                        m_ws = m.get("workspace_id")
                        if (m_org and str(m_org) == str(workspace_id)) or (m_ws and str(m_ws) == str(workspace_id)):
                            seen_ids.add(item.name)
                            created_ts = m.get("created_at") or m.get("uploaded_at")
                            sz_bytes, sz_human = _resolve_size(item.name, m)
                            uploads_data.append({
                                "filename":    m.get("filename", item.name),
                                "rows":        m.get("rows", 0) or 0,
                                "cols":        m.get("cols", 0) or 0,
                                "size_bytes":  sz_bytes,
                                "size_human":  sz_human,
                                "missing_pct": m.get("missing_pct", 0) or 0,
                                "time_ago":    _time_ago_local(created_ts),
                                "id":          m.get("id", item.name),
                                "source_type": m.get("source_type", "csv") or "csv",
                                "timestamp":   created_ts,
                            })
        except Exception as e:
            log.warning("Failed scanning team uploads: %s", e)
    else:
        # Personal workspace: STRICTLY show user's personal uploads (not tagged with an org_id)
        c_email = (getattr(user, "email", None) or "").strip().lower()
        seen_ids = set()

        # 1. Query Supabase database uploads table
        try:
            db_uploads = db_all("uploads", {"user_id": user.id}, order_by="uploaded_at", limit=50)
            for u in db_uploads:
                if u.get("org_id") or (u.get("workspace_id") and u.get("workspace_id") != "personal"):
                    continue  # Belongs to an org workspace, skip in personal
                uid_str = str(u.get("id"))
                m = load(uid_str, "meta")
                if m and (m.get("org_id") or (m.get("workspace_id") and m.get("workspace_id") != "personal")):
                    continue  # Belongs to an org workspace, skip in personal
                seen_ids.add(uid_str)
                sz_bytes, sz_human = _resolve_size(uid_str, m)
                uploads_data.append({
                    "filename":    u.get("filename", ""),
                    "rows":        u.get("rows", 0) or 0,
                    "cols":        u.get("cols", 0) or 0,
                    "size_bytes":  sz_bytes,
                    "size_human":  sz_human,
                    "missing_pct": u.get("missing_pct", 0) or 0,
                    "time_ago":    _time_ago_local(u.get("uploaded_at")),
                    "id":          uid_str,
                    "source_type": u.get("source_type", "csv") or "csv",
                    "timestamp":   u.get("uploaded_at"),
                })
        except Exception as e:
            log.warning("db_all uploads error: %s", e)

        # 2. Scan local STORE_DIR for all personal datasets owned by user_id or email
        try:
            if STORE_DIR.exists():
                for item in STORE_DIR.iterdir():
                    if item.is_dir() and item.name not in seen_ids and (item / "meta.json").exists():
                        m = load(item.name, "meta")
                        if not m or not isinstance(m, dict):
                            continue
                        if m.get("org_id") or (m.get("workspace_id") and m.get("workspace_id") != "personal"):
                            continue

                        m_uid = str(m.get("user_id") or "")
                        m_email = (m.get("user_email") or "").strip().lower()

                        is_owner = (
                            (m_uid and m_uid == str(user.id))
                            or (bool(c_email) and m_email == c_email)
                            or (not settings.PRODUCTION and (user.id == 1 or m_uid == "1"))
                        )

                        if is_owner:
                            seen_ids.add(item.name)
                            created_ts = m.get("created_at") or m.get("uploaded_at")
                            sz_bytes, sz_human = _resolve_size(item.name, m)
                            uploads_data.append({
                                "filename":    m.get("filename", item.name),
                                "rows":        m.get("rows", 0) or 0,
                                "cols":        m.get("cols", 0) or 0,
                                "size_bytes":  sz_bytes,
                                "size_human":  sz_human,
                                "missing_pct": m.get("missing_pct", 0) or 0,
                                "time_ago":    _time_ago_local(created_ts),
                                "id":          item.name,
                                "source_type": m.get("source_type", "csv") or "csv",
                                "timestamp":   created_ts,
                            })
        except Exception as e:
            log.warning("STORE_DIR scan error: %s", e)

    # Sort all uploads newest first
    def _parse_ts(u):
        for k in ("timestamp", "created_at", "uploaded_at"):
            v = u.get(k)
            if v:
                try:
                    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
                except Exception:
                    pass
        return 0.0

    uploads_data.sort(key=_parse_ts, reverse=True)
    uploads_data = uploads_data[:100]

    _icon_map = {"eda": "📊", "automl": "🤖", "clean": "🧹", "query": "💬", "insights": "💡", "report": "📄"}
    _map_labels = {
        "eda":      "EDA Report",
        "automl":   "AutoML Training",
        "clean":    "Data Cleaning",
        "query":    "AI Query",
        "insights": "Insights",
        "report":   "Report Generated",
    }

    analyses_data = []
    if not is_team_workspace and db_client:
        try:
            analyses_res = db_client.table("analyses").select("*, uploads(filename)").eq("user_id", user.id).order("created_at", desc=True).limit(30).execute()
            recent_analyses = analyses_res.data if analyses_res and analyses_res.data else []
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
        except Exception:
            pass

    alert_count = db_count("alerts", {"user_id": user.id, "resolved": False}) if not is_team_workspace else 0

    recent_reports = []
    if not is_team_workspace and db_client:
        try:
            reports_res = db_client.table("reports").select("*, uploads(filename)").eq("user_id", user.id).order("created_at", desc=True).limit(5).execute()
            recent_reports = reports_res.data if reports_res and reports_res.data else []
        except Exception:
            pass
    reports_data = []
    for r in recent_reports:
        up = r.get("uploads") or {}
        reports_data.append({
            "id":           r.get("id"),
            "filename":     up.get("filename", "Dataset"),
            "time_ago":     _time_ago_local(r.get("created_at")),
            "triggered_by": r.get("triggered_by", "auto"),
        })

    schedule_count = db_count("schedules", {"user_id": user.id}) if not is_team_workspace else 0

    member_since = ""
    try:
        created = user.created_at
        if created:
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            member_since = dt.strftime("%B %Y")
    except Exception:
        pass

    upload_count = len(uploads_data)
    analysis_count = len(analyses_data)
    query_count = db_count("chat_sessions", {"user_id": user.id}) if not is_team_workspace else 0
    models_list = ModelRegistry.list_models(org_id=workspace_id if is_team_workspace else None)
    models_count = len(models_list)

    stats = {
        "uploads": upload_count,
        "analyses": analysis_count,
        "models": models_count,
        "queries": query_count,
    }

    return {
        "user": {
            "name": user.name,
            "email": user.email,
            "avatar": user.avatar,
        },
        "stats": stats,
        "recent_uploads": uploads_data,
        "recent_analyses": analyses_data,
        "alert_count": alert_count,
        "recent_reports": reports_data,
        "schedule_count": schedule_count,
        "member_since": member_since,
        "workspace_id": workspace_id or "personal",
    }


# ── Local chart helper (self-contained, no Flask dependency) ─────────────────

def is_meaningful_numeric_col(col: str, s: pd.Series) -> bool:
    if is_id_like_col(col, s):
        return False
    num_s = robust_numeric_series(s).dropna()
    return len(num_s) >= 3 and num_s.nunique() >= 1


def is_intensive_metric(col: str, s: Optional[pd.Series] = None) -> bool:
    """
    Identifies if a numeric metric is intensive (scores, marks, averages, ratios, rates, percentages)
    where calculating a sum across rows is statistically nonsensical.
    """
    col_lower = (col or "").lower().strip()
    intensive_keywords = [
        "mark", "score", "pct", "percent", "percentage", "rate", "ratio",
        "grade", "gpa", "rating", "accuracy", "attendance", "discount",
        "temp", "temperature", "speed", "velocity", "yield", "margin",
        "prob", "probability", "index", "age", "unit_price", "unit_cost",
        "frequency", "rank", "ranking", "satisfaction", "retention", "per_"
    ]
    if any(k in col_lower for k in intensive_keywords):
        return True

    if s is not None:
        try:
            s_clean = pd.to_numeric(s, errors="coerce").dropna()
            if len(s_clean) > 0:
                if 0 <= s_clean.min() and s_clean.max() <= 100:
                    if any(k in col_lower for k in ["pct", "%", "rate", "ratio", "share", "score", "portion"]):
                        return True
                if 0 <= s_clean.min() and s_clean.max() <= 1.0 and s_clean.max() > 0:
                    if any(k in col_lower for k in ["rate", "ratio", "score", "pct", "factor", "weight"]):
                        return True
        except Exception:
            pass
    return False


def get_benchmark_col_and_val(metric_col: str, df: pd.DataFrame) -> tuple[Optional[str], Optional[float]]:
    """
    Finds a paired benchmark or ceiling value for an intensive metric (e.g. max_marks for marks_obtained).
    """
    col_lower = (metric_col or "").lower()
    candidate_keywords = ["max", "target", "total", "out_of", "benchmark", "ceiling", "full"]

    # 1. Exact or prefix/suffix patterns
    for c in df.columns:
        c_l = c.lower()
        if c_l == col_lower:
            continue
        if any(kw in c_l for kw in candidate_keywords) and any(stem in c_l for stem in ["mark", "score", "grade", "target", "pts", "points"]):
            s = robust_numeric_series(df[c]).dropna()
            if len(s) > 0 and s.nunique() <= 5:
                val = float(s.mode().iloc[0]) if not s.mode().empty else float(s.max())
                if val > 0:
                    return c, val

    # 2. General search for target/benchmark/max columns
    for c in df.columns:
        c_l = c.lower()
        if c_l in ["target", "benchmark", "max", "goal", "quota"]:
            s = robust_numeric_series(df[c]).dropna()
            if len(s) > 0:
                val = float(s.mode().iloc[0]) if not s.mode().empty else float(s.max())
                if val > 0:
                    return c, val

    return None, None

def _compute_chart_data(df, config):
    """Compute chart data for a custom chart config dict."""
    chart_id   = config.get("id")
    chart_type = config.get("chart_type") or config.get("type") or "bar"
    raw_x      = config.get("x_col")
    raw_y      = config.get("y_col")
    agg_type   = config.get("agg_type", "count" if not raw_y else "mean")

    x_col = resolve_column(raw_x, df.columns) if raw_x else None
    if not x_col and chart_type != "heatmap":
        return None

    y_col = resolve_column(raw_y, df.columns) if raw_y and str(raw_y).strip().lower() not in ("count", "none", "") else None
    if not y_col and agg_type not in ("none",):
        agg_type = "count"

    title = config.get("title")
    if not title:
        if chart_type == "heatmap":
            title = "Correlation Matrix (Heatmap)"
        else:
            title = f"{chart_type.title()} of {x_col}"

    labels           = []
    values           = []
    formatted_values = None

    if chart_type == "scatter":
        if not y_col:
            cand_y = [c for c in df.columns if c != x_col]
            y_col = cand_y[0] if cand_y else x_col
        x_s = robust_numeric_series(df[x_col])
        y_s = robust_numeric_series(df[y_col])
        sub_df = pd.DataFrame({"x": x_s, "y": y_s}).dropna()
        if sub_df.empty:
            sub_df = pd.DataFrame({"x": range(min(50, len(df))), "y": range(min(50, len(df)))})
        if len(sub_df) > 500:
            sub_df = sub_df.sample(n=500, random_state=42)
        sub_df = sub_df.sort_values(by="x")
        values = [{"x": float(r["x"]), "y": float(r["y"])} for _, r in sub_df.iterrows()]
        labels = []

    elif chart_type == "histogram":
        s = robust_numeric_series(df[x_col]).dropna()
        if len(s) > 0 and s.nunique() > 1:
            bins_count = min(15, max(5, int(s.nunique())))
            counts, edges = np.histogram(s, bins=bins_count)
            for i in range(len(counts)):
                labels.append(f"{format_stat_val(x_col, edges[i])} - {format_stat_val(x_col, edges[i+1])}")
            values = [int(c) for c in counts]
        else:
            grp = df[x_col].dropna().value_counts().head(15)
            labels = [str(x) for x in grp.index]
            values = [int(v) for v in grp.values]

    elif chart_type == "boxplot":
        num_col = x_col if x_col in df.columns and is_meaningful_numeric_col(x_col, df[x_col]) else (
            y_col if y_col and y_col in df.columns and is_meaningful_numeric_col(y_col, df[y_col]) else None
        )
        if not num_col:
            num_col = x_col if x_col in df.columns else (y_col if y_col in df.columns else None)

        cat_group_col = y_col if num_col == x_col and y_col in df.columns and y_col != x_col else (
            x_col if num_col == y_col and x_col in df.columns and x_col != y_col else None
        )

        if num_col and num_col in df.columns:
            s = robust_numeric_series(df[num_col]).dropna()
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
                    "min":    format_stat_val(num_col, lower_whisker),
                    "q1":     format_stat_val(num_col, q1),
                    "median": format_stat_val(num_col, median),
                    "q3":     format_stat_val(num_col, q3),
                    "max":    format_stat_val(num_col, upper_whisker),
                }

                if cat_group_col and cat_group_col in df.columns and 2 <= df[cat_group_col].dropna().nunique() <= 8:
                    grp_res = []
                    for cat_val, grp_df in df.groupby(cat_group_col):
                        gs = robust_numeric_series(grp_df[num_col]).dropna()
                        if len(gs) >= 3:
                            gdesc = gs.describe()
                            gq1 = float(gdesc["25%"])
                            gmed = float(gdesc["50%"])
                            gq3 = float(gdesc["75%"])
                            giqr = gq3 - gq1
                            gmin = float(gs[gs >= gq1 - 1.5 * giqr].min()) if not gs[gs >= gq1 - 1.5 * giqr].empty else float(gdesc["min"])
                            gmax = float(gs[gs <= gq3 + 1.5 * giqr].max()) if not gs[gs <= gq3 + 1.5 * giqr].empty else float(gdesc["max"])
                            grp_res.append({
                                "category": str(cat_val),
                                "min": gmin, "q1": gq1, "median": gmed, "q3": gq3, "max": gmax,
                                "formatted_median": format_stat_val(num_col, gmed),
                            })
                    if grp_res:
                        values["grouped"] = grp_res
            else:
                values = {"min": 0.0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0.0}
                formatted_values = {"min": "0", "q1": "0", "median": "0", "q3": "0", "max": "0"}
        else:
            values = {"min": 0.0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0.0}
            formatted_values = {"min": "0", "q1": "0", "median": "0", "q3": "0", "max": "0"}

    elif chart_type in ("radar", "polarArea"):
        canonical_x = canonicalize_series(df[x_col])
        if y_col and agg_type in ("sum", "mean"):
            num_y = robust_numeric_series(df[y_col])
            temp = pd.DataFrame({"_x": canonical_x, "_y": num_y}).dropna()
            grp = temp.groupby("_x")["_y"].sum() if agg_type == "sum" else temp.groupby("_x")["_y"].mean()
            grp = grp.sort_values(ascending=False).head(10)
        else:
            grp = canonical_x.dropna().value_counts().head(10)
        labels = [str(x) for x in grp.index]
        values = [round(float(v), 2) for v in grp.values]

    elif chart_type == "heatmap":
        num_cols = [c for c in df.select_dtypes(include=np.number).columns if not is_id_like_col(c, df[c])]
        for col in df.select_dtypes(include=["object", "string"]).columns:
            if col not in num_cols and not is_id_like_col(col, df[col]):
                s_num = robust_numeric_series(df[col])
                if s_num.notna().sum() >= max(5, int(len(df) * 0.5)):
                    num_cols.append(col)
        if len(num_cols) >= 2:
            sub = df[num_cols[:8]].apply(robust_numeric_series)
            corr_mat = sub.corr(method="pearson").fillna(0.0)
            labels = [str(c) for c in corr_mat.columns]
            values = [[round(float(v), 3) for v in row] for row in corr_mat.values]
        else:
            top_cats = [c for c in df.columns if df[c].nunique() >= 2][:6]
            if len(top_cats) >= 2:
                encoded = pd.DataFrame({c: df[c].astype('category').cat.codes for c in top_cats})
                corr_mat = encoded.corr(method="spearman").fillna(0.0)
                labels = top_cats
                values = [[round(float(v), 3) for v in row] for row in corr_mat.values]
            else:
                labels = [x_col] if x_col else ["Attribute A", "Attribute B"]
                values = [[1.0, 0.0], [0.0, 1.0]]

    elif chart_type == "waterfall":
        canonical_x = canonicalize_series(df[x_col])
        if y_col and agg_type in ("sum", "mean"):
            num_y = robust_numeric_series(df[y_col])
            temp = pd.DataFrame({"_x": canonical_x, "_y": num_y}).dropna()
            grp = temp.groupby("_x")["_y"].sum().sort_values(ascending=False).head(8)
        else:
            grp = canonical_x.dropna().value_counts().head(8)
        labels = [str(x) for x in grp.index] + ["Net Total"]
        vals = [round(float(v), 2) for v in grp.values]
        net_val = round(float(sum(vals)), 2)
        values = vals + [net_val]

    elif chart_type == "funnel":
        canonical_x = canonicalize_series(df[x_col])
        if y_col and agg_type in ("sum", "mean"):
            num_y = robust_numeric_series(df[y_col])
            temp = pd.DataFrame({"_x": canonical_x, "_y": num_y}).dropna()
            grp = temp.groupby("_x")["_y"].sum().sort_values(ascending=False).head(6)
        else:
            grp = canonical_x.dropna().value_counts().head(6)
        labels = [str(x) for x in grp.index]
        counts = [round(float(v), 2) for v in grp.values]
        top_c = counts[0] if counts and counts[0] > 0 else 1.0
        pcts = [round((c / top_c) * 100, 1) for c in counts]
        values = {"counts": counts, "pcts": pcts}

    elif chart_type == "combo":
        canonical_x = canonicalize_series(df[x_col])
        grp_cnt = canonical_x.dropna().value_counts().head(10)
        labels = [str(x) for x in grp_cnt.index]
        bars = [round(float(v), 2) for v in grp_cnt.values]
        if y_col:
            num_y = robust_numeric_series(df[y_col])
            temp = pd.DataFrame({"_x": canonical_x, "_y": num_y}).dropna()
            line_grp = temp.groupby("_x")["_y"].mean().reindex(grp_cnt.index).fillna(0.0)
            lines = [round(float(v), 2) for v in line_grp.values]
        else:
            lines = [round(b * 1.05, 2) for b in bars]
        values = {"bars": bars, "lines": lines}

    else:  # bar / line / area / pie / doughnut
        canonical_x = canonicalize_series(df[x_col])
        if agg_type == "none":
            sub_df = pd.DataFrame({"_x": canonical_x})
            if y_col:
                sub_df["_y"] = robust_numeric_series(df[y_col])
                sub_df = sub_df.dropna(subset=["_x", "_y"])
            else:
                sub_df = sub_df.dropna(subset=["_x"])
            if len(sub_df) > 500:
                sub_df = sub_df.head(500)
            labels = [str(v) for v in sub_df["_x"]]
            if y_col:
                values = [round(float(v), 2) for v in sub_df["_y"]]
            else:
                values = [1.0] * len(sub_df)
        else:
            if not y_col or agg_type == "count":
                grp = canonical_x.dropna().value_counts()
            else:
                num_y = robust_numeric_series(df[y_col])
                temp_df = pd.DataFrame({"_x": canonical_x, "_y": num_y}).dropna(subset=["_x", "_y"])
                if agg_type == "sum":
                    grp = temp_df.groupby("_x")["_y"].sum()
                elif agg_type == "mean":
                    grp = temp_df.groupby("_x")["_y"].mean()
                else:
                    grp = temp_df.groupby("_x")["_y"].count()

            top_n = config.get("top_n", 10) or 10
            if chart_type in ("pie", "doughnut"):
                grp_sorted = grp.sort_values(ascending=False)
                if len(grp_sorted) > top_n:
                    top_slices = grp_sorted.iloc[:top_n]
                    other_val = grp_sorted.iloc[top_n:].sum() if (not y_col or agg_type in ("sum", "count")) else grp_sorted.iloc[top_n:].mean()
                    labels = [str(x) for x in top_slices.index] + ["Other"]
                    values = [round(float(v), 2) for v in top_slices.values] + [round(float(other_val), 2)]
                else:
                    labels = [str(x) for x in grp_sorted.index]
                    values = [round(float(v), 2) for v in grp_sorted.values]
            elif chart_type in ("line", "area"):
                try:
                    dt_idx = pd.to_datetime(grp.index, errors="coerce")
                    if dt_idx.notna().sum() >= len(grp) * 0.7:
                        grp = grp.iloc[dt_idx.argsort()]
                    else:
                        grp = grp.sort_index()
                except Exception:
                    grp = grp.sort_index()
                grp = grp.head(100)
                labels = [str(x) for x in grp.index]
                values = [round(float(v), 2) for v in grp.values]
            else:  # bar
                grp = grp.sort_values(ascending=False).head(top_n if top_n > 0 else 20)
                labels = [str(x) for x in grp.index]
                values = [round(float(v), 2) for v in grp.values]

    return {
        "id":               chart_id,
        "type":             chart_type,
        "x_col":            x_col or "",
        "y_col":            y_col or ("count" if agg_type == "count" else ""),
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
    body: Optional[DashboardStatsRequest] = None,
    current_user: CurrentUser = None,
    upload_id: Optional[str] = Query(default=None),
):
    req_body = body or DashboardStatsRequest()
    target_upload_id = req_body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    def _compute():
        from dataforge.api.storage.manager import load as _load

        df_clean = _load(target_upload_id, "df_clean")
        df = df_clean if df_clean is not None else _load(target_upload_id, "df_raw")

        # Apply filters
        filters = req_body.filters or {}
        for col, val in filters.items():
            if col in df.columns:
                try:
                    df = df[df[col] == val]
                except Exception:
                    pass

        dim    = req_body.chart_dim
        metric = req_body.chart_metric

        schema  = _load(target_upload_id, "last_schema") or {}
        profile = _load(target_upload_id, "profile") or {}

        all_numeric = df.select_dtypes(include=np.number).columns.tolist()
        for col in df.select_dtypes(include=["object", "string"]).columns:
            if col not in all_numeric:
                s_num = robust_numeric_series(df[col])
                if s_num.notna().sum() >= max(5, int(len(df) * 0.6)):
                    all_numeric.append(col)

        # Separate true business metrics from IDs/entity keys
        id_cols = [c for c in df.columns if is_id_like_col(c, df[c])]
        valid_numeric_cols = [c for c in all_numeric if c not in id_cols]
        cat_cols = [c for c in df.columns if c not in all_numeric and c not in id_cols]

        # KPI stats formatting
        stats = []
        stats.append({
            "label": "Total Records",
            "value": f"{len(df):,}",
            "sub": f"{df.shape[1]} Columns",
            "type": "rows",
        })

        # Case-insensitive resolution of requested dim / metric
        col_map = {c.lower(): c for c in df.columns}
        if dim and dim not in df.columns and dim.lower() in col_map:
            dim = col_map[dim.lower()]
        if metric and metric not in df.columns and metric.lower() in col_map:
            metric = col_map[metric.lower()]

        dim_col = dim or (cat_cols[0] if cat_cols else None)

        if metric and metric in df.columns:
            metric_col = metric
        elif valid_numeric_cols:
            metric_col = valid_numeric_cols[0]
            for m in valid_numeric_cols:
                if any(k in m.lower() for k in ["revenue", "sales", "profit", "amount", "price", "cost", "score", "marks", "balance", "total", "gdp", "value", "quantity"]):
                    metric_col = m
                    break
        elif id_cols:
            metric_col = id_cols[0]
        else:
            metric_col = None

        if metric_col and metric_col in df.columns:
            is_id = is_id_like_col(metric_col, df[metric_col])
            if is_id:
                s_id = df[metric_col].dropna()
                u_cnt = s_id.nunique()
                is_100_pct = u_cnt == len(s_id)
                sub_txt = f"ID Range: {s_id.min()} to {s_id.max()} (100% Unique)" if is_100_pct else f"ID Range: {s_id.min()} to {s_id.max()} ({u_cnt:,} distinct)"
                stats.append({
                    "label": f"Unique {metric_col}",
                    "value": f"{u_cnt:,}",
                    "sub": sub_txt,
                    "type": "entity_count",
                    "color": "#6366f1",
                })
            elif pd.api.types.is_numeric_dtype(df[metric_col]) or metric_col in all_numeric:
                s = robust_numeric_series(df[metric_col]).dropna()
                if len(s) > 0:
                    if is_intensive_metric(metric_col, s):
                        b_col, b_val = get_benchmark_col_and_val(metric_col, df)
                        mean_val = float(s.mean())
                        s_min = float(s.min())
                        s_max = float(s.max())
                        s_med = float(s.median())
                        if b_val and b_val > 0:
                            val_str = f"{mean_val:.1f} / {b_val:.0f}"
                            valid_s = s[(s >= 0) & (s <= b_val)]
                            valid_min = float(valid_s.min()) if not valid_s.empty else 0.0
                            valid_max = float(valid_s.max()) if not valid_s.empty else b_val
                            sub_txt = f"Max: {valid_max:.0f} · Min: {valid_min:.0f} · Median: {s_med:.1f}"
                        elif any(k in metric_col.lower() for k in ["pct", "percent", "%", "attendance", "rate", "ratio", "margin", "yield"]):
                            val_str = f"{mean_val:.1f}%"
                            valid_s = s[(s >= 0) & (s <= 100)]
                            valid_min = float(valid_s.min()) if not valid_s.empty else 0.0
                            valid_max = float(valid_s.max()) if not valid_s.empty else 100.0
                            sub_txt = f"Max: {valid_max:.1f}% · Min: {valid_min:.1f}% · Median: {s_med:.1f}%"
                        else:
                            val_str = f"{mean_val:.2f}"
                            sub_txt = f"Max: {s_max:.1f} · Min: {s_min:.1f} · Median: {s_med:.1f}"
                        stats.append({
                            "label": f"Average {metric_col}",
                            "value": val_str,
                            "sub": sub_txt,
                            "type": "average",
                            "color": "#6366f1",
                        })
                    else:
                        stats.append({
                            "label": f"Total {metric_col}",
                            "value": format_stat_val(metric_col, float(s.sum())),
                            "sub": f"Avg: {format_stat_val(metric_col, float(s.mean()))}",
                            "type": "sum",
                        })
            else:
                s_cat = canonicalize_series(df[metric_col]).dropna()
                u_cnt = s_cat.nunique()
                top_v = str(s_cat.mode().iloc[0]) if not s_cat.mode().empty else "N/A"
                if len(top_v) > 15:
                    top_v = top_v[:12] + "..."
                stats.append({
                    "label": f"Categories: {metric_col}",
                    "value": f"{u_cnt:,}",
                    "sub": f"Dominant: '{top_v}'",
                    "type": "distinct",
                    "color": "#3b82f6",
                })

        if dim_col and dim_col in df.columns:
            s = canonicalize_series(df[dim_col]).dropna()
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

        # 4th KPI Card: High-Impact Performance or Attainment (Keep Data Health out of Executive Dashboard)
        fourth_card_added = False
        if metric_col and metric_col in df.columns and (pd.api.types.is_numeric_dtype(df[metric_col]) or metric_col in all_numeric):
            s_met = robust_numeric_series(df[metric_col]).dropna()
            b_col, b_val = get_benchmark_col_and_val(metric_col, df)

            # If a categorical dimension exists, find top cohort by mean
            if dim_col and dim_col in df.columns:
                temp_cohort = pd.DataFrame({"_c": df[dim_col], "_v": robust_numeric_series(df[metric_col])}).dropna()
                if not temp_cohort.empty and temp_cohort["_c"].nunique() >= 2:
                    grp_cohort = temp_cohort.groupby("_c")["_v"].mean().sort_values(ascending=False)
                    top_name = str(grp_cohort.index[0])
                    top_avg = float(grp_cohort.iloc[0])
                    if len(top_name) > 16:
                        top_name = top_name[:14] + "..."
                    stats.append({
                        "label": f"Top Cohort ({dim_col})",
                        "value": top_name,
                        "sub": f"Highest Avg {metric_col}: {top_avg:.1f}",
                        "color": "#10b981",
                        "type": "top_performer",
                    })
                    fourth_card_added = True

            # If benchmark exists, show benchmark attainment
            if not fourth_card_added and b_val and b_val > 0 and len(s_met) > 0:
                pass_th = b_val * 0.4
                pct_pass = (s_met >= pass_th).mean() * 100
                stats.append({
                    "label": "Benchmark Attainment",
                    "value": f"{pct_pass:.1f}%",
                    "sub": f"Scoring ≥ {pass_th:.0f} of {b_val:.0f} Target",
                    "color": "#10b981",
                    "type": "attainment",
                })
                fourth_card_added = True

        if not fourth_card_added:
            sec_candidates = [c for c in cat_cols if c != dim_col] if 'cat_cols' in locals() and cat_cols else []
            if sec_candidates:
                s_alt = canonicalize_series(df[sec_candidates[0]]).dropna()
                top_v = str(s_alt.mode().iloc[0]) if not s_alt.mode().empty else "N/A"
                stats.append({
                    "label": f"Cohort ({sec_candidates[0]})",
                    "value": f"{s_alt.nunique():,} Categories",
                    "sub": f"Dominant: '{top_v[:14]}'",
                    "color": "#8b5cf6",
                    "type": "distinct",
                })
            else:
                stats.append({
                    "label": "Active Analysis Scope",
                    "value": f"{len(df):,} Records",
                    "sub": f"{df.shape[1]} Ingested Dimensions",
                    "color": "#6366f1",
                    "type": "rows",
                })

        # Charts
        charts = []
        if dim_col and dim_col in df.columns:
            s_dim = canonicalize_series(df[dim_col])
            if metric_col and metric_col in df.columns and metric_col in valid_numeric_cols:
                s_m = robust_numeric_series(df[metric_col])
                temp_df = pd.DataFrame({"_dim": s_dim, "_metric": s_m}).dropna()
                is_int = is_intensive_metric(metric_col, s_m)
                agg_type = "mean" if is_int else "sum"
                if agg_type == "mean":
                    grp = temp_df.groupby("_dim")["_metric"].mean().sort_values(ascending=False).head(15)
                    ch_title = f"Average {metric_col} by {dim_col}"
                else:
                    grp = temp_df.groupby("_dim")["_metric"].sum().sort_values(ascending=False).head(15)
                    ch_title = f"{metric_col} by {dim_col}"
                charts.append({
                    "id": "bar", "type": "bar",
                    "title": ch_title,
                    "labels": [str(x) for x in grp.index],
                    "values": [round(float(v), 2) for v in grp.values],
                    "x_col": dim_col, "y_col": metric_col,
                    "agg_type": agg_type,
                })
            else:
                grp = s_dim.dropna().value_counts().head(15)
                charts.append({
                    "id": "bar", "type": "bar",
                    "title": f"Distribution of {dim_col}",
                    "labels": [str(x) for x in grp.index],
                    "values": [int(v) for v in grp.values],
                    "x_col": dim_col, "y_col": "count",
                    "agg_type": "count",
                })

        if valid_numeric_cols:
            col = valid_numeric_cols[0]
            s = robust_numeric_series(df[col]).dropna()
            if len(s) > 0 and s.nunique() > 1:
                counts, edges = np.histogram(s, bins=15)
                charts.append({
                    "id": "dist", "type": "histogram",
                    "title": f"Distribution: {col}",
                    "labels": [f"{format_stat_val(col, edges[i])}" for i in range(len(counts))],
                    "values": [int(c) for c in counts],
                    "x_col": col, "y_col": "count",
                })

            # Intelligent dispersion scoring for boxplot
            disp_candidates = []
            for c in valid_numeric_cols:
                sc = robust_numeric_series(df[c]).dropna()
                if len(sc) >= 5 and sc.nunique() >= 3:
                    std_val = float(sc.std())
                    iqr_val = float(sc.quantile(0.75) - sc.quantile(0.25))
                    if std_val > 1e-4 or iqr_val > 1e-4:
                        scr = min(sc.nunique(), 500)
                        if c == metric_col:
                            scr += 1000
                        if any(kw in c.lower() for kw in ["mark", "score", "price", "amount", "salary", "revenue", "cost", "val", "pct", "rate"]):
                            scr += 300
                        disp_candidates.append((scr, c))
            disp_candidates.sort(key=lambda x: x[0], reverse=True)
            box_col = disp_candidates[0][1] if disp_candidates else (metric_col if metric_col in valid_numeric_cols else valid_numeric_cols[0])
            s_box = robust_numeric_series(df[box_col]).dropna()
            if len(s_box) > 0:
                desc_b = s_box.describe()
                q1_b = float(desc_b["25%"])
                med_b = float(desc_b["50%"])
                q3_b = float(desc_b["75%"])
                iqr_b = q3_b - q1_b
                lw_b = float(s_box[s_box >= q1_b - 1.5 * iqr_b].min()) if not s_box[s_box >= q1_b - 1.5 * iqr_b].empty else float(desc_b["min"])
                uw_b = float(s_box[s_box <= q3_b + 1.5 * iqr_b].max()) if not s_box[s_box <= q3_b + 1.5 * iqr_b].empty else float(desc_b["max"])
                b_vals = {"min": lw_b, "q1": q1_b, "median": med_b, "q3": q3_b, "max": uw_b}
                if dim_col and dim_col in df.columns and 2 <= df[dim_col].dropna().nunique() <= 6:
                    g_res = []
                    for cv, gdf in df.groupby(dim_col):
                        gsc = robust_numeric_series(gdf[box_col]).dropna()
                        if len(gsc) >= 3:
                            gd = gsc.describe()
                            gq1 = float(gd["25%"])
                            gmed = float(gd["50%"])
                            gq3 = float(gd["75%"])
                            giqr = gq3 - gq1
                            gmin = float(gsc[gsc >= gq1 - 1.5 * giqr].min()) if not gsc[gsc >= gq1 - 1.5 * giqr].empty else float(gd["min"])
                            gmax = float(gsc[gsc <= gq3 + 1.5 * giqr].max()) if not gsc[gsc <= gq3 + 1.5 * giqr].empty else float(gd["max"])
                            g_res.append({
                                "category": str(cv),
                                "min": gmin, "q1": gq1, "median": gmed, "q3": gq3, "max": gmax,
                                "formatted_median": format_stat_val(box_col, gmed),
                            })
                    if g_res:
                        b_vals["grouped"] = g_res
                charts.append({
                    "id": "boxplot_stat", "type": "boxplot",
                    "title": f"Quantile Dispersion: {box_col}",
                    "values": b_vals,
                    "formatted_values": {
                        "min": format_stat_val(box_col, lw_b),
                        "q1": format_stat_val(box_col, q1_b),
                        "median": format_stat_val(box_col, med_b),
                        "q3": format_stat_val(box_col, q3_b),
                        "max": format_stat_val(box_col, uw_b),
                    },
                    "x_col": box_col, "y_col": "distribution",
                })

        custom_configs = _load(target_upload_id, "custom_charts") or []
        for config in custom_configs:
            computed = _compute_chart_data(df, config)
            if computed:
                charts.append(computed)

        # ID stats
        id_stats = None
        for col in df.columns:
            if is_id_like_col(col, df[col]):
                try:
                    s_id = df[col].dropna()
                    id_stats = {
                        "col": col,
                        "min": float(s_id.min()) if pd.api.types.is_numeric_dtype(s_id) else str(s_id.min()),
                        "max": float(s_id.max()) if pd.api.types.is_numeric_dtype(s_id) else str(s_id.max()),
                        "total": int(s_id.nunique()),
                    }
                    break
                except Exception:
                    pass

        recent_data = []
        if dim_col and metric_col and dim_col in df.columns and metric_col in df.columns:
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
            "pinned_insights": _load(target_upload_id, "pinned_insights") or [],
            "schema": schema_info, "profile": profile,
            "id_stats": id_stats, "recent_data": recent_data,
            "dim": dim_col, "metric": metric_col,
            "valid_metrics": valid_numeric_cols,
            "id_cols": id_cols,
            "numeric_cols": valid_numeric_cols, "cat_cols": cat_cols,
        }

    result = await run_in_executor(_compute)
    return JSONResponse(content=safe_jsonable(result))


# ── Agentic Auto-Pilot Dashboard ──────────────────────────────────────────────
@router.post("/dashboard/agentic-auto", summary="Generate agentic automated dashboard governed by AI workflow")
async def api_agentic_auto_dashboard(
    body: Optional[DashboardStatsRequest] = None,
    current_user: CurrentUser = None,
    upload_id: Optional[str] = Query(default=None),
):
    req_body = body or DashboardStatsRequest()
    target_upload_id = req_body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    def _generate_agentic():
        from dataforge.api.storage.manager import load as _load, save as _save
        df_clean = _load(target_upload_id, "df_clean")
        df = df_clean if df_clean is not None else _load(target_upload_id, "df_raw")
        if df is None:
            raise ValueError("No dataset found")

        # 1. Column classification with robust coercion detection
        all_numeric = df.select_dtypes(include=np.number).columns.tolist()
        for col in df.select_dtypes(include=["object", "string"]).columns:
            if col not in all_numeric:
                s_num = robust_numeric_series(df[col])
                if s_num.notna().sum() >= max(5, int(len(df) * 0.6)):
                    all_numeric.append(col)

        # Separate true business metrics from IDs/entity keys
        id_cols = [c for c in df.columns if is_id_like_col(c, df[c])]
        valid_numeric_cols = [c for c in all_numeric if c not in id_cols]
        date_cols = [c for c in df.columns if any(kw in c.lower() for kw in ["date", "time", "year", "month", "day"])]
        cat_cols = [c for c in df.columns if c not in all_numeric and c not in date_cols and c not in id_cols]

        # Case-insensitive resolution of requested dim / metric from body
        col_map = {c.lower(): c for c in df.columns}
        req_metric = req_body.chart_metric
        if req_metric and req_metric not in df.columns and req_metric.lower() in col_map:
            req_metric = col_map[req_metric.lower()]

        req_dim = req_body.chart_dim
        if req_dim and req_dim not in df.columns and req_dim.lower() in col_map:
            req_dim = col_map[req_dim.lower()]

        # 2. Primary metric & primary cohort selection
        if req_metric and req_metric in df.columns:
            primary_metric = req_metric
        elif valid_numeric_cols:
            primary_metric = valid_numeric_cols[0]
            for m in valid_numeric_cols:
                if any(k in m.lower() for k in ["sales", "revenue", "amount", "price", "profit", "cost", "total", "score", "value", "balance", "gdp", "marks"]):
                    primary_metric = m
                    break
        elif id_cols:
            primary_metric = id_cols[0]
        else:
            primary_metric = None

        if req_dim and req_dim in df.columns:
            primary_cat = req_dim
        elif cat_cols:
            primary_cat = cat_cols[0]
            for c in cat_cols:
                if any(k in c.lower() for k in ["category", "type", "segment", "region", "country", "status", "department", "genre", "state", "city", "class"]):
                    primary_cat = c
                    break
        else:
            primary_cat = df.columns[0] if len(df.columns) > 0 else None

        # 3. Executive KPI Cards (Always 4 distinct, meaningful cards)
        stats = []
        stats.append({
            "label": "Total Records",
            "value": f"{len(df):,}",
            "sub": f"{df.shape[1]} Attributes Ingested",
            "type": "rows",
        })

        if primary_metric:
            is_id = is_id_like_col(primary_metric, df[primary_metric])
            if is_id:
                s_id = df[primary_metric].dropna()
                u_cnt = s_id.nunique()
                is_100_pct = u_cnt == len(s_id)
                sub_txt = f"ID Range: {s_id.min()} to {s_id.max()} (100% Unique)" if is_100_pct else f"ID Range: {s_id.min()} to {s_id.max()} ({u_cnt:,} distinct)"
                stats.append({
                    "label": f"Unique {primary_metric}",
                    "value": f"{u_cnt:,}",
                    "sub": sub_txt,
                    "type": "entity_count",
                    "color": "#6366f1",
                })
            elif primary_metric in valid_numeric_cols or pd.api.types.is_numeric_dtype(df[primary_metric]):
                s = robust_numeric_series(df[primary_metric]).dropna()
                if len(s) > 0:
                    if is_intensive_metric(primary_metric, s):
                        b_col, b_val = get_benchmark_col_and_val(primary_metric, df)
                        mean_val = float(s.mean())
                        s_min = float(s.min())
                        s_max = float(s.max())
                        s_med = float(s.median())
                        if b_val and b_val > 0:
                            val_str = f"{mean_val:.1f} / {b_val:.0f}"
                            valid_s = s[(s >= 0) & (s <= b_val)]
                            valid_min = float(valid_s.min()) if not valid_s.empty else 0.0
                            valid_max = float(valid_s.max()) if not valid_s.empty else b_val
                            sub_txt = f"Max: {valid_max:.0f} · Min: {valid_min:.0f} · Median: {s_med:.1f}"
                        elif any(k in primary_metric.lower() for k in ["pct", "percent", "%", "attendance", "rate", "ratio", "margin", "yield"]):
                            val_str = f"{mean_val:.1f}%"
                            valid_s = s[(s >= 0) & (s <= 100)]
                            valid_min = float(valid_s.min()) if not valid_s.empty else 0.0
                            valid_max = float(valid_s.max()) if not valid_s.empty else 100.0
                            sub_txt = f"Max: {valid_max:.1f}% · Min: {valid_min:.1f}% · Median: {s_med:.1f}%"
                        else:
                            val_str = f"{mean_val:.2f}"
                            sub_txt = f"Max: {s_max:.1f} · Min: {s_min:.1f} · Median: {s_med:.1f}"
                        stats.append({
                            "label": f"Average {primary_metric}",
                            "value": val_str,
                            "sub": sub_txt,
                            "type": "average",
                            "color": "#6366f1",
                        })
                    else:
                        stats.append({
                            "label": f"Total {primary_metric}",
                            "value": format_stat_val(primary_metric, float(s.sum())),
                            "sub": f"Mean: {format_stat_val(primary_metric, float(s.mean()))}",
                            "type": "sum",
                        })
            else:
                sc = canonicalize_series(df[primary_metric]).dropna()
                top_v = str(sc.mode().iloc[0]) if not sc.mode().empty else "N/A"
                if len(top_v) > 15:
                    top_v = top_v[:12] + "..."
                stats.append({
                    "label": f"Categories: {primary_metric}",
                    "value": f"{sc.nunique():,}",
                    "sub": f"Dominant: '{top_v}'",
                    "type": "distinct",
                    "color": "#3b82f6",
                })
        elif primary_cat and len(df) > 0:
            sc = canonicalize_series(df[primary_cat]).dropna()
            if len(sc) > 0:
                top_v = str(sc.mode().iloc[0]) if not sc.mode().empty else "dominant segment"
                top_cnt = int(sc.value_counts().iloc[0]) if not sc.empty else 0
                top_pct = (top_cnt / len(sc)) * 100 if len(sc) > 0 else 0
                stats.append({
                    "label": "Segment Concentration",
                    "value": f"{top_pct:.1f}%",
                    "sub": f"Dominant: '{top_v[:14]}' ({top_cnt:,} rows)",
                    "type": "concentration",
                    "color": "#6366f1",
                })

        if primary_cat and primary_cat != primary_metric:
            sc = canonicalize_series(df[primary_cat]).dropna()
            if len(sc) > 0:
                top_v = str(sc.mode().iloc[0]) if not sc.mode().empty else "N/A"
                if len(top_v) > 15:
                    top_v = top_v[:12] + "..."
                stats.append({
                    "label": f"Primary Cohort ({primary_cat})",
                    "value": f"{sc.nunique():,} Categories",
                    "sub": f"Dominant: {top_v}",
                    "type": "distinct",
                })
        elif len(cat_cols) > 0 and cat_cols[0] != primary_metric:
            sc = canonicalize_series(df[cat_cols[0]]).dropna()
            if len(sc) > 0:
                top_v = str(sc.mode().iloc[0]) if not sc.mode().empty else "N/A"
                if len(top_v) > 15:
                    top_v = top_v[:12] + "..."
                stats.append({
                    "label": f"Cohort ({cat_cols[0]})",
                    "value": f"{sc.nunique():,} Categories",
                    "sub": f"Dominant: {top_v}",
                    "type": "distinct",
                })

        # 4. Fourth KPI Card: Top Performing Cohort or Benchmark Attainment (Keep Data Health out)
        fourth_card_added = False
        if primary_metric and (primary_metric in valid_numeric_cols or pd.api.types.is_numeric_dtype(df[primary_metric])):
            s_met = robust_numeric_series(df[primary_metric]).dropna()
            b_col, b_val = get_benchmark_col_and_val(primary_metric, df)

            # Check if primary_cat exists to find top cohort
            if primary_cat and primary_cat in df.columns:
                temp_cohort = pd.DataFrame({"_c": df[primary_cat], "_v": robust_numeric_series(df[primary_metric])}).dropna()
                if not temp_cohort.empty and temp_cohort["_c"].nunique() >= 2:
                    grp_cohort = temp_cohort.groupby("_c")["_v"].mean().sort_values(ascending=False)
                    top_name = str(grp_cohort.index[0])
                    top_avg = float(grp_cohort.iloc[0])
                    if len(top_name) > 16:
                        top_name = top_name[:14] + "..."
                    stats.append({
                        "label": f"Top Cohort ({primary_cat})",
                        "value": top_name,
                        "sub": f"Highest Avg {primary_metric}: {top_avg:.1f}",
                        "color": "#10b981",
                        "type": "top_performer",
                    })
                    fourth_card_added = True

            if not fourth_card_added and b_val and b_val > 0 and len(s_met) > 0:
                pass_th = b_val * 0.4
                pct_pass = (s_met >= pass_th).mean() * 100
                stats.append({
                    "label": "Benchmark Attainment",
                    "value": f"{pct_pass:.1f}%",
                    "sub": f"Scoring ≥ {pass_th:.0f} of {b_val:.0f} Target",
                    "color": "#10b981",
                    "type": "attainment",
                })
                fourth_card_added = True

        if not fourth_card_added:
            sec_cats = [c for c in cat_cols if c != primary_cat]
            if sec_cats:
                s_alt = canonicalize_series(df[sec_cats[0]]).dropna()
                top_v = str(s_alt.mode().iloc[0]) if not s_alt.mode().empty else "N/A"
                stats.append({
                    "label": f"Cohort ({sec_cats[0]})",
                    "value": f"{s_alt.nunique():,} Categories",
                    "sub": f"Dominant: '{top_v[:14]}'",
                    "color": "#8b5cf6",
                    "type": "distinct",
                })
            else:
                stats.append({
                    "label": "Metric Scope",
                    "value": f"{len(valid_numeric_cols)} Metrics",
                    "sub": f"{len(cat_cols)} Categorical Features",
                    "color": "#6366f1",
                    "type": "rows",
                })

        # 4. Automated Charts Suite
        charts = []
        chart_id_counter = 1
        seen_charts: set[tuple] = set()

        # Chart 1: Primary Cohort Breakdown
        if primary_cat and primary_metric and primary_metric in valid_numeric_cols:
            s_metric = robust_numeric_series(df[primary_metric])
            s_cat = canonicalize_series(df[primary_cat])
            temp_df = pd.DataFrame({"_cat": s_cat, "_metric": s_metric}).dropna()
            is_intensive = is_intensive_metric(primary_metric, s_metric)
            agg_type = "mean" if is_intensive else "sum"
            if agg_type == "mean":
                grp = temp_df.groupby("_cat")["_metric"].mean().sort_values(ascending=False).head(12)
                ch_title = f"Average {primary_metric} by {primary_cat}"
            else:
                grp = temp_df.groupby("_cat")["_metric"].sum().sort_values(ascending=False).head(12)
                ch_title = f"{primary_metric} by {primary_cat}"
            charts.append({
                "id": f"auto_{chart_id_counter}",
                "type": "bar",
                "title": ch_title,
                "labels": [str(x) for x in grp.index],
                "values": [round(float(v), 2) for v in grp.values],
                "x_col": primary_cat,
                "y_col": primary_metric,
                "agg_type": agg_type,
                "is_custom": False,
            })
            seen_charts.add((primary_cat, primary_metric))
            chart_id_counter += 1
        elif primary_cat:
            s_cat = canonicalize_series(df[primary_cat]).dropna()
            grp = s_cat.value_counts().head(12)
            charts.append({
                "id": f"auto_{chart_id_counter}",
                "type": "bar",
                "title": f"Distribution of {primary_cat}",
                "labels": [str(x) for x in grp.index],
                "values": [int(v) for v in grp.values],
                "x_col": primary_cat,
                "y_col": "count",
                "agg_type": "count",
                "is_custom": False,
            })
            seen_charts.add((primary_cat, "count"))
            chart_id_counter += 1

        # Chart 2: Category Share / Donut Chart
        target_donut_cat = None
        for c in cat_cols:
            if c != primary_cat and 2 <= canonicalize_series(df[c]).nunique() <= 12:
                target_donut_cat = c
                break
        if not target_donut_cat and len(cat_cols) > 1 and cat_cols[1] != primary_cat:
            target_donut_cat = cat_cols[1]

        if target_donut_cat and (target_donut_cat, "count") not in seen_charts:
            s_donut = canonicalize_series(df[target_donut_cat]).dropna()
            grp = s_donut.value_counts().head(8)
            charts.append({
                "id": f"auto_{chart_id_counter}",
                "type": "doughnut",
                "title": f"Distribution of {target_donut_cat}",
                "labels": [str(x) for x in grp.index],
                "values": [int(v) for v in grp.values],
                "x_col": target_donut_cat,
                "y_col": "count",
                "agg_type": "count",
                "is_custom": False,
            })
            seen_charts.add((target_donut_cat, "count"))
            chart_id_counter += 1

        # Chart 3: Temporal Trend / Activity over Time (Line) - Requires >= 3 unique points
        best_date_col = None
        for c in date_cols:
            if df[c].dropna().nunique() >= 3:
                best_date_col = c
                break
        if not best_date_col:
            for c in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[c]) and df[c].dropna().nunique() >= 3:
                    best_date_col = c
                    break

        if best_date_col:
            d_col = best_date_col
            try:
                if primary_metric and primary_metric in valid_numeric_cols:
                    s_m = robust_numeric_series(df[primary_metric])
                    temp = pd.DataFrame({d_col: df[d_col], primary_metric: s_m}).dropna()
                    temp_grp = temp.groupby(d_col)[primary_metric].mean().sort_index().tail(40)
                    if len(temp_grp) >= 3:
                        charts.append({
                            "id": f"auto_{chart_id_counter}",
                            "type": "line",
                            "title": f"{primary_metric} Trajectory over {d_col}",
                            "labels": [str(x)[:10] for x in temp_grp.index],
                            "values": [round(float(v), 2) for v in temp_grp.values],
                            "x_col": d_col,
                            "y_col": primary_metric,
                            "agg_type": "mean",
                            "is_custom": False,
                            "agent_source": "AnalyticsAgent",
                        })
                        chart_id_counter += 1
                else:
                    t_grp = df.groupby(d_col).size().sort_index().tail(30)
                    if len(t_grp) >= 3:
                        charts.append({
                            "id": f"auto_{chart_id_counter}",
                            "type": "line",
                            "title": f"Activity Volume over {d_col}",
                            "labels": [str(x)[:10] for x in t_grp.index],
                            "values": [int(v) for v in t_grp.values],
                            "x_col": d_col,
                            "y_col": "count",
                            "agg_type": "count",
                            "is_custom": False,
                            "agent_source": "AnalyticsAgent",
                        })
                        chart_id_counter += 1
            except Exception:
                pass
        elif len(cat_cols) > 1:
            sec_cat = cat_cols[1] if cat_cols[1] != primary_cat else (cat_cols[0] if len(cat_cols) > 0 else None)
            if sec_cat and (sec_cat, "count") not in seen_charts:
                s_sec = canonicalize_series(df[sec_cat]).dropna()
                grp = s_sec.value_counts().head(8)
                if len(grp) >= 2:
                    charts.append({
                        "id": f"auto_{chart_id_counter}",
                        "type": "bar",
                        "title": f"Volume by {sec_cat}",
                        "labels": [str(x) for x in grp.index],
                        "values": [int(v) for v in grp.values],
                        "x_col": sec_cat,
                        "y_col": "count",
                        "agg_type": "count",
                        "is_custom": False,
                        "agent_source": "AnalyticsAgent",
                    })
                    chart_id_counter += 1

        # Chart 4: Bivariate Correlation Scatter (if >=2 valid numeric measures with variance) OR Secondary Categorical Breakdown
        varying_numeric_cols = [
            c for c in valid_numeric_cols
            if robust_numeric_series(df[c]).dropna().nunique() >= 4
            and robust_numeric_series(df[c]).dropna().std() > 1e-4
        ]
        if len(varying_numeric_cols) >= 2:
            if primary_metric in varying_numeric_cols:
                cand_others = [c for c in varying_numeric_cols if c != primary_metric]
                def _corr_score(col):
                    try:
                        s1 = robust_numeric_series(df[primary_metric]).dropna()
                        s2 = robust_numeric_series(df[col]).dropna()
                        idx = s1.index.intersection(s2.index)
                        return abs(float(np.corrcoef(s1.loc[idx], s2.loc[idx])[0, 1]))
                    except Exception:
                        return 0.0
                cand_others.sort(key=_corr_score, reverse=True)
                x_num = cand_others[0]
                y_num = primary_metric
            else:
                x_num = varying_numeric_cols[0]
                y_num = varying_numeric_cols[1]

            x_s = robust_numeric_series(df[x_num])
            y_s = robust_numeric_series(df[y_num])
            sub = pd.DataFrame({x_num: x_s, y_num: y_s}).dropna()
            if len(sub) > 300:
                sub = sub.sample(n=300, random_state=42)
            sub = sub.sort_values(by=x_num)
            is_discrete_x = x_s.dropna().nunique() <= 5
            rng = np.random.default_rng(42)
            jitter_vals = rng.uniform(-0.5, 0.5, size=len(sub)) if is_discrete_x else np.zeros(len(sub))

            charts.append({
                "id": f"auto_{chart_id_counter}",
                "type": "scatter",
                "title": f"Bivariate Correlation: {x_num} vs {y_num}",
                "labels": [],
                "values": [
                    {"x": round(float(r[x_num]) + float(jitter_vals[i]), 2), "y": round(float(r[y_num]), 2)}
                    for i, (_, r) in enumerate(sub.iterrows())
                ],
                "x_col": x_num,
                "y_col": y_num,
                "is_custom": False,
                "agent_source": "AnalyticsAgent",
            })
            chart_id_counter += 1
        elif len(cat_cols) >= 3:
            third_cat = next((c for c in cat_cols if c not in (primary_cat, target_donut_cat)), None)
            if third_cat and (third_cat, "count") not in seen_charts:
                s_third = canonicalize_series(df[third_cat]).dropna()
                grp = s_third.value_counts().head(10)
                charts.append({
                    "id": f"auto_{chart_id_counter}",
                    "type": "bar",
                    "title": f"Breakdown by {third_cat}",
                    "labels": [str(x) for x in grp.index],
                    "values": [int(v) for v in grp.values],
                    "x_col": third_cat,
                    "y_col": "count",
                    "agg_type": "count",
                    "is_custom": False,
                    "agent_source": "AnalyticsAgent",
                })
                seen_charts.add((third_cat, "count"))
                chart_id_counter += 1

        # Chart 5: Numerical Distribution (Histogram) if primary_metric is a valid metric, OR Fourth Categorical Distribution
        if primary_metric and primary_metric in valid_numeric_cols:
            s = robust_numeric_series(df[primary_metric]).dropna()
            if len(s) > 0 and s.nunique() > 1:
                counts, edges = np.histogram(s, bins=12)
                charts.append({
                    "id": f"auto_{chart_id_counter}",
                    "type": "histogram",
                    "title": f"Frequency Distribution of {primary_metric}",
                    "labels": [f"{format_stat_val(primary_metric, edges[i])}" for i in range(len(counts))],
                    "values": [int(c) for c in counts],
                    "x_col": primary_metric,
                    "y_col": "count",
                    "is_custom": False,
                    "agent_source": "VisualizerAgent",
                })
                chart_id_counter += 1
        elif len(cat_cols) >= 4:
            fourth_cat = next((c for c in cat_cols if c not in (primary_cat, target_donut_cat, charts[-1]["x_col"])), None)
            if fourth_cat and (fourth_cat, "count") not in seen_charts:
                s_fourth = canonicalize_series(df[fourth_cat]).dropna()
                grp = s_fourth.value_counts().head(8)
                charts.append({
                    "id": f"auto_{chart_id_counter}",
                    "type": "doughnut",
                    "title": f"Category Share: {fourth_cat}",
                    "labels": [str(x) for x in grp.index],
                    "values": [int(v) for v in grp.values],
                    "x_col": fourth_cat,
                    "y_col": "count",
                    "agg_type": "count",
                    "is_custom": False,
                    "agent_source": "VisualizerAgent",
                })
                seen_charts.add((fourth_cat, "count"))
                chart_id_counter += 1

        # Chart 6: Statistical Box Plot OR Heatmap Association Matrix
        # Intelligently score continuous numeric columns to pick high-variance metrics
        dispersion_candidates = []
        for c in valid_numeric_cols:
            s_col = robust_numeric_series(df[c]).dropna()
            if len(s_col) >= 5 and s_col.nunique() >= 3:
                std_val = float(s_col.std())
                iqr_val = float(s_col.quantile(0.75) - s_col.quantile(0.25))
                if std_val > 1e-4 or iqr_val > 1e-4:
                    score = min(s_col.nunique(), 500)
                    if c == primary_metric:
                        score += 1000
                    if any(kw in c.lower() for kw in ["mark", "score", "price", "amount", "salary", "revenue", "cost", "val", "pct", "rate"]):
                        score += 300
                    dispersion_candidates.append((score, c))
        dispersion_candidates.sort(key=lambda x: x[0], reverse=True)
        target_box_metric = dispersion_candidates[0][1] if dispersion_candidates else (
            primary_metric if primary_metric in valid_numeric_cols else (valid_numeric_cols[0] if valid_numeric_cols else None)
        )
        if target_box_metric:
            s = robust_numeric_series(df[target_box_metric]).dropna()
            if len(s) > 0:
                desc = s.describe()
                q1 = float(desc["25%"])
                median = float(desc["50%"])
                q3 = float(desc["75%"])
                iqr = q3 - q1
                lower_w = float(s[s >= q1 - 1.5 * iqr].min()) if not s[s >= q1 - 1.5 * iqr].empty else float(desc["min"])
                upper_w = float(s[s <= q3 + 1.5 * iqr].max()) if not s[s <= q3 + 1.5 * iqr].empty else float(desc["max"])
                auto_box_vals = {"min": lower_w, "q1": q1, "median": median, "q3": q3, "max": upper_w}
                if primary_cat and primary_cat in df.columns and 2 <= df[primary_cat].dropna().nunique() <= 6:
                    auto_grp = []
                    for cv, gdf in df.groupby(primary_cat):
                        gs = robust_numeric_series(gdf[target_box_metric]).dropna()
                        if len(gs) >= 3:
                            gd = gs.describe()
                            gq1 = float(gd["25%"])
                            gmed = float(gd["50%"])
                            gq3 = float(gd["75%"])
                            giqr = gq3 - gq1
                            gmin = float(gs[gs >= gq1 - 1.5 * giqr].min()) if not gs[gs >= gq1 - 1.5 * giqr].empty else float(gd["min"])
                            gmax = float(gs[gs <= gq3 + 1.5 * giqr].max()) if not gs[gs <= gq3 + 1.5 * giqr].empty else float(gd["max"])
                            auto_grp.append({
                                "category": str(cv),
                                "min": gmin, "q1": gq1, "median": gmed, "q3": gq3, "max": gmax,
                                "formatted_median": format_stat_val(target_box_metric, gmed),
                            })
                    if auto_grp:
                        auto_box_vals["grouped"] = auto_grp

                charts.append({
                    "id": f"auto_{chart_id_counter}",
                    "type": "boxplot",
                    "title": f"Quantile Dispersion & Outlier Bounds: {target_box_metric}",
                    "values": auto_box_vals,
                    "formatted_values": {
                        "min": format_stat_val(target_box_metric, lower_w),
                        "q1": format_stat_val(target_box_metric, q1),
                        "median": format_stat_val(target_box_metric, median),
                        "q3": format_stat_val(target_box_metric, q3),
                        "max": format_stat_val(target_box_metric, upper_w),
                    },
                    "x_col": target_box_metric,
                    "y_col": "distribution",
                    "is_custom": False,
                    "agent_source": "AnalyticsAgent",
                })
                chart_id_counter += 1
        elif len(cat_cols) >= 2:
            sub_cats = cat_cols[:6]
            encoded = pd.DataFrame({c: df[c].astype('category').cat.codes for c in sub_cats})
            corr_mat = encoded.corr(method="spearman").fillna(0.0)
            charts.append({
                "id": f"auto_{chart_id_counter}",
                "type": "heatmap",
                "title": "Cross-Cohort Correlation Matrix",
                "labels": sub_cats,
                "values": [[round(float(v), 3) for v in row] for row in corr_mat.values],
                "x_col": "Cohort Matrix",
                "y_col": "Correlation",
                "is_custom": False,
                "agent_source": "AnalyticsAgent",
            })
            chart_id_counter += 1

        # 5. Load & Compute Custom Charts (CRITICAL FOR USER-ADDED CHARTS)
        custom_configs = _load(target_upload_id, "custom_charts") or []
        for config in custom_configs:
            computed = _compute_chart_data(df, config)
            if computed:
                charts.append(computed)

        # 6. ID Stats
        id_stats = None
        for col in df.columns:
            if is_id_like_col(col, df[col]):
                try:
                    s_id = df[col].dropna()
                    id_stats = {
                        "col": col,
                        "min": float(s_id.min()) if pd.api.types.is_numeric_dtype(s_id) else str(s_id.min()),
                        "max": float(s_id.max()) if pd.api.types.is_numeric_dtype(s_id) else str(s_id.max()),
                        "total": int(s_id.nunique()),
                    }
                    break
                except Exception:
                    pass

        # 7. Agentic Narrative Summary (Never output 'N/A')
        if primary_metric and primary_metric in valid_numeric_cols and primary_cat:
            s_m = robust_numeric_series(df[primary_metric]).dropna()
            tot_str = format_stat_val(primary_metric, float(s_m.sum())) if len(s_m) > 0 else "0"
            mean_str = format_stat_val(primary_metric, float(s_m.mean())) if len(s_m) > 0 else "0"
            agentic_summary = (
                f"The DataForge Agentic Workflow evaluated {len(df):,} records across {len(df.columns)} dimensions. "
                f"Primary quantitative driver detected is '{primary_metric}' (Total: {tot_str}, Mean: {mean_str}) benchmarked across dominant cohort '{primary_cat}'. "
                f"Automated visualizations and KPIs were curated by VisualizerAgent and AnalyticsAgent utilizing Pareto distribution, statistical dispersion, and bivariate correlation."
            )
        elif primary_metric and is_id_like_col(primary_metric, df[primary_metric]):
            u_cnt = df[primary_metric].nunique()
            agentic_summary = (
                f"The DataForge Agentic Workflow evaluated {len(df):,} records across {len(df.columns)} dimensions. "
                f"Entity tracking is anchored on '{primary_metric}' with {u_cnt:,} distinct identifiers. "
                f"Visualizations and cohort metrics were curated by VisualizerAgent and AnalyticsAgent using categorical grouping and cardinality analysis."
            )
        elif primary_metric:
            s_m = robust_numeric_series(df[primary_metric]).dropna()
            tot_str = format_stat_val(primary_metric, float(s_m.sum())) if len(s_m) > 0 else "0"
            agentic_summary = (
                f"The DataForge Agentic Workflow evaluated {len(df):,} records across {len(df.columns)} dimensions. "
                f"Primary quantitative driver detected is '{primary_metric}' (Total: {tot_str}). "
                f"Automated visualizations and metrics were curated by VisualizerAgent and AnalyticsAgent using statistical dispersion and frequency distribution."
            )
        elif primary_cat:
            sc = df[primary_cat].dropna()
            top_v = str(sc.mode().iloc[0]) if not sc.mode().empty else "dominant segment"
            agentic_summary = (
                f"The DataForge Agentic Workflow evaluated {len(df):,} records across {len(df.columns)} dimensions. "
                f"Primary categorical cohort identified is '{primary_cat}' with {sc.nunique()} distinct categories (dominant: '{top_v}'). "
                f"Automated charts and executive metrics were curated by VisualizerAgent and AnalyticsAgent using Pareto volumetric distributions, category share, and frequency ranking."
            )
        else:
            agentic_summary = (
                f"The DataForge Agentic Workflow evaluated {len(df):,} records across {len(df.columns)} dimensions. "
                f"Automated visualizations and executive KPIs were curated by VisualizerAgent and AnalyticsAgent across all available attributes."
            )

        agentic_payload = {
            "ok": True,
            "mode": "agentic_auto",
            "governed_by": "VisualizerAgent & AnalyticsAgent (Gemini Argon)",
            "stats": stats,
            "charts": charts,
            "summary": agentic_summary,
            "pinned_insights": _load(target_upload_id, "pinned_insights") or [],
            "valid_metrics": valid_numeric_cols,
            "id_cols": id_cols,
            "numeric_cols": valid_numeric_cols,
            "cat_cols": cat_cols,
            "dim": primary_cat,
            "metric": primary_metric,
            "id_stats": id_stats,
        }

        _save(target_upload_id, "agentic_dashboard", agentic_payload)
        return agentic_payload

    result = await run_in_executor(_generate_agentic)
    return JSONResponse(content=safe_jsonable(result))


# ── Drilldown ─────────────────────────────────────────────────────────────────

@router.post("/dashboard/drilldown", summary="Drill into filtered rows for a chart segment")
async def api_drilldown(
    body: DrilldownRequest,
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

    raw_col_name = body.col_name
    x_label      = body.x_label
    chart_id     = body.chart_id

    col_name = resolve_column(raw_col_name, df.columns)
    if not col_name:
        raise HTTPException(400, f"Column '{raw_col_name}' not found")

    try:
        if chart_id == "dist" and "-" in str(x_label):
            parts = str(x_label).split("-")
            p0 = parts[0].replace("$", "").replace(",", "").strip()
            p1 = parts[1].replace("$", "").replace(",", "").strip()
            left, right = float(p0), float(p1)
            s_num = robust_numeric_series(df[col_name])
            filtered = df[(s_num > left) & (s_num <= right)]
        else:
            col_dtype = df[col_name].dtype
            if pd.api.types.is_numeric_dtype(col_dtype):
                try:
                    val = float(x_label)
                    filtered = df[df[col_name] == val]
                except (ValueError, TypeError):
                    filtered = df[df[col_name].astype(str).str.strip().str.lower() == str(x_label).strip().lower()]
            else:
                filtered = df[df[col_name].astype(str).str.strip().str.lower() == str(x_label).strip().lower()]

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
    upload_id: Optional[str] = Query(default=None),
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


@router.delete("/reports/{report_id}", summary="Delete a saved report")
async def api_report_delete(
    current_user: CurrentUser,
    report_id: int = Path(...),
):
    rep = report_repo.get_by_id(report_id)
    if not rep or rep.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Report not found")

    success = report_repo.delete(report_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete report")

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "report_id": report_id,
        "message": "Report deleted successfully"
    }))



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
    upload_id: Optional[str] = Query(default=None),
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
    upload_id: Optional[str] = Query(default=None),
):
    from dataforge.api.routes.workspace import api_custom_chart_delete
    from dataforge.api.schemas.workspace import CustomChartDeleteRequest
    if upload_id and "upload_id" not in body:
        body["upload_id"] = upload_id
    return await api_custom_chart_delete(CustomChartDeleteRequest(**body), current_user, upload_id=upload_id)


# ── Pin / Unpin Insight to Dashboard ─────────────────────────────────────────

class PinInsightRequest(BaseModel):
    upload_id: str
    insight: dict
    action: str = "pin"  # "pin" or "unpin"


@router.post("/dashboard/pin-insight", summary="Pin or unpin an insight card to the dashboard")
async def api_pin_insight(
    body: PinInsightRequest,
    current_user: CurrentUser,
):
    await require_upload_with_data(body.upload_id, current_user)
    pinned = load(body.upload_id, "pinned_insights") or []
    ins_id = body.insight.get("title") or str(body.insight.get("id"))

    if body.action == "unpin":
        pinned = [p for p in pinned if (p.get("title") or str(p.get("id"))) != ins_id]
    else:
        if not any((p.get("title") or str(p.get("id"))) == ins_id for p in pinned):
            pinned.append(body.insight)

    save(body.upload_id, "pinned_insights", pinned)
    return {"ok": True, "pinned_count": len(pinned), "pinned_insights": pinned}
