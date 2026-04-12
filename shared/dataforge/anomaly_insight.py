"""
Anomaly Insight
───────────────
Detects unusual spikes or drops using z-score (|z| > 2.8).
If a date column exists, reports the date of the anomaly.
"""

import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class AnomalyInsight(BaseInsight):
    name = "anomaly"
    Z_THRESHOLD = 2.8

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) > 0

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        metric   = schema["metrics"][0]
        date_col = schema.get("date")

        try:
            series = df[metric].dropna()
            if len(series) < 10:
                return None

            mean = float(series.mean())
            std  = float(series.std())
            if std == 0:
                return None

            z_scores = (series - mean) / std
            anomalies = df.loc[z_scores.abs() > self.Z_THRESHOLD].copy()

            if anomalies.empty:
                return None

            # Most extreme anomaly
            z_abs = z_scores.abs()
            worst_idx = z_abs.idxmax()
            worst_z   = self._safe_float(z_abs[worst_idx])
            worst_val = self._safe_float(df.loc[worst_idx, metric])
            kind      = "spike" if df.loc[worst_idx, metric] > mean else "drop"

            # Date attribution
            date_str = ""
            if date_col and date_col in df.columns:
                raw_date = df.loc[worst_idx, date_col]
                try:
                    date_str = f" on {pd.to_datetime(raw_date).strftime('%b %d, %Y')}"
                except Exception:
                    date_str = f" (row {worst_idx})"

            n = len(anomalies)
            description = (
                f"Unusual {kind} detected in {metric}{date_str}. "
                f"Value was {round(worst_val, 2)} — {round(worst_z, 1)}σ from mean. "
                f"Total anomalies found: {n}."
            )

            return {
                "title":       f"{metric} Anomaly",
                "description": description,
                "importance":  self._clamp(worst_z / 6),
                "type":        "anomaly",
                "chart":       None,
                "chart_data":  None,
                "metric":      metric,
            }

        except Exception:
            return None
