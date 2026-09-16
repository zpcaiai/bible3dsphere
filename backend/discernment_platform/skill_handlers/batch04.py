"""Batch 04 - 自高自义深层模型：bindings to hypothesis packs and the engine."""

from __future__ import annotations

from ..skill_runtime import SkillInvocationError, handler
from ._engines import case_create, discernment_engine, pack, registry
from ._support import Payload, require


def _pack_id(payload: Payload) -> str:
    (pack_id,) = require(payload, "hypothesis_pack_id")
    return pack_id


@handler("observation-normalizer")
def observation_normalizer(contract, payload: Payload, context: Payload) -> Payload:
    case = case_create(payload)
    return {
        "normalized_observation": case.model_dump(mode="json"),
        "observation_only": True,
        "interpretation_deferred": True,
    }


@handler("self-other-scope-router")
def self_other_scope_router(contract, payload: Payload, context: Payload) -> Payload:
    subject = (payload.get("case") or payload).get("subject_type", "idea")
    scope = "self" if subject == "self_reflection" else "other"
    return {
        "scope": scope,
        "public_material_only": scope == "other",
        "start_with_self_examination": True,
    }


@handler("pride-signal-extractor")
def pride_signal_extractor(contract, payload: Payload, context: Payload) -> Payload:
    case = case_create(payload)
    engine = discernment_engine()
    matches = engine._domain_matches(case.raw_input)
    hypotheses = engine._pride_hypotheses(case, matches)
    return {"pride_hypotheses": hypotheses, "domain_matches": matches}


@handler("hypothesis-builder")
def hypothesis_builder(contract, payload: Payload, context: Payload) -> Payload:
    data = pack("hypothesis", _pack_id(payload))
    return {
        "hypothesis": {
            "id": data["id"],
            "name": data.get("name_zh"),
            "version": data["version"],
            "created_good": data["created_good"],
            "signals": data["signals"],
        },
        "evidence_level_required": "E3",
    }


@handler("alternative-explanation-generator")
def alternative_explanation_generator(contract, payload: Payload, context: Payload) -> Payload:
    data = pack("hypothesis", _pack_id(payload))
    alternatives = data["alternative_explanations"]
    if not alternatives:
        raise SkillInvocationError(
            "INSUFFICIENT_EVIDENCE", "pack declares no alternative explanations"
        )
    return {"alternative_explanations": alternatives}


@handler("counter-evidence-planner")
def counter_evidence_planner(contract, payload: Payload, context: Payload) -> Payload:
    data = pack("hypothesis", _pack_id(payload))
    return {"counter_evidence": data["counter_evidence"], "disconfirmation_required": True}


@handler("created-good-protector")
def created_good_protector(contract, payload: Payload, context: Payload) -> Payload:
    data = pack("hypothesis", _pack_id(payload))
    return {"created_good": data["created_good"], "must_affirm_before_critique": True}


@handler("gospel-identity-reanchoring")
def gospel_identity_reanchoring(contract, payload: Payload, context: Payload) -> Payload:
    data = pack("hypothesis", _pack_id(payload))
    return {"gospel_bridge": data["gospel_bridge"]}


@handler("hypothesis-red-team-evaluator")
def hypothesis_red_team_evaluator(contract, payload: Payload, context: Payload) -> Payload:
    reg = registry()
    pack_id = _pack_id(payload)
    data = reg.hypothesis_packs[pack_id]
    tests = reg.related_asset(data, "tests.json", {})
    if not tests:
        raise SkillInvocationError("INSUFFICIENT_EVIDENCE", f"no red-team tests for {pack_id}")
    return {"red_team_tests": tests, "pack_id": pack_id}
