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
    bible_verse_hint: str
    disclaimer: str


REFLECTION_PROMPT = """你是一位不带评判的人格形成动态观察者。
根据以下提取的心理状态，生成一份反思性解读。

严格规则：
- 绝不进行道德评判
- 绝不贴人格类型标签
- 绝不确定性预测人生结果
- 始终保留模糊性
- 始终允许多种解读并存
- 使用"似乎..."、"一种可能是..."、"这可能暗示..."等语言

状态数据：
- 主要情绪：{primary_emotion}（强度：{intensity}）
- 次要情绪：{secondary_emotions}
- 注意力焦点：{focus}（固化程度：{fixation_score}）
- 漂移风险：{drift_risk}
- 决策模式：{decision_type}（恐惧={fear}，自我={ego}，爱={love}）
- 形成度评分：{formation_score}
- 漂移评分：{drift_score}
- 稳定性：{stability_score}

只返回合法的 JSON：
{{
  "state_interpretation": "<2-3句话解读当前内在状态>",
  "loop_detection": "<是否检测到重复性思维/行为回路，如有请描述>",
  "risk_assessment": "<观察到的风险：情绪耗竭、固化、回避模式等>",
  "reflective_question": "<一个温柔邀请人在神同在中自我觉察的问题。问题要自然引导用户联想到耶稣的应许——祂的圣洁公义、慈爱怜悯、安慰、信实等属性。例如：当那种'被忽视'的感觉浮现时，如果无需向任何人解释或证明什么，你能否在心里听到祂说'我从不丢弃你'——那一刻你最渴望在祂里面安息的是什么？>",
  "bible_verse_hint": "<一节与当前处境最相关的圣经经文，包含书卷、章节和简短经文内容，作为耶稣应许的锚点。例如：来13:5-6 '我总不撇下你，也不丢弃你。'>"
}}
"""


class ReflectionGenerator:
    """Generates reflective output from formation state."""

    DISCLAIMER = (
        "本反思仅具观察性质，不构成心理诊断、人格评估或行为处方。"
        "系统绝不以以下目标进行优化：人类行为改变、情绪结果优化、人格状态改善或行为合规率。"
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
            secondary_emotions=", ".join(emotion.secondary_emotions) or "无",
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
                state_interpretation=data.get("state_interpretation", "无法解读当前状态。"),
                loop_detection=data.get("loop_detection", "未检测到明显回路。"),
                risk_assessment=data.get("risk_assessment", "数据不足以评估风险。"),
                reflective_question=data.get("reflective_question", "此刻，什么在你里面最活跃？"),
                bible_verse_hint=data.get("bible_verse_hint", ""),
                disclaimer=self.DISCLAIMER,
            )
        except Exception as e:
            logger.warning(f"[reflection] generation failed: {e}")
            return ReflectionOutput(
                state_interpretation="正在处理状态数据...",
                loop_detection="数据不足以检测回路。",
                risk_assessment="暂时无法评估风险。",
                reflective_question="此刻，你注意到自己什么？",
                bible_verse_hint="",
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
        raise ValueError(f"[reflection] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
