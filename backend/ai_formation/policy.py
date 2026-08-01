"""Deterministic hard gates shared across all formation batches."""

from collections.abc import Iterable
from typing import Any

from .catalog import RELEASE_GATES

_S3 = {
    "我不想活", "想自杀", "我要自杀", "伤害自己", "杀了他", "正在虐待", "被性侵",
    "勒索裸照", "成人要我保密", "immediate danger", "kill myself", "suicide", "sexual abuse",
}
_S2 = {"持续抑郁", "恐慌发作", "进食障碍", "无法正常生活", "complex trauma", "panic attack", "eating disorder"}
_S1 = {"反复色情", "长期失眠", "严重家庭冲突", "明显孤立", "反复失控", "persistent insomnia", "isolated"}


def assess_pastoral_safety(text: str, *, age_band: str = "adult", locale: str = "zh-CN") -> dict[str, Any]:
    """Return reason codes only; the caller must never persist ``text``."""

    lowered = text.casefold()
    if any(term.casefold() in lowered for term in _S3):
        referrals = ["emergency_service", "child_protection"] if age_band != "adult" else ["emergency_service"]
        return {
            "level": "S3", "continueCourse": False,
            "userMessageKey": f"ai_formation.safety.s3.{locale}",
            "reasons": ["IMMEDIATE_SAFETY_OR_PROTECTION_SIGNAL"], "requiresHumanReview": True,
            "referralTypes": referrals, "storeSensitiveDetails": False,
        }
    if any(term.casefold() in lowered for term in _S2):
        referrals = ["licensed_counselor", "medical_professional"]
        if age_band != "adult":
            referrals.insert(0, "parent_or_guardian")
        return {
            "level": "S2", "continueCourse": False,
            "userMessageKey": f"ai_formation.safety.s2.{locale}",
            "reasons": ["QUALIFIED_SUPPORT_RECOMMENDED"], "requiresHumanReview": True,
            "referralTypes": referrals, "storeSensitiveDetails": False,
        }
    if any(term.casefold() in lowered for term in _S1):
        return {
            "level": "S1", "continueCourse": True,
            "userMessageKey": f"ai_formation.safety.s1.{locale}",
            "reasons": ["PASTORAL_CONCERN"], "requiresHumanReview": False,
            "referralTypes": ["pastor"], "storeSensitiveDetails": False,
        }
    return {
        "level": "S0", "continueCourse": True,
        "userMessageKey": f"ai_formation.safety.s0.{locale}",
        "reasons": ["GENERAL_EDUCATION"], "requiresHumanReview": False,
        "referralTypes": [], "storeSensitiveDetails": False,
    }


_PROHIBITED_AI_ROLES = {
    "final_moral_authority", "pastoral_diagnostician", "divine_messenger", "secret_minor_companion",
}


def assess_ai_authority(intent: dict[str, Any]) -> dict[str, Any]:
    role = intent.get("requested_role")
    stakes = intent.get("stakes")
    prohibited = role in _PROHIBITED_AI_ROLES or stakes == "emergency" or intent.get("delegation_level") == "decide"
    return {
        "decision": "prohibited_substitution" if prohibited else "assist_with_human_ownership",
        "aiMay": [] if prohibited else [role],
        "humanMustRetain": ["final_decision", "verification", "prayer_and_conscience", "relational_responsibility"],
        "requiresSafetyFlow": stakes == "emergency",
        "finalDecisionOwner": "human",
    }


_HUMAN_REVIEW_GATES = {
    "theology", "pastoral_safety", "child_safety", "privacy_security",
    "accessibility_manual", "content_quality",
}


def evaluate_release_evidence(evidence: Iterable[dict[str, Any]]) -> dict[str, Any]:
    latest = {item.get("gate"): item for item in evidence if item.get("gate") in RELEASE_GATES}
    blockers: list[str] = []
    for gate in RELEASE_GATES:
        item = latest.get(gate)
        if not item:
            blockers.append(f"{gate}:MISSING")
            continue
        if item.get("result") != "passed" or item.get("exit_code") not in (0, None):
            blockers.append(f"{gate}:{str(item.get('result', 'INVALID')).upper()}")
        if gate in _HUMAN_REVIEW_GATES and not item.get("human_reviewer"):
            blockers.append(f"{gate}:HUMAN_REVIEW_MISSING")
    return {
        "status": "READY_FOR_HUMAN_DECISION" if not blockers else "NOT_CERTIFIED",
        "automatedApproval": False,
        "humanReleaseDecisionRequired": True,
        "blockers": blockers,
        "evaluatedGates": sorted(latest),
    }
