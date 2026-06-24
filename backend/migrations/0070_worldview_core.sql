-- 0070_worldview_core.sql
-- Worldview Formation OS — 世界观诊断核心层 (Kingdom Lens OS)
-- 键以 email 为准，与本仓库其余表 (attachment_*, gift_*, agent_runs) 一致。
-- 幂等：CREATE TABLE/INDEX IF NOT EXISTS + INSERT ... ON CONFLICT DO NOTHING。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 12 个世界观领域目录 ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_domains (
    domain              TEXT PRIMARY KEY,
    display_name        TEXT NOT NULL,
    description         TEXT,
    key_questions       JSONB DEFAULT '[]',
    biblical_themes     JSONB DEFAULT '[]',
    common_distortions  JSONB DEFAULT '[]',
    common_idols        JSONB DEFAULT '[]',
    sort_order          INT DEFAULT 0,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- 世界观问题库 ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_question_bank (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain                  TEXT NOT NULL,
    question_text           TEXT NOT NULL,
    question_type           TEXT DEFAULT 'open',
    options                 JSONB DEFAULT '[]',
    theological_intent      TEXT,
    detects_idol_categories JSONB DEFAULT '[]',
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wv_question_bank_domain ON worldview_question_bank(domain);

-- 用户当前世界观画像 (每人一行) -----------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_profiles (
    email                    TEXT PRIMARY KEY,
    summary                  TEXT,
    dimension_views          JSONB DEFAULT '{}',
    dominant_idols           JSONB DEFAULT '[]',
    distorted_beliefs        JSONB DEFAULT '[]',
    biblical_alignment_score NUMERIC(5,2),
    maturity_level           INT DEFAULT 1,
    strongest_domains        JSONB DEFAULT '[]',
    weakest_domains          JSONB DEFAULT '[]',
    current_growth_focus     TEXT,
    risk_level               TEXT DEFAULT 'green',
    last_assessed_at         TIMESTAMPTZ,
    created_at               TIMESTAMPTZ DEFAULT now(),
    updated_at               TIMESTAMPTZ DEFAULT now()
);

-- 每次诊断记录 ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_assessments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT NOT NULL,
    assessment_type     TEXT NOT NULL DEFAULT 'auto',
    source_type         TEXT,
    raw_input_summary   TEXT,
    detected_domains    JSONB DEFAULT '[]',
    detected_idols      JSONB DEFAULT '[]',
    detected_distortions JSONB DEFAULT '[]',
    agent_outputs       JSONB DEFAULT '{}',
    overall_score       NUMERIC(5,2),
    confidence          NUMERIC(5,2),
    risk_level          TEXT DEFAULT 'green',
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wv_assessments_email ON worldview_assessments(email);
CREATE INDEX IF NOT EXISTS idx_wv_assessments_created ON worldview_assessments(created_at);

-- 维度评分 (雷达图来源) -------------------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_dimension_scores (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 TEXT NOT NULL,
    assessment_id         UUID,
    domain                TEXT NOT NULL,
    score                 NUMERIC(5,2),
    confidence            NUMERIC(5,2),
    evidence              JSONB DEFAULT '[]',
    distortion_patterns   JSONB DEFAULT '[]',
    growth_recommendation TEXT,
    created_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wv_dimscores_email_domain ON worldview_dimension_scores(email, domain);

-- 原始回应 (问卷/日记/祷告/聊天) ----------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_responses (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT NOT NULL,
    question_id       UUID,
    source_type       TEXT NOT NULL,
    raw_response      TEXT NOT NULL,
    detected_beliefs  JSONB DEFAULT '[]',
    detected_emotions JSONB DEFAULT '[]',
    detected_idols    JSONB DEFAULT '[]',
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wv_responses_email ON worldview_responses(email);

-- 底层信念 --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_beliefs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 TEXT NOT NULL,
    assessment_id         UUID,
    domain                TEXT NOT NULL,
    belief_statement      TEXT NOT NULL,
    belief_type           TEXT,
    belief_status         TEXT DEFAULT 'detected',
    confidence            NUMERIC(5,2),
    source_text_excerpt   TEXT,
    emotional_fruit       JSONB DEFAULT '[]',
    behavioral_fruit      JSONB DEFAULT '[]',
    biblical_evaluation   TEXT,
    related_scripture_refs JSONB DEFAULT '[]',
    first_detected_at     TIMESTAMPTZ DEFAULT now(),
    last_seen_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wv_beliefs_email_domain ON worldview_beliefs(email, domain);
CREATE INDEX IF NOT EXISTS idx_wv_beliefs_status ON worldview_beliefs(belief_status);

-- 终极权威 / 预设 -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_presuppositions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT NOT NULL,
    belief_id           UUID,
    presupposition_text TEXT NOT NULL,
    assumed_authority   TEXT,
    ultimate_standard   TEXT,
    biblical_challenge  TEXT,
    gospel_reframe      TEXT,
    confidence          NUMERIC(5,2),
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wv_presupp_email ON worldview_presuppositions(email);

-- 长期雷达图快照 --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS worldview_metric_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT NOT NULL,
    snapshot_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    scores              JSONB DEFAULT '{}',
    dominant_idols      JSONB DEFAULT '[]',
    active_growth_focus JSONB DEFAULT '[]',
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(email, snapshot_date)
);
CREATE INDEX IF NOT EXISTS idx_wv_snapshots_email_date ON worldview_metric_snapshots(email, snapshot_date);

-- ── 种子：12 个世界观领域 ───────────────────────────────────────────────────
INSERT INTO worldview_domains (domain, display_name, description, key_questions, common_distortions, common_idols, sort_order) VALUES
 ('god',          '神观',   '用户如何理解神的属性、主权、信实与同在。',
   '["神是谁？","神是否信实可靠？","神在我的苦难中在哪里？"]',
   '["神是严厉的债主","神靠不住","神只在我表现好时爱我"]', '["spiritual_performance","control"]', 1),
 ('self',         '自我观', '用户如何理解自己的价值、身份与有限性。',
   '["我是谁？","我的价值从何而来？"]',
   '["价值取决于成就","必须掌控才安全"]', '["success","control"]', 2),
 ('sin',          '罪观',   '用户如何理解罪、羞耻、内疚与悔改。',
   '["罪是什么？","羞耻与认罪有何不同？"]',
   '["罪不过是软弱","我无可救药"]', '["self_realization"]', 3),
 ('salvation',    '救恩观', '用户如何理解恩典、称义与接纳。',
   '["我凭什么被神接纳？","得救靠恩典还是靠行为？"]',
   '["要靠表现赚取救恩"]', '["spiritual_performance"]', 4),
 ('suffering',    '苦难观', '用户如何理解痛苦、失去、神的护理与盼望。',
   '["神为何允许苦难？","苦难有意义吗？"]',
   '["苦难=神离弃","人生无意义"]', '["victimhood","control"]', 5),
 ('money',        '金钱观', '用户如何理解安全感、财富、奉献与管家职分。',
   '["钱是安全感来源吗？","奉献意味着什么？"]',
   '["钱=安全","财富=价值"]', '["money","security"]', 6),
 ('work',         '工作观', '用户如何理解工作、成就、呼召与成功。',
   '["工作是咒诅还是使命？","成功定义我吗？"]',
   '["成就定义价值","必须赢过别人"]', '["success","control"]', 7),
 ('relationship', '关系观', '用户如何理解爱、认可、孤独与界限。',
   '["被爱决定我的价值吗？","我能在神里独自完整吗？"]',
   '["被认可才有价值","没有某人就崩溃"]', '["relationship","approval"]', 8),
 ('technology',   '技术观', '用户如何理解 AI、技术、效率、控制与人的有限性。',
   '["技术是工具还是救主？","AI 会取代我的价值吗？"]',
   '["技术救世主义","效率至上","以掌控代替信靠"]', '["technology","control","knowledge"]', 9),
 ('history',      '历史观', '用户如何理解时代、文化、进步与神的护理。',
   '["历史走向何方？","进步等于救赎吗？"]',
   '["进步主义","文化决定论"]', '["national_political"]', 10),
 ('eternity',     '永恒观', '用户如何理解死亡、永恒、终末与意义。',
   '["死后有什么？","什么是终极盼望？"]',
   '["此生即一切","虚无主义"]', '["pleasure","comfort"]', 11),
 ('mission',      '使命观', '用户如何理解呼召、服事、福音与国度。',
   '["我为何而活？","我的使命是什么？"]',
   '["使命=自我实现","服事换取认可"]', '["self_realization","spiritual_performance"]', 12)
ON CONFLICT (domain) DO NOTHING;

-- ── 种子：少量诊断问题 (open) ───────────────────────────────────────────────
INSERT INTO worldview_question_bank (domain, question_text, theological_intent, detects_idol_categories) VALUES
 ('self',         '我最近最害怕失去什么？为什么？',                 '探测身份与安全感的真实来源', '["success","control","security"]'),
 ('money',        '如果收入减少一半，我最怕失去的是物质，还是「我能掌控」的感觉？', '区分供应观与掌控偶像', '["money","control"]'),
 ('technology',   '当我想到 AI 与未来，我的第一反应是盼望、好奇，还是恐惧？',   '探测技术救世/技术恐惧', '["technology","control"]'),
 ('work',         '如果这件事失败了，我还相信自己在神面前有价值吗？',       '探测成就主义', '["success"]'),
 ('suffering',    '在最近的痛苦里，我感觉神在哪里？',                 '探测苦难观与神观', '["victimhood"]'),
 ('god',          '我相信神接纳我，是因为基督，还是因为我的表现？',         '探测因信称义 vs 属灵表现', '["spiritual_performance"]')
ON CONFLICT DO NOTHING;
