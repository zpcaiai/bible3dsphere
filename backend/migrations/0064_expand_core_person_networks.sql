-- 0064_expand_core_person_networks.sql
-- Expand the biblical knowledge graph and 镜鉴 character database with the core
-- person networks: Genesis genealogy fill-ins, the patriarch / exodus / conquest /
-- judges / monarchy / divided-kingdom / exile-return / gospel / Acts / epistle people,
-- plus the rich family · ministry · political · event · place · theme · typology edges
-- that turn the flat roster into a queryable multi-layer graph (the 12 priority subgraphs).
--
-- Pattern follows 0062: PART A inserts people (NOT EXISTS guards), PART B creates graph
-- nodes generically, PART C resolves and inserts typed edges by name (unmatched skipped),
-- PART D performs the section-13 split / merge cleanup. Fully idempotent.

-- Keep the character id sequence past the current max so new ids do not collide.
SELECT setval(
    pg_get_serial_sequence('biblical_characters', 'id'),
    COALESCE((SELECT MAX(id) FROM biblical_characters), 0)
);

-- ============================================================
-- PART 0a. Register new relationship types (registry only; edges have no FK)
-- ============================================================
INSERT INTO biblical_graph_relationship_types
    (relationship_type, relationship_category, label_zh, label_en, description, inverse_type, target_types, sort_order, is_core)
VALUES
    ('KILLED','event','杀害','killed','一人杀害另一人的事件关系。','KILLED_BY',ARRAY['character']::text[],900,false),
    ('KILLED_BY','event','被杀于','killed by','某人被另一人所杀。','KILLED',ARRAY['character']::text[],900,false),
    ('FRIEND_OF','family','朋友','friend of','深厚友谊的关系，通常为无向。','FRIEND_OF',ARRAY['character']::text[],900,false),
    ('BETRAYED','political','背叛','betrayed','背叛、出卖另一人的关系。',NULL,ARRAY['character']::text[],900,false),
    ('SERVANT_OF','spiritual','仆人','servant of','作某人的仆人或随从。',NULL,ARRAY['character']::text[],900,false),
    ('COMMANDER_OF','political','元帅','commander of','作某君王或军队的元帅。',NULL,ARRAY['character']::text[],900,false),
    ('HEALED','event','医治','healed','耶稣或使徒医治、释放某人。','HEALED_BY',ARRAY['character']::text[],900,false),
    ('HEALED_BY','event','得医治于','healed by','某人被医治或得释放。','HEALED',ARRAY['character']::text[],900,false),
    ('PROTECTED','event','保护','protected','保护、藏匿、抚养或拯救某人。',NULL,ARRAY['character']::text[],900,false)
ON CONFLICT (relationship_type) DO NOTHING;

-- ============================================================
-- PART 0b. New non-character graph nodes (place / event / nation / group / book)
-- ============================================================
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($nodes$
nation|assyria-empire|亚述帝国|Assyrian Empire|nation|掳掠北国以色列、围攻犹大的帝国。
nation|aram-damascus|亚兰|Aram (Syria)|nation|以大马士革为中心的亚兰王国，常与以色列争战。
nation|moab|摩押|Moab|nation|罗得后裔之国，士师与王国时期与以色列为敌。
nation|midian|米甸|Midian|nation|亚伯拉罕与基土拉后裔，士师时代压迫以色列。
nation|philistia|非利士|Philistia|nation|以色列沿海的宿敌，歌利亚、参孙故事背景。
nation|amalek|亚玛力|Amalek|nation|以扫后裔，以色列世代的仇敌。
nation|edom|以东|Edom|nation|以扫的后裔之国。
nation|tyre|推罗|Tyre|nation|腓尼基沿海商业王国，希兰王之国。
nation|ammon|亚扪|Ammon|nation|罗得后裔之国。
nation|rome-empire|罗马帝国|Roman Empire|nation|新约时期统治犹太地的帝国。
place|susa|书珊|Susa|location|波斯王宫所在地，以斯帖记的背景城。
place|samaria|撒玛利亚|Samaria|location|北国以色列的都城。
place|gibeah|基比亚|Gibeah|location|扫罗的家乡与王都。
place|jezreel|耶斯列|Jezreel|location|拿伯葡萄园与耶户清洗亚哈家之地。
place|mahanaim|玛哈念|Mahanaim|location|伊施波设作王、大卫避难之地。
place|geshur|基述|Geshur|location|押沙龙杀暗嫩后逃往之地。
place|endor|隐多珥|En-dor|location|扫罗求问交鬼妇人之地。
place|timnah|亭拿|Timnah|location|参孙娶非利士妻之地。
event|esther-deliverance|以斯帖拯救|Deliverance through Esther|event|以斯帖与末底改拯救犹大人、设立普珥日。
event|elijah-elisha-ministry|以利亚以利沙事工|Ministry of Elijah and Elisha|event|北国先知以利亚、以利沙的事奉与神迹。
event|jesus-miracles|耶稣的神迹|Miracles of Jesus|event|耶稣医病、赶鬼、使死人复活的神迹。
event|assyrian-crisis|亚述围城危机|Assyrian Crisis|event|西拿基立围攻耶路撒冷，神拯救希西家。
event|naboth-vineyard|拿伯葡萄园事件|Naboth's Vineyard|event|耶洗别陷害拿伯，亚哈夺取葡萄园。
group|herodian-dynasty|希律王朝|Herodian Dynasty|group|新约时期统治犹太地的希律家族。
book|samuel|撒母耳记|Samuel|book|记载撒母耳、扫罗与大卫的历史书。
book|kings|列王纪|Kings|book|记载所罗门至被掳的列王历史。
book|chronicles|历代志|Chronicles|book|以祭司与谱系视角重述以色列历史。
book|psalms|诗篇|Psalms|book|以色列的祷告与敬拜诗集，多为大卫所作。
$nodes$, E'\n')
), node_rows AS (
    SELECT parts[1] AS node_type, parts[2] AS slug, parts[3] AS name,
           parts[4] AS name_en, parts[5] AS category, parts[6] AS description
    FROM raw CROSS JOIN LATERAL (SELECT string_to_array(line,'|') AS parts) p
    WHERE line <> '' AND line NOT LIKE '--%'
)
INSERT INTO biblical_graph_nodes (id, node_type, name, name_en, category, description, chinese_name, english_name, testament)
SELECT node_type||'-'||slug, node_type, name, name_en, category, description, name, name_en,
       CASE WHEN node_type='nation' AND slug IN ('rome-empire') THEN 'New Testament' ELSE NULL END
