"""Batch 07 - Formation Twin：bindings to the formation_twin package."""

from __future__ import annotations

from ..skill_runtime import SkillInvocationError, handler
from ._support import Payload, dumped, require


def _event(payload: Payload):
    from ..formation_twin.models import FormationEvent

    raw = payload.get("event") or payload.get("formation_event")
    if raw is None:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "event is required")
    if isinstance(raw, FormationEvent):
        return raw
    return FormationEvent(**raw)


def _events(payload: Payload) -> list:
    from ..formation_twin.models import FormationEvent

    raw = payload.get("events") or []
    if not raw:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "events are required")
    return [e if isinstance(e, FormationEvent) else FormationEvent(**e) for e in raw]


@handler("formation-event-ingestor")
def formation_event_ingestor(contract, payload: Payload, context: Payload) -> Payload:
    from ..formation_twin import FormationTwinOrchestrator

    return {"ingested": dumped(FormationTwinOrchestrator().ingest(_event(payload)))}


@handler("event-consent-and-privacy-router")
def event_consent_router(contract, payload: Payload, context: Payload) -> Payload:
    event = _event(payload)
    consented = bool(getattr(event, "consent_to_tracking", False))
    level = getattr(event, "data_level", "L1")
    return {
        "consent_to_tracking": consented,
        "data_level": dumped(level),
        "may_persist": consented,
        "may_share_with_mentor": consented and dumped(level) in {"L0", "L1"},
        "minimum_necessary": True,
    }


@handler("formation-chain-builder")
def formation_chain_builder(contract, payload: Payload, context: Payload) -> Payload:
    from ..formation_twin import build_chain

    return {"formation_chain": dumped(build_chain(_event(payload)))}


def _window_handler(days: int):
    def run(contract, payload: Payload, context: Payload) -> Payload:
        from ..formation_twin import review_window

        (user_id,) = require(payload, "user_id")
        review = review_window(user_id, _events(payload), days)
        return {"window_review": dumped(review), "window_days": days}

    return run


handler("fourteen-day-activation-reviewer")(_window_handler(14))
handler("thirty-day-transfer-reviewer")(_window_handler(30))
handler("ninety-day-stability-reviewer")(_window_handler(90))


@handler("relapse-cycle-detector")
def relapse_cycle_detector(contract, payload: Payload, context: Payload) -> Payload:
    from ..formation_twin import RelapseStateMachine
    from ..formation_twin.models import RelapseState

    current, target = require(payload, "current", "target")
    machine = RelapseStateMachine()
    try:
        current_state = RelapseState(current)
        target_state = RelapseState(target)
    except ValueError as exc:
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", str(exc)) from exc
    allowed = machine.can_transition(current_state, target_state)
    return {
        "current": current,
        "target": target,
        "transition_allowed": allowed,
        "resulting_state": target if allowed else current,
        "relapse_is_event_not_identity_loss": True,
    }


@handler("relationship-repair-verifier")
def relationship_repair_verifier(contract, payload: Payload, context: Payload) -> Payload:
    from ..formation_twin import verify_repair
    from ..formation_twin.models import RelationshipRepair

    raw = payload.get("repair")
    if raw is None:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "repair is required")
    repair = raw if isinstance(raw, RelationshipRepair) else RelationshipRepair(**raw)
    return {"repair_verification": dumped(verify_repair(repair))}


@handler("gospel-identity-migration-evaluator")
def identity_migration_evaluator(contract, payload: Payload, context: Payload) -> Payload:
    from ..formation_twin import evaluate_identity_migration
    from ..formation_twin.models import IdentityMigration

    raw = payload.get("migration")
    if raw is None:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "migration is required")
    migration = raw if isinstance(raw, IdentityMigration) else IdentityMigration(**raw)
    return {"identity_migration": dumped(evaluate_identity_migration(migration))}


@handler("formation-safety-governance-and-report")
def formation_safety_report(contract, payload: Payload, context: Payload) -> Payload:
    from ..formation_twin import FormationSafetyGuardian

    text = str(payload.get("text") or payload.get("raw_input") or "")
    decision = FormationSafetyGuardian().review(text)
    return {"safety": dumped(decision)}
