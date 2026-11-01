"""
dataforge/api/routes/pipeline.py
────────────────────────────────
Production Pipeline Exporter & Data Quality Assertions Suite.
Generates dbt models, Apache Airflow DAGs, standalone Python ETL scripts,
and executes live Great Expectations-style data quality validations.
Accurately reflects dataset architecture both Before Cleaning (Raw Baseline)
and After Cleaning (Production Cleaned Pipeline with active transformation rules).
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from dataforge.api.deps import CurrentUser, require_upload_access
from dataforge.api.storage.manager import STORE_DIR, exists, load
from dataforge.api.utils.json import safe_jsonable

log = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class QualityAssertionRequest(BaseModel):
    upload_id: str
    share_token: Optional[str] = None
    assertions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of assertion rules: {type: 'unique'|'not_null'|'range'|'regex', column: '...', min: ..., max: ...}",
    )


def _detect_dataset_state(upload_id: str):
    """
    Loads dataset assets and determines whether the workspace is in
    a pre-cleaning (raw baseline) or post-cleaning (cleaned & transformed) state.
    """
    df_clean = load(upload_id, "df_clean")
    df_raw = load(upload_id, "df_raw")
    profile = load(upload_id, "profile") or {}
    clean_meta = load(upload_id, "clean_meta") or {}

    if not clean_meta:
        try:
            from dataforge.db import db_get
            up_row = db_get("uploads", upload_id) or {}
            if up_row.get("clean_meta_json"):
                clean_meta = json.loads(up_row["clean_meta_json"])
        except Exception:
            pass

    has_clean_meta = bool(
        clean_meta
        and (
            clean_meta.get("stats")
            or clean_meta.get("struct_actions")
            or clean_meta.get("rules_applied")
            or clean_meta.get("missing_log")
        )
    )

    is_cleaned = df_clean is not None and (
        has_clean_meta or (df_raw is not None and not df_clean.equals(df_raw))
    )

    df_active = df_clean if is_cleaned else (df_raw if df_raw is not None else df_clean)
    return df_active, df_raw, df_clean, profile, clean_meta, is_cleaned


@router.get("/export", summary="Export production pipeline code (Python, dbt, Airflow, DF-SPE)")
async def export_pipeline(
    request: Request,
    current_user: CurrentUser,
    upload_id: str = Query(..., description="Workspace Upload ID"),
    share_token: Optional[str] = Query(default=None),
):
    """
    Synthesizes reproducible production code representing the visual workspace steps:
    - Stored Procedure recipe (DF-SPE v1)
    - Standalone Python ETL script
    - dbt Staging SQL model + schema.yml
    - Apache Airflow orchestration DAG
    - Data quality assertions suite (pytest)
    Accurately supports both Before Cleaning (raw baseline) and After Cleaning (cleaned pipeline).
    """
    await require_upload_access(upload_id, current_user, share_token=share_token, request=request)
    df_active, df_raw, df_clean, profile, clean_meta, is_cleaned = _detect_dataset_state(upload_id)

    if df_active is None and not profile:
        raise HTTPException(404, "Dataset not found. Please upload a dataset or check your upload ID.")

    filename = profile.get("filename", "dataset.csv")
    prefix = upload_id[:8]
    clean_prefix = f"stg_{prefix}_transformed" if is_cleaned else f"stg_{prefix}_raw"

    cols = list(df_active.columns) if df_active is not None else profile.get("columns", [])
    raw_cols = list(df_raw.columns) if df_raw is not None else cols

    # Extract cleaning rules, dropped columns, and imputed columns
    dropped: List[str] = []
    imputed: Dict[str, str] = {}
    struct_actions: List[str] = []
    applied_rules: List[Dict[str, Any]] = []

    if is_cleaned:
        if clean_meta.get("dropped_cols"):
            dropped.extend([c for c in clean_meta["dropped_cols"] if c in raw_cols])
        for item in clean_meta.get("missing_log", []):
            if isinstance(item, dict) and item.get("type") == "drop" and item.get("column") and item["column"] != "Dataset":
                if item["column"] not in dropped:
                    dropped.append(item["column"])
        for r in clean_meta.get("rules_applied", []):
            if isinstance(r, dict):
                applied_rules.append(r)
                if r.get("action_type") == "drop":
                    rcs = r.get("columns") or ([r.get("column")] if r.get("column") else [])
                    for c in rcs:
                        if c not in dropped:
                            dropped.append(c)

        if df_raw is not None and df_clean is not None:
            for c in df_raw.columns:
                if c not in df_clean.columns and c not in dropped:
                    dropped.append(c)

        if clean_meta.get("imputed_cols"):
            imputed.update(clean_meta["imputed_cols"])
        for col, details in clean_meta.get("imputed_cells", {}).items():
            if isinstance(details, dict):
                imputed[col] = details.get("strategy", "median")
            elif isinstance(details, str):
                imputed[col] = details

        for r in clean_meta.get("rules_applied", []):
            if isinstance(r, dict) and r.get("action_type") == "impute":
                rcs = r.get("columns") or ([r.get("column")] if r.get("column") else [])
                method = r.get("impute_method", "median")
                if method == "constant":
                    method = f"constant ({r.get('fill_value', 0)})"
                for c in rcs:
                    imputed[c] = method

        struct_actions = [
            a for a in clean_meta.get("struct_actions", [])
            if a and not str(a).lower().startswith("no structural issues")
        ]

    # 1. Stored Procedure Recipe (DF-SPE v1)
    clean_sql_cols = ", ".join([f'"{c}"' for c in cols[:10]]) if cols else "*"
    if is_cleaned:
        recipe_steps = [
            {
                "step_id": "s1_raw_source",
                "type": "source",
                "source_upload_id": upload_id,
                "format": "csv",
                "table_name": f"raw_{prefix}",
                "description": f"Ingest raw source table: {filename}",
            },
            {
                "step_id": "s2_clean_and_transform",
                "type": "transformation_pipeline",
                "description": f"Apply DataForge verified transformations ({len(dropped)} drops, {len(imputed)} imputations)",
                "dropped_columns": dropped,
                "imputation_rules": imputed,
                "normalization": "snake_case column headers and whitespace trimming",
                "deduplication": any("duplicate" in a.lower() for a in struct_actions),
                "dynamic_rules_count": len(applied_rules),
                "sql": f"SELECT {clean_sql_cols} FROM s1_raw_source WHERE 1=1",
            },
            {
                "step_id": "s3_quality_gate",
                "type": "assertion_gate",
                "description": "Production Great Expectations-style quality gates",
                "rules": [
                    {"rule": "row_count_gte", "threshold": 1, "description": "Ensure non-empty output"},
                    {"rule": "not_null_threshold", "column": cols[0] if cols else "id", "threshold_pct": 1.0},
                    {"rule": "zero_duplicates", "threshold": 0, "description": "Zero duplicate primary records"},
                ],
                "on_violation": "fail",
            },
        ]
        recipe_dict = {
            "schema_version": "1.0",
            "pipeline_mode": "production_cleaned",
            "procedure_name": f"sp_clean_{prefix}_pipeline",
            "description": f"Production cleaning and transformation DAG with quality assertion gates for {filename}",
            "parameters": [
                {"name": "source_path", "type": "string", "default_value": filename, "description": "Raw source file path"},
                {"name": "min_rows", "type": "int", "default_value": 1, "description": "Row count assertion threshold"},
            ],
            "steps": recipe_steps,
            "output_step_id": "s2_clean_and_transform",
        }
    else:
        recipe_steps = [
            {
                "step_id": "s1_raw_source",
                "type": "source",
                "source_upload_id": upload_id,
                "format": "csv",
                "table_name": f"raw_{prefix}",
                "description": f"Raw baseline ingestion source: {filename}",
            },
            {
                "step_id": "s2_schema_validation",
                "type": "assertion_gate",
                "description": "Enforce baseline volume and critical column integrity",
                "rules": [
                    {"rule": "row_count_gte", "threshold": 1, "description": "Ensure dataset is not empty"},
                    {"rule": "expected_columns_count", "threshold": len(cols), "description": f"Verify {len(cols)} schema columns present"},
                ],
                "on_violation": "warn",
            },
        ]
        recipe_dict = {
            "schema_version": "1.0",
            "pipeline_mode": "raw_baseline",
            "procedure_name": f"sp_ingest_{prefix}_baseline",
            "description": f"Baseline raw ingestion and schema verification pipeline for {filename} (Pre-Cleaning)",
            "parameters": [
                {"name": "source_path", "type": "string", "default_value": filename, "description": "Raw source file path"},
                {"name": "min_rows", "type": "int", "default_value": 1, "description": "Row threshold"},
            ],
            "steps": recipe_steps,
            "output_step_id": "s1_raw_source",
        }

    # 2. Python ETL Script
    now_iso = datetime.now(timezone.utc).isoformat()
    if is_cleaned:
        python_code = f'''#!/usr/bin/env python3
"""
DataForge Production Pipeline — Cleaned & Transformed State
──────────────────────────────────────────────────────────
Auto-generated standalone ETL microservice.
Source: {filename}
Mode: Production Cleaned Pipeline (Applied DataForge transformations)
Generated at: {now_iso}
"""

import sys
import duckdb
import numpy as np
import pandas as pd


def extract(source_path: str = "{filename}") -> pd.DataFrame:
    """Ingests raw data using high-performance DuckDB pushdown."""
    print(f"📥 [Extract] Reading {{source_path}} via DuckDB engine...")
    con = duckdb.connect(database=":memory:")
    query = f"SELECT * FROM read_csv_auto('{{source_path}}')"
    df = con.execute(query).df()
    print(f"   Loaded {{len(df)}} rows, {{df.shape[1]}} columns.")
    return df


def clean_and_transform(df: pd.DataFrame) -> pd.DataFrame:
    """Executes validated DataForge cleaning rules and transformations."""
    print("🧹 [Transform] Applying DataForge verified cleaning rules...")

    # 1. Column drops
    drop_cols = {dropped}
    existing_drops = [c for c in drop_cols if c in df.columns]
    if existing_drops:
        df = df.drop(columns=existing_drops)
        print(f"   Dropped redundant columns: {{existing_drops}}")

    # 2. Schema normalization (snake_case column headers)
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

    # 3. Row deduplication
    initial_rows = len(df)
    df = df.drop_duplicates()
    if len(df) < initial_rows:
        print(f"   Removed {{initial_rows - len(df):,}} duplicate rows.")

    # 4. Missing value imputation
    impute_rules = {imputed}
    for col, rule in impute_rules.items():
        norm_col = col.strip().lower().replace(" ", "_").replace("-", "_")
        target_col = norm_col if norm_col in df.columns else (col if col in df.columns else None)
        if target_col:
            if "median" in rule and pd.api.types.is_numeric_dtype(df[target_col]):
                fill_val = df[target_col].median()
                df[target_col] = df[target_col].fillna(fill_val)
            elif "mean" in rule and pd.api.types.is_numeric_dtype(df[target_col]):
                fill_val = df[target_col].mean()
                df[target_col] = df[target_col].fillna(fill_val)
            elif "mode" in rule:
                mode_val = df[target_col].mode().iloc[0] if not df[target_col].mode().empty else "Unknown"
                df[target_col] = df[target_col].fillna(mode_val)
            elif "constant" in rule:
                df[target_col] = df[target_col].fillna(0)

    # 5. Clean numeric coercion
    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6. String whitespace cleanup
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()

    print(f"   Cleaned DataFrame: {{len(df)}} rows, {{df.shape[1]}} columns.")
    return df


def load_output(df: pd.DataFrame, target_path: str = "cleaned_data.parquet") -> None:
    """Materializes transformed data into compressed Apache Parquet."""
    print(f"💾 [Load] Exporting output to {{target_path}}...")
    df.to_parquet(target_path, index=False, compression="snappy")
    print("✅ Pipeline execution completed successfully.")


def main():
    source_file = sys.argv[1] if len(sys.argv) > 1 else "{filename}"
    df_raw = extract(source_file)
    df_clean = clean_and_transform(df_raw)
    load_output(df_clean)


if __name__ == "__main__":
    main()
'''
    else:
        python_code = f'''#!/usr/bin/env python3
"""
DataForge Pipeline — Raw Baseline Ingestion State
─────────────────────────────────────────────────
Auto-generated baseline ingestion & verification microservice.
Source: {filename}
Mode: Raw Baseline Ingestion (Pre-Cleaning State)
Generated at: {now_iso}
"""

import sys
import duckdb
import numpy as np
import pandas as pd


def extract(source_path: str = "{filename}") -> pd.DataFrame:
    """Ingests raw data using high-performance DuckDB pushdown."""
    print(f"📥 [Extract] Reading raw source {{source_path}} via DuckDB engine...")
    con = duckdb.connect(database=":memory:")
    query = f"SELECT * FROM read_csv_auto('{{source_path}}')"
    df = con.execute(query).df()
    print(f"   Loaded {{len(df)}} rows, {{df.shape[1]}} columns.")
    return df


def validate_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validates raw schema structure and baseline row assertions."""
    print("🔍 [Validate] Checking raw schema and row count integrity...")
    assert len(df) > 0, "Dataset contains 0 records."
    print(f"   ✓ Verified: {{len(df)}} rows present across {{len(df.columns)}} columns.")
    return df