FROM node_rows
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- PART A. Insert people (镜鉴 character rows). name|name_en|era|role|type|scripture_ref|summary
-- ============================================================
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($people$
基土拉|Keturah|族长时代|女性|混合|创25:1-4|亚伯拉罕的后妻，为他生了米甸等六子。
米甸|Midian|族长时代|其他|混合|创25:2|亚伯拉罕与基土拉所生之子，米甸族的祖先。
拉班|Laban|族长时代|其他|混合|创24,29-31|利百加之兄，利亚与拉结之父，雅各的岳父。
辟拉|Bilhah|族长时代|女性|混合|创30:1-8|拉结的使女，生但与拿弗他利。
悉帕|Zilpah|族长时代|女性|混合|创30:9-13|利亚的使女，生迦得与亚设。
底拿|Dinah|族长时代|女性|混合|创34|雅各与利亚的女儿，示剑事件的中心人物。
示剑|Shechem|族长时代|其他|警戒|创34|希未人哈抹之子，玷辱底拿。
哈抹|Hamor|族长时代|其他|混合|创34|希未人，示剑之父。
谢拉（犹大之子）|Zerah|族长时代|其他|混合|创38:30|犹大与他玛所生的双胞胎之一。
波提乏|Potiphar|族长时代|其他|混合|创39:1|埃及法老的护卫长，约瑟的主人。
波提乏的妻子|Potiphar's wife|族长时代|女性|警戒|创39:7-20|诬陷约瑟、试探他的妇人。
酒政|Cupbearer|族长时代|其他|混合|创40|埃及法老的酒政，约瑟为他解梦。
膳长|Baker|族长时代|其他|警戒|创40|埃及法老的膳长，约瑟为他解梦。
提幔人以利法|Eliphaz the Temanite|族长时代|其他|混合|伯4-5|约伯的三友之一，以传统智慧论断约伯。
书亚人比勒达|Bildad the Shuhite|族长时代|其他|混合|伯8|约伯的三友之一。
拿玛人琐法|Zophar the Naamathite|族长时代|其他|混合|伯11|约伯的三友之一。
暗兰|Amram|出埃及时代|其他|正面|出6:20|利未的孙子，摩西、亚伦、米利暗之父。
法老的女儿|Pharaoh's daughter|出埃及时代|女性|正面|出2:5-10|从河中救起婴孩摩西并收养他。
叶忒罗|Jethro|出埃及时代|祭司|正面|出3:1,18:13-26|米甸的祭司，摩西的岳父，给摩西治理的智慧（又名流珥）。
革舜|Gershom|出埃及时代|其他|混合|出2:22|摩西与西坡拉的长子。
以利以谢（摩西之子）|Eliezer|出埃及时代|其他|混合|出18:4|摩西的次子，名意为神是我的帮助。
亚比户|Abihu|出埃及时代|祭司|警戒|利10:1-2|亚伦次子，与拿答献凡火被神击杀。
以利亚撒（亚伦之子）|Eleazar|出埃及时代|祭司|正面|民20:25-28|亚伦之子，继任大祭司，与约书亚分地。
以他玛|Ithamar|出埃及时代|祭司|混合|出38:21|亚伦之子，祭司家族的一支。
昂|On|出埃及时代|其他|警戒|民16:1|流便支派人，可拉党羽之一。
巴勒|Balak|出埃及时代|君王|警戒|民22-24|摩押王，雇巴兰咒诅以色列。
西罗非哈|Zelophehad|出埃及时代|其他|混合|民27:1-7|玛拿西支派人，无子，五个女儿争得产业。
玛拉（西罗非哈之女）|Mahlah|出埃及时代|女性|正面|民27:1|西罗非哈的女儿之一。
挪阿|Noah (daughter)|出埃及时代|女性|正面|民27:1|西罗非哈的女儿之一。
曷拉|Hoglah|出埃及时代|女性|正面|民27:1|西罗非哈的女儿之一。
密迦（西罗非哈之女）|Milcah|出埃及时代|女性|正面|民27:1|西罗非哈的女儿之一。
得撒|Tirzah|出埃及时代|女性|正面|民27:1|西罗非哈的女儿之一。
亚干|Achan|进入迦南时代|其他|警戒|书7|因私取当灭之物连累以色列在艾城失败。
迦米|Carmi|进入迦南时代|其他|混合|书7:1|亚干之父。
撒底|Zabdi|进入迦南时代|其他|混合|书7:1|亚干的祖父。
押撒|Achsah|进入迦南时代|女性|正面|书15:16-19|迦勒的女儿，俄陀聂之妻，求得水泉之地。
亚多尼洗德|Adoni-zedek|进入迦南时代|君王|警戒|书10:1-27|耶路撒冷王，南方五王联盟之首。
何咸|Hoham|进入迦南时代|君王|警戒|书10:3|希伯仑王，南方联盟成员。
毗兰|Piram|进入迦南时代|君王|警戒|书10:3|耶末王，南方联盟成员。
雅非亚|Japhia|进入迦南时代|君王|警戒|书10:3|拉吉王，南方联盟成员。
底璧王|Debir|进入迦南时代|君王|警戒|书10:3|伊矶伦王，南方联盟成员。
耶宾（夏琐王）|Jabin|进入迦南时代|君王|警戒|书11:1-11|夏琐王，北方联盟之首，被约书亚击败。
基遍人长老|Gibeonite elders|进入迦南时代|其他|混合|书9|基遍居民的首领，用诡计与以色列立约。
西西拉|Sisera|士师时代|其他|警戒|士4|迦南将军，被雅亿用帐棚橛子所杀。
伊矶伦|Eglon|士师时代|君王|警戒|士3:12-30|摩押王，被以笏刺杀。
耶宾（士师时代）|Jabin|士师时代|君王|警戒|士4|夏琐王，压迫以色列二十年，底波拉时代的敌人。
西巴（米甸王）|Zebah|士师时代|君王|警戒|士8|米甸二王之一，被基甸追杀。
撒慕拿|Zalmunna|士师时代|君王|警戒|士8|米甸二王之一，被基甸所杀。
俄立|Oreb|士师时代|其他|警戒|士7:25|米甸首领，被基甸的军队所杀。
西伊伯|Zeeb|士师时代|其他|警戒|士7:25|米甸首领，与俄立一同被杀。
玛挪亚的妻子|Manoah's wife|士师时代|女性|正面|士13|参孙的母亲，蒙天使预告生子。
大利拉|Delilah|士师时代|女性|警戒|士16|受非利士人收买，探出参孙力量的秘密并出卖他。
参孙的非利士妻|Samson's Philistine wife|士师时代|女性|混合|士14|亭拿的女子，参孙的第一任妻子。
耶弗他的女儿|Jephthah's daughter|士师时代|女性|正面|士11:34-40|因父亲的许愿而献上自己的独生女。
但支派探子|Danite spies|士师时代|其他|混合|士18|但支派所差、夺取米迦神像的五人。
以利加拿|Elkanah|王国时代|其他|正面|撒上1|哈拿的丈夫，撒母耳的父亲。
毗尼拿|Peninnah|王国时代|女性|警戒|撒上1|以利加拿的另一妻子，常激动哈拿。
何弗尼|Hophni|王国时代|祭司|警戒|撒上2|以利的恶儿子之一，藐视耶和华的祭物。
非尼哈（以利之子）|Phinehas|王国时代|祭司|警戒|撒上2,4|以利的恶儿子，与约柜一同战死。
以迦博|Ichabod|王国时代|其他|混合|撒上4:21|非尼哈之子，名意为荣耀离开以色列。
基士|Kish|王国时代|其他|混合|撒上9:1-2|便雅悯人，扫罗的父亲。
亚比拿达（扫罗之子）|Abinadab|王国时代|其他|混合|撒上31:2|扫罗之子，与父同死于基利波。
麦基舒亚|Malchishua|王国时代|其他|混合|撒上31:2|扫罗之子，战死于基利波山。
伊施波设|Ish-bosheth|王国时代|君王|混合|撒下2-4|扫罗之子，短暂作以色列王，后被刺杀。
押尼珥|Abner|王国时代|其他|混合|撒下2-3|扫罗的元帅，立伊施波设为王，后归大卫被约押所杀。
米甲|Michal|王国时代|女性|混合|撒上18-19;撒下6|扫罗的女儿，大卫的妻子。
亚希米勒|Ahimelech|王国时代|祭司|正面|撒上21-22|挪伯的祭司，帮助大卫，被扫罗下令杀害。
多益|Doeg|王国时代|其他|警戒|撒上22|以东人，告发并杀害挪伯的祭司。
耶西|Jesse|王国时代|其他|正面|撒上16;得4|大卫的父亲，伯利恒人，弥赛亚谱系。
以利押|Eliab|王国时代|其他|混合|撒上16:6,17:28|大卫的长兄。
亚比拿达（大卫之兄）|Abinadab|王国时代|其他|混合|撒上16:8|耶西的次子，大卫的哥哥。
沙玛（大卫之兄）|Shammah|王国时代|其他|混合|撒上16:9|耶西的三子，大卫的哥哥。
暗嫩|Amnon|王国时代|其他|警戒|撒下13|大卫的长子，玷辱他玛，被押沙龙所杀。
他玛（大卫之女）|Tamar|王国时代|女性|混合|撒下13|大卫的女儿，押沙龙的妹妹，被暗嫩玷辱。
基利押|Chileab|王国时代|其他|混合|撒下3:3|大卫与亚比该所生之子。
亚多尼雅|Adonijah|王国时代|其他|警戒|王上1|大卫之子，自立为王，争夺王位。
亚玛撒|Amasa|王国时代|其他|混合|撒下17,20|押沙龙的元帅，后被约押所杀。
巴西莱|Barzillai|王国时代|其他|正面|撒下17,19|基列人，在大卫逃难时供应他。
洗巴|Ziba|王国时代|其他|混合|撒下9,16|扫罗家的仆人，服事米非波设。
示每|Shimei|王国时代|其他|警戒|撒下16|便雅悯人，大卫逃难时咒骂他。
亚比筛|Abishai|王国时代|其他|混合|撒上26;撒下10|洗鲁雅之子，约押之兄，大卫的勇士。
亚撒黑|Asahel|王国时代|其他|混合|撒下2|洗鲁雅之子，跑得快，被押尼珥所杀。
雅朔班|Jashobeam|王国时代|其他|正面|代上11:11|大卫勇士之首，又名约设巴设。
以利亚撒（大卫勇士）|Eleazar|王国时代|其他|正面|撒下23:9|大卫三勇士之一。
沙玛（大卫勇士）|Shammah|王国时代|其他|正面|撒下23:11|大卫三勇士之一，独守豆田击败非利士人。
洗鲁雅|Zeruiah|王国时代|女性|混合|代上2:16|大卫的姊妹，约押、亚比筛、亚撒黑之母。
希兰|Hiram|王国时代|君王|正面|王上5|推罗王，供应建殿的材料。
哈达|Hadad|王国时代|其他|警戒|王上11:14-22|以东王室后裔，所罗门晚年的敌人。
利逊|Rezon|王国时代|其他|警戒|王上11:23-25|大马士革的亚兰人，所罗门的敌人。
尼八|Nebat|王国时代|其他|混合|王上11:26|耶罗波安的父亲。
洗鲁阿|Zeruah|王国时代|女性|混合|王上11:26|耶罗波安的母亲，寡妇。
示撒|Shishak|王国时代|君王|警戒|王上14:25-26|埃及王，攻打耶路撒冷夺取圣殿宝物。
所罗门的外邦妃嫔|Solomon's foreign wives|王国时代|女性|警戒|王上11:1-8|使所罗门的心偏离耶和华的外邦女子。
西缅（雅各之子）|Simeon|族长时代|族长|混合|创29:33;34:25|雅各与利亚的次子，西缅支派的祖先，为底拿向示剑报仇。
利未（雅各之子）|Levi|族长时代|族长|混合|创29:34;出6:16|雅各与利亚的三子，利未支派与祭司体系的祖先。
巴沙|Baasha|王国时代|君王|警戒|王上15:16-16:7|篡夺拿答王位，行恶的北国王。
以拉（以色列王）|Elah|王国时代|君王|警戒|王上16:8-10|巴沙之子，北国王，醉酒时被心利所弑。
心利|Zimri|王国时代|君王|警戒|王上16:8-20|作王仅七日的篡位者。
提比尼|Tibni|王国时代|君王|混合|王上16:21-22|与暗利争夺王位失败。
撒迦利雅（以色列王）|Zechariah|王国时代|君王|警戒|王下15:8-12|耶户王朝末代，作王六个月被弑。
沙龙（以色列王）|Shallum|王国时代|君王|警戒|王下15:10-15|弑撒迦利雅篡位，作王仅一个月。
米拿现|Menahem|王国时代|君王|警戒|王下15:14-22|残暴的北国王，向亚述纳贡。
比加辖|Pekahiah|王国时代|君王|警戒|王下15:23-26|米拿现之子，被比加所弑。
比加|Pekah|王国时代|君王|警戒|王下15:27-31|北国王，与利汛联合攻犹大，国土被亚述夺取。
基大利|Gedaliah|被掳归回时代|其他|混合|王下25:22-25;耶40|巴比伦所立的犹大省长，被以实玛利所杀。
哈拿尼（先见）|Hanani|王国时代|先知|正面|代下16:7-10|责备亚撒王倚靠亚兰的先见。
耶户（哈拿尼之子）|Jehu son of Hanani|王国时代|先知|正面|代下19:1-3|责备约沙法与亚哈结盟的先知。
亚撒利雅（俄德之子）|Azariah son of Oded|王国时代|先知|正面|代下15:1-8|劝勉亚撒推行宗教改革的先知。
撒迦利亚（耶何耶大之子）|Zechariah son of Jehoiada|王国时代|祭司|正面|代下24:20-22|因责备约阿施而被石头打死的祭司。
乌利亚祭司|Uriah the priest|王国时代|祭司|警戒|王下16:10-16|照大马士革坛样式为亚哈斯筑坛的祭司。
希勒家|Hilkiah|王国时代|祭司|正面|王下22|约西亚时的大祭司，发现律法书。
沙番|Shaphan|王国时代|其他|正面|王下22|约西亚时的书记，宣读律法书。
亚希甘|Ahikam|王国时代|其他|正面|王下22:12;耶26:24|沙番之子，保护耶利米。
约拿达（利甲之子）|Jonadab son of Rechab|王国时代|其他|正面|王下10:15-23;耶35|利甲族不饮酒传统的奠基者。
利甲族人|Rechabites|王国时代|其他|正面|耶35|顺服祖先吩咐、不喝酒的群体，被立为榜样。
俄巴底（亚哈家宰）|Obadiah|王国时代|其他|正面|王上18:3-16|亚哈的家宰，敬畏神，藏匿一百个先知。
哈薛|Hazael|王国时代|君王|警戒|王下8:7-15|亚兰王，以利沙预言他兴起，残害以色列。
便哈达|Ben-hadad|王国时代|君王|警戒|王上20;王下6|亚兰王（数位同名），多次与以色列争战。
利汛|Rezin|王国时代|君王|警戒|王下16:5-9|亚兰王，与比加联合攻打亚哈斯。
拉伯沙基|Rabshakeh|王国时代|其他|警戒|王下18-19|亚述的将领，在耶路撒冷城下羞辱神。
西拿基立|Sennacherib|王国时代|君王|警戒|王下18-19|亚述王，围攻耶路撒冷，军队被天使击杀。
提革拉毗列色|Tiglath-pileser|王国时代|君王|警戒|王下15:29;16:7-10|亚述王，掳掠以色列北部。
撒缦以色|Shalmaneser|王国时代|君王|警戒|王下17:3-6|亚述王，围困撒玛利亚。
撒珥根|Sargon|王国时代|君王|警戒|赛20:1|亚述王，攻取亚实突。
以撒哈顿|Esarhaddon|王国时代|君王|警戒|王下19:37;拉4:2|西拿基立之子，亚述王。
施亚雅述|Shear-jashub|王国时代|其他|混合|赛7:3|以赛亚之子，名意为余剩的人必归回。
玛黑珥沙拉勒哈施罢斯|Maher-shalal-hash-baz|王国时代|其他|混合|赛8:1-4|以赛亚之子，名意为掳掠速临。
米罗达巴拉但|Merodach-baladan|王国时代|君王|混合|赛39;王下20:12|巴比伦王，派使者见希西家。
以赛亚的妻子|Isaiah's wife|王国时代|女性|正面|赛8:3|被称为女先知，为以赛亚生子。
西莱雅|Seraiah|王国时代|其他|正面|耶51:59-64|尼利亚之子，巴录之兄，奉命将预言书带到巴比伦。
巴施户珥|Pashhur|王国时代|祭司|警戒|耶20|逼迫耶利米、将他枷锁的祭司。
哈拿尼雅（假先知）|Hananiah|王国时代|先知|警戒|耶28|与耶利米对抗、折断木轭的假先知。
示玛雅（尼希兰人）|Shemaiah the Nehelamite|被掳归回时代|先知|警戒|耶29:24-32|从巴比伦写信攻击耶利米的假先知。
约哈难（加利亚之子）|Johanan son of Kareah|被掳归回时代|其他|混合|耶40-43|犹大亡国后的军长，带百姓下埃及。
以实玛利（尼探雅之子）|Ishmael son of Nethaniah|被掳归回时代|其他|警戒|耶41|王室后裔，刺杀省长基大利。
尼布撒拉旦|Nebuzaradan|被掳归回时代|其他|混合|王下25:8-21;耶39|巴比伦的护卫长，焚毁耶路撒冷。
尼布沙斯班|Nebushazban|被掳归回时代|其他|混合|耶39:13|巴比伦的官长。
尼甲沙利薛|Nergal-sharezer|被掳归回时代|其他|混合|耶39:3,13|巴比伦的官长。
布西|Buzi|被掳归回时代|祭司|混合|结1:3|以西结的父亲，祭司。
亚施毗拿|Ashpenaz|被掳归回时代|其他|混合|但1:3-7|巴比伦的太监长，管理但以理等人。
亚略|Arioch|被掳归回时代|其他|混合|但2:14-25|巴比伦王的护卫长。
大利乌（玛代人）|Darius the Mede|被掳归回时代|君王|混合|但6|在伯沙撒之后掌权，将但以理投入狮坑又救他。
耶斯列（何西阿之子）|Jezreel|王国时代|其他|混合|何1:4|何西阿的长子，象征审判的名字。
罗路哈玛|Lo-ruhamah|王国时代|女性|混合|何1:6|何西阿的女儿，名意为不蒙怜悯。
罗阿米|Lo-ammi|王国时代|其他|混合|何1:9|何西阿的儿子，名意为非我民。
亚米太|Amittai|王国时代|其他|混合|拿1:1;王下14:25|约拿的父亲。
尼尼微王|King of Nineveh|王国时代|君王|正面|拿3:6-9|带领尼尼微全城悔改的王。
比利家|Berechiah|被掳归回时代|其他|混合|亚1:1|撒迦利亚先知的父亲。
易多|Iddo|被掳归回时代|先知|混合|亚1:1;拉5:1|撒迦利亚先知的祖父。
设巴萨|Sheshbazzar|被掳归回时代|其他|正面|拉1:8-11;5:14|被立为犹大省长，带回圣殿器皿的归回领袖。
约萨达|Jozadak|被掳归回时代|祭司|混合|拉3:2;该1:1|耶书亚大祭司的父亲。
哈拿尼（尼希米之兄）|Hanani|被掳归回时代|其他|正面|尼1:2;7:2|尼希米的兄弟，被派管理耶路撒冷。
基善|Geshem|被掳归回时代|其他|警戒|尼2:19;6:1-2|阿拉伯人首领，反对尼希米修墙（又名迦施慕）。
示玛雅（阻挠尼希米）|Shemaiah|被掳归回时代|先知|警戒|尼6:10-13|受雇恐吓尼希米的假先知。
挪亚底|Noadiah|被掳归回时代|女性|警戒|尼6:14|恐吓尼希米的女先知。
哈拿尼雅（尼希米治理者）|Hananiah|被掳归回时代|其他|正面|尼7:2|忠信敬畏神，被派管理耶路撒冷营楼。
瓦实提|Vashti|被掳归回时代|女性|混合|斯1|被废的王后。
细利斯|Zeresh|被掳归回时代|女性|警戒|斯5-6|哈曼的妻子，献计立木架害末底改。
哈曼十子|Haman's ten sons|被掳归回时代|其他|警戒|斯9:7-10|哈曼的十个儿子，与父一同灭亡。
希该|Hegai|被掳归回时代|其他|混合|斯2:8-15|管理后宫女子的太监，善待以斯帖。
沙甲|Shaashgaz|被掳归回时代|其他|混合|斯2:14|管理妃嫔的太监。
哈波拿|Harbona|被掳归回时代|其他|混合|斯7:9|指出哈曼木架的太监。
比革他|Bigthan|被掳归回时代|其他|警戒|斯2:21-23|图谋杀王的太监。
提列|Teresh|被掳归回时代|其他|警戒|斯2:21-23|与比革他同谋害王的太监。
加百列|Gabriel|新约时代|其他|正面|路1|向撒迦利亚和马利亚报信的天使。
东方博士|Magi|新约时代|其他|正面|太2|从东方来拜见婴孩耶稣的智者。
牧羊人|Shepherds|新约时代|其他|正面|路2:8-20|伯利恒野地里得见主降生的牧人。
希律大帝|Herod the Great|新约时代|君王|警戒|太2|屠杀伯利恒婴孩的犹太王。
希律安提帕|Herod Antipas|新约时代|君王|警戒|可6;路23|杀施洗约翰、审问耶稣的分封王。
希律腓力|Herod Philip|新约时代|其他|混合|可6:17|希罗底的前夫。
希罗底|Herodias|新约时代|女性|警戒|可6|唆使杀施洗约翰的妇人。
希罗底的女儿|Daughter of Herodias|新约时代|女性|警戒|可6:22|为希律跳舞、求施洗约翰头颅的少女。
居里扭|Quirinius|新约时代|其他|混合|路2:2|叙利亚巡抚，报名上册时在任。
凯撒奥古斯都|Caesar Augustus|新约时代|君王|混合|路2:1|耶稣降生时下令报名上册的罗马皇帝。
提庇留|Tiberius Caesar|新约时代|君王|混合|路3:1|施洗约翰与耶稣传道时期的罗马皇帝。
西庇太|Zebedee|新约时代|其他|混合|太4:21|雅各和约翰的父亲，加利利的渔夫。
亚勒腓|Alphaeus|新约时代|其他|混合|可2:14;3:18|马太（利未）与小雅各的父亲。
小雅各（亚勒腓之子）|James son of Alphaeus|新约时代|使徒|正面|可3:18|十二使徒之一，又称小雅各。
睚鲁|Jairus|新约时代|其他|正面|可5|会堂主管，求耶稣医治女儿。
睚鲁的女儿|Jairus' daughter|新约时代|女性|正面|可5:41-42|被耶稣从死里救活的女孩。
血漏的妇人|Woman with the issue of blood|新约时代|女性|正面|可5:25-34|摸耶稣衣裳就得医治。
巴底买|Bartimaeus|新约时代|其他|正面|可10:46-52|耶利哥的瞎子，因信得看见。
毕士大池的病人|Man at Bethesda|新约时代|其他|正面|约5|病了三十八年、被耶稣医好的人。
生来瞎眼的人|Man born blind|新约时代|其他|正面|约9|耶稣医好的生来瞎眼者，勇敢为主作见证。
撒玛利亚妇人|Samaritan woman|新约时代|女性|正面|约4|井边遇见耶稣、得活水的妇人。
叙利腓尼基妇人|Syrophoenician woman|新约时代|女性|正面|可7:24-30|为女儿恳求、以信心蒙称许的外邦妇人（迦南妇人）。
迦百农的百夫长|Centurion at Capernaum|新约时代|其他|正面|太8:5-13|信心大、求耶稣医治仆人的罗马军官。
百夫长的仆人|Centurion's servant|新约时代|其他|正面|太8:5-13|被耶稣远程医治的仆人。
十个长大麻风的|Ten lepers|新约时代|其他|混合|路17:11-19|被耶稣洁净，只有一个撒玛利亚人回来感恩。
格拉森被鬼附的人|Gerasene demoniac|新约时代|其他|正面|可5:1-20|被群鬼所附、得耶稣释放的人。
迦拿婚筵的新郎|Bridegroom at Cana|新约时代|其他|混合|约2:1-11|水变酒神迹中的新郎。
管筵席的|Master of the banquet|新约时代|其他|混合|约2:9|尝出水变之酒的管筵席者。
革罗罢|Cleopas|新约时代|其他|正面|路24:18|以马忤斯路上遇见复活主的门徒。
亚利马太的约瑟|Joseph of Arimathea|新约时代|其他|正面|太27:57-60|安葬耶稣的议士。
彼拉多的妻子|Pilate's wife|新约时代|女性|混合|太27:19|因梦警告彼拉多不可定耶稣的罪。
巴拉巴|Barabbas|新约时代|其他|混合|太27|被释放代替耶稣的囚犯。
亚历山大（古利奈人之子）|Alexander|新约时代|其他|混合|可15:21|古利奈人西门的儿子，与鲁孚同被提名。
埃提阿伯太监|Ethiopian eunuch|新约时代|其他|正面|徒8:26-39|腓利向他传福音并施洗的埃提阿伯财政大臣。
迦玛列|Gamaliel|新约时代|其他|混合|徒5:34-39;22:3|公会中受敬重的教法师，保罗的老师。
马利亚（马可的母亲）|Mary mother of Mark|新约时代|女性|正面|徒12:12|耶路撒冷家庭教会的主人。
罗大|Rhoda|新约时代|女性|正面|徒12:13-15|彼得出监时报信的使女。
亚迦布|Agabus|新约时代|先知|正面|徒11:28;21:10|预言饥荒和保罗被捆的先知。
犹大（巴撒巴）|Judas Barsabbas|新约时代|其他|正面|徒15:22-32|耶路撒冷教会差往安提阿的领袖。
西面（尼结）|Simeon called Niger|新约时代|其他|正面|徒13:1|安提阿教会的先知和教师。
马念|Manaen|新约时代|其他|正面|徒13:1|与希律安提帕一同长大的安提阿教会领袖。
士求保罗|Sergius Paulus|新约时代|其他|正面|徒13:7-12|居比路的方伯，听道信主。
以吕马|Elymas|新约时代|其他|警戒|徒13:8-11|又名巴耶稣，敌挡保罗被罚瞎眼的术士。
腓立比的狱卒|Philippian jailer|新约时代|其他|正面|徒16:25-34|因地震信主、全家受洗的狱卒。
被鬼附的使女|Slave girl with a spirit|新约时代|女性|混合|徒16:16-19|保罗赶出她身上的巫鬼。
底米丢|Demetrius|新约时代|其他|警戒|徒19:24-29|以弗所的银匠，煽动反对保罗的暴乱。
亚里达古|Aristarchus|新约时代|其他|正面|徒19:29;27:2|马其顿人，保罗忠心的同伴与同囚。
所巴特|Sopater|新约时代|其他|正面|徒20:4|庇哩亚人，保罗的同伴。
西公都|Secundus|新约时代|其他|正面|徒20:4|帖撒罗尼迦人，保罗的同伴。
特罗非摩|Trophimus|新约时代|其他|正面|徒21:29;提后4:20|以弗所人，保罗的同伴。
犹推古|Eutychus|新约时代|其他|混合|徒20:9-12|听道睡着坠楼、被保罗救活的少年。
腓力的四个女儿|Philip's four daughters|新约时代|女性|正面|徒21:9|是处女、说预言的四姊妹。
革老丢吕西亚|Claudius Lysias|新约时代|其他|混合|徒21-23|保护保罗的千夫长。
腓力斯|Felix|新约时代|其他|警戒|徒23-24|拖延审判保罗的罗马巡抚。
土西拉|Drusilla|新约时代|女性|混合|徒24:24|腓力斯的犹太妻子。
非斯都|Festus|新约时代|其他|混合|徒25-26|接替腓力斯审问保罗的巡抚。
希律亚基帕一世|Herod Agrippa I|新约时代|君王|警戒|徒12|杀雅各、囚彼得，后被虫咬而死。
希律亚基帕二世|Herod Agrippa II|新约时代|君王|混合|徒25-26|听保罗申辩的王。
百尼基|Bernice|新约时代|女性|混合|徒25:13|亚基帕二世的姊妹。
犹流|Julius|新约时代|其他|正面|徒27|押送保罗去罗马、善待他的百夫长。
部百流|Publius|新约时代|其他|正面|徒28:7-8|米利大岛的首领，接待保罗。
马利亚（罗马教会）|Mary|新约时代|女性|正面|罗16:6|在罗马为信徒多多劳苦的姊妹。
尼利亚的姊妹|Sister of Nereus|新约时代|女性|正面|罗16:15|保罗所问安的圣徒。
德丢|Tertius|新约时代|其他|正面|罗16:22|代笔写罗马书的人。
该犹（马其顿人）|Gaius the Macedonian|新约时代|其他|混合|徒19:29|保罗的马其顿同伴，在以弗所暴乱中被抓。
该犹（约翰三书）|Gaius|新约时代|其他|正面|约三1|约翰所爱、忠心接待弟兄的人。
括土|Quartus|新约时代|其他|正面|罗16:23|保罗问安中提到的弟兄。
亚利多布家的人|Household of Aristobulus|新约时代|其他|混合|罗16:10|保罗问安的一家。
拿其数家的人|Household of Narcissus|新约时代|其他|混合|罗16:11|保罗问安、在主里的一家。
鲁孚的母亲|Rufus' mother|新约时代|女性|正面|罗16:13|待保罗如同母亲的姊妹。
革来氏家里的人|Chloe's people|新约时代|其他|混合|林前1:11|向保罗报告哥林多纷争的人。
所提尼|Sosthenes|新约时代|其他|正面|林前1:1;徒18:17|与保罗同具名写信的弟兄。
司提反一家|Household of Stephanas|新约时代|其他|正面|林前16:15-17|亚该亚初结的果子，专以服事圣徒为念。
福徒拿都|Fortunatus|新约时代|其他|正面|林前16:17|从哥林多来见保罗的同工。
亚该古|Achaicus|新约时代|其他|正面|林前16:17|与福徒拿都同来的同工。
革勒免|Clement|新约时代|其他|正面|腓4:3|腓立比与保罗同劳的同工。
宁法|Nympha|新约时代|女性|正面|西4:15|在家里设立教会的姊妹。
亚腓亚|Apphia|新约时代|女性|正面|门2|腓利门书所问安的姊妹。
耶数（犹士都）|Jesus Justus|新约时代|其他|正面|西4:11|保罗的犹太同工。
革勒士|Crescens|新约时代|其他|混合|提后4:10|去了加拉太的同工。
加布|Carpus|新约时代|其他|混合|提后4:13|保罗把外衣存放在他家的人。
亚历山大（铜匠）|Alexander the coppersmith|新约时代|其他|警戒|提后4:14|多多敌对保罗的铜匠。
亚历山大（以弗所人）|Alexander|新约时代|其他|混合|徒19:33|以弗所暴乱中被推出来的犹太人。
腓吉路|Phygelus|新约时代|其他|警戒|提后1:15|在亚细亚离弃保罗的人。
黑摩其尼|Hermogenes|新约时代|其他|警戒|提后1:15|与腓吉路一同离弃保罗的人。
罗以|Lois|新约时代|女性|正面|提后1:5|提摩太的外祖母，有真实信心。
友尼基|Eunice|新约时代|女性|正面|提后1:5;徒16:1|提摩太的母亲，敬虔的犹太信徒。
亚居拉|Aquila|新约时代|其他|正面|徒18;罗16:3|百基拉的丈夫，制造帐棚的同工。
百基拉|Priscilla|新约时代|女性|正面|徒18;罗16:3|亚居拉的妻子，教导亚波罗的同工。
亚拿尼亚（撒非喇之夫）|Ananias|新约时代|其他|警戒|徒5:1-6|与妻子撒非喇同谋欺哄圣灵而死。
撒非喇|Sapphira|新约时代|女性|警戒|徒5:1-10|亚拿尼亚之妻，同谋欺哄圣灵。
丢特腓|Diotrephes|新约时代|其他|警戒|约三9-10|好作首领、不接待弟兄的人。
低米丢|Demetrius (3 John)|新约时代|其他|正面|约三12|众人给他作美好见证的人。
米迦勒|Michael|新约时代|其他|正面|但10;犹9;启12|天使长，与龙争战。
尼哥拉党人|Nicolaitans|新约时代|其他|警戒|启2:6,15|主所恨恶的异端群体。
耶洗别（推雅推喇）|Jezebel of Thyatira|新约时代|女性|警戒|启2:20|推雅推喇教会中自称先知、诱惑人的妇人。
龙|The Dragon|新约时代|其他|警戒|启12|大红龙，就是古蛇魔鬼，敌对神和教会。
兽|The Beast|新约时代|其他|警戒|启13|从海中上来、敌对神、亵渎神的兽。
假先知（启示录）|The False Prophet|新约时代|其他|警戒|启16:13;19:20|与兽一同迷惑世人的假先知。
大淫妇巴比伦|Babylon the Great|新约时代|女性|警戒|启17-18|象征敌对神之城邦的大淫妇。
两个见证人|Two Witnesses|新约时代|其他|正面|启11|穿毛衣传道、被杀又复活的两位见证人。
$people$, E'\n')
), parsed AS (
    SELECT string_to_array(line,'|') AS parts FROM raw WHERE line <> ''
), person AS (
    SELECT parts[1] AS name, parts[2] AS name_en, parts[3] AS era, parts[4] AS role,
           parts[5] AS character_type, parts[6] AS scripture_ref, parts[7] AS summary
    FROM parsed
)
INSERT INTO biblical_characters
    (name, name_en, era, role, character_type, lesson, summary, witness, scripture_ref, prayer, is_active, sort_order)
