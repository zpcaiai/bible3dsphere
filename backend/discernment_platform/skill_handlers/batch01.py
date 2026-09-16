"""Batch 01 - native bindings to :mod:`discernment_platform.batch01_core`."""

from __future__ import annotations

from typing import Any

from ..batch01_core import (
    DiscernmentCase,
    DiscernmentOrchestrator,
)
from ..batch01_core import claims as claims_skill
from ..batch01_core import desire as desire_skill
from ..batch01_core import gospel as gospel_skill
from ..batch01_core import intake as intake_skill
from ..batch01_core import pride as pride_skill
from ..batch01_core import report as report_skill
from ..batch01_core import safety as safety_skill
from ..batch01_core import socratic as socratic_skill
from ..batch01_core import trace as trace_skill
from ..batch01_core import worldview as worldview_skill
from ..batch01_core.models import (
    Claim,
    DesireChain,
    GospelBridge,
    NormalizedCase,
    PrideHypothesis,
    SafetyDecision,
    SkillFailure,
    SocraticQuestion,
    TraceRecord,
    WorldviewMap,
)
from ..skill_runtime import SkillInvocationError, handler
from ._support import Payload, dumped, require


def _case(payload: Payload) -> DiscernmentCase:
    raw = payload.get("case") or payload
    if isinstance(raw, DiscernmentCase):
        return raw
    return DiscernmentCase(**raw)


def _normalized(payload: Payload) -> NormalizedCase:
    value = payload.get("normalized_case")
    if isinstance(value, NormalizedCase):
        return value
    if isinstance(value, dict):
        return NormalizedCase(**value)
    return intake_skill.normalize(_case(payload))


def _claims(payload: Payload, normalized: NormalizedCase) -> list[Claim]:
    value = payload.get("claims")
    if value:
        return [c if isinstance(c, Claim) else Claim(**c) for c in value]
    return claims_skill.extract(normalized)


def _worldview(payload: Payload, normalized, claims) -> WorldviewMap:
    value = payload.get("worldview_map")
    if isinstance(value, WorldviewMap):
        return value
    if isinstance(value, dict) and value.get("case_id"):
        return WorldviewMap(**value)
    return worldview_skill.map_worldview(normalized, claims)


def _hypotheses(payload: Payload, normalized, claims, wv) -> list[PrideHypothesis]:
    value = payload.get("pride_hypotheses")
    if value:
        return [h if isinstance(h, PrideHypothesis) else PrideHypothesis(**h) for h in value]
    return pride_skill.detect(normalized, claims, wv, payload.get("user_reaction", ""))


def _desires(payload: Payload, normalized, wv, hypotheses) -> list[DesireChain]:
    value = payload.get("desire_map")
    if value:
        return [d if isinstance(d, DesireChain) else DesireChain(**d) for d in value]
    return desire_skill.map_desires(normalized, wv, hypotheses, payload.get("user_reaction", ""))


def _wrap(exc: SkillFailure) -> SkillInvocationError:
    return SkillInvocationError(exc.code.value, exc.message)


@handler("case-intake-normalizer")
def case_intake_normalizer(contract, payload: Payload, context: Payload) -> Payload:
    require(payload, "case") if "case" in payload else require(payload, "raw_input")
    try:
        normalized = intake_skill.normalize(_case(payload))
    except SkillFailure as exc:
        raise _wrap(exc) from exc
    return {"normalized_case": dumped(normalized)}


@handler("claim-evidence-extractor")
def claim_evidence_extractor(contract, payload: Payload, context: Payload) -> Payload:
    normalized = _normalized(payload)
    found = claims_skill.extract(normalized)
    return {
        "claims": dumped(found),
        "high_confidence_claim_ids": [c.claim_id for c in claims_skill.high_confidence(found)],
    }


@handler("worldview-frame-mapper")
def worldview_frame_mapper(contract, payload: Payload, context: Payload) -> Payload:
    normalized = _normalized(payload)
    found = _claims(payload, normalized)
    return {"worldview_map": dumped(worldview_skill.map_worldview(normalized, found))}


@handler("pride-signal-detector")
def pride_signal_detector(contract, payload: Payload, context: Payload) -> Payload:
    normalized = _normalized(payload)
    found = _claims(payload, normalized)
    wv = _worldview(payload, normalized, found)
    hypotheses = pride_skill.detect(normalized, found, wv, payload.get("user_reaction", ""))
    return {
        "pride_hypotheses": dumped(hypotheses),
        "conclusive_hypothesis_ids": [h.hypothesis_id for h in pride_skill.conclusive(hypotheses)],
        "self_examination_prompts": pride_skill.redirect_to_self_examination(hypotheses),
    }


