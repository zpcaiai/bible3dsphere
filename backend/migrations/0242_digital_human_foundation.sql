-- Stores release governance and metadata-only turn audit. Raw questions,
-- transcripts, microphone audio and answer text are intentionally absent.
CREATE TABLE IF NOT EXISTS digital_human_character_releases (
    character_id TEXT NOT NULL,
    version TEXT NOT NULL,
    content_sha256 TEXT NOT NULL CHECK(content_sha256 ~ '^[a-f0-9]{64}$'),
    review_status TEXT NOT NULL DEFAULT 'THEOLOGY_REVIEW'
        CHECK(review_status IN ('DRAFT','THEOLOGY_REVIEW','APPROVED','WITHDRAWN')),
    avatar_manifest_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    voice_manifest_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    required_review_roles_json JSONB NOT NULL DEFAULT
        '["theology_reviewer","pastoral_reviewer","rights_reviewer","accessibility_reviewer","release_reviewer"]'::jsonb,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(character_id, version),
    CHECK(review_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS digital_human_turn_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_email TEXT NOT NULL,
    session_id TEXT NOT NULL, turn_id TEXT NOT NULL, trace_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    result_state TEXT NOT NULL CHECK(result_state IN ('READY_TO_SPEAK','TEXT_ONLY','BLOCKED')),
    grounding_level TEXT NOT NULL CHECK(grounding_level IN (
        'G5_DIRECT_SCRIPTURE','G4_STRONG_SCRIPTURAL_FACT','G3_SCRIPTURAL_INFERENCE',
        'G2_HISTORICAL_RECONSTRUCTION','G1_INTERPRETIVE_POSSIBILITY','G0_UNSUPPORTED')),
    reason_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    latency_ms NUMERIC(12,3) NOT NULL CHECK(latency_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(owner_email, turn_id)
);
CREATE INDEX IF NOT EXISTS idx_digital_human_turn_owner_created ON digital_human_turn_audit(owner_email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_digital_human_turn_trace ON digital_human_turn_audit(trace_id);
ALTER TABLE digital_human_character_releases ENABLE ROW LEVEL SECURITY;
ALTER TABLE digital_human_turn_audit ENABLE ROW LEVEL SECURITY;
-- The application commonly owns tables in existing deployments. FORCE keeps
-- owner connections from bypassing the same per-user policy enforced for
-- delegated roles.
ALTER TABLE digital_human_character_releases FORCE ROW LEVEL SECURITY;
ALTER TABLE digital_human_turn_audit FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS digital_human_release_read ON digital_human_character_releases;
CREATE POLICY digital_human_release_read ON digital_human_character_releases FOR SELECT USING (review_status = 'APPROVED');
DROP POLICY IF EXISTS digital_human_turn_owner ON digital_human_turn_audit;
CREATE POLICY digital_human_turn_owner ON digital_human_turn_audit
    USING (owner_email = NULLIF(current_setting('app.user_email', true), ''))
    WITH CHECK (owner_email = NULLIF(current_setting('app.user_email', true), ''));
COMMENT ON TABLE digital_human_turn_audit IS
    'Metadata-only audit. Never store raw audio, question text, transcript text, confession, health detail, or answer text.';
