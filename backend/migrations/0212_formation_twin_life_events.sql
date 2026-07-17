-- Formation Twin Batch 2: immutable, provenance-rich life events.
-- Existing email/session auth remains the user source of truth.

CREATE TABLE IF NOT EXISTS formation_twin_sensitive_contents (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    email TEXT NOT NULL,
    content_type VARCHAR(40) NOT NULL,
    nonce BYTEA NOT NULL,
    encrypted_content BYTEA NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    encryption_key_version VARCHAR(40) NOT NULL,
    retention_policy VARCHAR(40) NOT NULL DEFAULT 'UNTIL_USER_DELETES',
    processing_preference VARCHAR(40) NOT NULL DEFAULT 'STORE_ONLY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_sensitive_owner ON formation_twin_sensitive_contents(email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_life_events (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    email TEXT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_subtype VARCHAR(80),
    event_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    original_timezone VARCHAR(80) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_module VARCHAR(80) NOT NULL,
    source_record_id VARCHAR(160),
    source_event_id VARCHAR(160),
    client_event_id VARCHAR(160),
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    self_report_json JSONB,
    behavioral_facts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    spiritual_practice_facts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    relationship_facts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_reference_id UUID REFERENCES formation_twin_sensitive_contents(id),
    safety_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    consent_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_classification VARCHAR(30) NOT NULL DEFAULT 'HIGHLY_SENSITIVE',
    processing_preference VARCHAR(40) NOT NULL DEFAULT 'STORE_ONLY',
    retention_policy VARCHAR(40) NOT NULL DEFAULT 'UNTIL_USER_DELETES',
    status VARCHAR(30) NOT NULL,
    exclude_from_twin_processing BOOLEAN NOT NULL DEFAULT FALSE,
    normalization_version VARCHAR(50) NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    supersedes_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_events_owner_time ON formation_twin_life_events(email, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_ft_events_source ON formation_twin_life_events(email, source_module, occurred_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_daily_checkins (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    email TEXT NOT NULL,
    checkin_type VARCHAR(40) NOT NULL,
    overall_state INTEGER CHECK (overall_state BETWEEN 0 AND 10),
    energy_level INTEGER CHECK (energy_level BETWEEN 0 AND 10),
    stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10),
    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10),
    connection_with_god VARCHAR(30),
    connection_with_people VARCHAR(30),
    self_report_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    sensitive_content_id UUID REFERENCES formation_twin_sensitive_contents(id),
    canonical_event_id UUID REFERENCES formation_twin_life_events(id),
    processing_preference VARCHAR(40) NOT NULL DEFAULT 'STORE_ONLY',
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revision INTEGER NOT NULL DEFAULT 1,
    supersedes_id UUID REFERENCES formation_twin_daily_checkins(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_checkins_owner_time ON formation_twin_daily_checkins(email, occurred_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_journals (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    email TEXT NOT NULL,
    journal_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    sensitive_content_id UUID NOT NULL REFERENCES formation_twin_sensitive_contents(id),
    canonical_event_id UUID REFERENCES formation_twin_life_events(id),
    processing_preference VARCHAR(40) NOT NULL DEFAULT 'STORE_ONLY',
    life_domains JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_selected_emotions JSONB NOT NULL DEFAULT '[]'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revision INTEGER NOT NULL DEFAULT 1,
    supersedes_id UUID REFERENCES formation_twin_journals(id),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_journals_owner_time ON formation_twin_journals(email, occurred_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_voice_journals (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    email TEXT NOT NULL,
    transcript_sensitive_content_id UUID REFERENCES formation_twin_sensitive_contents(id),
    canonical_event_id UUID REFERENCES formation_twin_life_events(id),
    transcription_status VARCHAR(40) NOT NULL,
    detected_language VARCHAR(20),
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    audio_retention_policy VARCHAR(50) NOT NULL DEFAULT 'DELETE_AFTER_TRANSCRIPTION',
    audio_sha256 VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    audio_deleted_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_voice_owner ON formation_twin_voice_journals(email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_event_revisions (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    event_id UUID NOT NULL REFERENCES formation_twin_life_events(id),
    revision INTEGER NOT NULL,
    change_type VARCHAR(40) NOT NULL,
    previous_event_id UUID REFERENCES formation_twin_life_events(id),
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS formation_twin_ingestion_receipts (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_event_id VARCHAR(160),
    client_event_id VARCHAR(160),
    canonical_event_id UUID REFERENCES formation_twin_life_events(id),
    processing_status VARCHAR(30) NOT NULL,
    failure_code VARCHAR(80),
    idempotent_replay BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ft_receipts_owner ON formation_twin_ingestion_receipts(email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_ingestion_failures (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT,
    source_type VARCHAR(50) NOT NULL,
    source_event_reference VARCHAR(160),
    error_code VARCHAR(80) NOT NULL,
    redacted_error_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    retryable BOOLEAN NOT NULL DEFAULT FALSE,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_source_connections (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source_module VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PAUSED',
    consent_scope VARCHAR(100) NOT NULL,
    allowed_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    blocked_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_event_received_at TIMESTAMPTZ,
    last_successful_sync_at TIMESTAMPTZ,
    last_failure_code VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, profile_id, source_module)
);

-- Publish only metadata to the existing event bus; sensitive text stays in the vault table.
COMMENT ON TABLE formation_twin_life_events IS 'Canonical life-event metadata; never stores full journal, prayer, transcript, confession, or crisis text.';
