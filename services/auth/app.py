import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session
from flask_login import current_user, login_user, logout_user

ROOT_DIR = Path(__file__).resolve().parents[2]
os.environ.setdefault("DATAFORGE_ROOT", str(ROOT_DIR))
SHARED_DIR = ROOT_DIR / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

load_dotenv(override=True, dotenv_path=ROOT_DIR / ".env")

from dataforge.db import User, db_first, db_get, db_insert, db_update

from .shared import (
    build_auth_url,
    build_web_url,
    google_auth_enabled,
    init_google_oauth,
    init_shared_auth,
    normalize_relative_url,
    register_auth_template_globals,
)

app = Flask(__name__, template_folder="templates", static_folder="../web/static")
init_shared_auth(app)
register_auth_template_globals(app)
oauth = init_google_oauth(app)


@app.route("/")
def index():
    return redirect(build_auth_url("/login"))


@app.route("/healthz")
def healthz():
    return {"ok": True, "service": "auth"}


@app.route("/login")
def login_page():
    next_url = normalize_relative_url(request.args.get("next"), "/dashboard")
    if current_user.is_authenticated:
        return redirect(build_web_url(next_url))
    return render_template(
        "login.html",
        google_enabled=google_auth_enabled(),
        next_url=next_url,
    )


@app.route("/login/google")
def login_google():
    next_url = normalize_relative_url(request.args.get("next"), "/dashboard")
    if not google_auth_enabled():
        return redirect(build_auth_url("/login", next_url=next_url))
    session["next_url"] = next_url
    redirect_uri = build_auth_url("/auth/google/callback")
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def auth_google_callback():
    if not google_auth_enabled():
        return redirect(build_auth_url("/login"))

    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.userinfo(token=token)
    except Exception as exc:
        app.logger.error("Google OAuth callback error: %s", exc)
        return redirect(build_auth_url("/login"))

    google_id = userinfo.get("sub")
    if not google_id:
        return redirect(build_auth_url("/login"))

    try:
        user_data = db_first("users", {"google_id": google_id})
        if user_data is None:
            created = db_insert(
                "users",
                {
                    "google_id": google_id,
                    "email": userinfo.get("email"),
                    "name": userinfo.get("name"),
                    "avatar": userinfo.get("picture"),
                    "last_login": datetime.utcnow().isoformat(),
                },
            )
            user = User(**created)
        else:
            db_update(
                "users",
                user_data["id"],
                {
                    "name": userinfo.get("name", user_data.get("name")),
                    "avatar": userinfo.get("picture", user_data.get("avatar")),
                    "last_login": datetime.utcnow().isoformat(),
                },
            )
            user = User(**(db_get("users", user_data["id"]) or user_data))
    except Exception as exc:
        app.logger.error("Google OAuth DB error: %s", exc)
        return redirect(build_auth_url("/login"))

    login_user(user, remember=True)
    next_url = normalize_relative_url(session.pop("next_url", None), "/dashboard")
    return redirect(build_web_url(next_url))


@app.route("/logout")
def logout():
    logout_user()
    next_url = normalize_relative_url(request.args.get("next"), "/")
    return redirect(build_web_url(next_url))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=True)
