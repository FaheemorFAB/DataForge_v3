"""
dataforge/api/services/entitlements.py
──────────────────────────────────────
Backend-Enforced Subscription Entitlements, Quotas, and Resource Metering.

Guarantees that usage limits (storage, rows, AutoML tournaments, AI queries)
are strictly validated server-side according to active plan tiers.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dataforge.api.storage.manager import STORE_DIR
from dataforge.db import db_client, db_first, db_insert, db_update

log = logging.getLogger(__name__)

# ── Plan Configuration & Limits ────────────────────────────────────────────────
PLAN_TIERS: Dict[str, Dict[str, Any]] = {
    "free": {
        "name": "Free Starter",
        "price_monthly": 0,
        "max_storage_mb": 500,
        "max_rows_per_dataset": 100_000,
        "monthly_automl_jobs": 5,
        "monthly_ai_queries": 25,
        "max_projects": 3,
        "max_team_members": 1,
        "export_formats": ["csv", "json"],
        "support_level": "community",
    },
    "pro": {
        "name": "Pro Analyst",
        "price_monthly": 29,
        "max_storage_mb": 10_000,
        "max_rows_per_dataset": 1_000_000,
        "monthly_automl_jobs": 50,
        "monthly_ai_queries": 250,
        "max_projects": 25,
        "max_team_members": 5,
        "export_formats": ["csv", "json", "parquet", "excel", "dbt", "airflow"],
        "support_level": "priority_email",
    },
    "team": {
        "name": "Team Collaboration",
        "price_monthly": 79,
        "max_storage_mb": 50_000,
        "max_rows_per_dataset": 5_000_000,
        "monthly_automl_jobs": 200,
        "monthly_ai_queries": 1_000,
        "max_projects": 100,
        "max_team_members": 25,
        "export_formats": ["csv", "json", "parquet", "excel", "dbt", "airflow", "docker"],
        "support_level": "24_7_dedicated",
    },
    "enterprise": {
        "name": "Enterprise Scale",
        "price_monthly": 249,
        "max_storage_mb": 500_000,
        "max_rows_per_dataset": 20_000_000,
        "monthly_automl_jobs": 1_000,
        "monthly_ai_queries": 10_000,
        "max_projects": 1_000,
        "max_team_members": 1000,
        "export_formats": ["all"],
        "support_level": "dedicated_sla",
    },
}

_LOCK = threading.Lock()
_SUBS_DIR = STORE_DIR / "subscriptions"
_SUBS_DIR.mkdir(parents=True, exist_ok=True)


def _current_month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


class EntitlementService:
    """Central authority for subscription tier checks and metered quota usage."""

    @classmethod
    def get_subscription(cls, user_id: int) -> Dict[str, Any]:
        """Fetches active subscription plan for the user, falling back to free tier."""
        # 1. Check Supabase / Postgres if configured
        if db_client:
            try:
                row = db_first("subscriptions", {"user_id": user_id})
                if row:
                    plan_key = row.get("plan", "free").lower()
                    limits = PLAN_TIERS.get(plan_key, PLAN_TIERS["free"])
                    return {**limits, **row}
            except Exception as e:
                log.warning("DB subscription lookup failed for user %s: %s", user_id, e)

        # 2. Local fallback storage
        sub_file = _SUBS_DIR / f"user_{user_id}.json"
        if sub_file.exists():
            try:
                data = json.loads(sub_file.read_text(encoding="utf-8"))
                plan_key = data.get("plan", "free").lower()
                limits = PLAN_TIERS.get(plan_key, PLAN_TIERS["free"])
                return {**limits, **data}
            except Exception:
                pass

        # 3. Default Free Plan
        default_sub = {
            "user_id": user_id,
            "plan": "free",
            "status": "active",
            **PLAN_TIERS["free"],
        }
        return default_sub

    @classmethod
    def get_user_plan(cls, user_id: int) -> str:
        """Convenience method returning user's active plan key."""
        return cls.get_subscription(user_id).get("plan", "free")

    @classmethod
    def set_user_plan(cls, user_id: int, plan: str) -> Dict[str, Any]:
        """Upgrades or modifies a user's subscription tier."""
        plan_key = plan.lower()
        if plan_key not in PLAN_TIERS:
            raise ValueError(f"Unknown plan tier '{plan}'. Allowed: {list(PLAN_TIERS.keys())}")

        limits = PLAN_TIERS[plan_key]
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "user_id": user_id,
            "plan": plan_key,
            "status": "active",
            "max_storage_mb": limits["max_storage_mb"],
            "max_rows_per_dataset": limits["max_rows_per_dataset"],
            "monthly_automl_jobs": limits["monthly_automl_jobs"],
            "monthly_ai_queries": limits["monthly_ai_queries"],
            "updated_at": now_iso,
        }

        # Save to DB if available
        if db_client:
            try:
                existing = db_first("subscriptions", {"user_id": user_id})
                if existing:
                    db_update("subscriptions", existing["id"], payload)
                else:
                    db_insert("subscriptions", payload)
            except Exception as e:
                log.warning("Failed to persist subscription to DB: %s", e)

        # Always save locally
        with _LOCK:
            sub_file = _SUBS_DIR / f"user_{user_id}.json"
            sub_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return {**limits, **payload}

    @classmethod
    def get_monthly_usage(cls, user_id: int) -> Dict[str, Any]:
        """Returns the resource consumption metrics for the current calendar month."""
        month = _current_month_key()

        # Check DB
        if db_client:
            try:
                row = db_first("usage_records", {"user_id": user_id, "period_month": month})
                if row:
                    return row
            except Exception:
                pass

        # Check Local File
        usage_file = _SUBS_DIR / f"usage_{user_id}_{month}.json"
        if usage_file.exists():
            try:
                return json.loads(usage_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "user_id": user_id,
            "period_month": month,
            "storage_mb_used": 0.0,
            "automl_jobs_count": 0,
            "ai_queries_count": 0,
        }

    @classmethod
    def record_usage(cls, user_id: int, metric: str, amount: float = 1.0) -> Dict[str, Any]:
        """Atomically increments the user's monthly meter for a given resource."""
        month = _current_month_key()
        with _LOCK:
            usage = cls.get_monthly_usage(user_id)
            if metric == "automl_jobs":
                usage["automl_jobs_count"] = usage.get("automl_jobs_count", 0) + int(amount)
            elif metric == "ai_queries":
                usage["ai_queries_count"] = usage.get("ai_queries_count", 0) + int(amount)
            elif metric == "storage_mb":
                usage["storage_mb_used"] = round(usage.get("storage_mb_used", 0.0) + float(amount), 2)

            usage["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Save to disk
            usage_file = _SUBS_DIR / f"usage_{user_id}_{month}.json"
            usage_file.write_text(json.dumps(usage, indent=2), encoding="utf-8")

            # Save to DB
            if db_client:
                try:
                    existing = db_first("usage_records", {"user_id": user_id, "period_month": month})
                    if existing:
                        db_update("usage_records", existing["id"], usage)
                    else:
                        db_insert("usage_records", usage)
                except Exception:
                    pass

            return usage

    @classmethod
    def check_entitlement(
        cls,
        user_id: int,
        metric: str,
        requested_units: float = 1.0,
    ) -> Tuple[bool, str]:
        """
        Validates whether the user has sufficient plan quota for the requested operation.
        Returns: (is_allowed, reason_if_denied)
        """
        sub = cls.get_subscription(user_id)
        plan_name = sub.get("name", "Free Starter")
        plan_key = sub.get("plan", "free")

        if metric == "rows":
            max_rows = sub.get("max_rows_per_dataset", 100_000)
            if requested_units > max_rows:
                return (
                    False,
                    f"Dataset contains {int(requested_units):,} rows, exceeding the {max_rows:,} limit on your {plan_name} plan. Upgrade to Pro for 1M+ rows.",
                )

        elif metric == "automl_jobs":
            usage = cls.get_monthly_usage(user_id)
            used = usage.get("automl_jobs_count", 0)
            max_allowed = sub.get("monthly_automl_jobs", 5)
            if used + requested_units > max_allowed:
                return (
                    False,
                    f"Monthly AutoML tournament limit reached ({used}/{max_allowed} used) on your {plan_name} plan. Upgrade to Pro for 50 tournaments/month.",
                )

        elif metric == "ai_queries":
            usage = cls.get_monthly_usage(user_id)
            used = usage.get("ai_queries_count", 0)
            max_allowed = sub.get("monthly_ai_queries", 25)
            if used + requested_units > max_allowed:
                return (
                    False,
                    f"Monthly AI natural-language query limit reached ({used}/{max_allowed} used) on your {plan_name} plan. Upgrade to Pro for 250 queries/month.",
                )

        elif metric == "storage_mb":
            usage = cls.get_monthly_usage(user_id)
            used = usage.get("storage_mb_used", 0.0)
            max_allowed = sub.get("max_storage_mb", 500)
            if used + requested_units > max_allowed:
                return (
                    False,
                    f"Storage quota exceeded ({round(used, 1)}MB / {max_allowed}MB) on your {plan_name} plan. Upgrade to Pro for 10 GB storage.",
                )

        return (True, "")
