"""
Change Detection Insight
────────────────────────
Compares the most recent period vs the previous period.
Works with or without a date column (falls back to row halves).
"""

import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class ChangeInsight(BaseInsight):
    name = "change"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) > 0 and len(df) >= 10

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        metric   = schema["metrics"][0]
        date_col = schema.get("date")

        try:
            if date_col and date_col in df.columns:
                ts = df.copy()
                ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
                ts = ts.sort_values(date_col).dropna(subset=[date_col])
                midpoint = len(ts) // 2
                recent   = ts.iloc[midpoint:][metric]
                previous = ts.iloc[:midpoint][metric]
            else:
                midpoint = len(df) // 2
                recent   = df.iloc[midpoint:][metric]
                previous = df.iloc[:midpoint][metric]

            prev_mean   = float(previous.mean())
            recent_mean = float(recent.mean())

            if prev_mean == 0:
                return None

            change_pct = (recent_mean - prev_mean) / abs(prev_mean) * 100

            if abs(change_pct) < 5:     # < 5% not worth surfacing
                return None

            direction = "up" if change_pct > 0 else "down"
            emoji     = "📈" if change_pct > 0 else "📉"

            return {
                "title":       f"{metric} Period Change",
                "description": (
                    f"{emoji} {metric} is {direction} {round(abs(change_pct), 1)}% "
                    f"in the recent period vs the previous period "
                    f"({round(recent_mean,2)} vs {round(prev_mean,2)})."
                ),
                "importance":  self._clamp(abs(change_pct) / 100),
                "type":        "change",
                "chart":       None,
                "chart_data":  None,
                "metric":      metric,
            }
        except Exception:
            return None
