"""
Module: Data Cleaning
Pure Python — no Streamlit. Returns dicts/DataFrames for Flask & FastAPI API consumption.

FIXES (2026-03):
  • janitor.clean_names(case_type=…) → removed in pyjanitor ≥ 0.29; now uses
    try/except with graceful fallback to manual snake_case so any janitor version works.
  • pd.to_datetime(infer_format=True) → removed in pandas ≥ 2.2; argument dropped.
  • Column-drop loop: collect candidates first, then drop in one shot to avoid
    mutating df.columns mid-iteration.
  • series.skew() returns NaN when n < 3; guard with explicit count check.
  • Dynamic Data Cleaning Engine added: column-by-column interactive rule execution.
"""

import re
import pandas as pd
import numpy as np

try:
    import janitor  # noqa: F401
    JANITOR_OK = True
except ImportError:
    JANITOR_OK = False


# ── helpers ───────────────────────────────────────────────────────────────────

def _to_snake(name: str) -> str:
    """Convert any column name string to snake_case."""
    s = str(name).strip()
    s = re.sub(r"[^\w\s]", "_", s)          # non-word chars → _
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)   # ABCDef → ABC_Def
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)       # camelCase → camel_Case
    s = re.sub(r"[\s\-]+", "_", s)           # spaces/dashes → _
    s = re.sub(r"_+", "_", s)               # collapse multiple _
    return s.strip("_").lower()


def _is_non_numeric(series: pd.Series) -> bool:
    """
    True for string / categorical / object columns.
    Handles both legacy object dtype (pandas < 2) and the new
    StringDtype (pandas 3.x where string cols default to 'str' dtype).
    """
    if pd.api.types.is_numeric_dtype(series):
        return False
    if pd.api.types.is_datetime64_any_dtype(series):
        return False
    return True  # string, object, category, StringDtype, etc.


def _infer_fill_strategy(series: pd.Series):
    """Return (strategy_label, filled_series)."""
    if _is_non_numeric(series):
        mode_vals = series.mode(dropna=True)
        mode_val  = mode_vals.iloc[0] if not mode_vals.empty else "Unknown"
        return f"mode ('{mode_val}')", series.fillna(mode_val)

    n_valid = series.notna().sum()
    if n_valid < 3:
        median_val = float(series.median())
        return f"median ({median_val:.4g})", series.fillna(median_val)

    median_val = float(series.median())
    mean_val   = float(series.mean())
    skew_val   = series.skew()
    skew       = abs(skew_val) if pd.notna(skew_val) else 0.0
    if skew > 1:
        return f"median ({median_val:.4g})", series.fillna(median_val)
    else:
        return f"mean ({mean_val:.4g})", series.fillna(mean_val)


# ── public API ────────────────────────────────────────────────────────────────

def auto_fix_missing(df: pd.DataFrame) -> tuple:
    """
    Impute missing values column-by-column.
    Returns (cleaned_df, log_of_changes as list[dict]).
    """
    df = df.copy()
    log = []

    to_drop = []
    for col in df.columns:
        n_missing = int(df[col].isnull().sum())
        if n_missing == 0:
            continue
        pct = n_missing / len(df) * 100
        if pct > 60:
            to_drop.append(col)
            log.append({
                "column":      col,
                "missing":     n_missing,
                "pct_missing": round(pct, 1),
                "action":      "Dropped (>60% missing)",
                "type":        "drop",
            })

    if to_drop:
        df.drop(columns=to_drop, inplace=True)

    for col in df.columns:
        n_missing = int(df[col].isnull().sum())
        if n_missing == 0:
            continue
        pct = n_missing / len(df) * 100
        strategy, filled = _infer_fill_strategy(df[col])
        df[col] = filled
        log.append({
            "column":      col,
            "missing":     n_missing,
            "pct_missing": round(pct, 1),
            "action":      f"Filled with {strategy}",
            "type":        "fill",
        })

    return df, log


