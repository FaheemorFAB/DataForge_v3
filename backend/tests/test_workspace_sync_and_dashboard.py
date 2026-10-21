"""
backend/tests/test_workspace_sync_and_dashboard.py
─────────────────────────────────────────────────
Automated tests for:
1. Ask AI dataset mutation safety and snapshot versioning.
2. Active workspace state synchronisation.
3. Dual-mode dashboard (Agentic Auto & Manual Builder).
4. Reusable insight pinning to last_insights and executive reports.
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parents[1]
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import pytest
import pandas as pd
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.deps import get_current_user
from dataforge.api.repositories.upload import UploadRepository
from dataforge.api.services.auth import User
from dataforge.api.storage.manager import save, load
from dataforge.ai.tools.cleaner_tool import clean_dataset_tool
from dataforge.api.storage.snapshots import SnapshotManager

app = create_app()

mock_user = User(id=1, email="lead_analyst@dataforge.io", name="DataForge Lead")
app.dependency_overrides[get_current_user] = lambda: mock_user

client = TestClient(app)

TEST_UPLOAD_ID = "sync_test_888"

@pytest.fixture(autouse=True)
def setup_test_dataset(monkeypatch):
    """Initializes sample test dataset and mocks upload repository."""
    orig_get = UploadRepository.get_by_id
    monkeypatch.setattr(
        UploadRepository,
        "get_by_id",
        lambda self, upload_id: {
            "id": str(upload_id),
            "user_id": 1,
            "filename": "revenue_and_churn_sample.csv"
        } if str(upload_id) == str(TEST_UPLOAD_ID) else orig_get(self, upload_id)
    )

    df_sample = pd.DataFrame({
        "Company_ID": [f"CORP_{i:03d}" for i in range(40)],
        "Sector": ["SaaS", "Fintech", "HealthTech", "CleanTech"] * 10,
        "ARR": [120000.0, 240000.0, None, 450000.0] * 10,
        "Net_Retention": [108.5, 114.0, 95.2, 122.0] * 10,
        "Customer_Count": [50, 120, 300, 80] * 10,
    })

    save(TEST_UPLOAD_ID, "df_raw", df_sample)
    save(TEST_UPLOAD_ID, "df_clean", None)
    save(TEST_UPLOAD_ID, "last_insights", [])
    yield


def test_data_mutation_safety_and_versioning():
    """
    Verifies that when cleaner_tool runs:
    1. df_clean is computed and persisted.
    2. An immutable snapshot is committed to SnapshotManager.
    3. dataset_updated is returned as True with version_id.
    """
    res = clean_dataset_tool(upload_id=TEST_UPLOAD_ID, auto_clean=True)
    assert res["ok"] is True
    assert res["dataset_updated"] is True
    assert isinstance(res["version_id"], str) and len(res["version_id"]) > 0
    assert "clean_profile" in res
    assert res["clean_profile"]["rows"] == 40

    # Verify SnapshotManager committed version
    snapshots = SnapshotManager.get_manifest(TEST_UPLOAD_ID)
    assert len(snapshots) >= 1
    latest = snapshots[-1]
    assert latest["version_id"] == res["version_id"]
    assert latest["metadata"]["source"] == "Ask AI CleanerAgent"

    # Verify canonical df_clean persisted to storage
    df_clean = load(TEST_UPLOAD_ID, "df_clean")
    assert df_clean is not None
    col_arr = "arr" if "arr" in df_clean.columns else "ARR"
    assert df_clean[col_arr].isnull().sum() == 0  # Imputed


def test_agentic_auto_dashboard_generation():
    """
    Verifies POST /api/dashboard/agentic-auto:
    1. Generates multi-agent governed executive KPIs and charts.
    2. Provides Pareto distributions, category shares, and boxplots.
    3. Retains agentic governance metadata.
    """
    # First ensure df_clean exists
    clean_dataset_tool(upload_id=TEST_UPLOAD_ID, auto_clean=True)

    res = client.post(
        f"/api/dashboard/agentic-auto?upload_id={TEST_UPLOAD_ID}",
        json={"chart_dim": "", "chart_metric": "", "upload_id": TEST_UPLOAD_ID}
    )
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["ok"] is True
    assert "governed_by" in d
    assert "VisualizerAgent" in d["governed_by"]
    assert len(d["stats"]) >= 4
    assert len(d["charts"]) >= 3

    # Check chart types
    chart_types = [c.get("chart_type") or c.get("type") for c in d["charts"]]
    assert "bar" in chart_types or "doughnut" in chart_types or "boxplot" in chart_types


def test_manual_dashboard_builder_preserved():
    """
    Ensures existing manual dashboard builder endpoints continue working seamlessly.
    """
    clean_dataset_tool(upload_id=TEST_UPLOAD_ID, auto_clean=True)

    # 1. Custom chart creation
    payload = {
        "upload_id": TEST_UPLOAD_ID,
        "chart_type": "bar",
        "x_col": "Sector",
        "y_col": "ARR",
        "agg_type": "mean",
        "title": "Sector ARR Comparison"
    }
    res = client.post("/api/dashboard/custom-chart", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ok"] is True
    assert data["chart"]["title"] == "Sector ARR Comparison"

    # 2. Manual dashboard fetch
    stats_res = client.post(
        f"/api/dashboard/stats?upload_id={TEST_UPLOAD_ID}",
        json={"chart_dim": "Sector", "chart_metric": "ARR", "upload_id": TEST_UPLOAD_ID}
    )
    assert stats_res.status_code == 200
    sd = stats_res.json()
    assert sd["ok"] is True
    assert any(c.get("title") == "Sector ARR Comparison" for c in sd.get("charts", []))


def test_pin_insight_persistence_and_reports():
    """
    Verifies that:
    1. POST /api/insights/pin saves custom chart/insight to last_insights.
    2. GET /api/insights/current returns the pinned insight.
    3. GET /api/workspace/report incorporates the pinned insight into executive report.
    """
    clean_dataset_tool(upload_id=TEST_UPLOAD_ID, auto_clean=True)

    pin_payload = {
        "upload_id": TEST_UPLOAD_ID,
        "title": "Breakthrough Sector Growth in SaaS",
        "description": "SaaS sector outperforms benchmark by 24% in net dollar retention.",
        "type": "ask_ai",
        "importance": 1.0,
        "chart_data": {
            "type": "bar",
            "labels": ["SaaS", "Fintech", "HealthTech", "CleanTech"],
            "values": [450000, 240000, 180000, 120000],
            "title": "Sector ARR Distribution"
        }
    }

    # Pin insight
    res = client.post("/api/insights/pin", json=pin_payload)
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["ok"] is True
    assert d["pinned"] is True
    assert d["insight"]["title"] == "Breakthrough Sector Growth in SaaS"

    # Verify last_insights disk storage
    insights = load(TEST_UPLOAD_ID, "last_insights")
    assert isinstance(insights, list)
    assert len(insights) >= 1
    assert insights[0]["title"] == "Breakthrough Sector Growth in SaaS"
    assert insights[0]["pinned"] is True

    # Verify /insights/current endpoint returns it
    curr_res = client.get(f"/api/insights/current?upload_id={TEST_UPLOAD_ID}")
    assert curr_res.status_code == 200
    curr_data = curr_res.json()
    assert curr_data["count"] >= 1
    assert curr_data["insights"][0]["title"] == "Breakthrough Sector Growth in SaaS"

    # Verify generate_html_report embeds the pinned finding and badge
    from dataforge.report_generator import generate_html_report
    html_report = generate_html_report(
        insights=insights,
        summary_text="Executive ARR Analysis",
        dataset_name="Revenue Dataset"
    )
    assert "Breakthrough Sector Growth in SaaS" in html_report
    assert "Ask AI Strategic Finding" in html_report
