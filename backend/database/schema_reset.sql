-- ==============================================================================
-- DataForge v3: Complete Database Reset & Migration Schema
-- ==============================================================================
-- Target Supabase Project: gifwhorzaubjysfukykr
-- Direct SQL Editor: https://supabase.com/dashboard/project/gifwhorzaubjysfukykr/sql/new
--
-- Note: This drops all existing tables and rebuilds the authoritative 17-table schema.
-- ==============================================================================

-- 0. CLEANUP (Drop existing tables in dependency order)
DROP TABLE IF EXISTS audit_events CASCADE;
DROP TABLE IF EXISTS usage_records CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS memberships CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS metric_definitions CASCADE;
DROP TABLE IF EXISTS report_schedules CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS insight_records CASCADE;
DROP TABLE IF EXISTS analyses CASCADE;
DROP TABLE IF EXISTS uploads CASCADE;
DROP TABLE IF EXISTS data_sources CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS
CREATE TABLE users (
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

CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_google_id ON users(google_id);
CREATE INDEX ix_users_oauth_sub ON users(oauth_sub);

-- 2. DATA SOURCES
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(32),
    name VARCHAR(256),
    config_json TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    last_sync TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_data_sources_user_id ON data_sources(user_id);

-- 3. UPLOADS
CREATE TABLE uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE INDEX ix_uploads_user_id ON uploads(user_id);

-- 4. ANALYSES
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
    type VARCHAR(64),
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_analyses_user_type ON analyses(user_id, type);
CREATE INDEX ix_analyses_upload_id ON analyses(upload_id);

-- 5. INSIGHT RECORDS
CREATE TABLE insight_records (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
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

CREATE INDEX ix_insight_records_upload ON insight_records(upload_id);
CREATE INDEX ix_insight_records_user_id ON insight_records(user_id);

-- 6. REPORTS
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
    filename VARCHAR(512),
    triggered_by VARCHAR(64) DEFAULT 'manual',
    report_html TEXT,
    report_json TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    storage_path TEXT
);

CREATE INDEX ix_reports_user_id ON reports(user_id);
CREATE INDEX ix_reports_upload_id ON reports(upload_id);

-- 7. ALERTS
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
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

CREATE INDEX ix_alerts_user_id ON alerts(user_id);
CREATE INDEX ix_alerts_upload_id ON alerts(upload_id);

-- 8. REPORT SCHEDULES
CREATE TABLE report_schedules (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
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

CREATE INDEX ix_report_schedules_user_id ON report_schedules(user_id);
CREATE INDEX ix_report_schedules_upload_id ON report_schedules(upload_id);

-- 9. METRIC DEFINITIONS
CREATE TABLE metric_definitions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    formula TEXT NOT NULL,
    description TEXT,
    category VARCHAR(64) DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_metrics_user ON metric_definitions(user_id);

-- 10. JOBS
CREATE TABLE jobs (
    id VARCHAR(64) PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
    type VARCHAR(32),
    status VARCHAR(16) DEFAULT 'queued',
    result_ref TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX ix_jobs_user_status ON jobs(user_id, status);
CREATE INDEX ix_jobs_upload_id ON jobs(upload_id);

-- 11. ORGANIZATIONS (Business Collaboration)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    creator_user_id INT REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(64) DEFAULT 'Enterprise',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_orgs_slug ON organizations(slug);
CREATE INDEX ix_orgs_creator ON organizations(creator_user_id);

-- 12. WORKSPACES (Personal by default, or Org-associated)
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(32) NOT NULL DEFAULT 'personal', -- 'personal' or 'organization'
    owner_user_id INT REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_workspaces_owner ON workspaces(owner_user_id);
CREATE INDEX ix_workspaces_org ON workspaces(org_id);

-- 13. MEMBERSHIPS (Strict 3-Tier RBAC: Admin, Analyst, Viewer)
CREATE TABLE memberships (
    id SERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(64) NOT NULL DEFAULT 'Viewer' CHECK (role IN ('Admin', 'Analyst', 'Viewer')),
    invited_by INT REFERENCES users(id) ON DELETE SET NULL,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

CREATE INDEX ix_memberships_user ON memberships(user_id);
CREATE INDEX ix_memberships_org ON memberships(org_id);

-- 14. PROJECTS (Logical Workspace Containers)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_projects_workspace ON projects(workspace_id);
CREATE INDEX ix_projects_user ON projects(user_id);

-- 15. SUBSCRIPTIONS (Backend-Enforced Entitlements)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(64) NOT NULL DEFAULT 'free', -- 'free', 'pro', 'team', 'enterprise'
    status VARCHAR(64) NOT NULL DEFAULT 'active', -- 'active', 'trialing', 'past_due', 'canceled'
    max_storage_mb INT NOT NULL DEFAULT 250,
    max_rows_per_dataset INT NOT NULL DEFAULT 25000,
    monthly_automl_jobs INT NOT NULL DEFAULT 5,
    monthly_ai_queries INT NOT NULL DEFAULT 25,
    current_period_start TIMESTAMPTZ DEFAULT NOW(),
    current_period_end TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_subscriptions_user ON subscriptions(user_id);

-- 16. USAGE RECORDS (Metered Resource Consumption)
CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    period_month VARCHAR(7) NOT NULL, -- e.g. '2026-10'
    storage_mb_used FLOAT DEFAULT 0.0,
    automl_jobs_count INT DEFAULT 0,
    ai_queries_count INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, period_month)
);

CREATE INDEX ix_usage_user_period ON usage_records(user_id, period_month);

-- 17. AUDIT EVENTS (Enterprise Compliance Trail)
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    ip_address VARCHAR(64),
    details_json TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_audit_user ON audit_events(user_id);
CREATE INDEX ix_audit_org ON audit_events(org_id);
CREATE INDEX ix_audit_created ON audit_events(created_at);
