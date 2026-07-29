"""
dataforge/api/utils/helpers.py
────────────────────────────────
Shared utility functions used across services and routes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import math
import numpy as np
import pandas as pd


# ── Time formatting ───────────────────────────────────────────────────────────

def time_ago(dt_str: Optional[str]) -> str:
    """Convert an ISO datetime string to a human-readable 'X ago' string."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.utcnow()
        diff = now - dt
        s = int(diff.total_seconds())
        if s < 60:    return "just now"
        if s < 3600:  return f"{s // 60}m ago"
        if s < 86400: return f"{s // 3600}h ago"
        if s < 604800: return f"{s // 86400}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return ""


def format_member_since(val: Any) -> str:
    if not val:
        return "—"
    try:
        if hasattr(val, "strftime"):
            return val.strftime("%B %Y")
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.strftime("%B %Y")
    except Exception:
        return "—"


# ── DataFrame helpers ─────────────────────────────────────────────────────────

def resolve_column(col_name: Optional[str], df_columns: Any) -> Optional[str]:
    """Case-insensitive & whitespace-tolerant column name resolution."""
    if not col_name:
        return None
    s = str(col_name).strip()
    if not s:
        return None
    if s in df_columns:
        return s
    s_lower = s.lower()
    for real_col in df_columns:
        if str(real_col).strip().lower() == s_lower:
            return str(real_col)
    return None


def safe_json_value(v: Any) -> Any:
    if isinstance(v, np.integer):   return int(v)
    if isinstance(v, np.floating):  return None if np.isnan(v) else float(v)
    if isinstance(v, np.bool_):     return bool(v)
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return None
    if isinstance(v, pd.Timestamp): return v.isoformat() if not pd.isna(v) else None
    try:
        if pd.isna(v): return None
    except (TypeError, ValueError):
        pass
    return v


def df_profile(df: pd.DataFrame, filename: str = "") -> dict:
    """Compute a lightweight profile summary for a DataFrame."""
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else None)

    missing     = int(df.isnull().sum().sum())
    numeric_cnt = int(len(df.select_dtypes(include=np.number).columns))
    total_cells = df.shape[0] * df.shape[1]
    miss_pct    = round(missing / max(total_cells, 1) * 100, 1)
    columns = []
    for col, dtype in zip(df.columns, df.dtypes):
        null_pct = round(df[col].isnull().mean() * 100, 1)
        columns.append({
            "name": col, "dtype": str(dtype),
            "null_pct": null_pct, "quality": round(100 - null_pct, 1)
        })
    return {
        "filename": filename,
        "rows": df.shape[0], "cols": df.shape[1],
        "numeric": numeric_cnt, "missing": missing, "missing_pct": miss_pct,
        "columns": columns,
    }


def df_to_json_rows(df: pd.DataFrame, limit: int = 500) -> dict:
    """Serialize a DataFrame to a dict suitable for JSON response."""
    total = len(df)
    preview_df = df.head(limit).replace([np.inf, -np.inf], None)
    headers = [str(c) for c in preview_df.columns]
    rows = [[safe_json_value(v) for v in row] for _, row in preview_df.iterrows()]
    return {
        "headers": headers,
        "rows": rows,
        "loaded": len(preview_df),
        "total": total,
        "preview_only": total > len(preview_df),
    }


# ── Financial / stat formatting ───────────────────────────────────────────────

def is_financial(col_name: str) -> bool:
    if not col_name:
        return False
    cl = str(col_name).lower()
    return any(kw in cl for kw in ["price", "revenue", "cost", "sales", "spend", "profit"])


def format_stat_val(col_name: Optional[str], val: float) -> str:
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    is_fin = is_financial(col_name or "")
    prefix = "$" if is_fin else ""
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        formatted = f"{val / 1_000_000:.2f}M"
    elif abs_val >= 1_000:
        formatted = f"{val / 1_000:.1f}K"
    else:
        if is_fin:
            formatted = f"{val:,.2f}"
        else:
            formatted = f"{val:,.0f}" if val == int(val) else f"{val:,.2f}"
    for suffix in (".00M", ".0M", ".0K"):
        if formatted.endswith(suffix):
            formatted = formatted[: -len(suffix)] + suffix[-1]
    return f"{prefix}{formatted}"


_ID_KEYWORDS = (
    "id", "no", "num", "number", "code", "roll", "batch",
    "year", "reg", "serial", "seq", "rank", "index", "ref",
    "emp", "student", "class", "section", "grade", "date", "time", "timestamp",
)


def is_id_like_col(col_name: str, series: pd.Series) -> bool:
    cl = col_name.lower().replace("_", " ").replace("-", " ")
    if any(kw in cl.split() or cl.startswith(kw) or cl.endswith(kw) for kw in _ID_KEYWORDS):
        return True
    if pd.api.types.is_integer_dtype(series):
        unique_vals = series.dropna().unique()
        if len(unique_vals) <= max(20, len(series) * 0.05):
            return True
        if all(1900 <= v <= 2100 for v in unique_vals[:50]):
            return True
    return False
