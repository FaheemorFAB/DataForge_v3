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
            if abs(skew) < 0.3:
                skew_label = "approximately symmetric"
            elif 0.3 <= abs(skew) < 1.0:
                skew_label = "slightly right-skewed" if skew > 0 else "slightly left-skewed"
            else:
                skew_label = "strongly right-skewed" if skew > 0 else "strongly left-skewed"

            # ── Kurtosis (excess / Fisher) ────────────────────────────────────
            kurt = self._safe_float(s.kurtosis())   # excess kurtosis (normal = 0)
            if kurt > 1.0:
                kurt_label = "heavy-tailed (leptokurtic) — extreme values are more common than normal"
            elif kurt < -1.0:
                kurt_label = "light-tailed (platykurtic) — values cluster near the mean"
            else:
                kurt_label = "normal-like tail behaviour (mesokurtic)"

            # ── Coefficient of Variation ──────────────────────────────────────
            cv = round(abs(std / mean) * 100, 1) if mean != 0 else None
            cv_desc = f" Relative spread (CV): {cv}%." if cv is not None else ""

            # ── Histogram data ────────────────────────────────────────────────
            hist, edges = np.histogram(s, bins=min(20, len(s) // 5 or 5))
            labels = [f"{round(float(e), 2)}" for e in edges[:-1]]
            values = [int(v) for v in hist]

            description = (
                f"{metric} values range from P10={round(p10,2)} to P90={round(p90,2)} "
                f"(IQR {round(q1,2)}–{round(q3,2)}, mean {round(mean,2)}, std {round(std,2)}). "
                f"Distribution is {skew_label}; {kurt_label}.{cv_desc}"
            )

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
