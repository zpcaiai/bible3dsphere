"""
GOVERNANCE / CONSTITUTION LAYER (HIDOS Layer 5)
Hard safety constraints — NOT content filtering, but structural governance.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class GovernanceReport:
    passed: bool
    violations: List[str]
    warnings: List[str]
    formation_danger_flag: bool  # if system is drifting into deterministic modeling
    categories: Dict[str, List[str]]
    risk_level: str


class ConstitutionLayer:
    """
    Three hard constraints:
    1. No behavioral manipulation
    2. No single personality path enforcement
    3. No moral scoring
    """

    CONSTRAINTS = {
        "no_manipulation": "System must not include prescriptive advice, behavioral nudges, or action recommendations",
        "no_single_path": "System must preserve ambiguity and allow multiple interpretations of the same state",
        "no_moral_scoring": "System must not assign moral grades, virtue scores, or character rankings",
        "probabilistic_only": "All statements must use probabilistic framing (may, might, appears, suggests)",
        "trajectory_not_identity": "System describes trajectory signals, never fixed personality labels",
        "no_divine_certainty": "System must not claim direct divine speech, certainty, or authority over a user's decision",
    }

    MANIPULATIVE_TERMS = [
        "should", "must", "need to", "have to", "try to", "you should", "start", "stop", "do this",
        "你应该", "你必须", "你需要", "一定要", "马上去", "立刻去", "停止", "照着做",
    ]
    MORAL_SCORING_TERMS = [
        "good person", "bad", "moral failure", "weakness", "strength", "virtue", "character flaw",
        "好基督徒", "坏基督徒", "属灵失败", "道德失败", "软弱的人", "品格缺陷", "不够属灵",
    ]
    IDENTITY_PATTERNS = [
        "you are a", "you are an", "your personality is", "you are the type of",
        "你就是一个", "你是那种", "你的性格就是", "你这个人就是",
    ]
    DETERMINISTIC_TERMS = [
        "will lead to", "will result in", "inevitably", "definitely", "always", "you will",
        "必然导致", "一定会", "绝对会", "永远都会", "你将会", "肯定会",
    ]
    DIVINE_CERTAINTY_TERMS = [
        "god told me", "god says you must", "this is god's will", "the lord requires you to",
        "神告诉我", "神说你必须", "这是神的旨意", "主要求你", "圣灵明确说",
    ]

    def _find_first(self, text_lower: str, terms: list[str]) -> str | None:
        for term in terms:
            if term.lower() in text_lower:
                return term
        return None

    def audit(self, reflection_text: str, formation: dict) -> GovernanceReport:
        """Audit system output against constitutional constraints."""
        violations = []
        warnings = []
        categories: Dict[str, List[str]] = {}

        def add_violation(category: str, message: str) -> None:
            violations.append(message)
            categories.setdefault(category, []).append(message)

        def add_warning(category: str, message: str) -> None:
            warnings.append(message)
            categories.setdefault(category, []).append(message)

        # Check 1: Manipulation detection
        text_lower = reflection_text.lower()
        word = self._find_first(text_lower, self.MANIPULATIVE_TERMS)
        if word:
            add_violation("manipulation", f"manipulation_detected: '{word}' implies behavioral prescription")

        # Check 2: Moral scoring
        word = self._find_first(text_lower, self.MORAL_SCORING_TERMS)
        if word:
            add_violation("moral_scoring", f"moral_scoring: '{word}' assigns moral judgment")

        # Check 3: Identity labeling
        pattern = self._find_first(text_lower, self.IDENTITY_PATTERNS)
        if pattern:
            add_violation("identity_labeling", f"identity_labeling: '{pattern}' fixes personality")

        # Check 4: Deterministic prediction
        word = self._find_first(text_lower, self.DETERMINISTIC_TERMS)
        if word:
            add_warning("deterministic_language", f"deterministic_language: '{word}' overstates predictability")

        # Check 5: Divine certainty
        word = self._find_first(text_lower, self.DIVINE_CERTAINTY_TERMS)
        if word:
            add_violation("divine_certainty", f"divine_certainty: '{word}' claims unwarranted spiritual authority")

        # Check 6: Formation danger — if drift_score is high but system is treating it as certainty
        formation_danger = False
        drift = formation.get("drift_score", 0)
        if drift > 0.5 and categories.get("deterministic_language"):
            add_violation("formation_danger", "formation_danger: high drift with deterministic language")
            formation_danger = True

        passed = len(violations) == 0
        risk_level = "high" if formation_danger or len(violations) >= 2 else "medium" if violations else "low"
        if not passed:
            logger.warning(f"[governance] {len(violations)} violations, {len(warnings)} warnings")

        return GovernanceReport(
            passed=passed,
            violations=violations,
            warnings=warnings,
            formation_danger_flag=formation_danger,
            categories=categories,
            risk_level=risk_level,
        )

    def sanitize(self, reflection_text: str, report: GovernanceReport) -> str:
        """If violations found, prepend governance notice and soften language."""
        if report.passed:
            return reflection_text

        notice = (
            "[SYSTEM NOTE: The following is an observational reading only. It does not prescribe behavior, "
            "assign moral judgment, claim divine certainty, or fix personality traits. Multiple interpretations "
            "are always possible.]\n\n"
        )
        softened = reflection_text
        replacements = {
            "you should": "one possible invitation is to",
            "must": "may consider",
            "have to": "may consider",
            "你应该": "也许可以留意",
            "你必须": "也许可以考虑",
            "一定要": "可以谨慎考虑是否",
            "这是神的旨意": "这可能需要在祷告和群体中继续分辨",
            "神说你必须": "不要把这个理解为直接命令；可以继续分辨是否",
        }
        for source, target in replacements.items():
            softened = softened.replace(source, target)
        return notice + softened
