"""
vocation_worldview_engine.py — Vocation Worldview Agent / 职业使命世界观 Agent

从圣经世界观看工作、创业、AI 产品、投资、财富、职业选择、使命、治理与成功。
不是职业规划，而是诊断职业观是否被成就/金钱/控制/比较/恐惧驱动，并重塑为
「呼召、忠心、治理、服事、管家职分」的框架。

注：本引擎独立运行；如需更深的恩赐/呼召数据，可与既有 gift_calling_engine 组合。
"""
from __future__ import annotations

from typing import Any, Dict, List

try:
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore

# 职业观诊断维度的关键词
_WORK_IDOL_KW = {
    "success": ["成功", "证明自己", "超过别人", "出人头地", "赢", "成就"],
    "money": ["赚钱", "快速赚", "财务自由", "暴富", "收入", "估值", "变现"],
    "control": ["掌控", "确定", "稳定", "不能失败", "风险太大"],
    "approval": ["被认可", "别人怎么看", "面子", "名声"],
}

_KINGDOM_KW = ["服事", "祝福", "造就", "帮助人", "使命", "见证", "国度", "灵命", "福音"]
_AI_PRODUCT_KW = ["ai", "产品", "应用", "平台", "用户", "创业", "技术"]


def analyze(vocation_context: str, *, current_question: str = "",
            use_ai: bool = False) -> Dict[str, Any]:
    """诊断职业使命世界观，返回规格结构。"""
    text = f"{vocation_context} {current_question}".lower()

    possible_idols: List[str] = []
    for idol, kws in _WORK_IDOL_KW.items():
        if any(k.lower() in text for k in kws):
            possible_idols.append(idol)

    work_view = _work_view(text, possible_idols)
    money_view = _money_view(text, possible_idols)
    success_view = _success_view(text, possible_idols)
    calling_view = _calling_view(text)

    kingdom = _kingdom_opportunities(text)
    ethical = _ethical_risks(text)

    next_agents = ["decision_formation", "formation_practice"]
    if possible_idols:
        next_agents.insert(0, "idol_detector")

    out = {
        "vocationContext": vocation_context,
        "currentQuestion": current_question,
        "workViewDetected": work_view,
        "callingViewDetected": calling_view,
        "moneyViewDetected": money_view,
        "successViewDetected": success_view,
        "possibleIdols": possible_idols,
        "kingdomOpportunities": kingdom,
        "ethicalRisks": ethical,
        "biblicalVocationFrame": _biblical_frame(text, possible_idols),
        "suggestedNextSteps": _next_steps(possible_idols, text),
        "recommendedPractices": _practices(possible_idols),
        "recommendedNextAgents": list(dict.fromkeys(next_agents)),
    }
    if not use_ai or _llm is None:
        return out
    system = ("你是基督教工作/使命神学助手。基于诊断，用中文改写 biblicalVocationFrame（3-5句）："
              "把工作视为创造与治理使命，赚钱为管家职分，成功为忠心的可能果子，技术/创业为受托工具。"
              "**不要**引用具体经文出处。只输出 JSON：{\"biblicalVocationFrame\":\"...\"}")
    user = (f"职业处境：{vocation_context[:800]}\n问题：{current_question[:400]}\n"
            f"可能偶像：{possible_idols}\n当前 frame：{out['biblicalVocationFrame']}")
    try:
        ai = _llm.enhance(system, user, temperature=0.5, max_tokens=500)
        return _llm.merge_fields(out, ai, ["biblicalVocationFrame"])
    except Exception:
        return out


def _work_view(text: str, idols: List[str]) -> str:
    if "success" in idols:
        return "工作可能正被当作证明自己价值的舞台（成就→身份）。"
    return "工作可被理解为创造使命的一部分——值得进一步省察动机。"


def _money_view(text: str, idols: List[str]) -> str:
    if "money" in idols:
        return "金钱可能被当作安全感与成功证据（赚钱→安心/价值），而非托管资源。"
    return "金钱观尚不明显；可省察它在你心中是工具还是主人。"


def _success_view(text: str, idols: List[str]) -> str:
    if "success" in idols or "approval" in idols:
        return "成功可能被当作身份来源，而非忠心的可能果子。"
    return "成功观尚不明显。"


def _calling_view(text: str) -> str:
    if any(k in text for k in _KINGDOM_KW):
        return "已带有服事/使命的意识——好的起点，需让它居于成就与金钱动机之上。"
    return "呼召意识尚不清晰；可从『我的工作如何服事人、荣耀神』开始省察。"


def _kingdom_opportunities(text: str) -> List[str]:
    out = []
    if any(k in text for k in _AI_PRODUCT_KW):
        out.append("用技术/产品服事人的灵命成长与真实需要。")
        out.append("以诚实、不操控的设计见证神的国（反成瘾、尊重用户）。")
    out.append("在所在行业以卓越与正直作光作盐，造就同事与客户。")
    return out


def _ethical_risks(text: str) -> List[str]:
    risks = []
    if any(k in text for k in _AI_PRODUCT_KW):
        risks += ["操控用户、制造依赖/成瘾", "夸大属灵效果、滥用属灵权威", "用户隐私与数据风险"]
    if "money" in " ".join(_WORK_IDOL_KW["money"]) and any(k in text for k in _WORK_IDOL_KW["money"]):
        risks.append("为快速变现而牺牲诚实或人的益处")
    if "success" in text or any(k in text for k in _WORK_IDOL_KW["success"]):
        risks.append("把事工/事业当作自我称义，导致 burnout 与操纵")
    return risks or ["在压力下可能为结果妥协诚实或爱人。"]


def _biblical_frame(text: str, idols: List[str]) -> str:
    return (
        "工作是神创造与治理使命的一部分（创2:15）；赚钱是管家职分而非自我称义（路16:10-11）；"
        "成功若来临，是忠心的可能果子，而非身份来源（林前4:2）。技术与创业是受托的工具，"
        "用来服事人、造就人，而非荣耀自己。先求神的国（太6:33），让职业服在使命之下。"
    )


def _next_steps(idols: List[str], text: str) -> List[str]:
    steps = ["写下这个职业选择中：我真正的动机、恐惧与盼望各是什么。",
             "把决定带到祷告与一两位属灵长者面前寻求印证（不只靠自己判断）。"]
    if "money" in idols:
        steps.append("设定一个『够用』的标准，预先决定盈余如何用于奉献与祝福他人。")
    if any(k in text for k in _AI_PRODUCT_KW):
        steps.append("为产品立下不操控、不制造依赖、保护隐私的伦理底线。")
    steps.append("未来 7 天做一个『隐藏的忠心』行动，操练不靠成果定义价值。")
    return steps


def _practices(idols: List[str]) -> List[str]:
    out = ["安息操练：设定不工作、不查收益的安息时段。"]
    if "success" in idols:
        out.append("反成就操练：做一件无人看见的服事。")
    if "money" in idols:
        out.append("奉献操练：为一个具体的人或事奉献。")
    return out


def meta() -> Dict[str, Any]:
    return {"workIdols": list(_WORK_IDOL_KW.keys()),
            "note": "诊断工作/金钱/成功/呼召观，重塑为管家职分与使命。"}
