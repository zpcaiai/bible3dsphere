-- 0066_complete_core_network_backbones.sql
-- Complete the connective backbone of the 12 core person-networks: the Adam→Jesus
-- messianic genealogy spine (adds 6 bridge people), Jacob→12 tribes, the 12 apostles→
-- Jesus (incl. Judas' betrayal), the Judah & Israel royal successions, and key
-- prophet↔king / mentor links. Idempotent (NOT EXISTS / ON CONFLICT).

SELECT setval(pg_get_serial_sequence('biblical_characters','id'),
              COALESCE((SELECT MAX(id) FROM biblical_characters),0));

-- PART A. Genealogy bridge people
WITH raw(line) AS (SELECT * FROM regexp_split_to_table($people$
希斯仑|Hezron|族长时代|其他|混合|得4:18;太1:3|法勒斯之子，犹大支派、大卫与基督谱系的一环。
兰|Ram|族长时代|其他|混合|得4:19;太1:3|希斯仑之子，弥赛亚谱系一环（又作亚兰）。
亚米拿达|Amminadab|出埃及时代|其他|混合|得4:19;太1:4|拿顺之父，弥赛亚谱系一环。
拿顺|Nahshon|出埃及时代|其他|正面|民1:7;得4:20|犹大支派的首领，弥赛亚谱系一环。
撒门|Salmon|进入迦南时代|其他|混合|得4:21;太1:5|波阿斯之父，娶喇合，弥赛亚谱系一环。
撒拉铁|Shealtiel|被掳归回时代|其他|混合|拉3:2;太1:12|约雅斤之子，所罗巴伯之父，被掳后谱系一环。
$people$, E'\n')), parsed AS (SELECT string_to_array(line,'|') p FROM raw WHERE line<>''), person AS (SELECT p[1] name,p[2] name_en,p[3] era,p[4] role,p[5] character_type,p[6] scripture_ref,p[7] summary FROM parsed)
INSERT INTO biblical_characters (name,name_en,era,role,character_type,lesson,summary,witness,scripture_ref,prayer,is_active,sort_order)
SELECT name,name_en,era,role,character_type,name||'在圣经救赎历史中的位置与见证。',summary,summary,scripture_ref,'愿我从'||name||'的记载中认识神在历史与群体中的作为。',true,6600 FROM person p
WHERE NOT EXISTS (SELECT 1 FROM biblical_characters c WHERE c.name=p.name);

-- PART B. Create graph nodes for the new bridge people
INSERT INTO biblical_graph_nodes (id,node_type,name,name_en,category,description,character_id,chinese_name,english_name,aliases,testament,era,role_labels,importance_level,first_appearance,related_books,key_events,theological_themes,moral_evaluation,summary)
SELECT 'char-'||c.id,'character',c.name,c.name_en,c.role,c.summary,c.id,c.name,c.name_en,ARRAY_REMOVE(ARRAY[c.name,c.name_en],NULL),
 CASE WHEN c.era ILIKE '%新约%' THEN 'New Testament' WHEN c.era ILIKE '%两约%' THEN 'Intertestamental' ELSE 'Old Testament' END,
 c.era,ARRAY_REMOVE(ARRAY[c.role],NULL),'C',c.scripture_ref,ARRAY_REMOVE(ARRAY[c.scripture_ref],NULL),ARRAY_REMOVE(ARRAY[c.lesson],NULL),
 ARRAY_REMOVE(ARRAY[c.role,c.character_type],NULL),
 CASE c.character_type WHEN '正面' THEN 'positive' WHEN '警戒' THEN 'negative' ELSE 'mixed' END,c.summary
FROM biblical_characters c WHERE c.is_active=true AND c.era<>'教会时代'
 AND NOT EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.character_id=c.id) ON CONFLICT (id) DO NOTHING;

