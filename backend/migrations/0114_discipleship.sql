-- Migration 0114: 门徒成长路径 Discipleship Pathway（B7 Skill 25）
-- 阶段评估 → 目标阶段 → 30/90/180 天路径 + 步骤。阶段是成长辅助,不是身份标签,不排高低。
-- 区别于既有 disciple.py(门徒塑造引擎)。email 标识用户。

CREATE TABLE IF NOT EXISTS discipleship_stages (
    stage_key             VARCHAR(30)  PRIMARY KEY,
    display_name          VARCHAR(60)  NOT NULL,
    description           TEXT         DEFAULT '',
    core_marks            JSONB        DEFAULT '[]'::jsonb,
    recommended_practices JSONB        DEFAULT '[]'::jsonb,
    next_stage_key        VARCHAR(30)  DEFAULT '',
    sort_order            INT          DEFAULT 0,
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discipleship_assessments (
    id                      VARCHAR(64)  PRIMARY KEY,
    email                   VARCHAR(255) NOT NULL,
    assessment_date         DATE         DEFAULT CURRENT_DATE,
    assessed_stage_key      VARCHAR(30)  DEFAULT '',
    self_report_stage_key   VARCHAR(30)  DEFAULT '',
    church_connection_level VARCHAR(20)  DEFAULT 'none',
    scripture_practice_level INT         DEFAULT 0,
    prayer_practice_level   INT          DEFAULT 0,
    community_level         INT          DEFAULT 0,
    service_level           INT          DEFAULT 0,
    notes                   TEXT         DEFAULT '',
    created_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_disc_assess_email ON discipleship_assessments (email, assessment_date DESC);

CREATE TABLE IF NOT EXISTS user_discipleship_paths (
    id               VARCHAR(64)  PRIMARY KEY,
    email            VARCHAR(255) NOT NULL,
    title            VARCHAR(160) DEFAULT '门徒成长路径',
    current_stage_key VARCHAR(30) DEFAULT '',
    target_stage_key VARCHAR(30)  DEFAULT '',
    duration_days    INT          DEFAULT 90,
    start_date       DATE         DEFAULT CURRENT_DATE,
    status           VARCHAR(12)  DEFAULT 'active',
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_disc_paths_email ON user_discipleship_paths (email, status);

CREATE TABLE IF NOT EXISTS discipleship_path_steps (
    id              VARCHAR(64)  PRIMARY KEY,
    path_id         VARCHAR(64)  NOT NULL,
    email           VARCHAR(255) NOT NULL,
    step_title      VARCHAR(200) NOT NULL,
    step_description TEXT        DEFAULT '',
    step_type       VARCHAR(20)  DEFAULT 'custom',
    related_module  VARCHAR(40)  DEFAULT '',
    status          VARCHAR(12)  DEFAULT 'planned',
    sort_order      INT          DEFAULT 0,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_disc_steps_path ON discipleship_path_steps (path_id, sort_order);

INSERT INTO discipleship_stages (stage_key, display_name, description, core_marks, recommended_practices, next_stage_key, sort_order) VALUES
 ('seeker','寻道者','在认识福音、提出问题的阶段。','["对信仰开放","有真诚的疑问"]','["福音基础","马可/约翰福音","安全的教会连接"]','new_believer',1),
 ('new_believer','初信者','刚信主,需扎根基要真理。','["接受福音","愿意跟随"]','["受洗预备","祷告基础","读经基础","导师连接"]','rooted_disciple',2),
 ('rooted_disciple','扎根门徒','建立稳定的灵修与教义根基。','["规律读经祷告","参与聚会"]','["教义基础","祷告规则","探索教会成员"]','practicing_disciple',3),
 ('practicing_disciple','操练门徒','建立生活规则、德性、初步服事。','["生活规则","参与小组"]','["生活规则","德性塑造","问责小组","服事探索"]','serving_member',4),
 ('serving_member','服事成员','按恩赐参与教会服事。','["稳定服事","恩赐运用"]','["恩赐评估","服事匹配","安息界限"]','mature_disciple',5),
 ('mature_disciple','成熟门徒','结果子、能陪伴他人。','["品格成熟","能牧养他人"]','["导师训练","教义深化","门训节奏"]','leader_in_training',6),
 ('leader_in_training','受训领袖','预备承担带领责任。','["谦卑","可问责"]','["牧养基础","教义复习","谦卑操练","领袖问责"]','disciple_maker',7),
 ('disciple_maker','门徒倍增者','带领他人作门徒、繁殖小组。','["门训他人","繁殖群体"]','["倍增小组","导师看板","使命节奏"]','missionary_sent',8),
 ('missionary_sent','差派宣教','被差派进入使命场景。','["跨文化","坚韧"]','["宣教支持","处境智慧","坚韧操练"]','elder_like_maturity',9),
 ('elder_like_maturity','长老式成熟','以成熟看顾、教导、守护群体。','["智慧","守护群体"]','["看顾监督","教导","安息与谦卑"]','',10)
ON CONFLICT (stage_key) DO NOTHING;
