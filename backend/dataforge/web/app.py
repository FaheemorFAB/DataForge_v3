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

import os, json, uuid, math
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, redirect, url_for
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
os.environ.setdefault("DATAFORGE_ROOT", str(ROOT_DIR))

load_dotenv(override=True, dotenv_path=PROJECT_ROOT / ".env")

from dataforge.settings import PROJECTS_DIR

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=str(FRONTEND_DIR / "templates"),
    static_folder=str(FRONTEND_DIR / "static"),
)
app.secret_key = os.environ["FLASK_SECRET_KEY"]  # crash loudly if missing
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

# ── Redis / Celery config ─────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.config["broker_url"]     = REDIS_URL
app.config["result_backend"]  = REDIS_URL
SYNC_FALLBACK_ENABLED = os.getenv("DATAFORGE_SYNC_FALLBACK", "1") == "1"

# ── WebSocket via flask-socketio ──────────────────────────────────────────────
from flask_socketio import SocketIO, emit as ws_emit_raw, join_room
try:
    import redis  # noqa: F401
    _redis_py_ok = True
except Exception:
    _redis_py_ok = False
_sio_mq = REDIS_URL if (os.getenv("REDIS_URL") and _redis_py_ok) else None
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading",
                    logger=False, engineio_logger=False,
                    message_queue=_sio_mq)

def _ws_push(event: str, data: dict, user_id: int | None = None):
    """Emit a socketio event to a specific user's room (or broadcast)."""
    try:
        room = f"user_{user_id}" if user_id else None
        socketio.emit(event, data, room=room, namespace="/")
    except Exception:
        pass  # best-effort


# ── Database ───────────────────────────────────────────────────────────────────
from dataforge.db import (db_client, db_get, db_first, db_all, db_insert,
                          db_update, db_delete, db_count)
from dataforge.db import (User, Upload, ReportSchedule)


# ── Flask-Login ────────────────────────────────────────────────────────────────
from flask_login import (LoginManager, login_user, logout_user,
                          login_required, current_user)

login_manager = LoginManager(app)
login_manager.login_view = "auth.login_page"
login_manager.login_message = ""

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
    if ("application/json" in request.headers.get("Accept", "") or
            request.headers.get("Content-Type", "").startswith("application/json")):
        return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
    return redirect(url_for("upload_bp.index") + "?login=1")

@login_manager.user_loader
def load_user(user_id: str):
    data = db_get("users", int(user_id))
    return User(**data) if data else None

# ── Google OAuth via Authlib ───────────────────────────────────────────────────
from authlib.integrations.flask_client import OAuth

_GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
_GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_AUTH_ENABLED   = bool(_GOOGLE_CLIENT_ID and _GOOGLE_CLIENT_SECRET)
app.config["GOOGLE_AUTH_ENABLED"] = GOOGLE_AUTH_ENABLED

oauth = OAuth(app)
if GOOGLE_AUTH_ENABLED:
    oauth.register(
        name="google",
        client_id=_GOOGLE_CLIENT_ID,
        client_secret=_GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
        },
    )

# ── SafeJSON provider ─────────────────────────────────────────────────────────
from flask.json.provider import DefaultJSONProvider
class _SafeJSON(DefaultJSONProvider):
    def dumps(self, obj, **kw):
        def _fix(o):
            if isinstance(o, (float, np.floating)):
                if math.isnan(o) or math.isinf(o) or np.isnan(o) or np.isinf(o):
                    return None
                return float(o)
            if isinstance(o, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(o)
            if isinstance(o, (np.bool_, bool)):
                return bool(o)
            if isinstance(o, np.ndarray):
                return [_fix(x) for x in o.tolist()]
            if isinstance(o, dict):
                return {str(k): _fix(v) for k, v in o.items()}
            if isinstance(o, (list, tuple, set)):
                return [_fix(v) for v in o]
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
# BLUEPRINT REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
from .routes.auth      import auth_bp, init_auth
from .routes.upload     import upload_bp
from .routes.workspace  import workspace_bp
from .routes.automl     import automl_bp
from .routes.insights   import insights_bp
from .routes.dashboard  import dashboard_bp
from .routes.projects   import projects_bp
from .routes.tasks_api  import tasks_api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(workspace_bp)
app.register_blueprint(automl_bp)
app.register_blueprint(insights_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(tasks_api_bp)

# Post-registration init for auth (passes OAuth and flags)
init_auth(app, oauth, GOOGLE_AUTH_ENABLED)


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
