"""Deterministic pre-review packets for the 67 AI Formation content assets.

Automation prepares evidence; it never signs theology, pastoral, child-safety,
rights, accessibility, or release decisions on behalf of a human reviewer.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .spec_registry import asset_catalog


HUMAN_REVIEW_ROLES = {
    "theology_reviewer",
    "pastoral_reviewer",
    "child_safety_reviewer",
    "rights_reviewer",
    "content_reviewer",
    "accessibility_reviewer",
    "release_reviewer",
}

REQUIRED_REVIEW_ATTESTATIONS = {
    "theology_reviewer": [
        "SCRIPTURE_CONTEXT_CHECKED",
        "AUTHORITY_LAYERING_CHECKED",
        "GOSPEL_ORDER_CHECKED",
        "DENOMINATIONAL_VARIANCE_CHECKED",
        "HARMFUL_USE_CHECKED",
    ],
    "pastoral_reviewer": [
        "S0_S3_ROUTING_CHECKED",
        "NON_DIAGNOSTIC_LANGUAGE_CHECKED",
        "SHAME_COERCION_CHECKED",
        "HUMAN_HANDOFF_CHECKED",
    ],
    "child_safety_reviewer": [
        "SECRECY_GROOMING_CHECKED",
        "AGE_APPROPRIATENESS_CHECKED",
        "ADULT_MINOR_CHANNELS_CHECKED",
        "CHILD_DATA_EXPOSURE_CHECKED",
        "SAFEGUARDING_ESCALATION_CHECKED",
    ],
    "rights_reviewer": [
        "SOURCE_RIGHTS_CHECKED",
        "BIBLE_TRANSLATION_RIGHTS_CHECKED",
        "CACHE_EXPORT_DISTRIBUTION_CHECKED",
    ],
    "content_reviewer": [
        "FACTUAL_CLAIMS_CHECKED",
        "SCRIPTURE_REFERENCES_CHECKED",
        "AGE_FIT_CHECKED",
        "SHAME_COERCION_BIAS_CHECKED",
        "REVIEW_STATE_CHECKED",
    ],
    "accessibility_reviewer": [
        "KEYBOARD_FLOW_CHECKED",
        "SCREEN_READER_FLOW_CHECKED",
        "MOBILE_REFLOW_CHECKED",
        "COGNITIVE_LOAD_CHECKED",
        "SENSITIVE_EXIT_CHECKED",
    ],
    "release_reviewer": [
        "EVIDENCE_SCOPE_HASH_CHECKED",
        "BLOCKERS_REVIEWED",
        "LIMITED_ROLLOUT_CHECKED",
        "ROLLBACK_INCIDENT_OWNERS_CHECKED",
    ],
}

_RISK_TERMS = {
    "theology_authority": ("神告诉你", "神命令", "绝对服从", "救恩", "得救", "重生"),
    "pastoral_safety": ("自杀", "自伤", "虐待", "性侵", "诊断", "成瘾", "绝望", "保密"),
    "child_safety": ("未成年人", "儿童", "孩子", "青少年", "秘密", "私聊", "性化", "监控", "导师"),
    "coercion_shame": ("羞辱", "惩罚", "强迫", "胁迫", "恐惧", "神对你失望"),
    "privacy_rights": ("隐私", "删除", "导出", "日志", "浏览历史", "第三方", "译文", "版权"),
}
_SCRIPTURE_KEYS = {"scripture_anchors", "scriptureAnchors", "scripture_references", "scriptureReferences"}
_AUTHORITY_KEYS = {"authority_level", "authorityLevel"}
_REVIEW_KEYS = {"review_status", "reviewStatus"}
_URL_RE = re.compile(r"https?://[^\s\"<>]+")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _walk(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, (*path, str(index)))


def _values_for_keys(data: Any, keys: set[str]) -> list[Any]:
    values: list[Any] = []
    for path, value in _walk(data):
        if path and path[-1] in keys:
            values.extend(value if isinstance(value, list) else [value])
    return values


def _strings(data: Any) -> list[tuple[str, str]]:
    return [
        ("/".join(path), value)
        for path, value in _walk(data)
        if isinstance(value, str)
    ]


def _stable_ids(data: Any) -> tuple[int, list[str]]:
    ids = [
        value
        for path, value in _walk(data)
        if path and path[-1] in {"id", "course_id", "moduleId", "scenario_set_id", "catalog_id"}
        and isinstance(value, str)
    ]
    duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
    return len(ids), duplicates


def required_reviews(batch_id: str) -> list[str]:
    # The release scope explicitly requires every one of the 67 content
    # versions to receive these five independent human reviews.  Age- or
    # release-specific roles remain additive.
    roles = [
        "theology_reviewer",
        "pastoral_reviewer",
        "child_safety_reviewer",
        "rights_reviewer",
        "content_reviewer",
    ]
    if batch_id in {"07", "08", "09", "10", "12"}:
        roles.append("accessibility_reviewer")
    if batch_id == "12":
        roles.append("release_reviewer")
    return roles


def age_bands(batch_id: str) -> list[str]:
    return {
        "04": ["16_18", "adult"],
        "06": ["0_6", "7_12", "13_15", "16_18", "adult"],
        "07": ["0_6", "7_12", "adult"],
        "08": ["13_15", "16_18", "adult"],
        "10": ["7_12", "13_15", "16_18", "adult"],
        "11": ["7_12", "13_15", "16_18", "adult"],
    }.get(batch_id, ["adult"])


def build_review_packet(
    asset: dict[str, Any], *, statement_of_faith_version: str | None,
    rights_attestation_id: str | None, generated_at: str,
) -> dict[str, Any]:
    data = asset["data"]
    canonical = canonical_json(data)
    content_hash = sha256_text(canonical)
    strings = _strings(data)
    scripture = sorted({str(value) for value in _values_for_keys(data, _SCRIPTURE_KEYS)})
    authorities = Counter(str(value) for value in _values_for_keys(data, _AUTHORITY_KEYS))
    review_states = Counter(str(value) for value in _values_for_keys(data, _REVIEW_KEYS))
    urls = sorted({url for _path, value in strings for url in _URL_RE.findall(value)})
    longest_text = max((len(value) for _path, value in strings), default=0)
    risk_hits = {
        category: [
            {"path": path, "term": term}
            for path, value in strings
            for term in terms
            if term in value
        ]
        for category, terms in _RISK_TERMS.items()
    }
    id_count, duplicate_ids = _stable_ids(data)
    roles = required_reviews(asset["batchId"])
    blockers = []
    if not statement_of_faith_version:
        blockers.append("STATEMENT_OF_FAITH_VERSION_REQUIRED")
    if not rights_attestation_id:
        blockers.append("SOURCE_RIGHTS_OWNER_ATTESTATION_REQUIRED")
    if duplicate_ids:
        blockers.append("DUPLICATE_STABLE_IDS")

    return {
        "packetVersion": "1.0.0",
        "contentId": asset["id"],
        "batchId": asset["batchId"],
        "contentKind": asset["kind"],
        "contentVersion": asset["version"],
        "contentSha256": content_hash,
        "canonicalSizeBytes": len(canonical.encode("utf-8")),
        "sourcePath": asset["sourcePath"],
        "generatedAt": generated_at,
        "scope": {
            "statementOfFaithVersion": statement_of_faith_version,
            "rightsAttestationId": rights_attestation_id,
            "ageBands": age_bands(asset["batchId"]),
            "requiredReviewerRoles": roles,
        },
        "automatedPreReview": {
            "yamlParsed": True,
            "stableIdCount": id_count,
            "duplicateStableIds": duplicate_ids,
            "authorityLabels": dict(sorted(authorities.items())),
            "embeddedReviewStates": dict(sorted(review_states.items())),
            "scriptureAnchors": scripture,
            "scriptureAnchorCount": len(scripture),
            "externalUrls": urls,
            "longestTextScalarCharacters": longest_text,
            "longBibleTranslationExcerptDetected": longest_text > 500,
            "riskTermsForHumanContextReview": {
                key: value for key, value in risk_hits.items() if value
            },
            "limitations": [
                "Term hits identify passages requiring human context review; they are not automatic failures.",
                "No automated process determines theology, pastoral fitness, child safety, or legal rights.",
            ],
        },
        "humanReview": {
            role: {
                "status": "not_signed",
                "reviewerId": None,
                "decision": None,
                "completedAt": None,
                "evidenceRefs": [],
                "conditions": [],
                "requiredAttestationCodes": REQUIRED_REVIEW_ATTESTATIONS[role],
            }
            for role in roles
        },
        "preReviewStatus": "BLOCKED" if blockers else "READY_FOR_AUTHORIZED_HUMAN_REVIEW",
        "blockers": blockers,
        "automatedApprovalAllowed": False,
        "autoPublishAllowed": False,
    }


def build_review_bundle(
    *, statement_of_faith_version: str | None = None,
    rights_attestation_id: str | None = None, generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or datetime.now(UTC).isoformat()
    packets = [
        build_review_packet(
            asset,
            statement_of_faith_version=statement_of_faith_version,
            rights_attestation_id=rights_attestation_id,
            generated_at=created,
        )
        for asset in asset_catalog()
    ]
    artifact_hash = sha256_text(canonical_json([
        {"contentId": packet["contentId"], "version": packet["contentVersion"], "sha256": packet["contentSha256"]}
        for packet in packets
    ]))
    blockers = sorted({blocker for packet in packets for blocker in packet["blockers"]})
    return {
        "bundleVersion": "1.0.0",
        "artifactId": "sunday_school.ai_formation.content-bundle",
        "artifactVersion": "1.0.0",
        "artifactSha256": artifact_hash,
        "generatedAt": created,
        "contentVersionCount": len(packets),
        "status": "BLOCKED" if blockers else "READY_FOR_AUTHORIZED_HUMAN_REVIEW",
        "blockers": blockers,
        "automatedApprovalAllowed": False,
        "packets": packets,
    }


def write_review_bundle(bundle: dict[str, Any], output_dir: Path) -> None:
    packets_dir = output_dir / "content-review-packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    for packet in bundle["packets"]:
        filename = f"{packet['contentId']}@{packet['contentVersion']}.json"
        (packets_dir / filename).write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    index = {**bundle, "packets": [
        {
            "contentId": packet["contentId"],
            "contentVersion": packet["contentVersion"],
            "contentSha256": packet["contentSha256"],
            "preReviewStatus": packet["preReviewStatus"],
            "packet": f"content-review-packets/{packet['contentId']}@{packet['contentVersion']}.json",
        }
        for packet in bundle["packets"]
    ]}
    (output_dir / "content-review-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
