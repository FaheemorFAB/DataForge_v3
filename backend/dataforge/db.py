import os
import threading
import time
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import supabase
from supabase import create_client, Client

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CLIENT INSTANCE
# ══════════════════════════════════════════════════════════════════════════════

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    # Accept either env var name (older docs used SUPABASE_KEY).
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) must be set in .env")
    return create_client(url, key)

# Cached instance
try:
    db_client = get_supabase_client()
except RuntimeError:
    db_client = None  # Expected during some blind local imports before .env loads

_db_lock = threading.RLock()


def _execute(query, retries: int = 3):
    """Run Supabase/PostgREST calls defensively.

    The Supabase client keeps an HTTP connection pool. Under the threaded Flask
    dev server, concurrent requests can occasionally trip httpx/httpcore HTTP/2
    stream errors. Serializing these small metadata queries and retrying once or
    twice keeps dashboard widgets from failing because one background request
    raced another.
    """
    last_exc = None
    for attempt in range(retries):
        try:
            with _db_lock:
                return query.execute()
        except Exception as exc:
            last_exc = exc
            if attempt == retries - 1:
                raise
            time.sleep(0.2 * (attempt + 1))
    raise last_exc


def db_get(table: str, id_val: Any) -> Optional[dict]:
    if not db_client: return None
    res = _execute(db_client.table(table).select("*").eq("id", id_val))
    return res.data[0] if res.data else None

def db_first(table: str, match: dict) -> Optional[dict]:
    if not db_client: return None
    q = db_client.table(table).select("*")
    for k, v in match.items(): q = q.eq(k, v)
    res = _execute(q.limit(1))
    return res.data[0] if res.data else None

def db_all(table: str, match: dict = None, order_by: str = None, desc: bool = True, limit: int = None) -> list[dict]:
    if not db_client: return []
    q = db_client.table(table).select("*")
    if match:
        for k, v in match.items(): q = q.eq(k, v)
    if order_by:
        q = q.order(order_by, desc=desc)
    if limit:
        q = q.limit(limit)
    return _execute(q).data

def db_insert(table: str, data: dict) -> dict:
    if not db_client: return {}
    return _execute(db_client.table(table).insert(data)).data[0]

def db_update(table: str, id_val: Any, data: dict) -> dict:
    if not db_client: return {}
    return _execute(db_client.table(table).update(data).eq("id", id_val)).data[0]

def db_delete(table: str, id_val: Any) -> bool:
    if not db_client: return False
    _execute(db_client.table(table).delete().eq("id", id_val))
    return True

def db_count(table: str, match: dict = None) -> int:
    if not db_client: return 0
    q = db_client.table(table).select("*", count="exact")
    if match:
        for k, v in match.items(): q = q.eq(k, v)
    res = _execute(q.limit(0))
    return res.count if res.count is not None else 0

# ══════════════════════════════════════════════════════════════════════════════
# DATACLASSES / PYDANTIC MODELS (Replacing SQLAlchemy Models)
# ══════════════════════════════════════════════════════════════════════════════

class User(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    google_id: Optional[str] = None
    oauth_provider: str = "google"
    oauth_sub: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    is_active: bool = True
    storage_quota_mb: int = 5120

    # For Flask-Login compatibility
    @property
    def is_authenticated(self): return True
    @property
    def is_anonymous(self): return False
    def get_id(self): return str(self.id)


class Job(BaseModel):
    id: str
    user_id: Optional[int] = None
    upload_id: Optional[int] = None
    type: Optional[str] = None
    status: str = "queued"
    result_ref: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    finished_at: Optional[str] = None


class Upload(BaseModel):
    id: int
    user_id: Optional[int] = None
    filename: Optional[str] = None
    original_name: Optional[str] = None
    rows: Optional[int] = None
    cols: Optional[int] = None
    missing_pct: float = 0.0
    uploaded_at: Optional[str] = None
    chat_history: Optional[str] = None
    clean_meta_json: Optional[str] = None
    automl_meta_json: Optional[str] = None
    source_type: str = "csv"
    source_id: Optional[int] = None
    storage_path: Optional[str] = None


class ReportSchedule(BaseModel):
    id: int
    user_id: Optional[int] = None
    upload_id: Optional[int] = None
    cron_expression: Optional[str] = None
    cron: Optional[str] = None
    cron_human: Optional[str] = None
    email: Optional[str] = None
    slack_webhook: Optional[str] = None
    enabled: bool = True
    last_run_at: Optional[str] = None
    last_run: Optional[str] = None
    created_at: Optional[str] = None

    @property
    def cron_human_text(self) -> str:
        if self.cron_human:
            return self.cron_human
        expr = self.cron_expression or self.cron or ""
        _presets = {
            "0 9 * * 1": "Every Monday at 09:00 UTC",
            "0 9 * * *": "Every day at 09:00 UTC",
            "0 9 1 * *": "First of every month at 09:00 UTC",
        }
        return _presets.get(expr, expr)


class MetricDefinition(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    formula: str
    description: Optional[str] = None
    category: str = "general"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
