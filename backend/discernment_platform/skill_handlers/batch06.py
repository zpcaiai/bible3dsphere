"""Batch 06 - 律法—福音—联合基督路径：bindings to doctrine packs and gospel engine."""

from __future__ import annotations

from ..skill_runtime import SkillInvocationError, handler
from ._engines import case_create, gospel_engine, pack, registry
from ._support import Payload, require

_DOCTRINE_FOR_SKILL = {
    "created-good-affirmation-builder": "creation_order",
    "sin-idolatry-personalizer": "sin_and_idolatry",
    "law-functions-selector": "uses_of_law",
    "christ-person-work-presenter": "christ_and_atonement",
    "atonement-need-mapper": "christ_and_atonement",
    "justification-by-faith-clarifier": "justification_by_faith",
    "adoption-security-builder": "adoption",
    "union-with-christ-integrator": "union_with_christ",
    "spirit-sanctification-planner": "sanctification_by_spirit",
    "church-community-path-builder": "church_community",
    "eschatological-hope-reframer": "eschatological_hope",
}


def _doctrine_handler(pack_id: str):
    def run(contract, payload: Payload, context: Payload) -> Payload:
        data = pack("doctrine", pack_id)
        return {
            "doctrine_pack": {
                "id": data["id"],
                "name": data.get("name_zh"),
                "version": data["version"],
                "tier": data["tier"],
            },
            "core_claims": data["core_claims"],
            "pastoral_applications": data["pastoral_applications"],
        }

    return run


for _skill_id, _pack_id in _DOCTRINE_FOR_SKILL.items():
    handler(_skill_id)(_doctrine_handler(_pack_id))


@handler("gospel-path-context-builder")
def gospel_path_context_builder(contract, payload: Payload, context: Payload) -> Payload:
    case = case_create(payload)
    return {
        "gospel_path_context": {
            "faith_context": case.faith_context,
            "sensitivity": case.sensitivity,
            "consent": case.consent_scope.model_dump(mode="json"),
            "user_goal": case.user_goal,
        }
    }


@handler("faith-context-and-depth-router")
def faith_context_router(contract, payload: Payload, context: Payload) -> Payload:
    faith = payload.get("faith_context", "unknown")
    depth = payload.get("preferred_depth", "standard")
    consented = bool((payload.get("consent_scope") or {}).get("allow_gospel_bridge", False))
    return {
        "faith_context": faith,
        "depth": depth,
        "requires_consent_before_gospel": faith != "christian" and not consented,
        "route": "law_first" if faith == "christian" else "creation_first",
    }


@handler("law-gospel-balance-controller")
def law_gospel_balance(contract, payload: Payload, context: Payload) -> Payload:
    sensitivity = payload.get("sensitivity", "normal")
    reduce_law = sensitivity in {"mental_health", "abuse", "crisis"}
    return {
        "law_pressure": "reduced" if reduce_law else "standard",
        "gospel_priority": "assurance_first" if reduce_law else "law_then_gospel",
        "uses_of_law": pack("doctrine", "uses_of_law")["core_claims"],
    }


@handler("justification-sanctification-boundary-guardian")
def justification_sanctification_boundary(contract, payload: Payload, context: Payload) -> Payload:
    justification = pack("doctrine", "justification_by_faith")
    sanctification = pack("doctrine", "sanctification_by_spirit")
    text = str(payload.get("text", ""))
    conflated = bool(text) and "越圣洁越被神接纳" in text
    return {
        "justification_claims": justification["core_claims"],
        "sanctification_claims": sanctification["core_claims"],
        "boundary_violation": conflated,
        "correction_required": conflated,
    }


@handler("denominational-difference-governor")
def denominational_governor(contract, payload: Payload, context: Payload) -> Payload:
    reg = registry()
    return {
        "doctrine_tiers": {
            p["id"]: p["tier"] for p in reg.ordered_doctrine_packs()
        },
        "policy": "tier1 states consensus; tier2/tier3 must present positions without adjudicating",
    }


@handler("gospel-path-report-and-eval-composer")
def gospel_path_report(contract, payload: Payload, context: Payload) -> Payload:
    case = case_create(payload)
    if not case.consent_scope.allow_gospel_bridge:
        raise SkillInvocationError("USER_CONSENT_REQUIRED", "gospel bridge consent not granted")
    report = payload.get("report", {}) or {}
    built = gospel_engine().build(
        case_id=payload.get("case_id", "gospel-path-case"),
        presenting_issue=payload.get("presenting_issue") or case.user_goal,
        faith_context=case.faith_context,
        consent_scope=case.consent_scope.model_dump(mode="json"),
        pride_hypotheses=payload.get("pride_hypotheses") or report.get("pride_hypotheses", []),
        desire_map=payload.get("desire_map") or report.get("desire_map", []),
        sensitivity=case.sensitivity,
        preferred_depth=payload.get("preferred_depth", "standard"),
        church_context=payload.get("church_context", ""),
    )
    return {"gospel_path": built}


@handler("gospel-safety-and-consent-guardian")
def gospel_safety_consent(contract, payload: Payload, context: Payload) -> Payload:
    from ..safety import precheck

    raw = payload.get("raw_input") or (payload.get("case") or {}).get("raw_input", "")
    decision = precheck(
        raw or "",
        subject_type=payload.get("subject_type", "self_reflection"),
        sensitivity=payload.get("sensitivity", "normal"),
    ).as_dict()
    consent = (payload.get("consent_scope") or {}).get("allow_gospel_bridge", False)
    decision["gospel_consent_granted"] = bool(consent)
    decision["may_present_gospel"] = bool(consent) and not decision.get("blocked", False)
    return decision


@handler("suffering-structure-responsibility-balancer")
def suffering_balance(contract, payload: Payload, context: Payload) -> Payload:
    text = str(payload.get("raw_input") or (payload.get("case") or {}).get("raw_input", ""))
    structural_markers = ("裁员", "贫困", "歧视", "霸凌", "压迫", "体制", "创伤", "家暴")
    found = [m for m in structural_markers if m in text]
    return {
        "structural_factors": found,
        "personal_responsibility_scope": "限于本人可选择的部分",
        "balance_rule": "不把结构问题个人化，也不把个人责任结构化",
        "structural_preserved": True,
    }


@handler("gospel-response-and-practice-designer")
def gospel_practice(contract, payload: Payload, context: Payload) -> Payload:
    doctrine = pack("doctrine", "sanctification_by_spirit")
    return {
        "practices": doctrine["pastoral_applications"],
        "non_performative": True,
        "single_next_step_only": True,
    }
