from __future__ import annotations

from .models import RagQuery, SourceDocument
from .rights import RightsPolicy
from .misuse import detect_misuse


class TheologyKnowledgeOrchestrator:
    def __init__(self) -> None:
        self.rights = RightsPolicy()

    def filter_sources(
        self,
        query: RagQuery,
        sources: list[SourceDocument],
    ) -> dict:
        allowed = []
        blocked = []

        allowed_statuses = set(query.allowed_rights)
        for source in sources:
            if source.rights_status.value not in allowed_statuses:
                blocked.append({"source_id": source.source_id, "reason": "rights_not_allowed"})
                continue
            if source.source_type not in query.required_source_types:
                blocked.append({"source_id": source.source_id, "reason": "source_type_not_required"})
                continue
            if not self.rights.can_generate_from(source.rights_status):
                blocked.append({"source_id": source.source_id, "reason": "generation_prohibited"})
                continue
            allowed.append(source.model_dump())

        return {
            "allowed": allowed,
            "blocked": blocked,
            "review_status": "ready" if allowed else "insufficient_evidence",
        }

    def check_misuse(self, text: str) -> dict:
        return detect_misuse(text)
