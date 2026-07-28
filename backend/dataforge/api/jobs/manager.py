"""
dataforge/api/jobs/manager.py
───────────────────────────────
JobManager — central orchestrator for all background tasks.

Usage from routes:
    manager = get_job_manager()
    job_id = await manager.dispatch_insights(upload_id, user_id)
    # Returns immediately, task runs in background via asyncio.create_task

Architecture:
    dispatch_*()  →  create registry entry  →  asyncio.create_task(task_fn)
                                                        ↓
                                              run_in_executor(cpu_fn)
                                                        ↓
                                              ws_manager.send_to_user(...)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional
from fastapi import BackgroundTasks

from dataforge.api.jobs import registry

log = logging.getLogger(__name__)


class JobManager:
    """Orchestrates async background job dispatch."""

    async def dispatch_insights(
        self,
        background_tasks: BackgroundTasks,
        upload_id: int,
        user_id: int,
        top_n: int = 6,
    ) -> str:
        """Dispatch an insights job. Returns job_id immediately."""
        # Check for active job (idempotency)
        active = registry.get_active_job(upload_id, "insights")
        if active:
            return active["id"]

        from dataforge.api.jobs.tasks import run_insights_task
        job_id = await registry.create_job(user_id, upload_id, "insights")
        background_tasks.add_task(run_insights_task, job_id, upload_id, user_id, top_n)
        log.info("Dispatched insights job %s for upload_id=%d", job_id, upload_id)
        return job_id

    async def dispatch_automl(
        self,
        background_tasks: BackgroundTasks,
        upload_id: int,
        user_id: int,
        target_col: str,
        task_choice: str = "auto-detect",
        time_budget: int = 60,
        test_size: float = 0.2,
    ) -> str:
        """Dispatch an AutoML training job. Returns job_id immediately."""
        active = registry.get_active_job(upload_id, "automl")
        if active:
            return active["id"]

        from dataforge.api.jobs.tasks import run_automl_task
        job_id = await registry.create_job(user_id, upload_id, "automl")
        background_tasks.add_task(
            run_automl_task, job_id, upload_id, user_id, target_col,
            task_choice, time_budget, test_size
        )
        log.info("Dispatched automl job %s for upload_id=%d target=%s", job_id, upload_id, target_col)
        return job_id

    async def dispatch_eda(
        self,
        background_tasks: BackgroundTasks,
        upload_id: int,
        user_id: int,
        minimal: bool = True,
        sample_n: int = 5000,
    ) -> str:
        """Dispatch an EDA report generation job. Returns job_id immediately."""
        active = registry.get_active_job(upload_id, "eda")
        if active:
            return active["id"]

        from dataforge.api.jobs.tasks import run_eda_task
        job_id = await registry.create_job(user_id, upload_id, "eda")
        background_tasks.add_task(
            run_eda_task, job_id, upload_id, user_id, minimal, sample_n
        )
        log.info("Dispatched EDA job %s for upload_id=%d", job_id, upload_id)
        return job_id

    async def dispatch_report(self, background_tasks: BackgroundTasks, upload_id: int, user_id: int) -> str:
        """Dispatch an HTML report generation job. Returns job_id immediately."""
        active = registry.get_active_job(upload_id, "report")
        if active:
            return active["id"]

        from dataforge.api.jobs.tasks import generate_report_task
        job_id = await registry.create_job(user_id, upload_id, "report")
        background_tasks.add_task(generate_report_task, job_id, upload_id, user_id)
        log.info("Dispatched report job %s for upload_id=%d", job_id, upload_id)
        return job_id

    async def dispatch_alerts(self, background_tasks: BackgroundTasks, upload_id: int, user_id: int) -> str:
        """Dispatch an alerts check job. Returns job_id immediately."""
        active = registry.get_active_job(upload_id, "alerts")
        if active:
            return active["id"]

        from dataforge.api.jobs.tasks import check_alerts_task
        job_id = await registry.create_job(user_id, upload_id, "alerts")
        background_tasks.add_task(check_alerts_task, job_id, upload_id, user_id)
        log.info("Dispatched alerts job %s for upload_id=%d", job_id, upload_id)
        return job_id


# ── Singleton ─────────────────────────────────────────────────────────────────
_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    global _manager
    if _manager is None:
        _manager = JobManager()
    return _manager
