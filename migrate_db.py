"""
Entry point shim.
The migration script now lives in services/web/migrate_db.py.
"""

from services.web.migrate_db import run


if __name__ == "__main__":
    run()
