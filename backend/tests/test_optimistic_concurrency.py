"""
backend/tests/test_optimistic_concurrency.py
─────────────────────────────────────────────
P1-2 & P1-3 Test Suite:
1. Optimistic Concurrency Control (OCC) with If-Match header and compare-and-swap (409 Conflict).
2. Content-Addressed Immutable Parquet Snapshots & Manifest lineage.
3. Two-writer race condition verification: exactly one writer succeeds, second receives 409.
"""

import concurrent.futures
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.auth.jwt import create_access_token
from dataforge.api.storage.manager import save
from dataforge.api.storage.snapshots import SnapshotManager


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token(user_id=101)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_dataset():
    upload_id = "test_occ_dataset_777"
    df = pd.DataFrame({"sales": [100.0, 200.0, 300.0], "region": ["North", "South", "East"]})
    meta = {
        "id": upload_id,
        "user_id": 101,
        "filename": "sales_q1.csv",
        "rows": 3,
        "cols": 2,
    }
    save(upload_id, "meta", meta)
    save(upload_id, "df_raw", df)
    save(upload_id, "df_clean", df)
    return upload_id


def test_workspace_state_exposes_etag_and_version(client, auth_headers, sample_dataset):
    """Verify workspace state returns version_id and HTTP ETag header."""
    res = client.get(f"/api/workspace/state?upload_id={sample_dataset}", headers=auth_headers)
    assert res.status_code == 200
    assert "version_id" in res.json()
    assert "ETag" in res.headers
    assert res.headers["ETag"] == f'"{res.json()["version_id"]}"'


def test_compare_and_swap_409_on_stale_if_match(client, auth_headers, sample_dataset):
    """Ensure mutation with stale If-Match is rejected with 409 Conflict."""
    # 1. Fetch initial state
    res_state = client.get(f"/api/workspace/state?upload_id={sample_dataset}", headers=auth_headers)
    initial_v = res_state.json()["version_id"]

    # 2. First mutation succeeds with matching version
    headers_1 = {**auth_headers, "If-Match": f'"{initial_v}"'}
    res_clean_1 = client.post(
        "/api/clean",
        json={"upload_id": sample_dataset},
        headers=headers_1,
    )
    assert res_clean_1.status_code == 200
    new_v = res_clean_1.json()["version_id"]
    assert new_v != initial_v

    # 3. Second mutation using the now-stale initial version receives 409 Conflict
    headers_stale = {**auth_headers, "If-Match": f'"{initial_v}"'}
    res_clean_2 = client.post(
        "/api/clean",
        json={"upload_id": sample_dataset},
        headers=headers_stale,
    )
    assert res_clean_2.status_code == 409
    err_body = res_clean_2.json()
    assert "conflict" in err_body["detail"]["error"].lower()
    assert err_body["detail"]["current_version_id"] == new_v

    # 4. Verify snapshot manifest was populated
    res_snaps = client.get(f"/api/workspace/snapshots?upload_id={sample_dataset}", headers=auth_headers)
    assert res_snaps.status_code == 200
    snaps = res_snaps.json()["snapshots"]
    assert len(snaps) >= 1
    assert snaps[-1]["version_id"] == new_v
    assert "snapshot_id" in snaps[-1]


def test_two_concurrent_writers_exactly_one_succeeds(client, auth_headers, sample_dataset):
    """Acceptance test: two concurrent writers with same starting version_id -> 1 succeeds (200), 1 gets 409."""
    res_state = client.get(f"/api/workspace/state?upload_id={sample_dataset}", headers=auth_headers)
    base_v = res_state.json()["version_id"]

    def perform_mutation():
        c = TestClient(create_app())
        h = {**auth_headers, "If-Match": f'"{base_v}"'}
        return c.post(
            "/api/clean",
            json={"upload_id": sample_dataset},
            headers=h,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(perform_mutation)
        f2 = executor.submit(perform_mutation)
        r1, r2 = f1.result(), f2.result()

    status_codes = sorted([r1.status_code, r2.status_code])
    assert status_codes == [200, 409], f"Expected exactly one 200 and one 409, got: {status_codes}"
