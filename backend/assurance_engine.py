"""
assurance_engine.py — 得救的确据 / Assurance of Salvation
（Sinclair Ferguson《全备的基督》The Whole Christ；出自「马罗神学争论」）

补足系统一直缺的一味：**确据**。傅格森的核心洞见——律法主义与反律法主义看似两极，
其实是同一个错误的两种表现：**都把神的律法（和神的恩赐）从神那位慈爱的赐予者身上剥离开来**。
  · 律法主义：把确据建立在「我做得够不够好」上——于是永远不够，永远战兢。
  · 反律法主义：以为恩典就是可以轻看顺服——于是确据变成廉价的自我安慰。
两者的解药都不是「多一点律法」或「少一点律法」，而是**全备的基督**：确据的根基不在我的
表现、也不在我的情绪，而在基督已成之工、神白白的应许、以及祂儿子名分的凭据。

三重确据的次序（改革宗）：
  (1) 客观首要：基督的成全 + 福音的应许（我信靠的是祂，不是我信得好不好）；
  (2) 圣灵的内证：圣灵与我们的心同证我们是神的儿女（罗8:16）；
  (3) 次要凭据：恩典的果子（约壹的记号）——是佐证，不是根基，不可拿来定罪自己。

与 checkup / 钟马田属灵低潮互补：低潮常源于确据缺失。本引擎只做一件事——
接住一句「我到底得救了吗 / 我这样神还要我吗」，温柔地把确据从「我」挪回「基督」。
纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只把人的眼目从表现与情绪，转回全备的基督。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 动摇确据的常见「触发点」→ 它暗藏的错误根基 + 全备之基督的真理 + 经文 ──
DOUBT_TRIGGERS: List[Dict[str, Any]] = [
    {"key": "sin", "name": "又犯了同样的罪",
     "kw": ["又犯", "又跌倒", "同样的罪", "戒不掉", "又失败", "老毛病", "屡次", "又软弱", "犯罪"],
     "lean": "legalist",
     "lie": "我还在犯这罪，说明我根本没得救。",
     "truth": "得救的确据不建立在「我不再犯罪」上，而在「基督已经为这罪死了」。真信徒仍会与罪征战——"
              "会为罪忧伤、会再回到基督，这本身正是恩典在你里面动工的记号，而不是失丧的证据。",
     "ref": "约壹2:1", "text": "我们若有人犯罪，在父那里我们有一位中保，就是那义者耶稣基督。"},
    {"key": "feeling", "name": "感觉不到神 / 没有火热",
     "kw": ["感觉不到", "冷淡", "没有火热", "干枯", "麻木", "没感觉", "神很远", "空", "冰冷"],
     "lean": "experiential",
     "lie": "我感受不到神，所以我可能不是真的属祂。",
     "truth": "确据的根基不是我的感觉的温度，而是神应许的可靠。感觉像天气会变，基督的成全像磐石不动。"
              "把确据挂在情绪上，就是把房子建在流沙上——挪回到「祂说过」的应许上。",
     "ref": "赛54:10", "text": "大山可以挪开，小山可以迁移，但我的慈爱必不离开你。"},
    {"key": "worthy", "name": "我这样的人不配 / 太糟了",
     "kw": ["不配", "太糟", "配不上", "这样的人", "肮脏", "没资格", "不够格", "太差", "羞愧"],
     "lean": "legalist",
     "lie": "我太糟了，神不可能接纳我这样的人。",
     "truth": "从来没有人「配得」被接纳——福音的整个前提就是「基督为不配的人死」。你的不配不是障碍，"
              "正是恩典所要临到的地方。神接纳你不是因为你好，而是因为基督好，而你在祂里面。",
     "ref": "罗5:8", "text": "惟有基督在我们还作罪人的时候为我们死，神的爱就在此向我们显明了。"},
    {"key": "performance", "name": "做得不够 / 不够好",
     "kw": ["做得不够", "不够好", "不够努力", "该更", "还不够", "不合格", "亏欠", "达不到", "做不到"],
     "lean": "legalist",
     "lie": "我灵修/服事/顺服都做得不够，神大概不满意我。",
     "truth": "这正是律法主义的声音——它把确据建立在「我的表现」上，于是永远战兢。傅格森说：解药不是"
              "更努力，而是回到「全备的基督」——神悦纳你不是因为你的成绩单，而是因为基督的成绩单归给了你。",
     "ref": "加2:16", "text": "人称义不是因行律法，乃是因信耶稣基督。"},
    {"key": "past", "name": "过去的失败 / 曾经离开",
     "kw": ["过去", "曾经", "以前", "背叛过", "离开过", "浪费", "回不去", "毁了", "从前"],
     "lean": "experiential",
     "lie": "我曾经那样远离神/伤害人，祂不会再要我了。",
     "truth": "浪子还在远处，父亲就跑过去了。你的过去不能取消基督的血所成就的赦免。回转本身，就是"
              "牧人早已在寻找你的证据——不是你找回了神，是神从未松开你。",
     "ref": "约10:28", "text": "我又赐给他们永生，他们永不灭亡，谁也不能从我手里把他们夺去。"},
    {"key": "cheap", "name": "我信了却随便活 / 恩典是不是借口",
     "kw": ["随便", "无所谓", "反正有恩典", "不在乎", "放纵", "借口", "不用悔改", "怎样都行"],
     "lean": "antinomian",
     "lie": "既然靠恩典得救，怎么活都无所谓。",
     "truth": "这是反律法主义的错觉——它以为恩典是「可以轻看顺服的许可证」。但真恩典从不叫人远离基督，"
              "而是叫人爱祂、像祂。若心里毫无对圣洁的渴慕、对罪的忧伤，那要小心的不是「确据太少」，"
              "而是「还没真尝到恩典」。真确据总是带出感恩的顺服，而非放纵。",
     "ref": "多2:11-12", "text": "神救众人的恩典……教训我们除去不敬虔的心和世俗的情欲，在今世……过敬虔的生活。"},
]

# ── 三重确据的根基（次序：客观→内证→果子）──
GROUNDS: List[Dict[str, str]] = [
    {"key": "objective", "name": "基督的成全与神的应许（首要·客观）",
     "note": "我信靠的对象是基督，不是「我信得好不好」。祂已成了，神的应许可靠。",
     "ref": "来7:25", "text": "凡靠着祂进到神面前的人，祂都能拯救到底。"},
    {"key": "spirit", "name": "圣灵的内证",
     "note": "圣灵亲自与我的心同证：我是神的儿女，可以喊「阿爸，父」。",
     "ref": "罗8:16", "text": "圣灵与我们的心同证我们是神的儿女。"},
    {"key": "fruit", "name": "恩典的果子（次要·佐证，非根基）",
     "note": "爱弟兄、渴慕圣洁、为罪忧伤——这些是佐证，用来印证，不用来定罪自己。",
     "ref": "约壹3:14", "text": "我们因为爱弟兄，就晓得是已经出死入生了。"},
]

LEAN_NOTE = {
    "legalist": "你的疑惑偏向「律法主义」的一端——把确据挂在自己的表现上。傅格森的药：不是更努力，是回到全备的基督。",
    "antinomian": "你的疑惑偏向「反律法主义」的一端——把恩典当成轻看顺服的借口。真恩典带出感恩的顺服，而非放纵。",
    "experiential": "你的疑惑偏向「凭感觉」的一端——把确据挂在情绪的温度上。感觉会变，基督的成全不变。",
}

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们谈确据之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线——你值得有人此刻真实地陪着你。"
    "神在基督里对你的爱，不因你此刻的软弱而动摇。（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for d in DOUBT_TRIGGERS:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or DOUBT_TRIGGERS[3]  # 默认落到「做得不够」——最常见的律法主义之声


def meta() -> Dict[str, Any]:
    return {
        "title": "得救的确据",
        "source": "Sinclair Ferguson《全备的基督》(The Whole Christ)",
        "thesis": ("律法主义与反律法主义是同一错误的两面——都把律法与恩赐从慈爱的神身上剥离。"
                   "确据的根基不在我的表现或情绪，而在全备的基督。"),
        "grounds": GROUNDS,
        "verse": "约壹5:13",
        "principle": "「我将这些话写给你们信奉神儿子之名的人，要叫你们知道自己有永生。」——确据是神要儿女拥有的，不是奢侈品。",
    }


def analyze(struggle: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    struggle = (struggle or "").strip()
    crisis = _detect_crisis(struggle)
    picked = _pick(struggle)
    lean = picked.get("lean", "legalist")

    diagnosis = (
        "你此刻动摇的确据，触发点是「" + picked["name"] + "」。它悄悄在你耳边说：「"
        + picked["lie"] + "」。" + LEAN_NOTE.get(lean, "")
    )
    gospel = picked["truth"]
    grounds_line = (
        "把确据挪回它真正的根基（按次序）：先是**" + GROUNDS[0]["name"] + "**——" + GROUNDS[0]["note"]
        + "（" + GROUNDS[0]["ref"] + "）；再有**" + GROUNDS[1]["name"] + "**（" + GROUNDS[1]["ref"] + "）；"
        "至于恩典的果子，是佐证，不是拿来给自己定罪的尺子。"
    )
    practices = [
        "向自己传讲福音：把上面那句谎言写下来，旁边写上基督的真理（" + picked["ref"] + "），"
        "每次谎言浮现，就大声读那句真理。",
        "分辨根基：问自己「我此刻是想靠什么得着确据——我的表现、我的感觉，还是基督的成全？」"
        "只把重量压在基督身上。",
    ]

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "trigger": {"key": picked["key"], "name": picked["name"]},
        "lean": lean,
        "lean_note": LEAN_NOTE.get(lean, ""),
        "lie": picked["lie"],
        "diagnosis": diagnosis,
        "gospel_truth": gospel,
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "grounds": GROUNDS,
        "grounds_line": grounds_line,
        "prayer": ("父啊，我承认我一直想靠自己站立，就摇摇欲坠。谢谢你，我的确据不在我，而在基督已经成了的工。"
                   "求圣灵与我的心同证，我是你的儿女；叫我安息在全备的基督里，从这份被爱的确据里，欢然地顺服你。"),
        "practices": practices,
        "summary": ("确据不是「我信得够不够好」，而是「祂够不够好」——祂全备，你在祂里面。"
                    "把眼目从自己的表现和情绪，转回基督已成之工。"),
        "closing": "「凡靠着祂进到神面前的人，祂都能拯救到底。」（来7:25）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(struggle, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(struggle: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Sinclair Ferguson《全备的基督》"
        "(The Whole Christ) 关于律法主义、反律法主义与得救确据的教导。核心：确据的根基不在人的"
        "表现或情绪，而在全备的基督（祂的成全 + 神的应许 + 圣灵的内证），恩典的果子只是佐证不是根基。"
        "请针对用户动摇确据的处境，温柔指出那句谎言、分辨它偏向律法主义/反律法主义/凭感觉的哪一端，"
        "把确据挪回基督，给一处经文锚点、一段可祷告的话、一个操练。中文，温暖不说教，"
        "绝不定罪、不贴标签、不说『你信心不够』『你可能没得救』之类的话。\n"
        f"用户处境：{struggle}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"gospel_truth\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(struggle: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(struggle, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("diagnosis", "gospel_truth", "prayer", "summary", "closing"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    for modname, fn in (("engine_ai", "call_ai"),):
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
    """确据属于「身份 + 盼望 + 信靠」。"""
    if result.get("crisis"):
        return (["identity", "hope", "trust"], False, True, 2.0)
    return (["identity", "hope", "trust"], True, True, 4.0)
