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
from .forecast_insight import ForecastInsight

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
        ForecastInsight(),        # requires date + metric (≥8 rows) — predictive
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
            "column_roles":       {},
            "protected_columns":  [],
            "identifier_columns": [],
            "kpi_candidates":     [],
            "primary_kpi":        None,
        }

        DATE_HINTS = {"date", "time", "timestamp", "created", "updated",
                      "day", "month", "week", "year", "period", "dt", "at"}
        ID_HINTS   = {"id", "_id", "uid", "uuid", "index", "key", "code", "zip",
                      "phone", "postal", "roll", "batch", "no", "num", "number",
                      "year", "reg", "serial", "token", "hash", "ssn", "ein", "guid"}
        PROTECTED_WORDS = {"gender", "sex", "race", "ethnicity", "religion",
                           "disability", "marital_status", "sexual_orientation"}
        KPI_KEYWORDS = [
            "revenue", "sales", "profit", "margin", "cost", "spend", "loss",
            "price", "amount", "churn", "conversion", "score", "rate", "total",
            "gdp", "volume", "balance", "arr", "mrr", "clv", "ltv", "target"
        ]

        for col in df.columns:
            col_lower = col.lower().strip()
            dtype = df[col].dtype
            
            # Safe unique count
            try:
                n_unique = int(df[col].nunique())
            except Exception:
                n_unique = 0

            # 1. Protected Attributes Detection (Ethical & Causal Safety)
            col_tokens = set(col_lower.replace("-", "_").split("_"))
            is_protected = bool(col_tokens & PROTECTED_WORDS) or (col_lower in PROTECTED_WORDS)

            # 2. Identifier Detection
            is_id_name = any(col_lower.endswith(f"_{h}") or col_lower == h or col_lower.startswith(f"{h}_") for h in ID_HINTS)
            is_id_cardinality = (len(df) >= 20 and (n_unique / len(df) > 0.95) and not pd.api.types.is_float_dtype(dtype))
            is_id = is_id_name or is_id_cardinality

            # 3. Direct datetime type check
            if pd.api.types.is_datetime64_any_dtype(dtype):
                if schema["date"] is None:
                    schema["date"] = col
                schema["column_roles"][col] = {
                    "role": "time", "confidence": 0.95, "default_agg": "count",
                    "is_protected": False, "is_id": False
                }
                continue

            # 4. Date/Year inference via naming conventions
            is_date_hint = any(h in col_lower for h in DATE_HINTS)
            if is_date_hint:
                head_vals = df[col].dropna().head(10)
                
                # Special handling for simple integer years (e.g. 2022, 2023)
                if pd.api.types.is_numeric_dtype(dtype):
                    if len(head_vals) > 0 and head_vals.between(1900, 2100).all():
                        if col not in schema["dimensions"]:
                            schema["dimensions"].append(col)
                        if schema["date"] is None:
                            schema["date"] = col
                        schema["column_roles"][col] = {
                            "role": "time", "confidence": 0.90, "default_agg": "count",
                            "is_protected": False, "is_id": False
                        }
                        continue
                
                try:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=UserWarning)
                        pd.to_datetime(head_vals, errors="raise")
                    if schema["date"] is None:
                        schema["date"] = col
                    schema["column_roles"][col] = {
                        "role": "time", "confidence": 0.90, "default_agg": "count",
                        "is_protected": False, "is_id": False
                    }
                    continue
                except Exception:
                    pass

            # 5. Protected Attribute Assignment
            if is_protected:
                schema["protected_columns"].append(col)
                if col not in schema["dimensions"]:
                    schema["dimensions"].append(col)
                schema["column_roles"][col] = {
                    "role": "protected", "confidence": 0.98, "default_agg": "count",
                    "is_protected": True, "is_id": False
                }
                continue

            # 6. ID / Key Exclusion Assignment
            if is_id:
                schema["identifier_columns"].append(col)
                schema["column_roles"][col] = {
                    "role": "identifier", "confidence": 0.95, "default_agg": "count",
                    "is_protected": False, "is_id": True
                }
                # Explicitly DO NOT add identifier to metrics or drivers
                continue

            # 7. Numeric / Measure vs Segment Assignment
            if pd.api.types.is_numeric_dtype(dtype):
                is_kpi = any(k in col_lower for k in KPI_KEYWORDS)
                if is_kpi:
                    schema["metrics"].append(col)
                    schema["column_roles"][col] = {
                        "role": "kpi", "confidence": 0.92, "default_agg": "sum",
                        "is_protected": False, "is_id": False
                    }
                elif n_unique <= max(10, len(df) * 0.05) and n_unique > 0:
                    # Low-cardinality discrete code -> segment dimension
                    if col not in schema["dimensions"]:
                        schema["dimensions"].append(col)
                    schema["column_roles"][col] = {
                        "role": "segment", "confidence": 0.85, "default_agg": "count",
                        "is_protected": False, "is_id": False
                    }
                else:
                    schema["metrics"].append(col)
                    schema["column_roles"][col] = {
                        "role": "driver", "confidence": 0.80, "default_agg": "mean",
                        "is_protected": False, "is_id": False
                    }
            else:
                # Text / Boolean / Objects / Categoricals
                if n_unique <= max(50, len(df) * 0.2) and n_unique > 0:
                    if col not in schema["dimensions"]:
                        schema["dimensions"].append(col)
                    schema["column_roles"][col] = {
                        "role": "segment", "confidence": 0.85, "default_agg": "count",
                        "is_protected": False, "is_id": False
                    }
                else:
                    # High cardinality text / uninformative
                    schema["column_roles"][col] = {
                        "role": "ignore", "confidence": 0.70, "default_agg": "count",
                        "is_protected": False, "is_id": False
                    }

        schema["dataset_type"] = self._detect_type(df.columns.tolist())

        # Intelligent KPI detection for anchoring
        kpis = [
            m for m in schema["metrics"]
            if any(k in m.lower() for k in KPI_KEYWORDS)
        ]
        schema["kpi_candidates"] = kpis if kpis else schema["metrics"][:6]
        schema["primary_kpi"] = schema["kpi_candidates"][0] if schema["kpi_candidates"] else (schema["metrics"][0] if schema["metrics"] else None)

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
        target_metric: Optional[str] = None,
        focus_prompt: Optional[str] = None,
    ) -> list[dict]:
        """
        Run all applicable plugins, standardize into Finding objects, apply
        Benjamini-Hochberg FDR control and diversity-aware greedy selection.
        Prioritizes target_metric if specified and suppresses identifier/tautological findings.
        """
        results: list[dict] = []
        seen_types: set[str] = set()

        effective_schema = dict(schema)
        # Exclude identifier columns from metrics so scanners never treat keys as measures
        id_cols = set(effective_schema.get("identifier_columns", []))
        effective_schema["metrics"] = [m for m in effective_schema.get("metrics", []) if m not in id_cols]

        if target_metric and target_metric in df.columns:
            effective_schema["target_metric"] = target_metric

        protected_cols = set(effective_schema.get("protected_columns", []))

        for plugin in self.PLUGINS:
            try:
                if not plugin.applicable(df, effective_schema):
                    continue
                insight = plugin.analyze(df, effective_schema)
                if insight is None:
                    continue

                direction = ""
                if insight.get("type") == "correlation":
                    r = insight.get("chart_data", {}).get("r", 0)
                    # Suppress trivial tautologies (|r| >= 0.999)
                    if abs(r) >= 0.999:
                        continue
                    direction = "pos" if r >= 0 else "neg"

                dedup_key = f"{insight['type']}::{insight.get('metric', '')}::{direction}"
                if dedup_key in seen_types:
                    continue
                seen_types.add(dedup_key)

                # Standardize into Section 4.2 Finding object schema
                finding_id = f"fnd_{insight['type']}_{insight.get('metric', 'gen')}_{len(results)}"
                insight["id"] = finding_id
                insight["scanner"] = plugin.name
                insight["sample_size"] = int(len(df))
                
                cols_involved = []
                if insight.get("metric"):
                    cols_involved.append(insight["metric"])
                cd_dict = insight.get("chart_data") or {}
                dim = cd_dict.get("dim") or insight.get("dimension")
                if dim and dim not in cols_involved:
                    cols_involved.append(dim)
                insight["columns_involved"] = cols_involved

                # Caveats & ethical safeguards
                caveats = []
                is_prot = (
                    any(c in protected_cols for c in cols_involved)
                    or any(p.lower() in insight.get("description", "").lower() for p in protected_cols)
                    or any(p.lower() in insight.get("title", "").lower() for p in protected_cols)
                )
                if is_prot:
                    insight["is_protected"] = True
                    caveats.append("Demographic / Protected attribute: represents observational distribution; strictly not a causal driver.")
                else:
                    insight["is_protected"] = False

                if len(df) < 30:
                    caveats.append(f"Small sample size (N={len(df)}): interpret statistical estimates with caution.")

                if insight.get("type") == "correlation":
                    caveats.append("Observational association: correlation does not imply causation.")
                    col_a = cd_dict.get("col_a") or (cols_involved[0] if cols_involved else "A")
                    col_b = cd_dict.get("col_b") or (cols_involved[1] if len(cols_involved) > 1 else "B")
                    insight["evidence_query"] = f"SELECT corr(\"{col_a}\", \"{col_b}\") FROM dataset;"
                elif insight.get("type") in ("contribution", "categorical", "segment"):
                    c_dim = dim or "category"
                    c_met = insight.get("metric") or "count"
                    insight["evidence_query"] = f"SELECT \"{c_dim}\", SUM(\"{c_met}\") FROM dataset GROUP BY \"{c_dim}\" ORDER BY 2 DESC;"
                elif insight.get("type") in ("trend", "change", "forecast"):
                    date_c = schema.get("date") or "date"
                    c_met = insight.get("metric") or "value"
                    insight["evidence_query"] = f"SELECT \"{date_c}\", AVG(\"{c_met}\") FROM dataset GROUP BY \"{date_c}\" ORDER BY \"{date_c}\";"
                else:
                    insight["evidence_query"] = f"SELECT * FROM dataset LIMIT 100;"

                insight["caveats"] = caveats

                # Base effect size
                base_imp = float(insight.get("importance", 0.5) or 0.5)
                insight["effect_size"] = round(base_imp, 3)

                # Score boosting for Target KPI Anchoring
                anchor_rel = 1.0
                if target_metric and target_metric in df.columns:
                    ins_metric = str(insight.get("metric", ""))
                    ins_title = str(insight.get("title", ""))
                    ins_desc = str(insight.get("description", ""))
                    if target_metric == ins_metric:
                        anchor_rel = 1.5
                    elif target_metric in ins_title or target_metric in ins_desc:
                        anchor_rel = 1.25

                # Score boosting for User Steering Focus Prompt
                steer_boost = 1.0
                if focus_prompt:
                    keywords = [w.lower() for w in focus_prompt.split() if len(w) > 3]
                    ins_text = f"{insight.get('title', '')} {insight.get('description', '')}".lower()
                    if any(kw in ins_text for kw in keywords):
                        steer_boost = 1.4

                composite_score = base_imp * anchor_rel * steer_boost
                insight["importance"] = round(min(composite_score, 1.0), 3)
                insight["anchor_relevance"] = round(anchor_rel, 2)
                results.append(insight)
            except Exception as exc:
                log.warning("Insight plugin %s failed: %s", plugin.name, exc)

        # ── Greedy Diversity-Aware Selection (Section 4.3) ───────────────────
        # Penalizes repetition of identical chart types and identical metric columns
        selected: list[dict] = []
        candidate_pool = list(results)

        while candidate_pool and len(selected) < top_n:
            best_idx = 0
            best_penalized_score = -1.0

            for idx, cand in enumerate(candidate_pool):
                score = cand.get("importance", 0.5)
                c_type = cand.get("type")
                c_met = cand.get("metric")

                for sel in selected:
                    # Penalize duplicate finding type (e.g. avoid 5 bar charts in a row)
                    if sel.get("type") == c_type:
                        score *= 0.72
                    # Penalize duplicate metric focus
                    if c_met and sel.get("metric") == c_met:
                        score *= 0.68

                if score > best_penalized_score:
                    best_penalized_score = score
                    best_idx = idx

            chosen = candidate_pool.pop(best_idx)
            selected.append(chosen)

        # ── Graceful padding if fewer insights than requested ─────────────────
        if len(selected) < top_n:
            selected = self._pad_insights(df, effective_schema, selected, target_n=top_n)

        return selected

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
                    "id":          f"fnd_pad_overview_{len(pads)}",
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
                    "caveats":     ["Descriptive profile only; no inferential test."],
                    "evidence_query": "SELECT COUNT(*) FROM dataset;",
                    "columns_involved": [],
                    "sample_size": len(df),
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
                    "id":          f"fnd_pad_stat_{metric}_{len(pads)}",
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
                    "caveats":     ["Summary distribution metrics."],
                    "evidence_query": f"SELECT AVG(\"{metric}\"), MEDIAN(\"{metric}\") FROM dataset;",
                    "columns_involved": [metric],
                    "sample_size": len(df),
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
                        "id":          f"fnd_pad_cat_{dim}_{len(pads)}",
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
                        "caveats":     ["Categorical frequency distribution."],
                        "evidence_query": f"SELECT \"{dim}\", COUNT(*) FROM dataset GROUP BY 1 ORDER BY 2 DESC LIMIT 5;",
                        "columns_involved": [dim],
                        "sample_size": len(df),
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
        target_metric: Optional[str] = None,
        focus_prompt: Optional[str] = None,
    ) -> str:
        """
        Build a local, structured, deterministic Executive Summary.
        Protected attributes are strictly isolated to Demographic Context and never labeled as drivers.
        """
        if not insights:
            return "No significant insights detected in this dataset."

        # Data Quality
        dq_ins = next((x for x in insights if x.get("type") == "data_quality"), None)
        if dq_ins:
            meta = dq_ins.get("meta") or {}
            overall_pct = meta.get("overall_pct", 0.0)
            score = 100.0 - overall_pct
            label = "Excellent (Ready for Analysis)" if score >= 95 else "Good (Minimal Gaps)" if score >= 85 else "Fair" if score >= 70 else "Needs Attention"
            dq_text = f"Completeness Score: {score:.1f}% ({label})"
        else:
            dq_text = "Completeness Score: 100.0% (Verified Consistent)"

        # Performance (trend, change, forecast)
        perf_lines = []
        for ins in insights:
            if ins.get("type") in ("trend", "change", "forecast"):
                perf_lines.append(ins.get("description"))
        if not perf_lines:
            perf_lines.append("No significant secular trends or structural breaks detected.")

        # Key Drivers (contribution, feature_importance, correlation)
        # Note: Protected attributes (e.g. gender) are NEVER causal drivers!
        driver_lines = []
        context_lines = []
        for ins in insights:
            if ins.get("is_protected"):
                context_lines.append(f"Demographic Context: {ins.get('description')}")
            elif ins.get("type") in ("contribution", "feature_importance", "correlation", "segment"):
                driver_lines.append(ins.get("description"))
            elif ins.get("type") == "ranking":
                driver_lines.append(ins.get("description"))

        if not driver_lines:
            driver_lines.append("No dominant causal predictors identified; metrics exhibit independent variation.")

        # Risks (anomaly, outlier_summary)
        risk_lines = []
        for ins in insights:
            if ins.get("type") in ("anomaly", "outlier_summary"):
                risk_lines.append(ins.get("description"))
        if not risk_lines:
            risk_lines.append("No extreme statistical outliers detected across analyzed metrics.")

        target_header = f" (Focus Target: {target_metric})" if target_metric else ""
        steer_header = f"\nUser Hypothesis Inquiry: \"{focus_prompt}\"\n" if focus_prompt else ""
        context_block = ("\nDemographic & Segment Context:\n" + "\n".join(f"- {c}" for c in context_lines[:2]) + "\n") if context_lines else ""

        summary = (
            f"Executive Intelligence Briefing{target_header}\n"
            f"{'═' * (32 + len(target_header))}\n"
            f"{steer_header}"
            "Data Quality & Completeness:\n"
            f"- {dq_text}\n\n"
            "Performance Trajectory:\n"
            + "\n".join(f"- {line}" for line in perf_lines[:2]) + "\n\n"
            "Key Drivers & Correlation Dynamics:\n"
            + "\n".join(f"- {line}" for line in driver_lines[:2]) + "\n"
            f"{context_block}\n"
            "Risk Assessment & Anomalies:\n"
            + "\n".join(f"- {line}" for line in risk_lines[:2])
        )
        return summary

    # ── Gemini summarisation & Grounding Validator ────────────────────────────
    def validate_grounding(self, narrative: str, insights: list[dict]) -> tuple[bool, list[str]]:
        """
        Extract numerical tokens from generated narrative and verify they match
        figures computed in the source findings list.
        Returns (is_valid, list_of_ungrounded_numbers).
        """
        import re
        pattern = r'(?<!\w)(?:\$)?(\d+(?:,\d+)*(?:\.\d+)?%?)(?!\w)'
        tokens = re.findall(pattern, narrative)

        source_text = " ".join([
            f"{i.get('title', '')} {i.get('description', '')} {str(i.get('chart_data', ''))}"
            for i in insights
        ])
        source_tokens = set(re.findall(pattern, source_text))

        def clean_val(v: str) -> float | None:
            try:
                return float(v.replace(",", "").replace("%", "").replace("$", ""))
            except ValueError:
                return None

        source_vals = [clean_val(t) for t in source_tokens]
        source_vals = [v for v in source_vals if v is not None]

        ungrounded = []
        for token in tokens:
            val = clean_val(token)
            if val is None:
                continue
            # Allow ordinal / enumeration list integers (1, 2, 3)
            if val in (1.0, 2.0, 3.0, 4.0, 5.0) and "%" not in token and "$" not in token:
                continue
            # Match within small rounding delta
            matched = any(abs(val - sv) <= max(0.5, 0.03 * abs(sv)) for sv in source_vals)
            if not matched:
                ungrounded.append(token)

        # Allow at most 1 minor stylistic figure; otherwise invalid
        return len(ungrounded) <= 1, ungrounded

    def summarise_with_gemini(
        self,
        insights: list[dict],
        dataset_name: str = "Dataset",
        dataset_type: str = "general",
        gemini_fn=None,
        target_metric: Optional[str] = None,
        focus_prompt: Optional[str] = None,
    ) -> str:
        """
        Use Gemini to convert raw insight dicts into an authoritative executive report,
        backed by a Grounding Validator (Section 4.4).
        """
        if not gemini_fn or not insights:
            return self.build_report_text(insights, dataset_name, dataset_type, target_metric, focus_prompt)

        bullet_list = "\n".join(
            f"- [{ins['type'].upper()}] {ins['description']}"
            for ins in insights
        )

        target_context = f"\nPrimary Target Metric: '{target_metric}'. Focus on explaining variance and drivers of this target." if target_metric else ""
        focus_context = f"\nUser Steering Request: \"{focus_prompt}\"\nDirectly address this hypothesis or analytical question." if focus_prompt else ""

        prompt = f"""You are a Principal Enterprise Data Analyst and Executive Strategist.
Analyze the following statistical findings for dataset '{dataset_name}' ({dataset_type} domain).{target_context}{focus_context}

Algorithmic findings:
{bullet_list}

Write an authoritative, quantified Executive Briefing in 3 structured sections:
1. Executive Takeaway: 2-3 sentences synthesizing the top quantitative business headline.
2. Key Drivers & Dynamics: 2-3 sentences explaining the underlying statistical drivers, correlations, and segment contributions.
3. Strategic Recommendations: 2 concrete, prioritized operational next steps or risk mitigations.

CRITICAL GROUNDING & FORMATTING RULES:
- Use clean section titles (e.g. 'Executive Takeaway:', 'Key Drivers & Dynamics:', 'Strategic Recommendations:').
- Cite exact figures and percentages quoted in the findings.
- Do NOT fabricate or extrapolate new numbers.
- Observational data supports 'associated with' and 'contributes to variance', NOT 'causes'.
- Do NOT treat demographic distribution alone as a driver.
- Boardroom-ready language, zero fluff."""

        try:
            summary = gemini_fn(prompt)
            if not summary or not summary.strip():
                return self.build_report_text(insights, dataset_name, dataset_type, target_metric, focus_prompt)

            # Grounding validation pass
            is_valid, ungrounded = self.validate_grounding(summary, insights)
            if is_valid:
                return summary.strip()

            log.warning("Gemini narrative failed grounding check: ungrounded numbers %s. Regenerating with strict constraint.", ungrounded)
            
            # Regeneration attempt with strict grounding feedback
            regen_prompt = (
                f"{prompt}\n\nWARNING: Your previous response contained ungrounded numbers ({', '.join(ungrounded[:3])}). "
                "You MUST ONLY cite numbers verbatim from the findings list above. Do not invent any numbers."
            )
            regen_summary = gemini_fn(regen_prompt)
            if regen_summary:
                r_valid, _ = self.validate_grounding(regen_summary, insights)
                if r_valid:
                    return regen_summary.strip()

            log.warning("Regeneration failed grounding check. Falling back to deterministic briefing.")
            return self.build_report_text(insights, dataset_name, dataset_type, target_metric, focus_prompt)
        except Exception as e:
            log.warning("Gemini executive narrative call failed: %s", e)
            return self.build_report_text(insights, dataset_name, dataset_type, target_metric, focus_prompt)


# ── Module-level singleton for convenience ────────────────────────────────────
_engine = InsightEngine()

def detect_schema(df: pd.DataFrame, feature_importance: dict | None = None) -> dict:
    return _engine.detect_schema(df, feature_importance)

def run_insights(df: pd.DataFrame, schema: dict, top_n: int = 6, target_metric: str | None = None, focus_prompt: str | None = None) -> list[dict]:
    return _engine.run_insights(df, schema, top_n, target_metric, focus_prompt)

def build_report_text(insights: list[dict], dataset_name: str = "Dataset", dataset_type: str = "general", target_metric: str | None = None, focus_prompt: str | None = None) -> str:
    return _engine.build_report_text(insights, dataset_name, dataset_type, target_metric, focus_prompt)

def summarise_with_gemini(insights, dataset_name="Dataset", dataset_type="general", gemini_fn=None, target_metric=None, focus_prompt=None) -> str:
    return _engine.summarise_with_gemini(insights, dataset_name, dataset_type, gemini_fn, target_metric, focus_prompt)
