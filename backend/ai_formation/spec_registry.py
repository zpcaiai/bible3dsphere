"""Canonical Batch 01-12 JSON Schema and reviewed-asset registry.

The copied specs are the exact resources installed by the complete-program
Skill.  Runtime validation is deterministic and does not ask an LLM to decide
whether sensitive data, age gates, or safety invariants are acceptable.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from jsonschema.validators import validator_for


SPECS_ROOT = Path(__file__).with_name("specs")
_SCHEMA_SUFFIX = ".schema.json"
_FORBIDDEN_TRUE_FIELDS = {
    "aiIsUltimateAuthority", "claimsDivineRevelation", "claimsDivineRevelationAllowed",
    "aiMayReplacePrayer", "aiMayReplaceChurch", "aiMayPerformHumanAct",
    "aiMayClaimMutualLove", "aiMayDemandSecrecy", "aiMayProvideSexualContentToMinor",
    "privateMinorChatAllowed", "secretMonitoringAllowed", "fullDeviceHistoryShared",
    "explicitContentShared", "explicitContentStored", "explicitNarrativeStored",
    "explicitEvidenceUploaded", "rawPromptStored", "rawGeneratedAnswerStored",
    "rawConversationStored", "rawFantasyStored", "rawDisclosureStored",
    "sexualHistoryStored", "individualizedSexualHistoryRequested", "coercionAllowed",
    "explicitDemonstrationAllowed", "diagnosisGenerated", "clinicalDiagnosisGenerated",
    "salvationInferenceGenerated", "spiritualRankGenerated", "spiritualMaturityScoreGenerated",
    "overallMaturityStateGenerated", "futureSpiritualStatePredicted", "hiddenTraitInferred",
    "crossUserComparisonGenerated", "crossUserRankingEnabled", "publicLeaderboardEnabled",
    "modelInferredEventAllowed", "rawDeviceTelemetryUsed", "browsingHistoryUsed",
    "observerMayAccessPrivateJournal", "relationshipQualityScoreGenerated",
    "automaticBehaviorChangeAllowed", "automaticNotificationToOthersAllowed",
    "highStakesDecisionAllowed", "modelConfidenceOverridesHuman", "automatedApprovalAllowed",
    "automatedDecisionAllowed", "automatedOverrideAllowed", "autoPublishAllowed",
}
_FORBIDDEN_TEXT_FIELD = re.compile(
    r"(?:raw(?:Prompt|Answer|Conversation|Disclosure|Narrative|Transcript)|"
    r"explicit(?:Content|Media)|browsingHistory|privateChat|sexualHistory|medicalDetails)$",
    re.IGNORECASE,
)


class SpecValidationError(ValueError):
    def __init__(self, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.path = path


def _batch_id(path: Path) -> str:
    return path.parents[1].name.removeprefix("batch_")


def _schema_key(path: Path) -> str:
    return path.name.removesuffix(_SCHEMA_SUFFIX)


@lru_cache(maxsize=1)
def _schemas() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}
    for path in sorted(SPECS_ROOT.glob("batch_*/schemas/*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        key = _schema_key(path)
        if key in result:
            raise RuntimeError(f"duplicate AI formation schema key: {key}")
        item = {
            "key": key,
            "batchId": _batch_id(path),
            "filename": path.name,
            "schema": schema,
        }
        result[key] = item
        for alias in (schema.get("title"), schema.get("$id"), path.name):
            if alias:
                aliases[str(alias).casefold()] = key
    result["__aliases__"] = aliases  # type: ignore[assignment]
    return result


def resolve_schema(name: str) -> dict[str, Any]:
    catalog = _schemas()
    key = name.removesuffix(_SCHEMA_SUFFIX)
    if key not in catalog:
        key = catalog["__aliases__"].get(name.casefold(), "")  # type: ignore[index]
    item = catalog.get(key)
    if not item or key == "__aliases__":
        raise SpecValidationError(f"unknown AI formation schema: {name}")
    return item


def schema_catalog(*, batch_id: str | None = None, include_schema: bool = False) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, item in _schemas().items():
        if key == "__aliases__" or (batch_id and item["batchId"] != batch_id):
            continue
        schema = item["schema"]
        entry = {
            "key": key,
            "batchId": item["batchId"],
            "title": schema.get("title", key),
            "version": schema.get("properties", {}).get("version", {}).get("const", "1.0.0"),
            "required": schema.get("required", []),
            "propertyCount": len(schema.get("properties", {})),
            "serverManagedFields": sorted(_server_managed_fields(schema)),
        }
        if include_schema:
            entry["schema"] = copy.deepcopy(schema)
        items.append(entry)
    return items


def _server_managed_fields(schema: dict[str, Any]) -> set[str]:
    fields = {
        "tenantId", "learnerId", "ownerUserId", "subjectRef", "requestedByRef",
        "createdAt", "updatedAt", "startedAt", "generatedAt", "requestedAt", "checkedAt",
    }
    primary_id = next(
        (
            field for field in schema.get("required", [])
            if field.endswith("Id") and field not in fields
        ),
        None,
    )
    if primary_id:
        fields.add(primary_id)
    return fields


def _default_for(
    field: str, spec: dict[str, Any], *, tenant_id: str, learner_id: str,
    server_managed_fields: set[str],
) -> Any:
    if "const" in spec:
        return copy.deepcopy(spec["const"])
    if "default" in spec:
        return copy.deepcopy(spec["default"])
    if field == "tenantId":
        return tenant_id
    if field in {"learnerId", "ownerUserId", "subjectRef", "requestedByRef"}:
        return learner_id
    if field == "version":
        return "1.0.0"
    if field in server_managed_fields and field.endswith("Id"):
        return str(uuid.uuid4())
    if field in {"createdAt", "updatedAt", "startedAt", "generatedAt", "requestedAt", "checkedAt"}:
        return datetime.now(UTC).isoformat()
    if field == "safetyLevel":
        return "S0"
    raise KeyError(field)


def _bind_server_fields(schema: dict[str, Any], payload: dict[str, Any], *, tenant_id: str, learner_id: str) -> dict[str, Any]:
    normalized = copy.deepcopy(payload)
    properties = schema.get("properties", {})
    server_managed_fields = _server_managed_fields(schema)
    for field in schema.get("required", []):
        if field in normalized:
            continue
        try:
            normalized[field] = _default_for(
                field, properties.get(field, {}), tenant_id=tenant_id, learner_id=learner_id,
                server_managed_fields=server_managed_fields,
            )
        except KeyError:
            pass
    for field, expected in (("tenantId", tenant_id), ("learnerId", learner_id)):
        if field not in properties:
            continue
        supplied = normalized.get(field)
        if supplied not in (None, "", expected):
            raise SpecValidationError(f"{field} does not match authenticated owner", path=field)
        normalized[field] = expected
    return normalized


def _enforce_privacy(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, key)
            if key in _FORBIDDEN_TRUE_FIELDS and child is True:
                raise SpecValidationError(f"prohibited safety/privacy flag enabled: {key}", path=".".join(child_path))
            if _FORBIDDEN_TEXT_FIELD.search(key) and child not in (None, "", False, [], {}):
                raise SpecValidationError(f"prohibited sensitive narrative field: {key}", path=".".join(child_path))
            _enforce_privacy(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _enforce_privacy(child, (*path, str(index)))


def validate_spec_payload(name: str, payload: dict[str, Any], *, tenant_id: str, learner_id: str) -> tuple[str, str, dict[str, Any]]:
    item = resolve_schema(name)
    schema = item["schema"]
    normalized = _bind_server_fields(schema, payload, tenant_id=tenant_id, learner_id=learner_id)
    _enforce_privacy(normalized)
    validator_cls = validator_for(schema)
    validator = validator_cls(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(normalized), key=lambda error: list(error.absolute_path))
    if errors:
        error: JsonSchemaValidationError = errors[0]
        path = ".".join(str(part) for part in error.absolute_path)
        raise SpecValidationError(error.message, path=path)
    version = str(normalized.get("version", "1.0.0"))
    return item["batchId"], version, normalized


@lru_cache(maxsize=1)
def asset_catalog() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for path in sorted(SPECS_ROOT.glob("batch_*/assets/*")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        batch_id = _batch_id(path)
        version = str(data.get("version", "1.0.0")) if isinstance(data, dict) else "1.0.0"
        review_status = data.get("review_status", "theology_review") if isinstance(data, dict) else "theology_review"
        if review_status not in {"draft", "theology_review", "pastoral_review", "approved", "rejected"}:
            review_status = "theology_review"
        assets.append({
            "id": f"ai-formation.batch-{batch_id}.{path.stem}",
            "batchId": batch_id,
            "kind": path.stem,
            "version": version,
            "reviewStatus": review_status,
            "sourcePath": f"batch_{batch_id}/assets/{path.name}",
            "data": data,
        })
    return assets
