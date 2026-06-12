"""
DataForge — Gemini Query Pipeline  [NEW SINGLE-CALL VERSION — NO LANGCHAIN]
Replace: dataforge/gemini_pipeline.py
"""
import os, re, json, time, logging, ast
import pandas as pd
import numpy as np
from dotenv import load_dotenv

from .settings import ROOT_DIR

_env_path = ROOT_DIR / ".env" if (ROOT_DIR / ".env").exists() else ROOT_DIR.parent / ".env"
load_dotenv(override=True, dotenv_path=_env_path)
# Also load backend/.env overrides
_backend_env = ROOT_DIR / "backend" / ".env"
if _backend_env.exists():
    load_dotenv(override=True, dotenv_path=_backend_env)

logger = logging.getLogger(__name__)
print("[gemini_pipeline] Pipeline loaded — using Google Gemini API Key", flush=True)

MAX_CODE_RETRIES = 2
SAMPLE_ROWS      = 6
GEMINI_OK        = True

# ── Identity intercept — questions about what model / who you are ─────────────
_IDENTITY_PATTERNS = re.compile(
    r"(who\s+are\s+you|what\s+are\s+you|your\s+name|what.*model|are\s+you\s+(an?\s+)?(ai|bot|chatbot|gpt|gemini|claude|llm)|tell\s+me\s+about\s+yourself|introduce\s+yourself)",
    re.IGNORECASE
)

def is_available() -> bool:
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip("'\"")
    return bool(api_key)

def _gemini(prompt: str, temperature: float = 0.1, timeout: int = 60) -> str:
    import requests
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip("'\"")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Add it to backend/.env.")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192,
        }
    }
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if response.status_code != 200:
        logger.error("Gemini API error %s: %s", response.status_code, response.text[:300])
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text[:300]}")
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return parts[0].get("text", "") if parts else ""

def _gemini_call(prompt: str, model: str = "", temperature: float = 0.1, timeout: int = 30) -> str:
    return _gemini(prompt, temperature=temperature, timeout=timeout)
# ── Schema summary for prompt ─────────────────────────────────────────────────

def _schema(df: pd.DataFrame) -> str:
    rows = []
    for col in df.columns:
        pct = round(df[col].isnull().mean() * 100, 1)
        dtype_str = str(df[col].dtype)
        
        try:
            non_nulls = df[col].dropna()
            nunique = non_nulls.nunique()
            if nunique <= 10:
                unique_vals = sorted(non_nulls.unique().tolist())
                meta_str = f"unique_values={unique_vals}"
            elif np.issubdtype(df[col].dtype, np.number):
                meta_str = f"range=[{non_nulls.min()}, {non_nulls.max()}]"
            else:
                meta_str = f"sample={non_nulls.head(3).tolist()}"
        except Exception:
            meta_str = f"sample={df[col].dropna().head(3).tolist()}"
            
        rows.append(f"  {col!r}: {dtype_str}, {pct}% null, {meta_str}")
    return "\n".join(rows)


# ── Single Gemini call: returns structured JSON ───────────────────────────────

def _ask_gemini(query: str, df: pd.DataFrame, metric_context: str = "") -> dict:
    col_list = ", ".join(f'"{c}"' for c in df.columns)
    metric_block = f"\n\nBUSINESS METRICS (user-defined):\n{metric_context}\n" if metric_context else ""
    prompt = f"""You are a senior data analyst. Answer the user query about a pandas DataFrame called `df`.

DATAFRAME: {df.shape[0]:,} rows x {df.shape[1]} columns
COLUMNS:
{_schema(df)}

SAMPLE DATA ({SAMPLE_ROWS} rows):
{df.head(SAMPLE_ROWS).to_string(index=False, max_cols=20)}{metric_block}

USER QUERY: "{query}"

TASK:
1. Write pandas/numpy code that answers the query. Assign the final answer to `result`.
2. Write a clear 2-5 sentence plain-text answer with specific numbers from the data.
3. Pick the best visualization: bar_chart, line_chart, scatter_chart, histogram, table, metric, or summary.

RULES:
- Use only df, pd, np — no imports, no print(), no plt
- Always assign to result
- Plain text answer only — no markdown, no asterisks, no bullet points
- Return ONLY valid JSON — no markdown fences, no extra text

JSON FORMAT:
{{
  "code": "result = ...",
  "answer": "plain text answer with numbers",
  "intent": "bar_chart|line_chart|scatter_chart|histogram|table|metric|summary",
  "x_col": "column name or null",
  "y_col": "column name or null",
  "top_n": 10
}}

Available columns: {col_list}"""

    raw  = _gemini(prompt, temperature=0.1, timeout=30)
    text = raw.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$",       "", text, flags=re.MULTILINE).strip()
    # Extract first JSON object
    s, e = text.find("{"), text.rfind("}") + 1
    if s == -1 or e <= s:
        raise ValueError(f"No JSON found in Gemini response: {text[:200]}")
    return json.loads(text[s:e])


