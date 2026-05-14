"""
ATTENTION MODULE
Detects attention anchoring, fixation, and drift risk.
"""
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AttentionState:
    focus: str  # what the user is fixated on
    fixation_score: float  # 0.0-1.0, how fixated
    drift_risk: float  # 0.0-1.0, likelihood of repetitive loop
    anchor_object: str  # the specific thing anchoring attention


ATTENTION_EXTRACTION_PROMPT = """Analyze the attentional content of the following text.
Determine what the person is focused on, how fixated they are, and whether this represents a repetitive loop.

Return ONLY valid JSON:
{
  "focus": "<what the person is mentally focused on>",
  "fixation_score": <float 0.0-1.0, how fixated/obsessed>,
  "drift_risk": <float 0.0-1.0, probability this is a repetitive thought loop>,
  "anchor_object": "<the specific thing/person/event anchoring attention>"
}

Rules:
- fixation_score: 0.0 = casual mention, 1.0 = complete obsession
- drift_risk: 0.0 = healthy processing, 1.0 = trapped in loop
- anchor_object: concrete noun or situation

Text: "{text}"
"""


class AttentionExtractor:
    """Extracts attention state from text using LLM."""

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def extract(self, text: str) -> AttentionState:
        prompt = ATTENTION_EXTRACTION_PROMPT.format(text=text[:2000])
        try:
            raw = self._llm(prompt)
            data = _parse_json(raw)
            return AttentionState(
                focus=str(data.get("focus", "unknown")),
                fixation_score=_clamp(float(data.get("fixation_score", 0.5))),
                drift_risk=_clamp(float(data.get("drift_risk", 0.3))),
                anchor_object=str(data.get("anchor_object", "unknown")),
            )
        except Exception as e:
            logger.warning(f"[attention] extraction failed: {e}")
            return AttentionState(
                focus="unknown",
                fixation_score=0.5,
                drift_risk=0.3,
                anchor_object="unknown",
            )

    def to_dict(self, state: AttentionState) -> dict:
        return asdict(state)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


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
        raise ValueError(f"[attention] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
