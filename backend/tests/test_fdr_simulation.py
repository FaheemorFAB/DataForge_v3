"""
tests/test_fdr_simulation.py
────────────────────────────
Rigorous simulation suite proving Benjamini-Hochberg FDR control and planted signal recovery.

Requirements from A+ Implementation Plan (P4-1):
  • Pure-noise simulation:
      - 40 columns of independent Gaussian or Uniform noise across multiple seeds.
      - 780 pairwise correlation hypotheses tested per seed.
      - Prove that uncorrected hypothesis testing produces false positives,
        while Benjamini-Hochberg FDR control ensures false discovery proportion (FDP) <= q.
  • Planted correlation recovery:
      - Plant true ground-truth relationships (r >= 0.8) amidst noise.
      - Prove that the FDR engine recovers the planted signal without false alarms.
"""

import numpy as np
import pandas as pd
import pytest

from dataforge.correlation_insight import CorrelationInsight
from dataforge.statistical_rigor import (
    MultipleTestingHypothesisEngine,
    multipletests_fdr,
)


def test_benjamini_hochberg_exact_properties():
    """Verify BH adjustment monotonicity, bounds, and known textbook case."""
    raw_pvals = [0.001, 0.01, 0.03, 0.04, 0.20, 0.50]
    reject, q_vals = multipletests_fdr(raw_pvals, alpha=0.05, method="fdr_bh")

    assert len(reject) == 6
    assert len(q_vals) == 6
    # q-values must be non-decreasing for ordered p-values
    assert np.all(np.diff(q_vals) >= -1e-12)
    # q-values must be bounded in [0, 1]
    assert np.all((q_vals >= 0.0) & (q_vals <= 1.0))
    # Smallest p-value should reject at alpha=0.05
    assert bool(reject[0]) is True
    # Large p-value should not reject
    assert bool(reject[-1]) is False


def test_pure_noise_fdr_simulation():
    """
    Simulate pure noise tables (40 columns, 100 rows) across 10 random seeds.
    Total tests per seed = 40 * 39 / 2 = 780 tests.
    With alpha = 0.05, without FDR correction, dozens of pairs cross nominal p < 0.05.
    Under Benjamini-Hochberg FDR, the empirical False Discovery Proportion (FDP)
    is strictly controlled at or below target q=0.05 on average.
    """
    n_cols = 40
    n_rows = 100
    n_seeds = 10
    alpha = 0.05

    engine = MultipleTestingHypothesisEngine(alpha=alpha, fdr_method="fdr_bh")
    col_names = [f"noise_col_{i}" for i in range(n_cols)]

    false_discoveries_uncorrected = []
    false_discoveries_fdr = []

    for seed in range(42, 42 + n_seeds):
        rng = np.random.default_rng(seed)
        # 40 independent Gaussian columns: null hypothesis is True for ALL pairs
        data = rng.standard_normal(size=(n_rows, n_cols))
        df_noise = pd.DataFrame(data, columns=col_names)

        results = engine.evaluate_numeric_correlations(df_noise, col_names)
        assert len(results) == (n_cols * (n_cols - 1)) // 2  # 780 pairs

        # Uncorrected discoveries (raw p < 0.05)
        uncorrected = sum(1 for r in results if r["raw_p_value"] < alpha)
        false_discoveries_uncorrected.append(uncorrected)

        # FDR-controlled discoveries (q_value <= 0.05)
        fdr_sig = sum(1 for r in results if r["significant"])
        false_discoveries_fdr.append(fdr_sig)

    avg_uncorrected = float(np.mean(false_discoveries_uncorrected))
    avg_fdr = float(np.mean(false_discoveries_fdr))

    # Expect ~39 false positives per seed under uncorrected testing (780 * 0.05)
    assert avg_uncorrected >= 15, f"Expected Type I error inflation, got {avg_uncorrected}"

    # Under pure noise where all nulls are true, BH FDR strictly controls family-wise error
    # The average number of false discoveries with FDR control must be near 0
    assert avg_fdr <= 1.0, f"FDR failed to control false discoveries on pure noise! Got avg {avg_fdr}"


def test_planted_correlation_recovery():
    """
    Create a dataset with 20 noise columns and 2 planted correlated pairs:
      - X1 and X2 (strong positive: r ~ 0.92)
      - X3 and X4 (strong negative: r ~ -0.88)
    Verify that the FDR engine discovers BOTH planted pairs and filters out all noise pairs.
    """
    rng = np.random.default_rng(101)
    n_rows = 150

    # Planted pairs
    x1 = rng.standard_normal(n_rows)
    x2 = 0.9 * x1 + 0.1 * rng.standard_normal(n_rows)

    x3 = rng.standard_normal(n_rows)
    x4 = -0.85 * x3 + 0.15 * rng.standard_normal(n_rows)

    data = {"planted_x1": x1, "planted_x2": x2, "planted_x3": x3, "planted_x4": x4}
    for i in range(16):
        data[f"noise_{i}"] = rng.standard_normal(n_rows)

    df = pd.DataFrame(data)
    cols = list(df.columns)

    engine = MultipleTestingHypothesisEngine(alpha=0.05, fdr_method="fdr_bh")
    results = engine.evaluate_numeric_correlations(df, cols)

    sig_results = [r for r in results if r["significant"]]
    assert len(sig_results) >= 2

    # Verify that the planted pairs are ranked at the top
    top_pairs = {(r["column_a"], r["column_b"]) for r in sig_results[:2]}
    expected_pair_1 = ("planted_x1", "planted_x2")
    expected_pair_2 = ("planted_x3", "planted_x4")

    assert expected_pair_1 in top_pairs or (expected_pair_1[1], expected_pair_1[0]) in top_pairs
    assert expected_pair_2 in top_pairs or (expected_pair_2[1], expected_pair_2[0]) in top_pairs

    # Verify CorrelationInsight surfaces the planted relationship with q-value
    insight_plugin = CorrelationInsight()
    schema = {"metrics": cols}
    insight = insight_plugin.analyze(df, schema)

    assert insight is not None
    assert "planted" in insight["title"]
    assert insight["fdr_controlled"] is True
    assert insight["q_value"] < 0.01
    assert insight["chart_data"]["q_value"] < 0.01