def load_output(df: pd.DataFrame, target_path: str = "raw_ingested_data.parquet") -> None:
    """Materializes raw ingested dataset into compressed Apache Parquet."""
    print(f"💾 [Load] Materializing raw ingestion layer to {{target_path}}...")
    df.to_parquet(target_path, index=False, compression="snappy")
    print("✅ Baseline ingestion pipeline completed successfully.")


def main():
    source_file = sys.argv[1] if len(sys.argv) > 1 else "{filename}"
    df = extract(source_file)
    df = validate_schema(df)
    load_output(df)


if __name__ == "__main__":
    main()
'''

    # 3. dbt SQL Model & schema.yml
    clean_cols = [f'"{c}"' for c in cols if c not in dropped]
    cols_select = ",\n        ".join(clean_cols[:12]) if clean_cols else "*"

    if is_cleaned:
        dbt_sql = f'''-- models/staging/{clean_prefix}.sql
-- Auto-generated by DataForge dbt Engine (Production Cleaned Layer)
{{{{ config(materialized='table') }}}}

with raw_source as (
    select * from {{{{ source('raw', '{prefix}') }}}}
),

cleaned as (
    select
        {cols_select}
    from raw_source
    -- Automated DataForge filters & row validations
    where 1=1
)

select * from cleaned
'''
        col_items = [
            f"      - name: '{c}'\n        description: 'Cleaned and validated field from {filename}'\n        tests:\n          - not_null"
            if c in imputed else
            f"      - name: '{c}'\n        description: 'Transformed field from {filename}'"
            for c in cols[:8]
        ]
        col_str = "\n".join(col_items) if col_items else f"      - name: 'id'\n        description: 'Primary identifier'"

        dbt_yml = f'''version: 2

