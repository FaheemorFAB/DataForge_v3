"""
DataForge Insight Engine
════════════════════════
Pipeline:
  CSV/DataFrame
    ↓  detect_schema()
  schema dict (date / metrics / dimensions / dataset_type)
    ↓  run_insights()
  raw insight list
    ↓  rank + deduplicate
  top N insights
    ↓  (optionally) summarise_with_gemini()
  final narrative report

Usage::

    from dataforge.insight_engine import InsightEngine

    engine   = InsightEngine()
    schema   = engine.detect_schema(df)
    insights = engine.run_insights(df, schema, top_n=5)
    report   = engine.build_report_text(insights)
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional

from .trend_insight import TrendInsight
from .top_performer import TopPerformerInsight
from .correlation_insight import CorrelationInsight
from .anomaly_insight import AnomalyInsight
from .distribution_insight import DistributionInsight
from .contribution_insight import ContributionInsight
from .segment_insight import SegmentInsight
from .change_insight import ChangeInsight
from .feature_importance_insight import FeatureImportanceInsight
from .data_quality_insight import DataQualityInsight
from .numeric_summary_insight import NumericSummaryInsight
from .categorical_insight import CategoricalInsight
from .outlier_summary_insight import OutlierSummaryInsight

log = logging.getLogger(__name__)

# ── Dataset-type keyword map ───────────────────────────────────────────────────
DATASET_PATTERNS: dict[str, list[str]] = {
    "sales":      ["revenue", "sales", "product", "order", "units", "price", "sku",
                   "quantity", "invoice", "discount", "coupon"],
    "marketing":  ["campaign", "impression", "click", "ctr", "spend", "ad",
                   "conversion", "reach", "engagement", "channel", "utm"],
    "finance":    ["cost", "profit", "expense", "margin", "budget", "invoice",
                   "payment", "debit", "credit", "balance", "tax"],
    "customer":   ["customer", "churn", "subscription", "signup", "retention",
                   "ltv", "nps", "support", "ticket", "user", "account"],
    "hr":         ["employee", "salary", "department", "hire", "attrition",
                   "headcount", "performance", "leave", "tenure"],
    "product":    ["feature", "usage", "session", "event", "dau", "mau",
                   "retention", "cohort", "funnel", "page", "view"],
    "logistics":  ["shipment", "delivery", "carrier", "warehouse", "inventory",
                   "stock", "lead_time", "freight", "sku", "fulfil"],
}


class InsightEngine:
    """
    Plugin-based insight engine.  Add a new plugin by appending to PLUGINS.
    """

    PLUGINS = [
        # --- Conditional plugins (require specific schema features) ---
        TrendInsight(),           # requires date + metric
        TopPerformerInsight(),    # requires dimension + metric
        CorrelationInsight(),     # requires ≥2 metrics
        AnomalyInsight(),         # requires ≥1 metric
        ChangeInsight(),          # requires date + metric
        ContributionInsight(),    # requires dimension + metric
        SegmentInsight(),         # requires dimension + metric
        DistributionInsight(),    # requires ≥1 metric
        FeatureImportanceInsight(),  # requires prior AutoML run
        # --- Always-applicable plugins (fire on any dataset) ---
        DataQualityInsight(),     # always: missing value landscape
        OutlierSummaryInsight(),  # always: IQR sweep across all numerics
        NumericSummaryInsight(),  # always: CV / range analysis
        CategoricalInsight(),     # always: category concentration
    ]

    # ── Schema detection ──────────────────────────────────────────────────────
    def detect_schema(
        self,
        df: pd.DataFrame,
        feature_importance: Optional[dict] = None,
    ) -> dict:
        """
        Infer date column, numeric metrics, categorical dimensions, and
        dataset type from column names and dtypes.
        """
        schema: dict = {
            "date":               None,
            "metrics":            [],
            "dimensions":         [],
            "dataset_type":       "general",
            "feature_importance": feature_importance or {},
        }

        DATE_HINTS = {"date", "time", "timestamp", "created", "updated",
                      "day", "month", "week", "year", "period", "dt", "at"}
        ID_HINTS   = {"id", "_id", "uid", "uuid", "index", "key", "code", "zip",
                      "phone", "postal"}

        for col in df.columns:
            col_lower = col.lower()
            dtype = df[col].dtype
            
            # Safe unique count
            try:
                n_unique = df[col].nunique()
            except Exception:
                n_unique = 0

            # 1. Direct datetime type check
            if pd.api.types.is_datetime64_any_dtype(dtype):
                if schema["date"] is None:
                    schema["date"] = col
                continue

            # 2. Date/Year inference via naming conventions
            is_date_hint = any(h in col_lower for h in DATE_HINTS)
            if is_date_hint:
                head_vals = df[col].dropna().head(10)
                
                # Special handling for simple integer years (e.g. 2022, 2023) to prevent float interpolation
                if pd.api.types.is_numeric_dtype(dtype):
                    if len(head_vals) > 0 and head_vals.between(1900, 2100).all():
                        if col not in schema["dimensions"]:
                            schema["dimensions"].append(col) # treat as dimension so it isn't averaged
                        if schema["date"] is None:
                            schema["date"] = col
                        continue
                
                try:
                    pd.to_datetime(head_vals, errors="raise")
                    if schema["date"] is None:
                        schema["date"] = col
                    continue
                except Exception:
                    pass

            # 3. ID / Key validation
            is_id = any(h in col_lower for h in ID_HINTS)

            # 4. Categorisation Engine
            if pd.api.types.is_numeric_dtype(dtype):
                # Numerics can act as Metrics or Dimensions
                if is_id or col_lower == 'year' or ('year' in col_lower and n_unique < 50):
                    # IDs and Explicit Years -> Dimension 
                    if col not in schema["dimensions"]:
                        schema["dimensions"].append(col)
                elif n_unique <= max(10, len(df) * 0.05) and n_unique > 0:
                    # Low Cardinality Numerical -> Categorical representation (e.g. status codes, priority)
                    if col not in schema["dimensions"]:
                        schema["dimensions"].append(col)
                else:
                    # General numerical operations -> Metric
                    if col not in schema["metrics"]:
                        schema["metrics"].append(col)
            else:
                # Text / Boolean / Objects / Categoricals
                if (n_unique <= max(50, len(df) * 0.2) and n_unique > 0) or is_id:
                    # Prevents ingesting verbose free-text descriptions into UI charts
                    if col not in schema["dimensions"]:
                        schema["dimensions"].append(col)

        schema["dataset_type"] = self._detect_type(df.columns.tolist())
        return schema

    # ── Dataset type detection ────────────────────────────────────────────────
    def _detect_type(self, columns: list[str]) -> str:
        scores: dict[str, int] = {k: 0 for k in DATASET_PATTERNS}
        for col in columns:
            col_lower = col.lower()
            for ds_type, keywords in DATASET_PATTERNS.items():
                for kw in keywords:
                    if kw in col_lower:
                        scores[ds_type] += 1
        best       = max(scores, key=scores.get)
        best_score = scores[best]
        return best if best_score > 0 else "general"

    # ── Plugin runner ─────────────────────────────────────────────────────────
    def run_insights(
        self,
        df: pd.DataFrame,
        schema: dict,
        top_n: int = 8,
    ) -> list[dict]:
        """
        Run all applicable plugins, deduplicate by metric, rank by importance,
        return exactly top_n insights.

        If the plugins cannot fill top_n slots (e.g. simple dataset with no
        date column, few metrics), honest dataset-profile cards pad the list
        so the UI always receives the requested count.
        """
        results: list[dict] = []
        seen_types: set[str] = set()

        for plugin in self.PLUGINS:
            try:
                if not plugin.applicable(df, schema):
                    continue
                insight = plugin.analyze(df, schema)
                if insight is None:
                    continue

                # Tighter deduplication — prevent same metric appearing with a
                # near-identical insight type (e.g. two 'distribution' entries).
                # Key: type :: metric :: direction (positive/negative for correlation)
                direction = ""
                if insight.get("type") == "correlation":
                    r = insight.get("chart_data", {}).get("r", 0)
                    direction = "pos" if r >= 0 else "neg"
                dedup_key = f"{insight['type']}::{insight.get('metric', '')}::{direction}"
                if dedup_key in seen_types:
                    continue
                seen_types.add(dedup_key)

                results.append(insight)
            except Exception as exc:
                log.warning("Insight plugin %s failed: %s", plugin.name, exc)

        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        results = results[:top_n]

        # ── Graceful padding if fewer insights than requested ─────────────────
        # Rather than returning fewer cards than requested (which breaks the UI),
        # synthesize honest data-profile insights from the raw dataframe.
        if len(results) < top_n:
            results = self._pad_insights(df, schema, results, top_n)

        return results

    def _pad_insights(self, df: pd.DataFrame, schema: dict,
                      existing: list, target_n: int) -> list:
        """Generate honest descriptive insights to fill any gap below target_n."""
        pads: list[dict] = []
        seen_titles = {i["title"] for i in existing}

        # Pad 1: Dataset dimensions
        if len(existing) + len(pads) < target_n:
            title = "Dataset Overview"
            if title not in seen_titles:
                num_cols = len(schema.get("metrics", []))
                cat_cols = len(schema.get("dimensions", []))
                date_col = schema.get("date")
                pads.append({
                    "title":       title,
                    "description": (
                        f"This dataset contains {df.shape[0]:,} rows and {df.shape[1]} columns "
                        f"({num_cols} numeric metric(s), {cat_cols} categorical dimension(s)"
                        + (f", date column: '{date_col}'" if date_col else ", no date column detected")
                        + f"). Dataset type classified as: {schema.get('dataset_type', 'general')}."
                    ),
                    "importance":  0.2,
                    "type":        "profile",
                    "chart":       None,
                    "chart_data":  None,
                    "metric":      "",
                })
                seen_titles.add(title)

        # Pad 2: Top numeric column stats
        if len(existing) + len(pads) < target_n and schema.get("metrics"):
            for metric in schema["metrics"][:3]:
                if metric not in df.columns:
                    continue
                title = f"Summary Statistics: {metric}"
                if title in seen_titles:
                    continue
                s = df[metric].dropna()
                if len(s) < 2:
                    continue
                pads.append({
                    "title":       title,
                    "description": (
                        f"'{metric}' — Mean: {s.mean():,.2f}, Median: {s.median():,.2f}, "
                        f"Std Dev: {s.std():,.2f}, Min: {s.min():,.2f}, Max: {s.max():,.2f}. "
                        f"Based on {len(s):,} non-null values "
                        f"({round(df[metric].isna().mean()*100, 1)}% missing)."
                    ),
                    "importance":  0.18,
                    "type":        "profile",
                    "chart":       None,
                    "chart_data":  None,
                    "metric":      metric,
                })
                seen_titles.add(title)
                if len(existing) + len(pads) >= target_n:
                    break

        # Pad 3: Dominant category info
        if len(existing) + len(pads) < target_n and schema.get("dimensions"):
            for dim in schema["dimensions"][:2]:
                if dim not in df.columns:
                    continue
                title = f"Category Breakdown: {dim}"
                if title in seen_titles:
                    continue
                try:
                    vc   = df[dim].value_counts().head(5)
                    top  = str(vc.index[0])
                    top_pct = round(float(vc.iloc[0] / len(df) * 100), 1)
                    pads.append({
                        "title":       title,
                        "description": (
                            f"'{dim}' has {int(df[dim].nunique())} unique values. "
                            f"The most common is '{top}' ({top_pct}% of rows). "
                            f"Top 5: {', '.join(str(v) for v in vc.index.tolist())}."
                        ),
                        "importance":  0.15,
                        "type":        "profile",
                        "chart":       None,
                        "chart_data":  None,
                        "metric":      dim,
                    })
                    seen_titles.add(title)
                except Exception:
                    pass
                if len(existing) + len(pads) >= target_n:
                    break

        combined = existing + pads
        return combined[:target_n]

    # ── Report text builder ───────────────────────────────────────────────────
    def build_report_text(
        self,
        insights: list[dict],
        dataset_name: str = "Dataset",
        dataset_type: str = "general",
    ) -> str:
        """
        Build a plain-English summary from a ranked list of insights.
        Format: one line per insight as "N. Title — Description"
        so that the workspace formatSummary() parser can split them correctly.
        This is the fallback when Gemini is not available.
        """
        if not insights:
            return "No significant insights detected in this dataset."

        lines = []
        for i, ins in enumerate(insights, 1):
            title = ins.get("title", "").strip()
            desc  = ins.get("description", "").strip()
            lines.append(f"{i}. {title} — {desc}")

        return "\n".join(lines)

    # ── Gemini summarisation ──────────────────────────────────────────────────
    def summarise_with_gemini(
        self,
        insights: list[dict],
        dataset_name: str = "Dataset",
        dataset_type: str = "general",
        gemini_fn=None,
    ) -> str:
        """
        Use Gemini to convert raw insight dicts into a polished executive report.
        `gemini_fn` should accept (prompt: str) → str.
        Falls back to build_report_text if Gemini is unavailable.
        """
        if not gemini_fn or not insights:
            return self.build_report_text(insights, dataset_name, dataset_type)

        bullet_list = "\n".join(
            f"- [{ins['type'].upper()}] {ins['description']}"
            for ins in insights
        )

        prompt = f"""You are a senior data analyst writing an executive business report.

