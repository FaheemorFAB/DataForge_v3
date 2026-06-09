"""
Outlier Summary Insight
───────────────────────
Always fires when the dataset has at least 1 numeric column.
Sweeps ALL numeric columns with IQR fencing and gives an aggregate
cross-column outlier count. Different from AnomalyInsight which focuses
on one metric over time — this is a cross-sectional scan.
"""
import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class OutlierSummaryInsight(BaseInsight):
    name = "outlier_summary"

    IQR_FACTOR = 1.5

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) >= 1

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        try:
            metrics = schema["metrics"]
            num_df  = df[metrics].select_dtypes(include="number")
            if num_df.empty:
                return None

            col_results = []
            total_outlier_rows = set()

            for col in num_df.columns:
                series = num_df[col].dropna()
                if len(series) < 10:
                    continue
                q1, q3 = series.quantile(0.25), series.quantile(0.75)
                iqr    = q3 - q1
                lo, hi = q1 - self.IQR_FACTOR * iqr, q3 + self.IQR_FACTOR * iqr
                mask   = (series < lo) | (series > hi)
                n_out  = int(mask.sum())
                if n_out > 0:
                    pct = round(n_out / len(series) * 100, 1)
                    col_results.append({
                        "column":  col,
                        "n_outliers": n_out,
                        "pct":     pct,
                        "lo":      round(float(lo), 4),
                        "hi":      round(float(hi), 4),
                    })
                    # Track rows that are outliers in at least one column
                    total_outlier_rows.update(series.index[mask].tolist())

            if not col_results:
                # No outliers found — still a useful insight
                cols_word = "column" if num_df.shape[1] == 1 else "columns"
                description = (
                    f"No unusual values falling outside normal expected operational bounds were detected across {num_df.shape[1]} "
                    f"numeric {cols_word}. The data distribution appears clean and consistent."
                )
                return {
                    "title":       "Outlier Scan: No Anomalies Detected",
                    "description": description,
                    "importance":  0.25,
                    "type":        "outlier_summary",
                    "chart":       None,
                    "chart_data":  None,
                    "metric":      "",
                }

            col_results.sort(key=lambda x: x["n_outliers"], reverse=True)
            worst    = col_results[0]
            n_cols   = len(col_results)
            n_rows   = len(total_outlier_rows)
            row_pct  = round(n_rows / len(df) * 100, 1)

            worst_col = worst['column']
            worst_lo_fmt = self._format_precise(worst_col, worst['lo'])
            worst_hi_fmt = self._format_precise(worst_col, worst['hi'])
            description = (
                f"{n_rows:,} records ({row_pct}%) contain values falling outside normal expected operational bounds "
                f"across {n_cols} analyzed column(s). The most significant variance is in '{worst_col}', which contains {worst['n_outliers']:,} "
                f"unusual entries ({worst['pct']}%) falling outside the typical expected range of "
                f"[{worst_lo_fmt} to {worst_hi_fmt}]. "
                f"These extreme values can skew average results and inflate overall variance."
            )

            # Bar chart: outlier counts per column
            chart_data = {
                "labels":  [r["column"] for r in col_results[:10]],
                "values":  [r["n_outliers"] for r in col_results[:10]],
                "x_label": "Column",
                "y_label": "Outlier Count (IQR)",
            }

            return {
                "title":       "Cross-Column Outlier Summary",
                "description": description,
                "importance":  round(min(row_pct / 100 + 0.3, 0.88), 3),
                "type":        "outlier_summary",
                "chart":       "bar_chart",
                "chart_data":  chart_data,
                "metric":      worst["column"],
                "meta": {
                    "n_outlier_rows":   n_rows,
                    "outlier_row_pct":  row_pct,
                    "affected_columns": col_results,
                },
            }

        except Exception:
            return None
