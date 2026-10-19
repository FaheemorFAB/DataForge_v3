"""
Database Connector
══════════════════
Pulls a table or SQL query from any SQLAlchemy-compatible database
(PostgreSQL, MySQL, SQLite, BigQuery, Snowflake, etc.) as a pandas DataFrame.

Usage::

    from dataforge.data_sources.db_connector import DBConnector

    conn = DBConnector("postgresql://user:pass@host:5432/mydb")
    df   = conn.query("SELECT * FROM orders WHERE created_at >= NOW() - INTERVAL '7 days'")
    df   = conn.load_table("sales")

    # Test connection
    ok, msg = conn.test()
"""

import os
import logging
from typing import Optional

try:
    from dotenv import load_dotenv
    from dataforge.settings import ROOT_DIR
    load_dotenv(override=False, dotenv_path=ROOT_DIR / ".env")
except Exception:
    pass

import pandas as pd

log = logging.getLogger(__name__)

# Supported engines and friendly names
SUPPORTED_DIALECTS = {
    "supabase":   "Supabase (PostgreSQL)",
    "postgresql": "PostgreSQL",
    "mysql":      "MySQL",
    "sqlite":     "SQLite",
    "mssql":      "SQL Server",
    "bigquery":   "BigQuery",
    "snowflake":  "Snowflake",
    "clickhouse": "ClickHouse",
    "neon":       "Neon (PostgreSQL)",
}


class DBConnector:

    def __init__(self, connection_string: str):
        """
        connection_string examples:
          postgresql://postgres:pass@db.ref.supabase.co:5432/postgres
          mysql+pymysql://admin:pass@mysql.us-east-1.rds.amazonaws.com:3306/dbname
          clickhouse+native://default:pass@service.clickhouse.cloud:9440/default
        """
        self.connection_string = connection_string
        self._engine = None

    # ── Engine ────────────────────────────────────────────────────────────────
    def _get_engine(self):
        if self._engine:
            return self._engine
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.engine import make_url
        except ImportError:
            raise RuntimeError("sqlalchemy not installed. Run: pip install sqlalchemy")

        from dataforge.api.utils.ssrf import validate_and_resolve_host, SSRFSecurityError

        # Register pymysql as default MySQL driver if mysqlclient is absent
        try:
            import pymysql
            pymysql.install_as_MySQLdb()
        except Exception:
            pass

        conn_str = self.connection_string.strip()
        if conn_str.startswith("supabase://"):
            conn_str = "postgresql://" + conn_str[len("supabase://"):]
        elif conn_str.startswith("mysql://"):
            conn_str = "mysql+pymysql://" + conn_str[len("mysql://"):]
        elif conn_str.startswith("clickhouse://"):
            conn_str = "clickhouse+native://" + conn_str[len("clickhouse://"):]

        try:
            url = make_url(conn_str)
        except Exception as e:
            raise ValueError(f"Invalid connection string format: {e}")

        # Strip accidental placeholder brackets e.g. [my-password] or [postgres] copied from docs
        if url.password and url.password.startswith("[") and url.password.endswith("]"):
            url = url.set(password=url.password[1:-1])
        if url.username and url.username.startswith("[") and url.username.endswith("]"):
            url = url.set(username=url.username[1:-1])
        if url.database and url.database.startswith("[") and url.database.endswith("]"):
            url = url.set(database=url.database[1:-1])

        # 1. Strictly forbid file-backed/local dialects (e.g. SQLite, local DuckDB)
        backend = (url.drivername or "").split("+")[0].lower()
        if backend in ("sqlite", "duckdb", "") or not url.host:
            raise ValueError(
                f"Database dialect '{backend or 'unknown'}' or local file storage is prohibited. "
                "Only remote network database services (PostgreSQL, MySQL, Snowflake, BigQuery, etc.) are permitted."
            )

        # 2. Prevent query-parameter bypasses (e.g. ?host=/var/run/postgresql, ?sslkey=/etc/passwd)
        ALLOWED_QUERY_PARAMS = {
            "sslmode", "connect_timeout", "application_name", "charset",
            "secure", "compression", "database", "client_encoding"
        }
        for param_key in url.query:
            if param_key.lower() not in ALLOWED_QUERY_PARAMS:
                raise ValueError(
                    f"Prohibited database connection parameter '{param_key}'. "
                    f"Allowed parameters: {sorted(ALLOWED_QUERY_PARAMS)}"
                )

        # Auto-enable sslmode=require for cloud-hosted databases (Supabase, Neon, etc.) if omitted
        if url.host and any(cloud in url.host.lower() for cloud in ("supabase", "neon.tech", "render.com", "railway.app", "pooler")):
            if "sslmode" not in url.query:
                query_dict = dict(url.query)
                query_dict["sslmode"] = "require"
                url = url.set(query=query_dict)

        # 3. SSRF / Private IP protection & DNS Rebinding Elimination
        allow_local = (
            os.getenv("ALLOW_LOCAL_DATABASE", "false").lower() in ("true", "1", "yes")
            or os.getenv("ALLOW_LOCAL_DB", "false").lower() in ("true", "1", "yes")
        )
        if url.port:
            port = url.port
        elif "mysql" in backend:
            port = 3306
        elif "clickhouse" in backend:
            port = 8123 if "http" in (url.drivername or "") else 9000
        else:
            port = 5432

        try:
            pinned_ip = validate_and_resolve_host(url.host, port, allow_local=allow_local)
        except SSRFSecurityError as sec_err:
            raise ValueError(f"Database connection prohibited for security: {sec_err}")

        # For SSL/SNI compatibility with cloud databases (e.g. Supabase certificate checks),
        # keep the validated hostname in the URL while connecting with pre-ping and timeout
        connect_args = {"connect_timeout": 10} if any(k in backend for k in ("postgres", "mysql", "clickhouse")) else {}
        try:
            self._engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
            return self._engine
        except ImportError as imp_err:
            raise RuntimeError(f"Database driver for '{backend}' is missing: {imp_err}")

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
        engine = self._get_engine()
        quote_fn = getattr(engine.dialect.identifier_preparer, "quote_identifier", lambda s: f'"{s}"')

        safe_table = table_name.replace('"', "").replace("`", "").replace(";", "")
        quoted_table = quote_fn(safe_table)

        if schema:
            safe_schema = schema.replace('"', "").replace("`", "").replace(";", "")
            full_table = f"{quote_fn(safe_schema)}.{quoted_table}"
        else:
            full_table = quoted_table

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
