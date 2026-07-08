"""
hope_engine.py — 复活盼望 / Living Hope（N.T. 赖特《意料之外的盼望》Surprised by Hope；
Randy Alcorn《天堂》Heaven；诗90 数算自己的日子）

补足系统偏「当下内在诊断」、缺「终末盼望」的空白。赖特的核心纠正：基督徒的盼望**不是**
「灵魂逃离世界、飘去天堂」，而是**身体复活 + 新天新地**——神要更新、而非废弃祂的受造界；
「天堂」不是终点，复活与新造才是。这盼望不是逃避现实，反而**改变我们此刻如何活**：
在主里的劳苦不是徒然（林前15:58）。

四种「盼望的阴影」：哀伤失丧、惧怕死亡、觉得人生没意义/「不过如此」、久等生厌。
本引擎接住其中一种，把眼目从「此生的尽头」抬向「那日的确据」，并落成「向着那日而活」的操练。

含 memento mori（数算日子）的健康面：不是病态怕死，而是让永恒的重量校正今天的轻重。
纯函数；确定性优先；内置危机词检测（死亡/绝望主题→若命中自伤词，先接住、转真人帮助）；
AI 仅作可选增强。不轻看眼前的痛，只把它放进复活的盼望里。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

SHADOWS: List[Dict[str, Any]] = [
    {"key": "grief", "name": "哀伤 / 失去了所爱的人",
     "kw": ["失去", "去世", "离世", "走了", "哀伤", "想念", "过世", "死了", "丧", "永别", "阴阳两隔"],
     "diag": "你在为一个所爱的人哀伤。基督徒的哀伤不是没有盼望的哀伤——泪是真的，但坟墓不是句号。",
     "hope": "基督已经复活，成了睡了之人初熟的果子。凡在主里死了的，必要复活；将来有一天，死亡要被完全吞灭，"
             "神要亲手擦去一切的眼泪。你的想念不是错觉——那是为「重逢」而设的心。",
     "ref": "帖前4:13-14", "text": "论到睡了的人，我们不愿意你们不知道，恐怕你们忧伤，像那些没有指望的人一样……神也必将他与耶稣一同带来。"},
    {"key": "death_fear", "name": "惧怕死亡 / 惧怕失去",
     "kw": ["怕死", "死亡", "怕失去", "怕结束", "生命有限", "怕老", "绝症", "临终", "末期", "活不长"],
     "diag": "对死亡的惧怕，是人最深的阴影之一。福音正是对着这道阴影说话的。",
     "hope": "基督藉着死，败坏了那掌死权的，叫一生因怕死而为奴的人得释放。对信主的人，死不是坠入虚空，"
             "而是「与基督同在，好得无比」；肉身睡了，将来必复活，得着不朽坏的身体。",
     "ref": "林前15:54-55", "text": "死被得胜吞灭的话就应验了。死啊，你得胜的权势在哪里？"},
    {"key": "meaningless", "name": "觉得人生没意义 / 一切是虚空",
     "kw": ["没意义", "虚空", "白活", "没价值", "徒劳", "空虚", "不过如此", "为什么活", "没盼望", "麻木绝望"],
     "diag": "你触到了传道书的诚实：日光之下，一切似乎都是虚空。但传道书不是终点，复活才是。",
     "hope": "因为基督复活了，你在主里的劳苦就不是徒然的——没有一件出于爱的事会消失在虚空里，"
             "它们要被带进那更新了的世界。你的人生不是通往虚无，而是通往新造。这给今天最小的忠心以永恒的重量。",
     "ref": "林前15:58", "text": "你们务要坚固，不可摇动，常常竭力多做主工，因为知道你们的劳苦在主里面不是徒然的。"},
    {"key": "weary_wait", "name": "久等生厌 / 盼望快熄了",
     "kw": ["等太久", "熬不住", "盼望", "还要多久", "撑不住", "看不到头", "疲乏", "灰心", "快放弃", "遥遥无期"],
     "diag": "你等得太久，盼望的火快要熄了。圣经知道这种疲乏，也为它预备了「那日」的确据。",
     "hope": "现在的苦楚，若与将要显于我们的荣耀相比，就不足介意。神并不误事——祂在为你存留一个「万物更新」的日子，"
             "那时公义居在其中，再没有眼泪、疼痛与死亡。举目望那日，好走过今天。",
     "ref": "罗8:18", "text": "我想现在的苦楚若比起将来要显于我们的荣耀，就不足介意了。"},
    {"key": "seek_hope", "name": "想更扎根于盼望 / 想活得有永恒感",
     "kw": ["盼望", "永恒", "新天新地", "那日", "复活", "天家", "更扎根", "活出", "眼光", "属天"],
     "diag": "你想让永恒的重量来校正今天——这正是复活盼望要做的事。",
     "hope": "把心定在「那日」：基督必再来，死人复活，神更新万有。这不是逃避今生，反而叫你更认真地爱、更忠心地活——"
             "因为你所做的一切美善，都要存到那更新了的世界里。",
     "ref": "启21:4-5", "text": "神要擦去他们一切的眼泪……看哪，我将一切都更新了。"},
]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。谈复活盼望之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线——你此刻的痛是真的，你值得有人真实地陪着你。"
    "复活的盼望不是要跳过你的痛，而是要在你的痛里陪你到底。（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for s in SHADOWS:
        hits = sum(1 for k in s["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, s
    return best or SHADOWS[4]


def meta() -> Dict[str, Any]:
    return {
        "title": "复活盼望",
        "source": "N.T. 赖特《意料之外的盼望》；Randy Alcorn《天堂》",
        "core": "基督徒的盼望不是灵魂逃去天堂，而是身体复活 + 新天新地——神更新而非废弃受造界；这盼望改变我们此刻如何活。",
        "shadows": [{"key": s["key"], "name": s["name"]} for s in SHADOWS],
        "verse": "彼前1:3",
        "principle": "「他……重生了我们，叫我们有活泼的盼望，是藉耶稣基督从死里复活。」——盼望是「活泼的」，因为它系于一位复活的主。",
        "memento_mori": "数算自己的日子（诗90:12）不是病态怕死，而是让永恒的重量校正今天的轻重。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "shadow": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diag"],
        "hope": picked["hope"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("复活的主啊，谢谢你——你不只赦免我，还要更新一切。当我被眼前的失丧、惧怕或虚空压住，"
                   "求你把我的眼目抬向那日：死亡被吞灭、眼泪被擦干、万物被更新。叫我因你复活的确据，"
                   "有勇气再爱一次、再忠心一天，因为知道在你里面的劳苦不是徒然的。"),
        "practices": [
            "向着那日而活：写下今天一件「会存到新世界里」的小小忠心（一次爱、一次饶恕、一件善工），今天就去做。",
            "数算日子（memento mori）：安静一分钟，想「若从永恒回看今天，什么才真正要紧？」据此调整今天的一个选择。",
        ],
        "summary": ("基督徒的盼望是复活与新造，不是逃离世界。它不轻看眼前的痛，而是把痛放进「那日」的确据里——"
                    "死亡不是句号，你在主里的劳苦不是徒然。"),
        "closing": "「看哪，我将一切都更新了。」（启21:5）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心、有安宁疗护般敏感度的属灵陪伴者，熟悉 N.T. 赖特《意料之外的盼望》"
        "与 Randy Alcorn《天堂》。核心：基督徒盼望是身体复活+新天新地（非逃去天堂），它不跳过眼前的痛，"
        "而把痛放进那日的确据里，并改变此刻如何活（在主里的劳苦不徒然）。请针对用户的处境（哀伤/怕死/虚空/久等），"
        "温柔诊断，给复活盼望的安慰、经文、祷告与一个『向着那日而活』的操练。中文，温暖不说教，绝不轻看其痛。\n"
        f"用户处境：{text}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"hope\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("diagnosis", "hope", "prayer", "summary", "closing") if data.get(k)} or None
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
    if result.get("crisis"):
        return (["hope", "eternity", "trust"], False, True, 2.0)
    return (["hope", "eternity", "trust"], True, True, 4.0)
