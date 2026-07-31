from __future__ import annotations

from .models import IdentityMigration


def evaluate_identity_migration(migration: IdentityMigration) -> dict:
    dimensions = {
        "interpretation": bool(migration.interpretation_shift),
        "desire": bool(migration.desire_shift),
        "action": bool(migration.action_shift),
        "relationship": bool(migration.relationship_shift),
        "relapse_response": bool(migration.relapse_response_shift),
    }
    count = sum(dimensions.values())

    if count == 0:
        status = "language_only" if migration.gospel_identity_truth else "unassessed"
    elif count <= 2:
        status = "early_transfer"
    elif count <= 4:
        status = "multi_context_transfer"
    else:
        status = "stable_under_pressure"

    return {
        "status": status,
        "dimensions": dimensions,
        "dimension_count": count,
        "warning": "This status describes observed transfer, not salvation status.",
    }
