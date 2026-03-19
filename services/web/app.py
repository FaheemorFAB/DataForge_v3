"""
DataForge — Flask Application
New in this version
───────────────────
  • SQLite database via Flask-SQLAlchemy (users / uploads / analyses tables)
  • Google OAuth 2.0 via Authlib
  • Flask-Login for session management
  • /login, /logout, /auth/google/callback routes
  • /dashboard route (login required)
  • DB logging on every upload / clean / eda / automl / query action
  • Auth is additive — workspace still works without login (DB logging skipped)
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os, io, uuid, json, pickle, tempfile
import sys
from datetime import datetime
from pathlib import Path
from functools import wraps

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

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", uuid.uuid4().hex)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

# ── Redis / Celery config ─────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.config["CELERY_BROKER_URL"]     = REDIS_URL
app.config["CELERY_RESULT_BACKEND"]  = REDIS_URL

# ── WebSocket via flask-socketio ──────────────────────────────────────────────
# message_queue enables workers to emit events across processes via Redis pub/sub
from flask_socketio import SocketIO, emit as ws_emit_raw, join_room
_sio_mq = REDIS_URL if os.getenv("REDIS_URL") else None
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading",
                    logger=False, engineio_logger=False,
                    message_queue=_sio_mq)

def _ws_push(event: str, data: dict, user_id: int | None = None):
    """Emit a socketio event to a specific user's room (or broadcast)."""
    try:
        room = f"user_{user_id}" if user_id else None
        socketio.emit(event, data, room=room, namespace="/")
    except Exception:
        pass  # WebSocket push is best-effort — never break the HTTP response

# ── Database ───────────────────────────────────────────────────────────────────
# ── Database — Supabase Native ──────────────────────────────────────────────────
# Replaced SQLAlchemy SQLite/Postgres ORM with direct PostgREST calls

from dataforge.db import (db_client, db_get, db_first, db_all, db_insert, 
                          db_update, db_delete, db_count)
from dataforge.db import (User, Upload, ReportSchedule)


# ── Flask-Login ────────────────────────────────────────────────────────────────
from flask_login import (LoginManager, login_user, logout_user,
                          login_required, current_user)

login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message = ""

# ── API calls return JSON 401 instead of HTML redirect ────────────────────────
@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
    if ("application/json" in request.headers.get("Accept", "") or
            request.headers.get("Content-Type", "").startswith("application/json")):
        return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
    return redirect(url_for("index") + "?login=1")

@login_manager.user_loader
def load_user(user_id: str):
    data = db_get("users", int(user_id))
    return User(**data) if data else None

# ── Google OAuth via Authlib ───────────────────────────────────────────────────
from authlib.integrations.flask_client import OAuth

_GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
_GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_AUTH_ENABLED   = bool(_GOOGLE_CLIENT_ID and _GOOGLE_CLIENT_SECRET)

oauth = OAuth(app)
if GOOGLE_AUTH_ENABLED:
    oauth.register(
        name="google",
        client_id=_GOOGLE_CLIENT_ID,
        client_secret=_GOOGLE_CLIENT_SECRET,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        access_token_url="https://oauth2.googleapis.com/token",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
        client_kwargs={
            "scope": "openid email profile",
            "token_endpoint_auth_method": "client_secret_post",
        },
    )

# Temp storage dir for large objects (DataFrames, models)
STORE_DIR = Path(tempfile.gettempdir()) / "dataforge_store"
STORE_DIR.mkdir(exist_ok=True)

import math
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

def _get_upload_user_id(upload_id: int):
    """Return the user_id for an Upload row (used by Supabase storage helpers)."""
    try:
        up = db_get("uploads", upload_id)
        return up.get("user_id") if up else None
    except Exception:
        return None


def _get_filename(upload_id: int) -> str:
    """Helper to fetch the filename from the cached profile or DB."""
    p = _load(upload_id, "profile") or {}
    return p.get("filename", "")


def _persist(upload_id: int, key: str, obj):
    """
    Write-through storage: always saves to local disk, also pushes to
    Supabase Storage when configured (for durability across deploys).
    """
    # ── Local write (original behaviour, always runs) ─────────────────────────
    d = PROJECTS_DIR / str(upload_id)
    d.mkdir(exist_ok=True)
    if isinstance(obj, pd.DataFrame):
        if len(obj) > 2_000_000:
            raise ValueError("Dataset too large (exceeds 2M rows limit)")
        obj.to_parquet(d / f"{key}.parquet", index=False, compression="snappy")
    elif isinstance(obj, bytes):
        (d / f"{key}.joblib").write_bytes(obj)
    else:
        with open(d / f"{key}.json", "w", encoding="utf-8") as f:
            json.dump(obj, f, default=str)

    # ── Supabase write (new — non-fatal if it fails) ──────────────────────────
    if STORAGE_OK:
        try:
            user_id = _get_upload_user_id(upload_id)
            if user_id is None:
                return
            store = get_store()
            if key in ("df_raw", "df_clean") and isinstance(obj, pd.DataFrame):
                csv_key = "raw" if key == "df_raw" else "clean"
                path    = store.upload_dataframe(user_id, upload_id, obj, csv_key)
            elif isinstance(obj, bytes):
                path = store.upload_joblib(user_id, upload_id, key, obj)
            else:
                path = store.upload_json(user_id, upload_id, key, obj)
            
            # Persist the storage path into the Upload row for df_raw
            if key == "df_raw":
                try:
                    db_update("uploads", upload_id, {"storage_path": path})
                except Exception:
                    pass
        except Exception as _exc:
            app.logger.warning("Supabase _persist failed (key=%s): %s", key, _exc)


