-- Formation Twin Batch 7: user-confirmed temptation cycles, explainable warnings,
-- minimum protection actions and non-shaming recovery.  No sensitive source body,
-- relapse probability, moral score, or internal risk band may enter notifications.

CREATE TABLE IF NOT EXISTS formation_twin_temptation_cycles (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160) NOT NULL, cycle_type VARCHAR(80) NOT NULL,
    trigger_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    vulnerability_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    emotional_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    environmental_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    protective_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    interruption_points_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    recovery_paths_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    rule_json JSONB NOT NULL DEFAULT '{"minimum_independent_conditions":2}'::jsonb,
    scope_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lifecycle_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    source_kind VARCHAR(50) NOT NULL DEFAULT 'USER_BUILT',
    statement_type VARCHAR(50) NOT NULL DEFAULT 'USER_CONFIRMED_INTERPRETATION',
    user_review_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    counterevidence_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    version INTEGER NOT NULL DEFAULT 1 CHECK(version >= 1),
    supersedes_cycle_id UUID REFERENCES formation_twin_temptation_cycles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_temptation_cycle_owner ON formation_twin_temptation_cycles(email,lifecycle_status,updated_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_temptation_cycle_nodes (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    cycle_id UUID NOT NULL REFERENCES formation_twin_temptation_cycles(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL, condition_code VARCHAR(100), content TEXT NOT NULL,
    source_kind VARCHAR(50) NOT NULL DEFAULT 'USER_BUILT',
    statement_type VARCHAR(50) NOT NULL DEFAULT 'USER_CONFIRMED_INTERPRETATION',
    user_review_status VARCHAR(40) NOT NULL DEFAULT 'PENDING', sequence_order INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_temptation_node_owner ON formation_twin_temptation_cycle_nodes(email,cycle_id,sequence_order) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_temptation_cycle_edges (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    cycle_id UUID NOT NULL REFERENCES formation_twin_temptation_cycles(id) ON DELETE CASCADE,
    from_node_id UUID NOT NULL REFERENCES formation_twin_temptation_cycle_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES formation_twin_temptation_cycle_nodes(id) ON DELETE CASCADE,
    relation_type VARCHAR(60) NOT NULL, source_kind VARCHAR(50) NOT NULL DEFAULT 'USER_BUILT',
    statement_type VARCHAR(50) NOT NULL DEFAULT 'USER_CONFIRMED_INTERPRETATION',
    confidence NUMERIC, user_review_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK(confidence IS NULL OR confidence BETWEEN 0 AND 1), CHECK(from_node_id <> to_node_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_risk_conditions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    condition_type VARCHAR(80) NOT NULL, condition_code VARCHAR(100) NOT NULL,
    user_visible_description TEXT NOT NULL, source_kind VARCHAR(50) NOT NULL,
    statement_type VARCHAR(50) NOT NULL, user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    consent_type VARCHAR(80), independence_group VARCHAR(160),
    occurred_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
    evidence_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), invalidated_at TIMESTAMPTZ,
    CHECK(expires_at > occurred_at)
);
CREATE INDEX IF NOT EXISTS idx_ft_risk_condition_owner ON formation_twin_risk_conditions(email,expires_at DESC) WHERE invalidated_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_risk_snapshots (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    matched_cycle_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_protective_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_protective_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    unknown_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    internal_risk_band VARCHAR(50) NOT NULL,
    user_visible_warning_level VARCHAR(50) NOT NULL,
    evidence_quality VARCHAR(50) NOT NULL,
    explanation_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    counterevidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    warning_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    warning_suppression_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    engine_version VARCHAR(80) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    invalidated_at TIMESTAMPTZ, CHECK(window_end >= window_start)
);
CREATE INDEX IF NOT EXISTS idx_ft_risk_snapshot_owner ON formation_twin_risk_snapshots(email,created_at DESC) WHERE invalidated_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_early_warnings (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    risk_snapshot_id UUID NOT NULL REFERENCES formation_twin_risk_snapshots(id) ON DELETE CASCADE,
    warning_level VARCHAR(50) NOT NULL, title VARCHAR(120) NOT NULL, message TEXT NOT NULL,
    matched_cycle_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_condition_summaries_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_protection_summaries_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    unknown_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    counterevidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    uncertainty_notes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    proposed_protection_action_id UUID,
    delivery_channel VARCHAR(40) NOT NULL DEFAULT 'IN_APP_ONLY',
    delivery_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    user_decision_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    sharing_status VARCHAR(40) NOT NULL DEFAULT 'PRIVATE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ, dismissed_at TIMESTAMPTZ, snoozed_until TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_early_warning_owner ON formation_twin_early_warnings(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_warning_feedback (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    warning_id UUID NOT NULL REFERENCES formation_twin_early_warnings(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL, user_comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_protection_action_templates (
    id UUID PRIMARY KEY, template_key VARCHAR(100) NOT NULL, version VARCHAR(40) NOT NULL,
    action_type VARCHAR(60) NOT NULL, title_template TEXT NOT NULL, description_template TEXT NOT NULL,
    allowed_warning_levels_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_capacity_modes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_module VARCHAR(60) NOT NULL, routing_schema_version VARCHAR(60) NOT NULL,
    contraindications_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    safety_notes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(template_key,version)
);

CREATE TABLE IF NOT EXISTS formation_twin_protection_actions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    warning_id UUID REFERENCES formation_twin_early_warnings(id) ON DELETE SET NULL,
    action_type VARCHAR(60) NOT NULL, title VARCHAR(120) NOT NULL, description TEXT NOT NULL,
    target_module VARCHAR(60) NOT NULL, routing_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision_status VARCHAR(40) NOT NULL DEFAULT 'PENDING', execution_status VARCHAR(40) NOT NULL DEFAULT 'NOT_STARTED',
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    sensitive_context_included BOOLEAN NOT NULL DEFAULT FALSE,
    request_id UUID, idempotency_key VARCHAR(64),
    version INTEGER NOT NULL DEFAULT 1, supersedes_action_id UUID REFERENCES formation_twin_protection_actions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ, stopped_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    UNIQUE(email,request_id), UNIQUE(email,idempotency_key), CHECK(sensitive_context_included=FALSE)
);
CREATE INDEX IF NOT EXISTS idx_ft_protection_action_owner ON formation_twin_protection_actions(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_protection_plans (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160) NOT NULL, cycle_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    early_signs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    high_risk_contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    protective_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    environment_boundaries_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    support_contact_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    spiritual_supports_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    professional_supports_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    sharing_policy_json JSONB NOT NULL DEFAULT '{"mode":"PRIVATE_ONLY"}'::jsonb,
    escalation_rules_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE, active BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1, supersedes_plan_id UUID REFERENCES formation_twin_protection_plans(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_rehearsed_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_support_contacts (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    contact_reference_id VARCHAR(200), display_alias VARCHAR(120) NOT NULL,
    support_role VARCHAR(60) NOT NULL, allowed_share_fields_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_actions_json JSONB NOT NULL DEFAULT '["DRAFT_MESSAGE_ONLY"]'::jsonb,
    sharing_expires_at TIMESTAMPTZ, active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_support_requests (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    support_contact_id UUID NOT NULL REFERENCES formation_twin_support_contacts(id) ON DELETE CASCADE,
    request_type VARCHAR(50) NOT NULL, message_draft TEXT,
    share_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    delivery_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), sent_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_recovery_records (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    event_type VARCHAR(60) NOT NULL, occurred_at TIMESTAMPTZ NOT NULL,
    immediate_safety_status VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
    continuation_risk VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
    user_reported_behavior_encrypted_ref UUID,
    shame_state_json JSONB, isolation_state_json JSONB,
    immediate_recovery_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    support_connections_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    environment_changes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_reported_effects_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    lessons_to_retain_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    statement_type VARCHAR(50) NOT NULL DEFAULT 'USER_REPORTED_FACT',
    processing_preference VARCHAR(50) NOT NULL DEFAULT 'STORE_ONLY',
    recovery_status VARCHAR(50) NOT NULL DEFAULT 'SAFETY_CHECK_REQUIRED',
    first_step VARCHAR(50) NOT NULL DEFAULT 'IMMEDIATE_SAFETY',
    safety_checked_at TIMESTAMPTZ, behavior_stopped_at TIMESTAMPTZ,
    stabilized_at TIMESTAMPTZ, review_due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK(statement_type='USER_REPORTED_FACT'), CHECK(first_step='IMMEDIATE_SAFETY')
);

CREATE TABLE IF NOT EXISTS formation_twin_recovery_reviews (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    recovery_record_id UUID NOT NULL REFERENCES formation_twin_recovery_records(id) ON DELETE CASCADE,
    review_status VARCHAR(40) NOT NULL DEFAULT 'PENDING', answers_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    cycle_updates_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    scheduled_for TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ, skipped_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_risk_settings (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    warnings_enabled BOOLEAN NOT NULL DEFAULT FALSE, enabled_cycle_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    delivery_channel VARCHAR(40) NOT NULL DEFAULT 'IN_APP_ONLY',
    quiet_hours_json JSONB NOT NULL DEFAULT '{"start":"22:00","end":"07:00","timezone":"Asia/Shanghai"}'::jsonb,
    cooldown_settings_json JSONB NOT NULL DEFAULT '{"AWARENESS":12,"PROTECTION_SUGGESTED":4}'::jsonb,
    model_assistance_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    passive_metadata_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    passive_metadata_consent BOOLEAN NOT NULL DEFAULT FALSE,
    effect_learning_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    accountability_drafts_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    all_warnings_paused BOOLEAN NOT NULL DEFAULT FALSE,
    paused_until TIMESTAMPTZ,
    sharing_defaults_json JSONB NOT NULL DEFAULT '{"mode":"DRAFT_MESSAGE_ONLY"}'::jsonb,
    blocked_action_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    false_positive_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id,profile_id), CHECK(false_positive_count >= 0)
);

INSERT INTO formation_twin_protection_action_templates
    (id,template_key,version,action_type,title_template,description_template,
     allowed_warning_levels_json,allowed_capacity_modes_json,target_module,routing_schema_version,
     contraindications_json,safety_notes_json)
VALUES
    (gen_random_uuid(),'leave-environment','1.0','LEAVE_ENVIRONMENT','先离开当前环境','到一个安全、有人或更开放的空间停留十分钟。','["PROTECTION_SUGGESTED","IMMEDIATE_SUPPORT_SUGGESTED"]','["MICRO_ONLY","NORMAL"]','ATTENTION_OS','1.0','[]','["不得阻断紧急通信"]'),
    (gen_random_uuid(),'move-device','1.0','MOVE_DEVICE','把设备移远','把当前设备放到另一个房间，先保留十分钟距离。','["AWARENESS","PROTECTION_SUGGESTED"]','["MICRO_ONLY","NORMAL"]','ATTENTION_OS','1.0','[]','[]'),
    (gen_random_uuid(),'delay-decision','1.0','DELAY_DECISION','延迟十分钟','先不作最终决定；十分钟后再重新选择。','["AWARENESS","PROTECTION_SUGGESTED"]','["MICRO_ONLY","NORMAL"]','FORMATION_ENGINE','1.0','[]','[]'),
    (gen_random_uuid(),'support-draft','1.0','MESSAGE_SUPPORT_PERSON','准备一条求助消息','生成一句五分钟陪伴请求草稿；不会自动发送。','["PROTECTION_SUGGESTED","IMMEDIATE_SUPPORT_SUGGESTED"]','["MICRO_ONLY","NORMAL"]','ACCOUNTABILITY','1.0','[]','["默认草稿，不自动发送"]'),
    (gen_random_uuid(),'short-honest-prayer','1.0','SHORT_HONEST_PRAYER','一句诚实祷告','一句诚实表达，并同时保留环境和真人支持。','["AWARENESS","PROTECTION_SUGGESTED"]','["MICRO_ONLY","NORMAL"]','PRAYER_OS','1.0','[]','["不得替代安全行动"]'),
    (gen_random_uuid(),'crisis-handoff','1.0','CRISIS_HANDOFF','打开安全帮助','暂停普通分析，连接现有 Crisis Care 安全入口。','["CRISIS_HANDOFF"]','["MICRO_ONLY","NORMAL"]','CRISIS_CARE','1.0','[]','[]'),
    (gen_random_uuid(),'no-action','1.0','NO_ACTION','现在不增加行动','只保留这次看见；安全状态变化时可随时求助。','["AWARENESS"]','["MICRO_ONLY","NORMAL"]','NO_ACTION','1.0','[]','[]')
ON CONFLICT(template_key,version) DO NOTHING;

-- Owner RLS is defense in depth; application queries also retain email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_temptation_cycles','formation_twin_temptation_cycle_nodes',
    'formation_twin_temptation_cycle_edges','formation_twin_risk_conditions',
    'formation_twin_risk_snapshots','formation_twin_early_warnings',
    'formation_twin_warning_feedback','formation_twin_protection_actions',
    'formation_twin_protection_plans','formation_twin_support_contacts',
    'formation_twin_support_requests','formation_twin_recovery_records',
    'formation_twin_recovery_reviews','formation_twin_risk_settings'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
