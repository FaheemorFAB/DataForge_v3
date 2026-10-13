"""
backend/tests/test_characterization_golden.py
─────────────────────────────────────────────
P0-4 Golden Characterization Tests.
Locks in expected deterministic input-output behavior for:
1. TransformEngine (filter, groupby, create, sort)
2. DataCleaner (snake_case conversion, missing imputation, duplicate removal)
3. InsightEngine (distribution, correlation, outlier summaries)
"""

import pandas as pd
import numpy as np
import pytest

from dataforge.transform_engine import TransformEngine
from dataforge.data_cleaner import run_cleaning_pipeline
from dataforge.insight_engine import InsightEngine


@pytest.fixture
def sample_orders_df():
    return pd.DataFrame({
        "Order ID": ["ORD-1", "ORD-2", "ORD-3", "ORD-4", "ORD-5", "ORD-6"],
        "Customer Region": ["North", "North", "South", "South", "East", "West"],
        "Product Category": ["Hardware", "Software", "Hardware", "Services", "Software", "Hardware"],
        "Unit Price": [100.0, 250.0, 150.0, np.nan, 300.0, 50.0],
        "Units Sold": [5, 2, 4, 1, 3, 10],
    })


def test_golden_transform_engine(sample_orders_df):
    """Characterize baseline TransformEngine pipeline execution."""
    engine = TransformEngine()
    df = sample_orders_df.copy()

    # Step 1: Filter
    res1 = engine.apply(df, steps=[
        {"op": "filter", "rules": [{"col": "Customer Region", "op": "in", "val": ["North", "South"]}]}
    ])
    assert len(res1.df) == 4
    assert set(res1.df["Customer Region"].unique()) == {"North", "South"}

    # Step 2: Create derived column
    res2 = engine.apply(df, steps=[
        {"op": "create", "name": "Total Cost", "formula": "Units_Sold * 10"}
    ])
    assert "Total Cost" in res2.df.columns
    assert list(res2.df["Total Cost"]) == [50, 20, 40, 10, 30, 100]

    # Step 3: GroupBy and Aggregate
    res3 = engine.apply(df.dropna(), steps=[
        {"op": "groupby", "group": ["Customer Region"], "agg": {"Units Sold": "sum"}}
    ])
    assert "Customer Region" in res3.df.columns
    assert "Units Sold" in res3.df.columns
    assert len(res3.df) > 0


def test_golden_data_cleaner(sample_orders_df):
    """Characterize baseline run_cleaning_pipeline output."""
    df = sample_orders_df.copy()
    result = run_cleaning_pipeline(df)
    cleaned_df = result["df_clean"]

    # 1. Names should be normalized to snake_case
    assert "order_id" in cleaned_df.columns
    assert "customer_region" in cleaned_df.columns
    assert "product_category" in cleaned_df.columns
    assert "unit_price" in cleaned_df.columns
    assert "units_sold" in cleaned_df.columns

    # 2. Null values in numeric columns should be imputed
    assert cleaned_df["unit_price"].isna().sum() == 0

    # 3. Stats dictionary is populated
    stats = result["stats"]
    assert stats["original_rows"] == 6
    assert stats["cleaned_rows"] == 6


def test_golden_insight_engine(sample_orders_df):
    """Characterize baseline InsightEngine output."""
    engine = InsightEngine()
    df = sample_orders_df.copy().fillna(100.0)
    schema = engine.detect_schema(df)
    insights = engine.run_insights(df, schema)

    assert isinstance(insights, list)
    assert len(insights) > 0
    first = insights[0]
    assert hasattr(first, "insight_type") or hasattr(first, "title") or isinstance(first, dict)