def _load_persisted(upload_id: int, key: str):
    """
    Load persisted data: tries local disk first (fast), falls back to
    Supabase Storage (handles cases where local disk was cleared after deploy).
    On Supabase hit, re-caches to local disk for subsequent fast reads.
    """
    # ── Local read ────────────────────────────────────────────────────────────
    d = PROJECTS_DIR / str(upload_id)
    p_pq = d / f"{key}.parquet"
    if p_pq.exists():
        try: return pd.read_parquet(p_pq)
        except Exception: pass

    p_bin = d / f"{key}.joblib"
    if p_bin.exists():
        try: return p_bin.read_bytes()
        except Exception: pass

    p_json = d / f"{key}.json"
    if p_json.exists():
        try:
            with open(p_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass

    # legacy fallback
    p_leg = d / key
    if p_leg.exists():
        try:
            with open(p_leg, "rb") as f:
                return pickle.load(f)
        except Exception: pass

    # ── Supabase fallback ─────────────────────────────────────────────────────
    if STORAGE_OK:
        try:
            user_id = _get_upload_user_id(upload_id)
            if user_id is None:
                return None
            store = get_store()
            if key in ("df_raw", "df_clean"):
                csv_key = "raw" if key == "df_raw" else "clean"
                spath   = f"users/{user_id}/uploads/{upload_id}/{csv_key}.parquet"
                obj     = store.download_dataframe(spath)
            else:
                # Try JSON first
                spath_json = f"users/{user_id}/uploads/{upload_id}/{key}.json"
                obj = store.download_json(spath_json)
                if obj is None:
                    spath_joblib = f"users/{user_id}/uploads/{upload_id}/{key}.joblib"
                    obj = store.download_joblib(spath_joblib)
                # We dropped the original pickle methods, so we don't fallback to remote .pkl

            if obj is not None:
                # Re-cache locally for next time
                d.mkdir(exist_ok=True)
                if isinstance(obj, pd.DataFrame):
                    obj.to_parquet(d / f"{key}.parquet", index=False, compression="snappy")
                elif isinstance(obj, bytes):
                    (d / f"{key}.joblib").write_bytes(obj)
                else:
                    with open(d / f"{key}.json", "w", encoding="utf-8") as f:
                        json.dump(obj, f, default=str)
                app.logger.info("Restored %s/%s from Supabase Storage.", upload_id, key)
            return obj
        except Exception as _exc:
            app.logger.warning("Supabase _load_persisted failed (key=%s): %s", key, _exc)

    return None

def _project_meta(upload_id: int) -> dict:
    d = PROJECTS_DIR / str(upload_id)
    return {
        "has_raw":   (d / "df_raw.parquet").exists() or (d / "df_raw").exists(),
        "has_clean": (d / "df_clean.parquet").exists() or (d / "df_clean").exists(),
        "has_eda":   (d / "eda_html").exists(),
        "has_model": (d / "model_pkl.joblib").exists() or (d / "model_pkl").exists(),
        "has_chat":  (d / "chat_history.json").exists() or (d / "chat_history").exists(),
    }

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

# ── Module imports ─────────────────────────────────────────────────────────────
from dataforge.data_cleaner   import run_cleaning_pipeline
from dataforge.eda_report     import generate_eda_report
from dataforge.automl_trainer import run_automl, _detect_task
from dataforge.gemini_pipeline import run_query_pipeline, is_available as gemini_available

# ── Reporting engine ────────────────────────────────────────────────────────────
try:
    from dataforge.insight_engine  import detect_schema, run_insights, summarise_with_gemini, build_report_text
    from dataforge.report_generator import generate_html_report
    from dataforge.alert_engine     import AlertEngine
    REPORTING_ENABLED = True
except ImportError as _re:
    REPORTING_ENABLED = False
    print(f"[WARN] Reporting engine not loaded: {_re}")

# ── Transform Engine & Root Cause Analysis ────────────────────────────────────
try:
    from dataforge.transform_engine import apply_transforms
    from dataforge.root_cause import run_root_cause
    TRANSFORM_ENABLED = True
except ImportError as _te:
    TRANSFORM_ENABLED = False
    print(f"[WARN] Transform engine not loaded: {_te}")

# ── Supabase Storage (graceful fallback to local disk if not configured) ────────
try:
    from dataforge.supabase_storage import get_store, STORAGE_OK
except ImportError:
    STORAGE_OK = False
    def get_store(): return None

# ── Redis cache helpers ───────────────────────────────────────────────────────
try:
    from cache import (
        get_profile, set_profile,
        get_schema, set_schema,
        get_clean_meta, set_clean_meta,
        get_alert_status, set_alert_status,
        get_user_metrics, set_user_metrics,
        invalidate_upload, invalidate_user,
        rate_limit as _rate_limit,
    )
    CACHE_OK = True
except ImportError:
    CACHE_OK = False
    def get_profile(uid): return None
    def set_profile(uid, p): pass
    def get_schema(uid): return None
    def set_schema(uid, s): pass
    def get_clean_meta(uid): return None
    def set_clean_meta(uid, m): pass
    def get_alert_status(uid): return None
    def set_alert_status(uid, s): pass
    def get_user_metrics(uid): return None
    def set_user_metrics(uid, m): pass
    def invalidate_upload(uid): pass
    def invalidate_user(uid): pass
    def _rate_limit(uid, action, limit=3, window_s=60): return True

# ── Celery tasks (lazy import to avoid circular on app boot) ──────────────────
def _tasks():
    from tasks import (task_run_insights, task_run_automl,
                       task_run_eda, task_generate_report, task_check_alerts)
    return (task_run_insights, task_run_automl,
            task_run_eda, task_generate_report, task_check_alerts)

# Note: No local SQLite migrations needed. All schema definition is in supabase/schema.sql


# ══════════════════════════════════════════════════════════════════════════════
# SESSION HELPERS  — DataFrames too large for cookie; store on disk
# ══════════════════════════════════════════════════════════════════════════════
from filelock import FileLock
import shutil

def _upath(upload_id: int, key: str) -> Path:
    d = STORE_DIR / str(upload_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / key

def _lock_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")

def _save(upload_id: int, key: str, obj):
    path = _upath(upload_id, key)
    lock = FileLock(_lock_path(path))
    with lock:
        tmp = path.with_suffix(path.suffix + ".tmp")
        if isinstance(obj, pd.DataFrame):
            if len(obj) > 2_000_000:
                raise ValueError("Dataset too large (exceeds 2M rows limit)")
            tmp = tmp.with_suffix(".parquet")
            path = path.with_suffix(".parquet")
            obj.to_parquet(tmp, index=False, compression="snappy")
        elif isinstance(obj, bytes):
            tmp = tmp.with_suffix(".joblib")
            path = path.with_suffix(".joblib")
            tmp.write_bytes(obj)
        else:
            tmp = tmp.with_suffix(".json")
            path = path.with_suffix(".json")
            tmp.write_text(json.dumps(obj, default=str), encoding="utf-8")
        tmp.replace(path)

def _load(upload_id: int, key: str):
    path = _upath(upload_id, key)
    p_pq = path.with_suffix('.parquet')
    if p_pq.exists():
        with FileLock(_lock_path(p_pq)):
            return pd.read_parquet(p_pq)
    p_bin = path.with_suffix('.joblib')
    if p_bin.exists():
        with FileLock(_lock_path(p_bin)):
            return p_bin.read_bytes()
    p_json = path.with_suffix('.json')
    if p_json.exists():
        with FileLock(_lock_path(p_json)):
            return json.loads(p_json.read_text(encoding="utf-8"))
    if path.exists():
        with FileLock(_lock_path(path)):
            with open(path, "rb") as f:
                return pickle.load(f)
    return None

def _exists(upload_id: int, key: str) -> bool:
    path = _upath(upload_id, key)
    return path.with_suffix('.parquet').exists() or path.with_suffix('.json').exists() \
        or path.with_suffix('.joblib').exists() or path.exists()

def _clear_store(upload_id: int):
    d = STORE_DIR / str(upload_id)
    if d.exists():
        shutil.rmtree(d)

def _get_upload_id() -> int | None:
    if request.is_json:
        body = request.get_json(silent=True)
        if body and "upload_id" in body:
            return int(body["upload_id"])
    if "upload_id" in request.form:
        return int(request.form["upload_id"])
    if "upload_id" in request.args:
        return int(request.args["upload_id"])
    return None

def _get_upload_or_403(upload_id: int):
    data = db_get("uploads", upload_id)
    if not data or data.get("user_id") != current_user.id:
        return None, (jsonify({"error": "Unauthorized"}), 403)
    return Upload(**data), None

def _require_df(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        upload_id = _get_upload_id()
        if upload_id is None:
            return jsonify({"error": "upload_id required"}), 400
        upload, err = _get_upload_or_403(upload_id)
        if err:
            return err
        if not _exists(upload_id, "df_raw") and not _exists(upload_id, "df_clean"):
            return jsonify({"error": "No dataset loaded. Please upload a CSV first."}), 400
        kwargs["upload_id"] = upload_id
        return fn(*args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# DB LOGGING HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _db_log_upload(profile: dict, source_type: str = "csv", source_config: dict | None = None) -> int | None:
    """Save an upload record to DB. Returns upload.id or None."""
    if not current_user.is_authenticated:
        return None
    try:
        up_dict = {
            "user_id": current_user.id,
            "filename": profile.get("filename", ""),
            "original_name": profile.get("filename", ""),
            "rows": profile.get("rows", 0),
            "cols": profile.get("cols", 0),
            "missing_pct": profile.get("missing_pct", 0.0),
            "source_type": source_type,
            "storage_path": json.dumps(source_config) if source_config and source_type != "csv" else None,
        }
        res = db_insert("uploads", up_dict)
        return res.get("id")
    except Exception as e:
        app.logger.warning("Failed to log upload: %s", e)
        return None


def _db_log_analysis(type_: str, summary: str = ""):
    """Save an analysis record to DB and push real-time WS event."""
    if not current_user.is_authenticated:
        return
    try:
        upload_id = _get_upload_id()
        an_dict = {
            "user_id": current_user.id,
            "upload_id": upload_id,
            "type": type_,
            "summary": summary,
        }
        res = db_insert("analyses", an_dict)
        uid = current_user.id
        _ws_push("activity", {
            "type":     type_,
            "summary":  summary,
            "filename": _get_filename(upload_id) if upload_id else "",
            "ts":       datetime.utcnow().isoformat(),
            "analysis_id": res.get("id"),
        }, user_id=uid)
        _ws_push("stats_update", {
            "uploads":  db_count("uploads", {"user_id": uid}),
            "analyses": db_count("analyses", {"user_id": uid}),
            "models":   db_count("analyses", {"user_id": uid, "type": "automl"}),
            "queries":  db_count("analyses", {"user_id": uid, "type": "query"}),
        }, user_id=uid)
    except Exception as e:
        app.logger.warning("Failed to log analysis: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _df_profile(df: pd.DataFrame, filename: str = "") -> dict:
    missing     = int(df.isnull().sum().sum())
    numeric_cnt = int(len(df.select_dtypes(include=np.number).columns))
    total_cells = df.shape[0] * df.shape[1]
    miss_pct    = round(missing / max(total_cells, 1) * 100, 1)
    columns = []
    for col, dtype in zip(df.columns, df.dtypes):
        null_pct = round(df[col].isnull().mean() * 100, 1)
        columns.append({"name": col, "dtype": str(dtype),
                        "null_pct": null_pct, "quality": round(100 - null_pct, 1)})
    return {"filename": filename, "rows": df.shape[0], "cols": df.shape[1],
            "numeric": numeric_cnt, "missing": missing, "missing_pct": miss_pct,
            "columns": columns}

def _safe_json_value(v):
    if isinstance(v, np.integer):   return int(v)
    if isinstance(v, np.floating):  return None if np.isnan(v) else float(v)
    if isinstance(v, np.bool_):     return bool(v)
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return None
    if isinstance(v, pd.Timestamp): return v.isoformat() if not pd.isna(v) else None
    try:
        if pd.isna(v): return None
    except (TypeError, ValueError):
        pass
    return v

def _df_to_json_rows(df: pd.DataFrame, limit: int = 500) -> dict:
    df = df.head(limit).replace([np.inf, -np.inf], None)
    headers = [str(c) for c in df.columns]
    rows = [[_safe_json_value(v) for v in row] for _, row in df.iterrows()]
    return {"headers": headers, "rows": rows, "total": len(df)}

def _time_ago(dt: datetime) -> str:
    diff = datetime.utcnow() - dt
    s = int(diff.total_seconds())
    if s < 60:    return "just now"
    if s < 3600:  return f"{s//60}m ago"
    if s < 86400: return f"{s//3600}h ago"
    if s < 604800: return f"{s//86400}d ago"
    return dt.strftime("%b %d")


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("index") + "?login=1")


@app.route("/login/google")
def login_google():
    if not GOOGLE_AUTH_ENABLED:
        return redirect(url_for("index") + "?login=1")
    redirect_uri = url_for("auth_google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def auth_google_callback():
    if not GOOGLE_AUTH_ENABLED:
        return redirect(url_for("index") + "?login=1")
    try:
        oauth.google.authorize_access_token()  # side-effect: validates + stores token
        resp     = oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo")
        userinfo = resp.json()
    except Exception as e:
        app.logger.error(f"Google OAuth callback error: {e}")
        return redirect(url_for("index") + "?login=1")

    google_id = userinfo.get("sub")
    if not google_id:
        return redirect(url_for("index") + "?login=1")

    user_data = db_first("users", {"google_id": google_id})
    if user_data is None:
        new_user = {
            "google_id": google_id,
            "email": userinfo.get("email"),
            "name": userinfo.get("name"),
            "avatar": userinfo.get("picture"),
        }
        res = db_insert("users", new_user)
        user = User(**res) if res else None
    else:
        db_update("users", user_data["id"], {
            "name": userinfo.get("name", user_data.get("name")),
            "avatar": userinfo.get("picture", user_data.get("avatar")),
            "last_login": datetime.utcnow().isoformat()
        })
        updated = db_get("users", user_data["id"])
        user = User(**updated) if updated else User(**user_data)

    if user:
        login_user(user, remember=True)
    return redirect(url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("upload.html", user=current_user, google_enabled=GOOGLE_AUTH_ENABLED)


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

    return render_template(
        "dashboard.html",
        user            = user,
        stats           = Stats(),
        recent_uploads  = uploads_data,
        recent_analyses = analyses_data,
        alert_count     = alert_count,
        recent_reports  = reports_data,
        schedule_count  = schedule_count,
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
# API: INSIGHT ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _persist_insights(upload_id, user_id, insights):
    try:
        db_delete("insight_records", upload_id) # actually needs to match upload_id, not id
        db_client.table("insight_records").delete().eq("upload_id", upload_id).execute()
        
        insert_data = []
        for ins in insights:
            insert_data.append({
                "upload_id": upload_id,
                "user_id": user_id,
                "type": ins.get("type", ""),
                "title": ins.get("title", ""),
                "description": ins.get("description", ""),
                "importance": ins.get("importance", 0.0),
                "chart_type": ins.get("chart"),
                "metric": ins.get("metric", ""),
                "chart_data": json.dumps(ins.get("chart_data")) if ins.get("chart_data") else None,
            })
        if insert_data:
            db_client.table("insight_records").insert(insert_data).execute()
    except Exception as e:
        app.logger.warning("Failed to bulk persist insights: %s", e)


@app.route("/api/insights/run", methods=["POST"])
@login_required
@_require_df
def api_insights_run(upload_id):
    if not REPORTING_ENABLED:
        return jsonify({"error": "Reporting engine not installed"}), 503

    if not _rate_limit(current_user.id, "insights"):
        return jsonify({"error": "Rate limit: max 3 insight jobs per minute"}), 429

    # Idempotency: don't queue a second job if one is already running
    existing = db_first("jobs", {"upload_id": upload_id, "type": "insights", "status": "started"})
    if existing:
        return jsonify({"task_id": existing["id"], "queued": False}), 200

    body    = request.get_json(force=True) or {}
    top_n   = int(body.get("top_n", 6))
    use_gem = bool(body.get("use_gemini", True))

    (task_run_insights, *_) = _tasks()
    job = task_run_insights.apply_async(args=[upload_id, current_user.id, top_n, use_gem])
    db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "insights"})
    _db_log_analysis("insights", "queued async")
    return jsonify({"task_id": job.id, "queued": True}), 202


@app.route("/api/insights/list")
@login_required
def api_insights_list():
    upload_id = _get_upload_id()
    if not upload_id:
        return jsonify([])
    recs = db_all("insight_records", {"upload_id": upload_id, "user_id": current_user.id})
    recs.sort(key=lambda x: x.get("importance", 0), reverse=True)
    return jsonify([{
        "id": r.get("id"), "type": r.get("type"), "title": r.get("title"), "description": r.get("description"),
        "importance": r.get("importance"), "chart_type": r.get("chart_type"), "metric": r.get("metric"),
        "chart_data": json.loads(r["chart_data"]) if r.get("chart_data") and isinstance(r["chart_data"], str) else r.get("chart_data"),
    } for r in recs])


# ══════════════════════════════════════════════════════════════════════════════
# API: REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/reports/generate", methods=["POST"])
@login_required
@_require_df
def api_report_generate(upload_id):
    if not REPORTING_ENABLED:
        return jsonify({"error": "Reporting engine not installed"}), 503

    existing = db_first("jobs", {"upload_id": upload_id, "type": "report", "status": "started"})
    if existing:
        return jsonify({"task_id": existing.get("id"), "queued": False}), 200

    (_, _, _, task_generate_report, _) = _tasks()
    job = task_generate_report.apply_async(args=[upload_id, current_user.id])
    db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "report"})
    _db_log_analysis("report", "queued async")
    return jsonify({"task_id": job.id, "queued": True}), 202


@app.route("/api/reports/<int:report_id>")
@login_required
def api_report_view(report_id):
    rep = db_get("reports", report_id)
    if not rep or rep.get("user_id") != current_user.id:
        return Response("Not found", status=404)
    return Response(rep.get("report_html", ""), mimetype="text/html")


@app.route("/api/reports/current")
@login_required
def api_report_current():
    upload_id = _get_upload_id()
    if not upload_id:
        return Response("upload_id required", status=400)
    html = _load(upload_id, "report_html")
    if not html:
        return Response("No report yet.", status=404)
    return Response(html, mimetype="text/html")


@app.route("/api/reports")
@login_required
def api_reports_list():
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

# ══════════════════════════════════════════════════════════════════════════════
# API: ALERTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/alerts")
@login_required
def api_alerts_list():
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

@app.route("/api/alerts/check", methods=["POST"])
@login_required
@_require_df
def api_alerts_check(upload_id):
    if not REPORTING_ENABLED:
        return jsonify({"ok": True, "alerts": []})

    # Check if a recently cached result is still valid (15-min TTL)
    cached = get_alert_status(upload_id)
    if cached:
        return jsonify({"ok": True, "from_cache": True, **cached})

    existing = db_first("jobs", {"upload_id": upload_id, "type": "alerts", "status": "started"})
    if existing:
        return jsonify({"task_id": existing.get("id"), "queued": False}), 200

    (_, _, _, _, task_check_alerts) = _tasks()
    job = task_check_alerts.apply_async(args=[upload_id, current_user.id])
    db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "alerts"})
    return jsonify({"task_id": job.id, "queued": True}), 202


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def api_alert_resolve(alert_id):
    a = db_get("alerts", alert_id)
    if not a or a.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404
        
    db_update("alerts", alert_id, {
        "resolved": True,
        "resolved_at": datetime.utcnow().isoformat()
    })
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# API: SCHEDULES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/schedules", methods=["GET"])
@login_required
def api_schedules_list():
    scheds = ReportSchedule.query.filter_by(user_id=current_user.id, enabled=True)\
                                  .order_by(ReportSchedule.created_at.desc()).all()
    return jsonify([{
        "id": s.id, "upload_id": s.upload_id,
        "filename": s.upload.filename if s.upload else "",
        "cron": s.cron_expression, "cron_human": s.cron_human,
        "email": s.email, "enabled": s.enabled,
        "last_run": s.last_run_at.isoformat() if s.last_run_at else None,
    } for s in scheds])


@app.route("/api/schedules", methods=["POST"])
@login_required
def api_schedules_create():
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
        return jsonify({"ok": True, "schedule_id": res.get("id"), "cron_human": ReportSchedule(**res).cron_human_text if res else ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
@login_required
def api_schedules_delete(schedule_id):
    sched = db_get("report_schedules", schedule_id)
    if not sched or sched.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404
    try:
        db_update("report_schedules", schedule_id, {"enabled": False})
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"error": "Failed to delete"}), 500


# ══════════════════════════════════════════════════════════════════════════════
# API: DATA SOURCES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/sources", methods=["GET"])
@login_required
def api_sources_list():
    sources = db_all("data_sources", {"user_id": current_user.id, "enabled": True})
    return jsonify([{
        "id": s.get("id"), "name": s.get("name"), "source_type": s.get("source_type"),
        "last_sync": s.get("last_sync"),
    } for s in sources])


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — workspace & projects
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/workspace")
@login_required
def workspace():
    return render_template(
        "workspace.html",
        user      = current_user,
        gemini_ok = gemini_available(),
    )


@app.route("/projects")
@login_required
def projects():
    return render_template("projects.html", user=current_user)


# ══════════════════════════════════════════════════════════════════════════════
# API: UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/upload", methods=["POST"])
def api_upload():
    if not current_user.is_authenticated:
        return jsonify({"error": "login_required"}), 401
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    try:
        df = pd.read_csv(f)
    except Exception as e:
        return jsonify({"error": f"Could not parse CSV: {e}"}), 400

    profile = _df_profile(df, f.filename)
    upload_id = _db_log_upload(profile)
    if not upload_id:
        return jsonify({"error": "Failed to create upload record"}), 500

    _save(upload_id, "df_raw", df)
    _save(upload_id, "profile", profile)
    _persist(upload_id, "df_raw", df)

    return jsonify({"ok": True, "profile": profile, "upload_id": upload_id})


@app.route("/api/upload/sheets", methods=["POST"])
def api_upload_sheets():
    if not current_user.is_authenticated:
        return jsonify({"error": "login_required"}), 401
    body = request.get_json(force=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        from dataforge.sheets_connector import SheetsConnector
        conn = SheetsConnector()
        import re as _re
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

    return jsonify({"ok": True, "profile": profile, "upload_id": upload_id})


# ══════════════════════════════════════════════════════════════════════════════
# API: WORKSPACE STATE  (restores UI on page reload)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/workspace/state")
@login_required
def api_workspace_state():
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

    clean_profile = None
    if df_clean is not None:
        clean_profile = _df_profile(df_clean, _get_filename(upload_id))

    # ── FIX 4b: detect "restored project with no disk data" ───────────────────
    # When a project was restored from DB but its pickle files don't exist
    # (uploaded before persistence was added), df_raw will be None even though
    # db_upload_id is set.  Surface this as needs_reupload so the workspace can
    # show a targeted prompt instead of a silent empty state.
    needs_reupload    = False
    reupload_filename = ""
    reupload_message  = ""
    reupload_source_type = "csv"
    upload_id = _get_upload_id()
    if upload_id and df_raw is None:
        try:
            up = db_get("uploads", upload_id)
            if up:
                src = up.get("source_type", "csv") or "csv"
                reupload_source_type = src
                up_filename = up.get("filename", "")

                # Google Sheets: attempt silent re-fetch before declaring reupload
                if src == "sheets" and up.get("storage_path"):
                    try:
                        src_cfg = json.loads(up.get("storage_path"))
                        sheet_id_r = src_cfg.get("sheet_id", "")
                        if sheet_id_r:
                            from dataforge.sheets_connector import SheetsConnector
                            df_refetch = SheetsConnector().load_public(sheet_id_r)
                            _save(upload_id, "df_raw", df_refetch)
                            df_raw = df_refetch                         # used below for state dict
                            profile = _df_profile(df_refetch, up_filename)
                            _save(upload_id, "profile", profile)
                            _persist(upload_id, "df_raw", df_refetch)  # cache for next time
                    except Exception:
                        pass  # fall through to needs_reupload

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
                            f"'{up_filename}' was saved before data persistence was enabled. "
                            "Re-upload the original file to continue your analysis."
                        )
                    # Populate profile from DB row so the workspace shows metadata
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
        # ── new fields ────────────────────────────────────────────────────────
        "needs_reupload":      needs_reupload,
        "reupload_filename":   reupload_filename,
        "reupload_message":    reupload_message,
        "source_type":         reupload_source_type,
    }
    return jsonify(state)


