"""
routes/workspace.py — Workspace Blueprint
Handles workspace page, state, preview, clean, EDA, AI query, and transform.
"""
import io
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
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


def _inject_eda_view_theme(html: str, theme: str = "dark", print_mode: bool = False) -> str:
    """Apply final DataForge theming over ydata/pandas EDA HTML."""
    light_themes = {"light", "cupcake", "retro", "solarized", "lavender", "matcha"}
    theme = (theme or "dark").lower()
    if print_mode:
        theme = "cupcake"
    bs_theme = "light" if theme in light_themes else "dark"

    palettes = {
        "dark": {
            "bg": "#050505", "surface": "#0a0a0b", "surface2": "#111113",
            "text": "#e5e7eb", "muted": "#9ca3af", "border": "#27272a", "accent": "#2E5BFF",
        },
        "dracula": {
            "bg": "#282a36", "surface": "#1e1f29", "surface2": "#343746",
            "text": "#f8f8f2", "muted": "#c7c7bd", "border": "#44475a", "accent": "#bd93f9",
        },
        "slate": {
            "bg": "#1e222b", "surface": "#252a34", "surface2": "#303643",
            "text": "#f1f5f9", "muted": "#b6c2d2", "border": "#3b4352", "accent": "#38bdf8",
        },
        "emerald": {
            "bg": "#141e1b", "surface": "#1b2824", "surface2": "#24372f",
            "text": "#e6f4f1", "muted": "#a7c5bb", "border": "#2f493f", "accent": "#10b981",
        },
        "nord": {
            "bg": "#2e3440", "surface": "#3b4252", "surface2": "#434c5e",
            "text": "#eceff4", "muted": "#c4ceda", "border": "#4c566a", "accent": "#88c0d0",
        },
        "luxury": {
            "bg": "#09090b", "surface": "#18181b", "surface2": "#27272a",
            "text": "#f4f4f5", "muted": "#b7b7bf", "border": "#3f3f46", "accent": "#d4af37",
        },
        "light": {
            "bg": "#f8fafc", "surface": "#ffffff", "surface2": "#f1f5f9",
            "text": "#0f172a", "muted": "#475569", "border": "#e2e8f0", "accent": "#4f46e5",
        },
        "cupcake": {
            "bg": "#fafaf9", "surface": "#ffffff", "surface2": "#f5f5f4",
            "text": "#291334", "muted": "#8d779b", "border": "#e7e5e4", "accent": "#ec4899",
        },
        "solarized": {
            "bg": "#fdf6e3", "surface": "#eee8d5", "surface2": "#decdaf",
            "text": "#002b36", "muted": "#586e75", "border": "#d5c4a1", "accent": "#2aa198",
        },
        "lavender": {
            "bg": "#f5f3ff", "surface": "#ffffff", "surface2": "#e9d5ff",
            "text": "#1e1b4b", "muted": "#5b21b6", "border": "#a78bfa", "accent": "#7c3aed",
        },
        "matcha": {
            "bg": "#f4f8f5", "surface": "#ffffff", "surface2": "#d1e7dd",
            "text": "#0f291b", "muted": "#2d6a4f", "border": "#74a88e", "accent": "#15803d",
        },
        "retro": {
            "bg": "#ece3ca", "surface": "#fff8e8", "surface2": "#e4d8b4",
            "text": "#282425", "muted": "#6f675b", "border": "#c8b98d", "accent": "#ef9995",
        },
    }
    p = palettes.get(theme, palettes["dark"])
    print_css = """
@page { size: A4; margin: 14mm; }
body { padding: 0 !important; }
.navbar, nav, .offcanvas, .modal, .btn, button { display: none !important; }
.container, .container-fluid { max-width: none !important; width: 100% !important; padding: 0 !important; }
.card, section, article, table, pre { break-inside: avoid; page-break-inside: avoid; }
a[href]::after { content: ""; }
""" if print_mode else ""

    css = f"""
<style id="df-eda-view-theme">
html {{
  color-scheme: {bs_theme};
  background: {p["bg"]} !important;
}}
html, body {{
  min-height: 100%;
  background: {p["bg"]} !important;
  color: {p["text"]} !important;
}}
:root, [data-bs-theme] {{
  --bs-body-bg: {p["bg"]};
  --bs-body-color: {p["text"]};
  --bs-emphasis-color: {p["text"]};
  --bs-secondary-color: {p["muted"]};
  --bs-tertiary-color: {p["muted"]};
  --bs-border-color: {p["border"]};
  --bs-card-bg: {p["surface"]};
  --bs-card-border-color: {p["border"]};
  --bs-secondary-bg: {p["surface2"]};
  --bs-tertiary-bg: {p["surface2"]};
  --bs-link-color: {p["accent"]};
  --bs-link-hover-color: {p["accent"]};
}}
body, .page, .wrapper, .content, main, section, article,
.container, .container-fluid, .row, .col, [class*="container"] {{
  background-color: {p["bg"]} !important;
  color: {p["text"]} !important;
}}
.card, .card-body, .card-header, .card-footer, .list-group-item,
.accordion-item, .accordion-button, .dropdown-menu, .modal-content,
.tab-content, .tab-pane, .report-section, .section, .well, .panel {{
  background-color: {p["surface"]} !important;
  color: {p["text"]} !important;
  border-color: {p["border"]} !important;
}}
.card-header, thead, th, .accordion-button:not(.collapsed) {{
  background-color: {p["surface2"]} !important;
}}
.navbar, .navbar-light, .navbar-dark, header, nav[class*="navbar"] {{
  background-color: {p["surface"]} !important;
  border-color: {p["border"]} !important;
}}
h1,h2,h3,h4,h5,h6, .navbar-brand, .nav-link, label, strong {{
  color: {p["text"]} !important;
}}
p, span, small, .text-muted, .text-secondary, .form-text, figcaption {{
  color: {p["muted"]} !important;
}}
a, a.nav-link, .btn-link {{
  color: {p["accent"]} !important;
}}
table, .table {{
  background-color: {p["surface"]} !important;
  color: {p["text"]} !important;
  border-color: {p["border"]} !important;
}}
td, th, .table>:not(caption)>*>* {{
  background-color: transparent !important;
  color: {p["text"]} !important;
  border-color: {p["border"]} !important;
  vertical-align: middle !important;
}}
tbody tr:hover td {{
  background-color: {p["surface2"]} !important;
}}
pre, code, kbd, samp {{
  background-color: {p["surface2"]} !important;
  color: {p["text"]} !important;
  border-color: {p["border"]} !important;
}}
input, select, textarea, .form-control, .form-select {{
  background-color: {p["surface"]} !important;
  color: {p["text"]} !important;
  border-color: {p["border"]} !important;
}}
.alert, .badge, .progress, .progress-bar {{
  border-color: {p["border"]} !important;
}}
svg text, svg tspan {{
  fill: {p["muted"]} !important;
}}
svg, canvas, img {{
  max-width: 100% !important;
}}
.table-responsive {{
  overflow-x: auto !important;
}}
{print_css}
</style>
"""
    if re.search(r"<html\b", html, flags=re.IGNORECASE):
        def _html_open(match):
            attrs = re.sub(r'\sdata-(?:bs-)?theme="[^"]*"', "", match.group(1), flags=re.IGNORECASE)
            return f'<html{attrs} data-theme="{theme}" data-bs-theme="{bs_theme}">'

        html = re.sub(r"<html\b([^>]*)>", _html_open, html, count=1, flags=re.IGNORECASE)
    if "</head>" in html:
        return html.replace("</head>", css + "\n</head>", 1)
    return css + html


def _render_pdf_with_browser(html: str) -> bytes | None:
    """Render HTML to PDF using local Chromium/Edge when available."""
    browser = (
        shutil.which("chrome")
        or shutil.which("msedge")
        or shutil.which("chromium")
        or next(
            (
                p for p in [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                ]
                if Path(p).exists()
            ),
            None,
        )
    )
    if not browser:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "eda_report.html"
        pdf_path = tmp_path / "eda_report.pdf"
        user_data = tmp_path / "browser-profile"
        html_path.write_text(html, encoding="utf-8")
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            f"--user-data-dir={user_data}",
            f"--print-to-pdf={pdf_path}",
            str(html_path),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        except Exception:
            return None
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return pdf_path.read_bytes()
    return None


