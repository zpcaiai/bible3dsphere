from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SafetyDecision:
    status: str
    reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


class PastoralSafetyGuardian:
    BLOCK = {
        "surveillance": re.compile(r"(偷偷监控|不让他知道就共享|查看全部聊天记录)"),
        "ai_discipline": re.compile(r"(让AI直接决定开除|根据AI分数执行纪律)"),
        "forced_reconciliation": re.compile(r"(必须马上和施虐者和好|不恢复接触就不算饶恕)"),
        "internal_only_abuse": re.compile(r"(性侵只在教会内部处理|不要报警只祷告)"),
    }

    ESCALATE = {
        "minor_abuse": re.compile(r"(未成年人.*虐待|儿童.*性侵|猥亵儿童)"),
        "crisis": re.compile(r"(想死|伤害自己|杀了他|迫近危险)"),
        "leader_abuse": re.compile(r"(牧师.*性侵|领袖.*虐待|属灵控制)"),
    }

    def review(self, text: str) -> SafetyDecision:
        blocked = [k for k,p in self.BLOCK.items() if p.search(text)]
        if blocked:
            return SafetyDecision("blocked", blocked, ["stop_and_human_review"])

        escalations = [k for k,p in self.ESCALATE.items() if p.search(text)]
        if escalations:
            return SafetyDecision(
                "safeguarding_review",
                escalations,
                ["restrict_access", "qualified_human_review", "external_duty_check"],
            )

        return SafetyDecision("ready")
