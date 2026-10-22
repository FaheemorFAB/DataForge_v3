import pandas as pd
import numpy as np
import pytest
from dataforge.data_cleaner import compute_rule_diff

def test_compute_rule_diff_impute_zero():
    # Customer age with 10 normal rows and 15 missing values
    ages = [67.0, 29.0, 19.0, 55.0, 45.0, 61.0, 23.0, 22.0, 47.0, 63.0] + [np.nan] * 15 + [40.0] * 50
    df = pd.DataFrame({"customer_age": ages})

    rule = {
        "action_type": "impute",
        "columns": ["customer_age"],
        "impute_method": "zero"
    }

    res = compute_rule_diff(df, rule)
    assert "error" not in res
    assert res["total_changed_rows"] == 15
    assert res["stats_before"]["nulls"] == 15
    assert res["stats_after"]["nulls"] == 0

    # Ensure changed rows appear at the top of sample_diff
    first_rows = res["sample_diff"][:12]
    for r in first_rows:
        assert r["changed"] is True
        assert r["before"] == "NaN"
        assert r["after"] == "0.0"

    # Subsequent rows should be unchanged
    last_rows = res["sample_diff"][12:]
    for r in last_rows:
        assert r["changed"] is False
        assert r["before"] == r["after"]


def test_compute_rule_diff_outlier_clip():
    vals = [10.0, 12.0, 11.0, 10.5, 11.5, 12.0, 10.8, 11.2, 500.0, -200.0] + [11.0] * 30
    df = pd.DataFrame({"salary": vals})

    rule = {
        "action_type": "outlier",
        "columns": ["salary"],
        "outlier_method": "iqr",
        "outlier_action": "clip",
        "multiplier_k": 1.5
    }

    res = compute_rule_diff(df, rule)
    assert res["total_changed_rows"] > 0
    # Modified rows at top
    assert res["sample_diff"][0]["changed"] is True


def test_compute_rule_diff_drop_column():
    df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": [4, 5, 6]})
    rule = {
        "action_type": "drop",
        "columns": ["col_a"]
    }
    res = compute_rule_diff(df, rule)
    assert res["action"] == "drop"
    assert res["total_changed_rows"] == 3
    assert all(r["after"] == "REMOVED" for r in res["sample_diff"])


def test_compute_rule_diff_no_changes():
    df = pd.DataFrame({"customer_age": [20.0, 30.0, 40.0, 50.0]})
    rule = {
        "action_type": "impute",
        "columns": ["customer_age"],
        "impute_method": "zero"
    }
    res = compute_rule_diff(df, rule)
    assert res["total_changed_rows"] == 0
    assert all(r["changed"] is False for r in res["sample_diff"])
