-- Enrich the biblical knowledge graph in three layers:
--   A. Extend node fields (hebrew/greek name, gender, tribe, nation, family line, christ typology).
--   B. Populate member edges for previously empty list/group container nodes
--      (Paul greetings, priesthood, levites, returnees, Solomon officials, Nehemiah wall builders, genealogies, parables).
--   C. Densify core character networks (Moses, Abraham, Jesus, Paul, David, Joshua, Elijah, Daniel...)
--      with place / event / theme / typology edges, matching the "people-family-place-event-book-theme" goal.
--
-- The migration is idempotent: columns use ADD COLUMN IF NOT EXISTS, edges use ON CONFLICT DO NOTHING,
-- and character references are resolved through biblical_characters so unmatched names are silently skipped.

-- ============================================================
-- PART A. Node profile fields
-- ============================================================
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS hebrew_name VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS greek_name VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS tribe VARCHAR(60);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS nation VARCHAR(60);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS family_line VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS christ_typology TEXT[];

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'biblical_graph_nodes_gender_check'
          AND conrelid = 'biblical_graph_nodes'::regclass
    ) THEN
        ALTER TABLE biblical_graph_nodes
            ADD CONSTRAINT biblical_graph_nodes_gender_check
            CHECK (gender IS NULL OR gender IN ('male', 'female', 'unknown'));
    END IF;
END $$;

-- Coarse gender backfill from the mirror character role (镜鉴中以"女性"归类的人物)
UPDATE biblical_graph_nodes n
SET gender = 'female'
FROM biblical_characters c
WHERE n.character_id = c.id
  AND c.role = '女性'
  AND n.gender IS NULL;

