"""
DataForge — Flask Application (Slim Entry Point)
═════════════════════════════════════════════════
Route handlers have been extracted into Blueprint modules under routes/.
Shared utilities live in helpers.py and storage.py.

This file retains:
  • Flask app creation & config
  • SocketIO setup
  • Flask-Login manager
  • Google OAuth registration
  • SafeJSON provider
  • Blueprint registration
  • WebSocket event handlers
  • Background health endpoint
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os, io, json, pickle, tempfile
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from flask import (Flask, render_template, request, jsonify,
                   send_file, redirect, url_for, Response)
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
os.environ.setdefault("DATAFORGE_ROOT", str(ROOT_DIR))
SHARED_DIR = ROOT_DIR / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

load_dotenv(override=True, dotenv_path=ROOT_DIR / ".env")

from dataforge.settings import PROJECTS_DIR
from services.auth import (
    google_auth_enabled,
    init_shared_auth,
    register_auth_template_globals,
)

from dataforge.db import (db_client, db_get, db_first, db_all, db_insert,
                          db_update, db_delete, db_count)
from dataforge.db import (Upload, ReportSchedule)
from flask_login import login_required, current_user

# App setup
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dataforge-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

# Redis / Celery config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.config["broker_url"] = REDIS_URL
app.config["result_backend"] = REDIS_URL
SYNC_FALLBACK_ENABLED = os.getenv("DATAFORGE_SYNC_FALLBACK", "1") == "1"

# WebSocket via flask-socketio
from flask_socketio import SocketIO, emit as ws_emit_raw, join_room
try:
    import redis  # noqa: F401
    _redis_py_ok = True
except Exception:
    _redis_py_ok = False
_sio_mq = REDIS_URL if (os.getenv("REDIS_URL") and _redis_py_ok) else None
_socketio_kwargs = {
    "cors_allowed_origins": "*",
    "logger": False,
    "engineio_logger": False,
    "message_queue": _sio_mq,
}
if os.getenv("SOCKETIO_ASYNC_MODE"):
    _socketio_kwargs["async_mode"] = os.getenv("SOCKETIO_ASYNC_MODE")
socketio = SocketIO(app, **_socketio_kwargs)


def _ws_push(event: str, data: dict, user_id: int | None = None):
    """Emit a socketio event to a specific user's room (or broadcast)."""
    try:
        room = f"user_{user_id}" if user_id else None
        socketio.emit(event, data, room=room, namespace="/")
    except Exception:
        pass


login_manager = init_shared_auth(app)
register_auth_template_globals(app)

# ── SafeJSON provider ─────────────────────────────────────────────────────────
from flask.json.provider import DefaultJSONProvider
class _SafeJSON(DefaultJSONProvider):
    def dumps(self, obj, **kw):
        def _fix(o):
            if isinstance(o, float) and (math.isnan(o) or math.isinf(o)): return None
            if isinstance(o, dict):  return {k: _fix(v) for k, v in o.items()}
            if isinstance(o, list):  return [_fix(v) for v in o]
            return o
        return super().dumps(_fix(obj), **kw)
app.json_provider_class = _SafeJSON
app.json = _SafeJSON(app)


# ══════════════════════════════════════════════════════════════════════════════
# INJECT SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════
from .helpers import set_ws_push
from . import helpers as _helpers

# Wire the WS push function into helpers so blueprints can use it
set_ws_push(_ws_push)
_helpers.SYNC_FALLBACK_ENABLED = SYNC_FALLBACK_ENABLED


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("upload.html", user=current_user, google_enabled=google_auth_enabled())


@app.route("/healthz")
def healthz():
    return {"ok": True, "service": "web"}


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user
    
    recent_uploads = db_all("uploads", {"user_id": user.id}, order_by="uploaded_at", limit=10)

    def _time_ago_local(dt_str):
        if not dt_str:
            return ""
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            # Supabase returns UTC ISO strings. Convert naive datetime.utcnow() logically
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
    
    # Supabase Join: fetch Analysis and its parent Upload's filename
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
        """Format created_at for template (Supabase returns ISO strings)."""
        if not val:
            return "—"
        # datetime-like object (just in case)
        try:
            if hasattr(val, "strftime"):
                return val.strftime("%B %Y")
        except Exception:
            pass
        # ISO string fallback
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


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@socketio.on("connect")
def on_ws_connect():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")

@socketio.on("disconnect")
def on_ws_disconnect():
    pass

@socketio.on("ping_dashboard")
def on_ping(data):
    if current_user.is_authenticated:
        ws_emit_raw("pong_dashboard", {"uid": current_user.id})


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/health/background", methods=["GET"])
def api_health_background():
    from .helpers import _tasks
    out = {
        "tasks_import_ok": False,
        "broker_ok": False,
        "redis_py_installed": _redis_py_ok,
        "redis_url_set": bool(os.getenv("REDIS_URL")),
        "details": "",
    }
    try:
        (task_run_insights, *_) = _tasks()
        out["tasks_import_ok"] = True
        try:
            with task_run_insights.app.connection_for_read() as conn:
                conn.ensure_connection(max_retries=1)
            out["broker_ok"] = True
        except Exception as be:
            out["details"] = f"Broker unavailable: {be}"
    except Exception as ie:
        out["details"] = f"Task import failed: {ie}"
    healthy = out.get("tasks_import_ok") and out.get("broker_ok")
    return jsonify({"ok": bool(healthy), **out}), (200 if healthy else 503)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    socketio.run(
        app,
        debug=True,
        host="0.0.0.0",
        port=5000,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )


