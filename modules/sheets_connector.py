"""
Google Sheets Connector
════════════════════════
Fetches a Google Sheets spreadsheet as a pandas DataFrame.

Two auth modes:
  A) Public sheet (export URL)   — no credentials needed
  B) Private sheet (service account) — requires gspread + credentials JSON

Setup for private sheets:
  pip install gspread gspread-dataframe google-auth
  Set env var GOOGLE_SERVICE_ACCOUNT_JSON to the path of your service account file
  OR set the JSON content directly in GOOGLE_SA_JSON_CONTENT

Usage::

    from modules.data_sources.sheets_connector import SheetsConnector

    # Public sheet (published to web as CSV)
    conn = SheetsConnector()
    df   = conn.load_public(sheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms")

    # Private sheet (service account)
    conn = SheetsConnector()
    df   = conn.load_private(spreadsheet_name="Sales Dashboard", worksheet="Sheet1")
"""

import logging
import os
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

_PUBLIC_CSV_URL = "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


class SheetsConnector:

    def __init__(self):
        self._gc = None   # gspread client, lazily initialised

    # ── Public sheet ──────────────────────────────────────────────────────────
    def load_public(self, sheet_id: str, gid: str = "0") -> pd.DataFrame:
        """
        Load a Google Sheet that has been published to the web.
        Tries multiple URL formats — Google's export endpoint returns 400
        intermittently even on correctly shared sheets.
        """
        import requests as _req, io as _io

        # Four URL formats Google has used — try all before giving up
        urls = [
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv",
        ]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

        last_err = None
        for url in urls:
            try:
                log.info("SheetsConnector: trying %s", url)
                resp = _req.get(url, headers=headers, timeout=30, proxies={})
                if resp.status_code == 200:
                    df = pd.read_csv(_io.StringIO(resp.text))
                    log.info("SheetsConnector: loaded %d rows x %d cols", *df.shape)
                    return df
                last_err = f"HTTP {resp.status_code} from {url}"
                log.warning("SheetsConnector: %s", last_err)
            except Exception as e:
                last_err = str(e)
                log.warning("SheetsConnector: %s failed: %s", url, e)

        raise ValueError(
            f"Could not load Google Sheet ({last_err}). "
            "Check that sharing is set to 'Anyone with the link can view'."
        )

    # ── Private sheet (service account) ──────────────────────────────────────
    def _get_client(self):
        if self._gc:
            return self._gc
        try:
            import gspread
            sa_path    = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
            sa_content = os.getenv("GOOGLE_SA_JSON_CONTENT", "")

            if sa_content:
                import json, tempfile
                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
                    tf.write(sa_content)
                    sa_path = tf.name

            if sa_path:
                self._gc = gspread.service_account(filename=sa_path)
            else:
                # Try Application Default Credentials
                from google.oauth2.service_account import Credentials
                self._gc = gspread.Client(auth=None)

            return self._gc
        except ImportError:
            raise RuntimeError(
                "gspread not installed. Run: pip install gspread gspread-dataframe google-auth"
            )

    def load_private(
        self,
        spreadsheet_name: str | None = None,
        spreadsheet_url:  str | None = None,
        worksheet:        str = "Sheet1",
    ) -> pd.DataFrame:
        """
        Load a private Google Sheet using a service account.
        Provide either spreadsheet_name or spreadsheet_url.
        """
        gc = self._get_client()
        if spreadsheet_url:
            sh = gc.open_by_url(spreadsheet_url)
        elif spreadsheet_name:
            sh = gc.open(spreadsheet_name)
        else:
            raise ValueError("Provide spreadsheet_name or spreadsheet_url.")

        ws = sh.worksheet(worksheet)

        # Use gspread-dataframe if available, else manual conversion
        try:
            from gspread_dataframe import get_as_dataframe
            df = get_as_dataframe(ws, evaluate_formulas=True, usecols=lambda c: True)
        except ImportError:
            records = ws.get_all_records()
            df      = pd.DataFrame(records)

        df = df.dropna(how="all").reset_index(drop=True)
        log.info("SheetsConnector: loaded private sheet '%s' — %d rows", spreadsheet_name or spreadsheet_url, len(df))
        return df

    def list_worksheets(
        self,
        spreadsheet_name: str | None = None,
        spreadsheet_url:  str | None = None,
    ) -> list[str]:
        """Return all worksheet tab names in a spreadsheet."""
        gc = self._get_client()
        if spreadsheet_url:
            sh = gc.open_by_url(spreadsheet_url)
        elif spreadsheet_name:
            sh = gc.open(spreadsheet_name)
        else:
            raise ValueError("Provide spreadsheet_name or spreadsheet_url.")
        return [ws.title for ws in sh.worksheets()]