# ══════════════════════════════════════════════════════════════════════════════
# API: PREVIEW
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/preview")
@login_required
@_require_df

def api_preview(upload_id):
    limit = int(request.args.get("limit", 500))
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
                cols_list = [f'"{c.strip()}"' for c in cols.split(",")]
                select_clause = ", ".join(cols_list)
            else:
                select_clause = "*"
            
            preview_df = duckdb.execute(f"SELECT {select_clause} FROM '{str(p)}' LIMIT {limit}").df()
            return jsonify(_df_to_json_rows(preview_df, limit))
        except Exception as e:
            app.logger.warning("DuckDB preview failed: %s", e)

    _dc = _load(upload_id, "df_clean") if use_clean else None; df = _dc if _dc is not None else _load(upload_id, "df_raw")
    return jsonify(_df_to_json_rows(df, limit))


# ══════════════════════════════════════════════════════════════════════════════
# API: CLEAN
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/clean", methods=["POST"])
@login_required
@_require_df

def api_clean(upload_id):
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
            invalidate_upload(upload_id) # P2: Invalidate cache after clean
        except Exception:
            pass
        try:
            db_update("uploads", upload_id, {"clean_meta_json": json.dumps(meta, default=str)})
        except Exception as e:
            app.logger.warning("Failed to save clean_meta_json to DB: %s", e)

    _db_log_analysis("clean", f"Removed {result['stats'].get('rows_removed',0)} rows · "
                               f"{result['stats'].get('cols_removed',0)} cols dropped")
    return jsonify({
        "ok":             True,
        "stats":          result["stats"],
        "missing_log":    result["missing_log"],
        "struct_actions": result["struct_actions"],
        "clean_profile":  clean_profile,
    })


