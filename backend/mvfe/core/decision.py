"""
DECISION MODULE
Classifies decision patterns with probabilistic reasoning.
"""
import json
import logging
from dataclasses import dataclass, asdict
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class DecisionDrivers:
    fear: float  # 0.0-1.0
    ego: float  # 0.0-1.0
    love: float  # 0.0-1.0


@dataclass
class DecisionState:
    type: str  # "approach" | "avoidance"
    drivers: DecisionDrivers
    confidence: float  # 0.0-1.0


DECISION_EXTRACTION_PROMPT = """Analyze the decision-making pattern in the following text.
Classify whether the person is approaching something or avoiding something,
and estimate the probabilistic drivers behind their decision.

Return ONLY valid JSON:
{{
  "type": "approach" or "avoidance",
  "drivers": {{
    "fear": <float 0.0-1.0, how much fear drives this>,
    "ego": <float 0.0-1.0, how much ego/pride drives this>,
    "love": <float 0.0-1.0, how much love/care drives this>
  }},
  "confidence": <float 0.0-1.0, how confident you are in this classification>
}}

Rules:
- Do NOT assume determinism. People have mixed motives.
- "approach" = moving toward something
- "avoidance" = moving away from something
- drivers should sum to roughly 1.0 but don't have to be exact
- confidence < 0.5 means you're genuinely unsure

Text: "{text}"
"""


class DecisionClassifier:
    """Classifies decision patterns using LLM."""

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def extract(self, text: str) -> DecisionState:
        prompt = DECISION_EXTRACTION_PROMPT.format(text=text[:2000])
        try:
            raw = self._llm(prompt)
            data = _parse_json(raw)
            drivers_raw = data.get("drivers", {})
            return DecisionState(
                type=data.get("type", "avoidance") if data.get("type") in ("approach", "avoidance") else "avoidance",
                drivers=DecisionDrivers(
                    fear=_clamp(float(drivers_raw.get("fear", 0.4))),
                    ego=_clamp(float(drivers_raw.get("ego", 0.3))),
                    love=_clamp(float(drivers_raw.get("love", 0.3))),
                ),
                confidence=_clamp(float(data.get("confidence", 0.5))),
            )
        except Exception as e:
            logger.warning(f"[decision] extraction failed: {e}")
            return DecisionState(
                type="avoidance",
                drivers=DecisionDrivers(fear=0.5, ego=0.3, love=0.2),
                confidence=0.3,
            )

    def to_dict(self, state: DecisionState) -> dict:
        return asdict(state)


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