# ── Execute pandas code ───────────────────────────────────────────────────────

class SecurityError(Exception):
    pass

class SecureASTValidator(ast.NodeVisitor):
    def __init__(self):
        self.allowed_nodes = {
            ast.Module, ast.Assign, ast.Name, ast.Store, ast.Load,
            ast.Constant, ast.BinOp, ast.UnaryOp, ast.Subscript, ast.Slice,
            ast.Attribute, ast.Call, ast.List, ast.Dict, ast.Tuple, ast.Compare,
            ast.BoolOp, ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
            ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn, ast.Add, ast.Sub,
            ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
            ast.keyword, ast.Lambda, ast.ListComp, ast.DictComp, ast.SetComp,
            ast.GeneratorExp, ast.comprehension
        }
        self.allowed_builtins = {"len", "round", "range", "float", "int", "str", "bool", "list", "dict", "set", "sum", "max", "min", "abs"}

    def visit(self, node):
        node_type = type(node)
        if node_type not in self.allowed_nodes:
            raise SecurityError(f"Unauthorized code node type: {node_type.__name__}")
        if isinstance(node, ast.Name):
            if node.id in __builtins__ and node.id not in self.allowed_builtins:
                raise SecurityError(f"Access to unauthorized builtin: {node.id}")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in __builtins__ and func.id not in self.allowed_builtins:
                    raise SecurityError(f"Call to unauthorized builtin function: {func.id}")
            elif isinstance(func, ast.Attribute):
                if func.attr.startswith("__"):
                    raise SecurityError(f"Dunder attribute access prohibited: {func.attr}")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise SecurityError(f"Dunder attribute access prohibited: {node.attr}")
        self.generic_visit(node)

def _run_code(code: str, df: pd.DataFrame):
    import ast
    cleaned = _clean_code(code)
    try:
        tree = ast.parse(cleaned)
        SecureASTValidator().visit(tree)
    except Exception as e:
        logger.warning("[gemini_pipeline] AST security validation failed: %s", e)
        raise SecurityError(f"AST security validation failed: {e}") from e

    ns = {"df": df.copy(), "pd": pd, "np": np, "result": None}
    exec(cleaned, {}, ns)  # noqa: S102
    return ns.get("result")


# ── Build chart/table/metric payload ─────────────────────────────────────────

