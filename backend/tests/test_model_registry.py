"""
tests/test_model_registry.py
----------------------------
Unit tests for the Enterprise Model Registry, Inference Engine,
and AutoML auto-registration pipeline.
"""

import io
import zipfile
import pandas as pd
import pytest

from dataforge.models.registry import ModelRegistry


@pytest.fixture(autouse=True)
def setup_seed_models_for_tests():
    ModelRegistry.ensure_seed_models()
    yield
    try:
        ModelRegistry.delete_model("model_churn_lgbm_v1")
        ModelRegistry.delete_model("model_revenue_xgb_v1")
    except Exception:
        pass


def test_ensure_seed_models_and_list():
    models = ModelRegistry.list_models()
    assert len(models) >= 2
    names = [m["model_name"] for m in models]
    assert "Customer Churn Gradient Booster" in names
    assert "Monthly Recurring Revenue Forecaster" in names


def test_register_and_get_model_with_clean_id():
    m = ModelRegistry.register_model(
        org_id="default",
        model_name="Test Linear Forecaster",
        task_type="regression",
        algorithm="Linear / Ridge",
        target_column="sales",
        features=["marketing_spend", "store_size"],
        metrics={"r2": 0.88, "rmse": 12.5},
        created_by="test@dataforge.app",
        upload_id="test_upload_123",
    )
    assert m is not None
    assert "/" not in m["id"]
    assert " " not in m["id"]
    assert m["features"] == ["marketing_spend", "store_size"]

    fetched = ModelRegistry.get_model(m["id"])
    assert fetched is not None
    assert fetched["model_name"] == "Test Linear Forecaster"


def test_online_predict_classification_and_regression():
    # Test classification seed model
    res_c = ModelRegistry.predict("model_churn_lgbm_v1", {
        "age": 45,
        "income": 80000,
        "support_calls": 4,
        "tenure_months": 12,
    })
    assert res_c["ok"] is True
    assert res_c["task_type"] == "classification"
    assert "prediction" in res_c
    assert "confidence" in res_c
    assert "latency_ms" in res_c

    # Test regression seed model
    res_r = ModelRegistry.predict("model_revenue_xgb_v1", {
        "employee_count": 50,
        "active_licenses": 45,
        "feature_usage_score": 88,
        "days_active": 300,
    })
    assert res_r["ok"] is True
    assert res_r["task_type"] == "regression"
    assert isinstance(res_r["prediction"], (int, float))
    assert len(res_r["confidence_interval"]) == 2


def test_predict_dataframe_batch():
    df = pd.DataFrame({
        "age": [25, 45, 60],
        "income": [40000, 75000, 110000],
        "support_calls": [0, 2, 5],
        "tenure_months": [6, 24, 48],
    })
    res = ModelRegistry.predict_dataframe("model_churn_lgbm_v1", df)
    assert res["ok"] is True
    assert len(res["predictions"]) == 3
    assert len(res["confidences"]) == 3


def test_update_status_and_delete_model():
    m = ModelRegistry.register_model(
        org_id="default",
        model_name="Temporary Model",
        task_type="classification",
        algorithm="Random Forest",
        target_column="churn",
        features=["f1", "f2"],
        metrics={"accuracy": 0.91},
        created_by="temp@dataforge.app",
    )
    model_id = m["id"]

    # Promote to production
    updated = ModelRegistry.update_model_status(model_id, "production")
    assert updated["status"] == "production"

    # Delete
    deleted = ModelRegistry.delete_model(model_id)
    assert deleted is True
    assert ModelRegistry.get_model(model_id) is None


def test_export_docker_package_zip():
    zip_bytes = ModelRegistry.export_docker_package("model_churn_lgbm_v1")
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        assert "Dockerfile" in names
        assert "app.py" in names
        assert "requirements.txt" in names


def test_apply_model_to_workspace_integration(monkeypatch):
    from fastapi.testclient import TestClient
    from dataforge.api.app import create_app
    from dataforge.api.deps import get_current_user
    from dataforge.api.services.auth import User
    from dataforge.api.storage.manager import save, load
    from dataforge.api.repositories.upload import UploadRepository

    upload_id = "test_apply_workspace_99"
    df_sample = pd.DataFrame({
        "age": [32, 54, 21],
        "income": [65000, 120000, 32000],
        "support_calls": [1, 5, 0],
        "tenure_months": [18, 48, 6],
    })
    save(upload_id, "df_raw", df_sample)
    save(upload_id, "df_clean", df_sample.copy())
    save(upload_id, "meta", {"id": upload_id, "user_id": 1, "filename": "sample_clients.csv"})

    orig_get = UploadRepository.get_by_id
    monkeypatch.setattr(
        UploadRepository,
        "get_by_id",
        lambda self, uid: {"id": uid, "user_id": 1, "filename": "sample_clients.csv"} if str(uid) == upload_id else orig_get(self, uid)
    )

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: User(id=1, email="test@dataforge.app", name="Tester")
    client = TestClient(app)

    res = client.post(
        "/api/models/model_churn_lgbm_v1/apply-to-workspace",
        json={"upload_id": upload_id},
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body["ok"] is True
    assert body["rows_scored"] == 3
    assert len(body["new_columns"]) >= 1

    # Verify column was actually added to df_clean in storage
    df_updated = load(upload_id, "df_clean")
    assert df_updated is not None
    assert body["new_columns"][0] in df_updated.columns
    assert len(df_updated) == 3

