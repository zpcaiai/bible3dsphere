-- Migration 0069: 恩赐与呼召识别系统 (Gift & Calling OS / GCOS v1.0 — MVP3)
-- 把"识别天然优势 / 属灵恩赐 / 属灵果子 / 使命负担 / 误用风险 / 服事匹配 / 成长计划"
-- 落成一次可计算、可复盘的闭环。每次完整测评 = 一条 gift_assessments 主记录，
-- 八个子维度结果挂在该次 assessment 之下；共同体反馈与长期复盘可独立收集。
--
-- 适配本项目栈（与 disciple/crisis/formation 各 OS 一致）：
--   - 用户以 users.email 标识（不新建 users 表，不用 UUID）。
--   - 不用 PG ENUM，枚举一律 VARCHAR + 注释（沿用全库惯例）。
--   - 分数 INT(0~100) 结构化，复杂解释 JSONB；高频字段已结构化，低频先入 JSONB。
--   - updated_at 由 update_updated_at_column() 触发器维护（沿用 database_schema.sql）。
-- 幂等：所有对象使用 IF NOT EXISTS / OR REPLACE / DROP TRIGGER IF EXISTS。
--
-- 神学边界：本系统只提供"辅助辨识"，不宣告最终呼召；身份根基在基督里。
-- theological_boundary_ack 记录用户是否已确认该边界。

-- ===========================================================================
-- 0. updated_at 触发器函数（与 database_schema.sql 同名，OR REPLACE 幂等）
-- ===========================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================================================
-- 1. gift_assessments — 测评主记录（系统主表，聚合根）
--    每做一次完整"恩赐与呼召分析" → 一条记录；恩赐分析结果存 agent_outputs。
-- ===========================================================================
CREATE TABLE IF NOT EXISTS gift_assessments (
    id                       BIGSERIAL PRIMARY KEY,
    email                    VARCHAR(255) NOT NULL,                 -- 用户标识（users.email）
    assessment_type          VARCHAR(30)  NOT NULL DEFAULT 'initial',
        -- initial | reassessment | pastoral_review | community_review | ai_generated
    status                   VARCHAR(20)  NOT NULL DEFAULT 'draft',
        -- draft | in_progress | completed | archived
    version                  VARCHAR(20)  DEFAULT 'gcos1.0',
    title                    VARCHAR(200) DEFAULT '',
    summary                  TEXT         DEFAULT '',
    questionnaire_responses  JSONB        DEFAULT '{}'::jsonb,      -- 原始问卷答案
    input_sources            JSONB        DEFAULT '[]'::jsonb,      -- [{type,...}]
    agent_outputs            JSONB        DEFAULT '{}'::jsonb,      -- 各 Agent 原始结果(含 spiritual_gifts)
    confidence               VARCHAR(10)  NOT NULL DEFAULT 'medium',-- low | medium | high
    theological_boundary_ack BOOLEAN      NOT NULL DEFAULT FALSE,   -- 是否确认"非最终呼召宣告"
    completed_at             TIMESTAMP,
    created_at               TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gift_assessments_email
    ON gift_assessments(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gift_assessments_status
    ON gift_assessments(status);
CREATE INDEX IF NOT EXISTS idx_gift_assessments_email_completed
    ON gift_assessments(email, completed_at DESC) WHERE status = 'completed';

-- ===========================================================================
-- 2. strength_profiles — 天然优势画像（结构化分数 + JSONB 明细）
-- ===========================================================================
CREATE TABLE IF NOT EXISTS strength_profiles (
    id                    BIGSERIAL PRIMARY KEY,
    assessment_id         BIGINT       NOT NULL REFERENCES gift_assessments(id) ON DELETE CASCADE,
    email                 VARCHAR(255) NOT NULL,
    cognitive_score       INT CHECK (cognitive_score   BETWEEN 0 AND 100),
    expression_score      INT CHECK (expression_score  BETWEEN 0 AND 100),
    relational_score      INT CHECK (relational_score  BETWEEN 0 AND 100),
    execution_score       INT CHECK (execution_score   BETWEEN 0 AND 100),
    creativity_score      INT CHECK (creativity_score  BETWEEN 0 AND 100),
    leadership_score      INT CHECK (leadership_score  BETWEEN 0 AND 100),
    discernment_score     INT CHECK (discernment_score BETWEEN 0 AND 100),
    learning_score        INT CHECK (learning_score    BETWEEN 0 AND 100),
    technical_score       INT CHECK (technical_score   BETWEEN 0 AND 100),
    resilience_score      INT CHECK (resilience_score  BETWEEN 0 AND 100),
    core_strengths        JSONB DEFAULT '[]'::jsonb,   -- [{name,score,evidence[],possible_use[]}]
    secondary_strengths   JSONB DEFAULT '[]'::jsonb,
    underdeveloped_areas  JSONB DEFAULT '[]'::jsonb,
    skill_assets          JSONB DEFAULT '[]'::jsonb,    -- 后天技能
    personality_tendencies JSONB DEFAULT '[]'::jsonb,
    evidence_summary      TEXT DEFAULT '',
    summary               TEXT DEFAULT '',
    confidence            VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assessment_id)
);
CREATE INDEX IF NOT EXISTS idx_strength_profiles_email ON strength_profiles(email);
CREATE INDEX IF NOT EXISTS idx_strength_profiles_core_gin
    ON strength_profiles USING GIN(core_strengths);

-- ===========================================================================
-- 3. fruit_scores — 圣灵果子成熟度（防止系统只看"能力/恩赐"）
-- ===========================================================================
CREATE TABLE IF NOT EXISTS fruit_scores (
    id                   BIGSERIAL PRIMARY KEY,
    assessment_id        BIGINT       NOT NULL REFERENCES gift_assessments(id) ON DELETE CASCADE,
    email                VARCHAR(255) NOT NULL,
    love_score           INT CHECK (love_score         BETWEEN 0 AND 100),
    joy_score            INT CHECK (joy_score          BETWEEN 0 AND 100),
    peace_score          INT CHECK (peace_score        BETWEEN 0 AND 100),
    patience_score       INT CHECK (patience_score     BETWEEN 0 AND 100),
    kindness_score       INT CHECK (kindness_score     BETWEEN 0 AND 100),
    goodness_score       INT CHECK (goodness_score     BETWEEN 0 AND 100),
    faithfulness_score   INT CHECK (faithfulness_score BETWEEN 0 AND 100),
    gentleness_score     INT CHECK (gentleness_score   BETWEEN 0 AND 100),
    self_control_score   INT CHECK (self_control_score BETWEEN 0 AND 100),
    average_score        NUMERIC(5,2) DEFAULT 0,
    supporting_fruits    JSONB DEFAULT '[]'::jsonb,    -- 较成熟的果子
    growth_fruits        JSONB DEFAULT '[]'::jsonb,    -- 需要操练的果子
    gift_fruit_alignment JSONB DEFAULT '[]'::jsonb,    -- [{gift_or_strength,supporting_fruits[],current_risk,growth_practice}]
    red_flags            JSONB DEFAULT '[]'::jsonb,
    evidence_summary     TEXT DEFAULT '',
    pastoral_note        TEXT DEFAULT '',
    summary              TEXT DEFAULT '',
    confidence           VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assessment_id)
);
CREATE INDEX IF NOT EXISTS idx_fruit_scores_email ON fruit_scores(email);