SELECT p.name, p.name_en, p.era, p.role, p.character_type,
       p.name || '在圣经救赎历史中的位置与见证。', p.summary, p.summary, p.scripture_ref,
       '愿我从' || p.name || '的记载中认识神在历史与群体中的作为。', true, 6400
FROM person p
WHERE NOT EXISTS (SELECT 1 FROM biblical_characters c WHERE c.name = p.name);

-- ============================================================
-- PART B. Create graph nodes for any active non-教会时代 character lacking one
-- ============================================================
INSERT INTO biblical_graph_nodes (
    id, node_type, name, name_en, category, description, character_id,
    chinese_name, english_name, aliases, testament, era, role_labels,
    importance_level, first_appearance, related_books, key_events,
    theological_themes, moral_evaluation, summary
)
SELECT
    'char-' || c.id, 'character', c.name, c.name_en, c.role, c.summary, c.id,
    c.name, c.name_en, ARRAY_REMOVE(ARRAY[c.name, c.name_en], NULL),
    CASE WHEN c.era ILIKE '%新约%' THEN 'New Testament'
         WHEN c.era ILIKE '%两约%' THEN 'Intertestamental'
         ELSE 'Old Testament' END,
    c.era, ARRAY_REMOVE(ARRAY[c.role], NULL), 'C', c.scripture_ref,
    ARRAY_REMOVE(ARRAY[c.scripture_ref], NULL), ARRAY_REMOVE(ARRAY[c.lesson], NULL),
    ARRAY_REMOVE(ARRAY[c.role, c.character_type], NULL),
    CASE c.character_type WHEN '正面' THEN 'positive' WHEN '警戒' THEN 'negative' ELSE 'mixed' END,
    c.summary
FROM biblical_characters c
WHERE c.is_active = true AND c.era <> '教会时代'
  AND NOT EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.character_id = c.id)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- PART B2. Enrichment: gender, S/A/B importance tiering, aliases
-- ============================================================
UPDATE biblical_graph_nodes n SET gender='female'
FROM biblical_characters c
WHERE n.character_id=c.id AND c.role='女性' AND (n.gender IS NULL OR n.gender='');
UPDATE biblical_graph_nodes n SET gender='male'
FROM biblical_characters c
WHERE n.character_id=c.id AND c.role IN ('族长','君王','祭司','使徒') AND (n.gender IS NULL OR n.gender='');
UPDATE biblical_graph_nodes n SET importance_level='S'
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name IN ('亚当','挪亚','亚伯拉罕','以撒','雅各','约瑟','摩西','约书亚','撒母耳','大卫','所罗门','以利亚','以利沙','以赛亚','耶利米','但以理','以斯拉','尼希米','施洗约翰','马利亚','耶稣','彼得','约翰','保罗');
UPDATE biblical_graph_nodes n SET importance_level='A'
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name IN ('亚伦','米利暗','底波拉','基甸','参孙','扫罗','约拿单','拿单','以斯帖','末底改','尼布甲尼撒','古列','巴拿巴','提摩太','提多','西拉','路加','马可','腓力','司提反','押沙龙','约押','耶西','希西家','约西亚','耶罗波安','罗波安','何西阿','约拿（先知）','加百列','押尼珥','以利','希律大帝','西庇太','亚波罗','百基拉','亚居拉','西缅（雅各之子）','利未（雅各之子）');
UPDATE biblical_graph_nodes n SET importance_level='B'
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name IN ('耶斯列（何西阿之子）','歌篾','瓦实提','哈曼','西拿基立','哈薛','大利拉','米甲','暗嫩','亚多尼雅','亚玛撒','基大利','希勒家','沙番','巴录','以巴弗','亚利马太的约瑟','迦玛列','希律安提帕','希律亚基帕一世','士求保罗','埃提阿伯太监','亚迦布','所提尼','友尼基','罗以','拉伯沙基','示撒','希兰','哈达','耶宾（士师时代）','西西拉','以利加拿','亚希米勒','设巴萨','马利亚（马可的母亲）','西庇太','龙','兽','大淫妇巴比伦');
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['亚撒利雅']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='乌西雅';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['加略人犹大']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='犹大';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['流珥']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='叶忒罗';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['耶书亚','约书亚（大祭司）']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='约书亚大祭司';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['巴耶稣']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='以吕马';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['约设巴设']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='雅朔班';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['迦南妇人']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='叙利腓尼基妇人';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['提庇留凯撒']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='提庇留';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['迦施慕']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='基善';
UPDATE biblical_graph_nodes n SET aliases = (
    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}') || ARRAY['亚拿尼亚']::text[]))
)
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name='亚拿尼亚（撒非喇之夫）';

