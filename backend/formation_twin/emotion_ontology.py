"""Open, non-diagnostic emotion vocabulary for Formation Twin Batch 3."""
from __future__ import annotations

from enum import Enum


class EmotionLabel(str, Enum):
    JOY = "JOY"; PEACE = "PEACE"; LOVE = "LOVE"; HOPE = "HOPE"; GRATITUDE = "GRATITUDE"
    INTEREST = "INTEREST"; EXCITEMENT = "EXCITEMENT"; SADNESS = "SADNESS"; GRIEF = "GRIEF"
    LONELINESS = "LONELINESS"; DISAPPOINTMENT = "DISAPPOINTMENT"; HELPLESSNESS = "HELPLESSNESS"
    ANGER = "ANGER"; FRUSTRATION = "FRUSTRATION"; RESENTMENT = "RESENTMENT"; IRRITATION = "IRRITATION"
    FEAR = "FEAR"; ANXIETY = "ANXIETY"; WORRY = "WORRY"; UNCERTAINTY = "UNCERTAINTY"
    OVERWHELM = "OVERWHELM"; SHAME = "SHAME"; GUILT = "GUILT"; EMBARRASSMENT = "EMBARRASSMENT"
    REGRET = "REGRET"; ENVY = "ENVY"; JEALOUSY = "JEALOUSY"; DISGUST = "DISGUST"
    AVERSION = "AVERSION"; NUMBNESS = "NUMBNESS"; CONFUSION = "CONFUSION"; MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"; OTHER = "OTHER"


ZH_ALIASES = {
    "喜乐": "JOY", "快乐": "JOY", "平安": "PEACE", "平静": "PEACE", "爱": "LOVE", "盼望": "HOPE",
    "感恩": "GRATITUDE", "感兴趣": "INTEREST", "兴奋": "EXCITEMENT", "难过": "SADNESS", "悲伤": "SADNESS",
    "哀伤": "GRIEF", "孤单": "LONELINESS", "失望": "DISAPPOINTMENT", "失落": "DISAPPOINTMENT",
    "无助": "HELPLESSNESS", "愤怒": "ANGER", "生气": "ANGER", "挫败": "FRUSTRATION", "烦躁": "IRRITATION",
    "恐惧": "FEAR", "害怕": "FEAR", "焦虑": "ANXIETY", "担忧": "WORRY", "不安": "UNCERTAINTY",
    "不确定": "UNCERTAINTY", "不堪重负": "OVERWHELM", "羞耻": "SHAME", "内疚": "GUILT",
    "尴尬": "EMBARRASSMENT", "后悔": "REGRET", "羡慕": "ENVY", "嫉妒": "JEALOUSY", "厌恶": "DISGUST",
    "麻木": "NUMBNESS", "困惑": "CONFUSION", "混合": "MIXED", "说不清": "UNKNOWN", "疲惫": "OTHER",
}


def normalize_emotion_label(value: str) -> tuple[str, str | None]:
    raw = (value or "").strip()
    upper = raw.upper().replace(" ", "_")
    if upper in {item.value for item in EmotionLabel}:
        return upper, None
    if raw in ZH_ALIASES:
        canonical = ZH_ALIASES[raw]
        return canonical, (raw if canonical in {"OTHER", "UNKNOWN"} else None)
    return "OTHER", raw[:80] or None
