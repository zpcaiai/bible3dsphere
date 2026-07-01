"""
gratitude_engine.py — 感恩 / Eucharisteo（Ann Voskamp《一千次感谢》One Thousand Gifts）

给已有的 gratitude 路由（感恩日记 CRUD，/api/gratitude）配一层**塑造/诊断引擎**（/api/eucharisteo）：
不只是记录，而是用 Voskamp 的 eucharisteo 神学，把「数算恩典」变成重排心的操练。

核心洞见：
  · **eucharisteo（感恩）先于神迹**——耶稣「拿起饼来，祝谢了(eucharisteo)」，掰开就够了众人。
    感恩不是等好事发生后的反应，而是先在此刻承认恩典，心就被打开。
  · **数算恩典**：把神在具体、微小、寻常之物中的恩典一件件命名出来（一千件），
    训练眼睛看见「凡是好的，都是从上头来的」，把心从「缺乏/不满」重排为「信靠/喜乐」。
  · **hard eucharisteo（艰难中的感恩）**：连在难处里也寻找恩典——但**不是否认痛苦、不是强颜欢笑**；
    它与哀歌并行：先诚实哀恸，再在破碎处寻找一线恩典。绝不拿感恩去压制真实的伤痛。

与 contentment 互补：知足对治「对缺乏的不满」（做减法、安息），感恩是「主动数算已有」（做加法、睁眼）。
纯函数；确定性优先；内置危机词检测（命中则先接住痛，不催逼感恩，并可转介哀歌）；AI 仅作可选增强。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 数算恩典的取景框（帮人把「说不出感恩」变成「看得见的具体」）──
GIFT_LENSES: List[Dict[str, str]] = [
    {"key": "senses", "name": "感官里的恩典", "prompt": "此刻你看见/听见/尝到/触到的一样好东西——光、一杯热水、一段音乐、窗外的树。"},
    {"key": "ordinary", "name": "寻常小事里的恩典", "prompt": "今天一件不起眼却是恩典的小事——睡醒、一顿饭、一次顺利、一个准点的公交。"},
    {"key": "people", "name": "关系里的恩典", "prompt": "今天一个人（哪怕只是一句问候、一个眼神）让你尝到被爱或被陪。"},
    {"key": "grace", "name": "救恩里的恩典", "prompt": "一件与神有关的恩典——被赦免、有圣经可读、可以祷告、祂从未离开。"},
    {"key": "body", "name": "身体里的恩典", "prompt": "身体今天为你做成的一件事——能呼吸、能走路、能拥抱、伤在愈合。"},
]

# ── 心境 → eucharisteo 的对应引导 ──
MOODS: List[Dict[str, Any]] = [
    {"key": "flat", "name": "平淡 / 麻木 / 感受不到什么",
     "kw": ["平淡", "麻木", "没感觉", "无聊", "空", "提不起", "乏味", "日子重复", "没劲"],
     "mode": "count",
     "note": "麻木常是因为眼睛习惯了、看不见了。eucharisteo 的操练正是重新睁眼——不是制造感觉，是命名本已在的恩典。"},
    {"key": "discontent", "name": "不满 / 总觉得别人更好",
     "kw": ["不满", "羡慕", "别人", "比较", "不如", "抱怨", "为什么我", "得不到", "嫉妒"],
     "mode": "count",
     "note": "不满的眼睛盯着「还没有的」；感恩的操练把镜头转向「已领受的」。数算恩典，是把心从匮乏搬回丰盛。"},
    {"key": "hard", "name": "正在难处里 / 有痛，但想寻找恩典",
     "kw": ["难", "痛", "苦", "失去", "生病", "难处", "眼泪", "熬", "艰难", "低谷"],
     "mode": "hard",
     "note": "hard eucharisteo 不是否认痛。先让哀恸是真的，再在破碎的边缘，轻轻寻找哪怕一线恩典——两者可以并存。"},
    {"key": "thankful", "name": "心里有感恩，想献上 / 想数点",
     "kw": ["感恩", "感谢", "谢谢", "想记录", "领受", "满足", "被爱", "恩典", "献上"],
     "mode": "count",
     "note": "很好——把这份感恩落成具体的清单，感恩越具体，喜乐越扎根。"},
]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。此刻我不会请你去「数算恩典」——那会显得轻慢你的痛。我想先温柔地说："
    "如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。你的痛是真的，你值得被真实地陪着。"
    "（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for m in MOODS:
        hits = sum(1 for k in m["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, m
    return best or MOODS[0]  # 默认落到「平淡/麻木」


def meta() -> Dict[str, Any]:
    return {
        "title": "感恩 · Eucharisteo",
        "source": "Ann Voskamp《一千次感谢》(One Thousand Gifts)",
        "core": "eucharisteo（感恩）先于神迹；数算具体、微小、寻常的恩典，把心从缺乏重排为信靠与喜乐。",
        "gift_lenses": GIFT_LENSES,
        "hard_eucharisteo": "艰难中的感恩与哀歌并行——先诚实哀恸，再在破碎处寻找一线恩典，绝不否认痛苦。",
        "verse": "帖前5:18",
        "principle": "「凡事谢恩，因为这是神在基督耶稣里向你们所定的旨意。」——注意是『凡事谢恩』，不是『为凡事谢恩』。",
        "complement": "与「知足」互补：知足对治不满（做减法、安息），感恩主动数算已有（做加法、睁眼）。",
    }


def analyze(mood_text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    mood_text = (mood_text or "").strip()
    crisis = _detect_crisis(mood_text)
    picked = _pick(mood_text)
    hard = picked["mode"] == "hard"

    if crisis:
        invite = "此刻先不数算恩典。先让你的痛被听见、被陪伴。"
    elif hard:
        invite = ("我们不假装难处不存在。可以先把痛诚实地说出来（若需要，去「哀歌」页把它谱成祷告），"
                  "然后——只有当你预备好时——试着在破碎的边缘，轻轻找出哪怕一件仍在的恩典。")
    else:
        invite = "让我们做一次 eucharisteo：用下面的取景框，把此刻本已在的恩典，一件件具体地命名出来。"

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "mood": {"key": picked["key"], "name": picked["name"], "mode": picked["mode"]},
        "note": picked["note"],
        "invite": invite,
        "gift_lenses": GIFT_LENSES if not crisis else [],
        "hard_mode": hard,
        "lament_link": ("这份痛值得被诚实地哀诉——可到「哀歌」页(/api/lament)把它带到神面前。" if (hard or crisis) else ""),
        "anchor": {"ref": "帖前5:18", "text": "凡事谢恩，因为这是神在基督耶稣里向你们所定的旨意。"},
        "prayer": ("父啊，谢谢你——在我常常看不见的地方，你早已把恩典撒满我的日子。求你开我的眼，"
                   "叫我不再只盯着缺乏，而学会一件一件地数点你的恩慈；就算在难处里，也求你给我恩典，"
                   "在破碎的边缘仍认出你的手。愿我的心因看见你的赐予，重新学会信靠与喜乐。"),
        "practices": [
            ("先哀恸，后感恩：允许自己把痛说完；预备好时，再试着写下一件仍在的恩典。" if hard
             else "数算三件恩典：用上面任一取景框，此刻具体写下三样恩典（越小越好，越具体越好）。"),
            "养成节奏：给自己定一个「每天记 3 件恩典」的小操练，可记在「感恩日记」页(/api/gratitude)，连做一周。",
        ],
        "summary": ("感恩不是等好事发生后的反应，而是此刻就睁眼命名恩典的操练。凡事谢恩（不是为凡事谢恩）——"
                    "数算越具体，心越从缺乏被搬回丰盛。"),
        "closing": "「你们要称谢耶和华，因他本为善；他的慈爱永远长存。」（诗107:1）",
        "ai_used": False,
    }
    result["practices"] = [p for p in result["practices"] if p]

    if use_ai:
        enhanced = _ai_enhance(mood_text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(mood_text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Ann Voskamp《一千次感谢》的 eucharisteo 神学。"
        "核心：感恩先于神迹；数算具体微小寻常的恩典，把心从缺乏重排为信靠喜乐；艰难中的感恩(hard eucharisteo)"
        "与哀歌并行，绝不否认痛苦、绝不强颜欢笑。请针对用户的心境，若在难处先接住痛、可转介哀歌，"
        "否则温柔引导他具体数算恩典，给经文、祷告与一个操练。中文，温暖不说教，绝不用『你该知足』施压。\n"
        f"用户心境：{mood_text}\n"
        "请输出 JSON：{\"invite\":\"...\",\"note\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(mood_text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(mood_text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("invite", "note", "prayer", "summary", "closing"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    for modname, fn in (("waiting_engine", "call_ai_provider"), ("llm_provider", "call_llm")):
        try:
            mod = __import__(modname)
            f = getattr(mod, fn, None)
            if f:
                out = f(prompt) if settings is None else f(prompt, settings=settings)
                if out:
                    return out if isinstance(out, str) else str(out)
        except Exception:
            continue
    return None


def formation_signal(result: Dict[str, Any]):
    """感恩属于「喜乐 + 信靠 + 盼望」。危机时降权并标记需真人陪伴。"""
    if result.get("crisis"):
        return (["joy", "trust", "hope"], False, True, 2.0)
    return (["joy", "trust", "hope"], True, True, 4.5)
