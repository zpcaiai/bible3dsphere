"""
pastoral_engine.py — 每周「牧养小结」

把一周内的 checkin 情绪、偶像监测、等候之路等信号，温柔地综合成一段「牧养小结」：
  神这周在你身上做的工 + 一个邀请 + 一节经文。
不定罪、不评判、不制造焦虑；纯函数，便于测试与可选 AI 增强。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

EMOTION_ZH = {
    "anxiety": "焦虑", "fear": "恐惧", "peace": "平静", "hope": "盼望",
    "joy": "喜乐", "sadness": "悲伤", "anger": "愤怒", "gratitude": "感恩",
    "loneliness": "孤独", "shame": "羞耻", "guilt": "内疚", "love": "爱",
}

_VERSES = {
    "peace":   {"ref": "腓4:6-7", "text": "应当一无挂虑……神所赐出人意外的平安，必在基督耶稣里保守你们的心怀意念。"},
    "fear":    {"ref": "赛41:10", "text": "你不要害怕，因为我与你同在……我必坚固你，我必帮助你。"},
    "anxiety": {"ref": "彼前5:7", "text": "你们要将一切的忧虑卸给神，因为他顾念你们。"},
    "sadness": {"ref": "诗34:18", "text": "耶和华靠近伤心的人，拯救灵性痛悔的人。"},
    "gratitude": {"ref": "帖前5:18", "text": "凡事谢恩，因为这是神在基督耶稣里向你们所定的旨意。"},
    "joy":     {"ref": "尼8:10", "text": "靠耶和华而得的喜乐是你们的力量。"},
    "default": {"ref": "哀3:22-23", "text": "我们不致消灭，是出于耶和华诸般的慈爱……每早晨这都是新的。"},
}


def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
    """data: {checkin_count, dominant_emotion, emotion_counts, top_attachment,
              waiting_types, activity_count}. 返回温柔的牧养小结。"""
    n = int(data.get("activity_count", 0) or 0)
    dom = data.get("dominant_emotion") or ""
    dom_zh = EMOTION_ZH.get(dom, dom)
    top_att = data.get("top_attachment") or None
    wtypes = data.get("waiting_types") or []

    if n == 0:
        return {
            "has_data": False,
            "title": "这一周，先从一次记录开始",
            "gods_work": "本周还没有留下足够的痕迹来回顾。没关系——属灵的进深不靠数据，"
                         "而靠一次次诚实地来到神面前。",
            "invitation": "今天就做一次今日打卡或一次心迹省察，下周这里会长出属于你的故事。",
            "scripture": _VERSES["default"],
            "stats": data,
        }

    # 神这周做的工
    work_parts: List[str] = [f"这一周，你来到神面前 {n} 次。这份持续本身，就是恩典在你里面的工作。"]
    if dom_zh:
        work_parts.append(f"你最常带到神面前的，是「{dom_zh}」——他没有嫌弃这份情绪，反而藉它靠近你。")
    if top_att:
        work_parts.append(
            f"在偶像监测里，「{top_att.get('name','')}」一度想坐上只有神能坐的位置；"
            f"你愿意看见它，已是松手的开始。")
    if "godot_waiting" in wtypes and "god_waiting" in wtypes:
        work_parts.append("你的等待在「等戈多」与「等候上帝」之间来回——这很真实，神正是在这摇摆里塑造你的信靠。")
    elif "god_waiting" in wtypes:
        work_parts.append("你的等待正越来越像「等候上帝」：在不确定中仍选择信靠与忠心。")
    elif "godot_waiting" in wtypes:
        work_parts.append("你的等待还带着些焦虑与被动——这不是失败，是一个被重新校准的邀请。")

    # 一个邀请
    if dom in ("anxiety", "fear"):
        invitation = "这周的邀请：每天睡前，把一件最放不下的事，一句话交托给神——「这件事我交给你」。"
    elif dom in ("sadness", "loneliness"):
        invitation = "这周的邀请：允许自己在神面前诚实地悲伤，并主动找一位弟兄姊妹说说话。"
    elif top_att:
        invitation = "这周的邀请：做一个小小的、不依赖结果的顺服行动，练习把中心还给神。"
    else:
        invitation = "这周的邀请：选一个固定时刻安静三分钟，只是与神同在，不求什么。"

    verse = _VERSES.get(dom, _VERSES["default"])

    return {
        "has_data": True,
        "title": "本周牧养小结",
        "gods_work": " ".join(work_parts),
        "invitation": invitation,
        "scripture": verse,
        "stats": {
            "activity_count": n,
            "dominant_emotion": dom_zh,
            "top_attachment": (top_att or {}).get("name", ""),
        },
    }