-- ===========================================================================
-- 4. calling_patterns — 使命负担模式（记录长期反复主题，非宣告呼召）
-- ===========================================================================
CREATE TABLE IF NOT EXISTS calling_patterns (
    id                      BIGSERIAL PRIMARY KEY,
    assessment_id           BIGINT       NOT NULL REFERENCES gift_assessments(id) ON DELETE CASCADE,
    email                   VARCHAR(255) NOT NULL,
    primary_pattern         VARCHAR(120) DEFAULT '',     -- 如：护教学辨析型
    secondary_patterns      JSONB DEFAULT '[]'::jsonb,
    pattern_scores          JSONB DEFAULT '{}'::jsonb,   -- {teaching_formation:82,...}
    evidence                JSONB DEFAULT '[]'::jsonb,
    burden_groups           JSONB DEFAULT '[]'::jsonb,   -- 关心的人群
    burden_topics           JSONB DEFAULT '[]'::jsonb,   -- 关心的问题
    crossroads              JSONB DEFAULT '{}'::jsonb,   -- {strengths,gifts,burdens,opportunities}
    possible_mission_sentence TEXT DEFAULT '',
    validation_path         JSONB DEFAULT '[]'::jsonb,   -- 如何验证使命
    warnings                JSONB DEFAULT '[]'::jsonb,
    confidence              VARCHAR(10) NOT NULL DEFAULT 'medium',
    summary                 TEXT DEFAULT '',
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assessment_id)
);
CREATE INDEX IF NOT EXISTS idx_calling_patterns_email ON calling_patterns(email);
CREATE INDEX IF NOT EXISTS idx_calling_patterns_primary ON calling_patterns(primary_pattern);
CREATE INDEX IF NOT EXISTS idx_calling_patterns_scores_gin
    ON calling_patterns USING GIN(pattern_scores);

