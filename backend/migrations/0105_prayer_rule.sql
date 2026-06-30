-- Migration 0105: 固定祷告规则 / 每日祷告节奏 Prayer Rule（B2 Skill 05）
-- 帮助用户建立简单的祷告生活规则（晨/午/晚/睡前/安息日…）。
-- 焦点是与神相交、忠心、感恩、依靠，而非表现。错过不定罪，鼓励小而稳。email 标识用户。

CREATE TABLE IF NOT EXISTS prayer_templates (
    id              VARCHAR(64)  PRIMARY KEY,
    title           VARCHAR(120) NOT NULL,
    tradition_tag   VARCHAR(40)  DEFAULT 'simple',
    template_type   VARCHAR(24)  DEFAULT 'custom',  -- adoration/confession/thanksgiving/supplication/examen/scripture_prayer/lord_prayer/custom
    body            TEXT         DEFAULT '',
    scripture_refs  JSONB        DEFAULT '[]'::jsonb,
    public          BOOLEAN      DEFAULT TRUE,
    created_by_email VARCHAR(255) DEFAULT '',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prayer_rules (
    id          VARCHAR(64)  PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    title       VARCHAR(120) DEFAULT '我的祷告规则',
    description TEXT         DEFAULT '',
    rule_type   VARCHAR(20)  DEFAULT 'daily',   -- daily/weekly/seasonal/fasting/retreat/custom
    active      BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_prayer_rules_email ON prayer_rules (email, active);

CREATE TABLE IF NOT EXISTS prayer_rule_slots (
    id               VARCHAR(64)  PRIMARY KEY,
    email            VARCHAR(255) NOT NULL,
    rule_id          VARCHAR(64)  NOT NULL,
    slot_key         VARCHAR(24)  DEFAULT 'morning', -- morning/midday/evening/before_work/before_sleep/sabbath/custom
    display_name     VARCHAR(80)  DEFAULT '',
    target_time      TIME,
    duration_minutes INT          DEFAULT 5,
    template_id      VARCHAR(64)  DEFAULT '',
    enabled          BOOLEAN      DEFAULT TRUE,
    sort_order       INT          DEFAULT 0,
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_prayer_slots_rule ON prayer_rule_slots (rule_id, sort_order);

CREATE TABLE IF NOT EXISTS prayer_rule_sessions (
    id               VARCHAR(64)  PRIMARY KEY,
    email            VARCHAR(255) NOT NULL,
    rule_id          VARCHAR(64)  DEFAULT '',
    slot_id          VARCHAR(64)  DEFAULT '',
    session_date     DATE         NOT NULL,
    started_at       TIMESTAMP,
    completed_at     TIMESTAMP,
    duration_minutes INT,
    prayer_text      TEXT         DEFAULT '',
    gratitude_items  JSONB        DEFAULT '[]'::jsonb,
    confession_items JSONB        DEFAULT '[]'::jsonb,
    petitions        JSONB        DEFAULT '[]'::jsonb,
    grace_received   TEXT         DEFAULT '',
    status           VARCHAR(12)  DEFAULT 'started',  -- started/completed/skipped/interrupted
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_prayer_rule_sessions_email_date ON prayer_rule_sessions (email, session_date DESC);

INSERT INTO prayer_templates (id, title, tradition_tag, template_type, body, scripture_refs) VALUES
 ('pt_morning',     '晨祷 · 交托',       'simple',  'adoration',       '父啊，我从你手中领受这一天。我把今天的时间、工作与所遇的人交在你手中。求你今天引导我，使我忠心、诚实、有爱。', '["哀3:22-23"]'),
 ('pt_midday',      '午间 · 临在',       'simple',  'examen',          '主耶稣基督，怜悯我。在今天的忙碌中，求你提醒我你一直与我同在。让我停下片刻，重新把心转向你。', '["诗46:10"]'),
 ('pt_evening',     '晚祷 · 感恩与安息', 'simple',  'thanksgiving',    '主啊，谢谢你今天的恩典。我数算你给的礼物，也把今天的亏欠交托给你。求你赦免，让我在你里面安歇。', '["诗4:8"]'),
 ('pt_confession',  '认罪祷告',          'biblical','confession',      '主啊，我承认我的过犯，不隐瞒、不夸大。求你按你的信实赦免我，洗净我，重新把你放在我心的中心。', '["约一1:9"]'),
 ('pt_lords',       '主祷文',            'biblical','lord_prayer',     '我们在天上的父，愿人都尊你的名为圣。愿你的国降临，愿你的旨意行在地上，如同行在天上。我们日用的饮食，今日赐给我们。免我们的债，如同我们免了人的债。不叫我们遇见试探，救我们脱离凶恶。', '["太6:9-13"]'),
 ('pt_ps23',        '诗篇23祷告',        'psalm',   'scripture_prayer','耶和华是我的牧者，我必不至缺乏。求你使我躺卧在青草地上，领我在可安歇的水边，使我的灵魂苏醒。我虽行过死荫幽谷，因你与我同在，也不怕遭害。', '["诗23"]'),
 ('pt_ps51',        '诗篇51悔改',        'psalm',   'confession',      '神啊，求你按你的慈爱怜恤我，涂抹我的过犯。求你为我造清洁的心，使我里面重新有正直的灵，使我仍得救恩之乐。', '["诗51"]'),
 ('pt_intercession','代祷',              'simple',  'supplication',    '父啊，我把以下的人交托给你（在此一一提名）。求你按你的良善与智慧，怜悯、医治、保守、引导他们。我把结果交在你手中。', '["提前2:1"]'),
 ('pt_sabbath',     '安息祷告',          'simple',  'adoration',       '主啊，我停下手中的工，向你支取安息。我不靠效率证明自己的价值，乃在你里面被爱、被接纳。求你今天更新我的身心灵。', '["太11:28"]'),
 ('pt_work',        '工作奉献',          'simple',  'supplication',    '主啊，我把今天的工作献给你。使我做工诚实、卓越、不焦虑，待人公平有爱。愿我的劳碌成为对你的敬拜。', '["西3:23"]')
ON CONFLICT (id) DO NOTHING;