-- PART B2. importance
UPDATE biblical_graph_nodes n SET importance_level='B' FROM biblical_characters c WHERE n.character_id=c.id AND c.name IN ('拿顺','希斯仑','撒拉铁');

-- PART C. Backbone edges
WITH raw(line) AS (SELECT * FROM regexp_split_to_table($edges$
character|法勒斯|character|希斯仑|FATHER_OF|family|父亲|得4:18|法勒斯生希斯仑。|2.2
character|希斯仑|character|兰|FATHER_OF|family|父亲|得4:19|希斯仑生兰。|2.0
character|兰|character|亚米拿达|FATHER_OF|family|父亲|得4:19|兰生亚米拿达。|2.0
character|亚米拿达|character|拿顺|FATHER_OF|family|父亲|得4:20|亚米拿达生拿顺。|2.0
character|拿顺|character|撒门|FATHER_OF|family|父亲|得4:21|拿顺生撒门。|2.0
character|撒门|character|波阿斯|FATHER_OF|family|父亲|得4:21|撒门生波阿斯。|2.2
character|撒门|character|喇合|SPOUSE_OF|family|丈夫/妻子|太1:5|撒门娶喇合。|1.8
character|波阿斯|character|路得|SPOUSE_OF|family|丈夫/妻子|得4:13|波阿斯娶路得。|2.0
character|波阿斯|character|俄备得|FATHER_OF|family|父亲|得4:21|波阿斯生俄备得。|2.2
character|路得|character|俄备得|MOTHER_OF|family|母亲|得4:17|路得生俄备得。|2.0
character|俄备得|character|耶西|FATHER_OF|family|父亲|得4:22|俄备得生耶西。|2.2
character|所罗门|character|罗波安|FATHER_OF|family|父亲|王上11:43|所罗门生罗波安。|2.2
character|约雅斤|character|撒拉铁|FATHER_OF|family|父亲|太1:12|约雅斤生撒拉铁。|1.8
character|撒拉铁|character|所罗巴伯|FATHER_OF|family|父亲|太1:12|撒拉铁生所罗巴伯。|1.8
character|亚伯拉罕|character|耶稣基督|ANCESTOR_OF|family|祖先|太1:1|耶稣是亚伯拉罕的后裔。|2.4
character|大卫|character|耶稣基督|ANCESTOR_OF|family|祖先|太1:1|耶稣是大卫的子孙。|2.6
character|所罗巴伯|character|耶稣基督|ANCESTOR_OF|family|祖先|太1:12-16|被掳后弥赛亚谱系的一环。|1.8
character|马利亚|character|耶稣基督|MOTHER_OF|family|母亲|太1:16|马利亚从圣灵怀孕生耶稣。|2.6
character|约瑟（耶稣父亲）|character|耶稣基督|FATHER_OF|family|律法上的父亲|太1:16|约瑟是耶稣律法上的父亲。|2.2
character|耶稣基督|theme|messianic-line|HAS_THEME|other|主题|太1:1|耶稣成全弥赛亚谱系的应许。|2.0
character|雅各|character|流便（雅各长子）|FATHER_OF|family|父亲|创29:32|雅各的长子流便。|2.0
character|雅各|character|犹大（雅各之子）|FATHER_OF|family|父亲|创29:35|雅各与利亚生犹大。|2.4
character|雅各|character|但（雅各之子）|FATHER_OF|family|父亲|创30:6|雅各的儿子但。|1.8
character|雅各|character|拿弗他利（雅各之子）|FATHER_OF|family|父亲|创30:8|雅各的儿子拿弗他利。|1.8
character|雅各|character|迦得（雅各之子）|FATHER_OF|family|父亲|创30:11|雅各的儿子迦得。|1.8
character|雅各|character|亚设（雅各之子）|FATHER_OF|family|父亲|创30:13|雅各的儿子亚设。|1.8
character|雅各|character|以萨迦（雅各之子）|FATHER_OF|family|父亲|创30:18|雅各的儿子以萨迦。|1.8
character|雅各|character|西布伦（雅各之子）|FATHER_OF|family|父亲|创30:20|雅各的儿子西布伦。|1.8
character|雅各|character|约瑟|FATHER_OF|family|父亲|创30:24|雅各所爱的儿子约瑟。|2.4
character|雅各|character|便雅悯（雅各之子）|FATHER_OF|family|父亲|创35:18|雅各的幼子便雅悯。|2.0
character|利亚|character|流便（雅各长子）|MOTHER_OF|family|母亲|创29:32|利亚生流便。|1.6
character|利亚|character|犹大（雅各之子）|MOTHER_OF|family|母亲|创29:35|利亚生犹大。|1.8
character|利亚|character|以萨迦（雅各之子）|MOTHER_OF|family|母亲|创30:18|利亚生以萨迦。|1.6
character|利亚|character|西布伦（雅各之子）|MOTHER_OF|family|母亲|创30:20|利亚生西布伦。|1.6
character|拉结|character|约瑟|MOTHER_OF|family|母亲|创30:24|拉结生约瑟。|2.0
character|拉结|character|便雅悯（雅各之子）|MOTHER_OF|family|母亲|创35:18|拉结生便雅悯而死。|1.8
character|彼得|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:2|彼得是使徒之首。|2.0
character|安得烈|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:2|安得烈是十二使徒之一。|1.8
character|西庇太的雅各|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:2|西庇太的雅各是使徒。|1.8
character|约翰|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:2|约翰是主所爱的使徒。|2.0
character|腓力|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:3|腓力是十二使徒之一。|1.8
character|巴多罗买|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:3|巴多罗买是十二使徒之一。|1.8
character|拿但业|character|耶稣基督|APOSTLE_OF|spiritual|使徒|约1:45|拿但业（即巴多罗买）跟随耶稣。|1.6
character|多马|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:3|多马是十二使徒之一。|1.8
character|马太|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:3|马太是税吏蒙召作使徒。|1.8
character|小雅各（亚勒腓之子）|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:3|小雅各是十二使徒之一。|1.6
character|达太|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:3|达太（犹大）是十二使徒之一。|1.6
character|奋锐党的西门|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:4|奋锐党的西门是使徒。|1.6
character|犹大|character|耶稣基督|APOSTLE_OF|spiritual|使徒|太10:4|加略人犹大原是十二使徒之一。|1.6
character|犹大|character|耶稣基督|BETRAYED|political|出卖|太26:14-16|加略人犹大出卖耶稣。|2.2
character|彼得|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:2|彼得属十二使徒。|1.6
character|安得烈|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:2|安得烈属十二使徒。|1.4
character|西庇太的雅各|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:2|属十二使徒。|1.4
character|约翰|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:2|约翰属十二使徒。|1.4
character|腓力|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:3|腓力属十二使徒。|1.4
character|巴多罗买|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:3|巴多罗买属十二使徒。|1.4
character|多马|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:3|多马属十二使徒。|1.4
character|马太|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:3|马太属十二使徒。|1.4
character|小雅各（亚勒腓之子）|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:3|属十二使徒。|1.4
character|达太|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:3|达太属十二使徒。|1.4
character|奋锐党的西门|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:4|属十二使徒。|1.4
character|犹大|group|twelve-apostles|MEMBER_OF|other|十二使徒|太10:4|加略人犹大原属十二使徒。|1.4
character|马提亚|group|twelve-apostles|MEMBER_OF|other|补选使徒|徒1:26|马提亚补选替代犹大。|1.4
character|罗波安|character|亚比央|FATHER_OF|family|父亲|王上14:31|罗波安生亚比央。|1.8
character|亚比央|character|亚撒|FATHER_OF|family|父亲|王上15:8|亚比央生亚撒。|1.8
character|亚撒|character|约沙法|FATHER_OF|family|父亲|王上15:24|亚撒生约沙法。|1.8
character|约沙法|character|约兰|FATHER_OF|family|父亲|王上22:50|约沙法生约兰。|1.6
character|约兰|character|亚哈谢|FATHER_OF|family|父亲|王下8:24|约兰生亚哈谢。|1.6
character|亚哈谢|character|约阿施|FATHER_OF|family|父亲|王下11:2|亚哈谢之子约阿施得存活。|1.6
character|约阿施|character|亚玛谢|FATHER_OF|family|父亲|王下12:21|约阿施生亚玛谢。|1.6
character|亚玛谢|character|乌西雅|FATHER_OF|family|父亲|王下14:21|亚玛谢之子乌西雅。|1.8
character|乌西雅|character|约坦|FATHER_OF|family|父亲|王下15:7|乌西雅生约坦。|1.8
character|约坦|character|亚哈斯|FATHER_OF|family|父亲|王下15:38|约坦生亚哈斯。|1.8
character|亚哈斯|character|希西家|FATHER_OF|family|父亲|王下16:20|亚哈斯生希西家。|2.0
character|希西家|character|玛拿西|FATHER_OF|family|父亲|王下20:21|希西家生玛拿西。|1.8
character|玛拿西|character|亚们|FATHER_OF|family|父亲|王下21:18|玛拿西生亚们。|1.6
character|亚们|character|约西亚|FATHER_OF|family|父亲|王下21:24|亚们生约西亚。|1.8
character|约西亚|character|约雅敬|FATHER_OF|family|父亲|王下23:34|约西亚之子约雅敬。|1.8
character|约西亚|character|约哈斯|FATHER_OF|family|父亲|王下23:30|约西亚之子约哈斯。|1.6
character|约西亚|character|西底家|FATHER_OF|family|父亲|王下24:18|约西亚之子西底家（末代王）。|1.8
character|约雅敬|character|约雅斤|FATHER_OF|family|父亲|王下24:6|约雅敬生约雅斤。|1.8
character|罗波安|nation|southern-judah|KING_OF|spiritual|君王|王上14:21|罗波安作犹大王。|1.6
character|亚撒|nation|southern-judah|KING_OF|spiritual|君王|王上15:9|亚撒作犹大王。|1.6
character|约沙法|nation|southern-judah|KING_OF|spiritual|君王|王上22:41|约沙法作犹大王。|1.6
character|约阿施|nation|southern-judah|KING_OF|spiritual|君王|王下12:1|约阿施作犹大王。|1.4
character|乌西雅|nation|southern-judah|KING_OF|spiritual|君王|王下15:1|乌西雅作犹大王。|1.6
character|亚哈斯|nation|southern-judah|KING_OF|spiritual|君王|王下16:1|亚哈斯作犹大王。|1.6
character|希西家|nation|southern-judah|KING_OF|spiritual|君王|王下18:1|希西家作犹大王。|1.8
character|玛拿西|nation|southern-judah|KING_OF|spiritual|君王|王下21:1|玛拿西作犹大王。|1.6
character|约西亚|nation|southern-judah|KING_OF|spiritual|君王|王下22:1|约西亚作犹大王。|1.8
character|西底家|nation|southern-judah|KING_OF|spiritual|君王|王下24:18|西底家是犹大末代王。|1.6
character|大卫|nation|united-kingdom|KING_OF|spiritual|君王|撒下5:4|大卫作全以色列的王。|2.0
character|所罗门|nation|united-kingdom|KING_OF|spiritual|君王|王上1:39|所罗门作全以色列的王。|1.8
character|扫罗|nation|united-kingdom|KING_OF|spiritual|君王|撒上11:15|扫罗是以色列第一位王。|1.8
character|耶罗波安|character|拿答|FATHER_OF|family|父亲|王上14:20|耶罗波安生拿答。|1.6
character|暗利|character|亚哈|FATHER_OF|family|父亲|王上16:28|暗利生亚哈。|1.8
character|耶户|character|约哈斯（北）|FATHER_OF|family|父亲|王下10:35|耶户生约哈斯。|1.6
character|约哈斯（北）|character|约阿施（北）|FATHER_OF|family|父亲|王下13:9|约哈斯生约阿施。|1.6
character|约阿施（北）|character|耶罗波安二世|FATHER_OF|family|父亲|王下13:13|约阿施生耶罗波安二世。|1.6
character|拿答|nation|northern-israel|KING_OF|spiritual|君王|王上15:25|拿答作以色列王。|1.4
character|暗利|nation|northern-israel|KING_OF|spiritual|君王|王上16:23|暗利建撒玛利亚作王。|1.6
character|亚哈|nation|northern-israel|KING_OF|spiritual|君王|王上16:29|亚哈作以色列王。|1.8
character|耶户|nation|northern-israel|KING_OF|spiritual|君王|王下10:36|耶户作以色列王。|1.6
character|约哈斯（北）|nation|northern-israel|KING_OF|spiritual|君王|王下13:1|约哈斯作以色列王。|1.4
character|约阿施（北）|nation|northern-israel|KING_OF|spiritual|君王|王下13:10|约阿施作以色列王。|1.4
character|耶罗波安二世|nation|northern-israel|KING_OF|spiritual|君王|王下14:23|耶罗波安二世使北国强盛。|1.6
character|何细亚|nation|northern-israel|KING_OF|spiritual|君王|王下17:1|何细亚是北国末代王。|1.6
character|拿单|character|大卫|PROPHET_OF|spiritual|先知|撒下7:2|拿单是大卫王的先知。|1.8
character|拿单|character|大卫|OPPOSED|event|责备|撒下12:7|拿单责备大卫的罪。|1.8
character|以利亚|character|亚哈|OPPOSED|event|对抗|王上18:18|以利亚对抗亚哈与巴力。|2.0
character|耶利米|character|西底家|PREACHED_TO|spiritual|劝告|耶38:14|耶利米向西底家传神的话。|1.6
character|米该雅|character|亚哈|OPPOSED|event|预言战死|王上22:17|米该雅预言亚哈必战死。|1.6
character|亚希雅|character|耶罗波安|ASSOCIATED_WITH|event|预言得国|王上11:30|亚希雅预言耶罗波安得十支派。|1.6
character|以利沙|character|耶户|ANOINTED|spiritual|膏立|王下9:6|以利沙差人膏耶户作王。|1.6
character|以利|character|撒母耳|MENTOR_OF|spiritual|师傅|撒上3:1|撒母耳在以利面前事奉学习。|1.8
character|拿俄米|character|路得|MENTOR_OF|spiritual|婆婆引导|得3:1|拿俄米引导路得寻得归宿。|1.6
$edges$, E'\n')), edge_seed AS (
  SELECT row_number() OVER () ord,p[1] source_kind,p[2] source_ref,p[3] target_kind,p[4] target_ref,p[5] relationship_type,p[6] relationship_category,p[7] label_zh,p[8] scripture_ref,p[9] description,p[10]::numeric weight
  FROM raw CROSS JOIN LATERAL (SELECT string_to_array(line,'|') p) x WHERE line<>'' AND line NOT LIKE '--%'),
 resolved AS (SELECT edge_seed.*, CASE WHEN source_kind='character' THEN sn.id ELSE source_kind||'-'||source_ref END source_node_id,
   CASE WHEN target_kind='character' THEN tn.id ELSE target_kind||'-'||target_ref END target_node_id
  FROM edge_seed
  LEFT JOIN biblical_characters sc ON source_kind='character' AND sc.name=source_ref AND sc.is_active=true
  LEFT JOIN biblical_graph_nodes sn ON sn.character_id=sc.id AND sn.is_active=true
  LEFT JOIN biblical_characters tc ON target_kind='character' AND tc.name=target_ref AND tc.is_active=true
  LEFT JOIN biblical_graph_nodes tn ON tn.character_id=tc.id AND tn.is_active=true)