def structural_clean(df: pd.DataFrame) -> tuple:
    """
    Apply pyjanitor + structural fixes.
    Returns (cleaned_df, list[str] of actions).
    """
    actions = []
    original_cols = df.columns.tolist()

    if JANITOR_OK:
        applied_janitor = False
        try:
            df = df.janitor.clean_names(strip_underscores=True)
            applied_janitor = True
        except TypeError:
            pass

        if not applied_janitor:
            try:
                df = df.janitor.clean_names(strip_underscores=True, case_type="snake")
                applied_janitor = True
            except TypeError:
                pass

        if not applied_janitor:
            df.columns = [_to_snake(c) for c in df.columns]
    else:
        df.columns = [_to_snake(c) for c in df.columns]

    new_cols = df.columns.tolist()
    renamed  = [(o, n) for o, n in zip(original_cols, new_cols) if o != n]
    if renamed:
        actions.append(f"Renamed {len(renamed)} column(s) to snake_case")

    n_dupes = int(df.duplicated().sum())
    if n_dupes:
        df = df.drop_duplicates()
        actions.append(f"Removed {n_dupes:,} duplicate row(s)")

    str_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in str_cols:
        df[col] = df[col].str.strip()
    if str_cols:
        actions.append(f"Stripped whitespace from {len(str_cols)} string column(s)")

    empty_rows = int(df.isnull().all(axis=1).sum())
    if empty_rows:
        df = df[~df.isnull().all(axis=1)]
        actions.append(f"Removed {empty_rows} fully-empty row(s)")

    for col in df.select_dtypes(include=["object", "string"]).columns.tolist():
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().mean() > 0.85:
            df[col] = coerced
            actions.append(f"Coerced '{col}' to numeric")

    for col in df.select_dtypes(include=["object", "string"]).columns.tolist():
        try:
            parsed = pd.to_datetime(df[col], format="mixed", dayfirst=False, errors="coerce")
            if parsed.notna().mean() > 0.85:
                df[col] = parsed
                actions.append(f"Parsed '{col}' as datetime")
        except Exception:
            pass

    if not actions:
        actions.append("No structural issues found — data looks clean!")

    return df, actions


def run_cleaning_pipeline(df_raw: pd.DataFrame) -> dict:
    """
    Run automated 1-click cleaning pipeline.
    Returns dict with cleaned df, stats, logs.
    """
    df_step1, missing_log  = auto_fix_missing(df_raw)
    df_clean, struct_actions = structural_clean(df_step1)

    return {
        "df_clean":       df_clean,
        "missing_log":    missing_log,
        "struct_actions": struct_actions,
        "stats": {
            "original_rows": int(len(df_raw)),
            "cleaned_rows":  int(len(df_clean)),
            "original_cols": int(df_raw.shape[1]),
            "cleaned_cols":  int(df_clean.shape[1]),
            "rows_removed":  int(len(df_raw) - len(df_clean)),
            "cols_removed":  int(df_raw.shape[1] - df_clean.shape[1]),
        },
    }