@workspace_bp.route("/workspace")
@login_required
def workspace():
    from ..helpers import gemini_available
    upload_id = request.args.get("upload_id", type=int)
    if not upload_id:
        from flask import session
        upload_id = session.get("last_upload_id")
        if upload_id:
            from flask import redirect, url_for
            return redirect(url_for("workspace_bp.workspace", upload_id=upload_id))

        from dataforge.db import db_all
        uploads = db_all("uploads", {"user_id": current_user.id}, order_by="uploaded_at", desc=True, limit=1)
        if uploads:
            from flask import redirect, url_for
            return redirect(url_for("workspace_bp.workspace", upload_id=uploads[0]["id"]))

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
                           gemini_available, _exists)
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

    from datetime import datetime

    # Migrate and structure chat history
    chat_data = chat_history
    if isinstance(chat_data, list):
        if len(chat_data) > 0:
            default_session = {
                "id": "default",
                "name": "Previous Chat",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": chat_data
            }
            chat_data = {
                "active_session_id": "default",
                "sessions": [default_session]
            }
        else:
            chat_data = {
                "active_session_id": "default",
                "sessions": [{
                    "id": "default",
                    "name": "New Chat",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "messages": []
                }]
            }

    if not isinstance(chat_data, dict) or "sessions" not in chat_data or not chat_data.get("sessions"):
        chat_data = {
            "active_session_id": "default",
            "sessions": [{
                "id": "default",
                "name": "New Chat",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": []
            }]
        }
        _save(upload_id, "chat_history", chat_data)

    active_session_id = chat_data.get("active_session_id", "default")
    chat_sessions = chat_data.get("sessions", [])
    active_history = next((s["messages"] for s in chat_sessions if s["id"] == active_session_id), [])
    ai_consent = bool(_load(upload_id, "ai_consent"))

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
    
    # Always get source_type from DB upload record
    try:
        up = db_get("uploads", upload_id)
        if up:
            src = up.get("source_type", "csv") or "csv"
            reupload_source_type = src
            up_filename = up.get("filename", "")

            if df_raw is None and df_clean is None:
                # Data needs to be reloaded
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
        "has_biz_report":    _exists(upload_id, "data_report_html"),
        "profile":           profile,
        "clean_profile":     clean_profile,
        "columns":           profile.get("columns", []),
        "clean_meta":        clean_meta,
        "automl_meta":       automl_meta,
        "chat_history":      active_history,
        "chat_sessions":     chat_sessions,
        "active_session_id": active_session_id,
        "ai_consent":        ai_consent,
        "filename":          _get_filename(upload_id),
        "gemini_ok":         gemini_available(),
        "needs_reupload":      needs_reupload,
        "reupload_filename":   reupload_filename,
        "reupload_message":    reupload_message,
        "source_type":         reupload_source_type,
    }
    return jsonify(state)


@workspace_bp.route("/api/workspace/sync-sheets", methods=["POST"])
@login_required
def api_workspace_sync_sheets():
    import pandas as pd
    from ..storage import _save, _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _df_profile,
                           _persist, _upath)
    from dataforge.db import db_get, db_update

    upload_id = _get_upload_id()
    if not upload_id:
        return jsonify({"error": "upload_id parameter is required"}), 400
    up, err = _get_upload_or_403(upload_id)
    if err:
        return err

    up_row = db_get("uploads", upload_id)
    if not up_row:
        return jsonify({"error": "Upload record not found"}), 404

    src_type = up_row.get("source_type", "csv")
    if src_type != "sheets":
        return jsonify({"error": "This project was not loaded from Google Sheets"}), 400

    storage_path = up_row.get("storage_path") or ""
    if not storage_path:
        return jsonify({"error": "Google Sheets configuration not found for this project. Re-connect the sheet once, then sync will work normally."}), 400

    try:
        src_cfg = json.loads(storage_path)
    except Exception:
        return jsonify({
            "error": (
                "This sheet was saved with an older storage format and its Google Sheets URL is no longer available. "
                "Re-connect the Google Sheet once; future syncs will preserve the sheet configuration."
            )
        }), 400

    sheet_id = (src_cfg.get("sheet_id") or "").strip()
    if not sheet_id and src_cfg.get("url"):
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", src_cfg.get("url", ""))
        if m:
            sheet_id = m.group(1)
    if not sheet_id:
        return jsonify({"error": "Sheet ID not found in Google Sheets configuration. Re-connect the sheet once, then sync will work normally."}), 400

    try:
        from dataforge.sheets_connector import SheetsConnector
        conn = SheetsConnector()
        df = conn.load_public(sheet_id)
    except Exception as e:
        return jsonify({"error": f"Could not sync with Google Sheets: {e}"}), 400

    filename = up_row.get("filename", "sheet.csv")
    profile = _df_profile(df, filename)

    for key in ("df_clean", "clean_meta", "automl_meta", "eda_html"):
        p = _upath(upload_id, key)
        for suffix in (".parquet", ".json", ".joblib", ".html", ""):
            f = p.with_suffix(suffix) if suffix else p
            if f.exists() and not f.is_dir():
                try:
                    f.unlink()
                except Exception:
                    pass

    try:
        _save(upload_id, "df_raw", df)
        _save(upload_id, "profile", profile)
        _persist(upload_id, "df_raw", df)
    except Exception as e:
        return jsonify({"error": f"Synced from Google Sheets, but failed to save the refreshed dataset: {e}"}), 500

    try:
        db_update("uploads", upload_id, {"storage_path": json.dumps(src_cfg)})
    except Exception:
        pass

    try:
        db_update("uploads", upload_id, {
            "rows": profile.get("rows", 0),
            "cols": profile.get("cols", 0),
            "missing_pct": profile.get("missing_pct", 0.0),
        })
    except Exception:
        pass

    return jsonify({"ok": True, "profile": profile})


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
    from flask import current_app
    from ..storage import _save, _load
    from ..helpers import (_get_upload_id, _get_upload_or_403, _exists,
                           _tasks, _run_task_sync, _db_log_analysis,
                           _broker_available, SYNC_FALLBACK_ENABLED)
    from dataforge.db import db_first, db_insert

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

    # Use sync execution when no Celery worker is alive (local mode — Redis/Celery optional)
    if not _broker_available():
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (_, _, task_run_eda, *_) = _tasks()
            _run_task_sync(task_run_eda, [upload_id, current_user.id, minimal, sample_n])
            _db_log_analysis("eda", "completed sync (no worker)")
            return jsonify({"queued": False, "sync": True, "ok": True}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for EDA: %s", se)
            return jsonify({"error": f"EDA failed: {se}"}), 500

    existing = db_first("jobs", {"upload_id": upload_id, "type": "eda", "status": "started"})
    if existing:
        return jsonify({"task_id": existing.get("id"), "queued": False}), 200

    try:
        (_, _, task_run_eda, *_) = _tasks()
        job = task_run_eda.apply_async(args=[upload_id, current_user.id, minimal, sample_n])
        db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "eda"})
        _db_log_analysis("eda", "queued async")
        return jsonify({"task_id": job.id, "queued": True}), 202
    except Exception as e:
        current_app.logger.error("Celery task dispatch failed: %s", e)
        if not SYNC_FALLBACK_ENABLED:
            return jsonify({"error": "Background task system unavailable."}), 503
        try:
            (_, _, task_run_eda, *_) = _tasks()
            _run_task_sync(task_run_eda, [upload_id, current_user.id, minimal, sample_n])
            _db_log_analysis("eda", "completed sync fallback")
            return jsonify({"queued": False, "sync": True, "ok": True}), 200
        except Exception as se:
            current_app.logger.exception("Sync fallback failed for EDA: %s", se)
            return jsonify({"error": f"EDA failed: {se}"}), 500


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
    fmt = (request.args.get("format") or "html").lower()
    force_download = request.args.get("download") in {"1", "true", "yes"}
    wants_pdf = fmt == "pdf"
    print_mode = force_download or wants_pdf
    theme = request.args.get("theme") or ("cupcake" if print_mode else "dark")
    html = _inject_eda_view_theme(html, theme=theme, print_mode=print_mode)

    if wants_pdf:
        try:
            from weasyprint import HTML
            pdf = HTML(string=html, base_url=request.url_root).write_pdf()
            return Response(
                pdf,
                mimetype="application/pdf",
                headers={"Content-Disposition": "attachment; filename=dataforge_eda_report_cupcake.pdf"},
            )
        except Exception:
            pdf = _render_pdf_with_browser(html)
            if pdf:
                return Response(
                    pdf,
                    mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=dataforge_eda_report_cupcake.pdf"},
                )
            # Keep the download useful even when no PDF renderer is installed.
            force_download = True

    headers = {}
    if force_download:
        headers["Content-Disposition"] = "attachment; filename=dataforge_eda_report.html"
    return Response(html, mimetype="text/html", headers=headers)
