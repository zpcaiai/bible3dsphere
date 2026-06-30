-- Migration 0103: 使命生活设计 Mission Life Design（B8）
-- 把基督的使命整合进日常：职业、家庭、邻舍、款待、怜悯、传福音、教会、宣教、
-- 金钱、时间、技能、科技、创作、学习、祷告、安息。不是要人人全职服事，
-- 而是全人在神面前的管家职分。内建过载护栏：忙碌/burnout 时先安息再扩张。
-- email 标识用户。

CREATE TABLE IF NOT EXISTS mission_domains (
    domain_key    VARCHAR(40)  PRIMARY KEY,
    display_name  VARCHAR(80)  NOT NULL,
    description   TEXT         DEFAULT '',
    examples      JSONB        DEFAULT '[]'::jsonb,
    sort_order    INT          DEFAULT 0,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mission_life_profiles (
    id                   VARCHAR(64)  PRIMARY KEY,
    email                VARCHAR(255) NOT NULL,
    title                VARCHAR(120) DEFAULT '使命生活',
    life_season          VARCHAR(30)  DEFAULT 'single_worker',
    vocation_summary     TEXT         DEFAULT '',
    family_context       TEXT         DEFAULT '',
    work_context         TEXT         DEFAULT '',
    neighborhood_context TEXT         DEFAULT '',
    key_constraints      JSONB        DEFAULT '[]'::jsonb,
    key_opportunities    JSONB        DEFAULT '[]'::jsonb,
    mission_summary      TEXT         DEFAULT '',
    status               VARCHAR(20)  DEFAULT 'active',
    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mission_profiles_email ON mission_life_profiles (email, created_at DESC);

CREATE TABLE IF NOT EXISTS mission_commitments (
    id                VARCHAR(64)  PRIMARY KEY,
    email             VARCHAR(255) NOT NULL,
    profile_id        VARCHAR(64)  DEFAULT '',
    domain_key        VARCHAR(40)  DEFAULT '',
    title             VARCHAR(160) DEFAULT '',
    description       TEXT         DEFAULT '',
    frequency         VARCHAR(20)  DEFAULT 'weekly',   -- daily/weekly/monthly/seasonal/situational
    minimum_action    TEXT         DEFAULT '',
    normal_action     TEXT         DEFAULT '',
    stretch_action    TEXT         DEFAULT '',
    status            VARCHAR(20)  DEFAULT 'active',
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mission_commitments_email ON mission_commitments (email, status);

CREATE TABLE IF NOT EXISTS mission_projects (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    title         VARCHAR(160) NOT NULL,
    description   TEXT         DEFAULT '',
    project_type  VARCHAR(30)  DEFAULT 'personal',
    desired_fruit JSONB        DEFAULT '[]'::jsonb,
    status        VARCHAR(20)  DEFAULT 'active',
    start_date    DATE,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mission_projects_email ON mission_projects (email, status);

CREATE TABLE IF NOT EXISTS mission_project_logs (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    project_id    VARCHAR(64)  NOT NULL,
    log_date      DATE         NOT NULL,
    action_taken  TEXT         DEFAULT '',
    fruit_observed JSONB       DEFAULT '[]'::jsonb,
    obstacles     TEXT         DEFAULT '',
    next_step     TEXT         DEFAULT '',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mission_logs_project ON mission_project_logs (project_id, log_date DESC);

INSERT INTO mission_domains (domain_key, display_name, description, examples, sort_order) VALUES
 ('workplace_witness',   '职场见证', '在工作中以卓越、诚实、不焦虑、公平待人来荣耀神。', '["开工前一句奉献祷告","诚实地说话","公平待人","以卓越事奉神"]', 1),
 ('family_discipleship', '家庭门训', '在家中以祷告、圣经对话、忍耐与祝福来牧养所爱的人。', '["饭前祷告","与家人聊一句神的话","操练忍耐","祝福孩子/配偶/父母"]', 2),
 ('neighborhood_presence','邻舍同在', '在所住之地稳定地出现、记住名字、提供实际帮助。', '["认识一个邻居的名字","规律地出现","提供实际帮助"]', 3),
 ('hospitality',         '款待', '以简单的饭食或咖啡向人敞开家与生命。', '["每月邀一个人吃便饭","发出一个邀请"]', 4),
 ('mercy_justice',       '怜悯与公义', '关怀软弱者、被忽略者，行公义、好怜悯。', '["探望一个孤单的人","参与一次怜悯服事"]', 5),
 ('evangelism',          '传福音', '以祷告、友谊与诚实的见证向人介绍基督。', '["为一位朋友祷告","一次真诚的属灵对话"]', 6),
 ('church_service',      '教会服事', '在地方教会以恩赐服事身体，不过度承诺。', '["每月一次服事","观摩一个事工"]', 7),
 ('global_mission',      '普世宣教', '以祷告、奉献、关系支持普世福音工作。', '["为一个工人/族群祷告","定期奉献给宣教"]', 8),
 ('money_stewardship',   '金钱管家', '以慷慨、简朴、感恩管理金钱，抵抗贪婪。', '["一个慷慨计划","简朴审视","感恩日记"]', 9),
 ('time_stewardship',    '时间管家', '把时间献给神，分别优先次序，留出安息。', '["保护安息时段","优先次序排序"]', 10),
 ('skill_stewardship',   '技能管家', '把专业技能作为服事与祝福他人的器皿。', '["用技能帮一个人","开发一个造就人的工具"]', 11),
 ('technology_mission',  '科技使命', '以智慧、节制、伦理使用科技，并用它造就人。', '["数字节制","用科技服事造就","伦理地使用AI"]', 12),
 ('creative_mission',    '创作使命', '以创作（写作、音乐、艺术）指向真善美。', '["一个造就人的创作项目"]', 13),
 ('learning_teaching',   '学习与教导', '持续学习真理，并把所学传递给他人。', '["一个学习计划","教导/陪读一个人"]', 14),
 ('prayer_mission',      '祷告使命', '以代祷托住人、城市、族群与教会。', '["代祷名单","固定代祷时段"]', 15),
 ('rest_as_witness',     '安息为证', '以安息抵挡效率偶像，向世界见证神的信实。', '["守安息日","不焦虑的界限","拒绝把生产力当神"]', 16)
ON CONFLICT (domain_key) DO NOTHING;
