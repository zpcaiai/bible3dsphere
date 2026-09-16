"""Batch 08 - 牧者协作与人工复核：bindings to pastoral_collaboration."""

from __future__ import annotations

from ..skill_runtime import SkillInvocationError, handler
from ._support import Payload, dumped, require


def _actor(payload: Payload):
    from ..pastoral_collaboration.models import Actor

    raw = payload.get("actor")
    if raw is None:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "actor is required")
    return raw if isinstance(raw, Actor) else Actor(**raw)


def _case(payload: Payload):
    from ..pastoral_collaboration.models import PastoralCase

    raw = payload.get("pastoral_case") or payload.get("case")
    if raw is None:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "pastoral_case is required")
    return raw if isinstance(raw, PastoralCase) else PastoralCase(**raw)


def _grants(payload: Payload) -> list:
    from ..pastoral_collaboration.models import ConsentGrant

    return [
        g if isinstance(g, ConsentGrant) else ConsentGrant(**g)
        for g in payload.get("consent_grants", []) or []
    ]


@handler("pastoral-case-intake")
def pastoral_case_intake(contract, payload: Payload, context: Payload) -> Payload:
    case = _case(payload)
    return {"pastoral_case": dumped(case), "intake_complete": True}


@handler("actor-role-credential-resolver")
def actor_role_resolver(contract, payload: Payload, context: Payload) -> Payload:
    from ._engines import registry

    actor = _actor(payload)
    packs = registry().role_packs
    role_ids = [getattr(r, "value", r) for r in (actor.roles or [])]
    if not role_ids:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "actor declares no roles")
    unknown = [r for r in role_ids if str(r) not in packs]
    if unknown:
        raise SkillInvocationError("INSUFFICIENT_EVIDENCE", f"unknown role(s): {unknown}")
    resolved = [
        {k: v for k, v in packs[str(r)].items() if k != "_asset_dir"} for r in role_ids
    ]
    return {
        "actor": dumped(actor),
        "role_packs": resolved,
        "permissions": sorted({p for pack in resolved for p in pack["permissions"]}),
        "prohibitions": sorted({p for pack in resolved for p in pack["prohibitions"]}),
    }


@handler("consent-grant-manager")
def consent_grant_manager(contract, payload: Payload, context: Payload) -> Payload:
    grants = _grants(payload)
    return {
        "consent_grants": dumped(grants),
        "grant_count": len(grants),
        "withdrawable": True,
    }


@handler("rbac-abac-policy-evaluator")
def rbac_abac_policy_evaluator(contract, payload: Payload, context: Payload) -> Payload:
    from ..pastoral_collaboration import AccessPolicyEvaluator

    from ..pastoral_collaboration.models import DataLevel

    actor = _actor(payload)
    case = _case(payload)
    grants = _grants(payload)
    (purpose,) = require(payload, "purpose")
    try:
        requested_level = DataLevel(payload.get("requested_level", "L1"))
    except ValueError as exc:
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", str(exc)) from exc
    decision = AccessPolicyEvaluator().evaluate(
        actor=actor,
        case=case,
        consent=grants[0] if grants else None,
        purpose=str(purpose),
        requested_level=requested_level,
        conflict_present=bool(payload.get("conflict_present", False)),
        safety_basis=bool(payload.get("safety_basis", False)),
    )
    return {"access_decision": dumped(decision), "requested_level": requested_level.value}


@handler("minimum-necessary-disclosure-builder")
def minimum_necessary_disclosure(contract, payload: Payload, context: Payload) -> Payload:
    from ..pastoral_collaboration import build_disclosure

    case = _case(payload)
    recipient, purpose, expires_at = require(
        payload, "recipient_actor_id", "purpose", "expires_at"
    )
    disclosure = build_disclosure(
        disclosure_id=payload.get("disclosure_id", f"disc-{case.case_id}"),
        case_id=case.case_id,
        recipient_actor_id=str(recipient),
        purpose=str(purpose),
        requested_fields=list(payload.get("requested_fields", [])),
        allowed_fields=set(payload.get("allowed_fields", [])),
        prohibited_fields=set(payload.get("prohibited_fields", [])),
        expires_at=str(expires_at),
        basis=payload.get("basis", "consent"),
        audit_id=payload.get("audit_id", f"audit-{case.case_id}"),
    )
    return {"disclosure": dumped(disclosure), "minimum_necessary": True}


@handler("meeting-preparation-generator")
def meeting_preparation_generator(contract, payload: Payload, context: Payload) -> Payload:
    from ..pastoral_collaboration import build_meeting_prep

    case = _case(payload)
    prep = build_meeting_prep(
        case_id=case.case_id,
        meeting_purpose=payload.get("meeting_purpose") or case.purpose,
        user_selected_focus=list(payload.get("user_selected_focus", [])),
        last_agreements=list(payload.get("last_agreements", [])),
        evidence_summary=list(payload.get("evidence_summary", [])),
        uncertainties=list(payload.get("uncertainties", [])),
        priority_question=payload.get("priority_question", ""),
        gospel_truth=payload.get("gospel_truth", ""),
        action_option=payload.get("action_option", ""),
        do_not_use_language=list(payload.get("do_not_use_language", [])),
    )
    return {"meeting_preparation": dumped(prep)}


@handler("escalation-state-machine")
def escalation_state_machine(contract, payload: Payload, context: Payload) -> Payload:
    from ..pastoral_collaboration import EscalationStateMachine
    from ..pastoral_collaboration.models import EscalationState

    current, target = require(payload, "current", "target")
    try:
        current_state, target_state = EscalationState(current), EscalationState(target)
    except ValueError as exc:
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", str(exc)) from exc
    machine = EscalationStateMachine()
    allowed = machine.can_transition(current_state, target_state)
    return {
        "current": current,
        "target": target,
        "transition_allowed": allowed,
        "resulting_state": target if allowed else current,
    }


@handler("conflict-of-interest-detector")
def conflict_of_interest_detector(contract, payload: Payload, context: Payload) -> Payload:
    from ..pastoral_collaboration import detect_conflict

    actor = _actor(payload)
    relationships = payload.get("case_relationships", []) or []
    return {"conflict": dumped(detect_conflict(actor, list(relationships)))}


@handler("sensitive-case-triage")
def sensitive_case_triage(contract, payload: Payload, context: Payload) -> Payload:
    from ..pastoral_collaboration import PastoralSafetyGuardian

    text = str(payload.get("text") or payload.get("raw_input") or "")
    return {"triage": dumped(PastoralSafetyGuardian().review(text))}


@handler("safeguarding-and-external-duty-guardian")
def safeguarding_guardian(contract, payload: Payload, context: Payload) -> Payload:
    from ..pastoral_collaboration import PastoralSafetyGuardian

    text = str(payload.get("text") or payload.get("raw_input") or "")
    decision = dumped(PastoralSafetyGuardian().review(text))
    decision["external_duty_may_apply"] = bool(
        decision.get("blocked") or decision.get("human_review_required")
    )
    return {"safeguarding": decision}