-- ===========================================================================
-- 5. community_feedback — 共同体反馈（牧者/同工/被服事者/家人，支持匿名）
--    可挂某次 assessment（ON DELETE SET NULL），也可独立收集。
-- ===========================================================================
CREATE TABLE IF NOT EXISTS community_feedback (
    id                       BIGSERIAL PRIMARY KEY,
    email                    VARCHAR(255) NOT NULL,                -- 被反馈者
    assessment_id            BIGINT REFERENCES gift_assessments(id) ON DELETE SET NULL,
    source_type              VARCHAR(30) NOT NULL DEFAULT 'other',
        -- self|pastor|elder|small_group_leader|coworker|recipient|family|friend|mentor|other
    source_alias             VARCHAR(120) DEFAULT '',             -- 不存真实姓名（除非授权）
    source_contact           VARCHAR(255) DEFAULT '',
    is_anonymous             BOOLEAN NOT NULL DEFAULT TRUE,
    relationship_description TEXT DEFAULT '',
    form_version             VARCHAR(20) DEFAULT 'gcos1.0',
    scores                   JSONB DEFAULT '{}'::jsonb,           -- {clarity,edification,love,humility,...} 1~5
    confirmed_strengths      JSONB DEFAULT '[]'::jsonb,
    confirmed_gifts          JSONB DEFAULT '[]'::jsonb,
    concern_areas            JSONB DEFAULT '[]'::jsonb,
    free_text_feedback       TEXT DEFAULT '',
    suggested_ministry_roles JSONB DEFAULT '[]'::jsonb,
    maturity_observations    TEXT DEFAULT '',
    risk_observations        TEXT DEFAULT '',
    consent_given            BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_community_feedback_email
    ON community_feedback(email, submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_feedback_assessment
    ON community_feedback(assessment_id);
CREATE INDEX IF NOT EXISTS idx_community_feedback_source ON community_feedback(source_type);
CREATE INDEX IF NOT EXISTS idx_community_feedback_scores_gin
    ON community_feedback USING GIN(scores);

-- ===========================================================================
-- 6. misuse_risks — 恩赐误用风险（知识骄傲/控制欲/批判>建造/效率偶像…）
-- ===========================================================================
CREATE TABLE IF NOT EXISTS misuse_risks (
    id                     BIGSERIAL PRIMARY KEY,
    assessment_id          BIGINT       NOT NULL REFERENCES gift_assessments(id) ON DELETE CASCADE,
    email                  VARCHAR(255) NOT NULL,
    overall_risk_score     INT CHECK (overall_risk_score BETWEEN 0 AND 100),
    top_risks              JSONB DEFAULT '[]'::jsonb,   -- [{risk,score,related_gift_or_strength,evidence[],root_possibility[],gospel_reframe,practice}]
    risk_profile           JSONB DEFAULT '{}'::jsonb,   -- {pride,control,comparison,people_pleasing,efficiency_idol}
    protective_disciplines JSONB DEFAULT '[]'::jsonb,
    community_safeguards   JSONB DEFAULT '[]'::jsonb,
    gospel_reframes        JSONB DEFAULT '[]'::jsonb,
    warning_signs          JSONB DEFAULT '[]'::jsonb,
    summary                TEXT DEFAULT '',
    confidence             VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assessment_id)
);
CREATE INDEX IF NOT EXISTS idx_misuse_risks_email ON misuse_risks(email);
CREATE INDEX IF NOT EXISTS idx_misuse_risks_overall
    ON misuse_risks(overall_risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_misuse_risks_profile_gin
    ON misuse_risks USING GIN(risk_profile);

-- ===========================================================================
-- 7. ministry_matches — 服事岗位匹配（A/B/C/D 推荐等级 + 保护机制）
-- ===========================================================================
CREATE TABLE IF NOT EXISTS ministry_matches (
    id                      BIGSERIAL PRIMARY KEY,
    assessment_id           BIGINT       NOT NULL REFERENCES gift_assessments(id) ON DELETE CASCADE,
    email                   VARCHAR(255) NOT NULL,
    top_ministry            VARCHAR(160) DEFAULT '',
    top_match_score         INT CHECK (top_match_score BETWEEN 0 AND 100),
    recommended_ministries  JSONB DEFAULT '[]'::jsonb,  -- [{ministry,level,match_score,matched_gifts[],matched_strengths[],fruit_requirements[],risks[],safeguards[],first_step}]
    experimental_ministries JSONB DEFAULT '[]'::jsonb,  -- B/C 级尝试
    not_recommended_now     JSONB DEFAULT '[]'::jsonb,  -- 当前不建议主责
    safeguards              JSONB DEFAULT '[]'::jsonb,
    church_needs_alignment  JSONB DEFAULT '{}'::jsonb,
    time_capacity_note      TEXT DEFAULT '',
    summary                 TEXT DEFAULT '',
    confidence              VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assessment_id)
);
CREATE INDEX IF NOT EXISTS idx_ministry_matches_email ON ministry_matches(email);
CREATE INDEX IF NOT EXISTS idx_ministry_matches_top ON ministry_matches(top_ministry);
CREATE INDEX IF NOT EXISTS idx_ministry_matches_recommended_gin
    ON ministry_matches USING GIN(recommended_ministries);

-- ===========================================================================
-- 8. growth_plans — 30/90/180 天成长计划（三阶段存 plan_json）
-- ===========================================================================
CREATE TABLE IF NOT EXISTS growth_plans (
    id                 BIGSERIAL PRIMARY KEY,
    assessment_id      BIGINT       NOT NULL REFERENCES gift_assessments(id) ON DELETE CASCADE,
    email              VARCHAR(255) NOT NULL,
    status             VARCHAR(20) NOT NULL DEFAULT 'not_started',
        -- not_started | active | paused | completed | cancelled
    start_date         DATE,
    target_end_date    DATE,
    plan_json          JSONB NOT NULL DEFAULT '{}'::jsonb,  -- {30_days:{...},90_days:{...},180_days:{...}}
    weekly_rhythm      JSONB DEFAULT '[]'::jsonb,           -- [{day,practice}]
    success_indicators JSONB DEFAULT '[]'::jsonb,
    warning_signs      JSONB DEFAULT '[]'::jsonb,
    current_phase      VARCHAR(20) DEFAULT '30_days',       -- 30_days | 90_days | 180_days
    progress_snapshot  JSONB DEFAULT '{}'::jsonb,
    summary            TEXT DEFAULT '',
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assessment_id)
);
CREATE INDEX IF NOT EXISTS idx_growth_plans_email ON growth_plans(email);
CREATE INDEX IF NOT EXISTS idx_growth_plans_status ON growth_plans(status);
CREATE INDEX IF NOT EXISTS idx_growth_plans_phase ON growth_plans(current_phase);
CREATE INDEX IF NOT EXISTS idx_growth_plans_plan_gin
    ON growth_plans USING GIN(plan_json);

