# -*- coding: utf-8 -*-
"""Validate + emit migration 0064 SQL from gen_0064_data.py and gen_0064_edges.py."""
import sys
from gen_0064_data import (PEOPLE, NEW_NODES, NEW_RELTYPES, ALIASES, IMPORTANCE,
    DEACTIVATE_NODES, DEDUP_KEEP_MIN, BASE_EVENTS, BASE_GROUPS, BASE_NATIONS, BASE_PLACES,
    ERA_OK, ROLE_OK, TYPE_OK)
from gen_0064_edges import EDGES

EDGE_CAT_OK = {"family","spiritual","political","event","location","other"}
OUT = "/sessions/exciting-determined-rubin/mnt/bible3dsphere/backend/migrations/0064_expand_core_person_networks.sql"

# ---- Build name + node universes ----
existing = set(l.strip() for l in open('/tmp/existing_chars.txt',encoding='utf-8') if l.strip())
new_names = set(r[0] for r in PEOPLE)
name_universe = existing | new_names

node_slugs = set()
for kind,base in (("event",BASE_EVENTS),("group",BASE_GROUPS),("nation",BASE_NATIONS),("place",BASE_PLACES)):
    for s in base: node_slugs.add(f"{kind}-{s}")
# theme slugs known
for s in ("davidic-covenant","messianic-line","repentance","worship","christ-typology","spiritual-application"):
    node_slugs.add(f"theme-{s}")
for kind,slug,*_ in NEW_NODES:
    node_slugs.add(f"{kind}-{slug}")

# ---- Validate edges ----
errs=0; unresolved_chars=set(); warns=0
for i,e in enumerate(EDGES):
    if len(e)!=10: print("BAD EDGE FIELDS:",e); errs+=1; continue
    sk,sr,tk,tr,rel,cat,lab,scr,desc,w = e
    if cat not in EDGE_CAT_OK: print("BAD CAT:",rel,cat); errs+=1
    if not isinstance(w,(int,float)): print("BAD WEIGHT:",e); errs+=1
    for kind,ref in ((sk,sr),(tk,tr)):
        if kind=="character":
            if ref not in name_universe:
                unresolved_chars.add(ref); warns+=1
        else:
            nid=f"{kind}-{ref}"
            if nid not in node_slugs:
                print("UNKNOWN NODE SLUG:",nid,"in edge",rel,sr,"->",tr); errs+=1
if unresolved_chars:
    print(f"\n[warn] {len(unresolved_chars)} character refs not in known roster "
          f"(edges silently skipped at runtime). Review high-value ones:")
    print("  " + "，".join(sorted(unresolved_chars)))
print(f"\nEDGES: {len(EDGES)}  hard-errors: {errs}  soft-warns(unresolved char refs): {warns}")
if errs: print("ABORT: fix hard errors first."); sys.exit(1)

# =====================================================================
# Emit SQL
# =====================================================================
def q(s):  # SQL single-quote literal (no embedded quotes expected)
    assert "'" not in s, s
    return "'" + s + "'"

L=[]
L.append("""-- 0064_expand_core_person_networks.sql
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
""")

# ---- PART 0a: register new relationship types ----
L.append("-- ============================================================\n"
         "-- PART 0a. Register new relationship types (registry only; edges have no FK)\n"
         "-- ============================================================")
vals=[]
for rel,cat,zh,en,desc,inv in NEW_RELTYPES:
    inv_sql = q(inv) if inv else "NULL"
    vals.append(f"    ({q(rel)},{q(cat)},{q(zh)},{q(en)},{q(desc)},{inv_sql},ARRAY['character']::text[],900,false)")
L.append("INSERT INTO biblical_graph_relationship_types\n"
         "    (relationship_type, relationship_category, label_zh, label_en, description, inverse_type, target_types, sort_order, is_core)\nVALUES\n"
         + ",\n".join(vals) + "\nON CONFLICT (relationship_type) DO NOTHING;\n")

# ---- PART 0b: new non-character nodes ----
L.append("-- ============================================================\n"
         "-- PART 0b. New non-character graph nodes (place / event / nation / group / book)\n"
         "-- ============================================================")
node_lines=[]
for kind,slug,zh,en,cat,desc in NEW_NODES:
    node_lines.append(f"{kind}|{slug}|{zh}|{en}|{cat}|{desc}")
