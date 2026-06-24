-- 0090_worldview_decision_formation.sql
-- Worldview Formation OS — 决策塑造 + 操练闭环（库/计划/任务/日志）
-- 幂等；email 为用户键。worldview_metric_snapshots 已在 0070 建立。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 决策案例 --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decision_cases (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                       TEXT NOT NULL,
    decision_title              TEXT NOT NULL,
    decision_context            TEXT NOT NULL,
    options                     JSONB DEFAULT '[]',
    detected_motives            JSONB DEFAULT '[]',
    detected_fears              JSONB DEFAULT '[]',
    detected_idols              JSONB DEFAULT '[]',
    biblical_values             JSONB DEFAULT '[]',
    wisdom_questions            JSONB DEFAULT '[]',
    red_flags                   JSONB DEFAULT '[]',
    counsel_needed              BOOLEAN DEFAULT FALSE,
    recommended_people_to_consult JSONB DEFAULT '[]',
    discernment_summary         TEXT,
    next_faithful_step          TEXT,
    final_user_decision         TEXT,
    created_at                  TIMESTAMPTZ DEFAULT now(),
    updated_at                  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_decision_cases_email ON decision_cases(email);

-- 操练库 ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS formation_practice_library (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    practice_key        TEXT UNIQUE NOT NULL,
    title               TEXT NOT NULL,
    description         TEXT,
    target_idols        JSONB DEFAULT '[]',
    target_domains      JSONB DEFAULT '[]',
    duration_days       INT DEFAULT 1,
    difficulty_level    INT DEFAULT 1,
    instructions        JSONB DEFAULT '[]',
    scripture_refs      JSONB DEFAULT '[]',
    reflection_questions JSONB DEFAULT '[]',
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- 操练计划 (7/30/90 天) -------------------------------------------------------
CREATE TABLE IF NOT EXISTS formation_plans (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT NOT NULL,
    title             TEXT NOT NULL,
    description       TEXT,
    duration_days     INT NOT NULL,
    intensity         TEXT DEFAULT 'normal',
    focus_domains     JSONB DEFAULT '[]',
    focus_idols       JSONB DEFAULT '[]',
    focus_beliefs     JSONB DEFAULT '[]',
    review_questions  JSONB DEFAULT '[]',
    success_markers   JSONB DEFAULT '[]',
    warning_signs     JSONB DEFAULT '[]',
    start_date        DATE,
    end_date          DATE,
    status            TEXT DEFAULT 'active',
    generated_by_agent TEXT DEFAULT 'formation_practice',
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_plans_email ON formation_plans(email);

-- 操练任务 --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS formation_tasks (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT NOT NULL,
    plan_id           UUID,
    practice_key      TEXT,
    day_index         INT,
    title             TEXT NOT NULL,
    instructions      TEXT,
    expected_minutes  INT,
    scripture_refs    JSONB DEFAULT '[]',
    reflection_prompt TEXT,
    status            TEXT DEFAULT 'pending',
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_tasks_email_status ON formation_tasks(email, status);
CREATE INDEX IF NOT EXISTS idx_formation_tasks_plan ON formation_tasks(plan_id);

-- 操练完成记录 ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS formation_task_logs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                TEXT NOT NULL,
    task_id              UUID,
    completed            BOOLEAN DEFAULT FALSE,
    user_reflection      TEXT,
    emotion_before       JSONB DEFAULT '{}',
    emotion_after        JSONB DEFAULT '{}',
    perceived_helpfulness INT CHECK (perceived_helpfulness BETWEEN 1 AND 10),
    created_at           TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_task_logs_email ON formation_task_logs(email);

-- ── 种子：操练库 10 类 ──────────────────────────────────────────────────────
INSERT INTO formation_practice_library (practice_key, title, description, target_idols, duration_days) VALUES
 ('daily_meditation',  '每日默想',   '默想经文，记下神向你说的话与今天要交托的事。', '[]', 1),
 ('anti_idol',         '反偶像操练', '不靠成就/掌控证明自己，做隐藏的忠心行动。', '["success","control","approval","power"]', 1),
 ('repentance_prayer', '悔改祷告',   '诚实承认把受造之物当救主，转向恩典。', '["spiritual_performance"]', 1),
 ('gratitude',         '感恩记录',   '写下不是靠表现换来的恩典，对抗比较与匮乏。', '["money","victimhood"]', 1),
 ('sabbath_rest',      '安息操练',   '设定不工作不比较的安息，承认人的有限。', '["control","success","technology"]', 1),
 ('giving',            '奉献操练',   '为具体的人或事奉献，松开对掌控的手。', '["money","security"]', 1),
 ('service',           '服事行动',   '不求回报地鼓励或服事一个人。', '["success","self_realization","power"]', 1),
 ('relational_repair', '关系修复',   '向一个人表达歉意或感谢，跨出修复一步。', '["relationship","approval"]', 1),
 ('tech_temperance',   '技术节制',   '设定 AI/信息工具边界并写下使用目的。', '["technology","knowledge"]', 1),
 ('lament_prayer',     '哀歌祷告',   '向神诚实倾诉痛苦，同时抓住盼望应许。', '["victimhood"]', 1)
ON CONFLICT (practice_key) DO NOTHING;
