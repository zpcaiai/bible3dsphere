"""Batch 05 - 苏格拉底式对话引擎：bindings to the dialogue engine."""

from __future__ import annotations

from ..skill_runtime import SkillInvocationError, handler
from ._engines import dialogue_engine, registry
from ._support import Payload, require


@handler("dialogue-session-initializer")
def dialogue_session_initializer(contract, payload: Payload, context: Payload) -> Payload:
    session_id, case_id = require(payload, "session_id", "case_id")
    session = dialogue_engine().initialize(
        session_id=session_id,
        case_id=case_id,
        report=payload.get("report", {}),
        faith_context=payload.get("faith_context", "unknown"),
    )
    return {"session": session}


@handler("one-question-at-a-time-enforcer")
def one_question_enforcer(contract, payload: Payload, context: Payload) -> Payload:
    from ..dialogue import _one_question

    (text,) = require(payload, "text")
    single = _one_question(str(text))
    return {
        "question": single,
        "enforced": single != str(text),
        "max_questions_per_turn": 1,
    }


@handler("resistance-and-defensiveness-detector")
def resistance_detector(contract, payload: Payload, context: Payload) -> Payload:
    from ..safety import classify_resistance

    (answer,) = require(payload, "answer")
    return classify_resistance(str(answer))


@handler("socratic-question-tree-engine")
def question_tree_engine(contract, payload: Payload, context: Payload) -> Payload:
    stage = payload.get("stage")
    packs = registry().question_packs
    if stage:
        if stage not in packs:
            raise SkillInvocationError("INSUFFICIENT_EVIDENCE", f"unknown stage: {stage}")
        return {"question_pack": packs[stage], "stage": stage}
    return {"available_stages": sorted(packs), "question_packs": packs}


@handler("gospel-consent-gate")
def gospel_consent_gate(contract, payload: Payload, context: Payload) -> Payload:
    consent = payload.get("gospel_consent", "not_asked")
    faith = payload.get("faith_context", "unknown")
    allowed = consent == "accepted" or faith == "christian"
    return {
        "gospel_consent": consent,
        "may_enter_gospel_layer": allowed,
        "required_action": "ask_consent" if not allowed else "proceed",
    }


@handler("dialogue-trace-and-review-packager")
def dialogue_trace_packager(contract, payload: Payload, context: Payload) -> Payload:
    session = payload.get("session") or {}
    turns = session.get("turns") or payload.get("turns") or []
    return {
        "trace": {
            "session_id": session.get("session_id") or payload.get("session_id"),
            "case_id": session.get("case_id") or payload.get("case_id"),
            "turn_count": len(turns),
            "turns": turns,
        },
        "review_required": bool(session.get("human_review_required")),
    }


@handler("pause-repair-and-exit-manager")
def pause_repair_exit(contract, payload: Payload, context: Payload) -> Payload:
    from ..safety import classify_resistance

    answer = str(payload.get("answer", ""))
    resistance = classify_resistance(answer) if answer else {"type": "none", "confidence": 0.0}
    escalated = resistance.get("type", "none") != "none"
    return {
        "action": "pause_and_empathise" if escalated else "continue",
        "resistance": resistance,
        "exit_available": True,
    }
