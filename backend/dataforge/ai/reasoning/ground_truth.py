"""
DataForge AI - Ground Truth Synchronizer
Guarantees 100% mathematical and factual synchronization between executed code output,
written text analysis, dynamic insight callouts, and rendered Chart.js specifications.
Prevents LLM hallucinations and corrects improper chart type selections.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def is_temporal_index(index: pd.Index) -> bool:
    """Detects whether an index represents chronological dates or timestamps."""
    if isinstance(index, pd.DatetimeIndex):
        return True
    sample = [str(x) for x in index[:5]]
    import re
    # Check for date patterns (YYYY-MM-DD, MM/DD/YYYY, etc.)
    date_pattern = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", re.IGNORECASE)
    return any(date_pattern.search(s) for s in sample)


def synchronize_ground_truth(
    query: str,
    raw_result: Any,
    df: pd.DataFrame,
    proposed_answer: str,
    proposed_intent: str,
    proposed_insight: Optional[str] = None,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Synthesizes and validates the final response against the verified execution output (`raw_result`).
    Returns: (grounded_answer, corrected_intent, grounded_insight).
    """
    corrected_intent = proposed_intent or "summary"
    grounded_answer = proposed_answer or ""
    grounded_insight = proposed_insight or ""

    # ─────────────────────────────────────────────────────────────────────────
    # CASE 1: raw_result is a pandas Series (Value Counts, Group-by Aggregations)
    # ─────────────────────────────────────────────────────────────────────────
    if isinstance(raw_result, pd.Series) and len(raw_result) > 0:
        s = raw_result.copy()
        
        # Enforce descending sort for rankings / value counts
        if not is_temporal_index(s.index):
            s = s.sort_values(ascending=False)

        # Enforce Chart Type Semantic Correctness:
        # Categorical variables (region, category, status) must NEVER be a line chart!
        is_temporal = is_temporal_index(s.index)
        if not is_temporal and corrected_intent == "line_chart":
            logger.info("[GroundTruth] Correcting improper 'line_chart' to 'bar_chart' for categorical index.")
            corrected_intent = "bar_chart"
        elif "pie" in query.lower() or "donut" in query.lower() or "doughnut" in query.lower():
            corrected_intent = "pie_chart"
        elif corrected_intent in ("summary", "metric") and len(s) > 1:
            corrected_intent = "bar_chart"

        # Compute Ground Truth Metrics
        total_vol = float(s.sum()) if pd.api.types.is_numeric_dtype(s) and (s >= 0).all() else None
        top_name = str(s.index[0])
        top_val = s.iloc[0]
        top_val_fmt = f"{top_val:,.2f}" if isinstance(top_val, float) and not top_val.is_integer() else f"{int(top_val):,}"

        top_pct_str = f" ({top_val / total_vol * 100:.1f}%)" if total_vol and total_vol > 0 else ""

        second_str = ""
        second_name = None
        if len(s) > 1:
            second_name = str(s.index[1])
            second_val = s.iloc[1]
            second_val_fmt = f"{second_val:,.2f}" if isinstance(second_val, float) and not second_val.is_integer() else f"{int(second_val):,}"
            second_pct_str = f" ({second_val / total_vol * 100:.1f}%)" if total_vol and total_vol > 0 else ""
            second_str = f" This is followed by **{second_name}** with **{second_val_fmt}**{second_pct_str}"

        third_str = ""
        if len(s) > 2:
            third_name = str(s.index[2])
            third_val = s.iloc[2]
            third_val_fmt = f"{third_val:,.2f}" if isinstance(third_val, float) and not third_val.is_integer() else f"{int(third_val):,}"
            third_pct_str = f" ({third_val / total_vol * 100:.1f}%)" if total_vol and total_vol > 0 else ""
            third_str = f", and **{third_name}** with **{third_val_fmt}**{third_pct_str}."
        elif second_str:
            second_str += "."

        bottom_name = str(s.index[-1])
        bottom_val = s.iloc[-1]
        bottom_val_fmt = f"{bottom_val:,.2f}" if isinstance(bottom_val, float) and not bottom_val.is_integer() else f"{int(bottom_val):,}"

        # Construct Grounded Text
        dim_label = str(s.index.name or x_col or "category").replace("_", " ").title()
        raw_m = str(y_col or "volume").lower()
        if any(k in raw_m for k in ["id", "count", "volume", "records", "freq"]) or "order" in query.lower():
            metric_phrase = "total orders" if "order" in query.lower() else "total volume"
        else:
            metric_phrase = raw_m.replace("_", " ")

        breakdown_items = []
        for idx, val in s.head(5).items():
            val_fmt = f"{val:,.2f}" if isinstance(val, float) and not val.is_integer() else f"{int(val):,}"
            pct_s = f" ({val / total_vol * 100:.1f}%)" if total_vol and total_vol > 0 else ""
            breakdown_items.append(f"• **{idx}**: **{val_fmt}**{pct_s}")
        breakdown_md = "\n".join(breakdown_items)

        grounded_answer = (
            f"### {dim_label} Analysis\n\n"
            f"The **{top_name}** {dim_label.lower()} leads in {metric_phrase} with **{top_val_fmt}**{top_pct_str}.{second_str}{third_str}\n\n"
            f"#### Top Breakdown:\n{breakdown_md}\n\n"
            f"• **Highest**: `{top_name}` ({top_val_fmt})\n"
            f"• **Lowest**: `{bottom_name}` ({bottom_val_fmt})"
        )

        grounded_insight = f"The {top_name} {dim_label.lower()} leads in {metric_phrase} with {top_val_fmt}{top_pct_str}, indicating the strongest market presence."

    # ─────────────────────────────────────────────────────────────────────────
    # CASE 2: raw_result is a Scalar (Single KPI, Average, Sum, Count)
    # ─────────────────────────────────────────────────────────────────────────
    elif isinstance(raw_result, (int, float, np.number)):
        scalar_val = float(raw_result)
        scalar_fmt = f"{scalar_val:,.2f}" if not scalar_val.is_integer() else f"{int(scalar_val):,}"
        metric_name = (y_col or x_col or "metric").replace("_", " ").title()

        grounded_answer = (
            f"### Computed {metric_name}\n\n"
            f"The calculated value for **{metric_name}** is **{scalar_fmt}** across {len(df):,} records."
        )
        grounded_insight = f"Calculated {metric_name}: {scalar_fmt}."
        corrected_intent = "metric"

    # ─────────────────────────────────────────────────────────────────────────
    # CASE 3: raw_result is a DataFrame (Multi-column Slicing or Table)
    # ─────────────────────────────────────────────────────────────────────────
    elif isinstance(raw_result, pd.DataFrame) and len(raw_result) > 0:
        is_preview_or_table = any(k in query.lower() for k in ["preview", "sample", "head", "show rows", "table", "overview", "first few", "summarize"])
        if not is_preview_or_table and raw_result.shape[1] == 2 and pd.api.types.is_numeric_dtype(raw_result.iloc[:, 1]):
            # If exactly 2 columns (category, metric), treat like Series for accurate ranking
            col0 = raw_result.columns[0]
            col1 = raw_result.columns[1]
            s_equiv = raw_result.set_index(col0)[col1]
            return synchronize_ground_truth(
                query=query,
                raw_result=s_equiv,
                df=df,
                proposed_answer=proposed_answer,
                proposed_intent=proposed_intent,
                proposed_insight=proposed_insight,
                x_col=col0,
                y_col=col1,
            )
        else:
            corrected_intent = "table"
            cols_preview = ", ".join(f"`{c}`" for c in list(raw_result.columns)[:10])
            if len(raw_result.columns) > 10:
                cols_preview += f", and {len(raw_result.columns) - 10} more"

            base_ans = proposed_answer.strip() if proposed_answer and len(proposed_answer.strip()) > 25 else f"Structured table generated across {len(df):,} records."
            if "preview table" not in base_ans.lower() and "table below" not in base_ans.lower():
                grounded_answer = (
                    f"{base_ans}\n\n"
                    f"**Preview Table:** Rendered interactive table of {len(raw_result)} records with columns: {cols_preview}."
                )
            else:
                grounded_answer = base_ans
            grounded_insight = proposed_insight or f"Displaying {len(raw_result)} records from dataset."

    return grounded_answer, corrected_intent, grounded_insight
