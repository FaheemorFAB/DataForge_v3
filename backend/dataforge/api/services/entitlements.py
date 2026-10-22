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
import os
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
        "max_storage_mb": 250,
        "max_rows_per_dataset": 25_000,
        "unlimited_ingestion": False,
        "allowed_sources": ["local_csv", "local_excel", "google_sheets"],
        "monthly_automl_jobs": 5,
        "monthly_ai_queries": 25,
        "max_projects": 3,
        "max_team_members": 1,
        "export_formats": [],
        "can_export": False,
        "support_level": "community",
    },
    "pro": {
        "name": "Pro Analyst",
        "price_monthly": 29,
        "max_storage_mb": 5_000,
        "max_rows_per_dataset": 250_000,
        "unlimited_ingestion": True,
        "allowed_sources": ["local_csv", "local_excel", "google_sheets", "onedrive_excel"],
        "monthly_automl_jobs": 50,
        "monthly_ai_queries": 250,
        "max_projects": -1,
        "max_team_members": 1,  # Dedicated solo practitioner seat
        "export_formats": ["csv", "json", "parquet", "excel", "dbt", "slides", "docker"],
        "can_export": True,
        "has_eda_slides": True,
        "has_docker_export": True,
        "has_all_exports": True,
        "has_team_collaboration": False,
        "support_level": "priority_email",
    },
    "team": {
        "name": "Team Collaboration",
        "price_monthly": 79,
        "max_storage_mb": 25_000,
        "max_rows_per_dataset": 1_000_000,
        "unlimited_ingestion": True,
        "allowed_sources": ["local_csv", "local_excel", "google_sheets", "onedrive_excel", "databases"],
        "monthly_automl_jobs": 200,
        "monthly_ai_queries": 1_000,
        "max_projects": -1,
        "max_team_members": 5,
        "team_roles": ["Viewer", "Analyst", "Admin"],
        "export_formats": ["csv", "json", "parquet", "excel", "dbt", "airflow", "slides", "docker", "database_push", "audit_logs", "all"],
        "can_export": True,
        "has_eda_slides": True,
        "has_docker_export": True,
        "has_all_exports": True,
        "has_database_push": True,
        "has_audit_logs_export": True,
        "has_team_collaboration": True,
        "support_level": "priority_team",
    },
    "enterprise": {
        "name": "Enterprise Scale",
        "price_monthly": 249,
        "max_storage_mb": 100_000,
        "max_rows_per_dataset": 5_000_000,
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


def get_tier_for_email(email: Optional[str]) -> Optional[str]:
    """Returns the lifetime plan tier for whitelisted test/VIP emails, or None."""
    if not email:
        return None
    e = email.strip().lower()

    # 1. Team Collaboration Whitelist (comma-separated, supports multiple emails)
    team_env = os.environ.get("TEAM_TIER_EMAILS", "9256fa@gmail.com")
    team_list = [x.strip().lower() for x in team_env.split(",") if x.strip()]
    if e in team_list:
        return "team"

    # 2. Pro Analyst Whitelist (comma-separated, supports multiple emails)
    pro_env = os.environ.get("PRO_TIER_EMAILS", "mohammadnuman7788@gmail.com")
    pro_list = [x.strip().lower() for x in pro_env.split(",") if x.strip()]
    if e in pro_list:
        return "pro"

    return None


_SUBSCRIPTION_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


class EntitlementService:
    """Central authority for subscription tier checks and metered quota usage."""

    @classmethod
    def get_subscription(cls, user_id: int, email: Optional[str] = None) -> Dict[str, Any]:
        """Fetches active subscription plan for the user, checking lifetime email overrides first."""
        resolved_email = (email or "").strip().lower()
        now = datetime.now(timezone.utc).timestamp()
        cache_key = f"{user_id}:{resolved_email}"
        cached = _SUBSCRIPTION_CACHE.get(cache_key)
        if cached and (now - cached[0] < 120.0):
            return cached[1]

        if not resolved_email and user_id:
            try:
                from dataforge.api.repositories.user import user_repo
                u = user_repo.get_by_id(user_id)
                if u and u.get("email"):
                    resolved_email = u["email"].strip().lower()
            except Exception:
                pass

        # 0. Check Permanent Lifetime Tier Override by Email
        if resolved_email:
            override_tier = get_tier_for_email(resolved_email)
            if override_tier and override_tier in PLAN_TIERS:
                limits = PLAN_TIERS[override_tier]
                res = {
                    **limits,
                    "user_id": user_id,
                    "email": resolved_email,
                    "plan": override_tier,
                    "status": "active",
                    "is_lifetime": True,
                }
                _SUBSCRIPTION_CACHE[cache_key] = (now, res)
                return res

        # 1. Check Supabase / Postgres if configured
        if db_client:
            try:
                row = db_first("subscriptions", {"user_id": user_id})
                if row:
                    plan_key = row.get("plan", "free").lower()
                    limits = PLAN_TIERS.get(plan_key, PLAN_TIERS["free"])
                    res = {**limits, **row}
                    _SUBSCRIPTION_CACHE[cache_key] = (now, res)
                    return res
            except Exception as e:
                log.warning("DB subscription lookup failed for user %s: %s", user_id, e)

        # 2. Local fallback storage
        sub_file = _SUBS_DIR / f"user_{user_id}.json"
        if sub_file.exists():
            try:
                data = json.loads(sub_file.read_text(encoding="utf-8"))
                plan_key = data.get("plan", "free").lower()
                limits = PLAN_TIERS.get(plan_key, PLAN_TIERS["free"])
                res = {**limits, **data}
                _SUBSCRIPTION_CACHE[cache_key] = (now, res)
                return res
            except Exception:
                pass

        # 3. Default Free Plan
        default_sub = {
            "user_id": user_id,
            "plan": "free",
            "status": "active",
            **PLAN_TIERS["free"],
        }
        _SUBSCRIPTION_CACHE[cache_key] = (now, default_sub)
        return default_sub

    @classmethod
    def get_user_plan(cls, user_id: int, email: Optional[str] = None) -> str:
        """Convenience method returning user's active plan key."""
        return cls.get_subscription(user_id, email=email).get("plan", "free")

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
            to_del = [k for k in _SUBSCRIPTION_CACHE if k.startswith(f"{user_id}:")]
            for k in to_del:
                _SUBSCRIPTION_CACHE.pop(k, None)

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

            # Save to DB (non-blocking background thread)
            if db_client:
                import threading
                def _bg_record_usage(u_id=user_id, p_month=month, u_data=dict(usage)):
                    try:
                        existing = db_first("usage_records", {"user_id": u_id, "period_month": p_month})
                        if existing:
                            db_update("usage_records", existing["id"], u_data)
                        else:
                            db_insert("usage_records", u_data)
                    except Exception:
                        pass
                threading.Thread(target=_bg_record_usage, daemon=True).start()

            return usage

    @classmethod
    def check_entitlement(
        cls,
        user_id: int,
        metric: str,
        requested_units: float = 1.0,
        email: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validates whether the user has sufficient plan quota for the requested operation.
        Returns: (is_allowed, reason_if_denied)
        """
        sub = cls.get_subscription(user_id, email=email)
        plan_name = sub.get("name", "Free Starter")
        plan_key = sub.get("plan", "free")

        if metric == "rows":
            max_rows = sub.get("max_rows_per_dataset", 100_000)
            if requested_units > max_rows:
                return (
                    False,
                    f"Dataset contains {int(requested_units):,} rows, exceeding the {max_rows:,} limit on your {plan_name} plan. Upgrade to Pro Analyst for 250k rows or Team Collaboration for 1M rows.",
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
            max_allowed = sub.get("max_storage_mb", 250)
            if used + requested_units > max_allowed:
                return (
                    False,
                    f"Storage quota exceeded ({round(used, 1)}MB / {max_allowed}MB) on your {plan_name} plan. Upgrade to Pro for 5 GB storage.",
                )

        return (True, "")

    @classmethod
    def check_source_access(cls, user_id: int, source: str) -> Tuple[bool, str]:
        """
        Validates whether the user's subscription tier is allowed to ingest from the given source.
        Sources: 'local_csv', 'local_excel', 'google_sheets', 'onedrive_excel', 'databases'
        """
        sub = cls.get_subscription(user_id)
        plan_name = sub.get("name", "Free Starter")
        allowed_sources = sub.get("allowed_sources", ["local_csv", "local_excel", "google_sheets"])

        # Map aliases
        norm_source = "databases" if source in ("database", "sql") else source
        if norm_source == "excel_online":
            norm_source = "onedrive_excel"
        elif norm_source in ("sheets", "sheet"):
            norm_source = "google_sheets"

        if norm_source not in allowed_sources:
            if norm_source == "onedrive_excel":
                return (
                    False,
                    f"OneDrive / Microsoft 365 Excel Online ingestion is not included in {plan_name}. "
                    "Upgrade to Pro Analyst or Team Collaboration for cloud spreadsheet sync.",
                )
            elif norm_source == "databases":
                return (
                    False,
                    f"Shared Database Connection Vault is exclusive to Team Collaboration. "
                    "Upgrade your organization to connect PostgreSQL, MySQL, DuckDB & SQLite databases.",
                )
            return (
                False,
                f"Data source '{source}' is not enabled on your {plan_name} plan. Free tier supports local CSV, Excel and Google Sheets only.",
            )

        return (True, "")

    @classmethod
    def check_export_access(cls, user_id: int, export_type: str = "dataset") -> Tuple[bool, str]:
        """
        Validates whether the user's subscription tier allows downloading or exporting files/artifacts.
        Free Starter: No downloads (in-browser sandbox only).
        Pro Analyst: CSV, Excel, Parquet, JSON, slides, docker, python, dbt.
        Team Collaboration: All above + Airflow DAGs, database write-back push, audit logs.
        """
        sub = cls.get_subscription(user_id)
        plan_name = sub.get("name", "Free Starter")
        can_export = sub.get("can_export", False)
        export_formats = sub.get("export_formats", [])

        if not can_export or not export_formats:
            return (
                False,
                f"File exports & downloads are locked on {plan_name}. "
                "Upgrade to Pro Analyst to download datasets (CSV, Excel, Parquet), presentation slides, and Docker containers.",
            )

        if "all" in export_formats:
            return (True, "")

        norm_type = export_type.lower()
        if norm_type in ("airflow", "database_push", "audit_logs") and norm_type not in export_formats:
            return (
                False,
                f"'{export_type}' export is exclusive to Team Collaboration. "
                "Upgrade to Team Collaboration to unlock orchestration DAGs and enterprise database push.",
            )

        return (True, "")


