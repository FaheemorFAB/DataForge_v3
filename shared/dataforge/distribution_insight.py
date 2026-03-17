"""
Distribution Insight
────────────────────
Summarises the spread and typical range of the primary metric.
"""

import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class DistributionInsight(BaseInsight):
    name = "distribution"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) > 0

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        metric = schema["metrics"][0]
        try:
            s = df[metric].dropna()
            if len(s) < 5:
                return None

            q1   = self._safe_float(s.quantile(0.25))
            q3   = self._safe_float(s.quantile(0.75))
            med  = self._safe_float(s.median())
            mean = self._safe_float(s.mean())
            std  = self._safe_float(s.std())

            # Skew flag
            skew = self._safe_float(s.skew())
            skew_desc = ""
            if abs(skew) > 1.0:
                skew_desc = " The distribution is right-skewed." if skew > 0 else " The distribution is left-skewed."

            # Histogram data
            hist, edges = np.histogram(s.dropna(), bins=20)
            labels = [f"{round(float(e), 1)}" for e in edges[:-1]]
            values = [int(v) for v in hist]

            return {
                "title":       f"{metric} Distribution",
                "description": (
                    f"Most {metric} values fall between {round(q1,2)} and {round(q3,2)} "
                    f"(median {round(med,2)}, mean {round(mean,2)}, std {round(std,2)}).{skew_desc}"
                ),
                "importance":  0.35,
                "type":        "distribution",
                "chart":       "histogram",
                "chart_data":  {"labels": labels, "values": values},
                "metric":      metric,
            }
        except Exception:
            return None
