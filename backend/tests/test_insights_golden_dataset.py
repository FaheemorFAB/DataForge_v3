"""
backend/tests/test_insights_golden_dataset.py
─────────────────────────────────────────────
Section 7 Evaluation & Quality: Golden Datasets with Planted Findings and Traps.
Validates:
  • Trap 1: Protected attribute (gender, race) must never be labeled a "Key Driver".
  • Trap 2: ID column must be excluded from correlation scans and metrics.
  • Trap 3: Tautological derived column is suppressed from correlation insights.
  • Trap 4: Dataset with no date column executes cleanly without crashes.
  • Trap 5: Dataset with no numeric KPI degrades gracefully into profile mode.
  • Trap 6: Grounding validator flags ungrounded numbers.
  • Trap 7: Diversity-aware greedy selection suppresses redundant duplicate cards.
"""

import pytest
import numpy as np
import pandas as pd
from dataforge.insight_engine import (
    InsightEngine,
    detect_schema,
    run_insights,
    build_report_text,
    summarise_with_gemini,
)


@pytest.fixture
def engine():
    return InsightEngine()


# ── Trap 1: Protected Attribute Trap ──────────────────────────────────────────
def test_trap_1_protected_attribute_never_driver(engine):
    """
    Planted Trap: Column 'gender' has 60% Female / 40% Male distribution.
    Must NOT be labeled a 'Key Driver' or causal driver in the executive summary.
    """
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "gender": np.random.choice(["Female", "Male"], size=n, p=[0.6, 0.4]),
        "revenue": np.random.normal(500, 50, size=n),
        "cost": np.random.normal(300, 30, size=n),
    })

    schema = engine.detect_schema(df)
    assert "gender" in schema["protected_columns"]
    assert schema["column_roles"]["gender"]["role"] == "protected"

    insights = engine.run_insights(df, schema, top_n=6)
    
    # Check that any insight referencing gender is flagged as is_protected
    for ins in insights:
        if ins.get("metric") == "gender" or "gender" in ins.get("columns_involved", []):
            assert ins.get("is_protected") is True

    # Check that the executive report does NOT list gender under Key Drivers
    report = engine.build_report_text(insights)
    
    # Split report into sections
    parts = report.split("Key Drivers & Correlation Dynamics:")
    assert len(parts) >= 2, "Report must contain Key Drivers section"
    driver_section = parts[1].split("\n\n")[0]
    
    assert "gender" not in driver_section.lower()
    assert "female" not in driver_section.lower()


# ── Trap 2: Identifier Column Trap ───────────────────────────────────────────
def test_trap_2_identifier_excluded_from_correlations(engine):
    """
    Planted Trap: 'customer_id' is an arbitrary monotonic sequence 1..N.
    Must be identified as role: 'identifier' and NEVER correlated against metrics.
    """
    n = 100
    df = pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "revenue": np.linspace(100, 1000, n) + np.random.normal(0, 10, n),
        "margin": np.linspace(20, 200, n) + np.random.normal(0, 5, n),
    })

    schema = engine.detect_schema(df)
    assert "customer_id" in schema["identifier_columns"]
    assert "customer_id" not in schema["metrics"]
    assert schema["column_roles"]["customer_id"]["role"] == "identifier"

    insights = engine.run_insights(df, schema, top_n=6)
    corr_insights = [i for i in insights if i.get("type") == "correlation"]
    
    for ci in corr_insights:
        assert "customer_id" not in str(ci.get("columns_involved", []))
        assert "customer_id" != ci.get("metric")


# ── Trap 3: Tautological Derived Column Trap ─────────────────────────────────
def test_trap_3_tautological_column_suppressed(engine):
    """
    Planted Trap: 'revenue_exact_copy' = revenue * 1.0 (trivial tautology r=1.0).
    Must NOT be reported as a breakthrough correlation insight.
    """
    np.random.seed(42)
    n = 100
    rev = np.random.normal(1000, 100, n)
    df = pd.DataFrame({
        "revenue": rev,
        "revenue_exact_copy": rev * 1.0,  # perfect collinearity
        "expenses": np.random.normal(500, 50, n),
    })

    schema = engine.detect_schema(df)
    insights = engine.run_insights(df, schema, top_n=6)
    corr_insights = [i for i in insights if i.get("type") == "correlation"]

    for ci in corr_insights:
        chart_d = ci.get("chart_data") or {}
        r = abs(chart_d.get("r", 0))
        assert r < 0.999, "Trivial tautology with |r| >= 0.999 must be suppressed"


