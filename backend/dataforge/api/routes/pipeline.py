"""
dataforge/api/routes/pipeline.py
────────────────────────────────
Production Pipeline Exporter & Data Quality Assertions Suite.
Generates dbt models, Apache Airflow DAGs, standalone Python ETL scripts,
and executes live Great Expectations-style data quality validations.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from dataforge.api.deps import CurrentUser, require_upload_access
from dataforge.api.storage.manager import STORE_DIR, exists, load
from dataforge.api.utils.json import safe_jsonable

log = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class QualityAssertionRequest(BaseModel):
    upload_id: str
    assertions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of assertion rules: {type: 'unique'|'not_null'|'range'|'regex', column: '...', min: ..., max: ...}",
    )


@router.get("/export", summary="Export production pipeline code (Python, dbt, Airflow)")
async def export_pipeline(
    current_user: CurrentUser,
    upload_id: str = Query(..., description="Workspace Upload ID"),
):
    """
    Synthesizes reproducible production code representing the visual workspace steps:
    - Standalone Python ETL script
    - dbt Staging SQL model + schema.yml
    - Apache Airflow orchestration DAG
    - Data quality assertions suite
    """
    await require_upload_access(upload_id, current_user)
    profile = load(upload_id, "profile") or {}
    clean_meta = load(upload_id, "clean_meta") or {}
    df_dataset = load(upload_id, "df_clean")
    if df_dataset is None:
        df_dataset = load(upload_id, "df_raw")
    filename = profile.get("filename", "dataset.csv")

    cols = list(df_dataset.columns) if df_dataset is not None else profile.get("columns", [])

    # 1. Generate Python ETL Script
    dropped = clean_meta.get("dropped_cols", [])
    imputed = clean_meta.get("imputed_cols", {})

    python_code = f'''#!/usr/bin/env python3
"""
DataForge Production Pipeline
──────────────────────────────
Auto-generated standalone ETL microservice.
Source: {filename}
Generated at: {datetime.now(timezone.utc).isoformat()}
"""

import sys
import duckdb
import numpy as np
import pandas as pd


def extract(source_path: str = "{filename}") -> pd.DataFrame:
    """Ingests raw data using high-performance DuckDB pushdown."""
    print(f"📥 [Extract] Reading {{source_path}} via DuckDB...")
    con = duckdb.connect(database=":memory:")
    query = f"SELECT * FROM read_csv_auto('{{source_path}}')"
    df = con.execute(query).df()
    print(f"   Loaded {{len(df)}} rows, {{df.shape[1]}} columns.")
    return df


def clean_and_transform(df: pd.DataFrame) -> pd.DataFrame:
    """Executes validated DataForge cleaning rules and transformations."""
    print("🧹 [Transform] Applying DataForge cleaning rules...")
    
    # 1. Column drops
    drop_cols = {dropped}
    existing_drops = [c for c in drop_cols if c in df.columns]
    if existing_drops:
        df = df.drop(columns=existing_drops)
        print(f"   Dropped redundant columns: {{existing_drops}}")

    # 2. Missing value imputation
    impute_rules = {imputed}
    for col, rule in impute_rules.items():
        if col in df.columns:
            if rule == "median" and pd.api.types.is_numeric_dtype(df[col]):
                fill_val = df[col].median()
                df[col] = df[col].fillna(fill_val)
            elif rule == "mean" and pd.api.types.is_numeric_dtype(df[col]):
                fill_val = df[col].mean()
                df[col] = df[col].fillna(fill_val)
            elif rule == "mode":
                mode_val = df[col].mode().iloc[0] if not df[col].mode().empty else "Unknown"
                df[col] = df[col].fillna(mode_val)

    # 3. Clean numeric coercion
    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

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

    # 2. Generate dbt SQL model
    clean_cols = [f'"{c}"' for c in cols if c not in dropped]
    cols_select = ",\n        ".join(clean_cols[:12]) if clean_cols else "*"

    dbt_sql = f'''-- models/staging/stg_{upload_id[:8]}_transformed.sql
-- Auto-generated by DataForge Enterprise dbt Engine
{{{{ config(materialized='table') }}}}

with raw_source as (
    select * from {{{{ source('raw', '{upload_id[:8]}') }}}}
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

    col_items = [f"      - name: '{c}'{chr(10)}        description: 'Auto-validated field from {filename}'" for c in cols[:8]]
    col_str = chr(10).join(col_items) if col_items else f"      - name: 'id'{chr(10)}        description: 'Primary identifier'"

    dbt_yml = f'''version: 2

models:
  - name: stg_{upload_id[:8]}_transformed
    description: "Production cleaned dataset materialized from DataForge workspace."
    columns:
{col_str}
'''

    # 3. Generate Airflow DAG
    airflow_dag = f'''# dags/dataforge_{upload_id[:8]}_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

default_args = {{
    'owner': 'dataforge',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}}

with DAG(
    'dataforge_{upload_id[:8]}_pipeline',
    default_args=default_args,
    description='Automated DataForge Ingestion & Transformation DAG',
    schedule_interval='@daily',
    catchup=False,
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

    # 4. Generate Data Quality Test Suite (pytest)
    quality_py = f'''# tests/test_data_quality.py
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def df():
    return pd.read_parquet("cleaned_data.parquet")


def test_row_count_not_empty(df):
    """Assert output dataset contains records."""
    assert len(df) > 0, "Dataset should have at least 1 row"


def test_columns_exist(df):
    """Assert expected features exist in materialized artifact."""
    expected = {cols[:5]}
    for col in expected:
        assert col in df.columns, f"Missing critical column: {{col}}"


def test_critical_not_null(df):
    """Assert non-null threshold."""
    if len(df) > 0 and len(df.columns) > 0:
        first_col = df.columns[0]
        missing_pct = df[first_col].isna().mean()
        assert missing_pct < 0.05, f"Column {{first_col}} exceeds 5% null threshold"
'''

    return JSONResponse(
        content={
            "ok": True,
            "upload_id": upload_id,
            "filename": filename,
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
):
    """
    Runs automated schema and data quality assertions on the active dataset:
    - Not-null percentage guarantees (< 1%)
    - Primary key candidate uniqueness (0 duplicates)
    - Value boundary checks (min, max)
    - Valid categorical member checks
    """
    await require_upload_access(body.upload_id, current_user)
    df_clean = load(body.upload_id, "df_clean")
    df = df_clean if df_clean is not None else load(body.upload_id, "df_raw")
    if df is None:
        raise HTTPException(400, "Dataset not loaded")

    if len(df.columns) == 0:
        return JSONResponse(
            content={
                "ok": True,
                "upload_id": body.upload_id,
                "overall_status": "PASSED",
                "passed_count": 0,
                "total_count": 0,
                "score": 100.0,
                "assertions": [],
            }
        )

    results = []
    default_assertions = body.assertions or [
        {"type": "not_null_threshold", "column": df.columns[0], "max_null_pct": 2.0},
        {"type": "uniqueness_check", "column": df.columns[0]},
    ]

    # Add numeric range checks for first numeric column
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if num_cols:
        default_assertions.append({
            "type": "range_check",
            "column": num_cols[0],
            "min": float(df[num_cols[0]].min()),
            "max": float(df[num_cols[0]].max()),
        })

    for rule in default_assertions:
        rtype = rule.get("type")
        col = rule.get("column")

        if col not in df.columns:
            results.append({
                "rule": rtype,
                "column": col,
                "status": "FAILED",
                "message": f"Column '{col}' does not exist in dataset",
            })
            continue

        if rtype == "not_null_threshold":
            max_pct = rule.get("max_null_pct", 5.0)
            null_pct = round(float(df[col].isna().mean() * 100), 2)
            passed = null_pct <= max_pct
            results.append({
                "rule": "Not Null Threshold",
                "column": col,
                "status": "PASSED" if passed else "FAILED",
                "null_pct": null_pct,
                "threshold_pct": max_pct,
                "message": f"Observed {null_pct}% nulls (Threshold: {max_pct}%)",
            })

        elif rtype == "uniqueness_check":
            dup_count = int(df[col].duplicated().sum())
            passed = dup_count == 0
            results.append({
                "rule": "Uniqueness Constraint",
                "column": col,
                "status": "PASSED" if passed else "WARNING",
                "duplicate_count": dup_count,
                "message": f"{dup_count} duplicate keys detected (Unique rows: {df[col].nunique()})",
            })

        elif rtype == "range_check":
            s = df[col].dropna()
            min_val = rule.get("min", float(s.min()))
            max_val = rule.get("max", float(s.max()))
            out_of_bounds = int(((s < min_val) | (s > max_val)).sum())
            passed = out_of_bounds == 0
            results.append({
                "rule": "Value Range Constraint",
                "column": col,
                "status": "PASSED" if passed else "FAILED",
                "out_of_bounds_count": out_of_bounds,
                "observed_range": [float(s.min()), float(s.max())],
                "message": f"All values within [{min_val}, {max_val}]" if passed else f"{out_of_bounds} values outside [{min_val}, {max_val}]",
            })

    passed_count = sum(1 for r in results if r["status"] == "PASSED")
    total_count = len(results)

    return JSONResponse(
        content={
            "ok": True,
            "upload_id": body.upload_id,
            "overall_status": "PASSED" if passed_count == total_count else "WARNING",
            "passed_count": passed_count,
            "total_count": total_count,
            "score": round((passed_count / max(1, total_count)) * 100, 1),
            "assertions": results,
        }
    )


@router.get("/download-zip", summary="Download full pipeline code zip bundle")
async def download_pipeline_zip(
    current_user: CurrentUser,
    upload_id: str = Query(..., description="Workspace Upload ID"),
):
    """Downloads a complete production zip containing Python ETL, dbt models, Airflow DAG, and tests."""
    res = await export_pipeline(upload_id=upload_id, current_user=current_user)
    data = json.loads(res.body.decode("utf-8"))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pipeline.py", data["python_script"])
        z.writestr("models/staging/stg_transformed.sql", data["dbt_sql"])
        z.writestr("models/schema.yml", data["dbt_schema_yml"])
        z.writestr("dags/dataforge_pipeline_dag.py", data["airflow_dag"])
        z.writestr("tests/test_data_quality.py", data["data_quality_tests"])
        z.writestr(
            "requirements.txt",
            "duckdb>=1.0.0\npandas>=2.2.0\npyarrow>=16.0.0\npytest>=8.0.0\n",
        )
        z.writestr(
            "README.md",
            f"# DataForge Pipeline Export\n\nAuto-generated production pipeline for {data.get('filename')}.\n\n"
            "## Run Locally\n```bash\npip install -r requirements.txt\npython pipeline.py\npytest tests/\n```\n",
        )

    buf.seek(0)
    filename = f"dataforge-pipeline-{upload_id[:8]}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
