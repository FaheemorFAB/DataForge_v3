"""
backend/tests/test_security_headers.py
─────────────────────────────────────
Security Suite: OWASP HTTP Security Headers.
Verifies that all API responses include defensive headers against
clickjacking, MIME sniffing, and information leakage.
"""

import pytest
from fastapi.testclient import TestClient
from dataforge.api.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


def test_security_headers_present_on_endpoints(client):
    """Verify presence of OWASP security headers on public and protected endpoints."""
    endpoints = ["/api/health", "/api/subscription/plans"]
    for path in endpoints:
        res = client.get(path)
        assert res.status_code == 200
        headers = res.headers

        assert headers.get("x-content-type-options") == "nosniff", "Missing X-Content-Type-Options"
        assert headers.get("x-frame-options") == "DENY", "Missing X-Frame-Options"
        assert headers.get("x-xss-protection") == "1; mode=block", "Missing X-XSS-Protection"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin", "Missing Referrer-Policy"
        assert "camera=()" in headers.get("permissions-policy", ""), "Missing Permissions-Policy"