-- Curated profile backfill for core figures.
-- name|hebrew|greek|gender|tribe|nation|family_line|christ_typology
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($profiles$
亚当|אָדָם||male|||人类始祖|末后的亚当（罗5、林前15）
夏娃|חַוָּה||female|||人类之母|
挪亚|נֹחַ||male|||塞特一系|藉方舟拯救预表基督里的救恩
亚伯拉罕|אַבְרָהָם||male||迦勒底吾珥/迦南|信心之父|献以撒预表父神舍子
撒拉|שָׂרָה||female|||亚伯拉罕家族|
以撒|יִצְחָק||male|||亚伯拉罕—以撒—雅各|被献的独生子预表基督
利百加|רִבְקָה||female|||亚伯拉罕家族|
雅各|יַעֲקֹב||male||以色列|以色列十二支派之父|
利亚|לֵאָה||female|||雅各家族|
拉结|רָחֵל||female|||雅各家族|
约瑟|יוֹסֵף||male|以法莲/玛拿西||雅各家族|被弃后高升拯救全家预表基督
犹大（雅各之子）|יְהוּדָה||male|犹大||雅各家族|弥赛亚所出的支派
摩西|מֹשֶׁה||male|利未|以色列|暗兰家族|先知—中保预表基督
亚伦|אַהֲרֹן||male|利未|以色列|暗兰家族|大祭司职分预表基督
米利暗|מִרְיָם||female|利未||暗兰家族|
约书亚|יְהוֹשֻׁעַ||male|以法莲|以色列|嫩的儿子|带领进入安息预表基督
喇合（进入迦南）|רָחָב||female||迦南|基督肉身家谱|
路得|רוּת||female||摩押|大卫—基督家谱|
波阿斯|בֹּעַז||male|犹大||大卫—基督家谱|救赎亲属预表基督
撒母耳|שְׁמוּאֵל||male|利未|以色列|以利加拿家族|
扫罗|שָׁאוּל||male|便雅悯|以色列|基士家族|
大卫|דָּוִד||male|犹大|以色列|大卫王朝|受膏牧者君王预表基督
所罗门|שְׁלֹמֹה||male|犹大|以色列|大卫王朝|建殿君王预表基督
拔示巴|בַּת־שֶׁבַע||female|||大卫王朝|
押沙龙|אַבְשָׁלוֹם||male|犹大|以色列|大卫王朝|
以利亚|אֵלִיָּהוּ||male||北国以色列||被提与再来相关预表
以利沙|אֱלִישָׁע||male||北国以色列||
以赛亚|יְשַׁעְיָהוּ||male|犹大|南国犹大||受苦仆人预言的传讲者
耶利米|יִרְמְיָהוּ||male|利未|南国犹大|希勒家祭司家族|流泪先知预表受苦基督
以西结|יְחֶזְקֵאל||male|利未|犹大被掳群体|布西家族|
但以理|דָּנִיֵּאל||male|犹大|犹大被掳群体||
以斯帖|אֶסְתֵּר||female|便雅悯|波斯帝国|基士—末底改家族|
末底改|מָרְדֳּכַי||male|便雅悯|波斯帝国|基士家族|
尼希米|נְחֶמְיָה||male||波斯帝国/犹大||
以斯拉|עֶזְרָא||male|利未|波斯帝国/犹大|亚伦祭司家族|
约伯|אִיּוֹב||male||乌斯地||受苦中持守信心预表
耶稣基督||Ἰησοῦς|male|犹大|以色列|大卫王朝—弥赛亚谱系|神的儿子、弥赛亚本体
马利亚||Μαρία|female|犹大||大卫王朝|
约瑟（耶稣父亲）||Ἰωσήφ|male|犹大||大卫王朝|
施洗约翰||Ἰωάννης|male|利未||撒迦利亚祭司家族|以利亚样式的先锋
彼得||Πέτρος|male|||约拿/约翰之子|
约翰||Ἰωάννης|male|||西庇太家族|
保罗||Παῦλος|male|便雅悯|罗马公民|大数的扫罗|
巴拿巴||Βαρνάβας|male|利未|居比路||
提摩太||Τιμόθεος|male||路司得||
路加||Λουκᾶς|male||外邦|医生—史家|
马可||Μᾶρκος|male||||
马太||Ματθαῖος|male||||
安得烈||Ἀνδρέας|male|||约拿之子|
腓力||Φίλιππος|male||伯赛大||
多马||Θωμᾶς|male||||
$profiles$, E'\n')
), parsed AS (
    SELECT
        string_to_array(line, '|') AS parts
    FROM raw
    WHERE line <> ''
), profile AS (
    SELECT
        parts[1] AS name,
        NULLIF(parts[2], '') AS hebrew_name,
        NULLIF(parts[3], '') AS greek_name,
        NULLIF(parts[4], '') AS gender,
        NULLIF(parts[5], '') AS tribe,
        NULLIF(parts[6], '') AS nation,
        NULLIF(parts[7], '') AS family_line,
        NULLIF(parts[8], '') AS typology
    FROM parsed
)
UPDATE biblical_graph_nodes n
SET
    hebrew_name = COALESCE(p.hebrew_name, n.hebrew_name),
    greek_name = COALESCE(p.greek_name, n.greek_name),
    gender = COALESCE(p.gender, n.gender),
    tribe = COALESCE(p.tribe, n.tribe),
    nation = COALESCE(p.nation, n.nation),
    family_line = COALESCE(p.family_line, n.family_line),
    christ_typology = CASE
        WHEN p.typology IS NOT NULL THEN ARRAY[p.typology]
        ELSE n.christ_typology
    END
FROM biblical_characters c
JOIN profile p ON p.name = c.name
WHERE n.character_id = c.id;

-- ============================================================
-- PART B/C prerequisites: extra place nodes + MEMBER_OF relationship type
-- ============================================================
INSERT INTO biblical_graph_nodes (
    id, node_type, name, name_en, category, description,
    chinese_name, english_name, aliases, testament, importance_level, summary
)
VALUES
    ('place-midian', 'place', '米甸', 'Midian', 'location', '摩西逃亡牧羊、娶西坡拉并蒙召之地。', '米甸', 'Midian', ARRAY['米甸', 'Midian'], 'Old Testament', 'C', '摩西在米甸牧羊四十年并在何烈山蒙召。'),
    ('place-tarsus', 'place', '大数', 'Tarsus', 'location', '保罗的出生城与早年成长地。', '大数', 'Tarsus', ARRAY['大数', 'Tarsus'], 'New Testament', 'C', '保罗生于基利家的大数，拥有罗马公民身份。'),
    ('place-mount-carmel', 'place', '迦密山', 'Mount Carmel', 'location', '以利亚与巴力先知对决之地。', '迦密山', 'Mount Carmel', ARRAY['迦密山', 'Mount Carmel'], 'Old Testament', 'C', '以利亚在迦密山求火降下，证明耶和华是神。')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    description = EXCLUDED.description,
    summary = EXCLUDED.summary,
    is_active = true;

