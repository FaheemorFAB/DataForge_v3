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
import logging
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from dataforge.api.deps import CurrentUser, get_current_user
from dataforge.api.jobs.executor import run_in_executor
from dataforge.api.utils.json import safe_jsonable
from dataforge.api.routes.workspace import require_upload_with_data
from dataforge.api.services.procedure_service import ProcedureService
from dataforge.procedure_schema import ProcedureDefinition

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Stored Procedures"])


class AdHocProcedureRequest(BaseModel):
    upload_id: Optional[str] = None
    recipe: Optional[Dict[str, Any]] = None
    definition: Optional[Dict[str, Any]] = None
    runtime_params: Optional[Dict[str, Any]] = None


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


def _parse_recipe_or_definition(data: Dict[str, Any], default_upload_id: Optional[str] = None) -> Tuple[ProcedureDefinition, Optional[str]]:
    upload_id = default_upload_id
    if not isinstance(data, dict):
        raise ValueError("Recipe or definition must be a JSON object.")

    if not upload_id:
        upload_id = data.get("source_upload_id") or data.get("upload_id")

    # If standard ProcedureDefinition with nodes
    if "nodes" in data and isinstance(data["nodes"], list):
        proc_def = ProcedureDefinition(
            schema_version=data.get("schema_version", "1.0.0"),
            procedure_id=data.get("procedure_id", data.get("procedure_name", "adhoc_pipeline_procedure")),
            version=data.get("version", "1.0.0"),
            name=data.get("name", data.get("procedure_name", "Ad-hoc Pipeline Procedure")),
            description=data.get("description", "Pipeline procedure"),
            parameters=data.get("parameters", []),
            nodes=data.get("nodes", []),
            golden_tests=data.get("golden_tests", []),
        )
        return proc_def, upload_id

    # If step-based recipe (e.g. from template or custom recipe JSON)
    steps = data.get("steps", [])
    nodes = []
    prev_node_id = None

    for step in steps:
        step_id = step.get("step_id") or f"step_{len(nodes)}"
        step_type = step.get("type", "clean_names")
        inputs = []
        if prev_node_id and step_type != "source":
            inputs = [prev_node_id]

        if step_type == "source":
            if not upload_id and step.get("source_upload_id") and step.get("source_upload_id") != "active_dataset":
                upload_id = step.get("source_upload_id")
            nodes.append({
                "id": step_id,
                "type": "source",
                "inputs": [],
                "config": {"dataset_name": "default"}
            })
            prev_node_id = step_id

        elif step_type == "assertion_gate":
            raw_rules = step.get("rules", [])
            assertions = []
            for r in raw_rules:
                if isinstance(r, dict):
                    if r.get("rule") == "row_count_gte" or "row_count_gte" in r:
                        thresh = r.get("threshold", 1)
                        assertions.append({"type": "row_count", "min_rows": thresh, "severity": step.get("on_violation", "warn")})
                    elif r.get("rule") == "not_null":
                        assertions.append({"type": "not_null", "column": r.get("column"), "severity": step.get("on_violation", "warn")})
                    elif r.get("rule") == "unique":
                        assertions.append({"type": "unique", "column": r.get("column"), "severity": step.get("on_violation", "warn")})
                    else:
                        assertions.append({"type": "row_count", "min_rows": 1, "severity": "warn"})
            nodes.append({
                "id": step_id,
                "type": "assertion_gate",
                "inputs": inputs,
                "config": {
                    "assertions": assertions,
                    "fail_on_error": step.get("on_violation", "warn") == "error"
                }
            })
            prev_node_id = step_id

        elif step_type in ("clean_names", "filter", "impute", "compute", "aggregate", "dedupe", "cast"):
            nodes.append({
                "id": step_id,
                "type": step_type,
                "inputs": inputs,
                "config": step.get("config", {})
            })
            prev_node_id = step_id

        else: # transform_sql or fallback
            nodes.append({
                "id": step_id,
                "type": "clean_names",
                "inputs": inputs,
                "config": {"casing": "snake_case"}
            })
            prev_node_id = step_id

    if not nodes:
        nodes = [
            {"id": "s1_source", "type": "source", "inputs": [], "config": {"dataset_name": "default"}},
            {"id": "s2_clean", "type": "clean_names", "inputs": ["s1_source"], "config": {"casing": "snake_case"}},
            {"id": "out_final", "type": "output", "inputs": ["s2_clean"], "config": {}},
        ]
    else:
        nodes.append({
            "id": "out_final",
            "type": "output",
            "inputs": [prev_node_id] if prev_node_id else [],
            "config": {}
        })

    proc_def = ProcedureDefinition(
        schema_version="1.0.0",
        procedure_id=data.get("procedure_name", "custom_pipeline_procedure"),
        version="1.0.0",
        name=data.get("procedure_name", "Custom Pipeline Procedure"),
        description=data.get("description", "Pipeline DAG with quality assertion gates"),
        parameters=[
            {"name": p.get("name"), "type": p.get("type", "string"), "default": p.get("default_value", p.get("default"))}
            for p in data.get("parameters", []) if p.get("name")
        ],
        nodes=nodes,
    )
    return proc_def, upload_id


