-- DataForge v3 Native Supabase Schema
-- Run this in your Supabase SQL Editor to map the previous SQLAlchemy models

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar TEXT,
    google_id VARCHAR(255) UNIQUE,
    oauth_provider VARCHAR(64) DEFAULT 'google',
    oauth_sub VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    storage_quota_mb INT DEFAULT 5120
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS ix_users_oauth_sub ON users(oauth_sub);

-- 2. DATA SOURCES
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(32),
    name VARCHAR(256),
    config_json TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    last_sync TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_data_sources_user_id ON data_sources(user_id);

-- 3. UPLOADS
CREATE TABLE IF NOT EXISTS uploads (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(512),
    original_name VARCHAR(512),
    rows INT,
    cols INT,
    missing_pct FLOAT DEFAULT 0.0,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    chat_history TEXT,
    clean_meta_json TEXT,
    automl_meta_json TEXT,
    source_type VARCHAR(64) DEFAULT 'csv',
    source_id INT,
    storage_path TEXT
);

CREATE INDEX IF NOT EXISTS ix_uploads_user_id ON uploads(user_id);

-- 4. ANALYSES
CREATE TABLE IF NOT EXISTS analyses (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id INT REFERENCES uploads(id) ON DELETE CASCADE,
    type VARCHAR(64),
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analyses_user_type ON analyses(user_id, type);
CREATE INDEX IF NOT EXISTS ix_analyses_upload_id ON analyses(upload_id);

-- 5. INSIGHT RECORDS
CREATE TABLE IF NOT EXISTS insight_records (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id INT REFERENCES uploads(id) ON DELETE CASCADE,
    type VARCHAR(64),
    title VARCHAR(512),
    description TEXT,
    importance FLOAT DEFAULT 0.0,
    chart_type VARCHAR(32),
    metric VARCHAR(256),
    chart_data TEXT,
    insight_json TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_insight_records_upload ON insight_records(upload_id);
CREATE INDEX IF NOT EXISTS ix_insight_records_user_id ON insight_records(user_id);

-- 6. REPORTS
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id INT REFERENCES uploads(id) ON DELETE CASCADE,
    filename VARCHAR(512),
    triggered_by VARCHAR(64) DEFAULT 'manual',
    report_html TEXT,
    report_json TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    storage_path TEXT
);

CREATE INDEX IF NOT EXISTS ix_reports_user_id ON reports(user_id);
CREATE INDEX IF NOT EXISTS ix_reports_upload_id ON reports(upload_id);

-- 7. ALERTS
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id INT REFERENCES uploads(id) ON DELETE CASCADE,
    filename VARCHAR(512),
    severity VARCHAR(32) DEFAULT 'warning',
    rule VARCHAR(64),
    message TEXT,
    colour VARCHAR(16) DEFAULT '#f59e0b',
    metric VARCHAR(256),
    pct_change FLOAT,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    triggered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS ix_alerts_upload_id ON alerts(upload_id);

-- 8. REPORT SCHEDULES
CREATE TABLE IF NOT EXISTS report_schedules (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id INT REFERENCES uploads(id) ON DELETE CASCADE,
    cron_expression VARCHAR(64),
    cron VARCHAR(64),
    cron_human VARCHAR(128),
    email VARCHAR(255),
    slack_webhook VARCHAR(512),
    enabled BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    last_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_report_schedules_user_id ON report_schedules(user_id);
CREATE INDEX IF NOT EXISTS ix_report_schedules_upload_id ON report_schedules(upload_id);

-- 9. METRIC DEFINITIONS
CREATE TABLE IF NOT EXISTS metric_definitions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    formula TEXT NOT NULL,
    description TEXT,
    category VARCHAR(64) DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_metrics_user ON metric_definitions(user_id);

-- 10. JOBS
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(64) PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id INT REFERENCES uploads(id) ON DELETE CASCADE,
    type VARCHAR(32),
    status VARCHAR(16) DEFAULT 'queued',
    result_ref TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_jobs_user_status ON jobs(user_id, status);
CREATE INDEX IF NOT EXISTS ix_jobs_upload_id ON jobs(upload_id);
