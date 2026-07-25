"""
Correlation Insight — All-Pairs Scan + Matrix (Improved 2026-04-29)
────────────────────────────────────────────────────────────────────
Previous behaviour: only compared metrics[0] against each other column.
Improved behaviour:
  - Scans ALL numeric column pairs for the globally strongest correlation.
  - Returns a full correlation_matrix in chart_data for frontend heatmap rendering.
  - Threshold: |r| > 0.55 (lowered from 0.65 to surface more real-world signals).
  - Distinguishes "strong" (|r|>0.85), "moderate" (|r|>0.65), "weak" (|r|>0.55).
"""

import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class CorrelationInsight(BaseInsight):
    name = "correlation"

    THRESHOLD_WEAK     = 0.55
    THRESHOLD_MODERATE = 0.65
    THRESHOLD_STRONG   = 0.85

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) >= 2

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        metrics = schema["metrics"]

        try:
            numeric_df = df[metrics].select_dtypes(include="number").dropna()
            if len(numeric_df) < 10 or numeric_df.shape[1] < 2:
                return None

            # Full correlation matrix
            try:
                corr_matrix = numeric_df.corr(numeric_only=True).round(4)
            except TypeError:
                corr_matrix = numeric_df.corr().round(4)

            # ── All-pairs scan ─────────────────────────────────────────────────
            cols      = corr_matrix.columns.tolist()
            best_r    = 0.0
            best_pair = (cols[0], cols[1])

            for i, col_a in enumerate(cols):
                for col_b in cols[i + 1:]:
                    r = corr_matrix.loc[col_a, col_b]
                    if abs(r) > abs(best_r):
                        best_r    = float(r)
                        best_pair = (col_a, col_b)

            if abs(best_r) < self.THRESHOLD_WEAK:
                return None

            col_a, col_b = best_pair
            direction    = "positively" if best_r > 0 else "negatively"

            if abs(best_r) >= self.THRESHOLD_STRONG:
                strength = "strongly"
            elif abs(best_r) >= self.THRESHOLD_MODERATE:
                strength = "moderately"
            else:
                strength = "weakly"

            # ── Correlation matrix for frontend heatmap ─────────────────────
            matrix_cols  = corr_matrix.columns.tolist()
            matrix_rows  = []
            for row_col in matrix_cols:
                matrix_rows.append({
                    "column": row_col,
                    **{c: (None if pd.isna(corr_matrix.loc[row_col, c])
                           else round(float(corr_matrix.loc[row_col, c]), 3))
                       for c in matrix_cols}
                })

            # ── Scatter data for the best pair ──────────────────────────────
            pair_df = numeric_df[[col_a, col_b]].dropna()
            scatter_x = [self._safe_float(v) for v in pair_df[col_a].head(300).tolist()]
            scatter_y = [self._safe_float(v) for v in pair_df[col_b].head(300).tolist()]

            alignment_pct = round(abs(best_r) * 100, 1)
            likelihood_str = "highly likely" if abs(best_r) >= 0.65 else "somewhat likely"
            direction_str = "positive" if best_r > 0 else "negative"
            strength_str = "strong" if abs(best_r) >= 0.85 else "moderate" if abs(best_r) >= 0.65 else "weak"
            total_sig_pairs = sum(1 for i, a in enumerate(cols) for b in cols[i+1:] if abs(corr_matrix.loc[a, b]) >= self.THRESHOLD_WEAK)
            
            description = (
                f"A {strength_str} {direction_str} relationship was detected between '{col_a}' and '{col_b}' "
                f"({alignment_pct}% alignment). Changes in one are {likelihood_str} to align with changes in the other. "
                f"A scan of {len(cols)} numeric columns identified {total_sig_pairs} significant relationships."
            )

            return {
                "title":       f"Correlation: {col_a} ↔ {col_b}",
                "description": description,
                "importance":  self._clamp(abs(best_r)),
                "type":        "correlation",
                "chart":       "scatter",
                "chart_data":  {
                    "x_label":          col_a,
                    "y_label":          col_b,
                    "x":                scatter_x,
                    "y":                scatter_y,
                    "r":                round(best_r, 4),
                    "correlation_matrix": {
                        "columns": matrix_cols,
                        "rows":    matrix_rows,
                    },
                },
                "metric":      col_a,
            }

        except Exception:
            return None
