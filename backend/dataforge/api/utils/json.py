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
