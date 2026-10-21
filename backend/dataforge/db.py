import os
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import supabase
from supabase import create_client, Client

logger = logging.getLogger(__name__)

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


def _is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    import uuid
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def db_get(table: str, id_val: Any) -> Optional[dict]:
    # Check local project store first for uploads table to avoid remote network latency
    if table == "uploads" and id_val:
        try:
            from dataforge.api.storage.manager import load
            local_meta = load(str(id_val), "meta")
            if local_meta and isinstance(local_meta, dict):
                return local_meta
        except Exception:
            pass
        if not _is_valid_uuid(id_val):
            return None

    if not db_client: return None
    try:
        res = db_client.table(table).select("*").eq("id", id_val).execute()
        return res.data[0] if res.data else None
    except Exception as exc:
        logger.error("Supabase db_get failed (table=%s, id=%s): %s", table, id_val, exc)
        return None

def db_first(table: str, match: dict) -> Optional[dict]:
    if not db_client: return None
    try:
        q = db_client.table(table).select("*")
        for k, v in match.items(): q = q.eq(k, v)
        res = q.limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as exc:
        logger.error("Supabase db_first failed (table=%s, match=%s): %s", table, match, exc)
        return None

def db_all(table: str, match: dict = None, order_by: str = None, desc: bool = True, limit: int = None) -> list[dict]:
    if not db_client: return []
    try:
        q = db_client.table(table).select("*")
        if match:
            for k, v in match.items(): q = q.eq(k, v)
        if order_by:
            q = q.order(order_by, desc=desc)
        if limit:
            q = q.limit(limit)
        return q.execute().data
    except Exception as exc:
        logger.error("Supabase db_all failed (table=%s, match=%s): %s", table, match, exc)
        return []

def db_insert(table: str, data: dict) -> dict:
    if not db_client: return {}
    try:
        res = db_client.table(table).insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as exc:
        logger.error("Supabase db_insert failed (table=%s): %s", table, exc)
        return {}

def db_update(table: str, id_val: Any, data: dict) -> dict:
    if table == "uploads" and id_val:
        try:
            from dataforge.api.storage.manager import load, save
            local_meta = load(str(id_val), "meta") or {}
            if isinstance(local_meta, dict):
                local_meta.update(data)
                save(str(id_val), "meta", local_meta)
        except Exception:
            pass
    if not db_client: return {}
    try:
        supabase_data = dict(data)
        if table == "uploads":
            supabase_data.pop("source_config", None)
        res = db_client.table(table).update(supabase_data).eq("id", id_val).execute()
        return res.data[0] if res.data else {}
    except Exception as exc:
        logger.error("Supabase db_update failed (table=%s, id=%s): %s", table, id_val, exc)
        return {}

def db_delete(table: str, id_val: Any) -> bool:
    if not db_client: return False
    try:
        db_client.table(table).delete().eq("id", id_val).execute()
        return True
    except Exception as exc:
        logger.error("Supabase db_delete failed (table=%s, id=%s): %s", table, id_val, exc)
        return False

def db_count(table: str, match: dict = None) -> int:
    if not db_client: return 0
    try:
        q = db_client.table(table).select("*", count="exact")
        if match:
            for k, v in match.items(): q = q.eq(k, v)
        res = q.limit(0).execute()
        return res.count if res.count is not None else 0
    except Exception as exc:
        logger.error("Supabase db_count failed (table=%s, match=%s): %s", table, match, exc)
        return 0

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
    role: str = "Analyst"

    # For Flask-Login compatibility
    @property
    def is_authenticated(self): return True
    @property
    def is_anonymous(self): return False
    def get_id(self): return str(self.id)


class Job(BaseModel):
    id: str
    user_id: Optional[int] = None
    upload_id: Optional[str] = None
    type: Optional[str] = None
    status: str = "queued"
    result_ref: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    finished_at: Optional[str] = None


class Upload(BaseModel):
    id: str
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
    upload_id: Optional[str] = None
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


class Workspace(BaseModel):
    id: str
    name: str
    type: str = "personal"  # "personal" or "organization"
    owner_user_id: int
    org_id: Optional[str] = None
    created_at: Optional[str] = None


class Organization(BaseModel):
    id: str
    name: str
    slug: str
    creator_user_id: int
    plan: str = "Enterprise"
    created_at: Optional[str] = None


class Membership(BaseModel):
    id: Optional[int] = None
    org_id: str
    user_id: int
    role: str = "Viewer"  # "Admin", "Analyst", "Viewer"
    invited_by: Optional[int] = None
    joined_at: Optional[str] = None


class Project(BaseModel):
    id: str
    workspace_id: str
    user_id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Subscription(BaseModel):
    id: str
    user_id: int
    plan: str = "free"  # "free", "pro", "team", "enterprise"
    status: str = "active"  # "active", "trialing", "past_due", "canceled"
    max_storage_mb: int = 250
    max_rows_per_dataset: int = 25000
    monthly_automl_jobs: int = 5
    monthly_ai_queries: int = 25
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UsageRecord(BaseModel):
    id: str
    user_id: int
    period_month: str  # YYYY-MM
    storage_mb_used: float = 0.0
    automl_jobs_count: int = 0
    ai_queries_count: int = 0
    updated_at: Optional[str] = None


class AuditEvent(BaseModel):
    id: str
    user_id: Optional[int] = None
    org_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    details_json: Optional[str] = None
    created_at: Optional[str] = None


class Procedure(BaseModel):
    id: str
    org_id: Optional[str] = None
    created_by_user_id: int
    name: str
    slug: str
    description: Optional[str] = None
    category: str = "general"
    is_public: bool = False
    active_version_id: Optional[str] = None
    active_version_tag: Optional[str] = "1.0.0"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProcedureVersion(BaseModel):
    id: str
    procedure_id: str
    version_tag: str
    content_hash: str
    definition_json: Dict[str, Any]
    change_log: Optional[str] = None
    golden_tests_json: Optional[List[Dict[str, Any]]] = None
    created_by_user_id: int
    created_at: Optional[str] = None


class ProcedureRun(BaseModel):
    id: str
    procedure_id: str
    version_id: str
    upload_id: Optional[str] = None
    input_snapshot_id: Optional[str] = None
    output_snapshot_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    triggered_by_user_id: int
    runtime_params: Dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"  # PENDING, QUEUED, RUNNING, SUCCESS, FAILED, CANCELLED, TIMED_OUT
    rows_in: int = 0
    rows_out: int = 0
    duration_ms: int = 0
    quality_score: float = 1.0
    lineage_manifest_json: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: Optional[str] = None

