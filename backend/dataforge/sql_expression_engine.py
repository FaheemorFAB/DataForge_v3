"""
dataforge/sql_expression_engine.py
───────────────────────────────────
Hardened, SQL-native expression evaluation engine.
Replaces insecure Python eval() with validated DuckDB SQL AST projection.
Enforces:
1. Strict scalar AST allowlisting via sqlglot.
2. Complete prohibition of subqueries, filesystem calls, network I/O, and table functions.
3. Hardened in-memory DuckDB connection with enable_external_access=false and lock_configuration=true.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Set
import duckdb
import numpy as np
import pandas as pd
import sqlglot
from sqlglot import exp

log = logging.getLogger(__name__)

# ── Permitted scalar functions ────────────────────────────────────────────────
ALLOWED_FUNCTIONS: Set[str] = {
    # Math & Numeric
    "abs", "round", "floor", "ceil", "sign", "sqrt", "cbrt",
    "exp", "ln", "log", "log2", "log10", "power", "pow", "mod", "pi",
    # Trigonometry
    "sin", "cos", "tan", "asin", "acos", "atan",
    # Conditional & Null handling
    "coalesce", "nullif", "greatest", "least", "ifnull",
    # String manipulation
    "lower", "upper", "trim", "ltrim", "rtrim", "length", "len",
    "concat", "substr", "substring", "replace",
    # Type conversion
    "cast", "try_cast",
    # Aggregates / Scalar bounds
    "min", "max",
}

# ── Permitted AST node types ──────────────────────────────────────────────────
ALLOWED_NODE_TYPES = (
    # Arithmetic & Logic operators
    exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod, exp.Pow,
    exp.Neg, exp.Not, exp.Paren,
    # Comparison operators
    exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Between,
    # Conditionals
    exp.Case, exp.If, exp.When,
    # Literals & Values
    exp.Literal, exp.Null, exp.Boolean,
    # Identifiers
    exp.Column, exp.Identifier,
    # Functions
    exp.Func, exp.Anonymous, exp.Cast, exp.TryCast,
)

DISALLOWED_NODE_TYPES = (
    exp.Select, exp.Subquery, exp.Command, exp.Copy, exp.Attach, exp.Detach,
    exp.Pragma, exp.Block, exp.Table, exp.Dot, exp.Star,
    exp.Drop, exp.Create, exp.Alter, exp.Insert, exp.Update, exp.Delete,
)


def _get_hardened_connection() -> duckdb.DuckDBPyConnection:
    """Creates a memory-bounded DuckDB connection locked against external I/O."""
    return duckdb.connect(
        database=":memory:",
        config={
            "enable_external_access": False,
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
            "max_memory": "256MB",
            "threads": 1,
            "lock_configuration": True,
        },
    )


def validate_and_compile_formula(
    formula: str,
    valid_columns: list[str],
) -> tuple[str, dict[str, str]]:
    """
    Validates a user-supplied formula string and compiles it to hardened DuckDB SQL.
    Returns: (compiled_sql: str, column_mapping: dict)
    Raises: ValueError if the formula contains syntax errors, disallowed constructs, or unknown columns.
    """
    clean_formula = formula.strip()
    if not clean_formula:
        raise ValueError("Formula expression cannot be empty")

    try:
        parsed = sqlglot.parse_one(clean_formula, read="duckdb")
    except Exception as e:
        raise ValueError(f"Formula syntax error ({clean_formula!r}): {e}") from e

    # Reject top-level statements that are not expressions
    if isinstance(parsed, DISALLOWED_NODE_TYPES):
        raise ValueError(f"Disallowed expression type ({type(parsed).__name__}): {clean_formula!r}")

    # Build case-insensitive and snake_case column lookup table
    col_lookup: dict[str, str] = {}
    for col in valid_columns:
        col_lookup[col.lower()] = col
        snake = re.sub(r"[^\w\s]", "_", col).strip()
        snake = re.sub(r"[\s\-]+", "_", snake).strip("_").lower()
        col_lookup[snake] = col

    used_column_mappings: dict[str, str] = {}

    # Inspect all AST nodes
    for node in parsed.walk():
        if isinstance(node, DISALLOWED_NODE_TYPES):
            raise ValueError(f"Forbidden syntax construct ({type(node).__name__}): {clean_formula!r}")

        if not isinstance(node, ALLOWED_NODE_TYPES):
            raise ValueError(f"Disallowed syntax node ({type(node).__name__}): {clean_formula!r}")

        # Validate function names
        if isinstance(node, (exp.Func, exp.Anonymous)):
            func_name = ""
            if isinstance(node, exp.Anonymous):
                func_name = str(node.this).lower()
            elif hasattr(node, "sql_name"):
                func_name = node.sql_name().lower()
            elif hasattr(node, "key"):
                func_name = str(node.key).lower()
            else:
                func_name = str(node.name).lower()

            # Special case for generic binary operators parsed as functions
            if func_name not in ALLOWED_FUNCTIONS:
                raise ValueError(f"Forbidden or untrusted function call ({func_name!r})")

        # Validate and rewrite column references
        if isinstance(node, exp.Column):
            raw_col_name = node.name
            normalized = raw_col_name.lower()
            if normalized not in col_lookup:
                raise ValueError(
                    f"Column '{raw_col_name}' in formula does not exist in dataset. "
                    f"Available columns: {list(valid_columns)[:8]}"
                )
            actual_col = col_lookup[normalized]
            used_column_mappings[actual_col] = actual_col
            # Rewrite node identifier to quoted actual column name
            node.set("this", exp.to_identifier(actual_col, quoted=True))

    compiled_sql = parsed.sql(dialect="duckdb")
    return compiled_sql, used_column_mappings


def evaluate_formula(formula: str, df: pd.DataFrame) -> pd.Series:
    """
    Evaluates a derived formula on a DataFrame using hardened DuckDB SQL pushdown.
    Guarantees no arbitrary Python code execution, no filesystem access, and no network I/O.
    """
    if len(df) == 0:
        return pd.Series([], dtype=float, index=df.index)

    compiled_sql, _ = validate_and_compile_formula(formula, list(df.columns))

    con = _get_hardened_connection()
    try:
        # Register in-memory dataframe
        con.register("__source_table__", df)
        query = f'SELECT ({compiled_sql}) AS "__eval_result__" FROM __source_table__'
        res_df = con.execute(query).df()
        series_out = res_df["__eval_result__"]
        series_out.index = df.index
        return series_out
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Evaluation error for formula ({formula!r}): {e}") from e
    finally:
        con.close()
