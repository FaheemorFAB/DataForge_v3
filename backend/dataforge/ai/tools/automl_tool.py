"""
AutoMLAgent Toolkit - Provides predictive modeling, task formulation, and feature signal insights.
"""

import logging
from typing import Optional, Dict, Any
import pandas as pd

from dataforge.api.storage.manager import load
from dataforge.automl_trainer import _detect_task, _detect_imbalance, analyze_features_for_target

logger = logging.getLogger(__name__)

def analyze_automl_tool(
    upload_id: str,
    target_col: str,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Inspects target variable, automatically infers machine learning task type,
    checks class balance, and ranks features by predictive signal.
    """
    if df is None:
        df = load(upload_id, "df_clean")
        if df is None:
            df = load(upload_id, "df_raw")

    if df is None:
        return {"ok": False, "error": f"Dataset {upload_id} not loaded."}

    # Match column case-insensitively if needed
    matched_col = None
    for c in df.columns:
        if c.lower() == target_col.lower():
            matched_col = c
            break

    if not matched_col:
        return {
            "ok": False,
            "error": f"Target column '{target_col}' not found in dataset columns: {list(df.columns[:10])}",
        }

    try:
        y = df[matched_col].dropna()
        task_type = _detect_task(y)
        imbalance_meta = _detect_imbalance(y) if task_type == "classification" else {}
        feature_signals = analyze_features_for_target(df, matched_col)

        recommended_models = (
            ["LightGBM Classifier", "XGBoost", "Random Forest", "Logistic Regression"]
            if task_type == "classification"
            else ["LightGBM Regressor", "XGBoost", "Random Forest", "Ridge"]
        )

        return {
            "ok": True,
            "target": matched_col,
            "task": task_type,
            "imbalance": imbalance_meta,
            "top_features": feature_signals.get("feature_importance", [])[:5] if isinstance(feature_signals, dict) else [],
            "recommended_models": recommended_models,
            "message": f"Inferred {task_type.upper()} problem for '{matched_col}'. Top signal models: {', '.join(recommended_models[:2])}.",
        }
    except Exception as exc:
        logger.error("[AutoMLAgent] Failed to analyze target: %s", exc)
        return {"ok": False, "error": str(exc)}
