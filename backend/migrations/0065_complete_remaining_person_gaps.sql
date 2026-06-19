-- 0065_complete_remaining_person_gaps.sql
-- Final coverage pass: Ruth's family, David's wife & remaining mighty men, Lot's wife,
-- foreign kings (Achish/Hanun/Nahash/Evil-merodach), NT individuals (Joanna, Susanna,
-- Annas, Phoebe, Nero), parable figures, and the scribe/Pharisee/Sadducee/Herodian
-- group nodes. Splits the combined 迷失的羊/儿子 and 利未人与他的妾 cards into
-- independent graph nodes. Same idempotent pattern as 0064.

SELECT setval(pg_get_serial_sequence('biblical_characters','id'),
              COALESCE((SELECT MAX(id) FROM biblical_characters),0));

-- PART A. People (镜鉴 rows)
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($people$
以利米勒|Elimelech|士师时代|其他|混合|得1:1-3|拿俄米的丈夫，因饥荒带全家迁往摩押，客死他乡。
玛伦|Mahlon|士师时代|其他|混合|得1:2-5|以利米勒之子，路得的前夫，死于摩押。
基连|Chilion|士师时代|其他|混合|得1:2-5|以利米勒之子，俄珥巴的丈夫，死于摩押。
亚希暖|Ahinoam|王国时代|女性|混合|撒上25:43|耶斯列人，大卫的妻子，暗嫩的母亲。
以特买|Ithmah|王国时代|其他|正面|代上11:46|摩押人，大卫的勇士之一。
希勒斯|Helez|王国时代|其他|正面|撒下23:26|巴勒提人，大卫的勇士之一。
希莱|Heleb|王国时代|其他|正面|撒下23:29|尼陀法人，大卫的勇士之一。
罗得的妻子|Lot's wife|族长时代|女性|警戒|创19:26|逃离所多玛时因回头观看而变成盐柱。
亚吉|Achish|王国时代|君王|混合|撒上27:1-12|迦特的非利士王，大卫逃避扫罗时投奔他。
哈嫩|Hanun|王国时代|君王|警戒|撒下10|亚扪王，羞辱大卫的使者，引发战争。
拿辖|Nahash|王国时代|君王|混合|撒上11|亚扪王，围困基列雅比，被扫罗击败。
以未米罗达|Evil-merodach|被掳归回时代|君王|混合|王下25:27-30|巴比伦王，释放被囚的约雅斤并恩待他。
约亚拿|Joanna|新约时代|女性|正面|路8:3;24:10|希律家宰苦撒的妻子，供给耶稣、复活的见证人。
苏撒拿|Susanna|新约时代|女性|正面|路8:3|供给耶稣和门徒所需的妇女之一。
亚那|Annas|新约时代|祭司|警戒|约18:13;路3:2|前任大祭司，该亚法的岳父，参与审问耶稣。
非比|Phoebe|新约时代|女性|正面|罗16:1-2|坚革哩教会的女执事，保罗所推荐、可能携带罗马书的人。
尼禄|Nero|新约时代|君王|警戒|徒25:11;提后4:16-17|保罗上诉的罗马皇帝（该撒），传统上保罗殉道时期的皇帝。
浪子|The Prodigal Son|新约时代|其他|混合|路15:11-32|挥霍家产后悔改归家的小儿子。
浪子的父亲|Father of the Prodigal|新约时代|其他|正面|路15:20-24|盼望并欢喜迎接浪子回家的父亲，预表天父的慈爱。
浪子的哥哥|Elder Brother|新约时代|其他|警戒|路15:25-32|因父亲接纳弟弟而嫉妒愤怒的大儿子。
财主（与拉撒路）|Rich Man (and Lazarus)|新约时代|其他|警戒|路16:19-31|比喻中宴乐无度、死后受苦的财主。
不义的管家|Unjust Steward|新约时代|其他|混合|路16:1-8|比喻中精明却不义、为自己预备后路的管家。
迷失的羊|The Lost Sheep|新约时代|其他|正面|路15:3-7|比喻中失而复得的羊，象征罪人悔改、牧人寻回。
悔改的强盗|Penitent thief|新约时代|其他|正面|路23:39-43|与耶稣同钉、悔改求主记念、蒙应许同进乐园的强盗。
讥诮的强盗|Impenitent thief|新约时代|其他|警戒|路23:39|与耶稣同钉、讥诮主的另一个强盗。
文士|Scribes|新约时代|其他|混合|太23|抄写、教导律法的宗教学者群体，常与耶稣冲突。
法利赛人|Pharisees|新约时代|其他|混合|太23|严守律法传统的犹太教派，常被耶稣责备假冒为善。
撒都该人|Sadducees|新约时代|其他|混合|太22:23|祭司贵族教派，不信复活。
希律党人|Herodians|新约时代|其他|混合|可3:6|拥护希律王朝的政治群体，与法利赛人合谋陷害耶稣。
基比亚的利未人|The Levite of Gibeah|士师时代|其他|警戒|士19|带妾返家、在基比亚遭遇暴行的利未人。
利未人的妾|The Levite's concubine|士师时代|女性|警戒|士19|在基比亚被凌辱致死，引发支派内战。
$people$, E'\n')
), parsed AS (SELECT string_to_array(line,'|') AS p FROM raw WHERE line<>''), person AS (SELECT p[1] name,p[2] name_en,p[3] era,p[4] role,p[5] character_type,p[6] scripture_ref,p[7] summary FROM parsed)
INSERT INTO biblical_characters (name,name_en,era,role,character_type,lesson,summary,witness,scripture_ref,prayer,is_active,sort_order)
SELECT name,name_en,era,role,character_type, name||'在圣经救赎历史中的位置与见证。', summary, summary, scripture_ref, '愿我从'||name||'的记载中认识神在历史与群体中的作为。', true, 6500
FROM person p WHERE NOT EXISTS (SELECT 1 FROM biblical_characters c WHERE c.name=p.name);

