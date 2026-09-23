-- Immutable independent-review attestations and signed release evidence.
-- Raw content, prompts, transcripts and private keys never belong here.
CREATE TABLE IF NOT EXISTS digital_human_review_attestations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_version TEXT NOT NULL,
    content_sha256 TEXT NOT NULL CHECK(content_sha256 ~ '^[a-f0-9]{64}$'),
    catalog_sha256 TEXT NOT NULL CHECK(catalog_sha256 ~ '^[a-f0-9]{64}$'),
    asset_manifest_sha256 TEXT NOT NULL CHECK(asset_manifest_sha256 ~ '^[a-f0-9]{64}$'),
    reviewer_id TEXT NOT NULL,
    reviewer_role TEXT NOT NULL CHECK(reviewer_role IN (
        'theology_reviewer','pastoral_reviewer','rights_reviewer',
        'accessibility_reviewer','release_reviewer'
    )),
    decision TEXT NOT NULL CHECK(decision IN ('APPROVED','CHANGES_REQUIRED','REJECTED')),
    signer_key_id TEXT NOT NULL,
    attestation_sha256 TEXT NOT NULL UNIQUE CHECK(attestation_sha256 ~ '^[a-f0-9]{64}$'),
    attestation_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(content_version, content_sha256, asset_manifest_sha256, reviewer_role),
    UNIQUE(content_version, content_sha256, asset_manifest_sha256, reviewer_id)
);

CREATE TABLE IF NOT EXISTS digital_human_release_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_version TEXT NOT NULL,
    content_sha256 TEXT NOT NULL CHECK(content_sha256 ~ '^[a-f0-9]{64}$'),
    catalog_sha256 TEXT NOT NULL CHECK(catalog_sha256 ~ '^[a-f0-9]{64}$'),
    asset_manifest_sha256 TEXT NOT NULL CHECK(asset_manifest_sha256 ~ '^[a-f0-9]{64}$'),
    build_revision TEXT NOT NULL,
    test_evidence_sha256 TEXT NOT NULL CHECK(test_evidence_sha256 ~ '^[a-f0-9]{64}$'),
    signer_key_id TEXT NOT NULL,
    certificate_sha256 TEXT NOT NULL UNIQUE CHECK(certificate_sha256 ~ '^[a-f0-9]{64}$'),
    certificate_json JSONB NOT NULL,
    content_decision TEXT NOT NULL CHECK(content_decision IN ('APPROVED','WITHDRAWN')),
    product_assurance TEXT NOT NULL DEFAULT 'NOT_CERTIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION prevent_digital_human_evidence_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'digital-human release evidence is append-only';
END;
$$;

DROP TRIGGER IF EXISTS digital_human_review_immutable ON digital_human_review_attestations;
CREATE TRIGGER digital_human_review_immutable
BEFORE UPDATE OR DELETE ON digital_human_review_attestations
FOR EACH ROW EXECUTE FUNCTION prevent_digital_human_evidence_mutation();

DROP TRIGGER IF EXISTS digital_human_release_immutable ON digital_human_release_evidence;
CREATE TRIGGER digital_human_release_immutable
BEFORE UPDATE OR DELETE ON digital_human_release_evidence
FOR EACH ROW EXECUTE FUNCTION prevent_digital_human_evidence_mutation();

ALTER TABLE digital_human_review_attestations ENABLE ROW LEVEL SECURITY;
ALTER TABLE digital_human_review_attestations FORCE ROW LEVEL SECURITY;
ALTER TABLE digital_human_release_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE digital_human_release_evidence FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS digital_human_review_insert ON digital_human_review_attestations;
CREATE POLICY digital_human_review_insert ON digital_human_review_attestations
    FOR INSERT WITH CHECK (current_setting('app.release_evidence_writer', true) = 'true');
DROP POLICY IF EXISTS digital_human_review_admin_read ON digital_human_review_attestations;
CREATE POLICY digital_human_review_admin_read ON digital_human_review_attestations
    FOR SELECT USING (current_setting('app.platform_admin', true) = 'true');
DROP POLICY IF EXISTS digital_human_release_insert ON digital_human_release_evidence;
CREATE POLICY digital_human_release_insert ON digital_human_release_evidence
    FOR INSERT WITH CHECK (current_setting('app.release_evidence_writer', true) = 'true');
DROP POLICY IF EXISTS digital_human_release_admin_read ON digital_human_release_evidence;
CREATE POLICY digital_human_release_admin_read ON digital_human_release_evidence
    FOR SELECT USING (current_setting('app.platform_admin', true) = 'true');

COMMENT ON TABLE digital_human_review_attestations IS
    'Detached human review attestations only; no raw theological or pastoral conversation content.';
COMMENT ON TABLE digital_human_release_evidence IS
    'Append-only Ed25519 release certificates. product_assurance remains separate from content approval.';
