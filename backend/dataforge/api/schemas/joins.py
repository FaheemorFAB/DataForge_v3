"""
dataforge/api/schemas/joins.py
──────────────────────────────
Pydantic schemas for DuckDB pushdown multi-table joins, relational modeling,
schema relationship inference, pre-join rollups/aggregations, and custom filters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


JoinType = Literal["INNER", "LEFT", "RIGHT", "FULL", "CROSS", "SEMI", "ANTI"]
FilterOperator = Literal[
    "=", "!=", ">", "<", ">=", "<=", "CONTAINS", "STARTS_WITH", "ENDS_WITH", "IS_NULL", "IS_NOT_NULL", "IN"
]
AggregateFunction = Literal["COUNT", "SUM", "AVG", "MIN", "MAX", "COUNT_DISTINCT"]


class JoinCondition(BaseModel):
    left_col: str = Field(..., description="Column on the left (or source) table")
    right_col: str = Field(..., description="Column on the right (target) table")
    left_table: Optional[str] = Field(
        None, description="Optional explicit name of the left table"
    )


class AggregateExpression(BaseModel):
    column: str = Field(..., description="Column to aggregate")
    function: AggregateFunction = Field("COUNT", description="Aggregation function")
    alias: Optional[str] = Field(None, description="Output alias for the aggregated metric")


class TableRollup(BaseModel):
    table: str = Field(..., description="Target table name to aggregate")
    group_by: List[str] = Field(
        default_factory=list, description="Columns to GROUP BY (e.g. primary/foreign key)"
    )
    aggregates: List[AggregateExpression] = Field(
        default_factory=list, description="List of aggregate metrics"
    )


class TableFilter(BaseModel):
    table: str = Field(..., description="Target table name")
    column: str = Field(..., description="Column name to filter on")
    operator: FilterOperator = Field("=", description="Comparison operator")
    value: Optional[str] = Field(None, description="Comparison value or comma-separated list for IN")


class JoinDefinition(BaseModel):
    table: str = Field(..., description="Target table name to join")
    join_type: JoinType = Field("LEFT", description="SQL Join type")
    conditions: List[JoinCondition] = Field(
        default_factory=list, description="Equi-join conditions"
    )
    rollup: Optional[TableRollup] = Field(
        None, description="Optional pre-join aggregation / rollup definition"
    )


class JoinPreviewRequest(BaseModel):
    upload_id: str = Field(..., description="Workspace upload ID")
    base_table: str = Field(..., description="Starting table name in the FROM clause")
    joins: List[JoinDefinition] = Field(
        default_factory=list, description="Ordered join specifications"
    )
    filters: Optional[List[TableFilter]] = Field(
        None, description="Optional WHERE clause filters across tables"
    )
    rollups: Optional[List[TableRollup]] = Field(
        None, description="Optional standalone table rollups"
    )
    selected_columns: Optional[List[str]] = Field(
        None, description="Optional projected column list / aliases"
    )
    custom_sql: Optional[str] = Field(
        None, description="Optional direct DuckDB SQL override to preview"
    )
    limit: Optional[int] = Field(
        50, ge=1, le=500, description="Preview row limit"
    )


class JoinMaterializeRequest(BaseModel):
    upload_id: str = Field(..., description="Workspace upload ID")
    base_table: str = Field(..., description="Starting table name")
    joins: List[JoinDefinition] = Field(
        default_factory=list, description="Ordered join specifications"
    )
    filters: Optional[List[TableFilter]] = Field(
        None, description="Optional WHERE clause filters across tables"
    )
    rollups: Optional[List[TableRollup]] = Field(
        None, description="Optional standalone table rollups"
    )
    selected_columns: Optional[List[str]] = Field(
        None, description="Optional projected column list / aliases"
    )
    custom_sql: Optional[str] = Field(
        None, description="Optional direct DuckDB SQL override to materialize"
    )
    output_dataset_name: Optional[str] = Field(
        None, description="Target name for the materialized workspace dataset"
    )


class ExecuteCustomSqlRequest(BaseModel):
    upload_id: str = Field(..., description="Workspace upload ID")
    sql: str = Field(..., description="DuckDB SQL query to execute")
    limit: Optional[int] = Field(50, ge=1, le=500, description="Preview row limit")


class MaterializeCustomSqlRequest(BaseModel):
    upload_id: str = Field(..., description="Workspace upload ID")
    sql: str = Field(..., description="DuckDB SQL query to execute and commit")
    output_dataset_name: Optional[str] = Field(
        None, description="Target name for the materialized workspace dataset"
    )


class PresetLoadRequest(BaseModel):
    upload_id: str = Field(..., description="Workspace upload ID")
    preset: Literal["ecommerce", "saas", "healthcare"] = Field(
        "ecommerce", description="Pre-packaged multi-table schema preset"
    )


class ColumnSummary(BaseModel):
    name: str
    dtype: str
    null_count: int = 0
    unique_count: int = 0
    sample_values: List[Any] = Field(default_factory=list)


class TableSummary(BaseModel):
    name: str
    is_primary: bool
    row_count: int
    col_count: int
    columns: List[ColumnSummary] = Field(default_factory=list)


class InferredRelationship(BaseModel):
    left_table: str
    left_column: str
    right_table: str
    right_column: str
    confidence: float
    cardinality: str
    reason: str


class TablesListResponse(BaseModel):
    ok: bool = True
    tables: List[TableSummary]
    relationships: List[InferredRelationship]


class SheetImportItem(BaseModel):
    sheet_name: str
    table_name: Optional[str] = None


class SheetsImportRequest(BaseModel):
    upload_id: str
    source_type: Literal["excel_local", "google_sheets", "excel_online"] = "excel_local"
    source_url: Optional[str] = None
    selected_sheets: List[SheetImportItem] = Field(default_factory=list)


class SheetsInspectRequest(BaseModel):
    source_type: Literal["google_sheets", "excel_online"]
    url: str


class IntegrityAuditRequest(BaseModel):
    upload_id: str
    left_table: str
    left_column: str
    right_table: str
    right_column: str


class DrillDownRequest(BaseModel):
    upload_id: str
    parent_table: str
    child_table: str
    parent_column: str
    child_column: str
    parent_value: Any
    limit: Optional[int] = 100

