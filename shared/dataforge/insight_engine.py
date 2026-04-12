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
        TrendInsight(),
        TopPerformerInsight(),
        CorrelationInsight(),
        AnomalyInsight(),
        ChangeInsight(),
        ContributionInsight(),
        SegmentInsight(),
        DistributionInsight(),
        FeatureImportanceInsight(),
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

            # Skip obvious ID columns before numeric check
            is_id = any(h in col_lower for h in ID_HINTS)

            # Date detection — try name hints first, then parse attempt
            if any(h in col_lower for h in DATE_HINTS):
                try:
                    pd.to_datetime(df[col].dropna().head(10), errors="raise")
                    if schema["date"] is None:
                        schema["date"] = col
                    continue
                except Exception:
                    pass

            dtype = df[col].dtype
            if pd.api.types.is_datetime64_any_dtype(dtype):
                if schema["date"] is None:
                    schema["date"] = col
                continue

            if pd.api.types.is_numeric_dtype(dtype) and not is_id:
                schema["metrics"].append(col)
            elif df[col].dtype == object or pd.api.types.is_categorical_dtype(df[col]):
                n_unique = df[col].nunique()
                if n_unique <= max(50, len(df) * 0.1):   # not a free-text column
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
        top_n: int = 6,
    ) -> list[dict]:
        """
        Run all applicable plugins, deduplicate by metric, rank by importance,
        return top_n insights.
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

                # Light deduplication — skip if same type already present for same metric
                dedup_key = f"{insight['type']}::{insight.get('metric', '')}"
                if dedup_key in seen_types:
                    continue
                seen_types.add(dedup_key)

                results.append(insight)
            except Exception as exc:
                log.warning("Insight plugin %s failed: %s", plugin.name, exc)

        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return results[:top_n]

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

Write a concise, professional business insight report (4–8 sentences).
Use plain English. Do not use bullet points. Focus on decisions the reader should make.
Do not repeat the exact wording from the findings — rephrase naturally."""

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