@router.post("/procedures/dry-run", summary="Ad-hoc dry run of procedure DAG against active dataset")
async def api_ad_hoc_dry_run(
    body: AdHocProcedureRequest,
    current_user: CurrentUser,
):
    try:
        raw_data = body.definition or body.recipe or {}
        definition, req_upload_id = _parse_recipe_or_definition(raw_data, body.upload_id)
        target_upload_id = body.upload_id or req_upload_id
        if not target_upload_id:
            raise HTTPException(status_code=400, detail="upload_id is required for procedure dry run.")

        await require_upload_with_data(target_upload_id, current_user)

        from dataforge.api.storage.manager import load
        from dataforge.procedure_engine import StoredProcedureExecutor

        df_input = load(target_upload_id, "df_clean")
        if df_input is None:
            df_input = load(target_upload_id, "df_raw")
        if df_input is None:
            raise HTTPException(status_code=404, detail=f"No dataset found for upload_id '{target_upload_id}'.")

        executor = StoredProcedureExecutor(definition, body.runtime_params)
        exec_result = executor.execute(
            input_dfs={"default": df_input},
            dry_run=True,
            upload_id=target_upload_id,
        )

        df_out = exec_result.pop("df_result", None)
        preview_rows = df_out.head(50).to_dict(orient="records") if df_out is not None else []
        columns = list(df_out.columns) if df_out is not None else []

        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "isDryRun": True,
                "dry_run": True,
                "status": "SUCCESS",
                "preview_sample": preview_rows,
                "columns": columns,
                "rows_affected": exec_result.get("rows_out", len(preview_rows)),
                "row_count": exec_result.get("rows_out", len(preview_rows)),
                "elapsed_ms": exec_result.get("duration_ms", 0),
                "execution_time_ms": exec_result.get("duration_ms", 0),
                **exec_result,
            })
        )
    except Exception as exc:
        logger.exception("Procedure dry-run failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/procedures/execute", summary="Ad-hoc live execution of procedure DAG against active dataset")
async def api_ad_hoc_execute(
    body: AdHocProcedureRequest,
    current_user: CurrentUser,
):
    try:
        raw_data = body.definition or body.recipe or {}
        definition, req_upload_id = _parse_recipe_or_definition(raw_data, body.upload_id)
        target_upload_id = body.upload_id or req_upload_id
        if not target_upload_id:
            raise HTTPException(status_code=400, detail="upload_id is required for procedure execution.")

        await require_upload_with_data(target_upload_id, current_user, min_role="Analyst")

        from dataforge.api.storage.manager import load, save
        from dataforge.procedure_engine import StoredProcedureExecutor

        df_input = load(target_upload_id, "df_clean")
        if df_input is None:
            df_input = load(target_upload_id, "df_raw")
        if df_input is None:
            raise HTTPException(status_code=404, detail=f"No dataset found for upload_id '{target_upload_id}'.")

        executor = StoredProcedureExecutor(definition, body.runtime_params)
        exec_result = executor.execute(
            input_dfs={"default": df_input},
            dry_run=False,
            upload_id=target_upload_id,
        )

        df_out = exec_result.pop("df_result", None)
        columns = list(df_out.columns) if df_out is not None else []

        if df_out is not None:
            from dataforge.api.utils.helpers import df_profile
            save(target_upload_id, "df_clean", df_out)
            new_prof = df_profile(df_out)
            old_prof = load(target_upload_id, "profile") or {}
            new_prof["filename"] = old_prof.get("filename", f"pipeline_result_{target_upload_id[:8]}.csv")
            save(target_upload_id, "clean_profile", new_prof)
            save(target_upload_id, "profile", new_prof)

            try:
                from dataforge.db import db_update
                db_update("uploads", target_upload_id, {
                    "row_count": len(df_out),
                    "col_count": df_out.shape[1],
                })
            except Exception:
                pass

        try:
            from dataforge.api.cache.manager import invalidate_upload
            invalidate_upload(target_upload_id)
        except Exception:
            pass

        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "isDryRun": False,
                "dry_run": False,
                "status": "SUCCESS",
                "snapshot_id": exec_result.get("output_snapshot_id"),
                "columns": columns,
                "rows_affected": exec_result.get("rows_out", len(df_out) if df_out is not None else 0),
                "row_count": exec_result.get("rows_out", len(df_out) if df_out is not None else 0),
                "elapsed_ms": exec_result.get("duration_ms", 0),
                "execution_time_ms": exec_result.get("duration_ms", 0),
                **exec_result,
            })
        )
    except Exception as exc:
        logger.exception("Procedure execute failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


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


@router.post("/procedures/{procedure_id}/execute", summary="Execute stored procedure alias for /run")
async def api_execute_procedure_alias(
    procedure_id: str,
    body: RunProcedureRequest,
    current_user: CurrentUser,
):
    return await api_run_procedure(procedure_id, body, current_user)


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
