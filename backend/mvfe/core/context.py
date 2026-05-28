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


CONTEXT_EXTRACTION_PROMPT = """分析以下文本，提取此人的处境框架。
这不是关于情绪的，而是关于其人生处境、阶段和位置的。

只返回合法的 JSON：
{
  "life_stage": "<人生阶段标签，必须从下方枚举值中选择>",
  "situational_background": "<用中文描述其处境，2句话>",
  "identity_anchors": ["<角色1>", "<角色2>", "<角色3>"],
  "relationship_context": "<用中文描述关系状态，一句话>",
  "temporal_urgency": <float 0.0-1.0>
}

规则：
- life_stage 必须是以下英文枚举值之一：[early_career, mid_career, late_career, midlife_transition, retirement, student, caregiving, searching, unknown]
- situational_background: 客观描述，不做主观解读，用中文
- identity_anchors: 此人认同的角色，用中文（如 父母、专业人士、照护者 等）
- relationship_context: 简要关系状态描述，用中文
- temporal_urgency: 0.0 = 无时间压力，1.0 = 极度紧迫

文本："{text}"
"""


class ContextExtractor:
    """Extracts contextual frame from user text."""

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def extract(self, text: str) -> ContextFrame:
        prompt = CONTEXT_EXTRACTION_PROMPT.replace('{text}', text[:2000])
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
        # Fallback: json5 handles trailing commas, unquoted keys, comments, etc.
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
        raise ValueError(f"[context] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
