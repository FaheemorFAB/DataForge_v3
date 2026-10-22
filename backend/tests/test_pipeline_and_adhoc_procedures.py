import pytest
import pandas as pd
from starlette.testclient import TestClient
from dataforge.api.app import create_app
from dataforge.api.deps import get_current_user
from dataforge.api.repositories.upload import UploadRepository
from dataforge.api.services.auth import User
from dataforge.api.storage.manager import save, load

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(UploadRepository, "get_by_id", lambda self, upload_id: {"id": upload_id, "user_id": 1, "filename": "test.csv"})
    app = create_app()
    mock_user = User(id=1, email="test@example.com", name="Test User")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)

def test_pipeline_export_and_assert(client):
    upload_id = "test_pipe_export_123"
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "category": ["A", "B", "A", "C"],
        "revenue": [100.5, 200.0, 150.0, 300.0]
    })
    save(upload_id, "df_raw", df)
    save(upload_id, "profile", {"filename": "sales.csv", "columns": list(df.columns)})

    # Test export
    res = client.get(f"/api/pipeline/export?upload_id={upload_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "sales.csv" in data["python_script"]
    assert "stg_test_pip_transformed" in data["dbt_sql"]
    assert "dags/dataforge_test_pip_dag.py" in data["airflow_dag"]
    assert "test_data_quality.py" in data["data_quality_tests"]

    # Test data quality assertions
    res_assert = client.post("/api/pipeline/assert", json={"upload_id": upload_id})
    assert res_assert.status_code == 200
    assert_data = res_assert.json()
    assert assert_data["ok"] is True
    assert assert_data["score"] > 0
    assert len(assert_data["assertions"]) >= 2

    # Test zip download
    res_zip = client.get(f"/api/pipeline/download-zip?upload_id={upload_id}")
    assert res_zip.status_code == 200
    assert res_zip.headers["content-type"] == "application/zip"
    assert len(res_zip.content) > 100

def test_adhoc_procedure_dry_run_and_execute(client):
    upload_id = "test_adhoc_proc_456"
    df = pd.DataFrame({
        "User ID": [101, 102, 103],
        "Gross Revenue": [50.0, 120.0, 80.0]
    })
    save(upload_id, "df_raw", df)
    save(upload_id, "profile", {"filename": "revenue.csv", "columns": list(df.columns)})

    # Recipe format (with steps)
    recipe = {
        "procedure_name": "clean_revenue_pipe",
        "steps": [
            {"step_id": "s1", "type": "source", "source_upload_id": upload_id},
            {"step_id": "s2", "type": "clean_names", "config": {"casing": "snake_case"}},
            {"step_id": "s3", "type": "assertion_gate", "rules": [{"rule": "row_count_gte", "threshold": 1}], "on_violation": "warn"}
        ]
    }

    # 1. Dry run
    res_dry = client.post("/api/procedures/dry-run", json={"upload_id": upload_id, "recipe": recipe})
    assert res_dry.status_code == 200, res_dry.text
    dry_data = res_dry.json()
    assert dry_data["ok"] is True
    assert dry_data["isDryRun"] is True
    assert "user_id" in dry_data["columns"]
    assert "gross_revenue" in dry_data["columns"]
    assert len(dry_data["preview_sample"]) == 3

    # 2. Live execute
    res_exec = client.post("/api/procedures/execute", json={"upload_id": upload_id, "recipe": recipe})
    assert res_exec.status_code == 200, res_exec.text
    exec_data = res_exec.json()
    assert exec_data["ok"] is True
    assert exec_data["isDryRun"] is False
    assert exec_data["rows_affected"] == 3

    # Verify df_clean and clean_profile were saved
    df_clean = load(upload_id, "df_clean")
    assert df_clean is not None
    assert "user_id" in df_clean.columns
    clean_p = load(upload_id, "clean_profile")
    assert clean_p is not None
    col_names = [c["name"] if isinstance(c, dict) else c for c in clean_p["columns"]]
    assert "user_id" in col_names
