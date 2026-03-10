"""
DataForge — Transform Engine
════════════════════════════
Stateless transformation pipeline for DataFrames.
All operations return a NEW DataFrame — originals are never mutated.

Supported operations (in order):
  1. filter    — row-level filtering by column/operator/value rules
  2. groupby   — group by columns + aggregate metrics
  3. create    — formula-based derived columns (safe eval)
  4. sort      — sort rows by one or more columns

Usage::

    from modules.transform_engine import TransformEngine

    engine = TransformEngine()
    result = engine.apply(df, steps=[
        {"op": "filter",  "rules": [{"col": "region", "op": "==", "val": "West"}]},
        {"op": "groupby", "group": ["region", "product"],
                          "agg":   {"revenue": "sum", "units": "sum"}},
        {"op": "create",  "name": "avg_price", "formula": "revenue / units"},
        {"op": "sort",    "by": "revenue", "ascending": False},
    ])
    # result.df  → transformed DataFrame
    # result.summary → human-readable description of what was done
"""

from __future__ import annotations
import re
import math
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Any

# ── Safe expression evaluation whitelist ─────────────────────────────────────
_SAFE_NAMES: dict[str, Any] = {
    # math
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "len": len, "int": int, "float": float, "str": str,
    # numpy shortcuts
    "log": np.log, "log2": np.log2, "log10": np.log10,
    "sqrt": np.sqrt, "exp": np.exp, "nan": float("nan"),
    # pandas date helpers
    "pd": pd, "np": np,
}

_FORBIDDEN_RE = re.compile(
    r"\b(import|exec|eval|open|os|sys|subprocess|__|\bcompile\b|breakpoint)\b",
    re.IGNORECASE,
)


def _safe_eval(formula: str, df: pd.DataFrame) -> pd.Series:
    """
    Evaluate a column formula in the context of the DataFrame columns.
    Raises ValueError for unsafe expressions.
    """
    if _FORBIDDEN_RE.search(formula):
        raise ValueError(f"Unsafe expression: {formula!r}")
    local_env = dict(_SAFE_NAMES)
    for col in df.columns:
        safe_key = re.sub(r"[^a-zA-Z0-9_]", "_", col)
        local_env[safe_key] = df[col]
        local_env[col]      = df[col]   # also allow original name
    try:
        result = eval(formula, {"__builtins__": {}}, local_env)  # noqa: S307
    except Exception as e:
        raise ValueError(f"Formula error ({formula!r}): {e}") from e
    if not isinstance(result, pd.Series):
        result = pd.Series([result] * len(df), index=df.index)
    return result


# ── Operator map ──────────────────────────────────────────────────────────────
_OPS = {
    "==":         lambda s, v: s == v,
    "!=":         lambda s, v: s != v,
    ">":          lambda s, v: s >  _coerce(s, v),
    ">=":         lambda s, v: s >= _coerce(s, v),
    "<":          lambda s, v: s <  _coerce(s, v),
    "<=":         lambda s, v: s <= _coerce(s, v),
    "contains":   lambda s, v: s.astype(str).str.contains(str(v), case=False, na=False),
    "not_contains": lambda s, v: ~s.astype(str).str.contains(str(v), case=False, na=False),
    "startswith": lambda s, v: s.astype(str).str.startswith(str(v), na=False),
    "endswith":   lambda s, v: s.astype(str).str.endswith(str(v), na=False),
    "in":         lambda s, v: s.isin(v if isinstance(v, list) else str(v).split(",")),
    "not_in":     lambda s, v: ~s.isin(v if isinstance(v, list) else str(v).split(",")),
    "is_null":    lambda s, _: s.isnull(),
    "not_null":   lambda s, _: s.notnull(),
}

_AGG_FUNCS = {
    "sum":    "sum",
    "mean":   "mean",
    "avg":    "mean",
    "count":  "count",
    "min":    "min",
    "max":    "max",
    "median": "median",
    "std":    "std",
    "var":    "var",
    "nunique":"nunique",
    "first":  "first",
    "last":   "last",
}


def _coerce(series: pd.Series, value: Any) -> Any:
    """Try to cast value to match the series dtype."""
    try:
        if pd.api.types.is_numeric_dtype(series):
            return float(value)
    except (ValueError, TypeError):
        pass
    return value


# ── Result object ─────────────────────────────────────────────────────────────
@dataclass
class TransformResult:
    df:      pd.DataFrame
    steps:   list[dict] = field(default_factory=list)
    errors:  list[str]  = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = []
        for s in self.steps:
            op = s.get("op", "?")
            if op == "filter":
                n = s.get("rows_removed", 0)
                parts.append(f"Filtered — {n:,} rows removed")
            elif op == "groupby":
                parts.append(f"Grouped by {s.get('group')} → {s.get('out_rows'):,} groups")
            elif op == "create":
                parts.append(f"Created column '{s.get('name')}'")
            elif op == "sort":
                parts.append(f"Sorted by {s.get('by')} ({'asc' if s.get('ascending') else 'desc'})")
            elif op == "rename":
                parts.append(f"Renamed {len(s.get('map', {}))} column(s)")
            elif op == "drop_cols":
                parts.append(f"Dropped {len(s.get('cols', []))} column(s)")
        return " → ".join(parts) if parts else "No transformations applied"

    def to_dict(self) -> dict:
        return {
            "rows":    len(self.df),
            "cols":    len(self.df.columns),
            "columns": self.df.columns.tolist(),
            "steps":   self.steps,
            "errors":  self.errors,
            "summary": self.summary,
        }


