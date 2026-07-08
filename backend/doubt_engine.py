"""
doubt_engine.py — 与怀疑同行 / 信心危机（牧养向，非护教辩论）

apologetics 引擎处理「世界观论证」；本引擎补一件不同的事——**牧养正在怀疑的人**：
不急着赢辩论，先接住「我信不动了」，陪他把疑问诚实地带到神面前。

核心立场：
  · 怀疑不等于背叛，也不等于失丧——圣经里满了带着疑问仍抓住神的人（诗篇的哀歌、施洗约翰在狱中、多马）。
  · 分辨怀疑的**种类**：理性的疑问（有答案可寻）、受伤的怀疑（被人或苦难所伤）、枯竭的怀疑（属灵低谷）、
    道德性的逃避（想为选择找借口）——不同的怀疑，需要不同的回应。
  · 不轻看疑问、也不否定真理；把怀疑当作可以「带到神面前」的东西，而非必须先自己解决的羞耻。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。附「可继续寻求」的温柔出口
（把理性问题导向 apologetics/牧者，把受伤/枯竭导向 lament/spirits/真人陪伴）。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

KINDS: List[Dict[str, Any]] = [
    {"key": "intellectual", "name": "理性的疑问（这信得住吗）",
     "kw": ["证据", "科学", "理性", "逻辑", "矛盾", "怎么证明", "真的假的", "站得住", "可信吗", "为什么信"],
     "diagnosis": "你的怀疑更多是『理性的疑问』——你想知道这信得住吗。这是好问题，信仰经得起诚实的追问。",
     "way": "带着问题去寻求，而不是带着问题躲开。多数疑问都有认真的回应（可到『护教视角』或找成熟的信徒/牧者深谈）。"
            "同时记得：没有人是先把所有问题都想通了才信的——可以带着未解的问题，仍抓住你已知的那位。",
     "ref": "可9:24", "text": "我信！但我信不足，求主帮助。",
     "route": "理性问题可继续到『护教视角』模块，或找成熟信徒/牧者深谈。"},
    {"key": "wounded", "name": "受伤的怀疑（被人或苦难伤了）",
     "kw": ["受伤", "苦难", "为什么让", "教会伤", "被伤害", "祷告没用", "神在哪", "失望", "痛", "不管我"],
     "diagnosis": "你的怀疑底下，藏着一个伤口——这不是逻辑问题，是心痛。苦难或人的伤，让你对神起了疑。",
     "way": "这不需要先被辩赢，需要先被听见。你可以像诗人一样，把不解与痛直接向神哭诉（这在圣经里是被允许的）。"
            "神能承受你的质问；把伤带到祂面前，比自己躲起来硬扛更近祂。",
     "ref": "诗13:1-2", "text": "耶和华啊，你忘记我要到几时呢？……我心里筹算，终日愁苦，要到几时呢？",
     "route": "受伤的怀疑可到『哀歌』把痛谱成祷告；必要时找真人牧养陪伴。"},
    {"key": "dry", "name": "枯竭的怀疑（属灵低谷、感觉不到神）",
     "kw": ["枯竭", "低谷", "感觉不到", "冷淡", "干", "麻木", "没有神的同在", "空", "信心变淡", "提不起"],
     "diagnosis": "你的怀疑可能来自属灵的枯竭期，而非真的想通了什么——低谷里，感觉先撤退，怀疑就趁虚而入。",
     "way": "低谷不等于失丧。这时不要凭枯竭改弦更张（依纳爵：枯竭中不改先前在安慰中所立的方向）。"
            "凭已知的真理而行，而非凭此刻的感觉；持守简单的操练，等候同在回来。",
     "ref": "诗42:11", "text": "我的心哪，你为何忧闷？……应当仰望神，因我还要称赞他。",
     "route": "枯竭的怀疑可到『诸灵分辨』（安慰/枯竭）或『默观』安歇。"},
    {"key": "moral", "name": "想为一个选择找借口的怀疑",
     "kw": ["借口", "想放纵", "不想守", "反正", "太难守", "想放弃信", "束缚", "自由", "不想被管"],
     "diagnosis": "有时怀疑是心先想走某个方向，再回头找理由——诚实地问：我是真有疑问，还是想为一个选择松绑？",
     "way": "这不是定你的罪，而是请你对自己诚实。若怀疑底下是一个想放纵的欲望，真正的问题不在『信不信得过』，"
            "而在『愿不愿顺服』。把这也带到神面前——祂看得见，也仍然爱你，愿意帮助你回转。",
     "ref": "约7:17", "text": "人若立志遵着他的旨意行，就必晓得这教训或是出于神，或是我凭着自己说的。",
     "route": "可结合『悔改的解剖』诚实面对底层的欲望。"},
    {"key": "companion", "name": "只是想在怀疑里被陪伴 / 不知道自己怎么了",
     "kw": ["不知道", "陪伴", "迷茫", "怎么了", "信不动", "累了", "撑着", "说不清", "混乱", "想聊聊"],
     "diagnosis": "你不确定自己的怀疑是哪一种，只知道信得很吃力。没关系——你不必先诊断清楚才能被神接住。",
     "way": "先把最诚实的一句话对神说出来，哪怕是『主啊，我信不动了』。怀疑不是神经受不了的东西；"
            "带着它来，比假装没事更蒙祂喜悦。慢慢来，你不必今天就把一切想清楚。",
     "ref": "犹1:22", "text": "有些人存疑心，你们要怜悯他们。",
     "route": "可找一位成熟、安全的信徒同行，不必独自在怀疑里。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "你的怀疑与痛都可以带到神面前，你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in KINDS:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or KINDS[4]


def meta() -> Dict[str, Any]:
    return {
        "title": "与怀疑同行",
        "source": "牧养向（非护教辩论）：诗篇的哀歌 · 多马 · 施洗约翰的疑问",
        "core": "怀疑不等于背叛；分辨怀疑的种类（理性/受伤/枯竭/道德逃避），把疑问带到神面前，而非当作必须先独自解决的羞耻。",
        "kinds": [{"key": d["key"], "name": d["name"]} for d in KINDS],
        "verse": "可9:24",
        "principle": "「我信！但我信不足，求主帮助。」——你可以带着未解的问题，仍抓住你已知的那位。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "kind": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diagnosis"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "next_route": picked["route"],
        "prayer": ("主啊，我信不动了，但我还是来到你面前。谢谢你没有因我的疑问就丢下我。"
                   "我把我的问题、我的伤、我的枯竭，都诚实地摆在你面前——求你怜悯我这存疑心的人。"
                   "我信，但我信不足，求你帮助我。在我看不清的时候，求你抓住我，因为我抓不住的时候，你没有松手。"),
        "practices": [
            "对神说最诚实的一句：哪怕是『主啊，我信不动了』——把怀疑带到祂面前，而不是躲开祂。",
            "继续寻求：" + picked["route"],
        ],
        "summary": ("怀疑不等于背叛。先分清它是理性的疑问、受伤的怀疑、枯竭的怀疑，还是想为选择松绑——"
                    "然后把它带到神面前。你可以带着未解的问题，仍抓住你已知的那位。"),
        "closing": "「我信！但我信不足，求主帮助。」（可9:24）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心、牧养向（非辩论）的属灵陪伴者。核心：怀疑不等于背叛；"
            "分辨怀疑的种类——理性的疑问(可寻答案)、受伤的怀疑(被人/苦难所伤)、枯竭的怀疑(属灵低谷)、"
            "道德性的逃避(为选择找借口)，并把疑问带到神面前而非当羞耻。请针对用户处境，温柔分辨其怀疑的种类，"
            "给不急于辩赢的回应、经文、祷告与一个『继续寻求』的出口。中文，绝不轻看疑问、也不否定真理。\n"
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
    for modname, fn in (("engine_ai", "call_ai"),):
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
        return (["faith", "honesty", "seeking"], False, True, 2.0)
    return (["faith", "honesty", "seeking"], True, True, 4.0)
