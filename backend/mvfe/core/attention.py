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


ATTENTION_EXTRACTION_PROMPT = """分析以下文本的注意力内容。
判断此人当前注意力集中在什么上面，固化程度如何，以及是否代表一种重复性思维回路。

只返回合法的 JSON：
{
  "focus": "<此人当前注意力所聚焦的事物，用中文描述>",
  "fixation_score": <float 0.0-1.0，固化/执着的程度>,
  "drift_risk": <float 0.0-1.0，这是重复性思维回路的概率>,
  "anchor_object": "<具体锚定注意力的人、事、物，用中文描述>"
}

规则：
- fixation_score: 0.0 = 随口一提，1.0 = 完全沉迷
- drift_risk: 0.0 = 健康处理中，1.0 = 被困在回路里
- focus 和 anchor_object 必须用中文回答

文本："{text}"
"""


class AttentionExtractor:
    """Extracts attention state from text using LLM."""

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def extract(self, text: str) -> AttentionState:
        prompt = ATTENTION_EXTRACTION_PROMPT.replace('{text}', text[:2000])
        try:
            raw = self._llm(prompt)
            data = _parse_json(raw)
            return AttentionState(
                focus=str(data.get("focus", "未知")),
                fixation_score=_clamp(float(data.get("fixation_score", 0.5))),
                drift_risk=_clamp(float(data.get("drift_risk", 0.3))),
                anchor_object=str(data.get("anchor_object", "未知")),
            )
        except Exception as e:
            logger.warning(f"[attention] extraction failed: {e}")
            return AttentionState(
                focus="未知",
                fixation_score=0.5,
                drift_risk=0.3,
                anchor_object="未知",
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
        raise ValueError(f"[attention] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