# ── Engine ────────────────────────────────────────────────────────────────────
class TransformEngine:

    def apply(self, df: pd.DataFrame, steps: list[dict]) -> TransformResult:
        """Apply a list of transformation steps in order."""
        result = TransformResult(df=df.copy())
        for step in steps:
            op = (step.get("op") or "").lower()
            try:
                if op == "filter":
                    result = self._filter(result, step)
                elif op == "groupby":
                    result = self._groupby(result, step)
                elif op == "create":
                    result = self._create(result, step)
                elif op == "sort":
                    result = self._sort(result, step)
                elif op == "rename":
                    result = self._rename(result, step)
                elif op == "drop_cols":
                    result = self._drop_cols(result, step)
                else:
                    result.errors.append(f"Unknown op: {op!r}")
            except Exception as e:
                result.errors.append(f"{op}: {e}")
        return result

    # ── Individual ops ────────────────────────────────────────────────────────

    def _filter(self, result: TransformResult, step: dict) -> TransformResult:
        df   = result.df
        orig = len(df)
        mask = pd.Series([True] * len(df), index=df.index)
        for rule in step.get("rules", []):
            col = rule.get("col")
            op  = rule.get("op", "==")
            val = rule.get("val")
            if col not in df.columns:
                result.errors.append(f"Filter: column {col!r} not found")
                continue
            fn = _OPS.get(op)
            if fn is None:
                result.errors.append(f"Filter: unknown operator {op!r}")
                continue
            row_mask = fn(df[col], val)
            logic    = rule.get("logic", "AND").upper()
            mask     = (mask & row_mask) if logic == "AND" else (mask | row_mask)
        filtered = df[mask].reset_index(drop=True)
        result.df = filtered
        result.steps.append({"op": "filter", "rows_removed": orig - len(filtered)})
        return result

    def _groupby(self, result: TransformResult, step: dict) -> TransformResult:
        df      = result.df
        group   = step.get("group", [])
        agg_raw = step.get("agg", {})
        if not group:
            result.errors.append("groupby: 'group' list is required")
            return result
        missing = [c for c in group if c not in df.columns]
        if missing:
            result.errors.append(f"groupby: columns not found: {missing}")
            return result
        # Build pandas agg spec
        agg_spec = {}
        for col, func in agg_raw.items():
            if col in df.columns:
                agg_spec[col] = _AGG_FUNCS.get(str(func).lower(), func)
        if not agg_spec:
            # Auto-aggregate all numerics with sum
            for c in df.select_dtypes(include="number").columns:
                if c not in group:
                    agg_spec[c] = "sum"
        grouped = df.groupby(group, as_index=True).agg(agg_spec)
        grouped.columns = [c if not isinstance(c, tuple) else "_".join(c) for c in grouped.columns]
        grouped = grouped.reset_index()
        result.df = grouped
        result.steps.append({"op": "groupby", "group": group, "out_rows": len(grouped)})
        return result

    def _create(self, result: TransformResult, step: dict) -> TransformResult:
        df      = result.df
        name    = step.get("name", "new_col")
        formula = step.get("formula", "")
        if not formula:
            result.errors.append("create: 'formula' is required")
            return result
        series = _safe_eval(formula, df)
        df     = df.copy()
        df[name] = series
        result.df = df
        result.steps.append({"op": "create", "name": name})
        return result

    def _sort(self, result: TransformResult, step: dict) -> TransformResult:
        df  = result.df
        by  = step.get("by")
        asc = bool(step.get("ascending", False))
        if not by:
            result.errors.append("sort: 'by' is required")
            return result
        cols = [by] if isinstance(by, str) else list(by)
        valid = [c for c in cols if c in df.columns]
        if not valid:
            result.errors.append(f"sort: columns not found: {cols}")
            return result
        result.df = df.sort_values(valid, ascending=asc).reset_index(drop=True)
        result.steps.append({"op": "sort", "by": valid, "ascending": asc})
        return result

    def _rename(self, result: TransformResult, step: dict) -> TransformResult:
        mapping = step.get("map", {})
        result.df = result.df.rename(columns=mapping)
        result.steps.append({"op": "rename", "map": mapping})
        return result

    def _drop_cols(self, result: TransformResult, step: dict) -> TransformResult:
        cols   = step.get("cols", [])
        exists = [c for c in cols if c in result.df.columns]
        result.df = result.df.drop(columns=exists)
        result.steps.append({"op": "drop_cols", "cols": exists})
        return result


# ── Module-level convenience ──────────────────────────────────────────────────
_engine = TransformEngine()

def apply_transforms(df: pd.DataFrame, steps: list[dict]) -> TransformResult:
    return _engine.apply(df, steps)