-- ============================================================
-- PART C. Typed edges (the 12 subgraphs). 
-- src_kind|src_ref|tgt_kind|tgt_ref|rel|cat|label|scripture|desc|weight
-- character refs resolve by name; unmatched rows are skipped.
-- ============================================================
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($edges$
character|亚伯拉罕|character|米甸|FATHER_OF|family|父亲|创25:2|亚伯拉罕与基土拉生米甸。|2.4
character|基土拉|character|米甸|MOTHER_OF|family|母亲|创25:2|基土拉是米甸的母亲。|2.0
character|亚伯拉罕|character|基土拉|SPOUSE_OF|family|丈夫/妻子|创25:1|基土拉是亚伯拉罕的后妻。|2.2
character|米甸|nation|midian|ANCESTOR_OF|family|祖先|创25:2|米甸是米甸族的祖先。|2.0
character|犹大|character|谢拉（犹大之子）|FATHER_OF|family|父亲|创38:30|犹大与他玛生谢拉。|2.2
character|他玛|character|谢拉（犹大之子）|MOTHER_OF|family|母亲|创38:30|他玛是谢拉的母亲。|2.0
character|犹大|character|法勒斯|FATHER_OF|family|父亲|创38:29|犹大与他玛生法勒斯。|2.6
character|他玛|character|法勒斯|MOTHER_OF|family|母亲|创38:29|他玛是法勒斯的母亲，进入基督家谱。|2.4
character|谢拉（犹大之子）|character|法勒斯|SIBLING_OF|family|兄弟|创38:27-30|法勒斯与谢拉是双胞胎。|1.8
character|拉班|character|利百加|SIBLING_OF|family|兄妹|创24:29|拉班是利百加的哥哥。|2.2
character|拉班|character|利亚|FATHER_OF|family|父亲|创29:16|拉班是利亚的父亲。|2.2
character|拉班|character|拉结|FATHER_OF|family|父亲|创29:16|拉班是拉结的父亲。|2.2
character|雅各|character|拉班|SERVANT_OF|spiritual|作工于|创29-31|雅各为拉班牧羊二十年。|1.8
character|雅各|character|辟拉|SPOUSE_OF|family|丈夫/妻子|创30:4|辟拉作雅各的妾。|1.8
character|雅各|character|悉帕|SPOUSE_OF|family|丈夫/妻子|创30:9|悉帕作雅各的妾。|1.8
character|拉结|character|辟拉|SERVANT_OF|spiritual|使女|创30:3|辟拉是拉结的使女。|1.6
character|利亚|character|悉帕|SERVANT_OF|spiritual|使女|创30:9|悉帕是利亚的使女。|1.6
character|辟拉|character|但（雅各之子）|MOTHER_OF|family|母亲|创30:5-6|辟拉生但。|1.8
character|辟拉|character|拿弗他利（雅各之子）|MOTHER_OF|family|母亲|创30:7-8|辟拉生拿弗他利。|1.8
character|悉帕|character|迦得（雅各之子）|MOTHER_OF|family|母亲|创30:10-11|悉帕生迦得。|1.8
character|悉帕|character|亚设（雅各之子）|MOTHER_OF|family|母亲|创30:12-13|悉帕生亚设。|1.8
character|雅各|character|底拿|FATHER_OF|family|父亲|创30:21|雅各与利亚生底拿。|2.0
character|利亚|character|底拿|MOTHER_OF|family|母亲|创30:21|利亚是底拿的母亲。|1.8
character|哈抹|character|示剑|FATHER_OF|family|父亲|创34:2|哈抹是示剑的父亲。|1.8
character|示剑|character|底拿|OPPOSED|event|玷辱|创34:2|示剑玷辱底拿。|1.8
character|西缅（雅各之子）|character|示剑|KILLED|event|杀害|创34:25|西缅为底拿报仇杀示剑。|1.8
character|利未（雅各之子）|character|哈抹|KILLED|event|杀害|创34:25|利未为底拿报仇杀哈抹。|1.8
character|雅各|character|西缅（雅各之子）|FATHER_OF|family|父亲|创29:33|雅各与利亚生西缅。|2.0
character|雅各|character|利未（雅各之子）|FATHER_OF|family|父亲|创29:34|雅各与利亚生利未。|2.2
character|西缅（雅各之子）|character|利未（雅各之子）|SIBLING_OF|family|兄弟|创34:25|西缅与利未同心报仇。|1.8
character|利未（雅各之子）|character|暗兰|ANCESTOR_OF|family|祖先|出6:16-20|利未是暗兰、亚伦、摩西的祖先。|1.8
character|提幔人以利法|character|约伯|FRIEND_OF|family|辩友|伯4:1|以利法是约伯的友人。|1.8
character|书亚人比勒达|character|约伯|FRIEND_OF|family|辩友|伯8:1|比勒达是约伯的友人。|1.8
character|拿玛人琐法|character|约伯|FRIEND_OF|family|辩友|伯11:1|琐法是约伯的友人。|1.8
character|暗兰|character|摩西|FATHER_OF|family|父亲|出6:20|暗兰是摩西的父亲。|2.6
character|暗兰|character|亚伦|FATHER_OF|family|父亲|出6:20|暗兰是亚伦的父亲。|2.4
character|暗兰|character|米利暗|FATHER_OF|family|父亲|民26:59|暗兰是米利暗的父亲。|2.2
character|约基别|character|摩西|MOTHER_OF|family|母亲|出6:20|约基别是摩西的母亲。|2.2
character|法老的女儿|character|摩西|PROTECTED|event|收养|出2:5-10|法老女儿救起并收养摩西。|2.2
character|摩西|character|西坡拉|SPOUSE_OF|family|丈夫/妻子|出2:21|西坡拉是摩西的妻子。|2.0
character|叶忒罗|character|西坡拉|FATHER_OF|family|父亲|出2:21|叶忒罗是西坡拉的父亲。|2.0
character|叶忒罗|character|摩西|ASSOCIATED_WITH|event|献策|出18:13-26|叶忒罗教摩西设立官长分层治理。|2.0
character|叶忒罗|nation|midian|PRIEST_OF|spiritual|祭司|出3:1|叶忒罗是米甸的祭司。|1.8
character|摩西|character|革舜|FATHER_OF|family|父亲|出2:22|摩西生革舜。|2.0
character|摩西|character|以利以谢（摩西之子）|FATHER_OF|family|父亲|出18:4|摩西生以利以谢。|2.0
character|亚伦|character|拿答|FATHER_OF|family|父亲|出6:23|亚伦的长子拿答。|2.0
character|亚伦|character|亚比户|FATHER_OF|family|父亲|出6:23|亚伦的次子亚比户。|2.0
character|亚伦|character|以利亚撒（亚伦之子）|FATHER_OF|family|父亲|出6:23|亚伦之子以利亚撒，继任大祭司。|2.4
character|亚伦|character|以他玛|FATHER_OF|family|父亲|出6:23|亚伦之子以他玛。|2.0
character|以利亚撒（亚伦之子）|character|非尼哈|FATHER_OF|family|父亲|出6:25|以利亚撒生非尼哈。|2.2
character|以利亚撒（亚伦之子）|group|priesthood|PRIEST_OF|spiritual|大祭司|民20:28|以利亚撒承接大祭司职分。|2.0
character|亚比户|character|拿答|SIBLING_OF|family|兄弟|利10:1|拿答与亚比户一同献凡火。|1.6
character|可拉|character|昂|ALLIED_WITH|political|同党|民16:1|昂与可拉一同起来反叛。|1.6
character|昂|event|wilderness-rebellion|PARTICIPATED_IN|event|参与|民16|昂参与可拉的叛乱。|1.6
character|巴勒|nation|moab|KING_OF|spiritual|君王|民22:4|巴勒是摩押王。|2.0
character|巴勒|character|巴兰|ASSOCIATED_WITH|event|雇用|民22:5-7|巴勒雇巴兰咒诅以色列。|2.0
character|巴勒|event|wilderness-rebellion|PARTICIPATED_IN|event|参与|民22-24|巴勒企图咒诅以色列。|1.8
character|西罗非哈|character|玛拉（西罗非哈之女）|FATHER_OF|family|父亲|民27:1|西罗非哈的女儿玛拉。|1.8
character|西罗非哈|character|挪阿|FATHER_OF|family|父亲|民27:1|西罗非哈的女儿挪阿。|1.8
character|西罗非哈|character|曷拉|FATHER_OF|family|父亲|民27:1|西罗非哈的女儿曷拉。|1.8
character|西罗非哈|character|密迦（西罗非哈之女）|FATHER_OF|family|父亲|民27:1|西罗非哈的女儿密迦。|1.8
character|西罗非哈|character|得撒|FATHER_OF|family|父亲|民27:1|西罗非哈的女儿得撒。|1.8
character|撒底|character|迦米|FATHER_OF|family|父亲|书7:1|撒底是迦米的父亲。|1.8
character|迦米|character|亚干|FATHER_OF|family|父亲|书7:1|迦米是亚干的父亲。|1.8
character|谢拉（犹大之子）|character|亚干|ANCESTOR_OF|family|祖先|书7:1|亚干属犹大谢拉的支系。|1.6
character|亚干|event|conquest-canaan|CAUSED_FAILURE_IN|event|连累失败|书7|亚干私取当灭之物，使以色列在艾城战败。|2.0
character|约书亚|character|亚干|OPPOSED|event|治罪|书7:25|约书亚按神命处置亚干。|1.6
character|迦勒|character|押撒|FATHER_OF|family|父亲|书15:16|迦勒是押撒的父亲。|2.0
character|押撒|character|俄陀聂|SPOUSE_OF|family|丈夫/妻子|书15:17|押撒嫁给俄陀聂。|1.8
character|约书亚|character|亚多尼洗德|DEFEATED|political|击败|书10|约书亚击败耶路撒冷王联盟。|2.0
character|约书亚|character|耶宾（夏琐王）|DEFEATED|political|击败|书11|约书亚击败夏琐王耶宾的北方联盟。|2.0
character|亚多尼洗德|character|何咸|ALLIED_WITH|political|结盟|书10:3|南方五王联盟。|1.6
character|亚多尼洗德|character|毗兰|ALLIED_WITH|political|结盟|书10:3|南方五王联盟。|1.6
character|亚多尼洗德|character|雅非亚|ALLIED_WITH|political|结盟|书10:3|南方五王联盟。|1.6
character|亚多尼洗德|character|底璧王|ALLIED_WITH|political|结盟|书10:3|南方五王联盟。|1.6
character|亚多尼洗德|event|conquest-canaan|PARTICIPATED_IN|event|参与|书10|耶路撒冷王对抗以色列。|1.6
character|耶宾（夏琐王）|event|conquest-canaan|PARTICIPATED_IN|event|参与|书11|夏琐王对抗以色列。|1.6
character|基遍人长老|character|约书亚|ASSOCIATED_WITH|event|用诡计立约|书9|基遍人用诡计与以色列立约。|1.8
character|基遍人长老|event|conquest-canaan|PARTICIPATED_IN|event|参与|书9|基遍人在征服迦南时立约求存。|1.6
character|耶宾（士师时代）|character|西西拉|COMMANDER_OF|political|元帅|士4:2|西西拉是耶宾的元帅。|1.8
character|西西拉|character|耶宾（士师时代）|SERVANT_OF|spiritual|元帅|士4:2|西西拉作夏琐王的军长。|1.6
character|雅亿|character|西西拉|KILLED|event|杀害|士4:21|雅亿用帐棚橛子钉死西西拉。|2.0
character|底波拉|character|西西拉|DEFEATED|political|击败|士4|底波拉与巴拉击败西西拉。|2.0
character|巴拉|character|西西拉|DEFEATED|political|击败|士4|巴拉率军击败西西拉。|1.8
character|耶宾（士师时代）|group|israelites|ATTACKED|political|压迫|士4:3|耶宾压迫以色列二十年。|1.6
character|以笏|character|伊矶伦|KILLED|event|刺杀|士3:21|以笏刺杀摩押王伊矶伦。|2.0
character|伊矶伦|nation|moab|KING_OF|spiritual|君王|士3:12|伊矶伦是摩押王。|1.8
character|伊矶伦|group|israelites|ATTACKED|political|压迫|士3:14|伊矶伦辖制以色列十八年。|1.6
character|基甸|character|西巴（米甸王）|KILLED|event|击杀|士8:21|基甸击杀米甸王西巴。|1.8
character|基甸|character|撒慕拿|KILLED|event|击杀|士8:21|基甸击杀米甸王撒慕拿。|1.8
character|基甸|character|俄立|DEFEATED|political|击败|士7:25|基甸的军队擒杀俄立。|1.6
character|基甸|character|西伊伯|DEFEATED|political|击败|士7:25|基甸的军队擒杀西伊伯。|1.6
character|西巴（米甸王）|character|撒慕拿|ALLIED_WITH|political|结盟|士8:5|西巴与撒慕拿同为米甸王。|1.6
character|西巴（米甸王）|nation|midian|KING_OF|spiritual|君王|士8:5|西巴是米甸王。|1.6
character|撒慕拿|nation|midian|KING_OF|spiritual|君王|士8:5|撒慕拿是米甸王。|1.6
character|俄立|character|西伊伯|ALLIED_WITH|political|同党|士7:25|俄立与西伊伯同为米甸首领。|1.4
character|玛挪亚|character|参孙|FATHER_OF|family|父亲|士13:24|玛挪亚是参孙的父亲。|2.0
character|玛挪亚的妻子|character|参孙|MOTHER_OF|family|母亲|士13:24|玛挪亚的妻子是参孙的母亲。|2.0
character|玛挪亚|character|玛挪亚的妻子|SPOUSE_OF|family|丈夫/妻子|士13|玛挪亚夫妇。|1.6
character|参孙|character|参孙的非利士妻|SPOUSE_OF|family|丈夫/妻子|士14|参孙娶亭拿的非利士女子。|1.8
character|大利拉|character|参孙|BETRAYED|political|出卖|士16|大利拉出卖参孙。|2.2
character|大利拉|nation|philistia|ALLIED_WITH|political|受贿|士16:5|大利拉受非利士首领收买。|1.6
character|参孙|nation|philistia|OPPOSED|event|争战|士14-16|参孙与非利士人争战。|1.8
character|参孙的非利士妻|place|timnah|LIVED_IN|location|居住|士14:1|亭拿的女子。|1.4
character|耶弗他|character|耶弗他的女儿|FATHER_OF|family|父亲|士11:34|耶弗他的独生女。|2.0
character|耶弗他的女儿|event|judges-cycle|PARTICIPATED_IN|event|参与|士11|因父亲许愿被献上。|1.6
character|以利加拿|character|哈拿|SPOUSE_OF|family|丈夫/妻子|撒上1:2|以利加拿与哈拿。|1.8
character|以利加拿|character|毗尼拿|SPOUSE_OF|family|丈夫/妻子|撒上1:2|以利加拿的另一妻子毗尼拿。|1.6
character|毗尼拿|character|哈拿|OPPOSED|event|激动|撒上1:6|毗尼拿常激动哈拿。|1.6
character|以利加拿|character|撒母耳|FATHER_OF|family|父亲|撒上1:20|以利加拿是撒母耳的父亲。|2.2
character|哈拿|character|撒母耳|MOTHER_OF|family|母亲|撒上1:20|哈拿祈求得撒母耳并献给神。|2.4
character|以利|character|何弗尼|FATHER_OF|family|父亲|撒上1:3|以利的儿子何弗尼。|1.8
character|以利|character|非尼哈（以利之子）|FATHER_OF|family|父亲|撒上1:3|以利的儿子非尼哈。|1.8
character|何弗尼|character|非尼哈（以利之子）|SIBLING_OF|family|兄弟|撒上2:34|何弗尼与非尼哈同日而死。|1.6
character|非尼哈（以利之子）|character|以迦博|FATHER_OF|family|父亲|撒上4:21|非尼哈的儿子以迦博。|1.6
character|基士|character|扫罗|FATHER_OF|family|父亲|撒上9:1-2|基士是扫罗的父亲。|2.2
character|撒母耳|character|扫罗|ANOINTED|spiritual|膏立|撒上10:1|撒母耳膏扫罗为王。|2.4
character|撒母耳|character|大卫|ANOINTED|spiritual|膏立|撒上16:13|撒母耳膏大卫为王。|2.6
character|扫罗|character|约拿单|FATHER_OF|family|父亲|撒上13:16|扫罗的儿子约拿单。|2.2
character|扫罗|character|亚比拿达（扫罗之子）|FATHER_OF|family|父亲|撒上31:2|扫罗之子亚比拿达。|1.8
character|扫罗|character|麦基舒亚|FATHER_OF|family|父亲|撒上31:2|扫罗之子麦基舒亚。|1.8
character|扫罗|character|伊施波设|FATHER_OF|family|父亲|撒下2:8|扫罗之子伊施波设。|2.0
character|扫罗|character|米甲|FATHER_OF|family|父亲|撒上18:20|扫罗的女儿米甲。|2.0
character|米甲|character|大卫|SPOUSE_OF|family|丈夫/妻子|撒上18:27|米甲嫁给大卫。|2.0
character|扫罗|place|gibeah|LIVED_IN|location|居住|撒上11:4|扫罗的王都在基比亚。|1.6
character|扫罗|place|endor|TRAVELED_TO|location|前往|撒上28:7|扫罗往隐多珥求问交鬼妇人。|1.6
character|押尼珥|character|扫罗|COMMANDER_OF|political|元帅|撒上14:50|押尼珥是扫罗的元帅。|2.0
character|押尼珥|character|伊施波设|ALLIED_WITH|political|拥立|撒下2:8-9|押尼珥立伊施波设为王。|1.8
character|约押|character|押尼珥|KILLED|event|杀害|撒下3:27|约押在希伯仑杀押尼珥。|2.0
character|押尼珥|character|亚撒黑|KILLED|event|杀害|撒下2:23|押尼珥在战阵中杀亚撒黑。|1.8
character|伊施波设|group|israelites|RULED_OVER|political|作王|撒下2:9|伊施波设短暂作以色列王。|1.6
character|伊施波设|place|mahanaim|LIVED_IN|location|居住|撒下2:8|伊施波设在玛哈念作王。|1.4
character|亚希米勒|character|大卫|PROTECTED|event|帮助|撒上21|亚希米勒供应大卫食物和刀。|1.8
character|多益|character|亚希米勒|KILLED|event|杀害|撒上22:18|多益奉扫罗命杀挪伯祭司。|1.8
character|多益|character|扫罗|SERVANT_OF|spiritual|臣仆|撒上22:9|多益是扫罗的司牧长。|1.4
character|多益|nation|edom|MEMBER_OF|other|以东人|撒上22:9|多益是以东人。|1.2
character|大卫|character|歌利亚|KILLED|event|击杀|撒上17:50|大卫用机弦击杀歌利亚。|2.4
character|歌利亚|nation|philistia|MEMBER_OF|other|非利士人|撒上17:4|歌利亚是非利士的勇士。|1.6
character|耶西|character|大卫|FATHER_OF|family|父亲|撒上16:11|耶西是大卫的父亲。|2.6
character|耶西|character|以利押|FATHER_OF|family|父亲|撒上16:6|耶西的长子以利押。|1.8
character|耶西|character|亚比拿达（大卫之兄）|FATHER_OF|family|父亲|撒上16:8|耶西的次子亚比拿达。|1.6
character|耶西|character|沙玛（大卫之兄）|FATHER_OF|family|父亲|撒上16:9|耶西的三子沙玛。|1.6
character|耶西|character|洗鲁雅|FATHER_OF|family|父亲|代上2:16|洗鲁雅是耶西的女儿。|1.6
character|耶西|place|bethlehem|LIVED_IN|location|居住|撒上16:1|耶西是伯利恒人。|1.6
character|洗鲁雅|character|约押|MOTHER_OF|family|母亲|代上2:16|洗鲁雅是约押的母亲。|1.8
character|洗鲁雅|character|亚比筛|MOTHER_OF|family|母亲|代上2:16|洗鲁雅是亚比筛的母亲。|1.6
character|洗鲁雅|character|亚撒黑|MOTHER_OF|family|母亲|代上2:16|洗鲁雅是亚撒黑的母亲。|1.6
character|洗鲁雅|character|大卫|SIBLING_OF|family|姊弟|代上2:16|洗鲁雅是大卫的姊妹。|1.8
character|约押|character|亚比筛|SIBLING_OF|family|兄弟|撒下2:18|约押与亚比筛是兄弟。|1.6
character|约押|character|亚撒黑|SIBLING_OF|family|兄弟|撒下2:18|亚撒黑是约押的兄弟。|1.6
character|大卫|character|暗嫩|FATHER_OF|family|父亲|撒下3:2|大卫的长子暗嫩。|2.0
character|大卫|character|押沙龙|FATHER_OF|family|父亲|撒下3:3|大卫的儿子押沙龙。|2.4
character|大卫|character|所罗门|FATHER_OF|family|父亲|撒下12:24|大卫与拔示巴生所罗门。|2.6
character|大卫|character|他玛（大卫之女）|FATHER_OF|family|父亲|撒下13:1|大卫的女儿他玛。|2.0
character|大卫|character|亚多尼雅|FATHER_OF|family|父亲|撒下3:4|大卫的儿子亚多尼雅。|1.8
character|大卫|character|基利押|FATHER_OF|family|父亲|撒下3:3|大卫与亚比该生基利押。|1.6
character|暗嫩|character|他玛（大卫之女）|OPPOSED|event|玷辱|撒下13:14|暗嫩玷辱同父异母的妹妹他玛。|2.0
character|押沙龙|character|暗嫩|KILLED|event|杀害|撒下13:28|押沙龙为他玛报仇杀暗嫩。|2.0
character|押沙龙|character|他玛（大卫之女）|SIBLING_OF|family|兄妹|撒下13:1|押沙龙是他玛的同胞哥哥。|1.8
character|押沙龙|character|暗嫩|SIBLING_OF|family|兄弟|撒下13|押沙龙与暗嫩是同父兄弟。|1.6
character|押沙龙|character|大卫|REBELLED_AGAINST|political|背叛|撒下15|押沙龙起兵背叛父亲大卫。|2.2
character|押沙龙|place|geshur|TRAVELED_TO|location|逃往|撒下13:38|押沙龙杀暗嫩后逃往基述。|1.6
character|约押|character|押沙龙|KILLED|event|杀害|撒下18:14|约押用枪刺透押沙龙。|2.0
character|亚玛撒|character|押沙龙|COMMANDER_OF|political|元帅|撒下17:25|亚玛撒作押沙龙的元帅。|1.6
character|约押|character|亚玛撒|KILLED|event|杀害|撒下20:10|约押假意问安刺杀亚玛撒。|1.8
character|亚多尼雅|character|所罗门|OPPOSED|political|争位|王上1:5|亚多尼雅自立、争夺王位。|1.8
character|所罗门|character|亚多尼雅|KILLED|event|处死|王上2:25|所罗门处死亚多尼雅。|1.6
character|约拿单|character|大卫|FRIEND_OF|family|至友|撒上18:1|约拿单与大卫情谊深厚。|2.2
character|户筛|character|大卫|FRIEND_OF|family|朋友|撒下15:37|户筛是大卫的朋友。|1.8
character|户筛|event|absalom-rebellion|PARTICIPATED_IN|event|参与|撒下17|户筛破坏亚希多弗的计谋。|1.8
character|户筛|character|亚希多弗|OPPOSED|political|对抗|撒下17:14|户筛破坏亚希多弗的计谋。|1.6
character|巴西莱|character|大卫|PROTECTED|event|供应|撒下17:27|巴西莱在玛哈念供应大卫。|1.6
character|示每|character|大卫|OPPOSED|event|咒骂|撒下16:5|示每咒骂逃难的大卫。|1.6
character|洗巴|character|米非波设|SERVANT_OF|spiritual|仆人|撒下9:2|洗巴是扫罗家的仆人。|1.4
character|洗巴|character|约拿单的儿子米非波设|SERVANT_OF|spiritual|仆人|撒下9:9-10|洗巴服事米非波设。|1.4
character|雅朔班|character|大卫|SERVANT_OF|spiritual|勇士|代上11:11|雅朔班是大卫勇士之首。|1.6
character|以利亚撒（大卫勇士）|character|大卫|SERVANT_OF|spiritual|勇士|撒下23:9|三勇士之一。|1.6
character|沙玛（大卫勇士）|character|大卫|SERVANT_OF|spiritual|勇士|撒下23:11|三勇士之一，独守豆田。|1.6
character|亚比筛|character|大卫|SERVANT_OF|spiritual|勇士|撒下21:17|亚比筛救护大卫。|1.6
character|大卫|place|bethlehem|BORN_IN|location|出生|撒上16:1|大卫生于伯利恒。|2.0
character|大卫|place|hebron|LIVED_IN|location|作王|撒下2:11|大卫先在希伯仑作王七年半。|1.8
character|大卫|place|jerusalem|LIVED_IN|location|建都|撒下5:6-9|大卫攻取耶路撒冷为京。|2.0
character|大卫|place|en-gedi|TRAVELED_TO|location|逃避|撒上24|大卫在隐基底躲避扫罗。|1.6
character|大卫|place|ziklag|LIVED_IN|location|寄居|撒上27:6|大卫寄居洗革拉。|1.6
character|大卫|event|bathsheba-incident|PARTICIPATED_IN|event|跌倒|撒下11|大卫与拔示巴犯罪。|2.0
character|大卫|event|ark-to-jerusalem|LED|event|迎约柜|撒下6|大卫将约柜迎入耶路撒冷。|1.8
character|大卫|theme|davidic-covenant|HAS_THEME|other|主题|撒下7|神与大卫立永远的约。|2.2
character|大卫|theme|repentance|HAS_THEME|other|主题|诗51|大卫犯罪后真诚悔改。|2.0
character|大卫|theme|worship|HAS_THEME|other|主题|诗篇|大卫是合神心意的敬拜者。|2.0
character|大卫|theme|messianic-line|HAS_THEME|other|主题|太1:1|大卫是弥赛亚谱系的关键。|2.2
character|大卫|theme|christ-typology|TYPOLOGY_OF_CHRIST|other|预表基督|路1:32|大卫预表受膏的牧者君王基督。|2.2
character|大卫|book|samuel|APPEARS_IN|other|记载于|撒上16-撒下24|大卫的事迹记于撒母耳记。|1.6
character|大卫|book|psalms|APPEARS_IN|other|记载于|诗篇|大卫作了许多诗篇。|1.8
character|大卫|book|chronicles|APPEARS_IN|other|记载于|代上11-29|历代志重述大卫的统治。|1.4
character|希兰|nation|tyre|KING_OF|spiritual|君王|王上5:1|希兰是推罗王。|1.8
character|希兰|character|所罗门|ALLIED_WITH|political|结盟|王上5:12|希兰供应所罗门建殿的材料。|1.8
character|希兰|event|solomon-officials|PARTICIPATED_IN|event|参与|王上5|推罗王协助建殿工程。|1.4
character|哈达|character|所罗门|OPPOSED|political|敌对|王上11:14|哈达是所罗门的敌人。|1.6
character|哈达|nation|edom|MEMBER_OF|other|以东王室|王上11:14|哈达出自以东王室。|1.4
character|利逊|character|所罗门|OPPOSED|political|敌对|王上11:23|利逊是所罗门的敌人。|1.6
character|利逊|place|damascus|LIVED_IN|location|据守|王上11:24|利逊据守大马士革。|1.4
character|利逊|nation|aram-damascus|MEMBER_OF|other|亚兰人|王上11:23|利逊建立大马士革政权。|1.4
character|尼八|character|耶罗波安|FATHER_OF|family|父亲|王上11:26|尼八是耶罗波安的父亲。|1.8
character|洗鲁阿|character|耶罗波安|MOTHER_OF|family|母亲|王上11:26|洗鲁阿是耶罗波安的母亲。|1.6
character|所罗门的外邦妃嫔|character|所罗门|SPOUSE_OF|family|妃嫔|王上11:1|外邦妃嫔成为所罗门的妻妾。|1.6
character|所罗门的外邦妃嫔|character|所罗门|CAUSED|event|使心偏离|王上11:4|外邦妃嫔使所罗门的心偏离耶和华。|1.8
character|示撒|place|egypt|RULED_OVER|political|作王|王上14:25|示撒是埃及王。|1.6
character|示撒|character|罗波安|ATTACKED|political|攻打|王上14:25|示撒攻打耶路撒冷，夺走圣殿宝物。|1.8
character|示撒|event|kingdom-split|PARTICIPATED_IN|event|参与|王上14|埃及王示撒在分裂初期入侵。|1.4
character|耶罗波安|character|罗波安|REBELLED_AGAINST|political|分裂|王上12|耶罗波安率十支派脱离罗波安。|2.0
character|耶罗波安|nation|northern-israel|KING_OF|spiritual|君王|王上12:20|耶罗波安作北国第一王。|2.0
character|罗波安|nation|southern-judah|KING_OF|spiritual|君王|王上12:17|罗波安作南国犹大王。|2.0
character|巴沙|nation|northern-israel|KING_OF|spiritual|君王|王上15:33|巴沙作北国王。|1.6
character|巴沙|character|以拉（以色列王）|FATHER_OF|family|父亲|王上16:6|以拉是巴沙之子。|1.6
character|心利|character|以拉（以色列王）|KILLED|event|弑君|王上16:10|心利弑以拉篡位。|1.6
character|心利|nation|northern-israel|KING_OF|spiritual|君王|王上16:15|心利作王仅七日。|1.4
character|提比尼|character|暗利|OPPOSED|political|争位|王上16:21|提比尼与暗利争夺王位。|1.4
character|耶罗波安二世|character|撒迦利雅（以色列王）|FATHER_OF|family|父亲|王下15:8|撒迦利雅是耶罗波安二世之子。|1.6
character|沙龙（以色列王）|character|撒迦利雅（以色列王）|KILLED|event|弑君|王下15:10|沙龙弑撒迦利雅。|1.6
character|米拿现|character|沙龙（以色列王）|KILLED|event|弑君|王下15:14|米拿现弑沙龙篡位。|1.6
character|米拿现|character|比加辖|FATHER_OF|family|父亲|王下15:22|比加辖是米拿现之子。|1.6
character|比加|character|比加辖|KILLED|event|弑君|王下15:25|比加弑比加辖篡位。|1.6
character|比加|character|利汛|ALLIED_WITH|political|结盟|王下16:5|比加与利汛联合攻打犹大。|1.6
character|何细亚|character|比加|KILLED|event|弑君|王下15:30|何细亚弑比加，成为末代北国王。|1.6
character|米拿现|nation|northern-israel|KING_OF|spiritual|君王|王下15:17|米拿现作北国王。|1.4
character|比加|nation|northern-israel|KING_OF|spiritual|君王|王下15:27|比加作北国王。|1.4
character|哈薛|nation|aram-damascus|KING_OF|spiritual|君王|王下8:15|哈薛作亚兰王。|1.8
character|便哈达|nation|aram-damascus|KING_OF|spiritual|君王|王上20:1|便哈达作亚兰王。|1.6
character|哈薛|character|便哈达|KILLED|event|弑君|王下8:15|哈薛闷死便哈达篡位。|1.8
character|利汛|nation|aram-damascus|KING_OF|spiritual|君王|王下16:6|利汛作亚兰王。|1.6
character|哈薛|group|israelites|ATTACKED|political|攻击|王下10:32|哈薛屡次攻击以色列。|1.4
character|以利亚|character|哈薛|ANOINTED|spiritual|预言膏立|王上19:15|以利亚奉命膏哈薛作亚兰王。|1.6
character|以利亚|event|elijah-elisha-ministry|PARTICIPATED_IN|event|事奉|王上17-19|以利亚的先知事奉。|1.8
character|以利沙|event|elijah-elisha-ministry|PARTICIPATED_IN|event|事奉|王下2-13|以利沙承接以利亚的事奉。|1.8
character|以利沙|character|哈薛|ASSOCIATED_WITH|event|预言兴起|王下8:13|以利沙预言哈薛必作王。|1.6
character|乃缦|event|elijah-elisha-ministry|PARTICIPATED_IN|event|得医治|王下5|乃缦在约旦河得洁净。|1.6
character|乃缦|nation|aram-damascus|COMMANDER_OF|political|元帅|王下5:1|乃缦是亚兰王的元帅。|1.6
character|基哈西|character|以利沙|SERVANT_OF|spiritual|仆人|王下5:20|基哈西是以利沙的仆人。|1.8
character|拿伯|event|naboth-vineyard|DIED_IN|event|被害|王上21|拿伯因葡萄园被陷害致死。|1.8
character|耶洗别|character|拿伯|KILLED|event|谋害|王上21:15|耶洗别设计陷害拿伯。|1.8
character|耶洗别|event|naboth-vineyard|CAUSED|event|主谋|王上21:7|耶洗别主谋夺取拿伯葡萄园。|1.8
character|亚哈|event|naboth-vineyard|PARTICIPATED_IN|event|得葡萄园|王上21:16|亚哈夺取拿伯的葡萄园。|1.6
character|拿伯|place|jezreel|LIVED_IN|location|居住|王上21:1|拿伯是耶斯列人。|1.4
character|耶户|character|耶洗别|KILLED|event|处死|王下9:33|耶户使耶洗别坠楼而死。|1.8
character|耶户|character|约兰|KILLED|event|射杀|王下9:24|耶户射杀约兰王。|1.6
character|俄巴底（亚哈家宰）|character|亚哈|SERVANT_OF|spiritual|家宰|王上18:3|俄巴底是亚哈的家宰。|1.6
character|俄巴底（亚哈家宰）|event|elijah-elisha-ministry|PROTECTED|event|藏匿先知|王上18:4|俄巴底藏匿一百位先知。|1.6
character|约拿达（利甲之子）|character|耶户|ALLIED_WITH|political|同行|王下10:15|约拿达与耶户同车除巴力。|1.6
character|利甲族人|character|约拿达（利甲之子）|DESCENDANT_OF|family|后裔|耶35:6|利甲族遵守先祖约拿达的吩咐。|1.6
character|西拿基立|nation|assyria-empire|KING_OF|spiritual|君王|王下18:13|西拿基立是亚述王。|2.0
character|提革拉毗列色|nation|assyria-empire|KING_OF|spiritual|君王|王下15:29|提革拉毗列色是亚述王。|1.8
character|撒缦以色|nation|assyria-empire|KING_OF|spiritual|君王|王下17:3|撒缦以色是亚述王。|1.6
character|撒珥根|nation|assyria-empire|KING_OF|spiritual|君王|赛20:1|撒珥根是亚述王。|1.6
character|以撒哈顿|nation|assyria-empire|KING_OF|spiritual|君王|王下19:37|以撒哈顿是亚述王。|1.6
character|西拿基立|character|以撒哈顿|FATHER_OF|family|父亲|王下19:37|以撒哈顿继西拿基立为王。|1.6
character|拉伯沙基|character|西拿基立|SERVANT_OF|spiritual|将领|王下18:17|拉伯沙基是西拿基立的将领。|1.6
character|拉伯沙基|event|assyrian-crisis|PARTICIPATED_IN|event|叫阵|王下18:19|拉伯沙基在城下羞辱神。|1.6
character|西拿基立|character|希西家|ATTACKED|political|围攻|王下18:13|西拿基立围攻犹大与耶路撒冷。|2.0
character|西拿基立|event|assyrian-crisis|INITIATED|event|发动|王下18-19|西拿基立围攻耶路撒冷。|1.8
character|希西家|event|assyrian-crisis|PARTICIPATED_IN|event|求告得救|王下19:14|希西家祷告，神拯救耶路撒冷。|2.0
character|以赛亚|character|希西家|PREACHED_TO|spiritual|传神谕|王下19:6|以赛亚向希西家传神的应许。|1.8
character|提革拉毗列色|nation|northern-israel|ATTACKED|political|掳掠|王下15:29|提革拉毗列色掳掠以色列北部。|1.6
character|撒缦以色|character|何细亚|ATTACKED|political|围困|王下17:3|撒缦以色围困何细亚。|1.4
character|撒缦以色|place|samaria|ATTACKED|location|围困|王下17:5|撒缦以色围困撒玛利亚。|1.4
character|米罗达巴拉但|nation|babylon-empire|KING_OF|spiritual|君王|赛39:1|米罗达巴拉但是巴比伦王。|1.6
character|米罗达巴拉但|character|希西家|ASSOCIATED_WITH|event|遣使|王下20:12|米罗达巴拉但派使者见希西家。|1.6
character|哈拿尼（先见）|character|亚撒|OPPOSED|event|责备|代下16:7|哈拿尼责备亚撒倚靠亚兰。|1.6
character|哈拿尼（先见）|character|耶户（哈拿尼之子）|FATHER_OF|family|父亲|王上16:1|哈拿尼是先知耶户的父亲。|1.6
character|耶户（哈拿尼之子）|character|约沙法|OPPOSED|event|责备|代下19:2|耶户责备约沙法与亚哈结盟。|1.6
character|亚撒利雅（俄德之子）|character|亚撒|PREACHED_TO|spiritual|劝勉|代下15:1|亚撒利雅劝勉亚撒推行改革。|1.6
character|撒迦利亚（耶何耶大之子）|character|约阿施|OPPOSED|event|责备|代下24:20|撒迦利亚责备约阿施离弃神。|1.6
character|约阿施|character|撒迦利亚（耶何耶大之子）|KILLED|event|杀害|代下24:21|约阿施下令用石头打死撒迦利亚。|1.8
character|耶何耶大|character|撒迦利亚（耶何耶大之子）|FATHER_OF|family|父亲|代下24:20|耶何耶大是撒迦利亚的父亲。|1.6
character|乌利亚祭司|character|亚哈斯|SERVANT_OF|spiritual|祭司|王下16:11|乌利亚照亚哈斯的吩咐筑坛。|1.4
character|希勒家|group|priesthood|PRIEST_OF|spiritual|大祭司|王下22:8|希勒家是约西亚时的大祭司。|1.6
character|希勒家|character|约西亚|ASSOCIATED_WITH|event|发现律法书|王下22:8|希勒家在殿中发现律法书。|1.8
character|沙番|character|约西亚|SERVANT_OF|spiritual|书记|王下22:3|沙番是约西亚的书记。|1.6
character|沙番|character|亚希甘|FATHER_OF|family|父亲|王下22:12|亚希甘是沙番之子。|1.6
character|亚希甘|character|耶利米|PROTECTED|event|保护|耶26:24|亚希甘保护耶利米免被处死。|1.8
character|利汛|character|亚哈斯|ATTACKED|political|攻打|王下16:5|利汛与比加攻打亚哈斯。|1.6
character|以赛亚|character|施亚雅述|FATHER_OF|family|父亲|赛7:3|以赛亚的儿子施亚雅述。|1.6
character|以赛亚|character|玛黑珥沙拉勒哈施罢斯|FATHER_OF|family|父亲|赛8:3|以赛亚的儿子。|1.6
character|以赛亚|character|以赛亚的妻子|SPOUSE_OF|family|丈夫/妻子|赛8:3|以赛亚的妻子被称为女先知。|1.6
character|以赛亚的妻子|character|玛黑珥沙拉勒哈施罢斯|MOTHER_OF|family|母亲|赛8:3|女先知生子。|1.4
character|尼利亚|character|巴录|FATHER_OF|family|父亲|耶32:12|尼利亚是巴录的父亲。|1.8
character|尼利亚|character|西莱雅|FATHER_OF|family|父亲|耶51:59|尼利亚是西莱雅的父亲。|1.6
character|西莱雅|character|巴录|SIBLING_OF|family|兄弟|耶51:59|西莱雅与巴录是兄弟。|1.4
character|巴录|character|耶利米|SERVANT_OF|spiritual|文士|耶36:4|巴录是耶利米的文士。|2.0
character|西莱雅|character|耶利米|SERVANT_OF|spiritual|执事|耶51:59|西莱雅奉命带预言书到巴比伦。|1.6
character|巴施户珥|character|耶利米|OPPOSED|event|逼迫|耶20:2|巴施户珥打耶利米并枷锁他。|1.6
character|哈拿尼雅（假先知）|character|耶利米|OPPOSED|event|对抗|耶28:10|哈拿尼雅折断耶利米的木轭。|1.8
character|示玛雅（尼希兰人）|character|耶利米|OPPOSED|event|攻击|耶29:24|示玛雅写信攻击耶利米。|1.4
character|以伯米勒|character|耶利米|PROTECTED|event|搭救|耶38:7-13|以伯米勒把耶利米从泥坑拉上来。|1.8
character|以实玛利（尼探雅之子）|character|基大利|KILLED|event|刺杀|耶41:2|以实玛利刺杀省长基大利。|1.8
character|约哈难（加利亚之子）|character|以实玛利（尼探雅之子）|OPPOSED|political|追讨|耶41:11|约哈难追击以实玛利。|1.6
character|约哈难（加利亚之子）|place|egypt|TRAVELED_TO|location|下埃及|耶43:7|约哈难带百姓下埃及。|1.4
character|尼布撒拉旦|character|尼布甲尼撒|SERVANT_OF|spiritual|护卫长|王下25:8|尼布撒拉旦是巴比伦护卫长。|1.6
character|尼布撒拉旦|character|耶利米|PROTECTED|event|释放|耶39:11-14|尼布撒拉旦善待并释放耶利米。|1.6
character|尼布甲尼撒|place|jerusalem|CONQUERED|political|攻陷|王下25:1|尼布甲尼撒攻陷耶路撒冷。|2.0
character|尼布甲尼撒|nation|babylon-empire|KING_OF|spiritual|君王|但2:1|尼布甲尼撒是巴比伦王。|2.2
character|尼布甲尼撒|group|judah-exiles|EXILED|political|掳掠|王下25:11|尼布甲尼撒掳掠犹大人。|1.8
character|基大利|event|return-from-exile|PARTICIPATED_IN|event|作省长|耶40:7|基大利被立为犹大省长。|1.4
character|布西|character|以西结|FATHER_OF|family|父亲|结1:3|布西是以西结的父亲。|1.6
character|亚施毗拿|character|尼布甲尼撒|SERVANT_OF|spiritual|太监长|但1:3|亚施毗拿是巴比伦太监长。|1.6
character|亚施毗拿|character|但以理|ASSOCIATED_WITH|event|管理|但1:11|亚施毗拿管理但以理等少年。|1.6
character|亚略|character|尼布甲尼撒|SERVANT_OF|spiritual|护卫长|但2:14|亚略是巴比伦护卫长。|1.4
character|大利乌（玛代人）|character|但以理|PROTECTED|event|搭救|但6:23|大利乌将但以理从狮坑救出。|1.8
character|大利乌（玛代人）|character|伯沙撒|ASSOCIATED_WITH|event|接续掌权|但5:31|玛代人大利乌在伯沙撒后取国。|1.6
character|但以理|character|大利乌（玛代人）|SERVANT_OF|spiritual|臣宰|但6:2|但以理作大利乌的总长。|1.6
character|何西阿|character|歌篾|SPOUSE_OF|family|丈夫/妻子|何1:3|何西阿娶歌篾为妻。|2.0
character|何西阿|character|耶斯列（何西阿之子）|FATHER_OF|family|父亲|何1:4|何西阿的长子耶斯列。|1.6
character|何西阿|character|罗路哈玛|FATHER_OF|family|父亲|何1:6|何西阿的女儿罗路哈玛。|1.6
character|何西阿|character|罗阿米|FATHER_OF|family|父亲|何1:9|何西阿的儿子罗阿米。|1.6
character|歌篾|character|耶斯列（何西阿之子）|MOTHER_OF|family|母亲|何1:3-4|歌篾是耶斯列的母亲。|1.4
character|亚米太|character|约拿（先知）|FATHER_OF|family|父亲|拿1:1|亚米太是约拿的父亲。|1.8
character|约拿（先知）|character|尼尼微王|PREACHED_TO|spiritual|传警告|拿3:4|约拿向尼尼微宣告审判。|1.8
character|约拿（先知）|place|nineveh|TRAVELED_TO|location|前往|拿3:3|约拿往尼尼微城。|1.6
character|尼尼微王|place|nineveh|LIVED_IN|location|在位|拿3:6|尼尼微王带领全城悔改。|1.6
character|尼尼微王|theme|repentance|HAS_THEME|other|主题|拿3:7|尼尼微王带头悔改禁食。|1.6
character|易多|character|比利家|FATHER_OF|family|父亲|亚1:1|易多是比利家的父亲。|1.4
character|比利家|character|撒迦利亚|FATHER_OF|family|父亲|亚1:1|比利家是先知撒迦利亚的父亲。|1.6
character|设巴萨|event|return-from-exile|PARTICIPATED_IN|event|归回领袖|拉1:11|设巴萨带回圣殿器皿。|1.6
character|古列|group|jews-returnees|ALLOWED_RETURN|political|准许归回|拉1:1|古列下诏准许犹太人归回。|1.8
character|约萨达|character|约书亚大祭司|FATHER_OF|family|父亲|该1:1|约萨达是约书亚大祭司的父亲。|1.6
character|约书亚大祭司|event|return-from-exile|PARTICIPATED_IN|event|重建祭坛|拉3:2|约书亚与所罗巴伯重建祭坛。|1.6
character|约书亚大祭司|character|所罗巴伯|ALLIED_WITH|political|同工|拉3:2|约书亚与所罗巴伯一同带领归回。|1.6
character|哈拿尼（尼希米之兄）|character|尼希米|SIBLING_OF|family|兄弟|尼1:2|哈拿尼是尼希米的兄弟。|1.6
character|哈拿尼（尼希米之兄）|event|nehemiah-wall-builders|PARTICIPATED_IN|event|管理|尼7:2|哈拿尼被派管理耶路撒冷。|1.4
character|哈拿尼雅（尼希米治理者）|event|nehemiah-wall-builders|PARTICIPATED_IN|event|管理营楼|尼7:2|哈拿尼雅管理耶路撒冷营楼。|1.4
character|参巴拉|character|尼希米|OPPOSED|political|反对|尼4:1|参巴拉反对修墙。|1.8
character|多比雅|character|尼希米|OPPOSED|political|反对|尼4:3|多比雅反对修墙。|1.6
character|基善|character|尼希米|OPPOSED|political|反对|尼6:1|基善反对修墙。|1.6
character|参巴拉|character|多比雅|ALLIED_WITH|political|结盟|尼4:7|参巴拉与多比雅联手。|1.4
character|基善|character|参巴拉|ALLIED_WITH|political|结盟|尼6:1|基善与参巴拉联手。|1.4
character|示玛雅（阻挠尼希米）|character|尼希米|OPPOSED|event|恐吓|尼6:10|示玛雅受雇恐吓尼希米。|1.4
character|挪亚底|character|尼希米|OPPOSED|event|恐吓|尼6:14|女先知挪亚底恐吓尼希米。|1.4
character|参巴拉|event|jerusalem-wall-rebuild|OPPOSED|event|反对修墙|尼4|参巴拉百般阻挠修墙。|1.6
character|亚哈随鲁王|character|瓦实提|SPOUSE_OF|family|丈夫/妻子|斯1:9|瓦实提原为亚哈随鲁的王后。|1.6
character|亚哈随鲁王|character|以斯帖|SPOUSE_OF|family|丈夫/妻子|斯2:17|以斯帖被立为王后。|2.0
character|亚哈随鲁王|nation|persian-empire|KING_OF|spiritual|君王|斯1:1|亚哈随鲁是波斯王。|1.8
character|哈曼|character|末底改|OPPOSED|political|仇恨|斯3:5|哈曼因末底改不跪拜而怀恨。|2.0
character|哈曼|character|以斯帖|OPPOSED|political|谋害犹大人|斯3:6|哈曼图谋灭绝犹大人。|1.8
character|细利斯|character|哈曼|SPOUSE_OF|family|丈夫/妻子|斯5:14|细利斯是哈曼的妻子。|1.6
character|细利斯|character|哈曼|ASSOCIATED_WITH|event|献计|斯5:14|细利斯献计立木架。|1.4
character|哈曼|character|哈曼十子|FATHER_OF|family|父亲|斯9:10|哈曼有十个儿子。|1.4
character|哈曼|nation|amalek|MEMBER_OF|other|亚甲族|斯3:1|哈曼是亚甲族人。|1.4
character|亚甲|character|哈曼|ANCESTOR_OF|family|祖先|斯3:1|哈曼是亚玛力王亚甲的后裔。|1.4
character|希该|character|以斯帖|PROTECTED|event|善待|斯2:9|希该恩待以斯帖。|1.6
character|希该|character|亚哈随鲁王|SERVANT_OF|spiritual|太监|斯2:8|希该是管理女子的太监。|1.4
character|沙甲|character|亚哈随鲁王|SERVANT_OF|spiritual|太监|斯2:14|沙甲管理妃嫔。|1.2
character|哈波拿|character|哈曼|OPPOSED|event|指出木架|斯7:9|哈波拿指出哈曼所立的木架。|1.4
character|比革他|character|亚哈随鲁王|OPPOSED|event|谋害|斯2:21|比革他谋害王。|1.4
character|提列|character|比革他|ALLIED_WITH|political|同谋|斯2:21|提列与比革他同谋。|1.2
character|末底改|character|亚哈随鲁王|PROTECTED|event|揭发阴谋|斯2:22|末底改揭发谋害王的阴谋。|1.6
character|末底改|event|esther-deliverance|PARTICIPATED_IN|event|参与|斯|末底改在拯救中起关键作用。|1.8
character|以斯帖|event|esther-deliverance|LED|event|带领|斯4-9|以斯帖冒死为本族求情。|2.0
character|哈曼|event|esther-deliverance|PARTICIPATED_IN|event|败亡|斯7|哈曼的诡计反害己身。|1.6
character|哈曼十子|event|esther-deliverance|DIED_IN|event|灭亡|斯9:10|哈曼十子一同被除。|1.4
character|末底改|place|susa|LIVED_IN|location|居住|斯2:5|末底改住在书珊城。|1.4
character|以斯帖|place|susa|LIVED_IN|location|居住|斯2:8|以斯帖住在书珊宫。|1.4
character|加百列|character|马利亚|ASSOCIATED_WITH|event|报信|路1:26|加百列向马利亚报喜信。|1.8
character|加百列|character|撒迦利亚|ASSOCIATED_WITH|event|报信|路1:11|加百列向撒迦利亚报信。|1.6
character|加百列|event|incarnation|PARTICIPATED_IN|event|参与|路1|加百列宣告基督降生。|1.6
character|东方博士|event|incarnation|PARTICIPATED_IN|event|朝拜|太2:1|东方博士来朝拜婴孩耶稣。|1.6
character|东方博士|place|bethlehem|TRAVELED_TO|location|前往|太2:9|东方博士到伯利恒。|1.4
character|牧羊人|event|incarnation|PARTICIPATED_IN|event|见证降生|路2:16|牧羊人见证主降生。|1.6
character|牧羊人|place|bethlehem|LIVED_IN|location|野地|路2:8|牧羊人在伯利恒野地。|1.2
character|希律大帝|group|herodian-dynasty|MEMBER_OF|other|希律家族|太2:1|希律大帝是王朝的开创者。|1.6
character|希律大帝|character|耶稣基督|OPPOSED|event|屠婴|太2:16|希律屠杀伯利恒婴孩寻索耶稣。|1.8
character|希律大帝|character|希律安提帕|FATHER_OF|family|父亲|路3:1|希律安提帕是希律大帝之子。|1.6
character|希律大帝|character|希律腓力|FATHER_OF|family|父亲|可6:17|希律腓力是希律大帝之子。|1.4
character|希律安提帕|group|herodian-dynasty|MEMBER_OF|other|希律家族|路3:1|希律安提帕属希律家族。|1.4
character|希律腓力|group|herodian-dynasty|MEMBER_OF|other|希律家族|可6:17|希律腓力属希律家族。|1.2
character|希律安提帕|character|施洗约翰|KILLED|event|斩首|可6:27|希律安提帕斩施洗约翰。|2.0
character|希律安提帕|character|耶稣基督|OPPOSED|event|戏弄|路23:11|希律安提帕戏弄耶稣。|1.6
character|希罗底|character|希律腓力|SPOUSE_OF|family|原配|可6:17|希罗底原是希律腓力的妻子。|1.4
character|希罗底|character|希律安提帕|SPOUSE_OF|family|再嫁|可6:17|希罗底改嫁希律安提帕。|1.4
character|希罗底|character|施洗约翰|OPPOSED|event|怀恨|可6:19|希罗底怀恨施洗约翰要杀他。|1.6
character|希罗底|character|希罗底的女儿|MOTHER_OF|family|母亲|可6:22|希罗底的女儿为希律跳舞。|1.4
character|希罗底的女儿|character|施洗约翰|ASSOCIATED_WITH|event|求其首级|可6:25|少女受母指使求约翰的头。|1.4
character|凯撒奥古斯都|nation|rome-empire|RULED_OVER|political|作皇帝|路2:1|奥古斯都是罗马皇帝。|1.6
character|凯撒奥古斯都|event|incarnation|PARTICIPATED_IN|event|报名上册|路2:1|奥古斯都的谕旨成就降生预言背景。|1.4
character|居里扭|event|incarnation|PARTICIPATED_IN|event|报名背景|路2:2|居里扭作叙利亚巡抚时报名上册。|1.2
character|提庇留|nation|rome-empire|RULED_OVER|political|作皇帝|路3:1|提庇留是传道时期的罗马皇帝。|1.4
character|西庇太|character|西庇太的雅各|FATHER_OF|family|父亲|太4:21|西庇太是雅各的父亲。|1.8
character|西庇太|character|约翰|FATHER_OF|family|父亲|太4:21|西庇太是使徒约翰的父亲。|1.8
character|亚勒腓|character|马太|FATHER_OF|family|父亲|可2:14|亚勒腓是马太（利未）的父亲。|1.6
character|亚勒腓|character|小雅各（亚勒腓之子）|FATHER_OF|family|父亲|可3:18|亚勒腓是小雅各的父亲。|1.6
character|小雅各（亚勒腓之子）|group|twelve-apostles|MEMBER_OF|other|十二使徒|可3:18|小雅各是十二使徒之一。|1.6
character|小雅各（亚勒腓之子）|character|耶稣基督|APOSTLE_OF|spiritual|使徒|可3:18|小雅各作耶稣的使徒。|1.6
character|睚鲁|character|睚鲁的女儿|FATHER_OF|family|父亲|可5:23|睚鲁的女儿病危。|1.6
character|耶稣基督|character|睚鲁的女儿|HEALED|event|使复活|可5:41|耶稣使睚鲁的女儿复活。|1.8
character|睚鲁|event|jesus-miracles|PARTICIPATED_IN|event|求医治|可5:22|会堂主管睚鲁求耶稣。|1.6
character|耶稣基督|character|血漏的妇人|HEALED|event|医治|可5:29|女人摸耶稣衣裳得医治。|1.6
character|血漏的妇人|event|jesus-miracles|PARTICIPATED_IN|event|得医治|可5:25|血漏妇人因信得医治。|1.6
character|耶稣基督|character|巴底买|HEALED|event|开眼|可10:52|耶稣使巴底买重见光明。|1.6
character|巴底买|place|jericho|LIVED_IN|location|耶利哥|可10:46|巴底买在耶利哥乞讨。|1.2
character|耶稣基督|character|毕士大池的病人|HEALED|event|医治|约5:8|耶稣医好三十八年的病人。|1.6
character|耶稣基督|character|生来瞎眼的人|HEALED|event|开眼|约9:7|耶稣医好生来瞎眼的人。|1.6
character|生来瞎眼的人|event|jesus-miracles|PARTICIPATED_IN|event|得医治作见证|约9|他勇敢为耶稣作见证。|1.6
character|耶稣基督|character|撒玛利亚妇人|ASSOCIATED_WITH|event|井边对话|约4:7|耶稣在井边向撒玛利亚妇人启示自己。|1.8
character|耶稣基督|character|叙利腓尼基妇人|ASSOCIATED_WITH|event|称许信心|可7:29|耶稣因她的信医治她女儿。|1.6
character|迦百农的百夫长|character|耶稣基督|ASSOCIATED_WITH|event|信心榜样|太8:10|百夫长信耶稣只要说一句话。|1.6
character|百夫长的仆人|character|迦百农的百夫长|SERVANT_OF|spiritual|仆人|太8:6|仆人是百夫长所重看的。|1.2
character|耶稣基督|character|百夫长的仆人|HEALED|event|远程医治|太8:13|耶稣远程医治百夫长的仆人。|1.6
character|迦百农的百夫长|nation|rome-empire|MEMBER_OF|other|罗马军官|太8:5|百夫长是罗马军官。|1.2
character|耶稣基督|character|格拉森被鬼附的人|HEALED|event|赶鬼|可5:13|耶稣释放被群鬼所附的人。|1.6
character|格拉森被鬼附的人|event|jesus-miracles|PARTICIPATED_IN|event|得释放|可5:1|格拉森人得耶稣释放。|1.4
character|十个长大麻风的|event|jesus-miracles|PARTICIPATED_IN|event|得洁净|路17:14|十个麻风病人得洁净。|1.4
character|耶稣基督|character|十个长大麻风的|HEALED|event|洁净|路17:14|耶稣洁净十个麻风病人。|1.6
character|迦拿婚筵的新郎|event|jesus-miracles|PARTICIPATED_IN|event|水变酒|约2:9|水变酒发生在迦拿婚筵。|1.4
character|管筵席的|event|jesus-miracles|WITNESSED|event|见证|约2:9|管筵席的尝出变好的酒。|1.2
character|革罗罢|event|resurrection|WITNESSED|event|见证|路24:18|革罗罢在以马忤斯路上遇见复活主。|1.6
character|革罗罢|place|emmaus|TRAVELED_TO|location|前往|路24:13|革罗罢往以马忤斯。|1.4
character|亚利马太的约瑟|event|crucifixion|PARTICIPATED_IN|event|安葬耶稣|太27:60|亚利马太的约瑟安葬耶稣。|1.8
character|彼拉多的妻子|character|彼拉多|SPOUSE_OF|family|丈夫/妻子|太27:19|彼拉多的妻子因梦警告他。|1.4
character|彼拉多的妻子|character|耶稣基督|ASSOCIATED_WITH|event|梦中警告|太27:19|她为耶稣的事受警告。|1.4
character|巴拉巴|event|crucifixion|PARTICIPATED_IN|event|被释放|太27:26|巴拉巴被释放，耶稣被定罪。|1.6
character|巴拉巴|character|彼拉多|ASSOCIATED_WITH|event|得释放|可15:15|彼拉多释放巴拉巴。|1.2
character|西门（古利奈人）|character|亚历山大（古利奈人之子）|FATHER_OF|family|父亲|可15:21|西门是亚历山大的父亲。|1.6
character|西门（古利奈人）|character|鲁孚|FATHER_OF|family|父亲|可15:21|西门是鲁孚的父亲。|1.6
character|西门（古利奈人）|event|crucifixion|PARTICIPATED_IN|event|背十字架|可15:21|西门被迫背耶稣的十字架。|1.6
character|腓力|character|埃提阿伯太监|PREACHED_TO|spiritual|传福音|徒8:35|腓利向埃提阿伯太监传耶稣。|1.8
character|埃提阿伯太监|group|early-church|MEMBER_OF|other|信主|徒8:38|埃提阿伯太监受洗归主。|1.4
character|腓力|character|腓力的四个女儿|FATHER_OF|family|父亲|徒21:9|腓利有四个说预言的女儿。|1.4
character|腓力的四个女儿|group|early-church|PROPHET_OF|spiritual|女先知|徒21:9|四个女儿都说预言。|1.2
character|迦玛列|character|保罗|MENTOR_OF|spiritual|老师|徒22:3|保罗是迦玛列门下受教的。|1.8
character|马利亚（马可的母亲）|character|马可|MOTHER_OF|family|母亲|徒12:12|马可的母亲马利亚。|1.6
character|马利亚（马可的母亲）|group|early-church|MEMBER_OF|other|家庭教会|徒12:12|她家是耶路撒冷的祷告之家。|1.4
character|罗大|character|马利亚（马可的母亲）|SERVANT_OF|spiritual|使女|徒12:13|罗大是这家的使女。|1.2
character|罗大|character|彼得|ASSOCIATED_WITH|event|报信|徒12:14|罗大认出彼得的声音去报信。|1.2
character|亚迦布|group|early-church|PROPHET_OF|spiritual|先知|徒11:28|亚迦布是耶路撒冷来的先知。|1.4
character|亚迦布|character|保罗|ASSOCIATED_WITH|event|预言被捆|徒21:11|亚迦布预言保罗在耶路撒冷被捆。|1.6
character|犹大（巴撒巴）|group|early-church|MEMBER_OF|other|教会代表|徒15:22|犹大被差往安提阿传达决议。|1.4
character|西面（尼结）|group|antioch-church|MEMBER_OF|other|教会领袖|徒13:1|西面是安提阿教会的先知教师。|1.6
character|马念|group|antioch-church|MEMBER_OF|other|教会领袖|徒13:1|马念是安提阿教会的领袖。|1.6
character|路求|group|antioch-church|MEMBER_OF|other|教会领袖|徒13:1|路求是安提阿教会的领袖。|1.4
character|士求保罗|character|保罗|ASSOCIATED_WITH|event|听道信主|徒13:12|方伯士求保罗信了道。|1.6
character|士求保罗|place|cyprus|LIVED_IN|location|居比路|徒13:7|士求保罗是居比路方伯。|1.4
character|以吕马|character|保罗|OPPOSED|event|敌挡|徒13:8|以吕马敌挡保罗传道。|1.6
character|以吕马|character|士求保罗|OPPOSED|event|拦阻|徒13:8|以吕马想拦阻方伯信道。|1.4
character|腓立比的狱卒|group|early-church|MEMBER_OF|other|信主|徒16:34|狱卒全家信主受洗。|1.4
character|腓立比的狱卒|place|philippi|LIVED_IN|location|腓立比|徒16:23|狱卒在腓立比。|1.2
character|保罗|character|被鬼附的使女|HEALED|event|赶鬼|徒16:18|保罗赶出使女身上的巫鬼。|1.4
character|底米丢|character|保罗|OPPOSED|event|煽动暴乱|徒19:24|银匠底米丢煽动反对保罗。|1.6
character|底米丢|place|ephesus|LIVED_IN|location|以弗所|徒19:24|底米丢在以弗所制造银龛。|1.2
character|亚历山大（以弗所人）|character|底米丢|ASSOCIATED_WITH|event|以弗所暴乱|徒19:33|亚历山大被推出来想分诉。|1.2
character|亚历山大（以弗所人）|place|ephesus|LIVED_IN|location|以弗所|徒19:33|以弗所暴乱中的犹太人。|1.2
character|亚里达古|character|保罗|ALLIED_WITH|political|同伴|徒27:2|亚里达古是保罗的同伴。|1.6
character|亚里达古|group|paul-coworkers|MEMBER_OF|other|同工|徒19:29|亚里达古是保罗的马其顿同工。|1.6
character|所巴特|group|paul-coworkers|MEMBER_OF|other|同工|徒20:4|所巴特陪同保罗。|1.4
character|西公都|group|paul-coworkers|MEMBER_OF|other|同工|徒20:4|西公都陪同保罗。|1.4
character|特罗非摩|group|paul-coworkers|MEMBER_OF|other|同工|徒21:29|特罗非摩是以弗所的同工。|1.4
character|该犹（马其顿人）|group|paul-coworkers|MEMBER_OF|other|同伴|徒19:29|该犹是保罗的马其顿同伴。|1.4
character|该犹（马其顿人）|character|亚里达古|ALLIED_WITH|political|同伴|徒19:29|该犹与亚里达古一同被抓。|1.4
character|保罗|character|犹推古|HEALED|event|使复活|徒20:10|保罗使坠楼的犹推古活过来。|1.6
character|革老丢吕西亚|character|保罗|PROTECTED|event|搭救|徒23:10|千夫长搭救保罗脱离众人。|1.6
character|腓力斯|character|保罗|ASSOCIATED_WITH|event|审讯|徒24:1|腓力斯审问保罗却拖延。|1.4
character|腓力斯|character|土西拉|SPOUSE_OF|family|丈夫/妻子|徒24:24|土西拉是腓力斯的妻子。|1.2
character|非斯都|character|保罗|ASSOCIATED_WITH|event|审讯|徒25:6|非斯都接续审问保罗。|1.4
character|希律亚基帕一世|group|herodian-dynasty|MEMBER_OF|other|希律家族|徒12:1|亚基帕一世属希律家族。|1.4
character|希律亚基帕一世|character|西庇太的雅各|KILLED|event|杀害|徒12:2|亚基帕一世用刀杀雅各。|1.8
character|希律亚基帕一世|character|彼得|OPPOSED|event|下监|徒12:3|亚基帕一世捉拿彼得下监。|1.6
character|希律亚基帕二世|group|herodian-dynasty|MEMBER_OF|other|希律家族|徒25:13|亚基帕二世属希律家族。|1.4
character|希律亚基帕二世|character|保罗|ASSOCIATED_WITH|event|听申辩|徒26:1|保罗在亚基帕二世面前申辩。|1.6
character|百尼基|character|希律亚基帕二世|SIBLING_OF|family|姊弟|徒25:13|百尼基是亚基帕二世的姊妹。|1.2
character|犹流|character|保罗|PROTECTED|event|善待|徒27:3|百夫长犹流宽待保罗。|1.4
character|犹流|event|paul-rome-imprisonment|PARTICIPATED_IN|event|押送|徒27:1|犹流押送保罗往罗马。|1.4
character|部百流|character|保罗|PROTECTED|event|接待|徒28:7|部百流在米利大接待保罗。|1.4
character|部百流|place|malta|LIVED_IN|location|米利大|徒28:7|部百流是米利大岛的首领。|1.2
character|马利亚（罗马教会）|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:6|为信徒劳苦的马利亚。|1.4
character|尼利亚的姊妹|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:15|保罗问安的圣徒。|1.2
character|尼利亚的姊妹|character|尼利亚|SIBLING_OF|family|姊妹|罗16:15|尼利亚的姊妹。|1.2
character|德丢|character|保罗|SERVANT_OF|spiritual|代笔|罗16:22|德丢代笔写罗马书。|1.4
character|括土|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:23|括土向罗马教会问安。|1.2
character|鲁孚的母亲|character|鲁孚|MOTHER_OF|family|母亲|罗16:13|待保罗如同母亲。|1.4
character|亚利多布家的人|event|paul-greetings|MEMBER_OF|other|问安一家|罗16:10|亚利多布家在主里的人。|1.2
character|拿其数家的人|event|paul-greetings|MEMBER_OF|other|问安一家|罗16:11|拿其数家在主里的人。|1.2
character|该犹（约翰三书）|character|约翰|ASSOCIATED_WITH|event|收信人|约三1|约翰写信给所爱的该犹。|1.4
character|该犹（约翰三书）|character|丢特腓|OPPOSED|event|对比|约三9|该犹的好客与丢特腓相对。|1.2
character|革来氏家里的人|character|保罗|ASSOCIATED_WITH|event|报告纷争|林前1:11|革来氏家的人报告哥林多的纷争。|1.4
character|所提尼|character|保罗|ALLIED_WITH|political|同具名|林前1:1|所提尼与保罗联名写信。|1.4
character|司提反一家|group|early-church|MEMBER_OF|other|初熟果子|林前16:15|司提反一家是亚该亚初结的果子。|1.4
character|福徒拿都|group|paul-coworkers|MEMBER_OF|other|同工|林前16:17|福徒拿都来见保罗。|1.2
character|亚该古|group|paul-coworkers|MEMBER_OF|other|同工|林前16:17|亚该古来见保罗。|1.2
character|福徒拿都|character|亚该古|ALLIED_WITH|political|同来|林前16:17|福徒拿都与亚该古同来。|1.2
character|革勒免|group|paul-coworkers|MEMBER_OF|other|同工|腓4:3|革勒免与保罗同劳。|1.2
character|宁法|group|early-church|MEMBER_OF|other|家庭教会|西4:15|宁法家里有教会。|1.2
character|亚腓亚|character|腓利门|ASSOCIATED_WITH|event|同蒙问安|门1:2|亚腓亚与腓利门一同受问安。|1.2
character|亚基布|character|亚腓亚|ALLIED_WITH|political|同工|门1:2|亚基布与亚腓亚同被提名。|1.2
character|耶数（犹士都）|group|paul-coworkers|MEMBER_OF|other|同工|西4:11|犹士都是保罗的犹太同工。|1.2
character|革勒士|group|paul-coworkers|MEMBER_OF|other|同工|提后4:10|革勒士往加拉太去了。|1.2
character|加布|character|保罗|ASSOCIATED_WITH|event|存放外衣|提后4:13|保罗把外衣留在加布家。|1.2
character|亚历山大（铜匠）|character|保罗|OPPOSED|event|敌对|提后4:14|铜匠亚历山大多多敌对保罗。|1.4
character|腓吉路|character|保罗|BETRAYED|political|离弃|提后1:15|腓吉路在亚细亚离弃保罗。|1.4
character|黑摩其尼|character|保罗|BETRAYED|political|离弃|提后1:15|黑摩其尼离弃保罗。|1.4
character|腓吉路|character|黑摩其尼|ALLIED_WITH|political|一同离弃|提后1:15|腓吉路与黑摩其尼一同离弃保罗。|1.2
character|罗以|character|友尼基|MOTHER_OF|family|母亲|提后1:5|罗以是友尼基的母亲。|1.4
character|友尼基|character|提摩太|MOTHER_OF|family|母亲|提后1:5|友尼基是提摩太的母亲。|1.6
character|罗以|character|提摩太|ANCESTOR_OF|family|外祖母|提后1:5|罗以是提摩太的外祖母。|1.4
character|亚居拉|character|百基拉|SPOUSE_OF|family|丈夫/妻子|徒18:2|亚居拉与百基拉是夫妻。|1.8
character|亚居拉|group|paul-coworkers|MEMBER_OF|other|同工|罗16:3|亚居拉是保罗的同工。|1.6
character|百基拉|group|paul-coworkers|MEMBER_OF|other|同工|罗16:3|百基拉是保罗的同工。|1.6
character|百基拉|character|亚波罗|MENTOR_OF|spiritual|教导|徒18:26|百基拉将道更详细讲给亚波罗。|1.6
character|亚居拉|character|亚波罗|MENTOR_OF|spiritual|教导|徒18:26|亚居拉将道更详细讲给亚波罗。|1.4
character|亚拿尼亚（撒非喇之夫）|character|撒非喇|SPOUSE_OF|family|丈夫/妻子|徒5:1|亚拿尼亚与撒非喇是夫妻。|1.6
character|亚拿尼亚（撒非喇之夫）|group|early-church|OPPOSED|event|欺哄圣灵|徒5:3|他私自留下价银欺哄圣灵。|1.6
character|撒非喇|character|亚拿尼亚（撒非喇之夫）|ALLIED_WITH|political|同谋|徒5:2|撒非喇与丈夫同心试探圣灵。|1.4
character|撒非喇|group|early-church|OPPOSED|event|欺哄圣灵|徒5:8|撒非喇同谋欺哄圣灵。|1.4
character|丢特腓|character|约翰|OPPOSED|event|不接待|约三9|丢特腓不接待弟兄、抵挡约翰。|1.4
character|低米丢|character|约翰|ASSOCIATED_WITH|event|美好见证|约三12|低米丢有众人的美好见证。|1.2
character|米迦勒|character|龙|OPPOSED|event|争战|启12:7|米迦勒与龙争战。|1.6
character|龙|character|兽|ALLIED_WITH|political|赐权|启13:2|龙将权柄给了兽。|1.6
character|兽|character|假先知（启示录）|ALLIED_WITH|political|同党|启19:20|兽与假先知一同迷惑人。|1.4
character|兽|character|两个见证人|KILLED|event|杀害|启11:7|兽杀了两个见证人。|1.4
character|大淫妇巴比伦|character|兽|ALLIED_WITH|political|骑乘|启17:3|大淫妇骑在朱红色的兽上。|1.4
character|耶洗别（推雅推喇）|group|early-church|OPPOSED|event|引诱|启2:20|推雅推喇的耶洗别引诱信徒。|1.4
character|尼哥拉党人|group|early-church|OPPOSED|event|异端|启2:6|尼哥拉党的行为为主所恨恶。|1.4
$edges$, E'\n')
), edge_seed AS (
    SELECT row_number() OVER () AS ord,
        parts[1] AS source_kind, parts[2] AS source_ref, parts[3] AS target_kind,
        parts[4] AS target_ref, parts[5] AS relationship_type, parts[6] AS relationship_category,
        parts[7] AS label_zh, parts[8] AS scripture_ref, parts[9] AS description,
        parts[10]::numeric AS weight
    FROM raw CROSS JOIN LATERAL (SELECT string_to_array(line,'|') AS parts) parsed
    WHERE line <> '' AND line NOT LIKE '--%'
), resolved AS (
    SELECT edge_seed.*,
        CASE WHEN source_kind='character' THEN source_char_node.id ELSE source_kind||'-'||source_ref END AS source_node_id,
        CASE WHEN target_kind='character' THEN target_char_node.id ELSE target_kind||'-'||target_ref END AS target_node_id
    FROM edge_seed
    LEFT JOIN biblical_characters source_char ON source_kind='character' AND source_char.name=source_ref AND source_char.is_active=true
    LEFT JOIN biblical_graph_nodes source_char_node ON source_char_node.character_id=source_char.id AND source_char_node.is_active=true
    LEFT JOIN biblical_characters target_char ON target_kind='character' AND target_char.name=target_ref AND target_char.is_active=true
    LEFT JOIN biblical_graph_nodes target_char_node ON target_char_node.character_id=target_char.id AND target_char_node.is_active=true
)
INSERT INTO biblical_graph_edges (
    source_node_id, target_node_id, relationship_type, relationship_category, label_zh, label_en,
    scripture_ref, description, weight, confidence, is_directed, sort_order, scripture_refs, confidence_level
)
SELECT source_node_id, target_node_id, relationship_type, relationship_category, label_zh, relationship_type,
    scripture_ref, description, weight, 0.9,
    relationship_type NOT IN ('SPOUSE_OF','SIBLING_OF','ALLIED_WITH','FRIEND_OF'),
    64000 + ord, ARRAY_REMOVE(ARRAY[scripture_ref], NULL), 'high'