-- PART B. Create graph nodes for new non-教会时代 characters
INSERT INTO biblical_graph_nodes (id,node_type,name,name_en,category,description,character_id,chinese_name,english_name,aliases,testament,era,role_labels,importance_level,first_appearance,related_books,key_events,theological_themes,moral_evaluation,summary)
SELECT 'char-'||c.id,'character',c.name,c.name_en,c.role,c.summary,c.id,c.name,c.name_en,ARRAY_REMOVE(ARRAY[c.name,c.name_en],NULL),
    CASE WHEN c.era ILIKE '%新约%' THEN 'New Testament' WHEN c.era ILIKE '%两约%' THEN 'Intertestamental' ELSE 'Old Testament' END,
    c.era,ARRAY_REMOVE(ARRAY[c.role],NULL),'C',c.scripture_ref,ARRAY_REMOVE(ARRAY[c.scripture_ref],NULL),ARRAY_REMOVE(ARRAY[c.lesson],NULL),
    ARRAY_REMOVE(ARRAY[c.role,c.character_type],NULL),
    CASE c.character_type WHEN '正面' THEN 'positive' WHEN '警戒' THEN 'negative' ELSE 'mixed' END,c.summary
FROM biblical_characters c
WHERE c.is_active=true AND c.era<>'教会时代' AND NOT EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.character_id=c.id)
ON CONFLICT (id) DO NOTHING;