INSERT INTO biblical_graph_edges (source_node_id,target_node_id,relationship_type,relationship_category,label_zh,label_en,scripture_ref,description,weight,confidence,is_directed,sort_order,scripture_refs,confidence_level)
SELECT source_node_id,target_node_id,relationship_type,relationship_category,label_zh,relationship_type,scripture_ref,description,weight,0.92,
  relationship_type NOT IN ('SPOUSE_OF','SIBLING_OF','ALLIED_WITH','FRIEND_OF'),66000+ord,ARRAY_REMOVE(ARRAY[scripture_ref],NULL),'high'
FROM resolved WHERE source_node_id IS NOT NULL AND target_node_id IS NOT NULL AND source_node_id<>target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=target_node_id) ON CONFLICT DO NOTHING;

-- inverse family / membership edges
WITH new_edges AS (SELECT * FROM biblical_graph_edges WHERE is_active=true AND sort_order BETWEEN 66000 AND 69999
   AND relationship_type IN ('FATHER_OF','MOTHER_OF','ANCESTOR_OF','MEMBER_OF','ANOINTED')),
inv AS (SELECT target_node_id source_node_id, source_node_id target_node_id,
  CASE relationship_type WHEN 'FATHER_OF' THEN 'CHILD_OF' WHEN 'MOTHER_OF' THEN 'CHILD_OF' WHEN 'ANCESTOR_OF' THEN 'DESCENDANT_OF' WHEN 'MEMBER_OF' THEN 'CONTAINS_MEMBER' WHEN 'ANOINTED' THEN 'ANOINTED_BY' END relationship_type,
  relationship_category,
  CASE relationship_type WHEN 'ANCESTOR_OF' THEN '后裔' WHEN 'MEMBER_OF' THEN '包含成员' WHEN 'ANOINTED' THEN '受膏于' ELSE '儿子/女儿' END label_zh,
  CASE relationship_type WHEN 'ANCESTOR_OF' THEN 'descendant of' WHEN 'MEMBER_OF' THEN 'contains member' WHEN 'ANOINTED' THEN 'anointed by' ELSE 'child of' END label_en,
  scripture_ref,'由 0066 自动生成的反向关系：'||description description,GREATEST(weight-0.2,0.1) weight,confidence,true is_directed,
  sort_order+100000 sort_order,scripture_refs,confidence_level FROM new_edges)
INSERT INTO biblical_graph_edges (source_node_id,target_node_id,relationship_type,relationship_category,label_zh,label_en,scripture_ref,description,weight,confidence,is_directed,sort_order,scripture_refs,confidence_level)
SELECT source_node_id,target_node_id,relationship_type,relationship_category,label_zh,label_en,scripture_ref,description,weight,confidence,is_directed,sort_order,scripture_refs,confidence_level
FROM inv WHERE source_node_id<>target_node_id ON CONFLICT DO NOTHING;

-- PART D. Defensive: if an earlier build wrongly linked the apostle 犹大 (Iscariot) into the
-- patriarch genealogy, deactivate those edges (the correct source is 犹大（雅各之子）).
UPDATE biblical_graph_edges e SET is_active=false
FROM biblical_graph_nodes sn JOIN biblical_characters sc ON sc.id=sn.character_id,
     biblical_graph_nodes tn JOIN biblical_characters tc ON tc.id=tn.character_id
WHERE e.is_active=true AND e.relationship_type='FATHER_OF'
  AND e.source_node_id=sn.id AND sc.name='犹大' AND sc.era='新约时代'
  AND e.target_node_id=tn.id AND tc.name IN ('法勒斯','谢拉（犹大之子）');

-- End of 0066.