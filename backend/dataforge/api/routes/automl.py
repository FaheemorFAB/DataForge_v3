"""
dataforge/api/routes/automl.py
────────────────────────────────
AutoML training and model download routes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from dataforge.api.deps import CurrentUser, get_job_manager_dep, require_upload_with_data
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.automl import AutoMLDetectTaskRequest, AutoMLTrainRequest
from dataforge.api.storage.manager import load
from dataforge.api.utils.json import safe_jsonable
from dataforge.settings import PROJECTS_DIR

log = logging.getLogger(__name__)
router = APIRouter(tags=["automl"])


@router.post("/automl/detect-task", summary="Auto-detect ML task type for a target column")
async def api_automl_detect_task(
    body: AutoMLDetectTaskRequest,
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    target = body.target_col.strip()
    if not target or target not in df.columns:
        raise HTTPException(400, f"Column '{target}' not found")

    try:
        def _detect():
            from dataforge.automl_trainer import _detect_task
            task_type = _detect_task(df[target])
            n_unique = int(df[target].nunique())
            return {"task": task_type, "n_unique": n_unique, "needs_selection": False}

        result = await run_in_executor(_detect)
        return JSONResponse(content=safe_jsonable(result))
    except Exception as exc:
        log.exception("Task detection failed: %s", exc)
        raise HTTPException(500, f"Task detection failed: {exc}")


@router.post("/automl/train", summary="Start an async AutoML training job")
async def api_automl_train(
    body: AutoMLTrainRequest,
    current_user: CurrentUser,
    job_manager: JobManager = Depends(get_job_manager_dep),
    upload_id: Optional[int] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user)

    # Validate target column exists
    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "No dataset loaded")
    if body.target_col not in df.columns:
        raise HTTPException(400, f"Column '{body.target_col}' not found")

    job_id = await job_manager.dispatch_automl(
        target_upload_id, current_user.id,
        target_col=body.target_col,
        task_choice=body.task_choice,
        time_budget=body.time_budget,
        test_size=body.test_size / 100.0,
    )
    return {"task_id": job_id, "queued": True, "upload_id": target_upload_id}


@router.get("/automl/download", summary="Download the trained model (.joblib)")
async def api_automl_download(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    model_path = PROJECTS_DIR / str(upload_id) / "model_pkl.joblib"
    if not model_path.exists():
        model_path = STORE_DIR / str(upload_id) / "model_pkl.joblib"
    if not model_path.exists():
        raise HTTPException(404, "No trained model found")

    def _iter():
        with open(model_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        _iter(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=model_{upload_id}.joblib"},
    )


@router.get("/clean/download", summary="Download the cleaned dataset as CSV")
async def api_clean_download(
    current_user: CurrentUser,
    upload_id: Optional[int] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(upload_id, current_user)

    df = load(upload_id, "df_clean")
    if df is None:
        raise HTTPException(404, "No cleaned dataset found")

    import io
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cleaned_{upload_id}.csv"},
    )
