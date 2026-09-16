"""Tests for the extended guardrail rule families.

Every family gets both a violating case and a clean case, so a rule that
fires on everything (or nothing) fails here.
"""

from __future__ import annotations

import pytest

from backend.discernment_platform import guardrails as g
from backend.discernment_platform.skills import get_skill_registry

pytestmark = pytest.mark.no_db


def fires(guardrail: str, out: dict, ctx: dict | None = None) -> bool:
    return bool(g.violations(g.enforce([guardrail], out, ctx or {})))


# --- pastoral / trauma ------------------------------------------------------

def test_trauma_invalidation_blocked():
    assert fires("No trauma invalidation.", {"text": "你想多了，这不算什么"})


def test_trauma_acknowledgement_passes():
    assert not fires("No trauma invalidation.", {"text": "你所经历的伤害是真实的"})


def test_forced_reconciliation_blocked():
    assert fires("No forced reconciliation.", {"text": "你必须原谅他并回到他身边"})


def test_forgiveness_with_safety_passes():
    assert not fires(
        "No forced reconciliation.",
        {"text": "可以谈饶恕，但安全必须先被处理"},
        {"abuse_present": True},
    )


def test_forgiveness_without_safety_in_abuse_context_blocked():
    assert fires("No forced reconciliation.", {"text": "先考虑饶恕吧"}, {"abuse_present": True})


def test_scrupulosity_amplification_blocked():
    assert fires(
        "No scrupulosity amplification.",
        {"text": "还有没有隐藏的罪，再仔细找找你的罪"},
        {"sensitivity": "mental_health"},
    )


def test_assurance_language_passes():
    assert not fires(
        "No scrupulosity amplification.",
        {"text": "基督已一次成全，你可以停下来安息"},
        {"sensitivity": "mental_health"},
    )


def test_victim_blaming_blocked():
    assert fires("No victim blaming.", {"text": "苍蝇不叮无缝的蛋"})


def test_victim_support_passes():
    assert not fires("No victim blaming.", {"text": "这不是你的错"})


def test_abusive_scripture_blocked():
    assert fires("No abusive scripture application.", {"text": "圣经说你必须顺服我"})


def test_pastoral_scripture_passes():
    assert not fires("No abusive scripture application.", {"text": "罗马书 8:1 说不定罪"})


# --- gospel quality ---------------------------------------------------------

def test_moralism_blocked_when_practice_lacks_christ():
    assert fires("No moralism.", {"practice": "每天早起读书并且更努力"})


def test_practice_with_christ_passes():
    assert not fires("No moralism.", {"practice": "在基督里安息，本周做一件诚实的小事"})


def test_cheap_grace_blocked():
    out = {"gospel_bridge": {"christ_person_and_work": "神爱你，一切都好"}}
    assert fires("No cheap grace.", out)


def test_gospel_naming_sin_passes():
    out = {"gospel_bridge": {"christ_person_and_work": "基督为我们的罪死，呼召我们悔改"}}
    assert not fires("No cheap grace.", out)


def test_prosperity_promise_blocked():
    assert fires("No prosperity-gospel promises.", {"hope": "信了就必得医治，一定会富足"})


def test_honest_hope_passes():
    assert not fires("No prosperity-gospel promises.", {"hope": "今生的痛苦不保证立刻消失"})


def test_denominational_overreach_blocked():
    assert fires("No denomination-specific overreach.", {"claim": {"tier": "D3"}})


def test_labelled_tradition_passes():
    out = {"claim": {"tier": "D3", "tradition_label": "改革宗立场"}}
    assert not fires("No denomination-specific overreach.", out)


def test_salvation_scoring_blocked():
    assert fires("No salvation scoring.", {"result": {"salvation_score": 0.8}})


def test_maturity_total_score_blocked():
    assert fires("No single spiritual maturity score.", {"twin": {"maturity_score": 72}})


def test_dimension_scores_pass():
    out = {"twin": {"dimensions": [{"name": "attention", "trend": "improving"}]}}
    assert not fires("No single spiritual maturity score.", out)


