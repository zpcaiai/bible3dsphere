"""
CRITIC AGENT (HIDOS Multi-Agent Layer)
Challenges system output to detect false coherence, overfitting, and illusion of understanding.
"""
import json
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CriticReport:
    coherence_score: float  # 0.0-1.0, how internally consistent
    overfit_risk: float  # 0.0-1.0, how much pattern was forced onto noise
    alternative_hypotheses: list[str]  # other possible interpretations
    challenge_summary: str  # what the critic disagrees with
    confidence_adjustment: float  # -0.3 to +0.1, how much to adjust system confidence


CRITIC_PROMPT = """你是一位对抗性评估者，正在审查一个心理状态解读系统。
你的任务：找出系统出错、过拟合或错误假设的地方。

用户输入："{input_text}"

系统反思："{reflection_text}"

系统状态：
- 情绪：{primary_emotion}（强度 {intensity}）
- 注意力：{focus}（固化程度 {fixation_score}）
- 决策：{decision_type}（恐惧={fear}，自我={ego}，爱={love}）
- 形成度评分：{formation_score}
- 漂移评分：{drift_score}

评估规则：
1. 寻找"虚假连贯性"——系统构建了一个看似合理但实际上不符合数据的叙事
2. 检查系统是否过度解读了模糊性
3. 提出 2-3 个系统遗漏的替代性解读
4. 评估你对系统判断的信心程度（0-1）
5. 给出信心调整值（-0.3 到 +0.1）

只返回合法的 JSON：
{{
  "coherence_score": <float 0.0-1.0>,
  "overfit_risk": <float 0.0-1.0>,
  "alternative_hypotheses": ["<替代解读1>", "<替代解读2>", "<替代解读3>"],
  "challenge_summary": "<评估者具体不同意的观点，用中文>",
  "confidence_adjustment": <float -0.3 to +0.1>
}}
"""


class CriticAgent:
    """
    Adversarial reviewer that prevents the system from falling into
    'illusion of understanding' — pattern matching that looks coherent but is wrong.
    """

    def __init__(self, llm_fn):
        self._llm = llm_fn

    def challenge(
        self,
        input_text: str,
        reflection_text: str,
        emotion: dict,
        attention: dict,
        decision: dict,
        formation: dict,
    ) -> CriticReport:
        prompt = CRITIC_PROMPT.format(
            input_text=input_text[:500],
            reflection_text=reflection_text[:800],
            primary_emotion=emotion.get("primary_emotion", "unknown"),
            intensity=emotion.get("intensity", 0.5),
            focus=attention.get("focus", "unknown"),
            fixation_score=attention.get("fixation_score", 0.5),
            decision_type=decision.get("type", "avoidance"),
            fear=decision.get("drivers", {}).get("fear", 0.5),
            ego=decision.get("drivers", {}).get("ego", 0.3),
            love=decision.get("drivers", {}).get("love", 0.2),
            formation_score=formation.get("formation_score", 0.5),
            drift_score=formation.get("drift_score", 0.3),
        )
        try:
            raw = self._llm(prompt)
            data = _parse_json(raw)
            return CriticReport(
                coherence_score=_clamp(float(data.get("coherence_score", 0.5))),
                overfit_risk=_clamp(float(data.get("overfit_risk", 0.3))),
                alternative_hypotheses=data.get("alternative_hypotheses", [])[:3],
                challenge_summary=data.get("challenge_summary", "无具体不同意见。"),
                confidence_adjustment=max(-0.3, min(0.1, float(data.get("confidence_adjustment", 0.0)))),
            )
        except Exception as e:
            logger.warning(f"[critic] challenge failed: {e}")
            return CriticReport(
                coherence_score=0.5,
                overfit_risk=0.5,
                alternative_hypotheses=["无法生成替代解读。"],
                challenge_summary="评估系统暂时不可用。",
                confidence_adjustment=0.0,
            )

    def adjust_confidence(self, base_confidence: float, critic: CriticReport) -> float:
        """Apply critic's confidence adjustment to base system confidence."""
        adjusted = base_confidence + critic.confidence_adjustment
        if critic.overfit_risk > 0.6:
            adjusted -= 0.1
        if not critic.alternative_hypotheses:
            adjusted -= 0.05
        return _clamp(adjusted)

    def to_dict(self, report: CriticReport) -> dict:
        return asdict(report)


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
        raise ValueError(f"[critic] JSON parse failed: {e} | raw[:200]={raw[:200]!r}") from e
