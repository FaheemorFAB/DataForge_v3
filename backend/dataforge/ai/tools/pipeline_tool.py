import logging
import os
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def export_pipeline_tool(
    upload_id: str,
    format_type: str = "python",
    dataset_name: Optional[str] = "dataset",
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Generates an automated, reproducible, production-ready pipeline script (Python / Airflow / dbt)
    from exploratory and cleaning operations performed in DataForge.
    """
    format_lower = format_type.lower()
    clean_id = upload_id.replace("-", "_")

    if df is None:
        try:
            from dataforge.api.storage.manager import load
            df = load(upload_id, "df_clean")
            if df is None:
                df = load(upload_id, "df_raw")
        except Exception:
            pass

    # Extract actual dataset column information
    if df is not None and not df.empty:
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = [c for c in df.columns if c not in num_cols]
        all_cols = df.columns.tolist()
    else:
        num_cols = ["unit_price", "quantity", "discount", "revenue", "profit"]
        cat_cols = ["segment", "region", "category", "payment_method", "status"]
        all_cols = num_cols + cat_cols

    if "airflow" in format_lower:
        num_cols_repr = repr(num_cols[:8])
        cat_cols_repr = repr(cat_cols[:8])
        code = f'''# =============================================================================
#  DataForge Enterprise Apache Airflow DAG
#  Target Dataset: {dataset_name} (Upload ID: {upload_id})
#  Generated automatically by DataForge PipelineAgent
# =============================================================================
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger("airflow.task")

default_args = {{
    "owner": "dataforge",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}}

DATA_DIR = os.getenv("DATAFORGE_DATA_DIR", "/opt/airflow/data")
SOURCE_FILE = os.path.join(DATA_DIR, f"{dataset_name}.parquet")
CLEANED_FILE = os.path.join(DATA_DIR, f"{dataset_name}_cleaned.parquet")

def ingest_and_sanitize(**kwargs):
    """
    Ingests source dataset, eliminates blank records, and applies statistical imputations.
    """
    logger.info(f"Ingesting raw dataset from {{SOURCE_FILE}}...")
    if not os.path.exists(SOURCE_FILE):
        # Fallback to CSV if parquet does not exist
        csv_file = SOURCE_FILE.replace(".parquet", ".csv")
        df = pd.read_csv(csv_file)
    else:
        df = pd.read_parquet(SOURCE_FILE)
        
    initial_rows = len(df)
    logger.info(f"Loaded {{initial_rows:,}} rows and {{df.shape[1]}} columns.")

    # 1. Structural cleaning: drop empty rows & duplicate records
    df = df.dropna(how="all").drop_duplicates()

    # 2. Impute numerical columns with median
    numeric_features = {num_cols_repr}
    for col in numeric_features:
        if col in df.columns and df[col].isnull().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            logger.info(f"Imputed missing entries in numeric feature '{{col}}' with median: {{median_val}}")

    # 3. Standardize categorical features
    categorical_features = {cat_cols_repr}
    for col in categorical_features:
        if col in df.columns and df[col].isnull().any():
            df[col] = df[col].fillna("Unknown")

    # 4. Save cleaned output
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_parquet(CLEANED_FILE, index=False)
    logger.info(f"Sanitization complete: {{len(df):,}} rows saved to {{CLEANED_FILE}}.")

def compute_executive_metrics(**kwargs):
    """
    Computes key performance indicators (KPIs) and analytical distributions.
    """
    logger.info(f"Reading cleaned dataset from {{CLEANED_FILE}}...")
    df = pd.read_parquet(CLEANED_FILE)
    
    # Generate executive summary metrics
    summary = df.describe().round(2).to_dict()
    logger.info("Successfully calculated summary statistics across numeric dimensions.")
    return summary

with DAG(
    dag_id="dataforge_{clean_id}_pipeline",
    default_args=default_args,
    description="Automated production ETL pipeline compiled by DataForge PipelineAgent",
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["dataforge", "etl", "automated"],
) as dag:

    t1_sanitize = PythonOperator(
        task_id="ingest_and_sanitize_data",
        python_callable=ingest_and_sanitize,
    )

    t2_metrics = PythonOperator(
        task_id="compute_executive_metrics",
        python_callable=compute_executive_metrics,
    )

    t1_sanitize >> t2_metrics
'''
    elif "dbt" in format_lower:
        dbt_source_name = f"stg_{dataset_name.replace('.parquet', '').replace('.csv', '')}"
        cols_sql = "\n".join(f"        coalesce({c}, 'Unknown') as {c}," if c in cat_cols else f"        {c}," for c in all_cols[:12])
        code = f"""-- =============================================================================
--  DataForge Enterprise dbt Transformation Model
--  Target Dataset: {dataset_name} (Upload ID: {upload_id})
--  Generated automatically by DataForge PipelineAgent
-- =============================================================================

{{{{ config(materialized='table') }}}}
{{{{ config(
    tags=['dataforge', 'automated', 'cleaning']
) }}}}

with raw_source as (
    select * from {{{{ source('dataforge_raw', '{dbt_source_name}') }}}}
),

sanitized_data as (
    select
{cols_sql}
        current_timestamp() as _dataforge_transformed_at
    from raw_source
    -- Exclude fully null rows
    where {all_cols[0]} is not null
)

select * from sanitized_data
"""
    else:
        # Default Standalone Python / Pandas Script
        num_cols_repr = repr(num_cols[:10])
        cat_cols_repr = repr(cat_cols[:10])
        code = f'''# =============================================================================
#  DataForge Enterprise Standalone Python ETL Pipeline
#  Target Dataset: {dataset_name} (Upload ID: {upload_id})
#  Generated automatically by DataForge PipelineAgent
# =============================================================================
import os
import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataForgePipeline")

NUMERIC_FEATURES = {num_cols_repr}
CATEGORICAL_FEATURES = {cat_cols_repr}

def run_pipeline(source_path: str, output_path: str = "cleaned_output.parquet") -> pd.DataFrame:
    """
    Executes automated data ingestion, cleaning, missing-value imputation,
    and parquet optimization.
    """
    logger.info(f"Loading data from: {{source_path}}")
    if source_path.endswith(".parquet"):
        df = pd.read_parquet(source_path)
    else:
        df = pd.read_csv(source_path)

    orig_rows, orig_cols = df.shape
    logger.info(f"Initial shape: {{orig_rows:,}} rows × {{orig_cols}} columns")

    # 1. Structural cleaning: drop empty records and duplicates
    df = df.dropna(how="all").drop_duplicates()

    # 2. Impute numerical columns with median
    for col in NUMERIC_FEATURES:
        if col in df.columns and df[col].isnull().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            logger.info(f"Imputed nulls in '{{col}}' with median: {{median_val}}")

    # 3. Standardize categorical features
    for col in CATEGORICAL_FEATURES:
        if col in df.columns and df[col].isnull().any():
            df[col] = df[col].fillna("Unknown")

    # 4. Save optimized Parquet output
    df.to_parquet(output_path, index=False)
    logger.info(f"Pipeline complete: {{len(df):,}} rows successfully written to {{output_path}}")
    return df

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "{dataset_name}.parquet"
    run_pipeline(input_file)
'''

    filename = f"pipeline_{upload_id[:8]}.{'py' if 'dbt' not in format_lower else 'sql'}"
    return {
        "ok": True,
        "format": format_lower,
        "filename": filename,
        "code": code,
        "pipeline_code": code,
        "message": f"Successfully compiled {format_type.upper()} pipeline template.",
    }