FROM resolved
WHERE source_node_id IS NOT NULL AND target_node_id IS NOT NULL AND source_node_id <> target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=target_node_id)
ON CONFLICT DO NOTHING;

-- Auto-generate inverse edges for the family / membership relations added above.
WITH new_edges AS (
    SELECT * FROM biblical_graph_edges
    WHERE is_active = true AND sort_order BETWEEN 64000 AND 69999
      AND relationship_type IN ('FATHER_OF','MOTHER_OF','ANCESTOR_OF','MEMBER_OF','ANOINTED','HEALED','KILLED')
), inverse_rows AS (
    SELECT target_node_id AS source_node_id, source_node_id AS target_node_id,
        CASE relationship_type
            WHEN 'FATHER_OF' THEN 'CHILD_OF' WHEN 'MOTHER_OF' THEN 'CHILD_OF'
            WHEN 'ANCESTOR_OF' THEN 'DESCENDANT_OF' WHEN 'MEMBER_OF' THEN 'CONTAINS_MEMBER'
            WHEN 'ANOINTED' THEN 'ANOINTED_BY' WHEN 'HEALED' THEN 'HEALED_BY' WHEN 'KILLED' THEN 'KILLED_BY'
        END AS relationship_type,
        relationship_category,
        CASE relationship_type
            WHEN 'FATHER_OF' THEN '儿子/女儿' WHEN 'MOTHER_OF' THEN '儿子/女儿'
            WHEN 'ANCESTOR_OF' THEN '后裔' WHEN 'MEMBER_OF' THEN '包含成员'
            WHEN 'ANOINTED' THEN '受膏于' WHEN 'HEALED' THEN '得医治于' WHEN 'KILLED' THEN '被杀于'
        END AS label_zh,
        CASE relationship_type
            WHEN 'FATHER_OF' THEN 'child of' WHEN 'MOTHER_OF' THEN 'child of'
            WHEN 'ANCESTOR_OF' THEN 'descendant of' WHEN 'MEMBER_OF' THEN 'contains member'
            WHEN 'ANOINTED' THEN 'anointed by' WHEN 'HEALED' THEN 'healed by' WHEN 'KILLED' THEN 'killed by'
        END AS label_en,
        scripture_ref, '由 0064 关系自动生成的反向关系：' || description AS description,
        GREATEST(weight - 0.2, 0.1) AS weight, confidence, true AS is_directed,
        sort_order + 100000 AS sort_order, scripture_refs, confidence_level
    FROM new_edges
)
INSERT INTO biblical_graph_edges (
    source_node_id, target_node_id, relationship_type, relationship_category,
    label_zh, label_en, scripture_ref, description, weight, confidence,
    is_directed, sort_order, scripture_refs, confidence_level
)
SELECT source_node_id, target_node_id, relationship_type, relationship_category,
    label_zh, label_en, scripture_ref, description, weight, confidence,
    is_directed, sort_order, scripture_refs, confidence_level
