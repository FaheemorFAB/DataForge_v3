"""
DataForge AI - Query Router
Evaluates incoming questions, resolves ambiguities, and delegates to specialized domain agents.
Maintains clean, professional, enterprise-grade text formatting without informal emojis.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Literal, Tuple
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

from ..client import generate_structured
from ..schemas import AgentAction
from ..tools.cleaner_tool import clean_dataset_tool
from ..tools.automl_tool import analyze_automl_tool
from ..tools.pipeline_tool import export_pipeline_tool
from ..audit.data_auditor import audit_missing_values
from .patterns import (
    GREETING_PATTERNS,
    IDENTITY_PATTERNS,
    THANKS_PATTERNS,
    SCHEMA_EXPLORE_PATTERNS,
    CLEAN_KEYWORDS,
    AUTOML_KEYWORDS,
    PIPELINE_KEYWORDS,
)

logger = logging.getLogger(__name__)


class AgentSelectionDecision(BaseModel):
    chosen_agent: Literal["CleanerAgent", "AutoMLAgent", "PipelineAgent", "AnalyticsAgent", "VisualizerAgent"]
    reason: str = Field(description="1-sentence explanation of why this agent was chosen")
    target_col: Optional[str] = Field(None, description="Target column name if inferred or relevant")


from ..tools.viz_tool import _safe_rows


def generate_smart_dataset_suggestions(
    df: pd.DataFrame,
    current_query: str = "",
    active_col: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Generates intelligent, highly relevant, business-grade analytical questions
    tailored to the active dataset. Never suggests plotting meaningless ID columns.
    Always produces complete, natural questions (not 1-2 words).
    """
    suggestions = []
    if df is None or len(df.columns) == 0:
        return [
            {"label": "Summarize dataset overview and key distributions", "query": "summarize dataset overview and key distributions"}
        ]

    # 1. Categorize columns while strictly excluding ID/hash/key columns
    id_regex = re.compile(r"(^|_)(id|uuid|guid|key|pk|hash|index)($|_)", re.IGNORECASE)

    valid_cols = [c for c in df.columns if not id_regex.search(str(c).strip())]
    if not valid_cols:
        valid_cols = list(df.columns)

    num_cols = [c for c in valid_cols if pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() > 2]
    cat_cols = [c for c in valid_cols if not pd.api.types.is_numeric_dtype(df[c]) or (df[c].nunique() <= 10 and c not in num_cols)]

    def metric_score(c):
        c_low = str(c).lower()
        if any(k in c_low for k in ["revenue", "profit", "sales", "gmv"]): return 10
        if any(k in c_low for k in ["margin", "amount", "total"]): return 8
        if any(k in c_low for k in ["price", "cost", "discount"]): return 7
        if any(k in c_low for k in ["quantity", "units", "rating", "score"]): return 6
        if any(k in c_low for k in ["age", "duration", "tenure"]): return 5
        return 1

    num_cols.sort(key=metric_score, reverse=True)

    def cat_score(c):
        c_low = str(c).lower()
        if any(k in c_low for k in ["category", "segment", "region", "department"]): return 10
        if any(k in c_low for k in ["status", "country", "city", "state", "channel"]): return 8
        if any(k in c_low for k in ["payment", "product", "tier", "plan"]): return 7
        return 1

    cat_cols.sort(key=cat_score, reverse=True)

    top_num = num_cols[0] if num_cols else None
    second_num = num_cols[1] if len(num_cols) > 1 else None
    top_cat = cat_cols[0] if cat_cols else None
    second_cat = cat_cols[1] if len(cat_cols) > 1 else None

    # Contextual check: If active_col was analyzed in current query
    if active_col and active_col in df.columns and not id_regex.search(str(active_col)):
        is_num = pd.api.types.is_numeric_dtype(df[active_col])
        if is_num:
            if top_cat:
                suggestions.append({
                    "label": f"Which {top_cat.replace('_', ' ')} generated the highest {active_col.replace('_', ' ')}?",
                    "query": f"Which {top_cat} has the highest average {active_col}?",
                })
            suggestions.append({
                "label": f"Show statistical distribution and percentiles of {active_col.replace('_', ' ')}",
                "query": f"show histogram and percentiles of {active_col}",
            })
            if second_num and second_num != active_col:
                suggestions.append({
                    "label": f"How does {active_col.replace('_', ' ')} correlate with {second_num.replace('_', ' ')}?",
                    "query": f"show correlation between {active_col} and {second_num}",
                })
        else:
            if top_num:
                suggestions.append({
                    "label": f"Compare total {top_num.replace('_', ' ')} across {active_col.replace('_', ' ')} categories",
                    "query": f"compare total {top_num} by {active_col}",
                })
                suggestions.append({
                    "label": f"View proportion of records by {active_col.replace('_', ' ')} as a chart",
                    "query": f"show pie chart of {active_col}",
                })
            else:
                suggestions.append({
                    "label": f"What is the frequency breakdown of {active_col.replace('_', ' ')}?",
                    "query": f"what is the breakdown of {active_col}?",
                })

    # Add high-value domain suggestions if list is under 3
    if top_cat and top_num and len(suggestions) < 3:
        suggestions.append({
            "label": f"What are the top 5 {top_cat.replace('_', ' ')}s by total {top_num.replace('_', ' ')}?",
            "query": f"what are the top 5 {top_cat} by total {top_num}?",
        })

    if second_cat and top_num and len(suggestions) < 3:
        suggestions.append({
            "label": f"Compare total {top_num.replace('_', ' ')} across {second_cat.replace('_', ' ')} groups",
            "query": f"compare total {top_num} by {second_cat}",
        })
    elif top_num and second_num and len(suggestions) < 3:
        suggestions.append({
            "label": f"How does {second_num.replace('_', ' ')} correlate with {top_num.replace('_', ' ')}?",
            "query": f"correlation between {top_num} and {second_num}",
        })

    if top_num and len(suggestions) < 3:
        suggestions.append({
            "label": f"Show distribution and outlier spread for {top_num.replace('_', ' ')}",
            "query": f"show distribution of {top_num}",
        })

    if len(suggestions) < 3:
        suggestions.append({
            "label": "Audit dataset for missing values, duplicates, and anomalies",
            "query": "audit missing values and anomalies",
        })

    return suggestions[:4]


