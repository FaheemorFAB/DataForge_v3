"""
Test Suite: DataForge Google GenAI / ADK Multi-Agent Architecture
"""

import pandas as pd
import numpy as np
import pytest

from dataforge.ai.schemas import AnalysisResult, AgentAction, QueryResponse
from dataforge.ai.tools.cleaner_tool import clean_dataset_tool
from dataforge.ai.tools.analytics_tool import run_analytics_tool
from dataforge.ai.tools.viz_tool import build_chart_tool
from dataforge.ai.tools.automl_tool import analyze_automl_tool
from dataforge.ai.tools.pipeline_tool import export_pipeline_tool
from dataforge.ai.supervisor import supervisor, _schema_summary
from dataforge.api.storage.manager import save

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": range(1, 21),
        "region": ["North", "South", "East", "West"] * 5,
        "revenue": [100.0, 150.0, None, 200.0] * 5,
        "churn": [0, 1, 0, 0] * 5,
    })

def test_pydantic_schemas():
    """Verify AnalysisResult enforces structured outputs properly."""
    res = AnalysisResult(
        code="result = df['revenue'].mean()",
        answer="Average revenue is $150.",
        intent="metric",
        x_col=None,
        y_col="revenue",
        top_n=10,
        insight="Revenue is stable across regions."
    )
    assert res.intent == "metric"
    assert res.top_n == 10
    dumped = res.model_dump()
    assert dumped["intent"] == "metric"
    assert dumped["answer"] == "Average revenue is $150."

def test_cleaner_tool(sample_df):
    """Test CleanerAgent cleans missing values and updates storage."""
    save("test_clean_999", "df_raw", sample_df)
    res = clean_dataset_tool(upload_id="test_clean_999", auto_clean=True)
    assert res["ok"] is True
    assert "stats" in res
    assert res["stats"]["cleaned_rows"] > 0

def test_analytics_tool(sample_df):
    """Test AnalyticsAgent safely executes legitimate code and blocks forbidden imports."""
    # 1. Legitimate computation
    legit = run_analytics_tool("result = df['region'].value_counts()", df=sample_df)
    assert legit["ok"] is True
    assert isinstance(legit["raw_result"], pd.Series)
    assert len(legit["raw_result"]) == 4

    # 2. Blocked malicious call
    blocked = run_analytics_tool("import os; os.listdir('.')", df=sample_df)
    assert blocked["ok"] is False
    assert blocked.get("security_violation") is True

def test_viz_tool(sample_df):
    """Test VisualizerAgent formats chart specs correctly."""
    series = sample_df["region"].value_counts()
    chart = build_chart_tool(
        intent="bar_chart",
        raw_result=series,
        df=sample_df,
        x_col="region",
        y_col="count"
    )
    assert chart is not None
    assert chart["type"] == "bar_chart"
    assert len(chart["labels"]) == 4
    assert len(chart["values"]) == 4

def test_automl_tool(sample_df):
    """Test AutoMLAgent infers classification problem and recommends models."""
    res = analyze_automl_tool(upload_id="test_automl", target_col="churn", df=sample_df)
    assert res["ok"] is True
    assert res["task"] == "classification"
    assert len(res["recommended_models"]) > 0

def test_pipeline_tool():
    """Test PipelineAgent exports Python, Airflow DAG, and dbt models."""
    py_res = export_pipeline_tool(upload_id="123", format_type="python")
    assert py_res["ok"] is True
    assert "def run_pipeline" in py_res["code"]

    airflow_res = export_pipeline_tool(upload_id="123", format_type="airflow")
    assert airflow_res["ok"] is True
    assert "from airflow import DAG" in airflow_res["code"]

    dbt_res = export_pipeline_tool(upload_id="123", format_type="dbt")
    assert dbt_res["ok"] is True
    assert "config(materialized='table')" in dbt_res["code"]

def test_supervisor_identity(sample_df):
    """Verify Supervisor immediately intercepts identity questions without model latency."""
    res = supervisor.execute("Who are you?", sample_df)
    assert res["ok"] is True
    assert "DataForge Autonomous Analytics Intelligence" in res["answer"]
    assert res["intent"] == "summary"

def test_supervisor_deterministic_fallback(sample_df):
    """Verify fallback executes gracefully when needed."""
    fb = supervisor._deterministic_fallback("Summarize this dataset", sample_df)
    assert fb["ok"] is True
    assert "20 records" in fb["answer"]
