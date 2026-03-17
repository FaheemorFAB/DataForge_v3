"""
Correlation Insight
───────────────────
Finds the strongest correlation between the primary metric and other numeric columns.
Threshold: |r| > 0.65
"""

import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class CorrelationInsight(BaseInsight):
    name = "correlation"

    THRESHOLD = 0.65

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) >= 2

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        metrics = schema["metrics"]
        target  = metrics[0]

        try:
            numeric_df = df[metrics].select_dtypes(include="number").dropna()
            if len(numeric_df) < 10:
                return None

            corr = numeric_df.corr()[target].drop(index=target, errors="ignore")
            corr = corr.dropna()

            if corr.empty:
                return None

            # Strongest absolute correlation
            strongest = corr.abs().idxmax()
            r         = self._safe_float(corr[strongest])

            if abs(r) < self.THRESHOLD:
                return None

            direction = "positively" if r > 0 else "negatively"
            strength  = "strongly" if abs(r) > 0.85 else "moderately"
            r_rounded = round(r, 2)

            return {
                "title":       f"{target} ↔ {strongest}",
                "description": (
                    f"{target} is {strength} {direction} correlated with "
                    f"{strongest} (r = {r_rounded})."
                ),
                "importance":  self._clamp(abs(r)),
                "type":        "correlation",
                "chart":       "scatter",
                "chart_data":  {
                    "x_label": strongest,
                    "y_label": target,
                    "x": [self._safe_float(v) for v in numeric_df[strongest].head(200).tolist()],
                    "y": [self._safe_float(v) for v in numeric_df[target].head(200).tolist()],
                },
                "metric":      target,
            }

        except Exception:
            return None
