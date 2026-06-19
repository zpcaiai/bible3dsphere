# -*- coding: utf-8 -*-
"""Migration 0068: connect the last 7 isolated nodes (波提乏 & wife, 酒政/膳长,
但支派探子, 尼布沙斯班, 尼甲沙利薛) so every migration-added person has at least
one relationship in the graph. Same resolved-insert pattern as 0066."""
MIGDIR = "/sessions/exciting-determined-rubin/mnt/bible3dsphere/backend/migrations"
OUT = f"{MIGDIR}/0068_connect_isolated_nodes.sql"
C="character"; E="event"
EDGES = [
 (C,"波提乏",C,"波提乏的妻子","SPOUSE_OF","family","丈夫/妻子","创39","波提乏与其妻。",1.6),
 (C,"约瑟",C,"波提乏","SERVANT_OF","spiritual","管家","创39:1-6","约瑟作波提乏的管家。",1.8),
 (C,"波提乏的妻子",C,"约瑟","OPPOSED","event","诬陷","创39:7-20","波提乏的妻子诬陷约瑟下监。",1.8),
 (C,"波提乏",C,"法老","SERVANT_OF","spiritual","护卫长","创39:1","波提乏是法老的护卫长。",1.4),
 (C,"酒政",C,"约瑟","ASSOCIATED_WITH","event","蒙解梦","创40","约瑟为酒政解梦应验。",1.6),
 (C,"膳长",C,"约瑟","ASSOCIATED_WITH","event","蒙解梦","创40","约瑟为膳长解梦应验。",1.4),
 (C,"酒政",C,"法老","SERVANT_OF","spiritual","臣仆","创40:1-2","酒政是法老的臣仆。",1.4),
 (C,"膳长",C,"法老","SERVANT_OF","spiritual","臣仆","创40:1-2","膳长是法老的臣仆。",1.2),
 (C,"但支派探子",E,"judges-cycle","PARTICIPATED_IN","event","参与","士18","但支派探子夺米迦神像、迁居拉亿。",1.4),
 (C,"尼布沙斯班",C,"尼布甲尼撒","SERVANT_OF","spiritual","官长","耶39:13","尼布沙斯班是巴比伦的官长。",1.2),
 (C,"尼甲沙利薛",C,"尼布甲尼撒","SERVANT_OF","spiritual","官长","耶39:3","尼甲沙利薛是巴比伦的官长。",1.2),
 (C,"尼甲沙利薛",C,"尼布撒拉旦","ALLIED_WITH","political","同僚","耶39:3","同为攻陷耶路撒冷的巴比伦官长。",1.2),
 (C,"尼布沙斯班",C,"尼布撒拉旦","ALLIED_WITH","political","同僚","耶39:13","同为巴比伦的官长。",1.2),
]
elines = [f"{sk}|{sr}|{tk}|{tr}|{rel}|{cat}|{lab}|{scr}|{desc}|{w}" for (sk,sr,tk,tr,rel,cat,lab,scr,desc,w) in EDGES]
sql = """-- 0068_connect_isolated_nodes.sql
-- Final relationship pass: connect the 7 remaining isolated nodes so every
-- migration-added person has at least one edge in the knowledge graph.
WITH raw(line) AS (SELECT * FROM regexp_split_to_table($edges$
""" + "\n".join(elines) + """
$edges$, E'\\n')), edge_seed AS (
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
SELECT source_node_id,target_node_id,relationship_type,relationship_category,label_zh,relationship_type,scripture_ref,description,weight,0.9,
  relationship_type NOT IN ('SPOUSE_OF','SIBLING_OF','ALLIED_WITH','FRIEND_OF'),68000+ord,ARRAY_REMOVE(ARRAY[scripture_ref],NULL),'high'
FROM resolved WHERE source_node_id IS NOT NULL AND target_node_id IS NOT NULL AND source_node_id<>target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=target_node_id)
ON CONFLICT DO NOTHING;

-- End of 0068.
"""
open(OUT,"w",encoding="utf-8").write(sql)
print("WROTE",OUT,"edges",len(EDGES))
