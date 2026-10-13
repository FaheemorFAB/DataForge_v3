"""
backend/tests/test_spreadsheets_ingestion.py
─────────────────────────────────────────────
Unit and integration tests for Google Sheets and Microsoft Excel Online
link ingestion connectors and FastAPI endpoints.
"""

import io
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from dataforge.api.app import app
from dataforge.sheets_connector import SheetsConnector
from dataforge.excel_online_connector import ExcelOnlineConnector


client = TestClient(app)


def test_sheets_connector_url_parsing():
    """Verify robust extraction of spreadsheet ID and GID from diverse Google Sheets URLs."""
    # Standard URL with sharing params
    url1 = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit?usp=sharing"
    sheet_id1, gid1 = SheetsConnector.parse_sheet_url(url1)
    assert sheet_id1 == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
    assert gid1 == "0"

    # URL with hash GID
    url2 = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit#gid=45678"
    sheet_id2, gid2 = SheetsConnector.parse_sheet_url(url2)
    assert sheet_id2 == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
    assert gid2 == "45678"

    # Published web spreadsheet
    url3 = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQabc_12345/pubhtml"
    sheet_id3, gid3 = SheetsConnector.parse_sheet_url(url3)
    assert sheet_id3 == "pub:2PACX-1vQabc_12345"
    assert gid3 == "0"


def test_excel_online_connector_url_detection():
    """Verify detection of OneDrive, SharePoint, Office 365, and raw Excel links."""
    assert ExcelOnlineConnector.is_excel_online_url("https://1drv.ms/x/s!AkZ123456789")
    assert ExcelOnlineConnector.is_excel_online_url("https://onedrive.live.com/view.aspx?resid=ABC!123&authkey=!XYZ")
    assert ExcelOnlineConnector.is_excel_online_url("https://myorg.sharepoint.com/:x:/s/finance/EXample123")
    assert ExcelOnlineConnector.is_excel_online_url("https://cdn.example.com/exports/q3_metrics.xlsx")
    assert not ExcelOnlineConnector.is_excel_online_url("https://example.com/articles/news.html")


def test_excel_online_candidate_url_generation():
    """Verify generated download endpoint candidates for OneDrive and SharePoint."""
    one_drv_url = "https://1drv.ms/x/s!AkZ123456789"
    candidates = ExcelOnlineConnector.get_candidate_download_urls(one_drv_url)
    assert any("api.onedrive.com/v1.0/shares" in c for c in candidates)
    assert any("download=1" in c for c in candidates)

    sp_url = "https://corp.sharepoint.com/:x:/r/sites/data/report.xlsx"
    sp_candidates = ExcelOnlineConnector.get_candidate_download_urls(sp_url)
    assert any("download=1" in c for c in sp_candidates)


def test_excel_online_binary_parsing():
    """Verify that in-memory Excel files (.xlsx) are parsed accurately with openpyxl."""
    df_expected = pd.DataFrame({
        "employee_id": [101, 102, 103],
        "name": ["Alice", "Bob", "Charlie"],
        "salary": [95000, 110000, 105000]
    })
    buf = io.BytesIO()
    df_expected.to_excel(buf, index=False, engine="openpyxl", sheet_name="Payroll")
    raw_content = buf.getvalue()

    with patch("requests.Session.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = raw_content
        mock_resp.headers = {"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        mock_resp.url = "https://1drv.ms/x/s!mocked"
        mock_get.return_value = mock_resp

        df_loaded, meta = ExcelOnlineConnector.load_url("https://1drv.ms/x/s!mocked")
        assert len(df_loaded) == 3
        assert list(df_loaded.columns) == ["employee_id", "name", "salary"]
        assert "Payroll" in meta["sheets"]


def test_api_upload_sheets_and_excel_online_endpoints():
    """Verify FastAPI integration endpoints for sheets and excel-online with mock data."""
    from dataforge.api.deps import get_current_user
    from dataforge.api.services.auth import User
    from dataforge.api.services.entitlements import EntitlementService

    mock_user = User(id=1, email="faheembaiza@gmail.com", name="Faheem Ahmad Bhat")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    EntitlementService.set_user_plan(1, "pro")

    fake_df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})

    # Test Google Sheets endpoint
    with patch.object(SheetsConnector, "load_from_url", return_value=fake_df), \
         patch.object(SheetsConnector, "parse_sheet_url", return_value=("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms", "0")):
        resp = client.post("/api/upload/sheets", json={"url": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["source_type"] == "sheets"
        assert "upload_id" in data

    # Test Microsoft Excel Online endpoint
    with patch.object(ExcelOnlineConnector, "load_url", return_value=(fake_df, {"sheets": ["Sheet1"], "final_url": "https://1drv.ms/x/s!abc"})):
        resp = client.post("/api/upload/excel-online", json={"url": "https://1drv.ms/x/s!abc"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["source_type"] == "excel_online"
        assert "upload_id" in data

    app.dependency_overrides.clear()

