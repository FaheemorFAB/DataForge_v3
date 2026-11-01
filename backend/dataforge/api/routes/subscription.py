"""
dataforge/api/routes/subscription.py
────────────────────────────────────
REST endpoints for Plan Details, Entitlement Limits, Usage Progress, and Upgrades.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dataforge.api.deps import CurrentUser
from dataforge.api.services.entitlements import EntitlementService, PLAN_TIERS
from dataforge.api.utils.json import safe_jsonable

log = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["subscription"])


class UpdatePlanRequest(BaseModel):
    plan: str = Field(..., description="Plan tier key: free, pro, team")


@router.get("", summary="Get current user subscription and monthly usage meters")
async def get_subscription(current_user: CurrentUser):
    """Returns active subscription plan, limits, and current month resource consumption."""
    sub = EntitlementService.get_subscription(current_user.id)
    usage = EntitlementService.get_monthly_usage(current_user.id)

    # Calculate percentage progress for frontend meters
    storage_limit = sub.get("max_storage_mb", 500)
    automl_limit = sub.get("monthly_automl_jobs", 5)
    ai_limit = sub.get("monthly_ai_queries", 25)

    storage_used = usage.get("storage_mb_used", 0.0)
    automl_used = usage.get("automl_jobs_count", 0)
    ai_used = usage.get("ai_queries_count", 0)

    progress = {
        "storage": {
            "used": storage_used,
            "limit": storage_limit,
            "pct": min(100.0, round((storage_used / max(storage_limit, 1)) * 100, 1)),
        },
        "automl": {
            "used": automl_used,
            "limit": automl_limit,
            "pct": min(100.0, round((automl_used / max(automl_limit, 1)) * 100, 1)),
        },
        "ai_queries": {
            "used": ai_used,
            "limit": ai_limit,
            "pct": min(100.0, round((ai_used / max(ai_limit, 1)) * 100, 1)),
        },
    }

    return JSONResponse(
        content=safe_jsonable({
            "ok": True,
            "subscription": sub,
            "usage": usage,
            "progress": progress,
        })
    )


@router.get("/plans", summary="List all available public subscription plans")
async def list_plans():
    """Returns all public plan tiers, pricing, and feature comparison matrix."""
    return JSONResponse(content=safe_jsonable({"ok": True, "plans": PLAN_TIERS}))


class UpdatePlanRequest(BaseModel):
    plan: str = Field(..., description="Plan tier key: free, pro, team")
    direct_apply: bool = Field(default=False, description="Apply immediately (dev/admin testing only)")


@router.post("/upgrade", summary="Upgrade or switch subscription plan")
@router.post("/checkout", summary="Initiate checkout session for subscription plan")
async def update_plan(req: UpdatePlanRequest, current_user: CurrentUser):
    """
    Initiates payment checkout session for paid tiers (Pro, Team Collaboration),
    or switches directly to Free tier.
    """
    from dataforge.api.services.payments import get_payment_provider
    raw_key = req.plan.lower()
    plan_key = "team" if raw_key == "enterprise" else raw_key
    if plan_key not in PLAN_TIERS:
        raise HTTPException(status_code=400, detail=f"Unknown plan tier '{req.plan}'.")

    # Free tier or explicit dev bypass
    if plan_key == "free" or req.direct_apply:
        updated = EntitlementService.set_user_plan(current_user.id, plan_key)
        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "message": f"Successfully updated subscription to {updated.get('name')}.",
                "subscription": updated,
            })
        )

    # Initiate payment checkout session
    provider = get_payment_provider()
    session = provider.create_checkout_session(
        user_id=current_user.id,
        user_email=current_user.email,
        plan_key=plan_key,
        return_url="/billing/checkout",
    )

    return JSONResponse(
        content=safe_jsonable({
            "ok": True,
            "requires_payment": True,
            "checkout_session": session,
            "checkout_url": session.get("checkout_url"),
        })
    )


@router.post("/webhook", summary="Receive asynchronous payment provider billing events")
async def payment_webhook(request: Request):
    """
    Verifies cryptographic signatures on incoming payment provider webhooks,
    deduplicates event delivery, and transitions customer subscription states.
    """
    from dataforge.api.services.payments import get_payment_provider
    raw_body = await request.body()
    signature_header = (
        request.headers.get("webhook-signature")
        or request.headers.get("x-dodo-signature")
        or request.headers.get("stripe-signature")
        or request.headers.get("x-razorpay-signature")
        or request.headers.get("x-signature")
        or request.headers.get("signature")
        or ""
    )
    provider = get_payment_provider()
    try:
        event = provider.verify_webhook_signature(raw_body, signature_header)
    except Exception as e:
        log.warning("[payments] Webhook verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    result = provider.handle_event(event)
    return JSONResponse(content=result)


subscriptions_router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

@subscriptions_router.post("/checkout")
@subscriptions_router.post("/upgrade")
async def subscriptions_checkout_alias(req: UpdatePlanRequest, current_user: CurrentUser):
    return await update_plan(req, current_user)


@subscriptions_router.get("")
async def subscriptions_get_alias(current_user: CurrentUser):
    return await get_subscription(current_user)