# ══════════════════════════════════════════════════════════════════════════════
# API: EDA
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/eda", methods=["POST"])
@login_required
@_require_df

def api_eda(upload_id):
    """
    FIX 1 — generate_eda_report() now returns a dict, not a raw HTML string.
    The old route did: html = generate_eda_report(df); _save(upload_id, "eda_html", html)
    which stored the whole dict as the html key, breaking /api/eda/report.

    New behaviour:
      • Always succeeds (no 500) — eda_report.py falls back to pandas on crash.
      • Returns {"ok": True, "rows_profiled": N, "warning": str|None}
        where warning is set if the full ydata-profiling report wasn't available
        (so the frontend can show a yellow notice without hiding the report).
    """
    body     = request.get_json(force=True) or {}
    minimal  = bool(body.get("minimal", True))
    sample_n = int(body.get("sample_n", 5000)) or 5000

    _dc = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")

    # generate_eda_report returns {"html": str, "error": str|None, "rows_profiled": int}
    # It never raises — on any failure it falls back to a lightweight pandas report.
    result = generate_eda_report(df, minimal=minimal, sample_n=sample_n)

    html          = result.get("html") or ""
    rows_profiled = result.get("rows_profiled", len(df))
    warning       = result.get("error")   # non-None means fallback was used

    if html:
        _save(upload_id, "eda_html", html)
        upload_id = _get_upload_id()
        if upload_id:
            _persist(upload_id, "eda_html", html)

    _db_log_analysis("eda", f"EDA report · {rows_profiled} rows profiled")

    return jsonify({
        "ok":           bool(html),
        "rows_profiled": rows_profiled,
        # "warning" (not "error") so the frontend shows a yellow notice, not a red
        # error block, when the fallback pandas report was used instead of ydata-profiling.
        "warning":      warning,
    })


