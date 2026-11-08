"""
Segment Comparison Insight
──────────────────────────
Compares mean metric values across segments.
Surfaces the biggest gap between best and worst segment.
"""

import pandas as pd
from .base_insight import BaseInsight
from dataforge.api.utils.helpers import canonicalize_series


class SegmentInsight(BaseInsight):
    name = "segment"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        dims = schema.get("dimensions", [])
        # Need a dimension with 2–20 unique values (avoids ID columns)
        if not dims or not schema.get("metrics"):
            return False
        dim = dims[0]
        n = canonicalize_series(df[dim]).nunique()
        return 2 <= n <= 20

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        dim    = schema["dimensions"][0]
        metric = schema["metrics"][0]

        try:
            s_dim = canonicalize_series(df[dim])
            temp_df = pd.DataFrame({"_dim": s_dim, "_metric": df[metric]}).dropna()
            seg_means = temp_df.groupby("_dim")["_metric"].mean().sort_values(ascending=False)
            if len(seg_means) < 2:
                return None

            best      = str(seg_means.index[0])
            worst     = str(seg_means.index[-1])
            best_val  = self._safe_float(seg_means.iloc[0])
            worst_val = self._safe_float(seg_means.iloc[-1])

            if worst_val == 0:
                return None

            diff_abs = best_val - worst_val
            pct_diff = round((diff_abs / abs(worst_val) * 100) if worst_val != 0 else 0.0, 1)

            labels = [str(i) for i in seg_means.index]
            values = [self._safe_float(v) for v in seg_means.values]

            best_fmt = self._format_precise(metric, best_val)
            worst_fmt = self._format_precise(metric, worst_val)
            if abs(pct_diff) < 5.0:
                description = (
                    f"The '{best}' segment leads with an average '{metric}' of {best_fmt}, "
                    f"slightly ahead of '{worst}' ({worst_fmt}, +{diff_abs:.2f} pts or +{pct_diff:.1f}%). "
                    f"Cohort performance across '{dim}' is closely clustered with minimal variance."
                )
            else:
                description = (
                    f"The '{best}' segment leads with an average '{metric}' of {best_fmt}, "
                    f"outperforming '{worst}' ({worst_fmt}) by {pct_diff:.1f}% (+{diff_abs:.2f} pts)."
                )

            return {
                "title":       f"{metric} by {dim}",
                "description": description,
                "importance":  self._clamp(min(ratio / 10, 0.9)),
                "type":        "segment",
                "chart":       "bar",
                "chart_data":  {"labels": labels, "values": values},
                "metric":      metric,
            }
        except Exception:
            return None
