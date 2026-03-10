"""
DataForge — Root Cause Analysis
════════════════════════════════
Segment contribution analysis: given a primary metric and one or more
dimension columns, identifies which segments drove the most change
(or contribute most to the total).

Two modes:
  • contribution  — rank segments by % share of total metric value
  • change        — compare two periods and rank by contribution to Δ

Usage::

    from modules.root_cause import run_root_cause

    result = run_root_cause(
        df        = df,
        metric    = "revenue",
        dimensions = ["region", "product_line"],
        date_col  = "order_date",    # optional
        top_n     = 5,
    )
    # result["drivers"]  → list of dicts sorted by impact
    # result["summary"]  → human-readable summary
    # result["mode"]     → "contribution" | "change"
"""

from __future__ import annotations
import logging
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def _fmt(v: float) -> str:
    """Format a number cleanly (K/M suffix, 2dp)."""
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.1f}K"
    return f"{v:.2f}"


def _split_periods(df: pd.DataFrame, date_col: str):
    """Split df into [first half, second half] by date."""
    try:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        if len(df) < 4:
            return None, None
        mid = df[date_col].median()
        prev = df[df[date_col] <= mid]
        curr = df[df[date_col] >  mid]
        return prev, curr
    except Exception:
        return None, None


def run_root_cause(
    df:          pd.DataFrame,
    metric:      str,
    dimensions:  list[str],
    date_col:    Optional[str] = None,
    top_n:       int = 6,
) -> dict:
    """
    Segment contribution / change analysis.

    Returns::

        {
            "mode":     "contribution" | "change",
            "metric":   str,
            "total":    float,         # total metric value (contribution) or Δ (change)
            "pct_change": float|None,  # overall % change (change mode only)
            "drivers":  [
                {
                    "segment":     str,    # "region=West"
                    "dimension":   str,
                    "value":       str,
                    "contribution": float, # metric value of this segment
                    "pct_share":   float,  # % of total
                    "pct_change":  float|None,  # change mode: % Δ for this segment
                    "impact":      float,  # abs contribution magnitude (for sorting)
                }
            ],
            "summary":  str,
        }
    """
    if metric not in df.columns:
        return {"error": f"Metric column '{metric}' not found", "drivers": []}

    valid_dims = [d for d in dimensions if d in df.columns]
    if not valid_dims:
        return {"error": "No valid dimension columns provided", "drivers": []}

    # ── Try change mode if date column available ──────────────────────────────
    prev_df, curr_df = None, None
    if date_col and date_col in df.columns:
        prev_df, curr_df = _split_periods(df, date_col)

    mode = "change" if (prev_df is not None and curr_df is not None
                        and len(prev_df) >= 2 and len(curr_df) >= 2) else "contribution"

    drivers: list[dict] = []

    for dim in valid_dims:
        unique_vals = df[dim].dropna().unique()
        if len(unique_vals) < 2 or len(unique_vals) > 50:
            continue  # skip low-cardinality or exploding dimensions

        if mode == "change":
            total_prev = pd.to_numeric(prev_df[metric], errors="coerce").sum()
            total_curr = pd.to_numeric(curr_df[metric], errors="coerce").sum()
            delta_total = total_curr - total_prev

            seg_prev = pd.to_numeric(prev_df[metric], errors="coerce")\
                         .groupby(prev_df[dim]).sum()
            seg_curr = pd.to_numeric(curr_df[metric], errors="coerce")\
                         .groupby(curr_df[dim]).sum()
            all_segs = set(seg_prev.index) | set(seg_curr.index)
            for val in all_segs:
                p = seg_prev.get(val, 0.0)
                c = seg_curr.get(val, 0.0)
                delta = c - p
                pct_of_total = (delta / abs(delta_total) * 100) if delta_total != 0 else 0
                pct_seg_chg  = ((c - p) / p * 100) if p != 0 else (float("inf") if c > 0 else 0)
                drivers.append({
                    "segment":     f"{dim} = {val}",
                    "dimension":   dim,
                    "value":       str(val),
                    "contribution": round(delta, 4),
                    "pct_share":   round(pct_of_total, 2),
                    "pct_change":  round(pct_seg_chg, 2) if abs(pct_seg_chg) < 9999 else None,
                    "prev":        round(p, 4),
                    "curr":        round(c, 4),
                    "impact":      abs(delta),
                })
        else:
            # Contribution mode
            series  = pd.to_numeric(df[metric], errors="coerce").fillna(0)
            total   = series.sum()
            grouped = series.groupby(df[dim]).sum()
            for val, contrib in grouped.items():
                pct = (contrib / total * 100) if total != 0 else 0
                drivers.append({
                    "segment":     f"{dim} = {val}",
                    "dimension":   dim,
                    "value":       str(val),
                    "contribution": round(contrib, 4),
                    "pct_share":   round(pct, 2),
                    "pct_change":  None,
                    "impact":      abs(contrib),
                })

    # ── Sort by impact, dedupe top segments per dimension ─────────────────────
    drivers.sort(key=lambda x: x["impact"], reverse=True)

    # Take top_n across all dimensions (already sorted by impact)
    top_drivers = drivers[:top_n * len(valid_dims)]

    # ── Build summary ─────────────────────────────────────────────────────────
    if mode == "change":
        total_prev = pd.to_numeric(prev_df[metric], errors="coerce").sum()
        total_curr = pd.to_numeric(curr_df[metric], errors="coerce").sum()
        delta      = total_curr - total_prev
        pct_change = (delta / abs(total_prev) * 100) if total_prev != 0 else 0
        overall_total = delta
        summary_lines = [
            f"{metric} {'▲' if delta >= 0 else '▼'} {abs(pct_change):.1f}% "
            f"({_fmt(total_prev)} → {_fmt(total_curr)})",
            "",
            "Main drivers:",
        ]
        for d in top_drivers[:top_n]:
            arrow = "▲" if d["contribution"] >= 0 else "▼"
            summary_lines.append(
                f"  {d['segment']}  {arrow} {abs(d['pct_share']):.1f}% of change"
            )
    else:
        total_val     = pd.to_numeric(df[metric], errors="coerce").sum()
        overall_total = total_val
        pct_change    = None
        summary_lines = [
            f"{metric} total: {_fmt(total_val)}",
            "",
            f"Top contributors ({', '.join(valid_dims)}):",
        ]
        for d in top_drivers[:top_n]:
            summary_lines.append(
                f"  {d['segment']}  {d['pct_share']:.1f}%"
            )

    return {
        "mode":       mode,
        "metric":     metric,
        "dimensions": valid_dims,
        "total":      round(float(overall_total), 4),
        "pct_change": round(float(pct_change), 2) if pct_change is not None else None,
        "drivers":    top_drivers[:top_n * 2],  # return more so UI can pick top_n
        "summary":    "\n".join(summary_lines),
    }