# ── Trap 4: Dataset With No Date Column ───────────────────────────────────────
def test_trap_4_no_date_runs_gracefully(engine):
    """
    Planted Trap: Dataset with only categorical and numeric columns, no time column.
    Must degrade gracefully, omitting trend & forecast without error.
    """
    df = pd.DataFrame({
        "category": ["A", "B", "C", "D"] * 25,
        "units_sold": np.random.randint(10, 100, 100),
        "discount": np.random.uniform(0.05, 0.30, 100),
    })

    schema = engine.detect_schema(df)
    assert schema["date"] is None

    insights = engine.run_insights(df, schema, top_n=6)
    assert len(insights) > 0

    types = [i["type"] for i in insights]
    assert "trend" not in types
    assert "forecast" not in types

    report = engine.build_report_text(insights)
    assert "No significant secular trends" in report or len(report) > 50


# ── Trap 5: Dataset With No Obvious KPI ───────────────────────────────────────
def test_trap_5_no_kpi_profile_structure_mode(engine):
    """
    Planted Trap: Dataset consisting solely of categorical survey responses,
    no obvious revenue or margin KPI.
    Must switch to profile-and-structure mode.
    """
    df = pd.DataFrame({
        "country": ["USA", "CAN", "UK", "GER"] * 25,
        "department": ["Sales", "Engineering", "Marketing", "HR"] * 25,
        "satisfaction_band": ["High", "Medium", "Low", "High"] * 25,
    })

    schema = engine.detect_schema(df)
    assert len(schema["metrics"]) == 0
    assert schema["primary_kpi"] is None

    insights = engine.run_insights(df, schema, top_n=4)
    assert len(insights) >= 1
    # Check that overview or categorical profile is provided
    assert any(i["type"] in ("profile", "categorical") for i in insights)


# ── Trap 6: Grounding Validator ───────────────────────────────────────────────
def test_trap_6_number_grounding_check(engine):
    """
    Grounding check: A narrative with fabricated/hallucinated numbers
    must be flagged by validate_grounding and fallback to deterministic text.
    """
    test_insights = [
        {
            "type": "trend",
            "title": "Revenue Growth",
            "description": "Revenue grew by 14.5% reaching $50,000 across Q3.",
            "importance": 0.85,
            "chart_data": {"r": 0.72},
        },
        {
            "type": "categorical",
            "title": "Region Distribution",
            "description": "North region accounts for 42.0% of total volume.",
            "importance": 0.60,
            "chart_data": {"top_pct": 42.0},
        }
    ]

    # Grounded narrative: quotes 14.5% and 42.0%
    grounded_text = "Revenue grew 14.5% to $50,000, while North region accounts for 42.0% volume."
    valid, ungrounded = engine.validate_grounding(grounded_text, test_insights)
    assert valid is True
    assert len(ungrounded) == 0

    # Hallucinated narrative: fabricates 99.8% and $999,999
    hallucinated_text = "Revenue surged by 99.8% to reach $999,999 in profits."
    h_valid, h_ungrounded = engine.validate_grounding(hallucinated_text, test_insights)
    assert h_valid is False
    assert len(h_ungrounded) >= 1

    # summarise_with_gemini fallback test with a mock function returning hallucinated text
    mock_hallucinating_gemini = lambda p: "Profits expanded by 88.9% with 77.4% customer retention."
    result = engine.summarise_with_gemini(test_insights, gemini_fn=mock_hallucinating_gemini)
    # Must fallback to deterministic briefing
    assert "Executive Intelligence Briefing" in result
    assert "88.9%" not in result


# ── Trap 7: Diversity-Aware Selection Deduplication ───────────────────────────
def test_trap_7_diversity_selection(engine):
    """
    Planted test: When multiple plugins emit candidate findings,
    diversity-aware greedy selection penalizes repeated finding types
    so the output is diverse and non-repetitive.
    """
    n = 100
    df = pd.DataFrame({
        "sales": np.random.normal(500, 50, n),
        "profit": np.random.normal(100, 20, n),
        "units": np.random.normal(50, 10, n),
        "region": np.random.choice(["East", "West", "North", "South"], n),
        "channel": np.random.choice(["Online", "Retail", "Partner"], n),
    })

    schema = engine.detect_schema(df)
    insights = engine.run_insights(df, schema, top_n=6)

    # Check for diversity in finding types
    types = [i["type"] for i in insights]
    # No single type should dominate all 6 slots
    assert max(types.count(t) for t in set(types)) <= 3, f"Output lacked diversity: {types}"
