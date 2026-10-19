"""
DataForge AI - Intent and Keyword Match Patterns
Centralized regex definitions for multi-agent dispatch and query classification.
"""

import re
import difflib
from typing import List, Optional, Tuple
import pandas as pd

GREETING_PATTERNS = re.compile(
    r"^(hi|hello|hey|hiya|howdy|greetings|sup|good\s+(morning|afternoon|evening)|help|what\s+can\s+you\s+do)[\s!.,?]*$",
    re.IGNORECASE
)

IDENTITY_PATTERNS = re.compile(
    r"\b("
    r"who\s+(are|r)\s+(you|u)|"
    r"what\s+(are|r)\s+(you|u)|"
    r"w[ha]{1,4}t(\s+i?s|\'s)?\s+(yo?u?r|ur)\s*name|"
    r"yo?u?r\s+name|ur\s+name|"
    r"what\s+is\s+this(\s+ai)?|"
    r"who\s+(made|created|built)\s+(you|u)|"
    r"tell\s+me\s+about\s+yourself|"
    r"introduce\s+yourself|"
    r"are\s+you\s+(an?\s+)?(ai|bot|chatbot|gpt|gemini|claude|llm)"
    r")\b",
    re.IGNORECASE
)

SPECIFIC_CHART_PATTERNS = [
    (re.compile(r"\b(pie\s*chart|as\s*a\s*pie|in\s*a\s*pie|the\s*pie|pie)\b", re.IGNORECASE), "pie_chart"),
    (re.compile(r"\b(donut\s*chart|doughnut\s*chart|donut|doughnut)\b", re.IGNORECASE), "doughnut_chart"),
    (re.compile(r"\b(bar\s*chart|bar\s*graph|horizontal\s*bar)\b", re.IGNORECASE), "bar_chart"),
    (re.compile(r"\b(line\s*chart|line\s*graph|trend\s*line|time\s*series\s*plot)\b", re.IGNORECASE), "line_chart"),
    (re.compile(r"\b(scatter\s*plot|scatter\s*chart|scatter)\b", re.IGNORECASE), "scatter_chart"),
    (re.compile(r"\b(histogram|distribution\s*plot)\b", re.IGNORECASE), "histogram"),
    (re.compile(r"\b(box\s*plot|box\s*and\s*whisker)\b", re.IGNORECASE), "box_plot"),
]


def is_specific_chart_request(query: str) -> Tuple[bool, Optional[str]]:
    """
    Determines if the user explicitly requested a specific chart type.
    Returns (True, chart_type) if explicit (e.g. 'make the pie', 'bar chart of...').
    Returns (False, None) if generic (e.g. 'make its graph', 'plot this', 'visualize').
    """
    q = query.strip()
    for pattern, chart_type in SPECIFIC_CHART_PATTERNS:
        if pattern.search(q):
            return True, chart_type
    return False, None


CLEAN_KEYWORDS = re.compile(
    r"\b(clean|fix|impute|missing|nan|null|blanks|outlier|outliers|dedup|duplicate|duplicates|mask|pii|sanitize|undo|rollback|revert|drop\s+column|remove\s+column|delete\s+column)\b|^[123]$|^option\s*[123]$",
    re.IGNORECASE
)

AUTOML_KEYWORDS = re.compile(
    r"\b(predict|prediction|model|train|classifier|classification|regression|forecast|forecasting|automl|target)\b",
    re.IGNORECASE
)

PIPELINE_KEYWORDS = re.compile(
    r"\b(pipeline|export|airflow|dbt|dag|script|automate|workflow|cron)\b",
    re.IGNORECASE
)

THANKS_PATTERNS = re.compile(
    r"^(thanks|thank\s+you|awesome|great|cool|nice|good\s+job|perfect|thx|ty)[\s!.,?]*$",
    re.IGNORECASE
)

SCHEMA_EXPLORE_PATTERNS = re.compile(
    r"(what\s+columns|list(\s+all)?\s+columns|show(\s+all)?\s+columns|describe(\s+this|\s+the|\s+my)?\s+dataset|dataset\s+info|how\s+many\s+rows|summarize(\s+my|\s+the)?\s+dataset|dataset\s+summary|overview\s+of\s+(the\s+|my\s+)?(dataset|data)|preview(\s+the|\s+my)?\s+dataset|preview\s+table|show\s+(me\s+)?(the\s+)?(preview|sample|data)|little\s+preview|sample\s+(data|rows)|tell\s+me\s+about\s+(the\s+)?(dataset|data))",
    re.IGNORECASE
)

def is_id_column(col_name: str) -> bool:
    """Determines if a column is an ID, hash, or key that shouldn't be suggested for charts."""
    c = str(col_name).lower().strip()
    if c in ("id", "uuid", "guid", "pk", "key", "index", "hash"):
        return True
    if re.search(r"(^|_)(id|uuid|guid|key|pk|hash|index)($|_)", c):
        return True
    return False


def fuzzy_resolve_all_columns(q: str, df: pd.DataFrame) -> List[str]:
    """Finds all distinct dataframe columns mentioned in query using fuzzy and exact token matching."""
    if df is None or len(df.columns) == 0:
        return []
    found = []
    q_lower = q.lower()
    q_clean = q_lower.replace("_", " ").replace("-", " ")

    for col in df.columns:
        c_str = str(col)
        c_lower = c_str.lower()
        c_clean = c_lower.replace("_", " ").replace("-", " ")
        if re.search(rf"\b{re.escape(c_lower)}\b", q_lower) or re.search(rf"\b{re.escape(c_clean)}\b", q_clean):
            if col not in found:
                found.append(col)

    if not found:
        col_dict = {str(c).lower().replace("_", ""): c for c in df.columns}
        tokens = re.findall(r"[a-zA-Z0-9]+", q_lower)
        for tok in tokens:
            matches = difflib.get_close_matches(tok, col_dict.keys(), n=1, cutoff=0.82)
            if matches:
                matched_col = col_dict[matches[0]]
                if matched_col not in found:
                    found.append(matched_col)

    return found


def fuzzy_resolve_column(q: str, df: pd.DataFrame) -> Optional[str]:
    cols = fuzzy_resolve_all_columns(q, df)
    return cols[0] if cols else None
