"""
llm_schemas.py — Advanced Batch · Module 1
Strict Pydantic (v2) output schemas for every structured agent.

Every real LLM call that must return structured data is validated against one
of these models by ``llm_provider.generate_json``. Validation failure triggers
exactly one retry; a second failure is logged to ``agent_runs.status='FAILED'``.

Keep these models import-light (pydantic + stdlib only) so they can be unit
tested with ``-m no_db`` without the FastAPI app or a database.
"""
from __future__ import annotations

from typing import List, Literal, Optional

try:
    from pydantic import BaseModel, Field
except Exception as exc:  # pragma: no cover
    raise RuntimeError("pydantic is required for llm_schemas") from exc

RiskLevel = Literal["low", "medium", "high", "critical"]


# ── Spiritual Diagnosis Agent ───────────────────────────────────────────────
class DiagnosisFinding(BaseModel):
    category: str
    finding_type: str
    title: str
    description: str
    severity: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)
    possible_root: Optional[str] = None
    gospel_truth: Optional[str] = None
    scripture_anchors: List[str] = Field(default_factory=list)
    recommended_practice_types: List[str] = Field(default_factory=list)
    recommended_community_action: Optional[str] = None
    requires_pastor_attention: bool = False
    risk_level: RiskLevel = "low"


class DiagnosisAgentOutput(BaseModel):
    primary_theme: str
    risk_level: RiskLevel
    summary: str
    findings: List[DiagnosisFinding] = Field(default_factory=list)


# ── Worldview Formation Agent ───────────────────────────────────────────────
class WorldviewBeliefFinding(BaseModel):
    dimension_code: str
    expressed_belief: str
    belief_type: Literal["explicit", "implicit"] = "implicit"
    distortion_type: Optional[str] = None
    biblical_counter_truth: Optional[str] = None
    scripture_anchors: List[str] = Field(default_factory=list)
    evidence: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    recommended_practices: List[str] = Field(default_factory=list)


class WorldviewAgentOutput(BaseModel):
    summary: str
    dominant_distortions: List[str] = Field(default_factory=list)
    renewal_focus: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = "low"
    findings: List[WorldviewBeliefFinding] = Field(default_factory=list)


# ── Gifts & Calling Agent ───────────────────────────────────────────────────
class GiftFinding(BaseModel):
    name: str
    evidence: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0, le=1)


class CallingPattern(BaseModel):
    burden_area: str
    possible_calling: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0, le=1)


class MinistryMatch(BaseModel):
    ministry_area: str
    match_reason: str
    suggested_first_step: Optional[str] = None
    risk_notes: Optional[str] = None


class CallingExperiment(BaseModel):
    title: str
    hypothesis: str
    ministry_area: str
    expected_fruit: List[str] = Field(default_factory=list)


class GiftCallingAgentOutput(BaseModel):
    summary: str
    dominant_gifts: List[GiftFinding] = Field(default_factory=list)
    secondary_gifts: List[GiftFinding] = Field(default_factory=list)
    growth_edges: List[str] = Field(default_factory=list)
    misuse_risks: List[str] = Field(default_factory=list)
    calling_patterns: List[CallingPattern] = Field(default_factory=list)
    ministry_matches: List[MinistryMatch] = Field(default_factory=list)
    calling_experiments: List[CallingExperiment] = Field(default_factory=list)


# ── Suffering Theology & Care Agent ─────────────────────────────────────────
class SufferingCarePlanBlock(BaseModel):
    title: str
    scripture_path: List[str] = Field(default_factory=list)
    prayer_path: List[str] = Field(default_factory=list)
    community_actions: List[str] = Field(default_factory=list)
    duration_days: int = 14


class SufferingAgentOutput(BaseModel):
    case_type: str
    risk_level: RiskLevel
    suffering_stage: Optional[str] = None
    theological_theme: Optional[str] = None
    summary: str
    lament_needed: bool = False
    community_support_needed: bool = False
    professional_help_recommended: bool = False
    scripture_anchors: List[str] = Field(default_factory=list)
    guided_prayer: Optional[str] = None
    # When risk is high/critical the agent MUST name real-human next steps.
    real_person_actions: List[str] = Field(default_factory=list)
    care_plan: Optional[SufferingCarePlanBlock] = None


SCHEMA_REGISTRY = {
    "DiagnosisAgentOutput": DiagnosisAgentOutput,
    "WorldviewAgentOutput": WorldviewAgentOutput,
    "GiftCallingAgentOutput": GiftCallingAgentOutput,
    "SufferingAgentOutput": SufferingAgentOutput,
}
