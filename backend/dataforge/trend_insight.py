"""
Trend Insight
─────────────
Detects whether a numeric metric is growing or declining over time.
Requires a date column and at least one numeric column.
"""

import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class TrendInsight(BaseInsight):
    name = "trend"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return bool(schema.get("date")) and len(schema.get("metrics", [])) > 0

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        date_col = schema["date"]
        metric   = schema["metrics"][0]          # primary metric

        try:
            ts = df.copy()
            ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
            ts = ts.dropna(subset=[date_col])
            ts = ts.sort_values(date_col)

            if len(ts) < 4:
                return None

            # Compute overall trend via pct_change mean
            agg = ts.groupby(ts[date_col].dt.to_period("D"))[metric].sum()
            changes = agg.pct_change().dropna()
            if changes.empty:
                return None

            trend = float(changes.mean())
            if abs(trend) < 0.005:          # < 0.5% — not worth surfacing
                return None

            direction_str = "upward" if trend > 0 else "downward"
            movement_str = "increasing" if trend > 0 else "decreasing"
            pct       = round(abs(trend) * 100, 1)

            # Build chart data — daily aggregated values
            chart_labels = [str(p) for p in agg.index]
            chart_values = [self._safe_float(v) for v in agg.values]

            description = (
                f"We observed a steady {direction_str} trend in '{metric}', "
                f"with values {movement_str} by an average of {pct}% per period over the timeline."
            )

            return {
                "title":       f"{metric} Trend",
                "description": description,
                "importance":  self._clamp(abs(trend) * 2),
                "type":        "trend",
                "chart":       "line",
                "chart_data":  {"labels": chart_labels[-30:], "values": chart_values[-30:]},
                "metric":      metric,
            }

        except Exception:
            return None
