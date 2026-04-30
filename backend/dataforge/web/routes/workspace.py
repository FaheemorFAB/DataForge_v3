"""
routes/workspace.py — Workspace Blueprint
Handles workspace page, state, preview, clean, EDA, AI query, and transform.
"""
import io
import json
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user

workspace_bp = Blueprint("workspace_bp", __name__)


def _clamp_int(value, default, minimum, maximum):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


@workspace_bp.route("/workspace")
@login_required
def workspace():
    from ..helpers import gemini_available
    upload_id = request.args.get("upload_id", type=int)
    return render_template(
        "workspace.html",
        user=current_user,
        gemini_ok=gemini_available(),
        upload_id=upload_id,
        profile={},
    )


@workspace_bp.route("/api/workspace/state")
@login_required
def api_workspace_state():
    import pandas as pd
    from ..storage import _save, _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _df_profile,
                           _get_filename, _load_persisted, _persist, _upath,
                           gemini_available)
    from dataforge.db import db_get

    upload_id = _get_upload_id()
    if not upload_id:
        return jsonify({"error": "upload_id parameter is required"}), 400
    up, err = _get_upload_or_403(upload_id)
    if err:
        return err

    profile     = _load(upload_id, "profile") or {}
    df_raw      = _load(upload_id, "df_raw")
    df_clean    = _load(upload_id, "df_clean")
    clean_meta  = _load(upload_id, "clean_meta")
    automl_meta = _load(upload_id, "automl_meta")
    chat_history = _load(upload_id, "chat_history") or []
    has_eda     = _upath(upload_id, "eda_html").exists()

    if df_raw is None and df_clean is None:
        for key in ("df_clean", "df_raw"):
            restored = _load_persisted(upload_id, key)
            if restored is not None:
                _save(upload_id, key, restored)
                if key == "df_clean":
                    df_clean = restored
                else:
                    df_raw = restored
                break

    clean_profile = None
    if df_clean is not None:
        clean_profile = _df_profile(df_clean, _get_filename(upload_id))

    needs_reupload    = False
    reupload_filename = ""
    reupload_message  = ""
    reupload_source_type = "csv"
    upload_id = _get_upload_id()
    if upload_id and df_raw is None and df_clean is None:
        try:
            up = db_get("uploads", upload_id)
            if up:
                src = up.get("source_type", "csv") or "csv"
                reupload_source_type = src
                up_filename = up.get("filename", "")

                if src == "sheets" and up.get("storage_path"):
                    try:
                        src_cfg = json.loads(up.get("storage_path"))
                        sheet_id_r = src_cfg.get("sheet_id", "")
                        if sheet_id_r:
                            from dataforge.sheets_connector import SheetsConnector
                            df_refetch = SheetsConnector().load_public(sheet_id_r)
                            _save(upload_id, "df_raw", df_refetch)
                            df_raw = df_refetch
                            profile = _df_profile(df_refetch, up_filename)
                            _save(upload_id, "profile", profile)
                            _persist(upload_id, "df_raw", df_refetch)
                    except Exception:
                        pass

                if df_raw is None:
                    needs_reupload    = True
                    reupload_filename = up_filename
                    if src == "sheets":
                        reupload_message = (
                            f"Could not re-fetch '{up_filename}' from Google Sheets. "
                            "The sheet may be private or the URL changed. Re-connect it."
                        )
                    else:
                        reupload_message = (
                            f"'{up_filename}' could not be restored from saved storage. "
                            "The cached dataset may be missing or corrupted, so re-upload the original file to continue your analysis."
                        )
                    if not profile:
                        profile = {
                            "filename":    up_filename,
                            "rows":        up.get("rows", 0) or 0,
                            "cols":        up.get("cols", 0) or 0,
                            "missing_pct": up.get("missing_pct", 0.0) or 0.0,
                            "missing":     0,
                            "numeric":     0,
                            "columns":     [],
                        }
        except Exception:
            pass

    state = {
        "has_df":            df_raw is not None,
        "has_clean":         df_clean is not None,
        "has_eda":           has_eda,
        "profile":           profile,
        "clean_profile":     clean_profile,
        "columns":           profile.get("columns", []),
        "clean_meta":        clean_meta,
        "automl_meta":       automl_meta,
        "chat_history":      chat_history,
        "filename":          _get_filename(upload_id),
        "gemini_ok":         gemini_available(),
        "needs_reupload":      needs_reupload,
        "reupload_filename":   reupload_filename,
        "reupload_message":    reupload_message,
        "source_type":         reupload_source_type,
    }
    return jsonify(state)