@handler("desire-idolatry-mapper")
def desire_idolatry_mapper(contract, payload: Payload, context: Payload) -> Payload:
    normalized = _normalized(payload)
    found = _claims(payload, normalized)
    wv = _worldview(payload, normalized, found)
    hypotheses = _hypotheses(payload, normalized, found, wv)
    chains = desire_skill.map_desires(normalized, wv, hypotheses, payload.get("user_reaction", ""))
    return {
        "desire_map": dumped(chains),
        "more_self_report_needed": desire_skill.more_self_report_needed(chains),
    }


@handler("socratic-question-planner")
def socratic_question_planner(contract, payload: Payload, context: Payload) -> Payload:
    normalized = _normalized(payload)
    found = _claims(payload, normalized)
    wv = _worldview(payload, normalized, found)
    hypotheses = _hypotheses(payload, normalized, found, wv)
    chains = _desires(payload, normalized, wv, hypotheses)
    questions = socratic_skill.plan(
        normalized, found, wv, hypotheses, chains, bool(payload.get("defensiveness"))
    )
    return {
        "socratic_questions": dumped(questions),
        "next_question": dumped(socratic_skill.next_question(questions)),
    }


@handler("gospel-bridge-builder")
def gospel_bridge_builder(contract, payload: Payload, context: Payload) -> Payload:
    normalized = _normalized(payload)
    found = _claims(payload, normalized)
    wv = _worldview(payload, normalized, found)
    hypotheses = _hypotheses(payload, normalized, found, wv)
    chains = _desires(payload, normalized, wv, hypotheses)
    try:
        bridge = gospel_skill.build(normalized, wv, hypotheses, chains)
    except SkillFailure as exc:
        raise _wrap(exc) from exc
    return {"gospel_bridge": dumped(bridge)}


@handler("discernment-report-composer")
def discernment_report_composer(contract, payload: Payload, context: Payload) -> Payload:
    normalized = _normalized(payload)
    found = _claims(payload, normalized)
    wv = _worldview(payload, normalized, found)
    hypotheses = _hypotheses(payload, normalized, found, wv)
    chains = _desires(payload, normalized, wv, hypotheses)
    questions = socratic_skill.plan(normalized, found, wv, hypotheses, chains)
    bridge_raw = payload.get("gospel_bridge")
    bridge = None
    if isinstance(bridge_raw, GospelBridge):
        bridge = bridge_raw
    elif isinstance(bridge_raw, dict) and bridge_raw:
        bridge = GospelBridge(**bridge_raw)
    else:
        try:
            bridge = gospel_skill.build(normalized, wv, hypotheses, chains)
        except SkillFailure:
            bridge = None
    safety_raw = payload.get("safety") or {}
    decision = (
        safety_raw
        if isinstance(safety_raw, SafetyDecision)
        else SafetyDecision(**safety_raw)
        if safety_raw
        else safety_skill.precheck(_case(payload))
    )
    try:
        composed = report_skill.compose(
            normalized, found, wv, hypotheses, chains, questions, bridge, decision
        )
    except SkillFailure as exc:
        raise _wrap(exc) from exc
    return {"report": dumped(composed)}


@handler("pastoral-safety-guardian")
def pastoral_safety_guardian(contract, payload: Payload, context: Payload) -> Payload:
    case = _case(payload)
    pre = safety_skill.precheck(case)
    result: Payload = {"precheck": dumped(pre)}
    rendered = payload.get("rendered_output")
    if rendered:
        result["postcheck"] = dumped(safety_skill.postcheck(case, str(rendered)))
    result["risk_level"] = pre.risk_level.value
    result["blocked_patterns"] = pre.blocked_patterns
    result["human_review_required"] = pre.human_review_required
    result["halt_normal_flow"] = pre.halt_normal_flow
    return result


@handler("trace-review-packager")
def trace_review_packager(contract, payload: Payload, context: Payload) -> Payload:
    case_id = payload.get("case_id") or (payload.get("case") or {}).get("case_id", "unknown")
    raw_records = payload.get("trace_records") or []
    records = [
        r if isinstance(r, TraceRecord) else TraceRecord(**r) for r in raw_records
    ]
    bundle = trace_skill.package(case_id, records)
    report = payload.get("report") or {}
    return {
        "trace_bundle": dumped(bundle),
        "review_packet": trace_skill.review_packet(bundle, report),
        "redacted_user_view": trace_skill.redacted_user_view(report),
        "production_ready": bundle.production_ready,
    }


