"""
Contribution Insight
────────────────────
Shows what % of the total metric each dimension segment contributes.
Highlights dominant and lagging segments.
"""

import pandas as pd
from .base_insight import BaseInsight


class ContributionInsight(BaseInsight):
    name = "contribution"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return bool(schema.get("dimensions")) and bool(schema.get("metrics"))

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        # Use second dimension if available (first used by TopPerformer)
        dims   = schema["dimensions"]
        dim    = dims[1] if len(dims) > 1 else dims[0]
        metric = schema["metrics"][0]

        try:
            grouped = df.groupby(dim)[metric].sum().dropna().sort_values(ascending=False)
            total   = self._safe_float(grouped.sum())
            if total == 0 or len(grouped) < 2:
                return None

            contribs = (grouped / total * 100).round(1)
            top_name = str(contribs.index[0])
            top_pct  = self._safe_float(contribs.iloc[0])

            # Top 6 for chart
            top_n   = contribs.head(6)
            labels  = [str(i) for i in top_n.index]
            values  = [self._safe_float(v) for v in top_n.values]

            return {
                "title":       f"{metric} Breakdown by {dim}",
                "description": f"{top_name} accounts for {top_pct}% of total {metric}.",
                "importance":  self._clamp(top_pct / 100),
                "type":        "contribution",
                "chart":       "bar",
                "chart_data":  {"labels": labels, "values": values},
                "metric":      metric,
            }
        except Exception:
            return None