L.append("WITH raw(line) AS (\n    SELECT * FROM regexp_split_to_table($nodes$\n"
         + "\n".join(node_lines) +
         "\n$nodes$, E'\\n')\n), node_rows AS (\n"
         "    SELECT parts[1] AS node_type, parts[2] AS slug, parts[3] AS name,\n"
         "           parts[4] AS name_en, parts[5] AS category, parts[6] AS description\n"
         "    FROM raw CROSS JOIN LATERAL (SELECT string_to_array(line,'|') AS parts) p\n"
         "    WHERE line <> '' AND line NOT LIKE '--%'\n)\n"
         "INSERT INTO biblical_graph_nodes (id, node_type, name, name_en, category, description, chinese_name, english_name, testament)\n"
         "SELECT node_type||'-'||slug, node_type, name, name_en, category, description, name, name_en,\n"
         "       CASE WHEN node_type='nation' AND slug IN ('rome-empire') THEN 'New Testament' ELSE NULL END\n"
         "FROM node_rows\nON CONFLICT (id) DO NOTHING;\n")

# ---- PART A: people ----
L.append("-- ============================================================\n"
         "-- PART A. Insert people (镜鉴 character rows). name|name_en|era|role|type|scripture_ref|summary\n"
         "-- ============================================================")
plines=[f"{n}|{en}|{era}|{role}|{typ}|{ref}|{summ}" for (n,en,era,role,typ,ref,summ) in PEOPLE]
L.append("WITH raw(line) AS (\n    SELECT * FROM regexp_split_to_table($people$\n"
         + "\n".join(plines) +
         "\n$people$, E'\\n')\n), parsed AS (\n"
         "    SELECT string_to_array(line,'|') AS parts FROM raw WHERE line <> ''\n"
         "), person AS (\n"
         "    SELECT parts[1] AS name, parts[2] AS name_en, parts[3] AS era, parts[4] AS role,\n"
         "           parts[5] AS character_type, parts[6] AS scripture_ref, parts[7] AS summary\n"
         "    FROM parsed\n)\n"
         "INSERT INTO biblical_characters\n"
         "    (name, name_en, era, role, character_type, lesson, summary, witness, scripture_ref, prayer, is_active, sort_order)\n"
         "SELECT p.name, p.name_en, p.era, p.role, p.character_type,\n"
         "       p.name || '在圣经救赎历史中的位置与见证。', p.summary, p.summary, p.scripture_ref,\n"
         "       '愿我从' || p.name || '的记载中认识神在历史与群体中的作为。', true, 6400\n"
         "FROM person p\n"
         "WHERE NOT EXISTS (SELECT 1 FROM biblical_characters c WHERE c.name = p.name);\n")

# ---- PART B: generic node creation (verbatim from 0062) ----
L.append("""-- ============================================================
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
""")

# ---- PART B2: enrich (gender, importance tiers, aliases) ----
L.append("-- ============================================================\n"
         "-- PART B2. Enrichment: gender, S/A/B importance tiering, aliases\n"
         "-- ============================================================")
L.append("UPDATE biblical_graph_nodes n SET gender='female'\n"
         "FROM biblical_characters c\n"
         "WHERE n.character_id=c.id AND c.role='女性' AND (n.gender IS NULL OR n.gender='');")
L.append("UPDATE biblical_graph_nodes n SET gender='male'\n"
         "FROM biblical_characters c\n"
         "WHERE n.character_id=c.id AND c.role IN ('族长','君王','祭司','使徒') AND (n.gender IS NULL OR n.gender='');")
for lvl in ("S","A","B"):
    names = IMPORTANCE[lvl]
    inlist = ",".join(q(x) for x in names)
    L.append(f"UPDATE biblical_graph_nodes n SET importance_level={q(lvl)}\n"
             f"FROM biblical_characters c\n"
             f"WHERE n.character_id=c.id AND c.name IN ({inlist});")
for canonical, al in ALIASES.items():
    arr = "ARRAY[" + ",".join(q(a) for a in al) + "]::text[]"
    L.append(f"UPDATE biblical_graph_nodes n SET aliases = (\n"
             f"    SELECT ARRAY(SELECT DISTINCT unnest(COALESCE(n.aliases,'{{}}') || {arr}))\n"
             f")\nFROM biblical_characters c\n"
             f"WHERE n.character_id=c.id AND c.name={q(canonical)};")
L.append("")

# ---- PART C: edges ----
L.append("-- ============================================================\n"
         "-- PART C. Typed edges (the 12 subgraphs). \n"
         "-- src_kind|src_ref|tgt_kind|tgt_ref|rel|cat|label|scripture|desc|weight\n"
         "-- character refs resolve by name; unmatched rows are skipped.\n"
         "-- ============================================================")
elines=[]
for sk,sr,tk,tr,rel,cat,lab,scr,desc,w in EDGES:
    elines.append(f"{sk}|{sr}|{tk}|{tr}|{rel}|{cat}|{lab}|{scr}|{desc}|{w}")
