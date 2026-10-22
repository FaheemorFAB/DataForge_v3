"""
Comprehensive integration tests for DataForge Dashboard & Custom Chart API routes.
"""
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parents[1]
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import pandas as pd
from fastapi.testclient import TestClient
from dataforge.api.app import create_app
from dataforge.api.deps import get_current_user
from dataforge.api.repositories.upload import UploadRepository
from dataforge.api.services.auth import User
from dataforge.api.storage.manager import save

app = create_app()

mock_user = User(id=1, email="faheembaiza@gmail.com", name="Faheem Ahmad Bhat")
app.dependency_overrides[get_current_user] = lambda: mock_user

client = TestClient(app)

df_test = pd.DataFrame({
    "Business_ID": [f"BIZ00{i}" for i in range(50)],
    "Category": ["Technology", "Healthcare", "Finance", "Energy", "Retail"] * 10,
    "Revenue": [150000.0, 230000.0, 450000.0, 120000.0, 89000.0] * 10,
    "Employee_Count": [50, 120, 300, 45, 15] * 10,
})
save(1002, "df_raw", df_test)
save(1002, "df_clean", df_test)

def test_dashboard_endpoints(monkeypatch):
    orig_get = UploadRepository.get_by_id
    monkeypatch.setattr(
        UploadRepository,
        "get_by_id",
        lambda self, upload_id: {"id": upload_id, "user_id": 1, "filename": "dashboard_dataset.csv"} if str(upload_id) == "1002" else orig_get(self, upload_id)
    )
    print("\n── Dashboard & Custom Chart API Integration Tests ──\n")

    # 1. POST Dashboard Stats (KPI calculation & auto-generated charts)
    res = client.post("/api/dashboard/stats?upload_id=1002", json={"chart_dim": "Category", "chart_metric": "Revenue"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    d = res.json()
    assert d["ok"] is True
    assert len(d["stats"]) >= 4
    assert len(d["charts"]) >= 1
    print("  PASS  POST /api/dashboard/stats (KPIs & auto-charts)")

    # 2. POST Custom Chart Creation (Bar Chart)
    chart_payload = {
        "upload_id": "1002",
        "chart_type": "bar",
        "x_col": "Category",
        "y_col": "Revenue",
        "agg_type": "sum",
        "title": "Total Revenue by Category"
    }
    res = client.post("/api/dashboard/custom-chart?upload_id=1002", json=chart_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    c = res.json()
    assert c["ok"] is True
    print("  PASS  POST /api/dashboard/custom-chart (Bar Chart)")

    # 3. POST Custom Chart Creation (Scatter Plot)
    scatter_payload = {
        "upload_id": "1002",
        "chart_type": "scatter",
        "x_col": "Employee_Count",
        "y_col": "Revenue",
        "agg_type": "none",
        "title": "Revenue vs Employee Count"
    }
    res = client.post("/api/dashboard/custom-chart?upload_id=1002", json=scatter_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    print("  PASS  POST /api/dashboard/custom-chart (Scatter Plot)")

    # 4. POST Custom Chart (Heatmap)
    heatmap_payload = {
        "upload_id": "1002",
        "chart_type": "heatmap",
        "title": "Correlation Matrix",
    }
    res = client.post("/api/dashboard/custom-chart?upload_id=1002", json=heatmap_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    hm_data = res.json()
    assert hm_data["ok"] is True
    print("  PASS  POST /api/dashboard/custom-chart (Heatmap)")

    # 5. Agentic Auto Dashboard returns BOTH auto charts and custom charts
    auto_res = client.post("/api/dashboard/agentic-auto?upload_id=1002", json={"upload_id": "1002"})
    assert auto_res.status_code == 200, f"Expected 200: {auto_res.text}"
    auto_data = auto_res.json()
    assert auto_data["ok"] is True
    assert len(auto_data["stats"]) == 4
    chart_titles = [c.get("title") for c in auto_data["charts"]]
    assert "Total Revenue by Category" in chart_titles
    assert "Revenue vs Employee Count" in chart_titles
    assert "Correlation Matrix" in chart_titles
    assert any(c.get("is_custom") is True for c in auto_data["charts"])
    print("  PASS  POST /api/dashboard/agentic-auto (Includes custom charts)")

    # 6. Delete Custom Chart
    chart_to_del = next(c for c in auto_data["charts"] if c.get("title") == "Correlation Matrix")
    del_res = client.post("/api/dashboard/custom-chart/delete?upload_id=1002", json={"upload_id": "1002", "chart_id": chart_to_del["id"]})
    assert del_res.status_code == 200
    auto_res2 = client.post("/api/dashboard/agentic-auto?upload_id=1002", json={"upload_id": "1002"})
    auto_data2 = auto_res2.json()
    assert not any(c.get("id") == chart_to_del["id"] for c in auto_data2["charts"])
    print("  PASS  POST /api/dashboard/custom-chart/delete")

    # 7. POST Dashboard Drilldown
    drill_payload = {
        "upload_id": "1002",
        "chart_id": "top_cat",
        "col_name": "Category",
        "x_label": "Technology"
    }
    res = client.post("/api/dashboard/drilldown?upload_id=1002", json=drill_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    dr = res.json()
    assert dr["ok"] is True
    print("  PASS  POST /api/dashboard/drilldown")


def test_categorical_only_dashboard(monkeypatch):
    """
    Verifies that a purely categorical dataset (like job applications or survey responses):
    1. Never outputs 'N/A' in the AI insight summary.
    2. Generates 4 rich KPI cards including Segment Concentration.
    3. Generates multiple automated charts (Pareto bar, Doughnut share, and Heatmap).
    """
    df_cat = pd.DataFrame({
        "Status": ["No longer active", "Pending Review", "Interviewing", "Offer Extended"] * 25,
        "Source link page": ["Link", "LinkedIn Easy Apply", "Google Form", "Other"] * 25,
        "Department": ["Engineering", "Sales", "Marketing", "Finance"] * 25,
        "Location": ["Remote", "New York", "San Francisco", "London"] * 25,
    })
    save(1003, "df_raw", df_cat)
    save(1003, "df_clean", df_cat)

    orig_get = UploadRepository.get_by_id
    monkeypatch.setattr(
        UploadRepository,
        "get_by_id",
        lambda self, upload_id: {"id": upload_id, "user_id": 1, "filename": "jobs.csv"} if str(upload_id) == "1003" else orig_get(self, upload_id)
    )

    res = client.post("/api/dashboard/agentic-auto?upload_id=1003", json={"upload_id": "1003"})
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["ok"] is True
    assert len(d["stats"]) == 4
    # Summary must never display 'N/A'
    assert "'N/A'" not in d["summary"]
    assert "Status" in d["summary"]
    # Multiple charts generated
    assert len(d["charts"]) >= 3
    print("  PASS  Categorical dataset dashboard (No 'N/A', 4 KPIs, full chart suite)")

    print("\n============================================================")
    print("  ALL DASHBOARD API TESTS PASSED")
    print("============================================================\n")

if __name__ == "__main__":
    test_dashboard_endpoints()

