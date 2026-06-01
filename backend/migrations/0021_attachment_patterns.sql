-- Migration 0021: 偶像监测系统 — 依附强度指数 (Attachment Intensity Index)
--
-- 「偶像监测」不是要判断「你在拜偶像」，而是温柔地观测：
--   有什么东西正在取代神，成为你安全感、价值感、盼望、身份与顺服的中心。
--
-- 评分刻意不叫「偶像分」(避免定罪感)，而叫「依附强度指数」。每次省察会针对
-- 7 类「功能性偶像」中被触发的若干类，各写入一行；同一次省察共享 session_id。
--
-- 幂等：所有对象使用 IF NOT EXISTS。用户以 email 标识（沿用 users.email）。

-- ---------------------------------------------------------------------------
-- 1. 依附模式表 (attachment_patterns)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachment_patterns (
    id                   VARCHAR(64)  PRIMARY KEY,                 -- uuid (应用层生成)
    session_id           VARCHAR(64)  NOT NULL,                    -- 同一次省察的分组 id
    email                VARCHAR(255) NOT NULL,                    -- 用户 email

    target_type          VARCHAR(40)  NOT NULL,                    -- 7 类功能性偶像之一
                                                                   -- success|money|approval|control|relationship|comfort|spiritual_image
    target_name          VARCHAR(200) DEFAULT '',                  -- 用户具体所指 (可空)

    -- 五个子维度，区间 0.0–1.0
    fear_of_loss         REAL DEFAULT 0,                           -- 害怕失去
    identity_dependency  REAL DEFAULT 0,                           -- 身份依赖
    peace_disruption     REAL DEFAULT 0,                           -- 平安被扰动
    obedience_conflict   REAL DEFAULT 0,                           -- 与顺服/良心冲突
    attention_capture    REAL DEFAULT 0,                           -- 注意力被捕获

    intensity            REAL DEFAULT 0,                           -- 依附强度指数 (复合)
    risk_level           VARCHAR(16)  DEFAULT 'low',               -- low|moderate|elevated|high

    detected_from        VARCHAR(40)  DEFAULT 'self_reflection',   -- self_reflection|emotion|formation|decision|graph
    explanation          TEXT         DEFAULT '',                  -- 非定罪式说明

    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attachment_email_created
    ON attachment_patterns (email, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_attachment_session
    ON attachment_patterns (session_id);

CREATE INDEX IF NOT EXISTS idx_attachment_email_target
    ON attachment_patterns (email, target_type);

-- ---------------------------------------------------------------------------
-- 2. 省察会话表 (attachment_sessions) — 一次省察的整体快照
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachment_sessions (
    id              VARCHAR(64)  PRIMARY KEY,                      -- = attachment_patterns.session_id
    email           VARCHAR(255) NOT NULL,
    top_target      VARCHAR(40)  DEFAULT '',                       -- 本次最高依附类型
    top_intensity   REAL         DEFAULT 0,                        -- 最高依附强度指数
    risk_level      VARCHAR(16)  DEFAULT 'low',
    summary         TEXT         DEFAULT '',                       -- 整体观察 (非定罪)
    answers         JSONB        DEFAULT '{}'::jsonb,              -- 原始省察输入留底
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attachment_sessions_email_created
    ON attachment_sessions (email, created_at DESC);
