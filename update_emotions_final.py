#!/usr/bin/env python3
import json

# 用户提供的中英文对照表
translations = {
    "Joy": "快乐",
    "Peace": "平静",
    "Love": "爱",
    "Hope": "希望",
    "Gratitude": "感激",
    "Compassion": "同情",
    "Faith": "信任 / 信念",
    "Trust": "信任",
    "Contentment": "满足",
    "Delight": "愉快",
    "Wonder": "惊奇",
    "Awe": "震撼 / 敬畏感",
    "Serenity": "宁静",
    "Relief": "如释重负",
    "Excitement": "兴奋",
    "Enthusiasm": "热情",
    "Confidence": "自信",
    "Courage": "勇气",
    "Patience": "耐心",
    "Kindness": "善良",
    "Humility": "谦虚",
    "Zeal": "热情 / 干劲",
    "Passion": "激情",
    "Inspiration": "启发",
    "Curiosity": "好奇",
    "Eagerness": "迫切期待",
    "Optimism": "乐观",
    "Satisfaction": "满意",
    "Cheerfulness": "愉快",
    "Calmness": "冷静",
    "Security": "安全感",
    "Belonging": "归属感",
    "Acceptance": "接受",
    "Affection": "喜爱",
    "Admiration": "钦佩",
    "Appreciation": "欣赏",
    "Sympathy": "同情心",
    "Empathy": "共情",
    "Forgiveness": "原谅",
    "Gentleness": "温柔",
    "Tenderness": "柔和",
    "Playfulness": "爱玩",
    "Motivation": "动力",
    "Determination": "决心",
    "Focus": "专注",
    "Discipline": "自律",
    "Loyalty": "忠诚",
    "Devotion": "投入 / 奉献",
    "Reverence": "尊敬",
    "Conviction": "坚定信念",
    "Amazement": "惊讶",
    "Anticipation": "期待",
    "Encouragement": "鼓励",
    "Empowerment": "被赋能感",
    "Freedom": "自由",
    "Fulfillment": "成就感",
    "Harmony": "和谐",
    "Clarity": "清晰",
    "Stability": "稳定",
    "Resilience": "韧性",
    "Sadness": "伤心",
    "Grief": "悲痛",
    "Sorrow": "忧伤",
    "Loneliness": "孤独",
    "Despair": "绝望",
    "Hopelessness": "无望",
    "Regret": "后悔",
    "Shame": "羞愧",
    "Guilt": "内疚",
    "Embarrassment": "尴尬",
    "Disappointment": "失望",
    "Heartbreak": "心碎",
    "Rejection": "被拒绝",
    "Abandonment": "被抛弃感",
    "Hurt": "受伤",
    "Bitterness": "怨气",
    "Melancholy": "忧郁",
    "Misery": "痛苦",
    "Depression": "抑郁",
    "Weariness": "疲惫",
    "Exhaustion": "精疲力尽",
    "Emptiness": "空虚",
    "Insecurity": "不安全感",
    "Vulnerability": "脆弱",
    "Fear": "恐惧",
    "Anxiety": "焦虑",
    "Worry": "担心",
    "Panic": "恐慌",
    "Nervousness": "紧张",
    "Dread": "害怕",
    "Terror": "强烈恐惧",
    "Helplessness": "无助",
    "Confusion": "困惑",
    "Doubt": "怀疑",
    "Uncertainty": "不确定",
    "Restlessness": "不安",
    "Stress": "压力",
    "Tension": "紧张",
    "Frustration": "挫败",
    "Irritation": "烦躁",
    "Anger": "愤怒",
    "Rage": "暴怒",
    "Fury": "狂怒",
    "Resentment": "怨恨",
    "Hatred": "仇恨",
    "Jealousy": "嫉妒",
    "Envy": "羡慕 / 嫉妒",
    "Contempt": "轻视",
    "Disgust": "反感",
    "Offense": "被冒犯",
    "Suspicion": "怀疑",
    "Distrust": "不信任",
    "Defensiveness": "防御心理",
    "Cynicism": "犬儒",
    "Pride": "骄傲",
    "Arrogance": "傲慢",
    "Vanity": "虚荣",
    "Selfishness": "自私",
    "Greed": "贪婪",
    "Covetousness": "贪心",
    "Lust": "欲望",
    "Impatience": "不耐烦",
    "Stubbornness": "固执",
    "Rebellion": "叛逆",
    "Defiance": "违抗",
    "Coldness": "冷漠",
    "Numbness": "麻木",
    "Alienation": "疏离",
    "Isolation": "孤立",
    "Withdrawal": "退缩",
    "Shamefulness": "羞耻感",
    "Self-condemnation": "自责",
    "Self-pity": "自怜",
    "Discouragement": "气馁",
    "Defeat": "失败感",
    "Failure": "失败",
    "Powerlessness": "无力感",
    "Hesitation": "犹豫",
    "Apathy": "冷漠",
    "Boredom": "无聊",
    "Indifference": "冷淡",
    "Forgetfulness": "健忘",
    "Conflictedness": "内心冲突",
    "Bewilderment": "迷茫",
    "Shock": "震惊",
    "Surprise": "惊讶",
    "Nostalgia": "怀旧",
    "Longing": "渴望",
    "Yearning": "强烈渴望",
    "Craving": "强烈想要",
    "Desire": "欲望",
    "Attraction": "吸引",
    "Infatuation": "痴迷",
    "Romance": "浪漫情感",
    "Devastation": "崩溃",
    "Mourning": "哀悼",
    "Submission": "顺从",
    "Obedience": "听从",
    "Dependence": "依赖",
    "Assurance": "确信",
    "Boldness": "勇敢",
    "Triumph": "胜利",
    "Victory": "胜利",
    "Renewal": "更新",
    "Restoration": "恢复",
    "Reconciliation": "和解",
    "Redemption": "重建 / 挽回",
    "Conviction of Sin": "强烈自责 / 罪责感",
    "Brokenness": "破碎感",
    "Spiritual Hunger": "强烈精神渴望"
}

# 加载 JSON 文件
with open('emotion_sphere_layout.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 统计更新数量
updated_count = 0
not_found = []

# 遍历并更新
for item in data:
    en_label = item.get('short_en', '')
    if en_label in translations:
        item['short_en'] = translations[en_label]
        updated_count += 1
    elif en_label:
        # 尝试小写匹配
        en_lower = en_label.lower()
        found = False
        for key, value in translations.items():
            if key.lower() == en_lower:
                item['short_en'] = value
                updated_count += 1
                found = True
                break
        if not found:
            not_found.append(en_label)

# 保存更新后的文件
with open('emotion_sphere_layout.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"已更新 {updated_count} 个情绪的英文翻译")
print(f"未找到翻译的英文标签 ({len(not_found)} 个):")
for label in sorted(set(not_found)):
    print(f"  - {label}")
