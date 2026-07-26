"""
Anomaly Insight — IQR + Z-Score Hybrid (Improved 2026-04-29)
─────────────────────────────────────────────────────────────
Dual-method anomaly detection:
  1. IQR fence method  (robust to non-normal distributions)
  2. Z-Score method    (|z| > 2.8, good for symmetric data)

A row is flagged as an anomaly only when EITHER method triggers.
This catches outliers that a single z-score test misses — especially
important for financial, sales, and HR data which are rarely Gaussian.
"""

import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class AnomalyInsight(BaseInsight):
    name = "anomaly"

    # Thresholds
    Z_THRESHOLD   = 2.8   # standard deviations from mean
    IQR_FACTOR    = 1.5   # Tukey fence multiplier

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("metrics", [])) > 0

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        metric   = schema["metrics"][0]
        date_col = schema.get("date")

        try:
            series = df[metric].dropna()
            if len(series) < 10:
                return None

            mean = float(series.mean())
            std  = float(series.std())

            # ── Method 1: IQR (Tukey fence) — robust to skewed distributions ──
            q1, q3  = series.quantile(0.25), series.quantile(0.75)
            iqr     = q3 - q1
            iqr_lo  = q1 - self.IQR_FACTOR * iqr
            iqr_hi  = q3 + self.IQR_FACTOR * iqr
            iqr_mask = (series < iqr_lo) | (series > iqr_hi)

            # ── Method 2: Z-score — good for symmetric/normal data ─────────────
            z_mask = pd.Series(False, index=series.index)
            if std > 0:
                z_scores = (series - mean) / std
                z_mask   = z_scores.abs() > self.Z_THRESHOLD

            # ── Union of both methods ──────────────────────────────────────────
            combined_mask = iqr_mask | z_mask
            anomalies     = df.loc[series.index[combined_mask]]

            if anomalies.empty:
                return None

            # Most extreme anomaly by absolute distance from mean
            if std > 0:
                z_abs    = ((series - mean) / std).abs()
                worst_idx = z_abs[combined_mask].idxmax()
            else:
                worst_idx = series[combined_mask].sub(mean).abs().idxmax()

            worst_val = self._safe_float(df.loc[worst_idx, metric])
            worst_z   = self._safe_float((worst_val - mean) / std) if std > 0 else 0.0
            kind      = "spike" if worst_val > mean else "drop"

            # Date attribution
            date_str = ""
            if date_col and date_col in df.columns:
                try:
                    date_str = f" on {pd.to_datetime(df.loc[worst_idx, date_col]).strftime('%b %d, %Y')}"
                except Exception:
                    date_str = f" (row {worst_idx})"

            n_iqr  = int(iqr_mask.sum())
            n_z    = int(z_mask.sum())
            n_both = int((iqr_mask & z_mask).sum())
            n_total = int(combined_mask.sum())

            worst_val_fmt = self._format_precise(metric, worst_val)
            variation_times = round(abs(worst_z), 1)
            description = (
                f"A significant unusual {kind} was detected in '{metric}'{date_str}. "
                f"The value reached {worst_val_fmt}, representing a variation {variation_times} times larger than the average. "
                f"A total of {n_total} unusual values were identified across the timeline, which may warrant further investigation."
            )

            return {
                "title":       f"{metric} Anomaly Detected",
                "description": description,
                "importance":  self._clamp(abs(worst_z) / 6),
                "type":        "anomaly",
                "chart":       None,
                "chart_data":  None,
                "metric":      metric,
                "meta": {
                    "n_anomalies":  n_total,
                    "n_iqr":        n_iqr,
                    "n_zscore":     n_z,
                    "n_both":       n_both,
                    "worst_value":  round(worst_val, 4),
                    "worst_zscore": round(abs(worst_z), 3),
                    "iqr_fence_lo": round(float(iqr_lo), 4),
                    "iqr_fence_hi": round(float(iqr_hi), 4),
                },
            }

        except Exception:
            return None
