"""Pydantic models and enums for the Batch 01 discernment core.

Every structure here is bound to a SKILL.md output contract and to the two
JSON Schemas shipped in ``schemas/``.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SubjectType(str, Enum):
    IDEA = "idea"
    PERSON = "person"
    EVENT = "event"
    PRODUCT = "product"
    MEDIA = "media"
    SELF_REFLECTION = "self_reflection"
    MIXED = "mixed"


class FaithContext(str, Enum):
    CHRISTIAN = "christian"
    SEEKER = "seeker"
    UNKNOWN = "unknown"
    OTHER = "other"


class Sensitivity(str, Enum):
    NORMAL = "normal"
    PASTORAL = "pastoral"
    MENTAL_HEALTH = "mental_health"
    ABUSE = "abuse"
    CRISIS = "crisis"


class EvidenceLevel(str, Enum):
    """E0-E4 evidence ladder from BATCH_01_IMPLEMENTATION section 5."""

    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"

    @property
    def rank(self) -> int:
        return int(self.value[1])

    @property
    def is_conclusive(self) -> bool:
        """E0-E2 may never be emitted as a conclusion."""
        return self.rank >= 3


class ClaimType(str, Enum):
    FACTUAL = "factual_claim"
    CAUSAL = "causal_claim"
    MORAL = "moral_claim"
    IDENTITY = "identity_claim"
    ANTHROPOLOGICAL = "anthropological_claim"
    SALVATION = "salvation_claim"
    ENEMY = "enemy_claim"
    ACTION_CALL = "action_call"
    EMOTIONAL = "emotional_signal"


class PrideSignal(str, Enum):
    """Taxonomy from BATCH_01_IMPLEMENTATION section 4."""

    EPISTEMIC_SUPERIORITY = "epistemic_superiority"
    MORAL_SELF_RIGHTEOUSNESS = "moral_self_righteousness"
    ACHIEVEMENT_JUSTIFICATION = "achievement_justification"
    AUTONOMY_ABSOLUTISM = "autonomy_absolutism"
    CONTROL_SOVEREIGNTY = "control_sovereignty"
    STATUS_GLORY = "status_glory"
    TRIBAL_SUPERIORITY = "tribal_superiority"
    VICTIMHOOD_INNOCENCE = "victimhood_innocence"
    SPIRITUAL_PRIDE = "spiritual_pride"
    CONTEMPT_FOR_WEAKNESS = "contempt_for_weakness"
    RESENTFUL_JUDGMENT = "resentful_judgment"
    MESSIANIC_SELF_IMAGE = "messianic_self_image"


class QuestionStage(str, Enum):
    """Ten socratic stages, ordered, from skill 06."""

    CLARIFY = "clarify"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"
    COUNTEREXAMPLE = "counterexample"
    CONSEQUENCE = "consequence"
    HEART = "heart"
    WORSHIP = "worship"
    LAW = "law"
    GOSPEL = "gospel"
    RESPONSE = "response"

    @property
    def order(self) -> int:
        return list(QuestionStage).index(self) + 1


class CaseState(str, Enum):
    RECEIVED = "RECEIVED"
    SAFETY_CHECKED = "SAFETY_CHECKED"
    NORMALIZED = "NORMALIZED"
    CLAIMS_EXTRACTED = "CLAIMS_EXTRACTED"
    WORLDVIEW_MAPPED = "WORLDVIEW_MAPPED"
    PRIDE_HYPOTHESES_BUILT = "PRIDE_HYPOTHESES_BUILT"
    DESIRES_MAPPED = "DESIRES_MAPPED"
    QUESTIONS_PLANNED = "QUESTIONS_PLANNED"
    GOSPEL_BRIDGE_BUILT = "GOSPEL_BRIDGE_BUILT"
    REPORT_COMPOSED = "REPORT_COMPOSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY = "READY"
    DELIVERED = "DELIVERED"


class FailureCode(str, Enum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HIGH_RISK_REVIEW = "HIGH_RISK_REVIEW"
    UNSUPPORTED_THEOLOGICAL_CLAIM = "UNSUPPORTED_THEOLOGICAL_CLAIM"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    USER_CONSENT_REQUIRED = "USER_CONSENT_REQUIRED"


class ReviewStatus(str, Enum):
    READY = "ready"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BLOCKED = "blocked"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return list(RiskLevel).index(self)


class SourceKind(str, Enum):
    """Skill 01 step 3: mark provenance of every text segment."""

    QUOTE = "quote"
    PARAPHRASE = "paraphrase"
    USER_COMMENT = "user_comment"
    SYSTEM_INFERENCE = "system_inference"


class ConsentScope(BaseModel):
    allow_spiritual_analysis: bool
    allow_gospel_bridge: bool
    allow_longitudinal_memory: bool = False


class DiscernmentCase(BaseModel):
    """Matches schemas/discernment_case.schema.json."""

    case_id: str
    subject_type: SubjectType
    raw_input: str = Field(min_length=1)
    user_goal: str
    consent_scope: ConsentScope
    source_metadata: dict = Field(default_factory=dict)
    faith_context: FaithContext = FaithContext.UNKNOWN
    sensitivity: Sensitivity = Sensitivity.NORMAL


class TextSegment(BaseModel):
    segment_id: str
    text: str
    source_kind: SourceKind
    start: int
    end: int


class NormalizedCase(BaseModel):
    """`DiscernmentCaseNormalized` referenced by skill 01's prompt contract."""

    case_id: str
    subject_type: SubjectType
    topic: str
    subject_description: str
    user_goal: str
    faith_context: FaithContext
    sensitivity: Sensitivity
    consent_scope: ConsentScope
    analyzed_object_segments: list[TextSegment] = Field(default_factory=list)
    user_reaction_segments: list[TextSegment] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    time_range: str = "unspecified"
    source_metadata: dict = Field(default_factory=dict)