@workspace_bp.route("/api/preview")
@login_required
def api_preview():
    from flask import current_app
    from ..storage import _load
    from ..helpers import _get_upload_id, _get_upload_or_403, _df_to_json_rows, _upath, _load_persisted

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    limit = _clamp_int(request.args.get("limit", 500), 500, 50, 5000)
    use_clean = request.args.get("clean") == "true"
    key = "df_clean" if use_clean else "df_raw"

    p = _upath(upload_id, key).with_suffix('.parquet')
    if not p.exists():
        p = _upath(upload_id, "df_raw").with_suffix('.parquet')

    if p.exists():
        try:
            import duckdb
            cols = request.args.get("columns")
            if cols:
                cols_list = [_quote_ident(c.strip()) for c in cols.split(",") if c.strip()]
                select_clause = ", ".join(cols_list)
            else:
                select_clause = "*"
            total_rows = duckdb.execute(f"SELECT COUNT(*) AS total_rows FROM '{str(p)}'").fetchone()[0]
            preview_df = duckdb.execute(f"SELECT {select_clause} FROM '{str(p)}' LIMIT {limit}").df()
            payload = _df_to_json_rows(preview_df, limit)
            payload["loaded"] = len(preview_df)
            payload["total"] = int(total_rows)
            payload["preview_only"] = int(total_rows) > len(preview_df)
            return jsonify(payload)
        except Exception as e:
            current_app.logger.warning("DuckDB preview failed: %s", e)

    _dc = _load(upload_id, "df_clean") if use_clean else None
    df = _dc if _dc is not None else _load(upload_id, "df_raw")
    if df is None:
        for restore_key in ([key, "df_raw"] if key != "df_raw" else ["df_raw"]):
            restored = _load_persisted(upload_id, restore_key)
            if restored is not None:
                df = restored
                break
    if df is None:
        return jsonify({"error": "No dataset loaded"}), 400
    return jsonify(_df_to_json_rows(df, limit))


