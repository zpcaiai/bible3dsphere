-- Spiritual Planet Batch 10: finite scenarios, evaluation registry, fixed-version
-- release governance, kill switches, incident handling and data-subject rights.
-- 0219 remains reserved for the not-yet-landed Batch 8 relational collaboration.

CREATE TABLE IF NOT EXISTS formation_twin_scenarios (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160) NOT NULL, question TEXT NOT NULL, scenario_type VARCHAR(60) NOT NULL,
    baseline_snapshot_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    baseline_generated_at TIMESTAMPTZ NOT NULL,
    assumptions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    fixed_constraints_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    excluded_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    horizon VARCHAR(60) NOT NULL, branches_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_matrix_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    uncertainty_notes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    non_prediction_notice TEXT NOT NULL,
    prohibited_interpretations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    generation_method VARCHAR(40) NOT NULL DEFAULT 'RULE_ONLY',
    engine_version VARCHAR(80) NOT NULL, model_version VARCHAR(80), rule_version VARCHAR(80) NOT NULL,
    user_review_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT', major_decision_limited BOOLEAN NOT NULL DEFAULT FALSE,
    converted_proposal_reference UUID, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL, invalidated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    CHECK(expires_at > created_at), CHECK(generation_method='RULE_ONLY'),
    CHECK(jsonb_array_length(branches_json) BETWEEN 1 AND 3),
    CHECK(model_version IS NULL),
    CHECK(non_prediction_notice LIKE '%不是预测%')
);
CREATE INDEX IF NOT EXISTS idx_ft_scenarios_owner ON formation_twin_scenarios(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS governance_encrypted_artifacts (
    id UUID PRIMARY KEY, artifact_type VARCHAR(60) NOT NULL, nonce BYTEA NOT NULL,
    encrypted_content BYTEA NOT NULL, content_hash VARCHAR(64) NOT NULL,
    encryption_key_version VARCHAR(80) NOT NULL, retention_policy VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS governance_evaluation_datasets (
    id UUID PRIMARY KEY, dataset_key VARCHAR(100) NOT NULL, version VARCHAR(30) NOT NULL,
    task_family VARCHAR(80) NOT NULL, locale VARCHAR(20) NOT NULL,
    data_source_type VARCHAR(60) NOT NULL, sensitivity VARCHAR(40) NOT NULL,
    schema_version VARCHAR(30) NOT NULL, case_count INTEGER NOT NULL DEFAULT 0,
    consent_basis TEXT, retention_policy VARCHAR(80) NOT NULL,
    allowed_uses_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    owner_team VARCHAR(100) NOT NULL, approved_by_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deprecated_at TIMESTAMPTZ, UNIQUE(dataset_key,version), CHECK(case_count >= 0),
    CHECK(data_source_type IN ('SYNTHETIC','EXPERT_AUTHORED','PUBLIC_NON_SENSITIVE','CONSENTED_ANONYMIZED','PRODUCTION_INCIDENT_DERIVED_REDACTED','ADVERSARIAL_GENERATED')),
    CHECK(NOT (data_source_type='CONSENTED_ANONYMIZED' AND consent_basis IS NULL))
);

CREATE TABLE IF NOT EXISTS governance_evaluation_cases (
    id UUID PRIMARY KEY, dataset_id UUID NOT NULL REFERENCES governance_evaluation_datasets(id) ON DELETE CASCADE,
    case_key VARCHAR(120) NOT NULL, input_payload_encrypted_ref UUID REFERENCES governance_encrypted_artifacts(id) ON DELETE SET NULL,
    expected_constraints_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    prohibited_outputs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    safety_expectations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_requirements_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_control_requirements_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    tags_json JSONB NOT NULL DEFAULT '[]'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(dataset_id,case_key)
);

CREATE TABLE IF NOT EXISTS governance_evaluation_runs (
    id UUID PRIMARY KEY, run_type VARCHAR(40) NOT NULL,
    component_type VARCHAR(60) NOT NULL, component_id VARCHAR(120) NOT NULL,
    component_version VARCHAR(40) NOT NULL, dataset_id UUID REFERENCES governance_evaluation_datasets(id) ON DELETE RESTRICT,
    dataset_version VARCHAR(30) NOT NULL, metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    safety_failures_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    regression_comparison_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(40) NOT NULL, started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ, report_reference VARCHAR(500),
    CHECK(lower(component_version) <> 'latest')
);
CREATE INDEX IF NOT EXISTS idx_governance_eval_component ON governance_evaluation_runs(component_type,component_id,started_at DESC);

CREATE TABLE IF NOT EXISTS governance_component_versions (
    id UUID PRIMARY KEY, component_type VARCHAR(60) NOT NULL, component_id VARCHAR(120) NOT NULL,
    version VARCHAR(40) NOT NULL, artifact_reference VARCHAR(500) NOT NULL, checksum VARCHAR(64) NOT NULL,
    evaluation_report_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    approved_environments_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_classification VARCHAR(40) NOT NULL, approval_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    created_by VARCHAR(160) NOT NULL, approved_by_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), activated_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ, UNIQUE(component_type,component_id,version),
    CHECK(lower(version) <> 'latest'), CHECK(checksum ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS governance_data_lineage (
    id UUID PRIMARY KEY, tenant_id TEXT, subject_reference_hash VARCHAR(64),
    derived_entity_type VARCHAR(80) NOT NULL, derived_entity_reference VARCHAR(160) NOT NULL,
    source_module VARCHAR(80) NOT NULL, source_record_reference VARCHAR(160) NOT NULL,
    source_event_version VARCHAR(40) NOT NULL, consent_reference_hash VARCHAR(64),
    processing_step VARCHAR(100) NOT NULL, rule_version VARCHAR(80), prompt_version VARCHAR(80),
    model_version VARCHAR(80), user_confirmation_status VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), invalidated_at TIMESTAMPTZ,
    CHECK(lower(COALESCE(rule_version,'')) <> 'latest'),
    CHECK(lower(COALESCE(prompt_version,'')) <> 'latest'),
    CHECK(lower(COALESCE(model_version,'')) <> 'latest')
);

CREATE TABLE IF NOT EXISTS governance_release_candidates (
    id UUID PRIMARY KEY, release_key VARCHAR(120) NOT NULL, version VARCHAR(40) NOT NULL,
    changed_components_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    migration_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evaluation_report_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    security_scan_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    performance_report_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    gate_results_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    rollback_plan_reference VARCHAR(500) NOT NULL, incident_owner VARCHAR(160) NOT NULL,
    approval_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT', deployment_stage VARCHAR(40) NOT NULL DEFAULT 'DEVELOPMENT',
    blocker_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deployed_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ, rolled_back_at TIMESTAMPTZ, UNIQUE(release_key,version),
    CHECK(lower(version) <> 'latest')
);

CREATE TABLE IF NOT EXISTS governance_release_approvals (
    id UUID PRIMARY KEY, release_candidate_id UUID NOT NULL REFERENCES governance_release_candidates(id) ON DELETE CASCADE,
    approver_role VARCHAR(60) NOT NULL, approver_id VARCHAR(160) NOT NULL,
    decision VARCHAR(30) NOT NULL, comment TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(release_candidate_id,approver_role,approver_id)
);

CREATE TABLE IF NOT EXISTS governance_shadow_runs (
    id UUID PRIMARY KEY, component_id VARCHAR(120) NOT NULL,
    production_version VARCHAR(40) NOT NULL, candidate_version VARCHAR(40) NOT NULL,
    input_reference_hash VARCHAR(64) NOT NULL, consent_scope_hash VARCHAR(64) NOT NULL,
    production_output_encrypted_ref UUID REFERENCES governance_encrypted_artifacts(id) ON DELETE SET NULL,
    shadow_output_encrypted_ref UUID REFERENCES governance_encrypted_artifacts(id) ON DELETE SET NULL,
    difference_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    safety_comparison_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    side_effect_count INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL, deleted_at TIMESTAMPTZ,
    CHECK(side_effect_count=0), CHECK(expires_at > created_at),
    CHECK(lower(production_version) <> 'latest'), CHECK(lower(candidate_version) <> 'latest')
);

CREATE TABLE IF NOT EXISTS governance_kill_switches (
    id UUID PRIMARY KEY, switch_key VARCHAR(120) NOT NULL UNIQUE,
    scope_type VARCHAR(40) NOT NULL, scope_reference VARCHAR(160),
    active BOOLEAN NOT NULL DEFAULT FALSE, reason_code VARCHAR(100),
    activated_by VARCHAR(160), activated_at TIMESTAMPTZ,
    deactivated_by VARCHAR(160), deactivated_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance_kill_switch_audit (
    id UUID PRIMARY KEY, kill_switch_id UUID NOT NULL REFERENCES governance_kill_switches(id) ON DELETE RESTRICT,
    action VARCHAR(30) NOT NULL, actor_id VARCHAR(160) NOT NULL, reason_code VARCHAR(100) NOT NULL,
    impact_scope_json JSONB NOT NULL DEFAULT '{}'::jsonb, occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance_data_quality_rules (
    id UUID PRIMARY KEY, rule_key VARCHAR(120) NOT NULL, version VARCHAR(30) NOT NULL,
    target_entity VARCHAR(100) NOT NULL, severity VARCHAR(30) NOT NULL,
    condition_expression TEXT NOT NULL, remediation_action VARCHAR(100) NOT NULL,
    blocks_publication BOOLEAN NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(rule_key,version)
);

CREATE TABLE IF NOT EXISTS governance_data_quality_issues (
    id UUID PRIMARY KEY, tenant_id TEXT, subject_reference_hash VARCHAR(64),
    rule_id UUID NOT NULL REFERENCES governance_data_quality_rules(id) ON DELETE RESTRICT,
    affected_entity_type VARCHAR(100) NOT NULL, affected_entity_reference VARCHAR(160),
    severity VARCHAR(30) NOT NULL, status VARCHAR(40) NOT NULL DEFAULT 'OPEN',
    redacted_details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(), resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS governance_slo_measurements (
    id UUID PRIMARY KEY, slo_key VARCHAR(120) NOT NULL, environment VARCHAR(40) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    target_value NUMERIC NOT NULL, observed_value NUMERIC NOT NULL,
    status VARCHAR(30) NOT NULL, technical_dimensions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK(window_end > window_start)
);

CREATE TABLE IF NOT EXISTS governance_incidents (
    id UUID PRIMARY KEY, incident_key VARCHAR(120) NOT NULL UNIQUE,
    incident_type VARCHAR(60) NOT NULL, severity VARCHAR(30) NOT NULL,
    affected_components_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    affected_tenant_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(40) NOT NULL DEFAULT 'DETECTED', incident_owner VARCHAR(160) NOT NULL,
    containment_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_impact_summary TEXT, postmortem_reference VARCHAR(500),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(), contained_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ, CHECK(affected_tenant_count >= 0)
);

CREATE TABLE IF NOT EXISTS governance_third_party_processors (
    id UUID PRIMARY KEY, provider_key VARCHAR(120) NOT NULL UNIQUE, service_type VARCHAR(80) NOT NULL,
    data_categories_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    processing_purposes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    data_regions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    retention_terms TEXT NOT NULL, training_usage_policy TEXT NOT NULL,
    subprocessor_reference VARCHAR(500), security_review_status VARCHAR(40) NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE, exit_plan_reference VARCHAR(500) NOT NULL,
    review_due_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance_retention_policies (
    id UUID PRIMARY KEY, policy_key VARCHAR(120) NOT NULL, data_category VARCHAR(100) NOT NULL,
    default_retention_days INTEGER, user_configurable BOOLEAN NOT NULL,
    archive_allowed BOOLEAN NOT NULL, backup_retention_days INTEGER NOT NULL,
    legal_hold_supported BOOLEAN NOT NULL, deletion_behavior VARCHAR(120) NOT NULL,
    version VARCHAR(30) NOT NULL, approved_by_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(policy_key,version),
    CHECK(default_retention_days IS NULL OR default_retention_days > 0), CHECK(backup_retention_days >= 0)
);

CREATE TABLE IF NOT EXISTS governance_disaster_recovery_drills (
    id UUID PRIMARY KEY, drill_key VARCHAR(120) NOT NULL UNIQUE, drill_type VARCHAR(80) NOT NULL,
    environment VARCHAR(40) NOT NULL, rpo_target_minutes INTEGER,
    rto_target_minutes INTEGER, observed_rpo_minutes INTEGER, observed_rto_minutes INTEGER,
    deletion_tombstones_replayed BOOLEAN NOT NULL DEFAULT FALSE,
    consent_restored BOOLEAN NOT NULL DEFAULT FALSE, kill_switches_restored BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(40) NOT NULL DEFAULT 'PLANNED', evidence_reference VARCHAR(500),
    started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS compliance_rights_requests (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, subject_user_id TEXT NOT NULL, email TEXT NOT NULL,
    request_type VARCHAR(60) NOT NULL, scope_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(40) NOT NULL DEFAULT 'REQUESTED', requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    access_restricted_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, report_reference VARCHAR(500),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_compliance_rights_owner ON compliance_rights_requests(email,requested_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS governance_deletion_tombstones (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, subject_reference_hash VARCHAR(64) NOT NULL,
    source_manifest_reference VARCHAR(160) NOT NULL, deleted_scope_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), replayed_at TIMESTAMPTZ,
    UNIQUE(tenant_id,source_manifest_reference)
);

INSERT INTO governance_kill_switches(id,switch_key,scope_type,scope_reference)
VALUES
  (gen_random_uuid(),'formation-scenario-simulation','TASK_FAMILY','SCENARIO_SIMULATION'),
  (gen_random_uuid(),'formation-model-inference','TASK_FAMILY','MODEL_INFERENCE'),
  (gen_random_uuid(),'formation-early-warning','MODULE','EARLY_WARNING'),
  (gen_random_uuid(),'formation-relational-sharing','MODULE','RELATIONAL_SHARING'),
  (gen_random_uuid(),'spiritual-planet-cross-module-search','MODULE','CROSS_MODULE_SEARCH'),
  (gen_random_uuid(),'spiritual-planet-notifications','MODULE','NOTIFICATIONS')
ON CONFLICT(switch_key) DO NOTHING;

INSERT INTO governance_data_quality_rules
    (id,rule_key,version,target_entity,severity,condition_expression,remediation_action,blocks_publication)
VALUES
  (gen_random_uuid(),'scenario-confirmed-inputs','1.0.0','formation_twin_scenarios','HIGH','all assumptions user_confirmed','INVALIDATE_SCENARIO',TRUE),
  (gen_random_uuid(),'scenario-non-prediction','1.0.0','formation_twin_scenarios','HIGH','notice present and prohibited probabilities absent','INVALIDATE_SCENARIO',TRUE),
  (gen_random_uuid(),'production-fixed-version','1.0.0','governance_component_versions','HIGH','version is fixed and not latest','BLOCK_RELEASE',TRUE),
  (gen_random_uuid(),'release-rollback-evidence','1.0.0','governance_release_candidates','HIGH','rollback evidence passed','BLOCK_RELEASE',TRUE),
  (gen_random_uuid(),'shadow-no-side-effects','1.0.0','governance_shadow_runs','HIGH','side_effect_count equals zero','STOP_SHADOW',TRUE),
  (gen_random_uuid(),'deleted-data-not-reused','1.0.0','governance_data_lineage','HIGH','deleted source has no active derivative','INVALIDATE_DERIVATIVE',TRUE)
ON CONFLICT(rule_key,version) DO NOTHING;

INSERT INTO governance_retention_policies
    (id,policy_key,data_category,default_retention_days,user_configurable,archive_allowed,backup_retention_days,legal_hold_supported,deletion_behavior,version,approved_by_json)
VALUES
  (gen_random_uuid(),'scenario-default','FORMATION_SCENARIO',60,TRUE,FALSE,30,FALSE,'INVALIDATE_THEN_DELETE','1.0.0','[]'),
  (gen_random_uuid(),'shadow-default','SHADOW_OUTPUT',7,FALSE,FALSE,0,FALSE,'CRYPTO_ERASE_AND_DELETE','1.0.0','[]'),
  (gen_random_uuid(),'technical-log-default','REDACTED_TECHNICAL_LOG',30,FALSE,FALSE,30,TRUE,'ROTATE_AND_DELETE','1.0.0','[]')
ON CONFLICT(policy_key,version) DO NOTHING;

ALTER TABLE formation_twin_scenarios ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ft_scenario_owner_policy ON formation_twin_scenarios;
CREATE POLICY ft_scenario_owner_policy ON formation_twin_scenarios
  USING (email=current_setting('app.current_user_email',true))
  WITH CHECK (email=current_setting('app.current_user_email',true));

ALTER TABLE compliance_rights_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS compliance_rights_owner_policy ON compliance_rights_requests;
CREATE POLICY compliance_rights_owner_policy ON compliance_rights_requests
  USING (email=current_setting('app.current_user_email',true))
  WITH CHECK (email=current_setting('app.current_user_email',true));
