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

            # Determine aggregation strategy based on intensive vs extensive metric
            from dataforge.api.routes.dashboard import is_intensive_metric
            is_int = is_intensive_metric(metric, ts[metric])
            agg = ts.groupby(ts[date_col].dt.to_period("D"))[metric].mean() if is_int else ts.groupby(ts[date_col].dt.to_period("D"))[metric].sum()

            if len(agg) < 2:
                return None

            first_w = float(agg.head(min(14, len(agg))).mean())
            last_w = float(agg.tail(min(14, len(agg))).mean())
            drift = last_w - first_w
            pct = round((drift / abs(first_w) * 100) if first_w != 0 else 0.0, 1)

            if abs(pct) < 0.2:  # < 0.2% — not worth surfacing
                return None

            direction_str = "upward" if drift > 0 else "downward"
            movement_str = "rising" if drift > 0 else "declining"

            # Build chart data — daily aggregated values
            chart_labels = [str(p) for p in agg.index]
            chart_values = [self._safe_float(v) for v in agg.values]

            if is_int:
                description = (
                    f"We observed an underlying {direction_str} trend in '{metric}', "
                    f"moving from {first_w:.1f} to {last_w:.1f} ({pct:+.1f}%) over the timeline."
                )
            else:
                description = (
                    f"We observed a steady {direction_str} trend in '{metric}', "
                    f"with total values {movement_str} from {first_w:,.0f} to {last_w:,.0f} ({pct:+.1f}%) over the timeline."
                )

            return {
                "title":       f"{metric} Trend",
                "description": description,
                "importance":  self._clamp(min(abs(pct) / 50.0 + 0.3, 0.95)),
                "type":        "trend",
                "chart":       "line",
                "chart_data":  {"labels": chart_labels[-30:], "values": chart_values[-30:]},
                "metric":      metric,
            }

        except Exception:
            return None