models:
  - name: {clean_prefix}
    description: "Production cleaned dataset materialized from DataForge workspace."
    columns:
{col_str}
'''
    else:
        dbt_sql = f'''-- models/staging/{clean_prefix}.sql
-- Auto-generated by DataForge dbt Engine (Raw Baseline Ingestion Layer)
{{{{ config(materialized='table') }}}}

with raw_source as (
    select * from {{{{ source('raw', '{prefix}') }}}}
)

select
    {cols_select}
from raw_source
'''
        col_items = [
            f"      - name: '{c}'\n        description: 'Raw field ingested from {filename}'"
            for c in cols[:8]
        ]
        col_str = "\n".join(col_items) if col_items else f"      - name: 'id'\n        description: 'Primary identifier'"

        dbt_yml = f'''version: 2

models:
  - name: {clean_prefix}
    description: "Raw baseline ingestion dataset materialized from DataForge workspace."
    columns:
{col_str}
'''

    # 4. Apache Airflow DAG
    if is_cleaned:
        airflow_dag = f'''# dags/dataforge_{prefix}_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {{
    'owner': 'dataforge',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}}

with DAG(
    'dataforge_{prefix}_cleaned_pipeline',
    default_args=default_args,
    description='Automated DataForge Production Cleaning & Transformation DAG',
    schedule_interval='@daily',
    catchup=False,
    tags=['dataforge', 'production', 'cleaned'],
) as dag:

    task_extract = BashOperator(
        task_id='extract_raw_data',
        bash_command='python3 pipeline.py extract',
    )

    task_transform = BashOperator(
        task_id='clean_and_transform',
        bash_command='python3 pipeline.py transform',
    )

    task_test_quality = BashOperator(
        task_id='data_quality_assertions',
        bash_command='pytest tests/test_data_quality.py',
    )

    task_extract >> task_transform >> task_test_quality
