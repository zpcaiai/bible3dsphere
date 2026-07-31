from __future__ import annotations

from .chain import build_chain
from .models import FormationEvent
from .safety import FormationSafetyGuardian
from .windows import review_window


class FormationTwinOrchestrator:
    def __init__(self) -> None:
        self.guardian = FormationSafetyGuardian()

    def ingest(self, event: FormationEvent) -> dict:
        allow = bool(event.consent_scope.get("allow_longitudinal_tracking", False))
        if not allow:
            return {"review_status": "blocked", "reason": "tracking_consent_required"}

        safety = self.guardian.review(
            " ".join([
                event.context,
                event.trigger,
                event.automatic_interpretation,
                event.outcome,
            ])
        )
        if safety.status != "ready":
            return {
                "review_status": safety.status,
                "reasons": safety.reasons,
                "actions": safety.actions,
            }

        chain = build_chain(event)
        return {
            "review_status": "ready",
            "event": event.model_dump(),
            "chain": chain.model_dump(),
        }

    def review(self, user_id: str, events: list[FormationEvent], window_days: int) -> dict:
        return review_window(user_id, events, window_days)