Dataset: {dataset_name}
Dataset type: {dataset_type}

Algorithmic findings:
{bullet_list}

Write a concise, professional business insight report (4-8 sentences).
Use plain English. Do not use bullet points.
Focus on what is actually supported by the findings and avoid adding unsupported causal claims.
Prioritize the strongest quantified findings first and end with a practical next step or watchout.
Do not repeat the exact wording from the findings; rephrase naturally."""

        try:
            summary = gemini_fn(prompt)
            return summary.strip() if summary else self.build_report_text(insights, dataset_name, dataset_type)
        except Exception:
            return self.build_report_text(insights, dataset_name, dataset_type)


# ── Module-level singleton for convenience ────────────────────────────────────
_engine = InsightEngine()

def detect_schema(df: pd.DataFrame, feature_importance: dict | None = None) -> dict:
    return _engine.detect_schema(df, feature_importance)

def run_insights(df: pd.DataFrame, schema: dict, top_n: int = 6) -> list[dict]:
    return _engine.run_insights(df, schema, top_n)

def build_report_text(insights: list[dict], dataset_name: str = "Dataset", dataset_type: str = "general") -> str:
    return _engine.build_report_text(insights, dataset_name, dataset_type)

def summarise_with_gemini(insights, dataset_name="Dataset", dataset_type="general", gemini_fn=None) -> str:
    return _engine.summarise_with_gemini(insights, dataset_name, dataset_type, gemini_fn)
