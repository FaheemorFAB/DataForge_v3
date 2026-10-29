"""
DataForge Multi-Sheet Workbook Inspector & Ingestion Service
════════════════════════════════════════════════════════════
Inspects local Excel workbooks, Google Sheets, and Excel Online files
for multiple worksheets, schema metadata, and batch extraction into
relational DuckDB tables.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
import pandas as pd

from dataforge.api.storage.manager import STORE_DIR, load
from dataforge.excel_online_connector import ExcelOnlineConnector
from dataforge.join_engine import DuckDBJoinEngine, _sanitize_table_name
from dataforge.sheets_connector import SheetsConnector

log = logging.getLogger(__name__)


class WorkbookInspector:
    """
    Analyzes multi-sheet workbooks across local files, Google Sheets, and OneDrive
    without loading entire multi-gigabyte workbooks into memory at once.
    """

    @classmethod
    def inspect_excel_bytes(cls, raw: bytes, filename: str = "workbook.xlsx") -> Dict[str, Any]:
        """
        Inspects an in-memory Excel workbook (.xlsx / .xls) and extracts sheet summaries:
        sheet names, estimated row/col counts, and preview column headers.
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "xlsx"
        sheets_meta: List[Dict[str, Any]] = []

        if ext == "xlsx":
            try:
                # Use read_only mode for fast header extraction without full DOM loading
                wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    # Read first row for headers
                    headers: List[str] = []
                    sample_rows: List[List[Any]] = []
                    row_iter = ws.iter_rows(values_only=True)

                    try:
                        first_row = next(row_iter, None)
                        if first_row:
                            headers = [
                                str(c).strip() if c is not None and str(c).strip() else f"col_{idx+1}"
                                for idx, c in enumerate(first_row)
                            ]
                            # Read up to 2 preview rows
                            for _ in range(2):
                                r = next(row_iter, None)
                                if r:
                                    sample_rows.append([str(v) if v is not None else "" for v in r[:len(headers)]])
                    except Exception as e:
                        log.debug("Error iterating rows in sheet %s: %s", sheet_name, e)

                    max_r = ws.max_row or 0
                    max_c = ws.max_column or len(headers)

                    clean_name = _sanitize_table_name(sheet_name)
                    sheets_meta.append({
                        "sheet_name": sheet_name,
                        "table_name": clean_name,
                        "row_count": max_r,
                        "col_count": max_c,
                        "columns": headers,
                        "sample_preview": sample_rows,
                    })
                wb.close()
                return {
                    "ok": True,
                    "source_type": "excel_local",
                    "filename": filename,
                    "total_sheets": len(sheets_meta),
                    "sheets": sheets_meta,
                }
            except Exception as exc:
                log.warning("openpyxl inspection failed for %s, falling back to pd.ExcelFile: %s", filename, exc)

        # Fallback using pandas ExcelFile (handles .xls and edge-case .xlsx)
        try:
            xl = pd.ExcelFile(io.BytesIO(raw))
            for sheet_name in xl.sheet_names:
                df_sample = xl.parse(sheet_name, nrows=3)
                clean_name = _sanitize_table_name(sheet_name)
                sheets_meta.append({
                    "sheet_name": sheet_name,
                    "table_name": clean_name,
                    "row_count": -1,  # Unknown without full parse
                    "col_count": len(df_sample.columns),
                    "columns": [str(c) for c in df_sample.columns],
                    "sample_preview": df_sample.head(2).fillna("").astype(str).values.tolist(),
                })
            return {
                "ok": True,
                "source_type": "excel_local",
                "filename": filename,
                "total_sheets": len(sheets_meta),
                "sheets": sheets_meta,
            }
        except Exception as exc:
            log.exception("Excel inspection failed completely: %s", exc)
            return {
                "ok": False,
                "error": f"Failed to inspect Excel workbook: {exc}",
                "sheets": [],
            }

    @classmethod
    def inspect_google_sheets(cls, url: str) -> Dict[str, Any]:
        """Inspects a public Google Sheets URL to list available worksheet tabs."""
        conn = SheetsConnector()
        try:
            sheet_names = conn.list_public_worksheets(url)
            info = conn.parse_sheet_url(url)
            sheet_id = getattr(info, "sheet_id", info[0] if isinstance(info, (tuple, list)) else None)

            sheets_meta: List[Dict[str, Any]] = []
            for name in sheet_names:
                clean_name = _sanitize_table_name(name)
                sheets_meta.append({
                    "sheet_name": name,
                    "table_name": clean_name,
                    "row_count": -1,
                    "col_count": -1,
                    "columns": [],
                    "sample_preview": [],
                })

            return {
                "ok": True,
                "source_type": "google_sheets",
                "sheet_id": sheet_id,
                "url": url,
                "total_sheets": len(sheets_meta),
                "sheets": sheets_meta,
            }
        except Exception as exc:
            log.exception("Google Sheets inspection failed: %s", exc)
            return {
                "ok": False,
                "error": f"Failed to inspect Google Sheet: {exc}",
                "sheets": [],
            }

    @classmethod
    def inspect_excel_online(cls, url: str) -> Dict[str, Any]:
        """Inspects an Excel Online / OneDrive / SharePoint workbook URL."""
        try:
            sheet_names = ExcelOnlineConnector.list_worksheets(url)
            sheets_meta: List[Dict[str, Any]] = []
            for name in sheet_names:
                clean_name = _sanitize_table_name(name)
                sheets_meta.append({
                    "sheet_name": name,
                    "table_name": clean_name,
                    "row_count": -1,
                    "col_count": -1,
                    "columns": [],
                    "sample_preview": [],
                })

            return {
                "ok": True,
                "source_type": "excel_online",
                "url": url,
                "total_sheets": len(sheets_meta),
                "sheets": sheets_meta,
            }
        except Exception as exc:
            log.exception("Excel Online inspection failed: %s", exc)
            return {
                "ok": False,
                "error": f"Failed to inspect Excel Online workbook: {exc}",
                "sheets": [],
            }

    @classmethod
    def detect_workspace_origin(cls, upload_id: str) -> Dict[str, Any]:
        """
        Inspects the active workspace to detect if it originated from a multi-sheet file
        or cloud link, and returns any unimported companion sheets.
        """
        existing_tables = DuckDBJoinEngine.get_workspace_tables(upload_id)
        existing_names = set(existing_tables.keys())

        # Check stored workbook cache if available
        raw_wb_path = STORE_DIR / str(upload_id) / "raw_workbook.xlsx"
        if raw_wb_path.exists():
            try:
                raw_bytes = raw_wb_path.read_bytes()
                insp = cls.inspect_excel_bytes(raw_bytes, "raw_workbook.xlsx")
                if insp.get("ok"):
                    unimported = [
                        s for s in insp.get("sheets", [])
                        if s["table_name"] not in existing_names
                    ]
                    return {
                        "has_companion_sheets": len(unimported) > 0,
                        "origin_type": "excel_local",
                        "total_sheets": insp.get("total_sheets", 0),
                        "imported_count": len(existing_names),
                        "unimported_sheets": unimported,
                    }
            except Exception as e:
                log.warning("Failed inspecting raw_workbook.xlsx: %s", e)

        # Check metadata source_config
        meta = load(upload_id, "meta") or {}
        source_config = meta.get("source_config") or {}
        url = source_config.get("url")

        if url:
            if "docs.google.com" in url:
                insp = cls.inspect_google_sheets(url)
                if insp.get("ok"):
                    unimported = [
                        s for s in insp.get("sheets", [])
                        if s["table_name"] not in existing_names
                    ]
                    return {
                        "has_companion_sheets": len(unimported) > 0,
                        "origin_type": "google_sheets",
                        "url": url,
                        "total_sheets": insp.get("total_sheets", 0),
                        "imported_count": len(existing_names),
                        "unimported_sheets": unimported,
                    }
            elif ExcelOnlineConnector.is_excel_online_url(url):
                insp = cls.inspect_excel_online(url)
                if insp.get("ok"):
                    unimported = [
                        s for s in insp.get("sheets", [])
                        if s["table_name"] not in existing_names
                    ]
                    return {
                        "has_companion_sheets": len(unimported) > 0,
                        "origin_type": "excel_online",
                        "url": url,
                        "total_sheets": insp.get("total_sheets", 0),
                        "imported_count": len(existing_names),
                        "unimported_sheets": unimported,
                    }

        return {
            "has_companion_sheets": False,
            "origin_type": "unknown",
            "unimported_sheets": [],
        }

    @classmethod
    def import_selected_sheets(
        cls,
        upload_id: str,
        raw_bytes: Optional[bytes] = None,
        source_url: Optional[str] = None,
        source_type: str = "excel_local",
        selected_sheets: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extracts selected sheets and saves them into the workspace tables directory
        as DuckDB-ready parquet files.
        selected_sheets is a list of dicts: [{"sheet_name": "...", "table_name": "..."}]
        """
        imported: List[Dict[str, Any]] = []
        if not selected_sheets:
            return imported

        if source_type == "excel_local":
            data_bytes = raw_bytes
            if data_bytes is None:
                raw_wb_path = STORE_DIR / str(upload_id) / "raw_workbook.xlsx"
                if raw_wb_path.exists():
                    data_bytes = raw_wb_path.read_bytes()

            if not data_bytes:
                raise ValueError("No workbook data provided or found in workspace cache.")

            # Load selected sheets
            xl = pd.ExcelFile(io.BytesIO(data_bytes))
            for item in selected_sheets:
                s_name = item.get("sheet_name")
                t_name = item.get("table_name") or s_name
                if not s_name or s_name not in xl.sheet_names:
                    continue

                df = xl.parse(s_name)
                # Clean column headers
                df.columns = [str(c).strip() if str(c).strip() else f"col_{i+1}" for i, c in enumerate(df.columns)]
                saved_name = DuckDBJoinEngine.save_workspace_table(upload_id, t_name, df)
                imported.append({
                    "sheet_name": s_name,
                    "table_name": saved_name,
                    "row_count": len(df),
                    "col_count": len(df.columns),
                })

        elif source_type == "google_sheets":
            if not source_url:
                raise ValueError("Google Sheets URL is required.")
            conn = SheetsConnector()
            for item in selected_sheets:
                s_name = item.get("sheet_name")
                t_name = item.get("table_name") or s_name
                if not s_name:
                    continue
                df = conn.load_from_url(source_url, sheet_name=s_name)
                df.columns = [str(c).strip() if str(c).strip() else f"col_{i+1}" for i, c in enumerate(df.columns)]
                saved_name = DuckDBJoinEngine.save_workspace_table(upload_id, t_name, df)
                imported.append({
                    "sheet_name": s_name,
                    "table_name": saved_name,
                    "row_count": len(df),
                    "col_count": len(df.columns),
                })

        elif source_type == "excel_online":
            if not source_url:
                raise ValueError("Excel Online URL is required.")
            raw_wb, _, _ = ExcelOnlineConnector.fetch_workbook_bytes(source_url)
            if not raw_wb:
                raise ValueError("Failed downloading Excel Online workbook bytes.")

            xl = pd.ExcelFile(io.BytesIO(raw_wb))
            for item in selected_sheets:
                s_name = item.get("sheet_name")
                t_name = item.get("table_name") or s_name
                if not s_name or s_name not in xl.sheet_names:
                    continue
                df = xl.parse(s_name)
                df.columns = [str(c).strip() if str(c).strip() else f"col_{i+1}" for i, c in enumerate(df.columns)]
                saved_name = DuckDBJoinEngine.save_workspace_table(upload_id, t_name, df)
                imported.append({
                    "sheet_name": s_name,
                    "table_name": saved_name,
                    "row_count": len(df),
                    "col_count": len(df.columns),
                })

        return imported