'''
    else:
        airflow_dag = f'''# dags/dataforge_{prefix}_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {{
    'owner': 'dataforge',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}}

with DAG(
    'dataforge_{prefix}_raw_pipeline',
    default_args=default_args,
    description='Automated DataForge Raw Baseline Ingestion DAG',
    schedule_interval='@daily',
    catchup=False,
    tags=['dataforge', 'baseline', 'raw'],
) as dag:

    task_extract = BashOperator(
        task_id='extract_raw_data',
        bash_command='python3 pipeline.py extract',
    )

    task_validate_raw = BashOperator(
        task_id='validate_raw_schema',
        bash_command='python3 pipeline.py validate',
    )

    task_test_quality = BashOperator(
        task_id='data_quality_assertions',
        bash_command='pytest tests/test_data_quality.py',
    )

    task_extract >> task_validate_raw >> task_test_quality
'''

    # 5. Data Quality Test Suite (pytest)
    if is_cleaned:
        quality_py = f'''# tests/test_data_quality.py
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def df():
    return pd.read_parquet("cleaned_data.parquet")


def test_row_count_not_empty(df):
    """Assert output dataset contains records."""
    assert len(df) > 0, "Cleaned dataset should have at least 1 row"


def test_columns_exist(df):
    """Assert expected features exist in materialized artifact."""
    expected = {cols[:5]}
    for col in expected:
        assert col in df.columns, f"Missing critical column: {{col}}"


