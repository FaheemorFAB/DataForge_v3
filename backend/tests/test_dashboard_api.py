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

UploadRepository.get_by_id = lambda self, upload_id: {"id": upload_id, "user_id": 1, "filename": "dashboard_dataset.csv"}

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

def test_dashboard_endpoints():
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
        "upload_id": 1002,
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
        "upload_id": 1002,
        "chart_type": "scatter",
        "x_col": "Employee_Count",
        "y_col": "Revenue",
        "agg_type": "none",
        "title": "Revenue vs Employee Count"
    }
    res = client.post("/api/dashboard/custom-chart?upload_id=1002", json=scatter_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    print("  PASS  POST /api/dashboard/custom-chart (Scatter Plot)")

    # 4. POST Dashboard Drilldown
    drill_payload = {
        "upload_id": 1002,
        "chart_id": "top_cat",
        "col_name": "Category",
        "x_label": "Technology"
    }
    res = client.post("/api/dashboard/drilldown?upload_id=1002", json=drill_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    dr = res.json()
    assert dr["ok"] is True
    print("  PASS  POST /api/dashboard/drilldown")

    print("\n============================================================")
    print("  DASHBOARD API TESTS PASSED")
    print("============================================================\n")

if __name__ == "__main__":
    test_dashboard_endpoints()
