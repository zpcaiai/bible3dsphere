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


DECISION_EXTRACTION_PROMPT = """分析以下文本中的决策模式。
分辨此人是在“趋向”某物还是在“回避”某物，并评估其决策背后的概率性动机。

只返回合法的 JSON：
{{
  "type": "approach" 或 "avoidance",
  "drivers": {{
    "fear": <float 0.0-1.0，恐惧驱动的程度>,
    "ego": <float 0.0-1.0，自我/骄傲驱动的程度>,
    "love": <float 0.0-1.0，爱/关怀驱动的程度>
  }},
  "confidence": <float 0.0-1.0，分类的信心程度>
}}

规则：
- 不要预设确定性。人的动机通常是混合的。
- "approach" = 趋向、靠近、积极面对
- "avoidance" = 回避、远离、消极应对
- 动机评分(drivers)总和应大致为 1.0，但不要求完全精确。
- 信心程度(confidence) < 0.5 表示你确实不确定。

文本："{text}"
"""


class DecisionClassifier:
    """Classifies decision patterns using LLM."""

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def extract(self, text: str) -> DecisionState:
        prompt = DECISION_EXTRACTION_PROMPT.replace('{text}', text[:2000])
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
        raise ValueError(f"[decision] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