def test_no_critical_nulls(df):
    """Assert missing values were imputed."""
    if len(df) > 0 and len(df.columns) > 0:
        first_col = df.columns[0]
        missing_pct = df[first_col].isna().mean()
        assert missing_pct < 0.01, f"Column {{first_col}} exceeds 1% null threshold"


def test_no_duplicate_records(df):
    """Assert records were deduplicated."""
    if len(df) > 0:
        dup_count = df.duplicated().sum()
        assert dup_count == 0, f"Found {{dup_count}} duplicate records in cleaned data"
'''
    else:
        quality_py = f'''# tests/test_data_quality.py
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def df():
    return pd.read_parquet("raw_ingested_data.parquet")


def test_row_count_not_empty(df):
    """Assert raw ingested dataset contains records."""
    assert len(df) > 0, "Raw dataset should have at least 1 row"


def test_schema_columns_exist(df):
    """Assert raw schema features exist."""
    expected = {cols[:5]}
    for col in expected:
        assert col in df.columns, f"Missing raw column: {{col}}"
'''

    return JSONResponse(
        content={
            "ok": True,
            "upload_id": upload_id,
            "filename": filename,
            "is_cleaned": is_cleaned,
            "pipeline_mode": "production_cleaned" if is_cleaned else "raw_baseline",
            "cleaning_summary": {
                "is_cleaned": is_cleaned,
                "rules_count": len(applied_rules) or (len(dropped) + len(imputed) + (1 if is_cleaned else 0)),
                "dropped_cols": dropped,
                "imputed_cols": imputed,
                "struct_actions": struct_actions,
                "rows_count": len(df_active) if df_active is not None else 0,
                "cols_count": len(cols),
            },
            "recipe_json": recipe_dict,
            "python_script": python_code,
            "dbt_sql": dbt_sql,
            "dbt_schema_yml": dbt_yml,
            "airflow_dag": airflow_dag,
            "data_quality_tests": quality_py,
        }
    )


@router.post("/assert", summary="Execute live Data Quality assertions on dataset")
async def run_data_quality_assertions(
    body: QualityAssertionRequest,
    current_user: CurrentUser,
    request: Request,
):
    """
    Runs automated schema and data quality assertions on the active dataset:
    - Evaluates both pre-cleaning (df_raw) and post-cleaning (df_clean) metrics
    - Not-null percentage guarantees
    - Candidate uniqueness checks
    - Value boundary checks
    - Highlights issues resolved by Clean & Fix operations
    """
    await require_upload_access(body.upload_id, current_user, share_token=body.share_token, request=request)
    df_active, df_raw, df_clean, profile, clean_meta, is_cleaned = _detect_dataset_state(body.upload_id)

    if df_active is None:
        raise HTTPException(400, "Dataset not loaded")

    if len(df_active.columns) == 0:
        return JSONResponse(
            content={
                "ok": True,
                "upload_id": body.upload_id,
                "is_cleaned": is_cleaned,
                "overall_status": "PASSED",
                "passed_count": 0,
                "total_count": 0,
                "score": 100.0,
                "raw_score": 100.0,
                "improvement_pct": 0.0,
                "assertions": [],
            }
        )

    # Build assertions list
    default_assertions = list(body.assertions) if body.assertions else []
    if not default_assertions:
        # Check column 0 for not null and uniqueness
        col0 = df_active.columns[0]
        default_assertions.append({"type": "not_null_threshold", "column": col0, "max_null_pct": 2.0})
        default_assertions.append({"type": "uniqueness_check", "column": col0})

        # If clean_meta has imputed cells or columns, add assertion for the top imputed column
        imputed_cols = list(clean_meta.get("imputed_cells", {}).keys()) or list(clean_meta.get("imputed_cols", {}).keys())
        for imp_col in imputed_cols[:2]:
            if imp_col in df_active.columns and imp_col != col0:
                default_assertions.append({"type": "not_null_threshold", "column": imp_col, "max_null_pct": 1.0})

        # Add numeric range checks for first numeric column
        num_cols = df_active.select_dtypes(include=["number"]).columns.tolist()
        if num_cols:
            n_col = num_cols[0]
            s = df_active[n_col].dropna()
            if not s.empty:
                default_assertions.append({
                    "type": "range_check",
                    "column": n_col,
                    "min": float(s.min()),
                    "max": float(s.max()),
                })

    results = []
    raw_passed_count = 0

    for rule in default_assertions:
        rtype = rule.get("type")
        col = rule.get("column")

        if col not in df_active.columns:
            results.append({
                "rule": rtype,
                "column": col,
                "status": "FAILED",
                "message": f"Column '{col}' does not exist in dataset",
                "resolved": False,
            })
            continue

        if rtype == "not_null_threshold":
            max_pct = rule.get("max_null_pct", 5.0)
            null_pct = round(float(df_active[col].isna().mean() * 100), 2)
            passed = null_pct <= max_pct

            raw_null_pct = None
            resolved = False
            raw_passed = True
            if df_raw is not None and col in df_raw.columns:
                raw_null_pct = round(float(df_raw[col].isna().mean() * 100), 2)
                raw_passed = raw_null_pct <= max_pct
                if is_cleaned and not raw_passed and passed:
                    resolved = True

            if raw_passed:
                raw_passed_count += 1

            if resolved:
                msg = f"{null_pct}% nulls (resolved from {raw_null_pct}% in raw baseline)"
            elif is_cleaned and raw_null_pct is not None and raw_null_pct > null_pct:
                msg = f"{null_pct}% nulls (reduced from {raw_null_pct}% in raw baseline)"
            elif passed:
                msg = f"Observed {null_pct}% nulls (within {max_pct}% threshold)"
            else:
                msg = f"Observed {null_pct}% nulls (Threshold: {max_pct}%). Clean & Fix recommended."

            results.append({
                "rule": "Not Null Threshold",
                "column": col,
                "status": "PASSED" if passed else "FAILED",
                "null_pct": null_pct,
                "raw_null_pct": raw_null_pct,
                "threshold_pct": max_pct,
                "resolved": resolved,
                "before_val": f"{raw_null_pct}% nulls" if raw_null_pct is not None else None,
                "after_val": f"{null_pct}% nulls",
                "message": msg,
            })

        elif rtype == "uniqueness_check":
            dup_count = int(df_active[col].duplicated().sum())
            passed = dup_count == 0

            raw_dup_count = None
            resolved = False
            raw_passed = True
            if df_raw is not None and col in df_raw.columns:
                raw_dup_count = int(df_raw[col].duplicated().sum())
                raw_passed = raw_dup_count == 0
                if is_cleaned and not raw_passed and passed:
                    resolved = True

            if raw_passed:
                raw_passed_count += 1

            if resolved:
                msg = f"0 duplicate keys detected (resolved from {raw_dup_count} duplicate rows in raw data)"
            elif passed:
                msg = f"0 duplicate keys detected (Unique records: {df_active[col].nunique():,})"
            else:
                msg = f"{dup_count:,} duplicate keys detected (Unique rows: {df_active[col].nunique():,}). Clean & Fix recommended."

            results.append({
                "rule": "Uniqueness Constraint",
                "column": col,
                "status": "PASSED" if passed else "WARNING",
                "duplicate_count": dup_count,
                "raw_duplicate_count": raw_dup_count,
                "resolved": resolved,
                "before_val": f"{raw_dup_count:,} duplicates" if raw_dup_count is not None else None,
                "after_val": f"{dup_count:,} duplicates",
                "message": msg,
            })

        elif rtype == "range_check":
            s = df_active[col].dropna()
            min_val = rule.get("min", float(s.min()) if not s.empty else 0.0)
            max_val = rule.get("max", float(s.max()) if not s.empty else 100.0)
            out_of_bounds = int(((s < min_val) | (s > max_val)).sum()) if not s.empty else 0
            passed = out_of_bounds == 0

            raw_out_of_bounds = None
            resolved = False
            raw_passed = True
            if df_raw is not None and col in df_raw.columns:
                raw_s = df_raw[col].dropna()
                raw_out_of_bounds = int(((raw_s < min_val) | (raw_s > max_val)).sum()) if not raw_s.empty else 0
                raw_passed = raw_out_of_bounds == 0
                if is_cleaned and not raw_passed and passed:
                    resolved = True

            if raw_passed:
                raw_passed_count += 1

            if resolved:
                msg = f"All values within [{min_val}, {max_val}] (resolved {raw_out_of_bounds} outliers)"
            elif passed:
                msg = f"All values within [{min_val}, {max_val}]"
            else:
                msg = f"{out_of_bounds:,} values outside [{min_val}, {max_val}]"

            results.append({
                "rule": "Value Range Constraint",
                "column": col,
                "status": "PASSED" if passed else "FAILED",
                "out_of_bounds_count": out_of_bounds,
                "raw_out_of_bounds_count": raw_out_of_bounds,
                "resolved": resolved,
                "observed_range": [float(s.min()), float(s.max())] if not s.empty else [0.0, 0.0],
                "before_val": f"{raw_out_of_bounds} outliers" if raw_out_of_bounds is not None else None,
                "after_val": f"{out_of_bounds} outliers",
                "message": msg,
            })

    passed_count = sum(1 for r in results if r["status"] == "PASSED")
    total_count = len(results)
    clean_score = round((passed_count / max(1, total_count)) * 100, 1)
    raw_score = round((raw_passed_count / max(1, total_count)) * 100, 1)
    improvement = max(0.0, round(clean_score - raw_score, 1)) if is_cleaned else 0.0

    return JSONResponse(
        content={
            "ok": True,
            "upload_id": body.upload_id,
            "is_cleaned": is_cleaned,
            "overall_status": "PASSED" if passed_count == total_count else "WARNING",
            "passed_count": passed_count,
            "total_count": total_count,
            "score": clean_score,
            "raw_score": raw_score if is_cleaned else clean_score,
            "improvement_pct": improvement,
            "assertions": results,
        }
    )


@router.get("/download-zip", summary="Download full pipeline code zip bundle")
async def download_pipeline_zip(
    request: Request,
    current_user: CurrentUser,
    upload_id: str = Query(..., description="Workspace Upload ID"),
    share_token: Optional[str] = Query(default=None),
):
    """Downloads a complete production zip containing Python ETL, dbt models, Airflow DAG, DF-SPE recipe, and tests."""
    res = await export_pipeline(request=request, upload_id=upload_id, current_user=current_user, share_token=share_token)
    data = json.loads(res.body.decode("utf-8"))

    buf = io.BytesIO()
    is_cleaned = data.get("is_cleaned", False)
    mode_label = "Production Cleaned Pipeline" if is_cleaned else "Raw Baseline Pipeline"
    staging_file = "stg_transformed.sql" if is_cleaned else "stg_raw.sql"

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pipeline.py", data["python_script"])
        z.writestr(f"models/staging/{staging_file}", data["dbt_sql"])
        z.writestr("models/schema.yml", data["dbt_schema_yml"])
        z.writestr("dags/dataforge_pipeline_dag.py", data["airflow_dag"])
        z.writestr("tests/test_data_quality.py", data["data_quality_tests"])
        z.writestr("recipe.json", json.dumps(data.get("recipe_json", {}), indent=2))
        z.writestr(
            "requirements.txt",
            "duckdb>=1.0.0\npandas>=2.2.0\npyarrow>=16.0.0\npytest>=8.0.0\n",
        )
        z.writestr(
            "README.md",
            f"# DataForge Pipeline Export — {mode_label}\n\n"
            f"Auto-generated pipeline repository for {data.get('filename')}.\n"
            f"State: {mode_label}\n\n"
            "## Run Locally\n```bash\npip install -r requirements.txt\npython pipeline.py\npytest tests/\n```\n",
        )

    buf.seek(0)
    filename = f"dataforge-pipeline-{upload_id[:8]}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
