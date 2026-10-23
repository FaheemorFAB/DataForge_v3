"""
DataForge AI - Reasoning Prompt Builder
Formats compact, information-dense schema summaries and instructions for Gemini code generation.
"""

import pandas as pd
import numpy as np

SAMPLE_ROWS = 6


def schema_summary(df: pd.DataFrame) -> str:
    """Generate concise, information-dense schema summary for prompt context."""
    from dataforge.api.utils.helpers import is_id_like_col
    rows = []
    for col in df.columns:
        pct_null = round(df[col].isnull().mean() * 100, 1)
        dtype_str = str(df[col].dtype)
        is_id = is_id_like_col(col, df[col])
        id_tag = " [IDENTIFIER/KEY - DO NOT SUM/AVG]" if is_id else ""
        try:
            non_nulls = df[col].dropna()
            nunique = non_nulls.nunique()
            if is_id:
                meta = f"unique_count={nunique} (identifier column)"
            elif nunique <= 10:
                meta = f"unique_values={sorted(non_nulls.unique().tolist())}"
            elif np.issubdtype(df[col].dtype, np.number):
                meta = f"range=[{non_nulls.min()}, {non_nulls.max()}], mean={round(float(non_nulls.mean()), 2)}"
            else:
                meta = f"sample={non_nulls.head(3).tolist()}"
        except Exception:
            meta = f"sample={df[col].dropna().head(3).tolist()}"
        rows.append(f"  {col!r}: {dtype_str}{id_tag}, {pct_null}% null, {meta}")
    return "\n".join(rows)


_schema_summary = schema_summary


def build_analysis_prompt(
    query: str,
    df: pd.DataFrame,
    metric_context: str = "",
    chat_history: list = None,
) -> str:
    """Builds prompt instructing Gemini to generate executable pandas/numpy code and visualization intent."""
    col_list = ", ".join(f'"{c}"' for c in df.columns)
    metric_block = f"\n\nBUSINESS METRICS (user-defined):\n{metric_context}\n" if metric_context else ""

    history_block = ""
    if chat_history and len(chat_history) > 0:
        lines = ["\nRECENT CONVERSATION CONTEXT (use this to resolve pronouns/follow-ups like 'their', 'that', 'those'):"]
        for msg in chat_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = (msg.get("content") or "").strip()
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{role}: {content}")
        history_block = "\n".join(lines) + "\n"

    return f"""DATAFRAME: {df.shape[0]:,} rows x {df.shape[1]} columns
COLUMNS:
{schema_summary(df)}

SAMPLE DATA ({SAMPLE_ROWS} rows):
{df.head(SAMPLE_ROWS).to_string(index=False, max_cols=20)}{metric_block}{history_block}

USER QUERY: "{query}"

TASK:
1. Write concise, valid pandas/numpy code that answers the query and assigns the final value/series/dataframe to `result`.
2. Choose the optimal visualization intent: bar_chart, pie_chart, doughnut_chart, line_chart, scatter_chart, histogram, table, metric, or summary.

CRITICAL CONVERSATIONAL MEMORY RULE:
- If USER QUERY contains follow-up references (e.g. 'their', 'that', 'which of them', 'compare with', 'show that as a chart', 'how many'), resolve the exact entity and column using RECENT CONVERSATION CONTEXT.
- For example, if the previous turn identified "Private job" as the most common occupation and the user asks "what is their average income?", filter df by `df['parent_occupation'] == 'Private job'` and calculate mean income.

CRITICAL VISUALIZATION RULES:
- Categorical comparisons/distributions (e.g. region, category, country, segment, status) MUST use `bar_chart`, `pie_chart`, or `doughnut_chart`. NEVER use `line_chart` for non-temporal categories!
- Only use `line_chart` when the x-axis represents chronological time (dates, months, years, timestamps) or continuous numeric progressions.
- Use `scatter_chart` only when comparing two numeric variables against each other.
- Use `histogram` for single numeric variable distributions.
- Use `metric` when the user asks for a single scalar KPI (e.g. total revenue, average order value).

CODE EXECUTION RULES:
- Use only `df`, `pd`, `np` — no external imports, no plt, no print().
- Always assign output to variable `result`.
- NEVER calculate sum, average, or variance on identifier/ID columns (e.g. ID, roll number, student ID, employee code, registration number). Only count them (nunique(), count()).
- For category comparison of a numeric metric (e.g. highest income by occupation), use:
  `result = df.groupby('cat_col')['num_col'].mean().sort_values(ascending=False)`
- For rankings and distributions, sort values descending: e.g. `result = df['region'].value_counts()`.

Available columns: {col_list}"""