class Claim(BaseModel):
    claim_id: str
    claim_type: ClaimType
    statement: str
    evidence_span: str = ""
    implicit: bool = False
    verifiable: bool = False
    confidence: float = 0.0
    rhetoric_discount: float = 0.0
    counter_evidence_needed: list[str] = Field(default_factory=list)
    externally_verified: bool = False

    @property
    def high_confidence(self) -> bool:
        return self.confidence >= 0.6 and bool(self.evidence_span)


class WorldviewLayer(BaseModel):
    creation_good: list[str] = Field(default_factory=list)
    fall_distortion: list[str] = Field(default_factory=list)
    redemption_substitute: list[str] = Field(default_factory=list)
    consummation_telos: list[str] = Field(default_factory=list)


class WorldviewMap(BaseModel):
    case_id: str
    steelman: str
    layers: WorldviewLayer
    seven_questions: dict = Field(default_factory=dict)
    common_grace_insights: list[str] = Field(default_factory=list)
    possible_correct_points: list[str] = Field(default_factory=list)
    potential_distortions: list[str] = Field(default_factory=list)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    sufficient_material: bool = True


class PrideHypothesis(BaseModel):
    hypothesis_id: str
    observation: str
    possible_pattern: PrideSignal
    interpretation_hypothesis: str
    evidence_level: EvidenceLevel
    alternative_explanations: list[str] = Field(default_factory=list)
    disconfirming_evidence_needed: list[str] = Field(default_factory=list)
    pastoral_risk: str = "low"
    pastoral_question: str = ""
    scope: str = "other"
    public_material_only: bool = True


class DesireChain(BaseModel):
    chain_id: str
    good_desire: str
    absolutized_desire: str
    functional_savior: str
    demanded_sacrifice: str
    enslaving_fruit: str
    loss_reaction: str
    structural_factors: list[str] = Field(default_factory=list)
    reanchoring_in_christ: str
    confidence: EvidenceLevel = EvidenceLevel.E2
    candidate: bool = False


class SocraticQuestion(BaseModel):
    question_id: str
    stage: QuestionStage
    order: int
    question: str
    purpose: str
    difficulty: int = 1
    expected_risk: str = "low"
    branch_conditions: dict = Field(default_factory=dict)
    requires_consent: bool = False
    presumes_guilt: bool = False


class GospelBridge(BaseModel):
    affirmed_good: str
    exposure: str
    law_mirror: str
    christ_person_and_work: str
    union_identity: str
    practice: str
    hope: str
    justification_sanctification_note: str
    scripture_anchors: list[str] = Field(default_factory=list)
    consent_granted: bool = True
    theologically_supported: bool = True


class SafetyDecision(BaseModel):
    stage: str
    risk_level: RiskLevel
    blocked_patterns: list[str] = Field(default_factory=list)
    required_rewrite: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    halt_normal_flow: bool = False
    support_guidance: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DiscernmentReport(BaseModel):
    """Matches schemas/discernment_report.schema.json."""

    case_id: str
    summary: str
    observed_claims: list[dict] = Field(default_factory=list)
    worldview_map: dict = Field(default_factory=dict)
    pride_hypotheses: list[dict] = Field(default_factory=list)
    desire_map: list[dict] = Field(default_factory=list)
    socratic_questions: list[dict] = Field(default_factory=list)
    gospel_bridge: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.READY
    affirmations: list[str] = Field(default_factory=list)
    self_mirror: list[str] = Field(default_factory=list)
    actionable_response: str = ""


class TraceRecord(BaseModel):
    trace_id: str
    case_id: str
    skill_id: str
    skill_version: str
    model: str = "deterministic"
    provider: str = "local"
    prompt_hash: str = ""
    input_hash: str = ""
    output_hash: str = ""
    structured_output: dict = Field(default_factory=dict)
    evidence_links: list[str] = Field(default_factory=list)
    safety_decisions: list[dict] = Field(default_factory=list)
    latency_ms: float = 0.0
    tokens: int = 0
    cost: float = 0.0
    human_overrides: list[dict] = Field(default_factory=list)
    policy_version: str = "0.1.0"


class TraceBundle(BaseModel):
    case_id: str
    records: list[TraceRecord] = Field(default_factory=list)
    production_ready: bool = False
    missing_skills: list[str] = Field(default_factory=list)


class SkillFailure(Exception):
    def __init__(self, code: FailureCode, message: str = "") -> None:
        self.code = code
        self.message = message or code.value
        super().__init__(self.message)
