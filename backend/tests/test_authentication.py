"""
backend/tests/test_authentication.py
───────────────────────────────────
Security Suite: Authentication enforcement and token validation.
Verifies fail-closed behavior for all unauthenticated, invalid, or expired tokens.
"""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.auth.jwt import create_access_token
from dataforge.api.config import get_settings

settings = get_settings()


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


def test_unauthenticated_protected_routes_return_401(client):
    """Protected endpoints must return 401 when no token or cookie is supplied."""
    protected_endpoints = [
        ("GET", "/api/workspace/state?upload_id=mock-upload"),
        ("GET", "/api/models"),
        ("GET", "/api/teams"),
        ("GET", "/api/subscription"),
        ("POST", "/api/automl/train"),
        ("POST", "/api/dashboard/stats?upload_id=mock-upload"),
        ("GET", "/api/pipeline/export?upload_id=mock-upload"),
        ("POST", "/api/joins/preview"),
    ]
    for method, endpoint in protected_endpoints:
        if method == "GET":
            res = client.get(endpoint)
        else:
            res = client.post(endpoint, json={})
        assert res.status_code == 401, f"{method} {endpoint} returned {res.status_code}, expected 401"
        assert res.headers.get("www-authenticate") == "Bearer"


def test_invalid_token_returns_401(client):
    """Malformed tokens must be rejected with 401."""
    headers = {"Authorization": "Bearer invalid.jwt.signature"}
    res = client.get("/api/models", headers=headers)
    assert res.status_code == 401


def test_expired_token_returns_401(client):
    """Tokens with past expiration must be rejected with 401."""
    expired_payload = {
        "sub": "101",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "type": "access",
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {expired_token}"}
    res = client.get("/api/models", headers=headers)
    assert res.status_code == 401


def test_token_with_wrong_secret_returns_401(client):
    """Tokens signed with a different secret must be rejected."""
    wrong_secret_token = jwt.encode(
        {"sub": "101", "exp": datetime.now(timezone.utc) + timedelta(hours=1), "type": "access"},
        "wrong-secret-key-attacker",
        algorithm=settings.JWT_ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {wrong_secret_token}"}
    res = client.get("/api/models", headers=headers)
    assert res.status_code == 401


def test_valid_token_authenticates_user(client):
    """Valid JWT token authenticates successfully."""
    token = create_access_token(user_id=101)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/subscription", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["subscription"]["user_id"] == 101
    assert "plan" in data["subscription"]
