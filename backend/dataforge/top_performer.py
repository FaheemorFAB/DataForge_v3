"""
Top Performer Insight
─────────────────────
Finds the highest- and lowest-performing category for the primary metric.
Requires at least one categorical dimension and one numeric metric.
"""

import pandas as pd
from .base_insight import BaseInsight


class TopPerformerInsight(BaseInsight):
    name = "top_performer"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return bool(schema.get("dimensions")) and bool(schema.get("metrics"))

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        dim    = schema["dimensions"][0]
        metric = schema["metrics"][0]

        try:
            grouped = df.groupby(dim)[metric].sum().dropna().sort_values(ascending=False)
            if len(grouped) < 2:
                return None

            top_name  = str(grouped.index[0])
            top_val   = self._safe_float(grouped.iloc[0])
            total_val = self._safe_float(grouped.sum())

            if total_val == 0:
                return None

            pct = round(top_val / total_val * 100, 1)

            # Top-N for chart
            top_n  = grouped.head(8)
            labels = [str(i) for i in top_n.index]
            values = [self._safe_float(v) for v in top_n.values]

            top_val_fmt = self._format_precise(metric, top_val)
            total_val_fmt = self._format_precise(metric, total_val)
            is_prot = dim in schema.get("protected_columns", [])

            if is_prot:
                description = (
                    f"In demographic segment '{dim}', '{top_name}' represents "
                    f"{pct}% ({top_val_fmt}) of the total '{metric}' ({total_val_fmt}). "
                    f"(Note: observational segment distribution, not a causal driver)."
                )
                title = f"Segment Distribution: {dim}"
            else:
                description = (
                    f"The highest share category in '{dim}' is '{top_name}', which accounts for "
                    f"{pct}% ({top_val_fmt}) of the total '{metric}' ({total_val_fmt})."
                )
                title = f"Category Share: {dim}"

            return {
                "title":       title,
                "description": description,
                "importance":  self._clamp(pct / 100 * 1.5),
                "type":        "ranking",
                "chart":       "bar",
                "chart_data":  {"labels": labels, "values": values, "dim": dim},
                "dimension":   dim,
                "metric":      metric,
            }

        except Exception:
            return None
