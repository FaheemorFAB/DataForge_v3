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


def robust_numeric_series(series: Any) -> pd.Series:
    """Coerce series to numeric, stripping currency signs, commas, and percentage symbols."""
    if series is None:
        return pd.Series(dtype=float)
    if not isinstance(series, pd.Series):
        series = pd.Series(series)
    if len(series) == 0:
        return pd.Series(dtype=float)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.replace(r'[\$,%€£¥]', '', regex=True).str.replace(',', '').str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


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


def format_bytes(num_bytes: Optional[Union[int, float]]) -> str:
    """Format byte counts into a readable string (e.g. 500 B, 45.2 KB, 1.4 MB, 2.1 GB)."""
    if num_bytes is None or num_bytes < 0:
        return "—"
    if num_bytes < 1024:
        return f"{int(num_bytes)} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def df_profile(df: pd.DataFrame, filename: str = "", raw_bytes: Optional[int] = None) -> dict:
    """Compute a lightweight profile summary for a DataFrame."""
    missing     = int(df.isnull().sum().sum())
    numeric_cnt = int(len(df.select_dtypes(include=np.number).columns))
    total_cells = df.shape[0] * df.shape[1]
    miss_pct    = round(missing / max(total_cells, 1) * 100, 1)

    if raw_bytes is not None and raw_bytes > 0:
        size_bytes = int(raw_bytes)
    else:
        try:
            size_bytes = int(df.memory_usage(deep=True).sum())
        except Exception:
            size_bytes = 0

    size_human = format_bytes(size_bytes)
    size_mb = round(size_bytes / (1024 * 1024), 2)

    columns = []
    for col, dtype in zip(df.columns, df.dtypes):
        null_pct = round(df[col].isnull().mean() * 100, 1)
        columns.append({
            "name": str(col), "dtype": str(dtype),
            "null_pct": null_pct, "quality": round(100 - null_pct, 1)
        })
    return {
        "filename": filename,
        "rows": df.shape[0], "cols": df.shape[1],
        "numeric": numeric_cnt, "missing": missing, "missing_pct": miss_pct,
        "size_bytes": size_bytes,
        "size_human": size_human,
        "size_mb": size_mb,
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

import re

# Explicit identifier keywords or concatenated suffixes/tokens
_ID_EXACT_NAMES = {
    "id", "uuid", "guid", "uid", "pk", "fk", "key", "idx", "index",
    "hash", "token", "ssn", "ein", "pincode", "zipcode", "postalcode",
    "rollno", "roll_no", "rollnum", "roll_num", "rollnumber", "roll_number",
    "regno", "reg_no", "regnum", "reg_num", "registration_no", "registration_number",
    "std_id", "student_id", "studentid", "student_no", "studentno",
    "emp_id", "empid", "employee_id", "employee_no", "emp_no", "empno",
    "cust_id", "customer_id", "customerid", "client_id", "user_id", "userid",
    "acc_no", "accno", "account_no", "accountno", "account_num", "accountnumber",
    "inv_no", "invno", "invoice_no", "invoiceno", "bill_no", "billno",
    "order_id", "orderid", "trans_id", "transaction_id", "txn_id", "receipt_no",
    "ticket_id", "ticketid", "seq_no", "serial_no", "serialno", "serial_num",
    "batch_no", "batchno", "lot_no", "lotno", "phone_no", "phoneno", "mobile_no", "mobileno",
    "row_id", "row_num", "row_no", "rownum", "record_id",
}

_ID_REGEX = [
    re.compile(r"(^|[_\s])(id|uuid|guid|uid|pk|fk|key|idx|index)([_\s]|\d*$)", re.IGNORECASE),
    re.compile(r"(^|[_\s])(roll|reg|serial|seq|invoice|order|ticket|acc|account|cust|customer|emp|employee|user|student|member)[_\s]*(no|num|number|code|id)([_\s]|\d*$)", re.IGNORECASE),
    re.compile(r"(^|[_\s])(zip|postal|pin)[_\s]*(code)?([_\s]|\d*$)", re.IGNORECASE),
    re.compile(r"(^|[_\s])(phone|mobile|fax|tel)[_\s]*(no|num|number)?([_\s]|\d*$)", re.IGNORECASE),
    re.compile(r"(^|[_\s])(ssn|ein|itin|pan|aadhaar|license)[_\s]*(no|num|number)?([_\s]|\d*$)", re.IGNORECASE),
    re.compile(r"(^|[_\s])(code|tag|ref)([_\s]|\d*$)", re.IGNORECASE),
]

_PROTECTED_METRIC_WORDS = {
    "sales", "revenue", "profit", "loss", "margin", "cost", "expense", "budget",
    "price", "amount", "salary", "wage", "income", "balance", "total", "subtotal",
    "discount", "tax", "fee", "rate", "score", "rating", "gdp", "volume",
    "count", "quantity", "units", "inventory", "stock", "weight", "height", "length",
    "width", "depth", "distance", "duration", "hours", "minutes", "seconds", "days",
    "age", "temperature", "speed", "latitude", "longitude", "percentage", "pct", "ratio",
    "target", "prediction", "probability", "marks", "grade_point", "gpa",
}


def is_id_like_col(col_name: str, series: Optional[pd.Series] = None) -> bool:
    """
    Determines whether a column is an entity identifier, roll number, registration
    number, postal code, phone, or index that should NEVER be subject to mathematical
    aggregations like sum(), mean(), or variance.
    """
    if not col_name:
        return False
    cl = col_name.strip().lower()
    cl_clean = re.sub(r"[^a-z0-9]", "", cl)
    cl_tokens = set(re.split(r"[^a-z0-9]+", cl))

    # Explicit known ID names/compounds
    if cl in _ID_EXACT_NAMES or cl_clean in _ID_EXACT_NAMES:
        return True

    # If column ends with _id, _no, _num, _code (e.g. order_id, roll_no, emp_no)
    if cl.endswith(("_id", "-id", ".id", "_no", "-no", "_num", "-num", "_code", "-code", "_uuid", "_guid")):
        return True

    # Check regex patterns
    if any(pat.search(cl) for pat in _ID_REGEX):
        # But ensure we don't accidentally match legitimate measures unless explicit id suffix
        is_protected_metric = any(pw in cl_tokens for pw in _PROTECTED_METRIC_WORDS)
        if not is_protected_metric or cl.endswith(("_id", "_no", "_code", "_num")):
            return True

    # If series is provided, inspect data properties
    if series is not None and len(series) > 0:
        try:
            s_clean = series.dropna()
            if len(s_clean) > 0:
                # Check for year (1900-2100) -> temporal, not a summable metric
                if "year" in cl or "yr" in cl_tokens:
                    return True

                if pd.api.types.is_numeric_dtype(s_clean):
                    # Year integer check
                    if len(s_clean) >= 5 and (s_clean >= 1900).all() and (s_clean <= 2100).all():
                        return True

                    # Strictly sequential integers (e.g. 1, 2, 3, 4, 5... or 101, 102, 103...)
                    if pd.api.types.is_integer_dtype(s_clean) and len(s_clean) >= 5:
                        s_sorted = np.sort(s_clean.values)
                        diffs = np.diff(s_sorted)
                        if len(diffs) > 0 and np.all(diffs == 1) and s_sorted[0] >= 0:
                            # Sequential index sequence
                            if not any(pw in cl_tokens for pw in _PROTECTED_METRIC_WORDS):
                                return True

                    # High uniqueness integer without financial/metric names
                    if len(s_clean) >= 10 and pd.api.types.is_integer_dtype(s_clean):
                        unique_ratio = s_clean.nunique() / len(s_clean)
                        if unique_ratio >= 0.90:
                            if any(k in cl for k in ("id", "no", "num", "code", "roll", "reg", "std", "emp", "cust", "acc", "key")):
                                return True
        except Exception:
            pass

    return False


def is_valid_metric_col(col_name: str, series: Optional[pd.Series] = None) -> bool:
    """
    Returns True only if the column is numeric and is a genuine aggregatable business
    measure (NOT an identifier, roll number, or non-metric code).
    """
    if not col_name:
        return False
    if is_id_like_col(col_name, series):
        return False
    if series is not None:
        try:
            s_num = robust_numeric_series(series)
            if s_num.notna().sum() >= max(3, int(len(series) * 0.5)):
                return True
        except Exception:
            return False
    return True
