"""
migrate_db.py  ── Updated migration (run once from project root)
================================================================
Adds every column that the fixed models.py expects but may be absent
from an existing dataforge.db created by an older version.

Run:
    python migrate_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "instance" / "dataforge.db"

# ── Schema additions ──────────────────────────────────────────────────────────
# Format: (table, column_definition)
# Each entry is attempted independently; duplicates are silently skipped.

MIGRATIONS = [
    # users table
    ("users", "ADD COLUMN google_id        VARCHAR(255)"),
    ("users", "ADD COLUMN oauth_provider   VARCHAR(64)  DEFAULT 'google'"),
    ("users", "ADD COLUMN oauth_sub        VARCHAR(255)"),
    ("users", "ADD COLUMN is_active        BOOLEAN      DEFAULT 1"),
    ("users", "ADD COLUMN storage_quota_mb INTEGER      DEFAULT 5120"),

    # uploads table
    ("uploads", "ADD COLUMN missing_pct      REAL    DEFAULT 0.0"),
    ("uploads", "ADD COLUMN chat_history     TEXT"),
    ("uploads", "ADD COLUMN clean_meta_json  TEXT"),
    ("uploads", "ADD COLUMN automl_meta_json TEXT"),
    ("uploads", "ADD COLUMN source_type      TEXT    DEFAULT 'csv'"),
    ("uploads", "ADD COLUMN source_id        INTEGER"),
    ("uploads", "ADD COLUMN storage_path     TEXT"),

    # analyses table
    ("analyses", "ADD COLUMN upload_id  INTEGER"),
    ("analyses", "ADD COLUMN summary    TEXT"),

    # insight_records table  (FIX 3)
    ("insight_records", "ADD COLUMN type         TEXT"),
    ("insight_records", "ADD COLUMN title        TEXT"),
    ("insight_records", "ADD COLUMN description  TEXT"),
    ("insight_records", "ADD COLUMN importance   REAL    DEFAULT 0.0"),
    ("insight_records", "ADD COLUMN chart_type   TEXT"),
    ("insight_records", "ADD COLUMN metric       TEXT"),
    ("insight_records", "ADD COLUMN chart_data   TEXT"),

    # reports table  (FIX 1 + FIX 2)
    ("reports", "ADD COLUMN filename     TEXT"),
    ("reports", "ADD COLUMN report_json  TEXT"),
    ("reports", "ADD COLUMN storage_path TEXT"),

    # alerts table  (FIX 4)
    ("alerts", "ADD COLUMN filename     TEXT"),
    ("alerts", "ADD COLUMN colour       TEXT    DEFAULT '#f59e0b'"),
    ("alerts", "ADD COLUMN metric       TEXT"),
    ("alerts", "ADD COLUMN pct_change   REAL"),
    ("alerts", "ADD COLUMN resolved_at  DATETIME"),
    ("alerts", "ADD COLUMN resolved     BOOLEAN DEFAULT 0"),

    # report_schedules table  (FIX 5)
    ("report_schedules", "ADD COLUMN cron             TEXT"),
    ("report_schedules", "ADD COLUMN cron_expression  TEXT"),
    ("report_schedules", "ADD COLUMN cron_human       TEXT"),
    ("report_schedules", "ADD COLUMN email            TEXT"),
    ("report_schedules", "ADD COLUMN slack_webhook    TEXT"),
    ("report_schedules", "ADD COLUMN last_run         DATETIME"),
    ("report_schedules", "ADD COLUMN last_run_at      DATETIME"),
    ("report_schedules", "ADD COLUMN created_at       DATETIME"),

    # data_sources table
    ("data_sources", "ADD COLUMN enabled    BOOLEAN DEFAULT 1"),
    ("data_sources", "ADD COLUMN last_sync  DATETIME"),
    ("data_sources", "ADD COLUMN created_at DATETIME"),
]

# ── Back-fill existing google_id into oauth_sub ───────────────────────────────
BACKFILL_OAUTH_SUB = """
    UPDATE users
    SET oauth_provider = 'google',
        oauth_sub      = google_id,
        is_active      = 1
    WHERE oauth_sub IS NULL AND google_id IS NOT NULL
"""

# ── Back-fill cron_expression from cron ───────────────────────────────────────
BACKFILL_CRON = """
    UPDATE report_schedules
    SET cron_expression = cron
    WHERE cron_expression IS NULL AND cron IS NOT NULL
"""


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def run():
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found at {DB_PATH}")
        print("        Start the Flask app once first so SQLAlchemy can create the tables.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    for table, col_def in MIGRATIONS:
        if not _table_exists(cur, table):
            print(f"[SKIP] Table '{table}' does not exist yet — skipped.")
            continue
        col_name = col_def.split()[2]   # "ADD COLUMN <name> ..."
        sql = f"ALTER TABLE {table} {col_def}"
        try:
            cur.execute(sql)
            print(f"[OK]   {table}.{col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"[SKIP] {table}.{col_name} already exists")
            else:
                print(f"[WARN] {table}.{col_name}: {e}")

    # Back-fills
    for label, sql in [
        ("oauth_sub back-fill",     BACKFILL_OAUTH_SUB),
        ("cron_expression back-fill", BACKFILL_CRON),
    ]:
        try:
            cur.execute(sql)
            print(f"[OK]   {label} — {cur.rowcount} rows updated")
        except Exception as e:
            print(f"[WARN] {label}: {e}")

    conn.commit()
    conn.close()
    print("\nMigration complete. Restart your Flask app.")


if __name__ == "__main__":
    run()
