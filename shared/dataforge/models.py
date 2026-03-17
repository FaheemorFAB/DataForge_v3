"""
shared/dataforge/models.py  ── Complete fixed version
=============================================
Root causes fixed
─────────────────
FIX 1  Report.report_json column was missing from the ORM model.
       SQLAlchemy 2.x raises TypeError on unknown constructor kwargs, so
       every api_report_generate() call crashed silently → report_id=null
       → blank iframe in the workspace.

FIX 2  Report was missing its `upload` backref, so api_reports_list()
       always fell through to the AttributeError except-branch and
       returned an empty filename → every row showed "—" in the table.

FIX 3  InsightRecord was missing type / title / description / importance /
       chart_type / metric / chart_data columns.  _persist_insights() was
       therefore silently discarding every insight on every save.

FIX 4  Alert was missing metric / pct_change / resolved_at / colour, and
       lacked the severity_colour property referenced in reporting routes.

FIX 5  ReportSchedule was missing cron_expression / slack_webhook /
       last_run_at, and lacked the upload backref + cron_human property.

FIX 6  User was missing google_id (used by OAuth callback) and the
       total_uploads / total_analyses / total_models / total_queries
       properties used by the dashboard route.

FIX 7  Upload was missing missing_pct (used by _db_log_upload).

FIX 8  Analysis was missing upload_id / summary and used the wrong type
       (SAEnum vs plain String), breaking the dashboard activity feed.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float,
    ForeignKey, Boolean, Index,
)
from sqlalchemy.orm import relationship

db = SQLAlchemy()


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True)
    email            = Column(String(255), unique=True, nullable=False, index=True)
    name             = Column(String(255))
    avatar           = Column(Text)
    # FIX 6: google_id kept for the OAuth callback query filter
    google_id        = Column(String(255), unique=True, index=True)
    oauth_provider   = Column(String(64),  default="google")
    oauth_sub        = Column(String(255), unique=True, index=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    last_login       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active        = Column(Boolean, default=True)
    storage_quota_mb = Column(Integer, default=5120)

    # Relationships to legacy tables
    uploads   = relationship("Upload",   backref="user",   lazy="dynamic",
                             foreign_keys="Upload.user_id")
    analyses  = relationship("Analysis", backref="user",   lazy="dynamic",
                             foreign_keys="Analysis.user_id")
    reports   = relationship("Report",   backref="user",   lazy="dynamic",
                             foreign_keys="Report.user_id")
    alerts    = relationship("Alert",    backref="user",   lazy="dynamic",
                             foreign_keys="Alert.user_id")

    def __repr__(self):
        return f"<User {self.email}>"

    # FIX 6: dashboard stat properties
    @property
    def total_uploads(self) -> int:
        return Upload.query.filter_by(user_id=self.id).count()

    @property
    def total_analyses(self) -> int:
        return Analysis.query.filter_by(user_id=self.id).count()

    @property
    def total_models(self) -> int:
        return Analysis.query.filter_by(user_id=self.id, type="automl").count()

    @property
    def total_queries(self) -> int:
        return Analysis.query.filter_by(user_id=self.id, type="query").count()


# ══════════════════════════════════════════════════════════════════════════════
# UPLOADS  (legacy session-based records)
# ══════════════════════════════════════════════════════════════════════════════

class Upload(db.Model):
    __tablename__ = "uploads"

    id               = Column(Integer, primary_key=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    filename         = Column(String(512))
    original_name    = Column(String(512))
    rows             = Column(Integer)
    cols             = Column(Integer)
    # FIX 7: missing_pct was not in the original model
    missing_pct      = Column(Float, default=0.0)
    uploaded_at      = Column(DateTime, default=datetime.utcnow)
    chat_history     = Column(Text)
    clean_meta_json  = Column(Text)
    automl_meta_json = Column(Text)
    source_type      = Column(String(64), default="csv")
    source_id        = Column(Integer)
    # Supabase Storage path for the raw CSV
    storage_path     = Column(Text)

    # Relationships — FIX 2 / FIX 4 / FIX 5
    upload_analyses  = relationship("Analysis",      backref="upload",
                                    lazy="dynamic",  foreign_keys="Analysis.upload_id")
    upload_reports   = relationship("Report",        backref="upload",
                                    lazy="dynamic",  foreign_keys="Report.upload_id")
    upload_alerts    = relationship("Alert",         backref="upload",
                                    lazy="dynamic",  foreign_keys="Alert.upload_id")
    upload_schedules = relationship("ReportSchedule", backref="upload",
                                    lazy="dynamic",  foreign_keys="ReportSchedule.upload_id")
    insight_records  = relationship("InsightRecord", backref="upload",
                                    lazy="dynamic",  foreign_keys="InsightRecord.upload_id")


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS  (activity log)
# ══════════════════════════════════════════════════════════════════════════════

class Analysis(db.Model):
    # FIX 8: type must be plain String (not Enum) so _db_log_analysis("eda", ...) works.
    __tablename__ = "analyses"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"),   nullable=True, index=True)
    # FIX 8: upload_id FK (not dataset_id)
    upload_id  = Column(Integer, ForeignKey("uploads.id"), nullable=True, index=True)
    type       = Column(String(64))          # "eda" | "automl" | "clean" | "query" | "insights" | "report"
    summary    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_analyses_user_type", "user_id", "type"),
    )

    @property
    def label(self) -> str:
        """Human-readable label used in the dashboard activity feed."""
        _map = {
            "eda":      "EDA Report",
            "automl":   "AutoML Training",
            "clean":    "Data Cleaning",
            "query":    "AI Query",
            "insights": "Insights",
            "report":   "Report Generated",
        }
        return _map.get(self.type or "", (self.type or "Analysis").title())


# ══════════════════════════════════════════════════════════════════════════════
# INSIGHT RECORDS
# ══════════════════════════════════════════════════════════════════════════════

class InsightRecord(db.Model):
    # FIX 3: added all columns used by _persist_insights() and api_insights_list()
    __tablename__ = "insight_records"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"),   nullable=True, index=True)
    upload_id   = Column(Integer, ForeignKey("uploads.id"), nullable=True, index=True)
    type        = Column(String(64))
    title       = Column(String(512))
    description = Column(Text)
    importance  = Column(Float, default=0.0)
    chart_type  = Column(String(32))
    metric      = Column(String(256))
    chart_data  = Column(Text)        # JSON string
    insight_json = Column(Text)       # legacy field — kept for backward compat
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_insight_records_upload", "upload_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════

class Report(db.Model):
    __tablename__ = "reports"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"),   nullable=True, index=True)
    # FIX 2: upload_id backref is defined on Upload above → r.upload works
    upload_id    = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    filename     = Column(String(512))         # denormalised fallback
    triggered_by = Column(String(64), default="manual")
    report_html  = Column(Text)
    # FIX 1: report_json was the primary missing column causing the 500 / null report_id
    report_json  = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)
    # Supabase Storage path (optional — for large reports stored externally)
    storage_path = Column(Text)


# ══════════════════════════════════════════════════════════════════════════════
# ALERTS
# ══════════════════════════════════════════════════════════════════════════════

class Alert(db.Model):
    # FIX 4: metric / pct_change / resolved_at / colour added as proper columns
    __tablename__ = "alerts"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"),   nullable=True, index=True)
    # FIX 4: upload_id backref defined on Upload → a.upload works
    upload_id    = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    filename     = Column(String(512))
    severity     = Column(String(32), default="warning")
    rule         = Column(String(64))
    message      = Column(Text)
    colour       = Column(String(16), default="#f59e0b")
    metric       = Column(String(256))
    pct_change   = Column(Float)
    resolved     = Column(Boolean, default=False)
    resolved_at  = Column(DateTime)
    triggered_at = Column(DateTime, default=datetime.utcnow)

    @property
    def severity_colour(self) -> str:
        """CSS colour for the alert badge used in reporting routes."""
        _map = {
            "critical": "#EF4444",
            "warning":  "#F59E0B",
            "info":     "#3B82F6",
        }
        return _map.get(self.severity or "warning", self.colour or "#F59E0B")


# ══════════════════════════════════════════════════════════════════════════════
# REPORT SCHEDULES
# ══════════════════════════════════════════════════════════════════════════════

class ReportSchedule(db.Model):
    # FIX 5: cron_expression / slack_webhook / last_run_at added as proper columns
    __tablename__ = "report_schedules"

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id"),   nullable=True, index=True)
    # FIX 5: upload_id backref defined on Upload → s.upload works
    upload_id       = Column(Integer, ForeignKey("uploads.id"), nullable=True)
    cron_expression = Column(String(64))
    cron            = Column(String(64))          # legacy alias kept for compat
    cron_human      = Column(String(128))
    email           = Column(String(255))
    slack_webhook   = Column(String(512))
    enabled         = Column(Boolean, default=True)
    last_run_at     = Column(DateTime)
    last_run        = Column(DateTime)            # legacy alias kept for compat
    created_at      = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        # Mirror cron / last_run aliases on construction
        if "cron_expression" in kwargs and "cron" not in kwargs:
            kwargs["cron"] = kwargs["cron_expression"]
        super().__init__(**kwargs)

    @property
    def cron_human_text(self) -> str:
        """Return stored cron_human or derive a simple label from the expression."""
        if self.cron_human:
            return self.cron_human
        expr = self.cron_expression or self.cron or ""
        _presets = {
            "0 9 * * 1": "Every Monday at 09:00 UTC",
            "0 9 * * *": "Every day at 09:00 UTC",
            "0 9 1 * *": "First of every month at 09:00 UTC",
        }
        return _presets.get(expr, expr)


# ══════════════════════════════════════════════════════════════════════════════
# DATA SOURCES
# ══════════════════════════════════════════════════════════════════════════════

class DataSource(db.Model):
    __tablename__ = "data_sources"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    source_type = Column(String(32))    # "google_sheets" | "url" | "db" | "api"
    name        = Column(String(256))
    config_json = Column(Text)
    enabled     = Column(Boolean, default=True)
    last_sync   = Column(DateTime)
    created_at  = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# METRIC DEFINITIONS  (semantic layer — used in AI Query context)
# ══════════════════════════════════════════════════════════════════════════════

class MetricDefinition(db.Model):
    """User-defined business metric formulas (e.g. Revenue = price * units)."""
    __tablename__ = "metric_definitions"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name        = Column(String(256), nullable=False)
    formula     = Column(Text, nullable=False)     # e.g. "price * units"
    description = Column(Text)                     # optional human note
    category    = Column(String(64), default="general")
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_metrics_user", "user_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "name":        self.name,
            "formula":     self.formula,
            "description": self.description or "",
            "category":    self.category or "general",
            "created_at":  self.created_at.isoformat() if self.created_at else "",
            "updated_at":  self.updated_at.isoformat() if self.updated_at else "",
        }