@workspace_bp.route("/api/chart/build", methods=["POST"])
@login_required
def api_chart_build():
    import numpy as np
    import pandas as pd
    from ..storage import _load
    from ..helpers import _get_upload_id, _get_upload_or_403, _load_persisted, _safe_json_value

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    body = request.get_json(force=True) or {}
    chart_type = (body.get("chart_type") or "bar").strip().lower()
    x_col = (body.get("x_col") or "").strip()
    y_col = (body.get("y_col") or "").strip()
    agg = (body.get("agg") or "count").strip().lower()
    use_clean = bool(body.get("use_clean", True))
    top_n = _clamp_int(body.get("top_n", 25), 25, 5, 100)

    valid_chart_types = {"bar", "line", "scatter", "histogram", "pie"}
    if chart_type not in valid_chart_types:
        return jsonify({"error": f"Unsupported chart type '{chart_type}'"}), 400
    if not x_col and chart_type != "histogram":
        return jsonify({"error": "Please choose an X-axis column."}), 400

    key = "df_clean" if use_clean else "df_raw"
    df = _load(upload_id, key)
    using_clean_df = use_clean and df is not None and key == "df_clean"
    if df is None and key != "df_raw":
        df = _load(upload_id, "df_raw")
    if df is None:
        for restore_key in ([key, "df_raw"] if key != "df_raw" else ["df_raw"]):
            restored = _load_persisted(upload_id, restore_key)
            if restored is not None:
                df = restored
                if restore_key == "df_clean":
                    using_clean_df = True
                break
    if df is None:
        return jsonify({"error": "No dataset loaded"}), 400

    if chart_type != "histogram" and x_col not in df.columns:
        return jsonify({"error": f"Column '{x_col}' was not found in this dataset."}), 400
    if y_col and y_col not in df.columns:
        return jsonify({"error": f"Column '{y_col}' was not found in this dataset."}), 400

    def _coerce_datetime(series: pd.Series):
        if pd.api.types.is_datetime64_any_dtype(series):
            return series
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            return None
        parsed = pd.to_datetime(series, errors="coerce")
        valid = int(parsed.notna().sum())
        if valid >= 3 and valid / max(len(series), 1) >= 0.6:
            return parsed
        return None

    def _to_numeric(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce")

    def _format_label(value):
        if pd.isna(value):
            return "(missing)"
        if isinstance(value, pd.Timestamp):
            if value.time() == pd.Timestamp(value.date()).time():
                return value.strftime("%Y-%m-%d")
            return value.strftime("%Y-%m-%d %H:%M")
        return str(value)

    def _metric_label():
        if agg == "count" or not y_col:
            return "row count"
        return f"{agg} of {y_col}"

    if chart_type == "histogram":
        source_col = y_col or x_col
        if not source_col:
            return jsonify({"error": "Please choose a numeric column for the histogram."}), 400
        if source_col not in df.columns:
            return jsonify({"error": f"Column '{source_col}' was not found in this dataset."}), 400

        series = _to_numeric(df[source_col]).dropna()
        if series.empty:
            return jsonify({"error": f"Column '{source_col}' does not contain numeric values for a histogram."}), 400

        bins = min(24, max(8, int(np.sqrt(len(series)))))
        counts, edges = np.histogram(series, bins=bins)
        labels = [f"{edges[i]:.2f} to {edges[i + 1]:.2f}" for i in range(len(edges) - 1)]
        return jsonify({
            "chart": {
                "type": "histogram",
                "labels": labels,
                "values": [int(v) for v in counts.tolist()],
                "x_label": source_col,
                "y_label": "Count",
            },
            "summary": (
                f"Built a histogram for {source_col} from the full dataset. "
                f"Used {len(series):,} numeric rows out of {len(df):,} total rows."
            ),
            "meta": {
                "total_rows": int(len(df)),
                "rows_used": int(len(series)),
                "backend_scope": "full_dataset",
                "clean_used": bool(using_clean_df),
            },
        })

    if chart_type == "scatter":
        if not y_col:
            return jsonify({"error": "Scatter charts need both X and Y numeric columns."}), 400
        work = pd.DataFrame({
            "x": _to_numeric(df[x_col]),
            "y": _to_numeric(df[y_col]),
        }).dropna()
        if work.empty:
            return jsonify({"error": "Those columns do not have enough numeric values for a scatter chart."}), 400

        total_points = len(work)
        if total_points > 1200:
            work = work.sample(1200, random_state=42)

        points = [
            {"x": float(row.x), "y": float(row.y)}
            for row in work.itertuples(index=False)
        ]
        corr = float(work["x"].corr(work["y"])) if len(work) >= 2 else None
        corr_txt = f" Correlation is {corr:.3f}." if corr is not None and not np.isnan(corr) else ""
        return jsonify({
            "chart": {
                "type": "scatter_chart",
                "points": points,
                "x_label": x_col,
                "y_label": y_col,
                "total_points": int(total_points),
                "displayed_points": int(len(points)),
            },
            "summary": (
                f"Built a scatter chart from the full dataset using {total_points:,} valid rows."
                f"{corr_txt}"
            ),
            "meta": {
                "total_rows": int(len(df)),
                "rows_used": int(total_points),
                "displayed_points": int(len(points)),
                "backend_scope": "full_dataset",
                "clean_used": bool(using_clean_df),
            },
        })

    x_source = df[x_col]
    x_datetime = _coerce_datetime(x_source)
    work = pd.DataFrame({
        "x": x_datetime if x_datetime is not None else x_source,
    })

    if agg != "count" and y_col:
        work["y"] = _to_numeric(df[y_col])
        work = work.dropna(subset=["x", "y"])
    else:
        work = work.dropna(subset=["x"])

    if work.empty:
        return jsonify({"error": "No usable rows remained after removing missing values for the selected chart."}), 400

    valid_aggs = {"count", "sum", "mean", "median", "min", "max"}
    if agg not in valid_aggs:
        agg = "count"

    if agg == "count" or not y_col:
        grouped = work.groupby("x", dropna=False).size().reset_index(name="value")
    else:
        grouped = work.groupby("x", dropna=False)["y"].agg(agg).reset_index(name="value")

    grouped = grouped.replace([np.inf, -np.inf], np.nan).dropna(subset=["value"])
    if grouped.empty:
        return jsonify({"error": "Could not produce a usable chart from the selected columns."}), 400

    if x_datetime is not None:
        grouped = grouped.sort_values("x")
        if chart_type in {"line", "bar"} and len(grouped) > 60:
            grouped = grouped.tail(60)
    else:
        grouped["x_label"] = grouped["x"].map(_format_label)
        if chart_type == "line":
            grouped = grouped.sort_values("x_label").head(60)
        else:
            grouped = grouped.sort_values("value", ascending=False).head(top_n)

    if "x_label" not in grouped.columns:
        grouped["x_label"] = grouped["x"].map(_format_label)

    labels = grouped["x_label"].tolist()
    values = [
        _safe_json_value(float(v)) if pd.notna(v) else None
        for v in grouped["value"].tolist()
    ]
    top_idx = max(range(len(values)), key=lambda i: values[i] if values[i] is not None else float("-inf"))
    summary = (
        f"{labels[top_idx]} has the highest {_metric_label()} at {values[top_idx]:,.2f}. "
        f"Built from {len(work):,} usable rows out of {len(df):,} total rows."
    )
    if agg == "count" or not y_col:
        summary = (
            f"{labels[top_idx]} has the highest row count at {int(values[top_idx]):,}. "
            f"Built from {len(work):,} usable rows out of {len(df):,} total rows."
        )

    return jsonify({
        "chart": {
            "type": "line_chart" if chart_type == "line" else "bar_chart",
            "labels": labels,
            "values": values,
            "x_label": x_col,
            "y_label": _metric_label(),
            "render_as": chart_type,
        },
        "summary": summary,
        "meta": {
            "total_rows": int(len(df)),
            "rows_used": int(len(work)),
            "groups_rendered": int(len(labels)),
            "backend_scope": "full_dataset",
            "clean_used": bool(using_clean_df),
        },
    })


@workspace_bp.route("/api/clean", methods=["POST"])
@login_required
def api_clean():
    import json
    from flask import current_app
    from ..storage import _save, _load
    from ..helpers import (_require_df, _get_upload_id, _get_upload_or_403,
                           _df_profile, _get_filename, _persist, _db_log_analysis,
                           invalidate_upload, run_cleaning_pipeline, _exists)
    from dataforge.db import db_update

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded. Please upload a CSV first."}), 400

    df_raw = _load(upload_id, "df_raw")
    try:
        result = run_cleaning_pipeline(df_raw)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    df_clean = result["df_clean"]
    _save(upload_id, "df_clean", df_clean)

    clean_profile = _df_profile(df_clean, _get_filename(upload_id))
    meta = {
        "stats":          result["stats"],
        "missing_log":    result["missing_log"],
        "struct_actions": result["struct_actions"],
        "clean_profile":  clean_profile,
    }
    _save(upload_id, "clean_meta", meta)

    if upload_id:
        _persist(upload_id, "df_clean", df_clean)
        try:
            invalidate_upload(upload_id)
        except Exception:
            pass
        try:
            db_update("uploads", upload_id, {"clean_meta_json": json.dumps(meta, default=str)})
        except Exception as e:
            current_app.logger.warning("Failed to save clean_meta_json to DB: %s", e)

    _db_log_analysis("clean", f"Removed {result['stats'].get('rows_removed',0)} rows · "
                               f"{result['stats'].get('cols_removed',0)} cols dropped")
    return jsonify({
        "ok":             True,
        "stats":          result["stats"],
        "missing_log":    result["missing_log"],
        "struct_actions": result["struct_actions"],
        "clean_profile":  clean_profile,
    })


@workspace_bp.route("/api/eda", methods=["POST"])
@login_required
def api_eda():
    from ..storage import _save, _load
    from ..helpers import (_require_df, _get_upload_id, _get_upload_or_403,
                           _db_log_analysis, _persist, generate_eda_report, _exists)

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded. Please upload a CSV first."}), 400

    body     = request.get_json(force=True) or {}
    minimal  = bool(body.get("minimal", True))
    sample_n = int(body.get("sample_n", 5000)) or 5000

    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")

    result = generate_eda_report(df, minimal=minimal, sample_n=sample_n)

    html          = result.get("html") or ""
    rows_profiled = result.get("rows_profiled", len(df))
    warning       = result.get("error")

    if html:
        _save(upload_id, "eda_html", html)
        _persist(upload_id, "eda_html", html)

    _db_log_analysis("eda", f"EDA report · {rows_profiled} rows profiled")

    return jsonify({
        "ok":           bool(html),
        "rows_profiled": rows_profiled,
        "warning":      warning,
    })


@workspace_bp.route("/api/eda/report")
@login_required
def api_eda_report():
    from ..storage import _load
    from ..helpers import _get_upload_id

    upload_id = _get_upload_id()
    if not upload_id:
        return Response("upload_id required", status=400)

    html = _load(upload_id, "eda_html")
    if not html:
        return Response("No EDA report generated yet.", status=404)
    theme = request.args.get("theme", "dark")
    if theme == "dark":
        dark_css = """<style>
/* ── DataForge dark override ── */
:root,
[data-bs-theme],
.offcanvas, .offcanvas-start, .offcanvas-end, .offcanvas-top, .offcanvas-bottom {
  --bs-body-bg: #050505;
  --bs-body-color: #e0e0e0;
  --bs-border-color: #1a1a1c;
  --bs-secondary-bg: #0a0a0b;
  --bs-tertiary-bg: #111113;
  --bs-emphasis-color: #ffffff;
  --bs-card-bg: #0a0a0b;
  --bs-card-border-color: #1a1a1c;
}
html, body { background:#050505 !important; color:#e0e0e0 !important; }
.container,.container-fluid,section,article,main,.content,.wrapper,.page-content { background:#050505 !important; color:#e0e0e0 !important; }
.navbar,.navbar-light,.navbar-dark,header,nav[class*="navbar"] { background:#0a0a0b !important; border-bottom:1px solid #1a1a1c !important; }
.navbar-brand,.navbar-nav .nav-link,.nav-link { color:#e0e0e0 !important; }
.card { background:#0a0a0b !important; border-color:#1a1a1c !important; color:#e0e0e0 !important; }
.card-header { background:#111113 !important; border-color:#1a1a1c !important; color:#e0e0e0 !important; }
.card-body   { background:#0a0a0b !important; color:#e0e0e0 !important; }
.nav-tabs .nav-link { color:#888 !important; }
.nav-tabs .nav-link.active { background:#111113 !important; color:#fff !important; }
.tab-content,.tab-pane { background:#0a0a0b !important; color:#e0e0e0 !important; }
table,.table { background:#0a0a0b !important; color:#cccccc !important; }
th { background:#111113 !important; color:#888 !important; border-color:#1a1a1c !important; }
td { border-color:#1a1a1c !important; color:#cccccc !important; }
h1,h2,h3,h4,h5,h6 { color:#fff !important; }
p,span,label,small,.text-muted { color:#aaa !important; }
a { color:#4d79ff !important; }
code,pre { background:#111113 !important; color:#1e9902 !important; }
.alert-info { background:rgba(46,91,255,.1) !important; color:#8ba4ff !important; }
.progress { background:#1a1a1c !important; }
.progress-bar { background:#2E5BFF !important; }
input,select,textarea,.form-control { background:#0d0d0f !important; color:#e0e0e0 !important; border-color:#1a1a1c !important; }
.dropdown-menu { background:#0d0d0f !important; border-color:#1a1a1c !important; }
svg text { fill:#aaa !important; }
svg .bar { fill:#2E5BFF !important; }
.bg-light,.bg-white { background:#0a0a0b !important; }
hr { border-color:#1a1a1c !important; }
.offcanvas { background-color:#0d0d0f !important; color:#e0e0e0 !important; }
.btn-close { filter:invert(1) brightness(.7); }
.accordion-item { background:#0a0a0b !important; border-color:#1a1a1c !important; }
.accordion-button { background:#111113 !important; color:#e0e0e0 !important; }
.list-group-item { background:#0a0a0b !important; border-color:#1a1a1c !important; color:#ccc !important; }
.modal-content { background:#0d0d0f !important; border-color:#1a1a1c !important; color:#e0e0e0 !important; }
</style>"""
        if "</head>" in html:
            html = html.replace("</head>", dark_css + "\n</head>", 1)
        else:
            html = dark_css + html
    return Response(html, mimetype="text/html")


@workspace_bp.route("/api/query", methods=["POST"])
@login_required
def api_query():
    import json
    from ..storage import _save, _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _db_log_analysis,
                           _exists, run_query_pipeline)
    from dataforge.db import db_all, db_update

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded. Please upload a CSV first."}), 400

    body = request.get_json(force=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400

    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")

    metric_context = ""
    if current_user.is_authenticated:
        try:
            user_metrics = db_all("metric_definitions", {"user_id": current_user.id})
            if user_metrics:
                lines = ["Defined business metrics:"]
                for m in user_metrics:
                    l = f"  {m.get('name')} = {m.get('formula')}"
                    if m.get("description"):
                        l += f"  # {m.get('description')}"
                    lines.append(l)
                metric_context = "\n".join(lines)
        except Exception:
            pass

    try:
        result = run_query_pipeline(query, df, metric_context=metric_context)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    history = _load(upload_id, "chat_history") or []
    history.append({"role": "user", "content": query})
    msg = {"role": "assistant", "content": result.get("answer", "")}
    r = result.get("result") or {}
    if r.get("type") in ("bar_chart", "line_chart", "histogram", "scatter_chart"):
        msg["chartData"] = r
    elif r.get("type") == "table":
        msg["tableData"] = r
    if result.get("insight"):
        msg["insight"] = result["insight"]
    history.append(msg)
    _save(upload_id, "chat_history", history)

    if upload_id:
        try:
            db_update("uploads", upload_id, {
                "chat_history": json.dumps(history, default=str)
            })
        except Exception:
            pass

    _db_log_analysis("query", query[:120])
    return jsonify(result)


@workspace_bp.route("/api/transform", methods=["POST"])
@login_required
def api_transform():
    from ..storage import _save, _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _df_profile,
                           _get_filename, _df_to_json_rows, _exists,
                           TRANSFORM_ENABLED, apply_transforms)

    if not TRANSFORM_ENABLED:
        return jsonify({"error": "Transform engine not available"}), 503

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id required"}), 400
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
        return jsonify({"error": "No dataset loaded. Please upload a CSV first."}), 400

    body  = request.get_json(force=True) or {}
    steps = body.get("steps", [])
    reset = bool(body.get("reset", False))

    if reset:
        _save(upload_id, "df_transform", None)
        df_base = _load(upload_id, "df_clean")
        if df_base is None:
            df_base = _load(upload_id, "df_raw")
        if df_base is None:
            return jsonify({"error": "No dataset found to reset to"}), 400
        profile = _df_profile(df_base, _get_filename(upload_id))
        return jsonify({"ok": True, "reset": True, "profile": profile})

    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")

    try:
        result = apply_transforms(df, steps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _save(upload_id, "df_transform", result.df)
    profile   = _df_profile(result.df, _get_filename(upload_id))
    preview   = _df_to_json_rows(result.df, 500)

    return jsonify({
        "ok":      True,
        "profile": profile,
        "preview": preview,
        "result":  result.to_dict(),
        "errors":  result.errors,
    })


@workspace_bp.route("/api/transform/preview", methods=["GET"])
@login_required
def api_transform_preview():
    from flask import current_app
    from ..storage import _load
    from ..helpers import _get_upload_id, _df_to_json_rows, _upath

    upload_id = _get_upload_id()
    if not upload_id:
        return jsonify({"error": "upload_id parameter is required"}), 400
    p = _upath(upload_id, "df_transform").with_suffix('.parquet')
    if not p.exists(): p = _upath(upload_id, "df_clean").with_suffix('.parquet')
    if not p.exists(): p = _upath(upload_id, "df_raw").with_suffix('.parquet')

    if p.exists():
        try:
            import duckdb
            total_rows = duckdb.execute(f"SELECT COUNT(*) AS total_rows FROM '{str(p)}'").fetchone()[0]
            preview_df = duckdb.execute(f"SELECT * FROM '{str(p)}' LIMIT 500").df()
            payload = _df_to_json_rows(preview_df, 500)
            payload["loaded"] = len(preview_df)
            payload["total"] = int(total_rows)
            payload["preview_only"] = int(total_rows) > len(preview_df)
            return jsonify(payload)
        except Exception as e:
            current_app.logger.warning("DuckDB transform preview failed: %s", e)

    df = _load(upload_id, "df_transform") or _load(upload_id, "df_clean") or _load(upload_id, "df_raw")
    if df is None:
        return jsonify({"error": "No dataset loaded"}), 400
    return jsonify(_df_to_json_rows(df, 500))
