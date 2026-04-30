"""
Quick integration test for the AutoML trainer inside Docker.
Run: docker compose exec web python tests/run_integration_test.py
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/app")

from dataforge.automl_trainer import (
    _adaptive_time_budget, _detect_imbalance, _detect_task,
    _downcast_dtypes, _encode_features, _impute_features,
    _remove_low_variance, _smart_sample, get_json_result, run_automl,
)

rng    = np.random.default_rng(0)
passed = 0
failed = 0

def ok(label):
    global passed
    passed += 1
    print(f"  PASS  {label}")

def fail(label, detail=""):
    global failed
    failed += 1
    print(f"  FAIL  {label}: {detail}")

print("\n── Unit Tests ──────────────────────────────────────────────────────────\n")

# _detect_task
try:
    assert _detect_task(pd.Series(["a","b","a"]*10)) == "classification"
    assert _detect_task(pd.Series(rng.normal(0,1,1000))) == "regression"
    ok("_detect_task: string → classification, continuous → regression")
except Exception as e:
    fail("_detect_task", e)

# _downcast_dtypes
try:
    df = pd.DataFrame({"f": np.array([1.0, 2.0], dtype=np.float64),
                       "i": np.array([1, 2],   dtype=np.int64)})
    r  = _downcast_dtypes(df)
    assert r["f"].dtype == np.float32
    assert r["i"].dtype == np.int32
    assert df["f"].dtype == np.float64   # original unchanged
    ok("_downcast_dtypes: float64→float32, int64→int32, no mutation")
except Exception as e:
    fail("_downcast_dtypes", e)

# _remove_low_variance
try:
    df = pd.DataFrame({"const": [1.0]*50, "varies": range(50)})
    r, dropped = _remove_low_variance(df)
    assert "const" in dropped
    assert "const" not in r.columns
    ok("_remove_low_variance: constant column dropped")
except Exception as e:
    fail("_remove_low_variance", e)

# _smart_sample
try:
    X = pd.DataFrame({"a": rng.normal(0,1,60_000)})
    y = pd.Series(rng.integers(0, 2, 60_000))
    Xs, ys, sampled = _smart_sample(X, y, "classification", max_rows=50_000)
    assert sampled
    assert len(Xs) <= 50_000
    assert list(Xs.index) == list(ys.index)
    ok("_smart_sample: large dataset capped, indices aligned")
except Exception as e:
    fail("_smart_sample", e)

# _smart_sample no-op on small
try:
    X = pd.DataFrame({"a": rng.normal(0,1,200)})
    y = pd.Series(rng.normal(0,1,200))
    _, _, sampled = _smart_sample(X, y, "regression", max_rows=50_000)
    assert not sampled
    ok("_smart_sample: small dataset not sampled")
except Exception as e:
    fail("_smart_sample no-op", e)

# _adaptive_time_budget
try:
    assert _adaptive_time_budget(500, 10, 5)    == 20
    assert _adaptive_time_budget(100_000, 50, 5) == 60
    assert _adaptive_time_budget(500, 10, 120)  == 120
    ok("_adaptive_time_budget: floor values correct, user budget respected")
except Exception as e:
    fail("_adaptive_time_budget", e)

# _detect_imbalance
try:
    y = pd.Series([0]*95 + [1]*5)
    r = _detect_imbalance(y)
    assert r["is_imbalanced"]
    assert r["recommended_metric"] == "roc_auc"
    y2 = pd.Series([0]*1 + [1]*1)
    r2 = _detect_imbalance(y2)
    assert not r2["is_imbalanced"]
    ok("_detect_imbalance: imbalanced→roc_auc, balanced→auto")
except Exception as e:
    fail("_detect_imbalance", e)

# _impute_features
try:
    df = pd.DataFrame({"n": [1.0, np.nan, 3.0]*10,
                       "c": [0.0, np.nan, 1.0]*10})
    r  = _impute_features(df)
    assert not r.isnull().any().any()
    assert r.shape == df.shape
    ok("_impute_features: no NaN after imputation, shape preserved")
except Exception as e:
    fail("_impute_features", e)

# _encode_features — datetime dropped, cats become numeric, no -1 sentinel
try:
    df = pd.DataFrame({
        "dt":  pd.date_range("2023-01-01", periods=5),
        "cat": ["a", None, "b", None, "c"],
        "num": [1.0, 2.0, 3.0, 4.0, 5.0],
    })
    r = _encode_features(df)
    assert "dt" not in r.columns
    assert pd.api.types.is_numeric_dtype(r["cat"])
    assert (r["cat"] == -1).sum() == 0
    ok("_encode_features: datetime dropped, cats numeric, no -1 sentinel")
except Exception as e:
    fail("_encode_features", e)

print("\n── End-to-End: Regression ──────────────────────────────────────────────\n")

try:
    df = pd.DataFrame({
        "a": rng.normal(0, 1, 200),
        "b": rng.normal(0, 1, 200),
        "const_col": [5.0] * 200,
        "target": rng.normal(10, 3, 200),
    })
    res = run_automl(df, "target", time_budget=20)
    assert res.get("error") is None, res.get("error")
    ok("run_automl regression: no error")

    for m in ("MAE", "RMSE", "R\u00b2", "MAPE", "Expl. Variance", "Max Error"):
        assert m in res["metrics"], f"Missing metric: {m}"
    ok("run_automl regression: all 6 metrics present")

    tb = res.get("timing_breakdown", {})
    for key in ("preprocessing_s", "flaml_training_s", "evaluation_s", "total_s"):
        assert key in tb, f"Missing timing key: {key}"
    ok("run_automl regression: timing_breakdown complete")

    assert isinstance(res["leaderboard"], list) and len(res["leaderboard"]) > 0
    ok("run_automl regression: leaderboard populated")

    assert res["was_sampled"] is False
    ok("run_automl regression: was_sampled=False for small data")

    assert "const_col" in res.get("dropped_cols", [])
    ok("run_automl regression: constant column removed pre-training")

    assert isinstance(res.get("model_pkl"), bytes) and len(res["model_pkl"]) > 0
    ok("run_automl regression: model_pkl is bytes")

    safe = get_json_result(res)
    assert "model_pkl" not in safe
    ok("get_json_result: model_pkl stripped for JSON safety")

except Exception as e:
    fail("run_automl regression end-to-end", e)

print("\n── End-to-End: Classification ──────────────────────────────────────────\n")

try:
    df = pd.DataFrame({
        "x": rng.normal(0, 1, 300),
        "y": rng.normal(0, 1, 300),
        "label": rng.integers(0, 2, 300),
    })
    res2 = run_automl(df, "label", time_budget=20)
    assert res2.get("error") is None, res2.get("error")
    ok("run_automl classification: no error")

    for m in ("Accuracy", "F1 (weighted)", "Precision", "Recall"):
        assert m in res2["metrics"], f"Missing metric: {m}"
    ok("run_automl classification: all classification metrics present")

    report = res2.get("imbalance_report", {})
    assert "is_imbalanced" in report
    ok("run_automl classification: imbalance_report returned")

except Exception as e:
    fail("run_automl classification end-to-end", e)

print("\n── End-to-End: Imbalanced Dataset ─────────────────────────────────────\n")

try:
    labels_arr = [0]*380 + [1]*20
    df_imb = pd.DataFrame({
        "feat": rng.normal(0, 1, 400),
        "label": labels_arr,
    })
    res3 = run_automl(df_imb, "label", time_budget=20)
    assert res3.get("error") is None, res3.get("error")
    ok("run_automl imbalanced: no error")

    report = res3.get("imbalance_report", {})
    assert report.get("is_imbalanced") is True
    assert report.get("recommended_metric") == "roc_auc"
    ok("run_automl imbalanced: detected and metric switched to roc_auc")

except Exception as e:
    fail("run_automl imbalanced end-to-end", e)

# Summary
total = passed + failed
print(f"\n{'='*60}")
print(f"  RESULTS:  {passed}/{total} tests PASSED  |  {failed}/{total} FAILED")
print(f"{'='*60}\n")
if failed:
    sys.exit(1)