L.append("WITH raw(line) AS (\n    SELECT * FROM regexp_split_to_table($edges$\n"
         + "\n".join(elines) +
         "\n$edges$, E'\\n')\n), edge_seed AS (\n"
         "    SELECT row_number() OVER () AS ord,\n"
         "        parts[1] AS source_kind, parts[2] AS source_ref, parts[3] AS target_kind,\n"
         "        parts[4] AS target_ref, parts[5] AS relationship_type, parts[6] AS relationship_category,\n"
         "        parts[7] AS label_zh, parts[8] AS scripture_ref, parts[9] AS description,\n"
         "        parts[10]::numeric AS weight\n"
         "    FROM raw CROSS JOIN LATERAL (SELECT string_to_array(line,'|') AS parts) parsed\n"
         "    WHERE line <> '' AND line NOT LIKE '--%'\n"
         "), resolved AS (\n"
         "    SELECT edge_seed.*,\n"
         "        CASE WHEN source_kind='character' THEN source_char_node.id ELSE source_kind||'-'||source_ref END AS source_node_id,\n"
         "        CASE WHEN target_kind='character' THEN target_char_node.id ELSE target_kind||'-'||target_ref END AS target_node_id\n"
         "    FROM edge_seed\n"
         "    LEFT JOIN biblical_characters source_char ON source_kind='character' AND source_char.name=source_ref AND source_char.is_active=true\n"
         "    LEFT JOIN biblical_graph_nodes source_char_node ON source_char_node.character_id=source_char.id AND source_char_node.is_active=true\n"
         "    LEFT JOIN biblical_characters target_char ON target_kind='character' AND target_char.name=target_ref AND target_char.is_active=true\n"
         "    LEFT JOIN biblical_graph_nodes target_char_node ON target_char_node.character_id=target_char.id AND target_char_node.is_active=true\n"
         ")\n"
         "INSERT INTO biblical_graph_edges (\n"
         "    source_node_id, target_node_id, relationship_type, relationship_category, label_zh, label_en,\n"
         "    scripture_ref, description, weight, confidence, is_directed, sort_order, scripture_refs, confidence_level\n)\n"
         "SELECT source_node_id, target_node_id, relationship_type, relationship_category, label_zh, relationship_type,\n"
         "    scripture_ref, description, weight, 0.9,\n"
         "    relationship_type NOT IN ('SPOUSE_OF','SIBLING_OF','ALLIED_WITH','FRIEND_OF'),\n"
         "    64000 + ord, ARRAY_REMOVE(ARRAY[scripture_ref], NULL), 'high'\n"
         "FROM resolved\n"
         "WHERE source_node_id IS NOT NULL AND target_node_id IS NOT NULL AND source_node_id <> target_node_id\n"
         "  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=source_node_id)\n"
         "  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=target_node_id)\n"
         "ON CONFLICT DO NOTHING;\n")

# ---- PART C inverse ----
L.append("""-- Auto-generate inverse edges for the family / membership relations added above.
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
""")

# ---- PART D: section-13 merges / dedup ----
L.append("-- ============================================================\n"
         "-- PART D. Section-13 cleanup: retire combined / duplicate graph nodes\n"
         "--   (individual constituents were added above as their own nodes/edges).\n"
         "-- ============================================================")
deact = ",".join(q(x) for x in DEACTIVATE_NODES)
L.append(f"-- Deactivate combined-card / duplicate graph nodes (keeps mirrorData frontend untouched).\n"
         f"UPDATE biblical_graph_edges e SET is_active=false\n"
         f"WHERE is_active=true AND (\n"
         f"    e.source_node_id IN (SELECT n.id FROM biblical_graph_nodes n JOIN biblical_characters c ON c.id=n.character_id WHERE c.name IN ({deact}))\n"
         f"    OR e.target_node_id IN (SELECT n.id FROM biblical_graph_nodes n JOIN biblical_characters c ON c.id=n.character_id WHERE c.name IN ({deact}))\n"
         f");")
L.append(f"UPDATE biblical_graph_nodes n SET is_active=false\n"
         f"FROM biblical_characters c\n"
         f"WHERE n.character_id=c.id AND c.name IN ({deact});")
# Dedup: keep MIN(id), deactivate the rest, for names with duplicate cards.
ddl = ",".join(q(x) for x in DEDUP_KEEP_MIN)
L.append(f"-- Deduplicate cards sharing a name: keep the lowest id, retire the rest.\n"
         f"WITH dups AS (\n"
         f"    SELECT id, name, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS rn\n"
         f"    FROM biblical_characters WHERE name IN ({ddl})\n"
         f")\n"
         f"UPDATE biblical_graph_nodes n SET is_active=false\n"
         f"FROM dups WHERE n.character_id=dups.id AND dups.rn > 1;")
L.append("")
L.append("-- End of 0064.")

sql="\n".join(L)
open(OUT,"w",encoding="utf-8").write(sql)
print(f"WROTE {OUT}")
print(f"  people={len(PEOPLE)} nodes={len(NEW_NODES)} reltypes={len(NEW_RELTYPES)} edges={len(EDGES)}")
print(f"  SQL size: {len(sql)} bytes, {sql.count(chr(10))} lines")
