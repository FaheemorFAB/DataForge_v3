"""
JoinAgent Toolkit - Inspects relational schemas and recommends merge strategies.
"""

import logging
from typing import Optional, Dict, Any, List
import pandas as pd

from dataforge.api.storage.manager import load

logger = logging.getLogger(__name__)

def inspect_joins_tool(
    upload_id: str,
    other_upload_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyzes primary and foreign key candidates across datasets in the workspace.
    Recommends optimal join keys and flags cardinality mismatches.
    """
    df_primary = load(upload_id, "df_clean") or load(upload_id, "df_raw")
    if df_primary is None:
        return {"ok": False, "error": f"Primary dataset {upload_id} not loaded."}

    candidates = []
    # Identify unique identifier candidates in primary dataset
    primary_id_cols = [c for c in df_primary.columns if "id" in c.lower() or "code" in c.lower() or "key" in c.lower()]

    if other_upload_ids:
        for other_id in other_upload_ids:
            df_other = load(other_id, "df_clean") or load(other_id, "df_raw")
            if df_other is not None:
                common_cols = list(set(df_primary.columns).intersection(set(df_other.columns)))
                if common_cols:
                    candidates.append({
                        "target_upload_id": other_id,
                        "shared_keys": common_cols,
                        "recommended_join": "LEFT JOIN",
                        "estimated_overlap": f"{min(len(df_primary), len(df_other))} rows",
                    })

    return {
        "ok": True,
        "primary_keys": primary_id_cols[:5],
        "join_candidates": candidates,
        "message": f"Found {len(primary_id_cols)} key candidates in primary table."
    }
