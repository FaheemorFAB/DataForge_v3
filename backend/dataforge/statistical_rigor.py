"""
dataforge/statistical_rigor.py
───────────────────────────────
Rigorous Statistical Hypothesis Testing & Multiple-Testing Correction.
Implements:
  • Family-Wise Multiple-Testing Corrections:
      - Benjamini-Hochberg (BH) False Discovery Rate (FDR) control (fdr_bh)
      - Benjamini-Yekutieli (BY) FDR control for arbitrary dependence (fdr_by)
      - Bonferroni Family-Wise Error Rate (FWER) control
  • Statistical Families:
      - Numeric-Numeric: Pearson & Spearman correlation with exact two-tailed p-values
      - Categorical-Categorical: Chi-Square Independence Test + Cramér's V effect size
      - Numeric-Categorical: One-Way ANOVA F-test + Eta-squared effect size
  • Controlled Insight Discovery:
      - Eradicates Type I error inflation (spurious correlations in wide tables)
      - Ranks validated insights strictly by effect size within FDR-significant hypotheses
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def multipletests_fdr(
    p_values: List[float] | np.ndarray,
    alpha: float = 0.05,
    method: str = "fdr_bh",
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply multiple hypothesis testing correction.

    Parameters:
        p_values: 1D array-like of raw p-values.
        alpha: Target false discovery rate (FDR) or family-wise error rate (FWER).
        method: 'fdr_bh' (Benjamini-Hochberg), 'fdr_by' (Benjamini-Yekutieli),
                or 'bonferroni'.

    Returns:
        (reject_mask, q_values):
            reject_mask: Boolean numpy array where True indicates statistically significant rejection.
            q_values: Adjusted p-values (q-values) corresponding to each test in original order.
    """
    pvals = np.asarray(p_values, dtype=float)
    if pvals.ndim != 1:
        pvals = pvals.ravel()

    m = len(pvals)
    if m == 0:
        return np.array([], dtype=bool), np.array([], dtype=float)

    # Clean NaNs or out-of-range p-values
    pvals_clean = np.where(np.isnan(pvals), 1.0, np.clip(pvals, 0.0, 1.0))

    if method == "bonferroni":
        q_vals = np.clip(pvals_clean * m, 0.0, 1.0)
        reject = q_vals <= alpha
        return reject, q_vals

    # Sort p-values ascending
    sort_idx = np.argsort(pvals_clean)
    inv_idx = np.empty(m, dtype=int)
    inv_idx[sort_idx] = np.arange(m)

    sorted_pvals = pvals_clean[sort_idx]

    if method == "fdr_by":
        # Harmonic number c(m) = sum(1/i for i in 1..m)
        c_m = np.sum(1.0 / np.arange(1, m + 1))
    else:  # 'fdr_bh'
        c_m = 1.0

    # Calculate BH / BY adjusted p-values (q-values)
    # q(k) = min_{j >= k} (p(j) * m * c(m) / j)
    ranks = np.arange(1, m + 1, dtype=float)
    raw_factors = (sorted_pvals * m * c_m) / ranks

    # Enforce monotonicity from right to left
    q_sorted = np.minimum.accumulate(raw_factors[::-1])[::-1]
    q_sorted = np.clip(q_sorted, 0.0, 1.0)

    # Map back to original order
    q_vals = q_sorted[inv_idx]
    reject = q_vals <= alpha

    return reject, q_vals


