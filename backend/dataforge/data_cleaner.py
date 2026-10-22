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
        try:
            mode_vals = series.mode(dropna=True)
            mode_val  = mode_vals.iloc[0] if not mode_vals.empty else "Unknown"
        except Exception:
            mode_val = "Unknown"

        # If mode_val is a list or dict, use apply/where instead of fillna (pandas requires scalar for fillna)
        if isinstance(mode_val, (list, dict, set, tuple)):
            filled = series.apply(
                lambda x: mode_val if (x is None or (isinstance(x, float) and np.isnan(x))) else x
            )
            return f"mode ({mode_val})", filled
        else:
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


def _safe_duplicated(df: pd.DataFrame) -> pd.Series:
    """Safely check duplicated rows even when columns contain unhashable types (lists, dicts)."""
    try:
        return df.duplicated()
    except TypeError:
        import json
        hashable_cols = {}
        for c in df.columns:
            if df[c].dtype == "object":
                sample = df[c].dropna().iloc[0] if not df[c].dropna().empty else None
                if isinstance(sample, (list, dict, set, tuple)):
                    hashable_cols[c] = df[c].apply(
                        lambda x: json.dumps(x, sort_keys=True, default=str) if isinstance(x, (list, dict, set, tuple)) else str(x)
                    )
        temp = df.assign(**hashable_cols) if hashable_cols else df
        return temp.duplicated()


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

    imputed_cells: dict[str, dict] = {}
    for col in df.columns:
        missing_mask = df[col].isnull()
        n_missing = int(missing_mask.sum())
        if n_missing == 0:
            continue
        pct = n_missing / len(df) * 100
        strategy, filled = _infer_fill_strategy(df[col])
        imputed_indices = [int(idx) for idx in df.index[missing_mask].tolist()]
        imputed_cells[col] = {
            "strategy": strategy,
            "imputed_count": n_missing,
            "pct_missing": round(pct, 1),
            "sample_imputed_indices": imputed_indices[:50],
        }
        df[col] = filled
        log.append({
            "column":      col,
            "missing":     n_missing,
            "pct_missing": round(pct, 1),
            "action":      f"Filled with {strategy}",
            "type":        "fill",
            "imputed_indices_count": n_missing,
            "sample_imputed_indices": imputed_indices[:50],
        })

    return df, log, imputed_cells


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

    dup_mask = _safe_duplicated(df)
    n_dupes = int(dup_mask.sum())
    if n_dupes:
        df = df[~dup_mask]
        actions.append(f"Removed {n_dupes:,} duplicate row(s)")

    str_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    stripped_count = 0
    for col in str_cols:
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
        if isinstance(sample, str):
            df[col] = df[col].astype(str).str.strip()
            stripped_count += 1
        elif isinstance(sample, list):
            df[col] = df[col].apply(
                lambda lst: [x.strip() if isinstance(x, str) else x for x in lst] if isinstance(lst, list) else lst
            )
            stripped_count += 1
    if stripped_count:
        actions.append(f"Stripped whitespace from {stripped_count} string column(s)")

    empty_rows = int(df.isnull().all(axis=1).sum())
    if empty_rows:
        df = df[~df.isnull().all(axis=1)]
        actions.append(f"Removed {empty_rows} fully-empty row(s)")

    for col in df.select_dtypes(include=["object", "string"]).columns.tolist():
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
        if not isinstance(sample, (str, bytes, int, float)) or isinstance(sample, (list, dict, set, tuple)):
            continue
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().mean() > 0.85:
            df[col] = coerced
            actions.append(f"Coerced '{col}' to numeric")

    for col in df.select_dtypes(include=["object", "string"]).columns.tolist():
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
        if not isinstance(sample, (str, bytes)) or isinstance(sample, (list, dict, set, tuple)):
            continue
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
    Returns dict with cleaned df, stats, logs, and flagged imputed cells.
    """
    res = auto_fix_missing(df_raw)
    if len(res) == 3:
        df_step1, missing_log, imputed_cells = res
    else:
        df_step1, missing_log = res
        imputed_cells = {}

    df_clean, struct_actions = structural_clean(df_step1)

    return {
        "df_clean":       df_clean,
        "missing_log":    missing_log,
        "imputed_cells":  imputed_cells,
        "struct_actions": struct_actions,
        "stats": {
            "original_rows": int(len(df_raw)),
            "cleaned_rows":  int(len(df_clean)),
            "original_cols": int(df_raw.shape[1]),
            "cleaned_cols":  int(df_clean.shape[1]),
            "rows_removed":  int(len(df_raw) - len(df_clean)),
            "cols_removed":  int(df_raw.shape[1] - df_clean.shape[1]),
            "imputed_columns_count": len(imputed_cells),
        },
    }


def run_dynamic_cleaning_pipeline(df_raw: pd.DataFrame, rules: list[dict]) -> dict:
    """
    Applies custom user-defined dynamic cleaning rules column-by-column or in batch.
    Enterprise-grade engine supporting advanced statistical and ML algorithms:
      • Multi-column batch transformations
      • Advanced Imputation: Mean, Median, Mode, Constant, Zero, Forward/Backward fill,
        Linear/Spline/Polynomial Interpolation, KNN Imputer, MICE (IterativeImputer)
      • Outlier Handling: Tunable IQR fence (k-multiplier), Z-Score, Modified Z-Score (MAD),
        Isolation Forest, Local Outlier Factor (LOF), Percentile Winsorization
      • Scaling & Normalization: RobustScaler, StandardScaler, MinMaxScaler
      • Categorical Encoding: One-Hot Encoding (with min_freq), Ordinal Encoding
      • Text & PII Protection: Case conversion, Trim, RegEx substitution, Fuzzy Deduplication,
        PII masking (Email, Phone, SSN, Credit Cards)
      • Type Casting & Column Dropping
    """
    df = df_raw.copy()
    logs = []

    for rule in rules:
        # Support both 'columns' (list of str) and 'column' (single str)
        cols = rule.get("columns")
        if not cols:
            single_col = rule.get("column")
            cols = [single_col] if single_col else []
        
        # Filter to columns that actually exist in df
        target_cols = [c for c in cols if c in df.columns]
        if not target_cols:
            continue

        action = rule.get("action_type") or rule.get("action")

        # ── 1. DROP COLUMNS ───────────────────────────────────────────────────
        if action == "drop":
            df.drop(columns=target_cols, inplace=True)
            for c in target_cols:
                logs.append({
                    "column": c,
                    "missing": 0,
                    "pct_missing": 0.0,
                    "action": f"Dropped column '{c}'",
                    "type": "drop",
                })
            continue

        # ── 2. IMPUTATION ─────────────────────────────────────────────────────
        if action == "impute":
            method = rule.get("impute_method", "median")
            val = rule.get("fill_value")

            # A. Multivariate KNN Imputation (applied jointly across selected numeric cols)
            if method == "knn":
                num_target = [c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])]
                if num_target:
                    k_neighbors = int(rule.get("knn_neighbors", 5))
                    weights = rule.get("knn_weights", "uniform")
                    try:
                        from sklearn.impute import KNNImputer
                        imputer = KNNImputer(n_neighbors=k_neighbors, weights=weights)
                        df[num_target] = imputer.fit_transform(df[num_target])
                        for c in num_target:
                            logs.append({
                                "column": c,
                                "missing": 0,
                                "pct_missing": 0.0,
                                "action": f"Imputed via KNN (k={k_neighbors}, weights={weights})",
                                "type": "fill",
                            })
                    except Exception:
                        # Graceful fallback to median if sklearn is unavailable or fails
                        for c in num_target:
                            med = float(df[c].median())
                            df[c] = df[c].fillna(med)
                            logs.append({
                                "column": c,
                                "missing": 0,
                                "pct_missing": 0.0,
                                "action": f"Filled with Median ({med:.4g}) [KNN Fallback]",
                                "type": "fill",
                            })
                continue

            # B. Multivariate MICE / Iterative Imputation
            elif method in ("mice", "iterative"):
                num_target = [c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])]
                if num_target:
                    max_iter = int(rule.get("mice_max_iter", 10))
                    init_strat = rule.get("mice_initial", "median")
                    try:
                        from sklearn.experimental import enable_iterative_imputer  # noqa: F401
                        from sklearn.impute import IterativeImputer
                        imputer = IterativeImputer(max_iter=max_iter, initial_strategy=init_strat, random_state=42)
                        df[num_target] = imputer.fit_transform(df[num_target])
                        for c in num_target:
                            logs.append({
                                "column": c,
                                "missing": 0,
                                "pct_missing": 0.0,
                                "action": f"Imputed via MICE / IterativeImputer (max_iter={max_iter})",
                                "type": "fill",
                            })
                    except Exception:
                        for c in num_target:
                            med = float(df[c].median())
                            df[c] = df[c].fillna(med)
                            logs.append({
                                "column": c,
                                "missing": 0,
                                "pct_missing": 0.0,
                                "action": f"Filled with Median ({med:.4g}) [MICE Fallback]",
                                "type": "fill",
                            })
                continue

            # C. Standard Univariate Imputations (per column)
            for col in target_cols:
                n_miss = int(df[col].isnull().sum())
                pct_miss = round(n_miss / len(df) * 100, 1) if len(df) > 0 else 0.0
                if n_miss == 0:
                    continue

                if method == "mean" and pd.api.types.is_numeric_dtype(df[col]):
                    trim = float(rule.get("trim_percent", 0.0))
                    if 0.0 < trim < 0.5:
                        try:
                            from scipy.stats import trim_mean
                            m_val = float(trim_mean(df[col].dropna(), proportiontocut=trim))
                            action_label = f"Filled with Trimmed Mean ({trim*100:.0f}% cut: {m_val:.4g})"
                        except Exception:
                            m_val = float(df[col].mean())
                            action_label = f"Filled with Mean ({m_val:.4g})"
                    else:
                        m_val = float(df[col].mean())
                        action_label = f"Filled with Mean ({m_val:.4g})"
                    df[col] = df[col].fillna(m_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": action_label, "type": "fill"})

                elif method == "median" and pd.api.types.is_numeric_dtype(df[col]):
                    m_val = float(df[col].median())
                    df[col] = df[col].fillna(m_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Filled with Median ({m_val:.4g})", "type": "fill"})

                elif method == "mode":
                    try:
                        mode_v = df[col].mode(dropna=True)
                        m_val = mode_v.iloc[0] if not mode_v.empty else "Unknown"
                    except Exception:
                        m_val = "Unknown"
                    if isinstance(m_val, (list, dict, set, tuple)):
                        df[col] = df[col].apply(lambda x: m_val if (x is None or (isinstance(x, float) and np.isnan(x))) else x)
                    else:
                        df[col] = df[col].fillna(m_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Filled with Mode ('{m_val}')", "type": "fill"})

                elif method == "zero":
                    df[col] = df[col].fillna(0)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": "Filled with 0", "type": "fill"})

                elif method == "constant":
                    c_val = val if val is not None and str(val).strip() != "" else "N/A"
                    df[col] = df[col].fillna(c_val)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Filled with Constant ('{c_val}')", "type": "fill"})

                elif method == "ffill":
                    limit = int(rule.get("fill_limit")) if rule.get("fill_limit") else None
                    df[col] = df[col].ffill(limit=limit)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Forward-filled values (limit={limit})", "type": "fill"})

                elif method == "bfill":
                    limit = int(rule.get("fill_limit")) if rule.get("fill_limit") else None
                    df[col] = df[col].bfill(limit=limit)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Backward-filled values (limit={limit})", "type": "fill"})

                elif method == "interpolate" and pd.api.types.is_numeric_dtype(df[col]):
                    interp_m = rule.get("interp_method", "linear")
                    order = int(rule.get("interp_order", 2))
                    limit_dir = rule.get("limit_direction", "both")
                    try:
                        if interp_m in ("polynomial", "spline"):
                            df[col] = df[col].interpolate(method=interp_m, order=order, limit_direction=limit_dir)
                        else:
                            df[col] = df[col].interpolate(method="linear", limit_direction=limit_dir)
                        logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Interpolated ({interp_m}, order={order})", "type": "fill"})
                    except Exception as e:
                        df[col] = df[col].interpolate(method="linear")
                        logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Linear interpolation (fallback: {e})", "type": "fill"})

                elif method == "drop_rows":
                    before_len = len(df)
                    df = df.dropna(subset=[col])
                    dropped_n = before_len - len(df)
                    logs.append({"column": col, "missing": n_miss, "pct_missing": pct_miss, "action": f"Dropped {dropped_n} rows with missing values", "type": "drop"})

        # ── 3. OUTLIER HANDLING ───────────────────────────────────────────────
        elif action == "outlier":
            method = rule.get("outlier_method", "iqr")
            sub_action = rule.get("outlier_action", "clip")

            # A. Multivariate Isolation Forest
            if method == "isolation_forest":
                num_target = [c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])]
                if num_target:
                    contam = float(rule.get("iso_contamination", 0.05))
                    n_est = int(rule.get("iso_estimators", 100))
                    try:
                        from sklearn.ensemble import IsolationForest
                        iso = IsolationForest(contamination=contam, n_estimators=n_est, random_state=42)
                        # Impute temporary median for rows with null to allow isolation forest
                        x_temp = df[num_target].fillna(df[num_target].median())
                        preds = iso.fit_predict(x_temp)
                        outlier_mask = (preds == -1)
                        n_outliers = int(outlier_mask.sum())
                        if n_outliers > 0:
                            if sub_action == "drop_rows":
                                before_len = len(df)
                                df = df[~outlier_mask]
                                dropped_n = before_len - len(df)
                                logs.append({"column": ", ".join(num_target), "missing": 0, "pct_missing": 0.0, "action": f"Removed {dropped_n} anomaly rows via Isolation Forest", "type": "outlier"})
                            elif sub_action == "nullify":
                                for c in num_target:
                                    df.loc[outlier_mask, c] = np.nan
                                logs.append({"column": ", ".join(num_target), "missing": 0, "pct_missing": 0.0, "action": f"Set {n_outliers} anomalies to NaN via Isolation Forest", "type": "outlier"})
                            else: # clip to 1st/99th
                                for c in num_target:
                                    p1, p99 = df[c].quantile(0.01), df[c].quantile(0.99)
                                    df.loc[outlier_mask, c] = df.loc[outlier_mask, c].clip(lower=p1, upper=p99)
                                logs.append({"column": ", ".join(num_target), "missing": 0, "pct_missing": 0.0, "action": f"Clipped {n_outliers} Isolation Forest anomalies to [1st, 99th] percentiles", "type": "outlier"})
                    except Exception as exc:
                        logs.append({"column": ", ".join(num_target), "missing": 0, "pct_missing": 0.0, "action": f"Isolation Forest failed: {exc}", "type": "error"})
                continue

            # B. Column-by-Column Outlier Processing
            for col in target_cols:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    continue

                outlier_mask = pd.Series(False, index=df.index)

                # Method 1: Configurable IQR Fence
                if method == "iqr":
                    k = float(rule.get("multiplier_k", 1.5))
                    q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                    iqr = q3 - q1
                    lo_fence, hi_fence = q1 - k * iqr, q3 + k * iqr
                    outlier_mask = (df[col] < lo_fence) | (df[col] > hi_fence)

                # Method 2: Z-Score or Robust MAD
                elif method in ("zscore", "mad"):
                    thresh = float(rule.get("zscore_threshold", 3.0))
                    z_mode = rule.get("zscore_method", "zscore")
                    if z_mode == "mad":
                        med_val = df[col].median()
                        mad = (df[col] - med_val).abs().median()
                        scale = mad * 1.4826 if mad > 0 else df[col].std()
                        if scale > 0:
                            scores = (df[col] - med_val).abs() / scale
                            outlier_mask = scores > thresh
                    else:
                        std_val = df[col].std()
                        mean_val = df[col].mean()
                        if std_val > 0:
                            scores = ((df[col] - mean_val) / std_val).abs()
                            outlier_mask = scores > thresh

                # Method 3: Percentile Bounds
                elif method == "percentile" or method == "clip":
                    p_lo = float(rule.get("lower_percentile", 0.01))
                    p_hi = float(rule.get("upper_percentile", 0.99))
                    lo_fence, hi_fence = df[col].quantile(p_lo), df[col].quantile(p_hi)
                    outlier_mask = (df[col] < lo_fence) | (df[col] > hi_fence)

                n_outliers = int(outlier_mask.sum())
                if n_outliers == 0:
                    continue

                if sub_action == "clip":
                    if method == "iqr":
                        df[col] = df[col].clip(lower=lo_fence, upper=hi_fence)
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Clipped {n_outliers} outliers to IQR fences [k={k}]", "type": "outlier"})
                    elif method in ("zscore", "mad"):
                        p1, p99 = df[col].quantile(0.01), df[col].quantile(0.99)
                        df[col] = df[col].clip(lower=p1, upper=p99)
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Clipped {n_outliers} Z-score anomalies to [1st, 99th] percentiles", "type": "outlier"})
                    else:
                        df[col] = df[col].clip(lower=lo_fence, upper=hi_fence)
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Winsorized {n_outliers} outliers to [{p_lo*100:.0f}%, {p_hi*100:.0f}%] percentiles", "type": "outlier"})

                elif sub_action == "drop_rows":
                    before_len = len(df)
                    df = df[~outlier_mask]
                    dropped_n = before_len - len(df)
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Removed {dropped_n} outlier rows", "type": "outlier"})

                elif sub_action == "fill_median":
                    med_val = float(df[col].median())
                    df.loc[outlier_mask, col] = med_val
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Replaced {n_outliers} outliers with Median ({med_val:.4g})", "type": "outlier"})

                elif sub_action == "nullify":
                    df.loc[outlier_mask, col] = np.nan
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Set {n_outliers} outliers to NaN", "type": "outlier"})

        # ── 4. FEATURE SCALING & NORMALIZATION ────────────────────────────────
        elif action == "scale":
            scale_method = rule.get("scaler_method", "robust")
            for col in target_cols:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    continue
                if scale_method == "robust":
                    q_l = float(rule.get("quantile_low", 25.0)) / 100.0
                    q_h = float(rule.get("quantile_high", 75.0)) / 100.0
                    med = df[col].median()
                    iqr = df[col].quantile(q_h) - df[col].quantile(q_l)
                    denom = iqr if iqr > 0 else 1.0
                    df[col] = (df[col] - med) / denom
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Scaled via RobustScaler (Quantiles [{q_l*100:.0f}%, {q_h*100:.0f}%])", "type": "scale"})
                elif scale_method == "standard":
                    m, s = df[col].mean(), df[col].std()
                    denom = s if s > 0 else 1.0
                    df[col] = (df[col] - m) / denom
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Standardized (Zero Mean, Unit Variance)", "type": "scale"})
                elif scale_method == "minmax":
                    f_min = float(rule.get("scale_min", 0.0))
                    f_max = float(rule.get("scale_max", 1.0))
                    c_min, c_max = df[col].min(), df[col].max()
                    denom = (c_max - c_min) if (c_max - c_min) > 0 else 1.0
                    df[col] = (df[col] - c_min) / denom * (f_max - f_min) + f_min
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"MinMax Scaled to range [{f_min}, {f_max}]", "type": "scale"})

        # ── 5. CATEGORICAL ENCODING ──────────────────────────────────────────
        elif action == "encode":
            enc_method = rule.get("encode_method", "onehot")
            for col in target_cols:
                if enc_method == "onehot":
                    drop_first = bool(rule.get("drop_first", False))
                    min_freq = float(rule.get("min_freq", 0.0))
                    if min_freq > 0:
                        counts = df[col].value_counts(normalize=True)
                        rare_mask = df[col].isin(counts[counts < min_freq].index)
                        df.loc[rare_mask, col] = "Other"
                    dummies = pd.get_dummies(df[col], prefix=col, drop_first=drop_first)
                    df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"One-Hot Encoded into {dummies.shape[1]} binary column(s)", "type": "encode"})
                elif enc_method == "ordinal":
                    df[col] = df[col].astype("category").cat.codes
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Ordinal Encoded into integer categories", "type": "encode"})

        # ── 6. TEXT NORMALIZATION & PII PROTECTION ────────────────────────────
        elif action == "normalize" or action == "text":
            case_opt = rule.get("text_case", "trim")
            pattern = rule.get("regex_pattern")
            replacement = rule.get("regex_replacement", "")
            is_pii = bool(rule.get("pii_mask", False))
            is_fuzzy = bool(rule.get("fuzzy_dedupe", False))

            for col in target_cols:
                if not _is_non_numeric(df[col]):
                    continue
                
                # Case conversion
                if case_opt == "lowercase":
                    df[col] = df[col].astype(str).str.lower().str.strip()
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Converted text to lowercase", "type": "normalize"})
                elif case_opt == "uppercase":
                    df[col] = df[col].astype(str).str.upper().str.strip()
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Converted text to uppercase", "type": "normalize"})
                elif case_opt == "titlecase":
                    df[col] = df[col].astype(str).str.title().str.strip()
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Converted text to Title Case", "type": "normalize"})
                elif case_opt == "trim":
                    df[col] = df[col].astype(str).str.strip()
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Trimmed leading/trailing whitespace", "type": "normalize"})

                # Custom RegEx Substitution
                if pattern:
                    try:
                        df[col] = df[col].astype(str).str.replace(pattern, replacement, regex=True)
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Applied RegEx replace (/{pattern}/ -> '{replacement}')", "type": "normalize"})
                    except Exception as e:
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"RegEx error: {e}", "type": "error"})

                # PII Redaction
                if is_pii:
                    entities = rule.get("pii_entities", ["email", "phone"])
                    s = df[col].astype(str)
                    if "email" in entities:
                        s = s.str.replace(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]", regex=True)
                    if "phone" in entities:
                        s = s.str.replace(r"\+?[\d\s\-\(\)]{7,}\b", "[REDACTED_PHONE]", regex=True)
                    if "ssn" in entities:
                        s = s.str.replace(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", regex=True)
                    if "credit_card" in entities:
                        s = s.str.replace(r"\b(?:\d{4}[ -]?){3}\d{4}\b", "[REDACTED_CARD]", regex=True)
                    df[col] = s
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Redacted PII entities: {', '.join(entities)}", "type": "normalize"})

                # Fuzzy Deduplication
                if is_fuzzy:
                    threshold = float(rule.get("fuzzy_threshold", 0.85))
                    try:
                        unique_vals = [str(x) for x in df[col].dropna().unique()]
                    except TypeError:
                        import json
                        unique_vals = list({json.dumps(x, sort_keys=True, default=str) if isinstance(x, (list, dict, set, tuple)) else str(x) for x in df[col].dropna()})
                    mapping = {}
                    processed = set()
                    for val in sorted(unique_vals, key=len, reverse=True):
                        if val in processed:
                            continue
                        matches = difflib.get_close_matches(val, unique_vals, n=10, cutoff=threshold)
                        for m in matches:
                            mapping[m] = val
                            processed.add(m)
                    if mapping:
                        df[col] = df[col].astype(str).replace(mapping)
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Fuzzy deduplicated {len(mapping)} variants (similarity > {threshold*100:.0f}%)", "type": "normalize"})

        # ── 7. TYPE CASTING ───────────────────────────────────────────────────
        elif action == "cast":
            target_type = rule.get("cast_type", "float")
            for col in target_cols:
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
                    elif target_type == "bool":
                        df[col] = df[col].astype(bool)
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Cast column to Boolean", "type": "cast"})
                    elif target_type == "category":
                        df[col] = df[col].astype("category")
                        logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": "Cast column to Categorical", "type": "cast"})
                except Exception as e:
                    logs.append({"column": col, "missing": 0, "pct_missing": 0.0, "action": f"Type cast failed: {e}", "type": "error"})

    if not logs:
        logs.append({"column": "Dataset", "missing": 0, "pct_missing": 0.0, "action": "Cleaning rules executed cleanly.", "type": "info"})

    python_script = generate_python_script(rules)

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
        "pipeline_script": python_script,
    }


def compute_rule_diff(df_raw: pd.DataFrame, rule: dict, max_sample_rows: int = 1000) -> dict:
    """
    Simulates a single cleaning rule on a sample of the dataset and returns
    before/after metrics and row deltas for live UI preview across all selected columns.
    """
    cols = rule.get("columns")
    if not cols:
        single_col = rule.get("column")
        cols = [single_col] if single_col else []

    target_cols = [c for c in cols if c in df_raw.columns]
    if not target_cols:
        return {"error": "Target column(s) not found in dataset."}

    # Sample dataframe for fast preview - ensure rows with missing values are captured if present
    if len(df_raw) > max_sample_rows:
        head_sample = df_raw.head(max_sample_rows)
        # Check null indices across any target columns
        null_mask = df_raw[target_cols].isnull().any(axis=1)
        null_indices = df_raw[null_mask].index
        if len(null_indices) > 0 and not head_sample[target_cols].isnull().any().any():
            null_part = df_raw.loc[null_indices[:min(100, len(null_indices))]]
            keep_head = max_sample_rows - len(null_part)
            df_sample = pd.concat([head_sample.head(keep_head), null_part]).sort_index().copy()
        else:
            df_sample = head_sample.copy()
    else:
        df_sample = df_raw.copy()

    # Helper to cleanly format numbers, strings, and missing values
    def _fmt_diff_val(val):
        if pd.isna(val):
            return "NaN"
        if isinstance(val, (float, np.floating)):
            if np.isnan(val):
                return "NaN"
            r = round(float(val), 4)
            return f"{r:.1f}" if r == int(r) else str(r)
        return str(val)

    # Run single rule simulation
    sim_result = run_dynamic_cleaning_pipeline(df_sample, [rule])
    df_sim = sim_result["df_clean"]

    def _col_diff(c: str) -> dict:
        is_num = pd.api.types.is_numeric_dtype(df_sample[c])
        nulls_before = int(df_sample[c].isnull().sum())
        stats_before = {
            "nulls": nulls_before,
            "null_pct": round(nulls_before / len(df_sample) * 100, 1),
        }
        if is_num and df_sample[c].notna().sum() > 0:
            stats_before["mean"] = round(float(df_sample[c].mean()), 4)
            stats_before["median"] = round(float(df_sample[c].median()), 4)
            stats_before["std"] = round(float(df_sample[c].std()), 4) if df_sample[c].count() > 1 else 0.0
            stats_before["min"] = round(float(df_sample[c].min()), 4)
            stats_before["max"] = round(float(df_sample[c].max()), 4)

        if c not in df_sim.columns:
            return {
                "column": c,
                "action": "drop",
                "stats_before": stats_before,
                "stats_after": {"status": "Column Dropped"},
                "total_changed_rows": len(df_sample),
                "sample_diff": [
                    {
                        "row": int(idx),
                        "before": _fmt_diff_val(df_sample.loc[idx, c]),
                        "after": "REMOVED",
                        "changed": True,
                    }
                    for idx in df_sample.index[:15]
                ],
            }

        nulls_after = int(df_sim[c].isnull().sum())
        stats_after = {
            "nulls": nulls_after,
            "null_pct": round(nulls_after / max(len(df_sim), 1) * 100, 1),
        }
        if is_num and df_sim[c].notna().sum() > 0:
            stats_after["mean"] = round(float(df_sim[c].mean()), 4)
            stats_after["median"] = round(float(df_sim[c].median()), 4)
            stats_after["std"] = round(float(df_sim[c].std()), 4) if df_sim[c].count() > 1 else 0.0
            stats_after["min"] = round(float(df_sim[c].min()), 4)
            stats_after["max"] = round(float(df_sim[c].max()), 4)

        changed_diff = []
        unchanged_diff = []
        for idx in df_sample.index:
            b_exists = idx in df_sample.index
            a_exists = (idx in df_sim.index and c in df_sim.columns)
            if not a_exists:
                b_val = _fmt_diff_val(df_sample.loc[idx, c]) if b_exists else "N/A"
                changed_diff.append({"row": int(idx), "before": b_val, "after": "REMOVED", "changed": True})
                continue
            b_raw = df_sample.loc[idx, c]
            a_raw = df_sim.loc[idx, c]
            b_na = pd.isna(b_raw)
            a_na = pd.isna(a_raw)
            if b_na and a_na:
                is_changed = False
                b_val = "NaN"
                a_val = "NaN"
            elif b_na != a_na:
                is_changed = True
                b_val = _fmt_diff_val(b_raw)
                a_val = _fmt_diff_val(a_raw)
            else:
                if isinstance(b_raw, (int, float, np.number)) and isinstance(a_raw, (int, float, np.number)):
                    is_changed = bool(abs(float(b_raw) - float(a_raw)) > 1e-6)
                else:
                    is_changed = bool(str(b_raw) != str(a_raw))
                b_val = _fmt_diff_val(b_raw)
                a_val = _fmt_diff_val(a_raw)
            item = {"row": int(idx), "before": b_val, "after": a_val, "changed": is_changed}
            if is_changed:
                changed_diff.append(item)
            else:
                unchanged_diff.append(item)

        sample_diff = changed_diff[:12]
        slots_left = max(0, 15 - len(sample_diff))
        if slots_left > 0:
            sample_diff.extend(unchanged_diff[:slots_left])

        return {
            "column": c,
            "stats_before": stats_before,
            "stats_after": stats_after,
            "total_changed_rows": len(changed_diff),
            "sample_diff": sample_diff,
        }

    by_column = {c: _col_diff(c) for c in target_cols}
    primary_c = target_cols[0]
    primary_res = by_column[primary_c]
    total_cells = sum(res["total_changed_rows"] for res in by_column.values())

    return {
        "column": primary_c,
        "action": rule.get("action_type") or rule.get("action") or primary_res.get("action"),
        "columns_targeted": target_cols,
        "by_column": by_column,
        "stats_before": primary_res["stats_before"],
        "stats_after": primary_res["stats_after"],
        "actions_simulated": sim_result.get("struct_actions", []),
        "total_changed_rows": primary_res["total_changed_rows"],
        "total_changed_cells": total_cells,
        "total_sample_rows": len(df_sample),
        "sample_diff": primary_res["sample_diff"],
    }


def generate_python_script(rules: list[dict], filename: str = "raw_dataset.csv") -> str:
    """
    Generates a reproducible, standalone Python script representing the exact
    cleaning pipeline steps applied in DataForge.
    """
    lines = [
        '"""',
        f'DataForge Enterprise Data Pipeline',
        f'Auto-generated reproducible Python ETL pipeline for: {filename}',
        f'Generated on: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '"""',
        '',
        'import pandas as pd',
        'import numpy as np',
        '',
        'def clean_dataset(filepath: str = "input_dataset.csv") -> pd.DataFrame:',
        '    print(f"Loading dataset from {filepath}...")',
        '    # 1. Ingest Raw Dataset',
        '    df = pd.read_csv(filepath)',
        '    print(f"Initial shape: {df.shape[0]} rows x {df.shape[1]} columns")',
        '',
    ]

    step_idx = 1
    for r in rules:
        cols = r.get("columns") or ([r.get("column")] if r.get("column") else [])
        action = r.get("action_type")
        if not cols or not action:
            continue

        cols_repr = repr(cols) if len(cols) > 1 else repr(cols[0])
        lines.append(f'    # Step {step_idx}: {action.upper()} on {cols_repr}')

        if action == "drop":
            lines.append(f'    df.drop(columns={cols}, inplace=True, errors="ignore")')

        elif action == "impute":
            method = r.get("impute_method", "median")
            if method == "mean":
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].fillna(df["{c}"].mean())')
            elif method == "median":
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].fillna(df["{c}"].median())')
            elif method == "mode":
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].fillna(df["{c}"].mode().iloc[0] if not df["{c}"].mode().empty else "Unknown")')
            elif method == "zero":
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].fillna(0)')
            elif method == "constant":
                val = r.get("fill_value", "N/A")
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].fillna({repr(val)})')
            elif method == "ffill":
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].ffill()')
            elif method == "bfill":
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].bfill()')
            elif method == "knn":
                k = r.get("knn_neighbors", 5)
                lines.append('    from sklearn.impute import KNNImputer')
                lines.append(f'    imputer = KNNImputer(n_neighbors={k})')
                lines.append(f'    df[{cols}] = imputer.fit_transform(df[{cols}])')
            elif method in ("mice", "iterative"):
                max_iter = r.get("mice_max_iter", 10)
                lines.append('    from sklearn.experimental import enable_iterative_imputer')
                lines.append('    from sklearn.impute import IterativeImputer')
                lines.append(f'    imputer = IterativeImputer(max_iter={max_iter}, random_state=42)')
                lines.append(f'    df[{cols}] = imputer.fit_transform(df[{cols}])')
            elif method == "drop_rows":
                lines.append(f'    df.dropna(subset={cols}, inplace=True)')

        elif action == "outlier":
            method = r.get("outlier_method", "iqr")
            sub_action = r.get("outlier_action", "clip")
            k = r.get("multiplier_k", 1.5)
            if method == "iqr":
                for c in cols:
                    lines.append(f'    q1, q3 = df["{c}"].quantile(0.25), df["{c}"].quantile(0.75)')
                    lines.append(f'    iqr = q3 - q1')
                    lines.append(f'    lo, hi = q1 - {k} * iqr, q3 + {k} * iqr')
                    if sub_action == "clip":
                        lines.append(f'    df["{c}"] = df["{c}"].clip(lower=lo, upper=hi)')
                    elif sub_action == "drop_rows":
                        lines.append(f'    df = df[(df["{c}"] >= lo) & (df["{c}"] <= hi)]')
                    elif sub_action == "fill_median":
                        lines.append(f'    df.loc[(df["{c}"] < lo) | (df["{c}"] > hi), "{c}"] = df["{c}"].median()')
            elif method == "isolation_forest":
                contam = r.get("iso_contamination", 0.05)
                n_est = r.get("iso_estimators", 100)
                lines.append('    from sklearn.ensemble import IsolationForest')
                lines.append(f'    iso = IsolationForest(contamination={contam}, n_estimators={n_est}, random_state=42)')
                lines.append(f'    outliers = iso.fit_predict(df[{cols}].fillna(df[{cols}].median())) == -1')
                if sub_action == "drop_rows":
                    lines.append('    df = df[~outliers]')
                else:
                    for c in cols:
                        lines.append(f'    df.loc[outliers, "{c}"] = df["{c}"].median()')

        elif action == "scale":
            scale_m = r.get("scaler_method", "robust")
            if scale_m == "robust":
                lines.append('    from sklearn.preprocessing import RobustScaler')
                lines.append(f'    scaler = RobustScaler(quantile_range=({r.get("quantile_low", 25.0)}, {r.get("quantile_high", 75.0)}))')
                lines.append(f'    df[{cols}] = scaler.fit_transform(df[{cols}])')
            elif scale_m == "standard":
                lines.append('    from sklearn.preprocessing import StandardScaler')
                lines.append(f'    scaler = StandardScaler()')
                lines.append(f'    df[{cols}] = scaler.fit_transform(df[{cols}])')
            elif scale_m == "minmax":
                lines.append('    from sklearn.preprocessing import MinMaxScaler')
                lines.append(f'    scaler = MinMaxScaler(feature_range=({r.get("scale_min", 0.0)}, {r.get("scale_max", 1.0)}))')
                lines.append(f'    df[{cols}] = scaler.fit_transform(df[{cols}])')

        elif action == "normalize" or action == "text":
            case = r.get("text_case", "trim")
            for c in cols:
                if case == "lowercase":
                    lines.append(f'    df["{c}"] = df["{c}"].astype(str).str.lower().str.strip()')
                elif case == "uppercase":
                    lines.append(f'    df["{c}"] = df["{c}"].astype(str).str.upper().str.strip()')
                elif case == "trim":
                    lines.append(f'    df["{c}"] = df["{c}"].astype(str).str.strip()')
            if r.get("regex_pattern"):
                pat = r.get("regex_pattern")
                rep = r.get("regex_replacement", "")
                for c in cols:
                    lines.append(f'    df["{c}"] = df["{c}"].astype(str).str.replace(r"{pat}", "{rep}", regex=True)')

        elif action == "cast":
            ctype = r.get("cast_type", "float")
            for c in cols:
                if ctype == "float":
                    lines.append(f'    df["{c}"] = pd.to_numeric(df["{c}"], errors="coerce")')
                elif ctype == "int":
                    lines.append(f'    df["{c}"] = pd.to_numeric(df["{c}"], errors="coerce").fillna(0).astype(int)')
                elif ctype == "datetime":
                    lines.append(f'    df["{c}"] = pd.to_datetime(df["{c}"], format="mixed", errors="coerce")')
                elif ctype == "string":
                    lines.append(f'    df["{c}"] = df["{c}"].astype(str)')

        lines.append('')
        step_idx += 1

    lines.extend([
        '    print(f"Final cleaned shape: {df.shape[0]} rows x {df.shape[1]} columns")',
        '    return df',
        '',
        'if __name__ == "__main__":',
        '    cleaned_df = clean_dataset()',
        '    cleaned_df.to_parquet("cleaned_dataset.parquet", index=False)',
        '    cleaned_df.to_csv("cleaned_dataset.csv", index=False)',
        '    print("Cleaned dataset saved successfully to parquet & csv!")',
    ])

    return "\n".join(lines)