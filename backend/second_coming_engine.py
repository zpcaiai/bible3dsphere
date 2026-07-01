"""
second_coming_engine.py — 主再来 · 儆醒地活（帖前4-5；太25 十童女/才干/绵羊山羊）

系统的 hope 讲复活与新造；本引擎补一个**完全缺失**的主题：**基督必再来**，以及由此而来的
「存盼望、儆醒、忠心、向祂交账地活」。核心不是末世时间表的推算，而是**如何在等祂再来中活好今天**。

三幅主耶稣的画面（太24-25）：
  · **十童女**：儆醒预备，油要备足——别在拖延中被主的来临措手不及；
  · **按才干受托的仆人**：忠心运用神所托付的（恩赐、时间、资源），将来向祂交账；
  · **绵羊与山羊**：以对「最小的弟兄」的爱来见证真实的信——盼望主再来的人，如今就服事人。

安慰与激励并存：对受苦的，主再来是「擦干眼泪、伸张公义」的确据（帖前4 安慰哀伤者）；
对懈怠的，是「儆醒忠心」的催促。不制造末世恐慌，只把盼望落成「今天忠心而活」。

纯函数；确定性；内置危机词检测；AI 可选增强。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "grieving", "name": "在受苦/失丧中，盼望主再来的安慰",
     "kw": ["受苦", "失丧", "眼泪", "不公", "难", "痛", "什么时候是头", "盼主来", "撑", "等公义"],
     "diag": "对正在受苦的人，主再来首先是安慰：有一天祂必回来，擦干一切眼泪、伸张一切公义、更新万有。",
     "way": "举目望那日：现在的苦楚是暂时的，主必再来把一切颠倒的扶正、把一切破碎的更新。这不是逃避今天，"
            "而是给今天一个能撑下去的盼望——你所受的冤与痛，都不会被祂忘记，那日必得伸张与安慰。",
     "ref": "帖前4:16-18", "text": "因为主必亲自从天降临……以后我们……要和主永远同在。所以，你们当用这些话彼此劝慰。"},
    {"key": "drifting", "name": "属灵懈怠 / 活得像主不会回来",
     "kw": ["懈怠", "松懈", "拖延", "得过且过", "属灵怠惰", "无所谓", "反正还早", "混日子", "不预备"],
     "diag": "你活得有点像『主还早着呢』——十童女的比喻正是警醒这个：别在拖延中被主的来临措手不及。",
     "way": "儆醒不是焦虑地掐算日子，而是『油备足』地忠心度日——今天就把该修复的关系修复、该做的顺服去做、"
            "该预备的心预备好。像随时会见到主一样活着：不是恐慌，而是清醒而忠心。",
     "ref": "太25:13", "text": "所以，你们要儆醒；因为那日子，那时辰，你们不知道。"},
    {"key": "purpose", "name": "想忠心运用神所托付的 / 怕虚度",
     "kw": ["才干", "托付", "忠心", "运用恩赐", "虚度", "怕浪费", "交账", "尽本分", "为主而活", "有意义地活"],
     "diag": "你想把神托付的（恩赐、时间、资源）用在刀刃上——按才干受托的比喻说，将来你要向主交这个账。",
     "way": "『交账』不是威胁，是尊严：主看重你、把祂的产业托付了你。忠心不在于才干多寡，而在于是否动用了所领的。"
            "问『主托付我的是什么，我今天怎样忠心运用一点』，从一件小的忠心开始——将来你要听见『又良善又忠心的仆人』。",
     "ref": "太25:21", "text": "主人说：好，你这又良善又忠心的仆人……可以进来享受你主人的快乐。"},
    {"key": "serve", "name": "想让盼望落到爱人与服事上",
     "kw": ["服事", "爱人", "帮助最小的", "落实", "怎么活出", "怜悯", "行动", "见证", "关怀弱小"],
     "diag": "绵羊与山羊的比喻说：真实盼望主再来的人，如今就在服事『最小的弟兄』——盼望向下扎根成了爱。",
     "way": "把对那日的盼望，今天就落成对一个具体的人的爱：探望、供应、接待、安慰。你怎样待最小的一个，"
            "就是怎样待主自己。盼望不是仰望天空发呆，而是俯身去爱身边的人。",
     "ref": "太25:40", "text": "这些事你们既做在我这弟兄中一个最小的身上，就是做在我身上了。"},
    {"key": "ready", "name": "想学习存盼望、儆醒地活",
     "kw": ["儆醒", "预备", "盼望主来", "怎样预备", "警醒", "等候主", "活在盼望", "面向永恒", "随时预备"],
     "diag": "愿意为主的再来预备自己，是清醒的爱。儆醒不是恐慌，而是像等候心爱之人回家那样，欢喜而忠心地预备。",
     "way": "三样一起活：① 儆醒——油备足，把心与关系都预备好；② 忠心——运用主所托付的，将来交个好账；"
            "③ 服事——用对最小者的爱见证真信。这样，主来临对你不是惊吓，而是欢喜的重逢。",
     "ref": "路12:37", "text": "主人来了，看见仆人儆醒，那仆人就有福了。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "主必再来，擦干一切眼泪；此刻你也值得有人真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or STATES[4]


def meta() -> Dict[str, Any]:
    return {
        "title": "主再来 · 儆醒地活",
        "source": "帖前4-5；太25 十童女/才干/绵羊山羊",
        "core": "基督必再来；重点不是末世时间表，而是在等候中如何活好今天——儆醒预备、忠心受托、以爱服事最小者。",
        "pictures": ["十童女：儆醒预备，油要备足", "按才干受托：忠心运用、将来交账", "绵羊山羊：以爱最小者见证真信"],
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "太25:13",
        "principle": "「你们要儆醒。」——盼望主再来，不是掐算日子，而是欢喜忠心地预备与服事。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diag"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("主耶稣，你说过你必再来——我信你必成就。当我受苦，求这盼望安慰我：你必回来擦干眼泪、伸张公义、"
                   "更新万有。当我懈怠，求这盼望催醒我：叫我油备足、儆醒忠心地活，运用你所托付我的，"
                   "并用对最小者的爱来见证我真的在等你。愿你来的那日，于我不是惊吓，而是欢喜的重逢。主啊，我愿你来。"),
        "practices": [
            "像随时见主一样活：今天做一件『若主今天回来，我会想已经做好』的事（修复一段关系/一次顺服）。",
            "忠心用托付：想一样神给你的（恩赐/时间/资源），今天忠心地用它服事一个人。",
        ],
        "summary": ("基督必再来。对受苦的，这是擦干眼泪、伸张公义的安慰；对懈怠的，这是儆醒忠心的催促。"
                    "盼望落地成三样：儆醒预备、忠心受托、以爱服事最小者——好叫主来时是欢喜的重逢。"),
        "closing": "「主耶稣啊，我愿你来！」（启22:20）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉帖前4-5 与太25(十童女/才干/绵羊山羊)。核心：基督必再来，"
            "重点不是末世时间表推算，而是在等候中活好今天——儆醒预备、忠心受托、以爱服事最小者；对受苦者是安慰、"
            "对懈怠者是催促；不制造末世恐慌。请针对用户处境温柔应用，给经文、祷告与操练。中文。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"diagnosis\":\"...\",\"way_forward\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("diagnosis", "way_forward", "prayer", "summary", "closing") if data.get(k)} or None
    except Exception:
        return None


def _call_ai(prompt, settings):
    for modname, fn in (("waiting_engine", "call_ai_provider"), ("llm_provider", "call_llm")):
        try:
            mod = __import__(modname); f = getattr(mod, fn, None)
            if f:
                out = f(prompt) if settings is None else f(prompt, settings=settings)
                if out:
                    return out if isinstance(out, str) else str(out)
        except Exception:
            continue
    return None


def formation_signal(result):
    if result.get("crisis"):
        return (["hope", "vigilance", "faithfulness"], False, True, 2.0)
    return (["hope", "vigilance", "faithfulness"], True, True, 4.0)