def test_blanket_demonisation_blocked():
    assert fires("不得把所有非基督教观点简单标记为“魔鬼”", {"text": "这套思想就是魔鬼"})


def test_grace_levels_require_creation_good():
    out = {"layers": {"creation_good": [], "fall_distortion": ["x"]}}
    assert fires("应区分真理碎片、共同恩典、偶像化和明确恶行", out)


def test_grace_levels_pass_with_creation_good():
    out = {"layers": {"creation_good": ["对勤奋的肯定"], "fall_distortion": ["x"]}}
    assert not fires("应区分真理碎片、共同恩典、偶像化和明确恶行", out)


# --- dialogue ---------------------------------------------------------------

def test_hidden_multi_question_blocked():
    assert fires("No hidden multi-question prompts.", {"q": {"question": "你怎么想？还有呢？"}})


def test_single_question_passes():
    assert not fires("No hidden multi-question prompts.", {"q": {"question": "你怎么想？"}})


# --- longitudinal / prediction ---------------------------------------------

def test_deterministic_prediction_blocked():
    assert fires("No deterministic prediction.", {"forecast": "你一定会复发"})


def test_probability_one_blocked():
    assert fires("No deterministic prediction.", {"forecast": {"probability": 1.0}})


def test_hedged_forecast_passes():
    assert not fires("No deterministic prediction.", {"forecast": {"probability": 0.4}})


def test_public_person_private_twin_blocked():
    out = {"twin": {"formation_chain": {"x": 1}}}
    assert fires("No public-person private Formation Twin.", out, {"subject_type": "person"})


def test_self_reflection_twin_passes():
    out = {"twin": {"formation_chain": {"x": 1}}}
    assert not fires(
        "No public-person private Formation Twin.", out, {"subject_type": "self_reflection"}
    )


def test_unsupported_certainty_blocked():
    assert fires("No unsupported certainty.", {"claim": {"text": "毫无疑问他就是这样"}})


def test_certainty_with_e4_passes():
    out = {"claim": {"text": "毫无疑问", "evidence_level": "E4"}}
    assert not fires("No unsupported certainty.", out)


# --- governance / access ----------------------------------------------------

def test_disabling_recertification_blocked():
    assert fires("No disabling continuous recertification.", {"cfg": {"recertification_enabled": False}})


def test_recertification_enabled_passes():
    assert not fires(
        "No disabling continuous recertification.", {"cfg": {"recertification_enabled": True}}
    )


def test_unlimited_pastoral_access_blocked():
    out = {"disclosure": {"disclosure_id": "d1", "allowed_fields": ["summary"]}}
    assert fires("No unlimited pastoral access.", out)


def test_scoped_disclosure_passes():
    out = {
        "disclosure": {
            "disclosure_id": "d1",
            "allowed_fields": ["summary"],
            "expires_at": "2027-01-01",
            "purpose": "pastoral_care",
        }
    }
    assert not fires("No unlimited pastoral access.", out)


def test_surveillance_accountability_blocked():
    assert fires("No surveillance-style accountability.", {"plan": "偷偷监控他的手机"})


def test_transparent_accountability_passes():
    assert not fires("No surveillance-style accountability.", {"plan": {"notify_subject": True}})


def test_hidden_resharing_blocked():
    assert fires("No hidden re-sharing.", {"share": {"recipient_actor_id": "a2"}})


def test_audited_resharing_passes():
    out = {"share": {"recipient_actor_id": "a2", "basis": "consent", "audit_id": "au1"}}
    assert not fires("No hidden re-sharing.", out)


def test_internal_only_abuse_blocked():
    out = {"plan": {"reportable": True, "external_report_required": False}}
    assert fires("No internal-only handling of reportable abuse.", out, {"abuse_present": True})


def test_external_report_passes():
    out = {"plan": {"reportable": True, "external_report_required": True}}
    assert not fires("No internal-only handling of reportable abuse.", out, {"abuse_present": True})


