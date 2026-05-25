"""
routes/upload.py — Upload Blueprint (CSV + Google Sheets)
"""
import json
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user

upload_bp = Blueprint("upload_bp", __name__)


@upload_bp.route("/")
def index():
    from flask import current_app
    return render_template(
        "upload.html",
        user=current_user,
        google_enabled=current_app.config.get("GOOGLE_AUTH_ENABLED", False),
    )


@upload_bp.route("/api/upload", methods=["POST"])
def api_upload():
    import pandas as pd
    from ..storage import _save
    from ..helpers import _df_profile, _db_log_upload, _persist

    if not current_user.is_authenticated:
        return jsonify({"error": "login_required"}), 401
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    try:
        if f.filename.lower().endswith(".csv"):
            df = pd.read_csv(f)
        elif f.filename.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(f)
        else:
            return jsonify({"error": "Unsupported file format. Please upload CSV or Excel files."}), 400
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400

    profile = _df_profile(df, f.filename)
    upload_id = _db_log_upload(profile)
    if not upload_id:
        return jsonify({"error": "Failed to create upload record"}), 500

    _save(upload_id, "df_raw", df)
    _save(upload_id, "profile", profile)
    _persist(upload_id, "df_raw", df)

    return jsonify({"ok": True, "profile": profile, "upload_id": upload_id})


@upload_bp.route("/api/upload/sheets", methods=["POST"])
def api_upload_sheets():
    import pandas as pd
    from ..storage import _save
    from ..helpers import _df_profile, _db_log_upload, _persist

    if not current_user.is_authenticated:
        return jsonify({"error": "login_required"}), 401
    body = request.get_json(force=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        from dataforge.sheets_connector import SheetsConnector
        import re as _re
        conn = SheetsConnector()
        m = _re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if not m:
            return jsonify({"error": "Invalid Google Sheets URL"}), 400
        sheet_id = m.group(1)
        df = conn.load_public(sheet_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    fname = f"sheets_{sheet_id[:8]}.csv"
    profile = _df_profile(df, fname)
    source_config = {"url": url, "sheet_id": sheet_id}
    upload_id = _db_log_upload(profile, source_type="sheets", source_config=source_config)
    if not upload_id:
        return jsonify({"error": "Failed to create upload record"}), 500

    _save(upload_id, "df_raw", df)
    _save(upload_id, "profile", profile)
    _persist(upload_id, "df_raw", df)
    try:
        from dataforge.db import db_update
        db_update("uploads", upload_id, {"storage_path": json.dumps(source_config)})
    except Exception:
        pass

    return jsonify({"ok": True, "profile": profile, "upload_id": upload_id})