class MultipleTestingHypothesisEngine:
    """
    Coordinates hypothesis testing across variable families with FDR correction.
    """

    def __init__(self, alpha: float = 0.05, fdr_method: str = "fdr_bh"):
        self.alpha = float(alpha)
        self.fdr_method = fdr_method

    def evaluate_numeric_correlations(
        self,
        df: pd.DataFrame,
        numeric_columns: List[str],
        min_samples: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Scans all pairs of numeric columns, computing exact two-tailed Pearson p-values,
        applying Benjamini-Hochberg FDR control, and ranking by effect size (|r|).
        """
        cols = [c for c in numeric_columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        n_cols = len(cols)
        if n_cols < 2:
            return []

        tests: List[Dict[str, Any]] = []

        for i in range(n_cols):
            for j in range(i + 1, n_cols):
                col_a = cols[i]
                col_b = cols[j]

                sub = df[[col_a, col_b]].dropna()
                n = len(sub)
                if n < min_samples:
                    continue

                x = sub[col_a].to_numpy(dtype=float)
                y = sub[col_b].to_numpy(dtype=float)

                # Check for constant variance
                if np.std(x) < 1e-12 or np.std(y) < 1e-12:
                    continue

                try:
                    res = stats.pearsonr(x, y)
                    r = float(res.statistic)
                    p_val = float(res.pvalue)
                except Exception:
                    continue

                tests.append({
                    "family": "numeric_numeric",
                    "column_a": col_a,
                    "column_b": col_b,
                    "sample_size": n,
                    "statistic": r,
                    "effect_size": abs(r),
                    "raw_p_value": p_val,
                })

        if not tests:
            return []

        # Multiple-testing correction across all tested pairs
        p_values = [t["raw_p_value"] for t in tests]
        reject_mask, q_values = multipletests_fdr(p_values, alpha=self.alpha, method=self.fdr_method)

        results: List[Dict[str, Any]] = []
        for idx, t in enumerate(tests):
            t["q_value"] = float(q_values[idx])
            t["significant"] = bool(reject_mask[idx])
            results.append(t)

        # Sort by significance first, then by effect size descending
        results.sort(key=lambda item: (item["significant"], item["effect_size"]), reverse=True)
        return results

    def evaluate_categorical_associations(
        self,
        df: pd.DataFrame,
        categorical_columns: List[str],
        min_samples: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Scans pairs of categorical columns with Chi-Square Test of Independence
        and Cramér's V effect size with Benjamini-Hochberg FDR control.
        """
        cols = [c for c in categorical_columns if c in df.columns]
        n_cols = len(cols)
        if n_cols < 2:
            return []

        tests: List[Dict[str, Any]] = []

        for i in range(n_cols):
            for j in range(i + 1, n_cols):
                col_a = cols[i]
                col_b = cols[j]

                sub = df[[col_a, col_b]].dropna()
                n = len(sub)
                if n < min_samples:
                    continue

                # Exclude ultra-high cardinality columns (IDs)
                if sub[col_a].nunique() > 50 or sub[col_b].nunique() > 50:
                    continue

                contingency = pd.crosstab(sub[col_a], sub[col_b])
                if contingency.shape[0] < 2 or contingency.shape[1] < 2:
                    continue

                try:
                    chi2, p_val, dof, _ = stats.chi2_contingency(contingency)
                    r_dim, c_dim = contingency.shape
                    k = min(r_dim - 1, c_dim - 1)
                    cramers_v = np.sqrt(chi2 / (n * k)) if (n * k) > 0 else 0.0
                except Exception:
                    continue

                tests.append({
                    "family": "categorical_categorical",
                    "column_a": col_a,
                    "column_b": col_b,
                    "sample_size": n,
                    "statistic": float(chi2),
                    "effect_size": float(np.clip(cramers_v, 0.0, 1.0)),
                    "raw_p_value": float(p_val),
                })

        if not tests:
            return []

        p_values = [t["raw_p_value"] for t in tests]
        reject_mask, q_values = multipletests_fdr(p_values, alpha=self.alpha, method=self.fdr_method)

        results: List[Dict[str, Any]] = []
        for idx, t in enumerate(tests):
            t["q_value"] = float(q_values[idx])
            t["significant"] = bool(reject_mask[idx])
            results.append(t)

        results.sort(key=lambda item: (item["significant"], item["effect_size"]), reverse=True)
        return results
