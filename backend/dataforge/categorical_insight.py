"""
Categorical Insight
───────────────────
Always fires when the dataset has at least 1 categorical (dimension) column.
Reports:
  - Which category dominates (concentration risk in business data)
  - Which column is most fragmented (many small categories = diversity)
  - Top value counts for the most concentrated column
These are honest, factual, always-computable insights — no fabrication.
"""
import pandas as pd
import numpy as np
from .base_insight import BaseInsight


class CategoricalInsight(BaseInsight):
    name = "categorical"

    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        return len(schema.get("dimensions", [])) >= 1

    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        try:
            dims = schema["dimensions"]
            # Only process object/category/bool columns from the dimension list
            cat_cols = [
                c for c in dims
                if c in df.columns
                and df[c].dtype in ("object", "category", "bool")
                or (c in df.columns and df[c].dtype == "object")
            ]
            # Also allow low-cardinality numeric dimensions
            if not cat_cols:
                cat_cols = [
                    c for c in dims
                    if c in df.columns and df[c].nunique() <= 30
                ]
            if not cat_cols:
                return None

            # Find most concentrated column (lowest entropy = dominated by one value)
            entropies = {}
            for col in cat_cols:
                freqs = df[col].value_counts(normalize=True)
                # Shannon entropy (0 = fully concentrated, log(n) = fully uniform)
                entropies[col] = float(-(freqs * np.log(freqs + 1e-10)).sum())

            most_concentrated = min(entropies, key=entropies.get)
            most_fragmented   = max(entropies, key=entropies.get)

            vc        = df[most_concentrated].value_counts()
            top_val   = str(vc.index[0])
            top_pct   = round(float(vc.iloc[0] / len(df) * 100), 1)
            n_unique  = int(df[most_concentrated].nunique())

            frag_unique = int(df[most_fragmented].nunique())

            description = (
                f"We observed significant segment concentration in the '{most_concentrated}' category, "
                f"where the dominant value '{top_val}' accounts for {top_pct}% of the dataset (out of {n_unique} distinct categories). "
                f"This concentration presents a potential dependency risk or focus area. Conversely, the '{most_fragmented}' category "
                f"exhibits high diversity with {frag_unique} unique values, offering broad coverage for detailed segment-level insights."
            )

            # Bar chart: top 10 values in the most concentrated column
            top10     = vc.head(10)
            chart_data = {
                "labels":  [str(v) for v in top10.index],
                "values":  [int(v) for v in top10.values],
                "x_label": most_concentrated,
                "y_label": "Count",
            }

            return {
                "title":       f"Category Distribution: {most_concentrated}",
                "description": description,
                "importance":  round(min(top_pct / 100 + 0.2, 0.85), 3),
                "type":        "categorical",
                "chart":       "bar_chart",
                "chart_data":  chart_data,
                "metric":      most_concentrated,
                "meta": {
                    "most_concentrated": most_concentrated,
                    "dominant_value":    top_val,
                    "dominant_pct":      top_pct,
                    "n_unique":          n_unique,
                    "most_fragmented":   most_fragmented,
                    "fragmented_unique": frag_unique,
                },
            }

        except Exception:
            return None
