"""
SFDS v3.7 — HIDOS Safety Constitution

=================================================================
PURPOSE:
  This module defines and enforces the 15 immutable governance
  articles for all HIDOS system components.

  The Constitution exists to ensure that as the system becomes
  more capable, it does NOT become controlling, deterministic,
  or authoritarian.

  The Constitution is NOT configurable.
  The Constitution is NOT overridable by any subsystem.
  The Constitution is checked at runtime on every output.

=================================================================
IMMUTABLE ARTICLES (cannot be modified at runtime):

  Art. 1  — Human Autonomy        : user is always final authority
  Art. 2  — Non-Identity          : no fixed personality labels
  Art. 3  — Non-Determinism       : no deterministic predictions
  Art. 4  — Non-Moral Authority   : no moral judgment or ranking
  Art. 5  — Transparency          : reasoning must be explainable
  Art. 6  — Minimum Intervention  : reflective > suggestive > directive
  Art. 7  — Loop Safety           : loops = structures, not identity flaws
  Art. 8  — Formation Safety      : no scoring of human worth
  Art. 9  — Self-Improvement Limit: only system-level improvements
  Art. 10 — Boundary Principle    : never replaces human agency
  Art. 11 — Error Handling        : high uncertainty → explicit uncertainty
  Art. 12 — Ethical Gradient      : awareness > reflection > suggestion > guidance
  Art. 13 — Non-Manipulation      : no persuasion, no guilt/fear exploitation
  Art. 14 — Long-Term Alignment   : evolves toward clarity and agency, not compliance
  Art. 15 — Final Governance      : any violation → output rejected in orchestration

=================================================================
RUNTIME ENFORCEMENT:
  ConstitutionChecker.check(output) returns ConstitutionResult.
  If any article is violated:
    - violated_articles is populated
    - output must be sanitized or rejected
    - confidence is reduced to 0.30 (unsafe output penalty)
    - sanitized output has violations replaced with safe text

=================================================================
PHILOSOPHY (Article 15 summary):
  Human beings are NOT:
    - systems to be optimized
    - outputs to be corrected
    - behaviors to be controlled

  Human beings ARE:
    → self-reflective, evolving agents capable of change
      beyond any model's description

=================================================================
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Article registry ──────────────────────────────────────────────────────────

class Article(str, Enum):
    A1_HUMAN_AUTONOMY        = "A1_human_autonomy"
    A2_NON_IDENTITY          = "A2_non_identity"
    A3_NON_DETERMINISM       = "A3_non_determinism"
    A4_NON_MORAL_AUTHORITY   = "A4_non_moral_authority"
    A5_TRANSPARENCY          = "A5_transparency"
    A6_MINIMUM_INTERVENTION  = "A6_minimum_intervention"
    A7_LOOP_SAFETY           = "A7_loop_safety"
    A8_FORMATION_SAFETY      = "A8_formation_safety"
    A9_SELF_IMPROVEMENT_LIMIT= "A9_self_improvement_limit"
    A10_BOUNDARY_PRINCIPLE   = "A10_boundary_principle"
    A11_ERROR_HANDLING       = "A11_error_handling"
    A12_ETHICAL_GRADIENT     = "A12_ethical_gradient"
    A13_NON_MANIPULATION     = "A13_non_manipulation"
    A14_LONG_TERM_ALIGNMENT  = "A14_long_term_alignment"
    A15_FINAL_GOVERNANCE     = "A15_final_governance"


class ViolationSeverity(str, Enum):
    CRITICAL  = "critical"    # output must be rejected
    HIGH      = "high"        # output must be sanitized
    MODERATE  = "moderate"    # warning logged, output modified
    LOW       = "low"         # warning logged only


@dataclass(frozen=True)
class ArticleSpec:
    """
    Specification for one Safety Constitution article.
    Immutable — cannot be changed at runtime.
    """
    article:         Article
    title:           str
    principle:       str          # what the system MUST do
    forbidden:       List[str]    # patterns that violate this article (regex)
    required:        List[str]    # patterns that must be present (regex)
    severity:        ViolationSeverity
    applies_to:      List[str]    # which output fields to check


@dataclass
class ArticleViolation:
    article:     Article
    field:       str
    severity:    ViolationSeverity
    evidence:    str
    remedy:      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "article":  self.article.value,
            "field":    self.field,
            "severity": self.severity.value,
            "evidence": self.evidence,
            "remedy":   self.remedy,
        }


@dataclass
class ConstitutionResult:
    """
    Result of a constitution check on a single HIDOS output.
    """
    passed:             bool
    violation_count:    int
    critical_count:     int
    violations:         List[ArticleViolation] = field(default_factory=list)
    confidence_penalty: float = 0.0     # applied to output confidence if violations
    sanitized_fields:   Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed":             self.passed,
            "violation_count":    self.violation_count,
            "critical_count":     self.critical_count,
            "violations":         [v.to_dict() for v in self.violations],
            "confidence_penalty": round(self.confidence_penalty, 4),
            "sanitized_fields":   list(self.sanitized_fields.keys()),
        }


# ── The 15 Articles ───────────────────────────────────────────────────────────

_CONSTITUTION: List[ArticleSpec] = [

    ArticleSpec(
        article    = Article.A1_HUMAN_AUTONOMY,
        title      = "Human Autonomy Principle",
        principle  = "User is always the final decision-maker. System never overrides human agency.",
        forbidden  = [
            r"you (must|have to|need to|are required to) (change|stop|start|do|avoid)",
            r"system (decides|determines|enforces|requires) that you",
            r"you (are forced|must comply|are required)",
        ],
        required   = [],
        severity   = ViolationSeverity.CRITICAL,
        applies_to = ["reflective_insight", "intervention"],
    ),

    ArticleSpec(
        article    = Article.A2_NON_IDENTITY,
        title      = "Non-Identity Principle",
        principle  = "No fixed personality labels. All outputs are temporal, probabilistic, revisable.",
        forbidden  = [
            r"you are (a |an )?(controlling|avoidant|fearful|prideful|anxious|unstable) (person|type|personality)",
            r"(this is|you have) (your|a) (personality|character) (flaw|type|trait)",
            r"you are (fundamentally|inherently|by nature|always going to be)",
            r"this defines (who you are|your identity|your character)",
        ],
        required   = [],
        severity   = ViolationSeverity.CRITICAL,
        applies_to = ["reflective_insight", "integrated", "intervention"],
    ),

    ArticleSpec(
        article    = Article.A3_NON_DETERMINISM,
        title      = "Non-Determinism Principle",
        principle  = "No deterministic predictions. All outputs include uncertainty and possibility of change.",
        forbidden  = [
            r"you will (always|definitely|certainly|inevitably)",
            r"this (will|is going to) (happen|continue|worsen|escalate) (inevitably|certainly)",
            r"(impossible|cannot|will never) (change|improve|break|stop)",
        ],
        required   = [r"(may|might|appears|possible|tend|suggests|uncertain|likely)"],
        severity   = ViolationSeverity.HIGH,
        applies_to = ["reflective_insight", "simulation"],
    ),

    ArticleSpec(
        article    = Article.A4_NON_MORAL_AUTHORITY,
        title      = "Non-Moral Authority Principle",
        principle  = "System assigns no moral value. Behavior is not declared good or bad.",
        forbidden  = [
            r"(this|that|your) (behavior|pattern|loop|tendency) is (sinful|wrong|bad|evil|immoral|corrupt)",
            r"you (should be ashamed|ought to feel guilty|are morally)",
            r"god (condemns|judges|is displeased with) your",
            r"(morally|spiritually) (inferior|superior|wrong|right) (person|behavior)",
        ],
        required   = [],
        severity   = ViolationSeverity.CRITICAL,
        applies_to = ["reflective_insight", "intervention", "principle_match"],
    ),

    ArticleSpec(
        article    = Article.A5_TRANSPARENCY,
        title      = "Transparency of Reasoning",
        principle  = "All outputs expose reasoning structure and uncertainty levels.",
        forbidden  = [],
        required   = [],    # checked structurally: confidence field must exist
        severity   = ViolationSeverity.MODERATE,
        applies_to = ["confidence", "disclaimer"],
    ),

    ArticleSpec(
        article    = Article.A6_MINIMUM_INTERVENTION,
        title      = "Minimum Intervention Principle",
        principle  = "Recommendations are minimal, non-coercive, reflective-first.",
        forbidden  = [
            r"you (must immediately|need to urgently|have to now) (stop|change|fix|correct)",
            r"(urgent|emergency|critical) (action required|intervention needed|change necessary)",
        ],
        required   = [],
        severity   = ViolationSeverity.HIGH,
        applies_to = ["reflective_insight", "intervention"],
    ),

    ArticleSpec(
        article    = Article.A7_LOOP_SAFETY,
        title      = "Loop Interpretation Safety",
        principle  = "Behavioral loops are dynamic feedback structures, not personality flaws.",
        forbidden  = [
            r"(the loop|this pattern|your loop) (is|shows|proves) (your|a) (flaw|weakness|failure|problem)",
            r"you are (trapped|stuck|broken|damaged) (in|by) (this|the) loop",
            r"(this loop|the pattern) defines (who you are|your character)",
        ],
        required   = [],
        severity   = ViolationSeverity.HIGH,
        applies_to = ["reflective_insight", "loop_analysis"],
    ),

    ArticleSpec(
        article    = Article.A8_FORMATION_SAFETY,
        title      = "Formation Model Safety",
        principle  = "Formation dimensions are descriptive tendency estimates, never evaluative scores.",
        forbidden  = [
            r"(score|rating|rank) of (0|1|zero|one|100%|0%)",
            r"your (formation|character) (score|rating|rank) (is|shows)",
            r"(dimensionally|spiritually|emotionally) (inferior|superior|deficient|broken)",
        ],
        required   = [],
        severity   = ViolationSeverity.HIGH,
        applies_to = ["state_vector", "reflective_insight"],
    ),

    ArticleSpec(
        article    = Article.A9_SELF_IMPROVEMENT_LIMIT,
        title      = "Self-Improvement Constraint",
        principle  = "SICL optimizes system understanding only. Never optimizes human behavior/outcomes.",
        forbidden  = [
            r"(optimiz|improv)(ing|e|ed) (your|the user'?s?) (behavior|outcomes|emotions|personality)",
            r"target(ing)? (user|human) (behavior|emotional state|compliance)",
        ],
        required   = [],
        severity   = ViolationSeverity.CRITICAL,
        applies_to = ["improvement_description", "proposal_description"],
    ),

    ArticleSpec(
        article    = Article.A10_BOUNDARY_PRINCIPLE,
        title      = "System Boundary Principle",
        principle  = "HIDOS is a cognitive reflection system. Final authority always remains with the human.",
        forbidden  = [
            r"(system|hidos|ai) (decides|commands|orders|demands|controls)",
            r"(follow|obey|comply with) (the system|hidos|this guidance)",
        ],
        required   = [],
        severity   = ViolationSeverity.CRITICAL,
        applies_to = ["reflective_insight", "intervention"],
    ),

    ArticleSpec(
        article    = Article.A11_ERROR_HANDLING,
        title      = "Error Handling Principle",
        principle  = "High uncertainty must be explicitly stated. Never hallucinate certainty.",
        forbidden  = [
            r"(absolutely|definitely|certainly|with certainty) (true|correct|accurate|known)",
            r"100% (certain|sure|confident|accurate)",
        ],
        required   = [],
        severity   = ViolationSeverity.HIGH,
        applies_to = ["reflective_insight"],
    ),

    ArticleSpec(
        article    = Article.A12_ETHICAL_GRADIENT,
        title      = "Ethical Gradient Principle",
        principle  = "Preferred output order: awareness > reflection > understanding > suggestion > guidance.",
        forbidden  = [
            r"(step [0-9]+|first|then|finally)[:,.] (you must|you need to|you should|do this)",
        ],
        required   = [],
        severity   = ViolationSeverity.MODERATE,
        applies_to = ["reflective_insight", "intervention"],
    ),

    ArticleSpec(
        article    = Article.A13_NON_MANIPULATION,
        title      = "Non-Manipulation Principle",
        principle  = "No persuasion techniques. No exploitation of emotional vulnerability.",
        forbidden  = [
            r"(if you don'?t (change|act|do this)).{0,40}(will get worse|you will suffer|consequence)",
            r"(guilt|fear|shame) (you into|based|driven) (action|change|compliance)",
            r"you (should feel|ought to feel|must feel) (guilty|ashamed|afraid) (about|of) this",
        ],
        required   = [],
        severity   = ViolationSeverity.CRITICAL,
        applies_to = ["reflective_insight", "intervention"],
    ),

    ArticleSpec(
        article    = Article.A14_LONG_TERM_ALIGNMENT,
        title      = "Long-Term Alignment Principle",
        principle  = "System evolution targets human clarity, agency, and self-awareness — not behavioral compliance.",
        forbidden  = [
            r"(behavioral compliance|behavior modification|change compliance)",
            r"(training|conditioning) (the user|human behavior|responses)",
        ],
        required   = [],
        severity   = ViolationSeverity.HIGH,
        applies_to = ["improvement_description", "reflective_insight"],
    ),

    ArticleSpec(
        article    = Article.A15_FINAL_GOVERNANCE,
        title      = "Final Governance Statement",
        principle  = "Any subsystem output violating the constitution must be rejected during orchestration.",
        forbidden  = [],    # enforced by presence of disclaimer
        required   = [r"(tendency|structural|dynamic|possible|uncertainty|agency|change)"],
        severity   = ViolationSeverity.HIGH,
        applies_to = ["disclaimer", "reflective_insight"],
    ),
]

# Build lookup
_ARTICLE_MAP: Dict[Article, ArticleSpec] = {a.article: a for a in _CONSTITUTION}


# ── Runtime checker ───────────────────────────────────────────────────────────

class ConstitutionChecker:
    """
    HIDOS Safety Constitution runtime enforcer.

    Checks any dict output from HIDOS/FMM/SICL/GQE against all 15 articles.
    Returns a ConstitutionResult describing all violations.
    Provides sanitized text for fields that fail.

    Usage:
        checker = ConstitutionChecker()
        result  = checker.check(output_dict)
        if not result.passed:
            output = checker.apply_sanitization(output_dict, result)
    """

    def check(self, output: Dict[str, Any]) -> ConstitutionResult:
        """
        Check a HIDOS output dict against all 15 constitutional articles.
        Returns ConstitutionResult with full violation list.
        """
        violations: List[ArticleViolation] = []

        for spec in _CONSTITUTION:
            for field_path in spec.applies_to:
                text = self._extract_text(output, field_path)
                if text is None:
                    continue

                field_violations = self._check_field(spec, field_path, text)
                violations.extend(field_violations)

        # Aggregate
        critical_count    = sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL)
        confidence_penalty = min(0.55,
            sum(self._penalty(v.severity) for v in violations)
        )

        return ConstitutionResult(
            passed             = len(violations) == 0,
            violation_count    = len(violations),
            critical_count     = critical_count,
            violations         = violations,
            confidence_penalty = confidence_penalty,
        )

    def apply_sanitization(
        self,
        output:  Dict[str, Any],
        result:  ConstitutionResult,
    ) -> Dict[str, Any]:
        """
        Replace violating text fields with constitutionally-safe alternatives.
        Always adds/updates the disclaimer.
        """
        import copy
        sanitized = copy.deepcopy(output)

        for v in result.violations:
            if v.severity in (ViolationSeverity.CRITICAL, ViolationSeverity.HIGH):
                current = self._extract_text(output, v.field) or ""
                safe    = self._sanitize_text(current, v)
                self._set_text(sanitized, v.field, safe)
                result.sanitized_fields[v.field] = safe

        # Always ensure disclaimer is present and complete
        sanitized["disclaimer"] = _SAFE_DISCLAIMER
        sanitized["constitution_check"] = result.to_dict()

        return sanitized

    def _check_field(
        self, spec: ArticleSpec, field_path: str, text: str
    ) -> List[ArticleViolation]:
        violations = []
        text_lower = text.lower()

        # Check forbidden patterns
        for pattern in spec.forbidden:
            if re.search(pattern, text_lower, re.IGNORECASE):
                violations.append(ArticleViolation(
                    article  = spec.article,
                    field    = field_path,
                    severity = spec.severity,
                    evidence = f"Forbidden pattern matched: '{pattern[:60]}' in field '{field_path}'",
                    remedy   = f"Remove language violating {spec.title}. "
                               f"Principle: {spec.principle}",
                ))

        # Check required patterns (at least one must be present)
        if spec.required:
            found = any(
                re.search(p, text_lower, re.IGNORECASE) for p in spec.required
            )
            if not found and len(text) > 30:  # only check non-empty fields
                violations.append(ArticleViolation(
                    article  = spec.article,
                    field    = field_path,
                    severity = ViolationSeverity.MODERATE,
                    evidence = (
                        f"Required probabilistic language absent in '{field_path}'. "
                        f"Expected one of: {spec.required[:2]}"
                    ),
                    remedy   = f"Add uncertainty markers. Principle: {spec.principle}",
                ))

        return violations

    def _extract_text(self, output: Dict[str, Any], path: str) -> Optional[str]:
        """Extract text from a potentially nested dict path."""
        parts = path.split(".")
        current: Any = output
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        if isinstance(current, str):
            return current
        if isinstance(current, dict):
            return " ".join(str(v) for v in current.values() if isinstance(v, str))
        return None

    def _set_text(self, output: Dict[str, Any], path: str, value: str) -> None:
        parts = path.split(".")
        current = output
        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return
        if isinstance(current, dict):
            current[parts[-1]] = value

    def _sanitize_text(self, text: str, violation: ArticleViolation) -> str:
        """Replace violating text with a safe alternative."""
        return (
            f"[Constitutional review: this section was revised to comply with "
            f"{violation.article.value}. "
            f"The system description focuses on structural tendencies only, "
            f"without identity assignment, moral judgment, or deterministic prediction. "
            f"Original insight: {text[:120]}...]"
        )

    def _penalty(self, severity: ViolationSeverity) -> float:
        return {
            ViolationSeverity.CRITICAL:  0.30,
            ViolationSeverity.HIGH:      0.15,
            ViolationSeverity.MODERATE:  0.05,
            ViolationSeverity.LOW:       0.01,
        }.get(severity, 0.05)


# ── Safe fallback texts ───────────────────────────────────────────────────────

_SAFE_DISCLAIMER = (
    "HIDOS Safety Constitution v3.7 — Active. "
    "This system describes structural tendencies only. "
    "Human beings are NOT systems to be optimized, outputs to be corrected, "
    "or behaviors to be controlled. "
    "Human beings ARE self-reflective, evolving agents capable of change "
    "beyond any model's description. "
    "Final decision authority always remains with the human."
)

_CONSTITUTION_SUMMARY = {
    a.article.value: {
        "title":     a.title,
        "principle": a.principle,
        "severity":  a.severity.value,
    }
    for a in _CONSTITUTION
}


def get_constitution_summary() -> Dict[str, Any]:
    """Return the full 15-article summary for API exposure."""
    return {
        "schema":          "safety_constitution_v3.7",
        "article_count":   len(_CONSTITUTION),
        "articles":        _CONSTITUTION_SUMMARY,
        "enforcement":     "runtime — checked on every HIDOS output",
        "overridable":     False,
        "meta_principle":  (
            "Human beings are self-reflective, evolving agents capable of change "
            "beyond any model's description. The system exists to increase awareness, "
            "never to control."
        ),
    }


# ── Module-level singleton ────────────────────────────────────────────────────

_checker: Optional[ConstitutionChecker] = None


def get_constitution_checker() -> ConstitutionChecker:
    global _checker
    if _checker is None:
        _checker = ConstitutionChecker()
    return _checker
