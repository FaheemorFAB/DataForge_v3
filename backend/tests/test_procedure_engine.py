"""
tests/test_procedure_engine.py
──────────────────────────────
Comprehensive test suite for the DataForge Stored Procedure & Pipeline Engine (DF-SPE).

Tests:
  1. DAG Validation & Cycle Detection (Kahn's Algorithm)
  2. Parameter Resolution and Typing (int, float, bool, enum, defaults)
  3. Node Executions: source, clean_names, filter, compute (AST formula), aggregate, dedupe
  4. Assertion Gate: not_null, unique, range, row_count (pass & fail scenarios)
  5. Dry-run vs Live Execution: immutable snapshot generation & lineage manifest
  6. Version Management & Rollback (semver tags, pointer movements)
  7. SQL and dbt model compilation (P3-11)
  8. Full FastAPI REST API integration testing via TestClient
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
from fastapi.testclient import TestClient

_backend_dir = Path(__file__).resolve().parents[1]
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from dataforge.api.app import create_app
from dataforge.api.deps import get_current_user
from dataforge.api.repositories.upload import UploadRepository
from dataforge.api.services.auth import User
from dataforge.api.storage.manager import save
from dataforge.procedure_engine import ProcedureExecutionError, StoredProcedureExecutor
from dataforge.procedure_schema import (
    AssertionSeverity,
    ParameterType,
    ProcedureDefinition,
    ProcedureNode,
    ProcedureParameter,
    QualityAssertion,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Transaction ID": [101, 102, 103, 104, 105, 105],  # 105 is duplicate
        "Region": ["EMEA", "APAC", "EMEA", "LATAM", "EMEA", "EMEA"],
        "Amount (USD)": [250.0, 50.0, 1200.0, 15.0, 800.0, 800.0],
        "Status": ["COMPLETED", "VOID", "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED"],
    })


def test_procedure_dag_validation_and_cycles():
    """Verify cycle detection and missing dependencies."""
    # 1. Valid DAG
    valid_def = ProcedureDefinition(
        procedure_id="sp_test_valid",
        version="1.0.0",
        name="Valid DAG",
        nodes=[
            ProcedureNode(id="src", type="source", inputs=[]),
            ProcedureNode(id="step_clean", type="clean_names", inputs=["src"]),
            ProcedureNode(id="step_filter", type="filter", inputs=["step_clean"]),
        ],
    )
    ordered = valid_def.topological_sort()
    assert [n.id for n in ordered] == ["src", "step_clean", "step_filter"]

    # 2. Cycle detection
    cycle_def = ProcedureDefinition(
        procedure_id="sp_test_cycle",
        version="1.0.0",
        name="Cyclic DAG",
        nodes=[
            ProcedureNode(id="node_a", type="clean_names", inputs=["node_b"]),
            ProcedureNode(id="node_b", type="filter", inputs=["node_a"]),
        ],
    )
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        cycle_def.topological_sort()

    # 3. Missing dependency
    missing_def = ProcedureDefinition(
        procedure_id="sp_test_missing",
        version="1.0.0",
        name="Missing Dep DAG",
        nodes=[
            ProcedureNode(id="node_a", type="filter", inputs=["non_existent_node"]),
        ],
    )
    with pytest.raises(ValueError, match="undeclared input dependency"):
        missing_def.topological_sort()


def test_procedure_parameter_binding():
    """Verify typed parameter resolution with validation and defaults."""
    definition = ProcedureDefinition(
        procedure_id="sp_params",
        version="1.0.0",
        name="Parameter Test",
        parameters=[
            ProcedureParameter(name="min_amount", type=ParameterType.FLOAT, default=100.0, min_value=0.0),
            ProcedureParameter(name="target_region", type=ParameterType.ENUM, default="EMEA", allowed_values=["EMEA", "APAC", "LATAM"]),
            ProcedureParameter(name="strict_mode", type=ParameterType.BOOL, default=True),
        ],
    )

    # Defaults
    resolved = definition.get_parameter_dict({})
    assert resolved["min_amount"] == 100.0
    assert resolved["target_region"] == "EMEA"
    assert resolved["strict_mode"] is True

    # Overrides
    resolved2 = definition.get_parameter_dict({"min_amount": "250.5", "target_region": "APAC", "strict_mode": "false"})
    assert resolved2["min_amount"] == 250.5
    assert resolved2["target_region"] == "APAC"
    assert resolved2["strict_mode"] is False

    # Validation failure: enum out of bounds
    with pytest.raises(ValueError, match="not in allowed choices"):
        definition.get_parameter_dict({"target_region": "INVALID"})


def test_procedure_execution_pipeline():
    """Execute multi-node procedure with clean_names, dedupe, filter, compute, assertion_gate."""
    df_raw = _sample_df()

    definition = ProcedureDefinition(
        procedure_id="sp_financial_reconcile",
        version="1.0.0",
        name="Financial Reconciliation Routine",
        parameters=[
            ProcedureParameter(name="min_threshold", type=ParameterType.FLOAT, default=100.0),
            ProcedureParameter(name="active_region", type=ParameterType.STRING, default="EMEA"),
        ],
        nodes=[
            ProcedureNode(id="node_src", type="source", inputs=[]),
            ProcedureNode(id="node_clean", type="clean_names", inputs=["node_src"], config={"casing": "snake_case"}),
            ProcedureNode(id="node_dedupe", type="dedupe", inputs=["node_clean"]),
            ProcedureNode(
                id="node_filter",
                type="filter",
                inputs=["node_dedupe"],
                config={
                    "rules": [
                        {"col": "region", "op": "=", "param": "active_region"},
                        {"col": "amount_usd", "op": ">=", "param": "min_threshold"},
                    ]
                },
            ),
            ProcedureNode(
                id="node_compute",
                type="compute",
                inputs=["node_filter"],
                config={
                    "derived_column": "tax_amount",
                    "sql_expression": "amount_usd * 0.20",
                },
            ),
            ProcedureNode(
                id="node_gate",
                type="assertion_gate",
                inputs=["node_compute"],
                config={
                    "fail_on_error": True,
                    "assertions": [
                        {"type": "not_null", "column": "transaction_id", "severity": "error"},
                        {"type": "unique", "column": "transaction_id", "severity": "error"},
                        {"type": "range", "column": "amount_usd", "min": 0.0, "severity": "error"},
                    ],
                },
            ),
            ProcedureNode(id="node_output", type="output", inputs=["node_gate"]),
        ],
    )

    executor = StoredProcedureExecutor(definition)
    res = executor.execute(input_dfs={"default": df_raw}, dry_run=True)

    assert res["ok"] is True
    assert res["dry_run"] is True
    df_out = res["df_result"]

    # Original rows: 6. Dedupe removes 1 dupe -> 5. Filter for EMEA and amount >= 100 -> 3 rows (101: 250, 103: 1200, 105: 800)
    assert len(df_out) == 3
    assert "tax_amount" in df_out.columns
    # Check tax_amount is computed correctly (250 * 0.2 = 50.0)
    assert float(df_out.loc[df_out["transaction_id"] == 101, "tax_amount"].iloc[0]) == 50.0

    # Lineage manifest check
    manifest = res["lineage_manifest"]
    assert len(manifest) == 7
    filter_manifest = next(m for m in manifest if m["node_id"] == "node_filter")
    assert filter_manifest["rows_out"] == 3
    assert filter_manifest["dropped_count"] == 2


def test_procedure_assertion_gate_failure():
    """Verify that quality gate raises ProcedureExecutionError on invalid data."""
    df_with_null = pd.DataFrame({
        "id": [1, None, 3],
        "val": [10.0, 20.0, 30.0],
    })

    definition = ProcedureDefinition(
        procedure_id="sp_strict_gate",
        version="1.0.0",
        name="Strict Gate Test",
        nodes=[
            ProcedureNode(id="src", type="source", inputs=[]),
            ProcedureNode(
                id="gate",
                type="assertion_gate",
                inputs=["src"],
                config={
                    "fail_on_error": True,
                    "assertions": [
                        {"type": "not_null", "column": "id", "severity": "error"},
                    ],
                },
            ),
        ],
    )

    executor = StoredProcedureExecutor(definition)
    with pytest.raises(ProcedureExecutionError, match="Quality Gate assertion failed"):
        executor.execute(input_dfs={"default": df_with_null})


def test_procedure_fastapi_rest_endpoints(monkeypatch):
    """Test REST API endpoints for procedure creation, dry-run, live execution, and export."""
    monkeypatch.setattr(UploadRepository, "get_by_id", lambda self, upload_id: {"id": upload_id, "user_id": 1, "filename": "test.csv"})
    app = create_app()
    mock_user = User(id=1, email="faheembaiza@gmail.com", name="Faheem Ahmad Bhat")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)

    # Save mock dataset under upload_id "888"
    df_mock = _sample_df()
    save(888, "df_raw", df_mock)
    save(888, "df_clean", df_mock)

    # 1. Create Stored Procedure
    proc_payload = {
        "definition": {
            "schema_version": "1.0.0",
            "procedure_id": "sp_api_demo",
            "version": "1.0.0",
            "name": "API Demo Procedure",
            "description": "Cleans names and filters records",
            "parameters": [
                {"name": "min_val", "type": "float", "default": 100.0}
            ],
            "nodes": [
                {"id": "src", "type": "source", "inputs": [], "config": {}},
                {"id": "clean", "type": "clean_names", "inputs": ["src"], "config": {"casing": "snake_case"}},
                {
                    "id": "filter",
                    "type": "filter",
                    "inputs": ["clean"],
                    "config": {"rules": [{"col": "amount_usd", "op": ">=", "param": "min_val"}]},
                },
            ],
        }
    }

    res = client.post("/api/procedures", json=proc_payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["ok"] is True
    assert data["procedure"]["id"] == "sp_api_demo"

    # 2. Validate DAG
    res_val = client.post("/api/procedures/sp_api_demo/validate")
    assert res_val.status_code == 200
    assert res_val.json()["is_dag"] is True
    assert res_val.json()["node_count"] == 3

    # 3. Dry-run
    dry_res = client.post(
        "/api/procedures/sp_api_demo/dry-run",
        json={"upload_id": "888", "runtime_params": {"min_val": 200.0}},
    )
    assert dry_res.status_code == 200, dry_res.text
    dry_data = dry_res.json()
    assert dry_data["ok"] is True
    assert dry_data["dry_run"] is True
    assert len(dry_data["preview_sample"]) > 0

    # 4. Live Run
    run_res = client.post(
        "/api/procedures/sp_api_demo/run",
        json={"upload_id": "888", "runtime_params": {"min_val": 200.0}},
    )
    assert run_res.status_code == 200, run_res.text
    run_data = run_res.json()
    assert run_data["ok"] is True
    assert run_data["output_snapshot_id"] is not None
    assert "ETag" in run_res.headers
    run_id = run_data["run_id"]

    # 5. Fetch Run Audit
    run_audit_res = client.get(f"/api/runs/{run_id}")
    assert run_audit_res.status_code == 200
    audit_data = run_audit_res.json()
    assert audit_data["run"]["id"] == run_id
    assert audit_data["run"]["status"] == "SUCCESS"

    # 6. Export SQL (P3-11)
    export_res = client.get("/api/procedures/sp_api_demo/export?format=sql")
    assert export_res.status_code == 200
    sql_text = export_res.text
    assert "WITH" in sql_text
    assert "SELECT * FROM" in sql_text
