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

    from dataforge.data_sources.sheets_connector import SheetsConnector

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


class SheetUrlInfo(tuple):
    """2-tuple (sheet_id, gid) with optional .sheet_name attribute for full backwards compatibility."""
    def __new__(cls, sheet_id, gid, sheet_name=None):
        return super().__new__(cls, (sheet_id, gid))

    def __init__(self, sheet_id, gid, sheet_name=None):
        self.sheet_id = sheet_id
        self.gid = gid
        self.sheet_name = sheet_name


class SheetsConnector:

    def __init__(self):
        self._gc = None   # gspread client, lazily initialised

    # ── Public sheet ──────────────────────────────────────────────────────────
    def load_public(self, sheet_id: str, gid: str = "0", sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Load a Google Sheet that has been published to the web.
        Tries multiple URL formats — prioritizing GViz with headers=1 to ensure clean single-row headers.
        """
        import requests as _req, io as _io, urllib.parse as _up

        urls = []
        if sheet_name:
            enc_name = _up.quote_plus(sheet_name)
            urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={enc_name}&headers=1")
            urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={enc_name}")

        # GViz with headers=1 prevents Google from collapsing multiple rows into massive column names
        urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}&headers=1")
        urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&headers=1")
        urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}")
        urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv")
        urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}")
        urls.append(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv")

        if sheet_id.startswith("pub:"):
            pub_id = sheet_id.split("pub:", 1)[1]
            pub_urls = [
                f"https://docs.google.com/spreadsheets/d/e/{pub_id}/pub?output=csv&gid={gid}",
                f"https://docs.google.com/spreadsheets/d/e/{pub_id}/pub?output=csv",
            ]
            if sheet_name:
                enc_name = _up.quote_plus(sheet_name)
                pub_urls.insert(0, f"https://docs.google.com/spreadsheets/d/e/{pub_id}/pub?output=csv&sheet={enc_name}")
            urls = pub_urls + urls

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
                    text_content = resp.text.strip()
                    if not text_content:
                        continue
                    df = pd.read_csv(_io.StringIO(text_content))
                    if df.empty:
                        continue

                    # Clean and sanitize column names
                    df.columns = [str(c).strip() for c in df.columns]

                    # Strip empty/bogus columns Google Sheets outputs by default (Unnamed: 8 to 25 with 100% NaN)
                    valid_cols = []
                    for c in df.columns:
                        if (c.startswith("Unnamed:") or not c) and df[c].isna().all():
                            continue
                        valid_cols.append(c)
                    if valid_cols and len(valid_cols) < len(df.columns):
                        df = df[valid_cols]

                    # Strip completely empty rows
                    df = df.dropna(how="all").reset_index(drop=True)

                    log.info("SheetsConnector: loaded %d rows x %d cols from %s", df.shape[0], df.shape[1], url)
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

    @classmethod
    def parse_sheet_url(cls, url: str) -> SheetUrlInfo:
        """Extracts (sheet_id, gid, sheet_name) from any format of Google Sheets URL."""
        import re, urllib.parse
        if not url:
            return SheetUrlInfo(None, "0", None)
        url = url.strip()
        parsed = urllib.parse.urlparse(url)

        gid = "0"
        sheet_name = None
        qs = urllib.parse.parse_qs(parsed.query)
        if "gid" in qs and qs["gid"]:
            gid = qs["gid"][0]
        elif "gid=" in parsed.fragment:
            frag_match = re.search(r"gid=(\d+)", parsed.fragment)
            if frag_match:
                gid = frag_match.group(1)

        if "sheet" in qs and qs["sheet"]:
            sheet_name = qs["sheet"][0]
        elif "sheet=" in parsed.fragment:
            sheet_match = re.search(r"sheet=([^&]+)", parsed.fragment)
            if sheet_match:
                sheet_name = urllib.parse.unquote(sheet_match.group(1))

        # Published web spreadsheets: /spreadsheets/d/e/{pub_id}
        m_pub = re.search(r"/spreadsheets/d/e/([a-zA-Z0-9_-]+)", url)
        if m_pub:
            return SheetUrlInfo(f"pub:{m_pub.group(1)}", gid, sheet_name)

        # Standard spreadsheets: /spreadsheets/d/{sheet_id}
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if m and m.group(1) != "e":
            return SheetUrlInfo(m.group(1), gid, sheet_name)

        return SheetUrlInfo(None, gid, sheet_name)

    def load_from_url(self, url: str, sheet_name: Optional[str] = None, gid: Optional[str] = None) -> pd.DataFrame:
        """Parses and loads a Google Sheet directly from its full URL."""
        info = self.parse_sheet_url(url)
        sheet_id = info.sheet_id
        if not sheet_id:
            raise ValueError("Invalid Google Sheets URL. Could not find spreadsheet ID.")
        chosen_gid = gid or info.gid or "0"
        chosen_sheet = sheet_name or info.sheet_name
        return self.load_public(sheet_id=sheet_id, gid=chosen_gid, sheet_name=chosen_sheet)

    @classmethod
    def list_public_worksheets(cls, url_or_id: str) -> list[str]:
        """Scrapes the public HTML representation of a Google Sheet to discover sheet tab names."""
        import requests as _req, re
        info = cls.parse_sheet_url(url_or_id) if "http" in url_or_id else SheetUrlInfo(url_or_id, "0", None)
        sheet_id = info.sheet_id
        if not sheet_id:
            return []

        clean_id = sheet_id.replace("pub:", "")
        if sheet_id.startswith("pub:"):
            fetch_url = f"https://docs.google.com/spreadsheets/d/e/{clean_id}/pubhtml"
        else:
            fetch_url = f"https://docs.google.com/spreadsheets/d/{clean_id}/edit"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        try:
            resp = _req.get(fetch_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                captions = re.findall(r'docs-sheet-tab-caption">([^<]+)<', resp.text)
                if captions:
                    seen = set()
                    unique_captions = []
                    for c in captions:
                        c_clean = c.strip()
                        if c_clean and c_clean not in seen:
                            seen.add(c_clean)
                            unique_captions.append(c_clean)
                    return unique_captions
        except Exception as e:
            log.warning("SheetsConnector.list_public_worksheets failed: %s", e)
        return []

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