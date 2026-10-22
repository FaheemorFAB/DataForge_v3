import pytest
import pandas as pd
import numpy as np
from dataforge.join_engine import DuckDBJoinEngine, _sanitize_table_name, _format_filter_sql
from dataforge.api.storage.manager import save, load, exists

def test_sanitize_table_name():
    assert _sanitize_table_name("my table! 123") == "my_table__123"
    assert _sanitize_table_name("1st_table") == "t_1st_table"
    assert _sanitize_table_name("") == "primary_table"
    assert _sanitize_table_name(None) == "primary_table"

def test_infer_relationships():
    users_df = pd.DataFrame({
        "user_id": [1, 2, 3, 4],
        "name": ["Alice", "Bob", "Charlie", "David"]
    })
    orders_df = pd.DataFrame({
        "order_id": [101, 102, 103],
        "user_id": [1, 2, 2],
        "amount": [99.5, 45.0, 150.0]
    })
    tables = {
        "users": users_df,
        "orders": orders_df
    }
    inferred = DuckDBJoinEngine.infer_relationships(tables)
    assert len(inferred) >= 1
    rel = inferred[0]
    assert (rel["left_table"] == "orders" and rel["right_table"] == "users") or (rel["left_table"] == "users" and rel["right_table"] == "orders")
    assert "user_id" in (rel["left_column"], rel["right_column"])
    assert rel["confidence"] > 0.8

def test_build_sql_and_preview(tmp_path, monkeypatch):
    upload_id = "test_join_preview_123"
    customers_df = pd.DataFrame({
        "cust_id": ["C1", "C2", "C3"],
        "name": ["Alice", "Bob", "Charlie"]
    })
    orders_df = pd.DataFrame({
        "order_id": ["O1", "O2", "O3", "O4"],
        "cust_id": ["C1", "C2", "C2", "C4"],
        "total": [100, 200, 300, 400]
    })

    save(upload_id, "df_raw", customers_df)
    save(upload_id, "profile", {"filename": "customers.csv", "columns": list(customers_df.columns)})
    DuckDBJoinEngine.save_workspace_table(upload_id, "orders", orders_df)

    # 1. Preview zero joins (base table only)
    preview_base = DuckDBJoinEngine.preview_join(
        upload_id=upload_id,
        base_table="customers",
        joins=[],
        limit=10,
    )
    assert preview_base["ok"] is True
    assert preview_base["preview_count"] == 3
    assert "customers" in preview_base["sql"]

    # 2. Preview with LEFT join
    joins = [{
        "table": "orders",
        "join_type": "LEFT",
        "conditions": [{"left_col": "cust_id", "right_col": "cust_id", "left_table": "customers"}]
    }]
    preview_join = DuckDBJoinEngine.preview_join(
        upload_id=upload_id,
        base_table="customers",
        joins=joins,
        limit=10,
    )
    assert preview_join["ok"] is True
    assert preview_join["preview_count"] == 4
    assert "LEFT JOIN" in preview_join["sql"]

def test_materialize_join_updates_clean_profile():
    import shutil
    from dataforge.api.storage.manager import STORE_DIR
    upload_id = "test_mat_sync_456"
    shutil.rmtree(STORE_DIR / upload_id, ignore_errors=True)

    dept_df = pd.DataFrame({
        "dept_id": [1, 2],
        "dept_name": ["Engineering", "Product"]
    })
    emp_df = pd.DataFrame({
        "emp_id": [10, 20, 30],
        "dept_id": [1, 1, 2],
        "salary": [100000, 110000, 95000]
    })

    save(upload_id, "df_raw", dept_df)
    save(upload_id, "profile", {"filename": "departments.csv", "columns": ["dept_id", "dept_name"]})
    DuckDBJoinEngine.save_workspace_table(upload_id, "employees", emp_df)

    res = DuckDBJoinEngine.materialize_join(
        upload_id=upload_id,
        base_table="departments",
        joins=[{
            "table": "employees",
            "join_type": "INNER",
            "conditions": [{"left_col": "dept_id", "right_col": "dept_id", "left_table": "departments"}]
        }],
        output_dataset_name="dept_emp_joined.csv"
    )

    assert res["ok"] is True
    assert res["rows"] == 3

    # Check that df_clean, profile, and clean_profile are properly saved and in sync
    df_clean = load(upload_id, "df_clean")
    assert df_clean is not None
    assert len(df_clean) == 3

    clean_profile = load(upload_id, "clean_profile")
    profile = load(upload_id, "profile")
    assert clean_profile is not None
    assert profile is not None
    assert clean_profile["filename"] == "dept_emp_joined.csv"
    assert clean_profile["rows"] == 3
    assert profile["filename"] == "dept_emp_joined.csv"

def test_custom_sql_preview_and_materialize():
    import shutil
    from dataforge.api.storage.manager import STORE_DIR
    upload_id = "test_custom_sql_789"
    shutil.rmtree(STORE_DIR / upload_id, ignore_errors=True)

    df = pd.DataFrame({
        "category": ["A", "A", "B", "B", "C"],
        "val": [10, 20, 30, 40, 50]
    })
    save(upload_id, "df_raw", df)
    save(upload_id, "profile", {"filename": "items.csv", "columns": ["category", "val"]})

    sql = "SELECT category, SUM(val) AS total_val FROM items GROUP BY category ORDER BY total_val DESC"
    preview = DuckDBJoinEngine.execute_custom_sql(upload_id, sql)
    assert preview["ok"] is True
    assert len(preview["rows"]) == 3
    assert preview["rows"][0]["category"] == "B"
    assert preview["rows"][0]["total_val"] == 70

    mat = DuckDBJoinEngine.materialize_custom_sql(upload_id, sql, "aggregated.csv")
    assert mat["ok"] is True
    clean_p = load(upload_id, "clean_profile")
    assert clean_p is not None
    assert clean_p["filename"] == "aggregated.csv"
    assert clean_p["rows"] == 3

def test_load_relational_preset():
    upload_id = "test_preset_012"
    res = DuckDBJoinEngine.load_relational_preset(upload_id, "ecommerce")
    assert res["ok"] is True
    assert "customers" in res["created_tables"]
    assert "orders" in res["created_tables"]

    # Verify orders was saved as primary with clean_profile and profile
    df_raw = load(upload_id, "df_raw")
    df_clean = load(upload_id, "df_clean")
    profile = load(upload_id, "profile")
    clean_profile = load(upload_id, "clean_profile")
    assert df_raw is not None
    assert df_clean is not None
    assert profile is not None
    assert clean_profile is not None
    assert len(df_raw) == 1200
    assert len(df_clean) == 1200
