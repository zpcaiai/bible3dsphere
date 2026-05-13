"""
CONTEXT EXTRACTOR (HIDOS Input Layer)
Frames user input with life stage, situational background, and identity anchors.
"""
import json
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ContextFrame:
    life_stage: str  # e.g., "early career", "midlife transition", "retirement"
    situational_background: str  # what situation the person is in
    identity_anchors: list[str]  # what the person sees themselves as
    relationship_context: str  # relational state
    temporal_urgency: float  # 0.0-1.0, how time-pressured


CONTEXT_EXTRACTION_PROMPT = """Analyze the following text and extract the person's contextual frame.
This is NOT about emotions — it's about their LIFE SITUATION, STAGE, and POSITION.

Return ONLY valid JSON:
{
  "life_stage": "<brief life stage label>",
  "situational_background": "<2-sentence description of their situation>",
  "identity_anchors": ["<role1>", "<role2>", "<role3>"],
  "relationship_context": "<single sentence about relational state>",
  "temporal_urgency": <float 0.0-1.0>
}

Rules:
- life_stage: one of [early_career, mid_career, late_career, midlife_transition, retirement, student, caregiving, searching, unknown]
- situational_background: objective description, no interpretation
- identity_anchors: roles they identify with (parent, professional, caregiver, etc.)
- relationship_context: brief relational state description
- temporal_urgency: 0.0 = no time pressure, 1.0 = extreme urgency

Text: "{text}"
"""


class ContextExtractor:
    """Extracts contextual frame from user text."""

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def extract(self, text: str) -> ContextFrame:
        prompt = CONTEXT_EXTRACTION_PROMPT.format(text=text[:2000])
        try:
            raw = self._llm(prompt)
            data = _parse_json(raw)
            return ContextFrame(
                life_stage=str(data.get("life_stage", "unknown")),
                situational_background=str(data.get("situational_background", "")),
                identity_anchors=data.get("identity_anchors", [])[:4],
                relationship_context=str(data.get("relationship_context", "")),
                temporal_urgency=_clamp(float(data.get("temporal_urgency", 0.5))),
            )
        except Exception as e:
            logger.warning(f"[context] extraction failed: {e}")
            return ContextFrame(
                life_stage="unknown",
                situational_background="",
                identity_anchors=[],
                relationship_context="",
                temporal_urgency=0.5,
            )

    def to_dict(self, frame: ContextFrame) -> dict:
        return asdict(frame)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]
    return json.loads(raw)
