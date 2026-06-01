-- Migration 0024: 每日省察 Examen（依纳爵式）
-- 回顾今天的「安慰 / 枯涩」，感恩一件、求恕一件、明日一个微顺服。
-- 不定罪、不评判，是温柔的每日省察操练。每人每天一条（email + 日期 唯一）。

CREATE TABLE IF NOT EXISTS examen_entries (
    id                 VARCHAR(64)  PRIMARY KEY,
    email              VARCHAR(255) NOT NULL,
    entry_date         DATE         NOT NULL,

    consolation        TEXT  DEFAULT '',   -- 今天哪里感到神的同在 / 安慰
    desolation         TEXT  DEFAULT '',   -- 今天哪里感到枯涩 / 远离
    gratitude          TEXT  DEFAULT '',   -- 感恩的一件事
    confession         TEXT  DEFAULT '',   -- 想求神赦免 / 交托的一件事
    tomorrow_step      TEXT  DEFAULT '',   -- 明日一个微小的顺服

    consolation_level  REAL  DEFAULT 5,    -- 0–10 今天与神的亲近感

    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (email, entry_date)
);

CREATE INDEX IF NOT EXISTS idx_examen_email_date
    ON examen_entries (email, entry_date DESC);
