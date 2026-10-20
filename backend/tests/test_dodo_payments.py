"""
backend/tests/test_dodo_payments.py
───────────────────────────────────
Unit and integration tests for Dodo Payments Merchant of Record integration
and strictly monthly recurring billing subscriptions.
"""

import hashlib
import hmac
import json
import time
import pytest
from fastapi.testclient import TestClient

from dataforge.api.app import app
from dataforge.api.config import get_settings
from dataforge.api.services.entitlements import EntitlementService
from dataforge.api.services.payments import DodoPaymentProvider, get_payment_provider

client = TestClient(app)
settings = get_settings()


def test_dodo_checkout_session_monthly_pro():
    provider = DodoPaymentProvider(
        api_key="dodo_test_key_123",
        webhook_key="whsec_test_secret_abc",
        environment="test_mode",
    )

    checkout = provider.create_checkout_session(
        user_id=101,
        user_email="analyst@dataforge.test",
        plan_key="pro",
        return_url="/billing",
    )

    assert checkout["provider"] == "dodopayments"
    assert checkout["plan"] == "pro"
    assert checkout["billing_cycle"] == "monthly"
    assert checkout["amount"] == 29
    assert checkout["currency"] == "USD"
    assert checkout["product_id"] in checkout["checkout_url"]
    assert "metadata[billing_cycle]=monthly" in checkout["checkout_url"]
    assert "metadata[plan]=pro" in checkout["checkout_url"]
    assert "metadata[user_id]=101" in checkout["checkout_url"]


def test_dodo_checkout_session_monthly_team():
    provider = DodoPaymentProvider(
        api_key="dodo_test_key_123",
        webhook_key="whsec_test_secret_abc",
        environment="test_mode",
    )

    checkout = provider.create_checkout_session(
        user_id=202,
        user_email="teamlead@dataforge.test",
        plan_key="team",
        return_url="/billing",
    )

    assert checkout["provider"] == "dodopayments"
    assert checkout["plan"] == "team"
    assert checkout["billing_cycle"] == "monthly"
    assert checkout["amount"] == 79
    assert checkout["product_id"] in checkout["checkout_url"]


def test_dodo_invalid_plan_raises():
    provider = DodoPaymentProvider()
    with pytest.raises(ValueError, match="Unknown plan"):
        provider.create_checkout_session(
            user_id=999,
            user_email="err@test.com",
            plan_key="non_existent_tier",
            return_url="/billing",
        )


def test_dodo_webhook_signature_and_lifecycle():
    secret = "whsec_test_signing_key_456"
    provider = DodoPaymentProvider(webhook_key=secret)

    test_uid = 303
    EntitlementService.set_user_plan(test_uid, "free")
    assert EntitlementService.get_user_plan(test_uid) == "free"

    # 1. Activation webhook payload
    evt_id = f"dodo_evt_{int(time.time() * 1000)}"
    payload = {
        "id": evt_id,
        "type": "payment.succeeded",
        "data": {
            "product_id": "pdt_team_monthly_79",
            "metadata": {
                "user_id": test_uid,
                "plan": "team",
                "billing_cycle": "monthly",
            },
            "customer": {"email": "buyer@test.com"},
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    # Generate valid HMAC signature
    raw_secret = "test_signing_key_456"
    sig = hmac.new(raw_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    # Verify signature
    verified = provider.verify_webhook_signature(payload_bytes, sig)
    assert verified["id"] == evt_id

    # Handle activation event -> user upgraded to team
    res = provider.handle_event(verified)
    assert res["ok"] is True
    assert EntitlementService.get_user_plan(test_uid) == "team"

    # 2. Idempotency check: replayed event
    replay_res = provider.handle_event(verified)
    assert replay_res.get("replayed") is True

    # 3. Cancellation webhook payload -> user downgraded to free
    cancel_evt_id = f"dodo_evt_cancel_{int(time.time() * 1000)}"
    cancel_payload = {
        "id": cancel_evt_id,
        "type": "subscription.cancelled",
        "data": {
            "metadata": {
                "user_id": test_uid,
            },
        },
    }
    cancel_bytes = json.dumps(cancel_payload).encode("utf-8")
    cancel_sig = hmac.new(raw_secret.encode("utf-8"), cancel_bytes, hashlib.sha256).hexdigest()

    verified_cancel = provider.verify_webhook_signature(cancel_bytes, cancel_sig)
    res_cancel = provider.handle_event(verified_cancel)
    assert res_cancel["ok"] is True
    assert EntitlementService.get_user_plan(test_uid) == "free"


def test_dodo_webhook_invalid_signature_rejected():
    provider = DodoPaymentProvider(webhook_key="valid_secret_key")
    payload_bytes = b'{"type": "payment.succeeded"}'
    with pytest.raises(ValueError, match="Invalid Dodo Payments webhook signature"):
        provider.verify_webhook_signature(payload_bytes, "invalid_forged_signature_1234")


def test_dodo_factory_resolution():
    provider = get_payment_provider()
    assert isinstance(provider, DodoPaymentProvider)
