"""
perfectionism_engine.py — 完美主义 · 内在批判者 → 恩典

最贴合本系统「不定罪」铁律的一味。完美主义把「价值」绑在「表现」上；内在批判者是那个不断说
「不够好」的声音。它常伪装成高标准，底下却是：靠表现赚接纳、怕失败/羞耻、想用掌控换安全。

真理：在基督里你已经被完全接纳——那位批判的声音不是神的声音。神的良善引人悔改（而非鞭打），
祂向软弱者柔和谦卑。分辨「追求卓越」（健康、以爱为动力、能安息）与「完美主义」（把自我价值押在表现上、
永不满足、不敢失败、无法安息）。对策：把批判者的那句话，换成基督对你说的那句话。

纯函数；确定性；内置危机词检测 + 自我攻击/羞耻升级检测（命中先托住恩典）；AI 可选增强。
不加新的「你要少一点完美主义」的重担，只把人从内在批判者领回基督温柔的声音。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "never_enough", "name": "做什么都觉得不够好",
     "kw": ["不够好", "永远不够", "做得不好", "达不到", "不满意自己", "还不够", "总有瑕疵", "不完美", "做不好"],
     "critic": "『你还不够好。』",
     "christ": "『你在我里面已经蒙悦纳——不是因为你做到了，而是因为我为你做成了。』",
     "way": "那句『不够好』不是神的声音。神看你，看的是基督的完全，不是你的成绩单。今天当批判者开口，"
            "就用基督的话回它：我已被完全接纳。你的价值是被给予的，不是被赚取的。",
     "ref": "西2:10", "text": "你们在他里面也得了丰盛。他是各样执政掌权者的元首。"},
    {"key": "fear_fail", "name": "怕失败 / 不敢开始、拖延",
     "kw": ["怕失败", "不敢开始", "拖延", "怕做错", "怕搞砸", "迟迟不", "怕丢脸", "完美才敢", "怕不完美"],
     "critic": "『如果做不好/失败了，你就完了。』",
     "christ": "『你可以失败，因为你的身份不押在结果上——我的爱不因你的成败而改变。』",
     "way": "怕失败，是因为把身份押在了表现上。但你在基督里的地位不由结果决定。松开『必须完美才动手』，"
            "允许自己做出『足够好』的一步——不完美的顺服，胜过完美的瘫痪。",
     "ref": "林后12:9", "text": "我的恩典够你用的，因为我的能力是在人的软弱上显得完全。"},
    {"key": "harsh", "name": "对自己极苛刻 / 内在批判者很凶",
     "kw": ["苛刻", "批判", "骂自己", "自我攻击", "内在声音", "对自己狠", "毒舌", "折磨自己", "跟自己过不去"],
     "critic": "『你真没用、真差劲、又搞砸了。』",
     "christ": "『我心里柔和谦卑；我不折断压伤的芦苇。到我这里来，我使你得安息。』",
     "way": "分辨两个声音：控告者只带来碾压与绝望；圣灵的提醒带来盼望与转向。你对自己说话的方式，"
            "该像神对你说话——温柔、诚实、带盼望。把那句苛刻的自我攻击，写下来，划掉，换上基督的话。",
     "ref": "太11:29", "text": "我心里柔和谦卑，你们当负我的轭，学我的样式，这样，你们心里就必得享安息。"},
    {"key": "control", "name": "必须掌控一切 / 无法放松、不能出错",
     "kw": ["掌控", "不能出错", "无法放松", "必须完美", "控制", "不能松懈", "紧绷", "凡事亲力", "怕失控"],
     "critic": "『一切都得在你掌控中、不能有一点差错，否则会塌。』",
     "christ": "『你不必扛住全世界——扶持万有的是我，不是你。你可以松手、可以安息。』",
     "way": "完美主义常是伪装的掌控焦虑。真正托住万有的是神，不是你的严丝合缝。练习交出一件『不完美也没关系』"
            "的事，让自己经历：松手了，天不会塌——因为扶持的是祂。",
     "ref": "诗127:1-2", "text": "若不是耶和华建造房屋，建造的人就枉然劳力……他所亲爱的，必叫他安然睡觉。"},
    {"key": "rest", "name": "想从表现的重担里被释放 / 学会安息",
     "kw": ["释放", "安息", "放过自己", "不再逼", "喘口气", "接纳自己", "轻省", "被恩典", "松一口气"],
     "critic": "『你必须一直努力，才配停下来。』",
     "christ": "『凡劳苦担重担的，到我这里来，我就使你们得安息。』",
     "way": "你不必用不停的努力来证明自己值得存在。恩典的意思是：接纳在先，努力在后——你是从被爱里去活，"
            "不是为了被爱而活。今天给自己一段『不产出』的安息，作为相信恩典的操练。",
     "ref": "太11:28", "text": "凡劳苦担重担的人，可以到我这里来，我就使你们得安息。"},
]

SHAME_ESCALATE = ["我一无是处", "我恨自己", "我配不上活", "我是失败品", "我最差", "没救了"]


def _detect_shame(text: str) -> bool:
    return any(w in (text or "") for w in SHAME_ESCALATE)


CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你对自己的苛责已经很重了。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "神向你不是那个批判的声音，而是柔和谦卑的怀抱——你值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    if _detect_shame(t):
        return next(d for d in STATES if d["key"] == "harsh")
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or STATES[0]


def meta() -> Dict[str, Any]:
    return {
        "title": "完美主义 · 内在批判者 → 恩典",
        "source": "恩典神学（配合系统「不定罪」铁律）；太11:28-29",
        "core": "完美主义把价值绑在表现上，内在批判者说『不够好』——但那不是神的声音；在基督里你已被完全接纳。",
        "distinction": "追求卓越(健康、以爱为动力、能安息) vs 完美主义(把自我价值押在表现、永不满足、不敢失败、无法安息)。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "太11:28-29",
        "principle": "把内在批判者的那句话，换成基督对你说的那句话——神的良善引人悔改，而非鞭打。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    shame = _detect_shame(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "shame_flag": shame,
        "state": {"key": picked["key"], "name": picked["name"]},
        "inner_critic": picked["critic"],
        "christ_voice": picked["christ"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("主啊，我里面有个声音一直说我不够好——今天我要认出：那不是你的声音。谢谢你，在基督里我已经"
                   "被你完全接纳，不是因为我做到了，而是因为你为我做成了。求你把那个苛刻的批判者的声音，"
                   "换成你柔和谦卑的声音；教我从被你爱里去活，而不是为了被爱去拼命。求你叫我在你里面得安息。"),
        "practices": [
            "换掉那句话：把内在批判者的话（"+picked["critic"]+"）写下来，划掉，写上基督的话（"+picked["christ"]+"）。",
            "允许一次『足够好』：今天刻意把一件事做到『足够好』就交出去，作为相信『接纳在先、努力在后』的操练。",
        ],
        "summary": ("那个说『不够好』的内在批判者，不是神的声音。在基督里你已被完全接纳；把批判者的话，"
                    "换成基督对你说的话。追求卓越可以带着安息，完美主义却把价值押在表现上。"),
        "closing": "「到我这里来……我就使你们得安息。」（太11:28）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，处理完美主义与内在批判者。核心：完美主义把价值绑在表现上，"
            "内在批判者说『不够好』但那不是神的声音；在基督里已被完全接纳；分辨追求卓越(健康、能安息)与完美主义"
            "(押价值于表现、不敢失败、无法安息)；对策是把批判者的话换成基督的话(太11:28-29 柔和谦卑)。"
            "请针对用户处境，指出内在批判者的话与基督的话，给经文、祷告与操练；绝不加『你要少完美主义』的新重担。中文。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"inner_critic\":\"...\",\"christ_voice\":\"...\",\"way_forward\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("inner_critic", "christ_voice", "way_forward", "prayer", "summary", "closing") if data.get(k)} or None
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
    if result.get("crisis") or result.get("shame_flag"):
        return (["grace", "identity", "rest"], False, True, 2.0)
    return (["grace", "identity", "rest"], True, True, 4.0)
