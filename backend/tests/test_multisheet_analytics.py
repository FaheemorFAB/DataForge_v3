"""
Unit and Integration Tests for Multi-Sheet & Multi-Table Analytics
══════════════════════════════════════════════════════════════════
Tests multi-sheet workbook inspection, batch extraction, DuckDB pushdown,
referential integrity auditing, and parent-child drill-downs.
"""

import io
import pytest
import pandas as pd
import numpy as np

from dataforge.api.storage.manager import save, load, exists, STORE_DIR
from dataforge.join_engine import DuckDBJoinEngine, _sanitize_table_name
from dataforge.sheets_inspector import WorkbookInspector


@pytest.fixture
def sample_multisheet_excel() -> bytes:
    """Generates an in-memory 3-sheet Excel workbook with relational keys."""
    customers = pd.DataFrame({
        "customer_id": ["C101", "C102", "C103", "C104"],
        "customer_name": ["Acme Corp", "Beta LLC", "Gamma Inc", "Delta Co"],
        "region": ["North", "South", "East", "West"],
    })
    orders = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "customer_id": ["C101", "C102", "C102", "C105", "C106"],  # C105, C106 are orphans
        "total_amount": [250.0, 120.0, 430.0, 89.0, 670.0],
    })
    products = pd.DataFrame({
        "product_id": ["P1", "P2", "P3"],
        "sku": ["SKU-001", "SKU-002", "SKU-003"],
        "price": [19.99, 49.99, 99.99],
    })

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        customers.to_excel(writer, sheet_name="Customers", index=False)
        orders.to_excel(writer, sheet_name="Orders", index=False)
        products.to_excel(writer, sheet_name="Products", index=False)

    return bio.getvalue()


def test_inspect_excel_bytes(sample_multisheet_excel):
    """Verify workbook inspector extracts all sheets, columns, and previews."""
    res = WorkbookInspector.inspect_excel_bytes(sample_multisheet_excel, "company_data.xlsx")
    assert res["ok"] is True
    assert res["total_sheets"] == 3

    sheet_names = [s["sheet_name"] for s in res["sheets"]]
    assert "Customers" in sheet_names
    assert "Orders" in sheet_names
    assert "Products" in sheet_names

    cust_meta = next(s for s in res["sheets"] if s["sheet_name"] == "Customers")
    assert "customer_id" in cust_meta["columns"]
    assert "customer_name" in cust_meta["columns"]
    assert cust_meta["table_name"] == "customers"


def test_import_selected_sheets(sample_multisheet_excel):
    """Verify selective batch extraction into DuckDB workspace tables."""
    upload_id = "test_multisheet_import_999"

    # Set up primary table
    primary_df = pd.DataFrame({"id": [1, 2], "val": ["A", "B"]})
    save(upload_id, "df_raw", primary_df)
    save(upload_id, "profile", {"filename": "primary.csv", "columns": ["id", "val"]})

    # Batch import Customers and Orders
    imported = WorkbookInspector.import_selected_sheets(
        upload_id=upload_id,
        raw_bytes=sample_multisheet_excel,
        source_type="excel_local",
        selected_sheets=[
            {"sheet_name": "Customers", "table_name": "customers"},
            {"sheet_name": "Orders", "table_name": "orders"},
        ],
    )

    assert len(imported) == 2
    imported_tables = [item["table_name"] for item in imported]
    assert "customers" in imported_tables
    assert "orders" in imported_tables

    tables = DuckDBJoinEngine.get_workspace_tables(upload_id)
    assert "customers" in tables
    assert "orders" in tables
    assert len(tables["customers"]) == 4
    assert len(tables["orders"]) == 5


def test_audit_referential_integrity(sample_multisheet_excel):
    """Verify deep referential integrity audit, orphan detection, and health score."""
    upload_id = "test_integrity_audit_777"

    WorkbookInspector.import_selected_sheets(
        upload_id=upload_id,
        raw_bytes=sample_multisheet_excel,
        source_type="excel_local",
        selected_sheets=[
            {"sheet_name": "Customers", "table_name": "customers"},
            {"sheet_name": "Orders", "table_name": "orders"},
        ],
    )

    # Orders has 5 rows: C101, C102 (2x), C105, C106.
    # Customers has C101, C102, C103, C104.
    # So C105 and C106 are orphans in orders when referencing customers.customer_id.
    audit = DuckDBJoinEngine.audit_referential_integrity(
        upload_id=upload_id,
        left_table="orders",
        left_column="customer_id",
        right_table="customers",
        right_column="customer_id",
    )

    assert audit["ok"] is True
    metrics = audit["referential_metrics"]
    assert metrics["matched_keys_count"] == 2  # C101, C102
    assert metrics["orphan_keys_count"] == 2   # C105, C106
    assert metrics["orphan_rows_count"] == 2
    assert "C105" in metrics["orphan_samples"] or "C106" in metrics["orphan_samples"]
    assert 0 <= metrics["health_score"] <= 100
    assert len(audit["recommendations"]) >= 1


def test_drill_down_query(sample_multisheet_excel):
    """Verify instant parent-child drill down for child records."""
    upload_id = "test_drill_down_555"

    WorkbookInspector.import_selected_sheets(
        upload_id=upload_id,
        raw_bytes=sample_multisheet_excel,
        source_type="excel_local",
        selected_sheets=[
            {"sheet_name": "Customers", "table_name": "customers"},
            {"sheet_name": "Orders", "table_name": "orders"},
        ],
    )

    # Drill down into orders for customer C102 (should have 2 orders)
    drill = DuckDBJoinEngine.drill_down_query(
        upload_id=upload_id,
        parent_table="customers",
        child_table="orders",
        parent_column="customer_id",
        child_column="customer_id",
        parent_value="C102",
        limit=10,
    )

    assert drill["ok"] is True
    assert drill["total_matches"] == 2
    assert drill["returned_count"] == 2
    assert all(r["customer_id"] == "C102" for r in drill["records"])


def test_companion_sheets_detection(sample_multisheet_excel):
    """Verify detection of companion sheets stored in workspace cache."""
    upload_id = "test_companion_detection_333"

    # Cache raw workbook
    raw_wb_path = STORE_DIR / upload_id / "raw_workbook.xlsx"
    raw_wb_path.parent.mkdir(parents=True, exist_ok=True)
    raw_wb_path.write_bytes(sample_multisheet_excel)

    # Only import customers initially
    WorkbookInspector.import_selected_sheets(
        upload_id=upload_id,
        raw_bytes=sample_multisheet_excel,
        source_type="excel_local",
        selected_sheets=[{"sheet_name": "Customers", "table_name": "customers"}],
    )

    origin = WorkbookInspector.detect_workspace_origin(upload_id)
    assert origin["has_companion_sheets"] is True
    assert origin["total_sheets"] == 3
    assert origin["imported_count"] == 1
    unimported = [s["sheet_name"] for s in origin["unimported_sheets"]]
    assert "Orders" in unimported
    assert "Products" in unimported
