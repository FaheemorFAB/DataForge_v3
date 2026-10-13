"""
dataforge/api/services/usage.py
───────────────────────────────
Atomic Usage Reservation and Metering Service.
Guarantees two-phase resource reservation (reserve -> commit / release),
preventing race conditions and over-quota consumption during concurrent operations.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dataforge.api.services.entitlements import EntitlementService, PLAN_TIERS
from dataforge.api.storage.manager import STORE_DIR
from dataforge.db import db_client, db_first, db_insert, db_update

log = logging.getLogger(__name__)

_RESERVATIONS_FILE = STORE_DIR / "subscriptions" / "_reservations.json"
_LOCK = threading.Lock()


class QuotaExceededError(Exception):
    """Raised when an operation exceeds the tenant's plan quota."""
    def __init__(self, message: str, status_code: int = 402):
        super().__init__(message)
        self.status_code = status_code
        self.detail = message


class UsageService:
    """
    Central usage authority providing atomic reservation, commitment,
    and release of metered cloud resources.
    """

    @classmethod
    def _read_reservations(cls) -> Dict[str, Any]:
        _RESERVATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not _RESERVATIONS_FILE.exists():
            return {"reservations": {}, "idempotency_map": {}}
        try:
            with open(_RESERVATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"reservations": {}, "idempotency_map": {}}

    @classmethod
    def _write_reservations(cls, data: Dict[str, Any]) -> None:
        temp_file = _RESERVATIONS_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.replace(_RESERVATIONS_FILE)

    @classmethod
    def reserve(
        cls,
        *,
        tenant_id: int | str,
        metric: str,
        amount: int | float,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """
        Atomically reserves quota before dispatching an expensive operation.
        Raises QuotaExceededError (402) if limits would be violated.
        Returns the reservation record.
        """
        uid = int(tenant_id)
        with _LOCK:
            data = cls._read_reservations()
            reservations = data.setdefault("reservations", {})
            idempotency_map = data.setdefault("idempotency_map", {})

            # 1. Idempotency Check: Return existing reservation if replayed
            if idempotency_key in idempotency_map:
                res_id = idempotency_map[idempotency_key]
                if res_id in reservations:
                    existing = reservations[res_id]
                    if existing.get("status") in ("reserved", "committed"):
                        return existing

            # 2. Compute pending reserved amount for this tenant & metric
            pending_reserved = sum(
                r.get("amount", 0)
                for r in reservations.values()
                if r.get("tenant_id") == uid
                and r.get("metric") == metric
                and r.get("status") == "reserved"
            )

            # 3. Check plan limits against (committed usage + pending reserved)
            allowed, reason = EntitlementService.check_entitlement(
                user_id=uid,
                metric=metric,
                requested_units=amount + pending_reserved,
            )
            if not allowed:
                raise QuotaExceededError(reason, status_code=402)

            # 4. Create new reservation
            res_id = f"res_{uuid.uuid4().hex[:16]}"
            now_iso = datetime.now(timezone.utc).isoformat()
            reservation = {
                "id": res_id,
                "tenant_id": uid,
                "metric": metric,
                "amount": amount,
                "idempotency_key": idempotency_key,
                "status": "reserved",
                "created_at": now_iso,
                "updated_at": now_iso,
            }

            reservations[res_id] = reservation
            idempotency_map[idempotency_key] = res_id
            cls._write_reservations(data)

            log.info("[usage] Reserved %s %s for tenant %s (res_id: %s)", amount, metric, uid, res_id)
            return reservation

    @classmethod
    def commit(cls, reservation_id: str, actual_amount: Optional[int | float] = None) -> Dict[str, Any]:
        """
        Records actual usage after successful execution and marks reservation committed.
        """
        with _LOCK:
            data = cls._read_reservations()
            reservations = data.get("reservations", {})
            if reservation_id not in reservations:
                raise ValueError(f"Reservation '{reservation_id}' not found.")

            res = reservations[reservation_id]
            if res.get("status") == "committed":
                return res  # Already committed (idempotent)

            charge_amount = actual_amount if actual_amount is not None else res.get("amount", 1)
            res["status"] = "committed"
            res["actual_amount"] = charge_amount
            res["updated_at"] = datetime.now(timezone.utc).isoformat()
            cls._write_reservations(data)

            # Reconcile into permanent monthly usage ledger
            EntitlementService.record_usage(
                user_id=res["tenant_id"],
                metric=res["metric"],
                amount=charge_amount,
            )
            log.info("[usage] Committed reservation %s (%s %s)", reservation_id, charge_amount, res["metric"])
            return res

    @classmethod
    def release(cls, reservation_id: str) -> Dict[str, Any]:
        """
        Releases a reservation upon task failure or cancellation, freeing quota immediately.
        """
        with _LOCK:
            data = cls._read_reservations()
            reservations = data.get("reservations", {})
            if reservation_id not in reservations:
                return {}

            res = reservations[reservation_id]
            if res.get("status") == "released":
                return res

            res["status"] = "released"
            res["updated_at"] = datetime.now(timezone.utc).isoformat()
            cls._write_reservations(data)

            log.info("[usage] Released reservation %s for tenant %s", reservation_id, res["tenant_id"])
            return res
