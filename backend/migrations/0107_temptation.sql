-- Migration 0107: 试探抵抗 Temptation Resistance（B3 Skill 11）
-- 识别试探时刻、选择逃离路径、用忠心行动替代破坏行动、必要时引入守望/监督。
-- 区分：试探≠罪、软弱≠悖逆。不羞辱、不自惩；失败温柔导向认罪；危机/成瘾导向人帮助。
-- email 标识用户。

CREATE TABLE IF NOT EXISTS temptation_types (
    type_key          VARCHAR(40)  PRIMARY KEY,
    display_name      VARCHAR(80)  NOT NULL,
    description       TEXT         DEFAULT '',
    common_triggers   JSONB        DEFAULT '[]'::jsonb,
    escape_principles JSONB        DEFAULT '[]'::jsonb,
    opposite_virtues  JSONB        DEFAULT '[]'::jsonb,
    scripture_refs    JSONB        DEFAULT '[]'::jsonb,
    active            BOOLEAN      DEFAULT TRUE,
    sort_order        INT          DEFAULT 0,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS temptation_plans (
    id                     VARCHAR(64)  PRIMARY KEY,
    email                  VARCHAR(255) NOT NULL,
    title                  VARCHAR(160) NOT NULL,
    temptation_type_key    VARCHAR(40)  DEFAULT '',
    status                 VARCHAR(12)  DEFAULT 'active',
    vulnerable_contexts    JSONB        DEFAULT '[]'::jsonb,
    early_warning_signs    JSONB        DEFAULT '[]'::jsonb,
    escape_actions         JSONB        DEFAULT '[]'::jsonb,
    replacement_actions    JSONB        DEFAULT '[]'::jsonb,
    scripture_anchors      JSONB        DEFAULT '[]'::jsonb,
    accountability_contacts JSONB       DEFAULT '[]'::jsonb,
    created_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_temptation_plans_email ON temptation_plans (email, status);

CREATE TABLE IF NOT EXISTS temptation_checkins (
    id                       VARCHAR(64)  PRIMARY KEY,
    email                    VARCHAR(255) NOT NULL,
    plan_id                  VARCHAR(64)  DEFAULT '',
    checked_in_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    context_label            VARCHAR(40)  DEFAULT '',
    intensity_before         INT,
    intensity_after          INT,
    trigger_text             TEXT         DEFAULT '',
    chosen_escape_action     TEXT         DEFAULT '',
    chosen_replacement_action TEXT        DEFAULT '',
    outcome                  VARCHAR(20)  DEFAULT 'still_struggling', -- resisted/escaped/delayed/failed/still_struggling/asked_for_help
    notes                    TEXT         DEFAULT '',
    created_at               TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_temptation_checkins_email ON temptation_checkins (email, checked_in_at DESC);

CREATE TABLE IF NOT EXISTS temptation_failure_reviews (
    id                  VARCHAR(64)  PRIMARY KEY,
    email               VARCHAR(255) NOT NULL,
    checkin_id          VARCHAR(64)  DEFAULT '',
    what_happened       TEXT         DEFAULT '',
    trigger_chain       JSONB        DEFAULT '[]'::jsonb,
    shame_level         INT,
    confession_done     BOOLEAN      DEFAULT FALSE,
    next_plan_adjustment TEXT        DEFAULT '',
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO temptation_types (type_key, display_name, description, common_triggers, escape_principles, opposite_virtues, scripture_refs, sort_order) VALUES
 ('lust','情欲','寻求亲密或释放却走向不洁。','["孤独","疲惫","独处与设备","压力"]','["立刻离开/关闭设备","到有人的地方","告诉守望人"]','["纯洁","自控","爱"]','["林前10:13","诗119:9"]',1),
 ('anger','怒气','受挫或被冒犯时想用愤怒掌控或报复。','["被冒犯","被打断","掌控被夺"]','["回应前先停6秒呼吸","离开现场","写下而非发出"]','["温柔","忍耐","谦卑"]','["雅1:19","箴15:1"]',2),
 ('envy','嫉妒','看他人所有而心怀不平。','["社媒比较","他人成功"]','["停止刷屏","为对方祝福祷告","数算自己的恩典"]','["知足","感恩","爱"]','["诗73","加5:26"]',3),
 ('greed','贪婪','以拥有寻求安全与身份。','["促销","焦虑","比较"]','["延迟购买24小时","记录而非下单","转向慷慨"]','["慷慨","知足"]','["路12:15"]',4),
 ('overeating','暴食','以食物麻痹情绪。','["压力","无聊","深夜"]','["喝水等10分钟","离开厨房","命名真正的需要"]','["节制","安息"]','["林前6:19"]',5),
 ('escapism','逃避','用娱乐/刷屏逃离现实。','["压力","空虚","拖延"]','["设定时限","起身换环境","做一件小事5分钟"]','["勇气","忠心"]','["西3:2"]',6),
 ('social_media_compulsion','刷屏强迫','无意识地反复刷手机。','["无聊","焦虑","习惯"]','["把手机放远","开启灰度/限时","换成读经或走动"]','["节制","临在"]','["弗5:16"]',7),
 ('lying','说谎','为保护形象或逃避而扭曲真相。','["怕丢脸","怕冲突"]','["停一拍","选择说真话","求神给勇气"]','["诚实","勇气"]','["弗4:25"]',8),
 ('control','掌控','以掌控寻求安全。','["不确定","计划被打乱"]','["命名无法掌控的事","交托祷告","容许他人参与"]','["信靠","谦卑"]','["箴3:5-6"]',9),
 ('gossip','论断/八卦','以谈论他人寻求连结或优越。','["闲聊","群体压力"]','["转换话题","只说造就的话","为对方祷告"]','["仁慈","守舌"]','["弗4:29"]',10),
 ('bitterness','苦毒','抓住伤害不肯放手。','["被伤回忆","触发的人事"]','["把伤害带到神面前","选择释放的第一步","必要时设界限"]','["饶恕","怜悯"]','["弗4:31-32"]',11),
 ('despair','绝望','觉得没有出路、不想继续。','["失败","孤单","长期压力"]','["立刻联系信任的人","不独处","寻求即时帮助"]','["盼望","信心"]','["诗42","林后1"]',12),
 ('people_pleasing','讨好','以取悦换取认可。','["怕被拒","怕冲突"]','["允许自己说不","分辨真正的责任","求神的认可"]','["勇气","真诚"]','["加1:10"]',13),
 ('laziness','懒散','回避当尽的责任。','["疲惫","畏难","拖延"]','["只做5分钟","把任务拆小","起身活动身体"]','["恒忍","勤勉"]','["箴6:6"]',14),
 ('other','其它','未列出的冲动或试探。','[]','["停下并命名","选下一个忠心小步","必要时求助"]','["自控","信靠"]','["林前10:13"]',15)
ON CONFLICT (type_key) DO NOTHING;
