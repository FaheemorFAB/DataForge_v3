"""
tests/test_security_audit.py
────────────────────────────
Regression test suite for verified security audit findings and fixes:
  1. Mock Auth fail-closed defense (VULN-01)
  2. SSRF, DNS pinning, and private network rejection (VULN-02)
  3. External DB connector dialect restriction & query parameter allowlisting (VULN-02)
  4. Sandbox Landlock filesystem confinement, network isolation & AST guidance (VULN-04)
  5. Path traversal upload_id validation (UUID & integer)
  6. Spoof-proof X-Forwarded-For IP resolution for rate limiting
"""

import ipaddress
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from dataforge.api.app import app
from dataforge.api.config import Settings
from dataforge.api.deps import get_remote_addr
from dataforge.api.utils.ssrf import safe_fetch_url, SSRFSecurityError, validate_and_resolve_host, is_safe_ip
from dataforge.db_connector import DBConnector
from dataforge.sandbox import validate_ast, run_sandboxed_code, SecurityError
from dataforge.web.storage import _upath
import pandas as pd


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. Mock Authentication Regression Tests ────────────────────────────────────

def test_mock_auth_fails_closed_by_default(client):
    """Verify mock login endpoints return 404 by default (fail-closed)."""
    res_post = client.post("/api/v1/auth/mock", json={"email": "attacker@evil.com", "role": "Admin"})
    assert res_post.status_code == 404, "POST /api/v1/auth/mock must return 404 by default"

    res_get = client.get("/login/mock")
    assert res_get.status_code == 404, "GET /login/mock must return 404 by default"


def test_production_fails_fast_if_dev_auth_enabled():
    """Startup validation must throw RuntimeError if ENABLE_DEV_AUTH is True in production."""
    settings = Settings(
        PRODUCTION=True,
        ENABLE_DEV_AUTH=True,
        FLASK_SECRET_KEY="x" * 32,
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_KEY="service_key",
        FRONTEND_URL="https://app.example.com",
    )
    with pytest.raises(RuntimeError, match="ENABLE_DEV_AUTH must never be True when PRODUCTION=True"):
        settings.validate_production_environment()


# ── 2. SSRF & Protocol Smuggling Regression Tests ──────────────────────────────

def test_ssrf_rejects_file_scheme():
    with pytest.raises(SSRFSecurityError, match="Prohibited URL scheme"):
        safe_fetch_url("file:///etc/passwd")


def test_ssrf_rejects_loopback():
    with pytest.raises(SSRFSecurityError):
        safe_fetch_url("http://127.0.0.1:80/api")


def test_ssrf_rejects_private_subnets():
    private_ips = ["10.0.0.1", "172.16.0.1", "192.168.1.1"]
    for ip in private_ips:
        with pytest.raises(SSRFSecurityError, match="disallowed private/internal IP"):
            validate_and_resolve_host(ip, 80)


def test_ssrf_rejects_cloud_metadata():
    with pytest.raises(SSRFSecurityError):
        safe_fetch_url("http://169.254.169.254/latest/meta-data/")


def test_ssrf_rejects_ipv4_mapped_ipv6_and_nat64():
    # IPv4-mapped IPv6 loopback
    mapped_loopback = ipaddress.ip_address("::ffff:127.0.0.1")
    assert not is_safe_ip(mapped_loopback)

    # NAT64 prefix loopback
    nat64_loopback = ipaddress.ip_address("64:ff9b::127.0.0.1")
    assert not is_safe_ip(nat64_loopback)

    # IPv4-compatible IPv6 private
    compat_private = ipaddress.ip_address("::10.0.0.1")
    assert not is_safe_ip(compat_private)


# ── 3. DBConnector Dialect & SSRF Restriction ─────────────────────────────────

def test_db_connector_rejects_sqlite():
    conn = DBConnector("sqlite:////tmp/malicious.db")
    with pytest.raises(ValueError, match="Database dialect 'sqlite' or local file storage is prohibited"):
        conn._get_engine()
    ok, msg = conn.test()
    assert not ok
    assert "prohibited" in msg


