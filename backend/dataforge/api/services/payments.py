"""
dataforge/api/services/payments.py
──────────────────────────────────
Pluggable SaaS Payment Provider Adapter.
Supports Stripe, Razorpay, and Mock providers with cryptographic webhook
verification, idempotent event deduplication, and subscription lifecycle management.
"""

from __future__ import annotations

import abc
import hashlib
import hmac
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dataforge.api.config import get_settings
from dataforge.api.services.entitlements import EntitlementService, PLAN_TIERS
from dataforge.api.storage.manager import STORE_DIR

log = logging.getLogger(__name__)
settings = get_settings()

_EVENTS_FILE = STORE_DIR / "subscriptions" / "_processed_webhooks.json"
_LOCK = threading.Lock()


def _get_processed_events() -> set[str]:
    _EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _EVENTS_FILE.exists():
        return set()
    try:
        with open(_EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("event_ids", []))
    except Exception:
        return set()


def _mark_event_processed(event_id: str) -> None:
    with _LOCK:
        events = _get_processed_events()
        events.add(event_id)
        temp_file = _EVENTS_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({"event_ids": list(events)}, f, indent=2)
        temp_file.replace(_EVENTS_FILE)


class PaymentProvider(abc.ABC):
    """Abstract interface decoupling billing routes from specific payment gateways."""

    @abc.abstractmethod
    def create_checkout_session(
        self,
        user_id: int,
        user_email: str,
        plan_key: str,
        return_url: str,
    ) -> Dict[str, Any]:
        """Creates a redirect checkout session for subscription purchasing."""
        pass

    @abc.abstractmethod
    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        """Cryptographically verifies webhook payload signature."""
        pass

    @abc.abstractmethod
    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Applies subscription state transitions from verified webhook events."""
        pass


class MockPaymentProvider(PaymentProvider):
    """
    Standard test/development payment adapter with HMAC-SHA256 signature verification.
    """

    def __init__(self, webhook_secret: Optional[str] = None):
        self.webhook_secret = webhook_secret or settings.JWT_SECRET

    def create_checkout_session(
        self,
        user_id: int,
        user_email: str,
        plan_key: str,
        return_url: str,
    ) -> Dict[str, Any]:
        plan = PLAN_TIERS.get(plan_key.lower())
        if not plan:
            raise ValueError(f"Unknown plan: '{plan_key}'")

        session_id = f"cs_test_{int(time.time() * 1000)}"
        checkout_url = f"{settings.FRONTEND_URL}/billing/checkout?session_id={session_id}&plan={plan_key}&user_id={user_id}"

        return {
            "provider": "mock",
            "session_id": session_id,
            "checkout_url": checkout_url,
            "plan": plan_key,
            "amount": plan["price_monthly"],
            "currency": "USD",
        }

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature_header):
            raise ValueError("Invalid webhook signature")

        return json.loads(payload_bytes.decode("utf-8"))

    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("id") or f"evt_{hash(json.dumps(event, default=str))}"
        processed = _get_processed_events()
        if event_id in processed:
            log.info("[payments] Duplicate webhook event '%s' ignored (idempotent)", event_id)
            return {"ok": True, "replayed": True, "event_id": event_id}

        event_type = event.get("type", "")
        data = event.get("data", {})
        user_id = data.get("user_id")
        plan_key = data.get("plan", "pro")

        if not user_id:
            raise ValueError("Webhook missing target user_id")

        if event_type in ("checkout.session.completed", "subscription.activated", "invoice.payment_succeeded"):
            EntitlementService.set_user_plan(user_id=int(user_id), plan=plan_key)
            log.info("[payments] User %s upgraded to %s via webhook %s", user_id, plan_key, event_id)
        elif event_type in ("customer.subscription.deleted", "subscription.cancelled"):
            EntitlementService.set_user_plan(user_id=int(user_id), plan="free")
            log.info("[payments] User %s downgraded to free tier via webhook %s", user_id, event_id)
        elif event_type in ("invoice.payment_failed", "subscription.halted"):
            # Flag subscription past_due without revoking immediately (grace period)
            sub = EntitlementService.get_subscription(int(user_id))
            sub["status"] = "past_due"
            log.warning("[payments] User %s payment failed, status marked past_due", user_id)

        _mark_event_processed(event_id)
        return {"ok": True, "event_id": event_id, "processed": True}


class StripePaymentProvider(PaymentProvider):
    """Production Stripe Checkout & Billing Integration."""

    def __init__(self, api_key: str, webhook_secret: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    def create_checkout_session(
        self,
        user_id: int,
        user_email: str,
        plan_key: str,
        return_url: str,
    ) -> Dict[str, Any]:
        import stripe
        stripe.api_key = self.api_key
        plan = PLAN_TIERS[plan_key.lower()]

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"DataForge {plan['name']}"},
                    "unit_amount": int(plan["price_monthly"] * 100),
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            mode="subscription",
            client_reference_id=str(user_id),
            customer_email=user_email,
            success_url=f"{return_url}?session_id={{CHECKOUT_SESSION_ID}}&status=success",
            cancel_url=f"{return_url}?status=cancelled",
        )
        return {
            "provider": "stripe",
            "session_id": session.id,
            "checkout_url": session.url,
            "plan": plan_key,
        }

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        import stripe
        try:
            return stripe.Webhook.construct_event(
                payload_bytes, signature_header, self.webhook_secret
            )
        except Exception as e:
            raise ValueError(f"Stripe signature verification failed: {e}") from e

    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("id")
        if event_id in _get_processed_events():
            return {"ok": True, "replayed": True, "event_id": event_id}

        event_type = event.get("type")
        obj = event.get("data", {}).get("object", {})
        user_id = obj.get("client_reference_id")

        if user_id:
            uid = int(user_id)
            if event_type == "checkout.session.completed":
                EntitlementService.set_user_plan(uid, "pro")
            elif event_type == "customer.subscription.deleted":
                EntitlementService.set_user_plan(uid, "free")

        _mark_event_processed(event_id)
        return {"ok": True, "event_id": event_id}


class PaddlePaymentProvider(PaymentProvider):
    """
    Paddle Billing SaaS Integration.
    Supports Paddle Checkout Sessions, transaction tokens, and cryptographic webhook verification.
    """

    def __init__(
        self,
        vendor_id: Optional[str] = None,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self.vendor_id = vendor_id or getattr(settings, "PADDLE_VENDOR_ID", "") or "paddle_sandbox_vendor"
        self.api_key = api_key or getattr(settings, "PADDLE_API_KEY", "")
        self.webhook_secret = webhook_secret or getattr(settings, "PADDLE_WEBHOOK_SECRET", "") or settings.JWT_SECRET

    def create_checkout_session(
        self,
        user_id: int,
        user_email: str,
        plan_key: str,
        return_url: str,
    ) -> Dict[str, Any]:
        plan = PLAN_TIERS.get(plan_key.lower())
        if not plan:
            raise ValueError(f"Unknown plan: '{plan_key}'")

        session_id = f"pdl_txn_{int(time.time() * 1000)}"
        passthrough = json.dumps({"user_id": user_id, "email": user_email, "plan": plan_key})
        checkout_url = (
            f"https://buy.paddle.com/checkout/{plan_key}?"
            f"vendor={self.vendor_id}&guest_email={user_email}&passthrough={passthrough}&return_url={return_url}"
        )

        return {
            "provider": "paddle",
            "vendor_id": self.vendor_id,
            "session_id": session_id,
            "checkout_url": checkout_url,
            "plan": plan_key,
            "amount": plan["price_monthly"],
            "currency": "USD",
            "passthrough": passthrough,
        }

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        if "h1=" in signature_header:
            parts = dict(item.split("=", 1) for item in signature_header.split(";") if "=" in item)
            ts = parts.get("ts", "")
            h1 = parts.get("h1", "")
            signed_payload = f"{ts}:{payload_bytes.decode('utf-8', errors='ignore')}"
            computed = hmac.new(self.webhook_secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(computed, h1):
                raw_computed = hmac.new(self.webhook_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(raw_computed, h1):
                    raise ValueError("Invalid Paddle webhook signature")
        else:
            computed = hmac.new(self.webhook_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(computed, signature_header):
                raise ValueError("Invalid Paddle signature header")

        return json.loads(payload_bytes.decode("utf-8"))

    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("event_id") or event.get("id") or f"pdl_{hash(json.dumps(event, default=str))}"
        if event_id in _get_processed_events():
            return {"ok": True, "replayed": True, "event_id": event_id}

        event_type = event.get("event_type") or event.get("alert_name") or event.get("type", "")
        data = event.get("data", {})
        
        custom_data = data.get("custom_data", {})
        passthrough_raw = data.get("passthrough") or event.get("passthrough") or "{}"
        if isinstance(passthrough_raw, str):
            try:
                passthrough = json.loads(passthrough_raw)
            except Exception:
                passthrough = {}
        else:
            passthrough = passthrough_raw

        user_id = custom_data.get("user_id") or passthrough.get("user_id")
        plan_key = custom_data.get("plan") or passthrough.get("plan") or "pro"

        if not user_id:
            user_email = data.get("customer", {}).get("email") or event.get("email")
            if user_email:
                from dataforge.api.repositories.user import user_repo
                user_rec = user_repo.get_by_email(user_email)
                if user_rec:
                    user_id = user_rec.get("id")

        if user_id:
            uid = int(user_id)
            if event_type in ("subscription.activated", "subscription.created", "subscription_created", "transaction.completed"):
                EntitlementService.set_user_plan(uid, plan_key)
                log.info("[payments/paddle] Upgraded user %s to plan %s", uid, plan_key)
            elif event_type in ("subscription.canceled", "subscription_cancelled", "subscription.revoked"):
                EntitlementService.set_user_plan(uid, "free")
                log.info("[payments/paddle] Downgraded user %s to free tier", uid)
            elif event_type in ("subscription.past_due", "subscription_payment_failed"):
                sub = EntitlementService.get_subscription(uid)
                sub["status"] = "past_due"
                log.warning("[payments/paddle] Marked subscription for user %s as past_due", uid)

        _mark_event_processed(event_id)
        return {"ok": True, "event_id": event_id, "processed": True}


class DodoPaymentProvider(PaymentProvider):
    """
    Dodo Payments (dodopayments.com) Merchant of Record Integration.
    Supports monthly recurring subscription checkout sessions,
    cryptographic webhook signature verification, and lifecycle state management.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_key: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, "DODO_PAYMENTS_API_KEY", "") or ""
        self.webhook_key = (
            webhook_key
            or getattr(settings, "DODO_PAYMENTS_WEBHOOK_KEY", "")
            or getattr(settings, "JWT_SECRET", "dodo_default_webhook_secret")
        )
        self.environment = (
            environment
            or getattr(settings, "DODO_PAYMENTS_ENVIRONMENT", "test_mode")
            or "test_mode"
        )
        self.base_url = (
            "https://live.dodopayments.com"
            if self.environment == "live_mode"
            else "https://test.dodopayments.com"
        )

    def create_checkout_session(
        self,
        user_id: int,
        user_email: str,
        plan_key: str,
        return_url: str,
    ) -> Dict[str, Any]:
        """Creates a monthly recurring Dodo Payments checkout session."""
        plan_norm = plan_key.lower()
        plan = PLAN_TIERS.get(plan_norm)
        if not plan:
            raise ValueError(f"Unknown plan: '{plan_key}'")

        if plan_norm == "team":
            product_id = getattr(settings, "DODO_PRODUCT_TEAM_MONTHLY", "pdt_team_monthly_79")
        elif plan_norm == "pro":
            product_id = getattr(settings, "DODO_PRODUCT_PRO_MONTHLY", "pdt_pro_monthly_29")
        else:
            product_id = f"pdt_{plan_norm}_monthly"

        session_id = f"dodo_cs_{int(time.time() * 1000)}"
        return_target = f"{settings.FRONTEND_URL}{return_url if return_url.startswith('/') else '/' + return_url}"

        checkout_url = (
            f"{self.base_url}/buy/{product_id}?"
            f"quantity=1&email={user_email}&redirect_url={return_target}&"
            f"metadata[user_id]={user_id}&metadata[plan]={plan_norm}&metadata[billing_cycle]=monthly"
        )

        return {
            "provider": "dodopayments",
            "environment": self.environment,
            "session_id": session_id,
            "checkout_url": checkout_url,
            "product_id": product_id,
            "plan": plan_norm,
            "billing_cycle": "monthly",
            "amount": plan["price_monthly"],
            "currency": "USD",
        }

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        """
        Cryptographically verifies Dodo Payments webhook signatures.
        Supports standard hex HMAC-SHA256, formatted v1=..., or Svix-style signatures.
        """
        if not signature_header:
            raise ValueError("Missing webhook signature header")

        secret = self.webhook_key
        raw_secret_str = secret[6:] if secret.startswith("whsec_") else secret

        candidate_sigs: list[str] = []
        timestamp = ""

        if "=" in signature_header:
            parts = signature_header.split(",")
            for p in parts:
                if "=" in p:
                    k, v = p.strip().split("=", 1)
                    if k == "v1":
                        candidate_sigs.append(v)
                    elif k == "t":
                        timestamp = v
        elif signature_header.startswith("v1,"):
            candidate_sigs.append(signature_header.split(",", 1)[1])
        else:
            candidate_sigs.append(signature_header.strip())

        verified = False
        payload_str = payload_bytes.decode("utf-8", errors="ignore")

        digests_to_check: list[str] = []
        if timestamp:
            signed_content = f"{timestamp}.{payload_str}".encode("utf-8")
            digests_to_check.append(hmac.new(secret.encode("utf-8"), signed_content, hashlib.sha256).hexdigest())
            digests_to_check.append(hmac.new(raw_secret_str.encode("utf-8"), signed_content, hashlib.sha256).hexdigest())

        digests_to_check.append(hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest())
        digests_to_check.append(hmac.new(raw_secret_str.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest())

        try:
            import base64
            decoded_secret = base64.b64decode(raw_secret_str)
            if timestamp:
                digests_to_check.append(hmac.new(decoded_secret, f"{timestamp}.{payload_str}".encode("utf-8"), hashlib.sha256).hexdigest())
                b64_sig = base64.b64encode(hmac.new(decoded_secret, f"{timestamp}.{payload_str}".encode("utf-8"), hashlib.sha256).digest()).decode("utf-8")
                digests_to_check.append(b64_sig)
            digests_to_check.append(hmac.new(decoded_secret, payload_bytes, hashlib.sha256).hexdigest())
        except Exception:
            pass

        for cand in candidate_sigs:
            for d in digests_to_check:
                if hmac.compare_digest(cand, d):
                    verified = True
                    break
            if verified:
                break

        if not verified:
            raise ValueError("Invalid Dodo Payments webhook signature")

        return json.loads(payload_str)

    def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Idempotently processes Dodo Payments lifecycle events for monthly subscriptions.
        """
        event_id = (
            event.get("event_id")
            or event.get("id")
            or event.get("webhook_id")
            or f"dodo_{hash(json.dumps(event, default=str))}"
        )
        if event_id in _get_processed_events():
            return {"ok": True, "replayed": True, "event_id": event_id}

        event_type = event.get("type") or event.get("event_type") or ""
        data = event.get("data", {})

        metadata = data.get("metadata") or event.get("metadata") or {}
        user_id = (
            metadata.get("user_id")
            or data.get("user_id")
            or event.get("user_id")
            or data.get("customer", {}).get("metadata", {}).get("user_id")
        )
        plan_key = (
            metadata.get("plan")
            or data.get("plan")
            or event.get("plan")
            or "pro"
        )

        product_id = (
            data.get("product_id")
            or (data.get("product_cart", [{}])[0].get("product_id") if isinstance(data.get("product_cart"), list) and data.get("product_cart") else None)
        )
        if product_id:
            if "team" in product_id.lower():
                plan_key = "team"
            elif "pro" in product_id.lower():
                plan_key = "pro"

        if not user_id:
            user_email = data.get("customer", {}).get("email") or event.get("email")
            if user_email:
                from dataforge.api.repositories.user import user_repo
                user_rec = user_repo.get_by_email(user_email)
                if user_rec:
                    user_id = user_rec.get("id")

        if user_id:
            uid = int(user_id)
            if event_type in (
                "payment.succeeded",
                "subscription.active",
                "subscription.created",
                "subscription.renewed",
                "checkout.session.completed",
                "customer.subscription.created",
                "customer.subscription.updated",
            ):
                EntitlementService.set_user_plan(uid, plan_key)
                log.info("[payments/dodo] Upgraded user %s to monthly plan %s", uid, plan_key)
            elif event_type in (
                "subscription.cancelled",
                "subscription.canceled",
                "subscription.expired",
                "subscription.terminated",
                "customer.subscription.deleted",
                "subscription.deleted",
            ):
                EntitlementService.set_user_plan(uid, "free")
                log.info("[payments/dodo] Downgraded user %s to free tier after cancellation", uid)
            elif event_type in ("subscription.past_due", "payment.failed"):
                sub = EntitlementService.get_subscription(uid)
                sub["status"] = "past_due"
                log.warning("[payments/dodo] Subscription for user %s marked as past_due", uid)

        _mark_event_processed(event_id)
        return {"ok": True, "event_id": event_id, "provider": "dodopayments", "processed": True}


def get_payment_provider() -> PaymentProvider:
    """Factory returning configured payment adapter."""
    provider_type = getattr(settings, "PAYMENT_PROVIDER", "dodo").lower()
    if provider_type in ("dodo", "dodopayments") or getattr(settings, "DODO_PAYMENTS_API_KEY", None):
        return DodoPaymentProvider()
    if provider_type == "paddle" or getattr(settings, "PADDLE_VENDOR_ID", None):
        return PaddlePaymentProvider()
    if provider_type == "stripe" and getattr(settings, "STRIPE_SECRET_KEY", None):
        return StripePaymentProvider(settings.STRIPE_SECRET_KEY, settings.STRIPE_WEBHOOK_SECRET)
    if provider_type == "mock":
        return MockPaymentProvider()
    return DodoPaymentProvider()


