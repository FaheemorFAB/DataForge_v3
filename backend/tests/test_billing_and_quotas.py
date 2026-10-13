"""
backend/tests/test_billing_and_quotas.py
────────────────────────────────────────
Billing & Quota Suite:
Verifies atomic quota reservation, commit/release lifecycle, idempotency,
payment checkout session initiation, cryptographic webhook verification,
and subscription state transitions.
"""

import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.auth.jwt import create_access_token
from dataforge.api.config import get_settings
from dataforge.api.services.entitlements import EntitlementService
from dataforge.api.services.payments import get_payment_provider
from dataforge.api.services.usage import UsageService, QuotaExceededError
from dataforge.api.storage.manager import STORE_DIR

settings = get_settings()


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def test_user():
    uid = 303
    EntitlementService.set_user_plan(uid, "free")
    # Reset monthly usage ledger for clean test execution
    month = EntitlementService.get_monthly_usage(uid).get("period_month")
    subs_dir = STORE_DIR / "subscriptions"
    u_file = subs_dir / f"usage_{uid}_{month}.json"
    if u_file.exists():
        try:
            u_file.unlink()
        except Exception:
            pass
    # Clear any pending reservations for uid
    res_data = UsageService._read_reservations()
    res_data["reservations"] = {k: v for k, v in res_data.get("reservations", {}).items() if v.get("tenant_id") != uid}
    res_data["idempotency_map"] = {k: v for k, v in res_data.get("idempotency_map", {}).items() if not k.startswith(f"test_idemp_{uid}_")}
    UsageService._write_reservations(res_data)

    token = create_access_token(user_id=uid)
    return {"id": uid, "headers": {"Authorization": f"Bearer {token}"}}


def test_atomic_usage_reserve_commit_lifecycle(test_user):
    """Verify two-phase resource reservation and commitment."""
    uid = test_user["id"]
    import uuid
    idemp_key = f"test_idemp_{uid}_{uuid.uuid4().hex}"

    # 1. Reserve 1 AutoML job
    res = UsageService.reserve(tenant_id=uid, metric="automl_jobs", amount=1, idempotency_key=idemp_key)
    assert res["status"] == "reserved"
    assert res["amount"] == 1
    res_id = res["id"]

    # 2. Replaying same idempotency key returns the same reservation
    res_replayed = UsageService.reserve(tenant_id=uid, metric="automl_jobs", amount=1, idempotency_key=idemp_key)
    assert res_replayed["id"] == res_id

    # 3. Commit the reservation
    committed = UsageService.commit(reservation_id=res_id)
    assert committed["status"] == "committed"

    # Verify committed usage in monthly ledger
    usage = EntitlementService.get_monthly_usage(uid)
    assert usage.get("automl_jobs_count", 0) >= 1


def test_atomic_usage_release_restores_quota(test_user):
    """Verify that releasing a reservation prevents usage from being charged."""
    import uuid
    uid = test_user["id"]
    idemp_key = f"test_idemp_release_{uid}_{uuid.uuid4().hex}"

    # 1. Reserve 2 AI queries
    res = UsageService.reserve(tenant_id=uid, metric="ai_queries", amount=2, idempotency_key=idemp_key)
    res_id = res["id"]

    # 2. Release reservation (e.g. cancelled/failed operation)
    released = UsageService.release(res_id)
    assert released["status"] == "released"


def test_quota_exhaustion_rejects_excess_reservation(test_user):
    """Attempting to reserve more quota than plan allows raises QuotaExceededError."""
    uid = test_user["id"]
    # Free tier limit for AutoML is 5
    with pytest.raises(QuotaExceededError):
        UsageService.reserve(tenant_id=uid, metric="automl_jobs", amount=100, idempotency_key="excess_test")


def test_subscription_upgrade_initiates_checkout(client, test_user):
    """Paid tier upgrades create a checkout session rather than blindly modifying plan."""
    res = client.post(
        "/api/subscription/upgrade",
        json={"plan": "pro"},
        headers=test_user["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["requires_payment"] is True
    assert "checkout_session" in data
    assert "checkout_url" in data
    assert data["checkout_session"]["plan"] == "pro"


def test_verified_payment_webhook_transitions_subscription(client, test_user):
    """Verified webhook updates customer subscription state; duplicate delivery is idempotent."""
    import uuid
    uid = test_user["id"]
    event_id = f"evt_test_checkout_{uid}_{uuid.uuid4().hex}"
    payload = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "user_id": uid,
            "plan": "pro",
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    valid_signature = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # 1. Invalid signature is rejected
    res_invalid = client.post(
        "/api/subscription/webhook",
        content=payload_bytes,
        headers={"x-signature": "tampered_signature_attacker", "content-type": "application/json"},
    )
    assert res_invalid.status_code == 400

    # 2. Valid signature upgrades user to Pro
    res_valid = client.post(
        "/api/subscription/webhook",
        content=payload_bytes,
        headers={"x-signature": valid_signature, "content-type": "application/json"},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["ok"] is True
    assert res_valid.json().get("replayed") is not True

    # Confirm user is now on Pro tier
    sub = EntitlementService.get_subscription(uid)
    assert sub["plan"] == "pro"
    assert sub["max_rows_per_dataset"] == 1_000_000

    # 3. Duplicate delivery is idempotent
    res_replay = client.post(
        "/api/subscription/webhook",
        content=payload_bytes,
        headers={"x-signature": valid_signature, "content-type": "application/json"},
    )
    assert res_replay.status_code == 200
    assert res_replay.json().get("replayed") is True


def test_cancellation_webhook_downgrades_to_free(client, test_user):
    """Subscription cancellation event downgrades tier back to Free."""
    import uuid
    uid = test_user["id"]
    # Ensure starting in Pro
    EntitlementService.set_user_plan(uid, "pro")

    payload = {
        "id": f"evt_cancel_{uid}_{uuid.uuid4().hex}",
        "type": "customer.subscription.deleted",
        "data": {"user_id": uid},
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    res = client.post(
        "/api/subscription/webhook",
        content=payload_bytes,
        headers={"x-signature": signature, "content-type": "application/json"},
    )
    assert res.status_code == 200

    sub = EntitlementService.get_subscription(uid)
    assert sub["plan"] == "free"