def test_professional_claims_without_review_blocked():
    assert fires("No professional claims without qualified review.", {"advice": "建议调整用药"})


def test_professional_claims_with_reviewer_pass():
    out = {"advice": "建议调整用药", "reviewer": "licensed_clinician"}
    assert not fires("No professional claims without qualified review.", out)


def test_replacing_professional_care_blocked():
    out = {"plan": "多祷告就好", "risk": {"risk_level": "high"}}
    assert fires("No replacing church or professional care.", out)


def test_referral_included_passes():
    out = {"plan": "建议联系专业心理医生并告知牧者", "risk": {"risk_level": "high"}}
    assert not fires("No replacing church or professional care.", out)


def test_high_risk_domain_routing_blocked():
    assert fires("高风险医疗、法律、财务内容进入专项安全流程", {"advice": "关于诉讼的建议"})


def test_high_risk_domain_routed_passes():
    out = {"advice": "关于诉讼的建议", "escalated": True}
    assert not fires("高风险医疗、法律、财务内容进入专项安全流程", out)


# --- exegesis / rights ------------------------------------------------------

def test_proof_texting_blocked():
    assert fires("No proof-texting.", {"cite": {"used_as_proof": True, "locator": "罗 8:1"}})


def test_contextual_citation_passes():
    out = {"cite": {"used_as_proof": True, "locator": "罗 8:1", "literary_context": "第八章论证"}}
    assert not fires("No proof-texting.", out)


def test_strong_number_only_blocked():
    assert fires("No Strong-number-only word studies.", {"word": {"strong_number": "G26"}})


def test_word_study_with_corpus_passes():
    out = {"word": {"strong_number": "G26", "corpus_usage": ["约壹 4:8"]}}
    assert not fires("No Strong-number-only word studies.", out)


def test_copyright_leakage_by_length_blocked():
    assert fires("No copyright leakage.", {"c": {"quote_text": "长" * 600}})


def test_copyright_leakage_by_rights_status_blocked():
    out = {"c": {"quote_text": "短引文", "rights_status": "metadata_only"}}
    assert fires("No copyright leakage.", out)


def test_public_domain_quote_passes():
    out = {"c": {"quote_text": "短引文", "rights_status": "public_domain"}}
    assert not fires("No copyright leakage.", out)


def test_offline_external_verification_blocked():
    assert fires("不联网时不得把外部事实标为已核实", {"claim": {"externally_verified": True}})


def test_online_external_verification_passes():
    out = {"claim": {"externally_verified": True}}
    assert not fires("不联网时不得把外部事实标为已核实", out, {"network_available": True})


# --- public-figure analysis -------------------------------------------------

def test_harassment_tooling_blocked():
    assert fires("不得鼓励网暴、举报轰炸或人肉搜索", {"plan": "去把他人肉出来"})


def test_dignity_violation_blocked():
    assert fires("不得贬低其他宗教人士的人格尊严", {"text": "这种人不配被听见"})


def test_extreme_sampling_blocked():
    out = {"corpus": {"sampling_strategy": "most_extreme"}}
    assert fires("不得只采样最极端内容制造结论", out)


def test_representative_sampling_passes():
    out = {"corpus": {"sampling_strategy": "stratified", "corpus_size": 50, "sample_size": 20}}
    assert not fires("不得只采样最极端内容制造结论", out)


def test_malice_from_rhetoric_blocked():
    assert fires("不从强烈修辞直接推断恶意", {"h": {"malice_inferred": True}})


def test_malice_with_behavioral_evidence_passes():
    out = {"h": {"malice_inferred": True, "behavioral_evidence": ["重复删除退款请求"]}}
    assert not fires("不从强烈修辞直接推断恶意", out)


def test_commercialisation_as_sin_blocked():
    assert fires("不得把商业化本身视为罪", {"text": "卖课就是贪财"})


def test_platform_manipulation_blocked():
    assert fires("不提供规避平台安全、刷量或操纵推荐的方案", {"plan": "先刷量再买粉"})


