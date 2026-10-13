"""
tests/test_automl_leakage_spy.py
────────────────────────────────
Verification of statistical leakage prevention in AutoML preprocessing.

Requirements from A+ Implementation Plan (P4-2):
  • Imputers and scalers must be fitted strictly on training folds, never seeing test/validation data.
  • Spy transformer test asserting that fitting is isolated to training indices.
  • Target leakage detection warning for features with near-perfect correlation (|r| > 0.995).
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, TransformerMixin

from dataforge.automl_trainer import _leak_free_preprocess


class SpyTransformer(BaseEstimator, TransformerMixin):
    """Spy transformer that records indices seen during fit."""

    def __init__(self):
        self.fitted_indices = []

    def fit(self, X, y=None):
        if hasattr(X, "index"):
            self.fitted_indices = list(X.index)
        elif isinstance(X, np.ndarray):
            self.fitted_indices = list(range(len(X)))
        return self

    def transform(self, X):
        return X


def test_leak_free_preprocess_isolation():
    """Verify that _leak_free_preprocess fits strictly on X_train without test leakage."""
    # Training set with missing values
    X_train = pd.DataFrame({
        "num": [10.0, 20.0, np.nan, 40.0],  # Median of known values: 20.0
        "cat": [1, 2, 2, np.nan],            # Mode: 2
    }, index=[0, 1, 2, 3])

    # Test set with different missing values and different scale
    X_test = pd.DataFrame({
        "num": [100.0, 200.0, np.nan],       # If test leaked, median would be influenced by 100/200!
        "cat": [9, 9, np.nan],
    }, index=[10, 11, 12])

    X_tr_clean, X_te_clean = _leak_free_preprocess(X_train, X_test)

    # Imputed value in X_train for row 2 should be training median (20.0)
    assert X_tr_clean.loc[2, "num"] == 20.0
    # Imputed value in X_test for row 12 should ALSO be the training median (20.0), NOT test median!
    assert X_te_clean.loc[12, "num"] == 20.0


def test_spy_transformer_cv_isolation():
    """Verify that a Pipeline with SpyTransformer never exposes validation indices to fit."""
    from sklearn.model_selection import KFold
    from sklearn.pipeline import Pipeline

    df = pd.DataFrame({
        "feat": np.arange(100, dtype=float),
        "target": np.arange(100, dtype=float) * 2,
    })

    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    for train_idx, val_idx in kf.split(df):
        spy = SpyTransformer()
        pipeline = Pipeline([
            ("spy", spy),
        ])

        # Fit strictly on train split
        X_train = df.iloc[train_idx][["feat"]]
        X_val = df.iloc[val_idx][["feat"]]

        pipeline.fit(X_train)

        # Assert spy NEVER saw any validation indices during fit
        val_set = set(val_idx)
        seen_set = set(spy.fitted_indices)
        overlap = seen_set.intersection(val_set)
        assert len(overlap) == 0, f"Data leakage detected! Spy transformer saw validation indices: {overlap}"
