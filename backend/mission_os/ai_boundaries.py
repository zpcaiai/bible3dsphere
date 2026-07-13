"""Skill 36: AI calling-discernment boundaries and model governance invariants.

AI may summarise, question, find missing evidence and draft. AI may never declare
a divine calling, approve readiness, clear a hard block, or act as a decision
maker. Sensitive P4 data never enters a model. High-risk outputs require human
review.
"""
from __future__ import annotations
import re

# Actions the AI is categorically forbidden from performing.
FORBIDDEN_AI_ACTIONS = frozenset({
    "declare_divine_calling", "judge_salvation", "rate_spiritual_maturity",
    "replace_church_confirmation", "approve_readiness", "clear_hard_block",
    "approve_deployment", "diagnose_mental_illness", "instruct_stop_medication",
    "judge_spouse_objection", "infer_individual_religion_or_politics",
})

# Policy findings for outputs that must be rewritten / escalated.
POLICY_FINDINGS = frozenset({
    "divine_call_declaration", "spiritual_shaming", "obedience_coercion",
    "family_override", "church_authority_absolutism", "mental_health_spiritualization",
    "savior_complex_reinforcement", "illegal_entry_suggestion",
    "certainty_without_evidence", "discriminatory_role_assumption",
})

# Conditions that force human review of an AI draft.
HUMAN_REVIEW_TRIGGERS = frozenset({
    "mentions_hard_block", "spouse_family_or_church_conflict", "mental_health",
    "safeguarding", "recommends_pause", "recommends_high_risk_field",
    "serious_feedback_conflict", "low_data_quality", "bias_or_coercion_rule_hit",
})

# Data classes that must never reach a general model.
PROHIBITED_MODEL_DATA = frozenset({"P4"})

# Cheap lexical guards for the most dangerous phrasings (defence-in-depth; the
# real system also uses a classifier). Patterns are language-agnostic anchors.
_DIVINE_CALL_PATTERNS = (
    re.compile(r"god has called you", re.I),
    re.compile(r"上帝(已经)?呼召你"),
    re.compile(r"神(已经)?呼召你"),
    re.compile(r"you must become a missionary", re.I),
)
_COERCION_PATTERNS = (
    re.compile(r"if you (do not|don't) go.*(disobedien|rebel)", re.I),
    re.compile(r"不去就是悖逆"),
)


def assert_ai_action_allowed(action: str) -> None:
    if action in FORBIDDEN_AI_ACTIONS:
        raise ValueError(f"AI is not permitted to: {action}")


def scan_output(text: str) -> list[str]:
    """Return policy findings for an AI output. Empty list == clean."""
    findings = []
    for p in _DIVINE_CALL_PATTERNS:
        if p.search(text):
            findings.append("divine_call_declaration")
            break
    for p in _COERCION_PATTERNS:
        if p.search(text):
            findings.append("obedience_coercion")
            break
    return findings


def requires_human_review(triggers) -> bool:
    return bool(set(triggers) & HUMAN_REVIEW_TRIGGERS)


def assert_model_input_allowed(data_classes) -> None:
    bad = set(data_classes) & PROHIBITED_MODEL_DATA
    if bad:
        raise ValueError(f"data classes may not enter a model: {sorted(bad)}")


def sanitize_decision_field(draft: dict) -> dict:
    """Force the AI draft's `decision` field to null — AI never decides."""
    out = dict(draft)
    out["decision"] = None
    out.setdefault("requires_human_review", True)
    out.setdefault("certainty_statement", "This is not a declaration of calling.")
    return out