# ── DATA REPORT (Gemini Business Analyst Report) ──────────────────────────────

def _build_data_report_html(filename: str, narrative: str, stats: dict, charts: list, insights: list, df_preview_html: str) -> str:
    """Wrap Gemini narrative + stats + graphs + insights into a premium visually interactive HTML report."""
    import re as _re
    from datetime import datetime
    import math

    def _md_to_html(md: str) -> str:
        md = _re.sub(r"^#{1}\s+(.+)$", r"<h1>\1</h1>", md, flags=_re.MULTILINE)
        md = _re.sub(r"^#{2}\s+(.+)$", r"<h2>\1</h2>", md, flags=_re.MULTILINE)
        md = _re.sub(r"^#{3}\s+(.+)$", r"<h3>\1</h3>", md, flags=_re.MULTILINE)
        md = _re.sub(r"^#{4,6}\s+(.+)$", r"<h4>\1</h4>", md, flags=_re.MULTILINE)
        md = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md)
        md = _re.sub(r"\*(.+?)\*", r"<em>\1</em>", md)
        md = _re.sub(r"`([^`]+)`", r"<code>\1</code>", md)
        md = _re.sub(r"^[\*\-]\s+(.+)$", r"<li>\1</li>", md, flags=_re.MULTILINE)
        md = _re.sub(r"(<li>.*?</li>\n?)+", lambda m: f"<ul>{m.group(0)}</ul>", md, flags=_re.DOTALL)
        md = _re.sub(r"^\d+\.\s+(.+)$", r"<li>\1</li>", md, flags=_re.MULTILINE)
        md = _re.sub(r"\n\n+", "</p><p>", md)
        return f"<p>{md}</p>"

    html_narrative = _md_to_html(narrative)

    # ── SVG Chart Renderer inside the report ──────────────────────────────
    def _format_val_short(val: float) -> str:
        try:
            val = float(val)
        except (TypeError, ValueError):
            return str(val)
        abs_val = abs(val)
        if abs_val >= 1_000_000:
            return f"{val/1_000_000:.1f}M"
        elif abs_val >= 1_000:
            return f"{val/1_000:.1f}K"
        elif val == int(val):
            return str(int(val))
        else:
            return f"{val:.2f}"

    def _render_chart_as_svg(chart: dict) -> str:
        chart_type = chart.get("type", "bar")
        title = chart.get("title", "")
        labels = chart.get("labels", [])
        values = chart.get("values", [])
        x_label = chart.get("x_label", "")
        y_label = chart.get("y_label", "")
        
        # SVG dimensions
        width = 600
        height = 320
        padding_left = 65
        padding_right = 30
        padding_top = 40
        padding_bottom = 50
        
        plot_width = width - padding_left - padding_right
        plot_height = height - padding_top - padding_bottom
        
        svg = f'<svg viewBox="0 0 {width} {height}" class="report-svg-chart" style="width:100%; height:auto; background:#18181b; border-radius:12px; margin: 0; border: 1px solid #27272a;" xmlns="http://www.w3.org/2000/svg">'
        
        # Title
        svg += f'<text x="20" y="24" fill="#f4f4f5" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="12" font-weight="700">{title}</text>'
        
        if chart_type in ("bar", "line", "area", "histogram"):
            if not values or not isinstance(values, list):
                svg += f'<text x="{width/2}" y="{height/2}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" text-anchor="middle">No data available</text></svg>'
                return svg
            
            try:
                numeric_vals = [float(v) for v in values]
            except Exception:
                numeric_vals = []
                
            if not numeric_vals:
                svg += f'<text x="{width/2}" y="{height/2}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" text-anchor="middle">No numeric data</text></svg>'
                return svg
                
            max_val = max(numeric_vals) if numeric_vals else 1.0
            
            if max_val <= 0:
                max_val = 1.0
                
            magnitude = 10 ** math.floor(math.log10(max_val)) if max_val > 0 else 1
            if magnitude == 0:
                magnitude = 1
            nice_max = math.ceil(max_val / (magnitude / 2)) * (magnitude / 2)
            if nice_max == 0:
                nice_max = 1.0
                
            y_ticks = 4
            for i in range(y_ticks + 1):
                tick_val = nice_max * (i / y_ticks)
                y_pos = padding_top + plot_height * (1 - (i / y_ticks))
                svg += f'<line x1="{padding_left}" y1="{y_pos}" x2="{width - padding_right}" y2="{y_pos}" stroke="#27272a" stroke-dasharray="3,3" />'
                lbl = _format_val_short(tick_val)
                svg += f'<text x="{padding_left - 10}" y="{y_pos + 3}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8" text-anchor="end">{lbl}</text>'
                
            svg += f'<line x1="{padding_left}" y1="{padding_top + plot_height}" x2="{width - padding_right}" y2="{padding_top + plot_height}" stroke="#3f3f46" />'
            
            num_items = len(values)
            col_width = plot_width / max(1, num_items)
            
            if chart_type in ("bar", "histogram"):
                bar_gap = max(2, min(12, int(col_width * 0.2)))
                for idx, val in enumerate(values):
                    val_f = float(val)
                    bar_h = (val_f / nice_max) * plot_height
                    x_pos = padding_left + idx * col_width + bar_gap
                    y_pos = padding_top + plot_height - bar_h
                    w = col_width - 2 * bar_gap
                    h = max(2, bar_h)
                    
                    svg += f'<rect x="{x_pos}" y="{y_pos}" width="{w}" height="{h}" fill="#2E5BFF" rx="3" opacity="0.85" />'
                    
                    if num_items <= 12 and h > 15:
                        svg += f'<text x="{x_pos + w/2}" y="{y_pos - 4}" fill="#a1a1aa" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8" text-anchor="middle">{_format_val_short(val_f)}</text>'
                        
                    if num_items <= 15 or idx % (num_items // 8 or 1) == 0:
                        lbl_text = str(labels[idx]) if idx < len(labels) else ""
                        if len(lbl_text) > 10:
                            lbl_text = lbl_text[:8] + ".."
                        svg += f'<text x="{x_pos + w/2}" y="{padding_top + plot_height + 14}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8" text-anchor="middle" transform="rotate(-15, {x_pos + w/2}, {padding_top + plot_height + 14})">{lbl_text}</text>'
                        
            elif chart_type in ("line", "area"):
                points = []
                for idx, val in enumerate(values):
                    val_f = float(val)
                    x_pos = padding_left + idx * col_width + col_width/2
                    y_pos = padding_top + plot_height - (val_f / nice_max) * plot_height
                    points.append((x_pos, y_pos))
                    
                    if num_items <= 15 or idx % (num_items // 8 or 1) == 0:
                        lbl_text = str(labels[idx]) if idx < len(labels) else ""
                        if len(lbl_text) > 10:
                            lbl_text = lbl_text[:8] + ".."
                        svg += f'<text x="{x_pos}" y="{padding_top + plot_height + 14}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8" text-anchor="middle" transform="rotate(-15, {x_pos}, {padding_top + plot_height + 14})">{lbl_text}</text>'
                        
                if points:
                    line_d = "M " + " L ".join(f"{pt[0]},{pt[1]}" for pt in points)
                    if chart_type == "area":
                        area_d = line_d + f" L {points[-1][0]},{padding_top + plot_height} L {points[0][0]},{padding_top + plot_height} Z"
                        svg += f'<path d="{area_d}" fill="url(#areaGrad)" opacity="0.15" />'
                    svg += f'<path d="{line_d}" fill="none" stroke="#2E5BFF" stroke-width="2" />'
                    
                    if num_items <= 30:
                        for pt in points:
                            svg += f'<circle cx="{pt[0]}" cy="{pt[1]}" r="3" fill="#09090b" stroke="#2E5BFF" stroke-width="1.5" />'
                            
                svg += """
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#2E5BFF" />
                    <stop offset="100%" stop-color="#2E5BFF" stop-opacity="0" />
                  </linearGradient>
                </defs>
                """
                
        elif chart_type in ("pie", "doughnut"):
            if not values:
                svg += f'<text x="{width/2}" y="{height/2}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" text-anchor="middle">No data</text></svg>'
                return svg
                
            total = sum([float(v) for v in values])
            if total == 0:
                total = 1.0
                
            center_x = width * 0.38
            center_y = height * 0.52
            radius = min(width, height) * 0.34
            
            colors = ["#2E5BFF", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#3B82F6", "#F97316", "#06B6D4", "#14B8A6"]
            current_angle = -math.pi / 2
            
            legend_y = padding_top + 10
            legend_x = width * 0.70
            
            for idx, val in enumerate(values):
                val_f = float(val)
                pct = val_f / total
                angle = pct * 2 * math.pi
                
                x1 = center_x + radius * math.cos(current_angle)
                y1 = center_y + radius * math.sin(current_angle)
                x2 = center_x + radius * math.cos(current_angle + angle)
                y2 = center_y + radius * math.sin(current_angle + angle)
                
                large_arc = 1 if angle > math.pi else 0
                color = colors[idx % len(colors)]
                
                if pct < 0.999:
                    if chart_type == "doughnut":
                        inner_radius = radius * 0.55
                        ix1 = center_x + inner_radius * math.cos(current_angle)
                        iy1 = center_y + inner_radius * math.sin(current_angle)
                        ix2 = center_x + inner_radius * math.cos(current_angle + angle)
                        iy2 = center_y + inner_radius * math.sin(current_angle + angle)
                        d = f"M {x1} {y1} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} L {ix2} {iy2} A {inner_radius} {inner_radius} 0 {large_arc} 0 {ix1} {iy1} Z"
                    else:
                        d = f"M {center_x} {center_y} L {x1} {y1} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} Z"
                    svg += f'<path d="{d}" fill="{color}" stroke="#18181b" stroke-width="1.5" opacity="0.85" />'
                else:
                    if chart_type == "doughnut":
                        svg += f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="{color}" stroke-width="{radius * 0.45}" opacity="0.85" />'
                    else:
                        svg += f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="{color}" opacity="0.85" />'
                
                current_angle += angle
                
                if idx < 8:
                    lbl = str(labels[idx]) if idx < len(labels) else ""
                    if len(lbl) > 14:
                        lbl = lbl[:12] + ".."
                    svg += f'<rect x="{legend_x}" y="{legend_y}" width="10" height="10" fill="{color}" rx="2" />'
                    svg += f'<text x="{legend_x + 16}" y="{legend_y + 9}" fill="#a1a1aa" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8.5" text-anchor="start">{lbl} ({pct*100:.1f}%)</text>'
                    legend_y += 18
                    
            if len(values) > 8:
                svg += f'<text x="{legend_x}" y="{legend_y + 9}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8.5">And {len(values) - 8} more...</text>'
                
        elif chart_type == "scatter":
            if not values or not isinstance(values, list):
                svg += f'<text x="{width/2}" y="{height/2}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" text-anchor="middle">No data</text></svg>'
                return svg
                
            x_vals = [float(pt.get("x", 0)) for pt in values if pt.get("x") is not None]
            y_vals = [float(pt.get("y", 0)) for pt in values if pt.get("y") is not None]
            
            if not x_vals or not y_vals:
                svg += f'<text x="{width/2}" y="{height/2}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" text-anchor="middle">No scatter points</text></svg>'
                return svg
                
            min_x, max_x = min(x_vals), max(x_vals)
            min_y, max_y = min(y_vals), max(y_vals)
            
            range_x = (max_x - min_x) if max_x != min_x else 1.0
            range_y = (max_y - min_y) if max_y != min_y else 1.0
            
            min_x -= range_x * 0.05
            max_x += range_x * 0.05
            min_y -= range_y * 0.05
            max_y += range_y * 0.05
            range_x = max_x - min_x
            range_y = max_y - min_y
            
            for i in range(5):
                grid_x_val = min_x + range_x * (i / 4)
                grid_x_pos = padding_left + plot_width * (i / 4)
                svg += f'<line x1="{grid_x_pos}" y1="{padding_top}" x2="{grid_x_pos}" y2="{padding_top + plot_height}" stroke="#27272a" stroke-dasharray="2,2" />'
                svg += f'<text x="{grid_x_pos}" y="{padding_top + plot_height + 12}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="7.5" text-anchor="middle">{_format_val_short(grid_x_val)}</text>'
                
                grid_y_val = min_y + range_y * (i / 4)
                grid_y_pos = padding_top + plot_height * (1 - (i / 4))
                svg += f'<line x1="{padding_left}" y1="{grid_y_pos}" x2="{width - padding_right}" y2="{grid_y_pos}" stroke="#27272a" stroke-dasharray="2,2" />'
                svg += f'<text x="{padding_left - 10}" y="{grid_y_pos + 3}" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="7.5" text-anchor="end">{_format_val_short(grid_y_val)}</text>'
                
            svg += f'<line x1="{padding_left}" y1="{padding_top + plot_height}" x2="{width - padding_right}" y2="{padding_top + plot_height}" stroke="#3f3f46" />'
            svg += f'<line x1="{padding_left}" y1="{padding_top}" x2="{padding_left}" y2="{padding_top + plot_height}" stroke="#3f3f46" />'
            
            svg += f'<text x="{width/2}" y="{height - 6}" fill="#a1a1aa" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8.5" text-anchor="middle">{x_label}</text>'
            svg += f'<text x="12" y="{height/2}" fill="#a1a1aa" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="8.5" text-anchor="middle" transform="rotate(-90, 12, {height/2})">{y_label}</text>'
            
            for pt in values:
                cx = padding_left + ((float(pt.get("x", 0)) - min_x) / range_x) * plot_width
                cy = padding_top + plot_height - ((float(pt.get("y", 0)) - min_y) / range_y) * plot_height
                svg += f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="#2E5BFF" opacity="0.6" />'
                
        svg += "</svg>"
        return svg

    # Generate charts HTML grid
    charts_html = ""
    if charts:
        charts_html += '<div class="charts-grid">'
        for idx, ch in enumerate(charts):
            title = ch.get("title", f"Analysis Chart {idx+1}")
            svg_content = _render_chart_as_svg(ch)
            charts_html += f"""
            <div class="chart-card">
              <div class="chart-card-header">
                <span class="chart-card-icon">📈</span>
                <span class="chart-card-title">{title}</span>
              </div>
              <div class="chart-card-body">
                {svg_content}
              </div>
            </div>"""
        charts_html += '</div>'
    else:
        charts_html = '<div class="empty-state"><p>No visual dashboard graphs compiled. Ensure the dataset contains columns suitable for visualization.</p></div>'

    # Generate insights HTML grid
    insights_html = ""
    if insights:
        insights_html += '<div class="insights-grid">'
        for idx, ins in enumerate(insights):
            title = ins.get("title", f"Insight {idx+1}")
            desc = ins.get("description", "")
            importance = ins.get("importance", 0.5)
            metric_col = ins.get("metric", "")
            chart_type = ins.get("chart_type", "")
            
            if importance > 0.7:
                badge_lbl = "Critical Attention"
                badge_cls = "badge-danger"
            elif importance > 0.4:
                badge_lbl = "Important Insight"
                badge_cls = "badge-warning"
            else:
                badge_lbl = "Standard Observation"
                badge_cls = "badge-info"
                
            insights_html += f"""
            <div class="insight-card">
              <div class="insight-card-top">
                <span class="insight-number">#0{idx+1}</span>
                <span class="insight-badge {badge_cls}">{badge_lbl}</span>
              </div>
              <h3 class="insight-title">{title}</h3>
              <p class="insight-desc">{desc}</p>
              <div class="insight-meta">
                {f'<span class="meta-tag">🎯 Metric: <strong>{metric_col}</strong></span>' if metric_col else ''}
                {f'<span class="meta-tag">📊 Visual: <strong>{chart_type}</strong></span>' if chart_type else ''}
              </div>
            </div>"""
        insights_html += '</div>'
    else:
        insights_html = """
        <div class="empty-state">
          <p>No algorithmic insights run yet.</p>
          <p class="small">Click "Run Insights Analysis" on the Insights dashboard page to generate advanced statistical indicators, which will populate this section in future reports.</p>
        </div>"""

    # Generate stats table rows
    stat_rows = ""
    for k, v in stats.items():
        stat_rows += f"<tr><td>{k}</td><td><strong>{v}</strong></td></tr>"

    date_str = datetime.now().strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Dataforge Business Intelligence Report: {filename}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Outfit',-apple-system,BlinkMacSystemFont,sans-serif;background:#09090b;color:#e4e4e7;line-height:1.6;font-size:15px;padding-bottom:60px;}}
  
  /* Layout */
  .page{{max-width:1100px;margin:0 auto;padding:40px 24px;}}
  
  /* Header Cover Card */
  .report-header{{
    background:linear-gradient(135deg, #18181b 0%, #09090b 100%);
    border:1px solid #27272a;
    border-radius:16px;
    padding:40px;
    margin-bottom:30px;
    position:relative;
    overflow:hidden;
  }}
  .report-header::after{{
    content:"";
    position:absolute;
    top:-50%;
    right:-20%;
    width:350px;
    height:350px;
    background:radial-gradient(circle, rgba(46,91,255,0.15) 0%, rgba(0,0,0,0) 70%);
    border-radius:50%;
    pointer-events:none;
  }}
  .header-tag{{
    display:inline-block;
    font-size:10px;
    font-weight:800;
    letter-spacing:0.18em;
    text-transform:uppercase;
    color:#2E5BFF;
    margin-bottom:12px;
    background:rgba(46,91,255,0.08);
    padding:4px 10px;
    border-radius:100px;
    border:1px solid rgba(46,91,255,0.15);
  }}
  .report-header h1{{font-size:2.2rem;font-weight:900;color:#f4f4f5;line-height:1.2;letter-spacing:-0.02em;margin-bottom:12px;}}
  .report-meta{{display:flex;flex-wrap:wrap;gap:20px;font-size:0.85rem;color:#a1a1aa;margin-top:10px;}}
  .report-meta span{{display:flex;align-items:center;gap:6px;}}
  
  /* Tabs Navigation Styles */
  .tabs-container{{margin-top:20px;}}
  .tab-radio{{display:none;}}
  
  .tab-labels-row{{
    display:flex;
    flex-wrap:wrap;
    gap:8px;
    margin-bottom:24px;
    border-bottom:1px solid #27272a;
    padding-bottom:12px;
  }}
  .tab-label{{
    padding:10px 20px;
    border-radius:8px;
    font-size:0.88rem;
    font-weight:600;
    color:#a1a1aa;
    cursor:pointer;
    border:1px solid transparent;
    transition:all 0.25s ease;
    display:flex;
    align-items:center;
    gap:8px;
  }}
  .tab-label:hover{{
    background:#18181b;
    color:#f4f4f5;
  }}
  
  /* Active Tab Indicator */
  #tab-nav-narrative:checked ~ .tab-labels-row .label-narrative,
  #tab-nav-visuals:checked ~ .tab-labels-row .label-visuals,
  #tab-nav-insights:checked ~ .tab-labels-row .label-insights,
  #tab-nav-profile:checked ~ .tab-labels-row .label-profile{{
    background:rgba(46,91,255,0.12);
    color:#f4f4f5;
    border-color:rgba(46,91,255,0.3);
    box-shadow:0 4px 12px rgba(0,0,0,0.1);
  }}
  
  /* Panel Toggle visibility */
  .tab-panel{{display:none;animation:fadeIn 0.3s ease-in-out;}}
  #tab-nav-narrative:checked ~ .tab-panels .panel-narrative{{display:block;}}
  #tab-nav-visuals:checked ~ .tab-panels .panel-visuals{{display:block;}}
  #tab-nav-insights:checked ~ .tab-panels .panel-insights{{display:block;}}
  #tab-nav-profile:checked ~ .tab-panels .panel-profile{{display:block;}}
  
  @keyframes fadeIn{{
    from{{opacity:0;transform:translateY(4px);}}
    to{{opacity:1;transform:translateY(0);}}
  }}
  
  /* Executive Narrative Panel */
  .narrative-card{{
    background:#18181b;
    border:1px solid #27272a;
    border-radius:16px;
    padding:40px;
  }}
  .narrative h2{{
    font-size:1.35rem;
    font-weight:700;
    color:#f4f4f5;
    margin:36px 0 16px;
    border-left:4px solid #2E5BFF;
    padding-left:14px;
    letter-spacing:-0.01em;
  }}
  .narrative h2:first-child{{margin-top:0;}}
  .narrative h3{{font-size:1.05rem;font-weight:600;color:#f4f4f5;margin:24px 0 10px;}}
  .narrative p{{font-size:0.92rem;color:#d4d4d8;margin-bottom:18px;line-height:1.75;}}
  .narrative ul,.narrative ol{{padding-left:24px;margin-bottom:18px;}}
  .narrative li{{font-size:0.92rem;color:#d4d4d8;margin-bottom:8px;line-height:1.7;}}
  .narrative strong{{color:#ffffff;font-weight:600;}}
  .narrative code{{background:#27272a;color:#a5b4fc;padding:2px 6px;border-radius:4px;font-size:0.85rem;}}
  
  /* Visual Dashboard Grid */
  .charts-grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(480px, 1fr));
    gap:24px;
  }}
  .chart-card{{
    background:#18181b;
    border:1px solid #27272a;
    border-radius:14px;
    padding:24px;
    display:flex;
    flex-direction:column;
    gap:16px;
    transition:transform 0.2s ease;
  }}
  .chart-card:hover{{
    transform:translateY(-2px);
  }}
  .chart-card-header{{display:flex;align-items:center;gap:8px;font-weight:600;font-size:0.95rem;color:#f4f4f5;}}
  .chart-card-icon{{color:#2E5BFF;}}
  .chart-card-body{{width:100%;display:flex;justify-content:center;}}
  
  /* Insights Dashboard Grid */
  .insights-grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));
    gap:20px;
  }}
  .insight-card{{
    background:#18181b;
    border:1px solid #27272a;
    border-radius:14px;
    padding:24px;
    display:flex;
    flex-direction:column;
    gap:12px;
    position:relative;
  }}
  .insight-card-top{{display:flex;justify-content:space-between;align-items:center;}}
  .insight-number{{font-size:0.8rem;font-weight:800;color:#2E5BFF;opacity:0.6;}}
  .insight-badge{{
    font-size:8px;
    font-weight:800;
    text-transform:uppercase;
    padding:3px 8px;
    border-radius:100px;
    letter-spacing:0.06em;
  }}
  .badge-danger{{background:rgba(239,68,68,0.12);color:#EF4444;border:1px solid rgba(239,68,68,0.2);}}
  .badge-warning{{background:rgba(245,158,11,0.12);color:#F59E0B;border:1px solid rgba(245,158,11,0.2);}}
  .badge-info{{background:rgba(59,130,246,0.12);color:#3B82F6;border:1px solid rgba(59,130,246,0.2);}}
  
  .insight-title{{font-size:1.05rem;font-weight:700;color:#f4f4f5;letter-spacing:-0.01em;}}
  .insight-desc{{font-size:0.88rem;color:#a1a1aa;line-height:1.6;flex-grow:1;}}
  .insight-meta{{
    display:flex;
    flex-wrap:wrap;
    gap:10px;
    font-size:0.75rem;
    color:#71717a;
    border-top:1px solid #27272a;
    padding-top:10px;
    margin-top:6px;
  }}
  .meta-tag strong{{color:#e4e4e7;}}
  
  /* Structural Profile Panel */
  .profile-grid{{
    display:grid;
    grid-template-columns:1fr 2fr;
    gap:24px;
    align-items:start;
  }}
  .profile-card{{
    background:#18181b;
    border:1px solid #27272a;
    border-radius:14px;
    padding:24px;
  }}
  .profile-card h3{{font-size:1.1rem;font-weight:700;color:#f4f4f5;margin-bottom:16px;}}
  .stats-table{{width:100%;border-collapse:collapse;margin-top:8px;}}
  .stats-table td{{
    padding:12px 14px;
    border-top:1px solid #27272a;
    font-size:0.88rem;
    color:#a1a1aa;
  }}
  .stats-table tr:first-child td{{border-top:none;}}
  .stats-table td strong{{color:#f4f4f5;}}
  
  /* Dataset Preview Table */
  .preview-card{{grid-column:span 2;width:100%;}}
  .preview-container{{
    width:100%;
    overflow-x:auto;
    border:1px solid #27272a;
    border-radius:8px;
    margin-top:12px;
  }}
  .preview-table{{width:100%;border-collapse:collapse;text-align:left;font-size:0.78rem;}}
  .preview-table th{{
    background:#27272a;
    color:#a1a1aa;
    font-weight:700;
    padding:10px 14px;
    text-transform:uppercase;
    font-size:0.68rem;
    letter-spacing:0.06em;
  }}
  .preview-table td{{
    padding:10px 14px;
    border-top:1px solid #27272a;
    color:#d4d4d8;
    white-space:nowrap;
  }}
  .preview-table tr:hover td{{background:rgba(255,255,255,0.02);}}
  
  /* Empty state */
  .empty-state{{
    background:#18181b;
    border:1px dashed #3f3f46;
    border-radius:14px;
    padding:48px;
    text-align:center;
    color:#a1a1aa;
  }}
  .empty-state p.small{{font-size:0.8rem;margin-top:8px;color:#71717a;}}
  
  /* Footer */
  .report-footer{{
    margin-top:50px;
    padding-top:20px;
    border-top:1px solid #27272a;
    display:flex;
    justify-content:space-between;
    font-size:0.75rem;
    color:#71717a;
  }}
  
  /* Print Stylesheet Overrides */
  @media print{{
    body{{background:#ffffff!important;color:#111827!important;font-size:13px;padding-bottom:0;}}
    .page{{padding:0!important;max-width:100%!important;}}
    
    .tab-labels-row, .tab-radio{{display:none!important;}}
    
    .tab-panel{{
      display:block!important;
      opacity:1!important;
      transform:none!important;
      margin-bottom:40px;
      page-break-after:always;
    }}
    
    .report-header, .narrative-card, .chart-card, .insight-card, .profile-card, .preview-container{{
      background:#ffffff!important;
      color:#111827!important;
      border:1px solid #d1d5db!important;
      box-shadow:none!important;
      transform:none!important;
      padding:24px!important;
      margin-bottom:24px!important;
    }}
    .report-header h1, .narrative h2, .narrative h3, .insight-title, .profile-card h3{{
      color:#111827!important;
    }}
    .narrative p, .narrative li, .insight-desc, .stats-table td, .preview-table td{{
      color:#374151!important;
    }}
    .stats-table td strong, .preview-table th{{
      color:#111827!important;
    }}
    .narrative h2{{border-left-color:#1d4ed8!important;}}
    .preview-table th, .stats-table tr{{background:#f3f4f6!important;border-color:#d1d5db!important;}}
    .preview-table td, .stats-table td{{border-color:#e5e7eb!important;}}
    
    .report-svg-chart{{
      background:#ffffff!important;
      border:1px solid #d1d5db!important;
    }}
    .report-svg-chart text{{fill:#374151!important;}}
    .report-svg-chart line{{stroke:#e5e7eb!important;}}
    .report-svg-chart line[stroke="#3f3f46"]{{stroke:#9ca3af!important;}}
    .report-svg-chart rect[fill="#2E5BFF"], 
    .report-svg-chart path[stroke="#2E5BFF"], 
    .report-svg-chart circle[fill="#2E5BFF"]{{
      fill:#1d4ed8!important;
      stroke:#1d4ed8!important;
    }}
  }}
</style>
</head>
<body>
<div class="page">
  <div class="report-header">
    <div class="header-tag">Executive Business Intelligence Report</div>
    <h1>{filename}</h1>
    <div class="report-meta">
      <span>📅 Generated: <strong>{date_str}</strong></span>
      <span>🤖 Analyst: <strong>Dataforge Assistant</strong></span>
      <span>📊 Dimensions: <strong>{stats.get("Categorical columns", "0")} cols</strong></span>
      <span>📈 Metrics: <strong>{stats.get("Numeric columns", "0")} cols</strong></span>
    </div>
  </div>

  <div class="tabs-container">
    <input type="radio" id="tab-nav-narrative" name="report-tabs" class="tab-radio" checked>
    <input type="radio" id="tab-nav-visuals" name="report-tabs" class="tab-radio">
    <input type="radio" id="tab-nav-insights" name="report-tabs" class="tab-radio">
    <input type="radio" id="tab-nav-profile" name="report-tabs" class="tab-radio">

    <div class="tab-labels-row">
      <label for="tab-nav-narrative" class="tab-label label-narrative">📄 Executive Narrative</label>
      <label for="tab-nav-visuals" class="tab-label label-visuals">📊 Visual Dashboard</label>
      <label for="tab-nav-insights" class="tab-label label-insights">💡 Algorithmic Insights</label>
      <label for="tab-nav-profile" class="tab-label label-profile">🔬 Structural Profile</label>
    </div>

    <div class="tab-panels">
      <div class="tab-panel panel-narrative">
        <div class="narrative-card">
          <div class="narrative">
            {html_narrative}
          </div>
        </div>
      </div>

      <div class="tab-panel panel-visuals">
        {charts_html}
      </div>

      <div class="tab-panel panel-insights">
        {insights_html}
      </div>

      <div class="tab-panel panel-profile">
        <div class="profile-grid">
          <div class="profile-card">
            <h3>Key Stats</h3>
            <table class="stats-table">
              <tbody>{stat_rows}</tbody>
            </table>
          </div>
          
          <div class="profile-card preview-card">
            <h3>Dataset Preview (Top 15 Rows)</h3>
            <div class="preview-container">
              {df_preview_html}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="report-footer">
    <span>Dataforge Consulting Intelligence Report</span>
    <span>{date_str} &nbsp;·&nbsp; Confidential</span>
  </div>
</div>
</body>
</html>"""


@workspace_bp.route("/api/data-report", methods=["POST"])
@login_required
def api_data_report_generate():
    """Generate a Gemini-powered Business Analyst Data Report and cache it."""
    import numpy as np
    import pandas as pd
    from ..storage import _save, _load
    from ..helpers import _get_upload_id, _get_upload_or_403, _get_filename
    from .dashboard import _compute_chart_data, _is_id_like_col, _format_stat_val

    upload_id = _get_upload_id()
    if not upload_id:
        return jsonify({"error": "upload_id required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    df_clean = _load(upload_id, "df_clean")
    df_raw   = _load(upload_id, "df_raw")
    df = df_clean if df_clean is not None else df_raw
    if df is None:
        return jsonify({"error": "No dataset loaded. Upload a CSV first."}), 400

    filename = _get_filename(upload_id) or "Dataset"
    rows, cols = df.shape

    # ── Build structured stats ──────────────────────────────────────────────
    missing_cells = int(df.isnull().sum().sum())
    total_cells = rows * cols
    miss_pct = round(missing_cells / total_cells * 100, 2) if total_cells else 0.0
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    dt_cols  = df.select_dtypes(include="datetime").columns.tolist()

    stats = {
        "Dataset":           filename,
        "Rows":              f"{rows:,}",
        "Columns":           str(cols),
        "Missing cells":     f"{missing_cells:,} ({miss_pct}%)",
        "Numeric columns":   str(len(num_cols)),
        "Categorical columns": str(len(cat_cols)),
        "Datetime columns":  str(len(dt_cols)),
    }

    # Numeric descriptive stats block for prompt
    num_block = ""
    for c in num_cols[:12]:
        try:
            s = df[c].dropna()
            if len(s):
                num_block += (
                    f"  - {c}: mean={s.mean():.4g}, median={s.median():.4g}, "
                    f"std={s.std():.4g}, min={s.min():.4g}, max={s.max():.4g}\n"
                )
        except Exception:
            pass

    cat_block = ""
    for c in cat_cols[:8]:
        try:
            top = df[c].value_counts().head(5)
            cat_block += f"  - {c}: top values → " + ", ".join(f"{k} ({v})" for k, v in top.items()) + "\n"
        except Exception:
            pass

    corr_block = ""
    if len(num_cols) >= 2:
        try:
            corr = df[num_cols].corr().abs()
            pairs = (
                corr.where(~np.eye(len(corr), dtype=bool))
                .stack()
                .sort_values(ascending=False)
                .head(6)
            )
            corr_block = "\nTop correlations:\n"
            for (c1, c2), v in pairs.items():
                corr_block += f"  - {c1} ↔ {c2}: r={v:.3f}\n"
        except Exception:
            pass

    prompt = f"""You are a senior business analyst and data strategist at a top-tier consulting firm.
You have been given a dataset to analyse. Write a comprehensive, insightful business intelligence report.

DATASET: {filename}
SHAPE: {rows:,} rows × {cols} columns
MISSING: {miss_pct}% missing data across {missing_cells:,} cells

NUMERIC COLUMNS ({len(num_cols)}):
{num_block or '  (none)'}

CATEGORICAL COLUMNS ({len(cat_cols)}):
{cat_block or '  (none)'}
{corr_block}
ALL COLUMN NAMES: {', '.join(df.columns.tolist()[:40])}

SAMPLE DATA (first 5 rows):
{df.head(5).to_string(index=False, max_cols=20)}

TASK: Write a comprehensive business analyst report with the following sections:

## Executive Summary
A 3-4 sentence C-suite ready summary of the dataset's business significance and key takeaways.

## Dataset Overview
Describe the dataset's structure, completeness, and what business domain it likely represents.

## Key Metrics & Statistics
Highlight the most important numeric findings with business context. Quantify everything.

## Data Quality Assessment
Assess missing data, anomalies, and structural issues. Provide a data quality score (0-10) with reasoning.

## Pattern & Trend Analysis
Identify the most significant patterns, trends, or relationships in the data. Use specific numbers.

## Business Insights & Opportunities
3-5 concrete, actionable business insights derived from the data. Be specific and quantitative.

## Risk Factors & Watchouts
Highlight any data red flags, biases, or business risks to be aware of.

## Strategic Recommendations
3-5 prioritised, specific, actionable recommendations for stakeholders, with expected impact.

## Conclusion
Brief closing summary tying everything together.

RULES:
- Use ## for section headers
- Be specific with numbers and percentages from the actual data
- Write in professional business language — clear, concise, decisive
- NO vague statements — every claim must be backed by the data
- Total length: 800-1200 words
"""

    try:
        from dataforge.gemini_pipeline import _gemini
        narrative = _gemini(prompt, temperature=0.3, timeout=60)
    except Exception as e:
        return jsonify({"error": f"Gemini API failed: {e}"}), 500

    # ── Compile standard and custom charts for the Visual tab ──
    charts = []
    
    id_like_cols = [c for c in num_cols if _is_id_like_col(c, df[c])]
    true_metrics  = [c for c in num_cols if c not in id_like_cols and not c.lower().endswith("id") and c.lower() != "id"]
    if not true_metrics and num_cols:
        true_metrics = [c for c in num_cols if c not in id_like_cols] or num_cols
        
    valid_dims = cat_cols + id_like_cols + [c for c in num_cols if c.lower().endswith("id") or c.lower() == "id"]
    
    metric = true_metrics[0] if true_metrics else None
    dim = valid_dims[0] if valid_dims else (cat_cols[0] if cat_cols else None)
    
    schema = _load(upload_id, "last_schema")
    
    # 1. Trend chart
    if schema and schema.get("date") and true_metrics:
        try:
            date_col = schema["date"]
            ts_metric = true_metrics[0]
            ts = df[[date_col, ts_metric]].copy()
            ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
            ts = ts.dropna().sort_values(date_col)
            if _is_id_like_col(ts_metric, ts[ts_metric]):
                agg = ts.groupby(ts[date_col].dt.to_period("M"))[ts_metric].count()
                y_lbl = f"Count of {ts_metric}"
            else:
                agg = ts.groupby(ts[date_col].dt.to_period("M"))[ts_metric].sum()
                y_lbl = ts_metric
            charts.append({
                "type": "line",
                "title": f"{y_lbl} over time",
                "labels": [str(p) for p in agg.index[-24:]],
                "values": [round(float(v), 2) for v in agg.values[-24:]],
                "x_label": date_col, "y_label": y_lbl,
            })
        except Exception:
            pass
            
    # 2. Bar chart
    if dim and metric:
        try:
            if _is_id_like_col(metric, df[metric]):
                grp = df.groupby(dim)[metric].count().sort_values(ascending=False).head(10)
                y_lbl = f"Count of {metric}"
            else:
                grp = df.groupby(dim)[metric].mean().sort_values(ascending=False).head(10)
                y_lbl = metric
            charts.append({
                "type": "bar",
                "title": f"Top {dim} by Avg {y_lbl}",
                "labels": [str(i) for i in grp.index],
                "values": [round(float(v), 2) for v in grp.values],
                "x_label": dim, "y_label": y_lbl,
            })
        except Exception:
            pass
            
    # 3. Pie/doughnut
    if metric:
        try:
            col = metric
            s = df[col].dropna()
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
                        labels.append(f"{names[idx]} ({left_fmt}-{right_fmt})")
                    values = [int(v) for v in vc.values]
                charts.append({
                    "type": "doughnut",
                    "title": f"{col} Distribution",
                    "labels": labels,
                    "values": values,
                    "x_label": col, "y_label": "count",
                })
        except Exception:
            pass

    # Custom charts
    try:
        custom_configs = _load(upload_id, "custom_charts") or []
        for config in custom_configs:
            computed = _compute_chart_data(df, config)
            if computed:
                charts.append({
                    "type": computed.get("type", "bar"),
                    "title": computed.get("title", ""),
                    "labels": computed.get("labels", []),
                    "values": computed.get("values", []),
                    "x_label": computed.get("x_col", ""),
                    "y_label": computed.get("y_col", "") or "count"
                })
    except Exception:
        pass

    # ── Fetch Algorithmic Insights ──
    insights = _load(upload_id, "last_insights") or []

    # ── Generate Dataset Preview Table ──
    df_preview_html = ""
    try:
        preview_df = df.head(15)
        df_preview_html = preview_df.to_html(classes="preview-table", index=False, border=0)
    except Exception:
        pass

    # Build the final interactive HTML report
    html = _build_data_report_html(filename, narrative, stats, charts, insights, df_preview_html)
    _save(upload_id, "data_report_html", html)
    return jsonify({"ok": True}), 200


@workspace_bp.route("/api/data-report/download")
@login_required
def api_data_report_download():
    """Serve the cached Data Report as HTML download or PDF."""
    from ..storage import _load
    from ..helpers import _get_upload_id, _get_filename

    upload_id = _get_upload_id()
    if not upload_id:
        return Response("upload_id required", status=400)

    html = _load(upload_id, "data_report_html")
    if not html:
        return Response("No data report generated yet. Click 'Generate Analysis' first.", status=404)

    fmt = (request.args.get("format") or "html").lower()
    filename_base = (_get_filename(upload_id) or "dataset").replace(" ", "_").replace(".csv", "")

    if fmt == "pdf":
        # Try weasyprint first, then headless browser
        try:
            from weasyprint import HTML as WP_HTML
            pdf = WP_HTML(string=html).write_pdf()
            return Response(
                pdf,
                mimetype="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=dataforge_report_{filename_base}.pdf"},
            )
        except Exception:
            pass
        # Headless browser fallback
        pdf = _render_pdf_with_browser(html)
        if pdf:
            return Response(
                pdf,
                mimetype="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=dataforge_report_{filename_base}.pdf"},
            )
        # If PDF fails, fall through to HTML download with a note
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename=dataforge_report_{filename_base}.html"},
    )


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

    from datetime import datetime

    chat_data = _load(upload_id, "chat_history")
    if isinstance(chat_data, list):
        if len(chat_data) > 0:
            default_session = {
                "id": "default",
                "name": "Previous Chat",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": chat_data
            }
            chat_data = {
                "active_session_id": "default",
                "sessions": [default_session]
            }
        else:
            chat_data = {
                "active_session_id": "default",
                "sessions": [{
                    "id": "default",
                    "name": "New Chat",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "messages": []
                }]
            }
    
    if not isinstance(chat_data, dict) or "sessions" not in chat_data or not chat_data.get("sessions"):
        chat_data = {
            "active_session_id": "default",
            "sessions": [{
                "id": "default",
                "name": "New Chat",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": []
            }]
        }

    session_id = body.get("session_id") or chat_data.get("active_session_id") or "default"
    
    # Find the session
    session = None
    for s in chat_data["sessions"]:
        if s["id"] == session_id:
            session = s
            break
            
    if not session:
        session = {
            "id": session_id,
            "name": "New Chat",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        chat_data["sessions"].append(session)

    chat_data["active_session_id"] = session_id

    # Auto-rename if it was default-named
    if session.get("name") in ("New Chat", "New Chat Session"):
        name_candidate = query[:30] + "..." if len(query) > 30 else query
        session["name"] = name_candidate

    session["messages"].append({"role": "user", "content": query})
    msg = {"role": "assistant", "content": result.get("answer", "")}
    r = result.get("result") or {}
    if r.get("type") in ("bar_chart", "line_chart", "histogram", "scatter_chart"):
        msg["chartData"] = r
    elif r.get("type") == "table":
        msg["tableData"] = r
    if result.get("insight"):
        msg["insight"] = result["insight"]
    session["messages"].append(msg)
    session["updated_at"] = datetime.now().isoformat()
    
    _save(upload_id, "chat_history", chat_data)

    if upload_id:
        try:
            db_update("uploads", upload_id, {
                "chat_history": json.dumps(chat_data, default=str)
            })
        except Exception:
            pass

    # Provide updated session state to frontend
    result["chat_sessions"] = chat_data["sessions"]
    result["active_session_id"] = session_id

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


# ── NEW CHAT SESSION & CONSENT ENDPOINTS ──────────────────────────────────────
@workspace_bp.route("/api/workspace/consent", methods=["POST"])
@login_required
def api_workspace_consent():
    from ..storage import _save
    from ..helpers import _get_upload_id, _get_upload_or_403
    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id parameter is required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err
    _save(upload_id, "ai_consent", True)
    return jsonify({"ok": True})


@workspace_bp.route("/api/workspace/chat/session/new", methods=["POST"])
@login_required
def api_chat_session_new():
    import uuid
    import json
    from datetime import datetime
    from ..storage import _save, _load
    from ..helpers import _get_upload_id, _get_upload_or_403
    from dataforge.db import db_update

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id parameter is required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    chat_data = _load(upload_id, "chat_history") or {}
    if not isinstance(chat_data, dict) or "sessions" not in chat_data:
        chat_data = {"active_session_id": "default", "sessions": []}

    new_id = str(uuid.uuid4())
    new_sess = {
        "id": new_id,
        "name": "New Chat",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": []
    }
    chat_data["sessions"].append(new_sess)
    chat_data["active_session_id"] = new_id

    _save(upload_id, "chat_history", chat_data)
    try:
        db_update("uploads", upload_id, {"chat_history": json.dumps(chat_data, default=str)})
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "chat_sessions": chat_data["sessions"],
        "active_session_id": new_id
    })


@workspace_bp.route("/api/workspace/chat/session/select", methods=["POST"])
@login_required
def api_chat_session_select():
    import json
    from ..storage import _save, _load
    from ..helpers import _get_upload_id, _get_upload_or_403
    from dataforge.db import db_update

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id parameter is required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    body = request.get_json(force=True) or {}
    session_id = body.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    chat_data = _load(upload_id, "chat_history")
    if not isinstance(chat_data, dict) or "sessions" not in chat_data:
        return jsonify({"error": "Chat data not initialized"}), 400

    session_ids = [s["id"] for s in chat_data["sessions"]]
    if session_id not in session_ids:
        return jsonify({"error": "Session not found"}), 404

    chat_data["active_session_id"] = session_id
    _save(upload_id, "chat_history", chat_data)
    try:
        db_update("uploads", upload_id, {"chat_history": json.dumps(chat_data, default=str)})
    except Exception:
        pass

    active_history = next((s["messages"] for s in chat_data["sessions"] if s["id"] == session_id), [])

    return jsonify({
        "ok": True,
        "chat_sessions": chat_data["sessions"],
        "active_session_id": session_id,
        "chat_history": active_history
    })


@workspace_bp.route("/api/workspace/chat/session/rename", methods=["POST"])
@login_required
def api_chat_session_rename():
    import json
    from ..storage import _save, _load
    from ..helpers import _get_upload_id, _get_upload_or_403
    from dataforge.db import db_update

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id parameter is required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    body = request.get_json(force=True) or {}
    session_id = body.get("session_id")
    name = (body.get("name") or "").strip()
    if not session_id or not name:
        return jsonify({"error": "session_id and non-empty name required"}), 400

    chat_data = _load(upload_id, "chat_history")
    if not isinstance(chat_data, dict) or "sessions" not in chat_data:
        return jsonify({"error": "Chat data not initialized"}), 400

    session = None
    for s in chat_data["sessions"]:
        if s["id"] == session_id:
            session = s
            break

    if not session:
        return jsonify({"error": "Session not found"}), 404

    session["name"] = name
    _save(upload_id, "chat_history", chat_data)
    try:
        db_update("uploads", upload_id, {"chat_history": json.dumps(chat_data, default=str)})
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "chat_sessions": chat_data["sessions"],
        "active_session_id": chat_data.get("active_session_id")
    })


@workspace_bp.route("/api/workspace/chat/session/delete", methods=["POST"])
@login_required
def api_chat_session_delete():
    import json
    from datetime import datetime
    from ..storage import _save, _load
    from ..helpers import _get_upload_id, _get_upload_or_403
    from dataforge.db import db_update

    upload_id = _get_upload_id()
    if upload_id is None:
        return jsonify({"error": "upload_id parameter is required"}), 400
    _, err = _get_upload_or_403(upload_id)
    if err:
        return err

    body = request.get_json(force=True) or {}
    session_id = body.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    chat_data = _load(upload_id, "chat_history")
    if not isinstance(chat_data, dict) or "sessions" not in chat_data:
        return jsonify({"error": "Chat data not initialized"}), 400

    chat_data["sessions"] = [s for s in chat_data["sessions"] if s["id"] != session_id]

    if not chat_data["sessions"]:
        chat_data["sessions"] = [{
            "id": "default",
            "name": "New Chat",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }]
        chat_data["active_session_id"] = "default"
    elif chat_data.get("active_session_id") == session_id:
        chat_data["sessions"].sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        chat_data["active_session_id"] = chat_data["sessions"][0]["id"]

    _save(upload_id, "chat_history", chat_data)
    try:
        db_update("uploads", upload_id, {"chat_history": json.dumps(chat_data, default=str)})
    except Exception:
        pass

    active_session_id = chat_data.get("active_session_id")
    active_history = next((s["messages"] for s in chat_data["sessions"] if s["id"] == active_session_id), [])

    return jsonify({
        "ok": True,
        "chat_sessions": chat_data["sessions"],
        "active_session_id": active_session_id,
        "chat_history": active_history
    })
