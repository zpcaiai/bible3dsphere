"""Optional structured extraction for explicit formation expressions/hypotheses."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .formation_ontology import FormationNodeType, FormationScope, FormationStatementType
from .formation_safety import validate_model_candidate

PROMPT_VERSION = "formation-hypothesis-1.0"
SCHEMA_VERSION = "formation-candidate-1.0"


class EvidenceSpan(BaseModel):
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)


class FormationCandidate(BaseModel):
    node_type: FormationNodeType
    content: str = Field(min_length=1, max_length=500)
    statement_type: Literal[
        FormationStatementType.MODEL_EXTRACTED_EXPLICIT_EXPRESSION,
        FormationStatementType.MODEL_FORMATION_HYPOTHESIS,
    ]
    confidence: float = Field(ge=0, le=1)
    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=3)
    alternatives: list[str] = Field(default_factory=list, max_length=3)
    scope: FormationScope = FormationScope.THIS_EVENT_ONLY


class FormationInferenceOutput(BaseModel):
    candidates: list[FormationCandidate] = Field(default_factory=list, max_length=6)
    insufficient_context: bool = False
    diagnosis_attempted: bool = False
    theological_verdict_attempted: bool = False


SYSTEM_PROMPT = """只从用户主动授权的文本中提取用户明确说出的形成表达，或提出可拒绝的候选。
不得补全缺失环节，不得判断救恩、悔改、罪、偶像、隐藏动机、人格、成熟度、圣洁程度或神的旨意。
深层候选必须提供原文偏移证据、置信度、至少一个替代解释、仅限本事件的范围；全部候选待用户确认。
不得输出因果断言。若证据不足，设置 insufficient_context。只输出符合 JSON Schema 的 JSON。"""


def available() -> bool:
    if os.getenv("FORMATION_TWIN_BELIEF_HYPOTHESIS_ENABLED", "false").lower() != "true":
        return False
    try:
        import llm_provider
        return bool(llm_provider._real_configured())
    except Exception:
        return False


def infer_formation_candidates(text: str) -> tuple[list[dict], dict]:
    if not available():
        return [], {"status": "DISABLED", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
    try:
        import llm_provider
        output = llm_provider.generate_json(
            SYSTEM_PROMPT, {"text": text, "language": "zh-CN"}, FormationInferenceOutput,
            temperature=0.0, max_tokens=1300, agent_name="formation_twin_spiritual",
            skill_name="formation-twin-hypothesis",
        )
    except Exception:
        return [], {"status": "FAILED", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
    if output.diagnosis_attempted or output.theological_verdict_attempted:
        return [], {"status": "REJECTED_UNSAFE", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    accepted = []
    for item in output.candidates:
        evidence = [span.model_dump() for span in item.evidence_spans if span.end_offset <= len(text) and span.end_offset > span.start_offset]
        candidate = {
            "node_type": item.node_type.value,
            "content": item.content,
            "statement_type": item.statement_type.value,
            "source_kind": "MODEL",
            "confidence": item.confidence,
            "evidence": evidence,
            "alternatives": item.alternatives,
            "scope": item.scope.value,
            "user_review_status": "PENDING",
            "expires_at": expires_at,
        }
        if item.confidence >= 0.45 and not validate_model_candidate(candidate):
            accepted.append(candidate)
    return accepted, {"status": "ACCEPTED", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
