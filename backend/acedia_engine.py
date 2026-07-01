"""
acedia_engine.py — 属灵麻木 / 正午的魔鬼（沙漠教父 Evagrius；Kathleen Norris《Acedia & Me》）

与「属灵低潮体检」的诊断不同，本引擎专治古老的 acedia——一种属灵的倦怠/冷淡/『什么都不想做』：
不是悲伤（那是抑郁），而是**不在乎**；对属灵之事（祷告、聚会、圣言）提不起劲，坐立不安又懒散，
想逃到别处/别的事上。沙漠教父称它『正午的魔鬼』（诗91:6「午间灭人的毒病」）——在日头最毒、
最平淡的时候袭来，叫修士离开斗室、荒废本分。

要点：(1)先命名它（acedia 最擅长伪装成『我只是累/需要换换环境』）；(2)分辨与抑郁的不同"
（抑郁需专业帮助；acedia 是属灵倦怠）；(3)对治之道是『逆势而行/持守本分』（stability）——
不凭感觉决定去留，反倒『留在斗室』，做下一件小小的忠心之事；(4)以恒常的小操练，把心重新养回来。

纯函数；确定性；内置危机词检测（若像抑郁/危机，导向专业帮助）；AI 可选增强。
不定罪『你不属灵』，只帮人认出这古老的麻木，并以持守与小操练逆势而行。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "cant", "name": "什么都不想做 / 提不起劲",
     "kw": ["不想做", "提不起劲", "没动力", "懒", "拖着", "无所谓", "不想动", "躺平", "摆烂", "没劲"],
     "diag": "这可能是古老的 acedia——一种属灵的倦怠，不是悲伤，而是『不在乎』。沙漠教父称它『正午的魔鬼』，"
            "专在最平淡的时候袭来，叫人荒废本分。",
     "way": "acedia 的解药是『逆势而行 + 持守本分』：不凭感觉决定，反倒做下一件小小的忠心之事——"
            "哪怕只是把该做的一件事做完、把祷告照旧做一次。行动常先于感觉；持守本分，麻木会慢慢退去。",
     "ref": "加6:9", "text": "我们行善，不可丧志；若不灰心，到了时候就要收成。"},
    {"key": "dry_spiritual", "name": "对祷告读经聚会都冷淡 / 属灵麻木",
     "kw": ["冷淡", "麻木", "祷告不想", "读经没劲", "不想聚会", "属灵冷", "对神无感", "灵性麻木", "干"],
     "diag": "你对属灵之事整体冷了下来——不是怀疑，也不全是低潮，更像 acedia 这种『对神的事提不起劲』的倦怠。",
     "way": "不要因『没感觉』就停掉操练——恰恰相反，凭意志持守简单的操练（就算干巴巴地做）。感觉会回来，"
            "但要靠恒常的小忠心把心养回来。可从最小的开始：每天读一节、祷告一句。别等有感觉才做，做了感觉才回来。",
     "ref": "启2:4-5", "text": "然而有一件事我要责备你，就是你把起初的爱心离弃了……应当回想……行起初所行的事。"},
    {"key": "restless", "name": "坐立不安又懒散 / 总想逃到别处",
     "kw": ["坐立不安", "想逃", "换环境", "别处更好", "待不住", "分心", "想换", "这山望那山", "静不下又不想动"],
     "diag": "又躁又懒、总觉得『别处/别的事会更好』——这正是 acedia 的典型：它想把你从当下的本分与位置上拽走。",
     "way": "沙漠教父的智慧：『留在你的斗室』（stability）。别在倦怠里做重大改变（换教会/放弃承诺/逃离本分）。"
            "把注意力收回到眼前这一件小事上，安住在当下的位置，做完它。安定本身就是对抗『正午的魔鬼』的操练。",
     "ref": "帖前4:11", "text": "又要立志作安静人，办自己的事，亲手做工。"},
    {"key": "vs_depression", "name": "分不清是懒散还是抑郁 / 很沉、很空",
     "kw": ["抑郁", "很沉", "空", "没意义", "分不清", "是不是病", "情绪低", "沉重", "麻木绝望", "撑不动"],
     "diag": "要温柔地分辨：acedia 是属灵的倦怠/不在乎；抑郁是需要照顾、常需专业帮助的病症。两者可以并存。",
     "way": "如果你的低沉持续、影响睡眠食欲、伴随绝望，这更可能是抑郁——请寻求专业帮助，这不是不属灵。"
            "若更像是对属灵之事的倦怠冷淡，则用『持守本分 + 小操练』逆势而行。不确定时，两条路都走：找人帮助，也持守小忠心。",
     "ref": "诗42:11", "text": "我的心哪，你为何忧闷？为何在我里面烦躁？应当仰望神……",
     },
    {"key": "restore", "name": "想从属灵麻木里被重新点燃",
     "kw": ["重新点燃", "找回", "被更新", "回到起初", "重新爱", "点火", "复兴", "重新亲近", "养回来"],
     "diag": "愿意从麻木里回来，是恩典已经在动工——正午的魔鬼最怕你决定持守。",
     "way": "用『微小而恒常』重新养心：定一个极小、跑得掉不了的操练（每天一节经文 + 一句祷告），持续两周；"
            "配一个『安住当下本分』的决心（这段时间不做重大属灵去留的决定）。心是靠一次次小忠心，被慢慢养热的。",
     "ref": "亚4:10", "text": "谁藐视这日的事为小呢？",
     },
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你里面很沉、很麻木。如果你有伤害自己的念头，或长期低落到影响睡眠食欲，请现在就联系"
               "你信任的人或专业帮助——这可能不只是属灵倦怠，也可能是需要照顾的抑郁，寻求帮助不是不属灵。"
               "（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or STATES[0]


def meta() -> Dict[str, Any]:
    return {
        "title": "属灵麻木 · 正午的魔鬼（acedia）",
        "source": "沙漠教父 Evagrius；Kathleen Norris《Acedia & Me》",
        "core": "acedia 是属灵的倦怠/『不在乎』（非悲伤），在平淡时袭来叫人荒废本分；对治是逆势而行、持守本分、以小操练养回心。",
        "distinction": "与抑郁不同：抑郁常需专业帮助；acedia 是属灵倦怠（两者可并存，不确定就两条路都走）。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "加6:9",
        "principle": "沙漠教父的药方：『留在你的斗室』——不凭感觉决定去留，安住本分，做下一件小小的忠心之事。",
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
        "distinction": "温柔分辨：acedia 是属灵倦怠/不在乎；抑郁是需要照顾、常需专业帮助的病症。不确定时，两条路都走。",
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("主啊，我里面有一种说不清的倦怠——对你的事提不起劲，又坐立不安想逃。求你帮我认出这『正午的魔鬼』，"
                   "不被它拽离本分。教我不凭感觉决定，而是安住在你给我的位置，做下一件小小的忠心之事。"
                   "求你用一次次的小操练，把我冷掉的心重新养热；若这沉重超过我能承受，也求你差人来帮助我。"),
        "practices": [
            "逆势做一件小事：现在就做一件你一直拖着、其实五分钟能起步的本分之事——行动先于感觉。",
            "微小而恒常：定一个跑不掉的小操练（每天一节经文+一句祷告），持续两周，把心慢慢养回来。",
        ],
        "summary": ("acedia 是古老的属灵倦怠——不在乎、提不起劲、想逃。它最怕你决定持守。"
                    "别凭感觉决定去留，安住本分，用微小而恒常的忠心逆势而行；若更像抑郁，请寻求专业帮助。"),
        "closing": "「我们行善，不可丧志……到了时候就要收成。」（加6:9）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉沙漠教父的 acedia『正午的魔鬼』与 Kathleen Norris。核心："
            "acedia 是属灵倦怠/『不在乎』(非悲伤)，在平淡时袭来叫人荒废本分；对治是逆势而行/持守本分(留在斗室)、"
            "不凭感觉决定去留、以微小恒常的操练养回心；与抑郁不同(抑郁常需专业帮助，两者可并存)。若像抑郁/危机导向专业帮助。"
            "请针对用户处境温柔诊断，给经文、祷告与操练；不定罪『你不属灵』。中文。\n"
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
        return (["perseverance", "stability", "faithfulness"], False, True, 2.0)
    return (["perseverance", "stability", "faithfulness"], True, True, 4.0)
