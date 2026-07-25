"""
dataforge/api/repositories/report.py
──────────────────────────────────────
Report, alert, schedule, metric, and source repositories.
"""

from __future__ import annotations
from typing import Optional
from dataforge.db import db_get, db_all, db_insert, db_update, db_delete, db_count, db_first, db_client


class ReportRepository:

    def get_by_id(self, report_id: int) -> Optional[dict]:
        return db_get("reports", report_id)

    def list_for_user(self, user_id: int, limit: int = 50) -> list[dict]:
        if not db_client:
            return []
        try:
            res = (db_client.table("reports")
                   .select("*, uploads(filename)")
                   .eq("user_id", user_id)
                   .order("created_at", desc=True)
                   .limit(limit)
                   .execute())
            return res.data if res and res.data else []
        except Exception:
            return []

    def create(self, data: dict) -> Optional[dict]:
        return db_insert("reports", data) or None


class AlertRepository:

    def list_unresolved(self, user_id: int, limit: int = 100) -> list[dict]:
        if not db_client:
            return []
        try:
            res = (db_client.table("alerts")
                   .select("*, uploads(filename)")
                   .eq("user_id", user_id)
                   .eq("resolved", False)
                   .order("triggered_at", desc=True)
                   .limit(limit)
                   .execute())
            return res.data if res and res.data else []
        except Exception:
            return []

    def resolve(self, alert_id: int) -> bool:
        from datetime import datetime, timezone
        res = db_update("alerts", alert_id, {
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        })
        return bool(res)

    def get_by_id(self, alert_id: int) -> Optional[dict]:
        return db_get("alerts", alert_id)

    def count_unresolved(self, user_id: int) -> int:
        return db_count("alerts", {"user_id": user_id, "resolved": False})


class ScheduleRepository:

    def list_for_user(self, user_id: int) -> list[dict]:
        return db_all("report_schedules", {"user_id": user_id, "enabled": True},
                      order_by="created_at", limit=50)

    def get_by_id(self, schedule_id: int) -> Optional[dict]:
        return db_get("report_schedules", schedule_id)

    def create(self, data: dict) -> Optional[dict]:
        return db_insert("report_schedules", data) or None

    def disable(self, schedule_id: int) -> bool:
        res = db_update("report_schedules", schedule_id, {"enabled": False})
        return bool(res)

    def count_active(self, user_id: int) -> int:
        return db_count("report_schedules", {"user_id": user_id, "enabled": True})


class MetricRepository:

    def list_for_user(self, user_id: int) -> list[dict]:
        return db_all("metric_definitions", {"user_id": user_id}, order_by="created_at")

    def get_by_id(self, metric_id: int) -> Optional[dict]:
        return db_get("metric_definitions", metric_id)

    def find_by_name(self, user_id: int, name: str) -> Optional[dict]:
        return db_first("metric_definitions", {"user_id": user_id, "name": name})

    def create(self, data: dict) -> Optional[dict]:
        return db_insert("metric_definitions", data) or None

    def update(self, metric_id: int, data: dict) -> Optional[dict]:
        return db_update("metric_definitions", metric_id, data) or None

    def delete(self, metric_id: int) -> bool:
        return db_delete("metric_definitions", metric_id)


class SourceRepository:

    def list_enabled(self, user_id: int) -> list[dict]:
        return db_all("data_sources", {"user_id": user_id, "enabled": True})


report_repo   = ReportRepository()
alert_repo    = AlertRepository()
schedule_repo = ScheduleRepository()
metric_repo   = MetricRepository()
source_repo   = SourceRepository()