def _build_chart(intent, x_col, y_col, top_n, raw, df):
    try:
        if intent == "scatter_chart":
            nc = df.select_dtypes(include=np.number).columns.tolist()
            x  = (x_col if x_col and x_col in df.columns else nc[0] if nc else None)
            y  = (y_col if y_col and y_col in df.columns else nc[1] if len(nc) > 1 else None)
            if x and y:
                pts = [{"x": (float(r[x]) if pd.notna(r[x]) else None),
                        "y": (float(r[y]) if pd.notna(r[y]) else None)}
                       for r in df[[x, y]].dropna().head(500).to_dict("records")]
                return {"type": "scatter_chart", "points": pts, "x_label": x, "y_label": y}

        if intent in ("bar_chart", "histogram", "line_chart"):
            if isinstance(raw, pd.Series):
                series, lx, ly = raw, str(raw.index.name or x_col or "category"), str(y_col or "value")
            elif isinstance(raw, pd.DataFrame) and raw.shape[1] >= 2:
                series = raw.iloc[:, 1]
                series.index = raw.iloc[:, 0].values
                lx, ly = str(raw.columns[0]), str(raw.columns[1])
            elif x_col and x_col in df.columns:
                if y_col and y_col in df.columns:
                    series = df.groupby(x_col)[y_col].mean().sort_values(ascending=False)
                else:
                    series = df[x_col].value_counts()
                lx, ly = x_col, (y_col or "count")
            else:
                return None
            if top_n:
                series = series.head(int(top_n))
            t = "line_chart" if intent == "line_chart" else "bar_chart"
            return {"type": t,
                    "labels":  [str(i) for i in series.index],
                    "values":  [float(v) if pd.notna(v) else 0 for v in series],
                    "x_label": lx, "y_label": ly}

        if intent == "table":
            tbl = raw if isinstance(raw, pd.DataFrame) else df.head(50)
            return {"type": "table", "headers": tbl.columns.tolist(),
                    "rows": _safe_rows(tbl.head(100).to_dict("records")), "total": len(tbl)}

        if intent == "metric":
            val = raw
            if isinstance(val, (pd.Series, pd.DataFrame)):
                val = val.iloc[0] if len(val) else None
            if val is not None:
                try:
                    return {"type": "metric", "value": round(float(val), 4)}
                except (TypeError, ValueError):
                    pass
    except Exception as exc:
        logger.warning("[gemini_pipeline] chart build error: %s", exc)
    return None


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_query_pipeline(query: str, df: pd.DataFrame, metric_context: str = "") -> dict:
    """Gemini-first, deterministic fallback. Single API call, ~2-4s.
    
    metric_context: optional block of user-defined metric definitions
    (e.g. "revenue = price * units") injected into the Gemini prompt.
    """

    # ── Identity intercept ───────────────────────────────────────────────────
    if _IDENTITY_PATTERNS.search(query):
        return {
            "error":   None,
            "answer":  "I'm Dataforge Assistant, your AI-powered data analyst. I can help you explore, analyse, and visualise your dataset. Ask me anything about your data!",
            "result":  {"type": "summary", "text": "I'm Dataforge Assistant, your AI-powered data analyst. I can help you explore, analyse, and visualise your dataset. Ask me anything about your data!"},
            "insight": "",
            "intent":  {"type": "summary"},
            "engine":  "identity",
        }

    if GEMINI_OK:
        try:
            gd     = _ask_gemini(query, df, metric_context=metric_context)
            code   = gd.get("code", "")
            answer = _strip(gd.get("answer") or "")
            intent = gd.get("intent", "summary")
            x_col  = gd.get("x_col")
            y_col  = gd.get("y_col")
            top_n  = gd.get("top_n")

            raw = None
            if code:
                for attempt in range(MAX_CODE_RETRIES + 1):
                    try:
                        raw = _run_code(code, df)
                        break
                    except Exception as err:
                        if attempt < MAX_CODE_RETRIES:
                            logger.warning("[gemini_pipeline] code attempt %d failed: %s", attempt+1, err)
                            fix = _gemini(
                                f"Fix this pandas code:\n```python\n{code}\n```\n"
                                f"Error: {err}\nColumns available: {list(df.columns)}\n"
                                "Return ONLY corrected Python code, no explanation.", timeout=20)
                            code = _clean_code(fix)
                        else:
                            logger.warning("[gemini_pipeline] code exec failed after retries: %s", err)

            if not answer and raw is not None:
                answer = str(raw)[:500]

            result = None
            if intent != "summary":
                result = _build_chart(intent, x_col, y_col, top_n, raw, df)
            if result is None:
                result = {"type": "summary", "text": answer or "No result."}

            return {
                "error":   None,
                "answer":  answer or "No result.",
                "result":  result,
                "insight": "",
                "intent":  {"type": intent},
                "engine":  "llm",
            }

        except Exception as exc:
            logger.error("[gemini_pipeline] Gemini failed, falling back: %s", exc, exc_info=True)

    # Deterministic fallback
    try:
        det = _load_det()
        dr  = det.run_deterministic_pipeline(query, df)
        if not dr.get("error"):
            ri = dr.get("intent", "summary")
            return {"error": None, "answer": dr["answer"], "result": dr["result"],
                    "insight": dr.get("insight", ""),
                    "intent": {"type": ri} if isinstance(ri, str) else ri,
                    "engine": "deterministic"}
    except Exception as e:
        logger.error("[gemini_pipeline] deterministic failed: %s", e)

    return {"error": "Query failed. Check GEMINI_API_KEY in backend/.env."}


# ── Deterministic engine loader ───────────────────────────────────────────────

_DET = None

def _load_det():
    global _DET
    if _DET:
        return _DET
    try:
        from . import deterministic_engine as m
    except Exception as exc:
        raise ImportError("deterministic_engine module not found") from exc
    _DET = m
    return m


# ── Utilities ─────────────────────────────────────────────────────────────────

def _safe_rows(rows):
    out = []
    for row in rows:
        r = {}
        for k, v in row.items():
            if isinstance(v, np.integer):    v = int(v)
            elif isinstance(v, np.floating): v = None if np.isnan(v) else float(v)
            elif isinstance(v, np.bool_):    v = bool(v)
            elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)): v = None
            r[str(k)] = v
        out.append(r)
    return out

def _clean_code(t: str) -> str:
    if not t: return ""
    t = re.sub(r"^```(?:python)?\s*", "", t.strip(), flags=re.MULTILINE)
    return re.sub(r"\s*```\s*$", "", t.strip()).strip()

def _strip(text: str) -> str:
    if not text: return text
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`",      r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*",  r"\1", text)
    text = re.sub(r"^#{1,6}\s+",     "",    text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[*\-]\s+",   "",    text, flags=re.MULTILINE)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

# Aliases
strip_markdown = _strip
_call_gemini = _gemini  # imported by app.py and scheduler.py
