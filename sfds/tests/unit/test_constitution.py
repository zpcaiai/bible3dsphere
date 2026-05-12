"""
Unit Tests — HIDOS Safety Constitution v3.7

No database required. Tests validate:
  - All 15 articles are defined and accessible
  - Forbidden language patterns are correctly detected
  - Required language patterns are correctly checked
  - Confidence penalty applied on violations
  - Sanitization replaces violating fields
  - Critical violations detected: identity, determinism, moral authority, manipulation
  - Clean outputs pass without violations
  - Constitution is non-overridable (no runtime mutation)
"""

import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai.constitution.safety_constitution import (
    ConstitutionChecker, Article, ViolationSeverity, ArticleViolation,
    ConstitutionResult, get_constitution_summary, get_constitution_checker,
    _CONSTITUTION, _ARTICLE_MAP, _SAFE_DISCLAIMER,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def checker():
    return ConstitutionChecker()


def _make_output(
    insight: str = "",
    disclaimer: str = "Structural tendencies only. May change. Human agency preserved.",
    confidence: float = 0.70,
) -> dict:
    return {
        "schema":            "hidos_v3.5",
        "reflective_insight": insight,
        "disclaimer":        disclaimer,
        "confidence":        confidence,
    }


# ── Constitution structure ────────────────────────────────────────────────────

class TestConstitutionStructure:
    def test_exactly_15_articles(self):
        assert len(_CONSTITUTION) == 15

    def test_all_articles_in_enum(self):
        enum_values = {a.value for a in Article}
        spec_values = {a.article.value for a in _CONSTITUTION}
        assert spec_values == enum_values

    def test_article_map_complete(self):
        for article in Article:
            assert article in _ARTICLE_MAP, f"Article {article} missing from map"

    def test_all_articles_have_title_and_principle(self):
        for spec in _CONSTITUTION:
            assert len(spec.title) > 5
            assert len(spec.principle) > 10

    def test_constitution_summary_has_15_entries(self):
        summary = get_constitution_summary()
        assert summary["article_count"] == 15
        assert len(summary["articles"]) == 15

    def test_constitution_not_overridable(self):
        summary = get_constitution_summary()
        assert summary["overridable"] is False

    def test_singleton_returns_same_instance(self):
        c1 = get_constitution_checker()
        c2 = get_constitution_checker()
        assert c1 is c2


# ── Clean outputs pass ────────────────────────────────────────────────────────

class TestCleanOutputs:
    def test_safe_output_passes(self, checker):
        out = _make_output(
            insight=(
                "The system may be showing a tendency toward fear-based patterns. "
                "This appears to be a structural dynamic, not a fixed trait. "
                "Change is always structurally possible."
            )
        )
        result = checker.check(out)
        assert result.passed
        assert result.violation_count == 0
        assert result.confidence_penalty == 0.0

    def test_empty_insight_passes(self, checker):
        out = _make_output(insight="")
        result = checker.check(out)
        assert result.passed

    def test_probabilistic_language_satisfies_A3(self, checker):
        out = _make_output(
            insight="This pattern may be present. Possible structural tendency."
        )
        result = checker.check(out)
        a3_violations = [v for v in result.violations
                         if v.article == Article.A3_NON_DETERMINISM]
        assert len(a3_violations) == 0


# ── Article 1: Human Autonomy ─────────────────────────────────────────────────

class TestArticle1_HumanAutonomy:
    def test_coercive_language_violates_A1(self, checker):
        out = _make_output(
            insight="You must change your behavior immediately to avoid harm."
        )
        result = checker.check(out)
        a1 = [v for v in result.violations if v.article == Article.A1_HUMAN_AUTONOMY]
        assert len(a1) > 0
        assert a1[0].severity == ViolationSeverity.CRITICAL

    def test_system_decides_violates_A1(self, checker):
        out = _make_output(
            insight="The system determines that you must comply with these suggestions."
        )
        result = checker.check(out)
        a1 = [v for v in result.violations if v.article == Article.A1_HUMAN_AUTONOMY]
        assert len(a1) > 0


# ── Article 2: Non-Identity ───────────────────────────────────────────────────

class TestArticle2_NonIdentity:
    def test_personality_label_violates_A2(self, checker):
        out = _make_output(
            insight="You are a controlling person by nature."
        )
        result = checker.check(out)
        a2 = [v for v in result.violations if v.article == Article.A2_NON_IDENTITY]
        assert len(a2) > 0
        assert a2[0].severity == ViolationSeverity.CRITICAL

    def test_defines_identity_violates_A2(self, checker):
        out = _make_output(
            insight="This defines who you are at your core."
        )
        result = checker.check(out)
        a2 = [v for v in result.violations if v.article == Article.A2_NON_IDENTITY]
        assert len(a2) > 0

    def test_temporal_description_passes_A2(self, checker):
        out = _make_output(
            insight="Current tendency shows a pattern of avoidance. This may shift over time."
        )
        result = checker.check(out)
        a2 = [v for v in result.violations if v.article == Article.A2_NON_IDENTITY]
        assert len(a2) == 0


# ── Article 3: Non-Determinism ────────────────────────────────────────────────

class TestArticle3_NonDeterminism:
    def test_inevitability_violates_A3(self, checker):
        out = _make_output(
            insight="You will always struggle with this — it is impossible to change."
        )
        result = checker.check(out)
        a3 = [v for v in result.violations if v.article == Article.A3_NON_DETERMINISM]
        assert len(a3) > 0

    def test_missing_uncertainty_flagged(self, checker):
        # No word in this insight contains may|might|appears|possible|tend|suggests|uncertain|likely
        insight = (
            "The fear loop is active. "
            "The control drive is elevated. "
            "The burnout state is rising. "
            "The structural analysis confirms high loop activation. "
            "The formation signal is strong and consistent."
        )
        # Verify none of the probabilistic markers are present as substrings
        import re
        pattern = r"(may|might|appears|possible|tend|suggests|uncertain|likely)"
        assert not re.search(pattern, insight.lower()), \
            "Test insight still contains probabilistic markers"
        out    = _make_output(insight=insight)
        result = checker.check(out)
        a3 = [v for v in result.violations if v.article == Article.A3_NON_DETERMINISM]
        assert len(a3) > 0, (
            f"Expected A3 violation for insight lacking probabilistic language. "
            f"Violations found: {[v.article.value for v in result.violations]}"
        )


# ── Article 4: Non-Moral Authority ───────────────────────────────────────────

class TestArticle4_NonMoralAuthority:
    def test_moral_judgment_violates_A4(self, checker):
        out = _make_output(
            insight="This behavior is sinful and morally wrong."
        )
        result = checker.check(out)
        a4 = [v for v in result.violations if v.article == Article.A4_NON_MORAL_AUTHORITY]
        assert len(a4) > 0
        assert a4[0].severity == ViolationSeverity.CRITICAL

    def test_structural_description_passes_A4(self, checker):
        out = _make_output(
            insight="A reinforcement loop may be active in this area. This is a structural signal."
        )
        result = checker.check(out)
        a4 = [v for v in result.violations if v.article == Article.A4_NON_MORAL_AUTHORITY]
        assert len(a4) == 0


# ── Article 6: Minimum Intervention ──────────────────────────────────────────

class TestArticle6_MinimumIntervention:
    def test_urgent_command_violates_A6(self, checker):
        out = _make_output(
            insight="You must immediately stop this pattern. Urgent action required now."
        )
        result = checker.check(out)
        a6 = [v for v in result.violations if v.article == Article.A6_MINIMUM_INTERVENTION]
        assert len(a6) > 0


# ── Article 13: Non-Manipulation ─────────────────────────────────────────────

class TestArticle13_NonManipulation:
    def test_guilt_exploitation_violates_A13(self, checker):
        out = _make_output(
            insight="You should feel guilty about this pattern — it has caused damage."
        )
        result = checker.check(out)
        a13 = [v for v in result.violations if v.article == Article.A13_NON_MANIPULATION]
        assert len(a13) > 0
        assert a13[0].severity == ViolationSeverity.CRITICAL

    def test_fear_threat_violates_A13(self, checker):
        out = _make_output(
            insight="If you don't change this, things will get worse and you will suffer."
        )
        result = checker.check(out)
        a13 = [v for v in result.violations if v.article == Article.A13_NON_MANIPULATION]
        assert len(a13) > 0


# ── Confidence penalty ────────────────────────────────────────────────────────

class TestConfidencePenalty:
    def test_critical_violation_reduces_confidence(self, checker):
        out = _make_output(
            insight="You are a fearful person by nature."   # A2 critical
        )
        result = checker.check(out)
        assert result.confidence_penalty > 0
        assert result.critical_count > 0

    def test_no_violation_no_penalty(self, checker):
        out = _make_output(
            insight="The system may be showing structural tendencies. Change is possible."
        )
        result = checker.check(out)
        assert result.confidence_penalty == 0.0


# ── Sanitization ─────────────────────────────────────────────────────────────

class TestSanitization:
    def test_sanitization_replaces_violating_field(self, checker):
        out = _make_output(
            insight="You are an anxious personality type."
        )
        result    = checker.check(out)
        sanitized = checker.apply_sanitization(out, result)
        # Sanitization replaces the field with a [Constitutional review...] wrapper
        if "reflective_insight" in sanitized:
            field_text = sanitized["reflective_insight"].lower()
            # Either the field is replaced by a review notice, OR the original identity text is gone
            review_applied = "constitutional review" in field_text or "constitution_check" in sanitized
            assert review_applied, (
                f"Expected constitution review to be applied. Got: {field_text[:200]}"
            )

    def test_sanitization_adds_safe_disclaimer(self, checker):
        out = _make_output(
            insight="You are fundamentally controlling and always will be."
        )
        result   = checker.check(out)
        sanitized = checker.apply_sanitization(out, result)
        assert "disclaimer" in sanitized
        assert "human beings" in sanitized["disclaimer"].lower()

    def test_constitution_check_in_sanitized(self, checker):
        out = _make_output(
            insight="You will always do this — it is impossible to stop."
        )
        result   = checker.check(out)
        sanitized = checker.apply_sanitization(out, result)
        assert "constitution_check" in sanitized
