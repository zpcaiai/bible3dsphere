#!/usr/bin/env python3
import json

# 扩展翻译映射（127个未匹配词汇）
EXTRA = {
    "absolution": "赦免", "adoration": "敬爱", "affect": "情感", "affective experience": "情感体验",
    "affirmation": "肯定", "agitation": "躁动", "alarm": "惊觉", "ambiance": "氛围", "ambivalence": "矛盾",
    "anguish": "极度痛苦", "appraisal": "评价", "approval": "认可", "ardor": "热忱", "articulation": "倾诉",
    "aspiration": "志向", "atmosphere": "气氛", "attachment": "依恋", "awakening": "觉醒", "awareness": "觉察",
    "benevolence": "仁慈", "bittersweet": "苦乐参半", "bliss": "极乐", "camaraderie": "情谊", "charm": "魅力",
    "collective mood": "集体情绪", "commemoration": "纪念", "commendation": "褒扬", "complexity": "复杂",
    "comprehension": "理解", "concern": "关心", "confession": "告白", "consciousness": "意识", "countenance": "神情",
    "daydream": "白日梦", "deep love": "深爱", "delicacy": "细腻", "demeanor": "神态", "desolation": "凄凉",
    "devotedness": "虔诚", "dreaminess": "梦幻", "elation": "欢欣", "emotional attitude": "情感态度",
    "emotional fluctuation": "情绪波动", "emotional flux": "情感流动", "emotional journey": "心路历程",
    "emotional state": "情绪状态", "emotional stirring": "心绪涌动", "enjoyment": "享受", "enrichment": "充实",
    "epiphany": "顿悟", "equanimity": "平和", "exhilaration": "振奋", "experiential": "亲历感",
    "exuberance": "蓬勃", "fervor": "热切", "fond memory": "温情回忆", "fondness": "喜爱之情",
    "fortune": "幸运", "gladness": "欢喜", "goodwill": "善意", "happiness": "幸福",
    "heartfelt": "肺腑之言", "hopefulness": "满怀盼望", "hospitality": "款待", "idealism": "理想主义",
    "idealization": "理想化", "indignation": "愤慨", "indulgence": "放纵", "inner feeling": "内心情感",
    "inner landscape": "内心境界", "insight": "洞察", "intense": "炽烈", "intensity": "情感强度",
    "intimacy": "亲密感", "intoxication": "沉醉", "introspection": "内省", "invigoration": "鼓舞",
    "lamentation": "哀歌", "lexicon": "词汇", "lingering": "流连", "mixed feelings": "复杂感受",
    "moved": "动容", "musical feeling": "音乐情感", "nuance": "微妙", "outpouring": "情感流露",
    "outward affect": "外显情感", "overwhelm": "百感交集", "pathos": "悲情", "perception": "感知",
    "personal stance": "个人立场", "physical": "身体感受", "pleasure": "愉悦感", "poignancy": "触动",
    "portrayal": "描绘", "positivity": "积极性", "praise": "赞美", "rapture": "狂喜",
    "realization": "领悟", "reflection": "思绪", "refreshing": "清爽", "reluctance": "依依惜别",
    "remembrance": "缅怀", "reminiscence": "怀旧", "remorse": "懊悔", "resonance": "共鸣",
    "response": "反应", "retrospection": "感怀", "reverie": "遐想", "richness": "丰富",
    "self-reflection": "自我反思", "sentimentality": "情怀", "sincerity": "真诚", "solace": "慰藉",
    "solitude": "孤寂", "somatic": "体感", "subjectivity": "主观性", "susceptibility": "易感性",
    "tactile": "触感", "textual affect": "文字情感", "thankfulness": "感恩", "tranquility": "宁静",
    "trepidation": "忐忑", "turmoil": "心潮澎湃", "unease": "不安感", "utterance": "情语",
    "vocal expression": "情绪表达", "wistfulness": "惆怅"
}

with open('emotion_sphere_layout.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

updated = 0
for item in data:
    en = item.get('short_en', '')
    key = en.lower()
    if key in EXTRA:
        item['short_en'] = EXTRA[key]
        updated += 1

with open('emotion_sphere_layout.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"已额外更新 {updated} 个情绪翻译")
