"""
DataForge AI - Data Quality & Missing Value Auditor
Computes exact per-column null percentages, data completeness, and quality metrics.
Synchronizes 100% with the Clean & Fix tab and Explorer tab.
"""

from typing import Dict, Any, Optional
import pandas as pd
from dataforge.api.storage.manager import load


def audit_missing_values(df: pd.DataFrame, upload_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Audits missing values in the dataset.
    If upload_id is provided, cross-references raw and clean dataset states
    to guarantee exact alignment with the Clean & Fix and Explorer tabs.
    """
    # 1. Resolve raw and clean representations
    raw_df = None
    clean_df = None
    if upload_id:
        try:
            raw_df = load(upload_id, "df_raw")
            clean_df = load(upload_id, "df_clean")
        except Exception:
            pass

    # Use raw_df if available for missing value detection (matches Explorer and Clean & Fix)
    target_df = raw_df if raw_df is not None else df
    total_rows = len(target_df)
    total_cols = target_df.shape[1]
    total_cells = total_rows * total_cols

    null_counts = target_df.isnull().sum()
    missing_cols = null_counts[null_counts > 0].sort_values(ascending=False)
    total_missing = int(null_counts.sum())
    completeness_pct = round((1 - (total_missing / max(total_cells, 1))) * 100, 1)

    # 2. Case: Missing values detected
    if len(missing_cols) > 0:
        lines = []
        breakdown_records = []
        for col_name, missing_cnt in missing_cols.items():
            pct = round((missing_cnt / total_rows) * 100, 1)
            dtype_str = str(target_df[col_name].dtype)
            lines.append(f"- `{col_name}` ({dtype_str}): **{pct}% missing** ({missing_cnt:,} of {total_rows:,} rows)")
            breakdown_records.append({
                "column": col_name,
                "dtype": dtype_str,
                "missing": int(missing_cnt),
                "null_pct": pct,
                "quality": round(100.0 - pct, 1),
            })

        breakdown_text = "\n".join(lines)
        complete_cols_cnt = total_cols - len(missing_cols)

        clean_note = ""
        if clean_df is not None and int(clean_df.isnull().sum().sum()) == 0:
            clean_note = (
                "\n\n*Note: An active cleaned snapshot exists in workspace memory with all missing values imputed. "
                "The figures above reflect your original dataset as shown in the Explorer and Clean & Fix tabs.*"
            )

        answer = (
            f"### Missing Values & Data Health Audit\n\n"
            f"The dataset contains **{total_missing:,} missing cells** ({completeness_pct}% overall data completeness) "
            f"across **{len(missing_cols)} of {total_cols} columns** in {total_rows:,} records:\n\n"
            f"{breakdown_text}\n\n"
            f"The remaining **{complete_cols_cnt} columns** are 100% complete (0% missing).{clean_note}\n\n"
            f"Select a remediation strategy below or specify custom cleaning rules:"
        )

        insight = f"Identified {total_missing:,} missing cells across {len(missing_cols)} columns. Lowest completeness: {missing_cols.index[0]} ({round((missing_cols.iloc[0]/total_rows)*100, 1)}% null)."

        suggested_actions = [
            {"label": "1. Recommended (Median / Mode)", "query": "1"},
            {"label": "2. Drop Rows with Missing Values", "query": "2"},
            {"label": "3. Fill with Zero / Unknown", "query": "3"},
        ]

        return {
            "has_missing": True,
            "answer": answer,
            "insight": insight,
            "suggested_actions": suggested_actions,
            "missing_cols": breakdown_records,
            "total_missing": total_missing,
            "completeness_pct": completeness_pct,
        }

    # 3. Case: Zero missing values
    answer = (
        f"### Dataset Health: Complete\n\n"
        f"Your dataset contains **0 missing values** across all {total_cols} columns ({total_rows:,} rows). "
        f"Overall completeness is **100%**.\n\n"
        f"You can proceed with statistical profiling, anomaly detection, or predictive modeling."
    )
    insight = "Dataset is 100% complete with 0 missing values."
    suggested_actions = [
        {"label": "Check for Outliers", "query": "Check for outliers in the dataset"},
        {"label": "Check for Duplicate Rows", "query": "Remove duplicate rows"},
        {"label": "Analyze Correlations", "query": "Show correlation matrix"},
    ]

    return {
        "has_missing": False,
        "answer": answer,
        "insight": insight,
        "suggested_actions": suggested_actions,
        "missing_cols": [],
        "total_missing": 0,
        "completeness_pct": 100.0,
    }
