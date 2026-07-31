from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


@dataclass
class SafetyDecision:
    status: str = "ready"
    risk_level: str = "low"
    reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    human_review_required: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


CRISIS = re.compile(r"(不想活|想死|自杀|自傷|自伤|伤害自己|殺了他|杀了他|suicid|kill myself)", re.I)
ABUSE = re.compile(r"(家暴|性侵|虐待|被控制|被教会威胁|domestic violence|sexual assault|abuse)", re.I)
SCRUPULOSITY = re.compile(r"(反复认罪|认罪几个小时|神不会赦免|每天检查是否得救|任何.*都是罪)")
BLOCKED_CLAIMS = {
    "salvation_verdict": re.compile(r"(一定没得救|神已经弃绝|必定下地狱|你一定没得救)"),
    "demonic_claim": re.compile(r"(被鬼附|邪灵控制|魔鬼化身)"),
    "clinical_diagnosis": re.compile(r"(他就是精神病|人格障碍|自恋型人格障碍)"),
    "harassment_or_doxxing": re.compile(r"(开盒|人肉|住址|身份证|网暴|举报轰炸|围攻|骚扰)"),
    "coercive_gospel": re.compile(r"(你不接受就|拒绝福音说明|必须现在决志否则)"),
    "prosperity_promise": re.compile(r"(信了就一定发财|接受耶稣就不会生病|保证事业成功)"),
}
RISKY_ASSERTIONS = {
    "unsupported_illegal_claim": re.compile(r"(他就是骗子|诈骗犯|犯罪分子)"),
    "hidden_motive": re.compile(r"(他内心就是|他真正目的就是|他肯定是为了)"),
    "algorithm_certainty": re.compile(r"(算法一定|平台就是故意把他推爆)"),
    "income_certainty": re.compile(r"(他肯定赚了|他实际收入就是)"),
}


def precheck(text: str, *, subject_type: str, sensitivity: str) -> SafetyDecision:
    if CRISIS.search(text) or sensitivity == "crisis":
        return SafetyDecision(
            status="safety_hold", risk_level="critical", reasons=["crisis_signal"],
            actions=["停止普通辨识流程", "优先联系当地紧急服务、可信任的人或合格专业支持"],
            human_review_required=True,
        )
    if ABUSE.search(text) or sensitivity == "abuse":
        return SafetyDecision(
            status="safety_hold", risk_level="high", reasons=["abuse_or_trauma_signal"],
            actions=["优先确认现实安全", "不要求立即和解或恢复接触", "建议可信任的真人与专业支持"],
            human_review_required=True,
        )
    if SCRUPULOSITY.search(text):
        return SafetyDecision(
            status="safety_hold", risk_level="high", reasons=["scrupulosity_signal"],
            actions=["停止加深定罪", "优先赦免确据、休息和合格牧养或临床支持"],
            human_review_required=True,
        )
    blocked = [name for name, pattern in BLOCKED_CLAIMS.items() if pattern.search(text)]
    if blocked:
        return SafetyDecision(
            status="blocked", risk_level="high", reasons=blocked,
            actions=["删除越权或伤害性断言", "改写为可观察事实和可证伪假设"],
            human_review_required=True,
        )
    risky = [name for name, pattern in RISKY_ASSERTIONS.items() if pattern.search(text)]
    reputation = subject_type == "person" or sensitivity in {"reputation_sensitive", "legal_sensitive", "minor_involved"}
    if risky or reputation:
        return SafetyDecision(
            status="review_required", risk_level="medium", reasons=risky or ["public_person_or_reputation_sensitive"],
            actions=["仅使用公开证据", "隐藏动机、算法因果和未披露收入只可作为低置信度假设"],
            human_review_required=True,
        )
    return SafetyDecision()


def classify_resistance(text: str) -> dict:
    patterns = [
        ("boundary_setting", r"(不想回答|跳过|停止|到这里|不要再问|不讨论这个)"),
        ("scrupulosity", SCRUPULOSITY.pattern),
        ("trauma_activation", ABUSE.pattern),
        ("shame_flooding", r"(我一无是处|我太恶心|我不配活|全都是我的错)"),
        ("fatigue", r"(累了|不想继续|问太多了|以后再说)"),
        ("confusion", r"(没听懂|不明白|什么意思|能具体一点吗)"),
        ("disagreement", r"(我不同意|这个前提不成立|不是这样)"),
        ("hostility", r"(闭嘴|少来这一套|你没资格|滚)"),
    ]
    for kind, pattern in patterns:
        if re.search(pattern, text, re.I):
            return {"type": kind, "confidence": 0.8}
    return {"type": "none", "confidence": 0.4}
