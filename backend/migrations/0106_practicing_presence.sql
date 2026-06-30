-- Migration 0106: 操练与神同在 Practicing Presence（B2 Skill 08）
-- 劳伦斯弟兄式：在日常（工作/通勤/冲突/疲惫/试探）中短暂、重复地回到对神的觉知。
-- 焦点是短而频的回转，不是把觉知变成焦虑或强迫打卡。email 标识用户。

CREATE TABLE IF NOT EXISTS presence_practices (
    practice_key     VARCHAR(40)  PRIMARY KEY,
    title            VARCHAR(80)  NOT NULL,
    description      TEXT         DEFAULT '',
    practice_type    VARCHAR(30)  DEFAULT 'breath_prayer',
    duration_seconds INT          DEFAULT 60,
    scripture_refs   JSONB        DEFAULT '[]'::jsonb,
    difficulty       VARCHAR(20)  DEFAULT 'beginner',
    active           BOOLEAN      DEFAULT TRUE,
    sort_order       INT          DEFAULT 0,
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS presence_checkins (
    id               VARCHAR(64)  PRIMARY KEY,
    email            VARCHAR(255) NOT NULL,
    practice_key     VARCHAR(40)  DEFAULT '',
    checkin_time     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    context_label    VARCHAR(40)  DEFAULT '',
    awareness_before INT,
    awareness_after  INT,
    emotional_state  JSONB        DEFAULT '[]'::jsonb,
    short_prayer     TEXT         DEFAULT '',
    distraction_noted TEXT        DEFAULT '',
    return_action    TEXT         DEFAULT '',
    completed        BOOLEAN      DEFAULT FALSE,
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_presence_checkins_email ON presence_checkins (email, checkin_time DESC);

CREATE TABLE IF NOT EXISTS presence_rules (
    id             VARCHAR(64)  PRIMARY KEY,
    email          VARCHAR(255) NOT NULL,
    title          VARCHAR(120) DEFAULT '',
    active         BOOLEAN      DEFAULT TRUE,
    trigger_type   VARCHAR(20)  DEFAULT 'manual',  -- time_based/context_based/emotion_based/habit_linked/manual
    trigger_config JSONB        DEFAULT '{}'::jsonb,
    practice_key   VARCHAR(40)  DEFAULT '',
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_presence_rules_email ON presence_rules (email, active);

INSERT INTO presence_practices (practice_key, title, description, practice_type, duration_seconds, scripture_refs, sort_order) VALUES
 ('one_minute_breath_prayer','一分钟呼吸祷告','吸气时默想「主耶稣基督」，呼气时默想「怜悯我」。缓慢重复约一分钟。','breath_prayer',60,'["路18:13"]',1),
 ('work_offering','工作奉献','开工前轻声说：「主，我把这份工作献给你，使我忠心、诚实、有爱。」','work_offering',30,'["西3:23"]',2),
 ('gratitude_pause','感恩暂停','留意此刻的一件礼物，不抓取、不赶，单纯地向神道谢。','gratitude_pause',30,'["帖前5:18"]',3),
 ('temptation_pause','试探暂停','停一下。说出此刻的欲望。问自己：我在神之外寻求什么应许？然后选一个小顺服。','temptation_pause',60,'["林前10:13"]',4),
 ('conflict_pause','冲突暂停','回应之前先呼吸。问：此刻爱、真理与谦卑各要求我做什么？','conflict_pause',30,'["雅1:19"]',5),
 ('surrender_prayer','交托祷告','说出一件你无法掌控的事，祷告：「父啊，我把它交在你手中。」','surrender',30,'["路23:46"]',6),
 ('scripture_recollection','回想经文','想起一节熟悉的经文，在心里慢慢默念两三遍。','scripture_recollection',60,'["诗119:11"]',7),
 ('silence_60_seconds','安静六十秒','什么都不做，只是在神面前安静一分钟。','silence',60,'["诗46:10"]',8),
 ('commute_intercession','通勤代祷','在路上为一个人简短代祷，把他交托给神。','breath_prayer',120,'["提前2:1"]',9),
 ('fatigue_rest_prayer','疲惫安息祷告','感受身体的疲惫，对神说：「我需要安息，求你更新我。」','body_awareness',60,'["太11:28"]',10)
ON CONFLICT (practice_key) DO NOTHING;
