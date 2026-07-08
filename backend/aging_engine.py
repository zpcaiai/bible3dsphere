"""
aging_engine.py — 年老 · 善始善终（诗71,90；巴刻《Finishing Our Course with Joy》）

**缺失**的生命阶段主题。人生下半场/暮年的属灵陪伴：如何在体力衰退、角色转变、亲友渐逝、
死亡渐近中，仍向着神欢喜地『把这一程跑完』。

要点：(1)数算自己的日子（诗90:12）——不是病态怕老，而是让有限唤出智慧；(2)老年的呼召不是
『退场』而是继续结果子（诗92:14「年老的时候仍要结果子」）：祝福、代祷、传承、见证；
(3)交托与放手——体力、掌控、角色都在减少，学习把它们交回神手，安息在祂里；(4)向永恒而活，
盼望复活（跑到终点的不是消散，是回家）。

纯函数；确定性；内置危机词检测（暮年↔孤独/无用感/求死相邻，谨慎）；AI 可选增强。
不轻看衰老的失落，只把人从『我没用了/来日无多的惧怕』领向『仍能结果子 + 向永恒的盼望』。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "useless", "name": "觉得自己老了没用了 / 不再被需要",
     "kw": ["没用了", "老了", "不被需要", "累赘", "退场", "帮不上", "被淘汰", "无用", "跟不上", "多余"],
     "diag": "你觉得年纪大了就『没用了』——但圣经说，年老的义人『仍要结果子，要满了汁浆而常发青』。你的季节变了，呼召没变。",
     "way": "老年的果子换了样式：从『做事』转向『祝福、代祷、传承、见证』。你走过的路、你为家人和教会的代求、"
            "你安然的信心，都是极宝贵的果子。别用『还能做多少事』衡量价值——你在神眼中的价值，从不靠产出。"
            "问『这个季节，神要我结的果子是什么』，从一件（为谁代祷、向谁传承）开始。",
     "ref": "诗92:14", "text": "他们年老的时候仍要结果子，要满了汁浆而常发青。"},
    {"key": "decline", "name": "体力/健康衰退带来的失落与不甘",
     "kw": ["体力", "衰退", "记性", "走不动", "力不从心", "不甘", "身体差", "退化", "做不了以前", "老得快"],
     "diag": "身体在退，能做的在减少——这份失落是真实的，不必假装不在意。但『外体毁坏，内心却一天新似一天』。",
     "way": "学习交托与放手：把渐渐减少的体力、掌控、角色，一样样交回神手，安息在祂里。你不再靠『能做多少』站立，"
            "而靠『在基督里是谁』。这个减法的季节，恰恰能让人更纯粹地倚靠神、更深地经历祂的够用。",
     "ref": "林后4:16", "text": "所以，我们不丧胆。外体虽然毁坏，内心却一天新似一天。"},
    {"key": "legacy", "name": "想善用余年 / 留下属灵的传承",
     "kw": ["余年", "传承", "留下", "善用", "见证", "祝福后代", "怎么活好", "剩下的日子", "传给下一代"],
     "diag": "你想把余下的日子活出意义、传下去——这是极美的心愿。诗篇的祷告正是：把神的作为传给下一代。",
     "way": "有意地传承：把你一生看见的神的信实，说给儿孙、后辈听；为他们恒切代求；写下/说出你的见证。"
            "老年是『祝福的季节』——你的手或许颤抖，你的祝福却有分量。选一两个年轻的生命，把你所领受的浇灌下去。",
     "ref": "诗71:18", "text": "神啊，我到年老发白的时候，求你不要离弃我，等我将你的能力指示下代，将你的大能指示后世的人。"},
    {"key": "mortality", "name": "面对死亡渐近的思虑与惧怕",
     "kw": ["死亡", "怕死", "来日无多", "大限", "走了", "临终", "剩下不多", "怕离开", "身后事", "见主"],
     "diag": "死亡渐近，思虑与惧怕会浮上来——这很人性。但对在基督里的人，死不是消散，是回家、是与主同在好得无比。",
     "way": "数算日子，好得着智慧的心（诗90:12）：让有限唤出对永恒的看见，把要紧的事（和好、交托、见证）趁着还有日子去做。"
            "同时把死亡的惧怕交给那位胜过死亡的主——跑到终点的不是坠入虚空，是被父迎接回家。可到『复活盼望』页举目望那日。",
     "ref": "腓1:21,23", "text": "因我活着就是基督，我死了就有益处……情愿离世与基督同在，因为这是好得无比的。"},
    {"key": "lonely_old", "name": "暮年的孤独 / 亲友渐逝、被遗忘",
     "kw": ["孤独", "老伴走了", "亲友", "没人来", "被遗忘", "空巢", "独居老人", "冷清", "一个人老", "没人陪"],
     "diag": "暮年常伴随一层层的失去——老伴、老友、旧日的圈子渐渐散了。这份孤独是慢性受苦的一种，格外需要被神与人托住。",
     "way": "有一位应许『到你们年老，我仍这样；直到你们发白，我仍怀搋』的神，祂不会随岁月离你而去（赛46:4）。"
            "先被祂的同在托住；也主动向还在的人、向教会伸出手，哪怕只留一两段真实的连接。你并不被神遗忘，一个也不。",
     "ref": "赛46:4", "text": "直到你们年老，我仍这样；直到你们发白，我仍怀搋。我已造作，也必保抱；我必怀抱，也必拯救。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失", "不想拖累", "求死", "活够了"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你心里很沉。如果你有伤害自己、觉得自己是累赘或活够了的念头，请现在就联系你信任的人"
               "或当地心理危机热线——你的生命一直是宝贵的，神仍怀抱你，你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or (STATES[2] if len(STATES) > 2 else STATES[0])


def meta() -> Dict[str, Any]:
    return {
        "title": "年老 · 善始善终",
        "source": "诗71,90；巴刻《Finishing Our Course with Joy》",
        "core": "人生下半场/暮年的属灵陪伴：数算日子得智慧、老年仍要结果子（祝福/代祷/传承/见证）、学习交托放手、向永恒盼望复活。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "诗92:14",
        "principle": "「他们年老的时候仍要结果子。」——季节变了，呼召没变；把这一程向着神欢喜地跑完。",
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
        "prayer": ("主啊，我在人生的下半场。有失落、有不甘、有对来日的思虑。谢谢你说，年老的义人仍要结果子——"
                   "求你叫我看见，这个季节你要我结的果子：祝福、代祷、传承、见证。教我把渐渐减少的体力与掌控，"
                   "一样样交回你手，安息在你里。求你叫我数算自己的日子，好得着智慧的心，把要紧的事趁着还有日子去做，"
                   "并欢喜地把这一程向着你跑完——直到发白，你仍怀抱我。"),
        "practices": [
            "结这季节的果子：选一个年轻的生命，本周为他代祷一次、并把你看见的一件神的信实说给他听。",
            "数算日子：安静想『若从永恒回看，我余下的日子最要紧的是什么』，据此定一件趁早去做的事（和好/交托/见证）。",
        ],
        "summary": ("暮年的季节变了，呼召没变：老年仍要结果子——祝福、代祷、传承、见证。学习交托放手、"
                    "数算日子得智慧、向永恒盼望复活。跑到终点的不是消散，是被父迎接回家。"),
        "closing": "「直到你们年老……我仍怀搋。」（赛46:4）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉诗71,90 与巴刻《Finishing Our Course with Joy》。核心：暮年"
            "属灵陪伴——数算日子得智慧(诗90:12)、老年仍要结果子(诗92:14 祝福/代祷/传承/见证)、学习交托放手、向永恒盼望复活"
            "(跑到终点是回家)。不轻看衰老的失落。请针对用户处境温柔陪伴，给经文、祷告与操练；暮年孤独/求死念头导向真人帮助。中文。\n"
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
        return (["legacy", "hope", "trust"], False, True, 2.0)
    return (["legacy", "hope", "trust"], True, True, 4.0)
