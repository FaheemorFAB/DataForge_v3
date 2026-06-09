"""
Numeric Summary Insight
───────────────────────
Always fires when the dataset has at least 1 numeric column.
Reports the most variable and most stable numeric columns (by coefficient
of variation), plus the column with the highest absolute range.
These are honest, always-computable, statistically meaningful insights.
"""
import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class NumericSummaryInsight(BaseInsight):
    name = "numeric_summary"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) >= 1

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        try:
            metrics = schema["metrics"]
            num_df  = df[metrics].select_dtypes(include="number").dropna(how="all")
            if num_df.empty or num_df.shape[1] < 1:
                return None

            stats = num_df.describe().T
            stats["cv"]    = (stats["std"] / stats["mean"].replace(0, np.nan)).abs()
            stats["range"] = stats["max"] - stats["min"]

            valid = stats.dropna(subset=["cv"])
            if valid.empty:
                return None

            most_variable  = valid["cv"].idxmax()
            most_stable    = valid["cv"].idxmin()
            widest_range   = stats["range"].idxmax()

            cv_val     = round(float(valid.loc[most_variable, "cv"]) * 100, 1)
            stable_cv  = round(float(valid.loc[most_stable, "cv"]) * 100, 1)
            range_val  = round(float(stats.loc[widest_range, "range"]), 2)

            n_cols = len(valid)
            widest_range_fmt = self._format_precise(widest_range, range_val)
            description = (
                f"Across {n_cols} numeric column(s): '{most_variable}' is the most volatile "
                f"(volatility index of {cv_val}%), showing the highest relative spread. "
                f"Conversely, '{most_stable}' is the most consistent (volatility index of {stable_cv}%), "
                f"indicating steady, predictable values. '{widest_range}' has the widest absolute range "
                f"of {widest_range_fmt} from minimum to maximum."
            )

            # Bar chart of CV values
            chart_data = {
                "labels": valid.index.tolist(),
                "values": [round(float(v) * 100, 1) for v in valid["cv"]],
                "x_label": "Column",
                "y_label": "Coefficient of Variation (%)",
            }

            return {
                "title":       "Numeric Column Variability",
                "description": description,
                "importance":  round(min(cv_val / 200 + 0.35, 0.8), 3),
                "type":        "numeric_summary",
                "chart":       "bar_chart",
                "chart_data":  chart_data,
                "metric":      most_variable,
                "meta": {
                    "most_variable":  most_variable,
                    "cv_pct":         cv_val,
                    "most_stable":    most_stable,
                    "stable_cv_pct":  stable_cv,
                    "widest_range":   widest_range,
                    "range_value":    range_val,
                },
            }

        except Exception:
            return None
