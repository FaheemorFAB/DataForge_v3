"""
Segment Comparison Insight
──────────────────────────
Compares mean metric values across segments.
Surfaces the biggest gap between best and worst segment.
"""

import pandas as pd
from .base_insight import BaseInsight


class SegmentInsight(BaseInsight):
    name = "segment"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        dims = schema.get("dimensions", [])
        # Need a dimension with 2–20 unique values (avoids ID columns)
        if not dims or not schema.get("metrics"):
            return False
        dim = dims[0]
        n = df[dim].nunique()
        return 2 <= n <= 20

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        dim    = schema["dimensions"][0]
        metric = schema["metrics"][0]

        try:
            seg_means = df.groupby(dim)[metric].mean().dropna().sort_values(ascending=False)
            if len(seg_means) < 2:
                return None

            best      = str(seg_means.index[0])
            worst     = str(seg_means.index[-1])
            best_val  = self._safe_float(seg_means.iloc[0])
            worst_val = self._safe_float(seg_means.iloc[-1])

            if worst_val == 0:
                return None

            ratio = round(best_val / worst_val, 1)

            labels = [str(i) for i in seg_means.index]
            values = [self._safe_float(v) for v in seg_means.values]

            best_fmt = self._format_precise(metric, best_val)
            worst_fmt = self._format_precise(metric, worst_val)
            description = (
                f"The '{best}' segment leads with an average '{metric}' of {best_fmt}, "
                f"which is {ratio}× higher than the '{worst}' segment (average {worst_fmt})."
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
