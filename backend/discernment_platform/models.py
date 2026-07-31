from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


SubjectType = Literal["idea", "person", "event", "product", "media", "self_reflection", "mixed"]
FaithContext = Literal["christian", "seeker", "unknown", "other"]
Sensitivity = Literal["normal", "pastoral", "mental_health", "abuse", "crisis", "reputation_sensitive", "legal_sensitive", "minor_involved"]


class ConsentScope(BaseModel):
    allow_spiritual_analysis: bool = False
    allow_gospel_bridge: bool = False
    allow_public_content_analysis: bool = False
    allow_longitudinal_memory: bool = False


class SourceItem(BaseModel):
    source_type: str = Field(min_length=1, max_length=80)
    locator: str = Field(min_length=1, max_length=1000)
    quote: str | None = Field(default=None, max_length=2000)
    evidence_level: Literal["E0", "E1", "E2", "E3", "E4", "P0", "P1", "P2", "P3", "P4"] = "E1"
    independence_group: str | None = Field(default=None, max_length=120)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class DiscernmentCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    subject_type: SubjectType
    raw_input: str = Field(min_length=1, max_length=12000)
    user_goal: str = Field(min_length=1, max_length=1000)
    faith_context: FaithContext = "unknown"
    consent_scope: ConsentScope
    sensitivity: Sensitivity = "normal"
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    source_items: list[SourceItem] = Field(default_factory=list, max_length=100)

    @field_validator("title", "raw_input", "user_goal")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.strip().split())


class DialogueStart(BaseModel):
    preferred_depth: Literal["brief", "standard", "deep"] = "standard"


class DialogueTurn(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    gospel_consent: Literal["not_asked", "accepted", "declined", "later", "unclear"] | None = None


class ReviewRequest(BaseModel):
    action: Literal["REQUEST_REVIEW", "CORRECT", "WITHDRAW"]
    note: str = Field(default="", max_length=4000)
    correction: dict[str, Any] = Field(default_factory=dict)


class AdminReviewDecision(BaseModel):
    decision: Literal["APPROVED", "CHANGES_REQUIRED", "BLOCKED"]
    note: str = Field(min_length=1, max_length=4000)


class GospelPathRequest(BaseModel):
    preferred_depth: Literal["brief", "standard", "deep"] = "standard"
    church_context: str = Field(default="", max_length=1000)
