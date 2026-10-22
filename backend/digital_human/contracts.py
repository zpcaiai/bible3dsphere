from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GroundingLevel = Literal[
    "G5_DIRECT_SCRIPTURE", "G4_STRONG_SCRIPTURAL_FACT", "G3_SCRIPTURAL_INFERENCE",
    "G2_HISTORICAL_RECONSTRUCTION", "G1_INTERPRETIVE_POSSIBILITY", "G0_UNSUPPORTED",
]
ReviewState = Literal["DRAFT", "THEOLOGY_REVIEW", "APPROVED", "WITHDRAWN"]


class GroundingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sourceType: Literal["SCRIPTURE", "HISTORY", "COMMENTARY", "INTERNAL_REVIEW"]
    locator: str = Field(min_length=1, max_length=120)
    claimSupport: Literal["DIRECT", "STRONG", "INFERRED", "CONTEXT_ONLY"]
    sourceVersion: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class DigitalHumanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterId: str = Field(pattern=r"^[a-z0-9_-]+$")
    answerType: Literal["FACT", "EVENT", "THEOLOGY", "DEVOTIONAL", "UNSUPPORTED"]
    spokenText: str = Field(min_length=1, max_length=2400)
    displayText: str = Field(min_length=1, max_length=4000)
    references: list[GroundingEvidence] = Field(default_factory=list, max_length=24)
    groundingLevel: GroundingLevel
    relatedCharacters: list[str] = Field(default_factory=list, max_length=24)
    relatedEvents: list[str] = Field(default_factory=list, max_length=24)
    warnings: list[str] = Field(default_factory=list, max_length=24)
    contentVersion: str = Field(min_length=1, max_length=40)
    contentSha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    contentReviewState: ReviewState
    speechApproved: bool = False

    @model_validator(mode="after")
    def enforce_release_contract(self) -> "DigitalHumanResponse":
        if self.groundingLevel == "G0_UNSUPPORTED" and self.answerType != "UNSUPPORTED":
            raise ValueError("G0 responses must use UNSUPPORTED answerType")
        if self.groundingLevel in {"G5_DIRECT_SCRIPTURE", "G4_STRONG_SCRIPTURAL_FACT"}:
            if not any(item.sourceType == "SCRIPTURE" for item in self.references):
                raise ValueError("high grounding requires scripture evidence")
        if self.speechApproved and self.contentReviewState != "APPROVED":
            raise ValueError("unapproved content cannot be spoken")
        if self.speechApproved and self.groundingLevel == "G0_UNSUPPORTED":
            raise ValueError("unsupported content cannot be spoken")
        return self


class DigitalHumanTopicContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterId: str = Field(pattern=r"^[a-z0-9_-]+$")
    topicIds: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("topicIds")
    @classmethod
    def validate_topic_ids(cls, values: list[str]) -> list[str]:
        import re
        if any(not re.fullmatch(r"[a-z0-9_-]{1,100}", value) for value in values):
            raise ValueError("invalid context topic identifier")
        return list(dict.fromkeys(values))


class DigitalHumanTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterId: str = Field(pattern=r"^[a-z0-9_-]+$")
    question: str = Field(min_length=1, max_length=1200)
    sessionId: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,80}$")
    turnId: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,80}$")
    context: DigitalHumanTopicContext | None = None

    @model_validator(mode="after")
    def enforce_context_character(self) -> "DigitalHumanTurnRequest":
        if self.context and self.context.characterId != self.characterId:
            raise ValueError("context belongs to another character")
        return self

    @field_validator("question")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
            raise ValueError("question contains control characters")
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped


class TurnEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sessionId: str
    turnId: str
    traceId: str
    state: Literal["READY_TO_SPEAK", "TEXT_ONLY", "BLOCKED"]
    response: DigitalHumanResponse
    latencyMs: float = Field(ge=0)


class AvatarProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["metaperson"] = "metaperson"
    modelUrl: str | None = None
    portraitUrl: str | None = None
    version: str
    framing: Literal["head", "bust", "full"] = "bust"
    reviewState: ReviewState


class VoiceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    voiceId: str | None = None
    language: str = "zh-CN"
    reviewState: ReviewState


class CharacterProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    canonicalName: str
    englishName: str
    status: Literal["alpha-ready", "review-required", "withdrawn"]
    catalogTier: Literal["deep-alpha", "standard-alpha"]
    catalogStatus: Literal["alpha-ready", "standard-alpha"]
    truthCaseCount: int = Field(ge=1)
    avatar: AvatarProfile
    voice: VoiceProfile
    recommendedQuestions: list[str]
    disclosure: str
    runtimeReady: bool


class DigitalHumanDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterId: str = Field(pattern=r"^[a-z0-9_-]+$")
    topicId: str = Field(pattern=r"^[a-z0-9_-]{1,100}$")


class LiveKitTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterId: str = Field(pattern=r"^[a-z0-9_-]+$")
    sessionId: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")


class IdentityResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surface: str = Field(min_length=1, max_length=80)
    explicitCharacterId: str | None = Field(default=None, pattern=r"^[a-z0-9_\-]+$")
    currentCharacterId: str | None = Field(default=None, pattern=r"^[a-z0-9_\-]+$")


class IdentityCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterId: str
    stableLabel: str
    englishName: str


class IdentityResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["RESOLVED", "AMBIGUOUS", "NOT_FOUND"]
    characterId: str | None = None
    stableLabel: str | None = None
    candidates: list[IdentityCandidate] = Field(default_factory=list)
    reasonCodes: list[str] = Field(default_factory=list)


class ProviderTelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["livekit", "livespeak"]
    state: Literal["READY", "ERROR", "DISCONNECTED", "RECOVERING", "FALLBACK"]
    latencyMs: float = Field(default=0, ge=0, le=300_000)
