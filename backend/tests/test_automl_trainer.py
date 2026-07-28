"""
tests/test_automl_trainer.py
----------------------------
Unit tests for the improved DataForge AutoML pipeline.
Tests all new functions: _downcast_dtypes, _remove_low_variance,
_smart_sample, _adaptive_time_budget, _detect_imbalance, _impute_features,
and the full run_automl pipeline on synthetic data.

Run with:
    cd backend
    python -m pytest tests/test_automl_trainer.py -v
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Make sure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dataforge.automl_trainer import (
    _adaptive_time_budget,
    _build_leaderboard,
    _detect_imbalance,
    _detect_task,
    _downcast_dtypes,
    _encode_features,
    _impute_features,
    _remove_low_variance,
    _smart_sample,
    get_json_result,
    run_automl,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def regression_df():
    """Small numeric regression dataset."""
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "feat_a": rng.normal(0, 1, 200),
        "feat_b": rng.normal(5, 2, 200),
        "target": rng.normal(10, 3, 200),
    })


@pytest.fixture
def classification_df():
    """Small binary classification dataset (balanced)."""
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        "feat_x": rng.normal(0, 1, 300),
        "feat_y": rng.normal(0, 1, 300),
        "label":  rng.integers(0, 2, 300),
    })


@pytest.fixture
def imbalanced_df():
    """Highly imbalanced binary classification (5% minority)."""
    rng = np.random.default_rng(2)
    n = 400
    labels = np.zeros(n, dtype=int)
    labels[:20] = 1  # 5% positive class
    rng.shuffle(labels)
    return pd.DataFrame({
        "feat_a": rng.normal(0, 1, n),
        "label":  labels,
    })


@pytest.fixture
def large_df():
    """Synthetic dataset > 50k rows to test smart sampling."""
    rng = np.random.default_rng(3)
    n = 60_000
    return pd.DataFrame({
        "a": rng.normal(0, 1, n),
        "b": rng.normal(0, 1, n),
        "target": rng.integers(0, 3, n),
    })


@pytest.fixture
def df_with_nans():
    """DataFrame with NaN values for imputation testing."""
    rng = np.random.default_rng(4)
    df = pd.DataFrame({
        "num_col":  rng.normal(0, 1, 100).astype(float),
        "cat_col":  rng.integers(0, 3, 100).astype(float),
        "target":   rng.integers(0, 2, 100),
    })
    df.loc[::5, "num_col"] = np.nan   # 20% NaN in numeric
    df.loc[::7, "cat_col"] = np.nan   # ~14% NaN in categorical
    return df


# ─────────────────────────────────────────────────────────────────────────────
# _detect_task
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectTask:
    def test_string_target_is_classification(self):
        y = pd.Series(["cat", "dog", "cat", "bird"] * 10)
        assert _detect_task(y) == "classification"

    def test_few_unique_ints_is_classification(self):
        y = pd.Series([0, 1, 2] * 100)
        assert _detect_task(y) == "classification"

    def test_continuous_float_is_regression(self):
        rng = np.random.default_rng(0)
        y = pd.Series(rng.normal(0, 1, 1000))
        assert _detect_task(y) == "regression"


# ─────────────────────────────────────────────────────────────────────────────
# _downcast_dtypes
# ─────────────────────────────────────────────────────────────────────────────

class TestDowncastDtypes:
    def test_float64_becomes_float32(self):
        df = pd.DataFrame({"a": np.array([1.0, 2.0, 3.0], dtype=np.float64)})
        result = _downcast_dtypes(df)
        assert result["a"].dtype == np.float32

    def test_int64_becomes_int32_when_safe(self):
        df = pd.DataFrame({"b": np.array([1, 2, 3], dtype=np.int64)})
        result = _downcast_dtypes(df)
        assert result["b"].dtype == np.int32

    def test_large_int64_stays_int64(self):
        df = pd.DataFrame({"c": np.array([3_000_000_000], dtype=np.int64)})
        result = _downcast_dtypes(df)
        assert result["c"].dtype == np.int64

    def test_values_preserved(self):
        df = pd.DataFrame({"v": [1.5, 2.5, 3.5]})
        result = _downcast_dtypes(df)
        np.testing.assert_allclose(result["v"].values, df["v"].values, rtol=1e-5)

    def test_original_not_mutated(self):
        df = pd.DataFrame({"a": np.array([1.0], dtype=np.float64)})
        _ = _downcast_dtypes(df)
        assert df["a"].dtype == np.float64


# ─────────────────────────────────────────────────────────────────────────────
# _remove_low_variance
# ─────────────────────────────────────────────────────────────────────────────

class TestRemoveLowVariance:
    def test_constant_column_is_dropped(self):
        df = pd.DataFrame({"const": [1.0] * 50, "varies": range(50)})
        result, dropped = _remove_low_variance(df)
        assert "const" in dropped
        assert "const" not in result.columns

    def test_varying_columns_kept(self):
        df = pd.DataFrame({"a": range(50), "b": range(50, 100)})
        result, dropped = _remove_low_variance(df)
        assert dropped == []
        assert list(result.columns) == ["a", "b"]

    def test_empty_df_handled(self):
        df = pd.DataFrame()
        result, dropped = _remove_low_variance(df)
        assert dropped == []


# ─────────────────────────────────────────────────────────────────────────────
# _smart_sample
# ─────────────────────────────────────────────────────────────────────────────

class TestSmartSample:
    def test_small_dataset_not_sampled(self, regression_df):
        X = regression_df.drop(columns=["target"])
        y = regression_df["target"]
        X_s, y_s, sampled = _smart_sample(X, y, task="regression", max_rows=10_000)
        assert not sampled
        assert len(X_s) == len(X)

    def test_large_dataset_is_sampled(self, large_df):
        X = large_df.drop(columns=["target"])
        y = large_df["target"]
        X_s, y_s, sampled = _smart_sample(X, y, task="classification", max_rows=50_000)
        assert sampled
        assert len(X_s) <= 50_000

    def test_indices_align_after_sample(self, large_df):
        X = large_df.drop(columns=["target"])
        y = large_df["target"]
        X_s, y_s, _ = _smart_sample(X, y, task="classification", max_rows=50_000)
        assert list(X_s.index) == list(y_s.index)


# ─────────────────────────────────────────────────────────────────────────────
# _adaptive_time_budget
# ─────────────────────────────────────────────────────────────────────────────

class TestAdaptiveTimeBudget:
    def test_tiny_dataset_gets_at_least_20s(self):
        assert _adaptive_time_budget(500, 10, 10) == 20

    def test_large_dataset_gets_at_least_60s(self):
        assert _adaptive_time_budget(100_000, 50, 30) == 60

    def test_user_budget_honoured_when_above_minimum(self):
        assert _adaptive_time_budget(500, 10, 120) == 120

    def test_medium_dataset_floors(self):
        result = _adaptive_time_budget(5_000, 20, 5)
        assert result == 30


# ─────────────────────────────────────────────────────────────────────────────
# _detect_imbalance
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectImbalance:
    def test_balanced_not_flagged(self):
        y = pd.Series([0, 1] * 100)
        report = _detect_imbalance(y)
        assert not report["is_imbalanced"]
        assert report["recommended_metric"] == "auto"

    def test_severe_imbalance_flagged(self):
        y = pd.Series([0] * 95 + [1] * 5)
        report = _detect_imbalance(y)
        assert report["is_imbalanced"]
        assert report["recommended_metric"] == "roc_auc"

    def test_multiclass_imbalance_gets_f1(self):
        y = pd.Series([0] * 90 + [1] * 5 + [2] * 5)
        report = _detect_imbalance(y)
        assert report["recommended_metric"] == "f1"

    def test_minority_ratio_correct(self):
        y = pd.Series([0] * 90 + [1] * 10)
        report = _detect_imbalance(y)
        assert abs(report["minority_ratio"] - 0.10) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# _impute_features
# ─────────────────────────────────────────────────────────────────────────────

class TestImputeFeatures:
    def test_no_nans_after_imputation(self, df_with_nans):
        df = df_with_nans.drop(columns=["target"])
        result = _impute_features(df)
        assert not result.isnull().any().any()

    def test_shape_preserved(self, df_with_nans):
        df = df_with_nans.drop(columns=["target"])
        result = _impute_features(df)
        assert result.shape == df.shape


# ─────────────────────────────────────────────────────────────────────────────
# _encode_features
# ─────────────────────────────────────────────────────────────────────────────

class TestEncodeFeatures:
    def test_string_columns_become_numeric(self):
        df = pd.DataFrame({"cat": ["a", "b", "a", "c"], "num": [1.0, 2.0, 3.0, 4.0]})
        result = _encode_features(df)
        assert pd.api.types.is_numeric_dtype(result["cat"])

    def test_datetime_columns_dropped(self):
        df = pd.DataFrame({
            "dt": pd.date_range("2023-01-01", periods=5),
            "val": range(5),
        })
        result = _encode_features(df)
        assert "dt" not in result.columns

    def test_no_minus1_sentinel_in_output(self):
        df = pd.DataFrame({"cat": ["a", None, "b", None, "c"]})
        result = _encode_features(df)
        assert (result["cat"] == -1).sum() == 0


# ─────────────────────────────────────────────────────────────────────────────
# run_automl — end-to-end (fast smoke tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAutoml:
    def test_regression_returns_no_error(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        assert result.get("error") is None

    def test_regression_has_expected_metrics(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        metrics = result.get("metrics", {})
        assert "MAE"  in metrics
        assert "RMSE" in metrics
        assert "R²"   in metrics
        assert "MAPE" in metrics

    def test_classification_returns_no_error(self, classification_df):
        result = run_automl(classification_df, "label", time_budget=15)
        assert result.get("error") is None

    def test_classification_has_expected_metrics(self, classification_df):
        result = run_automl(classification_df, "label", time_budget=15)
        metrics = result.get("metrics", {})
        assert "Accuracy"      in metrics
        assert "F1 (weighted)" in metrics
        assert "Precision"     in metrics
        assert "Recall"        in metrics

    def test_timing_breakdown_present(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        tb = result.get("timing_breakdown", {})
        assert "preprocessing_s"  in tb
        assert "flaml_training_s" in tb
        assert "evaluation_s"     in tb
        assert "total_s"          in tb

    def test_leaderboard_is_list(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        assert isinstance(result.get("leaderboard"), list)
        assert len(result["leaderboard"]) > 0

    def test_imbalanced_detection_switches_metric(self, imbalanced_df):
        result = run_automl(imbalanced_df, "label", time_budget=15)
        assert result.get("error") is None
        report = result.get("imbalance_report", {})
        assert report.get("is_imbalanced") is True
        assert report.get("recommended_metric") == "roc_auc"

    def test_get_json_result_strips_model_pkl(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        safe   = get_json_result(result)
        assert "model_pkl" not in safe

    def test_model_pkl_is_bytes(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        assert isinstance(result.get("model_pkl"), bytes)
        assert len(result["model_pkl"]) > 0

    def test_dropped_cols_key_present(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        assert "dropped_cols" in result

    def test_was_sampled_false_for_small_data(self, regression_df):
        result = run_automl(regression_df, "target", time_budget=15)
        assert result.get("was_sampled") is False

    def test_invalid_target_col_returns_error(self, regression_df):
        result = run_automl(regression_df, "nonexistent_col", time_budget=10)
        assert result.get("error") is not None
