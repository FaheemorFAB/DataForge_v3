"""
dataforge/procedure_schema.py
───────────────────────────────
JSON Schema & Pydantic Definitions for DataForge Stored Procedures (DF-SPE).
Defines:
  • Typed Parameter Declarations (string, int, float, bool, enum, date, column_ref)
  • DAG Transformation Nodes (source, clean_names, filter, impute, compute,
    aggregate, dedupe, cast, join, union, assertion_gate, output)
  • Topological Sort & Cycle Detection (Kahn's Algorithm)
  • Schema Inference Across Nodes
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ParameterType(str, Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"
    DATE = "date"
    COLUMN_REF = "column_ref"


class ProcedureParameter(BaseModel):
    name: str = Field(..., description="Unique parameter identifier, e.g. 'min_order_value'")
    type: ParameterType = Field(default=ParameterType.STRING)
    default: Optional[Any] = Field(default=None, description="Default parameter value")
    required: bool = Field(default=False, description="Whether parameter is required at invocation")
    description: Optional[str] = Field(default=None)
    allowed_values: Optional[List[Any]] = Field(default=None, description="Allowed choices for enum parameters")
    min_value: Optional[float] = Field(default=None, description="Minimum numeric value")
    max_value: Optional[float] = Field(default=None, description="Maximum numeric value")


class AssertionSeverity(str, Enum):
    ERROR = "error"
    WARN = "warn"


class QualityAssertion(BaseModel):
    type: Literal["not_null", "unique", "range", "accepted_values", "row_count", "referential"] = Field(...)
    column: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    values: Optional[List[Any]] = None
    min_rows: Optional[int] = None
    max_rows: Optional[int] = None
    parent_column: Optional[str] = None
    foreign_column: Optional[str] = None
    severity: AssertionSeverity = Field(default=AssertionSeverity.ERROR)


class ProcedureNode(BaseModel):
    id: str = Field(..., description="Unique node identifier within the procedure DAG")
    type: Literal[
        "source",
        "clean_names",
        "filter",
        "impute",
        "compute",
        "aggregate",
        "dedupe",
        "cast",
        "join",
        "union",
        "assertion_gate",
        "output",
    ] = Field(...)
    inputs: List[str] = Field(
        default_factory=list,
        description="List of node IDs whose outputs serve as inputs to this node. Empty for source nodes.",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node-specific configuration dictionary",
    )


class GoldenTestCase(BaseModel):
    name: str
    description: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    expected_row_count: Optional[int] = None
    expected_columns: Optional[List[str]] = None
    expected_aggregates: Optional[Dict[str, float]] = None


class ProcedureDefinition(BaseModel):
    schema_version: str = Field(default="1.0.0")
    procedure_id: str = Field(..., description="Unique machine identifier or slug, e.g. 'sp_finance_reconcile'")
    version: str = Field(default="1.0.0", description="SemVer version tag, e.g. '1.0.0'")
    name: str = Field(..., description="Human-readable title")
    description: Optional[str] = Field(default=None)
    parameters: List[ProcedureParameter] = Field(default_factory=list)
    nodes: List[ProcedureNode] = Field(default_factory=list)
    golden_tests: List[GoldenTestCase] = Field(default_factory=list)

    def get_parameter_dict(self, runtime_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Resolves and validates runtime parameters against parameter definitions."""
        runtime_params = runtime_params or {}
        resolved: Dict[str, Any] = {}

        for param in self.parameters:
            val = runtime_params.get(param.name, param.default)
            if param.required and val is None:
                raise ValueError(f"Required procedure parameter '{param.name}' was not provided.")

            if val is not None:
                if param.type == ParameterType.INT:
                    val = int(val)
                elif param.type == ParameterType.FLOAT:
                    val = float(val)
                elif param.type == ParameterType.BOOL:
                    if isinstance(val, str):
                        val = val.lower() in ("true", "1", "yes")
                    else:
                        val = bool(val)
                elif param.type == ParameterType.ENUM and param.allowed_values is not None:
                    if val not in param.allowed_values:
                        raise ValueError(
                            f"Parameter '{param.name}' value '{val}' is not in allowed choices: {param.allowed_values}"
                        )

                if param.min_value is not None and isinstance(val, (int, float)) and val < param.min_value:
                    raise ValueError(f"Parameter '{param.name}' ({val}) is below minimum {param.min_value}")
                if param.max_value is not None and isinstance(val, (int, float)) and val > param.max_value:
                    raise ValueError(f"Parameter '{param.name}' ({val}) exceeds maximum {param.max_value}")

            resolved[param.name] = val

        return resolved

    def topological_sort(self) -> List[ProcedureNode]:
        """
        Validates that the procedure graph is a valid Directed Acyclic Graph (DAG)
        and returns nodes in topological execution order using Kahn's algorithm.
        Raises ValueError if a cycle or missing dependency is detected.
        """
        node_map = {n.id: n for n in self.nodes}
        if len(node_map) != len(self.nodes):
            raise ValueError("Duplicate node IDs found in procedure definition.")

        # In-degree computation
        in_degree: Dict[str, int] = {n.id: 0 for n in self.nodes}
        dependents: Dict[str, List[str]] = {n.id: [] for n in self.nodes}

        for node in self.nodes:
            for parent_id in node.inputs:
                if parent_id not in node_map:
                    raise ValueError(
                        f"Node '{node.id}' references undeclared input dependency '{parent_id}'."
                    )
                in_degree[node.id] += 1
                dependents[parent_id].append(node.id)

        # Queue nodes with in-degree 0 (roots / sources)
        queue = [n_id for n_id, deg in in_degree.items() if deg == 0]
        sorted_order: List[ProcedureNode] = []

        while queue:
            curr_id = queue.pop(0)
            sorted_order.append(node_map[curr_id])
            for child_id in dependents[curr_id]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)

        if len(sorted_order) != len(self.nodes):
            unresolved = [n_id for n_id, deg in in_degree.items() if deg > 0]
            raise ValueError(f"Cyclic dependency detected in procedure DAG involving nodes: {unresolved}")

        return sorted_order
