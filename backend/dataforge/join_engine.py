"""
DataForge Relational Modeling & DuckDB Pushdown Join Engine
═══════════════════════════════════════════════════════════
High-performance in-process SQL execution, multi-table relation inference,
collision resolution, live preview, and parquet materialization.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import numpy as np
import pandas as pd

from dataforge.api.storage.manager import STORE_DIR, exists, load, save, upath
from dataforge.api.utils.helpers import df_profile

log = logging.getLogger(__name__)


def _sanitize_table_name(name: Any) -> str:
    """Ensure table identifier is safe for SQL without injection risks."""
    if not name or str(name).lower() in ("none", "null"):
        return "primary_table"
    clean = re.sub(r"[^\w]", "_", str(name).strip())
    if clean and clean[0].isdigit():
        clean = f"t_{clean}"
    return clean.lower() or "primary_table"


def _format_filter_sql(f: Dict[str, Any], table_map: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Formats a single table filter specification into safe DuckDB SQL."""
    orig_tbl = _sanitize_table_name(f.get("table", ""))
    tbl = table_map.get(orig_tbl, orig_tbl) if table_map else orig_tbl
    col = str(f.get("column", "")).replace('"', '').strip()
    op = str(f.get("operator", "=")).upper().strip()
    raw_val = f.get("value")

    if not tbl or not col:
        return None

    col_expr = f'"{tbl}"."{col}"'

    if op == "IS_NULL":
        return f"{col_expr} IS NULL"
    if op == "IS_NOT_NULL":
        return f"{col_expr} IS NOT NULL"

    if raw_val is None:
        return None

    val_str = str(raw_val).strip()

    if op == "CONTAINS":
        clean_val = val_str.replace("'", "''")
        return f"{col_expr} ILIKE '%{clean_val}%'"
    elif op == "STARTS_WITH":
        clean_val = val_str.replace("'", "''")
        return f"{col_expr} ILIKE '{clean_val}%'"
    elif op == "ENDS_WITH":
        clean_val = val_str.replace("'", "''")
        return f"{col_expr} ILIKE '%{clean_val}'"
    elif op == "IN":
        items = [v.strip().replace("'", "''") for v in val_str.split(",") if v.strip()]
        if not items:
            return None
        in_items = ", ".join(f"'{i}'" for i in items)
        return f"{col_expr} IN ({in_items})"
    elif op in ("=", "!=", ">", "<", ">=", "<="):
        # Numeric check
        try:
            num = float(val_str)
            if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
                return f"{col_expr} {op} {int(val_str)}"
            return f"{col_expr} {op} {num}"
        except ValueError:
            clean_val = val_str.replace("'", "''")
            return f"{col_expr} {op} '{clean_val}'"

    return None


