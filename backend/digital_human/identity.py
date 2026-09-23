from __future__ import annotations

import re

from .contracts import IdentityCandidate, IdentityResolution


def _norm(value: str) -> str:
    return re.sub(r"[\s·・,，。()（）]+", "", value).lower()


def resolve_identity(
    *,
    surface: str,
    characters: list[dict],
    ambiguous: list[dict],
    stable_labels: dict[str, str],
    explicit_character_id: str | None = None,
    current_character_id: str | None = None,
) -> IdentityResolution:
    by_id = {item["id"]: item for item in characters}

    def candidate(character_id: str) -> IdentityCandidate:
        item = by_id[character_id]
        return IdentityCandidate(
            characterId=character_id,
            stableLabel=stable_labels.get(character_id, item["canonicalName"]),
            englishName=item["englishName"],
        )

    if explicit_character_id:
        if explicit_character_id not in by_id:
            return IdentityResolution(status="NOT_FOUND", reasonCodes=["unknown-explicit-character-id"])
        selected = candidate(explicit_character_id)
        return IdentityResolution(
            status="RESOLVED", characterId=selected.characterId, stableLabel=selected.stableLabel,
            reasonCodes=["explicit-character-id"],
        )

    normalized = _norm(surface)
    ambiguous_match = next((item for item in ambiguous if _norm(item["surface"]) == normalized), None)
    if ambiguous_match:
        candidates = [candidate(item) for item in ambiguous_match["candidates"]]
        if current_character_id and current_character_id in ambiguous_match["candidates"]:
            selected = candidate(current_character_id)
            return IdentityResolution(
                status="RESOLVED", characterId=selected.characterId, stableLabel=selected.stableLabel,
                reasonCodes=["current-character-context"],
            )
        return IdentityResolution(
            status="AMBIGUOUS", candidates=candidates,
            reasonCodes=["ambiguous-bare-name", "candidate-selection-required"],
        )

    exact = next(
        (
            item for item in characters
            if normalized in {_norm(item["id"]), _norm(item["canonicalName"]), _norm(item["englishName"]), _norm(stable_labels.get(item["id"], ""))}
        ),
        None,
    )
    if exact:
        selected = candidate(exact["id"])
        return IdentityResolution(
            status="RESOLVED", characterId=selected.characterId, stableLabel=selected.stableLabel,
            reasonCodes=["unambiguous-exact-match"],
        )
    return IdentityResolution(status="NOT_FOUND", reasonCodes=["no-identity-match"])
