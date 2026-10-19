"""
AnalyticsAgent Toolkit - Executes safe, sandboxed Pandas/NumPy analysis code.
"""

import re
import logging
from typing import Dict, Any, Optional
import pandas as pd

from dataforge.api.storage.manager import load
from dataforge.sandbox import run_sandboxed_code, SecurityError, SandboxTimeoutError

logger = logging.getLogger(__name__)

def _clean_code(code: str) -> str:
    """Strip markdown backtick fences from generated code."""
    cleaned = re.sub(r"^```(?:python)?\s*", "", code, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def run_analytics_tool(
    code: str,
    upload_id: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Executes Python code against df using the AST security sandbox.
    Guarantees the code executes only within safe pandas/numpy boundaries.
    """
    if df is None and upload_id:
        df = load(upload_id, "df_clean")
        if df is None:
            df = load(upload_id, "df_raw")

    if df is None:
        return {"ok": False, "error": "No DataFrame available for analysis."}

    cleaned = _clean_code(code)
    try:
        raw_result = run_sandboxed_code(cleaned, df)
        return {
            "ok": True,
            "raw_result": raw_result,
            "code": cleaned,
            "message": "Computation executed successfully.",
        }
    except (SecurityError, SandboxTimeoutError) as sec_exc:
        logger.warning("[AnalyticsAgent] Sandbox restricted execution: %s", sec_exc)
        return {"ok": False, "error": str(sec_exc), "security_violation": True}
    except Exception as exc:
        logger.warning("[AnalyticsAgent] Runtime error executing code: %s", exc)
        return {"ok": False, "error": str(exc), "code": cleaned}
