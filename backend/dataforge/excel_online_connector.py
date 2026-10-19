"""
dataforge/excel_online_connector.py
═══════════════════════════════════
Microsoft Excel Online, OneDrive & SharePoint Connector.

Fetches online spreadsheets hosted on:
- Microsoft OneDrive personal & business (1drv.ms, onedrive.live.com)
- Microsoft SharePoint & Office 365 (*.sharepoint.com, *.office.com)
- Excel Online web view links
- Direct public cloud Excel / CSV URLs (.xlsx, .xls, .csv)

Provides automatic share link translation, redirect resolution,
Microsoft Graph content endpoint fallback, and multi-format decoding.
"""

from __future__ import annotations

import base64
import io
import logging
import re
import urllib.parse
from typing import List, Optional, Tuple, Union

import pandas as pd
import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 DataForge/2.0"
)


class ExcelOnlineConnector:
    """Connector for downloading and parsing Microsoft Excel Online and OneDrive/SharePoint sheets."""

    @staticmethod
    def is_excel_online_url(url: str) -> bool:
        """Determines if a given URL is likely a Microsoft Excel Online, OneDrive, or SharePoint link."""
        if not url or not isinstance(url, str):
            return False
        clean = url.strip().lower()
        patterns = [
            r"1drv\.ms",
            r"onedrive\.live\.com",
            r"sharepoint\.com",
            r"office\.com",
            r"office365\.com",
            r"officeapps\.live\.com",
            r"\.xlsx(\?|$)",
            r"\.xls(\?|$)",
            r"\.xlsm(\?|$)",
        ]
        return any(re.search(pat, clean) for pat in patterns)

    @classmethod
    def get_candidate_download_urls(cls, url: str) -> List[str]:
        """
        Translates a user-facing view/share URL into direct download endpoints.
        Returns a list of URLs to try in order of preference.
        """
        url = url.strip()
        candidates: List[str] = []

        # 1. Microsoft Graph Share Content API for OneDrive & SharePoint shares
        try:
            b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").rstrip("=")
            candidates.append(f"https://api.onedrive.com/v1.0/shares/u!{b64}/root/content")
        except Exception:
            pass

        # 2. OneDrive short links (1drv.ms) - we will resolve redirects when fetching,
        # but also provide a direct download hint
        if "1drv.ms" in url:
            sep = "&" if "?" in url else "?"
            candidates.append(f"{url}{sep}download=1")
            candidates.append(url)

        # 3. onedrive.live.com URLs
        elif "onedrive.live.com" in url:
            # Replace view.aspx or edit.aspx with download
            download_url = re.sub(r"/(view|edit)\.aspx", "/download", url)
            if download_url != url:
                candidates.append(download_url)

            # Check for resid & authkey
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "resid" in qs and "authkey" in qs:
                resid = qs["resid"][0]
                authkey = qs["authkey"][0]
                candidates.append(
                    f"https://onedrive.live.com/download?resid={resid}&authkey={authkey}"
                )

            sep = "&" if "?" in url else "?"
            candidates.append(f"{url}{sep}download=1")

        # 4. SharePoint / Office 365 (*.sharepoint.com)
        elif "sharepoint.com" in url:
            # Adding download=1 to sharepoint links directly forces file download
            if "download=1" not in url:
                sep = "&" if "?" in url else "?"
                candidates.append(f"{url}{sep}download=1")
            candidates.append(url)

        # 5. Generic or fallback
        if url not in candidates:
            candidates.append(url)

        return candidates

    @classmethod
    def fetch_workbook_bytes(cls, url: str, timeout: int = 30) -> Tuple[Optional[bytes], str, Optional[str]]:
        """
        Downloads workbook bytes from online candidate endpoints.
        Returns (raw_bytes, final_url, last_error).
        """
        if not url or not url.strip():
            return None, url, "URL cannot be empty"

        candidates = cls.get_candidate_download_urls(url)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                "application/vnd.ms-excel,text/csv,application/octet-stream,*/*"
            ),
        }

        session = requests.Session()
        session.headers.update(headers)

        last_error = None
        raw_bytes: Optional[bytes] = None
        final_url = url

        for target in candidates:
            try:
                log.info("ExcelOnlineConnector: attempting download from %s", target)
                resp = session.get(target, allow_redirects=True, timeout=timeout)
                if resp.status_code == 200 and len(resp.content) > 0:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    content_start = resp.content[:200].lower()

                    is_html = (
                        "text/html" in content_type
                        or b"<!doctype html" in content_start
                        or b"<html" in content_start
                    )

                    is_excel_binary = resp.content.startswith(b"PK\x03\x04") or resp.content.startswith(b"\xd0\xcf\x11\xe0")

                    if is_html and not is_excel_binary:
                        html_text = resp.content.decode("utf-8", errors="ignore")
                        meta_match = re.search(r'url=([^"\' >]+)', html_text, re.IGNORECASE)
                        if meta_match:
                            redirect_target = meta_match.group(1).replace("&amp;", "&")
                            log.info("Following HTML meta refresh to: %s", redirect_target)
                            sub_resp = session.get(redirect_target, allow_redirects=True, timeout=timeout)
                            if sub_resp.status_code == 200 and len(sub_resp.content) > 0:
                                raw_bytes = sub_resp.content
                                final_url = sub_resp.url
                                break

                        last_error = f"Link requires authentication or returned HTML view instead of workbook (HTTP 200 from {target})"
                        continue

                    raw_bytes = resp.content
                    final_url = resp.url
                    break
                else:
                    last_error = f"HTTP {resp.status_code} from {target}"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {str(exc)}"
                log.warning("ExcelOnlineConnector attempt failed for %s: %s", target, exc)

        return raw_bytes, final_url, last_error

    @classmethod
    def list_worksheets(cls, url: str, timeout: int = 30) -> List[str]:
        """
        Inspects an online Excel workbook and returns the list of worksheet tab names.
        """
        raw_bytes, _, _ = cls.fetch_workbook_bytes(url, timeout=timeout)
        if not raw_bytes:
            return []

        try:
            excel_file = pd.ExcelFile(io.BytesIO(raw_bytes), engine="openpyxl")
            return [str(s) for s in excel_file.sheet_names]
        except Exception:
            try:
                excel_file = pd.ExcelFile(io.BytesIO(raw_bytes))
                return [str(s) for s in excel_file.sheet_names]
            except Exception:
                return []

    @classmethod
    def load_url(
        cls,
        url: str,
        sheet_name: Optional[Union[str, int]] = 0,
        timeout: int = 30,
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Fetches an Excel workbook from an online link and returns (DataFrame, metadata).
        """
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        raw_bytes, final_url, last_error = cls.fetch_workbook_bytes(url, timeout=timeout)
        if raw_bytes is None or len(raw_bytes) == 0:
            raise ValueError(
                f"Could not download Excel workbook from link ({last_error}). "
                "Ensure the link has 'Anyone with the link can view' permissions in OneDrive or SharePoint."
            )

        # Parse downloaded workbook bytes
        metadata = {
            "source_url": url,
            "final_url": final_url,
            "byte_size": len(raw_bytes),
            "sheets": [],
        }

        # 1. Try reading as modern XLSX or XLS with openpyxl
        try:
            excel_file = pd.ExcelFile(io.BytesIO(raw_bytes), engine="openpyxl")
            metadata["sheets"] = excel_file.sheet_names
            target_sheet = sheet_name
            if isinstance(target_sheet, str) and target_sheet not in excel_file.sheet_names:
                target_sheet = excel_file.sheet_names[0]
            df = excel_file.parse(target_sheet)
            log.info("ExcelOnlineConnector: parsed XLSX with openpyxl (%d rows x %d cols)", *df.shape)
            return df, metadata
        except Exception as xlsx_err:
            log.info("openpyxl parse failed (%s), trying alternate decoders", xlsx_err)

        # 2. Try generic pd.read_excel
        try:
            df = pd.read_excel(io.BytesIO(raw_bytes))
            log.info("ExcelOnlineConnector: parsed with default Excel engine (%d rows x %d cols)", *df.shape)
            return df, metadata
        except Exception:
            pass

        # 3. Try CSV / Delimited text fallback
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
                if not df.empty:
                    log.info("ExcelOnlineConnector: parsed as CSV (%d rows x %d cols)", *df.shape)
                    return df, metadata
            except Exception:
                continue

        raise ValueError(
            "Downloaded file could not be parsed as an Excel workbook or CSV. "
            "Please verify that the link points directly to a valid spreadsheet."
        )
