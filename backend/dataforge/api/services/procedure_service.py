"""
dataforge/api/services/procedure_service.py
───────────────────────────────────────────
Service layer for Stored Procedures (DF-SPE).
Manages:
  • CRUD for sys_procedures, sys_procedure_versions, and sys_procedure_runs
  • SemVer version validation, immutability, and rollback pointers
  • Dry-run preview execution and live execution with snapshot creation
  • Idempotent execution cache matching (procedure_id, version_tag, input_snapshot_id, runtime_params)
  • Exporting procedure DAG to standard SQL and dbt models (P3-11)
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import secrets
import threading
from typing import Any, Dict, List, Optional
import pandas as pd

from dataforge.api.storage.manager import STORE_DIR, load, save
from dataforge.api.storage.snapshots import SnapshotManager
from dataforge.db import (
    Procedure,
    ProcedureRun,
    ProcedureVersion,
    User,
    db_all,
    db_first,
    db_get,
    db_insert,
    db_update,
)
from dataforge.procedure_engine import StoredProcedureExecutor
from dataforge.procedure_schema import ProcedureDefinition

logger = logging.getLogger(__name__)
_LOCK = threading.RLock()


class ProcedureService:
    """Manages stored procedures, versions, and runs."""

    @classmethod
    def _local_proc_dir(cls) -> Any:
        p = STORE_DIR / "_procedures"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def create_procedure(
        cls,
        user: User,
        definition: ProcedureDefinition,
        org_id: Optional[str] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """Creates a new stored procedure and publishes its initial version (e.g. 1.0.0)."""
        # Validate DAG
        _ = definition.topological_sort()

        proc_id = definition.procedure_id or f"sp_{secrets.token_hex(6)}"
        now_iso = datetime.now(timezone.utc).isoformat()
        version_tag = definition.version or "1.0.0"
        version_id = f"pv_{secrets.token_hex(8)}"
        content_hash = hashlib.sha256(definition.model_dump_json().encode()).hexdigest()

        proc_record = {
            "id": proc_id,
            "org_id": org_id,
            "created_by_user_id": user.id,
            "name": definition.name,
            "slug": proc_id,
            "description": definition.description,
            "category": "general",
            "is_public": is_public,
            "active_version_id": version_id,
            "active_version_tag": version_tag,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        version_record = {
            "id": version_id,
            "procedure_id": proc_id,
            "version_tag": version_tag,
            "content_hash": content_hash,
            "definition_json": definition.model_dump(),
            "change_log": "Initial version publish",
            "golden_tests_json": [gt.model_dump() for gt in definition.golden_tests],
            "created_by_user_id": user.id,
            "created_at": now_iso,
        }

        with _LOCK:
            # 1. Database write (if Supabase configured)
            db_insert("sys_procedures", proc_record)
            db_insert("sys_procedure_versions", version_record)

            # 2. Local disk sync
            p_dir = cls._local_proc_dir() / proc_id
            p_dir.mkdir(parents=True, exist_ok=True)
            with open(p_dir / "meta.json", "w", encoding="utf-8") as f:
                json.dump(proc_record, f, indent=2)
            with open(p_dir / f"version_{version_tag}.json", "w", encoding="utf-8") as f:
                json.dump(version_record, f, indent=2)

        return {
            "procedure": proc_record,
            "active_version": version_record,
        }

    @classmethod
    def list_procedures(
        cls,
        user: User,
        org_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists procedures accessible to the user."""
        results: List[Dict[str, Any]] = []

        # Try db
        db_records = db_all("sys_procedures")
        if db_records:
            for r in db_records:
                if r.get("created_by_user_id") == user.id or r.get("is_public") or (org_id and r.get("org_id") == org_id):
                    results.append(r)
            return results

        # Fallback to local disk
        p_dir = cls._local_proc_dir()
        for item in p_dir.iterdir():
            if item.is_dir() and (item / "meta.json").exists():
                try:
                    with open(item / "meta.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("created_by_user_id") == user.id or data.get("is_public") or (org_id and data.get("org_id") == org_id):
                            results.append(data)
                except Exception:
                    pass

        return results

    @classmethod
    def get_procedure(cls, procedure_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves procedure metadata and its active version definition."""
        # Check DB
        proc_data = db_get("sys_procedures", procedure_id)
        if not proc_data:
            # Check local disk
            p_dir = cls._local_proc_dir() / procedure_id
            if (p_dir / "meta.json").exists():
                with open(p_dir / "meta.json", "r", encoding="utf-8") as f:
                    proc_data = json.load(f)

        if not proc_data:
            return None

        # Fetch active version
        active_ver_id = proc_data.get("active_version_id")
        active_ver_tag = proc_data.get("active_version_tag", "1.0.0")
        ver_data = None

        if active_ver_id:
            ver_data = db_get("sys_procedure_versions", active_ver_id)

        if not ver_data:
            p_dir = cls._local_proc_dir() / procedure_id
            target_file = p_dir / f"version_{active_ver_tag}.json"
            if target_file.exists():
                with open(target_file, "r", encoding="utf-8") as f:
                    ver_data = json.load(f)

        return {
            "procedure": proc_data,
            "active_version": ver_data,
        }

    @classmethod
    def publish_version(
        cls,
        user: User,
        procedure_id: str,
        definition: ProcedureDefinition,
        change_log: str = "",
    ) -> Dict[str, Any]:
        """Publishes an immutable new SemVer version for an existing procedure."""
        proc_info = cls.get_procedure(procedure_id)
        if not proc_info:
            raise ValueError(f"Procedure '{procedure_id}' not found.")

        # Validate DAG
        _ = definition.topological_sort()

        version_tag = definition.version
        version_id = f"pv_{secrets.token_hex(8)}"
        content_hash = hashlib.sha256(definition.model_dump_json().encode()).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()

        version_record = {
            "id": version_id,
            "procedure_id": procedure_id,
            "version_tag": version_tag,
            "content_hash": content_hash,
            "definition_json": definition.model_dump(),
            "change_log": change_log,
            "golden_tests_json": [gt.model_dump() for gt in definition.golden_tests],
            "created_by_user_id": user.id,
            "created_at": now_iso,
        }

        with _LOCK:
            db_insert("sys_procedure_versions", version_record)
            db_update("sys_procedures", procedure_id, {
                "active_version_id": version_id,
                "active_version_tag": version_tag,
                "updated_at": now_iso,
            })

            p_dir = cls._local_proc_dir() / procedure_id
            p_dir.mkdir(parents=True, exist_ok=True)
            with open(p_dir / f"version_{version_tag}.json", "w", encoding="utf-8") as f:
                json.dump(version_record, f, indent=2)

            # Update meta
            meta_path = p_dir / "meta.json"
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["active_version_id"] = version_id
                meta["active_version_tag"] = version_tag
                meta["updated_at"] = now_iso
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)

        return version_record

    @classmethod
    def rollback_version(
        cls,
        user: User,
        procedure_id: str,
        target_version_tag: str,
    ) -> Dict[str, Any]:
        """Rolls back the active pointer to a prior immutable version tag."""
        p_dir = cls._local_proc_dir() / procedure_id
        target_file = p_dir / f"version_{target_version_tag}.json"
        if not target_file.exists():
            raise ValueError(f"Version '{target_version_tag}' not found for procedure '{procedure_id}'.")

        with open(target_file, "r", encoding="utf-8") as f:
            ver_data = json.load(f)

        now_iso = datetime.now(timezone.utc).isoformat()
        with _LOCK:
            db_update("sys_procedures", procedure_id, {
                "active_version_id": ver_data["id"],
                "active_version_tag": target_version_tag,
                "updated_at": now_iso,
            })
            meta_path = p_dir / "meta.json"
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["active_version_id"] = ver_data["id"]
                meta["active_version_tag"] = target_version_tag
                meta["updated_at"] = now_iso
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)

        return {
            "procedure_id": procedure_id,
            "active_version_tag": target_version_tag,
            "active_version_id": ver_data["id"],
        }

    @classmethod
    def execute_procedure(
        cls,
        user: User,
        procedure_id: str,
        upload_id: str,
        runtime_params: Optional[Dict[str, Any]] = None,
        version_tag: Optional[str] = None,
        dry_run: bool = False,
        idempotency_key: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes procedure against dataset upload_id.
        Supports dry_run preview, idempotency check, and content-addressed snapshotting.
        """
        proc_info = cls.get_procedure(procedure_id)
        if not proc_info:
            raise ValueError(f"Procedure '{procedure_id}' not found.")

        active_ver = proc_info.get("active_version")
        if not active_ver or "definition_json" not in active_ver:
            raise ValueError(f"Active version definition not found for procedure '{procedure_id}'.")

        definition = ProcedureDefinition(**active_ver["definition_json"])

        # Fetch input dataset
        df_input = load(upload_id, "df_clean")
        if df_input is None:
            df_input = load(upload_id, "df_raw")
        if df_input is None:
            raise ValueError(f"No dataset found for upload_id '{upload_id}'.")

        # Snapshot and idempotency resolution
        input_snapshot_id = load(upload_id, "active_snapshot_id")
        run_id = f"run_{secrets.token_hex(8)}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check idempotency cache if not forced and not dry run
        if not dry_run and not force and idempotency_key:
            runs_dir = cls._local_proc_dir() / "_runs"
            if runs_dir.exists():
                for rf in runs_dir.glob("*.json"):
                    try:
                        with open(rf, "r", encoding="utf-8") as f:
                            r_cached = json.load(f)
                            if (
                                r_cached.get("idempotency_key") == idempotency_key
                                and r_cached.get("status") == "SUCCESS"
                            ):
                                return r_cached
                    except Exception:
                        pass

        # Execute DAG via StoredProcedureExecutor
        executor = StoredProcedureExecutor(definition, runtime_params)
        exec_result = executor.execute(
            input_dfs={"default": df_input},
            dry_run=dry_run,
            upload_id=upload_id,
            input_snapshot_id=input_snapshot_id,
        )

        run_record = {
            "id": run_id,
            "procedure_id": procedure_id,
            "version_id": active_ver["id"],
            "version_tag": definition.version,
            "upload_id": upload_id,
            "input_snapshot_id": input_snapshot_id,
            "output_snapshot_id": exec_result.get("output_snapshot_id"),
            "idempotency_key": idempotency_key,
            "triggered_by_user_id": user.id,
            "runtime_params": executor.params,
            "status": "SUCCESS",
            "rows_in": exec_result["rows_in"],
            "rows_out": exec_result["rows_out"],
            "duration_ms": exec_result["duration_ms"],
            "quality_score": 1.0,
            "step_logs": exec_result["step_logs"],
            "lineage_manifest": exec_result["lineage_manifest"],
            "created_at": now_iso,
        }

        if not dry_run:
            with _LOCK:
                db_insert("sys_procedure_runs", run_record)
                runs_dir = cls._local_proc_dir() / "_runs"
                runs_dir.mkdir(parents=True, exist_ok=True)
                with open(runs_dir / f"{run_id}.json", "w", encoding="utf-8") as f:
                    json.dump(run_record, f, indent=2)

        exec_result["run_id"] = run_id
        return exec_result

    @classmethod
    def get_run(cls, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a past procedure execution run."""
        # DB check
        r_db = db_get("sys_procedure_runs", run_id)
        if r_db:
            return r_db

        # Disk check
        run_file = cls._local_proc_dir() / "_runs" / f"{run_id}.json"
        if run_file.exists():
            with open(run_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    @classmethod
    def compile_to_sql_or_dbt(cls, procedure_id: str, format_type: str = "sql") -> str:
        """
        Compiles the stored procedure into clean DuckDB SQL or dbt CTE model script (P3-11).
        """
        proc_info = cls.get_procedure(procedure_id)
        if not proc_info:
            raise ValueError(f"Procedure '{procedure_id}' not found.")
        definition = ProcedureDefinition(**proc_info["active_version"]["definition_json"])
        sorted_nodes = definition.topological_sort()

        lines: List[str] = [
            f"-- DataForge Stored Procedure: {definition.name} (v{definition.version})",
            f"-- Generated on {datetime.now(timezone.utc).isoformat()}",
            "",
        ]

        if format_type == "dbt":
            lines.append("{{ config(materialized='table') }}")
            lines.append("")

        cte_definitions: List[str] = []
        for idx, node in enumerate(sorted_nodes):
            node_id = node.id
            node_type = node.type
            cfg = node.config or {}
            cte_name = f"step_{idx}_{node_id}"

            if node_type == "source":
                src_tbl = cfg.get("dataset_name", "source_table")
                cte_definitions.append(f"{cte_name} AS (\n  SELECT * FROM {src_tbl}\n)")
            elif node_type == "clean_names":
                prev_cte = f"step_{idx-1}_{sorted_nodes[idx-1].id}"
                cte_definitions.append(f"{cte_name} AS (\n  SELECT * FROM {prev_cte}\n)")
            elif node_type == "filter":
                prev_cte = f"step_{idx-1}_{sorted_nodes[idx-1].id}"
                rules = cfg.get("rules", [])
                filters = [f'"{r["col"]}" {r.get("op", "=")} {r.get("val", 0)}' for r in rules]
                where_clause = " AND ".join(filters) if filters else "1=1"
                cte_definitions.append(f"{cte_name} AS (\n  SELECT * FROM {prev_cte}\n  WHERE {where_clause}\n)")
            elif node_type == "compute":
                prev_cte = f"step_{idx-1}_{sorted_nodes[idx-1].id}"
                cte_definitions.append(
                    f"{cte_name} AS (\n  SELECT *, ({cfg['sql_expression']}) AS \"{cfg['derived_column']}\" FROM {prev_cte}\n)"
                )
            elif node_type == "aggregate":
                prev_cte = f"step_{idx-1}_{sorted_nodes[idx-1].id}"
                group_cols = [f'"{c}"' for c in cfg.get("group_by", [])]
                cte_definitions.append(
                    f"{cte_name} AS (\n  SELECT {', '.join(group_cols)}, COUNT(*) AS row_count FROM {prev_cte} GROUP BY {', '.join(group_cols)}\n)"
                )
            else:
                prev_cte = f"step_{idx-1}_{sorted_nodes[idx-1].id}" if idx > 0 else "source_table"
                cte_definitions.append(f"{cte_name} AS (\n  SELECT * FROM {prev_cte}\n)")

        lines.append("WITH " + ",\n".join(cte_definitions))
        last_cte = f"step_{len(sorted_nodes)-1}_{sorted_nodes[-1].id}"
        lines.append(f"\nSELECT * FROM {last_cte};")

        return "\n".join(lines)
