"""Fail-closed validation for licensed, versioned digital-human assets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

SHA256_KEYS = ("modelSha256", "portraitSha256", "voiceProfileSha256")
REVIEW_KEYS = ("theologyReviewId", "rightsReviewId", "accessibilityReviewId")


def _https_asset_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.endswith("example.com"):
        return None
    return value


def validate_asset_entry(character_id: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("characterId") != character_id:
        return None
    if value.get("reviewState") != "APPROVED" or not isinstance(value.get("version"), str):
        return None
    model_url = _https_asset_url(value.get("modelUrl"))
    portrait_url = _https_asset_url(value.get("portraitUrl"))
    if not model_url or not portrait_url:
        return None
    for key in SHA256_KEYS:
        digest = value.get(key)
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            return None
    for key in REVIEW_KEYS:
        if not isinstance(value.get(key), str) or not value[key].strip():
            return None
    if not isinstance(value.get("voiceId"), str) or not value["voiceId"].strip():
        return None
    if not isinstance(value.get("voiceProvider"), str) or not value["voiceProvider"].strip():
        return None
    return dict(value)


def validated_characters(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if manifest.get("schemaVersion") != "digital-human-assets/v1":
        return {}
    characters = manifest.get("characters")
    if not isinstance(characters, Mapping):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for character_id, value in characters.items():
        if isinstance(character_id, str) and (entry := validate_asset_entry(character_id, value)):
            result[character_id] = entry
    return result


def load_manifest_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("asset manifest must be a JSON object")
    return payload
