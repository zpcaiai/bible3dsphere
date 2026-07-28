-- EMD-OS Batch 10: production certification for the emotional maturity domain.
-- These tables extend the existing production_governance schema (migration 0220);
-- they are governance artefacts and hold no user Formation Twin content.

CREATE TABLE IF NOT EXISTS production_emd_intended_use_profiles (
    id UUID PRIMARY KEY,
    release_id VARCHAR(60) NOT NULL,
    classification_id VARCHAR(80) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'CLASSIFIED',
    intended_use_tier VARCHAR(32) NOT NULL,
    maximum_certifiable_level VARCHAR(40),
    risk_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    hard_blocks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    prohibited_uses_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(release_id, classification_id),
    CHECK(status IN ('CLASSIFIED','BLOCKED')),
    -- a forbidden intended use can never carry a certifiable level
    CHECK(intended_use_tier <> 'IU_X_FORBIDDEN' OR maximum_certifiable_level IS NULL)
);

CREATE TABLE IF NOT EXISTS production_emd_gate_reports (
    id UUID PRIMARY KEY,
    release_id VARCHAR(60) NOT NULL,
    gate_code VARCHAR(32) NOT NULL,
    report_id VARCHAR(80) NOT NULL,
    status VARCHAR(24) NOT NULL,
    blocking BOOLEAN NOT NULL DEFAULT FALSE,
    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(release_id, gate_code, report_id),
    CHECK(gate_code IN ('G0_INTENDED_USE','G1_PSYCHOMETRIC','G2_DATA_QUALITY','G3_FAIRNESS',
                        'G4_DOMAIN_SAFETY','G5_PRIVACY','G6_LLM_SECURITY','G7_ENGINEERING',
                        'G8_HUMAN_OPERATIONS','G9_SIGNOFF')),
    CHECK(status IN ('PASS','PASS_WITH_WARNINGS','PASS_WITH_RESTRICTIONS','BLOCKED','NOT_EVALUATED'))
);
CREATE INDEX IF NOT EXISTS idx_prod_emd_gate_release ON production_emd_gate_reports(release_id, gate_code);

CREATE TABLE IF NOT EXISTS production_emd_release_certificates (
    id UUID PRIMARY KEY,
    certificate_id VARCHAR(80) NOT NULL UNIQUE,
    release_id VARCHAR(60) NOT NULL,
    product_version VARCHAR(40) NOT NULL DEFAULT '0.1.0',
    intended_use_tier VARCHAR(32) NOT NULL,
    certified_level VARCHAR(40),
    decision VARCHAR(24) NOT NULL,
    certificate_status VARCHAR(32) NOT NULL DEFAULT 'NOT_EVALUATED',
    supported_locales_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    deployment_jurisdictions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    restricted_gates_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    known_limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    residual_risks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    obtained_signoffs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_runtime_controls_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- an internal certificate may never claim external certification
    external_certification_claimed BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from TIMESTAMPTZ, expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(decision IN ('GO','PASS_WITH_RESTRICTIONS','NO_GO')),
    CHECK(certificate_status IN ('NOT_EVALUATED','LAB_ONLY','RESTRICTED_PILOT','PRIVATE_PRODUCTION',
                                 'HUMAN_SUPPORTED_PRODUCTION','COMMUNITY_RESTRICTED','SUSPENDED',
                                 'REVOKED','EXPIRED')),
    CHECK(external_certification_claimed = FALSE),
    -- a granted certificate always has an expiry
    CHECK(decision = 'NO_GO' OR expires_at IS NOT NULL),
    CHECK(intended_use_tier <> 'IU_X_FORBIDDEN' OR decision = 'NO_GO')
);
CREATE INDEX IF NOT EXISTS idx_prod_emd_cert_release ON production_emd_release_certificates(release_id, created_at DESC);

CREATE TABLE IF NOT EXISTS production_emd_change_controls (
    id UUID PRIMARY KEY,
    change_control_id VARCHAR(80) NOT NULL UNIQUE,
    change_request_id VARCHAR(80) NOT NULL,
    current_release VARCHAR(60) NOT NULL,
    proposed_release VARCHAR(60) NOT NULL,
    requested_change_level VARCHAR(10) NOT NULL,
    actual_change_level VARCHAR(10) NOT NULL,
    reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_retests_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    invalidated_certificates_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    approved_by VARCHAR(80), approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(requested_change_level IN ('PATCH','MINOR','MAJOR')),
    CHECK(actual_change_level IN ('PATCH','MINOR','MAJOR'))
);

CREATE TABLE IF NOT EXISTS production_emd_incidents (
    id UUID PRIMARY KEY,
    incident_id VARCHAR(80) NOT NULL UNIQUE,
    incident_response_id VARCHAR(80) NOT NULL,
    incident_type VARCHAR(48) NOT NULL,
    severity VARCHAR(24) NOT NULL,
    affected_release VARCHAR(60) NOT NULL,
    affected_users INTEGER NOT NULL DEFAULT 0 CHECK(affected_users >= 0),
    affected_records INTEGER NOT NULL DEFAULT 0 CHECK(affected_records >= 0),
    immediate_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    kill_switches_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    certificate_action VARCHAR(20) NOT NULL DEFAULT 'UNCHANGED',
    recall_plan_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_notification_required BOOLEAN NOT NULL DEFAULT FALSE,
    recertification_required BOOLEAN NOT NULL DEFAULT FALSE,
    recall_completed BOOLEAN NOT NULL DEFAULT FALSE,
    regression_test_added BOOLEAN NOT NULL DEFAULT FALSE,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(severity IN ('SEV0_CATASTROPHIC','SEV1_CRITICAL','SEV2_HIGH','SEV3_MEDIUM','SEV4_LOW')),
    CHECK(certificate_action IN ('UNCHANGED','UNDER_REVIEW','SUSPENDED','REVOKED')),
    -- an incident cannot be closed by a code fix alone: recall and a new test are required
    CHECK(closed_at IS NULL OR (recall_completed = TRUE AND regression_test_added = TRUE))
);
CREATE INDEX IF NOT EXISTS idx_prod_emd_incident_release ON production_emd_incidents(affected_release, created_at DESC);
