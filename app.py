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

import os, io, uuid, json, pickle, tempfile, traceback
from datetime import datetime
from pathlib import Path
from functools import wraps

import pandas as pd
import numpy as np
from flask import (Flask, render_template, request, jsonify, session,
                   send_file, redirect, url_for, Response, flash)
from dotenv import load_dotenv

load_dotenv(override=True)

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", uuid.uuid4().hex)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

# ── WebSocket via flask-socketio ───────────────────────────────────────────────
from flask_socketio import SocketIO, emit as ws_emit_raw, join_room
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading",
                    logger=False, engineio_logger=False)

def _ws_push(event: str, data: dict, user_id: int | None = None):
    """Emit a socketio event to a specific user's room (or broadcast)."""
    try:
        room = f"user_{user_id}" if user_id else None
        socketio.emit(event, data, room=room, namespace="/")
    except Exception:
        pass  # WebSocket push is best-effort — never break the HTTP response

# ── Database ───────────────────────────────────────────────────────────────────
# ── Database — Supabase Postgres (SQLite fallback for local dev) ──────────────
_PG_URL = os.getenv("DATABASE_URL", "")
if _PG_URL:
    # Supabase / standard Postgres connection string
    # Fix "postgres://" → "postgresql://" (SQLAlchemy 2.x requirement)
    if _PG_URL.startswith("postgres://"):
        _PG_URL = "postgresql://" + _PG_URL[len("postgres://"):]
    app.config["SQLALCHEMY_DATABASE_URI"] = _PG_URL
    # For Supabase pooled connections, disable pre-ping overhead per-request
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle":  300,
        "connect_args":  {"sslmode": "require"},
    }