-- PART B2. gender + importance
UPDATE biblical_graph_nodes n SET gender='female' FROM biblical_characters c WHERE n.character_id=c.id AND c.role='女性' AND (n.gender IS NULL OR n.gender='');
UPDATE biblical_graph_nodes n SET gender='male' FROM biblical_characters c WHERE n.character_id=c.id AND c.role IN ('族长','君王','祭司','使徒') AND (n.gender IS NULL OR n.gender='');
UPDATE biblical_graph_nodes n SET importance_level='A' FROM biblical_characters c WHERE n.character_id=c.id AND c.name IN ('非比');
UPDATE biblical_graph_nodes n SET importance_level='B' FROM biblical_characters c WHERE n.character_id=c.id AND c.name IN ('亚那','尼禄','约亚拿','亚吉','拿辖','浪子','浪子的父亲','悔改的强盗');
UPDATE biblical_graph_nodes n SET aliases=(SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}')||ARRAY['财主']::text[]))) FROM biblical_characters c WHERE n.character_id=c.id AND c.name='财主（与拉撒路）';
UPDATE biblical_graph_nodes n SET aliases=(SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}')||ARRAY['不义管家']::text[]))) FROM biblical_characters c WHERE n.character_id=c.id AND c.name='不义的管家';
UPDATE biblical_graph_nodes n SET aliases=(SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{}')||ARRAY['另一个强盗','不悔改的强盗']::text[]))) FROM biblical_characters c WHERE n.character_id=c.id AND c.name='讥诮的强盗';

-- PART C. Edges
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($edges$
character|以利米勒|character|拿俄米|SPOUSE_OF|family|丈夫/妻子|得1:2|以利米勒与拿俄米。|1.8
character|以利米勒|character|玛伦|FATHER_OF|family|父亲|得1:2|以利米勒之子玛伦。|1.8
character|以利米勒|character|基连|FATHER_OF|family|父亲|得1:2|以利米勒之子基连。|1.8
character|拿俄米|character|玛伦|MOTHER_OF|family|母亲|得1:2|拿俄米是玛伦的母亲。|1.6
character|拿俄米|character|基连|MOTHER_OF|family|母亲|得1:2|拿俄米是基连的母亲。|1.6
character|玛伦|character|路得|SPOUSE_OF|family|丈夫/妻子|得4:10|玛伦原是路得的丈夫。|1.8
character|基连|character|俄珥巴|SPOUSE_OF|family|丈夫/妻子|得1:4|基连是俄珥巴的丈夫。|1.6
character|玛伦|character|基连|SIBLING_OF|family|兄弟|得1:2|玛伦与基连是兄弟。|1.4
character|以利米勒|place|bethlehem|LIVED_IN|location|本乡|得1:1|以利米勒是伯利恒人。|1.4
character|以利米勒|nation|moab|TRAVELED_TO|political|寄居|得1:1|以利米勒因饥荒迁往摩押。|1.4
character|大卫|character|亚希暖|SPOUSE_OF|family|丈夫/妻子|撒上25:43|亚希暖是大卫的妻子。|1.6
character|亚希暖|character|暗嫩|MOTHER_OF|family|母亲|撒下3:2|亚希暖是暗嫩的母亲。|1.6
character|以特买|character|大卫|SERVANT_OF|spiritual|勇士|代上11:46|以特买是大卫的勇士。|1.4
character|希勒斯|character|大卫|SERVANT_OF|spiritual|勇士|撒下23:26|希勒斯是大卫的勇士。|1.4
character|希莱|character|大卫|SERVANT_OF|spiritual|勇士|撒下23:29|希莱是大卫的勇士。|1.4
character|罗得|character|罗得的妻子|SPOUSE_OF|family|丈夫/妻子|创19:15|罗得与他的妻子。|1.6
character|罗得的妻子|event|creation-fall|WITNESSED|event|所多玛之灾|创19:26|回头观看而变成盐柱。|1.2
character|亚吉|nation|philistia|KING_OF|spiritual|君王|撒上27:2|亚吉是迦特的非利士王。|1.6
character|亚吉|character|大卫|PROTECTED|event|收留|撒上27:6|亚吉收留大卫并赐洗革拉。|1.6
character|大卫|place|ziklag|LIVED_IN|location|寄居|撒上27:6|亚吉将洗革拉赐给大卫居住。|1.4
character|哈嫩|nation|ammon|KING_OF|spiritual|君王|撒下10:1|哈嫩是亚扪王。|1.6
character|哈嫩|character|大卫|OPPOSED|event|羞辱使者|撒下10:4|哈嫩羞辱大卫的使者。|1.6
character|大卫|character|哈嫩|DEFEATED|political|击败|撒下10:14|大卫击败亚扪与亚兰联军。|1.6
character|拿辖|nation|ammon|KING_OF|spiritual|君王|撒上11:1|拿辖是亚扪王。|1.4
character|拿辖|character|哈嫩|FATHER_OF|family|父亲|撒下10:1|哈嫩是拿辖之子。|1.4
character|拿辖|group|israelites|ATTACKED|political|围困|撒上11:1|拿辖围困基列雅比。|1.4
character|扫罗|character|拿辖|DEFEATED|political|击败|撒上11:11|扫罗击败亚扪王拿辖。|1.6
character|以未米罗达|nation|babylon-empire|KING_OF|spiritual|君王|王下25:27|以未米罗达是巴比伦王。|1.4
character|以未米罗达|character|约雅斤|PROTECTED|event|释放|王下25:27|以未米罗达释放并恩待约雅斤。|1.6
character|约亚拿|character|耶稣基督|ASSOCIATED_WITH|event|供给随从|路8:3|约亚拿用财物供给耶稣。|1.6
character|约亚拿|event|resurrection|WITNESSED|event|见证空坟|路24:10|约亚拿是空坟墓的见证人之一。|1.6
character|苏撒拿|character|耶稣基督|ASSOCIATED_WITH|event|供给随从|路8:3|苏撒拿供给耶稣和门徒。|1.4
character|亚那|character|耶稣基督|OPPOSED|event|审问|约18:13|亚那先审问耶稣。|1.6
character|亚那|character|该亚法|ASSOCIATED_WITH|family|岳父|约18:13|亚那是该亚法的岳父。|1.4
character|亚那|group|priesthood|MEMBER_OF|other|大祭司|路3:2|亚那曾任大祭司。|1.4
character|亚那|character|撒都该人|MEMBER_OF|other|教派|徒5:17|大祭司家族属撒都该人。|1.2
character|非比|group|early-church|MEMBER_OF|other|女执事|罗16:1|非比是坚革哩教会的女执事。|1.6
character|非比|character|保罗|ASSOCIATED_WITH|event|受推荐送信|罗16:2|非比受保罗推荐，或携带罗马书。|1.6
character|尼禄|nation|rome-empire|RULED_OVER|political|作皇帝|徒25:11|尼禄是保罗上诉的该撒。|1.6
character|保罗|character|尼禄|ASSOCIATED_WITH|event|上诉该撒|徒25:11|保罗上诉于该撒（尼禄）。|1.6
character|尼禄|group|early-church|OPPOSED|event|逼迫|提后4:16|传统上尼禄逼迫教会、保罗殉道于其时。|1.4
character|浪子的父亲|character|浪子|FATHER_OF|family|父亲|路15:11|父亲有两个儿子。|1.6
character|浪子的父亲|character|浪子的哥哥|FATHER_OF|family|父亲|路15:11|父亲的大儿子。|1.6
character|浪子|character|浪子的哥哥|SIBLING_OF|family|兄弟|路15:25|浪子与哥哥是兄弟。|1.4
character|浪子|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路15:13|浪子的比喻。|1.4
character|浪子的父亲|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路15:20|慈父的比喻。|1.4
character|浪子的哥哥|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路15:28|大儿子的比喻。|1.2
character|浪子|theme|repentance|HAS_THEME|other|主题|路15:18|浪子悔改归家。|1.6
character|浪子的父亲|theme|christ-typology|HAS_THEME|other|主题|路15:20|慈父预表天父的赦免之爱。|1.4
character|财主（与拉撒路）|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路16:19|财主与拉撒路的比喻。|1.4
character|不义的管家|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路16:1|不义管家的比喻。|1.4
character|迷失的羊|event|parable-figures|PARTICIPATED_IN|event|比喻人物|路15:4|迷失之羊的比喻。|1.4
character|迷失的羊|theme|repentance|HAS_THEME|other|主题|路15:7|一个罪人悔改，天上欢喜。|1.4
character|悔改的强盗|event|crucifixion|PARTICIPATED_IN|event|同钉十架|路23:40|悔改的强盗与耶稣同钉。|1.6
character|讥诮的强盗|event|crucifixion|PARTICIPATED_IN|event|同钉十架|路23:39|讥诮的强盗与耶稣同钉。|1.4
character|悔改的强盗|character|耶稣基督|ASSOCIATED_WITH|event|蒙应许乐园|路23:43|主应许他同进乐园。|1.6
character|悔改的强盗|theme|repentance|HAS_THEME|other|主题|路23:42|临终悔改求主记念。|1.4
character|法利赛人|character|耶稣基督|OPPOSED|event|敌对|太23|法利赛人多次与耶稣冲突。|1.8
character|撒都该人|character|耶稣基督|OPPOSED|event|质问|太22:23|撒都该人以复活的问题试探耶稣。|1.6
character|文士|character|耶稣基督|OPPOSED|event|敌对|太23|文士与法利赛人一同敌对耶稣。|1.6
character|希律党人|character|耶稣基督|OPPOSED|event|谋害|可3:6|希律党人与法利赛人合谋害耶稣。|1.6
character|法利赛人|character|希律党人|ALLIED_WITH|political|合谋|可3:6|法利赛人与希律党人合谋。|1.4
character|尼哥底母|character|法利赛人|MEMBER_OF|other|教派|约3:1|尼哥底母是法利赛人。|1.4
character|迦玛列|character|法利赛人|MEMBER_OF|other|教派|徒5:34|迦玛列是法利赛教师。|1.4
character|保罗|character|法利赛人|MEMBER_OF|other|教派|徒23:6|保罗自称是法利赛人。|1.6
character|该亚法|character|撒都该人|MEMBER_OF|other|教派|徒5:17|大祭司家族属撒都该人。|1.2
character|基比亚的利未人|character|利未人的妾|SPOUSE_OF|family|丈夫/妾|士19:1|利未人与他的妾。|1.4
character|利未人的妾|event|judges-cycle|DIED_IN|event|基比亚暴行|士19:28|妾在基比亚被凌辱致死。|1.4
character|基比亚的利未人|event|judges-cycle|PARTICIPATED_IN|event|引发内战|士20|事件引发以色列对便雅悯的战争。|1.4
$edges$, E'\n')
), edge_seed AS (
  SELECT row_number() OVER () ord, p[1] source_kind,p[2] source_ref,p[3] target_kind,p[4] target_ref,p[5] relationship_type,p[6] relationship_category,p[7] label_zh,p[8] scripture_ref,p[9] description,p[10]::numeric weight
  FROM raw CROSS JOIN LATERAL (SELECT string_to_array(line,'|') p) x WHERE line<>'' AND line NOT LIKE '--%'
), resolved AS (
  SELECT edge_seed.*, CASE WHEN source_kind='character' THEN sn.id ELSE source_kind||'-'||source_ref END source_node_id,
         CASE WHEN target_kind='character' THEN tn.id ELSE target_kind||'-'||target_ref END target_node_id
  FROM edge_seed
  LEFT JOIN biblical_characters sc ON source_kind='character' AND sc.name=source_ref AND sc.is_active=true
  LEFT JOIN biblical_graph_nodes sn ON sn.character_id=sc.id AND sn.is_active=true
  LEFT JOIN biblical_characters tc ON target_kind='character' AND tc.name=target_ref AND tc.is_active=true
  LEFT JOIN biblical_graph_nodes tn ON tn.character_id=tc.id AND tn.is_active=true)
