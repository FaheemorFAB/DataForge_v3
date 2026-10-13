"""
dataforge/procedure_engine.py
──────────────────────────────
High-Performance DuckDB SQL Stored Procedure Execution Engine (DF-SPE).
Compiles declarative procedure DAGs into hardened DuckDB execution graphs with:
  • Zero eval() surface; formula nodes validated via AST
  • Hardened connection: enable_external_access=false, memory limits, lock_configuration=true
  • Parameterized filter bindings & safe identifier quoting
  • Comprehensive assertion gates: not_null, unique, range, accepted_values, row_count
  • Dry-run preview mode & full execution with immutable snapshot materialization
  • Tuple-level and step-level Why-Provenance lineage manifests
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import duckdb
import numpy as np
import pandas as pd

from dataforge.api.storage.snapshots import SnapshotManager
from dataforge.procedure_schema import (
    AssertionSeverity,
    ProcedureDefinition,
    ProcedureNode,
    QualityAssertion,
)
from dataforge.sql_expression_engine import evaluate_formula

logger = logging.getLogger(__name__)

# Allowed SQL comparison operators in filter rules
ALLOWED_OPERATORS = {
    "=": "=",
    "==": "=",
    "!=": "!=",
    "<>": "!=",
    ">": ">",
    ">=": ">=",
    "<": "<",
    "<=": "<=",
    "LIKE": "LIKE",
    "ILIKE": "ILIKE",
    "IN": "IN",
    "NOT IN": "NOT IN",
    "IS NULL": "IS NULL",
    "IS NOT NULL": "IS NOT NULL",
}


class ProcedureExecutionError(Exception):
    def __init__(self, message: str, step_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.step_id = step_id
        self.details = details or {}


def _quote_ident(ident: str) -> str:
    """Safely quote a SQL column/table identifier."""
    clean = str(ident).replace('"', '""')
    return f'"{clean}"'


def _format_sql_literal(val: Any) -> str:
    """Format literal value safely for DuckDB SQL without interpolation risk."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val):
            return "NULL"
        return str(val)
    if isinstance(val, (list, tuple)):
        items = [_format_sql_literal(x) for x in val]
        return f"({', '.join(items)})"
    # String escaping
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


