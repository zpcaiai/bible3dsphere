# -*- coding: utf-8 -*-
"""Build migration 0067: sync the full 镜鉴 card content (lesson/witness/summary/
prayer + follow/caution/applications/scriptures/tags) from mirrorData.js into the
DB for every migration-added person, replacing the placeholder text inserted by
0064/0065/0066. Uses an embedded JSON document + set-based UPDATE/INSERT. Idempotent."""
import json, re, glob, subprocess

MD = "/sessions/exciting-determined-rubin/mnt/bible3dsphereWeb/src/mirrorData.js"
MIGDIR = "/sessions/exciting-determined-rubin/mnt/bible3dsphere/backend/migrations"
OUT = f"{MIGDIR}/0067_sync_card_content_to_db.sql"

# migration-added people (names)
mignames = set()
for f in sorted(glob.glob(f"{MIGDIR}/00*.sql")):
    for line in open(f, encoding="utf-8"):
        s = line.strip()
        if s.startswith("--") or "|" not in s: continue
        p = s.split("|")
        if len(p) == 7 and re.search(r"(时代|时期)$", p[2].strip()) and re.match(r"^[一-鿿]", p[0]):
            mignames.add(p[0].strip())

# export all cards, filter to migration people
NODE = "import('file://%s').then(m=>console.log(JSON.stringify(m.MIRROR_CHARACTERS)));" % MD
cards = json.loads(subprocess.check_output(["node", "--input-type=module", "-e", NODE]).decode())
rows = []
for c in cards:
    if c["name"] not in mignames: continue
    rows.append({
        "name": c["name"], "lesson": c.get("lesson", ""), "witness": c.get("witness", ""),
        "summary": c.get("summary", ""), "prayer": c.get("prayer", ""),
        "tags": c.get("tags", []), "follow": c.get("follow", []),
        "caution": c.get("caution", []), "applications": c.get("applications", []),
        "scriptures": c.get("scriptures", []),
    })
print(f"syncing {len(rows)} people (of {len(mignames)} migration people)")

payload = json.dumps(rows, ensure_ascii=False)
assert "$json$" not in payload

sql = f"""-- 0067_sync_card_content_to_db.sql
-- Sync full 镜鉴 card content (lesson/witness/summary/prayer + follow/caution/
-- applications/scriptures/tags) from the frontend mirrorData.js into the DB for
-- every migration-added person, replacing the placeholder text from 0064-0066.
-- Embedded JSON + set-based UPDATE/INSERT. Idempotent (NOT EXISTS / ON CONFLICT).

CREATE TEMP TABLE _card_sync ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset($json${payload}$json$::jsonb)
  AS x(name text, lesson text, witness text, summary text, prayer text,
       tags jsonb, follow jsonb, caution jsonb, applications jsonb, scriptures jsonb);

-- 1) main fields
UPDATE biblical_characters c
SET lesson = LEFT(d.lesson, 200), witness = d.witness, summary = d.summary,
    prayer = d.prayer, updated_at = NOW()
FROM _card_sync d
WHERE c.name = d.name AND c.is_active = true;

-- 2) tags
INSERT INTO character_tags (character_id, tag)
SELECT c.id, t.tag
FROM _card_sync d
JOIN biblical_characters c ON c.name = d.name AND c.is_active = true,
     LATERAL jsonb_array_elements_text(d.tags) AS t(tag)
ON CONFLICT (character_id, tag) DO NOTHING;

-- 3) follow points
INSERT INTO character_follow_points (character_id, content, sort_order)
SELECT c.id, e.content, e.ord
FROM _card_sync d
JOIN biblical_characters c ON c.name = d.name AND c.is_active = true,
     LATERAL jsonb_array_elements_text(d.follow) WITH ORDINALITY AS e(content, ord)
WHERE NOT EXISTS (SELECT 1 FROM character_follow_points f
                  WHERE f.character_id = c.id AND f.content = e.content);

-- 4) caution points
INSERT INTO character_caution_points (character_id, content, sort_order)
SELECT c.id, e.content, e.ord
FROM _card_sync d
JOIN biblical_characters c ON c.name = d.name AND c.is_active = true,
     LATERAL jsonb_array_elements_text(d.caution) WITH ORDINALITY AS e(content, ord)
WHERE NOT EXISTS (SELECT 1 FROM character_caution_points f
                  WHERE f.character_id = c.id AND f.content = e.content);

-- 5) applications
INSERT INTO character_applications (character_id, content, sort_order)
SELECT c.id, e.content, e.ord
FROM _card_sync d
JOIN biblical_characters c ON c.name = d.name AND c.is_active = true,
     LATERAL jsonb_array_elements_text(d.applications) WITH ORDINALITY AS e(content, ord)
WHERE NOT EXISTS (SELECT 1 FROM character_applications f
                  WHERE f.character_id = c.id AND f.content = e.content);

-- 6) scriptures
INSERT INTO character_scriptures (character_id, reference, sort_order)
SELECT c.id, e.reference, e.ord
FROM _card_sync d
JOIN biblical_characters c ON c.name = d.name AND c.is_active = true,
     LATERAL jsonb_array_elements_text(d.scriptures) WITH ORDINALITY AS e(reference, ord)
WHERE NOT EXISTS (SELECT 1 FROM character_scriptures f
                  WHERE f.character_id = c.id AND f.reference = e.reference);

-- End of 0067.
"""
open(OUT, "w", encoding="utf-8").write(sql)
print("WROTE", OUT, "bytes", len(sql))
