"""Optional, provider-agnostic emotion candidate inference with fail-closed validation."""
from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .emotion_ontology import EmotionLabel

PROMPT_VERSION = "emotion-extraction-1.0"
SCHEMA_VERSION = "emotion-candidates-1.0"


class EvidenceSpan(BaseModel):
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_offset <= self.start_offset:
            raise ValueError("invalid evidence span")
        return self


class InferredCandidate(BaseModel):
    label: EmotionLabel
    custom_label: str | None = Field(default=None, max_length=80)
    confidence: float = Field(ge=0, le=1)
    evidence_spans: list[EvidenceSpan]
    alternative_labels: list[EmotionLabel] = Field(default_factory=list, max_length=3)
    explicit: bool = False


class EmotionInferenceOutput(BaseModel):
    language: str = "zh-CN"
    candidates: list[InferredCandidate] = Field(default_factory=list, max_length=5)
    body_state_candidates: list[dict] = Field(default_factory=list, max_length=5)
    insufficient_context: bool = False
    diagnosis_attempted: bool = False
    spiritual_judgment_attempted: bool = False


SYSTEM_PROMPT = """你的任务只是从用户主动授权的文本中提出情绪表达候选。
只根据给定文本；区分明确表达和可能表达；每个候选必须有合法文本偏移证据。
不得解释人格、核心信念、偶像、罪、救恩、属灵等级、神的旨意、创伤或心理疾病。
不得诊断，不得声称知道用户真正内心，不得分析第三方。输出只符合 JSON Schema。"""


def model_inference_available() -> bool:
    if os.getenv("FORMATION_TWIN_MODEL_INFERENCE_ENABLED", "false").lower() != "true":
        return False
    try:
        import llm_provider
        return bool(llm_provider._real_configured())
    except Exception:
        return False


def infer_candidates(text: str) -> tuple[list[dict], dict]:
    if not model_inference_available():
        return [], {"status": "DISABLED", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
    try:
        import llm_provider
        output = llm_provider.generate_json(
            SYSTEM_PROMPT, {"text": text, "language": "zh-CN"}, EmotionInferenceOutput,
            temperature=0.1, max_tokens=900, agent_name="formation_twin_emotion",
            skill_name="formation-twin-emotion-inference",
        )
    except Exception:
        return [], {"status": "FAILED", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
    if output.diagnosis_attempted or output.spiritual_judgment_attempted:
        return [], {"status": "REJECTED_UNSAFE", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
    accepted = []
    for candidate in output.candidates:
        spans = [span for span in candidate.evidence_spans if span.end_offset <= len(text)]
        if candidate.confidence < 0.45 or not spans:
            continue
        accepted.append({
            "emotion_label": candidate.label.value, "custom_label": candidate.custom_label,
            "confidence": candidate.confidence, "evidence_spans": [span.model_dump() for span in spans],
            "alternative_labels": [item.value for item in candidate.alternative_labels], "explicit": candidate.explicit,
            "source_kind": "MODEL", "statement_type": "MODEL_INFERENCE", "user_review_status": "PENDING",
            "model_version": os.getenv("LLM_MODEL", "configured-provider"), "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
        })
    return accepted, {"status": "ACCEPTED", "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION}
