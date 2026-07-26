"""
Comprehensive integration tests for DataForge Workspace API routes.
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

# Mock upload_repo.get_by_id
UploadRepository.get_by_id = lambda self, upload_id: {"id": upload_id, "user_id": 1, "filename": "test_dataset.csv"}

app = create_app()

mock_user = User(id=1, email="faheembaiza@gmail.com", name="Faheem Ahmad Bhat")
app.dependency_overrides[get_current_user] = lambda: mock_user

client = TestClient(app)

# Create mock data for upload_id 1001
df_test = pd.DataFrame({
    "Company_ID": [f"BIZ00{i}" for i in range(40)],
    "Category": ["Technology", "Healthcare", "Finance", "Energy", "Retail"] * 8,
    "Revenue": [150000.0, 230000.0, 450000.0, 120000.0, 89000.0] * 8,
    "Employee_Count": [50, 120, 300, 45, 15] * 8,
    "Target": [0, 1, 1, 0, 0] * 8,
})
save(1001, "df_raw", df_test)
save(1001, "df_clean", df_test)

def test_workspace_endpoints():
    print("\n── Workspace API Integration Tests ──\n")

    # 1. GET Workspace State
    res = client.get("/api/workspace/state?upload_id=1001")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    st = res.json()
    assert "source_type" in st
    print("  PASS  GET /api/workspace/state")

    # 2. GET Preview Data
    res = client.get("/api/preview?upload_id=1001&limit=50")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    pv = res.json()
    assert "rows" in pv
    assert len(pv["rows"]) > 0
    print("  PASS  GET /api/preview")

    # 3. POST AI Consent
    res = client.post("/api/workspace/consent?upload_id=1001", json={"upload_id": 1001, "consent": True})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    print("  PASS  POST /api/workspace/consent")

    # 4. POST AI Query (Gemini / Code Execution)
    res = client.post("/api/query?upload_id=1001", json={"upload_id": 1001, "query": "What is the average Revenue by Category?"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    q = res.json()
    assert "chat_sessions" in q
    print("  PASS  POST /api/query")

    # 5. POST Data Cleaning Operation
    clean_payload = {
        "upload_id": 1001,
        "fill_nulls": "none",
        "drop_duplicates": True,
        "outlier_method": "none"
    }
    res = client.post("/api/clean?upload_id=1001", json=clean_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    cl = res.json()
    assert cl["ok"] is True
    assert "stats" in cl
    print("  PASS  POST /api/clean")

    # 6. POST Data Transformation (Type conversion)
    transform_payload = {
        "upload_id": 1001,
        "operations": [{"type": "cast", "column": "Employee_Count", "target_type": "float"}]
    }
    res = client.post("/api/transform?upload_id=1001", json=transform_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    print("  PASS  POST /api/transform")

    print("\n============================================================")
    print("  WORKSPACE API TESTS PASSED")
    print("============================================================\n")

if __name__ == "__main__":
    test_workspace_endpoints()
