"""
Distribution Insight — Skewness + Kurtosis + Plain-English Labels (Improved 2026-04-29)
─────────────────────────────────────────────────────────────────────────────────────────
Additions over original:
  - Kurtosis with interpretation ("heavy-tailed", "light-tailed", "normal-like")
  - Richer skewness labels: "strongly right-skewed", "slightly left-skewed", etc.
  - Coefficient of Variation (CV) to describe relative spread
  - Percentile band (P10–P90) for a tighter central-range view
  - All new stats included in chart_data.meta for frontend display
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
            p10  = self._safe_float(s.quantile(0.10))
            p90  = self._safe_float(s.quantile(0.90))
            med  = self._safe_float(s.median())
            mean = self._safe_float(s.mean())
            std  = self._safe_float(s.std())

            # ── Skewness ──────────────────────────────────────────────────────
            skew = self._safe_float(s.skew())
            # Skewness translation
            if abs(skew) < 0.3:
                skew_desc = "distributed relatively symmetrically around the average"
            elif 0.3 <= abs(skew) < 1.0:
                skew_desc = "slightly concentrated towards the lower end with a tail of high values" if skew > 0 else "slightly concentrated towards the higher end with a tail of low values"
            else:
                skew_desc = "strongly concentrated at lower levels with a long tail of very high values" if skew > 0 else "strongly concentrated at higher levels with a long tail of very low values"

            # Kurtosis translation
            kurt = self._safe_float(s.kurtosis())
            if kurt > 1.0:
                kurt_desc = "exhibits a high frequency of extreme outlier values (heavy-tailed)"
            elif kurt < -1.0:
                kurt_desc = "values are uniformly spread out with very low outlier risk (light-tailed)"
            else:
                kurt_desc = "exhibits moderate outlier behavior similar to a standard bell curve"

            # Format values
            p10_fmt = self._format_precise(metric, p10)
            p90_fmt = self._format_precise(metric, p90)
            q1_fmt = self._format_precise(metric, q1)
            q3_fmt = self._format_precise(metric, q3)
            mean_fmt = self._format_precise(metric, mean)
            std_fmt = self._format_precise(metric, std)

            description = (
                f"The central 80% of '{metric}' values fall within {p10_fmt} and {p90_fmt}, "
                f"while the middle 50% range from {q1_fmt} to {q3_fmt} (averaging {mean_fmt} with a standard deviation of {std_fmt}). "
                f"The distribution is {skew_desc}, and {kurt_desc}."
            )
            if cv is not None:
                description += f" The volatility index (relative spread) is {cv}%."

            # ── Histogram data ────────────────────────────────────────────────
            hist, edges = np.histogram(s, bins=min(20, len(s) // 5 or 5))
            labels = [f"{round(float(e), 2)}" for e in edges[:-1]]
            values = [int(v) for v in hist]

            return {
                "title":       f"{metric} Distribution",
                "description": description,
                "importance":  0.38,
                "type":        "distribution",
                "chart":       "histogram",
                "chart_data":  {
                    "labels": labels,
                    "values": values,
                    "meta": {
                        "mean":       round(mean, 4),
                        "median":     round(med, 4),
                        "std":        round(std, 4),
                        "skewness":   round(skew, 4),
                        "kurtosis":   round(kurt, 4),
                        "skew_label": skew_label,
                        "kurt_label": kurt_label,
                        "q1":         round(q1, 4),
                        "q3":         round(q3, 4),
                        "p10":        round(p10, 4),
                        "p90":        round(p90, 4),
                        "cv_pct":     cv,
                    },
                },
                "metric":      metric,
            }
        except Exception:
            return None
