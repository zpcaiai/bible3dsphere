#!/usr/bin/env python3
import json

# 构建小写英文 -> 中文映射
trans = {}
for k, v in [
    ("Joy", "快乐"), ("Peace", "平静"), ("Love", "爱"), ("Hope", "希望"),
    ("Gratitude", "感激"), ("Compassion", "同情"), ("Faith", "信任 / 信念"),
    ("Trust", "信任"), ("Contentment", "满足"), ("Delight", "愉快"),
    ("Wonder", "惊奇"), ("Awe", "震撼 / 敬畏感"), ("Serenity", "宁静"),
    ("Relief", "如释重负"), ("Excitement", "兴奋"), ("Enthusiasm", "热情"),
    ("Confidence", "自信"), ("Courage", "勇气"), ("Patience", "耐心"),
    ("Kindness", "善良"), ("Humility", "谦虚"), ("Zeal", "热情 / 干劲"),
    ("Passion", "激情"), ("Inspiration", "启发"), ("Curiosity", "好奇"),
    ("Eagerness", "迫切期待"), ("Optimism", "乐观"), ("Satisfaction", "满意"),
    ("Cheerfulness", "愉快"), ("Calmness", "冷静"), ("Security", "安全感"),
    ("Belonging", "归属感"), ("Acceptance", "接受"), ("Affection", "喜爱"),
    ("Admiration", "钦佩"), ("Appreciation", "欣赏"), ("Sympathy", "同情心"),
    ("Empathy", "共情"), ("Forgiveness", "原谅"), ("Gentleness", "温柔"),
    ("Tenderness", "柔和"), ("Playfulness", "爱玩"), ("Motivation", "动力"),
    ("Determination", "决心"), ("Focus", "专注"), ("Discipline", "自律"),
    ("Loyalty", "忠诚"), ("Devotion", "投入 / 奉献"), ("Reverence", "尊敬"),
    ("Conviction", "坚定信念"), ("Amazement", "惊讶"), ("Anticipation", "期待"),
    ("Encouragement", "鼓励"), ("Empowerment", "被赋能感"), ("Freedom", "自由"),
    ("Fulfillment", "成就感"), ("Harmony", "和谐"), ("Clarity", "清晰"),
    ("Stability", "稳定"), ("Resilience", "韧性"), ("Sadness", "伤心"),
    ("Grief", "悲痛"), ("Sorrow", "忧伤"), ("Loneliness", "孤独"),
    ("Despair", "绝望"), ("Hopelessness", "无望"), ("Regret", "后悔"),
    ("Shame", "羞愧"), ("Guilt", "内疚"), ("Embarrassment", "尴尬"),
    ("Disappointment", "失望"), ("Heartbreak", "心碎"), ("Rejection", "被拒绝"),
    ("Abandonment", "被抛弃感"), ("Hurt", "受伤"), ("Bitterness", "怨气"),
    ("Melancholy", "忧郁"), ("Misery", "痛苦"), ("Depression", "抑郁"),
    ("Weariness", "疲惫"), ("Exhaustion", "精疲力尽"), ("Emptiness", "空虚"),
    ("Insecurity", "不安全感"), ("Vulnerability", "脆弱"), ("Fear", "恐惧"),
    ("Anxiety", "焦虑"), ("Worry", "担心"), ("Panic", "恐慌"),
    ("Nervousness", "紧张"), ("Dread", "害怕"), ("Terror", "强烈恐惧"),
    ("Helplessness", "无助"), ("Confusion", "困惑"), ("Doubt", "怀疑"),
    ("Uncertainty", "不确定"), ("Restlessness", "不安"), ("Stress", "压力"),
    ("Tension", "紧张"), ("Frustration", "挫败"), ("Irritation", "烦躁"),
    ("Anger", "愤怒"), ("Rage", "暴怒"), ("Fury", "狂怒"),
    ("Resentment", "怨恨"), ("Hatred", "仇恨"), ("Jealousy", "嫉妒"),
    ("Envy", "羡慕 / 嫉妒"), ("Contempt", "轻视"), ("Disgust", "反感"),
    ("Offense", "被冒犯"), ("Suspicion", "怀疑"), ("Distrust", "不信任"),
    ("Defensiveness", "防御心理"), ("Cynicism", "犬儒"), ("Pride", "骄傲"),
    ("Arrogance", "傲慢"), ("Vanity", "虚荣"), ("Selfishness", "自私"),
    ("Greed", "贪婪"), ("Covetousness", "贪心"), ("Lust", "欲望"),
]:
    trans[k.lower()] = v

with open('emotion_sphere_layout.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

updated = 0
for item in data:
    en = item.get('short_en', '').lower().strip()
    if en in trans:
        item['short_en'] = trans[en]
        updated += 1

with open('emotion_sphere_layout.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Updated: {updated}/171')
