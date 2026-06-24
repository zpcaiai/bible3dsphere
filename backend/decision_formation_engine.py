"""
decision_formation_engine.py — Decision Formation Agent / 属灵决策塑造 Agent

把世界观落到具体选择。**不替用户做决定**，而是检查决策背后的动机、恐惧、偶像、
价值排序、圣经原则、现实智慧与群体建议，给出「下一步忠心行动」而非「保证成功方案」。

注：既有 decision_support.py / discernment_engine.py 提供更重的时序+图分析；本引擎
聚焦规格的 10 维省察与 counsel_recommended 标志，可独立使用或与之组合。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore

_MOTIVE_KW = {
    "服事/爱人": ["服事", "帮助", "造就", "爱", "祝福", "需要的人"],
    "荣耀神": ["荣耀神", "讨神喜悦", "顺服", "呼召"],
    "快速成功": ["快速", "成功", "证明自己", "出人头地", "做大"],
    "恐惧驱动": ["怕", "害怕", "错过", "来不及", "被淘汰", "落后"],
    "掌控/安全": ["稳定", "保障", "掌控", "确定", "安全"],
    "野心/比较": ["超过", "比别人", "野心", "赢"],
}
_FEAR_KW = {
    "错过机会": ["错过", "窗口", "来不及", "机会"],
    "失败": ["失败", "搞砸", "做不成"],
    "被淘汰/落后": ["淘汰", "落后", "跟不上"],
    "匮乏": ["没钱", "养不活", "收入"],
    "被否定": ["被否定", "别人怎么看", "丢脸"],
}
_IDOL_KW = {
    "success": ["成功", "证明自己", "出人头地", "做大", "超过"],
    "money": ["赚钱", "快速赚", "收入", "财务", "估值"],
    "control": ["掌控", "稳定", "确定", "保障"],
    "approval": ["被认可", "别人怎么看", "面子"],
}

_BIBLICAL_VALUES = ["忠心（而非保证成功）", "管家职分（时间/钱/恩赐）", "诚实（不夸大、不操控）",
                    "爱人（造就而非利用）", "安息（承认人的有限）"]


def analyze(decision_title: str, decision_context: str, *,
            options: Optional[List[Dict[str, str]]] = None,
            urgency: str = "medium", use_ai: bool = False) -> Dict[str, Any]:
    """对一个具体决策做属灵省察，返回规格结构。"""
    text = f"{decision_title} {decision_context}".lower()

    motives = [name for name, kws in _MOTIVE_KW.items() if any(k.lower() in text for k in kws)]
    fears = [name for name, kws in _FEAR_KW.items() if any(k.lower() in text for k in kws)]
    idols = [name for name, kws in _IDOL_KW.items() if any(k.lower() in text for k in kws)]

    red_flags = _red_flags(text, motives, idols)
    counsel_needed = _counsel_needed(urgency, fears, idols, red_flags)

    out = {
        "decisionTitle": decision_title,
        "detectedMotives": motives or ["（动机尚不明确，值得在祷告中省察）"],
        "detectedFears": fears,
        "detectedIdols": idols,
        "biblicalValues": list(_BIBLICAL_VALUES),
        "wisdomQuestions": _wisdom_questions(),
        "redFlags": red_flags,
        "counselNeeded": counsel_needed,
        "recommendedPeopleToConsult": _people_to_consult(counsel_needed),
        "discernmentSummary": _summary(motives, fears, idols, counsel_needed),
        "nextFaithfulStep": _next_step(counsel_needed, fears),
        "recommendedPractices": _practices(idols),
        "recommendedNextAgents": (["idol_detector"] if idols else []) + ["formation_practice"],
    }
    if not use_ai or _llm is None:
        return out
    system = ("你是属灵决策辅导助手。**不替用户做决定**。基于动机/恐惧/偶像，用中文改写"
              "discernmentSummary（3-5句）与 nextFaithfulStep（一个可执行的『下一步忠心行动』，"
              "而非『做/不做』的结论）。**不要**引用具体经文出处。"
              "只输出 JSON：{\"discernmentSummary\":\"...\",\"nextFaithfulStep\":\"...\"}")
    user = (f"决定：{decision_title} — {decision_context[:800]}\n动机：{motives}\n恐惧：{fears}\n"
            f"偶像：{idols}\n当前 summary：{out['discernmentSummary']}\n当前 nextStep：{out['nextFaithfulStep']}")
    try:
        ai = _llm.enhance(system, user, temperature=0.5, max_tokens=500)
        return _llm.merge_fields(out, ai, ["discernmentSummary", "nextFaithfulStep"])
    except Exception:
        return out


def _wisdom_questions() -> List[str]:
    return [
        "这个选择的真实动机是荣耀神、服事人，还是证明自己？",
        "我是否正被害怕失败、贫穷或被看不起所驱动？",
        "在神、家庭、教会、使命、金钱、效率之间，我的排序失序了吗？",
        "这条路是否需要我隐瞒、操控或夸大什么？",
        "这个选择会造就人，还是利用人？",
        "我是否愿意接受属灵同伴和智慧人的建议，即使他们可能拦阻我？",
        "三年后回看，这个选择会把我塑造成怎样的人？",
    ]


def _red_flags(text: str, motives: List[str], idols: List[str]) -> List[str]:
    flags = []
    if "恐惧驱动" in motives:
        flags.append("决定主要由恐惧/紧迫感驱动——不宜在不安中拍板。")
    if "快速成功" in motives or "success" in idols:
        flags.append("有用决定证明自己价值的迹象——留意成就偶像。")
    if any(k in text for k in ["不能告诉", "隐瞒", "先不说", "夸大"]):
        flags.append("出现需要隐瞒或夸大的信号——诚实受威胁。")
    if any(k in text for k in ["马上", "立刻", "今天就", "现在就"]):
        flags.append("时间压力很大——警惕被『窗口』叙事推着走。")
    return flags


def _counsel_needed(urgency: str, fears: List[str], idols: List[str], red_flags: List[str]) -> bool:
    return bool(fears) or bool(idols) or bool(red_flags) or urgency == "high"


def _people_to_consult(counsel_needed: bool) -> List[str]:
    if not counsel_needed:
        return ["一位成熟的属灵同伴（让决定被看见）"]
    return ["牧者 / 小组长", "一位认识你、敢于诚实拦阻你的属灵长者",
            "相关领域有经验、且敬畏神的人（做现实尽调）"]


def _summary(motives: List[str], fears: List[str], idols: List[str], counsel: bool) -> str:
    parts = []
    if motives:
        parts.append("动机里既有好的，也可能混着需要省察的：" + "、".join(motives[:3]))
    if fears:
        parts.append("注意恐惧的影响：" + "、".join(fears[:2]))
    if idols:
        parts.append("留意可能的偶像：" + "、".join(idols[:2]))
    tail = "建议先寻求属灵同伴的印证，再做决定。" if counsel else "可在祷告与省察后从容推进。"
    return "（这不是替你做决定）" + "；".join(parts) + "。" + tail


def _next_step(counsel_needed: bool, fears: List[str]) -> str:
    if counsel_needed:
        return ("下一步忠心行动：本周不拍板，先安排与一位属灵长者的对话，把动机、恐惧与选项"
                "如实摊开；同时用 24 小时不在焦虑中做决定，记录祷告中的领受。")
    return "下一步忠心行动：在祷告中把这个决定交托，写下你愿意顺服神带领的具体一步，并设一个复盘日期。"


def _practices(idols: List[str]) -> List[str]:
    out = ["决策前的安息：留一段不解决问题、只在神面前安静的时间。"]
    if "success" in idols or "money" in idols:
        out.append("反偶像操练：先决定『无论结果如何，我在神面前的价值不变』，并写下来。")
    return out


def meta() -> Dict[str, Any]:
    return {"dimensions": list(_MOTIVE_KW.keys()),
            "principle": "不替用户决定；生成下一步忠心行动，而非保证成功方案。"}