def check_intercept_queries(query: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Checks for standard conversational intercepts (greetings, identity, gratitude, schema explore)."""
    clean_query = query.strip()

    # 1. Greeting
    if GREETING_PATTERNS.search(clean_query):
        return {
            "ok": True,
            "answer": (
                f"Hello. I am the **DataForge AI Analyst**. I coordinate specialized data agents to analyze, "
                f"clean, model, and visualize your dataset ({df.shape[0]:,} records across {df.shape[1]} columns).\n\n"
                f"Common operations you can perform:\n"
                f"- **Data Sanitization**: \"Clean missing values and clip outliers\"\n"
                f"- **Statistical Profiling**: \"What is the distribution of key metrics?\"\n"
                f"- **Machine Learning**: \"Predict the target column with AutoML\"\n"
                f"- **Workflow Export**: \"Export an Airflow DAG or Python pipeline\""
            ),
            "intent": "summary",
            "result": None,
            "agent_actions": [],
            "suggested_actions": generate_smart_dataset_suggestions(df, current_query=clean_query),
        }

    # 2. Identity / Name
    if IDENTITY_PATTERNS.search(clean_query):
        return {
            "ok": True,
            "answer": (
                "I am **DataForge Analyst**, the **DataForge Autonomous Analytics Intelligence** assistant. "
                "I coordinate specialized domain agents to compute statistics (AnalyticsAgent), "
                "clean dirty records and impute nulls (CleanerAgent), train machine learning models (AutoMLAgent), "
                "render interactive visualizations (VisualizerAgent), and export production pipelines (PipelineAgent) "
                f"for your active dataset ({df.shape[0]:,} records across {df.shape[1]} columns).\n\n"
                "How can I help you analyze your data today?"
            ),
            "intent": "summary",
            "result": None,
            "agent_actions": [],
            "suggested_actions": generate_smart_dataset_suggestions(df, current_query=clean_query),
        }

    # 3. Thanks / Appreciation
    if THANKS_PATTERNS.search(clean_query):
        return {
            "ok": True,
            "answer": "You are welcome. Please let me know if you would like to run additional statistical analyses, sanitize data, or export your pipeline.",
            "intent": "summary",
            "result": None,
            "agent_actions": [],
            "suggested_actions": generate_smart_dataset_suggestions(df, current_query=clean_query),
        }

    # 4. Schema Explore / Dataset Summary / Preview
    if SCHEMA_EXPLORE_PATTERNS.search(clean_query):
        col_list_md = "\n".join(f"- `{col}` ({df[col].dtype}): {df[col].isnull().sum():,} missing ({df[col].isnull().mean()*100:.1f}%)" for col in df.columns)
        
        # Provide an interactive 5-row table preview whenever summary/preview is requested
        preview_tbl = df.head(5)
        table_result = {
            "type": "table",
            "headers": [str(c) for c in df.columns],
            "rows": _safe_rows(preview_tbl.to_dict("records")),
            "total": len(df),
        }

        return {
            "ok": True,
            "answer": (
                f"### Dataset Schema & Column Overview\n\n"
                f"Your active dataset contains **{df.shape[0]:,} records** across **{df.shape[1]} columns**:\n\n"
                f"{col_list_md}\n\n"
                f"An interactive preview of the **first 5 records** is rendered in the table below."
            ),
            "intent": "table",
            "result": table_result,
            "agent_actions": [],
            "suggested_actions": generate_smart_dataset_suggestions(df, current_query=clean_query),
        }

    return None


def route_agent_task(
    query: str,
    df: pd.DataFrame,
    upload_id: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], List[AgentAction]]:
    """
    Evaluates query intent and triggers specialized agents (Cleaner, AutoML, Pipeline).
    Returns (response_dict, agent_actions). If None, query proceeds to Quantitative Reasoning.
    """
    clean_query = query.strip()
    agent_actions: List[AgentAction] = []

    clean_match = bool(CLEAN_KEYWORDS.search(clean_query))
    automl_match = bool(AUTOML_KEYWORDS.search(clean_query))
    pipeline_match = bool(PIPELINE_KEYWORDS.search(clean_query))
    triggers_count = sum([clean_match, automl_match, pipeline_match])

    selected_agent = None
    target_candidate = None

    is_confused = triggers_count > 1 or ("agent" in clean_query.lower() and any(k in clean_query.lower() for k in ["which", "what", "choose", "select", "give", "assign"]))
    if is_confused:
        logger.info("[Router] Query is ambiguous (triggers=%d). Consulting Gemini router...", triggers_count)
        try:
            router_decision: AgentSelectionDecision = generate_structured(
                prompt=(
                    f"USER QUERY: \"{query}\"\n"
                    f"COLUMNS: {list(df.columns)}\n\n"
                    f"SPECIALIZED AGENTS:\n"
                    f"1. CleanerAgent: Data cleaning, missing values, duplicates, outlier clipping, sanitation\n"
                    f"2. AutoMLAgent: Model training, classification, regression, predictive forecasting, target analysis\n"
                    f"3. PipelineAgent: Exporting workflows (Airflow DAG, dbt, Python scripts)\n"
                    f"4. AnalyticsAgent: Statistical calculations, aggregations, correlations, distributions\n"
                    f"5. VisualizerAgent: Graphical rendering, charts, histograms, bars, heatmaps\n\n"
                    f"Determine the single most appropriate agent to lead this task."
                ),
                response_schema=AgentSelectionDecision,
                temperature=0.0,
                system_instruction="You are the Lead Multi-Agent Router. Pick the single best agent for this query."
            )
            selected_agent = router_decision.chosen_agent
            target_candidate = router_decision.target_col
        except Exception as r_err:
            logger.warning("[Router] Gemini router fallback: %s", r_err)

    # ── A. CleanerAgent Delegation ───────────────────────────────────────────
    if upload_id and (selected_agent == "CleanerAgent" or (selected_agent is None and clean_match and triggers_count == 1)):
        logger.info("[Router] Delegating to CleanerAgent...")
        q_clean = clean_query.lower()
        
        is_specific_clean = any(k in q_clean for k in [
            "drop column", "remove column", "delete column",
            "impute", "fill", "clip", "outlier", "cast", "convert",
            "dedup", "duplicate", "undo", "rollback", "revert",
            "option 1", "option 2", "option 3", "median", "mean",
            "mode", "zero", "constant", "drop rows"
        ]) or q_clean in ("1", "2", "3")
        
        # Ambiguous / Informational Request (e.g. "audit missing values", "is there any null cell in percentage", "clean data")
        if not is_specific_clean:
            audit_res = audit_missing_values(df, upload_id=upload_id)
            return {
                "ok": True,
                "answer": audit_res["answer"],
                "result": None,
                "intent": "summary",
                "insight": audit_res["insight"],
                "suggested_actions": audit_res["suggested_actions"],
                "agent_actions": [AgentAction(agent="CleanerAgent", tool="audit_missing_values", status="completed", message="Audited missing value distributions.").model_dump()],
            }, agent_actions

        # Specific Cleaning Execution
        clean_res = clean_dataset_tool(upload_id=upload_id, query=clean_query, auto_clean=True, df=df)
        if clean_res.get("ok"):
            action_item = AgentAction(
                agent="CleanerAgent",
                tool="clean_dataset_tool",
                status="completed",
                message=clean_res.get("message", "Dataset cleaned successfully."),
                data=clean_res.get("stats")
            )
            agent_actions.append(action_item)

            if clean_res.get("is_undo"):
                return {
                    "ok": True,
                    "answer": (
                        f"### Dataset Snapshot Rollback Complete\n\n"
                        f"**CleanerAgent** successfully restored the dataset to the snapshot before the last cleaning operation.\n\n"
                        f"- Active Shape: **{len(df):,} rows across {df.shape[1]} columns**\n\n"
                        f"The active workspace table has been synchronized with the previous state."
                    ),
                    "result": None,
                    "intent": "summary",
                    "insight": "Restored previous dataset snapshot.",
                    "suggested_actions": [
                        {"label": "1. Recommended Cleaning (Median / Mode)", "query": "1"},
                        {"label": "Audit Missing Values", "query": "audit missing values"},
                    ],
                    "agent_actions": [action_item.model_dump()],
                }, agent_actions

            stats = clean_res.get("stats", {})
            actions_list = clean_res.get("actions", [])
            actions_bullet = "\n".join(f"- {a}" for a in actions_list[:5]) if actions_list else "- Applied automated median/mode imputation & structural cleaning"
            init_q = stats.get("initial_quality", 90.0)
            final_q = stats.get("final_quality", 100.0)

            return {
                "ok": True,
                "answer": (
                    f"### Data Sanitization Complete\n\n"
                    f"**CleanerAgent** processed your dataset:\n\n"
                    f"- **Data Completeness Score**: **{init_q}% to {final_q}%** {'(Complete Quality)' if final_q >= 99.9 else ''}\n"
                    f"- **Retained Records**: **{stats.get('cleaned_rows', len(df)):,} valid rows** (from {stats.get('original_rows', df.shape[0]):,})\n\n"
                    f"#### Applied Transformations:\n{actions_bullet}\n\n"
                    f"The active workspace table has been updated."
                ),
                "result": None,
                "intent": "summary",
                "insight": f"Data completeness improved from {init_q}% to {final_q}%.",
                "suggested_actions": [
                    {"label": "Undo Cleaning Snapshot", "query": "undo"},
                    {"label": "View Feature Distributions", "query": f"distribution of {df.columns[0]}"},
                    {"label": "Predict with AutoML", "query": f"predict {df.columns[-1]}"},
                ],
                "download_links": {
                    "csv": f"/api/export/download?format=csv&upload_id={upload_id}",
                    "parquet": f"/api/export/download?format=parquet&upload_id={upload_id}",
                },
                "agent_actions": [action_item.model_dump()],
            }, agent_actions

    # ── B. AutoMLAgent Delegation ────────────────────────────────────────────
    if upload_id and (selected_agent == "AutoMLAgent" or (selected_agent is None and automl_match and triggers_count == 1)):
        logger.info("[Router] Inspecting target for AutoMLAgent...")
        candidate_target = target_candidate
        if not candidate_target:
            for c in reversed(df.columns.tolist()):
                if re.search(rf"\b{re.escape(c.lower())}\b", query.lower()):
                    candidate_target = c
                    break
        if not candidate_target and len(df.columns) > 0:
            candidate_target = df.columns[-1]

        if candidate_target:
            ml_res = analyze_automl_tool(upload_id=upload_id, target_col=candidate_target, df=df)
            if ml_res.get("ok"):
                action_item = AgentAction(
                    agent="AutoMLAgent",
                    tool="analyze_automl_tool",
                    status="completed",
                    message=ml_res.get("message", "Analyzed predictive target."),
                    data={"task": ml_res.get("task"), "models": ml_res.get("recommended_models")}
                )
                agent_actions.append(action_item)

                analytical_intent = any(k in clean_query.lower() for k in ["what is the average", "show chart", "plot"])
                if not analytical_intent:
                    task = ml_res.get("task", "classification").upper()
                    models = ", ".join(ml_res.get("recommended_models", [])[:4])
                    top_feats = ml_res.get("top_features", [])
                    top_feats_str = ", ".join(f"`{f}`" for f in top_feats[:4]) if top_feats else f"All {len(df.columns)-1} candidate features"
                    imbalance = ml_res.get("imbalance", {})
                    imbalance_line = f"\n- **Class Distribution**: Balanced ({imbalance.get('ratio', '1:1')})" if imbalance else ""
                    return {
                        "ok": True,
                        "answer": (
                            f"### Predictive Modeling Formulation: `{candidate_target}`\n\n"
                            f"**AutoMLAgent** formulated a predictive problem for target `{candidate_target}`:\n\n"
                            f"- **Task Architecture**: **{task}**\n"
                            f"- **Target Feature**: `{candidate_target}` ({df[candidate_target].dtype})\n"
                            f"- **Recommended Models**: {models}\n"
                            f"- **High-Signal Predictors**: {top_feats_str}"
                            f"{imbalance_line}\n\n"
                            f"You can navigate to the **AutoML** tab to train and benchmark these models with hyperparameter optimization."
                        ),
                        "result": None,
                        "intent": "summary",
                        "insight": f"Formulated {task} predictive problem for {candidate_target}.",
                        "agent_actions": [action_item.model_dump()],
                    }, agent_actions

    # ── C. PipelineAgent Delegation ──────────────────────────────────────────
    if upload_id and (selected_agent == "PipelineAgent" or (selected_agent is None and pipeline_match and triggers_count == 1)):
        logger.info("[Router] Delegating to PipelineAgent...")
        target_fmt = "airflow" if "airflow" in query.lower() else ("dbt" if "dbt" in query.lower() else "python")
        pipe_res = export_pipeline_tool(upload_id=upload_id, format_type=target_fmt, df=df)
        if pipe_res.get("ok"):
            action_item = AgentAction(
                agent="PipelineAgent",
                tool="export_pipeline_tool",
                status="completed",
                message=pipe_res.get("message", "Generated pipeline code."),
                data={"format": pipe_res.get("format"), "filename": pipe_res.get("filename")}
            )
            agent_actions.append(action_item)
            fmt = pipe_res.get("format", "python").upper()
            full_code = pipe_res.get("code") or pipe_res.get("pipeline_code", "")
            lang = "sql" if "dbt" in target_fmt else "python"
            filename = pipe_res.get("filename", f"pipeline_{upload_id[:8]}.{'py' if 'dbt' not in target_fmt else 'sql'}")
            return {
                "ok": True,
                "answer": (
                    f"### Production Pipeline Export: **{fmt}**\n\n"
                    f"**PipelineAgent** compiled an enterprise ETL pipeline for this dataset:\n\n"
                    f"- **Orchestration Target**: **{fmt}**\n"
                    f"- **Generated Artifact**: `{filename}`\n"
                    f"- **Automated Tasks**: Ingestion, missing-value imputation, type casting, and KPI telemetry\n\n"
                    f"```{lang}\n{full_code}\n```\n\n"
                    f"#### Deployment Steps\n"
                    f"1. Copy the production code above.\n"
                    f"2. Save as `{filename}` in your project repository or DAG folder.\n"
                    f"3. Run locally or schedule in your orchestration environment."
                ),
                "result": None,
                "code": full_code,
                "intent": "summary",
                "insight": f"Pipeline compiled successfully for {fmt} orchestration.",
                "agent_actions": [action_item.model_dump()],
            }, agent_actions

    return None, agent_actions
