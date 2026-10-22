"""Human-review drafts, never the public answer or Avatar speech path."""
from __future__ import annotations

import hashlib
import json
import os

from pydantic import BaseModel, ConfigDict, Field

from .assurance import canonical_json
from .contracts import DigitalHumanResponse
from .guardrails import validate_response
from .registry import CATALOG_SHA256, CONTENT_SHA256, CONTENT_VERSION, catalog_artifact, evidence
from .scripture import expand_reference


class DraftClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1, max_length=550)
    references: list[str] = Field(min_length=1, max_length=6)


class DraftCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterId: str
    topicId: str
    claims: list[DraftClaim] = Field(min_length=1, max_length=4)


def draft_context(character_id: str, topic_id: str) -> dict[str, object]:
    character = next((item for item in catalog_artifact()["characters"] if item["id"] == character_id), None)
    if character is None:
        raise KeyError(character_id)
    topic = next((item for item in character["truthCases"] if item["id"] == topic_id), None)
    if topic is None:
        raise ValueError("topic must belong to the selected character")
    expected = topic["expected"]
    refs = list(expected.get("mustReference", []))
    if expected.get("grounding") == "G0_UNSUPPORTED" or not refs or not all(expand_reference(ref) for ref in refs):
        raise ValueError("unsupported topics cannot be generated as character facts")
    return {
        "characterId": character_id, "topicId": topic_id,
        "question": topic["question"], "persona": character["persona"]["text"],
        "personaSha256": character["persona"]["sha256"], "catalogSha256": CATALOG_SHA256,
        "allowedReferences": refs, "mustNotClaim": list(expected.get("mustNotClaim", [])),
        "sourceUncertaintyRequired": bool(expected.get("mustSayUncertain")),
        "reviewState": "THEOLOGY_REVIEW", "speechApproved": False,
    }


def validate_draft(candidate: DraftCandidate, context: dict[str, object]) -> dict[str, object]:
    if candidate.characterId != context["characterId"] or candidate.topicId != context["topicId"]:
        raise ValueError("draft identity differs from the source topic")
    allowed = {ref for locator in context["allowedReferences"] for ref in expand_reference(locator)}
    used = []
    for claim in candidate.claims:
        if not claim.statement.strip():
            raise ValueError("draft claim must not be blank")
        if any(marker and marker in claim.statement for marker in context["mustNotClaim"]):
            raise ValueError("draft contradicts the topic's explicit boundary")
        for locator in claim.references:
            canonical = expand_reference(locator)
            if not canonical or not set(canonical).issubset(allowed):
                raise ValueError("draft cites evidence outside the retrieved topic")
            used.append(locator)
    text = "\n".join(claim.statement.strip() for claim in candidate.claims)
    # Citation membership cannot prove semantic entailment. Every draft remains
    # a low-grounding, non-speakable human-review object even after validation.
    response = validate_response(DigitalHumanResponse(
        characterId=candidate.characterId, answerType="FACT", spokenText=text, displayText=text,
        references=[evidence(ref, "CONTEXT_ONLY") for ref in dict.fromkeys(used)],
        groundingLevel="G1_INTERPRETIVE_POSSIBILITY", relatedEvents=[candidate.topicId],
        warnings=["generated-draft", "human-theology-review-required", "citation-membership-is-not-entailment"],
        contentVersion=CONTENT_VERSION, contentSha256=CONTENT_SHA256,
        contentReviewState="THEOLOGY_REVIEW", speechApproved=False,
    ))
    return {
        "candidate": candidate.model_dump(), "response": response.model_dump(),
        "draftSha256": hashlib.sha256(canonical_json(candidate.model_dump())).hexdigest(),
        "catalogSha256": context["catalogSha256"], "personaSha256": context["personaSha256"],
        "reviewState": "THEOLOGY_REVIEW", "speechApproved": False,
        "claimVerification": "HUMAN_REVIEW_REQUIRED", "persisted": False,
    }


def generate_review_draft(character_id: str, topic_id: str) -> dict[str, object]:
    context = draft_context(character_id, topic_id)
    if os.getenv("DIGITAL_HUMAN_DRAFT_GENERATION_ENABLED", "").lower() not in {"1", "true", "yes"}:
        raise RuntimeError("draft generation is disabled")
    # Reuse the existing provider boundary. Its normal offline Mock fallback is
    # explicitly prohibited here; no fabricated response can count as inference.
    from llm_provider import MockLLMProvider, get_provider
    provider = get_provider()
    if isinstance(provider, MockLLMProvider) or provider.name not in {"openai", "anthropic", "gemini", "local"} or not provider.model:
        raise RuntimeError("a real explicitly configured model is required")
    if (provider.name != "local" and not provider.api_key) or (provider.name == "local" and not provider.base_url):
        raise RuntimeError("the real provider configuration is incomplete")
    provider.timeout = max(1, min(provider.timeout, 30))
    provider.max_retries = 0
    messages = [
        {"role": "system", "content": (
            "只编写供独立神学人工审核的中文学习草稿；不是启示，不得自称历史人物本人。"
            "只能使用提供的经文范围；不得虚构心理活动、历史细节或新的神谕。"
            "必须区分经文明说、推断和不确定内容。若证据不足，不得编造事实。"
            "每项陈述都要列出其引用，引用字符串必须取自 allowedReferences，不要自行缩写或细化。引用存在并不意味着陈述已被审核。"
            "只输出符合以下 schema 的 JSON，不得添加审核通过、发声许可或额外字段："
            + json.dumps(DraftCandidate.model_json_schema(), ensure_ascii=False)
        )},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]
    try:
        result = provider.complete(messages, temperature=0.2, max_tokens=1200)
    except Exception as exc:
        # Vendor exceptions can contain request contents or credentials.
        raise RuntimeError("draft provider request failed; no draft was approved") from exc
    candidate = DraftCandidate.model_validate_json(result.text)
    draft = validate_draft(candidate, context)
    draft.update(providerExecution="EXECUTED", model=provider.model)
    return draft
