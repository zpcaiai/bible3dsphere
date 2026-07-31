from __future__ import annotations

from .models import Actor


def detect_conflict(actor: Actor, case_relationships: list[str]) -> dict:
    conflicts = set(actor.conflicts).intersection(case_relationships)
    return {
        "conflict_present": bool(conflicts),
        "matches": sorted(conflicts),
        "decision": "recuse" if conflicts else "proceed",
    }
