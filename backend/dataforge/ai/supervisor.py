"""
DataForge AI - Chief Supervisor Agent
Coordinates multi-agent dispatch, quantitative reasoning, and ground-truth validation.
Delegates to modular subpackages: router/, reasoning/, fallback/, and tools/.
"""

import logging
from typing import Optional, Dict, Any, List
import pandas as pd

from .client import generate_structured
from .schemas import AnalysisResult, AgentAction
from .router import check_intercept_queries, route_agent_task, generate_smart_dataset_suggestions
from .reasoning import build_analysis_prompt, synchronize_ground_truth
from .reasoning.prompt_builder import schema_summary as _schema_summary
from .fallback import run_deterministic_analysis
from .tools.analytics_tool import run_analytics_tool
from .tools.viz_tool import build_chart_tool

logger = logging.getLogger(__name__)


class DataForgeSupervisor:
    """
    Central AI Coordinator that directs domain agents and guarantees
    100% mathematical synchronization between text analysis and visual charts.
    """

    def __init__(self):
        self.name = "DataForge Chief Analyst"

    def execute(
        self,
        query: str,
        df: pd.DataFrame,
        upload_id: Optional[str] = None,
        metric_context: str = "",
    ) -> Dict[str, Any]:
        """
        Main entrypoint. Evaluates query, delegates to domain agents, and produces unified output.
        """
        agent_actions: List[AgentAction] = []
        clean_query = query.strip()

        # 1. Conversational Intercepts (Greetings, Identity, Schema Explore)
        intercept_res = check_intercept_queries(clean_query, df)
        if intercept_res:
            return intercept_res

        # 2. Specialized Multi-Agent Delegation (Cleaner, AutoML, Pipeline)
        agent_res, actions = route_agent_task(clean_query, df, upload_id=upload_id)
        if agent_res:
            return agent_res
        agent_actions.extend(actions)

        # 3. Quantitative Code Generation via Google GenAI Structured Outputs
        prompt = build_analysis_prompt(clean_query, df, metric_context)

        try:
            analysis: AnalysisResult = generate_structured(
                prompt=prompt,
                response_schema=AnalysisResult,
                temperature=0.1,
                system_instruction=(
                    "You are DataForge Analyst, a Senior Principal Data Analyst and AI Intelligence assistant at DataForge. "
                    "If the user asks who you are or what your name is, clearly state you are DataForge Analyst. "
                    "Write precise pandas/numpy computation code that assigns the final calculation to `result`, "
                    "and select the optimal visualization intent. If the user asks for a preview, sample, head, or summary table, "
                    "assign df.head(5) to `result` and set intent to 'table'. Categorical comparisons must use bar_chart or pie_chart, never line_chart."
                )
            )
        except Exception as exc:
            logger.error("[Supervisor] Structured generation error: %s. Falling back to deterministic engine.", exc)
            return run_deterministic_analysis(clean_query, df, error_msg=str(exc))

        # 4. Sandboxed Code Execution via AnalyticsAgent
        raw_result = None
        executed_code = analysis.code or ""
        if executed_code:
            logger.info("[Supervisor] Executing code via AnalyticsAgent...")
            exec_res = run_analytics_tool(code=executed_code, df=df)
            if exec_res.get("ok"):
                raw_result = exec_res.get("raw_result")
                agent_actions.append(AgentAction(
                    agent="AnalyticsAgent",
                    tool="run_analytics_tool",
                    status="completed",
                    message="Calculated metrics and vectorized transformations.",
                ))
            else:
                logger.warning("[Supervisor] Analytics execution error: %s", exec_res.get("error"))

        # Guarantee preview if requested and code execution didn't produce a table
        if raw_result is None and any(k in clean_query.lower() for k in ["preview", "sample", "head", "show rows", "table preview"]):
            raw_result = df.head(5)
            analysis.intent = "table"

        # 5. Ground Truth Synchronization (Fixes Hallucinations & Syncs Text with Data)
        grounded_answer, corrected_intent, grounded_insight = synchronize_ground_truth(
            query=clean_query,
            raw_result=raw_result,
            df=df,
            proposed_answer=analysis.answer,
            proposed_intent=analysis.intent,
            proposed_insight=analysis.insight,
            x_col=analysis.x_col,
            y_col=analysis.y_col,
        )

        # 6. Interactive Visual Rendering via VisualizerAgent
        chart_spec = build_chart_tool(
            intent=corrected_intent,
            raw_result=raw_result,
            df=df,
            x_col=analysis.x_col,
            y_col=analysis.y_col,
            top_n=analysis.top_n or 10,
        )
        if chart_spec:
            agent_actions.append(AgentAction(
                agent="VisualizerAgent",
                tool="build_chart_tool",
                status="completed",
                message=f"Rendered interactive {corrected_intent.replace('_', ' ')}.",
            ))

        # 7. Follow-Up Suggested Actions (Intelligent, contextual, non-ID questions)
        suggested_actions = generate_smart_dataset_suggestions(
            df=df,
            current_query=clean_query,
            active_col=analysis.x_col or analysis.y_col,
        )

        return {
            "ok": True,
            "answer": grounded_answer,
            "result": chart_spec,
            "code": executed_code,
            "intent": corrected_intent,
            "insight": grounded_insight,
            "agent_actions": [a.model_dump() for a in agent_actions],
            "suggested_actions": suggested_actions,
        }

    def _deterministic_fallback(
        self,
        query: str,
        df: pd.DataFrame,
        sys_notice: str = "",
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper to the modular deterministic fallback engine."""
        return run_deterministic_analysis(query, df, sys_notice)


# Global singleton
supervisor = DataForgeSupervisor()
