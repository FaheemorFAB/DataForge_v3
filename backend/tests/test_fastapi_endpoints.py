"""
Test all FastAPI endpoints directly using TestClient.
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

def test_fastapi_endpoints(monkeypatch):
    monkeypatch.setattr(UploadRepository, "get_by_id", lambda self, upload_id: {"id": upload_id, "user_id": 1, "filename": "test.csv"})
    app = create_app()
    mock_user = User(id=1, email="faheembaiza@gmail.com", name="Faheem Ahmad Bhat")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)

    # Create mock data for upload_id 999
    df_mock = pd.DataFrame({
        "Business_ID": [f"BIZ00{i}" for i in range(50)],
        "Category": ["A", "B", "A", "B", "C"] * 10,
        "Annual Revenue (USD)": [100.0, 200.0, 150.0, 300.0, 250.0] * 10,
        "Target": [0, 1, 0, 1, 1] * 10,
    })
    save(999, "df_raw", df_mock)
    save(999, "df_clean", df_mock)

    from dataforge.api.services.entitlements import EntitlementService
    EntitlementService.set_user_plan(1, "pro")
    
    # 1. Dashboard Stats (Query param upload_id)
    res = client.post("/api/dashboard/stats?upload_id=999", json={"chart_dim": "", "chart_metric": ""})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["ok"] is True
    assert len(data["stats"]) > 0
    assert "charts" in data

    # 2. AI Query (/api/query)
    res = client.post("/api/query", json={"upload_id": "999", "query": "Summarize this dataset"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "chat_sessions" in data

    # 3. AutoML Detect Task (/api/automl/detect-task)
    res = client.post("/api/automl/detect-task?upload_id=999", json={"upload_id": "999", "target_col": "Target"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "task" in data

    # 4. AutoML Train (/api/automl/train)
    res = client.post("/api/automl/train?upload_id=999", json={"upload_id": "999", "target_col": "Target", "time_budget": 10})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "task_id" in data

    # 5. Dashboard Custom Chart (/api/dashboard/custom-chart)
    res = client.post("/api/dashboard/custom-chart?upload_id=999", json={"chart_type": "bar", "x_col": "Category", "y_col": "Annual Revenue (USD)", "agg_type": "mean"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["ok"] is True

print("  ALL API ENDPOINT TESTS PASSED CLEANLY")
print("============================================================\n")
