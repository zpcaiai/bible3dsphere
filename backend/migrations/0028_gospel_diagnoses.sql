-- Migration 0028: 福音诊断室 / Gospel Diagnostic Lab（钟马田诊断 + 司布真牧养）
-- 把一次「属灵病历」存档：经历→情绪→欲望→恐惧→不信→偶像→福音→基督→祷告→行动。
-- 用户以 email 标识。

CREATE TABLE IF NOT EXISTS gospel_diagnoses (
    id              VARCHAR(64)  PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,

    -- 五个输入
    event           TEXT  DEFAULT '',
    feeling         TEXT  DEFAULT '',
    want            TEXT  DEFAULT '',
    fear            TEXT  DEFAULT '',
    belief          TEXT  DEFAULT '',

    -- 钟马田诊断
    emotion         VARCHAR(40)  DEFAULT '',
    idol_type       VARCHAR(40)  DEFAULT '',
    unbelief        TEXT  DEFAULT '',

    -- 司布真牧养
    gospel_truth    TEXT  DEFAULT '',
    scripture_ref   VARCHAR(60)  DEFAULT '',
    scripture_text  TEXT  DEFAULT '',
    meditation      TEXT  DEFAULT '',
    prayer          TEXT  DEFAULT '',
    action          TEXT  DEFAULT '',

    analysis_json   JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gospel_email_created ON gospel_diagnoses (email, created_at DESC);