@app.route("/api/eda/report")
@login_required
def api_eda_report():
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
/* Override Bootstrap 5 CSS custom properties FIRST so they cascade everywhere */
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
  --bs-table-bg: transparent;
  --bs-table-striped-bg: rgba(255,255,255,.025);
  --bs-table-hover-bg: rgba(255,255,255,.05);
  --bs-offcanvas-bg: #0d0d0f;
  --bs-offcanvas-color: #e0e0e0;
  --bs-modal-bg: #0d0d0f;
  --bs-modal-color: #e0e0e0;
  --bs-dropdown-bg: #0d0d0f;
  --bs-dropdown-link-color: #aaa;
  --bs-dropdown-link-hover-bg: rgba(46,91,255,.1);
  --bs-dropdown-link-hover-color: #fff;
  --bs-nav-tabs-border-color: #1a1a1c;
  --bs-nav-tabs-link-active-bg: #111113;
  --bs-nav-tabs-link-active-color: #fff;
  --bs-nav-tabs-link-active-border-color: #1a1a1c #1a1a1c #111113;
  --bs-accordion-bg: #0a0a0b;
  --bs-accordion-border-color: #1a1a1c;
  --bs-accordion-btn-bg: #111113;
  --bs-accordion-btn-color: #e0e0e0;
  --bs-accordion-active-bg: #0d0d0f;
  --bs-accordion-active-color: #fff;
  --bs-input-bg: #0d0d0f;
  --bs-input-color: #e0e0e0;
  --bs-input-border-color: #1a1a1c;
  --bs-code-color: #1e9902;
  --bs-link-color: #4d79ff;
  --bs-link-hover-color: #7a9bff;
}
html, body { background:#050505 !important; color:#e0e0e0 !important; }
/* containers */
.container,.container-fluid,.container-sm,.container-md,.container-lg,.container-xl,
section,article,main,.content,.wrapper,.page-content,#overview-content,
#variables-content,#correlations-content,#missing-content,#sample-content,
.report-container { background:#050505 !important; color:#e0e0e0 !important; }
/* navbar */
.navbar,.navbar-light,.navbar-dark,header,.page-header,nav[class*="navbar"] {
  background:#0a0a0b !important;
  border-bottom:1px solid #1a1a1c !important;
}
.navbar-brand,.navbar-nav .nav-link,.nav-link { color:#e0e0e0 !important; }
.navbar-toggler { border-color:#444 !important; }
.navbar-toggler-icon { filter:invert(1) brightness(.8); }
.navbar-collapse { background:#0a0a0b !important; }
/* offcanvas — hamburger panel (the white popup) */
.offcanvas,.offcanvas-start,.offcanvas-end,.offcanvas-top,.offcanvas-bottom,
[class*="offcanvas"] {
  background-color:#0d0d0f !important;
  color:#e0e0e0 !important;
  border-color:#1a1a1c !important;
}
.offcanvas-header { background:#0d0d0f !important; border-bottom:1px solid #1a1a1c !important; }
.offcanvas-title  { color:#fff !important; }
.offcanvas-body   { background:#0d0d0f !important; }
.offcanvas .nav-link { color:#ccc !important; }
.btn-close { filter:invert(1) brightness(.7); }
/* cards */
.card { background:#0a0a0b !important; border-color:#1a1a1c !important; color:#e0e0e0 !important; }
.card-header { background:#111113 !important; border-color:#1a1a1c !important; color:#e0e0e0 !important; }
.card-body   { background:#0a0a0b !important; color:#e0e0e0 !important; }
.card-footer { background:#0d0d0f !important; border-color:#1a1a1c !important; }
/* tabs */
.nav-tabs { background:transparent !important; border-color:#1a1a1c !important; }
.nav-tabs .nav-link { color:#888 !important; border-color:transparent !important; background:transparent !important; }
.nav-tabs .nav-link:hover { color:#ccc !important; }
.nav-tabs .nav-link.active,.nav-tabs .nav-item.show .nav-link {
  background:#111113 !important; color:#fff !important;
  border-color:#1a1a1c #1a1a1c #111113 !important;
}
.tab-content,.tab-pane { background:#0a0a0b !important; color:#e0e0e0 !important; }
/* tables */
table,.table { background:#0a0a0b !important; color:#cccccc !important; }
thead,.table thead tr { background:#111113 !important; }
th { background:#111113 !important; color:#888 !important; border-color:#1a1a1c !important; }
td { border-color:#1a1a1c !important; color:#cccccc !important; }
.table-bordered,.table-bordered td,.table-bordered th { border-color:#1a1a1c !important; }
.table-striped>tbody>tr:nth-of-type(odd)>* { background:rgba(255,255,255,.02) !important; }
.table-hover>tbody>tr:hover>* { background:rgba(255,255,255,.05) !important; }
/* typography */
h1,h2,h3,h4,h5,h6,.h1,.h2,.h3,.h4,.h5,.h6 { color:#fff !important; }
p,span,label,small,.text-muted { color:#aaa !important; }
a,a:hover { color:#4d79ff !important; }
strong,b { color:#e0e0e0 !important; }
code,pre { background:#111113 !important; color:#1e9902 !important; border-color:#1a1a1c !important; }
/* alerts/badges */
.alert { border-color:#1a1a1c !important; }
.alert-info    { background:rgba(46,91,255,.1) !important; color:#8ba4ff !important; border-color:rgba(46,91,255,.25) !important; }
.alert-warning { background:rgba(245,158,11,.1) !important; color:#f59e0b !important; border-color:rgba(245,158,11,.25) !important; }
.alert-danger  { background:rgba(239,68,68,.1) !important; color:#f87171 !important; border-color:rgba(239,68,68,.25) !important; }
.alert-success { background:rgba(16,185,129,.1) !important; color:#34d399 !important; border-color:rgba(16,185,129,.25) !important; }
.badge { color:#fff !important; }
.badge-success,.bg-success { background:rgba(16,185,129,.2) !important; color:#34d399 !important; }
.badge-warning,.bg-warning { background:rgba(245,158,11,.2) !important; color:#fbbf24 !important; }
.badge-danger,.bg-danger   { background:rgba(239,68,68,.2) !important; color:#f87171 !important; }
/* progress */
.progress { background:#1a1a1c !important; }
.progress-bar { background:#2E5BFF !important; }
/* inputs */
input,select,textarea,.form-control,.form-select {
  background:#0d0d0f !important; color:#e0e0e0 !important; border-color:#1a1a1c !important;
}
input:focus,select:focus,.form-control:focus { border-color:#2E5BFF !important; box-shadow:0 0 0 3px rgba(46,91,255,.15) !important; }
/* dropdowns */
.dropdown-menu { background:#0d0d0f !important; border-color:#1a1a1c !important; }
.dropdown-item { color:#aaa !important; }
.dropdown-item:hover,.dropdown-item:focus { background:rgba(46,91,255,.1) !important; color:#fff !important; }
.dropdown-divider { border-color:#1a1a1c !important; }
/* accordion */
.accordion-item { background:#0a0a0b !important; border-color:#1a1a1c !important; }
.accordion-button { background:#111113 !important; color:#e0e0e0 !important; box-shadow:none !important; }
.accordion-button:not(.collapsed) { background:#0d0d0f !important; color:#fff !important; }
.accordion-body { background:#0a0a0b !important; color:#ccc !important; }
/* list groups */
.list-group-item { background:#0a0a0b !important; border-color:#1a1a1c !important; color:#ccc !important; }
.list-group-item.active { background:rgba(46,91,255,.15) !important; color:#fff !important; border-color:rgba(46,91,255,.3) !important; }
/* modals */
.modal-content { background:#0d0d0f !important; border-color:#1a1a1c !important; color:#e0e0e0 !important; }
.modal-header  { background:#111113 !important; border-color:#1a1a1c !important; }
.modal-footer  { background:#111113 !important; border-color:#1a1a1c !important; }
.modal-backdrop.show { opacity:.8 !important; }
/* SVG / charts */
svg text { fill:#aaa !important; }
svg .axis path,svg .axis line { stroke:#333 !important; }
svg .gridline,svg .grid line { stroke:rgba(255,255,255,.06) !important; }
svg rect.bar,svg .bar { fill:#2E5BFF !important; }
svg .domain { stroke:#444 !important; }
.plot-container,.plotly,.js-plotly-plot { background:#0a0a0b !important; }
/* Bootstrap utilities */
.bg-light,.bg-white { background:#0a0a0b !important; }
.bg-dark  { background:#050505 !important; }
.text-dark { color:#e0e0e0 !important; }
.text-secondary,.text-muted { color:#888 !important; }
.border,[class*="border-"] { border-color:#1a1a1c !important; }
hr { border-color:#1a1a1c !important; opacity:.5; }
.shadow,.shadow-sm,.shadow-lg { box-shadow:0 2px 16px rgba(0,0,0,.6) !important; }
/* ydata-profiling specifics */
.variable-description-row { background:#0a0a0b !important; }
.col-sm-3.row-variable { color:#888 !important; }
.freq_table td:first-child { color:#e0e0e0 !important; }
.mini.histogram svg rect { fill:#2E5BFF !important; }
.collapse-toggle { color:#4d79ff !important; }
</style>"""
        if "</head>" in html:
            html = html.replace("</head>", dark_css + "\n</head>", 1)
        else:
            html = dark_css + html
    return Response(html, mimetype="text/html")


# ══════════════════════════════════════════════════════════════════════════════
# API: AUTOML
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/automl/detect-task", methods=["POST"])
@login_required
@_require_df

def api_automl_detect_task(upload_id):
    body = request.get_json(force=True) or {}
    target_col = body.get("target_col", "")
    _dc = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")
    if not target_col or target_col not in df.columns:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols     = df.select_dtypes(include=["object","category"]).columns.tolist()
        return jsonify({
            "error":           f"Column '{target_col}' not found" if target_col else "No target column specified",
            "candidates":      numeric_cols + cat_cols,
            "columns":         df.columns.tolist(),
            "needs_selection": True,
        }), 400
    task     = _detect_task(df[target_col])
    n_unique = int(df[target_col].nunique())
    return jsonify({"task": task, "n_unique": n_unique})


@app.route("/api/automl/train", methods=["POST"])
@login_required
@_require_df
def api_automl_train(upload_id):
    body = request.get_json(force=True) or {}
    target_col  = body.get("target_col", "")
    task_choice = body.get("task_choice", "auto-detect")
    time_budget = int(body.get("time_budget", 60))
    test_size   = float(body.get("test_size", 20)) / 100.0

    if not _rate_limit(current_user.id, "automl", limit=2, window_s=120):
        return jsonify({"error": "Rate limit: max 2 AutoML jobs per 2 minutes"}), 429

    # Validate target column exists before enqueuing
    _dc = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")
    if not target_col or target_col not in df.columns:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols     = df.select_dtypes(include=["object", "category"]).columns.tolist()
        return jsonify({
            "error":           f"Column '{target_col}' not found" if target_col else "No target column specified",
            "candidates":      numeric_cols + cat_cols,
            "needs_selection": True,
        }), 400

    # Idempotency: reuse existing running job
    existing = db_first("jobs", {"upload_id": upload_id, "type": "automl", "status": "started"})
    if existing:
        return jsonify({"task_id": existing.get("id"), "queued": False}), 200

    (_, task_run_automl, *_) = _tasks()
    job = task_run_automl.apply_async(
        args=[upload_id, current_user.id, target_col, task_choice, time_budget, test_size]
    )
    db_insert("jobs", {"id": job.id, "user_id": current_user.id, "upload_id": upload_id, "type": "automl"})
    _db_log_analysis("automl", f"queued · target={target_col} · budget={time_budget}s")
    return jsonify({"task_id": job.id, "queued": True}), 202


# ══════════════════════════════════════════════════════════════════════════════
# API: AI QUERY (chat)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/query", methods=["POST"])
@login_required
@_require_df

def api_query(upload_id):
    body = request.get_json(force=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400

    _dc = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")

    # Inject user-defined metric definitions into Gemini context
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


# ══════════════════════════════════════════════════════════════════════════════
# API: TASK STATUS  (poll from frontend after async dispatch)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/task/<task_id>")
@login_required
def api_task_status(task_id):
    """
    Combined status endpoint: merges our Job DB row with Celery's AsyncResult.
    DB is the source of truth for status; Celery result backend is a fallback.
    """
    job = db_get("jobs", task_id)
    if not job or job.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404

    # Try to enrich with Celery native state (handles edge cases like worker crash)
    celery_status = job.get("status")
    try:
        from celery.result import AsyncResult
        (task_run_insights, *_) = _tasks()          # any import just to get the celery instance
        res = AsyncResult(task_id)
        if res.state == "FAILURE" and job.get("status") not in ("failure", "success"):
            celery_status = "failure"
        elif res.state == "SUCCESS" and job.get("status") not in ("failure", "success"):
            celery_status = "success"
    except Exception:
        pass

    result_ref = None
    try:
        result_ref = json.loads(job.get("result_ref")) if job.get("result_ref") else None
    except Exception:
        pass

    return jsonify({
        "id":          job.get("id"),
        "type":        job.get("type"),
        "status":      celery_status,
        "result_ref":  result_ref,
        "error":       job.get("error"),
        "created_at":  job.get("created_at"),
        "finished_at": job.get("finished_at"),
    })


@app.route("/api/tasks")
@login_required
def api_tasks_list():
    """List recent jobs for the current user (last 20)."""
    jobs = db_all("jobs", {"user_id": current_user.id}, order_by="created_at", limit=20)
    return jsonify([{
        "id": j.get("id"), "type": j.get("type"), "status": j.get("status"), 
        "error": j.get("error"), "created_at": j.get("created_at")
    } for j in jobs])


# ══════════════════════════════════════════════════════════════════════════════
# API: PROJECTS  (list & restore)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/projects")
@login_required
def api_projects():
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


@app.route("/api/restore/<int:upload_id>", methods=["POST"])
@login_required
def api_restore(upload_id):
    """
    FIX 4 — Restore a saved project into the current session.

    Old behaviour: if pickle files were missing, _df_profile(None) would crash
    with AttributeError → 500, or return an empty profile that left the
    workspace in a broken state with no guidance for the user.

    New behaviour:
      • If pickle files exist  → restore normally (unchanged).
      • If NO pickle files     → set session identifiers, return
        needs_reupload=True + DB metadata so the workspace can show a
        targeted "re-upload" prompt instead of a silent broken state.
      • Never returns a 500 for the missing-files case.
    """
    up = db_get("uploads", upload_id)
    if not up or up.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404

    _clear_store(upload_id)

    # ── Try to load persisted data ────────────────────────────────────────────
    loaded_keys = []
    for key in ("df_raw", "df_clean", "eda_html", "model_pkl"):
        obj = _load_persisted(upload_id, key)
        if obj is not None:
            _save(upload_id, key, obj)
            loaded_keys.append(key)

    # ── No data on disk → try to auto-re-fetch (Sheets) or ask for re-upload ──
    if "df_raw" not in loaded_keys and "df_clean" not in loaded_keys:

        # Google Sheets: if we stored the URL in storage_path, re-fetch it now
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
                    # Re-persist so subsequent restores are fast
                    _persist(upload_id, "df_raw", df_refetch)
                    return jsonify({"ok": True, "needs_reupload": False, "profile": profile,
                                    "auto_restored": True, "source": "sheets"})
            except Exception:
                pass  # fall through to needs_reupload

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

        # Tailor the message to the source type
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

    # ── Normal restore ────────────────────────────────────────────────────────
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

    _dc = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")
    profile = _df_profile(df, up.get("filename", ""))
    _save(upload_id, "profile", profile)

    return jsonify({"ok": True, "needs_reupload": False, "profile": profile})


# ══════════════════════════════════════════════════════════════════════════════
# API: DOWNLOADS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/clean/download")
@login_required
@_require_df

def api_clean_download(upload_id):
    df = _load(upload_id, "df_clean")
    if df is None:
        return jsonify({"error": "No cleaned dataset. Run cleaning first."}), 404
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    fname = _get_filename(upload_id).replace(".csv", "_cleaned.csv")
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=fname,
    )


@app.route("/api/automl/download")
@login_required
def api_automl_download():
    upload_id = _get_upload_id()
    model_pkl = None
    if upload_id:
        model_pkl = _load_persisted(upload_id, "model_pkl")
    if model_pkl is None:
        return jsonify({"error": "No trained model found. Run AutoML first."}), 404
    return send_file(
        io.BytesIO(model_pkl),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name="dataforge_model.pkl",
    )


# ══════════════════════════════════════════════════════════════════════════════
# API: DASHBOARD STATS  (auto-generated KPIs + charts)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/dashboard/stats")
@login_required
@_require_df

def api_dashboard_stats(upload_id):
    _dc = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")
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
                "id":     "trend",
                "type":   "line",
                "title":  f"{metric} over time",
                "labels": [str(p) for p in agg.index[-24:]],
                "values": [round(float(v), 2) for v in agg.values[-24:]],
                "x_label": date_col,
                "y_label": metric,
            })
        except Exception:
            pass

    if cat_cols and numeric_cols:
        try:
            dim = cat_cols[0]
            metric = numeric_cols[0]
            grp = df.groupby(dim)[metric].sum().sort_values(ascending=False).head(10)
            charts.append({
                "id":     "top_cat",
                "type":   "bar",
                "title":  f"Top {dim} by {metric}",
                "labels": [str(i) for i in grp.index],
                "values": [round(float(v), 2) for v in grp.values],
                "x_label": dim,
                "y_label": metric,
            })
        except Exception:
            pass

    if numeric_cols:
        try:
            col = numeric_cols[0]
            s = df[col].dropna()
            hist, edges = np.histogram(s, bins=20)
            charts.append({
                "id":     "dist",
                "type":   "bar",
                "title":  f"{col} distribution",
                "labels": [f"{round(float(e),1)}" for e in edges[:-1]],
                "values": [int(v) for v in hist],
                "x_label": col,
                "y_label": "count",
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
        "ok":         True,
        "stats":      stats,
        "charts":     charts,
        "insights":   insights[:6],
        "summary":    summary,
        "schema":     schema_info,
        "profile":    profile,
    })



# ══════════════════════════════════════════════════════════════════════════════
# API: TRANSFORM ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/transform", methods=["POST"])
@login_required
@_require_df

def api_transform(upload_id):
    """Apply transformation steps to the current dataset."""
    if not TRANSFORM_ENABLED:
        return jsonify({"error": "Transform engine not available"}), 503
    body  = request.get_json(force=True) or {}
    steps = body.get("steps", [])
    reset = bool(body.get("reset", False))

    if reset:
        # Remove any saved transform — revert to clean/raw
        _save(upload_id, "df_transform", None)
        df_base = _load(upload_id, "df_clean")
        if df_base is None:
            df_base = _load(upload_id, "df_raw")
        if df_base is None:
             return jsonify({"error": "No dataset found to reset to"}), 400
        profile = _df_profile(df_base, _get_filename(upload_id))
        return jsonify({"ok": True, "reset": True, "profile": profile})

    # Base: use clean if available, else raw
    _dc = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")

    try:
        result = apply_transforms(df, steps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _save(upload_id, "df_transform", result.df)
    profile   = _df_profile(result.df, _get_filename(upload_id))
    # Return first 500 rows for preview
    preview   = _df_to_json_rows(result.df, 500)

    return jsonify({
        "ok":      True,
        "profile": profile,
        "preview": preview,
        "result":  result.to_dict(),
        "errors":  result.errors,
    })


@app.route("/api/transform/preview", methods=["GET"])
@login_required
def api_transform_preview():
    """Return the current transformed dataset (or clean/raw if no transform saved)."""
    upload_id = _get_upload_id()
    if not upload_id:
        return jsonify({"error": "upload_id parameter is required"}), 400
    p = _upath(upload_id, "df_transform").with_suffix('.parquet')
    if not p.exists(): p = _upath(upload_id, "df_clean").with_suffix('.parquet')
    if not p.exists(): p = _upath(upload_id, "df_raw").with_suffix('.parquet')
    
    if p.exists():
        try:
            import duckdb
            preview_df = duckdb.execute(f"SELECT * FROM '{str(p)}' LIMIT 500").df()
            return jsonify(_df_to_json_rows(preview_df, 500))
        except Exception as e:
            app.logger.warning("DuckDB transform preview failed: %s", e)
            
    df = _load(upload_id, "df_transform") or _load(upload_id, "df_clean") or _load(upload_id, "df_raw")
    if df is None:
        return jsonify({"error": "No dataset loaded"}), 400
    return jsonify(_df_to_json_rows(df, 500))

@app.route("/api/delete/<int:upload_id>", methods=["DELETE"])
@login_required
def api_delete_upload(upload_id):
    upload, err = _get_upload_or_403(upload_id)
    if err:
        return err
    
    db_delete("uploads", upload.id)
    
    _clear_store(upload_id)
    return jsonify({"ok": True})



# ══════════════════════════════════════════════════════════════════════════════
# API: ROOT CAUSE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/insights/root-cause", methods=["POST"])
@login_required
@_require_df

def api_root_cause(upload_id):
    """Run segment contribution / root cause analysis."""
    if not TRANSFORM_ENABLED:
        return jsonify({"error": "Transform module not available"}), 503

    body    = request.get_json(force=True) or {}
    _dc     = _load(upload_id, "df_clean"); df = _dc if _dc is not None else _load(upload_id, "df_raw")

    # Auto-detect metric and dimensions from schema if not supplied
    schema    = _load(upload_id, "last_schema") or {}
    metric    = body.get("metric") or (schema.get("metrics") or [None])[0]
    dimensions = body.get("dimensions") or schema.get("dimensions") or []
    date_col  = body.get("date_col") or schema.get("date")
    top_n     = int(body.get("top_n", 6))

    if not metric:
        # Fall back to first numeric column
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if num_cols:
            metric = num_cols[0]
        else:
            return jsonify({"error": "No numeric metric column found"}), 400

    if not dimensions:
        # Fall back to first few object columns
        obj_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        dimensions = obj_cols[:3]

    try:
        result = run_root_cause(
            df=df, metric=metric, dimensions=dimensions,
            date_col=date_col, top_n=top_n,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _db_log_analysis("insights", f"Root cause: {metric} · {len(result.get('drivers', []))} drivers")
    return jsonify({"ok": True, **result})


# ══════════════════════════════════════════════════════════════════════════════
# API: METRIC DEFINITIONS  (semantic layer for AI Query)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/metrics", methods=["GET"])
@login_required
def api_metrics_list():
    """List all metric definitions for the current user."""
    metrics = db_all("metric_definitions", {"user_id": current_user.id}, order_by="created_at")
    return jsonify([{
        "id": m.get("id"), "name": m.get("name"), "formula": m.get("formula"),
        "description": m.get("description"), "category": m.get("category"),
        "created_at": m.get("created_at")
    } for m in metrics])


@app.route("/api/metrics", methods=["POST"])
@login_required
def api_metrics_create():
    """Create or update a metric definition."""
    body = request.get_json(force=True) or {}
    name    = (body.get("name") or "").strip()
    formula = (body.get("formula") or "").strip()
    if not name or not formula:
        return jsonify({"error": "name and formula are required"}), 400

    # Upsert — update existing metric with same name
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


@app.route("/api/metrics/<int:metric_id>", methods=["DELETE"])
@login_required
def api_metrics_delete(metric_id):
    """Delete a metric definition."""
    m = db_get("metric_definitions", metric_id)
    if not m or m.get("user_id") != current_user.id:
        return jsonify({"error": "Not found"}), 404
        
    db_delete("metric_definitions", metric_id)
    return jsonify({"ok": True})


@app.route("/api/metrics/context", methods=["GET"])
@login_required
def api_metrics_context():
    """Return metric definitions formatted as a Gemini prompt context block."""
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

if __name__ == "__main__":
    socketio.run(
        app,
        debug=True,
        host="0.0.0.0",
        port=5000,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
