"""
DataForge AI - Reasoning Prompt Builder
Formats compact, information-dense schema summaries and instructions for Gemini code generation.
"""

import pandas as pd
import numpy as np

SAMPLE_ROWS = 6


def schema_summary(df: pd.DataFrame) -> str:
    """Generate concise, information-dense schema summary for prompt context."""
    rows = []
    for col in df.columns:
        pct_null = round(df[col].isnull().mean() * 100, 1)
        dtype_str = str(df[col].dtype)
        try:
            non_nulls = df[col].dropna()
            nunique = non_nulls.nunique()
            if nunique <= 10:
                meta = f"unique_values={sorted(non_nulls.unique().tolist())}"
            elif np.issubdtype(df[col].dtype, np.number):
                meta = f"range=[{non_nulls.min()}, {non_nulls.max()}]"
            else:
                meta = f"sample={non_nulls.head(3).tolist()}"
        except Exception:
            meta = f"sample={df[col].dropna().head(3).tolist()}"
        rows.append(f"  {col!r}: {dtype_str}, {pct_null}% null, {meta}")
    return "\n".join(rows)


_schema_summary = schema_summary


def build_analysis_prompt(query: str, df: pd.DataFrame, metric_context: str = "") -> str:
    """Builds prompt instructing Gemini to generate executable pandas/numpy code and visualization intent."""
    col_list = ", ".join(f'"{c}"' for c in df.columns)
    metric_block = f"\n\nBUSINESS METRICS (user-defined):\n{metric_context}\n" if metric_context else ""

    return f"""DATAFRAME: {df.shape[0]:,} rows x {df.shape[1]} columns
COLUMNS:
{schema_summary(df)}

SAMPLE DATA ({SAMPLE_ROWS} rows):
{df.head(SAMPLE_ROWS).to_string(index=False, max_cols=20)}{metric_block}

USER QUERY: "{query}"

TASK:
1. Write concise, valid pandas/numpy code that answers the query and assigns the final value/series/dataframe to `result`.
2. Choose the optimal visualization intent: bar_chart, pie_chart, doughnut_chart, line_chart, scatter_chart, histogram, table, metric, or summary.

CRITICAL VISUALIZATION RULES:
- Categorical comparisons/distributions (e.g. region, category, country, segment, status) MUST use `bar_chart`, `pie_chart`, or `doughnut_chart`. NEVER use `line_chart` for non-temporal categories!
- Only use `line_chart` when the x-axis represents chronological time (dates, months, years, timestamps) or continuous numeric progressions.
- Use `scatter_chart` only when comparing two numeric variables against each other.
- Use `histogram` for single numeric variable distributions.
- Use `metric` when the user asks for a single scalar KPI (e.g. total revenue, average order value).

CODE EXECUTION RULES:
- Use only `df`, `pd`, `np` — no external imports, no plt, no print().
- Always assign output to variable `result`.
- For rankings and distributions, sort values descending: e.g. `result = df['region'].value_counts()`.

Available columns: {col_list}"""
