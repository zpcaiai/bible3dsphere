-- Migration 0118: 教义目录与学习路径模板 Doctrine Catalog（B9 Skill 35）
-- 结构化学习基督教教义,连接到成长操练。区分经文/教义/传统/应用;有争议教义给多视角与传统注记。
-- 这里保存公共教义主题与路径模板; 用户具体学习路径由 0117 的 doctrine_learning_paths 保存。

CREATE TABLE IF NOT EXISTS doctrine_topics (
    topic_key             VARCHAR(40)  PRIMARY KEY,
    display_name          VARCHAR(80)  NOT NULL,
    doctrine_area         VARCHAR(24)  DEFAULT 'other',
    difficulty            VARCHAR(12)  DEFAULT 'beginner',
    summary               TEXT         DEFAULT '',
    scripture_refs        JSONB        DEFAULT '[]'::jsonb,
    key_terms             JSONB        DEFAULT '[]'::jsonb,
    common_misunderstandings JSONB     DEFAULT '[]'::jsonb,
    formation_relevance   TEXT         DEFAULT '',
    linked_modules        JSONB        DEFAULT '[]'::jsonb,
    prerequisite_keys     JSONB        DEFAULT '[]'::jsonb,
    sort_order            INT          DEFAULT 0,
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctrine_path_templates (
    path_key    VARCHAR(40)  PRIMARY KEY,
    title       VARCHAR(120) NOT NULL,
    description  TEXT        DEFAULT '',
    path_type   VARCHAR(30)  DEFAULT 'beginner_foundations',
    topic_keys  JSONB        DEFAULT '[]'::jsonb,
    public      BOOLEAN      DEFAULT TRUE,
    sort_order  INT          DEFAULT 0,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_doctrine_progress (
    id           VARCHAR(64)  PRIMARY KEY,
    email        VARCHAR(255) NOT NULL,
    topic_key    VARCHAR(40)  NOT NULL,
    path_key     VARCHAR(40)  DEFAULT '',
    status       VARCHAR(12)  DEFAULT 'in_progress',  -- not_started/in_progress/completed/reviewed
    notes        TEXT         DEFAULT '',
    started_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_doctrine_progress_email ON user_doctrine_progress (email, topic_key);

CREATE TABLE IF NOT EXISTS doctrine_reflections (
    id                   VARCHAR(64)  PRIMARY KEY,
    email                VARCHAR(255) NOT NULL,
    topic_key            VARCHAR(40)  NOT NULL,
    reflection_text      TEXT         DEFAULT '',
    formation_application TEXT        DEFAULT '',
    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_doctrine_reflections_email ON doctrine_reflections (email, created_at DESC);

INSERT INTO doctrine_topics (topic_key, display_name, doctrine_area, difficulty, summary, scripture_refs, key_terms, formation_relevance, linked_modules, sort_order) VALUES
 ('revelation_scripture','启示与圣经','scripture','beginner','神主动启示自己;圣经是神所默示、可信、为生命与信仰的最高准则。','["提后3:16-17","来1:1-2"]','["默示","正典","权威"]','圣经是我们认识神与自己的根基,塑造一切操练。','["scripture_formation"]',1),
 ('trinity','三位一体','trinity','normal','独一真神,圣父、圣子、圣灵,三个位格、同质同尊。','["太28:19","约1:1"]','["位格","同质","相互内住"]','三一神的相爱团契是我们群体与相交的根基。','["prayer_communion"]',2),
 ('attributes_of_god','神的属性','god','beginner','神的圣洁、慈爱、信实、全能、智慧、不变等。','["出34:6-7","诗145"]','["圣洁","慈爱","信实"]','认识神是谁,决定我们如何信靠与敬拜。','["worldview_formation"]',3),
 ('creation','创造','creation','beginner','神从无造有,创造本为美好,人是其巅峰。','["创1-2","西1:16"]','["从无造有","美好","管家"]','工作、身体、受造界都有尊严,是使命的舞台。','["mission_life"]',4),
 ('providence','护理','providence','normal','神主动维系并引导历史与个人生命走向他的目的。','["罗8:28","太10:29"]','["维系","引导","主权"]','在苦难与不确定中,护理给我们信靠的根基。','["suffering_care"]',5),
 ('image_of_god','神的形像','humanity','beginner','人按神形像被造,有尊严、关系性与受托管理。','["创1:26-27"]','["尊严","关系","管理"]','每个人(包括你)有不可剥夺的尊严。','["worldview_formation"]',6),
 ('sin','罪','sin','beginner','罪是悖逆与失序的爱,破坏与神、人、受造界的关系。','["罗3:23","创3"]','["悖逆","失序的爱","堕落"]','正确看罪,才能正确领受恩典,不羞辱不轻看。','["virtue_vice","confession"]',7),
 ('person_of_christ','基督的位格','christology','normal','耶稣是完全的神、完全的人,一个位格、两个本性。','["约1:14","西2:9"]','["道成肉身","两性一位"]','基督亲自进入我们的处境,是盼望的核心。','["gospel"]',8),
 ('work_of_christ','基督的工作','christology','normal','基督的生、死、复活成就救赎:先知、祭司、君王。','["可10:45","林前15"]','["代赎","三重职分"]','福音重构的根基:十架与复活解释你的处境。','["gospel_reframing"]',9),
 ('atonement','救赎','atonement','deep','十架上,基督担当罪、平息忿怒、胜过权势、显明大爱。','["赛53","罗3:25"]','["代赎","和好","得胜"]','你被接纳不靠表现,乃靠基督已成之工。','["confession","gospel_reframing"]',10),
 ('resurrection','复活','resurrection','beginner','基督身体复活,胜过死亡,是新创造的初熟果子。','["林前15:20","路24"]','["身体复活","初熟果子"]','复活给一切忠心、受苦与盼望以确据。','["suffering_care"]',11),
 ('holy_spirit','圣灵','holy_spirit','normal','圣灵是神,重生、内住、成圣、赐恩赐、结果子。','["约16","加5:22-23"]','["重生","内住","成圣"]','成长是圣灵的工作,你的角色是常在主里。','["fruit","gift_calling"]',12),
 ('union_with_christ','与基督联合','union_with_christ','deep','信徒在基督里:同死、同复活、被接纳、得新身份。','["罗6","加2:20"]','["在基督里","新身份"]','医治羞耻与表现身份的核心真理。','["belief_diagnostic","gospel_reframing"]',13),
 ('justification','称义','justification','normal','神因信、靠恩,在基督里宣告罪人为义。','["罗3-5","加2-3"]','["白白的恩典","因信","归算"]','使你从表现换接纳的捆绑里被释放。','["confession","gospel_reframing","belief_diagnostic"]',14),
 ('adoption','得儿子名分','salvation','normal','在基督里被神收纳为儿女,得父的爱与产业。','["罗8:15","约一3:1"]','["儿女","阿爸父"]','你的根本身份是被爱的儿女,不是孤儿。','["belief_diagnostic"]',15),
 ('sanctification','成圣','sanctification','normal','圣灵渐进地使信徒更像基督,既是恩典也是操练。','["腓2:12-13","帖前4"]','["渐进","恩典与努力"]','成长是恩典里的忠心,不是靠拼搏赚取。','["holy_habit","virtue_vice"]',16),
 ('church','教会','church','beginner','教会是基督的身体、神的家、圣灵的殿,蒙召敬拜与差遣。','["弗2","徒2:42"]','["身体","团契","使命"]','成长是群体的,不是个人主义的。','["discipleship_community","church_integration"]',17),
 ('baptism','洗礼','sacraments','normal','洗礼是入会的记号,标志与基督同死同复活(各传统理解不同)。','["罗6:3-4","太28:19"]','["记号","归入"]','标志你新的身份与群体归属。','["church_integration"]',18),
 ('lord_supper','圣餐','sacraments','normal','主餐记念、相交、盼望,以饼杯领受基督之恩(各传统理解不同)。','["林前11:23-26"]','["记念","相交","盼望"]','规律地以具身方式领受福音。','["church_integration"]',19),
 ('prayer','祷告','prayer','beginner','祷告是与神相交、依靠、代求,既是恩典也是操练。','["太6:9-13","帖前5:17"]','["相交","代求","依靠"]','祷告是相交而非表现,塑造一切。','["prayer_communion"]',20),
 ('suffering','苦难','suffering','normal','基督徒的盼望是十架与复活式的;苦难中有同在、塑造与新创造盼望。','["罗8","林后1","诗"]','["哀歌","同在","盼望"]','容许哀伤,拒绝廉价答案,持守盼望。','["suffering_care"]',21),
 ('eschatology','末世','eschatology','deep','基督必再来,死人复活,新天新地,神与人同住。','["启21","帖前4"]','["再来","新创造"]','盼望给当下的忠心与受苦以意义。','["suffering_care"]',22),
 ('christian_ethics','基督教伦理','ethics','normal','以爱神爱人、效法基督、靠圣灵活出新生命的伦理。','["太22:37-40","加5"]','["爱","效法基督"]','伦理是从恩典流出的回应,不是赚取。','["virtue_vice","worldview_formation"]',23),
 ('mission','使命','mission','beginner','神差遣教会作见证,在万民中作门徒,直到地极。','["太28:18-20","徒1:8"]','["差遣","见证","门徒"]','使命整合进日常的职业、家庭与邻舍。','["mission_life","gift_calling"]',24)
ON CONFLICT (topic_key) DO NOTHING;

INSERT INTO doctrine_path_templates (path_key, title, description, path_type, topic_keys, sort_order) VALUES
 ('beginner_foundations','信仰根基入门','给初信或想打基础的人:圣经、神、福音、教会。','beginner_foundations','["revelation_scripture","attributes_of_god","sin","work_of_christ","resurrection","church"]',1),
 ('new_believer_core','初信核心','新生命的根基:福音、圣灵、祷告、教会、洗礼。','catechism_basic','["work_of_christ","holy_spirit","prayer","church","baptism","lord_supper"]',2),
 ('shame_to_grace','从羞耻到恩典','针对表现身份与羞耻:称义、与基督联合、得儿子名分。','custom','["justification","union_with_christ","adoption","atonement"]',3),
 ('holiness_and_spirit','圣洁与圣灵','成长之路:圣灵、成圣、与基督联合、伦理。','custom','["holy_spirit","sanctification","union_with_christ","christian_ethics"]',4),
 ('suffering_and_hope','苦难与盼望','护理、苦难、复活、末世盼望。','custom','["providence","suffering","resurrection","eschatology"]',5),
 ('leadership_theology','领袖神学','为带领预备:圣经、三一、基督论、救恩、教会、伦理。','leadership_training','["revelation_scripture","trinity","person_of_christ","justification","church","christian_ethics"]',6)
ON CONFLICT (path_key) DO NOTHING;
