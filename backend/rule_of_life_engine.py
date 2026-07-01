"""
rule_of_life_engine.py — 安息节奏 / 生活规则（Rule of Life）
（John Mark Comer《无情地铲除匆忙》；Ruth Haley Barton《神圣的节奏》；毕德生《持续一生的顺服》）

补足 sabbath（安息计划）、prayer-rule（祷告规则）之上缺的一层——**诊断与编排**：
它不做单一操练的 CRUD，而是接住一句「我现在的步调/我的匆忙病」，先诊断匆忙的病征，
再开出对应的「反节奏」操练，并把安息日、静默独处、放慢、简朴串成一套可持守的生活规则(regula)。

核心洞见：
  · 达拉斯·魏乐德对 Comer 的一句忠告：「你必须**无情地铲除生活里的匆忙**。」——匆忙是爱与属灵生命的头号敌人。
  · Barton：属灵成长需要**神圣的节奏**（安息、静默独处、祷告、与神独处），像葡萄藤需要棚架(trellis)。
  · 毕德生（借尼采反语）：门徒是「**朝同一方向持续一生的顺服**」——在这个求速成的世代逆流而行。
  · 「生活规则(rule of life)」不是律法主义的时间表，而是为神腾出空间的、恩典性的、可持守的节奏。

纯函数；确定性优先；内置危机词检测（长期匆忙常与耗竭/抑郁相邻）；AI 仅作可选增强。
不定罪、不贴标签，只帮助人从匆忙里慢下来，为神与所爱的人腾出空间。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 匆忙病的常见病征 → 对应的「反节奏」操练 + 经文 ──
HURRY_SYMPTOMS: List[Dict[str, Any]] = [
    {"key": "irritable", "name": "易怒 / 一点小事就上火",
     "kw": ["易怒", "烦躁", "上火", "不耐烦", "发脾气", "暴躁", "一点就炸", "忍不住", "急躁"],
     "remedy": "silence", "diag": "易怒常是匆忙的第一个外显症状——里面没有余量，一点摩擦就溢出来。"},
    {"key": "restless", "name": "停不下来 / 一闲下来就焦虑",
     "kw": ["停不下来", "闲不住", "一闲就", "静不下", "必须做点", "空虚", "无聊就慌", "闲下来焦虑", "坐不住"],
     "remedy": "sabbath", "diag": "你的价值感被绑在「产出」上，以致无法安然地什么都不做——这是最需要安息日的信号。"},
    {"key": "numb", "name": "麻木 / 靠刷手机追剧来逃",
     "kw": ["麻木", "刷手机", "追剧", "逃避", "刷视频", "停不下手机", "上瘾", "分心", "刷到深夜", "无法专注"],
     "remedy": "simplicity", "diag": "过载之后人会用廉价的刺激来麻醉自己。你需要的不是更多输入，而是做减法。"},
    {"key": "no_time_god", "name": "没时间祷告/读经，神被挤到边缘",
     "kw": ["没时间", "挤不出", "顾不上", "祷告不了", "读经", "灵修停了", "太忙", "神被挤", "没空", "抽不出"],
     "remedy": "sabbath", "diag": "当与神独处成了「有空才做」的选项，说明日程已经在替你敬拜别的东西了。要重排次序。"},
    {"key": "isolated", "name": "太忙以致与人疏远、关系变浅",
     "kw": ["疏远", "没空陪", "关系变浅", "冷落", "顾不上家人", "没时间朋友", "孤单", "错过", "陪不了"],
     "remedy": "slowing", "diag": "匆忙偷走的，首先是「在场」——你在，却没真的在。爱是需要不赶时间的在场的。"},
    {"key": "exhausted", "name": "长期疲惫、耗竭、快撑不住",
     "kw": ["疲惫", "耗竭", "累垮", "撑不住", "透支", "倦怠", "油尽", "身心俱疲", "崩", "扛不住"],
     "remedy": "sabbath", "diag": "长期耗竭不是靠意志硬扛能解决的——身体在替你的灵魂喊停。安息不是奖励，是造物主设的界限。"},
]

# ── 四种「反节奏」操练（Comer / Barton）──
PRACTICES: Dict[str, Dict[str, str]] = {
    "sabbath": {"name": "安息日", "en": "Sabbath",
                "how": "每周划出约 24 小时，停下工作与生产，转向安息、敬拜、与神与所爱的人相聚——不是空档，是圣定的界限。",
                "ref": "出20:8", "text": "当记念安息日，守为圣日。",
                "link": "可到「安息日」页(/api/sabbath)建立你的安息计划。"},
    "silence": {"name": "静默独处", "en": "Silence & Solitude",
                "how": "每天留 5–20 分钟，关掉一切输入，安静在神面前，什么都不「做」，只是与祂同在、把心里的躁交给祂。",
                "ref": "可1:35", "text": "次日早晨，天未亮的时候，耶稣起来，到旷野地方去，在那里祷告。",
                "link": "可结合「操练同在」/「诗篇祷告」页一起做。"},
    "slowing": {"name": "放慢", "en": "Slowing",
                "how": "刻意选一件事做慢一点：走路慢一点、排队时不掏手机、一次只做一件事——训练心不再被赶。",
                "ref": "诗23:2", "text": "他使我躺卧在青草地上，领我在可安歇的水边。",
                "link": "把「放慢」设成一天里的一个小提醒。"},
    "simplicity": {"name": "简朴", "en": "Simplicity",
                   "how": "给生活做减法：减少一样占据你注意力的东西（一个 App、一项承诺、一处杂物），为要紧的腾出空间。",
                   "ref": "太6:33", "text": "你们要先求他的国和他的义，这些东西都要加给你们了。",
                   "link": "可结合「禁食与简朴」页一起操练。"},
}

# ── 生活规则的三层节奏（日 / 周 / 季）──
RHYTHM_LAYERS = [
    {"layer": "每日", "examples": "静默独处、定时祷告、读一段经文、睡前省察"},
    {"layer": "每周", "examples": "安息日、团契聚会、一次不赶时间的深谈"},
    {"layer": "每季/每年", "examples": "退修/静修、较长的独处、检视生活规则是否还合身"},
]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失", "崩溃",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你已经累到很深的地方了。谈节奏之前，我想先温柔地说：如果你有伤害自己的念头，或长期到了"
    "撑不住的地步，请现在就联系你信任的人或专业帮助——安息不只是操练，有时是需要有人真实地扶你一把。"
    "（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for s in HURRY_SYMPTOMS:
        hits = sum(1 for k in s["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, s
    return best or HURRY_SYMPTOMS[1]  # 默认落到「停不下来」


def meta() -> Dict[str, Any]:
    return {
        "title": "安息节奏 / 生活规则",
        "source": "Comer《无情地铲除匆忙》；Barton《神圣的节奏》；毕德生《持续一生的顺服》",
        "core": "匆忙是爱与属灵生命的头号敌人；生活规则是为神腾出空间的、恩典性的、可持守的节奏，不是律法主义的时间表。",
        "practices": list(PRACTICES.values()),
        "rhythm_layers": RHYTHM_LAYERS,
        "verse": "太11:28-29",
        "principle": "「凡劳苦担重担的人，可以到我这里来，我就使你们得安息……我心里柔和谦卑，你们当负我的轭，学我的样式。」",
    }


def analyze(pace: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    pace = (pace or "").strip()
    crisis = _detect_crisis(pace)
    picked = _pick(pace)
    remedy = PRACTICES[picked["remedy"]]

    diagnosis = (
        "你描述的步调里，最明显的匆忙病征是「" + picked["name"] + "」。" + picked["diag"]
    )
    prescription = (
        "对着它，先操练一味「反节奏」——**" + remedy["name"] + "**（" + remedy["en"] + "）：" + remedy["how"]
        + "（" + remedy["ref"] + "：" + remedy["text"] + "）"
    )

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "symptom": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": diagnosis,
        "prescribed_practice": {"key": picked["remedy"], **remedy},
        "prescription": prescription,
        "rhythm_layers": RHYTHM_LAYERS,
        "rule_hint": ("把它长成一套「生活规则」：从一个每日的小操练开始，加上每周的安息日，"
                      "季度留一次较长的独处——规则是棚架，不是牢笼，可以随季节调整。"),
        "anchor": {"ref": "太11:28-29", "text": "凡劳苦担重担的人，可以到我这里来，我就使你们得安息……"},
        "prayer": ("主啊，我承认我活得太赶了，赶到你都被挤到了边缘。谢谢你没有催我，反而说「到我这里来，得安息」。"
                   "求你给我勇气无情地铲除生活里的匆忙，先从这一味操练开始；教我把日子重新排在你面前，"
                   "为你、也为我所爱的人，腾出不赶时间的空间。"),
        "practices": [
            "本周先落地一味：" + remedy["name"] + "——" + remedy["how"],
            remedy.get("link", ""),
            "定一个每日的锚点（如清晨 10 分钟静默独处），连做 7 天，作为你生活规则的第一块砖。",
        ],
        "summary": ("匆忙是爱的头号敌人。不必一次改造全部——先对着最明显的病征，操练一味反节奏，"
                    "再慢慢长成一套为神腾出空间的生活规则。"),
        "closing": "「你们要休息，要知道我是神。」（诗46:10）",
        "ai_used": False,
    }
    result["practices"] = [p for p in result["practices"] if p]

    if use_ai:
        enhanced = _ai_enhance(pace, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(pace: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 John Mark Comer《无情地铲除匆忙》、"
        "Ruth Haley Barton《神圣的节奏》与毕德生《持续一生的顺服》。核心：匆忙是爱与属灵生命的头号敌人；"
        "对策是安息日、静默独处、放慢、简朴等『反节奏』，并长成一套恩典性的『生活规则』（非律法主义时间表）。"
        "请针对用户的步调，温柔诊断匆忙病征，开出一味反节奏操练与一个可持守的节奏建议，给经文与祷告。"
        "中文，温暖不说教，绝不定罪、不制造新的『你不够自律』的重担。\n"
        f"用户的步调/处境：{pace}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"prescription\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(pace: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(pace, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("diagnosis", "prescription", "prayer", "summary", "closing"):
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
    """安息节奏属于「安息 + 习惯 + 信靠」。"""
    if result.get("crisis"):
        return (["rest", "habit", "trust"], False, True, 2.0)
    return (["rest", "habit", "trust"], True, True, 4.0)
