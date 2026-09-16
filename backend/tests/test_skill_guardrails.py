"""Executable guardrail enforcement."""

from __future__ import annotations

import pytest

from backend.discernment_platform import guardrails as g
from backend.discernment_platform.skills import get_skill_registry

pytestmark = pytest.mark.no_db


def _status(findings, rule_id):
    return [f.status for f in findings if f.rule_id == rule_id]


def test_evidence_floor_blocks_low_evidence_conclusion():
    out = {"items": [{"evidence_level": "E1", "is_conclusion": True}]}
    findings = g.enforce(["E0-E2 不得输出为结论"], out, {})
    assert "violation" in _status(findings, "evidence_level_floor")


def test_evidence_floor_passes_high_evidence():
    out = {"items": [{"evidence_level": "E4", "is_conclusion": True}]}
    findings = g.enforce(["E0-E2 不得输出为结论"], out, {})
    assert _status(findings, "evidence_level_floor") == ["pass"]


def test_salvation_verdict_is_blocked():
    findings = g.enforce(["Not a salvation judgment."], {"text": "他一定下地狱"}, {})
    assert g.violations(findings)


def test_spiritual_abuse_phrase_is_blocked():
    findings = g.enforce(["不得羞辱或强迫"], {"text": "你还没认够罪"}, {})
    assert g.violations(findings)


def test_clinical_diagnosis_without_hedge_is_blocked():
    findings = g.enforce(["Not a clinical diagnosis."], {"text": "他有抑郁症"}, {})
    assert g.violations(findings)


def test_clinical_term_with_hedge_passes():
    findings = g.enforce(["Not a clinical diagnosis."], {"text": "可能与抑郁症有关，需专业评估"}, {})
    assert not g.violations(findings)


def test_mind_reading_requires_alternatives():
    out = {"h": [{"possible_pattern": "spiritual_pride", "evidence_level": "E3"}]}
    findings = g.enforce(["不得声称知道当事人内心"], out, {})
    assert g.violations(findings)


def test_mind_reading_passes_with_alternatives():
    out = {
        "h": [
            {
                "possible_pattern": "spiritual_pride",
                "evidence_level": "E3",
                "alternative_explanations": ["可能只是群体惯用语言"],
            }
        ]
    }
    findings = g.enforce(["不得声称知道当事人内心"], out, {})
    assert not g.violations(findings)


def test_fabricated_evidence_reference_is_caught():
    ctx = {"evidence": [{"evidence_id": "e-1"}]}
    out = {"claim": {"evidence_references": ["e-1", "e-999"]}}
    findings = g.enforce(["No fabricated evidence or signatures."], out, ctx)
    assert g.violations(findings)


def test_ai_self_certification_of_c4_is_blocked():
    out = {"controls": [{"control_id": "c1", "severity": "C4", "decision": "pass"}]}
    findings = g.enforce(["No AI-only theological certification."], out, {})
    assert g.violations(findings)


def test_c4_pass_with_human_reviewer_is_allowed():
    out = {"controls": [{"control_id": "c1", "severity": "C4", "decision": "pass", "human_reviewer": "elder"}]}
    findings = g.enforce(["No AI-only theological certification."], out, {})
    assert not g.violations(findings)


def test_production_approval_without_rollback_is_blocked():
    findings = g.enforce(["No deployment without rollback."], {"status": "APPROVED_FOR_PRODUCTION"}, {})
    assert g.violations(findings)


def test_production_approval_with_rollback_passes():
    out = {"status": "APPROVED_FOR_PRODUCTION", "rollback_target": "v1.2.3"}
    findings = g.enforce(["No deployment without rollback."], out, {})
    assert not g.violations(findings)


def test_score_cannot_override_critical_blockers():
    out = {"domain": {"critical_blockers": ["b1"], "decision": "pass"}}
    findings = g.enforce(["No score-based override of critical failures."], out, {})
    assert g.violations(findings)


def test_consent_gate_blocks_unconsented_gospel():
    ctx = {"consent_scope": {"allow_gospel_bridge": False}}
    findings = g.enforce(["对非基督徒先征得进入福音层的同意"], {"gospel_bridge": {"x": 1}}, ctx)
    assert g.violations(findings)


def test_pii_field_is_flagged():
    findings = g.enforce(["涉及他人隐私时最小化保存"], {"person": {"phone": "139..."}}, {})
    assert g.violations(findings)


def test_certificate_without_expiry_is_flagged():
    findings = g.enforce(["No silent certificate expiry."], {"cert": {"certificate_id": "c1"}}, {})
    assert g.violations(findings)


def test_tenant_leak_is_caught():
    findings = g.enforce(["tenant isolation"], {"row": {"tenant_id": "t2"}}, {"tenant_id": "t1"})
    assert g.violations(findings)


def test_unmatched_guardrail_is_reported_for_manual_review():
    findings = g.enforce(["某条完全自定义的要求"], {}, {})
    assert findings[0].status == "manual_review"


def test_no_guardrail_line_is_silently_dropped():
    lines = ["E0-E2 不得输出为结论", "某条完全自定义的要求", "No fabricated evidence."]
    findings = g.enforce(lines, {}, {})
    assert {f.guardrail for f in findings} == set(lines)


def test_every_shipped_guardrail_gets_a_verdict():
    skills = get_skill_registry()
    for contract in skills:
        findings = g.enforce(contract.guardrails, {}, {})
        assert {f.guardrail for f in findings} == set(contract.guardrails)


def test_coverage_counts_add_up():
    findings = g.enforce(["E0-E2 不得输出为结论", "自定义"], {}, {})
    assert sum(g.coverage(findings).values()) == len(findings)
