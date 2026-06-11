-- Canonical multi-entity knowledge graph for biblical characters, events, places, nations, and groups.
-- Keeps biblical_character_relationships for existing character-only API while adding typed graph edges.

CREATE TABLE IF NOT EXISTS biblical_graph_nodes (
    id TEXT PRIMARY KEY,
    node_type VARCHAR(30) NOT NULL CHECK (node_type IN ('character', 'event', 'place', 'nation', 'group', 'theme')),
    name VARCHAR(120) NOT NULL,
    name_en VARCHAR(120),
    category VARCHAR(50),
    description TEXT,
    character_id INTEGER REFERENCES biblical_characters(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS biblical_graph_edges (
    id SERIAL PRIMARY KEY,
    source_node_id TEXT NOT NULL REFERENCES biblical_graph_nodes(id) ON DELETE CASCADE,
    target_node_id TEXT NOT NULL REFERENCES biblical_graph_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(60) NOT NULL,
    relationship_category VARCHAR(30) NOT NULL CHECK (relationship_category IN ('family', 'spiritual', 'political', 'event', 'location', 'other')),
    label_zh VARCHAR(100) NOT NULL,
    label_en VARCHAR(100),
    scripture_ref VARCHAR(200),
    description TEXT,
    weight NUMERIC(4,2) NOT NULL DEFAULT 1.0 CHECK (weight >= 0 AND weight <= 10),
    confidence NUMERIC(4,2) NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    is_directed BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (source_node_id <> target_node_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_biblical_graph_edges_unique
    ON biblical_graph_edges(source_node_id, target_node_id, relationship_type, COALESCE(scripture_ref, ''));
CREATE INDEX IF NOT EXISTS idx_biblical_graph_nodes_type ON biblical_graph_nodes(node_type) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_biblical_graph_edges_source ON biblical_graph_edges(source_node_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_biblical_graph_edges_target ON biblical_graph_edges(target_node_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_biblical_graph_edges_type ON biblical_graph_edges(relationship_type) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_biblical_graph_edges_category ON biblical_graph_edges(relationship_category) WHERE is_active = true;

DROP TRIGGER IF EXISTS update_biblical_graph_nodes_updated_at ON biblical_graph_nodes;
CREATE TRIGGER update_biblical_graph_nodes_updated_at
    BEFORE UPDATE ON biblical_graph_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_biblical_graph_edges_updated_at ON biblical_graph_edges;
CREATE TRIGGER update_biblical_graph_edges_updated_at
    BEFORE UPDATE ON biblical_graph_edges
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

INSERT INTO biblical_graph_nodes (id, node_type, name, name_en, category, description, character_id)
SELECT 'char-' || c.id, 'character', c.name, c.name_en, c.role, c.summary, c.id
FROM biblical_characters c
WHERE c.is_active = true
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    character_id = EXCLUDED.character_id,
    is_active = true;

WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($nodes$
place|bethlehem|伯利恒|Bethlehem|location|耶稣降生地，大卫城。
place|nazareth|拿撒勒|Nazareth|location|耶稣成长地。
place|golgotha|各各他|Golgotha|location|耶稣被钉十字架之处。
place|jerusalem|耶路撒冷|Jerusalem|location|圣殿、受难、复活和五旬节相关核心地点。
place|egypt|埃及|Egypt|location|以色列被奴役、出埃及、耶稣幼年避难地。
place|canaan|迦南|Canaan|location|应许之地，约书亚征服对象。
place|babylon|巴比伦|Babylon|location|被掳之地，尼布甲尼撒帝国中心。
place|persia|波斯|Persia|location|古列、亚达薛西等波斯王相关帝国。
place|antioch|安提阿|Antioch|location|保罗宣教差派基地。
place|rome|罗马|Rome|location|保罗被囚和书信相关地。
place|damascus|大马士革|Damascus|location|保罗悔改路上的关键地点。
place|nineveh|尼尼微|Nineveh|location|约拿、那鸿信息共同指向之城。
place|mount-sinai|西奈山|Mount Sinai|location|摩西领受律法之地。
place|jordan|约旦河|Jordan River|location|过约旦、施洗相关地点。
place|galilee|加利利|Galilee|location|耶稣传道和门徒呼召重要区域。
place|ephesus|以弗所|Ephesus|location|保罗宣教、以弗所事件和启示录七教会之一。
place|philippi|腓立比|Philippi|location|吕底亚、狱卒、友阿爹循都基相关教会。
event|creation-fall|创造与堕落|Creation and Fall|event|亚当、夏娃、该隐、亚伯相关早期叙事。
event|flood|洪水|Flood|event|挪亚和其儿子相关审判与拯救事件。
event|tower-of-babel|巴别塔|Tower of Babel|event|宁录和巴别传统相关事件。
event|abraham-call|亚伯拉罕蒙召|Call of Abraham|event|亚伯拉罕离开本地、本族、父家。
event|isaac-sacrifice|献以撒|Binding of Isaac|event|亚伯拉罕、以撒信心试炼。
event|exodus|出埃及|Exodus|event|摩西带领以色列脱离埃及。
event|sinai-covenant|西奈立约|Sinai Covenant|event|摩西、亚伦和以色列在西奈山立约。
event|wilderness-rebellion|旷野反叛|Wilderness Rebellion|event|可拉、大坍、亚比兰、巴兰巴勒等旷野警戒事件。
event|conquest-canaan|征服迦南|Conquest of Canaan|event|约书亚、迦勒、喇合、亚干等进入应许地事件。
event|judges-cycle|士师循环|Cycle of Judges|event|士师时代压迫、呼求、拯救、再堕落的循环。
event|monarchy-rise|王国兴起|Rise of Monarchy|event|撒母耳、扫罗、大卫受膏建国。
event|david-goliath|大卫击败歌利亚|David Defeats Goliath|event|大卫击败非利士巨人歌利亚。
event|kingdom-split|王国分裂|Divided Kingdom|event|罗波安和耶罗波安导致南北国分裂。
event|babylonian-exile|巴比伦被掳|Babylonian Exile|event|尼布甲尼撒征服耶路撒冷并掳走犹大人。
event|return-from-exile|被掳归回|Return from Exile|event|古列准许归回，以斯拉尼希米重建。
event|incarnation|道成肉身/降生|Incarnation|event|耶稣由童女马利亚所生。
event|baptism-jesus|耶稣受洗|Baptism of Jesus|event|施洗约翰为耶稣施洗。
event|crucifixion|十字架受难|Crucifixion|event|耶稣在各各他被钉十字架。
event|resurrection|复活|Resurrection|event|耶稣第三日复活。
event|pentecost|五旬节|Pentecost|event|彼得讲道，圣灵降临。
event|paul-conversion|保罗悔改|Paul Conversion|event|保罗在大马士革路上遇见复活主。
event|paul-missionary-journeys|保罗宣教旅程|Paul Missionary Journeys|event|保罗多次宣教、建立教会。
event|paul-rome-imprisonment|保罗罗马被囚|Paul Imprisonment in Rome|event|保罗被押送并在罗马被囚。
group|israelites|以色列人|Israelites|group|神藉摩西领出的约民群体。
group|judah-exiles|犹大被掳者|Judah Exiles|group|被巴比伦掳去的犹大群体。
group|jews-returnees|归回犹太人|Jewish Returnees|group|古列诏令后归回的犹太群体。
nation|babylon-empire|巴比伦帝国|Babylonian Empire|nation|尼布甲尼撒统治下征服犹大的帝国。
nation|persian-empire|波斯帝国|Persian Empire|nation|准许犹太人归回的帝国背景。
$nodes$, E'\n')
), nodes AS (
    SELECT
        parts[1] AS node_type,
        parts[2] AS slug,
        parts[3] AS name,
        parts[4] AS name_en,
        parts[5] AS category,
        parts[6] AS description
    FROM raw
    CROSS JOIN LATERAL (SELECT string_to_array(line, '|') AS parts) parsed
    WHERE line <> ''
)
INSERT INTO biblical_graph_nodes (id, node_type, name, name_en, category, description)
SELECT node_type || '-' || slug, node_type, name, name_en, category, description
FROM nodes
ON CONFLICT (id) DO UPDATE SET
    node_type = EXCLUDED.node_type,
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    is_active = true;

WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($edges$
character|亚伯拉罕|character|以撒|FATHER_OF|family|父亲|创21|亚伯拉罕是以撒的父亲。|3.5
character|以撒|character|雅各|FATHER_OF|family|父亲|创25|以撒是雅各的父亲。|3.5
character|以撒|character|以扫|FATHER_OF|family|父亲|创25|以撒是以扫的父亲。|3.0
character|雅各|character|犹大（雅各之子）|FATHER_OF|family|父亲|创29|雅各是犹大的父亲。|3.0
character|犹大（雅各之子）|character|法勒斯|FATHER_OF|family|父亲|创38|犹大与他玛生法勒斯。|3.0
character|他玛|character|法勒斯|MOTHER_OF|family|母亲|创38|他玛生法勒斯。|3.0
character|犹大（雅各之子）|character|大卫|ANCESTOR_OF|family|祖先|得4,太1|大卫出自犹大支派。|3.0
character|大卫|character|耶稣基督|ANCESTOR_OF|family|祖先|太1,路3|耶稣按肉身为大卫后裔。|3.5
character|撒拉|character|以撒|MOTHER_OF|family|母亲|创21|撒拉生以撒。|3.0
character|利百加|character|雅各|MOTHER_OF|family|母亲|创25|利百加生雅各。|2.8
character|利百加|character|以扫|MOTHER_OF|family|母亲|创25|利百加生以扫。|2.8
character|亚伯拉罕|character|撒拉|SPOUSE_OF|family|夫妻|创12-23|亚伯拉罕与撒拉为夫妻。|3.0
character|以撒|character|利百加|SPOUSE_OF|family|夫妻|创24|以撒与利百加为夫妻。|3.0
character|雅各|character|利亚|SPOUSE_OF|family|夫妻|创29|雅各与利亚为夫妻。|2.5
character|雅各|character|拉结|SPOUSE_OF|family|夫妻|创29|雅各与拉结为夫妻。|2.5
character|摩西|character|亚伦|SIBLING_OF|family|兄弟|出4-6|摩西与亚伦为兄弟。|2.8
character|摩西|character|米利暗|SIBLING_OF|family|姐弟|出15,民12|米利暗是摩西的姊妹。|2.5
character|马利亚|character|耶稣基督|MOTHER_OF|family|母亲|路1-2|马利亚生耶稣。|3.5
character|约瑟（耶稣父亲）|character|马利亚|SPOUSE_OF|family|夫妻|太1-2|约瑟与马利亚为夫妻。|2.5
character|撒迦利亚（约翰父亲）|character|施洗约翰|FATHER_OF|family|父亲|路1|撒迦利亚是施洗约翰的父亲。|3.0
character|以利沙伯|character|施洗约翰|MOTHER_OF|family|母亲|路1|以利沙伯是施洗约翰的母亲。|3.0
character|撒母耳|character|扫罗|ANOINTED|spiritual|膏立|撒上10|撒母耳膏立扫罗。|3.0
character|撒母耳|character|大卫|ANOINTED|spiritual|膏立|撒上16|撒母耳膏立大卫。|3.0
character|以利亚|character|以利沙|MENTOR_OF|spiritual|师徒|王上19,王下2|以利亚呼召并栽培以利沙。|3.5
character|摩西|character|约书亚|MENTOR_OF|spiritual|栽培继承者|民27,申31|摩西栽培约书亚承接带领。|3.5
character|耶稣基督|character|彼得|CALLED|spiritual|呼召|太4,约21|耶稣呼召彼得跟随。|3.5
character|耶稣基督|character|约翰|CALLED|spiritual|呼召|太4|耶稣呼召约翰跟随。|3.0
character|耶稣基督|character|西庇太的雅各|CALLED|spiritual|呼召|太4|耶稣呼召雅各跟随。|3.0
character|耶稣基督|character|马太|CALLED|spiritual|呼召|太9|耶稣呼召税吏马太。|3.0
character|保罗|character|提摩太|MENTOR_OF|spiritual|属灵父亲|提前,提后|保罗栽培提摩太。|3.5
character|保罗|character|提多|MENTOR_OF|spiritual|属灵父亲|多1|保罗差遣提多整顿教会。|3.0
character|巴拿巴|character|保罗|SENT_WITH|spiritual|同被差遣|徒13|巴拿巴与保罗同被安提阿教会差派。|2.8
character|彼得|character|百夫长哥尼流|PREACHED_TO|spiritual|传道给|徒10|彼得向哥尼流家传福音。|3.0
character|腓力|character|埃提阿伯太监|PREACHED_TO|spiritual|传道给|徒8|腓利向埃提阿伯太监讲解福音。|3.0
character|亚居拉|character|亚波罗|MENTOR_OF|spiritual|讲解真道|徒18|亚居拉帮助亚波罗更准确认识主道。|2.5
character|百基拉|character|亚波罗|MENTOR_OF|spiritual|讲解真道|徒18|百基拉帮助亚波罗更准确认识主道。|2.5
character|尼布甲尼撒|place|jerusalem|CONQUERED|political|攻陷|王下24-25|尼布甲尼撒攻陷耶路撒冷。|3.5
nation|babylon-empire|group|judah-exiles|EXILED|political|掳掠|王下24-25|巴比伦掳走犹大人。|3.5
character|古列|group|jews-returnees|ALLOWED_RETURN|political|准许归回|拉1|古列下诏准许犹太人归回。|3.5
character|大卫|character|歌利亚|DEFEATED|political|击败|撒上17|大卫击败歌利亚。|3.5
character|约书亚|place|canaan|LED_CONQUEST_OF|political|带领征服|书1-12|约书亚带领以色列进入并征服迦南。|3.5
character|押沙龙|character|大卫|REBELLED_AGAINST|political|背叛|撒下15-18|押沙龙背叛大卫。|3.0
character|扫罗|character|大卫|ATTACKED|political|追杀|撒上18-31|扫罗追杀大卫。|3.0
character|罗波安|character|耶罗波安|OPPOSED|political|王国分裂对立|王上12|罗波安与耶罗波安导致王国分裂。|3.0
character|彼拉多|character|耶稣基督|SENTENCED|political|判刑|约19|彼拉多将耶稣交给人钉十字架。|3.0
character|亚当|event|creation-fall|PARTICIPATED_IN|event|参与事件|创2-3|亚当参与创造与堕落叙事。|2.5
character|夏娃|event|creation-fall|PARTICIPATED_IN|event|参与事件|创2-3|夏娃参与创造与堕落叙事。|2.5
character|挪亚|event|flood|PARTICIPATED_IN|event|参与事件|创6-9|挪亚经历洪水审判与拯救。|3.0
character|宁录|event|tower-of-babel|ASSOCIATED_WITH|event|相关事件|创10-11|宁录与巴别、古代王权传统相关。|2.0
character|亚伯拉罕|event|abraham-call|PARTICIPATED_IN|event|参与事件|创12|亚伯拉罕蒙召离开本地。|3.0
character|亚伯拉罕|event|isaac-sacrifice|PARTICIPATED_IN|event|参与事件|创22|亚伯拉罕献以撒。|3.0
character|以撒|event|isaac-sacrifice|PARTICIPATED_IN|event|参与事件|创22|以撒参与摩利亚山事件。|2.5
character|摩西|event|exodus|LED|event|带领事件|出1-14|摩西带领出埃及。|3.5
character|亚伦|event|exodus|PARTICIPATED_IN|event|参与事件|出4-14|亚伦与摩西同工出埃及。|3.0
character|法老|event|exodus|OPPOSED|event|反对事件|出5-14|法老抵挡出埃及。|3.0
character|摩西|event|sinai-covenant|PARTICIPATED_IN|event|参与事件|出19-24|摩西在西奈领受律法。|3.0
character|可拉|event|wilderness-rebellion|INITIATED|event|发起事件|民16|可拉参与旷野反叛。|2.8
character|约书亚|event|conquest-canaan|LED|event|带领事件|书1-12|约书亚带领征服迦南。|3.5
character|喇合|event|conquest-canaan|PARTICIPATED_IN|event|参与事件|书2,6|喇合保护探子并在耶利哥得救。|2.8
character|亚干|event|conquest-canaan|CAUSED_FAILURE_IN|event|造成失败|书7|亚干犯罪导致艾城失败。|2.5
character|底波拉|event|judges-cycle|PARTICIPATED_IN|event|参与事件|士4-5|底波拉在士师循环中带来拯救。|2.5
character|撒母耳|event|monarchy-rise|PARTICIPATED_IN|event|参与事件|撒上8-16|撒母耳膏立以色列早期君王。|3.0
character|大卫|event|david-goliath|PARTICIPATED_IN|event|参与事件|撒上17|大卫参与击败歌利亚事件。|3.0
character|歌利亚|event|david-goliath|DIED_IN|event|死于事件|撒上17|歌利亚死于大卫击败他的事件。|2.8
character|罗波安|event|kingdom-split|CAUSED|event|造成事件|王上12|罗波安拒绝智慧建议导致分裂。|2.8
character|耶罗波安|event|kingdom-split|PARTICIPATED_IN|event|参与事件|王上12|耶罗波安成为北国第一位王。|2.8
character|尼布甲尼撒|event|babylonian-exile|INITIATED|event|发起事件|王下24-25|尼布甲尼撒导致犹大被掳。|3.0
character|但以理|event|babylonian-exile|PARTICIPATED_IN|event|参与事件|但1|但以理身处被掳背景。|2.5
character|古列|event|return-from-exile|INITIATED|event|发起事件|拉1|古列诏令开启归回。|3.0
character|以斯拉|event|return-from-exile|PARTICIPATED_IN|event|参与事件|拉7-10|以斯拉参与归回后的律法改革。|2.5
character|尼希米|event|return-from-exile|PARTICIPATED_IN|event|参与事件|尼1-6|尼希米重建耶路撒冷城墙。|2.5
character|马利亚|event|incarnation|PARTICIPATED_IN|event|参与事件|路1-2|马利亚参与耶稣降生事件。|3.0
character|约瑟（耶稣父亲）|event|incarnation|PARTICIPATED_IN|event|参与事件|太1-2|约瑟保护马利亚和耶稣。|2.8
character|施洗约翰|event|baptism-jesus|PARTICIPATED_IN|event|参与事件|太3|施洗约翰为耶稣施洗。|3.0
character|耶稣基督|event|crucifixion|PARTICIPATED_IN|event|参与事件|太27,约19|耶稣在十字架上受死。|3.5
character|犹大|event|crucifixion|CAUSED_CONTEXT_FOR|event|造成事件背景|太26-27|犹大出卖耶稣，进入受难事件链。|2.5
character|彼得|event|pentecost|PREACHED_AT|event|讲道于|徒2|彼得在五旬节讲道。|3.0
character|保罗|event|paul-conversion|PARTICIPATED_IN|event|参与事件|徒9|保罗在大马士革路上悔改。|3.0
character|亚拿尼亚（大马士革）|event|paul-conversion|PARTICIPATED_IN|event|参与事件|徒9|亚拿尼亚接待并按手在保罗身上。|2.5
character|保罗|event|paul-missionary-journeys|PARTICIPATED_IN|event|参与事件|徒13-28|保罗参与宣教旅程。|3.0
character|巴拿巴|event|paul-missionary-journeys|PARTICIPATED_IN|event|参与事件|徒13-15|巴拿巴参与保罗早期宣教。|2.5
character|保罗|event|paul-rome-imprisonment|PARTICIPATED_IN|event|参与事件|徒28|保罗在罗马被囚。|2.8
character|耶稣基督|place|bethlehem|BORN_IN|location|出生于|路2|耶稣生于伯利恒。|3.5
character|耶稣基督|place|nazareth|GREW_UP_IN|location|成长于|路2:51-52|耶稣在拿撒勒成长。|3.5
character|耶稣基督|place|golgotha|CRUCIFIED_AT|location|钉十字架于|约19|耶稣在各各他被钉十字架。|3.5
character|马利亚|place|bethlehem|TRAVELED_TO|location|前往|路2|马利亚前往伯利恒并生下耶稣。|2.5
character|约瑟（耶稣父亲）|place|egypt|TRAVELED_TO|location|逃往|太2|约瑟带马利亚和耶稣逃往埃及。|2.5
character|摩西|place|egypt|LIVED_IN|location|居住于|出2|摩西早年在埃及长大。|2.5
character|摩西|place|mount-sinai|MINISTERED_IN|location|服事于|出19-34|摩西在西奈领受律法。|3.0
character|约书亚|place|canaan|MINISTERED_IN|location|服事于|书1-24|约书亚在迦南带领以色列。|3.0
character|但以理|place|babylon|EXILED_TO|location|被掳到|但1|但以理被掳到巴比伦。|3.0
character|以西结|place|babylon|EXILED_TO|location|被掳到|结1|以西结在被掳之地事奉。|2.5
character|尼希米|place|jerusalem|MINISTERED_IN|location|服事于|尼1-6|尼希米在耶路撒冷重建城墙。|2.5
character|保罗|place|damascus|TRAVELED_TO|location|前往|徒9|保罗前往大马士革途中遇见主。|2.8
character|保罗|place|antioch|SENT_FROM|location|被差遣自|徒13|保罗从安提阿被差派。|2.8
character|保罗|place|ephesus|MINISTERED_IN|location|服事于|徒19|保罗在以弗所服事并引发广泛影响。|2.5
character|保罗|place|philippi|MINISTERED_IN|location|服事于|徒16|保罗在腓立比传福音。|2.5
character|保罗|place|rome|IMPRISONED_IN|location|被囚于|徒28|保罗在罗马被囚。|3.0
character|约拿（先知）|place|nineveh|PREACHED_IN|location|传道于|拿3|约拿在尼尼微传讲悔改。|2.8
character|那鸿|place|nineveh|PROPHESIED_AGAINST|location|预言攻击|鸿1-3|那鸿宣告尼尼微审判。|2.5
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
         ON source_kind = 'character' AND source_char.name = source_ref
    LEFT JOIN biblical_graph_nodes source_char_node
         ON source_char_node.character_id = source_char.id
    LEFT JOIN biblical_characters target_char
         ON target_kind = 'character' AND target_char.name = target_ref
    LEFT JOIN biblical_graph_nodes target_char_node
         ON target_char_node.character_id = target_char.id
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
    sort_order
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
    true,
    1000 + ord
FROM resolved
WHERE source_node_id IS NOT NULL
  AND target_node_id IS NOT NULL
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = target_node_id)
ON CONFLICT DO NOTHING;

CREATE OR REPLACE VIEW v_biblical_knowledge_graph_edges AS
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

CREATE OR REPLACE VIEW v_biblical_knowledge_graph_nodes AS
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