def run_dynamic_cleaning_pipeline(df_raw: pd.DataFrame, rules: list[dict]) -> dict:
    """
    Applies custom user-defined dynamic cleaning rules column-by-column.
    Returns cleaned dataframe, audit log of actions, and before/after stats.
    """
    df = df_raw.copy()
    logs = []
    
    for rule in rules:
        col = rule.get("column")
        action = rule.get("action_type")
        if not col or col not in df.columns:
            continue
        
        # 1. Drop Column
        if action == "drop":
            df.drop(columns=[col], inplace=True)
            logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Dropped column '{col}'", "type": "drop"})
            continue

        # 2. Imputation
        if action == "impute":
            method = rule.get("impute_method", "mean")
            val = rule.get("fill_value")
            n_miss = int(df[col].isnull().sum())
            pct_miss = round(n_miss / len(df) * 100, 1) if len(df) > 0 else 0.0
            
            if n_miss > 0:
                if method == "mean" and pd.api.types.is_numeric_dtype(df[col]):
                    m_val = float(df[col].mean())
                    df[col] = df[col].fillna(m_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Filled with Mean ({m_val:.4g})", "type": "fill"})
                elif method == "median" and pd.api.types.is_numeric_dtype(df[col]):
                    m_val = float(df[col].median())
                    df[col] = df[col].fillna(m_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Filled with Median ({m_val:.4g})", "type": "fill"})
                elif method == "mode":
                    mode_v = df[col].mode(dropna=True)
                    m_val = mode_v.iloc[0] if not mode_v.empty else "Unknown"
                    df[col] = df[col].fillna(m_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Filled with Mode ('{m_val}')", "type": "fill"})
                elif method == "zero":
                    df[col] = df[col].fillna(0)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": "Filled with 0", "type": "fill"})
                elif method == "constant":
                    c_val = val if val is not None else "N/A"
                    df[col] = df[col].fillna(c_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Filled with Constant ('{c_val}')", "type": "fill"})
                elif method == "ffill":
                    df[col] = df[col].ffill()
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": "Forward-filled values", "type": "fill"})
                elif method == "bfill":
                    df[col] = df[col].bfill()
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": "Backward-filled values", "type": "fill"})
                elif method == "drop_rows":
                    before_len = len(df)
                    df = df.dropna(subset=[col])
                    dropped_n = before_len - len(df)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Dropped {dropped_n} rows with missing values", "type": "drop"})

        # 3. Outlier Handling
        elif action == "outlier" and pd.api.types.is_numeric_dtype(df[col]):
            method = rule.get("outlier_method", "clip")
            q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            iqr = q3 - q1
            lo_fence, hi_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers_mask = (df[col] < lo_fence) | (df[col] > hi_fence)
            n_outliers = int(outliers_mask.sum())

            if n_outliers > 0:
                if method == "clip":
                    p1, p99 = df[col].quantile(0.01), df[col].quantile(0.99)
                    df[col] = df[col].clip(lower=p1, upper=p99)
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Clipped {n_outliers} outliers to [1st, 99th] percentiles", "type": "outlier"})
                elif method == "drop_rows":
                    before_len = len(df)
                    df = df[~outliers_mask]
                    dropped_n = before_len - len(df)
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Removed {dropped_n} outlier rows", "type": "outlier"})
                elif method == "fill_median":
                    med_val = float(df[col].median())
                    df.loc[outliers_mask, col] = med_val
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Replaced {n_outliers} outliers with Median ({med_val:.4g})", "type": "outlier"})

        # 4. Text Normalization
        elif action == "normalize":
            case_opt = rule.get("text_case", "trim")
            if _is_non_numeric(df[col]):
                if case_opt == "lowercase":
                    df[col] = df[col].astype(str).str.lower().str.strip()
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Converted text to lowercase", "type": "normalize"})
                elif case_opt == "uppercase":
                    df[col] = df[col].astype(str).str.upper().str.strip()
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Converted text to uppercase", "type": "normalize"})
                elif case_opt == "trim":
                    df[col] = df[col].astype(str).str.strip()
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Trimmed leading/trailing whitespace", "type": "normalize"})

        # 5. Type Casting
        elif action == "cast":
            target_type = rule.get("cast_type", "float")
            try:
                if target_type == "float":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Cast column to Float", "type": "cast"})
                elif target_type == "int":
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Cast column to Integer", "type": "cast"})
                elif target_type == "datetime":
                    df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Parsed column as Datetime", "type": "cast"})
                elif target_type == "string":
                    df[col] = df[col].astype(str)
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Cast column to Text", "type": "cast"})
            except Exception as e:
                logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Type cast failed: {e}", "type": "error"})

    if not logs:
        logs.append({"column": "Dataset", "missing": 0, "pct_missing": 0.0, "action": "Dynamic rules applied cleanly.", "type": "info"})

    return {
        "df_clean": df,
        "missing_log": logs,
        "struct_actions": [l["action"] for l in logs],
        "stats": {
            "original_rows": int(len(df_raw)),
            "cleaned_rows": int(len(df)),
            "original_cols": int(df_raw.shape[1]),
            "cleaned_cols": int(df.shape[1]),
            "rows_removed": int(len(df_raw) - len(df)),
            "cols_removed": int(df_raw.shape[1] - df.shape[1]),
        },
    }