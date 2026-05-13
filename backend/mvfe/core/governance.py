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
    }

    def audit(self, reflection_text: str, formation: dict) -> GovernanceReport:
        """Audit system output against constitutional constraints."""
        violations = []
        warnings = []

        # Check 1: Manipulation detection
        manipulative_words = ["should", "must", "need to", "have to", "try to", "you should", "start", "stop", "do this"]
        text_lower = reflection_text.lower()
        for word in manipulative_words:
            if word in text_lower:
                violations.append(f"manipulation_detected: '{word}' implies behavioral prescription")
                break

        # Check 2: Moral scoring
        moral_words = ["good person", "bad", "moral failure", "weakness", "strength", "virtue", "character flaw"]
        for word in moral_words:
            if word in text_lower:
                violations.append(f"moral_scoring: '{word}' assigns moral judgment")
                break

        # Check 3: Identity labeling
        identity_patterns = ["you are a", "you are an", "your personality is", "you are the type of"]
        for pattern in identity_patterns:
            if pattern in text_lower:
                violations.append(f"identity_labeling: '{pattern}' fixes personality")
                break

        # Check 4: Deterministic prediction
        deterministic_words = ["will lead to", "will result in", "inevitably", "definitely", "always", "you will"]
        for word in deterministic_words:
            if word in text_lower:
                warnings.append(f"deterministic_language: '{word}' overstates predictability")
                break

        # Check 5: Formation danger — if drift_score is high but system is treating it as certainty
        formation_danger = False
        drift = formation.get("drift_score", 0)
        if drift > 0.5 and "definitely" in text_lower:
            violations.append("formation_danger: high drift with deterministic language")
            formation_danger = True

        passed = len(violations) == 0
        if not passed:
            logger.warning(f"[governance] {len(violations)} violations, {len(warnings)} warnings")

        return GovernanceReport(
            passed=passed,
            violations=violations,
            warnings=warnings,
            formation_danger_flag=formation_danger,
        )

    def sanitize(self, reflection_text: str, report: GovernanceReport) -> str:
        """If violations found, prepend governance notice and soften language."""
        if report.passed:
            return reflection_text

        notice = "[SYSTEM NOTE: The following is an observational reading only. It does not prescribe behavior, assign moral judgment, or fix personality traits. Multiple interpretations are always possible.]\n\n"
        return notice + reflection_text
