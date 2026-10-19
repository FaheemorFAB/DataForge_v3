"""
VisualizerAgent Toolkit - Generates typed Chart.js & Table specifications from analysis results.
"""

import logging
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def _safe_val(v: Any) -> Any:
    """Ensure value is JSON serializable and finite."""
    if pd.isna(v) or v is None:
        return None
    if isinstance(v, (np.floating, float)):
        return round(float(v), 4) if np.isfinite(v) else None
    if isinstance(v, (np.integer, int)):
        return int(v)
    return str(v)

def _safe_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{k: _safe_val(v) for k, v in row.items()} for row in records]

CHART_PALETTE = [
    "#6366f1",  # Indigo
    "#8b5cf6",  # Violet
    "#ec4899",  # Pink
    "#06b6d4",  # Cyan
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
    "#f43f5e",  # Rose
    "#3b82f6",  # Blue
    "#14b8a6",  # Teal
    "#a855f7",  # Purple
]

def build_chart_tool(
    intent: str,
    raw_result: Any,
    df: pd.DataFrame,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    top_n: Optional[int] = 10,
    allow_type_switch: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Transforms analytical outputs into full-featured, structured Chart.js specifications.
    Guarantees compatibility with frontend Chart components in Workspace and ChatSidebar.
    """
    try:
        norm_intent = intent.lower().replace("-", "_")
        
        # 1. Scatter Chart
        if norm_intent in ("scatter_chart", "scatter"):
            num_cols = df.select_dtypes(include=np.number).columns.tolist()
            x = x_col if x_col and x_col in df.columns else (num_cols[0] if num_cols else None)
            y = y_col if y_col and y_col in df.columns else (num_cols[1] if len(num_cols) > 1 else None)
            if x and y:
                clean_subset = df[[x, y]].dropna().head(300)
                pts = [
                    {"x": _safe_val(r[x]), "y": _safe_val(r[y])}
                    for r in clean_subset.to_dict("records")
                ]
                return {
                    "type": "scatter_chart",
                    "points": pts,
                    "x_label": x,
                    "y_label": y,
                    "color": "#6366f1",
                    "total_points": len(pts),
                    "allow_type_switch": False,
                }

        # 2. Categorical & Continuous Charts (Pie, Doughnut, Bar, Histogram, Line)
        if norm_intent in ("bar_chart", "bar", "histogram", "line_chart", "line", "pie_chart", "pie", "doughnut_chart", "doughnut", "donut"):
            if isinstance(raw_result, pd.Series):
                series = raw_result
                lx = str(raw_result.index.name or x_col or "Category")
                ly = str(y_col or "Value")
            elif isinstance(raw_result, pd.DataFrame) and raw_result.shape[1] >= 2:
                series = raw_result.iloc[:, 1]
                series.index = raw_result.iloc[:, 0].values
                lx, ly = str(raw_result.columns[0]), str(raw_result.columns[1])
            elif x_col and x_col in df.columns:
                if y_col and y_col in df.columns:
                    series = df.groupby(x_col)[y_col].mean().sort_values(ascending=False)
                    lx, ly = x_col, f"Avg {y_col}"
                else:
                    series = df[x_col].value_counts()
                    lx, ly = x_col, "Count"
            else:
                return None

            if top_n and top_n > 0:
                series = series.head(int(top_n))

            # Determine normalized chart type
            if norm_intent in ("pie_chart", "pie"):
                chart_type = "pie_chart"
            elif norm_intent in ("doughnut_chart", "doughnut", "donut"):
                chart_type = "doughnut_chart"
            elif norm_intent in ("line_chart", "line"):
                chart_type = "line_chart"
            elif norm_intent == "histogram":
                chart_type = "histogram"
            else:
                chart_type = "bar_chart"

            labels = [str(i) for i in series.index]
            values = [_safe_val(v) or 0 for v in series]
            total_sum = sum(v for v in values if isinstance(v, (int, float))) or 1.0
            percentages = [round((v / total_sum) * 100, 1) if isinstance(v, (int, float)) else 0 for v in values]
            colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]

            return {
                "type": chart_type,
                "labels": labels,
                "values": values,
                "percentages": percentages,
                "colors": colors,
                "x_label": lx,
                "y_label": ly,
                "title": f"{ly} by {lx}" if lx != ly else lx,
                "allow_type_switch": allow_type_switch,
            }

        # 3. Table
        if norm_intent == "table":
            tbl = raw_result if isinstance(raw_result, pd.DataFrame) else df.head(50)
            return {
                "type": "table",
                "headers": tbl.columns.tolist(),
                "rows": _safe_rows(tbl.head(100).to_dict("records")),
                "total": len(tbl),
            }

        # 4. Metric Card
        if norm_intent == "metric":
            val = raw_result
            if isinstance(val, (pd.Series, pd.DataFrame)):
                val = val.iloc[0] if len(val) else None
            if val is not None:
                numeric_val = _safe_val(val)
                if numeric_val is not None:
                    return {"type": "metric", "value": numeric_val, "label": x_col or y_col or "Metric"}

    except Exception as exc:
        logger.warning("[VisualizerAgent] Failed to construct chart spec: %s", exc)

    return None
