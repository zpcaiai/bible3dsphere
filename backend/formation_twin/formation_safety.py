"""Fail-closed formation and theological safety rules.

These checks apply to system-created descriptions and model candidates.  A
user's own statement is stored as their statement and is never rewritten into
a spiritual verdict.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .formation_ontology import DEEP_FORMATION_TYPES


_BLOCKS: tuple[tuple[str, str], ...] = (
    ("salvation_verdict", r"你(已经|尚未|没有|一定|肯定)(得救|重生)|你的救恩(无效|有效|是真的|是假的)"),
    ("repentance_verdict", r"你(已经|根本没有|从未真正)(悔改|认罪)|你的悔改(不真实|是假的|无效)"),
    ("divine_oracle", r"神(告诉我|向系统启示|明确说|一定要你|命定你)|这是神(唯一|明确|最终)的旨意"),
    ("hidden_motive", r"你(真正|其实|内心深处)的(动机|目的|想法)(是|就是)|你自己没有意识到"),
    ("automatic_idol_sin", r"你(的)?(偶像|罪|罪性)(就是|一定是|显然是)|这证明你(拜偶像|犯罪)"),
    ("diagnosis", r"你(患有|就是|被诊断为).{0,8}(抑郁症|焦虑症|人格障碍|创伤后应激|双相|强迫症)|临床诊断"),
    ("personality_verdict", r"你(天生|本质上|就是一个).{0,8}(自恋|控制狂|讨好型人格|回避型人格)"),
    ("spiritual_rank", r"(属灵|成熟|圣洁|罪性|偶像|救恩)(分数|评分|等级|排名|指数)|比.+更(属灵|成熟|圣洁)"),
    ("absolute_causality", r"这(证明|必然说明|一定说明)|必定(导致|源于)|唯一原因|根本原因就是"),
)
_BLOCK_RE = [(code, re.compile(pattern, re.IGNORECASE)) for code, pattern in _BLOCKS]


@dataclass
class FormationSafetyResult:
    verdict: str = "PASS"
    flags: list[dict[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict == "PASS"


def review_generated_text(text: str) -> FormationSafetyResult:
    flags = [
        {"code": code, "severity": "BLOCK"}
        for code, pattern in _BLOCK_RE
        if pattern.search(text or "")
    ]
    try:
        from theological_safety import TheologicalSafetyService
        result = TheologicalSafetyService().review(
            text or "", agent_name="formation_twin_spiritual", skill_name="formation-chain",
            log=False,
        )
        flags.extend({"code": item["code"], "severity": "BLOCK" if item["severity"] == "block" else "FLAG"} for item in result.flags)
    except Exception:
        pass
    return FormationSafetyResult(verdict="BLOCK" if any(item["severity"] == "BLOCK" for item in flags) else "PASS", flags=flags)


def validate_model_candidate(candidate: dict[str, Any], *, now: datetime | None = None) -> list[str]:
    """Return validation errors; an empty list means the candidate is reviewable."""
    errors: list[str] = []
    node_type = str(candidate.get("node_type") or "")
    statement_type = str(candidate.get("statement_type") or "")
    evidence = candidate.get("evidence") or []
    alternatives = candidate.get("alternatives") or []
    if statement_type not in {"MODEL_EXTRACTED_EXPLICIT_EXPRESSION", "MODEL_FORMATION_HYPOTHESIS"}:
        errors.append("invalid_model_statement_type")
    if not evidence:
        errors.append("evidence_required")
    if candidate.get("confidence") is None:
        errors.append("confidence_required")
    if not candidate.get("scope"):
        errors.append("scope_required")
    if candidate.get("user_review_status") != "PENDING":
        errors.append("user_confirmation_required")
    if node_type in DEEP_FORMATION_TYPES and statement_type == "MODEL_FORMATION_HYPOTHESIS":
        if not alternatives:
            errors.append("alternative_explanations_required")
        if not candidate.get("expires_at"):
            errors.append("expiry_required")
    expires_at = candidate.get("expires_at")
    if expires_at:
        try:
            parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if parsed <= (now or datetime.now(timezone.utc)):
                errors.append("candidate_expired")
        except ValueError:
            errors.append("invalid_expiry")
    safety = review_generated_text(str(candidate.get("content") or ""))
    if not safety.ok:
        errors.extend(item["code"] for item in safety.flags)
    return list(dict.fromkeys(errors))


def crisis_blocks_formation(safety: dict[str, Any] | None, status: str | None) -> bool:
    level = str((safety or {}).get("safety_level") or "NONE").upper()
    return status == "ROUTED_TO_CRISIS" or level in {"CONCERN", "ELEVATED", "IMMINENT"}
