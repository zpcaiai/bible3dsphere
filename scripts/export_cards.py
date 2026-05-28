#!/usr/bin/env python3
import json, re, sys

start_id = int(sys.argv[1]) if len(sys.argv) > 1 else 51
end_id = int(sys.argv[2]) if len(sys.argv) > 2 else 120
out_file = sys.argv[3] if len(sys.argv) > 3 else f"scripts/characters_{start_id}_{end_id}.md"

with open('emotion-sphere-ui/src/mirrorData.js', 'r') as f:
    content = f.read()

m = re.search(r'export const MIRROR_CHARACTERS = (\[[\s\S]*?\]);', content)
raw = m.group(1)
raw = re.sub(r',(\s*[}\]])', r'\1', raw)
chars = json.loads(raw)

lines = [f"# 人物卡片 ID {start_id}–{end_id}\n"]

for c in sorted(chars, key=lambda x: x['id']):
    if start_id <= c['id'] <= end_id:
        lines.append(f"## ID {c['id']} {c['name']} ({c['en']})")
        lines.append(f"**时代：** {c['era']} | **角色：** {c['role']} | **类型：** {c['type']}")
        lines.append(f"**功课：** {c['lesson']}")
        lines.append(f"**摘要：** {c['summary']}")
        lines.append(f"**见证：** {c['witness']}")
        follow = c.get('follow', [])
        lines.append("**效法：** " + ("；".join(follow) if follow else "—"))
        caution = c.get('caution', [])
        lines.append("**警戒：** " + ("；".join(caution) if caution else "—"))
        apps = c.get('applications', [])
        lines.append("**应用：** " + ("；".join(apps) if apps else "—"))
        lines.append(f"**祷告：** {c.get('prayer', '')}")
        lines.append("")
        lines.append("---")
        lines.append("")

with open(out_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

count = sum(1 for c in chars if start_id <= c['id'] <= end_id)
print(f"写入完成：{out_file}，共 {count} 个人物")
