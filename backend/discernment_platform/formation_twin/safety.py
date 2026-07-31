from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SafetyDecision:
    status: str
    reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


class FormationSafetyGuardian:
    BLOCK = {
        "salvation_score": re.compile(r"(得救概率|救恩分数|属灵成熟度.*分)"),
        "public_private_twin": re.compile(r"(给这个网红建立私人生命孪生|推测他的私生活模式)"),
        "forced_reconciliation": re.compile(r"(必须马上和施虐者和好|必须恢复接触才算饶恕)"),
    }

    HOLD = {
        "scrupulosity": re.compile(r"(反复认罪|认罪几个小时|每天检查是否得救|神不会赦免)"),
        "abuse": re.compile(r"(家暴|性侵|虐待|被控制)"),
        "crisis": re.compile(r"(想死|不想活|伤害自己|杀了他)"),
    }

    def review(self, text: str) -> SafetyDecision:
        blocked = [k for k,p in self.BLOCK.items() if p.search(text)]
        if blocked:
            return SafetyDecision("blocked", blocked, ["rewrite_or_human_review"])

        holds = [k for k,p in self.HOLD.items() if p.search(text)]
        if holds:
            return SafetyDecision("safety_hold", holds, ["stop_normal_tracking", "prioritize_safety"])

        return SafetyDecision("ready")
