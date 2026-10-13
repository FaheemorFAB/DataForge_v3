"""
backend/tests/test_tenant_isolation.py
──────────────────────────────────────
Security Suite: Cross-tenant boundary verification.
Verifies that User B cannot read, mutate, execute, or export resources owned by User A.
"""

import pytest
import pandas as pd
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.auth.jwt import create_access_token
from dataforge.api.storage.manager import save


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def user_a():
    return {"id": 101, "headers": {"Authorization": f"Bearer {create_access_token(101)}"}}


@pytest.fixture
def user_b():
    return {"id": 202, "headers": {"Authorization": f"Bearer {create_access_token(202)}"}}


def test_cross_tenant_workspace_isolation(client, user_a, user_b):
    """User B cannot access User A's workspace state or stats."""
    upload_id = "tenant_iso_upload_101"
    df = pd.DataFrame({"revenue": [100, 200, 300], "country": ["US", "UK", "DE"]})
    meta = {
        "id": upload_id,
        "user_id": user_a["id"],
        "filename": "q4_financials.csv",
        "rows": 3,
        "cols": 2,
    }
    save(upload_id, "meta", meta)
    save(upload_id, "df_raw", df)

    # 1. User B cannot read User A's workspace state
    res_b = client.get(f"/api/workspace/state?upload_id={upload_id}", headers=user_b["headers"])
    assert res_b.status_code == 403, f"Expected 403 for User B workspace read, got {res_b.status_code}"

    # 2. User B cannot query dashboard stats for User A's dataset
    res_stats_b = client.post(
        f"/api/dashboard/stats?upload_id={upload_id}",
        json={"chart_dim": "country", "chart_metric": "revenue"},
        headers=user_b["headers"],
    )
    assert res_stats_b.status_code == 403, f"Expected 403 for User B dashboard stats, got {res_stats_b.status_code}"

    # 3. User B cannot trigger pipeline export for User A's dataset
    res_pipe_b = client.get(f"/api/pipeline/export?upload_id={upload_id}", headers=user_b["headers"])
    assert res_pipe_b.status_code == 403, f"Expected 403 for User B pipeline export, got {res_pipe_b.status_code}"

    # 4. User B cannot launch AutoML training on User A's dataset
    res_automl_b = client.post(
        "/api/automl/train",
        json={"upload_id": upload_id, "target_col": "revenue", "task_choice": "regression", "time_budget": 10},
        headers=user_b["headers"],
    )
    assert res_automl_b.status_code == 403, f"Expected 403 for User B AutoML run, got {res_automl_b.status_code}"

    # 5. User B cannot mutate User A's dataset via clean or transform
    res_clean_b = client.post(
        "/api/clean",
        json={"upload_id": upload_id},
        headers=user_b["headers"],
    )
    assert res_clean_b.status_code == 403, f"Expected 403 for User B clean, got {res_clean_b.status_code}"

    res_trans_b = client.post(
        "/api/transform",
        json={"upload_id": upload_id, "operations": []},
        headers=user_b["headers"],
    )
    assert res_trans_b.status_code == 403, f"Expected 403 for User B transform, got {res_trans_b.status_code}"

    # 6. User B cannot list snapshots for User A's dataset
    res_snaps_b = client.get(
        f"/api/workspace/snapshots?upload_id={upload_id}",
        headers=user_b["headers"],
    )
    assert res_snaps_b.status_code == 403, f"Expected 403 for User B snapshots, got {res_snaps_b.status_code}"

    # 7. Legitimate owner (User A) has full access
    res_a = client.get(f"/api/workspace/state?upload_id={upload_id}", headers=user_a["headers"])
    assert res_a.status_code == 200
    res_stats_a = client.post(
        f"/api/dashboard/stats?upload_id={upload_id}",
        json={"chart_dim": "country", "chart_metric": "revenue"},
        headers=user_a["headers"],
    )
    assert res_stats_a.status_code == 200


def test_cross_tenant_joins_isolation(client, user_a, user_b):
    """User B cannot preview or join datasets owned by User A."""
    upload_id = "tenant_iso_join_101"
    df = pd.DataFrame({"user_id": [1, 2], "score": [95, 88]})
    meta = {
        "id": upload_id,
        "user_id": user_a["id"],
        "filename": "scores.csv",
        "rows": 2,
        "cols": 2,
    }
    save(upload_id, "meta", meta)
    save(upload_id, "df_raw", df)

    res_join = client.post(
        "/api/joins/preview",
        json={
            "upload_id": upload_id,
            "base_table": "scores",
            "joins": [],
        },
        headers=user_b["headers"],
    )
    assert res_join.status_code == 403


def test_cross_tenant_model_registry_isolation(client, user_a, user_b):
    """User B cannot view models trained by User A."""
    res_models_b = client.get("/api/models", headers=user_b["headers"])
    assert res_models_b.status_code == 200
    models_b = res_models_b.json().get("models", [])
    # Verify none of User A's models appear in User B's list
    for model in models_b:
        assert model.get("user_id") != user_a["id"]
