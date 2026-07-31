from __future__ import annotations

from .models import FormationEvent


FOCUS = {
    14: ["awareness", "pause", "desire_naming", "gospel_recall", "first_repair"],
    30: ["repetition", "multi_context_transfer", "recovery_speed", "feedback_acceptance", "community_support"],
    90: ["pressure_stability", "relational_fruit", "relapse_recovery", "functional_savior_reduction", "identity_migration"],
}


def review_window(user_id: str, events: list[FormationEvent], window_days: int) -> dict:
    if window_days not in FOCUS:
        raise ValueError("window_days must be 14, 30, or 90")

    contexts = {e.context for e in events}
    gospel_recall_count = sum(bool(e.gospel_truth_recalled) for e in events)
    repair_count = sum(bool(e.repair_action) for e in events)
    relationship_events = sum(bool(e.relationship_effect) for e in events)

    limitations = []
    if len(events) < 3:
        limitations.append("Sparse event evidence.")
    if len(contexts) < 2 and window_days >= 30:
        limitations.append("Insufficient cross-context transfer evidence.")

    return {
        "review_id": f"review-{user_id}-{window_days}",
        "user_id": user_id,
        "window_days": window_days,
        "focus": FOCUS[window_days],
        "findings": {
            "event_count": len(events),
            "context_count": len(contexts),
            "gospel_recall_count": gospel_recall_count,
            "repair_count": repair_count,
            "relationship_event_count": relationship_events,
        },
        "limitations": limitations,
    }
