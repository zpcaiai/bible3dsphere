"""
contemplation_engine.py — 默观 / 与神独处的爱（诺里奇的朱利安《神圣之爱的启示》；
大德兰《七宝楼台》Interior Castle；《未知之云》The Cloud of Unknowing）

补默观传统的「情感线」（系统已有约翰十字架的枯竭线，缺朱利安的盼望与神之慈爱）。
本引擎接住一种「心的躁动」，用默观经典引它安歇在神的爱里。

三条经典的核心（**均附教义提示：以圣经为最终准绳、以基督为中心**）：
  · **诺里奇的朱利安**：在神的爱里，「凡事都必好，凡事都必好，万事都必好」——不是否认痛苦，
    而是深信神的爱托住万有；「我们被神包裹，如同衣裳」。（对治焦虑/惧怕未来）
  · **《未知之云》**：神不能被「想通」，只能被「爱进」——用一支「爱的箭」穿过思绪的云，
    单单向着神。（对治过度思虑/分析瘫痪）
  · **大德兰《七宝楼台》**：灵魂是一座城堡，越往里走越靠近居于中心的神——默观是回到内室与神独处。（对治想更深的亲密）

教义护栏：这些是宗教改革前的天主教默观传统，取其「安息于神的爱、与神独处」之精神；
凡与圣经相悖处以圣经为准；默观不是掏空自我或神秘经验的追逐，而是在基督里安歇、被神的爱充满。
纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不追逐玄秘，只把人领进「在神爱里的安息」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "anxious", "name": "焦虑 / 怕未来会不好",
     "kw": ["焦虑", "担心", "怕未来", "不安", "忧虑", "怕出事", "惶恐", "会不会", "灾难化", "睡不着"],
     "voice": "诺里奇的朱利安", "note": "朱利安在异象里反复听见的话：「凡事都必好，凡事都必好，万事都必好。」",
     "way": "这不是叫你否认难处，而是把难处放进一个更大的确据里：神的爱托住万有，你「被神包裹，如同衣裳」。"
            "今天不必看清全程，只需信托住你的那双手。",
     "ref": "彼前5:7", "text": "你们要将一切的忧虑卸给神，因为他顾念你们。",
     "practice": "呼吸祷告：吸气默念「凡事都必好」，呼气默念「因你的爱托住我」，重复 5–10 次，把忧虑一次次交出。"},
    {"key": "overthink", "name": "想太多 / 停不下分析、钻牛角尖",
     "kw": ["想太多", "停不下", "钻牛角尖", "反刍", "分析", "脑子停不下", "纠结", "越想越", "思绪乱", "内耗"],
     "voice": "《未知之云》", "note": "《未知之云》说：神不能被想通，只能被爱进。",
     "way": "你一直想「弄明白」，但有些事不是用头脑攻破的，是用爱安歇的。放下要想通的努力，"
            "用一支「爱的箭」——一个短词（如「耶稣」「主啊」）——一次次轻轻回到神那里，让思绪的云暂时落下。",
     "ref": "诗46:10", "text": "你们要休息，要知道我是神。",
     "practice": "定念祷告：选一个词（耶稣/父/爱），每当思绪飘走，就温柔地用这个词把心带回神面前，做 5 分钟。"},
    {"key": "distant", "name": "觉得离神很远 / 想更深地亲近神",
     "kw": ["离神远", "亲近", "更深", "进不去", "隔", "冷淡", "想亲近", "独处", "安静不下来", "渴慕神"],
     "voice": "大德兰《七宝楼台》", "note": "大德兰把灵魂比作一座城堡，神住在最内的居所，默观就是往里走、与祂独处。",
     "way": "亲近神不在更用力，而在更安静地往里走。退到一个安静处，放下外面的喧嚣，一层层向内，"
            "去到那位一直住在你里面（借着圣灵）的主面前，只是与祂同在，不必说很多话。",
     "ref": "太6:6", "text": "你祷告的时候，要进你的内屋，关上门，祷告你在暗中的父。",
     "practice": "独处片刻：找一个安静角落，关掉手机 10 分钟，只对神说一句「我在这里，你也在这里」，然后安静与祂同在。"},
    {"key": "restless", "name": "心里静不下来 / 一直很躁",
     "kw": ["静不下", "烦躁", "躁", "坐不住", "不安宁", "心乱", "浮躁", "停不下来", "闲不住", "紧绷"],
     "voice": "奥古斯丁 & 朱利安", "note": "奥古斯丁：「我的心不得安息，直到安息在你里面。」",
     "way": "你的躁，其实是心在找它真正的归宿。默观不是又一件要做的事，而是「停下来，被爱」。"
            "允许自己什么都不产出，只是在神面前安歇一会儿——你的价值不靠不停地动来证明。",
     "ref": "太11:28", "text": "凡劳苦担重担的人，可以到我这里来，我就使你们得安息。",
     "practice": "安歇一分钟：坐下，手心向上放在膝上，做几次慢呼吸，对神说「我不必抓住一切，你抓住我」。"},
]

DOCTRINE_NOTE = (
    "【温柔的教义提示】以上取自宗教改革前的默观传统，我们只取其「安息于神的爱、与神独处」的精神；"
    "凡事以圣经为最终准绳，以基督为中心。默观不是掏空自我或追逐神秘经验，而是在基督里安歇、被神的爱充满。"
)

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。此刻先不谈默观操练——如果你有伤害自己的念头，请现在就联系你信任的人"
    "或当地心理危机热线。神的爱此刻正包裹着你，你也值得有人真实地陪着你。（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for s in STATES:
        hits = sum(1 for k in s["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, s
    return best or STATES[3]


def meta() -> Dict[str, Any]:
    return {
        "title": "默观 · 在神爱里安息",
        "source": "诺里奇的朱利安《神圣之爱的启示》；大德兰《七宝楼台》；《未知之云》",
        "core": "默观不是追逐玄秘或掏空自我，而是在基督里安歇、被神的爱充满；神不能被想通，只能被爱进。",
        "states": [{"key": s["key"], "name": s["name"]} for s in STATES],
        "doctrine_note": DOCTRINE_NOTE,
        "verse": "诗131:2",
        "principle": "「我的心平稳安静，好像断过奶的孩子在他母亲的怀中；我的心在我里面真像断过奶的孩子。」",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "voice": picked["voice"],
        "voice_note": picked["note"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "contemplative_practice": picked["practice"],
        "doctrine_note": DOCTRINE_NOTE,
        "prayer": ("主啊，我的心一直在动、在想、在抓。此刻我愿意停下来，什么都不产出，只是来到你面前。"
                   "谢谢你早已住在我里面，谢谢你的爱包裹着我。求你让我的心平稳安静，像断过奶的孩子安歇在母亲怀中——"
                   "在你里面，凡事都必好。"),
        "practices": [
            picked["practice"],
            "安息片刻后，读一遍锚点经文（" + picked["ref"] + "），把它当作神此刻对你说的话。",
        ],
        "summary": ("默观是「停下来，被爱」。心躁时不必更用力，而是更安静地回到那位住在你里面的主——"
                    "祂的爱托住万有，在祂里面，凡事都必好。"),
        "closing": "「你们要休息，要知道我是神。」（诗46:10）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉诺里奇的朱利安《神圣之爱的启示》、大德兰《七宝楼台》"
        "与《未知之云》。核心：默观不是追逐玄秘或掏空自我，而是在基督里安歇、被神的爱充满；"
        "『凡事都必好』（朱利安）、『神不能被想通，只能被爱进』（未知之云）。请针对用户心的躁动，温柔引导，"
        "给一个默观小操练（呼吸祷告/定念祷告/独处）、经文与祷告，并附一句『以圣经为准、基督为中心』的教义提示。"
        "中文，温暖不说教，绝不引导追逐神秘经验或掏空式冥想。\n"
        f"用户处境：{text}\n"
        "请输出 JSON：{\"way_forward\":\"...\",\"contemplative_practice\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("way_forward", "contemplative_practice", "prayer", "summary", "closing") if data.get(k)} or None
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
        return (["presence", "rest", "love"], False, True, 2.0)
    return (["presence", "rest", "love"], True, True, 4.0)
