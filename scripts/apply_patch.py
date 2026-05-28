#!/usr/bin/env python3
"""Apply enrichment patches to mirrorData.js characters."""
import json, re

PATCH_FILE = "scripts/character_patch.json"
JS_FILE = "emotion-sphere-ui/src/mirrorData.js"

with open(JS_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'(export const MIRROR_CHARACTERS = )(\[[\s\S]*?\])(;\s*\nexport const MIRROR_THEMES)', content)
chars_json = re.sub(r',(\s*[}\]])', r'\1', m.group(2))
chars = json.loads(chars_json)
by_id = {c['id']: c for c in chars}

with open(PATCH_FILE, 'r', encoding='utf-8') as f:
    patches = json.load(f)

count = 0
for patch in patches:
    cid = patch['id']
    if cid in by_id:
        by_id[cid].update(patch)
        count += 1

ordered = sorted(by_id.values(), key=lambda c: c['id'])
new_json = json.dumps(ordered, ensure_ascii=False, separators=(',', ':'))
new_content = content[:m.start(2)] + new_json + content[m.end(2):]

with open(JS_FILE, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Patched {count} characters successfully.")
