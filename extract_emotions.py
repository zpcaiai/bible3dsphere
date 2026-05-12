#!/usr/bin/env python3
import json

with open('emotion_sphere_layout.json', 'r') as f:
    data = json.load(f)

# Sort by index
emotions = []
for i, item in enumerate(data):
    zh = item.get('zh_label', '')
    en = item.get('short_en', '')
    if zh and en:
        emotions.append((i+1, zh, en))

# Print as formatted list
print(f'共 {len(emotions)} 个情绪词汇\n')
print('| 序号 | 中文 | 英文 |')
print('|------|------|------|')
for idx, zh, en in emotions:
    print(f'| {idx} | {zh} | {en} |')
