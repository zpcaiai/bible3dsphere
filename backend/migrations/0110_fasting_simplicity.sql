-- Migration 0110: 禁食与简朴操练 Fasting & Simplicity（B4 Skill 16）
-- 训练欲望、抵抗消费主义、操练依靠、慷慨与自由。
-- 安全第一：不施压食物禁食；进食障碍/孕期/糖尿病/服药/体弱/减肥动机 → 禁止食物禁食、改非食物。
-- 食物禁食必须 health_acknowledgement=true。email 标识用户。

CREATE TABLE IF NOT EXISTS fasting_practices (
    practice_key      VARCHAR(40)  PRIMARY KEY,
    title             VARCHAR(80)  NOT NULL,
    description       TEXT         DEFAULT '',
    fasting_type      VARCHAR(20)  DEFAULT 'media',  -- food/media/technology/spending/comfort/speech/entertainment/custom
    difficulty        VARCHAR(20)  DEFAULT 'beginner',
    typical_duration  VARCHAR(40)  DEFAULT '',
    health_caution    TEXT         DEFAULT '',
    formation_purpose JSONB        DEFAULT '[]'::jsonb,
    sort_order        INT          DEFAULT 0,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fasting_plans (
    id                     VARCHAR(64)  PRIMARY KEY,
    email                  VARCHAR(255) NOT NULL,
    practice_key           VARCHAR(40)  DEFAULT '',
    title                  VARCHAR(160) NOT NULL,
    status                 VARCHAR(12)  DEFAULT 'active',
    fasting_type           VARCHAR(20)  DEFAULT 'media',
    start_at               TIMESTAMP,
    end_at                 TIMESTAMP,
    purpose                TEXT         DEFAULT '',
    prayer_focus           TEXT         DEFAULT '',
    simplicity_focus       TEXT         DEFAULT '',
    generosity_response    TEXT         DEFAULT '',
    health_acknowledgement BOOLEAN      DEFAULT FALSE,
    safety_flags           JSONB        DEFAULT '[]'::jsonb,
    created_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fasting_plans_email ON fasting_plans (email, status);

CREATE TABLE IF NOT EXISTS fasting_checkins (
    id                    VARCHAR(64)  PRIMARY KEY,
    email                 VARCHAR(255) NOT NULL,
    fasting_plan_id       VARCHAR(64)  NOT NULL,
    checkin_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    hunger_or_desire_level INT,
    emotional_state       JSONB        DEFAULT '[]'::jsonb,
    temptation_or_resistance TEXT      DEFAULT '',
    prayer_text           TEXT         DEFAULT '',
    desire_insight        TEXT         DEFAULT '',
    completed             BOOLEAN      DEFAULT FALSE,
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fasting_checkins_plan ON fasting_checkins (fasting_plan_id, checkin_at DESC);

CREATE TABLE IF NOT EXISTS simplicity_audits (
    id                        VARCHAR(64)  PRIMARY KEY,
    email                     VARCHAR(255) NOT NULL,
    audit_date                DATE         NOT NULL,
    money_clutter_score       INT,
    possession_clutter_score  INT,
    schedule_clutter_score    INT,
    digital_clutter_score     INT,
    desire_pressure_score     INT,
    comparison_pressure_score INT,
    identified_excesses       JSONB        DEFAULT '[]'::jsonb,
    gratitude_items           JSONB        DEFAULT '[]'::jsonb,
    possible_generosity_actions JSONB      DEFAULT '[]'::jsonb,
    simplification_actions    JSONB        DEFAULT '[]'::jsonb,
    created_at                TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_simplicity_audits_email ON simplicity_audits (email, audit_date DESC);

CREATE TABLE IF NOT EXISTS simplicity_actions (
    id              VARCHAR(64)  PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    audit_id        VARCHAR(64)  DEFAULT '',
    action_type     VARCHAR(24)  DEFAULT 'declutter', -- give/donate/unsubscribe/declutter/cancel_purchase/reduce_commitment/technology_boundary/budget_reflection/gratitude/custom
    description     TEXT         DEFAULT '',
    due_at          TIMESTAMP,
    status          VARCHAR(12)  DEFAULT 'planned',
    completion_notes TEXT        DEFAULT '',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_simplicity_actions_email ON simplicity_actions (email, status);

CREATE TABLE IF NOT EXISTS fasting_reviews (
    id                    VARCHAR(64)  PRIMARY KEY,
    email                 VARCHAR(255) NOT NULL,
    fasting_plan_id       VARCHAR(64)  NOT NULL,
    review_date           DATE,
    desire_patterns_noticed JSONB      DEFAULT '[]'::jsonb,
    prayer_insights       JSONB        DEFAULT '[]'::jsonb,
    gratitude_insights    JSONB        DEFAULT '[]'::jsonb,
    generosity_completed  BOOLEAN      DEFAULT FALSE,
    legalism_warning      TEXT         DEFAULT '',
    recommended_next_step TEXT         DEFAULT '',
    summary               TEXT         DEFAULT '',
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO fasting_practices (practice_key, title, description, fasting_type, difficulty, typical_duration, health_caution, formation_purpose, sort_order) VALUES
 ('one_meal_food_fast','禁食一餐','禁食一餐，把饥饿化为祷告与依靠。','food','beginner','一餐','若有进食障碍史、孕期、糖尿病、需随餐服药或体弱，请勿食物禁食，改用非食物禁食并咨询医生。','["依靠","祷告"]',1),
 ('social_media_24h_fast','社媒禁食 24 小时','停用社交媒体一天，留意逃避、比较与表演的欲望。','media','beginner','24 小时','','["简朴","专注"]',2),
 ('phone_evening_fast','手机晚间禁食','晚间不用手机，把时间还给安息、关系与祷告。','technology','beginner','一个晚上','','["节制","临在"]',3),
 ('spending_fast_one_week','消费禁食一周','一周不做非必要消费，察觉用购买安抚自己的模式。','spending','normal','一周','','["简朴","知足"]',4),
 ('speech_fast_half_day','言语禁食半天','半天少言或静默，操练守舌与聆听。','speech','normal','半天','','["守舌","聆听"]',5),
 ('entertainment_fast','娱乐禁食','暂停影视/游戏，把空出的时间转向神与人。','entertainment','beginner','按定','','["专注","临在"]',6),
 ('comfort_fast','舒适禁食','主动放下一个小舒适（如热水澡/咖啡），操练与穷乏者认同。','comfort','normal','按定','','["节制","与穷人认同"]',7),
 ('simplicity_audit','简朴审视','审视金钱/物品/日程/数字上的过剩，迈出简化一步。','custom','beginner','一次','','["简朴","自由"]',8),
 ('generosity_response','慷慨回应','把省下的资源转为对人的祝福。','custom','beginner','一次','','["慷慨","爱"]',9),
 ('digital_declutter','数字断舍离','退订/卸载会加剧焦虑或嫉妒的信息源。','technology','beginner','一次','','["简朴","专注"]',10)
ON CONFLICT (practice_key) DO NOTHING;
