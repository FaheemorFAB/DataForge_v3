"""
dataforge/api/routes/models.py
──────────────────────────────
REST endpoints for Enterprise Model Registry, Real-time Online Inference,
and 1-Click Containerized Docker Package Export.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse


from dataforge.api.deps import CurrentUser
from dataforge.db import User
from dataforge.api.schemas.models import (
    BatchPredictRequest,
    ApplyToWorkspaceRequest,
    ModelRecordResponse,
    PredictionResultResponse,
    PredictRequest,
    RegisterModelRequest,
    UpdateModelStatusRequest,
)
from dataforge.api.utils.json import safe_jsonable
from dataforge.models.registry import ModelRegistry
from dataforge.teams.manager import TeamManager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["models"])


def _resolve_user_email(current_user: User) -> str:
    return current_user.email


@router.get("", summary="List all registered models")
async def list_models(
    current_user: CurrentUser,
    org_id: Optional[str] = Query(None, description="Filter by Organization ID"),
):
    """Returns all models in the enterprise registry (pre-seeded with production benchmarks)."""
    models = ModelRegistry.list_models(org_id=org_id)
    return JSONResponse(content=safe_jsonable({"ok": True, "models": models}))


@router.get("/{model_id}", summary="Get model details and metadata")
async def get_model(model_id: str, current_user: CurrentUser):
    """Retrieves full model metadata, training metrics, and feature signature."""
    m = ModelRegistry.get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")
    return JSONResponse(content=safe_jsonable({"ok": True, "model": m}))


@router.post("", summary="Register a new model into the enterprise catalog")
async def register_model(
    req: RegisterModelRequest,
    current_user: CurrentUser,
):
    """Saves a model artifact from AutoML tournament into the team registry."""
    creator = _resolve_user_email(current_user)
    m = ModelRegistry.register_model(
        org_id=req.org_id,
        model_name=req.model_name,
        task_type=req.task_type,
        algorithm=req.algorithm,
        target_column=req.target_column,
        features=req.features,
        metrics=req.metrics,
        created_by=creator,
        upload_id=req.upload_id,
        version=req.version or "v1.0.0",
        summary=req.summary,
    )
    # Log audit event
    try:
        TeamManager.record_audit(
            org_id=req.org_id,
            user_id=getattr(current_user, "id", 1) if current_user else 1,
            user_email=creator,
            action="REGISTER_MODEL",
            target=req.model_name,
            metadata={"model_id": m["id"], "algorithm": req.algorithm, "version": req.version},
        )
    except Exception as e:
        log.warning("Audit log write failed: %s", e)

    return JSONResponse(content=safe_jsonable({"ok": True, "model": m}))


@router.patch("/{model_id}/status", summary="Promote model (production / staging / archived)")
async def update_model_status(
    model_id: str,
    req: UpdateModelStatusRequest,
    current_user: CurrentUser,
):
    """Promotes or archives a model in the production registry."""
    try:
        updated = ModelRegistry.update_model_status(model_id, req.status)
        creator = _resolve_user_email(current_user)
        try:
            TeamManager.record_audit(
                org_id=updated.get("org_id", "default"),
                user_id=current_user.id,
                user_email=creator,
                action="UPDATE_MODEL_STATUS",
                target=updated["model_name"],
                metadata={"model_id": model_id, "new_status": req.status},
            )
        except Exception:
            pass
        return JSONResponse(content=safe_jsonable({"ok": True, "model": updated}))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{model_id}/predict", response_model=PredictionResultResponse, summary="Execute real-time online inference")
async def predict_model(
    model_id: str,
    req: PredictRequest,
    current_user: CurrentUser,
):
    """
    Sub-second online prediction endpoint.
    Computes class probabilities, confidence intervals, and inference latency.
    """
    try:
        result = ModelRegistry.predict(model_id, req.features)
        return JSONResponse(content=safe_jsonable(result))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@router.post("/{model_id}/batch-predict", summary="Score batch records in microsecond vector mode")
async def batch_predict_model(
    model_id: str,
    req: BatchPredictRequest,
    current_user: CurrentUser,
):
    """Scores a batch of json records with bulk throughput."""
    m = ModelRegistry.get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    results = []
    for r in req.records:
        res = ModelRegistry.predict(model_id, r)
        results.append(res["prediction"])

    return JSONResponse(
        content=safe_jsonable({
            "ok": True,
            "model_id": model_id,
            "count": len(results),
            "predictions": results,
        })
    )


@router.post("/{model_id}/batch-predict-csv", summary="Bulk score a CSV dataset and return annotated predictions")
async def batch_predict_csv(
    model_id: str,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """
    Accepts an uploaded CSV file, scores every row against the model,
    and returns a downloadable scored CSV with 'predicted_target' and optional 'confidence'.
    """
    import pandas as pd
    m = ModelRegistry.get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

        predictions = []
        probabilities = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            res = ModelRegistry.predict(model_id, row_dict)
            predictions.append(res.get("prediction"))
            probabilities.append(res.get("probability"))

        target_col = m.get("target_column") or "output"
        df[f"predicted_{target_col}"] = predictions
        if any(p is not None for p in probabilities):
            df["prediction_confidence"] = [round(float(p), 4) if p is not None else 1.0 for p in probabilities]

        output_stream = io.StringIO()
        df.to_csv(output_stream, index=False)
        output_bytes = output_stream.getvalue().encode("utf-8")

        in_filename = file.filename or "dataset.csv"
        filename = f"scored_{in_filename}"
        return StreamingResponse(
            io.BytesIO(output_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Batch predict CSV error: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to score CSV: {str(e)}")


@router.post("/{model_id}/apply-to-workspace", summary="Apply model inference directly to the active workspace dataset")
async def apply_to_workspace(
    model_id: str,
    req: ApplyToWorkspaceRequest,
    current_user: CurrentUser,
):
    """
    Scores the active workspace dataset (df_clean / df_raw) against the model,
    appends 'predicted_{target}' and 'prediction_confidence' columns,
    and updates workspace dataset storage and profiles.
    """
    from dataforge.api.storage.manager import load, save
    from dataforge.api.cache.manager import invalidate_upload
    from dataforge.api.deps import require_upload_with_data
    from dataforge.profiler import df_profile
    from dataforge.db import db_get

    upload_id = req.upload_id
    await require_upload_with_data(upload_id, current_user)

    m = ModelRegistry.get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    # Load active dataset
    df = load(upload_id, "df_clean")
    if df is None:
        df = load(upload_id, "df_raw")
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="Workspace dataset is empty or not loaded.")

    try:
        eval_result = ModelRegistry.predict_dataframe(model_id, df)

        target_name = m.get("target_column") or "target"
        col_pred = req.pred_col_name or f"predicted_{target_name}"
        col_conf = f"{col_pred}_confidence"

        df[col_pred] = eval_result["predictions"]
        new_cols = [col_pred]

        if eval_result.get("confidences") is not None:
            df[col_conf] = eval_result["confidences"]
            new_cols.append(col_conf)

        # Save back to df_clean so all workspace tabs see it
        save(upload_id, "df_clean", df)

        # Compute updated profile and save
        up_row = db_get("uploads", upload_id) or {}
        filename = up_row.get("filename", "dataset.csv")
        try:
            profile = df_profile(df, filename)
            save(upload_id, "clean_profile", profile)
        except Exception as p_exc:
            log.warning("Profile re-computation error: %s", p_exc)

        invalidate_upload(upload_id)

        sample_preview = df[new_cols].head(5).to_dict("records")
        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "model_id": model_id,
                "model_name": m.get("model_name"),
                "rows_scored": len(df),
                "new_columns": new_cols,
                "sample_preview": sample_preview,
                "latency_ms": eval_result.get("latency_ms", 0),
                "is_real_artifact": eval_result.get("is_real_artifact", False),
            })
        )
    except Exception as e:
        log.exception("Apply to workspace failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to apply model to workspace: {str(e)}")


@router.get("/{model_id}/docker-package", summary="Download 1-click standalone Docker microservice bundle")
async def export_docker_package(model_id: str):
    """
    Generates a production-ready zip archive containing:
    - Dockerfile (FastAPI slim)
    - app.py (Inference microservice with /predict, /batch_predict, /health, /metadata)
    - requirements.txt
    - docker-compose.yml
    - README.md
    """
    try:
        zip_bytes = ModelRegistry.export_docker_package(model_id)
        m = ModelRegistry.get_model(model_id)
        slug = m["model_name"].lower().replace(" ", "-") if m else model_id
        filename = f"dataforge-{slug}-container.zip"

        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Container export error: {str(e)}")


@router.delete("/{model_id}", summary="Delete a model from the enterprise registry")
async def delete_model(
    model_id: str,
    current_user: CurrentUser,
):
    """Permanently deletes a registered model from the catalog."""
    m = ModelRegistry.get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    deleted = ModelRegistry.delete_model(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' could not be deleted.")

    creator = _resolve_user_email(current_user)
    try:
        TeamManager.record_audit(
            org_id=m.get("org_id", "default"),
            user_id=getattr(current_user, "id", 1) if current_user else 1,
            user_email=creator,
            action="DELETE_MODEL",
            target=m.get("model_name", model_id),
            metadata={"model_id": model_id, "algorithm": m.get("algorithm")},
        )
    except Exception as e:
        log.warning("Audit log write failed on model deletion: %s", e)

    return JSONResponse(content=safe_jsonable({
        "ok": True,
        "model_id": model_id,
        "message": f"Model '{m.get('model_name', model_id)}' successfully deleted from registry."
    }))

