-- Standard relationship capabilities and canonical edges for the biblical knowledge graph.
-- The graph should be queryable as people-family-place-event-book-theme-application,
-- not only as a flat character list.

ALTER TABLE biblical_graph_nodes DROP CONSTRAINT IF EXISTS biblical_graph_nodes_node_type_check;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'biblical_graph_nodes_node_type_check'
          AND conrelid = 'biblical_graph_nodes'::regclass
    ) THEN
        ALTER TABLE biblical_graph_nodes
            ADD CONSTRAINT biblical_graph_nodes_node_type_check
            CHECK (node_type IN ('character', 'event', 'place', 'nation', 'group', 'theme', 'book'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS biblical_graph_relationship_types (
    relationship_type VARCHAR(60) PRIMARY KEY,
    relationship_category VARCHAR(30) NOT NULL
        CHECK (relationship_category IN ('family', 'spiritual', 'political', 'event', 'location', 'other')),
    label_zh VARCHAR(100) NOT NULL,
    label_en VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    inverse_type VARCHAR(60),
    target_types TEXT[] NOT NULL DEFAULT '{}',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_core BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DROP TRIGGER IF EXISTS update_biblical_graph_relationship_types_updated_at ON biblical_graph_relationship_types;
CREATE TRIGGER update_biblical_graph_relationship_types_updated_at
    BEFORE UPDATE ON biblical_graph_relationship_types
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($types$
FATHER_OF|family|父亲|father of|父亲到儿女的直接家族关系。|CHILD_OF|character|10
MOTHER_OF|family|母亲|mother of|母亲到儿女的直接家族关系。|CHILD_OF|character|20
SPOUSE_OF|family|丈夫/妻子|spouse of|婚姻关系，通常为无向关系。|SPOUSE_OF|character|30
CHILD_OF|family|儿子/女儿|child of|儿女到父母的直接家族关系。|FATHER_OF|character|40
SIBLING_OF|family|兄弟姐妹|sibling of|兄弟姐妹关系，通常为无向关系。|SIBLING_OF|character|50
DESCENDANT_OF|family|后裔|descendant of|后裔到祖先或谱系源头的关系。|ANCESTOR_OF|character|60
ANCESTOR_OF|family|祖先|ancestor of|祖先到后裔的谱系关系。|DESCENDANT_OF|character|70
PROPHET_OF|spiritual|先知|prophet of|先知向某群体、君王或时代传讲神话语。||person,group,nation|110
PRIEST_OF|spiritual|祭司|priest of|祭司服事神并代表百姓办理圣所礼仪。||group,nation|120
KING_OF|spiritual|君王|king of|君王治理某国、群体或时代。|RULED_OVER|nation,group|130
JUDGE_OF|spiritual|士师|judge of|士师在以色列中审判、拯救和带领。||group,nation|140
APOSTLE_OF|spiritual|使徒|apostle of|使徒受差遣为复活基督作见证并建立教会。||group,theme|150
DISCIPLE_OF|spiritual|门徒|disciple of|门徒跟随师傅或主。||character|160
PREACHED_TO|spiritual|传道给|preached to|向某人或群体传讲福音、律法或神的话。||person,group,nation|170
ANOINTED|spiritual|膏立|anointed|膏立某人为君王、祭司或特别职分。|ANOINTED_BY|character|180
ANOINTED_BY|spiritual|受膏于|anointed by|某人被另一人膏立。|ANOINTED|character|190
SENT_BY|spiritual|差遣|sent by|被某人、教会或神差遣承担使命。||person,group,theme|200
MENTOR_OF|spiritual|栽培/师徒|mentor of|属灵栽培、教导或传承关系。||character|210
CALLED|spiritual|呼召|called|呼召某人跟随、服事或承担使命。||character|220
RULED_OVER|political|统治|ruled over|政治治理或王权管辖关系。|KING_OF|nation,group,place|310
ATTACKED|political|攻打|attacked|军事或政治攻击关系。||person,place,nation,group|320
DEFEATED|political|击败|defeated|在战争、冲突或审判中击败对方。||person,place,nation,group|330
ALLIED_WITH|political|联盟|allied with|政治或军事联盟关系，通常为无向。|ALLIED_WITH|person,nation,group|340
REBELLED_AGAINST|political|背叛/反叛|rebelled against|背叛、叛乱或公开反抗权柄。||person,nation,group|350
CONQUERED|political|攻陷/征服|conquered|攻陷城市、征服国家或压制群体。||place,nation,group|360
EXILED_TO|political|被掳到|exiled to|个人或群体被掳、迁移到某地。||place,nation|370
EXILED|political|掳掠|exiled|国家或势力掳掠某群体。||group,nation|380
RELEASED_BY|political|释放|released by|某人或群体被有权柄者释放。||person,nation,group|390
ALLOWED_RETURN|political|准许归回|allowed return|君王或政权允许被掳者归回。||group,nation|400
PARTICIPATED_IN|event|参与事件|participated in|人物参与某事件。||event|510
WITNESSED|event|见证事件|witnessed|人物见证某事件。||event|520
INITIATED|event|发起事件|initiated|人物或势力发起某事件。||event|530
OPPOSED|event|反对事件|opposed|人物反对某事件、使命或神的工作。||event,person,group|540
DIED_IN|event|死于事件/地点|died in|人物死于某事件或地点。||event,place|550
CAUSED|event|造成事件|caused|人物行为导致某事件发生。||event|560
LED|event|带领事件|led|人物带领某事件、行动或群体。||event,group|570
PREACHED_AT|event|讲道于|preached at|人物在某事件中讲道。||event|580
JOURNEYED_TO|event|行程到达|journeyed to|宣教、逃亡或使命旅程抵达某地。||place|590
BORN_IN|location|出生于|born in|人物出生地点。||place|610
LIVED_IN|location|居住于|lived in|人物曾居住或长期停留之地。||place|620
MINISTERED_IN|location|服事于|ministered in|人物主要服事或事奉地点。||place|630
GREW_UP_IN|location|成长于|grew up in|人物成长地点。||place|640
CRUCIFIED_AT|location|钉十字架于|crucified at|耶稣被钉十字架地点。||place|650
TRAVELED_THROUGH|location|经过|traveled through|人物行程经过某地。||place|660
TRAVELED_TO|location|前往|traveled to|人物前往某地。||place|670
IMPRISONED_IN|location|被囚于|imprisoned in|人物被囚地点。||place|680
APPEARS_IN|other|出现于书卷|appears in|人物、事件或主题与圣经书卷相连。||book|710
HAS_THEME|other|神学主题|has theme|人物或事件连接到神学主题。||theme|720
TYPOLOGY_OF_CHRIST|other|预表基督|typology of Christ|旧约人物、职分或事件作为基督预表。||theme|730
HAS_APPLICATION|other|属灵应用|has application|人物故事连接到属灵应用或镜鉴主题。||theme|740
$types$, E'\n')
), parsed AS (
    SELECT string_to_array(line, '|') AS parts
    FROM raw
    WHERE line <> ''
)
INSERT INTO biblical_graph_relationship_types (
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    description,
    inverse_type,
    target_types,
    sort_order
)
SELECT
    parts[1],
    parts[2],
    parts[3],
    parts[4],
    parts[5],
    NULLIF(parts[6], ''),
    string_to_array(parts[7], ','),
    parts[8]::int
FROM parsed
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

WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($nodes$
place|hebron|希伯仑|Hebron|location|大卫早期作王、族长埋葬地等重要地点。
place|en-gedi|隐基底|En Gedi|location|大卫逃避扫罗时期的重要旷野地点。
place|ziklag|洗革拉|Ziklag|location|大卫逃避扫罗时停留的非利士边境城。
place|gerar|基拉耳|Gerar|location|亚伯拉罕、以撒与亚比米勒相关地点。
place|shechem|示剑|Shechem|location|族长、底拿事件、约书亚立约和王国分裂相关地点。
place|jericho|耶利哥|Jericho|location|喇合、约书亚征服和巴底买相关地点。
place|bethany|伯大尼|Bethany|location|马大、马利亚、拉撒路和耶稣受难前事奉相关地点。
place|emmaus|以马忤斯|Emmaus|location|复活主向两个门徒显现的路途目的地。
place|malta|马耳他|Malta|location|保罗赴罗马途中遇船难后停留的岛。
place|colossae|歌罗西|Colossae|location|保罗书信和以巴弗、腓利门相关教会城市。
place|corinth|哥林多|Corinth|location|保罗宣教、哥林多书信和罗马书问安相关城市。
place|cyprus|居比路|Cyprus|location|巴拿巴、保罗第一次宣教旅程和士求保罗相关岛屿。
event|genesis-genealogies|创世记族谱|Genesis Genealogies|genealogy|创世记中的亚当至挪亚、挪亚至亚伯拉罕、族长家族谱系。
event|chronicles-genealogies|历代志族谱|Chronicles Genealogies|genealogy|历代志开篇的以色列家族、支派和职分谱系。
event|twelve-tribe-descendants|十二支派族长后裔|Twelve Tribe Descendants|genealogy|雅各众子及十二支派后裔网络。
event|city-leaders|各城首领名单|City Leaders Lists|list|旧约各城、各族和地方首领名单。
event|priestly-divisions|祭司班次|Priestly Divisions|list|祭司家族、班次和圣殿服事结构。
event|levite-lists|利未人名单|Levite Lists|list|利未人家族、歌唱者、守门者和圣殿服事人员。
event|returnee-lists|归回名单|Returnee Lists|list|以斯拉记、尼希米记中归回者、家族与领袖名单。
event|solomon-officials|所罗门官员名单|Solomon Officials|list|所罗门王国行政、军事和圣殿建设官员网络。
event|nehemiah-wall-builders|尼希米修墙名单|Nehemiah Wall Builders|list|尼希米记中各段城墙修造者和反对者网络。
event|paul-greetings|保罗书信问安人物|Paul Letter Greetings|list|罗马书16章、歌罗西书4章、提后4章等问安人物网络。
event|parable-figures|比喻人物|Parable Figures|symbolic|耶稣比喻中的人物、家庭、群体和属灵应用。
event|symbolic-figures|象征人物|Symbolic Figures|symbolic|但以理书、启示录等象征人物与敌对势力节点。
event|david-kingship|大卫登基|David Kingship|event|大卫在希伯仑和耶路撒冷作王。
event|ark-to-jerusalem|约柜入城|Ark Brought to Jerusalem|event|大卫将约柜运入耶路撒冷。
event|bathsheba-incident|拔示巴事件|Bathsheba Incident|event|大卫、拔示巴、乌利亚和拿单责备相关事件。
event|absalom-rebellion|押沙龙叛乱|Absalom Rebellion|event|押沙龙背叛大卫并引发王室悲剧。
event|jerusalem-wall-rebuild|重建耶路撒冷城墙|Jerusalem Wall Rebuild|event|尼希米带领百姓重建城墙。
group|twelve-apostles|十二使徒|Twelve Apostles|group|耶稣亲自呼召、差遣的十二使徒群体。
group|early-church|初代教会|Early Church|group|使徒行传和书信中的初代教会群体。
group|antioch-church|安提阿教会|Antioch Church|group|差派巴拿巴和保罗宣教的教会。
group|priesthood|祭司体系|Priesthood|group|亚伦后裔、祭司班次和圣殿服事体系。
group|levites|利未人|Levites|group|利未支派与圣殿/会幕服事群体。
group|paul-coworkers|保罗同工圈|Paul Coworkers|group|保罗宣教、书信问安和教会建立相关同工。
nation|united-kingdom|统一王国|United Kingdom of Israel|nation|扫罗、大卫、所罗门时期的统一以色列王国。
nation|northern-israel|北国以色列|Northern Kingdom of Israel|nation|王国分裂后的北国。
nation|southern-judah|南国犹大|Southern Kingdom of Judah|nation|王国分裂后的南国。
book|genesis|创世记|Genesis|book|创世记人物、族谱、族长叙事。
book|chronicles|历代志|Chronicles|book|历代志族谱、君王和祭司利未人名单。
book|samuel|撒母耳记|Samuel|book|撒母耳、扫罗、大卫时期主要书卷。
book|kings|列王纪|Kings|book|所罗门、南北国君王、先知与被掳主要书卷。
book|ezra-nehemiah|以斯拉记-尼希米记|Ezra-Nehemiah|book|归回、重建圣殿、修墙和律法更新。
book|esther|以斯帖记|Esther|book|以斯帖、末底改、哈曼和波斯宫廷事件。
book|matthew|马太福音|Matthew|book|耶稣家谱、门徒、天国教训和受难复活。
book|luke-acts|路加福音-使徒行传|Luke-Acts|book|耶稣生平、初代教会、保罗宣教。
book|john|约翰福音与约翰书信|John and Johannine Letters|book|约翰福音神迹、见证人与约翰书信人物。
book|romans|罗马书|Romans|book|罗马书16章问安人物网络。
book|revelation|启示录|Revelation|book|七教会、象征人物和末世异象。
theme|messianic-line|弥赛亚谱系|Messianic Line|theology|从亚当、亚伯拉罕、大卫到基督的救赎家谱主题。
theme|davidic-covenant|大卫之约|Davidic Covenant|theology|神应许大卫后裔坐王位，最终指向基督。
theme|repentance|悔改|Repentance|application|人物失败、责备、归回和福音更新主题。
theme|worship|敬拜|Worship|application|会幕、圣殿、约柜、诗篇和祭司利未人服事主题。
theme|christ-typology|基督预表|Christ Typology|typology|旧约人物、事件和职分预表基督。
theme|spiritual-application|属灵应用|Spiritual Application|application|人物故事进入今日顺服、警戒和效法的应用层。
$nodes$, E'\n')
), parsed AS (
    SELECT string_to_array(line, '|') AS parts
    FROM raw
    WHERE line <> ''
)
INSERT INTO biblical_graph_nodes (
    id,
    node_type,
    name,
    name_en,
    category,
    description,
    chinese_name,
    english_name,
    aliases,
    testament,
    importance_level,
    summary
)
SELECT
    parts[1] || '-' || parts[2],
    parts[1],
    parts[3],
    parts[4],
    parts[5],
    parts[6],
    parts[3],
    parts[4],
    ARRAY_REMOVE(ARRAY[parts[3], parts[4]], NULL),
    CASE
        WHEN parts[1] = 'book' AND parts[2] IN ('matthew', 'luke-acts', 'john', 'romans', 'revelation') THEN 'New Testament'
        WHEN parts[1] = 'event' AND parts[2] IN ('paul-greetings', 'parable-figures', 'symbolic-figures') THEN 'New Testament'
        ELSE 'Old Testament'
    END,
    CASE WHEN parts[1] IN ('event', 'theme') AND parts[2] IN ('messianic-line', 'christ-typology') THEN 'A' ELSE 'C' END,
    parts[6]
FROM parsed
ON CONFLICT (id) DO UPDATE SET
    node_type = EXCLUDED.node_type,
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    chinese_name = EXCLUDED.chinese_name,
    english_name = EXCLUDED.english_name,
    aliases = EXCLUDED.aliases,
    testament = EXCLUDED.testament,
    importance_level = EXCLUDED.importance_level,
    summary = EXCLUDED.summary,
    is_active = true;

WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($edges$
character|亚当|character|塞特|FATHER_OF|family|父亲|创5:3|亚当生塞特，弥赛亚谱系由此延续。|3.2
character|塞特|character|以挪士|FATHER_OF|family|父亲|创5:6|塞特生以挪士。|2.6
character|以挪士|character|该南|FATHER_OF|family|父亲|创5:9|以挪士生该南。|2.4
character|该南|character|玛勒列|FATHER_OF|family|父亲|创5:12|该南生玛勒列。|2.4
character|玛勒列|character|雅列|FATHER_OF|family|父亲|创5:15|玛勒列生雅列。|2.4
character|雅列|character|以诺|FATHER_OF|family|父亲|创5:18|雅列生以诺。|2.6
character|以诺|character|玛土撒拉|FATHER_OF|family|父亲|创5:21|以诺生玛土撒拉。|2.4
character|玛土撒拉|character|拉麦|FATHER_OF|family|父亲|创5:25|玛土撒拉生拉麦。|2.4
character|拉麦|character|挪亚|FATHER_OF|family|父亲|创5:28-29|拉麦是挪亚之父。|2.8
character|挪亚|character|闪|FATHER_OF|family|父亲|创5:32,10:1|闪是挪亚之子。|3.0
character|挪亚|character|含|FATHER_OF|family|父亲|创5:32,10:1|含是挪亚之子。|2.8
character|挪亚|character|雅弗|FATHER_OF|family|父亲|创5:32,10:1|雅弗是挪亚之子。|2.8
character|含|character|迦南|FATHER_OF|family|父亲|创10:6|迦南是含的儿子。|2.5
character|他拉|character|亚伯拉罕|FATHER_OF|family|父亲|创11:26|他拉生亚伯兰。|3.0
character|他拉|character|拿鹤|FATHER_OF|family|父亲|创11:26|拿鹤是他拉之子。|2.4
character|他拉|character|哈兰|FATHER_OF|family|父亲|创11:26|哈兰是他拉之子。|2.4
character|哈兰|character|罗得|FATHER_OF|family|父亲|创11:27|罗得是哈兰之子。|2.6
character|亚伯拉罕|character|撒拉|SPOUSE_OF|family|夫妻|创11:29|亚伯拉罕与撒拉为夫妻。|3.0
character|亚伯拉罕|character|夏甲|SPOUSE_OF|family|妾/配偶|创16|夏甲为亚伯拉罕妾，生以实玛利。|2.4
character|亚伯拉罕|character|基土拉|SPOUSE_OF|family|妻子|创25:1|基土拉是亚伯拉罕后妻。|2.2
character|亚伯拉罕|character|以撒|FATHER_OF|family|父亲|创21:3|亚伯拉罕是以撒之父。|3.8
character|撒拉|character|以撒|MOTHER_OF|family|母亲|创21:3|撒拉生以撒。|3.3
character|亚伯拉罕|character|以实玛利|FATHER_OF|family|父亲|创16:15|亚伯拉罕从夏甲生以实玛利。|3.0
character|夏甲|character|以实玛利|MOTHER_OF|family|母亲|创16:15|夏甲是以实玛利之母。|2.8
character|亚伯拉罕|character|米甸|FATHER_OF|family|父亲|创25:2|米甸是亚伯拉罕与基土拉所生。|2.3
character|以撒|character|利百加|SPOUSE_OF|family|夫妻|创24|以撒娶利百加为妻。|3.0
character|以撒|character|雅各|FATHER_OF|family|父亲|创25:26|以撒是雅各之父。|3.5
character|利百加|character|雅各|MOTHER_OF|family|母亲|创25:26|利百加生雅各。|3.0
character|以撒|character|以扫|FATHER_OF|family|父亲|创25:25-26|以扫是以撒之子。|2.8
character|利百加|character|以扫|MOTHER_OF|family|母亲|创25:25-26|利百加生以扫。|2.6
character|雅各|character|利亚|SPOUSE_OF|family|夫妻|创29|雅各与利亚为夫妻。|2.8
character|雅各|character|拉结|SPOUSE_OF|family|夫妻|创29|雅各与拉结为夫妻。|2.8
character|雅各|character|辟拉|SPOUSE_OF|family|妾/使女|创30|辟拉为拉结使女，给雅各生子。|2.0
character|雅各|character|悉帕|SPOUSE_OF|family|妾/使女|创30|悉帕为利亚使女，给雅各生子。|2.0
character|雅各|character|流便（雅各长子）|FATHER_OF|family|父亲|创29:32|流便是雅各长子。|2.8
character|雅各|character|西缅（雅各之子）|FATHER_OF|family|父亲|创29:33|西缅是雅各之子。|2.8
character|雅各|character|利未（雅各之子）|FATHER_OF|family|父亲|创29:34|利未是雅各之子。|2.8
character|雅各|character|犹大（雅各之子）|FATHER_OF|family|父亲|创29:35|犹大是雅各之子。|3.2
character|雅各|character|约瑟|FATHER_OF|family|父亲|创30:24|约瑟是雅各之子。|3.2
character|雅各|character|便雅悯（雅各之子）|FATHER_OF|family|父亲|创35:18|便雅悯是雅各之子。|2.8
character|拉结|character|约瑟|MOTHER_OF|family|母亲|创30:24|拉结生约瑟。|2.8
character|拉结|character|便雅悯（雅各之子）|MOTHER_OF|family|母亲|创35:18|拉结生便雅悯。|2.6
character|犹大（雅各之子）|character|法勒斯|FATHER_OF|family|父亲|创38:29|犹大与他玛生法勒斯。|3.0
character|他玛|character|法勒斯|MOTHER_OF|family|母亲|创38:29|他玛生法勒斯。|2.8
character|犹大（雅各之子）|character|大卫|ANCESTOR_OF|family|祖先|得4,太1|大卫出自犹大谱系。|3.2
character|大卫|character|耶稣基督|ANCESTOR_OF|family|祖先|太1,路3|耶稣按肉身是大卫后裔。|3.8
character|耶西|character|大卫|FATHER_OF|family|父亲|撒上16|耶西是大卫之父。|3.2
character|大卫|character|暗嫩|FATHER_OF|family|父亲|撒下3:2|暗嫩是大卫长子。|2.6
character|大卫|character|基利押|FATHER_OF|family|父亲|撒下3:3|基利押是大卫与亚比该之子。|2.2
character|大卫|character|押沙龙|FATHER_OF|family|父亲|撒下3:3|押沙龙是大卫之子。|3.0
character|大卫|character|所罗门|FATHER_OF|family|父亲|撒下12:24|所罗门是大卫与拔示巴之子。|3.2
character|大卫|character|亚多尼雅|FATHER_OF|family|父亲|王上1|亚多尼雅是大卫之子。|2.6
character|大卫|character|他玛，大卫女儿|FATHER_OF|family|父亲|撒下13|他玛是大卫女儿。|2.5
character|暗嫩|character|押沙龙|SIBLING_OF|family|兄弟|撒下13|暗嫩与押沙龙同为大卫之子。|2.2
character|押沙龙|character|他玛，大卫女儿|SIBLING_OF|family|兄妹|撒下13|押沙龙是他玛的哥哥。|2.6
character|马利亚|character|耶稣基督|MOTHER_OF|family|母亲|路1-2|马利亚生耶稣。|3.8
character|约瑟（耶稣父亲）|character|马利亚|SPOUSE_OF|family|夫妻|太1|约瑟与马利亚为夫妻。|3.0
character|撒迦利亚（约翰父亲）|character|施洗约翰|FATHER_OF|family|父亲|路1|撒迦利亚是施洗约翰之父。|3.0
character|以利沙伯|character|施洗约翰|MOTHER_OF|family|母亲|路1|以利沙伯生施洗约翰。|3.0
character|西庇太|character|西庇太的雅各|FATHER_OF|family|父亲|太4:21|西庇太是雅各之父。|2.6
character|西庇太|character|约翰|FATHER_OF|family|父亲|太4:21|西庇太是约翰之父。|2.6
character|摩西|character|亚伦|SIBLING_OF|family|兄弟|出6:20|摩西与亚伦为兄弟。|3.0
character|摩西|character|米利暗|SIBLING_OF|family|姐弟|出15,民12|米利暗是摩西和亚伦的姊妹。|2.8
character|暗兰|character|摩西|FATHER_OF|family|父亲|出6:20|暗兰是摩西之父。|2.8
character|暗兰|character|亚伦|FATHER_OF|family|父亲|出6:20|暗兰是亚伦之父。|2.8
character|暗兰|character|米利暗|FATHER_OF|family|父亲|出6:20,民26:59|暗兰是米利暗之父。|2.4
character|亚伦|character|拿答（亚伦之子）|FATHER_OF|family|父亲|出6:23|拿答是亚伦之子。|2.6
character|亚伦|character|亚比户|FATHER_OF|family|父亲|出6:23|亚比户是亚伦之子。|2.6
character|亚伦|character|以利亚撒|FATHER_OF|family|父亲|出6:23|以利亚撒是亚伦之子。|2.6
character|亚伦|character|以他玛|FATHER_OF|family|父亲|出6:23|以他玛是亚伦之子。|2.6
character|摩西|character|革舜|FATHER_OF|family|父亲|出2:22|革舜是摩西之子。|2.2
character|撒母耳|character|扫罗|ANOINTED|spiritual|膏立|撒上10|撒母耳膏立扫罗。|3.2
character|撒母耳|character|大卫|ANOINTED|spiritual|膏立|撒上16|撒母耳膏立大卫。|3.5
character|扫罗|character|撒母耳|ANOINTED_BY|spiritual|受膏于|撒上10|扫罗受撒母耳膏立。|2.4
character|大卫|character|撒母耳|ANOINTED_BY|spiritual|受膏于|撒上16|大卫受撒母耳膏立。|2.6
character|以利亚|character|以利沙|MENTOR_OF|spiritual|栽培|王上19,王下2|以利亚呼召并栽培以利沙。|3.5
character|摩西|character|约书亚|MENTOR_OF|spiritual|栽培继承者|民27,申31|摩西栽培约书亚承接带领。|3.5
character|保罗|character|提摩太|MENTOR_OF|spiritual|属灵父亲|提前,提后|保罗栽培提摩太。|3.5
character|保罗|character|提多|MENTOR_OF|spiritual|属灵父亲|多1|保罗差遣提多整顿教会。|3.0
character|彼得|character|百夫长哥尼流|PREACHED_TO|spiritual|传道给|徒10|彼得向哥尼流家传福音。|3.2
character|腓力|character|埃提阿伯太监|PREACHED_TO|spiritual|传道给|徒8|腓利向埃提阿伯太监讲解福音。|3.2
character|耶稣基督|character|彼得|CALLED|spiritual|呼召|太4|耶稣呼召彼得跟随。|3.5
character|耶稣基督|character|约翰|CALLED|spiritual|呼召|太4|耶稣呼召约翰跟随。|3.2
character|耶稣基督|character|西庇太的雅各|CALLED|spiritual|呼召|太4|耶稣呼召西庇太的雅各跟随。|3.2
character|耶稣基督|character|马太|CALLED|spiritual|呼召|太9|耶稣呼召税吏马太。|3.2
character|彼得|character|耶稣基督|DISCIPLE_OF|spiritual|门徒|太4|彼得是耶稣门徒。|3.0
character|约翰|character|耶稣基督|DISCIPLE_OF|spiritual|门徒|太4|约翰是耶稣门徒。|3.0
character|马太|character|耶稣基督|DISCIPLE_OF|spiritual|门徒|太9|马太是耶稣门徒。|3.0
character|保罗|group|paul-coworkers|APOSTLE_OF|spiritual|使徒|罗1,林前1|保罗作为使徒服事外邦教会并带领同工网络。|3.0
character|彼得|group|early-church|APOSTLE_OF|spiritual|使徒|徒1-12|彼得在初代教会中作使徒见证。|3.0
character|约翰|group|early-church|APOSTLE_OF|spiritual|使徒|徒3,约壹|约翰在初代教会中作使徒见证。|2.8
character|巴拿巴|group|antioch-church|SENT_BY|spiritual|差遣|徒13|巴拿巴由安提阿教会差派宣教。|2.8
character|保罗|group|antioch-church|SENT_BY|spiritual|差遣|徒13|保罗由安提阿教会差派宣教。|2.8
character|大卫|character|歌利亚|DEFEATED|political|击败|撒上17|大卫击败歌利亚。|3.5
character|扫罗|character|大卫|ATTACKED|political|攻打/追杀|撒上18-31|扫罗追杀大卫。|3.0
character|押沙龙|character|大卫|REBELLED_AGAINST|political|背叛|撒下15-18|押沙龙背叛大卫。|3.0
character|尼布甲尼撒|place|jerusalem|CONQUERED|political|攻陷|王下24-25|尼布甲尼撒攻陷耶路撒冷。|3.5
nation|babylon-empire|group|judah-exiles|EXILED|political|掳掠|王下24-25|巴比伦掳走犹大人。|3.5
group|judah-exiles|place|babylon|EXILED_TO|political|被掳到|王下24-25|犹大被掳者被掳到巴比伦。|3.2
character|古列|group|jews-returnees|ALLOWED_RETURN|political|准许归回|拉1|古列下诏准许犹太人归回。|3.5
group|jews-returnees|character|古列|RELEASED_BY|political|被释放/准许归回|拉1|归回犹太人因古列诏令得以返回。|2.6
character|罗波安|character|耶罗波安|OPPOSED|political|对立|王上12|罗波安与耶罗波安导致王国分裂对立。|3.0
character|所罗门|nation|united-kingdom|RULED_OVER|political|统治|王上1-11|所罗门统治统一王国。|3.0
character|耶罗波安|nation|northern-israel|RULED_OVER|political|统治|王上12|耶罗波安作北国以色列王。|2.8
character|罗波安|nation|southern-judah|RULED_OVER|political|统治|王上12|罗波安作南国犹大王。|2.8
character|摩西|event|exodus|LED|event|带领事件|出1-14|摩西带领以色列出埃及。|3.8
character|亚伦|event|exodus|PARTICIPATED_IN|event|参与事件|出4-14|亚伦与摩西同工出埃及。|3.0
character|法老|event|exodus|OPPOSED|event|反对事件|出5-14|法老抵挡出埃及。|3.0
character|约书亚|event|conquest-canaan|LED|event|带领事件|书1-12|约书亚带领征服迦南。|3.5
character|喇合|event|conquest-canaan|PARTICIPATED_IN|event|参与事件|书2,6|喇合保护探子并在耶利哥得救。|2.8
character|亚干|event|conquest-canaan|CAUSED|event|造成事件|书7|亚干犯罪导致艾城失败。|2.6
character|大卫|event|david-goliath|PARTICIPATED_IN|event|参与事件|撒上17|大卫参与击败歌利亚事件。|3.0
character|歌利亚|event|david-goliath|DIED_IN|event|死于事件|撒上17|歌利亚死于大卫击败他的事件。|2.8
character|押沙龙|event|absalom-rebellion|INITIATED|event|发起事件|撒下15|押沙龙发起叛乱。|2.8
character|大卫|event|absalom-rebellion|PARTICIPATED_IN|event|参与事件|撒下15-18|大卫经历押沙龙叛乱。|2.7
character|拿单先知|event|bathsheba-incident|WITNESSED|event|见证/责备|撒下12|拿单奉神话语责备大卫。|2.8
character|大卫|event|bathsheba-incident|CAUSED|event|造成事件|撒下11|大卫犯罪造成拔示巴与乌利亚事件。|2.6
character|乌利亚|event|bathsheba-incident|DIED_IN|event|死于事件|撒下11|乌利亚死于拔示巴事件的罪恶链条。|2.5
character|彼得|event|pentecost|PREACHED_AT|event|讲道于|徒2|彼得在五旬节讲道。|3.0
character|保罗|event|paul-missionary-journeys|PARTICIPATED_IN|event|参与事件|徒13-28|保罗参与多次宣教旅程。|3.2
character|保罗|event|paul-rome-imprisonment|PARTICIPATED_IN|event|参与事件|徒28|保罗在罗马被囚并传道。|2.8
character|保罗|place|rome|IMPRISONED_IN|location|被囚于|徒28|保罗在罗马被囚。|3.0
character|耶稣基督|place|bethlehem|BORN_IN|location|出生于|路2|耶稣降生于伯利恒。|3.5
character|耶稣基督|place|nazareth|GREW_UP_IN|location|成长于|太2:23,路2:51|耶稣在拿撒勒成长。|3.2
character|耶稣基督|place|golgotha|CRUCIFIED_AT|location|钉十字架于|约19|耶稣在各各他被钉十字架。|3.5
character|大卫|place|bethlehem|BORN_IN|location|出生于/出身|撒上16|大卫出自伯利恒。|2.8
character|大卫|place|hebron|LIVED_IN|location|居住/作王于|撒下2|大卫在希伯仑作王七年半。|2.5
character|大卫|place|jerusalem|RULED_OVER|political|统治|撒下5|大卫在耶路撒冷作王。|3.0
character|大卫|place|en-gedi|TRAVELED_THROUGH|location|经过/逃避|撒上24|大卫逃避扫罗时在隐基底。|2.2
character|大卫|place|ziklag|LIVED_IN|location|居住于|撒上27|大卫逃避扫罗时住在洗革拉。|2.2
character|亚伯拉罕|place|gerar|TRAVELED_TO|location|前往|创20|亚伯拉罕曾寄居基拉耳。|2.0
character|保罗|place|antioch|MINISTERED_IN|location|服事于|徒13|保罗从安提阿被差派并服事。|2.8
character|保罗|place|ephesus|MINISTERED_IN|location|服事于|徒19|保罗在以弗所长期服事。|2.8
character|保罗|place|philippi|MINISTERED_IN|location|服事于|徒16|保罗在腓立比传福音并建立教会。|2.6
character|保罗|place|rome|JOURNEYED_TO|event|行程到达|徒28|保罗最终被押送到罗马。|2.6
character|尼希米|event|jerusalem-wall-rebuild|LED|event|带领事件|尼1-6|尼希米带领重建耶路撒冷城墙。|3.2
character|参巴拉|event|jerusalem-wall-rebuild|OPPOSED|event|反对事件|尼4|参巴拉反对尼希米修墙。|2.6
character|多比雅|event|jerusalem-wall-rebuild|OPPOSED|event|反对事件|尼4|多比雅反对尼希米修墙。|2.6
character|鲁孚|event|paul-greetings|PARTICIPATED_IN|event|问安人物|罗16|鲁孚出现在保罗罗马书问安网络中。|1.8
character|腓比|event|paul-greetings|PARTICIPATED_IN|event|问安人物|罗16|腓比与罗马书问安和递送书信传统相关。|2.4
character|亚居拉|event|paul-greetings|PARTICIPATED_IN|event|问安人物|罗16|亚居拉是保罗问安的重要同工。|2.2
character|百基拉|event|paul-greetings|PARTICIPATED_IN|event|问安人物|罗16|百基拉是保罗问安的重要同工。|2.2
character|浪子|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路15|浪子属于耶稣比喻人物网络。|2.0
character|浪子的父亲|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路15|浪子的父亲呈现怜悯父爱的比喻主题。|2.0
character|龙|event|symbolic-figures|PARTICIPATED_IN|event|象征人物|启12|龙属于启示录象征敌对节点。|2.0
character|兽|event|symbolic-figures|PARTICIPATED_IN|event|象征人物|启13|兽属于启示录象征敌对节点。|2.0
character|亚当|book|genesis|APPEARS_IN|other|出现于书卷|创1-5|亚当主要出现于创世记。|1.2
character|亚伯拉罕|book|genesis|APPEARS_IN|other|出现于书卷|创11-25|亚伯拉罕主要出现于创世记。|1.2
character|大卫|book|samuel|APPEARS_IN|other|出现于书卷|撒上16-撒下24|大卫主要叙事集中在撒母耳记。|1.2
character|大卫|book|chronicles|APPEARS_IN|other|出现于书卷|代上|大卫也在历代志中被重述。|1.0
character|耶稣基督|book|matthew|APPEARS_IN|other|出现于书卷|太1-28|耶稣基督是福音书中心。|1.2
character|保罗|book|luke-acts|APPEARS_IN|other|出现于书卷|徒9-28|保罗主要叙事集中在使徒行传后半。|1.2
character|保罗|book|romans|APPEARS_IN|other|出现于书卷|罗1,16|保罗与罗马书及问安人物网络相关。|1.0
character|约翰（启示录）|book|revelation|APPEARS_IN|other|出现于书卷|启1|约翰领受并写下启示录异象。|1.0
character|大卫|theme|davidic-covenant|HAS_THEME|other|神学主题|撒下7|大卫节点连接君约主题。|2.8
character|大卫|theme|repentance|HAS_THEME|other|神学主题|诗51|大卫节点连接悔改主题。|2.4
character|大卫|theme|worship|HAS_THEME|other|神学主题|诗篇,撒下6|大卫节点连接敬拜主题。|2.4
character|大卫|theme|messianic-line|HAS_THEME|other|神学主题|太1|大卫节点连接弥赛亚谱系主题。|3.0
character|大卫|theme|christ-typology|TYPOLOGY_OF_CHRIST|other|基督预表|撒上16,撒下7|大卫作为受膏君王、牧者君王和受苦后得荣耀的基督预表。|3.0
character|麦基洗德|theme|christ-typology|TYPOLOGY_OF_CHRIST|other|基督预表|创14,来7|麦基洗德的君王祭司身份预表基督。|3.0
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
    WHERE line <> ''
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
    0.95,
    relationship_type NOT IN ('SPOUSE_OF', 'SIBLING_OF', 'ALLIED_WITH'),
    20000 + ord,
    ARRAY_REMOVE(ARRAY[scripture_ref], NULL),
    'high'
FROM resolved
WHERE source_node_id IS NOT NULL
  AND target_node_id IS NOT NULL
  AND source_node_id <> target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = target_node_id)
ON CONFLICT DO NOTHING;

WITH parent_edges AS (
    SELECT *
    FROM biblical_graph_edges
    WHERE is_active = true
      AND relationship_type IN ('FATHER_OF', 'MOTHER_OF')
), inverse_rows AS (
    SELECT
        target_node_id AS source_node_id,
        source_node_id AS target_node_id,
        'CHILD_OF' AS relationship_type,
        'family' AS relationship_category,
        '儿子/女儿' AS label_zh,
        'child of' AS label_en,
        scripture_ref,
        '由父母关系自动生成的子女反向关系：' || description AS description,
        GREATEST(weight - 0.2, 0.1) AS weight,
        confidence,
        true AS is_directed,
        sort_order + 1 AS sort_order,
        scripture_refs,
        confidence_level
    FROM parent_edges
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
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
FROM inverse_rows
WHERE source_node_id <> target_node_id
ON CONFLICT DO NOTHING;

WITH lineage_edges AS (
    SELECT *
    FROM biblical_graph_edges
    WHERE is_active = true
      AND relationship_type = 'ANCESTOR_OF'
), inverse_rows AS (
    SELECT
        target_node_id AS source_node_id,
        source_node_id AS target_node_id,
        'DESCENDANT_OF' AS relationship_type,
        'family' AS relationship_category,
        '后裔' AS label_zh,
        'descendant of' AS label_en,
        scripture_ref,
        '由祖先关系自动生成的后裔反向关系：' || description AS description,
        GREATEST(weight - 0.2, 0.1) AS weight,
        confidence,
        true AS is_directed,
        sort_order + 1 AS sort_order,
        scripture_refs,
        confidence_level
    FROM lineage_edges
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
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
FROM inverse_rows
WHERE source_node_id <> target_node_id
ON CONFLICT DO NOTHING;

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
    n.id,
    CASE
        WHEN c.role = '先知' THEN 'group-israelites'
        WHEN c.role = '祭司' THEN 'group-priesthood'
        WHEN c.role = '士师' THEN 'group-israelites'
        WHEN c.role = '使徒' THEN 'group-early-church'
        WHEN c.role = '君王' AND c.kingdom = '北国以色列' THEN 'nation-northern-israel'
        WHEN c.role = '君王' AND c.kingdom = '南国犹大' THEN 'nation-southern-judah'
        WHEN c.role = '君王' THEN 'nation-united-kingdom'
        ELSE NULL
    END,
    CASE
        WHEN c.role = '先知' THEN 'PROPHET_OF'
        WHEN c.role = '祭司' THEN 'PRIEST_OF'
        WHEN c.role = '士师' THEN 'JUDGE_OF'
        WHEN c.role = '使徒' THEN 'APOSTLE_OF'
        WHEN c.role = '君王' THEN 'KING_OF'
        ELSE NULL
    END,
    CASE WHEN c.role = '君王' THEN 'political' ELSE 'spiritual' END,
    c.role,
    CASE
        WHEN c.role = '先知' THEN 'prophet of'
        WHEN c.role = '祭司' THEN 'priest of'
        WHEN c.role = '士师' THEN 'judge of'
        WHEN c.role = '使徒' THEN 'apostle of'
        WHEN c.role = '君王' THEN 'king of'
    END,
    c.scripture_ref,
    c.name || '的人物卡角色为“' || c.role || '”，因此接入对应职分关系。',
    1.2,
    0.8,
    true,
    30000 + c.id,
    ARRAY_REMOVE(ARRAY[c.scripture_ref], NULL),
    'medium'
FROM biblical_characters c
JOIN biblical_graph_nodes n ON n.character_id = c.id
WHERE c.is_active = true
  AND c.role IN ('先知', '祭司', '士师', '使徒', '君王')
  AND EXISTS (
      SELECT 1
      FROM biblical_graph_nodes target
      WHERE target.id = CASE
          WHEN c.role = '先知' THEN 'group-israelites'
          WHEN c.role = '祭司' THEN 'group-priesthood'
          WHEN c.role = '士师' THEN 'group-israelites'
          WHEN c.role = '使徒' THEN 'group-early-church'
          WHEN c.role = '君王' AND c.kingdom = '北国以色列' THEN 'nation-northern-israel'
          WHEN c.role = '君王' AND c.kingdom = '南国犹大' THEN 'nation-southern-judah'
          WHEN c.role = '君王' THEN 'nation-united-kingdom'
      END
  )
ON CONFLICT DO NOTHING;

UPDATE biblical_graph_subgraphs
SET relationship_categories = ARRAY_REMOVE(ARRAY(
        SELECT DISTINCT unnest(relationship_categories)
        EXCEPT SELECT 'conflict'
    ), NULL)
WHERE 'conflict' = ANY(relationship_categories);

UPDATE biblical_graph_subgraphs
SET
    focus_nodes = ARRAY[
        '亚当', '塞特', '以挪士', '该南', '玛勒列', '雅列', '以诺', '玛土撒拉',
        '拉麦', '挪亚', '闪', '亚伯拉罕', '以撒', '雅各', '犹大（雅各之子）',
        '法勒斯', '大卫', '耶稣基督', '创世记族谱', '历代志族谱'
    ],
    node_types = ARRAY['character', 'event', 'book', 'theme'],
    relationship_categories = ARRAY['family', 'other'],
    relationship_types = ARRAY['FATHER_OF', 'MOTHER_OF', 'CHILD_OF', 'ANCESTOR_OF', 'DESCENDANT_OF', 'APPEARS_IN', 'HAS_THEME'],
    depth = 3
WHERE slug = 'adam-to-jesus-genealogy';

UPDATE biblical_graph_subgraphs
SET
    focus_nodes = ARRAY['亚伯拉罕', '撒拉', '夏甲', '以实玛利', '以撒', '基土拉', '米甸', '罗得', '麦基洗德', '基拉耳', '创世记'],
    node_types = ARRAY['character', 'place', 'event', 'book', 'theme'],
    relationship_categories = ARRAY['family', 'spiritual', 'event', 'location', 'other'],
    relationship_types = ARRAY['FATHER_OF', 'MOTHER_OF', 'SPOUSE_OF', 'CHILD_OF', 'ANCESTOR_OF', 'TRAVELED_TO', 'APPEARS_IN', 'TYPOLOGY_OF_CHRIST'],
    depth = 3
WHERE slug = 'abraham-family';

UPDATE biblical_graph_subgraphs
SET
    focus_nodes = ARRAY['雅各', '利亚', '拉结', '辟拉', '悉帕', '流便（雅各长子）', '西缅（雅各之子）', '利未（雅各之子）', '犹大（雅各之子）', '约瑟', '便雅悯（雅各之子）', '十二支派族长后裔'],
    node_types = ARRAY['character', 'event', 'book'],
    relationship_categories = ARRAY['family', 'other'],
    relationship_types = ARRAY['FATHER_OF', 'MOTHER_OF', 'SPOUSE_OF', 'SIBLING_OF', 'CHILD_OF', 'ANCESTOR_OF', 'DESCENDANT_OF', 'APPEARS_IN'],
    depth = 3
WHERE slug = 'jacob-twelve-tribes';

UPDATE biblical_graph_subgraphs
SET
    focus_nodes = ARRAY['大卫', '耶西', '扫罗', '约拿单', '歌利亚', '拔示巴', '乌利亚', '暗嫩', '他玛，大卫女儿', '押沙龙', '所罗门', '亚多尼雅', '拿单先知', '伯利恒', '希伯仑', '耶路撒冷', '隐基底', '洗革拉', '拔示巴事件', '押沙龙叛乱', '大卫之约', '基督预表'],
    node_types = ARRAY['character', 'event', 'place', 'book', 'theme'],
    relationship_categories = ARRAY['family', 'spiritual', 'political', 'event', 'location', 'other'],
    relationship_types = ARRAY['FATHER_OF', 'SIBLING_OF', 'SPOUSE_OF', 'ANOINTED', 'ANOINTED_BY', 'ATTACKED', 'DEFEATED', 'REBELLED_AGAINST', 'PARTICIPATED_IN', 'CAUSED', 'DIED_IN', 'BORN_IN', 'LIVED_IN', 'RULED_OVER', 'HAS_THEME', 'TYPOLOGY_OF_CHRIST', 'APPEARS_IN'],
    depth = 3
WHERE slug = 'david-family-tragedy';

UPDATE biblical_graph_subgraphs
SET
    focus_nodes = ARRAY['保罗', '巴拿巴', '西拉', '提摩太', '提多', '路加', '亚居拉', '百基拉', '腓比', '鲁孚', '安提阿', '以弗所', '腓立比', '罗马', '保罗宣教旅程', '保罗书信问安人物', '罗马书'],
    node_types = ARRAY['character', 'event', 'place', 'group', 'book'],
    relationship_categories = ARRAY['spiritual', 'event', 'location', 'other'],
    relationship_types = ARRAY['MENTOR_OF', 'SENT_BY', 'APOSTLE_OF', 'PREACHED_TO', 'PARTICIPATED_IN', 'PREACHED_AT', 'JOURNEYED_TO', 'MINISTERED_IN', 'IMPRISONED_IN', 'APPEARS_IN'],
    depth = 3
WHERE slug = 'paul-mission-network';

DROP VIEW IF EXISTS v_biblical_knowledge_graph_edges CASCADE;
CREATE VIEW v_biblical_knowledge_graph_edges AS
SELECT
    e.id,
    e.source_node_id AS source,
    source.name AS source_name,
    source.node_type AS source_type,
    e.target_node_id AS target,
    target.name AS target_name,
    target.node_type AS target_type,
    e.relationship_type,
    e.relationship_category,
    e.label_zh,
    e.label_en,
    e.scripture_ref,
    e.scripture_refs,
    e.confidence_level,
    e.description,
    e.weight,
    e.confidence,
    e.is_directed
FROM biblical_graph_edges e
JOIN biblical_graph_nodes source ON source.id = e.source_node_id
JOIN biblical_graph_nodes target ON target.id = e.target_node_id
WHERE e.is_active = true
  AND source.is_active = true
  AND target.is_active = true;

DROP VIEW IF EXISTS v_biblical_knowledge_graph_nodes CASCADE;
CREATE VIEW v_biblical_knowledge_graph_nodes AS
SELECT
    n.*,
    COALESCE(deg.degree, 0) AS degree,
    COALESCE(deg.out_degree, 0) AS out_degree,
    COALESCE(deg.in_degree, 0) AS in_degree
FROM biblical_graph_nodes n
LEFT JOIN (
    SELECT
         node_id,
         COUNT(*) AS degree,
         COUNT(*) FILTER (WHERE direction = 'out') AS out_degree,
         COUNT(*) FILTER (WHERE direction = 'in') AS in_degree
    FROM (
         SELECT source_node_id AS node_id, 'out' AS direction FROM biblical_graph_edges WHERE is_active = true
         UNION ALL
         SELECT target_node_id AS node_id, 'in' AS direction FROM biblical_graph_edges WHERE is_active = true
    ) rels
    GROUP BY node_id
) deg ON deg.node_id = n.id
WHERE n.is_active = true;
