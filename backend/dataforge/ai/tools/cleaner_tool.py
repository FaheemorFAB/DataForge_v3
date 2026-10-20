"""
CleanerAgent Toolkit - Connects AI to DataForge DataCleaner engine.
Provides full feature parity with Clean & Fix tab:
  • Multi-column dynamic imputation (median, mean, mode, zero, constant)
  • Outlier clipping and dropping (IQR, Z-Score)
  • Column dropping and type casting
  • 1-Click Snapshot Undo/Rollback
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np

from dataforge.api.storage.manager import load, save
from dataforge.data_cleaner import run_cleaning_pipeline, run_dynamic_cleaning_pipeline

logger = logging.getLogger(__name__)

def parse_clean_command(query: str, df: pd.DataFrame) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Parses conversational user instructions into structured dynamic cleaning rules.
    Returns (rules, strategy_name).
    """
    q_lower = query.lower().strip()
    rules: List[Dict[str, Any]] = []

    # 1. Rollback / Undo Check
    if q_lower in ("undo", "rollback", "revert", "undo cleaning", "revert cleaning"):
        return None, "undo"

    # 2. Global Option Shortcuts
    if q_lower in ("1", "option 1", "recommended") or "median and mode" in q_lower or "fill with typical" in q_lower:
        num_cols = df.select_dtypes(include=np.number).columns.tolist()
        cat_cols = [c for c in df.columns if c not in num_cols]
        if num_cols:
            rules.append({"columns": num_cols, "action_type": "impute", "impute_method": "median"})
        if cat_cols:
            rules.append({"columns": cat_cols, "action_type": "impute", "impute_method": "mode"})
        return rules, "recommended_impute"

    if q_lower in ("2", "option 2", "remove rows", "drop rows") or "drop rows with missing" in q_lower or "delete missing rows" in q_lower:
        # Drop rows where any cell is null
        return [{"columns": df.columns.tolist(), "action_type": "drop_na_rows"}], "drop_na_rows"

    if q_lower in ("3", "option 3", "zero and unknown") or "fill with zero" in q_lower or "fill missing values with 0" in q_lower:
        num_cols = df.select_dtypes(include=np.number).columns.tolist()
        cat_cols = [c for c in df.columns if c not in num_cols]
        if num_cols:
            rules.append({"columns": num_cols, "action_type": "impute", "impute_method": "constant", "fill_value": 0})
        if cat_cols:
            rules.append({"columns": cat_cols, "action_type": "impute", "impute_method": "constant", "fill_value": "Unknown"})
        return rules, "zero_unknown"

    # 3. Column-specific Dropping
    drop_col_match = re.search(r"\b(?:drop|remove|delete)\s+(?:column|col|feature)?\s*[`'\"]?([a-zA-Z0-9_]+)[`'\"]?", q_lower)
    if drop_col_match:
        target_name = drop_col_match.group(1)
        for c in df.columns:
            if c.lower() == target_name or target_name in c.lower():
                rules.append({"columns": [c], "action_type": "drop"})
                return rules, f"drop_col_{c}"

    # 4. Column-specific Imputation
    impute_match = re.search(r"\b(?:impute|fill)\s+[`'\"]?([a-zA-Z0-9_]+)[`'\"]?\s+(?:with|using)?\s*(median|mean|mode|zero|0|unknown|constant)?", q_lower)
    if impute_match:
        target_name = impute_match.group(1)
        method = impute_match.group(2) or "median"
        if method in ("0", "zero"):
            method = "constant"
            fill_val = 0
        elif method == "unknown":
            method = "constant"
            fill_val = "Unknown"
        else:
            fill_val = None

        for c in df.columns:
            if c.lower() == target_name or target_name in c.lower():
                rule = {"columns": [c], "action_type": "impute", "impute_method": method}
                if fill_val is not None:
                    rule["fill_value"] = fill_val
                rules.append(rule)
                return rules, f"impute_{c}_{method}"

    # 5. Outlier Clipping
    outlier_match = re.search(r"\b(?:clip|cap|handle)\s+outliers?\s+in\s+[`'\"]?([a-zA-Z0-9_]+)[`'\"]?", q_lower)
    if outlier_match:
        target_name = outlier_match.group(1)
        for c in df.columns:
            if c.lower() == target_name or target_name in c.lower():
                rules.append({"columns": [c], "action_type": "outlier", "outlier_method": "iqr", "outlier_action": "clip"})
                return rules, f"clip_outliers_{c}"

    # 6. Type Casting
    cast_match = re.search(r"\b(?:cast|convert)\s+[`'\"]?([a-zA-Z0-9_]+)[`'\"]?\s+to\s+(int|integer|float|number|datetime|date|string|str|bool|boolean)", q_lower)
    if cast_match:
        target_name = cast_match.group(1)
        target_type = cast_match.group(2)
        if target_type in ("integer", "int"):
            target_type = "int"
        elif target_type in ("number", "float"):
            target_type = "float"
        elif target_type in ("date", "datetime"):
            target_type = "datetime"
        for c in df.columns:
            if c.lower() == target_name or target_name in c.lower():
                rules.append({"columns": [c], "action_type": "cast", "cast_type": target_type})
                return rules, f"cast_{c}_{target_type}"

    # 7. Deduplication
    if "duplicate" in q_lower or "dedup" in q_lower:
        rules.append({"columns": df.columns.tolist(), "action_type": "drop_duplicates"})
        return rules, "drop_duplicates"

    return (rules if rules else None), None

