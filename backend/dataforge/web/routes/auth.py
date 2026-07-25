"""
routes/auth.py — Authentication Blueprint
"""
from flask import Blueprint, redirect, url_for, request, session, jsonify
from flask_login import login_required, login_user, logout_user, current_user
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


def init_auth(app, oauth_instance, google_auth_enabled):
    """
    Called once from app.py after blueprint registration.
    Binds the OAuth instance and flag that live on the app level.
    """
    auth_bp.oauth = oauth_instance
    auth_bp.google_enabled = google_auth_enabled


@auth_bp.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))
    return redirect(url_for("upload_bp.index") + "?login=1")


@auth_bp.route("/login/google")
def login_google():
    if not auth_bp.google_enabled:
        return redirect(url_for("upload_bp.index") + "?login=1")
    next_url = request.args.get("next") or url_for("dashboard_bp.dashboard")
    if not isinstance(next_url, str) or not next_url.startswith("/"):
        next_url = url_for("dashboard_bp.dashboard")
    session["next_url"] = next_url
    redirect_uri = url_for("auth.auth_google_callback", _external=True)
    return auth_bp.oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback")
def auth_google_callback():
    from flask import current_app
    from dataforge.db import db_get, db_first, db_insert, db_update
    from dataforge.db import User

    if not auth_bp.google_enabled:
        return redirect(url_for("upload_bp.index") + "?login=1")
    try:
        token    = auth_bp.oauth.google.authorize_access_token()
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = auth_bp.oauth.google.userinfo(token=token)
    except Exception as e:
        current_app.logger.error(f"Google OAuth callback error: {e}")
        return redirect(url_for("upload_bp.index") + "?login=1&error=oauth")

    google_id = userinfo.get("sub")
    if not google_id:
        return redirect(url_for("upload_bp.index") + "?login=1")

    try:
        user_data = db_first("users", {"google_id": google_id})
        if user_data is None and userinfo.get("email"):
            user_data = db_first("users", {"email": userinfo.get("email")})

        if user_data is None:
            new_user = {
                "google_id": google_id,
                "email": userinfo.get("email"),
                "name": userinfo.get("name"),
                "avatar": userinfo.get("picture"),
            }
            res = db_insert("users", new_user)
            if not res:
                current_app.logger.error("Google OAuth: db_insert('users') returned None — check SUPABASE_KEY in .env")
                return redirect(url_for("upload_bp.index") + "?login=1&error=db")
            user = User(**res)
        else:
            db_update("users", user_data["id"], {
                "google_id": google_id,
                "name": userinfo.get("name", user_data.get("name")),
                "avatar": userinfo.get("picture", user_data.get("avatar")),
                "last_login": datetime.utcnow().isoformat()
            })
            updated = db_get("users", user_data["id"])
            user = User(**updated) if updated else User(**user_data)

        login_user(user, remember=True)
        next_url = session.pop("next_url", None)
        if isinstance(next_url, str) and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("dashboard_bp.dashboard"))
    except Exception as e:
        current_app.logger.error(f"Google OAuth DB error: {e}")
        return redirect(url_for("upload_bp.index") + "?login=1&error=db")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("upload_bp.index"))


@auth_bp.route("/login/mock")
def mock_login():
    from dataforge.db import db_get, User
    from flask_login import login_user
    user_data = db_get("users", 1)
    if user_data:
        user = User(**user_data)
        login_user(user, remember=True)
        return "Logged in as mock user Faheem!"
    return "Mock user not found in DB", 404
