"""
Data Quality Insight
────────────────────
Always fires on any dataset (even 1 row, 1 column).
Reports missing value landscape across all columns — the most fundamental
honest insight possible about any dataset.
"""
import pandas as pd
from .base_insight import BaseInsight


class DataQualityInsight(BaseInsight):
    name = "data_quality"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(df.columns) > 0

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        try:
            total_cells = df.shape[0] * df.shape[1]
            if total_cells == 0:
                return None

            missing_per_col = df.isnull().sum()
            total_missing   = int(missing_per_col.sum())
            overall_pct     = round(total_missing / total_cells * 100, 1)

            # Columns with significant missing values
            bad_cols = missing_per_col[missing_per_col > 0].sort_values(ascending=False)
            worst    = bad_cols.head(5).to_dict()

            if total_missing == 0:
                description = (
                    f"This dataset is complete: {df.shape[0]:,} rows × {df.shape[1]} columns "
                    f"with zero missing values. No imputation required."
                )
                importance = 0.3
            else:
                worst_col  = bad_cols.index[0] if len(bad_cols) else "unknown"
                worst_pct  = round(bad_cols.iloc[0] / len(df) * 100, 1) if len(bad_cols) else 0
                n_bad_cols = int((missing_per_col > 0).sum())
                description = (
                    f"{overall_pct}% of values are missing across {n_bad_cols} column(s). "
                    f"Worst: '{worst_col}' is {worst_pct}% empty. "
                    f"High missing rates can bias ML models and skew aggregate statistics."
                )
                importance = min(0.9, overall_pct / 100 + 0.4)

            return {
                "title":       "Data Quality Assessment",
                "description": description,
                "importance":  round(importance, 3),
                "type":        "data_quality",
                "chart":       "bar_chart" if total_missing > 0 else None,
                "chart_data":  {
                    "labels": list(worst.keys()),
                    "values": [int(v) for v in worst.values()],
                    "x_label": "Column",
                    "y_label": "Missing Values",
                } if total_missing > 0 else None,
                "metric": "",
                "meta": {
                    "total_missing":   total_missing,
                    "overall_pct":     overall_pct,
                    "n_cols_affected": int((missing_per_col > 0).sum()),
                    "worst_columns":   {str(k): int(v) for k, v in worst.items()},
                },
            }

        except Exception:
            return None
