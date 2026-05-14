"""
EMOTION MODULE
Extracts structured emotional state from user text input.
"""
import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmotionState:
    primary_emotion: str
    intensity: float  # 0.0 - 1.0
    secondary_emotions: List[str]
    uncertainty: float  # 0.0 - 1.0, how uncertain the extraction is


EMOTION_EXTRACTION_PROMPT = """Analyze the emotional content of the following text.
Return ONLY valid JSON with this exact structure:
{
  "primary_emotion": "<the dominant emotion>",
  "intensity": <float 0.0-1.0>,
  "secondary_emotions": ["<emotion1>", "<emotion2>"],
  "uncertainty": <float 0.0-1.0, how uncertain you are>
}

Rules:
- primary_emotion: one of [joy, sadness, anger, fear, disgust, surprise, love, shame, guilt, anxiety, peace, hope, despair, gratitude, envy, loneliness]
- intensity: 0.0 = barely present, 1.0 = overwhelming
- secondary_emotions: up to 3 additional emotions detected
- uncertainty: 0.0 = very confident, 1.0 = highly uncertain

Text: "{text}"
"""


class EmotionExtractor:
    """Extracts emotion state from text using LLM."""

    def __init__(self, llm_fn):
        """
        Args:
            llm_fn: callable(prompt: str) -> str — LLM inference function
        """
        self._llm = llm_fn

    def extract(self, text: str) -> EmotionState:
        """Extract emotional state from input text."""
        prompt = EMOTION_EXTRACTION_PROMPT.replace('{text}', text[:2000])
        try:
            raw = self._llm(prompt)
            data = _parse_json(raw)
            return EmotionState(
                primary_emotion=str(data.get("primary_emotion", "unknown")),
                intensity=_clamp(float(data.get("intensity", 0.5))),
                secondary_emotions=data.get("secondary_emotions", [])[:3],
                uncertainty=_clamp(float(data.get("uncertainty", 0.5))),
            )
        except Exception as e:
            logger.warning(f"[emotion] extraction failed: {e}")
            return EmotionState(
                primary_emotion="unknown",
                intensity=0.5,
                secondary_emotions=[],
                uncertainty=1.0,
            )

    def to_dict(self, state: EmotionState) -> dict:
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
        try:
            import json5
            return json5.loads(candidate)
        except Exception:
            pass
    # Fallback: try parsing the full raw string
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        import json5
        return json5.loads(raw)
    except Exception as e:
        raise ValueError(f"[emotion] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
