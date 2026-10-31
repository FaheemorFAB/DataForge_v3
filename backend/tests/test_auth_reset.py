"""
backend/tests/test_auth_reset.py
────────────────────────────────
Unit and integration tests for Password Reset via Resend, Token Verification,
and Google OAuth Continuity.
"""

import pytest
from dotenv import load_dotenv
load_dotenv(".env")

from fastapi.testclient import TestClient
from dataforge.api.app import create_app
from dataforge.api.routes.auth import (
    create_password_reset_token,
    verify_password_reset_token,
    mark_reset_token_used,
    _load_reset_tokens,
)


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_password_reset_token_lifecycle():
    email = "qa-reset@dataforge.app"
    token = create_password_reset_token(email)
    assert token and len(token) > 20

    is_valid, reason, token_email = verify_password_reset_token(token)
    assert is_valid is True
    assert token_email == email

    # Consume token
    mark_reset_token_used(token)
    is_valid_after, reason_after, _ = verify_password_reset_token(token)
    assert is_valid_after is False
    assert "already been used" in reason_after


def test_forgot_and_reset_flow(client: TestClient):
    test_email = "analyst-reset@numan-10.site"

    # 1. Request forgot password link
    resp = client.post("/api/auth/password/forgot", json={"email": test_email})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    # 2. Extract token from storage
    tokens = _load_reset_tokens()
    token = None
    for t, d in tokens.items():
        if d.get("email") == test_email and not d.get("used"):
            token = t
            break
    assert token is not None

    # 3. Verify token via API
    resp_v = client.get(f"/api/auth/password/verify-token?token={token}")
    assert resp_v.status_code == 200
    assert resp_v.json()["valid"] is True
    assert "numan-10.site" in resp_v.json()["email"]

    # 4. Reject short password
    resp_short = client.post("/api/auth/password/reset", json={"token": token, "new_password": "short"})
    assert resp_short.status_code == 400

    # 5. Successfully update password
    resp_reset = client.post("/api/auth/password/reset", json={"token": token, "new_password": "NewStrongPass99!"})
    assert resp_reset.status_code == 200
    reset_data = resp_reset.json()
    assert reset_data["ok"] is True
    assert "token" in reset_data
    assert reset_data["user"]["email"] == test_email

    # 6. Replay attack rejection
    resp_replay = client.post("/api/auth/password/reset", json={"token": token, "new_password": "AnotherPassword1!"})
    assert resp_replay.status_code == 400


def test_google_oauth_continuity(client: TestClient):
    """Ensures Google OAuth login endpoint remains 100% functional and unmolested."""
    resp = client.get("/api/auth/login/google", follow_redirects=False)
    assert resp.status_code in (302, 307)
    loc = resp.headers.get("location", "")
    assert "accounts.google.com" in loc