FROM inverse_rows
WHERE source_node_id <> target_node_id
ON CONFLICT DO NOTHING;

-- ============================================================
-- PART D. Section-13 cleanup: retire combined / duplicate graph nodes
--   (individual constituents were added above as their own nodes/edges).
-- ============================================================
-- Deactivate combined-card / duplicate graph nodes (keeps mirrorData frontend untouched).
UPDATE biblical_graph_edges e SET is_active=false
WHERE is_active=true AND (
    e.source_node_id IN (SELECT n.id FROM biblical_graph_nodes n JOIN biblical_characters c ON c.id=n.character_id WHERE c.name IN ('百夫长哥尼流','以哥念的一个女门徒大比大','亚居拉与百基拉','亚拿尼亚与撒非喇','西缅与利未（雅各之子）'))
    OR e.target_node_id IN (SELECT n.id FROM biblical_graph_nodes n JOIN biblical_characters c ON c.id=n.character_id WHERE c.name IN ('百夫长哥尼流','以哥念的一个女门徒大比大','亚居拉与百基拉','亚拿尼亚与撒非喇','西缅与利未（雅各之子）'))
);
UPDATE biblical_graph_nodes n SET is_active=false
FROM biblical_characters c
WHERE n.character_id=c.id AND c.name IN ('百夫长哥尼流','以哥念的一个女门徒大比大','亚居拉与百基拉','亚拿尼亚与撒非喇','西缅与利未（雅各之子）');
-- Deduplicate cards sharing a name: keep the lowest id, retire the rest.
WITH dups AS (
    SELECT id, name, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS rn
    FROM biblical_characters WHERE name IN ('亚他利雅')
)
UPDATE biblical_graph_nodes n SET is_active=false
FROM dups WHERE n.character_id=dups.id AND dups.rn > 1;

-- End of 0064.