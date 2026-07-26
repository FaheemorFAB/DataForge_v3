"""
routes/projects.py — Projects Blueprint
"""
import json
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

projects_bp = Blueprint("projects_bp", __name__)


@projects_bp.route("/projects")
@login_required
def projects():
    return render_template("projects.html", user=current_user)


@projects_bp.route("/api/projects")
@login_required
def api_projects():
    from ..helpers import _project_meta
    from dataforge.db import db_all

    uploads = db_all("uploads", {"user_id": current_user.id}, order_by="uploaded_at", limit=50)
    result = []
    for u in uploads:
        uid = u.get("id")
        meta = _project_meta(uid)
        result.append({
            "id":          uid,
            "filename":    u.get("filename", ""),
            "rows":        u.get("rows", 0) or 0,
            "cols":        u.get("cols", 0) or 0,
            "missing_pct": u.get("missing_pct", 0) or 0,
            "uploaded_at": u.get("uploaded_at") or "",
            "source_type": u.get("source_type", "csv") or "csv",
            **meta,
        })
    return jsonify(result)


@projects_bp.route("/api/restore/<int:upload_id>", methods=["POST"])
@login_required
def api_restore(upload_id):
    from ..storage import _save, _load, _clear_store
    from ..helpers import (_df_profile, _load_persisted, _persist, _get_filename)
    from dataforge.db import db_get

    up = db_get("uploads", upload_id)
    if not up or up.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404

    _clear_store(upload_id)

    loaded_keys = []
    for key in ("df_raw", "df_clean", "eda_html", "model_pkl"):
        obj = _load_persisted(upload_id, key)
        if obj is not None:
            _save(upload_id, key, obj)
            loaded_keys.append(key)

    if "df_raw" not in loaded_keys and "df_clean" not in loaded_keys:
        source_type = up.get("source_type", "csv") or "csv"
        up_filename = up.get("filename", "")
        if source_type == "sheets" and up.get("storage_path"):
            try:
                source_cfg = json.loads(up.get("storage_path"))
                sheet_id_r = source_cfg.get("sheet_id", "")
                if sheet_id_r:
                    from dataforge.sheets_connector import SheetsConnector
                    df_refetch = SheetsConnector().load_public(sheet_id_r)
                    _save(upload_id, "df_raw", df_refetch)
                    profile = _df_profile(df_refetch, up_filename)
                    _save(upload_id, "profile", profile)
                    _persist(upload_id, "df_raw", df_refetch)
                    return jsonify({"ok": True, "needs_reupload": False, "profile": profile,
                                    "auto_restored": True, "source": "sheets"})
            except Exception:
                pass

        profile = {
            "filename":    up_filename,
            "rows":        up.get("rows", 0) or 0,
            "cols":        up.get("cols", 0) or 0,
            "missing_pct": up.get("missing_pct", 0.0) or 0.0,
            "missing":     0,
            "numeric":     0,
            "columns":     [],
        }
        _save(upload_id, "profile", profile)

        if source_type == "sheets":
            msg = (f"Could not re-fetch '{up_filename}' from Google Sheets. "
                   "The sheet may have been made private or the URL changed. "
                   "Re-connect the sheet to continue.")
        else:
            msg = (f"'{up_filename}' was saved before data persistence was enabled. "
                   "Re-upload the original file to continue your analysis.")

        return jsonify({
            "ok":             True,
            "needs_reupload": True,
            "source_type":    source_type,
            "profile":        profile,
            "message":        msg,
        })

    if up.get("clean_meta_json"):
        try:
            _save(upload_id, "clean_meta", json.loads(up.get("clean_meta_json")))
        except Exception:
            pass
    if up.get("automl_meta_json"):
        try:
            _save(upload_id, "automl_meta", json.loads(up.get("automl_meta_json")))
        except Exception:
            pass
    if up.get("chat_history"):
        try:
            _save(upload_id, "chat_history", json.loads(up.get("chat_history")))
        except Exception:
            pass

    _dc = _load(upload_id, "df_clean")
    df = _dc if _dc is not None else _load(upload_id, "df_raw")
    profile = _df_profile(df, up.get("filename", ""))
    _save(upload_id, "profile", profile)

    return jsonify({"ok": True, "needs_reupload": False, "profile": profile})


@projects_bp.route("/api/delete/<int:upload_id>", methods=["DELETE"])
@login_required
def api_delete_upload(upload_id):
    from ..storage import _clear_store
    from ..helpers import _get_upload_or_403
    from dataforge.db import db_delete

    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err

    db_delete("uploads", upload.id)
    _clear_store(upload_id)
    return jsonify({"ok": True})
