"""
DataForge AI - Deterministic Analytics Fallback Engine
High-performance local pandas/numpy analytics engine that executes when external LLM APIs
are unavailable, rate-limited, or out of prepayment credits (HTTP 402).
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from ..schemas import AgentAction
from ..tools.viz_tool import build_chart_tool
from ..router.patterns import fuzzy_resolve_all_columns

logger = logging.getLogger(__name__)


def run_deterministic_analysis(query: str, df: pd.DataFrame, error_msg: str = "") -> Dict[str, Any]:
    """Safety fallback if external API is unreachable. Computes local pandas analytics."""
    q_lower = query.lower()
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(exclude=np.number).columns.tolist()

    is_credits_error = "402" in error_msg or "prepayment credits" in error_msg.lower() or "resource_exhausted" in error_msg.lower()
    sys_notice = (
        "Google Gemini API: Prepayment credits depleted on your Google AI Studio account (HTTP 402). "
        "DataForge is running this query on the local deterministic analytics engine. "
        "To reactivate cloud models, top up credits at https://ai.studio/projects or update GEMINI_API_KEY in .env."
        if is_credits_error else None
    )

    # Detect columns mentioned in query
    matched_cols = fuzzy_resolve_all_columns(query, df)
    target_col = matched_cols[0] if matched_cols else None
    second_col = matched_cols[1] if len(matched_cols) > 1 else None

    # ── Case A: Bivariate Analysis (Two Columns detected) ───────────────
    if target_col and second_col:
        # Subcase 1: Both numeric -> Correlation & Scatter
        if target_col in num_cols and second_col in num_cols:
            s1 = df[target_col].dropna()
            s2 = df[second_col].dropna()
            valid_idx = s1.index.intersection(s2.index)
            corr_val = round(float(df.loc[valid_idx, [target_col, second_col]].corr().iloc[0, 1]), 3) if len(valid_idx) > 1 else 0.0
            strength = "strong" if abs(corr_val) > 0.6 else ("moderate" if abs(corr_val) > 0.3 else "weak")
            direction = "positive" if corr_val > 0 else "negative"

            ans = (
                f"### Correlation Analysis: `{target_col}` vs `{second_col}`\n\n"
                f"• **Pearson Correlation**: **{corr_val:+.3f}** ({strength} {direction} association)\n"
                f"• **Sample Size**: {len(valid_idx):,} common non-null observations\n"
                f"• **`{target_col}` range**: {s1.min():g} to {s1.max():g} (avg: {s1.mean():.2f})\n"
                f"• **`{second_col}` range**: {s2.min():g} to {s2.max():g} (avg: {s2.mean():.2f})\n\n"
                f"Higher values of `{target_col}` tend to {'increase' if corr_val > 0 else 'decrease'} alongside `{second_col}`."
            )
            chart = build_chart_tool(intent="scatter_chart", raw_result=df[[target_col, second_col]].head(100), df=df, x_col=target_col, y_col=second_col)
            return {
                "ok": True,
                "answer": ans,
                "result": chart,
                "intent": "scatter_chart",
                "code": f"result = df[['{target_col}', '{second_col}']].corr()",
                "insight": f"Pearson correlation coefficient: {corr_val:+.3f}.",
                "system_notice": sys_notice,
                "agent_actions": [AgentAction(agent="AnalyticsAgent", tool="local_pandas_engine", status="completed", message=f"Computed Pearson correlation between {target_col} and {second_col}.").model_dump()],
            }

        # Subcase 2: One categorical, one numeric -> Groupby aggregation
        cat_c = target_col if target_col in cat_cols else second_col
        num_c = second_col if target_col in cat_cols else target_col
        if cat_c in df.columns and num_c in df.columns and num_c in num_cols:
            agg_series = df.groupby(cat_c)[num_c].mean().dropna().sort_values(ascending=False).head(10).round(2)
            top_cat = agg_series.index[0]
            top_val = agg_series.iloc[0]
            bot_cat = agg_series.index[-1]
            bot_val = agg_series.iloc[-1]
            breakdown_md = "\n".join(f"• **{k}**: {v:,.2f}" for k, v in agg_series.items())

            ans = (
                f"### Average `{num_c}` by `{cat_c}`\n\n"
                f"Breakdown of `{num_c}` across top `{cat_c}` categories:\n\n"
                f"{breakdown_md}\n\n"
                f"• **Top Performer**: `{top_cat}` ({top_val:,.2f})\n"
                f"• **Lowest**: `{bot_cat}` ({bot_val:,.2f})"
            )
            chart = build_chart_tool(intent="bar_chart", raw_result=agg_series, df=df, x_col=cat_c, y_col=num_c)
            return {
                "ok": True,
                "answer": ans,
                "result": chart,
                "intent": "bar_chart",
                "code": f"result = df.groupby('{cat_c}')['{num_c}'].mean().sort_values(ascending=False)",
                "insight": f"`{top_cat}` leads `{num_c}` with an average of {top_val:,.2f}.",
                "system_notice": sys_notice,
                "agent_actions": [AgentAction(agent="AnalyticsAgent", tool="local_pandas_engine", status="completed", message=f"Grouped {num_c} by {cat_c}.").model_dump()],
            }

    # ── Case B: Univariate Analysis (Single Column detected) ────────────
    if target_col:
        # Numeric distribution
        if target_col in num_cols:
            s = df[target_col].dropna()
            q25, q50, q75 = s.quantile(0.25), s.quantile(0.50), s.quantile(0.75)
            mean_val = round(float(s.mean()), 2)
            std_val = round(float(s.std()), 2)
            skew_val = round(float(s.skew()), 2)
            skew_desc = "approximately symmetric" if abs(skew_val) < 0.5 else ("right-skewed (positive)" if skew_val > 0 else "left-skewed (negative)")

            ans = (
                f"### Statistical Profile: `{target_col}`\n\n"
                f"• **Mean**: **{mean_val:,.2f}** (Std Dev: {std_val:,.2f})\n"
                f"• **Median (Q2)**: **{q50:,.2f}** | IQR: {q25:,.2f} – {q75:,.2f}\n"
                f"• **Range**: {s.min():g} to {s.max():g} across {len(s):,} non-null records\n"
                f"• **Distribution Shape**: {skew_desc} (skewness: {skew_val:+.2f})\n"
                f"• **Missing Data**: {df[target_col].isnull().sum():,} cells ({df[target_col].isnull().mean()*100:.1f}%)"
            )
            chart = build_chart_tool(intent="histogram", raw_result=s, df=df, x_col=target_col)
            return {
                "ok": True,
                "answer": ans,
                "result": chart,
                "intent": "histogram",
                "code": f"result = df['{target_col}'].describe()",
                "insight": f"Median: {q50:,.2f}, Average: {mean_val:,.2f}. Distribution is {skew_desc}.",
                "system_notice": sys_notice,
                "agent_actions": [AgentAction(agent="AnalyticsAgent", tool="local_pandas_engine", status="completed", message=f"Generated univariate profile for {target_col}.").model_dump()],
                "suggested_actions": [
                    {"label": f"Check Outliers in {target_col}", "query": f"clip outliers in {target_col}"},
                    {"label": f"Compare {target_col} with other metrics", "query": f"compare {target_col} and {num_cols[1] if len(num_cols)>1 and num_cols[1]!=target_col else df.columns[0]}"},
                ]
            }

        # Categorical frequency
        if target_col in cat_cols or target_col in df.columns:
            vc = df[target_col].value_counts().head(8)
            total_cnt = len(df[target_col].dropna())
            breakdown_md = "\n".join(f"- **{cat}**: **{cnt:,}** ({cnt/total_cnt*100:.1f}%)" for cat, cnt in vc.items())
            top_cat = vc.index[0]
            top_pct = vc.iloc[0] / total_cnt * 100

            ans = (
                f"### Categorical Frequency: `{target_col}`\n\n"
                f"Top categories across {total_cnt:,} valid entries:\n\n"
                f"{breakdown_md}\n\n"
                f"- **Distinct Categories**: {df[target_col].nunique():,} unique values\n"
                f"- **Missing Values**: {df[target_col].isnull().sum():,} ({df[target_col].isnull().mean()*100:.1f}%)"
            )
            is_pie = any(k in q_lower for k in ["pie", "donut", "doughnut", "share", "proportion"])
            chart_intent = "pie_chart" if is_pie else "bar_chart"
            chart = build_chart_tool(intent=chart_intent, raw_result=vc, df=df, x_col=target_col)
            return {
                "ok": True,
                "answer": ans,
                "result": chart,
                "intent": chart_intent,
                "code": f"result = df['{target_col}'].value_counts()",
                "insight": f"Top category is '{top_cat}' comprising {top_pct:.1f}% of observed records.",
                "system_notice": sys_notice,
                "agent_actions": [AgentAction(agent="AnalyticsAgent", tool="local_pandas_engine", status="completed", message=f"Computed value counts for {target_col}.").model_dump()],
                "suggested_actions": [
                    {"label": "View as Pie Chart", "query": f"make a pie chart of {target_col}"},
                    {"label": "View as Bar Chart", "query": f"make a bar chart of {target_col}"},
                ]
            }

    # ── Case C: Global Missing Data Audit ───────────────────────────────
    if any(k in q_lower for k in ["missing", "null", "nan", "blanks", "empty", "quality"]):
        from ..audit.data_auditor import audit_missing_values
        audit_res = audit_missing_values(df)
        chart = None
        if audit_res.get("missing_cols"):
            series_data = pd.Series({r["column"]: r["missing"] for r in audit_res["missing_cols"]})
            chart = build_chart_tool(intent="bar_chart", raw_result=series_data, df=df, x_col="column", y_col="missing_count")
        return {
            "ok": True,
            "answer": audit_res["answer"],
            "result": chart,
            "intent": "bar_chart" if chart else "summary",
            "code": "result = df.isnull().sum()[df.isnull().sum() > 0]",
            "insight": audit_res["insight"],
            "system_notice": sys_notice,
            "agent_actions": [AgentAction(agent="AnalyticsAgent", tool="local_pandas_engine", status="completed", message="Audited missing data points.").model_dump()],
            "suggested_actions": audit_res["suggested_actions"],
        }

    # ── Case D: Global Correlation Matrix ───────────────────────────────
    if "correlation" in q_lower or "correlate" in q_lower or "heatmap" in q_lower:
        if len(num_cols) >= 2:
            corr = df[num_cols[:6]].corr().round(2)
            ans = f"### Pearson Correlation Matrix\n\nComputed pairwise correlation across top numeric features: {', '.join(f'`{c}`' for c in num_cols[:6])}."
            return {
                "ok": True,
                "answer": ans,
                "result": {"type": "table", "headers": corr.columns.tolist(), "rows": corr.reset_index().to_dict(orient="records"), "total": len(corr)},
                "intent": "table",
                "code": f"result = df[{num_cols[:6]}].corr()",
                "insight": f"Calculated correlations for {len(num_cols[:6])} numeric dimensions.",
                "system_notice": sys_notice,
                "agent_actions": [AgentAction(agent="AnalyticsAgent", tool="local_pandas_engine", status="completed", message="Computed Pearson correlation matrix.").model_dump()],
            }

    # ── Case E: General Dataset Summary Fallback ────────────────────────
    sample_nums = ", ".join(f"`{c}`" for c in num_cols[:4]) if num_cols else "None"
    sample_cats = ", ".join(f"`{c}`" for c in cat_cols[:4]) if cat_cols else "None"
    return {
        "ok": True,
        "answer": (
            f"### Dataset Overview: {df.shape[0]:,} records ({df.shape[0]:,} rows × {df.shape[1]} columns)\n\n"
            f"• **Numeric features ({len(num_cols)})**: {sample_nums}\n"
            f"• **Categorical features ({len(cat_cols)})**: {sample_cats}\n\n"
            f"You can ask me to analyze distributions (e.g. `distribution of {num_cols[0] if num_cols else df.columns[0]}`), "
            f"compare variables (e.g. `compare {num_cols[0] if num_cols else 'col1'} and {num_cols[1] if len(num_cols)>1 else 'col2'}`), "
            f"or ask CleanerAgent to sanitize your data."
        ),
        "result": None,
        "intent": "summary",
        "code": "result = df.describe()",
        "insight": f"Analyzed {df.shape[0]:,} records across {df.shape[1]} dimensions.",
        "system_notice": sys_notice,
        "agent_actions": [],
    }
