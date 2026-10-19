"""
dataforge/api/utils/json.py
────────────────────────────
Safe JSON serialization — handles numpy types, NaN, Inf, Timestamps.
Used as the default JSONResponse encoder throughout the app.
"""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
import pandas as pd


def _fix(obj: Any) -> Any:
    """Recursively make an object JSON-safe."""
    if isinstance(obj, (np.floating, float)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [_fix(x) for x in obj.tolist()]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat() if not pd.isna(obj) else None
    if isinstance(obj, dict):
        return {str(k): _fix(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_fix(v) for v in obj]
    return obj


def safe_dumps(obj: Any, **kwargs) -> str:
    """Serialize obj to JSON string with safe numpy/NaN handling."""
    return json.dumps(_fix(obj), default=str, **kwargs)


def safe_jsonable(obj: Any) -> Any:
    """Return a JSON-safe version of obj (for use with FastAPI's jsonable_encoder)."""
    return _fix(obj)


def parse_json_to_dataframe(raw: bytes) -> pd.DataFrame:
    """
    Robustly parse any JSON byte stream into a structured pandas DataFrame.
    Supports:
      1. Standard array of records / dicts
      2. Nested dictionary records (auto-flattened via json_normalize)
      3. Records with embedded list / array values
      4. Column-oriented JSON: {'col1': [1, 2], 'col2': [3, 4]}
      5. Split-oriented JSON: {'columns': [...], 'data': [...]}
      6. Index-oriented JSON: {'0': {'a': 1}, '1': {'a': 2}}
      7. Any wrapper key (e.g. data, items, records, results, payload, users, products, etc.)
      8. Deeply nested API payloads (e.g. {'response': {'result': {'data': [...]}}})
      9. GeoJSON FeatureCollection
      10. Primitive lists: [1, 2, 3] or ['a', 'b']
      11. JSON Lines / NDJSON: newline-delimited JSON objects
      12. UTF-8 with BOM (utf-8-sig), UTF-8, Latin-1, and Windows-1252 encodings
    """
    import io
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            content_str = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        content_str = raw.decode("utf-8", errors="replace")

    content_str = content_str.lstrip("\ufeff")

    try:
        parsed = json.loads(content_str)
    except Exception:
        try:
            return pd.read_json(io.BytesIO(raw), lines=True)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON content: {e}")

    if isinstance(parsed, list):
        if not parsed:
            return pd.DataFrame()
        if all(isinstance(x, dict) for x in parsed):
            return pd.json_normalize(parsed)
        elif all(not isinstance(x, (dict, list)) for x in parsed):
            return pd.DataFrame(parsed, columns=["value"])
        else:
            return pd.json_normalize(parsed)

    elif isinstance(parsed, dict):
        if not parsed:
            return pd.DataFrame()

        # Split-oriented: {'columns': [...], 'data': [...]}
        if "columns" in parsed and "data" in parsed and isinstance(parsed["data"], list):
            idx = parsed.get("index")
            return pd.DataFrame(data=parsed["data"], columns=parsed["columns"], index=idx)

        # GeoJSON FeatureCollection
        if parsed.get("type") == "FeatureCollection" and isinstance(parsed.get("features"), list):
            feats = [f.get("properties", f) for f in parsed["features"]]
            return pd.json_normalize(feats)

        # Column-oriented: {'col1': [1, 2], 'col2': [3, 4]}
        vals = list(parsed.values())
        if vals and all(isinstance(v, list) for v in vals):
            lens = [len(v) for v in vals]
            if len(set(lens)) == 1:
                return pd.DataFrame(parsed)

        # Recursive search for records list
        def find_records_list(d, depth=0):
            if depth > 4 or not isinstance(d, dict):
                return None
            for k in ("data", "items", "records", "rows", "results", "values", "entries", "payload", "features"):
                if k in d and isinstance(d[k], list) and d[k] and isinstance(d[k][0], dict):
                    return d[k]
            for k, v in d.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v
            for k, v in d.items():
                if isinstance(v, dict):
                    res = find_records_list(v, depth + 1)
                    if res is not None:
                        return res
            return None

        records = find_records_list(parsed)
        if records is not None:
            return pd.json_normalize(records)

        # Index-oriented: {'0': {'a': 1}, '1': {'a': 2}}
        if all(isinstance(v, dict) for v in parsed.values()):
            return pd.DataFrame.from_dict(parsed, orient="index")

        # Single record fallback
        return pd.json_normalize([parsed])

    raise ValueError("Unsupported JSON structure: must be an array or object")

