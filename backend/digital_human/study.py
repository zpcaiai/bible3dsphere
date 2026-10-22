"""Read-only study material from the real, versioned character catalog.

This is a reference browser, not generated answers or an approval mechanism.
All source content remains subject to independent human review.
"""
from __future__ import annotations

from .registry import CATALOG_SHA256, CONTENT_VERSION, PREPARED_ANSWERS, catalog_artifact
from .scripture import expand_reference


def study_material(character_id: str) -> dict[str, object]:
    artifact = catalog_artifact()
    characters = {item["id"]: item for item in artifact["characters"]}
    if character_id not in characters:
        raise KeyError(character_id)
    character = characters[character_id]
    topics = []
    for case in character["truthCases"]:
        expected = case["expected"]
        references = list(expected.get("mustReference", []))
        canonical = list(dict.fromkeys(ref for value in references for ref in expand_reference(value)))
        topics.append({
            "id": case["id"], "question": case["question"],
            "references": references, "canonicalReferences": canonical,
            "evidenceResolvable": bool(references) and all(expand_reference(value) for value in references),
            "unsupported": expected.get("grounding") == "G0_UNSUPPORTED" or not references,
            "sourceGrounding": expected.get("grounding") or expected.get("minGrounding"),
            "limitations": list(expected.get("mustNotClaim", [])),
            "reviewState": "THEOLOGY_REVIEW", "speechApproved": False,
        })
    relationships = [{
        "targetId": edge["target"],
        "targetName": characters.get(edge["target"], {}).get("canonicalName", edge["target"]),
        "selectable": edge["target"] in characters,
        "relationshipType": edge["type"],
        "references": list(edge["evidence"]),
        "canonicalReferences": list(dict.fromkeys(ref for value in edge["evidence"] for ref in expand_reference(value))),
        "reviewState": "THEOLOGY_REVIEW",
    } for edge in character["relationships"]]
    return {
        "characterId": character_id, "canonicalName": character["canonicalName"],
        "period": character["period"], "ragScope": character["ragScope"],
        "topics": topics, "relationships": relationships,
        "preparedAnswerCount": sum(item.character_id == character_id for item in PREPARED_ANSWERS),
        "contentVersion": CONTENT_VERSION, "catalogSha256": CATALOG_SHA256,
        "contentReviewState": "THEOLOGY_REVIEW", "speechApproved": False,
        "disclosure": "这是待审核的目录研读资料，不是完整人物回答；经文定位可核验，解释与关系仍需人工审核。",
    }
