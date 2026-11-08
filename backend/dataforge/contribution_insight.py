"""
Contribution Insight
────────────────────
Shows what % of the total metric each dimension segment contributes.
Highlights dominant and lagging segments.
"""

import pandas as pd
from .base_insight import BaseInsight
from dataforge.api.utils.helpers import canonicalize_series


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
            s_dim = canonicalize_series(df[dim])
            temp_df = pd.DataFrame({"_dim": s_dim, "_metric": df[metric]}).dropna()
            grouped = temp_df.groupby("_dim")["_metric"].sum().sort_values(ascending=False)
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

            top_val_abs = self._safe_float(grouped.iloc[0])
            is_prot = dim in schema.get("protected_columns", [])

            if is_prot:
                description = (
                    f"'{top_name}' represents {top_pct}% ({self._format_precise(metric, top_val_abs)}) "
                    f"of the total '{metric}' ({self._format_precise(metric, total)}) across demographic categories in '{dim}'. "
                    f"(Note: observational segment distribution, not a causal driver)."
                )
            else:
                description = (
                    f"'{top_name}' accounts for {top_pct}% ({self._format_precise(metric, top_val_abs)}) "
                    f"of the total '{metric}' ({self._format_precise(metric, total)}) across segments in '{dim}'."
                )

            return {
                "title":       f"{metric} Breakdown by {dim}",
                "description": description,
                "importance":  self._clamp(top_pct / 100),
                "type":        "contribution",
                "chart":       "bar",
                "chart_data":  {"labels": labels, "values": values, "dim": dim},
                "dimension":   dim,
                "metric":      metric,
                "columns_involved": [dim, metric],
                "is_protected": is_prot,
            }
        except Exception:
            return None
