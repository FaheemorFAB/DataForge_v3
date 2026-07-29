"""
Forecast Insight — Time-Series Predictive Analytics
═════════════════════════════════════════════════════
Auto-fires when a date column + ≥1 numeric column are detected.
Delegates to forecast_engine.run_forecast() and packages results
as a rich insight card that the frontend ForecastCard renders.
"""

from __future__ import annotations

import logging

import pandas as pd
import numpy as np

from .base_insight import BaseInsight
from .forecast_engine import run_forecast

log = logging.getLogger(__name__)

# Column name fragments that suggest ID / index columns — avoid forecasting these
_ID_FRAGMENTS = {"id", "_id", "uid", "uuid", "index", "key", "code",
                 "zip", "phone", "postal", "roll", "batch", "no", "num",
                 "number", "reg", "serial", "rank", "row"}


def _best_numeric_col(df: pd.DataFrame, schema: dict) -> str | None:
    """
    Pick the best numeric column to forecast.
    Priority:
      1. Schema-detected metrics (already filtered for quality).
      2. Any numeric column that is NOT id-like and has ≥50% non-null values.
    Returns None if nothing suitable is found.
    """
    # 1. Schema metrics first
    for m in schema.get("metrics", []):
        if m in df.columns:
            return m

    # 2. Fallback: any numeric column with enough non-null values
    for col in df.select_dtypes(include=[np.number]).columns:
        col_lower = col.lower()
        is_id = any(frag in col_lower for frag in _ID_FRAGMENTS)
        if is_id:
            continue
        non_null_ratio = df[col].notna().mean()
        if non_null_ratio >= 0.25:           # at least 25% non-null
            return col

    return None


class ForecastInsight(BaseInsight):
    name = "forecast"

    # ── Applicability ─────────────────────────────────────────────────────────
    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        has_date = bool(schema.get("date"))
        if not has_date:
            return False
        # Needs at least 8 rows with non-null dates AND a usable numeric column
        try:
            n_valid = pd.to_datetime(df[schema["date"]], errors="coerce").notna().sum()
            if int(n_valid) < 8:
                return False
        except Exception:
            return False
        return _best_numeric_col(df, schema) is not None

    # ── Analysis ──────────────────────────────────────────────────────────────
    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        date_col = schema["date"]
        metric   = _best_numeric_col(df, schema)
        if not metric:
            return None

        try:
            result = run_forecast(df, date_col, metric)

            if "error" in result:
                log.debug("[ForecastInsight] engine error: %s", result["error"])
                return None

            stats = result.get("summary_stats", {})
            direction = stats.get("direction", "stable")
            proj_growth = stats.get("projected_growth_pct", 0.0)
            mape = stats.get("avg_mape", 0.0)
            horizon = result.get("horizon", 30)
            freq = result.get("freq", "D")
            best_model = result.get("best_model", "Ensemble")

            freq_labels = {
                "D": "days", "W": "weeks", "M": "months",
                "Q": "quarters", "Y": "years", "H": "hours", "T": "minutes",
            }
            freq_label = freq_labels.get(freq, "periods")

            dir_word = {
                "upward": "grow", "downward": "decline", "stable": "remain stable"
            }.get(direction, "move")

            description = (
                f"Forecasting '{metric}' over the next {horizon} {freq_label}. "
                f"The model projects values to {dir_word} by "
                f"{abs(proj_growth):.1f}% (est. end value: "
                f"{self._format_value(metric, stats.get('proj_end_val', 0))}). "
                f"Ensemble accuracy (MAPE): {mape:.1f}% · Best model: {best_model}."
            )

            # Importance: stronger trend / larger dataset → higher importance
            n_pts = stats.get("n_points", 0)
            raw_imp = min(abs(proj_growth) / 50.0 + n_pts / 200.0, 1.0)

            return {
                "title":       f"{metric} Forecast",
                "description": description,
                "importance":  self._clamp(raw_imp, 0.55, 0.97),
                "type":        "forecast",
                "chart":       "forecast",
                "chart_data":  {
                    # Historical baseline
                    "labels":           result["historical_labels"],
                    "values":           result["historical_values"],
                    # Future predictions
                    "forecast_labels":  result["forecast_labels"],
                    "forecast_values":  result["forecast_values"],
                    "upper_95":         result["upper_95"],
                    "lower_95":         result["lower_95"],
                    "upper_80":         result["upper_80"],
                    "lower_80":         result["lower_80"],
                    # Decomposition
                    "decomposition":    result.get("decomposition"),
                    # Meta
                    "freq":             freq,
                    "horizon":          horizon,
                    "model_mapes":      result.get("model_mapes", {}),
                    "best_model":       best_model,
                    "summary_stats":    stats,
                },
                "metric":      metric,
            }

        except Exception as exc:
            log.exception("[ForecastInsight] Unhandled error: %s", exc)
            return None
