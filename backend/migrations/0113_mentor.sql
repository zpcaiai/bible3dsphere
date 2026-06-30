-- Migration 0113: 导师陪跑 Mentor Coaching（B7 Skill 27）
-- 成熟信徒/牧者/小组长按 consent 范围陪伴成长：关系、会面、成长观察、提问库、行动计划、回顾。
-- 同意优先:调用者必须是 mentee 或 mentor 本人;观察按 visible_to_mentee 控制。email 标识用户。

CREATE TABLE IF NOT EXISTS mentor_relationships (
    id                VARCHAR(64)  PRIMARY KEY,
    mentee_email      VARCHAR(255) NOT NULL,
    mentor_email      VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(20)  DEFAULT 'mentor',  -- mentor/pastor/group_leader/coach/discipler/peer_mentor
    status            VARCHAR(12)  DEFAULT 'requested',-- requested/active/paused/ended/revoked
    permission_scope  VARCHAR(24)  DEFAULT 'session_only', -- session_only/growth_summary/formation_dashboard/care_flags
    goals             JSONB        DEFAULT '[]'::jsonb,
    start_date        DATE,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mentor_rel_mentee ON mentor_relationships (mentee_email, status);
CREATE INDEX IF NOT EXISTS idx_mentor_rel_mentor ON mentor_relationships (mentor_email, status);

CREATE TABLE IF NOT EXISTS mentor_sessions (
    id              VARCHAR(64)  PRIMARY KEY,
    relationship_id VARCHAR(64)  NOT NULL,
    mentee_email    VARCHAR(255) NOT NULL,
    mentor_email    VARCHAR(255) NOT NULL,
    session_date    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    session_type    VARCHAR(24)  DEFAULT 'checkin',
    agenda          JSONB        DEFAULT '[]'::jsonb,
    summary         TEXT         DEFAULT '',
    prayer_notes    TEXT         DEFAULT '',
    action_items    JSONB        DEFAULT '[]'::jsonb,
    risk_flags      JSONB        DEFAULT '[]'::jsonb,
    status          VARCHAR(12)  DEFAULT 'planned',  -- planned/completed/cancelled/missed
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mentor_sessions_rel ON mentor_sessions (relationship_id, session_date DESC);

CREATE TABLE IF NOT EXISTS mentor_growth_observations (
    id                   VARCHAR(64)  PRIMARY KEY,
    relationship_id      VARCHAR(64)  NOT NULL,
    mentee_email         VARCHAR(255) NOT NULL,
    mentor_email         VARCHAR(255) NOT NULL,
    observation_date     DATE         DEFAULT CURRENT_DATE,
    observation_type     VARCHAR(24)  DEFAULT 'encouragement',
    title                VARCHAR(200) DEFAULT '',
    description          TEXT         DEFAULT '',
    recommended_next_step TEXT        DEFAULT '',
    visible_to_mentee    BOOLEAN      DEFAULT TRUE,
    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mentor_obs_rel ON mentor_growth_observations (relationship_id, observation_date DESC);

CREATE TABLE IF NOT EXISTS mentor_action_plans (
    id              VARCHAR(64)  PRIMARY KEY,
    relationship_id VARCHAR(64)  NOT NULL,
    mentee_email    VARCHAR(255) NOT NULL,
    mentor_email    VARCHAR(255) NOT NULL,
    title           VARCHAR(200) NOT NULL,
    description     TEXT         DEFAULT '',
    plan_type       VARCHAR(20)  DEFAULT 'habit',
    actions         JSONB        DEFAULT '[]'::jsonb,
    review_date     DATE,
    status          VARCHAR(12)  DEFAULT 'active',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mentor_plans_rel ON mentor_action_plans (relationship_id, status);

CREATE TABLE IF NOT EXISTS mentor_questions (
    id                VARCHAR(64)  PRIMARY KEY,
    question_text     TEXT         NOT NULL,
    question_category VARCHAR(20)  DEFAULT 'heart',
    difficulty        VARCHAR(12)  DEFAULT 'normal',
    active            BOOLEAN      DEFAULT TRUE,
    sort_order        INT          DEFAULT 0
);

INSERT INTO mentor_questions (id, question_text, question_category, sort_order) VALUES
 ('mq_heart1','这段时间你的心最被什么占据？','heart',1),
 ('mq_heart2','哪里你感到与神亲近，哪里感到遥远？','heart',2),
 ('mq_gospel1','此刻福音的哪一部分是你最需要重新听见的？','gospel',3),
 ('mq_gospel2','你在哪些地方还在靠表现换取被接纳？','gospel',4),
 ('mq_prayer1','你的祷告生活现在是怎样的？哪里卡住了？','prayer',5),
 ('mq_prayer2','有什么是你一直不敢向神说出口的？','prayer',6),
 ('mq_scripture1','最近哪段经文对你说话？','scripture',7),
 ('mq_scripture2','读经对你此刻是生命还是负担？','scripture',8),
 ('mq_virtue1','神最近在你身上培养哪一样品格？','virtue',9),
 ('mq_virtue2','哪一样美德你愿意更深操练？','virtue',10),
 ('mq_vice1','有没有一个反复出现的挣扎模式？','vice',11),
 ('mq_vice2','它通常在什么处境、什么情绪下出现？','vice',12),
 ('mq_habits1','哪个属灵习惯对你是生命的，哪个成了负担？','habits',13),
 ('mq_habits2','需要简化或恢复哪一个操练？','habits',14),
 ('mq_calling1','你最近感到为什么人或什么事有负担？','calling',15),
 ('mq_calling2','你在哪里服事时最有生命、也结果子？','calling',16),
 ('mq_relationship1','哪段关系现在需要修复或界限？','relationships',17),
 ('mq_relationship2','你在关系里更倾向讨好、退缩还是掌控？','relationships',18),
 ('mq_suffering1','你现在正在承受什么？神在其中似乎在哪里？','suffering',19),
 ('mq_suffering2','你允许自己在神面前哀伤吗？','suffering',20),
 ('mq_leadership1','带领中哪里你被试探用掌控或形象？','leadership',21),
 ('mq_leadership2','谁在你的生命里有权柄向你说真话？','leadership',22),
 ('mq_mission1','在日常（工作/家庭/邻舍）你如何活出见证？','mission',23),
 ('mq_mission2','有没有把使命做成另一种效率偶像的危险？','mission',24)
ON CONFLICT (id) DO NOTHING;