def test_private_family_analysis_blocked():
    assert fires("不分析非公开家庭成员", {"person": {"relation": "child"}})


def test_public_family_member_passes():
    out = {"person": {"relation": "spouse", "is_public_figure": True}}
    assert not fires("不分析非公开家庭成员", out)


def test_aggregate_by_default_blocked():
    out = {"audience": {"audience_segment": "青年", "individual_ids": ["u1"]}}
    assert fires("默认聚合化", out)


def test_aggregated_audience_passes():
    out = {"audience": {"audience_segment": "青年", "aggregated": True}}
    assert not fires("默认聚合化", out)


def test_divine_verdict_on_virality_blocked():
    assert fires("不得把爆火解释为神认可或神审判的直接证据", {"text": "爆火说明神喜悦"})


def test_counterfactual_excusing_harm_blocked():
    assert fires("不得使用反事实为真实伤害开脱", {"c": {"counterfactual": True, "harm_dismissed": True}})


def test_counterfactual_without_dismissal_passes():
    assert not fires("不得使用反事实为真实伤害开脱", {"c": {"counterfactual": True}})


def test_entertainment_criminalisation_blocked():
    assert fires("不得制造过度恐惧或把娱乐使用都罪化", {"text": "娱乐本身就是罪"})


def test_clip_as_whole_person_blocked():
    out = {"claim": {"clip_based": True, "scope": "whole_person"}}
    assert fires("不以剪辑片段代表完整人格", out)


def test_sensitive_attributes_blocked():
    assert fires("敏感人口属性只能在用户提供或合法公开聚合数据中使用", {"seg": {"ethnicity": "x"}})


def test_sensitive_attributes_aggregated_passes():
    out = {"seg": {"ethnicity": "x", "aggregated": True}}
    assert not fires("敏感人口属性只能在用户提供或合法公开聚合数据中使用", out)


def test_hide_internal_inferences_blocked():
    out = {"redacted_user_view": {"pride_hypotheses": [{"x": 1}]}}
    assert fires("对用户界面隐藏内部敏感推断", out)


def test_clean_user_view_passes():
    assert not fires("对用户界面隐藏内部敏感推断", {"redacted_user_view": {"summary": "s"}})


def test_monetization_dimensions_blocked_when_incomplete():
    out = {"analysis": {"business_model": "课程订阅", "disclosure": "充分"}}
    assert fires("重点评估披露、诚实、适配性和利用脆弱性的风险", out)


def test_monetization_dimensions_complete_passes():
    out = {
        "analysis": {
            "business_model": "课程订阅",
            "disclosure": "充分",
            "honesty": "宣称与实际相符",
            "fit": "适配目标人群",
            "vulnerability": "未见利用脆弱性",
        }
    }
    assert not fires("重点评估披露、诚实、适配性和利用脆弱性的风险", out)


# --- corpus-level guarantees ------------------------------------------------

def test_every_shipped_guardrail_line_now_has_a_rule():
    uncovered = [
        line
        for contract in get_skill_registry()
        for line in contract.guardrails
        if not any(rule.matches(line) for rule in g.RULES)
    ]
    assert uncovered == []


def test_rule_ids_are_unique():
    ids = [rule.rule_id for rule in g.RULES]
    assert len(ids) == len(set(ids))


def test_clean_output_does_not_trip_every_rule():
    """A benign, well-formed output must not be flagged by the whole corpus."""

    clean = {
        "summary": "这是一份中性的辨识摘要",
        "layers": {"creation_good": ["对勤奋的肯定"], "fall_distortion": ["绝对化"]},
    }
    flagged = 0
    for contract in get_skill_registry():
        flagged += len(g.violations(g.enforce(contract.guardrails, clean, {})))
    assert flagged == 0


def test_unknown_custom_guardrail_still_reports_manual_review():
    findings = g.enforce(["某条完全自定义且无关的组织要求"], {}, {})
    assert findings[0].status == "manual_review"
