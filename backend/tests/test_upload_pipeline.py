"""
tests/test_upload_pipeline.py
──────────────────────────────
Comprehensive test suite for file uploads across CSV, JSON, and format validation.
"""
import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from dataforge.api.app import create_app
from dataforge.api.deps import get_current_user
from dataforge.db import User

@pytest.fixture
def test_client():
    app = create_app()
    mock_user = User(id=1, email="9256fa@gmail.com", name="DataForge Developer", role="Admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)

def test_upload_csv_success(test_client):
    csv_bytes = b"colA,colB,colC\n1,2.5,alpha\n2,3.5,beta\n3,4.5,gamma\n"
    res = test_client.post(
        "/api/upload",
        files={"file": ("dataset.csv", csv_bytes, "text/csv")},
        data={"expected_format": "csv"},
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    assert "upload_id" in body
    assert body["profile"]["rows"] == 3
    assert body["profile"]["cols"] == 3

def test_upload_json_success(test_client):
    json_bytes = b'[{"x": 10, "y": "hello"}, {"x": 20, "y": "world"}]'
    res = test_client.post(
        "/api/upload",
        files={"file": ("dataset.json", json_bytes, "application/json")},
        data={"expected_format": "json"},
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("ok") is True
    assert body["profile"]["rows"] == 2

def test_upload_empty_file_rejected(test_client):
    res = test_client.post(
        "/api/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert res.status_code == 400
    detail = res.json().get("detail", "").lower()
    assert "empty" in detail or "no columns" in detail

def test_upload_unsupported_extension_rejected(test_client):
    res = test_client.post(
        "/api/upload",
        files={"file": ("malicious.exe", b"binarydata", "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json().get("detail", "")

def test_upload_format_mismatch(test_client):
    # Uploading CSV when expecting JSON
    res = test_client.post(
        "/api/upload",
        files={"file": ("table.csv", b"a,b\n1,2\n", "text/csv")},
        data={"expected_format": "json"},
    )
    assert res.status_code == 400
    assert "File extension mismatch" in res.json().get("detail", "")

def test_check_duplicate_endpoint(test_client):
    res = test_client.post(
        "/api/upload/check-duplicate",
        json={"filename": "non_existent_dataset_12345.csv"},
    )
    assert res.status_code == 200
    assert res.json().get("duplicate") is False


def test_upload_when_dataset_already_active_in_workspace_rejected(test_client):
    # 1. First upload succeeds
    csv_bytes = b"colA,colB\n1,2\n3,4\n"
    res1 = test_client.post(
        "/api/upload",
        files={"file": ("primary.csv", csv_bytes, "text/csv")},
    )
    assert res1.status_code == 200
    active_upload_id = res1.json()["upload_id"]

    # 2. Attempting to upload another dataset into the active workspace is blocked
    res2 = test_client.post(
        "/api/upload",
        files={"file": ("secondary.csv", csv_bytes, "text/csv")},
        data={"current_upload_id": active_upload_id},
    )
    assert res2.status_code == 400
    assert "already loaded in this workspace" in res2.json().get("detail", "")