INSERT INTO biblical_graph_relationship_types (
    relationship_type, relationship_category, label_zh, label_en, description,
    inverse_type, target_types, sort_order, is_core
)
VALUES
    ('MEMBER_OF', 'other', '名单/群体成员', 'member of', '人物属于某名单、群体、谱系或职分体系。', 'CONTAINS_MEMBER', ARRAY['group', 'event', 'nation'], 750, true),
    ('CONTAINS_MEMBER', 'other', '包含成员', 'contains member', '群组、名单或谱系容器包含某成员。', 'MEMBER_OF', ARRAY['character'], 760, false)
ON CONFLICT (relationship_type) DO UPDATE SET
    relationship_category = EXCLUDED.relationship_category,
    label_zh = EXCLUDED.label_zh,
    label_en = EXCLUDED.label_en,
    description = EXCLUDED.description,
    inverse_type = EXCLUDED.inverse_type,
    target_types = EXCLUDED.target_types,
    sort_order = EXCLUDED.sort_order,
    is_core = true,
    is_active = true;

-- ============================================================
-- PART B + C edges
-- Format: source_kind|source_ref|target_kind|target_ref|rel|cat|label|scripture|desc|weight
-- character refs resolve through biblical_characters.name; unmatched rows are skipped.
-- ============================================================
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($edges$
-- ---- B1. 保罗书信问安/同工名单 (event-paul-greetings) ----
character|友阿爹|event|paul-greetings|MEMBER_OF|other|问安人物|腓4:2|友阿爹出现在保罗腓立比书劝勉问安中。|2.0
character|循都基|event|paul-greetings|MEMBER_OF|other|问安人物|腓4:2|循都基出现在保罗腓立比书劝勉问安中。|2.0
character|腓比|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:1|腓比是保罗推荐递送罗马书的女执事。|2.4
character|亚居拉与百基拉|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:3|亚居拉与百基拉是保罗问安的核心同工夫妇。|2.4
character|马可|event|paul-greetings|MEMBER_OF|other|问安人物|西4:10,提后4:11|马可出现在保罗书信问安与同工网络中。|2.0
character|路加|event|paul-greetings|MEMBER_OF|other|问安人物|西4:14,提后4:11|路加是保罗书信问安中常伴的同工。|2.2
character|提摩太|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:21|提摩太与保罗一同问安众教会。|2.2
character|提多|event|paul-greetings|MEMBER_OF|other|问安人物|多1:4|提多是保罗书信中差遣与问安的同工。|2.0
character|底马|event|paul-greetings|MEMBER_OF|other|问安人物|西4:14,提后4:10|底马曾是保罗同工，后贪爱世界离开。|1.8
character|阿尼西母|event|paul-greetings|MEMBER_OF|other|问安人物|西4:9,门10|阿尼西母由保罗带领归主并随书信问安。|1.8
character|腓利门|event|paul-greetings|MEMBER_OF|other|问安人物|门1|腓利门是保罗写信问安的歌罗西信徒。|1.8
character|亚波罗|event|paul-greetings|MEMBER_OF|other|问安人物|多3:13|亚波罗在保罗同工与书信嘱托网络中。|1.8
character|西拉|event|paul-greetings|MEMBER_OF|other|问安人物|帖前1:1|西拉与保罗一同问安帖撒罗尼迦教会。|1.8
-- ---- B2. 祭司体系 (group-priesthood + event-priestly-divisions) ----
character|亚伦|group|priesthood|PRIEST_OF|spiritual|大祭司|出28-29|亚伦是以色列首任大祭司。|3.0
character|以利亚撒|group|priesthood|PRIEST_OF|spiritual|大祭司|民20:28|以利亚撒承接亚伦作大祭司。|2.4
character|以他玛|group|priesthood|PRIEST_OF|spiritual|祭司|出6:23|以他玛是亚伦祭司家族成员。|2.0
character|非尼哈|group|priesthood|PRIEST_OF|spiritual|祭司|民25|非尼哈以热心存留永远祭司之约。|2.4
character|撒督|group|priesthood|PRIEST_OF|spiritual|祭司|撒下15,王上1|撒督是大卫所罗门时期忠心祭司。|2.4
character|亚比亚他|group|priesthood|PRIEST_OF|spiritual|祭司|撒上22-23|亚比亚他在大卫患难时期作祭司。|2.0
character|希勒家|group|priesthood|PRIEST_OF|spiritual|大祭司|王下22|希勒家在约西亚时期发现律法书。|2.2
character|耶何耶大|group|priesthood|PRIEST_OF|spiritual|大祭司|王下11|耶何耶大保护约阿施并主导宗教改革。|2.4
character|耶书亚/约书亚，大祭司|group|priesthood|PRIEST_OF|spiritual|大祭司|该1,亚3|耶书亚是归回后重建圣殿的大祭司。|2.4
character|亚希米勒|group|priesthood|PRIEST_OF|spiritual|祭司|撒上21-22|亚希米勒是挪伯祭司，帮助大卫。|2.0
character|以利亚撒|event|priestly-divisions|MEMBER_OF|other|祭司班次|代上24|以利亚撒一系构成祭司班次主干。|2.0
character|以他玛|event|priestly-divisions|MEMBER_OF|other|祭司班次|代上24|以他玛一系构成祭司班次另一支。|2.0
character|撒迦利亚（约翰父亲）|event|priestly-divisions|MEMBER_OF|other|祭司班次|路1:5|撒迦利亚属亚比雅班次祭司。|2.0
-- ---- B3. 利未人 (group-levites + event-levite-lists) ----
character|利未（雅各之子）|group|levites|MEMBER_OF|other|利未支派源头|创29:34|利未是利未支派的源头。|2.2
character|可拉|event|levite-lists|MEMBER_OF|other|利未人|民16|可拉是利未人，后因叛乱受罚。|2.0
character|可拉的后裔|event|levite-lists|MEMBER_OF|other|利未歌者|代上6,诗篇|可拉后裔成为圣殿歌唱者。|2.0
character|比撒列|event|levite-lists|MEMBER_OF|other|会幕工匠|出31|比撒列受感建造会幕（属犹大支派的圣所工匠）。|1.8
-- ---- B4. 归回名单 (event-returnee-lists) ----
character|所罗巴伯|event|returnee-lists|MEMBER_OF|other|归回领袖|拉2-3|所罗巴伯带领首批被掳者归回并重建圣殿。|2.6
character|耶书亚/约书亚，大祭司|event|returnee-lists|MEMBER_OF|other|归回领袖|拉3|耶书亚与所罗巴伯同领归回重建。|2.4
character|以斯拉|event|returnee-lists|MEMBER_OF|other|归回领袖|拉7|以斯拉带领第二批归回并教导律法。|2.6
character|尼希米|event|returnee-lists|MEMBER_OF|other|归回领袖|尼2|尼希米归回重建耶路撒冷城墙。|2.6
character|设巴萨|event|returnee-lists|MEMBER_OF|other|归回领袖|拉1:8|设巴萨是首批归回的犹大首领。|2.0
character|古列|event|returnee-lists|INITIATED|event|发起归回|拉1|古列下诏开启被掳归回。|2.6
-- ---- B5. 尼希米修墙名单 (event-nehemiah-wall-builders) ----
character|尼希米|event|nehemiah-wall-builders|LED|event|带领修墙|尼3-6|尼希米带领百姓修造城墙。|2.8
character|以利亚实|event|nehemiah-wall-builders|MEMBER_OF|other|修墙者|尼3:1|大祭司以利亚实带领祭司修造羊门。|2.0
character|参巴拉|event|nehemiah-wall-builders|OPPOSED|event|反对修墙|尼4|参巴拉竭力阻挠修墙。|2.2
character|多比雅|event|nehemiah-wall-builders|OPPOSED|event|反对修墙|尼4|多比雅与参巴拉一同反对修墙。|2.2
character|基善/迦施慕|event|nehemiah-wall-builders|OPPOSED|event|反对修墙|尼6|基善散布谣言威胁尼希米。|2.0
-- ---- B6. 所罗门官员 (event-solomon-officials) ----
character|比拿雅|event|solomon-officials|MEMBER_OF|other|军长|王上2:35|比拿雅被所罗门立为军队元帅。|2.2
character|撒督|event|solomon-officials|MEMBER_OF|other|大祭司|王上2:35|撒督在所罗门朝作大祭司。|2.0
character|希兰|event|solomon-officials|MEMBER_OF|other|建殿盟友|王上5|推罗王希兰供应建殿材料。|2.0
character|户兰/希兰匠人|event|solomon-officials|MEMBER_OF|other|建殿工匠|王上7:13|户兰巧匠负责圣殿铜器工程。|2.0
-- ---- B7. 十二支派族长后裔 (event-twelve-tribe-descendants) ----
character|流便（雅各长子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:3|流便是雅各长子与支派祖。|2.0
character|犹大（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:8|犹大支派出君王与弥赛亚。|2.4
character|但（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:16|但是雅各之子与支派祖。|1.8
character|拿弗他利（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:21|拿弗他利是支派祖。|1.8
character|迦得（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:19|迦得是支派祖。|1.8
character|亚设（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:20|亚设是支派祖。|1.8
character|以萨迦（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:14|以萨迦是支派祖。|1.8
character|西布伦（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:13|西布伦是支派祖。|1.8
character|便雅悯（雅各之子）|event|twelve-tribe-descendants|MEMBER_OF|other|十二支派|创49:27|便雅悯是雅各幼子与支派祖。|2.0
character|玛拿西（约瑟长子）|event|twelve-tribe-descendants|MEMBER_OF|other|约瑟支派|创48|玛拿西承接约瑟支派之一。|1.8
character|以法莲（约瑟次子）|event|twelve-tribe-descendants|MEMBER_OF|other|约瑟支派|创48|以法莲承接约瑟支派之一并得大福。|2.0
-- ---- B8. 创世记/历代志族谱 (genealogy containers) ----
character|亚当|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5|亚当居创世记家谱之首。|2.0
character|塞特|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5:3|塞特延续敬虔后裔家谱。|1.8
character|玛土撒拉|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5:27|玛土撒拉是创世记最长寿者。|1.8
character|挪亚|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5:32|挪亚承接亚当至亚伯拉罕家谱。|2.0
character|亚当|event|chronicles-genealogies|MEMBER_OF|other|历代志族谱|代上1:1|历代志家谱由亚当开始。|1.8
character|大卫|event|chronicles-genealogies|MEMBER_OF|other|历代志族谱|代上3|历代志详述大卫家谱。|2.0
character|所罗门|event|chronicles-genealogies|MEMBER_OF|other|历代志族谱|代上3:10|历代志记载所罗门及犹大列王家谱。|1.8
-- ---- B9. 比喻人物 (event-parable-figures) ----
character|好撒玛利亚人|event|parable-figures|MEMBER_OF|other|比喻人物|路10:30-37|好撒玛利亚人是怜悯邻舍的比喻典范。|2.0
character|迷失的羊/儿子|event|parable-figures|MEMBER_OF|other|比喻人物|路15|失羊失钱浪子比喻彰显寻回的恩典。|2.0
-- ---- C1. 摩西网络 ----
character|摩西|place|midian|LIVED_IN|location|居住/牧羊|出2-3|摩西在米甸牧羊四十年。|2.4
character|摩西|place|mount-sinai|MINISTERED_IN|location|领受律法|出19-34|摩西在西奈山领受律法。|3.0
character|摩西|event|sinai-covenant|LED|event|带领立约|出19-24|摩西在西奈山为以色列立约。|3.2
character|摩西|event|wilderness-rebellion|PARTICIPATED_IN|event|经历旷野|民14-17|摩西在旷野面对百姓反叛。|2.6
character|摩西|group|israelites|LED|event|带领约民|出-申|摩西带领以色列约民四十年。|3.0
character|摩西|theme|worship|HAS_THEME|other|敬拜主题|出25-40|摩西按神样式立会幕敬拜。|2.4
character|摩西|theme|christ-typology|TYPOLOGY_OF_CHRIST|other|基督预表|申18:15|摩西作先知与中保预表那要来的先知基督。|2.8
character|西坡拉|character|摩西|SPOUSE_OF|family|夫妻|出2:21|西坡拉是摩西在米甸所娶的妻子。|2.2
-- ---- C2. 亚伯拉罕网络 ----
character|亚伯拉罕|event|abraham-call|PARTICIPATED_IN|event|蒙召|创12|亚伯拉罕因信离开本地本族。|2.8
character|亚伯拉罕|event|isaac-sacrifice|PARTICIPATED_IN|event|献以撒|创22|亚伯拉罕信心受试献以撒。|3.0
character|亚伯拉罕|place|canaan|TRAVELED_TO|location|前往应许地|创12|亚伯拉罕进入神所指示的迦南。|2.4
character|亚伯拉罕|theme|messianic-line|HAS_THEME|other|弥赛亚谱系|创12:3,加3|万族因亚伯拉罕的后裔得福。|2.8
character|以撒|event|isaac-sacrifice|PARTICIPATED_IN|event|被献|创22|以撒顺服被献预表基督。|2.6
character|以撒|theme|christ-typology|TYPOLOGY_OF_CHRIST|other|基督预表|创22|独生爱子被献预表父神舍子。|2.6
-- ---- C3. 耶稣网络 ----
character|耶稣基督|event|incarnation|PARTICIPATED_IN|event|道成肉身|约1:14|道成肉身住在人间。|3.0
character|耶稣基督|event|baptism-jesus|PARTICIPATED_IN|event|受洗|太3|耶稣受洗显明三一神。|2.8
character|耶稣基督|event|crucifixion|DIED_IN|event|受难|约19|耶稣为世人的罪被钉死。|3.5
character|耶稣基督|event|resurrection|PARTICIPATED_IN|event|复活|路24|耶稣第三日从死里复活。|3.5
character|耶稣基督|place|galilee|MINISTERED_IN|location|加利利传道|太4|耶稣主要传道事工在加利利。|2.8
character|耶稣基督|place|jerusalem|MINISTERED_IN|location|耶路撒冷|约2,12|耶稣多次上耶路撒冷并在此受难复活。|3.0
character|耶稣基督|place|jordan|TRAVELED_TO|location|约旦河受洗|太3|耶稣到约旦河受洗。|2.4
character|耶稣基督|theme|messianic-line|HAS_THEME|other|弥赛亚谱系|太1|耶稣是弥赛亚谱系的成全。|3.2
character|耶稣基督|theme|davidic-covenant|HAS_THEME|other|大卫之约|路1:32|耶稣承受大卫之约永远的国位。|3.0
-- ---- C4. 保罗网络 ----
character|保罗|event|paul-conversion|PARTICIPATED_IN|event|大马士革蒙召|徒9|保罗在大马士革路上遇见复活主。|3.0
character|保罗|place|tarsus|BORN_IN|location|出生于|徒22:3|保罗生于基利家的大数。|2.4
character|保罗|place|damascus|TRAVELED_TO|location|前往大马士革|徒9|保罗往大马士革途中悔改。|2.4
character|保罗|place|corinth|MINISTERED_IN|location|哥林多事工|徒18|保罗在哥林多建立教会。|2.4
character|保罗|theme|spiritual-application|HAS_APPLICATION|other|属灵应用|腓3|保罗以追求基督的榜样塑造门徒。|2.2
character|巴拿巴|place|cyprus|MINISTERED_IN|location|居比路宣教|徒13|巴拿巴与保罗在居比路传道。|2.2
character|巴拿巴|character|保罗|MENTOR_OF|spiritual|举荐同工|徒9,11|巴拿巴接纳举荐刚悔改的保罗。|2.6
-- ---- C5. 约书亚 / 以利亚 / 但以理 / 以斯帖 ----
character|约书亚|place|jericho|PARTICIPATED_IN|event|攻取耶利哥|书6|约书亚带领攻取耶利哥。|2.6
character|约书亚|group|israelites|LED|event|带领约民|书1-24|约书亚承接摩西带领以色列。|2.6
character|以利亚|place|mount-carmel|MINISTERED_IN|location|迦密山对决|王上18|以利亚在迦密山求火降下。|2.8
character|以利亚|nation|northern-israel|PROPHET_OF|spiritual|先知|王上17-19|以利亚在北国向亚哈传神的话。|2.6
character|以利亚|theme|repentance|HAS_THEME|other|悔改主题|王上18:37|以利亚呼吁百姓回转归向耶和华。|2.2
character|但以理|place|babylon|LIVED_IN|location|被掳为臣|但1-6|但以理在巴比伦宫廷持守信仰。|2.6
character|但以理|event|babylonian-exile|PARTICIPATED_IN|event|被掳|但1|但以理少年时被掳到巴比伦。|2.4
character|以斯帖|nation|persian-empire|MEMBER_OF|other|波斯王后|斯2|以斯帖成为波斯王后拯救本族。|2.6
character|末底改|nation|persian-empire|MEMBER_OF|other|波斯宫廷|斯2|末底改在波斯宫廷扶持以斯帖。|2.4
$edges$, E'\n')
), edge_seed AS (
    SELECT
        row_number() OVER () AS ord,
        parts[1] AS source_kind,
        parts[2] AS source_ref,
        parts[3] AS target_kind,
        parts[4] AS target_ref,
        parts[5] AS relationship_type,
        parts[6] AS relationship_category,
        parts[7] AS label_zh,
        parts[8] AS scripture_ref,
        parts[9] AS description,
        parts[10]::numeric AS weight
    FROM raw
    CROSS JOIN LATERAL (SELECT string_to_array(line, '|') AS parts) parsed
    WHERE line <> '' AND line NOT LIKE '--%'
), resolved AS (
    SELECT
        edge_seed.*,
        CASE
            WHEN source_kind = 'character' THEN source_char_node.id
            ELSE source_kind || '-' || source_ref
        END AS source_node_id,
        CASE
            WHEN target_kind = 'character' THEN target_char_node.id
            ELSE target_kind || '-' || target_ref
        END AS target_node_id
    FROM edge_seed
    LEFT JOIN biblical_characters source_char
        ON source_kind = 'character' AND source_char.name = source_ref AND source_char.is_active = true
    LEFT JOIN biblical_graph_nodes source_char_node
        ON source_char_node.character_id = source_char.id AND source_char_node.is_active = true
    LEFT JOIN biblical_characters target_char
        ON target_kind = 'character' AND target_char.name = target_ref AND target_char.is_active = true
    LEFT JOIN biblical_graph_nodes target_char_node
        ON target_char_node.character_id = target_char.id AND target_char_node.is_active = true
)
INSERT INTO biblical_graph_edges (
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
)
SELECT
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    relationship_type,
    scripture_ref,
    description,
    weight,
    0.9,
    relationship_type NOT IN ('SPOUSE_OF', 'SIBLING_OF', 'ALLIED_WITH'),
    40000 + ord,
    ARRAY_REMOVE(ARRAY[scripture_ref], NULL),
    'high'
FROM resolved
WHERE source_node_id IS NOT NULL
  AND target_node_id IS NOT NULL
  AND source_node_id <> target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = target_node_id)
ON CONFLICT DO NOTHING;

-- Auto-generate inverse CONTAINS_MEMBER edges for container membership.
WITH member_edges AS (
    SELECT *
    FROM biblical_graph_edges
    WHERE is_active = true
      AND relationship_type = 'MEMBER_OF'
)
INSERT INTO biblical_graph_edges (
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
)
SELECT
    target_node_id,
    source_node_id,
    'CONTAINS_MEMBER',
    'other',
    '包含成员',
    'contains member',
    scripture_ref,
    '由成员关系自动生成的反向包含关系：' || description,
    GREATEST(weight - 0.2, 0.1),
    confidence,
    true,
    sort_order + 1,
    scripture_refs,
    confidence_level
FROM member_edges
WHERE source_node_id <> target_node_id
ON CONFLICT DO NOTHING;
