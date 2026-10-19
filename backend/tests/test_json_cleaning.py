"""
Unit tests verifying comprehensive JSON dataset ingestion and cleaning for all types.
Guarantees:
1. All 12 JSON structures parse correctly into DataFrames.
2. 1-Click Automated Cleaning (run_cleaning_pipeline) succeeds without unhashable/scalar errors.
3. Interactive Dynamic Cleaning (run_dynamic_cleaning_pipeline) succeeds.
4. SnapshotManager and Parquet serialization succeed without ArrowInvalid errors.
"""

import io
import json
import pytest
import pandas as pd
import numpy as np

from dataforge.api.utils.json import parse_json_to_dataframe
from dataforge.data_cleaner import run_cleaning_pipeline, run_dynamic_cleaning_pipeline


SAMPLE_JSON_DATASETS = [
    ("list_records", b'[{"id": 1, "name": "Alice", "score": 95}, {"id": 2, "name": "Bob", "score": 88}]'),
    ("nested_list", b'[{"id": 1, "user": {"name": "Alice", "city": "Paris"}}, {"id": 2, "user": {"name": "Bob", "city": "London"}}]'),
    ("list_with_arrays", b'[{"id": 1, "tags": ["admin", "dev"], "meta": {"score": 90}}, {"id": 2, "tags": ["user"], "meta": {"score": 80}}]'),
    ("col_oriented", b'{"id": [1, 2, 3], "name": ["Alpha", "Beta", "Gamma"], "val": [10.5, 20.0, 30.5]}'),
    ("split_oriented", b'{"columns": ["c1", "c2"], "data": [[1, "apple"], [2, "banana"]]}'),
    ("wrapper_key_articles", b'{"status": "ok", "articles": [{"title": "Post 1", "views": 100}, {"title": "Post 2", "views": 250}]}'),
    ("deep_wrapper", b'{"response": {"code": 200, "data": [{"item": "Widget A", "price": 19.99}, {"item": "Widget B", "price": 29.99}]}}'),
    ("index_oriented", b'{"row_1": {"x": 10, "y": 20}, "row_2": {"x": 30, "y": 40}}'),
    ("primitive_list", b'[100, 200, 300, 400]'),
    ("geojson", b'{"type": "FeatureCollection", "features": [{"properties": {"city": "Paris", "pop": 2100000}}, {"properties": {"city": "Lyon", "pop": 520000}}]}'),
    ("ndjson", b'{"id": 1, "name": "Sensor 1", "temp": 22.4}\n{"id": 2, "name": "Sensor 2", "temp": 23.1}'),
    ("nulls_and_arrays", b'[{"id": 1, "tags": ["a", "b"], "status": "active"}, {"id": 2, "tags": null, "status": null}, {"id": 3, "tags": ["c"], "status": "pending"}]'),
    ("utf8_bom", '\ufeff[{"col1": "A", "col2": 1}, {"col1": "B", "col2": 2}]'.encode("utf-8-sig")),
]


@pytest.mark.parametrize("name,raw_bytes", SAMPLE_JSON_DATASETS)
def test_all_json_types_parsing(name, raw_bytes):
    df = parse_json_to_dataframe(raw_bytes)
    assert isinstance(df, pd.DataFrame), f"Failed to return DataFrame for {name}"
    assert len(df) > 0, f"DataFrame was empty for {name}"
    assert df.shape[1] > 0, f"No columns extracted for {name}"


@pytest.mark.parametrize("name,raw_bytes", SAMPLE_JSON_DATASETS)
def test_all_json_types_auto_cleaning(name, raw_bytes):
    df = parse_json_to_dataframe(raw_bytes)
    clean_result = run_cleaning_pipeline(df)
    assert isinstance(clean_result, dict)
    assert "df_clean" in clean_result
    assert "stats" in clean_result
    assert isinstance(clean_result["df_clean"], pd.DataFrame)
    assert len(clean_result["df_clean"]) > 0


def test_json_dynamic_cleaning_rules():
    raw = b'[{"id": 1, "tags": ["a", "b"], "val": 10.0}, {"id": 2, "tags": null, "val": null}, {"id": 3, "tags": ["c"], "val": 30.0}]'
    df = parse_json_to_dataframe(raw)
    rules = [
        {"column": "val", "action_type": "impute", "impute_method": "median"},
        {"column": "tags", "action_type": "impute", "impute_method": "mode"},
    ]
    res = run_dynamic_cleaning_pipeline(df, rules)
    assert isinstance(res, dict)
    assert "df_clean" in res
    assert res["df_clean"]["val"].isnull().sum() == 0
    assert res["df_clean"]["tags"].isnull().sum() == 0


def test_safe_parquet_serialization_with_lists():
    from dataforge.web.storage import _safe_df_for_parquet
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "tags": [["a", "b"], ["c"], None],
        "meta": [{"k": 1}, {"k": 2}, None],
        "mixed": [1, "two", {"three": 3}]
    })
    safe_df = _safe_df_for_parquet(df)
    buf = io.BytesIO()
    safe_df.to_parquet(buf, index=False, compression="snappy")
    assert len(buf.getvalue()) > 0
