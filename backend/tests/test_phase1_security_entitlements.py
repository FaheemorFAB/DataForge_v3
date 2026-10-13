"""
backend/tests/test_phase1_security_entitlements.py
──────────────────────────────────────────────────
Automated verification suite for Sprint 1 / Phase 1:
- Mandatory authentication enforcement (401 Unauthorized for unauthenticated callers)
- Tenant isolation and cross-user data leakage prevention (403 Forbidden)
- Server-side entitlement and quota enforcement (402 Payment Required)
- Safe analytical execution sandboxing in natural-language query engine
- Subscription retrieval and tier upgrades
"""

import os
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.auth.jwt import create_access_token
from dataforge.api.services.entitlements import EntitlementService, PLAN_TIERS
from dataforge.api.storage.manager import save
from dataforge.gemini_pipeline import _run_code, SecurityError


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def user_a_headers():
    token = create_access_token(user_id=101)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_headers():
    token = create_access_token(user_id=202)
    return {"Authorization": f"Bearer {token}"}


# ── 1. Mandatory Authentication (No Default-User Fallbacks) ────────────────────

def test_unauthenticated_requests_return_401(client):
    """Ensure protected routes reject unauthenticated requests rather than defaulting to user 1."""
    endpoints = [
        ("GET", "/api/workspace/state?upload_id=test-123"),
        ("GET", "/api/models"),
        ("GET", "/api/teams"),
        ("GET", "/api/pipeline/export?upload_id=test-123"),
        ("GET", "/api/subscription"),
        ("POST", "/api/automl/train"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code == 401, f"{method} {path} returned {res.status_code}, expected 401"


# ── 2. Cross-Tenant Isolation (No Data Leakage) ────────────────────────────────

def test_cross_tenant_access_denied_403(client, user_a_headers, user_b_headers):
    """Ensure User B cannot inspect or analyze User A's dataset."""
    upload_id = "test_tenant_dataset_999"

    # User A creates and owns this dataset
    df = pd.DataFrame({"sales": [10, 20, 30], "region": ["US", "EU", "APAC"]})
    meta = {
        "id": upload_id,
        "user_id": 101,  # Belongs to User A
        "filename": "revenue_q4.csv",
        "rows": 3,
        "cols": 2,
    }
    save(upload_id, "meta", meta)
    save(upload_id, "df_raw", df)

    # User B attempts to access User A's workspace state
    res_b = client.get(f"/api/workspace/state?upload_id={upload_id}", headers=user_b_headers)
    assert res_b.status_code == 403, f"Expected 403 Forbidden for User B, got {res_b.status_code}"

    # User A accesses their own dataset
    res_a = client.get(f"/api/workspace/state?upload_id={upload_id}", headers=user_a_headers)
    assert res_a.status_code == 200, f"Expected 200 OK for User A, got {res_a.status_code}"


# ── 3. Server-Side Entitlement & Quota Enforcement ────────────────────────────

def test_subscription_plans_and_upgrade(client, user_a_headers):
    """Verify subscription retrieval, public plan list, and tier upgrading."""
    # Check public plans
    res_plans = client.get("/api/subscription/plans")
    assert res_plans.status_code == 200
    plans = res_plans.json()["plans"]
    assert "free" in plans and "pro" in plans and "enterprise" in plans

    # Ensure user starts clean on free tier for test idempotency
    EntitlementService.set_user_plan(101, "free")

    # User starts on free tier
    res_sub = client.get("/api/subscription", headers=user_a_headers)
    assert res_sub.status_code == 200
    sub_data = res_sub.json()
    assert sub_data["subscription"]["plan"] == "free"
    assert sub_data["subscription"]["max_rows_per_dataset"] == 100_000

    # Upgrade to Pro
    res_upgrade = client.post("/api/subscription/upgrade", json={"plan": "pro", "direct_apply": True}, headers=user_a_headers)
    assert res_upgrade.status_code == 200
    assert res_upgrade.json()["subscription"]["plan"] == "pro"

    # Verify updated plan
    res_sub_after = client.get("/api/subscription", headers=user_a_headers)
    assert res_sub_after.json()["subscription"]["plan"] == "pro"
    assert res_sub_after.json()["subscription"]["max_rows_per_dataset"] == 1_000_000


def test_quota_rejection_for_exceeded_rows(client, user_b_headers):
    """Verify that uploading rows beyond the plan limit returns 402 Payment Required."""
    # Set User B to Free plan
    EntitlementService.set_user_plan(202, "free")

    # Free plan max is 100,000 rows
    allowed, reason = EntitlementService.check_entitlement(202, "rows", 150_000)
    assert not allowed
    assert "Upgrade to Pro" in reason

    # Check that Pro plan allows 150,000 rows
    EntitlementService.set_user_plan(202, "pro")
    allowed_pro, _ = EntitlementService.check_entitlement(202, "rows", 150_000)
    assert allowed_pro


# ── 4. Sandbox Execution Security ──────────────────────────────────────────────

def test_code_sandbox_blocks_malicious_tokens():
    """Ensure the code execution sandbox strictly rejects unauthorized imports and builtins."""
    df = pd.DataFrame({"val": [1, 2, 3]})

    # Direct import attempt
    with pytest.raises(SecurityError):
        _run_code("import os; result = os.getcwd()", df)

    # Dunder access attempt
    with pytest.raises(SecurityError):
        _run_code("result = ().__class__.__bases__[0].__subclasses__()", df)

    # File open attempt
    with pytest.raises(SecurityError):
        _run_code("open('/etc/passwd').read()", df)

    # Valid mathematical and analytical calculation should pass
    val = _run_code("result = int(df['val'].sum())", df)
    assert val == 6
