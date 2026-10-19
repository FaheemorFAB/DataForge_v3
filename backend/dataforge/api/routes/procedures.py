"""
dataforge/api/routes/procedures.py
──────────────────────────────────
FastAPI Router for DataForge Stored Procedures & Pipeline Engine (DF-SPE).
Endpoints:
  • POST /api/procedures             - Create procedure & initial version
  • GET  /api/procedures             - List accessible procedures
  • GET  /api/procedures/{id}         - Retrieve procedure & active version
  • POST /api/procedures/{id}/versions - Publish immutable new SemVer version
  • POST /api/procedures/{id}/validate - Validate DAG, parameters, and AST expressions
  • POST /api/procedures/{id}/dry-run  - Dry run preview against dataset without mutating
  • POST /api/procedures/{id}/run      - Execute procedure, commit snapshot & lineage
  • POST /api/procedures/{id}/rollback - Rollback active version pointer
  • GET  /api/procedures/{id}/export   - Compile to DuckDB SQL / dbt model script (P3-11)
  • GET  /api/runs/{run_id}            - Retrieve execution run audit and lineage details
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from dataforge.api.deps import CurrentUser, get_current_user
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.utils.json import safe_jsonable
from dataforge.api.routes.workspace import require_upload_with_data
from dataforge.api.services.procedure_service import ProcedureService
from dataforge.procedure_schema import ProcedureDefinition

router = APIRouter(prefix="/api", tags=["Stored Procedures"])


class CreateProcedureRequest(BaseModel):
    definition: ProcedureDefinition
    org_id: Optional[str] = None
    is_public: bool = False


class PublishVersionRequest(BaseModel):
    definition: ProcedureDefinition
    change_log: Optional[str] = ""


class RollbackVersionRequest(BaseModel):
    target_version_tag: str


class RunProcedureRequest(BaseModel):
    upload_id: str
    runtime_params: Dict[str, Any] = Field(default_factory=dict)
    version_tag: Optional[str] = None
    dry_run: bool = False
    idempotency_key: Optional[str] = None
    force: bool = False


# ── Procedure CRUD & Versions ──────────────────────────────────────────────────

@router.post("/procedures", summary="Create a new stored procedure definition and publish initial version")
async def api_create_procedure(
    body: CreateProcedureRequest,
    current_user: CurrentUser,
):
    try:
        def _create():
            return ProcedureService.create_procedure(
                user=current_user,
                definition=body.definition,
                org_id=body.org_id,
                is_public=body.is_public,
            )

        res = await run_in_executor(_create)
        return JSONResponse(status_code=201, content=safe_jsonable({"ok": True, **res}))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/procedures", summary="List all stored procedures accessible to the user")
async def api_list_procedures(
    current_user: CurrentUser,
    org_id: Optional[str] = Query(None),
):
    def _list():
        return ProcedureService.list_procedures(user=current_user, org_id=org_id)

    procedures = await run_in_executor(_list)
    return JSONResponse(content=safe_jsonable({"ok": True, "procedures": procedures}))


@router.get("/procedures/{procedure_id}", summary="Get stored procedure metadata and active version definition")
async def api_get_procedure(
    procedure_id: str,
    current_user: CurrentUser,
):
    def _get():
        return ProcedureService.get_procedure(procedure_id)

    proc_info = await run_in_executor(_get)
    if not proc_info:
        raise HTTPException(status_code=404, detail=f"Procedure '{procedure_id}' not found.")
    return JSONResponse(content=safe_jsonable({"ok": True, **proc_info}))


@router.post("/procedures/{procedure_id}/versions", summary="Publish an immutable new SemVer version")
async def api_publish_version(
    procedure_id: str,
    body: PublishVersionRequest,
    current_user: CurrentUser,
):
    try:
        def _publish():
            return ProcedureService.publish_version(
                user=current_user,
                procedure_id=procedure_id,
                definition=body.definition,
                change_log=body.change_log or "",
            )

        res = await run_in_executor(_publish)
        return JSONResponse(status_code=201, content=safe_jsonable({"ok": True, "version": res}))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/procedures/{procedure_id}/rollback", summary="Rollback active version pointer to a prior immutable version")
async def api_rollback_version(
    procedure_id: str,
    body: RollbackVersionRequest,
    current_user: CurrentUser,
):
    try:
        def _rollback():
            return ProcedureService.rollback_version(
                user=current_user,
                procedure_id=procedure_id,
                target_version_tag=body.target_version_tag,
            )

        res = await run_in_executor(_rollback)
        return JSONResponse(content=safe_jsonable({"ok": True, **res}))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── DAG Validation & Execution ─────────────────────────────────────────────────

@router.post("/procedures/{procedure_id}/validate", summary="Validate DAG topological order, cycles, and schema rules")
async def api_validate_procedure(
    procedure_id: str,
    body: Optional[ProcedureDefinition] = None,
    current_user: CurrentUser = None,
):
    try:
        if body:
            definition = body
        else:
            proc_info = ProcedureService.get_procedure(procedure_id)
            if not proc_info or not proc_info.get("active_version"):
                raise HTTPException(status_code=404, detail="Procedure definition not found")
            definition = ProcedureDefinition(**proc_info["active_version"]["definition_json"])

        ordered_nodes = definition.topological_sort()
        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "is_dag": True,
                "node_count": len(ordered_nodes),
                "execution_order": [n.id for n in ordered_nodes],
            })
        )
    except Exception as exc:
        return JSONResponse(status_code=422, content={"ok": False, "is_dag": False, "error": str(exc)})


@router.post("/procedures/{procedure_id}/dry-run", summary="Dry run procedure against a dataset without mutating")
async def api_dry_run_procedure(
    procedure_id: str,
    body: RunProcedureRequest,
    current_user: CurrentUser,
):
    await require_upload_with_data(body.upload_id, current_user)
    try:
        def _dry_run():
            return ProcedureService.execute_procedure(
                user=current_user,
                procedure_id=procedure_id,
                upload_id=body.upload_id,
                runtime_params=body.runtime_params,
                version_tag=body.version_tag,
                dry_run=True,
            )

        result = await run_in_executor(_dry_run)
        # Convert df_result to preview sample
        df_out = result.pop("df_result", None)
        preview_rows = df_out.head(50).to_dict(orient="records") if df_out is not None else []
        columns = list(df_out.columns) if df_out is not None else []

        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "preview_sample": preview_rows,
                "columns": columns,
                **result,
            })
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/procedures/{procedure_id}/run", summary="Execute stored procedure, commit immutable snapshot & lineage")
async def api_run_procedure(
    procedure_id: str,
    body: RunProcedureRequest,
    current_user: CurrentUser,
):
    await require_upload_with_data(body.upload_id, current_user, min_role="Analyst")
    try:
        def _run():
            return ProcedureService.execute_procedure(
                user=current_user,
                procedure_id=procedure_id,
                upload_id=body.upload_id,
                runtime_params=body.runtime_params,
                version_tag=body.version_tag,
                dry_run=False,
                idempotency_key=body.idempotency_key,
                force=body.force,
            )

        result = await run_in_executor(_run)
        df_out = result.pop("df_result", None)

        from dataforge.api.cache.manager import invalidate_upload
        invalidate_upload(body.upload_id)

        return JSONResponse(
            status_code=200,
            content=safe_jsonable({
                "ok": True,
                "columns": list(df_out.columns) if df_out is not None else [],
                **result,
            }),
            headers={"ETag": f'"{result.get("version_id")}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs/{run_id}", summary="Get stored procedure execution run details and lineage manifest")
async def api_get_run(
    run_id: str,
    current_user: CurrentUser,
):
    def _fetch_run():
        return ProcedureService.get_run(run_id)

    run_info = await run_in_executor(_fetch_run)
    if not run_info:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return JSONResponse(content=safe_jsonable({"ok": True, "run": run_info}))


@router.get("/procedures/{procedure_id}/export", summary="Compile procedure to DuckDB SQL or dbt model script (P3-11)")
async def api_export_procedure_sql(
    procedure_id: str,
    current_user: CurrentUser,
    format: str = Query("sql", pattern="^(sql|dbt)$"),
):
    try:
        def _export():
            return ProcedureService.compile_to_sql_or_dbt(procedure_id, format_type=format)

        code_str = await run_in_executor(_export)
        return PlainTextResponse(content=code_str, media_type="text/plain")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
