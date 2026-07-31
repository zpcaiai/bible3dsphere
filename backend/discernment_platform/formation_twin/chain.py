from __future__ import annotations

from .models import FormationChain, FormationEvent


def build_chain(event: FormationEvent) -> FormationChain:
    fruit = []
    if event.relationship_effect:
        fruit.extend(event.relationship_effect)
    if event.outcome:
        fruit.append(event.outcome)

    limitations = list(event.limitations)
    if not event.automatic_interpretation:
        limitations.append("Automatic interpretation not directly reported.")
    if event.source_type == "system_inference":
        limitations.append("System-only inference must remain low confidence.")

    return FormationChain(
        chain_id=f"chain-{event.event_id}",
        event_id=event.event_id,
        trigger=event.trigger,
        interpretation=event.automatic_interpretation,
        desire=event.desire_or_fear,
        belief=event.active_belief,
        emotion_body=event.emotion + event.body_signal,
        action=event.chosen_action,
        relationship_effect=event.relationship_effect,
        short_reward=event.immediate_reward,
        long_cost=event.delayed_cost,
        fruit=fruit,
        gospel_alternative={
            "truth_recalled": event.gospel_truth_recalled,
            "repair_action": event.repair_action,
        },
        limitations=limitations,
    )
