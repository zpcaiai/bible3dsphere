-- Migration 0119: 圣经神学时间线 Biblical Theology Timeline（B9 Skill 34）
-- 把圣经读成一个救赎历史的故事:创造→堕落→应许→出埃及→国度→被掳→基督→教会→新创造。
-- 渐进启示、盟约发展、预表与应验。email 标识用户。

CREATE TABLE IF NOT EXISTS biblical_timeline_eras (
    era_key             VARCHAR(30)  PRIMARY KEY,
    display_name        VARCHAR(60)  NOT NULL,
    description         TEXT         DEFAULT '',
    canonical_order     INT          DEFAULT 0,
    testament           VARCHAR(16)  DEFAULT 'old_testament',
    approximate_date_label VARCHAR(40) DEFAULT '',
    theological_summary TEXT         DEFAULT '',
    major_themes        JSONB        DEFAULT '[]'::jsonb,
    key_scripture_refs  JSONB        DEFAULT '[]'::jsonb,
    formation_relevance TEXT         DEFAULT '',
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS covenant_profiles (
    covenant_key  VARCHAR(24)  PRIMARY KEY,
    display_name  VARCHAR(60)  NOT NULL,
    covenant_type VARCHAR(16)  DEFAULT 'other',
    description   TEXT         DEFAULT '',
    parties       JSONB        DEFAULT '[]'::jsonb,
    promises      JSONB        DEFAULT '[]'::jsonb,
    signs         JSONB        DEFAULT '[]'::jsonb,
    scripture_refs JSONB       DEFAULT '[]'::jsonb,
    fulfillment_notes TEXT     DEFAULT '',
    sort_order    INT          DEFAULT 0,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS timeline_learning_sessions (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    session_date  DATE         DEFAULT CURRENT_DATE,
    mode          VARCHAR(20)  DEFAULT 'overview',
    selected_era_key VARCHAR(30) DEFAULT '',
    selected_theme VARCHAR(30) DEFAULT '',
    notes         TEXT         DEFAULT '',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_timeline_sessions_email ON timeline_learning_sessions (email, session_date DESC);

INSERT INTO biblical_timeline_eras (era_key, display_name, description, canonical_order, testament, theological_summary, major_themes, key_scripture_refs, formation_relevance) VALUES
 ('creation','创造','神造天地,本为美好,人按其形像受造。',1,'old_testament','创造是神有序的居所,人是受托的管家与敬拜者。','["creation","temple","kingdom"]','["创1-2"]','工作、身体、受造界都有尊严。'),
 ('fall','堕落','人悖逆,罪与死进入世界,关系破裂。',2,'old_testament','罪扭曲了爱与秩序,但神立刻应许救赎。','["fall","sin","promise"]','["创3"]','正确看罪与失序的爱。'),
 ('promise','原始福音应许','神应许女人的后裔要伤蛇的头。',3,'old_testament','救赎历史以恩典的应许开始。','["promise","messiah"]','["创3:15"]','盼望从最黑暗处开始。'),
 ('abrahamic_covenant','亚伯拉罕之约','神拣选亚伯拉罕,应许后裔、土地、万国的祝福。',4,'old_testament','神借一人一族,要祝福万民。','["covenant","promise","mission"]','["创12","创15"]','你被祝福是为了成为祝福。'),
 ('exodus','出埃及','神听见呼求,以大能领以色列出为奴之地。',5,'old_testament','救赎是神主动的拯救,逾越节预表基督。','["exodus","salvation","sacrifice"]','["出12-14"]','神是听见与拯救的神。'),
 ('sinai_law','西奈与律法','神在西奈赐律法,立以色列为属他的子民。',6,'old_testament','律法是盟约的回应,显明圣洁与爱。','["covenant","law","holiness"]','["出19-20"]','回应恩典而活,不是赚取。'),
 ('tabernacle_priesthood','会幕与祭司','神借会幕住在民中,设祭司与献祭。',7,'old_testament','圣洁的神借遮罪与中保与人同住。','["temple","priesthood","sacrifice"]','["出25-40","利"]','与神同住需要中保与遮罪。'),
 ('land_judges','应许之地与士师','进入迦南,循环堕落与拯救。',8,'old_testament','人的反复失败凸显对君王与救主的需要。','["kingdom","exile","sin"]','["书","士"]','循环的失败指向更深的救赎。'),
 ('kingdom','君主国度','以色列立王,扫罗、大卫、所罗门。',9,'old_testament','国度盼望兴起,也暴露人君的不足。','["kingdom","messiah"]','["撒上-撒下"]','对真王的渴望。'),
 ('davidic_covenant','大卫之约','神应许大卫的后裔要永远坐宝座。',10,'old_testament','弥赛亚君王的应许聚焦于大卫之家。','["covenant","kingdom","messiah"]','["撒下7"]','基督是大卫的子孙、真王。'),
 ('divided_kingdom','分裂的王国','国分南北,偶像与不义渐增。',11,'old_testament','背约带来审判,但神存留余民。','["exile","sin","remnant"]','["王上-王下"]','背约的后果与存留的恩典。'),
 ('prophets','先知','神差先知呼召悔改,预言审判与盼望。',12,'old_testament','先知既宣告审判,也应许新约与新心。','["covenant","judgment","messiah","spirit"]','["赛","耶","结"]','悔改与新约盼望。'),
 ('exile','被掳','北国南国相继被掳,圣殿被毁。',13,'old_testament','被掳是审判,却非终局;神仍信实。','["exile","judgment","remnant"]','["耶","哀","结"]','在失去与黑暗中持守盼望。'),
 ('return','归回','余民归回,重建圣殿与城墙。',14,'old_testament','归回不完全,渴望更大的拯救。','["return","temple","remnant"]','["拉","尼","该"]','部分的成全指向更大的盼望。'),
 ('wisdom_waiting','智慧与等候','智慧文学与两约之间的等候。',15,'intertestamental','在等候中操练敬畏、智慧与盼望。','["wisdom","messiah"]','["伯","箴","传","诗"]','在等候中持守敬畏与盼望。'),
 ('incarnation','道成肉身','神的儿子取了肉身,住在我们中间。',16,'new_testament','应许成全的开始:神与人同在。','["messiah","temple","promise"]','["约1","路1-2"]','神亲自进入我们的处境。'),
 ('kingdom_of_god','神的国','耶稣宣告并彰显神国的降临。',17,'new_testament','神的国在基督里已然临到、尚未完全。','["kingdom","messiah","spirit"]','["可1:15","太5-7"]','活在已然未然之间。'),
 ('cross','十字架','基督受死,担当罪、成就救赎。',18,'new_testament','十架成全了一切献祭与盟约的指向。','["sacrifice","salvation","covenant"]','["可15","约19"]','你被接纳靠基督已成之工。'),
 ('resurrection','复活','基督身体复活,胜过死亡。',19,'new_testament','复活是新创造的开端与确据。','["new_creation","salvation","kingdom"]','["路24","林前15"]','复活给忠心与盼望以确据。'),
 ('ascension','升天','基督升天,坐在父的右边掌权。',20,'new_testament','升天的基督是掌权的主与中保。','["kingdom","priesthood"]','["徒1","来"]','基督正在掌权与代求。'),
 ('pentecost','五旬节','圣灵浇灌,教会诞生。',21,'new_testament','圣灵内住,神的子民成为新圣殿。','["spirit","temple","mission","new_creation"]','["徒2"]','圣灵使你成为神的居所。'),
 ('church_mission','教会与使命','教会被差遣,在万民中作门徒。',22,'new_testament','神借教会把祝福带向地极。','["mission","kingdom","spirit"]','["徒","太28:18-20"]','你被差遣作见证。'),
 ('new_creation','新创造','基督再来,新天新地,神与人同住。',23,'new_testament','救赎历史的终点:万物更新,神人同住。','["new_creation","temple","kingdom"]','["启21-22"]','盼望给当下忠心以意义。')
ON CONFLICT (era_key) DO NOTHING;

INSERT INTO covenant_profiles (covenant_key, display_name, covenant_type, description, parties, promises, signs, scripture_refs, fulfillment_notes, sort_order) VALUES
 ('creation','创造之约','creation','神与受造界、与人的起初秩序。','["神","亚当/人类"]','["管理受造界","与神同在","多结果实"]','["安息日"]','["创1-2"]','基督是末后的亚当,带来新创造。',1),
 ('noahic','挪亚之约','noahic','洪水后神与一切有血肉的立约,存留世界。','["神","挪亚/受造界"]','["不再以洪水灭世","季节存续"]','["彩虹"]','["创9"]','神对受造界的忍耐与信实。',2),
 ('abrahamic','亚伯拉罕之约','abrahamic','应许后裔、土地、万国得福。','["神","亚伯拉罕"]','["后裔如星","土地","万国蒙福"]','["割礼"]','["创12","创15","创17"]','基督是那后裔,使万国蒙福(加3)。',3),
 ('mosaic','摩西之约','mosaic','西奈所立,以律法规范盟约子民的生活。','["神","以色列"]','["作属神子民","蒙福(顺服)"]','["安息日","律法"]','["出19-24"]','基督成全律法,赐新心与圣灵。',4),
 ('davidic','大卫之约','davidic','应许大卫后裔永坐宝座。','["神","大卫家"]','["永远的国与宝座"]','[]','["撒下7","诗89"]','基督是大卫的子孙、永远的王。',5),
 ('new_covenant','新约','new_covenant','应许赦罪、新心、内住的圣灵、认识神。','["神","他的子民"]','["赦罪","新心","圣灵内住","都认识神"]','["主餐","圣灵"]','["耶31","路22:20","来8"]','基督的血所立,今在教会中实现,将来完全成全。',6)
ON CONFLICT (covenant_key) DO NOTHING;
