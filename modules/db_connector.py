"""
Database Connector
══════════════════
Pulls a table or SQL query from any SQLAlchemy-compatible database
(PostgreSQL, MySQL, SQLite, BigQuery, Snowflake, etc.) as a pandas DataFrame.

Usage::

    from modules.data_sources.db_connector import DBConnector

    conn = DBConnector("postgresql://user:pass@host:5432/mydb")
    df   = conn.query("SELECT * FROM orders WHERE created_at >= NOW() - INTERVAL '7 days'")
    df   = conn.load_table("sales")

    # Test connection
    ok, msg = conn.test()
"""

import logging
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

# Supported engines and friendly names
SUPPORTED_DIALECTS = {
    "postgresql": "PostgreSQL",
    "mysql":      "MySQL",
    "sqlite":     "SQLite",
    "mssql":      "SQL Server",
    "bigquery":   "BigQuery",
    "snowflake":  "Snowflake",
}


class DBConnector:

    def __init__(self, connection_string: str):
        """
        connection_string examples:
          postgresql://user:pass@localhost:5432/dbname
          mysql+pymysql://user:pass@host/dbname
          sqlite:///path/to/file.db
        """
        self.connection_string = connection_string
        self._engine = None

    # ── Engine ────────────────────────────────────────────────────────────────
    def _get_engine(self):
        if self._engine:
            return self._engine
        try:
            from sqlalchemy import create_engine
            self._engine = create_engine(self.connection_string, pool_pre_ping=True)
            return self._engine
        except ImportError:
            raise RuntimeError("sqlalchemy not installed. Run: pip install sqlalchemy")

    # ── Connection test ───────────────────────────────────────────────────────
    def test(self) -> tuple[bool, str]:
        """Returns (True, 'OK') or (False, error_message)."""
        try:
            engine = self._get_engine()
            with engine.connect() as conn:
                conn.execute(engine.dialect.has_table.__doc__ and None or
                             __import__("sqlalchemy").text("SELECT 1"))
            return True, "Connection successful"
        except Exception as exc:
            return False, str(exc)

    # ── Data loading ──────────────────────────────────────────────────────────
    def query(self, sql: str, params: dict | None = None, chunksize: int | None = None) -> pd.DataFrame:
        """
        Execute an arbitrary SQL SELECT and return a DataFrame.
        Pass params dict for parameterised queries.
        """
        engine = self._get_engine()
        log.info("DBConnector: executing query (first 120 chars): %s", sql[:120])
        df = pd.read_sql(sql, engine, params=params, chunksize=chunksize)
        if chunksize:
            # Materialise chunks
            df = pd.concat(list(df), ignore_index=True)
        log.info("DBConnector: loaded %d rows × %d cols", *df.shape)
        return df

    def load_table(
        self,
        table_name: str,
        schema: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Load an entire table (optionally limited by row count)."""
        safe_table  = table_name.replace('"', "").replace(";", "")
        safe_schema = (schema or "").replace('"', "").replace(";", "")

        if safe_schema:
            full_table = f'"{safe_schema}"."{safe_table}"'
        else:
            full_table = f'"{safe_table}"'

        sql = f"SELECT * FROM {full_table}"
        if limit:
            sql += f" LIMIT {int(limit)}"

        return self.query(sql)

    def list_tables(self, schema: str | None = None) -> list[str]:
        """Return all table names in the connected database."""
        from sqlalchemy import inspect
        engine  = self._get_engine()
        insp    = inspect(engine)
        return insp.get_table_names(schema=schema)

    def get_columns(self, table_name: str, schema: str | None = None) -> list[dict]:
        """Return column names and types for a table."""
        from sqlalchemy import inspect
        engine = self._get_engine()
        insp   = inspect(engine)
        return [
            {"name": c["name"], "type": str(c["type"])}
            for c in insp.get_columns(table_name, schema=schema)
        ]

    def close(self):
        if self._engine:
            self._engine.dispose()
            self._engine = None