def clean_dataset_tool(
    upload_id: str,
    rules: Optional[List[Dict[str, Any]]] = None,
    query: Optional[str] = None,
    auto_clean: bool = True,
    df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Cleans the dataset associated with upload_id using DataForge's automated or dynamic cleaning engines.
    Saves a pre-clean snapshot for 1-click rollback, and saves the cleaned DataFrame to cache.
    """
    if df is None:
        df = load(upload_id, "df_clean")
    if df is None:
        df = load(upload_id, "df_raw")
    if df is None:
        return {"ok": False, "error": f"No dataset found for upload_id: {upload_id}"}

    # If query is provided, check for undo or parse specific rules
    parsed_rules = None
    strategy = None
    if query:
        parsed_rules, strategy = parse_clean_command(query, df)
        if strategy == "undo":
            pre_df = load(upload_id, "df_preclean")
            if pre_df is not None:
                save(upload_id, "df_clean", pre_df)
                try:
                    from dataforge.api.routes.workspace import df_profile
                    from dataforge.db import db_get
                    up_row = db_get("uploads", upload_id) or {}
                    c_prof = df_profile(pre_df, up_row.get("filename", "dataset.csv"))
                    save(upload_id, "clean_profile", c_prof)
                except Exception as p_err:
                    logger.warning("[CleanerAgent] Undo profile regenerate notice: %s", p_err)
                return {
                    "ok": True,
                    "is_undo": True,
                    "actions": ["Reverted dataset to snapshot before last cleaning operation"],
                    "stats": {
                        "original_rows": len(df),
                        "cleaned_rows": len(pre_df),
                        "original_cols": df.shape[1],
                        "cleaned_cols": pre_df.shape[1],
                    },
                    "message": "Dataset successfully reverted to previous snapshot.",
                }
            else:
                return {"ok": False, "error": "No previous dataset snapshot found to undo."}

    effective_rules = rules or parsed_rules

    try:
        # Save snapshot for 1-click rollback
        try:
            save(upload_id, "df_preclean", df.copy())
        except Exception as s_err:
            logger.warning("[CleanerAgent] Snapshot save notice: %s", s_err)

        initial_nulls = int(df.isnull().sum().sum())
        initial_cells = int(df.shape[0] * df.shape[1])
        initial_quality = round((1 - (initial_nulls / max(initial_cells, 1))) * 100, 1)

        if effective_rules and len(effective_rules) > 0:
            # Custom handling for drop_na_rows and drop_duplicates
            cleaned_df = df.copy()
            actions = []
            for r in effective_rules:
                action_t = r.get("action_type")
                if action_t == "drop_na_rows":
                    before_cnt = len(cleaned_df)
                    cleaned_df = cleaned_df.dropna()
                    actions.append(f"Dropped {before_cnt - len(cleaned_df):,} rows with missing values")
                elif action_t == "drop_duplicates":
                    before_cnt = len(cleaned_df)
                    cleaned_df = cleaned_df.drop_duplicates()
                    actions.append(f"Removed {before_cnt - len(cleaned_df):,} duplicate rows")
                else:
                    res_dyn = run_dynamic_cleaning_pipeline(cleaned_df, [r])
                    cleaned_df = res_dyn.get("df_clean", res_dyn.get("df", cleaned_df))
                    actions.extend(res_dyn.get("struct_actions", res_dyn.get("logs", [f"Applied {action_t}"])))

            stats = {
                "original_rows": len(df),
                "cleaned_rows": len(cleaned_df),
                "original_cols": df.shape[1],
                "cleaned_cols": cleaned_df.shape[1],
            }
        else:
            logger.info("[CleanerAgent] Executing automated 1-click cleaning pipeline.")
            res = run_cleaning_pipeline(df)
            cleaned_df = res["df_clean"]
            actions = res.get("struct_actions", [])
            stats = res.get("stats", {})

        # Compute post-clean quality score
        final_nulls = int(cleaned_df.isnull().sum().sum())
        final_cells = int(cleaned_df.shape[0] * cleaned_df.shape[1])
        final_quality = round((1 - (final_nulls / max(final_cells, 1))) * 100, 1)

        stats["initial_quality"] = initial_quality
        stats["final_quality"] = final_quality
        stats["initial_nulls"] = initial_nulls
        stats["final_nulls"] = final_nulls

        # Persist updated clean dataframe to workspace storage cache
        try:
            save(upload_id, "df_clean", cleaned_df)
            from dataforge.api.routes.workspace import df_profile
            from dataforge.db import db_get
            up_row = db_get("uploads", upload_id) or {}
            c_prof = df_profile(cleaned_df, up_row.get("filename", "dataset.csv"))
            save(upload_id, "clean_profile", c_prof)

            # Record AI action history for the presentation & report
            ai_history = load(upload_id, "ai_cleaning_actions") or []
            ai_history.append({
                "timestamp": pd.Timestamp.now().isoformat(),
                "agent": "CleanerAgent",
                "actions": actions,
                "initial_quality": initial_quality,
                "final_quality": final_quality,
                "rows_before": len(df),
                "rows_after": len(cleaned_df),
            })
            save(upload_id, "ai_cleaning_actions", ai_history)
        except Exception as s_err:
            logger.warning("[CleanerAgent] Clean dataset save notice: %s", s_err)

        return {
            "ok": True,
            "actions": actions,
            "stats": stats,
            "message": f"Dataset cleaned: {stats.get('cleaned_rows', len(cleaned_df))} rows remaining. Quality: {initial_quality}% -> {final_quality}%.",
        }
    except Exception as exc:
        logger.error("[CleanerAgent] Cleaning error: %s", exc)
        return {"ok": False, "error": str(exc)}