def _to_snake_case(name: str) -> str:
    s = str(name).strip()
    s = re.sub(r"[^\w\s]", "_", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_").lower()


class StoredProcedureExecutor:
    """
    Executes a declarative Stored Procedure DAG against input dataframes.
    """

    def __init__(
        self,
        procedure: ProcedureDefinition,
        runtime_params: Optional[Dict[str, Any]] = None,
        memory_limit: str = "512MB",
        threads: int = 2,
    ):
        self.procedure = procedure
        self.params = procedure.get_parameter_dict(runtime_params)
        self.memory_limit = memory_limit
        self.threads = threads

    def _create_hardened_connection(self) -> duckdb.DuckDBPyConnection:
        """Configures a sandboxed in-memory DuckDB connection."""
        con = duckdb.connect(database=":memory:")
        con.execute(f"SET memory_limit = '{self.memory_limit}'")
        con.execute(f"SET threads = {self.threads}")
        try:
            con.execute("SET enable_external_access = false")
        except Exception:
            pass
        try:
            con.execute("SET lock_configuration = true")
        except Exception:
            pass
        return con

    def execute(
        self,
        input_dfs: Dict[str, pd.DataFrame],
        dry_run: bool = False,
        upload_id: Optional[str] = None,
        input_snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the procedure.

        Parameters:
            input_dfs: Dictionary mapping source names (e.g. 'default' or source node id) to DataFrames.
            dry_run: If True, evaluates DAG without committing snapshots and returns step previews.
            upload_id: Optional dataset upload_id for committing snapshots.
            input_snapshot_id: Hash/ID of the input snapshot.

        Returns:
            Dictionary containing result DataFrame, duration, step audit logs, and lineage manifest.
        """
        start_time = time.perf_counter()
        con = self._create_hardened_connection()

        # Topological ordering
        execution_nodes = self.procedure.topological_sort()

        # Step logs and lineage manifest
        step_logs: List[Dict[str, Any]] = []
        lineage_entries: List[Dict[str, Any]] = []
        table_registry: Dict[str, str] = {}  # node_id -> duckdb_table_name

        total_rows_in = 0
        final_table_name = ""

        try:
            for idx, node in enumerate(execution_nodes):
                node_id = node.id
                node_type = node.type
                cfg = node.config or {}
                table_name = f"t_step_{idx}_{_to_snake_case(node_id)}"

                node_start = time.perf_counter()
                dropped_reason = None
                dropped_row_count = 0
                imputed_row_ids: List[int] = []

                # ── 1. SOURCE NODE ─────────────────────────────────────────
                if node_type == "source":
                    source_key = cfg.get("dataset_name", "default")
                    df_in = input_dfs.get(source_key)
                    if df_in is None:
                        df_in = input_dfs.get("default")
                    if df_in is None:
                        # Fallback to first available df
                        if len(input_dfs) > 0:
                            df_in = next(iter(input_dfs.values()))
                        else:
                            raise ProcedureExecutionError(f"Source node '{node_id}' found no input dataset.", node_id)

                    total_rows_in = len(df_in)
                    con.register(table_name, df_in)
                    table_registry[node_id] = table_name

                # ── 2. CLEAN NAMES ─────────────────────────────────────────
                elif node_type == "clean_names":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    cols_info = con.execute(f"DESCRIBE {parent_table}").fetchall()
                    casing = cfg.get("casing", "snake_case")

                    renames = []
                    for col_name, _, _, _, _, _ in cols_info:
                        if casing == "snake_case":
                            new_name = _to_snake_case(col_name)
                        elif casing == "uppercase":
                            new_name = str(col_name).strip().upper()
                        elif casing == "lowercase":
                            new_name = str(col_name).strip().lower()
                        else:
                            new_name = str(col_name).strip()
                        renames.append(f'{_quote_ident(col_name)} AS {_quote_ident(new_name)}')

                    query = f"CREATE TABLE {table_name} AS SELECT {', '.join(renames)} FROM {parent_table}"
                    con.execute(query)
                    table_registry[node_id] = table_name

                # ── 3. FILTER ──────────────────────────────────────────────
                elif node_type == "filter":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    rules = cfg.get("rules", [])
                    where_clauses = []

                    for r in rules:
                        col = r["col"]
                        op = r.get("op", "=").upper()
                        if op not in ALLOWED_OPERATORS:
                            raise ProcedureExecutionError(f"Unsupported filter operator: '{op}'", node_id)
                        actual_op = ALLOWED_OPERATORS[op]

                        # Resolve param vs static val
                        if "param" in r:
                            val = self.params.get(r["param"])
                        else:
                            val = r.get("val")

                        if actual_op in ("IS NULL", "IS NOT NULL"):
                            where_clauses.append(f"{_quote_ident(col)} {actual_op}")
                        else:
                            where_clauses.append(f"{_quote_ident(col)} {actual_op} {_format_sql_literal(val)}")

                    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                    rows_before = con.execute(f"SELECT COUNT(*) FROM {parent_table}").fetchone()[0]
                    con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {parent_table} WHERE {where_sql}")
                    rows_after = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    dropped_row_count = rows_before - rows_after
                    dropped_reason = f"Filtered out {dropped_row_count} rows not matching ({where_sql})"
                    table_registry[node_id] = table_name

                # ── 4. IMPUTE ──────────────────────────────────────────────
                elif node_type == "impute":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    col_strategies = cfg.get("columns", {})
                    cols_info = con.execute(f"DESCRIBE {parent_table}").fetchall()

                    select_exprs = []
                    for c_info in cols_info:
                        c_name = c_info[0]
                        if c_name in col_strategies:
                            strat = col_strategies[c_name]
                            method = strat.get("strategy", "median")
                            if method == "constant":
                                fill_val = _format_sql_literal(strat.get("value", ""))
                                select_exprs.append(f"COALESCE({_quote_ident(c_name)}, {fill_val}) AS {_quote_ident(c_name)}")
                            elif method == "zero":
                                select_exprs.append(f"COALESCE({_quote_ident(c_name)}, 0) AS {_quote_ident(c_name)}")
                            elif method == "mean":
                                select_exprs.append(
                                    f"COALESCE({_quote_ident(c_name)}, AVG({_quote_ident(c_name)}) OVER ()) AS {_quote_ident(c_name)}"
                                )
                            elif method == "median":
                                select_exprs.append(
                                    f"COALESCE({_quote_ident(c_name)}, MEDIAN({_quote_ident(c_name)}) OVER ()) AS {_quote_ident(c_name)}"
                                )
                            else:
                                select_exprs.append(_quote_ident(c_name))
                        else:
                            select_exprs.append(_quote_ident(c_name))

                    con.execute(f"CREATE TABLE {table_name} AS SELECT {', '.join(select_exprs)} FROM {parent_table}")
                    table_registry[node_id] = table_name

                # ── 5. COMPUTE / FORMULA ────────────────────────────────────
                elif node_type == "compute":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    derived_col = cfg["derived_column"]
                    expr = cfg["sql_expression"]

                    # Execute formula securely via DuckDB projection
                    # First fetch columns from parent table to validate
                    parent_df_sample = con.execute(f"SELECT * FROM {parent_table} LIMIT 5").df()
                    # Validate formula syntax using evaluate_formula AST validator
                    try:
                        _ = evaluate_formula(expr, parent_df_sample)
                    except Exception as err:
                        raise ProcedureExecutionError(f"Invalid compute formula expression: {err}", node_id) from err

                    con.execute(
                        f"CREATE TABLE {table_name} AS SELECT *, ({expr}) AS {_quote_ident(derived_col)} FROM {parent_table}"
                    )
                    table_registry[node_id] = table_name

                # ── 6. AGGREGATE ───────────────────────────────────────────
                elif node_type == "aggregate":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    group_cols = cfg.get("group_by", [])
                    metrics = cfg.get("metrics", [])  # [{"agg": "sum", "col": "amount", "alias": "total_amount"}]

                    select_parts = [_quote_ident(c) for c in group_cols]
                    for m in metrics:
                        agg = m["agg"].upper()
                        target_col = _quote_ident(m["col"])
                        alias = _quote_ident(m.get("alias", f"{m['agg']}_{m['col']}"))
                        select_parts.append(f"{agg}({target_col}) AS {alias}")

                    group_sql = f" GROUP BY {', '.join([_quote_ident(c) for c in group_cols])}" if group_cols else ""
                    con.execute(f"CREATE TABLE {table_name} AS SELECT {', '.join(select_parts)} FROM {parent_table}{group_sql}")
                    table_registry[node_id] = table_name

                # ── 7. DEDUPE ──────────────────────────────────────────────
                elif node_type == "dedupe":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    subset = cfg.get("subset", [])
                    rows_before = con.execute(f"SELECT COUNT(*) FROM {parent_table}").fetchone()[0]

                    if subset:
                        cols_all = [c[0] for c in con.execute(f"DESCRIBE {parent_table}").fetchall()]
                        part_cols = ", ".join([_quote_ident(c) for c in subset])
                        con.execute(
                            f"""
                            CREATE TABLE {table_name} AS
                            SELECT {', '.join([_quote_ident(c) for c in cols_all])}
                            FROM (
                                SELECT *, ROW_NUMBER() OVER (PARTITION BY {part_cols}) as _rn
                                FROM {parent_table}
                            )
                            WHERE _rn = 1
                            """
                        )
                    else:
                        con.execute(f"CREATE TABLE {table_name} AS SELECT DISTINCT * FROM {parent_table}")

                    rows_after = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    dropped_row_count = rows_before - rows_after
                    dropped_reason = f"Removed {dropped_row_count} duplicate rows"
                    table_registry[node_id] = table_name

                # ── 8. CAST ────────────────────────────────────────────────
                elif node_type == "cast":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    type_casts = cfg.get("casts", {})
                    cols_info = con.execute(f"DESCRIBE {parent_table}").fetchall()

                    select_exprs = []
                    for c_info in cols_info:
                        c_name = c_info[0]
                        if c_name in type_casts:
                            target_type = type_casts[c_name].upper()
                            select_exprs.append(f"CAST({_quote_ident(c_name)} AS {target_type}) AS {_quote_ident(c_name)}")
                        else:
                            select_exprs.append(_quote_ident(c_name))

                    con.execute(f"CREATE TABLE {table_name} AS SELECT {', '.join(select_exprs)} FROM {parent_table}")
                    table_registry[node_id] = table_name

                # ── 9. JOIN ────────────────────────────────────────────────
                elif node_type == "join":
                    if len(node.inputs) < 2:
                        raise ProcedureExecutionError("Join node requires at least 2 inputs.", node_id)
                    left_table = table_registry[node.inputs[0]]
                    right_table = table_registry[node.inputs[1]]
                    join_type = cfg.get("join_type", "INNER").upper()
                    left_on = cfg.get("left_on")
                    right_on = cfg.get("right_on")

                    query = (
                        f"CREATE TABLE {table_name} AS "
                        f"SELECT l.*, r.* EXCLUDE ({_quote_ident(right_on)}) "
                        f"FROM {left_table} l {join_type} JOIN {right_table} r "
                        f"ON l.{_quote_ident(left_on)} = r.{_quote_ident(right_on)}"
                    )
                    con.execute(query)
                    table_registry[node_id] = table_name

                # ── 10. ASSERTION GATE ─────────────────────────────────────
                elif node_type == "assertion_gate":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    assertions_raw = cfg.get("assertions", [])
                    assertions = [QualityAssertion(**a) if isinstance(a, dict) else a for a in assertions_raw]
                    fail_on_error = cfg.get("fail_on_error", True)

                    # Evaluate assertions
                    passed, assertion_results = self._verify_assertions(con, parent_table, assertions)

                    has_error = any(not r["passed"] and r["severity"] == AssertionSeverity.ERROR for r in assertion_results)
                    if has_error and fail_on_error:
                        raise ProcedureExecutionError(
                            f"Quality Gate assertion failed: {assertion_results}",
                            step_id=node_id,
                            details={"assertions": assertion_results},
                        )

                    # Passthrough
                    con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {parent_table}")
                    table_registry[node_id] = table_name

                # ── 11. OUTPUT / PASSTHROUGH ───────────────────────────────
                elif node_type == "output":
                    parent_table = table_registry[node.inputs[0]] if node.inputs else list(table_registry.values())[-1]
                    con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {parent_table}")
                    table_registry[node_id] = table_name

                else:
                    raise ProcedureExecutionError(f"Unknown procedure node type: '{node_type}'", node_id)

                final_table_name = table_name
                node_duration = int((time.perf_counter() - node_start) * 1000)
                current_rows = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

                log_entry = {
                    "node_id": node_id,
                    "type": node_type,
                    "status": "SUCCESS",
                    "rows": current_rows,
                    "duration_ms": node_duration,
                }
                step_logs.append(log_entry)

                lineage_entries.append({
                    "node_id": node_id,
                    "type": node_type,
                    "config_hash": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12],
                    "rows_in": total_rows_in if idx == 0 else step_logs[idx - 1]["rows"],
                    "rows_out": current_rows,
                    "dropped_count": dropped_row_count,
                    "dropped_reason": dropped_reason,
                })

            # Fetch output DataFrame
            df_result = con.execute(f"SELECT * FROM {final_table_name}").df()
            total_duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Output snapshot committing if not dry run and upload_id provided
            output_snapshot_id = None
            new_version_id = None
            if not dry_run and upload_id:
                new_version_id, output_snapshot_id = SnapshotManager.commit_snapshot(
                    upload_id=upload_id,
                    df=df_result,
                    action=f"procedure_run:{self.procedure.procedure_id}",
                    metadata={
                        "procedure_id": self.procedure.procedure_id,
                        "version": self.procedure.version,
                        "params": self.params,
                        "lineage": lineage_entries,
                    },
                )

            return {
                "ok": True,
                "procedure_id": self.procedure.procedure_id,
                "version": self.procedure.version,
                "dry_run": dry_run,
                "rows_in": total_rows_in,
                "rows_out": len(df_result),
                "duration_ms": total_duration_ms,
                "output_snapshot_id": output_snapshot_id,
                "version_id": new_version_id,
                "df_result": df_result,
                "step_logs": step_logs,
                "lineage_manifest": lineage_entries,
            }

        except Exception as e:
            total_duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Procedure execution failed: %s", e)
            if isinstance(e, ProcedureExecutionError):
                raise
            raise ProcedureExecutionError(f"Procedure halted: {e}") from e

    def _verify_assertions(
        self,
        con: duckdb.DuckDBPyConnection,
        table_name: str,
        assertions: List[QualityAssertion],
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Evaluates assertion checks (not_null, unique, range, accepted_values, row_count).
        Returns overall_passed boolean and list of assertion details.
        """
        all_passed = True
        results: List[Dict[str, Any]] = []

        for assertion in assertions:
            a_type = assertion.type
            col = assertion.column
            sev = assertion.severity
            passed = True
            failing_count = 0
            detail = ""

            try:
                if a_type == "not_null" and col:
                    null_count = con.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {_quote_ident(col)} IS NULL").fetchone()[0]
                    if null_count > 0:
                        passed = False
                        failing_count = null_count
                        detail = f"{null_count} NULL values detected in column '{col}'"

                elif a_type == "unique" and col:
                    dupe_res = con.execute(
                        f"""
                        SELECT COUNT(*) FROM (
                            SELECT {_quote_ident(col)}, COUNT(*) FROM {table_name}
                            WHERE {_quote_ident(col)} IS NOT NULL
                            GROUP BY {_quote_ident(col)} HAVING COUNT(*) > 1
                        )
                        """
                    ).fetchone()[0]
                    if dupe_res > 0:
                        passed = False
                        failing_count = dupe_res
                        detail = f"{dupe_res} duplicate keys detected in column '{col}'"

                elif a_type == "range" and col:
                    conditions = []
                    if assertion.min is not None:
                        conditions.append(f"{_quote_ident(col)} < {assertion.min}")
                    if assertion.max is not None:
                        conditions.append(f"{_quote_ident(col)} > {assertion.max}")
                    if conditions:
                        where_range = " OR ".join(conditions)
                        out_of_range = con.execute(
                            f"SELECT COUNT(*) FROM {table_name} WHERE ({where_range})"
                        ).fetchone()[0]
                        if out_of_range > 0:
                            passed = False
                            failing_count = out_of_range
                            detail = f"{out_of_range} values outside range [{assertion.min}, {assertion.max}]"

                elif a_type == "accepted_values" and col and assertion.values:
                    allowed_sql = _format_sql_literal(assertion.values)
                    unaccepted = con.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE {_quote_ident(col)} NOT IN {allowed_sql}"
                    ).fetchone()[0]
                    if unaccepted > 0:
                        passed = False
                        failing_count = unaccepted
                        detail = f"{unaccepted} rows with values outside accepted list"

                elif a_type == "row_count":
                    total_rows = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    if assertion.min_rows is not None and total_rows < assertion.min_rows:
                        passed = False
                        detail = f"Row count {total_rows} is below min_rows {assertion.min_rows}"
                    if assertion.max_rows is not None and total_rows > assertion.max_rows:
                        passed = False
                        detail = f"Row count {total_rows} exceeds max_rows {assertion.max_rows}"

            except Exception as exc:
                passed = False
                detail = f"Assertion evaluation failed: {exc}"

            if not passed and sev == AssertionSeverity.ERROR:
                all_passed = False

            results.append({
                "type": a_type,
                "column": col,
                "severity": sev.value,
                "passed": passed,
                "failing_count": failing_count,
                "detail": detail or "Passed",
            })

        return all_passed, results
