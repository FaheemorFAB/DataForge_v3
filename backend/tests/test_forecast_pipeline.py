"""
Unit and regression tests for DataForge Forecast Engine & ForecastInsight.
"""

import numpy as np
import pandas as pd
import pytest
from dataforge.forecast_engine import run_forecast
from dataforge.forecast_insight import ForecastInsight


def test_forecast_handles_gaps_without_zero_collapse():
    """Ensure missing dates are interpolated rather than collapsed to 0."""
    dates = pd.date_range("2021-01-01", periods=60, freq="D")
    t = np.arange(60)
    values = 50000 + 300 * t + 10000 * np.sin(2 * np.pi * t / 7)
    df = pd.DataFrame({"record_date": dates, "annual_family_income_inr": values})

    # Drop 30% of dates to simulate gaps
    df_with_gaps = df.sample(frac=0.7, random_state=42).sort_values("record_date").reset_index(drop=True)

    result = run_forecast(df_with_gaps, "record_date", "annual_family_income_inr", horizon=30)

    assert "error" not in result
    fc_vals = result["forecast_values"]
    assert len(fc_vals) == 30
    # Must NOT be a flat line
    assert np.std(fc_vals) > 10.0, "Forecast must not be a flat line"
    # Non-negative series must have non-negative lower bounds
    assert min(result["lower_95"]) >= 0.0, "Lower 95% bound must not be negative for positive metric"
    assert min(result["lower_80"]) >= 0.0, "Lower 80% bound must not be negative for positive metric"


def test_forecast_direction_and_summary_stats():
    """Verify growth calculation and direction alignment."""
    dates = pd.date_range("2021-01-01", periods=50, freq="D")
    values = 1000 + 20 * np.arange(50)  # clearly upward
    df = pd.DataFrame({"date": dates, "metric": values})

    result = run_forecast(df, "date", "metric", horizon=14)
    assert "error" not in result
    stats = result["summary_stats"]
    assert stats["direction"] == "upward"
    assert stats["projected_growth_pct"] > 0
    assert stats["horizon"] == 14
    assert stats["n_points"] == 50


def test_forecast_insight_applicable_and_analyze():
    """Test the full ForecastInsight plugin integration."""
    dates = pd.date_range("2022-01-01", periods=40, freq="D")
    t = np.arange(40)
    values = 20000 + 5000 * np.sin(2 * np.pi * t / 7)
    df = pd.DataFrame({"timestamp": dates, "revenue_usd": values})

    insight_obj = ForecastInsight()
    schema = {"date": "timestamp", "metrics": ["revenue_usd"]}
    assert insight_obj.applicable(df, schema) is True

    card = insight_obj.analyze(df, schema)
    assert card is not None
    assert card["type"] == "forecast"
    assert "revenue_usd" in card["title"]
    assert "remain stable by" not in card["description"], "Phrasing must be grammatically sound"
    cd = card["chart_data"]
    assert len(cd["forecast_values"]) == 30
    assert cd["best_model"] in ["Holt-Winters", "Ridge-Lag ML", "ARIMA"]