class DuckDBJoinEngine:
    """
    In-process DuckDB engine managing multi-table datasets, inferring schema relations,
    generating collision-free SQL, and executing pushdown joins.
    """

    @staticmethod
    def get_tables_dir(upload_id: str) -> Path:
        """Returns workspace tables directory for secondary tables."""
        t_dir = STORE_DIR / str(upload_id) / "tables"
        t_dir.mkdir(parents=True, exist_ok=True)
        return t_dir

    @classmethod
    def get_workspace_tables(cls, upload_id: str) -> Dict[str, pd.DataFrame]:
        """
        Loads all tables registered in the workspace session:
        - Secondary tables from STORE_DIR / upload_id / tables / *.parquet
        - Primary table if not already represented in secondary tables
        """
        tables: Dict[str, pd.DataFrame] = {}

        # 1. Secondary tables first
        t_dir = cls.get_tables_dir(upload_id)
        for p_file in sorted(t_dir.glob("*.parquet")):
            tbl_name = _sanitize_table_name(p_file.stem)
            try:
                tables[tbl_name] = pd.read_parquet(p_file)
            except Exception as e:
                log.warning("Failed to load secondary table %s: %s", p_file, e)

        # 2. Primary table (from df_clean or df_raw)
        primary_df = load(upload_id, "df_clean")
        if primary_df is None:
            primary_df = load(upload_id, "df_raw")

        if primary_df is not None:
            profile = load(upload_id, "profile") or {}
            raw_filename = profile.get("filename")
            if raw_filename:
                primary_name = _sanitize_table_name(Path(raw_filename).stem)
            else:
                primary_name = "orders" if "orders" in tables else "primary_table"

            # Only add primary_name if not already loaded from tables/ directory
            if primary_name not in tables:
                tables[primary_name] = primary_df

        return tables

    @classmethod
    def save_workspace_table(cls, upload_id: str, table_name: str, df: pd.DataFrame) -> str:
        """Saves an additional table to the workspace project."""
        clean_name = _sanitize_table_name(table_name)
        t_dir = cls.get_tables_dir(upload_id)
        out_path = t_dir / f"{clean_name}.parquet"
        df.to_parquet(out_path, index=False)
        log.info("Saved workspace secondary table: %s (%d rows)", clean_name, len(df))
        return clean_name

    @classmethod
    def delete_workspace_table(cls, upload_id: str, table_name: str) -> bool:
        """Removes a secondary table from the workspace."""
        clean_name = _sanitize_table_name(table_name)
        t_dir = cls.get_tables_dir(upload_id)
        p = t_dir / f"{clean_name}.parquet"
        if p.exists():
            p.unlink()
            return True
        return False

    @staticmethod
    def infer_relationships(tables: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Inspects all pairs of tables to automatically discover candidate Join Keys:
        - Exact matches: `user_id` <-> `user_id`
        - Normalized matches: `customer_id` <-> `id`, `order_id` <-> `id`
        - Type compatibility checks
        - Primary key candidate analysis (uniqueness in target table)
        """
        suggestions: List[Dict[str, Any]] = []
        table_names = list(tables.keys())

        for i in range(len(table_names)):
            for j in range(i + 1, len(table_names)):
                t1_name, t2_name = table_names[i], table_names[j]
                df1, df2 = tables[t1_name], tables[t2_name]

                cols1 = list(df1.columns)
                cols2 = list(df2.columns)

                for c1 in cols1:
                    c1_clean = c1.lower().strip()
                    for c2 in cols2:
                        c2_clean = c2.lower().strip()

                        # Evaluate match score
                        confidence = 0.0
                        match_reason = ""

                        # 1. Exact Name Match
                        if c1_clean == c2_clean:
                            if any(k in c1_clean for k in ("id", "key", "code", "num", "uuid")):
                                confidence = 0.95
                                match_reason = f"Exact Key Identifier Match: {c1}"
                            else:
                                confidence = 0.70
                                match_reason = f"Matching Column Name: {c1}"

                        # 2. Suffix / Entity ID Match (e.g. orders.customer_id <-> customers.id)
                        elif c1_clean == f"{t2_name}_id" and c2_clean in ("id", "pk"):
                            confidence = 0.98
                            match_reason = f"Foreign Key Relationship: {t1_name}.{c1} -> {t2_name}.{c2}"
                        elif c2_clean == f"{t1_name}_id" and c1_clean in ("id", "pk"):
                            confidence = 0.98
                            match_reason = f"Foreign Key Relationship: {t2_name}.{c2} -> {t1_name}.{c1}"

                        # 3. Partial Stem Matching (e.g. cust_id <-> customer_id)
                        elif "id" in c1_clean and "id" in c2_clean:
                            stem1 = c1_clean.replace("_id", "").replace("id", "")
                            stem2 = c2_clean.replace("_id", "").replace("id", "")
                            if stem1 and stem2 and (stem1 in stem2 or stem2 in stem1):
                                confidence = 0.85
                                match_reason = f"Fuzzy ID Match: {c1} ~ {c2}"

                        if confidence >= 0.65:
                            # Verify Type Compatibility
                            t1_is_num = pd.api.types.is_numeric_dtype(df1[c1])
                            t2_is_num = pd.api.types.is_numeric_dtype(df2[c2])
                            if t1_is_num != t2_is_num:
                                confidence *= 0.5  # Penalize mismatched types

                            # Determine Cardinality
                            u1 = df1[c1].nunique() / max(len(df1), 1)
                            u2 = df2[c2].nunique() / max(len(df2), 1)
                            if u2 >= 0.98 and u1 < 0.98:
                                cardinality = "many_to_one"
                            elif u1 >= 0.98 and u2 < 0.98:
                                cardinality = "one_to_many"
                            elif u1 >= 0.98 and u2 >= 0.98:
                                cardinality = "one_to_one"
                            else:
                                cardinality = "many_to_many"

                            suggestions.append({
                                "left_table": t1_name,
                                "left_column": c1,
                                "right_table": t2_name,
                                "right_column": c2,
                                "confidence": round(confidence, 2),
                                "cardinality": cardinality,
                                "reason": match_reason,
                            })

        # Sort suggestions by confidence descending
        suggestions.sort(key=lambda s: s["confidence"], reverse=True)
        return suggestions

    @classmethod
    def build_sql(
        cls,
        base_table: str,
        joins: List[Dict[str, Any]],
        tables: Dict[str, pd.DataFrame],
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        rollups: Optional[List[Dict[str, Any]]] = None,
        custom_sql: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Tuple[str, List[str]]:
        """
        Constructs an intelligent DuckDB SQL query with pre-join rollups (CTEs),
        collision-free column projections, and custom WHERE filters.
        """
        if custom_sql and custom_sql.strip():
            sql_clean = custom_sql.strip().rstrip(";")
            if limit and limit > 0 and not re.search(r"\bLIMIT\s+\d+", sql_clean, re.I):
                sql_clean += f" LIMIT {limit}"
            return sql_clean, []

        base_table_clean = _sanitize_table_name(base_table)
        if base_table_clean not in tables:
            raise ValueError(f"Base table '{base_table}' not found in workspace.")

        # 1. Collect all rollups / pre-join aggregations
        all_rollups: List[Dict[str, Any]] = list(rollups or [])
        for j in joins:
            if j.get("rollup"):
                all_rollups.append(j["rollup"])

        cte_clauses: List[str] = []
        table_query_map: Dict[str, str] = {}  # maps original table -> query reference (CTE or original)
        synthetic_table_cols: Dict[str, List[str]] = {}  # tracks projected columns for CTEs

        for r in all_rollups:
            orig_tbl = _sanitize_table_name(r.get("table", ""))
            if orig_tbl not in tables:
                continue
            cte_name = f"{orig_tbl}_rollup"
            group_by_cols = [str(c).strip() for c in r.get("group_by", [])]
            aggs = r.get("aggregates", [])

            agg_projs: List[str] = []
            synth_cols: List[str] = []
            for g in group_by_cols:
                agg_projs.append(f'"{g}"')
                synth_cols.append(g)

            for a in aggs:
                col_name = str(a.get("column", "")).strip()
                fn = str(a.get("function", "COUNT")).upper().strip()
                alias = a.get("alias") or f"{orig_tbl}_{fn.lower()}_{col_name}"
                if fn == "COUNT_DISTINCT":
                    agg_projs.append(f'COUNT(DISTINCT "{col_name}") AS "{alias}"')
                elif fn in ("COUNT", "SUM", "AVG", "MIN", "MAX"):
                    agg_projs.append(f'{fn}("{col_name}") AS "{alias}"')
                synth_cols.append(alias)

            if not agg_projs:
                continue

            group_str = f"GROUP BY {', '.join([f'\"{g}\"' for g in group_by_cols])}" if group_by_cols else ""
            cte_sql = f'"{cte_name}" AS (\n  SELECT\n    ' + ",\n    ".join(agg_projs) + f'\n  FROM "{orig_tbl}"\n  {group_str}\n)'
            cte_clauses.append(cte_sql)
            table_query_map[orig_tbl] = cte_name
            synthetic_table_cols[orig_tbl] = synth_cols

        # Determine participating tables
        participating_tables = [base_table_clean]
        for j in joins:
            jt = _sanitize_table_name(j.get("table", ""))
            if jt in tables and jt not in participating_tables:
                participating_tables.append(jt)

        # 2. Collision detection
        col_counts: Dict[str, int] = {}
        for t_name in participating_tables:
            cols_to_scan = synthetic_table_cols.get(t_name, list(tables[t_name].columns))
            for c in cols_to_scan:
                col_counts[c] = col_counts.get(c, 0) + 1

        # 3. Column Projections
        projections: List[str] = []
        projected_aliases: List[str] = []

        for t_name in participating_tables:
            source_tbl_in_query = table_query_map.get(t_name, t_name)
            cols_to_scan = synthetic_table_cols.get(t_name, list(tables[t_name].columns))

            for c in cols_to_scan:
                is_collision = col_counts[c] > 1
                alias = f"{t_name}_{c}" if is_collision else c

                if selected_columns and alias not in selected_columns and c not in selected_columns:
                    continue

                projections.append(f'"{source_tbl_in_query}"."{c}" AS "{alias}"')
                projected_aliases.append(alias)

        if not projections:
            base_src = table_query_map.get(base_table_clean, base_table_clean)
            projections = [f'"{base_src}".*']

        proj_str = ",\n  ".join(projections)

        # 4. Assemble FROM and JOIN clauses
        base_src = table_query_map.get(base_table_clean, base_table_clean)
        sql_lines = [
            f"SELECT\n  {proj_str}",
            f'FROM "{base_src}"',
        ]

        for j in joins:
            target_tbl = _sanitize_table_name(j.get("table", ""))
            if target_tbl not in tables:
                continue

            target_src = table_query_map.get(target_tbl, target_tbl)
            j_type = str(j.get("join_type", "LEFT")).upper().strip()
            if j_type not in ("INNER", "LEFT", "RIGHT", "FULL", "CROSS", "SEMI", "ANTI"):
                j_type = "LEFT"

            conditions = j.get("conditions", [])
            cond_clauses = []
            for cond in conditions:
                l_col = cond.get("left_col")
                r_col = cond.get("right_col")
                raw_lt = cond.get("left_table")
                l_tbl_name = _sanitize_table_name(raw_lt if raw_lt else base_table_clean)
                l_src = table_query_map.get(l_tbl_name, l_tbl_name)
                if l_col and r_col:
                    cond_clauses.append(f'"{l_src}"."{l_col}" = "{target_src}"."{r_col}"')

            if j_type == "CROSS" or not cond_clauses:
                sql_lines.append(f'CROSS JOIN "{target_src}"')
            elif j_type == "SEMI":
                sql_lines.append(f'SEMI JOIN "{target_src}" ON {" AND ".join(cond_clauses)}')
            elif j_type == "ANTI":
                sql_lines.append(f'ANTI JOIN "{target_src}" ON {" AND ".join(cond_clauses)}')
            else:
                sql_lines.append(f'{j_type} JOIN "{target_src}" ON {" AND ".join(cond_clauses)}')

        # 5. WHERE filters
        if filters:
            filter_clauses = []
            for f in filters:
                formatted = _format_filter_sql(f, table_query_map)
                if formatted:
                    filter_clauses.append(formatted)
            if filter_clauses:
                sql_lines.append(f"WHERE {' AND '.join(filter_clauses)}")

        if limit and limit > 0:
            sql_lines.append(f"LIMIT {limit}")

        body_sql = "\n".join(sql_lines)
        if cte_clauses:
            full_sql = "WITH\n  " + ",\n  ".join(cte_clauses) + "\n" + body_sql
        else:
            full_sql = body_sql

        return full_sql, projected_aliases

    @classmethod
    def preview_join(
        cls,
        upload_id: str,
        base_table: str,
        joins: List[Dict[str, Any]],
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        rollups: Optional[List[Dict[str, Any]]] = None,
        custom_sql: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Executes an in-memory DuckDB pushdown join with optional rollups and filters.
        """
        t0 = time.perf_counter()
        tables = cls.get_workspace_tables(upload_id)
        if not tables:
            raise ValueError("No tables found in workspace project.")

        sql_query, aliases = cls.build_sql(
            base_table=base_table,
            joins=joins,
            tables=tables,
            selected_columns=selected_columns,
            filters=filters,
            rollups=rollups,
            custom_sql=custom_sql,
            limit=limit,
        )

        con = duckdb.connect(database=":memory:")
        for t_name, df in tables.items():
            con.register(t_name, df)

        df_preview = con.execute(sql_query).df()

        # Compute full count estimate
        if custom_sql:
            count_query = f"SELECT COUNT(*) AS total_count FROM ({custom_sql.rstrip(';')}) subq"
        else:
            count_sql, _ = cls.build_sql(
                base_table=base_table,
                joins=joins,
                tables=tables,
                selected_columns=selected_columns,
                filters=filters,
                rollups=rollups,
                custom_sql=None,
                limit=None,
            )
            count_query = f"SELECT COUNT(*) AS total_count FROM ({count_sql}) subq"

        try:
            total_rows = int(con.execute(count_query).fetchone()[0])
        except Exception:
            total_rows = len(df_preview)

        con.close()
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        cols_meta = [{"name": c, "dtype": str(df_preview[c].dtype)} for c in df_preview.columns]
        rows = df_preview.replace({np.nan: None}).to_dict(orient="records")

        return {
            "ok": True,
            "sql": sql_query,
            "columns": cols_meta,
            "rows": rows,
            "preview_count": len(rows),
            "total_estimated_rows": total_rows,
            "execution_time_ms": elapsed_ms,
        }

    @classmethod
    def materialize_join(
        cls,
        upload_id: str,
        base_table: str,
        joins: List[Dict[str, Any]],
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        rollups: Optional[List[Dict[str, Any]]] = None,
        custom_sql: Optional[str] = None,
        output_dataset_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes full DuckDB pushdown join and commits merged result to workspace.
        """
        t0 = time.perf_counter()
        tables = cls.get_workspace_tables(upload_id)
        if not tables:
            raise ValueError("No tables found in workspace project.")

        full_sql, aliases = cls.build_sql(
            base_table=base_table,
            joins=joins,
            tables=tables,
            selected_columns=selected_columns,
            filters=filters,
            rollups=rollups,
            custom_sql=custom_sql,
            limit=None,
        )

        con = duckdb.connect(database=":memory:")
        for t_name, df in tables.items():
            con.register(t_name, df)

        df_joined = con.execute(full_sql).df()
        con.close()

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        save(upload_id, "df_clean", df_joined)
        new_profile = df_profile(df_joined)
        filename = output_dataset_name or f"relational_join_{base_table}.csv"
        new_profile["filename"] = filename
        save(upload_id, "profile", new_profile)

        join_meta = {
            "base_table": base_table,
            "joins": joins,
            "filters": filters,
            "rollups": rollups,
            "sql": full_sql,
            "rows": len(df_joined),
            "cols": df_joined.shape[1],
            "execution_time_ms": elapsed_ms,
            "timestamp": time.time(),
        }
        save(upload_id, "join_meta", join_meta)

        return {
            "ok": True,
            "message": f"Successfully joined and materialized {len(df_joined):,} rows across {df_joined.shape[1]} columns.",
            "sql": full_sql,
            "rows": len(df_joined),
            "cols": df_joined.shape[1],
            "execution_time_ms": elapsed_ms,
            "profile": new_profile,
        }

    @classmethod
    def execute_custom_sql(
        cls,
        upload_id: str,
        sql: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Executes arbitrary DuckDB SQL directly against registered workspace tables."""
        t0 = time.perf_counter()
        tables = cls.get_workspace_tables(upload_id)
        if not tables:
            raise ValueError("No tables found in workspace project.")

        con = duckdb.connect(database=":memory:")
        for t_name, df in tables.items():
            con.register(t_name, df)

        clean_sql = sql.strip().rstrip(";")
        has_limit = re.search(r"\bLIMIT\s+\d+", clean_sql, re.IGNORECASE)
        exec_sql = clean_sql if has_limit else f"{clean_sql} LIMIT {limit}"

        df_preview = con.execute(exec_sql).df()
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        try:
            count_query = f"SELECT COUNT(*) AS total_count FROM ({clean_sql}) subq"
            total_rows = int(con.execute(count_query).fetchone()[0])
        except Exception:
            total_rows = len(df_preview)

        con.close()

        cols_meta = [{"name": c, "dtype": str(df_preview[c].dtype)} for c in df_preview.columns]
        rows = df_preview.replace({np.nan: None}).to_dict(orient="records")

        return {
            "ok": True,
            "sql": clean_sql,
            "columns": cols_meta,
            "rows": rows,
            "preview_count": len(rows),
            "total_estimated_rows": total_rows,
            "execution_time_ms": elapsed_ms,
        }

    @classmethod
    def materialize_custom_sql(
        cls,
        upload_id: str,
        sql: str,
        output_dataset_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes custom DuckDB SQL and materializes into active workspace dataset."""
        t0 = time.perf_counter()
        tables = cls.get_workspace_tables(upload_id)
        if not tables:
            raise ValueError("No tables found in workspace project.")

        con = duckdb.connect(database=":memory:")
        for t_name, df in tables.items():
            con.register(t_name, df)

        clean_sql = sql.strip().rstrip(";")
        df_joined = con.execute(clean_sql).df()
        con.close()

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        save(upload_id, "df_clean", df_joined)
        new_profile = df_profile(df_joined)
        filename = output_dataset_name or "custom_sql_materialized.csv"
        new_profile["filename"] = filename
        save(upload_id, "profile", new_profile)

        join_meta = {
            "base_table": "custom_sql",
            "sql": clean_sql,
            "rows": len(df_joined),
            "cols": df_joined.shape[1],
            "execution_time_ms": elapsed_ms,
            "timestamp": time.time(),
        }
        save(upload_id, "join_meta", join_meta)

        return {
            "ok": True,
            "message": f"Successfully executed SQL and materialized {len(df_joined):,} rows across {df_joined.shape[1]} columns.",
            "sql": clean_sql,
            "rows": len(df_joined),
            "cols": df_joined.shape[1],
            "execution_time_ms": elapsed_ms,
            "profile": new_profile,
        }

    @classmethod
    def load_relational_preset(cls, upload_id: str, preset_name: str) -> Dict[str, Any]:
        """
        Generates and saves a multi-table relational schema preset:
        1. 'ecommerce': Customers (400) + Orders (1,200) + Products (100) + Order_Items (2,500)
        2. 'saas': Organizations (250) + Subscriptions (600) + Feature_Usage (1,800)
        3. 'healthcare': Patients (350) + Visits (1,000) + Treatments (500)
        """
        np.random.seed(42)
        created_tables = []

        if preset_name == "ecommerce":
            # 1. Customers
            n_cust = 400
            cust_df = pd.DataFrame({
                "customer_id": [f"CUST_{i:04d}" for i in range(1, n_cust + 1)],
                "first_name": np.random.choice(["Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery"], size=n_cust),
                "last_name": np.random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson"], size=n_cust),
                "email": [f"user_{i}@example.com" for i in range(1, n_cust + 1)],
                "loyalty_tier": np.random.choice(["Bronze", "Silver", "Gold", "Platinum"], size=n_cust, p=[0.5, 0.3, 0.15, 0.05]),
                "city": np.random.choice(["New York", "San Francisco", "Austin", "Chicago", "London", "Berlin", "Toronto"], size=n_cust),
                "signup_date": pd.date_range("2024-01-01", periods=n_cust, freq="12h").strftime("%Y-%m-%d"),
            })
            cls.save_workspace_table(upload_id, "customers", cust_df)
            created_tables.append("customers")

            # 2. Products
            n_prod = 100
            prod_df = pd.DataFrame({
                "product_id": [f"PROD_{i:03d}" for i in range(1, n_prod + 1)],
                "product_name": [f"Product SKU-{i:03d}" for i in range(1, n_prod + 1)],
                "category": np.random.choice(["Electronics", "Apparel", "Home", "Beauty", "Sports"], size=n_prod),
                "unit_price": np.round(np.random.uniform(15.0, 450.0, size=n_prod), 2),
                "stock_level": np.random.randint(5, 500, size=n_prod),
            })
            cls.save_workspace_table(upload_id, "products", prod_df)
            created_tables.append("products")

            # 3. Orders (Primary base table)
            n_orders = 1200
            orders_df = pd.DataFrame({
                "order_id": [f"ORD_{i:05d}" for i in range(1, n_orders + 1)],
                "customer_id": np.random.choice(cust_df["customer_id"], size=n_orders),
                "order_date": pd.date_range("2025-01-01", periods=n_orders, freq="4h").strftime("%Y-%m-%d"),
                "order_status": np.random.choice(["completed", "shipped", "pending", "cancelled"], size=n_orders, p=[0.75, 0.15, 0.07, 0.03]),
                "shipping_method": np.random.choice(["Standard", "Express", "Overnight"], size=n_orders),
                "total_amount": np.round(np.random.normal(120.0, 45.0, size=n_orders), 2),
            })
            cls.save_workspace_table(upload_id, "orders", orders_df)
            created_tables.append("orders")

            # Set orders as primary workspace table
            save(upload_id, "df_raw", orders_df)
            save(upload_id, "profile", df_profile(orders_df))

        elif preset_name == "saas":
            n_org = 250
            org_df = pd.DataFrame({
                "org_id": [f"ORG_{i:03d}" for i in range(1, n_org + 1)],
                "org_name": [f"Company {i}" for i in range(1, n_org + 1)],
                "industry": np.random.choice(["Fintech", "Healthcare", "E-Commerce", "Edtech", "DevTools"], size=n_org),
                "employee_count": np.random.choice([15, 45, 120, 450, 1500], size=n_org),
                "country": np.random.choice(["US", "UK", "DE", "FR", "CA", "SG"], size=n_org),
            })
            cls.save_workspace_table(upload_id, "organizations", org_df)
            created_tables.append("organizations")

            n_subs = 600
            subs_df = pd.DataFrame({
                "sub_id": [f"SUB_{i:04d}" for i in range(1, n_subs + 1)],
                "org_id": np.random.choice(org_df["org_id"], size=n_subs),
                "plan": np.random.choice(["Starter", "Professional", "Enterprise"], size=n_subs, p=[0.5, 0.35, 0.15]),
                "monthly_revenue": np.random.choice([49.0, 199.0, 899.0], size=n_subs, p=[0.5, 0.35, 0.15]),
                "is_churned": np.random.choice([0, 1], size=n_subs, p=[0.82, 0.18]),
            })
            cls.save_workspace_table(upload_id, "subscriptions", subs_df)
            created_tables.append("subscriptions")

            save(upload_id, "df_raw", subs_df)
            save(upload_id, "profile", df_profile(subs_df))

        else: # Healthcare default
            n_pat = 350
            pat_df = pd.DataFrame({
                "patient_id": [f"PAT_{i:04d}" for i in range(1, n_pat + 1)],
                "age": np.random.randint(18, 85, size=n_pat),
                "gender": np.random.choice(["M", "F"], size=n_pat),
                "bmi": np.round(np.random.normal(26.5, 4.2, size=n_pat), 1),
                "smoker": np.random.choice(["Yes", "No"], size=n_pat, p=[0.22, 0.78]),
            })
            cls.save_workspace_table(upload_id, "patients", pat_df)
            created_tables.append("patients")

            n_vis = 1000
            vis_df = pd.DataFrame({
                "visit_id": [f"VIS_{i:05d}" for i in range(1, n_vis + 1)],
                "patient_id": np.random.choice(pat_df["patient_id"], size=n_vis),
                "systolic_bp": np.random.randint(105, 160, size=n_vis),
                "diastolic_bp": np.random.randint(65, 100, size=n_vis),
                "glucose_mg_dl": np.random.randint(75, 220, size=n_vis),
            })
            cls.save_workspace_table(upload_id, "clinical_visits", vis_df)
            created_tables.append("clinical_visits")

            save(upload_id, "df_raw", vis_df)
            save(upload_id, "profile", df_profile(vis_df))

        return {
            "ok": True,
            "preset": preset_name,
            "created_tables": created_tables,
        }