-- ===========================================================================
-- 9. review_logs — 长期复盘（自我/Agent/牧者/共同体/月度/里程碑）
--    属灵恩赐需长期验证：每周/每月一条复盘记录。
-- ===========================================================================
CREATE TABLE IF NOT EXISTS review_logs (
    id                  BIGSERIAL PRIMARY KEY,
    email               VARCHAR(255) NOT NULL,
    assessment_id       BIGINT REFERENCES gift_assessments(id) ON DELETE SET NULL,
    growth_plan_id      BIGINT REFERENCES growth_plans(id)     ON DELETE SET NULL,
    review_type         VARCHAR(30) NOT NULL DEFAULT 'self_review',
        -- self_review | agent_review | pastoral_review | community_review | monthly_review | milestone_review
    reviewer_role       VARCHAR(30) NOT NULL DEFAULT 'self',
        -- self|pastor|elder|small_group_leader|coworker|recipient|family|friend|mentor|other
    reviewer_alias      VARCHAR(120) DEFAULT '',
    related_table       VARCHAR(60) DEFAULT '',
    related_id          BIGINT,
    review_period_start DATE,
    review_period_end   DATE,
    scores              JSONB DEFAULT '{}'::jsonb,
    completed_actions   JSONB DEFAULT '[]'::jsonb,
    unfinished_actions  JSONB DEFAULT '[]'::jsonb,
    observations        TEXT DEFAULT '',
    gratitude_notes     TEXT DEFAULT '',
    repentance_notes    TEXT DEFAULT '',
    prayer_notes        TEXT DEFAULT '',
    action_items        JSONB DEFAULT '[]'::jsonb,   -- [{action,owner,due_date}]
    next_review_at      TIMESTAMP,
    agent_summary       TEXT DEFAULT '',
    pastoral_summary    TEXT DEFAULT '',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_review_logs_email ON review_logs(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_logs_assessment ON review_logs(assessment_id);
CREATE INDEX IF NOT EXISTS idx_review_logs_growth_plan ON review_logs(growth_plan_id);
CREATE INDEX IF NOT EXISTS idx_review_logs_type ON review_logs(review_type);
CREATE INDEX IF NOT EXISTS idx_review_logs_next_review ON review_logs(next_review_at);

-- ===========================================================================
-- 10. updated_at 触发器（DROP IF EXISTS + CREATE，幂等；沿用 0056 风格）
-- ===========================================================================
DROP TRIGGER IF EXISTS update_gift_assessments_updated_at ON gift_assessments;
CREATE TRIGGER update_gift_assessments_updated_at
    BEFORE UPDATE ON gift_assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_strength_profiles_updated_at ON strength_profiles;
CREATE TRIGGER update_strength_profiles_updated_at
    BEFORE UPDATE ON strength_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_fruit_scores_updated_at ON fruit_scores;
CREATE TRIGGER update_fruit_scores_updated_at
    BEFORE UPDATE ON fruit_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_calling_patterns_updated_at ON calling_patterns;
CREATE TRIGGER update_calling_patterns_updated_at
    BEFORE UPDATE ON calling_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_community_feedback_updated_at ON community_feedback;
CREATE TRIGGER update_community_feedback_updated_at
    BEFORE UPDATE ON community_feedback
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_misuse_risks_updated_at ON misuse_risks;
CREATE TRIGGER update_misuse_risks_updated_at
    BEFORE UPDATE ON misuse_risks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ministry_matches_updated_at ON ministry_matches;
CREATE TRIGGER update_ministry_matches_updated_at
    BEFORE UPDATE ON ministry_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_growth_plans_updated_at ON growth_plans;
CREATE TRIGGER update_growth_plans_updated_at
    BEFORE UPDATE ON growth_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_review_logs_updated_at ON review_logs;
CREATE TRIGGER update_review_logs_updated_at
    BEFORE UPDATE ON review_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
