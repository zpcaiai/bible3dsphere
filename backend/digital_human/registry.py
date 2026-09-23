from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .assurance import canonical_json, load_key_map, verify_release_certificate
from .assets import validated_characters
from .contracts import AvatarProfile, CharacterProfile, GroundingEvidence, VoiceProfile

CONTENT_VERSION = "1.3.0"
RETRIEVAL_TEMPLATE_VERSION = "retrieval-review-notice-v1"
DISCLOSURE = "人物形象、声音与第一人称表达均为教育性艺术重建，不代表真实历史肖像、原声或新的启示。"


@dataclass(frozen=True)
class CharacterSeed:
    id: str
    canonical_name: str
    english_name: str
    questions: tuple[str, ...]
    catalog_tier: str = "deep-alpha"
    catalog_status: str = "alpha-ready"
    truth_case_count: int = 1


@lru_cache(maxsize=1)
def catalog_artifact() -> dict[str, Any]:
    path = Path(__file__).with_name("catalog.v1.3.0.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != CONTENT_VERSION or payload.get("characterCount") != 100:
        raise RuntimeError("digital-human catalog artifact is invalid or stale")
    return payload


CATALOG_SHA256 = hashlib.sha256(Path(__file__).with_name("catalog.v1.3.0.json").read_bytes()).hexdigest()


CHARACTERS = tuple(
    CharacterSeed(
        id=item["id"],
        canonical_name=item["canonicalName"],
        english_name=item["englishName"],
        questions=tuple(item["recommendedQuestions"]),
        catalog_tier=item["catalogTier"],
        catalog_status=item["catalogStatus"],
        truth_case_count=item["truthCaseCount"],
    )
    for item in catalog_artifact()["characters"]
)


@dataclass(frozen=True)
class PreparedAnswer:
    id: str
    character_id: str
    keywords: tuple[str, ...]
    answer_type: str
    spoken_text: str
    grounding_level: str
    references: tuple[tuple[str, str], ...]
    related_characters: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


PREPARED_ANSWERS = (
    PreparedAnswer(
        "moses-call", "moses", ("呼召", "荆棘", "法老"), "EVENT",
        "《出埃及记》记载，神在燃烧却没有烧毁的荆棘中呼召摩西，并回应了他的迟疑；经文没有把摩西塑造成毫无惧怕的人。",
        "G5_DIRECT_SCRIPTURE", (("Exodus 3", "DIRECT"), ("Exodus 4", "DIRECT")), ("aaron",),
    ),
    PreparedAnswer(
        "david-spare-saul", "david", ("扫罗", "杀"), "EVENT",
        "《撒母耳记上》24章和26章记载，大卫有机会伤害扫罗却选择克制，并拒绝伸手加害耶和华的受膏者。这里能确认的是经文记录的言行，不应虚构未记载的私人启示。",
        "G5_DIRECT_SCRIPTURE", (("1 Samuel 24", "DIRECT"), ("1 Samuel 26", "DIRECT")), ("saul",),
    ),
    PreparedAnswer(
        "david-goliath", "david", ("歌利亚",), "EVENT",
        "《撒母耳记上》17章记载，大卫面对歌利亚时把争战的归属指向神，而不是把胜利解释成自己的体格或武器优势。",
        "G5_DIRECT_SCRIPTURE", (("1 Samuel 17", "DIRECT"),), ("saul",),
    ),
    PreparedAnswer(
        "peter-restoration", "peter", ("恢复", "不认", "三次"), "EVENT",
        "福音书记载彼得三次不认耶稣；《约翰福音》21章又记载复活后的耶稣三次问他是否爱主，并托付他牧养。经文让失败与恢复同时被看见。",
        "G5_DIRECT_SCRIPTURE", (("Luke 22:54-62", "DIRECT"), ("John 21:15-19", "DIRECT")),
    ),
    PreparedAnswer(
        "paul-conversion", "paul", ("大马士革", "转变", "归信"), "EVENT",
        "《使徒行传》9章记载，原本逼迫教会的扫罗在前往大马士革途中被主拦阻，随后受洗并开始传讲耶稣。关于经历的细节应限于经文本身。",
        "G5_DIRECT_SCRIPTURE", (("Acts 9:1-22", "DIRECT"),),
    ),
)


def _content_payload() -> str:
    return json.dumps(
        {"preparedAnswers": [asdict(item) for item in PREPARED_ANSWERS], "retrievalTemplate": RETRIEVAL_TEMPLATE_VERSION},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )


CONTENT_SHA256 = hashlib.sha256(_content_payload().encode("utf-8")).hexdigest()


def content_review_state() -> str:
    certificate_path = os.getenv("DIGITAL_HUMAN_RELEASE_CERTIFICATE_PATH", "").strip()
    trusted_keys_path = os.getenv("DIGITAL_HUMAN_TRUSTED_RELEASE_KEYS_PATH", "").strip()
    if not certificate_path or not trusted_keys_path:
        return "THEOLOGY_REVIEW"
    try:
        certificate = json.loads(Path(certificate_path).read_text(encoding="utf-8"))
        trusted_keys = load_key_map(Path(trusted_keys_path))
        subject = {
            "contentVersion": CONTENT_VERSION,
            "contentSha256": CONTENT_SHA256,
            "catalogSha256": CATALOG_SHA256,
            "assetManifestSha256": hashlib.sha256(canonical_json(_asset_manifest())).hexdigest(),
        }
        return "APPROVED" if verify_release_certificate(
            certificate, expected_subject=subject, trusted_release_keys=trusted_keys,
        ) else "THEOLOGY_REVIEW"
    except Exception:
        return "THEOLOGY_REVIEW"


@lru_cache(maxsize=1)
def _asset_manifest() -> dict[str, Any]:
    raw = os.getenv("DIGITAL_HUMAN_ASSET_MANIFEST_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def character_seed(character_id: str) -> CharacterSeed | None:
    return next((item for item in CHARACTERS if item.id == character_id), None)


def character_profile(character_id: str) -> CharacterProfile | None:
    seed = character_seed(character_id)
    if seed is None:
        return None
    asset = validated_characters(_asset_manifest()).get(character_id, {})
    reviewed = bool(asset)
    model_url = asset.get("modelUrl") if reviewed else None
    portrait_url = asset.get("portraitUrl") if reviewed else None
    voice_id = asset.get("voiceId") if reviewed and isinstance(asset.get("voiceId"), str) else None
    runtime_ready = bool(model_url and voice_id and content_review_state() == "APPROVED")
    return CharacterProfile(
        id=seed.id,
        canonicalName=seed.canonical_name,
        englishName=seed.english_name,
        status="alpha-ready" if reviewed else "review-required",
        catalogTier=seed.catalog_tier,
        catalogStatus=seed.catalog_status,
        truthCaseCount=seed.truth_case_count,
        avatar=AvatarProfile(
            modelUrl=model_url, portraitUrl=portrait_url,
            version=str(asset.get("version") or "unreleased"),
            framing=asset.get("framing") if asset.get("framing") in {"head", "bust", "full"} else "bust",
            reviewState="APPROVED" if reviewed and model_url else "THEOLOGY_REVIEW",
        ),
        voice=VoiceProfile(
            provider=str(asset.get("voiceProvider") or "azure"), voiceId=voice_id,
            language=str(asset.get("language") or "zh-CN"),
            reviewState="APPROVED" if reviewed and voice_id else "THEOLOGY_REVIEW",
        ),
        recommendedQuestions=list(seed.questions), disclosure=DISCLOSURE, runtimeReady=runtime_ready,
    )


def catalog() -> list[CharacterProfile]:
    return [profile for seed in CHARACTERS if (profile := character_profile(seed.id)) is not None]


def evidence(locator: str, support: str) -> GroundingEvidence:
    return GroundingEvidence(
        sourceType="SCRIPTURE", locator=locator, claimSupport=support,
        sourceVersion="canonical-reference-v1",
        note="经文定位已由本地标准书卷/章节目次解析器验证；响应未复制译文正文。",
    )
