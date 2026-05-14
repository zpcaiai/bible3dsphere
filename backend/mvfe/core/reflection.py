"""
REFLECTION ENGINE
Generates interpretive, non-deterministic reflection.
Avoids moral judgment and personality labeling.
"""
import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional

from .emotion import EmotionState
from .attention import AttentionState
from .decision import DecisionState
from .formation import FormationResult

logger = logging.getLogger(__name__)


@dataclass
class ReflectionOutput:
    state_interpretation: str
    loop_detection: str  # narrative of detected loops
    risk_assessment: str
    reflective_question: str
    disclaimer: str


REFLECTION_PROMPT = """You are a non-judgmental human formation dynamics observer.
Given the following extracted psychological state, generate a reflective interpretation.

STRICT RULES:
- NEVER assign moral judgments
- NEVER label personality types
- NEVER predict life outcomes deterministically
- ALWAYS preserve ambiguity
- ALWAYS allow multiple interpretations
- Use language like "It appears...", "One possibility is...", "This might suggest..."

STATE DATA:
- Primary Emotion: {primary_emotion} (intensity: {intensity})
- Secondary Emotions: {secondary_emotions}
- Attention Focus: {focus} (fixation: {fixation_score})
- Drift Risk: {drift_risk}
- Decision Pattern: {decision_type} (fear={fear}, ego={ego}, love={love})
- Formation Score: {formation_score}
- Drift Score: {drift_score}
- Stability: {stability_score}

Return ONLY valid JSON:
{{
  "state_interpretation": "<2-3 sentence interpretation of current internal state>",
  "loop_detection": "<whether a repetitive thought/behavior loop is detected, describe it>",
  "risk_assessment": "<any risks observed: emotional exhaustion, fixation, avoidance patterns>",
  "reflective_question": "<one question to help the person gain self-awareness, without advice>"
}}
"""


class ReflectionGenerator:
    """Generates reflective output from formation state."""

    DISCLAIMER = (
        "This reflection is observational only. It does NOT constitute psychological diagnosis, "
        "personality assessment, or behavioral prescription. The system NEVER optimizes for: "
        "human behavior change, emotional outcome optimization, personality state improvement, "
        "or behavioral compliance rate."
    )

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def generate(
        self,
        emotion: EmotionState,
        attention: AttentionState,
        decision: DecisionState,
        formation: FormationResult,
    ) -> ReflectionOutput:
        prompt = REFLECTION_PROMPT.format(
            primary_emotion=emotion.primary_emotion,
            intensity=emotion.intensity,
            secondary_emotions=", ".join(emotion.secondary_emotions) or "none",
            focus=attention.focus,
            fixation_score=attention.fixation_score,
            drift_risk=attention.drift_risk,
            decision_type=decision.type,
            fear=decision.drivers.fear,
            ego=decision.drivers.ego,
            love=decision.drivers.love,
            formation_score=formation.formation_score,
            drift_score=formation.drift_score,
            stability_score=formation.stability_score,
        )
        try:
            raw = self._llm(prompt)
            data = _parse_json(raw)
            return ReflectionOutput(
                state_interpretation=data.get("state_interpretation", "Unable to interpret."),
                loop_detection=data.get("loop_detection", "No clear loop detected."),
                risk_assessment=data.get("risk_assessment", "Insufficient data for risk assessment."),
                reflective_question=data.get("reflective_question", "What is most alive in you right now?"),
                disclaimer=self.DISCLAIMER,
            )
        except Exception as e:
            logger.warning(f"[reflection] generation failed: {e}")
            return ReflectionOutput(
                state_interpretation="Processing state data...",
                loop_detection="Insufficient data for loop detection.",
                risk_assessment="Unable to assess risk at this time.",
                reflective_question="What are you noticing about yourself right now?",
                disclaimer=self.DISCLAIMER,
            )

    def to_dict(self, output: ReflectionOutput) -> dict:
        return asdict(output)


def _parse_json(raw: str) -> dict:
    """Robust JSON extraction — handles markdown fences, bare JSON, and edge cases."""
    raw = raw.strip()
    # Strip markdown code fences
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    raw = raw.strip()
    # Try to extract a JSON object by finding first { and last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end >= start:
        candidate = raw[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    # Fallback: try parsing the full raw string
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"[reflection] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
