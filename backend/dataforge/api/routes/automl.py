"""
dataforge/api/routes/automl.py
────────────────────────────────
AutoML training and model download routes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse

from dataforge.api.deps import CurrentUser, get_job_manager_dep, require_upload_with_data
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.jobs.manager import JobManager
from dataforge.api.schemas.automl import (
    AutoMLDetectTaskRequest,
    AutoMLTrainRequest,
    FeatureAnalysisRequest,
)
from dataforge.api.storage.manager import load, STORE_DIR, upath
from dataforge.api.utils.json import safe_jsonable
from dataforge.settings import PROJECTS_DIR

log = logging.getLogger(__name__)
router = APIRouter(tags=["automl"])


def _resolve_column(col_name: str, df_columns) -> str:
    """Case-insensitive column name resolution.
    Returns the actual DataFrame column name matching `col_name`,
    or raises HTTPException(400) if not found.
    """
    col_name = col_name.strip()
    if col_name in df_columns:
        return col_name
    # Case-insensitive fallback
    col_lower = col_name.lower()
    for real_col in df_columns:
        if real_col.lower() == col_lower:
            return real_col
    raise HTTPException(400, f"Column '{col_name}' not found. Available: {list(df_columns)}")


@router.post("/automl/detect-task", summary="Auto-detect ML task type for a target column")
async def api_automl_detect_task(
    body: AutoMLDetectTaskRequest,
    current_user: CurrentUser,
    request: Request = None,
    upload_id: Optional[str] = Query(default=None),
    share_token: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    eff_share_token = getattr(body, "share_token", None) or share_token or (request.headers.get("x-share-token") if request else None)
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user, share_token=eff_share_token, request=request)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        for td in [STORE_DIR / str(target_upload_id) / "tables", PROJECTS_DIR / str(target_upload_id) / "tables"]:
            if td.exists():
                pqs = list(td.glob("*.parquet"))
                if pqs:
                    import pandas as pd
                    df = pd.read_parquet(pqs[0])
                    break
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    target = _resolve_column(body.target_col, df.columns)

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


@router.post("/automl/feature-analysis", summary="Analyze features for target leakage, signal strength, and missingness")
async def api_automl_feature_analysis(
    body: FeatureAnalysisRequest,
    current_user: CurrentUser,
    request: Request = None,
    upload_id: Optional[str] = Query(default=None),
    share_token: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    eff_share_token = getattr(body, "share_token", None) or share_token or (request.headers.get("x-share-token") if request else None)
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user, share_token=eff_share_token, request=request)

    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        for td in [STORE_DIR / str(target_upload_id) / "tables", PROJECTS_DIR / str(target_upload_id) / "tables"]:
            if td.exists():
                pqs = list(td.glob("*.parquet"))
                if pqs:
                    import pandas as pd
                    df = pd.read_parquet(pqs[0])
                    break
    if df is None:
        raise HTTPException(400, "No dataset loaded")

    resolved_col = _resolve_column(body.target_col, df.columns)

    def _analyze():
        from dataforge.automl_trainer import analyze_features_for_target
        return analyze_features_for_target(df, resolved_col)

    result = await run_in_executor(_analyze)
    return JSONResponse(content=safe_jsonable(result))


@router.post("/automl/train", summary="Start an async AutoML training job")
async def api_automl_train(
    body: AutoMLTrainRequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    request: Request = None,
    job_manager: JobManager = Depends(get_job_manager_dep),
    upload_id: Optional[str] = Query(default=None),
    share_token: Optional[str] = Query(default=None),
):
    target_upload_id = body.upload_id or upload_id
    eff_share_token = getattr(body, "share_token", None) or share_token or (request.headers.get("x-share-token") if request else None)
    if not target_upload_id:
        raise HTTPException(400, "upload_id required")
    await require_upload_with_data(target_upload_id, current_user, min_role="Analyst", share_token=eff_share_token, request=request)

    # Validate target column exists
    df_clean = load(target_upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(target_upload_id, "df_raw")
    if df is None:
        for td in [STORE_DIR / str(target_upload_id) / "tables", PROJECTS_DIR / str(target_upload_id) / "tables"]:
            if td.exists():
                pqs = list(td.glob("*.parquet"))
                if pqs:
                    import pandas as pd
                    df = pd.read_parquet(pqs[0])
                    break
    if df is None:
        print("DEBUG: automl 400 - No dataset loaded (df is None)")
        raise HTTPException(400, "No dataset loaded")

    resolved_col = _resolve_column(body.target_col, df.columns)

    # Enforce plan quota on monthly AutoML training runs
    from dataforge.api.services.entitlements import EntitlementService
    allowed, reason = EntitlementService.check_entitlement(current_user.id, "automl_jobs", 1)
    if not allowed:
        raise HTTPException(402, detail=reason)
    EntitlementService.record_usage(current_user.id, "automl_jobs", 1)

    job_id = await job_manager.dispatch_automl(
        background_tasks, target_upload_id, current_user.id,
        target_col=resolved_col,
        task_choice=body.task_choice,
        time_budget=body.time_budget,
        test_size=body.test_size / 100.0,
        feature_whitelist=body.feature_whitelist,
        excluded_features=body.excluded_features,
        algorithm_whitelist=body.algorithm_whitelist,
        cv_strategy=body.cv_strategy,
        cv_folds=body.cv_folds,
        metric_override=body.metric_override,
        model_name=body.model_name,
        mode=body.mode,
        selected_model=body.selected_model,
        hyperparameters=body.hyperparameters,
    )
    return {"task_id": job_id, "queued": True, "upload_id": target_upload_id}


@router.get("/automl/download", summary="Download the trained model (.joblib)")
async def api_automl_download(
    current_user: CurrentUser,
    request: Request = None,
    upload_id: Optional[str] = Query(default=None),
    share_token: Optional[str] = Query(default=None),
):
    if not upload_id:
        raise HTTPException(400, "upload_id required")
    eff_share_token = share_token or (request.headers.get("x-share-token") if request else None)
    await require_upload_with_data(upload_id, current_user, share_token=eff_share_token, request=request)

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
    upload_id: Optional[str] = Query(default=None),
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