INSERT INTO biblical_graph_edges (source_node_id,target_node_id,relationship_type,relationship_category,label_zh,label_en,scripture_ref,description,weight,confidence,is_directed,sort_order,scripture_refs,confidence_level)
SELECT source_node_id,target_node_id,relationship_type,relationship_category,label_zh,relationship_type,scripture_ref,description,weight,0.9,
  relationship_type NOT IN ('SPOUSE_OF','SIBLING_OF','ALLIED_WITH','FRIEND_OF'),65000+ord,ARRAY_REMOVE(ARRAY[scripture_ref],NULL),'high'
FROM resolved WHERE source_node_id IS NOT NULL AND target_node_id IS NOT NULL AND source_node_id<>target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=target_node_id)
ON CONFLICT DO NOTHING;

-- inverse family / membership / death edges
WITH new_edges AS (SELECT * FROM biblical_graph_edges WHERE is_active=true AND sort_order BETWEEN 65000 AND 69999
   AND relationship_type IN ('FATHER_OF','MOTHER_OF','MEMBER_OF')),
inv AS (SELECT target_node_id source_node_id, source_node_id target_node_id,
  CASE relationship_type WHEN 'FATHER_OF' THEN 'CHILD_OF' WHEN 'MOTHER_OF' THEN 'CHILD_OF' WHEN 'MEMBER_OF' THEN 'CONTAINS_MEMBER' END relationship_type,
  relationship_category,
  CASE relationship_type WHEN 'MEMBER_OF' THEN '包含成员' ELSE '儿子/女儿' END label_zh,
  CASE relationship_type WHEN 'MEMBER_OF' THEN 'contains member' ELSE 'child of' END label_en,
  scripture_ref, '由 0065 自动生成的反向关系：'||description description, GREATEST(weight-0.2,0.1) weight, confidence, true is_directed,
  sort_order+100000 sort_order, scripture_refs, confidence_level FROM new_edges)
