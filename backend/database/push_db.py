"""
push_db.py
──────────
Utility script to push database schema to remote Supabase database.
Accepts database connection string or environment variables.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

def main():
    db_url = os.environ.get("DATABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not db_url:
        print("[!] No direct DATABASE_URL provided.")
        print("    Usage: python push_db.py \"postgresql://postgres:[PASSWORD]@db.gifwhorzaubjysfukykr.supabase.co:5432/postgres\"")
        print("    Or run the schema directly in Supabase SQL Editor:")
        print("    https://supabase.com/dashboard/project/gifwhorzaubjysfukykr/sql/new")
        return

    try:
        import psycopg2
    except ImportError:
        print("[!] Installing psycopg2-binary to execute migration...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2

    sql_path = Path(__file__).parent / "schema_reset.sql"
    sql = sql_path.read_text(encoding="utf-8")
    
    print(f"[*] Connecting to {db_url.split('@')[-1]}...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        print("[*] Executing schema_reset.sql...")
        cur.execute(sql)
    conn.close()
    print("[+] Database successfully reset and pushed with all 17 tables!")

if __name__ == "__main__":
    main()
