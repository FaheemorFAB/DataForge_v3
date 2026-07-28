"""
Base class for all DataForge insight plugins.

Every insight module inherits BaseInsight and implements:
  - applicable(df, schema) → bool
  - analyze(df, schema)    → dict | None

Standard output dict:
{
    "title":       str,          # Short insight name
    "description": str,          # Human-readable finding
    "importance":  float,        # 0.0–1.0 (used for ranking)
    "type":        str,          # trend | ranking | correlation | anomaly | distribution | contribution | segment | change
    "chart":       str | None,   # line | bar | scatter | histogram | None
    "chart_data":  dict | None,  # {labels, values} or None
    "metric":      str | None,   # Column name being analysed
}
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseInsight(ABC):
    name: str = "base"

    @abstractmethod
    def applicable(self, df: pd.DataFrame, schema: dict) -> bool:
        """Return True if this insight can run on the given dataset / schema."""

    @abstractmethod
    def analyze(self, df: pd.DataFrame, schema: dict) -> dict | None:
        """Run analysis and return a standard insight dict, or None if nothing notable."""

    # ── shared helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _safe_float(v) -> float:
        """Convert numpy / NaN values to a plain Python float."""
        try:
            f = float(v)
            if f != f:      # NaN
                return 0.0
            return f
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    @staticmethod
    def _is_financial(metric: str) -> bool:
        if not metric:
            return False
        m_lower = str(metric).lower()
        return any(kw in m_lower for kw in ["price", "revenue", "cost", "sales", "spend", "profit"])

    @classmethod
    def _format_value(cls, metric: str, val: float) -> str:
        """Format value cleanly with currency or commas based on metric name."""
        val = cls._safe_float(val)
        is_fin = cls._is_financial(metric)
        prefix = "$" if is_fin else ""
        abs_val = abs(val)
        if abs_val >= 1_000_000:
            formatted = f"{val / 1_000_000:.1f}M"
        elif abs_val >= 1_000:
            formatted = f"{val / 1_000:.1f}K"
        else:
            if is_fin:
                formatted = f"{val:.2f}"
            else:
                formatted = f"{val:g}"
        if formatted.endswith(".0K"):
            formatted = formatted[:-3] + "K"
        elif formatted.endswith(".0M"):
            formatted = formatted[:-3] + "M"
        return f"{prefix}{formatted}"

    @classmethod
    def _format_precise(cls, metric: str, val: float) -> str:
        """Format value with thousands separators, and optionally currency symbol."""
        val = cls._safe_float(val)
        is_fin = cls._is_financial(metric)
        prefix = "$" if is_fin else ""
        if is_fin:
            return f"{prefix}{val:,.2f}"
        else:
            if val.is_integer():
                return f"{val:,.0f}"
            return f"{val:,.2f}"
