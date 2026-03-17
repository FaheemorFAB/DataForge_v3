"""
Module: Data Cleaning
Pure Python — no Streamlit. Returns dicts/DataFrames for Flask API consumption.

FIXES (2026-03):
  • janitor.clean_names(case_type=…) → removed in pyjanitor ≥ 0.29; now uses
    try/except with graceful fallback to manual snake_case so any janitor version works.
  • pd.to_datetime(infer_format=True) → removed in pandas ≥ 2.2; argument dropped.
  • Column-drop loop: collect candidates first, then drop in one shot to avoid
    mutating df.columns mid-iteration.
  • series.skew() returns NaN when n < 3; guard with explicit count check.
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

    # FIX: collect columns to drop first — avoids mutating df.columns mid-loop
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

    # Now fill remaining columns
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

    # ── Column name normalisation ─────────────────────────────────────────────
    # FIX: pyjanitor ≥ 0.29 removed the case_type parameter entirely.
    # We now try the new API (no case_type), fall back to old API, then fall back
    # to a pure-Python snake_case implementation — so ANY version works.
    if JANITOR_OK:
        applied_janitor = False
        # Try new API (>= 0.29): clean_names has no case_type
        try:
            df = df.janitor.clean_names(strip_underscores=True)
            applied_janitor = True
        except TypeError:
            pass

        # Try old API (< 0.29) with case_type
        if not applied_janitor:
            try:
                df = df.janitor.clean_names(strip_underscores=True, case_type="snake")
                applied_janitor = True
            except TypeError:
                pass

        if not applied_janitor:
            # janitor is present but neither API worked — fall through to manual
            df.columns = [_to_snake(c) for c in df.columns]
    else:
        # Pure-Python fallback (no janitor installed)
        df.columns = [_to_snake(c) for c in df.columns]

    new_cols = df.columns.tolist()
    renamed  = [(o, n) for o, n in zip(original_cols, new_cols) if o != n]
    if renamed:
        actions.append(f"Renamed {len(renamed)} column(s) to snake_case")

    # ── Duplicate rows ────────────────────────────────────────────────────────
    n_dupes = int(df.duplicated().sum())
    if n_dupes:
        df = df.drop_duplicates()
        actions.append(f"Removed {n_dupes:,} duplicate row(s)")

    # ── Whitespace in strings ─────────────────────────────────────────────────
    str_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in str_cols:
        df[col] = df[col].str.strip()
    if str_cols:
        actions.append(f"Stripped whitespace from {len(str_cols)} string column(s)")

    # ── Fully-empty rows ──────────────────────────────────────────────────────
    empty_rows = int(df.isnull().all(axis=1).sum())
    if empty_rows:
        df = df[~df.isnull().all(axis=1)]
        actions.append(f"Removed {empty_rows} fully-empty row(s)")

    # ── Numeric coercion ──────────────────────────────────────────────────────
    for col in df.select_dtypes(include=["object", "string"]).columns.tolist():
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().mean() > 0.85:
            df[col] = coerced
            actions.append(f"Coerced '{col}' to numeric")

    # ── Datetime parsing ──────────────────────────────────────────────────────
    # FIX: removed infer_format=True — parameter was deprecated in pandas 2.0
    #      and fully removed in pandas 2.2, causing an unhandled TypeError.
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
    Run full cleaning pipeline.
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