def test_db_connector_rejects_internal_host(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_DATABASE", "false")
    monkeypatch.setenv("ALLOW_LOCAL_DB", "false")
    conn = DBConnector("postgresql://user:pass@127.0.0.1:5432/testdb")
    with pytest.raises(ValueError, match="Database connection prohibited for security"):
        conn._get_engine()
    ok, msg = conn.test()
    assert not ok
    assert "prohibited" in msg


def test_db_connector_allows_local_in_dev_when_flag_enabled(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_DATABASE", "true")
    conn = DBConnector("postgresql://user:pass@127.0.0.1:5432/testdb")
    eng = conn._get_engine()
    assert eng is not None


def test_db_connector_rejects_unauthorized_query_params():
    """Verify that dangerous parameters like host= and sslkey= are rejected."""
    dangerous_urls = [
        "postgresql://user:pass@remote.db.com:5432/mydb?host=/var/run/postgresql",
        "postgresql://user:pass@remote.db.com:5432/mydb?sslkey=/etc/passwd",
        "postgresql://user:pass@remote.db.com:5432/mydb?passfile=/etc/shadow",
        "postgresql://user:pass@remote.db.com:5432/mydb?sslrootcert=/root/secret.pem",
    ]
    for url in dangerous_urls:
        conn = DBConnector(url)
        with pytest.raises(ValueError, match="Prohibited database connection parameter"):
            conn._get_engine()


# ── 4. Sandbox AST, UX Guidance & Confinement ──────────────────────────────────

def test_sandbox_blocks_filesystem_reads():
    exploits = [
        "result = pd.read_csv('/etc/passwd')",
        "result = pd.read_parquet('/tmp/test.parquet')",
        "result = pd.read_json('data.json')",
        "result = df.to_pickle('/tmp/evil.pkl')",
    ]
    for code in exploits:
        with pytest.raises(SecurityError, match="Prohibited method"):
            validate_ast(code)


def test_sandbox_clear_error_for_eval_and_query():
    """Ensure clear guidance error is emitted instead of a generic failure."""
    for code in ["result = df.query('a > 10')", "result = pd.eval('1 + 1')"]:
        with pytest.raises(SecurityError, match="restricted in the analytics sandbox for security"):
            validate_ast(code)


def test_sandbox_legitimate_analytics_allowed():
    df = pd.DataFrame({"category": ["A", "B", "A"], "value": [10, 20, 30]})
    code = "result = df.groupby('category')['value'].sum().to_dict()"
    res = run_sandboxed_code(code, df)
    assert res == {"A": 40, "B": 20}


# ── 5. Path Traversal & Storage Validation ──────────────────────────────────────

def test_storage_upath_validates_upload_id_format():
    """Verify upload_id must be integer or UUID, blocking directory traversal."""
    # Valid integer upload_id
    p1 = _upath("123", "df_raw")
    assert "123" in str(p1)

    # Valid UUID upload_id
    p2 = _upath("550e8400-e29b-41d4-a716-446655440000", "df_clean")
    assert "550e8400-e29b-41d4-a716-446655440000" in str(p2)

    # Malicious path traversal upload_id
    invalid_ids = ["../../etc", "foo/bar", "123;rm", "../upload", "valid_id/../../"]
    for bad_id in invalid_ids:
        with pytest.raises(ValueError, match="Invalid upload_id format"):
            _upath(bad_id, "df_raw")


# ── 6. X-Forwarded-For Spoofing Defense for Rate Limiting ─────────────────────

def test_get_remote_addr_ignores_spoofed_headers_from_untrusted_peer():
    """Direct untrusted peer IP must be returned, ignoring attacker-supplied XFF."""
    req = Request({
        "type": "http",
        "client": ("198.51.100.5", 54321),
        "headers": [(b"x-forwarded-for", b"203.0.113.1"), (b"cf-connecting-ip", b"203.0.113.1")],
    })
    resolved_ip = get_remote_addr(req)
    assert resolved_ip == "198.51.100.5", "Must ignore XFF headers from untrusted direct peer"


def test_get_remote_addr_extracts_client_from_trusted_proxy():
    """When peer is a trusted reverse proxy, extract the rightmost untrusted hop."""
    req = Request({
        "type": "http",
        "client": ("127.0.0.1", 54321),
        "headers": [(b"x-forwarded-for", b"203.0.113.88, 127.0.0.1")],
    })
    resolved_ip = get_remote_addr(req)
    assert resolved_ip == "203.0.113.88", "Must extract rightmost untrusted hop from trusted proxy"
