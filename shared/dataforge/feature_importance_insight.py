"""
Feature Importance Insight
──────────────────────────
Re-surfaces FLAML feature importance as a business-language insight.
Falls back to correlation-based ranking if no AutoML result is available.
"""

import pandas as pd
from .base_insight import BaseInsight


class FeatureImportanceInsight(BaseInsight):
    name = "feature_importance"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        fi = schema.get("feature_importance")
        return bool(fi) or len(schema.get("metrics", [])) >= 2

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        fi = schema.get("feature_importance")   # dict {feature: importance}

        try:
            if fi:
                ranked = sorted(fi.items(), key=lambda x: x[1], reverse=True)
                top3   = ranked[:3]
                labels = [str(k) for k, _ in ranked[:8]]
                values = [self._safe_float(v) for _, v in ranked[:8]]
                desc   = (
                    f"Top predictors: {top3[0][0]}"
                    + (f", {top3[1][0]}" if len(top3) > 1 else "")
                    + (f", and {top3[2][0]}" if len(top3) > 2 else "")
                    + "."
                )
                importance = 0.75
            else:
                # Correlation-based fallback
                metrics = schema.get("metrics", [])
                if len(metrics) < 2:
                    return None
                target  = metrics[0]
                numeric = df[metrics].select_dtypes(include="number").dropna()
                corr    = numeric.corr()[target].drop(index=target, errors="ignore").abs()
                corr    = corr.sort_values(ascending=False).head(8)
                if corr.empty:
                    return None
                labels     = [str(i) for i in corr.index]
                values     = [self._safe_float(v) for v in corr.values]
                top_feat   = labels[0]
                desc       = (
                    f"Key drivers of {target} (by correlation): "
                    f"{', '.join(labels[:3])}."
                )
                importance = 0.5

            return {
                "title":       "Key Drivers",
                "description": desc,
                "importance":  importance,
                "type":        "ranking",
                "chart":       "bar",
                "chart_data":  {"labels": labels, "values": values},
                "metric":      schema.get("metrics", [""])[0],
            }
        except Exception:
            return None