INSERT INTO biblical_graph_edges (source_node_id,target_node_id,relationship_type,relationship_category,label_zh,label_en,scripture_ref,description,weight,confidence,is_directed,sort_order,scripture_refs,confidence_level)
SELECT source_node_id,target_node_id,relationship_type,relationship_category,label_zh,label_en,scripture_ref,description,weight,confidence,is_directed,sort_order,scripture_refs,confidence_level
FROM inv WHERE source_node_id<>target_node_id ON CONFLICT DO NOTHING;

-- PART D. Retire combined cards now split into independent nodes
UPDATE biblical_graph_edges e SET is_active=false WHERE is_active=true AND (
  e.source_node_id IN (SELECT n.id FROM biblical_graph_nodes n JOIN biblical_characters c ON c.id=n.character_id WHERE c.name IN ('迷失的羊/儿子','利未人与他的妾（士师记）'))
  OR e.target_node_id IN (SELECT n.id FROM biblical_graph_nodes n JOIN biblical_characters c ON c.id=n.character_id WHERE c.name IN ('迷失的羊/儿子','利未人与他的妾（士师记）')));
UPDATE biblical_graph_nodes n SET is_active=false FROM biblical_characters c WHERE n.character_id=c.id AND c.name IN ('迷失的羊/儿子','利未人与他的妾（士师记）');

-- End of 0065.