-- Formation Twin Batch 6: daily/weekly reflection and consent-gated micro interventions.
-- Mirrors contain bounded structured summaries only. Raw journals, prayer, confession,
-- transcripts, temptation details, crisis bodies, and third-party identity never belong here.

CREATE TABLE IF NOT EXISTS formation_twin_reflection_contexts (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    context_type VARCHAR(30) NOT NULL, window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    emotional_snapshot_id UUID REFERENCES formation_twin_emotional_snapshots(id) ON DELETE SET NULL,
    formation_snapshot_id UUID REFERENCES formation_twin_formation_snapshots(id) ON DELETE SET NULL,
    long_term_snapshot_id UUID REFERENCES formation_twin_long_term_snapshots(id) ON DELETE SET NULL,
    active_life_seasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    confirmed_patterns_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    protective_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    grace_recovery_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_capacity_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    safety_status_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_coverage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_output VARCHAR(40) NOT NULL,
    engine_version VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), invalidated_at TIMESTAMPTZ,
    CHECK(window_end >= window_start)
);
CREATE INDEX IF NOT EXISTS idx_ft_reflection_context_owner ON formation_twin_reflection_contexts(email,created_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_reflection_mirrors (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    context_id UUID NOT NULL REFERENCES formation_twin_reflection_contexts(id) ON DELETE CASCADE,
    mirror_type VARCHAR(20) NOT NULL, headline VARCHAR(160) NOT NULL, mirror_text TEXT NOT NULL,
    confirmed_observations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    pending_items_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    grace_protection_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    generation_method VARCHAR(30) NOT NULL, model_version VARCHAR(120), template_version VARCHAR(80) NOT NULL,
    user_review_status VARCHAR(30) NOT NULL DEFAULT 'PENDING', status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    version INTEGER NOT NULL DEFAULT 1,
    supersedes_mirror_id UUID REFERENCES formation_twin_reflection_mirrors(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), dismissed_at TIMESTAMPTZ,
    invalidated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    CHECK(jsonb_array_length(source_references_json) > 0 OR status IN ('DISMISSED','INVALIDATED'))
);
CREATE INDEX IF NOT EXISTS idx_ft_reflection_mirror_owner ON formation_twin_reflection_mirrors(email,mirror_type,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_reflection_questions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    mirror_id UUID REFERENCES formation_twin_reflection_mirrors(id) ON DELETE CASCADE,
    question_type VARCHAR(50) NOT NULL, question_text TEXT NOT NULL,
    selection_rationale_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    burden_level VARCHAR(20) NOT NULL, template_version VARCHAR(80) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    answered_at TIMESTAMPTZ, skipped_at TIMESTAMPTZ, cooldown_until TIMESTAMPTZ, deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_reflection_question_owner ON formation_twin_reflection_questions(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_reflection_answers (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    question_id UUID NOT NULL REFERENCES formation_twin_reflection_questions(id) ON DELETE CASCADE,
    answer_text TEXT, answer_type VARCHAR(30) NOT NULL, processing_preference VARCHAR(40) NOT NULL,
    statement_type VARCHAR(40) NOT NULL DEFAULT 'USER_REPORTED_FACT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_intervention_templates (
    id UUID PRIMARY KEY, template_key VARCHAR(80) NOT NULL, version VARCHAR(40) NOT NULL,
    intervention_type VARCHAR(50) NOT NULL, title_template TEXT NOT NULL, description_template TEXT NOT NULL,
    minimum_duration_minutes INTEGER NOT NULL, maximum_duration_minutes INTEGER NOT NULL,
    allowed_capacity_modes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_safety_levels_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_context_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    prohibited_context_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_module VARCHAR(50) NOT NULL, routing_schema_version VARCHAR(50) NOT NULL,
    contraindications_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    theological_safety_notes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(template_key,version), CHECK(maximum_duration_minutes >= minimum_duration_minutes)
);

CREATE TABLE IF NOT EXISTS formation_twin_intervention_proposals (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    context_id UUID NOT NULL REFERENCES formation_twin_reflection_contexts(id) ON DELETE CASCADE,
    mirror_id UUID REFERENCES formation_twin_reflection_mirrors(id) ON DELETE SET NULL,
    template_key VARCHAR(80), intervention_type VARCHAR(50) NOT NULL,
    title VARCHAR(160) NOT NULL, description TEXT NOT NULL, rationale TEXT NOT NULL,
    estimated_duration_minutes INTEGER NOT NULL CHECK(estimated_duration_minutes BETWEEN 0 AND 30),
    effort_level VARCHAR(20) NOT NULL, timing_window_json JSONB,
    target_module VARCHAR(50) NOT NULL, routing_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_pattern_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_factor_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    safety_classification VARCHAR(40) NOT NULL,
    contraindications_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    generation_method VARCHAR(30) NOT NULL, statement_type VARCHAR(50) NOT NULL,
    decision_status VARCHAR(40) NOT NULL DEFAULT 'PENDING', lifecycle_status VARCHAR(30) NOT NULL DEFAULT 'PROPOSED',
    required_user_confirmation BOOLEAN NOT NULL DEFAULT TRUE,
    one_time BOOLEAN NOT NULL DEFAULT TRUE, reminder_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    requires_second_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    supersedes_proposal_id UUID REFERENCES formation_twin_intervention_proposals(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ, invalidated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    CHECK(required_user_confirmation=TRUE), CHECK(reminder_enabled=FALSE)
);
CREATE INDEX IF NOT EXISTS idx_ft_intervention_proposal_owner ON formation_twin_intervention_proposals(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_intervention_decisions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    proposal_id UUID NOT NULL REFERENCES formation_twin_intervention_proposals(id) ON DELETE CASCADE,
    decision_status VARCHAR(40) NOT NULL, user_modifications_json JSONB,
    habit_confirmation_json JSONB, reason_code VARCHAR(80), user_comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_intervention_decision_owner ON formation_twin_intervention_decisions(email,proposal_id,created_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_intervention_executions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    proposal_id UUID NOT NULL REFERENCES formation_twin_intervention_proposals(id) ON DELETE CASCADE,
    request_id UUID NOT NULL, idempotency_key VARCHAR(64) NOT NULL,
    target_module VARCHAR(50) NOT NULL, target_record_reference VARCHAR(200),
    execution_status VARCHAR(40) NOT NULL, routing_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    routed_at TIMESTAMPTZ, started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ, cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(email,request_id), UNIQUE(email,idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_ft_intervention_execution_owner ON formation_twin_intervention_executions(email,created_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_intervention_effect_reviews (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    intervention_id UUID NOT NULL REFERENCES formation_twin_intervention_executions(id) ON DELETE CASCADE,
    execution_status VARCHAR(40) NOT NULL, helpfulness VARCHAR(30), burden VARCHAR(30),
    emotional_effect_json JSONB, formation_effect_json JSONB, practical_effect_json JSONB,
    what_helped TEXT, what_did_not_help TEXT, preferred_adjustment TEXT,
    statement_type VARCHAR(40) NOT NULL DEFAULT 'USER_REPORTED_FACT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email,intervention_id), CHECK(statement_type='USER_REPORTED_FACT')
);

CREATE TABLE IF NOT EXISTS formation_twin_intervention_preferences (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    preference_type VARCHAR(60) NOT NULL, preference_value_json JSONB NOT NULL,
    source_review_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb, confidence NUMERIC,
    scope VARCHAR(40) NOT NULL DEFAULT 'CURRENT_USER', active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ,
    CHECK(confidence IS NULL OR confidence BETWEEN 0 AND 1)
);
CREATE INDEX IF NOT EXISTS idx_ft_intervention_preference_owner ON formation_twin_intervention_preferences(email,active,created_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_weekly_reviews (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    context_id UUID NOT NULL REFERENCES formation_twin_reflection_contexts(id) ON DELETE CASCADE,
    window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    important_observations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    burden_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    grace_protection_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    emerging_alternatives_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    focus_theme TEXT, question_id UUID REFERENCES formation_twin_reflection_questions(id) ON DELETE SET NULL,
    proposal_id UUID REFERENCES formation_twin_intervention_proposals(id) ON DELETE SET NULL,
    data_coverage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING', version INTEGER NOT NULL DEFAULT 1,
    supersedes_review_id UUID REFERENCES formation_twin_weekly_reviews(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ,
    skipped_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    CHECK(window_end >= window_start), CHECK(jsonb_array_length(important_observations_json) <= 3)
);
CREATE INDEX IF NOT EXISTS idx_ft_weekly_review_owner ON formation_twin_weekly_reviews(email,window_end DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_reflection_settings (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    daily_mirror_mode VARCHAR(40) NOT NULL DEFAULT 'ON_DEMAND',
    weekly_review_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    effect_review_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    cross_module_routing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    preference_learning_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    interventions_paused BOOLEAN NOT NULL DEFAULT FALSE,
    reminder_settings_json JSONB NOT NULL DEFAULT '{"daily_enabled":false,"weekly_enabled":false,"effect_enabled":false}'::jsonb,
    quiet_hours_json JSONB NOT NULL DEFAULT '{"start":"22:00","end":"07:00","timezone":"Asia/Shanghai"}'::jsonb,
    capacity_default VARCHAR(30), maximum_action_minutes INTEGER NOT NULL DEFAULT 10,
    preferred_intervention_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    blocked_intervention_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id,profile_id), CHECK(maximum_action_minutes BETWEEN 0 AND 30)
);

INSERT INTO formation_twin_intervention_templates
    (id,template_key,version,intervention_type,title_template,description_template,minimum_duration_minutes,
     maximum_duration_minutes,allowed_capacity_modes_json,allowed_safety_levels_json,target_module,
     routing_schema_version,contraindications_json,theological_safety_notes_json)
VALUES
    (gen_random_uuid(),'pause-60s','1.0','PAUSE','暂停一分钟','暂停60秒，只说出一个感受。',1,1,'["MICRO_ONLY","NORMAL"]','["NONE","LOW"]','FORMATION_ENGINE','1.0','[]','[]'),
    (gen_random_uuid(),'rest-less','1.0','REST','允许今天少做一点','取消一个非必要任务。',1,1,'["MICRO_ONLY","NORMAL"]','["NONE","LOW"]','REST','1.0','[]','[]'),
    (gen_random_uuid(),'honest-prayer','1.0','PRAYER','两分钟诚实祷告','诚实说出害怕与希望，不要求立刻平静。',2,2,'["NORMAL"]','["NONE","LOW"]','PRAYER_OS','1.0','[]','["不得把祷告当作情绪消除工具"]'),
    (gen_random_uuid(),'relational-listening','1.0','RELATIONAL_SUPPORT','联系可信任的人','准备一句请求五分钟倾听的消息；不自动发送。',1,1,'["MICRO_ONLY","NORMAL"]','["NONE","LOW"]','RELATIONAL_SUPPORT','1.0','[]','[]'),
    (gen_random_uuid(),'attention-reminder','1.0','ATTENTION_BOUNDARY','温和注意力边界','创建提醒式边界，不强制封锁。',1,1,'["NORMAL"]','["NONE","LOW"]','ATTENTION_OS','1.0','[]','[]'),
    (gen_random_uuid(),'professional-support','1.0','PROFESSIONAL_SUPPORT','准备专业支持','记录对睡眠或工作的影响，准备与专业人员讨论。',3,3,'["MICRO_ONLY","NORMAL"]','["NONE","LOW"]','PROFESSIONAL_SUPPORT','1.0','[]','["不得诊断"]'),
    (gen_random_uuid(),'no-action','1.0','NO_ACTION','今天不增加行动','只保留这次看见。',0,0,'["MICRO_ONLY","NORMAL","REFLECTION_ONLY","STORE_ONLY"]','["NONE","LOW"]','NO_ACTION','1.0','[]','[]')
ON CONFLICT(template_key,version) DO NOTHING;

-- Owner RLS is defense in depth. Application queries also include email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_reflection_contexts','formation_twin_reflection_mirrors',
    'formation_twin_reflection_questions','formation_twin_reflection_answers',
    'formation_twin_intervention_proposals','formation_twin_intervention_decisions',
    'formation_twin_intervention_executions','formation_twin_intervention_effect_reviews',
    'formation_twin_intervention_preferences','formation_twin_weekly_reviews',
    'formation_twin_reflection_settings'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
