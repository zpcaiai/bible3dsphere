"""Mission OS end-to-end lifecycle pipeline — the spine that ties Batches 1-6 together.

Each batch produces a stage output that gates the next stage. This module encodes
that ordering explicitly so the whole system is logically coherent: a worker can
never reach a downstream stage without the upstream stage having reached its
required state, and no automated stage ever marks a worker as "deployed".

  Batch 3  calling_discernment   -> readiness_assessment
  Batch 4  training_and_practicum
  Batch 5  sending_application   -> sending_committee_decision
  Batch 6  deployment_preparation -> deployment_readiness_gate
           deployment_planning (terminal — operational, outside the automated gate)
"""
from __future__ import annotations

# Ordered lifecycle stages. `deployment_planning` is the terminal state; there is
# no further automated batch beyond it.
STAGES = (
    "calling_discernment",       # Batch 3 · Skill 28
    "readiness_assessment",      # Batch 3 · Skill 34
    "training_and_practicum",    # Batch 4 · Skill 37-49
    "sending_application",        # Batch 5 · Skill 52
    "sending_committee_decision", # Batch 5 · Skill 53
    "deployment_preparation",     # Batch 6 · Skill 61-70
    "deployment_readiness_gate",  # Batch 6 · Skill 71
    "deployment_planning",        # terminal — operational hand-off
)
_INDEX = {s: i for i, s in enumerate(STAGES)}

STAGE_BATCH = {
    "calling_discernment": 3, "readiness_assessment": 3, "training_and_practicum": 4,
    "sending_application": 5, "sending_committee_decision": 5,
    "deployment_preparation": 6, "deployment_readiness_gate": 6, "deployment_planning": 6,
}

# To enter a stage, an upstream stage must have reached one of these states.
PREREQUISITES = {
    "readiness_assessment": ("calling_discernment", {"ready_for_readiness_assessment", "completed"}),
    "training_and_practicum": ("readiness_assessment", {"foundational_development", "local_practice_ready",
                                                        "cross_cultural_internship_ready", "team_discernment_ready",
                                                        "deployment_candidate"}),
    "sending_application": ("readiness_assessment", {"deployment_candidate"}),
    "sending_committee_decision": ("sending_application", {"committee_ready"}),
    "deployment_preparation": ("sending_committee_decision", {"approved_for_next_stage", "conditionally_approved"}),
    "deployment_readiness_gate": ("deployment_preparation", {"complete"}),
    "deployment_planning": ("deployment_readiness_gate", {"ready_for_deployment_planning"}),
}

# The gate's Ready state unlocks this final operational stage — never "deployed".
DEPLOYMENT_PLANNING_UNLOCK = "deployment_planning"


def validate_stage(stage: str) -> None:
    if stage not in _INDEX:
        raise ValueError(f"unknown mission stage: {stage!r}")


def next_stage(current: str) -> str | None:
    validate_stage(current)
    i = _INDEX[current]
    return STAGES[i + 1] if i + 1 < len(STAGES) else None


def assert_can_enter(target_stage: str, achieved: dict) -> None:
    """Raise unless the upstream prerequisite for *target_stage* has been met.

    `achieved` maps stage -> its current state string.
    """
    validate_stage(target_stage)
    prereq = PREREQUISITES.get(target_stage)
    if prereq is None:
        return  # the first stage has no prerequisite
    upstream_stage, allowed_states = prereq
    state = achieved.get(upstream_stage)
    if state not in allowed_states:
        raise ValueError(
            f"cannot enter {target_stage}: upstream {upstream_stage} is {state!r}, "
            f"requires one of {sorted(allowed_states)}"
        )


def deployment_activates_worker() -> bool:
    """No stage in the automated pipeline marks a worker as physically deployed."""
    return False
