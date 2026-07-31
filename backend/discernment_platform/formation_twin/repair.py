from __future__ import annotations

from .models import RelationshipRepair


def verify_repair(repair: RelationshipRepair) -> dict:
    core = [
        repair.harm_named,
        repair.responsibility_taken,
        repair.excuse_free,
        repair.behavior_change,
        repair.boundary_respected,
    ]
    passed = sum(core)

    if repair.status == "paused_for_safety":
        decision = "safety_pause"
    elif passed == 5:
        decision = "verified_change"
    elif repair.harm_named and repair.responsibility_taken:
        decision = "in_progress"
    else:
        decision = "insufficient"

    return {
        "decision": decision,
        "core_checks_passed": passed,
        "apology_only": repair.harm_named and repair.responsibility_taken and not repair.behavior_change,
        "limitations": repair.limitations,
    }
