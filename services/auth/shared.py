import os
import sys
from pathlib import Path
from urllib.parse import urlencode

from authlib.integrations.flask_client import OAuth
from flask import jsonify, redirect, request
from flask_login import LoginManager

ROOT_DIR = Path(__file__).resolve().parents[2]
os.environ.setdefault("DATAFORGE_ROOT", str(ROOT_DIR))
SHARED_DIR = ROOT_DIR / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from dataforge.db import User, db_get


DEFAULT_AUTH_BASE_URL = "http://localhost:5001"
DEFAULT_WEB_BASE_URL = "http://localhost:5000"


def _clean_base_url(url: str | None, fallback: str) -> str:
    value = (url or fallback).strip()
    return value.rstrip("/")


def get_auth_base_url() -> str:
    return _clean_base_url(os.getenv("AUTH_BASE_URL"), DEFAULT_AUTH_BASE_URL)


def get_web_base_url() -> str:
    return _clean_base_url(os.getenv("WEB_BASE_URL"), DEFAULT_WEB_BASE_URL)


def google_auth_enabled() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))


def normalize_relative_url(value: str | None, fallback: str = "/") -> str:
    if not value or not isinstance(value, str):
        return fallback
    if not value.startswith("/") or value.startswith("//"):
        return fallback
    return value


def build_service_url(base_url: str, path: str, next_url: str | None = None) -> str:
    url = f"{base_url}{'/' + path.lstrip('/')}"
    safe_next = normalize_relative_url(next_url, fallback=None) if next_url else None
    if safe_next:
        return f"{url}?{urlencode({'next': safe_next})}"
    return url


def build_auth_url(path: str, next_url: str | None = None) -> str:
    return build_service_url(get_auth_base_url(), path, next_url=next_url)


def build_web_url(path: str = "/") -> str:
    return build_service_url(get_web_base_url(), path)


def _request_target() -> str:
    full_path = (request.full_path or request.path or "/").rstrip("?")
    return normalize_relative_url(full_path, "/")


def configure_shared_session(app) -> None:
    session_cookie_name = os.getenv("DATAFORGE_SESSION_COOKIE_NAME", "dataforge_session")
    remember_cookie_name = os.getenv("DATAFORGE_REMEMBER_COOKIE_NAME", "dataforge_remember")
    secure_cookies = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    same_site = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    cookie_domain = os.getenv("SESSION_COOKIE_DOMAIN")

    app.secret_key = os.getenv("FLASK_SECRET_KEY") or app.secret_key or "dataforge-dev-secret"
    app.config["SESSION_COOKIE_NAME"] = session_cookie_name
    app.config["REMEMBER_COOKIE_NAME"] = remember_cookie_name
    app.config["SESSION_COOKIE_SECURE"] = secure_cookies
    app.config["REMEMBER_COOKIE_SECURE"] = secure_cookies
    app.config["SESSION_COOKIE_SAMESITE"] = same_site
    app.config["REMEMBER_COOKIE_SAMESITE"] = same_site
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["AUTH_BASE_URL"] = get_auth_base_url()
    app.config["WEB_BASE_URL"] = get_web_base_url()
    if cookie_domain:
        app.config["SESSION_COOKIE_DOMAIN"] = cookie_domain
        app.config["REMEMBER_COOKIE_DOMAIN"] = cookie_domain


def init_shared_auth(app) -> LoginManager:
    configure_shared_session(app)

    login_manager = LoginManager()
    login_manager.login_message = ""
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        login_url = build_auth_url("/login", next_url=_request_target())
        wants_json = (
            request.path.startswith("/api/")
            or "application/json" in request.headers.get("Accept", "")
            or request.headers.get("Content-Type", "").startswith("application/json")
        )
        if wants_json:
            return jsonify({"error": "Authentication required", "redirect": login_url}), 401
        return redirect(login_url)

    @login_manager.user_loader
    def load_user(user_id: str):
        data = db_get("users", int(user_id))
        return User(**data) if data else None

    return login_manager


def register_auth_template_globals(app) -> None:
    @app.context_processor
    def inject_auth_urls():
        return {
            "auth_base_url": get_auth_base_url(),
            "auth_login_url": lambda next_url="/": build_auth_url("/login", next_url=next_url),
            "auth_google_login_url": lambda next_url="/": build_auth_url("/login/google", next_url=next_url),
            "auth_logout_url": lambda next_url="/": build_auth_url("/logout", next_url=next_url),
            "google_auth_enabled": google_auth_enabled(),
        }


def init_google_oauth(app) -> OAuth:
    oauth = OAuth(app)
    if google_auth_enabled():
        oauth.register(
            name="google",
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    return oauth
