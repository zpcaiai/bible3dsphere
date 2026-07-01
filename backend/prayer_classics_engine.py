"""
prayer_classics_engine.py — 祷告经典 / The School of Prayer
（慕安得烈《与主同行的祷告学校》；E.M. Bounds《祈祷出能力》；Ole Hallesby《祷告》；
《幽谷之旅》Valley of Vision 清教徒祷文）

给已有的 prayer / prayer-rule / psalm（祷告的「功能/节奏」）配一层**祷告经典的神学喂养**（/api/prayer-school）：
不做祷告排程，而是接住一句「我的祷告卡在哪里」，用经典的洞见解开它。

四位经典的核心：
  · **Hallesby**：祷告的本质是**无助 + 信心**——「祷告就是让耶稣进到我们的需要里」。不是靠字句华丽、
    也不是靠情绪，而是把「我不能」诚实地敞向那位「祂能」的主。连软弱的呼求也是祷告。
  · **慕安得烈**：祷告的根是**住在基督里**（约15）——「你们若常在我里面……凡你们所愿意的，祈求就给你们成就」。
  · **E.M. Bounds**：祷告的能力不在方法，而在**人与神的相交**——「神要的不是更好的方法，而是更合用的人」。
  · **Valley of Vision**：把矛盾诚实地带到神前（「让我在低处寻见你的高」）。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不制造「你祷告得不够」的重担，
只把人从「祷告的技术焦虑」领回「与父相交的孩子式信靠」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

BLOCKS: List[Dict[str, Any]] = [
    {"key": "dont_know_how", "name": "不知道怎么祷告 / 不会祷告",
     "kw": ["不会", "不知道怎么", "没词", "说不出", "不知道说什么", "笨嘴", "不会祷告", "开不了口"],
     "teach": "Hallesby 说：祷告的本质不是会不会用词，而是**无助地转向耶稣**。你不必先学会一套语言——"
              "把「主啊，我不知道怎么说，但我需要你」端到祂面前，这已经是祷告了。圣灵还会用说不出的叹息替你祷告。",
     "ref": "罗8:26", "text": "我们本不晓得当怎样祷告，只是圣灵亲自用说不出来的叹息替我们祷告。"},
    {"key": "dry", "name": "祷告很干、像对着空气 / 没感觉",
     "kw": ["干", "干枯", "对着空气", "没感觉", "冷淡", "机械", "走过场", "无力", "麻木", "没回应"],
     "teach": "Bounds 提醒：祷告的能力不在情绪的温度，而在与神的相交本身。干旱期照样去到祂面前——"
              "不是为了「有感觉」，而是因为祂是父。慕安得烈说：根在于「住在基督里」，先安住，再祈求。",
     "ref": "约15:7", "text": "你们若常在我里面，我的话也常在你们里面，凡你们所愿意的，祈求就给你们成就。"},
    {"key": "unanswered", "name": "祷告好像没被垂听 / 求了很久没有回应",
     "kw": ["没垂听", "没回应", "没答应", "求了很久", "神不听", "石沉大海", "没用", "白祷告", "没成就"],
     "teach": "未蒙应允不等于未蒙垂听。神有时说「是」、有时说「等」、有时说「我给你更好的」。慕安得烈说，"
              "祷告的第一目的不是改变神的手，而是在等候中被父改变、与祂更亲。把「要什么」暂放，先抓住「我要你」。",
     "ref": "路18:1", "text": "耶稣设一个比喻，是要人常常祷告，不可灰心。"},
    {"key": "unworthy", "name": "觉得自己不配祷告 / 太糟了不敢来",
     "kw": ["不配", "不敢", "太糟", "犯了罪", "没脸", "羞愧", "配不上", "不好意思", "肮脏", "远离"],
     "teach": "Hallesby：正是「无助、不配」的人最适合祷告——祷告不是好人的奖赏，是需要恩典之人的呼吸。"
              "施恩宝座是为你这样的人设的；你可以坦然无惧地来，因为来的凭据是基督，不是你的表现。",
     "ref": "来4:16", "text": "所以，我们只管坦然无惧地来到施恩的宝座前，为要得怜恤，蒙恩惠，作随时的帮助。"},
    {"key": "too_busy", "name": "太忙 / 挤不出时间祷告",
     "kw": ["太忙", "没时间", "挤不出", "顾不上", "忙到", "没空", "抽不出", "总被打断", "静不下来"],
     "teach": "Bounds：神要的不是更多方法，而是更合用的人——祷告是相交，不是又一项任务。不必等「大段时间」，"
              "先把零碎的时刻献上：路上、排队、睡前一句。慕安得烈说，祷告的门总为常在主里的人敞着。",
     "ref": "可1:35", "text": "次日早晨，天未亮的时候，耶稣起来……到旷野地方去，在那里祷告。"},
    {"key": "want_deeper", "name": "想学习更深地祷告 / 想与神更亲",
     "kw": ["更深", "学习祷告", "更亲", "长进", "更会祷告", "亲密", "操练", "更多祷告", "渴慕", "亲近神"],
     "teach": "慕安得烈的祷告学校第一课：住在基督里。祷告不是独立的技术，而是与父相交的生活——"
              "先安住在祂的爱里，祈求就从这份亲密里自然流出。可用一篇《幽谷之旅》的祷文，学习向神诚实。",
     "ref": "路11:1", "text": "主啊，教导我们祷告。"},
]

# 一篇《幽谷之旅》风格的祷文（意译，公版精神）
VALLEY_PRAYER = (
    "主啊，你使我在低处，好叫我在低处寻见你的高；\n"
    "使我在黑暗里，好叫我在黑暗中看见你的光；\n"
    "使我在忧伤里，好叫我在忧伤中尝到你的安慰。\n"
    "让我知道：拥有你，就拥有一切；失去你，纵得全世界也是虚空。\n"
    "叫我不靠自己的感觉，只靠你的应许；不靠我的祷告，只靠你的恩典。阿们。"
)

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。此刻你不必先「会祷告」——若你有伤害自己的念头，请现在就联系你信任的人"
    "或当地心理危机热线。神听得懂说不出的叹息，你也不必独自面对。（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for b in BLOCKS:
        hits = sum(1 for k in b["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, b
    return best or BLOCKS[5]


def meta() -> Dict[str, Any]:
    return {
        "title": "祷告经典 · 祷告的学校",
        "source": "慕安得烈《与主同行的祷告学校》；E.M. Bounds《祈祷出能力》；Hallesby《祷告》；《幽谷之旅》",
        "core": "祷告的本质是无助+信心，是与父相交而非技术表演；根在于住在基督里。",
        "blocks": [{"key": b["key"], "name": b["name"]} for b in BLOCKS],
        "valley_prayer": VALLEY_PRAYER,
        "verse": "路11:1",
        "principle": "门徒没有求「教我们讲道」，而是求「主啊，教导我们祷告」——祷告是可以学的，且要从与主同行里学。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "block": {"key": picked["key"], "name": picked["name"]},
        "teaching": picked["teach"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "valley_prayer": VALLEY_PRAYER,
        "prayer": ("父啊，谢谢你，祷告不是我要表演给你看的功课，而是孩子回到父这里。我承认我常常无助、"
                   "也常常不知怎么说；求你藉圣灵替我祷告，教我住在基督里，先安住在你的爱中，再把所求交给你。"
                   "叫我不靠感觉、不靠字句，只靠你的恩典与应许，坦然无惧地来到你面前。"),
        "practices": [
            "无助式祷告：现在就用一句最诚实的话开口——「主啊，我不能，但你能；我需要你。」",
            "读一篇祷文：慢慢读上面《幽谷之旅》风格的祷文一遍，把其中一句变成你今天自己的祷告。",
        ],
        "summary": ("祷告不是技术表演，是无助的人转向那位能的主，是孩子住在父的爱里。"
                    "卡住时，别更用力，先更亲近——从一句诚实的呼求开始。"),
        "closing": "「你们祈求，就给你们；寻找，就寻见；叩门，就给你们开门。」（太7:7）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉慕安得烈《祷告学校》、E.M. Bounds、Hallesby《祷告》"
        "与《幽谷之旅》。核心：祷告的本质是无助+信心，是与父相交而非技术表演，根在住在基督里；"
        "未蒙应允不等于未蒙垂听。请针对用户祷告的卡点，温柔地用经典洞见解开它，给经文、一段祷告与一个操练。"
        "中文，温暖不说教，绝不制造『你祷告得不够/不够属灵』的重担。\n"
        f"用户处境：{text}\n"
        "请输出 JSON：{\"teaching\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("teaching", "prayer", "summary", "closing") if data.get(k)} or None
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
    if result.get("crisis"):
        return (["prayer", "communion", "dependence"], False, True, 2.0)
    return (["prayer", "communion", "dependence"], True, True, 4.0)