else:
    # Local SQLite fallback
    DB_PATH = Path(__file__).parent / "instance" / "dataforge.db"
    DB_PATH.parent.mkdir(exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

from modules.models import (db, User, Upload, Analysis,
                             InsightRecord, Report, Alert,
                             ReportSchedule, DataSource, MetricDefinition)
db.init_app(app)

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
    return db.session.get(User, int(user_id))

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
PROJECTS_DIR = Path(__file__).parent / "instance" / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

def _get_upload_user_id(upload_id: int):
    """Return the user_id for an Upload row (used by Supabase storage helpers)."""
    try:
        up = db.session.get(Upload, upload_id)
        return up.user_id if up else None
    except Exception:
        return None


def _persist(upload_id: int, key: str, obj):
    """
    Write-through storage: always saves to local disk, also pushes to
    Supabase Storage when configured (for durability across deploys).
    """
    # ── Local write (original behaviour, always runs) ─────────────────────────
    d = PROJECTS_DIR / str(upload_id)
    d.mkdir(exist_ok=True)
    with open(d / key, "wb") as f:
        pickle.dump(obj, f)

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
            else:
                path = store.upload_pickle(user_id, upload_id, key, obj)
            # Persist the storage path into the Upload row for df_raw
            if key == "df_raw":
                try:
                    up = db.session.get(Upload, upload_id)
                    if up:
                        up.storage_path = path
                        db.session.commit()
                except Exception:
                    db.session.rollback()
        except Exception as _exc:
            app.logger.warning("Supabase _persist failed (key=%s): %s", key, _exc)


def _load_persisted(upload_id: int, key: str):
    """
    Load persisted data: tries local disk first (fast), falls back to
    Supabase Storage (handles cases where local disk was cleared after deploy).
    On Supabase hit, re-caches to local disk for subsequent fast reads.
    """
    # ── Local read ────────────────────────────────────────────────────────────
    p = PROJECTS_DIR / str(upload_id) / key
    if p.exists():
        try:
            with open(p, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass

    # ── Supabase fallback ─────────────────────────────────────────────────────
    if STORAGE_OK:
        try:
            user_id = _get_upload_user_id(upload_id)
            if user_id is None:
                return None
            store = get_store()
            if key in ("df_raw", "df_clean"):
                csv_key = "raw" if key == "df_raw" else "clean"
                spath   = f"users/{user_id}/uploads/{upload_id}/{csv_key}.csv"
                obj     = store.download_dataframe(spath)
            else:
                spath = f"users/{user_id}/uploads/{upload_id}/{key}.pkl"
                obj   = store.download_pickle(spath)

            if obj is not None:
                # Re-cache locally for next time
                d = PROJECTS_DIR / str(upload_id)
                d.mkdir(exist_ok=True)
                with open(d / key, "wb") as f:
                    pickle.dump(obj, f)
                app.logger.info("Restored %s/%s from Supabase Storage.", upload_id, key)
            return obj
        except Exception as _exc:
            app.logger.warning("Supabase _load_persisted failed (key=%s): %s", key, _exc)

    return None

def _project_meta(upload_id: int) -> dict:
    d = PROJECTS_DIR / str(upload_id)
    return {
        "has_raw":   (d / "df_raw").exists(),
        "has_clean": (d / "df_clean").exists(),
        "has_eda":   (d / "eda_html").exists(),
        "has_model": (d / "model_pkl").exists(),
        "has_chat":  (d / "chat_history").exists(),
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
import sys
sys.path.insert(0, str(Path(__file__).parent))
from modules.data_cleaner   import run_cleaning_pipeline
from modules.eda_report     import generate_eda_report
from modules.automl_trainer import run_automl, _detect_task
from modules.gemini_pipeline import run_query_pipeline, is_available as gemini_available

# ── Reporting engine ────────────────────────────────────────────────────────────
try:
    from modules.insight_engine  import detect_schema, run_insights, summarise_with_gemini, build_report_text
    from modules.report_generator import generate_html_report
    from modules.alert_engine     import AlertEngine
    REPORTING_ENABLED = True
except ImportError as _re:
    REPORTING_ENABLED = False
    print(f"[WARN] Reporting engine not loaded: {_re}")

# ── Transform Engine & Root Cause Analysis ────────────────────────────────────
try:
    from modules.transform_engine import apply_transforms
    from modules.root_cause import run_root_cause
    TRANSFORM_ENABLED = True
except ImportError as _te:
    TRANSFORM_ENABLED = False
    print(f"[WARN] Transform engine not loaded: {_te}")

# ── Supabase Storage (graceful fallback to local disk if not configured) ────────
try:
    from modules.supabase_storage import get_store, STORAGE_OK
except ImportError:
    STORAGE_OK = False
    def get_store(): return None

with app.app_context():
    db.create_all()
    from sqlalchemy import text
    with db.engine.connect() as _c:
        for _s in [
            # uploads
            "ALTER TABLE uploads ADD COLUMN original_name TEXT",
            "ALTER TABLE uploads ADD COLUMN missing_pct REAL DEFAULT 0.0",
            "ALTER TABLE uploads ADD COLUMN chat_history TEXT",
            "ALTER TABLE uploads ADD COLUMN clean_meta_json TEXT",
            "ALTER TABLE uploads ADD COLUMN automl_meta_json TEXT",
            "ALTER TABLE uploads ADD COLUMN source_type TEXT DEFAULT 'csv'",
            "ALTER TABLE uploads ADD COLUMN source_id INTEGER",
            "ALTER TABLE uploads ADD COLUMN storage_path TEXT",
            # insight_records
            "ALTER TABLE insight_records ADD COLUMN type TEXT",
            "ALTER TABLE insight_records ADD COLUMN title TEXT",
            "ALTER TABLE insight_records ADD COLUMN description TEXT",
            "ALTER TABLE insight_records ADD COLUMN importance REAL DEFAULT 0.0",
            "ALTER TABLE insight_records ADD COLUMN chart_type TEXT",
            "ALTER TABLE insight_records ADD COLUMN metric TEXT",
            "ALTER TABLE insight_records ADD COLUMN chart_data TEXT",
            # reports
            "ALTER TABLE reports ADD COLUMN filename TEXT",
            "ALTER TABLE reports ADD COLUMN report_json TEXT",
            "ALTER TABLE reports ADD COLUMN storage_path TEXT",
            # alerts  ← NEW
            "ALTER TABLE alerts ADD COLUMN filename TEXT",
            "ALTER TABLE alerts ADD COLUMN colour TEXT",
            "ALTER TABLE alerts ADD COLUMN metric TEXT",
            "ALTER TABLE alerts ADD COLUMN pct_change REAL",
            "ALTER TABLE alerts ADD COLUMN resolved_at DATETIME",
            # metric_definitions (new table — columns added after db.create_all)
            "ALTER TABLE metric_definitions ADD COLUMN category TEXT DEFAULT 'general'",
            "ALTER TABLE metric_definitions ADD COLUMN description TEXT",
            "ALTER TABLE metric_definitions ADD COLUMN updated_at DATETIME",
            # report_schedules  ← NEW
            "ALTER TABLE report_schedules ADD COLUMN cron TEXT",
            "ALTER TABLE report_schedules ADD COLUMN cron_human TEXT",
            "ALTER TABLE report_schedules ADD COLUMN email TEXT",
            "ALTER TABLE report_schedules ADD COLUMN last_run DATETIME",
            "ALTER TABLE report_schedules ADD COLUMN created_at DATETIME",
        ]:
            try: _c.execute(text(_s)); _c.commit()
            except Exception: pass


# ══════════════════════════════════════════════════════════════════════════════
# SESSION HELPERS  — DataFrames too large for cookie; store on disk
# ══════════════════════════════════════════════════════════════════════════════
def _sid() -> str:
    if "store_id" not in session:
        session["store_id"] = uuid.uuid4().hex
    return session["store_id"]

def _path(key: str) -> Path:
    return STORE_DIR / f"{_sid()}_{key}"

def _save(key: str, obj):
    with open(_path(key), "wb") as f:
        pickle.dump(obj, f)

def _load(key: str):
    p = _path(key)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return pickle.load(f)

def _clear_store():
    sid = _sid()
    for p in STORE_DIR.glob(f"{sid}_*"):
        p.unlink(missing_ok=True)

def _require_df(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if _load("df_raw") is None:
            return jsonify({"error": "No dataset uploaded. Please upload a CSV first."}), 400
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
        up = Upload(
            user_id      = current_user.id,
            filename     = profile.get("filename", ""),
            original_name = profile.get("filename", ""),
            rows         = profile.get("rows", 0),
            cols         = profile.get("cols", 0),
            missing_pct  = profile.get("missing_pct", 0.0),
            source_type  = source_type,
            # For Google Sheets: storage_path stores the JSON config (url, sheet_id)
            # so it can be re-fetched on restore. For CSV: filled by _persist().
            storage_path = json.dumps(source_config) if source_config and source_type != "csv" else None,
        )
        db.session.add(up)
        db.session.commit()
        session["db_upload_id"] = up.id
        return up.id
    except Exception:
        db.session.rollback()
        return None


def _db_log_analysis(type_: str, summary: str = ""):
    """Save an analysis record to DB and push real-time WS event."""
    if not current_user.is_authenticated:
        return
    try:
        an = Analysis(
            user_id   = current_user.id,
            upload_id = session.get("db_upload_id"),
            type      = type_,
            summary   = summary,
        )
        db.session.add(an)
        db.session.commit()
        uid = current_user.id
        _ws_push("activity", {
            "type":     type_,
            "summary":  summary,
            "filename": session.get("filename", ""),
            "ts":       datetime.utcnow().isoformat(),
            "analysis_id": an.id,
        }, user_id=uid)
        _ws_push("stats_update", {
            "uploads":  current_user.total_uploads,
            "analyses": current_user.total_analyses,
            "models":   current_user.total_models,
            "queries":  current_user.total_queries,
        }, user_id=uid)
    except Exception:
        db.session.rollback()


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
        token = oauth.google.authorize_access_token()
        resp     = oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo")
        userinfo = resp.json()
    except Exception as e:
        app.logger.error(f"Google OAuth callback error: {e}")
        return redirect(url_for("index") + "?login=1")

    google_id = userinfo.get("sub")
    if not google_id:
        return redirect(url_for("index") + "?login=1")

    user = User.query.filter_by(google_id=google_id).first()
    if user is None:
        user = User(
            google_id = google_id,
            email     = userinfo.get("email"),
            name      = userinfo.get("name"),
            avatar    = userinfo.get("picture"),
        )
        db.session.add(user)
    else:
        user.name       = userinfo.get("name", user.name)
        user.avatar     = userinfo.get("picture", user.avatar)
        user.last_login = datetime.utcnow()

    db.session.commit()
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
    from sqlalchemy import func as sqfunc

    user = current_user
    recent_uploads = (
        Upload.query.filter_by(user_id=user.id)
        .order_by(Upload.uploaded_at.desc()).limit(10).all()
    )

    def _time_ago_local(dt):
        if not dt:
            return ""
        diff = datetime.utcnow() - dt
        s = int(diff.total_seconds())
        if s < 60:       return "just now"
        if s < 3600:     return f"{s//60}m ago"
        if s < 86400:    return f"{s//3600}h ago"
        return f"{s//86400}d ago"

    uploads_data = [{
        "filename":    u.filename,
        "rows":        getattr(u, "rows", 0) or 0,
        "cols":        getattr(u, "cols", 0) or 0,
        "missing_pct": getattr(u, "missing_pct", 0) or 0,
        "time_ago":    _time_ago_local(u.uploaded_at),
        "id":          u.id,
        "source_type": getattr(u, "source_type", "csv") or "csv",
    } for u in recent_uploads]

    _icon_map = {"eda": "📊", "automl": "🤖", "clean": "🧹", "query": "💬",
                 "insights": "💡", "report": "📄"}
    recent_analyses = (
        Analysis.query.filter_by(user_id=user.id)
        .order_by(Analysis.created_at.desc()).limit(30).all()
    )
    analyses_data = [{
        "type":     a.type,
        "label":    a.label,
        "icon":     _icon_map.get(a.type, "⚡"),
        "summary":  a.summary or "",
        "filename": a.upload.filename if a.upload else "",
        "time_ago": _time_ago_local(a.created_at),
    } for a in recent_analyses]

    alert_count = Alert.query.filter_by(user_id=user.id, resolved=False).count()
    recent_reports = Report.query.filter_by(user_id=user.id)\
                                 .order_by(Report.created_at.desc()).limit(5).all()
    reports_data = [{
        "id": r.id,
        "filename": r.upload.filename if r.upload else "",
        "triggered_by": r.triggered_by,
        "time_ago": _time_ago_local(r.created_at),
    } for r in recent_reports]

    schedule_count = ReportSchedule.query.filter_by(user_id=user.id, enabled=True).count()

    class Stats:
        uploads  = user.total_uploads
        analyses = user.total_analyses
        models   = user.total_models
        queries  = user.total_queries

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
        InsightRecord.query.filter_by(upload_id=upload_id).delete()
        for ins in insights:
            db.session.add(InsightRecord(
                upload_id=upload_id, user_id=user_id,
                type=ins.get("type",""), title=ins.get("title",""),
                description=ins.get("description",""), importance=ins.get("importance",0.0),
                chart_type=ins.get("chart"), metric=ins.get("metric",""),
                chart_data=json.dumps(ins.get("chart_data")) if ins.get("chart_data") else None,
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route("/api/insights/run", methods=["POST"])
@login_required
@_require_df
def api_insights_run():
    if not REPORTING_ENABLED:
        return jsonify({"error": "Reporting engine not installed"}), 503
    body = request.get_json(force=True) or {}
    top_n = int(body.get("top_n", 6))
    use_gem = bool(body.get("use_gemini", True))

    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")
    automl_meta = _load("automl_meta")
    fi = {}
    if automl_meta and isinstance(automl_meta, dict):
        fi = {r["feature"]: r["importance"] for r in automl_meta.get("feature_importance", []) if isinstance(r, dict)}

    schema = detect_schema(df, feature_importance=fi)
    insights = run_insights(df, schema, top_n=top_n)

    gemini_fn = None
    if use_gem and gemini_available():
        try:
            from modules.gemini_pipeline import _call_gemini
            gemini_fn = _call_gemini
        except Exception:
            pass

    filename = session.get("filename", "Dataset")
    summary = summarise_with_gemini(insights, dataset_name=filename,
                                    dataset_type=schema["dataset_type"], gemini_fn=gemini_fn)

    upload_id = session.get("db_upload_id")
    if upload_id:
        _persist_insights(upload_id, current_user.id, insights)
        _save("last_insights", insights)
        _save("last_schema", schema)
        _save("last_summary", summary)
        _ws_push("insight_ready", {
            "count": len(insights), "dataset_type": schema["dataset_type"],
            "filename": filename, "ts": datetime.utcnow().isoformat(),
        }, user_id=current_user.id)

    _db_log_analysis("insights", f"{len(insights)} insights · {schema['dataset_type']}")
    return jsonify({"ok": True, "insights": list(insights), "summary": summary,
                    "schema": {"date": schema.get("date"), "metrics": schema.get("metrics", []),
                               "dimensions": schema.get("dimensions", []),
                               "dataset_type": schema.get("dataset_type")}})


@app.route("/api/insights/list")
@login_required
def api_insights_list():
    upload_id = session.get("db_upload_id")
    if not upload_id:
        return jsonify([])
    recs = InsightRecord.query.filter_by(upload_id=upload_id, user_id=current_user.id)\
                              .order_by(InsightRecord.importance.desc()).all()
    return jsonify([{
        "id": r.id, "type": r.type, "title": r.title, "description": r.description,
        "importance": r.importance, "chart_type": r.chart_type, "metric": r.metric,
        "chart_data": json.loads(r.chart_data) if r.chart_data else None,
    } for r in recs])


# ══════════════════════════════════════════════════════════════════════════════
# API: REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/reports/generate", methods=["POST"])
@login_required
@_require_df
def api_report_generate():
    if not REPORTING_ENABLED:
        return jsonify({"error": "Reporting engine not installed"}), 503
    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")
    insights = _load("last_insights")
    schema = _load("last_schema")
    summary = _load("last_summary")

    if not insights:
        fi = {}
        automl_meta = _load("automl_meta")
        if automl_meta and isinstance(automl_meta, dict):
            fi = {r["feature"]: r["importance"] for r in automl_meta.get("feature_importance", []) if isinstance(r, dict)}
        schema = detect_schema(df, feature_importance=fi)
        insights = run_insights(df, schema, top_n=6)
        summary = summarise_with_gemini(insights, dataset_name=session.get("filename","Dataset"),
                                        dataset_type=schema["dataset_type"])

    profile = _load("profile") or {}
    filename = session.get("filename", "Dataset")
    html = generate_html_report(
        insights=insights, summary_text=summary or "",
        dataset_name=filename, dataset_type=(schema or {}).get("dataset_type","general"),
        profile=profile,
    )
    upload_id = session.get("db_upload_id")
    report_id = None
    if upload_id:
        rep = Report(
            upload_id=upload_id, user_id=current_user.id,
            report_html=html,
            report_json=json.dumps({"summary": summary, "insights": [
                {k:v for k,v in i.items() if k!="chart_data"} for i in insights
            ]}, default=str),
            triggered_by="manual",
        )
        db.session.add(rep)
        try:
            db.session.commit()
            report_id = rep.id
            _ws_push("report_ready", {"report_id": report_id, "filename": filename,
                                       "ts": datetime.utcnow().isoformat()},
                     user_id=current_user.id)
        except Exception:
            db.session.rollback()
    _save("report_html", html)
    return jsonify({"ok": True, "report_id": report_id})


@app.route("/api/reports/<int:report_id>")
@login_required
def api_report_view(report_id):
    rep = db.session.get(Report, report_id)
    if not rep or rep.user_id != current_user.id:
        return Response("Not found", status=404)
    return Response(rep.report_html, mimetype="text/html")


@app.route("/api/reports/current")
@login_required
def api_report_current():
    html = _load("report_html")
    if not html:
        return Response("No report yet.", status=404)
    return Response(html, mimetype="text/html")


@app.route("/api/reports")
@login_required
def api_reports_list():
    reps = Report.query.filter_by(user_id=current_user.id)\
                       .order_by(Report.created_at.desc()).limit(50).all()
    out = []
    for r in reps:
        try:
            fname = r.upload.filename if r.upload else (r.filename or "")
        except Exception:
            fname = getattr(r, "filename", "") or ""
        out.append({
            "id": r.id, "upload_id": r.upload_id,
            "filename": fname,
            "triggered_by": r.triggered_by,
            "created_at": r.created_at.isoformat(),
        })
    return jsonify(out)

# ══════════════════════════════════════════════════════════════════════════════
# API: ALERTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/alerts")
@login_required
def api_alerts_list():
    alerts = Alert.query.filter_by(user_id=current_user.id, resolved=False)\
                        .order_by(Alert.triggered_at.desc()).limit(100).all()
    out = []
    for a in alerts:
        try:
            fname = a.upload.filename if a.upload else (getattr(a, "filename", "") or "")
        except Exception:
            fname = getattr(a, "filename", "") or ""
        out.append({
            "id": a.id, "upload_id": a.upload_id,
            "filename": fname,
            "rule": a.rule, "message": a.message, "severity": a.severity,
            "colour": getattr(a, "colour", getattr(a, "severity_colour", "#F59E0B")),
            "metric": getattr(a, "metric", ""),
            "pct_change": getattr(a, "pct_change", None),
            "triggered_at": a.triggered_at.isoformat(),
        })
    return jsonify(out)

@app.route("/api/alerts/check", methods=["POST"])
@login_required
@_require_df
def api_alerts_check():
    if not REPORTING_ENABLED:
        return jsonify({"ok": True, "alerts": []})
    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")
    upload_id = session.get("db_upload_id")
    if not upload_id:
        return jsonify({"ok": True, "alerts": []})
    schema = _load("last_schema") or detect_schema(df)
    engine = AlertEngine()
    fired_raw = engine.check(upload_id, df, schema)
    fired = []
    for a in fired_raw:
        row = Alert(upload_id=upload_id, user_id=current_user.id,
                    rule=a["rule"], message=a["message"], severity=a["severity"],
                    metric=a.get("metric",""), pct_change=a.get("pct_change"))
        db.session.add(row)
        fired.append(a)
    try:
        db.session.commit()
        for a in fired:
            _ws_push("alert", {**a, "filename": session.get("filename",""),
                                "ts": datetime.utcnow().isoformat()},
                     user_id=current_user.id)
    except Exception:
        db.session.rollback()
    return jsonify({"ok": True, "alerts": fired, "count": len(fired)})


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def api_alert_resolve(alert_id):
    a = db.session.get(Alert, alert_id)
    if not a or a.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    a.resolved = True
    a.resolved_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
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
    upload_id = body.get("upload_id") or session.get("db_upload_id")
    cron = body.get("cron", "0 9 * * 1")
    email = (body.get("email") or "").strip()
    if not upload_id:
        return jsonify({"error": "upload_id required — upload a dataset first"}), 400
    upload = db.session.get(Upload, upload_id)
    if not upload or upload.user_id != current_user.id:
        return jsonify({"error": "Upload not found"}), 404
    sched = ReportSchedule(upload_id=upload_id, user_id=current_user.id,
                           cron_expression=cron, email=email, enabled=True)
    db.session.add(sched)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "schedule_id": sched.id, "cron_human": sched.cron_human})


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
@login_required
def api_schedules_delete(schedule_id):
    sched = db.session.get(ReportSchedule, schedule_id)
    if not sched or sched.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    sched.enabled = False
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# API: DATA SOURCES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/sources", methods=["GET"])
@login_required
def api_sources_list():
    sources = DataSource.query.filter_by(user_id=current_user.id, enabled=True).all()
    return jsonify([{
        "id": s.id, "name": s.name, "source_type": s.source_type,
        "last_sync": s.last_sync.isoformat() if s.last_sync else None,
    } for s in sources])


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — workspace & projects
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/workspace")
@login_required
def workspace():
    profile = _load("profile") or None
    return render_template(
        "workspace.html",
        user      = current_user,
        profile   = profile,
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

    _clear_store()
    _save("df_raw", df)
    session["filename"] = f.filename

    profile = _df_profile(df, f.filename)
    _save("profile", profile)
    session["profile"] = profile

    # Log to DB first so we have an upload_id for Supabase path storage
    upload_id = _db_log_upload(profile)
    if upload_id:
        # _persist handles both local disk and Supabase (write-through)
        _persist(upload_id, "df_raw", df)

    return jsonify({"ok": True, "profile": profile})


@app.route("/api/upload/sheets", methods=["POST"])
def api_upload_sheets():
    if not current_user.is_authenticated:
        return jsonify({"error": "login_required"}), 401
    body = request.get_json(force=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        from modules.sheets_connector import SheetsConnector
        conn = SheetsConnector()
        import re as _re
        m = _re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if not m:
            return jsonify({"error": "Invalid Google Sheets URL"}), 400
        sheet_id = m.group(1)
        df = conn.load_public(sheet_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    _clear_store()
    _save("df_raw", df)
    fname = f"sheets_{sheet_id[:8]}.csv"
    session["filename"] = fname

    profile = _df_profile(df, fname)
    _save("profile", profile)
    session["profile"] = profile

    # BUG FIX: capture upload_id (was discarded) so we can persist the data
    # and store the Sheets URL for re-fetching on project restore.
    source_config = {"url": url, "sheet_id": sheet_id}
    upload_id = _db_log_upload(profile, source_type="sheets", source_config=source_config)
    if upload_id:
        _persist(upload_id, "df_raw", df)   # save to local disk + Supabase

    return jsonify({"ok": True, "profile": profile})


# ══════════════════════════════════════════════════════════════════════════════
# API: WORKSPACE STATE  (restores UI on page reload)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/workspace/state")
@login_required
def api_workspace_state():
    profile     = _load("profile") or {}
    df_raw      = _load("df_raw")
    df_clean    = _load("df_clean")
    clean_meta  = _load("clean_meta")
    automl_meta = _load("automl_meta")
    chat_history = _load("chat_history") or []
    has_eda     = _path("eda_html").exists()

    clean_profile = None
    if df_clean is not None:
        clean_profile = _df_profile(df_clean, session.get("filename", ""))

    # ── FIX 4b: detect "restored project with no disk data" ───────────────────
    # When a project was restored from DB but its pickle files don't exist
    # (uploaded before persistence was added), df_raw will be None even though
    # db_upload_id is set.  Surface this as needs_reupload so the workspace can
    # show a targeted prompt instead of a silent empty state.
    needs_reupload    = False
    reupload_filename = ""
    reupload_message  = ""
    reupload_source_type = "csv"
    upload_id = session.get("db_upload_id")
    if upload_id and df_raw is None:
        try:
            up = db.session.get(Upload, upload_id)
            if up:
                src = getattr(up, "source_type", "csv") or "csv"
                reupload_source_type = src

                # Google Sheets: attempt silent re-fetch before declaring reupload
                if src == "sheets" and up.storage_path:
                    try:
                        src_cfg = json.loads(up.storage_path)
                        sheet_id_r = src_cfg.get("sheet_id", "")
                        if sheet_id_r:
                            from modules.sheets_connector import SheetsConnector
                            df_refetch = SheetsConnector().load_public(sheet_id_r)
                            _save("df_raw", df_refetch)
                            df_raw = df_refetch                         # used below for state dict
                            profile = _df_profile(df_refetch, up.filename)
                            _save("profile", profile)
                            session["profile"] = profile
                            _persist(upload_id, "df_raw", df_refetch)  # cache for next time
                    except Exception:
                        pass  # fall through to needs_reupload

                if df_raw is None:
                    needs_reupload    = True
                    reupload_filename = up.filename
                    if src == "sheets":
                        reupload_message = (
                            f"Could not re-fetch '{up.filename}' from Google Sheets. "
                            "The sheet may be private or the URL changed. Re-connect it."
                        )
                    else:
                        reupload_message = (
                            f"'{up.filename}' was saved before data persistence was enabled. "
                            "Re-upload the original file to continue your analysis."
                        )
                    # Populate profile from DB row so the workspace shows metadata
                    if not profile:
                        profile = {
                            "filename":    up.filename,
                            "rows":        getattr(up, "rows", 0) or 0,
                            "cols":        getattr(up, "cols", 0) or 0,
                            "missing_pct": getattr(up, "missing_pct", 0.0) or 0.0,
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
        "filename":          session.get("filename", ""),
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
def api_preview():
    limit = int(request.args.get("limit", 500))
    use_clean = request.args.get("clean") == "true"
    _dc = _load("df_clean") if use_clean else None; df = _dc if _dc is not None else _load("df_raw")
    return jsonify(_df_to_json_rows(df, limit))


# ══════════════════════════════════════════════════════════════════════════════
# API: CLEAN
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/clean", methods=["POST"])
@login_required
@_require_df
def api_clean():
    df_raw = _load("df_raw")
    try:
        result = run_cleaning_pipeline(df_raw)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    df_clean = result["df_clean"]
    _save("df_clean", df_clean)

    clean_profile = _df_profile(df_clean, session.get("filename", ""))
    meta = {
        "stats":          result["stats"],
        "missing_log":    result["missing_log"],
        "struct_actions": result["struct_actions"],
        "clean_profile":  clean_profile,
    }
    _save("clean_meta", meta)

    upload_id = session.get("db_upload_id")
    if upload_id:
        _persist(upload_id, "df_clean", df_clean)
        try:
            up = db.session.get(Upload, upload_id)
            if up:
                up.clean_meta_json = json.dumps(meta, default=str)
                db.session.commit()
        except Exception:
            db.session.rollback()

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
def api_eda():
    """
    FIX 1 — generate_eda_report() now returns a dict, not a raw HTML string.
    The old route did: html = generate_eda_report(df); _save("eda_html", html)
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

    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")

    # generate_eda_report returns {"html": str, "error": str|None, "rows_profiled": int}
    # It never raises — on any failure it falls back to a lightweight pandas report.
    result = generate_eda_report(df, minimal=minimal, sample_n=sample_n)

    html          = result.get("html") or ""
    rows_profiled = result.get("rows_profiled", len(df))
    warning       = result.get("error")   # non-None means fallback was used

    if html:
        _save("eda_html", html)
        upload_id = session.get("db_upload_id")
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
    html = _load("eda_html")
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
def api_automl_detect_task():
    body = request.get_json(force=True) or {}
    target_col = body.get("target_col", "")
    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")
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
def api_automl_train():
    body = request.get_json(force=True) or {}
    target_col  = body.get("target_col", "")
    task_choice = body.get("task_choice", "auto-detect")
    time_budget = int(body.get("time_budget", 60))
    test_size   = float(body.get("test_size", 20)) / 100.0

    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")
    if not target_col or target_col not in df.columns:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols     = df.select_dtypes(include=["object","category"]).columns.tolist()
        return jsonify({
            "error":           f"Column '{target_col}' not found" if target_col else "No target column specified",
            "candidates":      numeric_cols + cat_cols,
            "columns":         df.columns.tolist(),
            "needs_selection": True,
        }), 400

    result = run_automl(df, target_col,
                        task_choice=task_choice,
                        time_budget=time_budget,
                        test_size=test_size)
    if result.get("error"):
        return jsonify(result), 500

    # Strip bytes before saving to session store / returning as JSON
    # model_pkl is bytes — jsonify() raises TypeError if it's included
    model_pkl = result.pop("model_pkl", None)
    result["target_col"] = target_col
    _save("automl_meta", result)

    upload_id = session.get("db_upload_id")
    if upload_id:
        if model_pkl:
            _persist(upload_id, "model_pkl", model_pkl)
        try:
            up = db.session.get(Upload, upload_id)
            if up:
                up.automl_meta_json = json.dumps(result, default=str)
                db.session.commit()
        except Exception:
            db.session.rollback()

    _db_log_analysis("automl",
        f"{result.get('best_estimator','?')} · {result.get('task','?')} · "
        f"{result.get('elapsed_s','?')}s")
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# API: AI QUERY (chat)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/query", methods=["POST"])
@login_required
@_require_df
def api_query():
    body = request.get_json(force=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400

    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")

    # Inject user-defined metric definitions into Gemini context
    metric_context = ""
    if current_user.is_authenticated:
        try:
            user_metrics = MetricDefinition.query.filter_by(user_id=current_user.id).all()
            if user_metrics:
                lines = ["Defined business metrics:"]
                for m in user_metrics:
                    l = f"  {m.name} = {m.formula}"
                    if m.description:
                        l += f"  # {m.description}"
                    lines.append(l)
                metric_context = "\n".join(lines)
        except Exception:
            pass

    try:
        result = run_query_pipeline(query, df, metric_context=metric_context)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    history = _load("chat_history") or []
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
    _save("chat_history", history)

    upload_id = session.get("db_upload_id")
    if upload_id:
        try:
            up = db.session.get(Upload, upload_id)
            if up:
                up.chat_history = json.dumps(history, default=str)
                db.session.commit()
        except Exception:
            db.session.rollback()

    _db_log_analysis("query", query[:120])
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# API: PROJECTS  (list & restore)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/projects")
@login_required
def api_projects():
    uploads = (Upload.query
               .filter_by(user_id=current_user.id)
               .order_by(Upload.uploaded_at.desc())
               .limit(50).all())
    result = []
    for u in uploads:
        meta = _project_meta(u.id)
        result.append({
            "id":          u.id,
            "filename":    u.filename,
            "rows":        getattr(u, "rows", 0) or 0,
            "cols":        getattr(u, "cols", 0) or 0,
            "missing_pct": getattr(u, "missing_pct", 0) or 0,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else "",
            "source_type": getattr(u, "source_type", "csv") or "csv",
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
    up = db.session.get(Upload, upload_id)
    if not up or up.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404

    _clear_store()
    session["db_upload_id"] = upload_id
    session["filename"]     = up.filename

    # ── Try to load persisted data ────────────────────────────────────────────
    loaded_keys = []
    for key in ("df_raw", "df_clean", "eda_html", "model_pkl"):
        obj = _load_persisted(upload_id, key)
        if obj is not None:
            _save(key, obj)
            loaded_keys.append(key)

    # ── No data on disk → try to auto-re-fetch (Sheets) or ask for re-upload ──
    if "df_raw" not in loaded_keys and "df_clean" not in loaded_keys:

        # Google Sheets: if we stored the URL in storage_path, re-fetch it now
        source_type = getattr(up, "source_type", "csv") or "csv"
        if source_type == "sheets" and up.storage_path:
            try:
                source_cfg = json.loads(up.storage_path)
                sheet_url  = source_cfg.get("url", "")
                sheet_id_r = source_cfg.get("sheet_id", "")
                if sheet_id_r:
                    from modules.sheets_connector import SheetsConnector
                    df_refetch = SheetsConnector().load_public(sheet_id_r)
                    _save("df_raw", df_refetch)
                    profile = _df_profile(df_refetch, up.filename)
                    _save("profile", profile)
                    session["profile"] = profile
                    # Re-persist so subsequent restores are fast
                    _persist(upload_id, "df_raw", df_refetch)
                    return jsonify({"ok": True, "needs_reupload": False, "profile": profile,
                                    "auto_restored": True, "source": "sheets"})
            except Exception as _se:
                pass  # fall through to needs_reupload

        profile = {
            "filename":    up.filename,
            "rows":        getattr(up, "rows", 0) or 0,
            "cols":        getattr(up, "cols", 0) or 0,
            "missing_pct": getattr(up, "missing_pct", 0.0) or 0.0,
            "missing":     0,
            "numeric":     0,
            "columns":     [],
        }
        _save("profile", profile)
        session["profile"] = profile

        # Tailor the message to the source type
        if source_type == "sheets":
            msg = (f"Could not re-fetch '{up.filename}' from Google Sheets. "
                   "The sheet may have been made private or the URL changed. "
                   "Re-connect the sheet to continue.")
        else:
            msg = (f"'{up.filename}' was saved before data persistence was enabled. "
                   "Re-upload the original file to continue your analysis.")

        return jsonify({
            "ok":             True,
            "needs_reupload": True,
            "source_type":    source_type,
            "profile":        profile,
            "message":        msg,
        })

    # ── Normal restore ────────────────────────────────────────────────────────
    if up.clean_meta_json:
        try:
            _save("clean_meta", json.loads(up.clean_meta_json))
        except Exception:
            pass

    if up.automl_meta_json:
        try:
            _save("automl_meta", json.loads(up.automl_meta_json))
        except Exception:
            pass

    if up.chat_history:
        try:
            _save("chat_history", json.loads(up.chat_history))
        except Exception:
            pass

    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")
    profile = _df_profile(df, up.filename)
    _save("profile", profile)
    session["profile"] = profile

    return jsonify({"ok": True, "needs_reupload": False, "profile": profile})


# ══════════════════════════════════════════════════════════════════════════════
# API: DOWNLOADS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/clean/download")
@login_required
@_require_df
def api_clean_download():
    df = _load("df_clean")
    if df is None:
        return jsonify({"error": "No cleaned dataset. Run cleaning first."}), 404
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    fname = session.get("filename", "data.csv").replace(".csv", "_cleaned.csv")
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=fname,
    )


@app.route("/api/automl/download")
@login_required
def api_automl_download():
    upload_id = session.get("db_upload_id")
    model_pkl = None
    if upload_id:
        model_pkl = _load_persisted(upload_id, "model_pkl")
    if model_pkl is None:
        return jsonify({"error": "No trained model found. Run AutoML first."}), 404
    return send_file(
        io.BytesIO(pickle.dumps(model_pkl)),
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
def api_dashboard_stats():
    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")
    profile = _load("profile") or {}

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

    schema = _load("last_schema")
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

    insights = _load("last_insights") or []
    summary  = _load("last_summary") or ""
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
def api_transform():
    """Apply transformation steps to the current dataset."""
    if not TRANSFORM_ENABLED:
        return jsonify({"error": "Transform engine not available"}), 503
    body  = request.get_json(force=True) or {}
    steps = body.get("steps", [])
    reset = bool(body.get("reset", False))

    if reset:
        # Remove any saved transform — revert to clean/raw
        _save("df_transform", None)
        df = _load("df_clean") or _load("df_raw")
        profile = _df_profile(df, session.get("filename", ""))
        return jsonify({"ok": True, "reset": True, "profile": profile})

    # Base: use clean if available, else raw
    _dc = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")

    try:
        result = apply_transforms(df, steps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _save("df_transform", result.df)
    profile   = _df_profile(result.df, session.get("filename", ""))
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
    df = _load("df_transform") or _load("df_clean") or _load("df_raw")
    if df is None:
        return jsonify({"error": "No dataset loaded"}), 400
    return jsonify(_df_to_json_rows(df, 500))


# ══════════════════════════════════════════════════════════════════════════════
# API: ROOT CAUSE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/insights/root-cause", methods=["POST"])
@login_required
@_require_df
def api_root_cause():
    """Run segment contribution / root cause analysis."""
    if not TRANSFORM_ENABLED:
        return jsonify({"error": "Transform module not available"}), 503

    body    = request.get_json(force=True) or {}
    _dc     = _load("df_clean"); df = _dc if _dc is not None else _load("df_raw")

    # Auto-detect metric and dimensions from schema if not supplied
    schema    = _load("last_schema") or {}
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
    metrics = MetricDefinition.query.filter_by(user_id=current_user.id)                                    .order_by(MetricDefinition.created_at.desc()).all()
    return jsonify([m.to_dict() for m in metrics])


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
    existing = MetricDefinition.query.filter_by(
        user_id=current_user.id, name=name
    ).first()
    if existing:
        existing.formula     = formula
        existing.description = body.get("description", existing.description)
        existing.category    = body.get("category", existing.category or "general")
        existing.updated_at  = datetime.utcnow()
    else:
        existing = MetricDefinition(
            user_id     = current_user.id,
            name        = name,
            formula     = formula,
            description = body.get("description", ""),
            category    = body.get("category", "general"),
        )
        db.session.add(existing)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True, "metric": existing.to_dict()})


@app.route("/api/metrics/<int:metric_id>", methods=["DELETE"])
@login_required
def api_metrics_delete(metric_id):
    """Delete a metric definition."""
    m = db.session.get(MetricDefinition, metric_id)
    if not m or m.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(m)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"ok": True})


@app.route("/api/metrics/context", methods=["GET"])
@login_required
def api_metrics_context():
    """Return metric definitions formatted as a Gemini prompt context block."""
    metrics = MetricDefinition.query.filter_by(user_id=current_user.id).all()
    if not metrics:
        return jsonify({"context": ""})
    lines = ["Defined business metrics:"]
    for m in metrics:
        line = f"  {m.name} = {m.formula}"
        if m.description:
            line += f"  # {m.description}"
        lines.append(line)
    return jsonify({"context": "\n".join(lines)})

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False)