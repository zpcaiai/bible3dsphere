-- Migration 0108: 圣灵果子追踪 Fruit of the Spirit Tracker（B3 Skill 12）
-- 加 5:22-23 的九样果子作长期生命变化的「谦卑指示」，不是属灵排名/打分竞赛。
-- 强调证据式反思（在哪里出现？哪里被拦阻？什么恩典帮助了你？），不与他人比较。email 标识用户。

CREATE TABLE IF NOT EXISTS fruit_dimensions (
    dimension_key       VARCHAR(24)  PRIMARY KEY,
    display_name        VARCHAR(40)  NOT NULL,
    description         TEXT         DEFAULT '',
    scripture_reference VARCHAR(40)  DEFAULT '加5:22-23',
    related_virtues     JSONB        DEFAULT '[]'::jsonb,
    opposing_vices      JSONB        DEFAULT '[]'::jsonb,
    example_evidences   JSONB        DEFAULT '[]'::jsonb,
    caution_notes       TEXT         DEFAULT '',
    sort_order          INT          DEFAULT 0,
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fruit_assessments (
    id              VARCHAR(64)  PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    assessment_date DATE         NOT NULL,
    assessment_type VARCHAR(16)  DEFAULT 'self',  -- self/mentor/group_leader/ai_reflection
    period_start    DATE,
    period_end      DATE,
    context_label   VARCHAR(24)  DEFAULT 'overall',
    notes           TEXT         DEFAULT '',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fruit_assessments_email ON fruit_assessments (email, assessment_date DESC);

CREATE TABLE IF NOT EXISTS fruit_assessment_scores (
    id              VARCHAR(64)  PRIMARY KEY,
    assessment_id   VARCHAR(64)  NOT NULL,
    email           VARCHAR(255) NOT NULL,
    dimension_key   VARCHAR(24)  NOT NULL,
    score           INT,
    evidence_text   TEXT         DEFAULT '',
    growth_example  TEXT         DEFAULT '',
    struggle_example TEXT        DEFAULT '',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fruit_assessment_scores_assessment ON fruit_assessment_scores (assessment_id);
CREATE INDEX IF NOT EXISTS idx_fruit_assessment_scores_email_dim ON fruit_assessment_scores (email, dimension_key);

INSERT INTO fruit_dimensions (dimension_key, display_name, description, related_virtues, opposing_vices, example_evidences, caution_notes, sort_order) VALUES
 ('love','仁爱','为他人真实益处舍己的爱。','["怜悯","慷慨"]','["冷漠","自私"]','["主动关心一个人","为难处的人付出时间"]','分数只是反思工具，不是被爱程度的度量。',1),
 ('joy','喜乐','根植于神而非环境的深层喜乐。','["感恩","盼望"]','["怨怼","绝望"]','["在难处中仍能感恩","为小事由衷欢喜"]','喜乐不等于一直开心；哀伤中也可有底层的喜乐。',2),
 ('peace','和平','在神里面的安稳，与人和睦。','["信靠","温柔"]','["焦虑","纷争"]','["焦虑时回到祷告","主动修复关系"]','',3),
 ('patience','忍耐','在延迟与挫折中持守恩慈。','["恒忍","温柔"]','["怒气","急躁"]','["被打断仍温和","等待中不抱怨"]','忍耐不等于纵容不义或留在危险里。',4),
 ('kindness','恩慈','以体贴待人。','["怜悯","慷慨"]','["刻薄","冷漠"]','["对服务员道谢","主动帮一个忙"]','',5),
 ('goodness','良善','正直地行善。','["诚实","公义"]','["诡诈","败坏"]','["私下也守正直","拒绝一个走捷径的诱惑"]','',6),
 ('faithfulness','信实','在小事与承诺上的可靠。','["忠心","恒忍"]','["善变","背信"]','["守住一个承诺","在隐藏处仍尽责"]','',7),
 ('gentleness','温柔','有力量却受约束的柔和。','["谦卑","忍耐"]','["粗暴","骄傲"]','["回应批评时柔和","以柔和指出错处"]','温柔不是软弱，也不是默许伤害。',8),
 ('self_control','节制','在神面前管理欲望与冲动。','["自律","纯洁"]','["放纵","冲动"]','["延迟一个冲动","守住一个界限"]','',9)
ON CONFLICT (dimension_key) DO NOTHING;
