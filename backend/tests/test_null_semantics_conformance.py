"""
tests/test_null_semantics_conformance.py
────────────────────────────────────────
Conformance suite verifying relational Three-Valued Logic (3VL) NULL semantics.

Requirements from A+ Implementation Plan (P4-4):
  • Three-valued logic: comparisons with NULL evaluate to UNKNOWN, not FALSE or TRUE.
  • In relational algebra:
      - `col = 'A'` excludes NULLs.
      - `col != 'A'` ALSO excludes NULLs (unlike Python `None != 'A'` which is True!).
      - `WHERE NOT (col = 'A')` excludes NULLs.
      - `WHERE col IS NULL` explicitly matches NULLs.
  • Inner Joins: NULL keys never match each other (NULL != NULL).
  • Aggregates:
      - `COUNT(*)` counts all rows including NULLs.
      - `COUNT(col)` excludes NULLs.
      - `AVG(col)`, `SUM(col)` ignore NULLs without coercion to zero.
  • Nullable preservation at the boundary: NULLs remain pd.NA or None, never synthetic zeroes.
"""

import duckdb
import numpy as np
import pandas as pd
import pytest

from dataforge.procedure_engine import StoredProcedureExecutor
from dataforge.procedure_schema import (
    ProcedureDefinition,
    ProcedureNode,
    ProcedureParameter,
)


def _conformance_df() -> pd.DataFrame:
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "category": ["A", "B", None, "A", None],
        "score": [10.0, None, 30.0, None, 50.0],
    })


def test_three_valued_logic_filter_conformance():
    """
    Verify that DuckDB execution adheres to standard Codd relational 3VL:
    Both `col = 'A'` and `col != 'A'` must drop NULLs.
    """
    df = _conformance_df()

    # Procedure with filter: category = 'A'
    proc_eq = ProcedureDefinition(
        procedure_id="sp_null_eq",
        version="1.0.0",
        name="NULL Eq Test",
        nodes=[
            ProcedureNode(id="src", type="source", inputs=[]),
            ProcedureNode(
                id="f_eq",
                type="filter",
                inputs=["src"],
                config={"rules": [{"col": "category", "op": "=", "val": "A"}]},
            ),
        ],
    )
    res_eq = StoredProcedureExecutor(proc_eq).execute(input_dfs={"default": df}, dry_run=True)
    df_eq = res_eq["df_result"]
    # Rows with category == 'A': id 1 and 4 -> exactly 2 rows
    assert len(df_eq) == 2
    assert list(df_eq["id"]) == [1, 4]

    # Procedure with filter: category != 'A'
    # In naive Python: row 2 ('B'), row 3 (None), row 5 (None) -> 3 rows!
    # In relational 3VL: NULL != 'A' evaluates to UNKNOWN, so row 3 and 5 are EXCLUDED!
    # Only row 2 ('B') must be retained!
    proc_neq = ProcedureDefinition(
        procedure_id="sp_null_neq",
        version="1.0.0",
        name="NULL Neq Test",
        nodes=[
            ProcedureNode(id="src", type="source", inputs=[]),
            ProcedureNode(
                id="f_neq",
                type="filter",
                inputs=["src"],
                config={"rules": [{"col": "category", "op": "!=", "val": "A"}]},
            ),
        ],
    )
    res_neq = StoredProcedureExecutor(proc_neq).execute(input_dfs={"default": df}, dry_run=True)
    df_neq = res_neq["df_result"]
    assert len(df_neq) == 1, f"Expected exactly 1 row under 3VL, got {len(df_neq)}"
    assert list(df_neq["id"]) == [2]

    # Explicit IS NULL filter
    proc_is_null = ProcedureDefinition(
        procedure_id="sp_null_is",
        version="1.0.0",
        name="NULL IS NULL Test",
        nodes=[
            ProcedureNode(id="src", type="source", inputs=[]),
            ProcedureNode(
                id="f_null",
                type="filter",
                inputs=["src"],
                config={"rules": [{"col": "category", "op": "IS NULL"}]},
            ),
        ],
    )
    res_null = StoredProcedureExecutor(proc_is_null).execute(input_dfs={"default": df}, dry_run=True)
    df_null = res_null["df_result"]
    assert len(df_null) == 2
    assert list(df_null["id"]) == [3, 5]


def test_inner_join_null_key_isolation():
    """Verify that NULL join keys do NOT match each other."""
    df_left = pd.DataFrame({
        "left_id": [1, 2, 3],
        "key": ["K1", None, "K2"],
        "val_left": [10, 20, 30],
    })
    df_right = pd.DataFrame({
        "right_id": [101, 102, 103],
        "key": ["K1", None, "K3"],
        "val_right": [100, 200, 300],
    })

    con = duckdb.connect(database=":memory:")
    con.register("t_left", df_left)
    con.register("t_right", df_right)

    res = con.execute("SELECT * FROM t_left l INNER JOIN t_right r ON l.key = r.key").df()
    # Only "K1" should match. The None/NULL keys must NEVER match.
    assert len(res) == 1
    assert res["key"].iloc[0] == "K1"


def test_aggregate_null_handling():
    """Verify that COUNT(col) excludes NULLs and AVG ignores NULLs without skew."""
    df = _conformance_df()  # score has: [10.0, None, 30.0, None, 50.0]

    con = duckdb.connect(database=":memory:")
    con.register("t_data", df)

    res = con.execute(
        """
        SELECT
            COUNT(*) as total_rows,
            COUNT(score) as score_non_null,
            SUM(score) as total_score,
            AVG(score) as avg_score
        FROM t_data
        """
    ).fetchone()

    total_rows, score_non_null, total_score, avg_score = res
    assert total_rows == 5
    assert score_non_null == 3
    assert total_score == 90.0  # 10 + 30 + 50
    assert avg_score == 30.0    # 90 / 3 = 30.0 (NOT 90 / 5 = 18.0)
