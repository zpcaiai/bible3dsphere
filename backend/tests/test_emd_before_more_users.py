"""The BEFORE_MORE_USERS items — everything about them that a machine can hold.

Three of these five items end in a human judgement (interviews, scoring, legal review) and
one ends in someone pulling a switch on staging. What is testable is the machinery around
those judgements: that the protocol is sound, that the agreement maths is right, that the
inventory matches the schema, and — most importantly — that none of these tools can report
"done" when the human part has not happened.

That last property is what the suite mostly asserts. A toolkit that quietly self-certifies
is worse than no toolkit.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from formation_twin.emotional_maturity import DIMENSION_CODES
from formation_twin.emotional_maturity_incident_drill import (
    CONTAINMENT_POSTURES,
    DRILL_STEPS,
    DrillRefused,
    build_drill_plan,
    containment_effects,
    describe_drill,
    run_drill,
)
from formation_twin.emotional_maturity_privacy_assessment import (
    LEGAL_QUESTIONS,
    SPECIAL_CATEGORIES,
    build_data_inventory,
    build_privacy_assessment,
    describe_privacy_assessment,
)
from formation_twin.emotional_maturity_psychometrics import (
    BLOCKING_FINDINGS,
    INTERVIEW_STEPS,
    KNOWN_AMBIGUOUS_TERMS,
    agreement_report,
    analyse_interviews,
    build_interview_protocol,
    cohens_kappa,
    describe_psychometrics,
    interpret_kappa,
    select_interview_items,
    triage_disagreements,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 认知访谈
# ═════════════════════════════════════════════════════════════════════════════

def test_the_protocol_asks_for_a_paraphrase_before_showing_options():
    """顺序是方法的一部分：先看到选项，就再也看不到他原本的理解了。"""
    steps = [step["step"] for step in INTERVIEW_STEPS]
    assert steps.index("PARAPHRASE") < steps.index("DECISION")


def test_the_protocol_flags_known_ambiguous_terms_in_the_item():
    protocol = build_interview_protocol(
        item_id="I-1", item_text="最近你是否能在冲突后放下情绪，回到真我？",
        dimension_code="D9",
    )
    flagged = {entry["term"] for entry in protocol["terms_to_probe"]}
    assert {"最近", "放下", "真我"} <= flagged


def test_the_protocol_tells_the_interviewer_not_to_correct_the_respondent():
    protocol = build_interview_protocol(item_id="I-1", item_text="题干", dimension_code="D1")
    joined = " ".join(protocol["interviewer_rules"])
    assert "不要说「对」「不对」" in joined
    assert "你在测题目，不是在测人" in joined


def test_an_unknown_dimension_is_refused():
    with pytest.raises(ValueError):
        build_interview_protocol(item_id="I", item_text="x", dimension_code="D99")


def test_item_selection_revisits_known_trouble_first():
    items = [
        {"item_id": "A", "dimension_code": "D1"},
        {"item_id": "B", "dimension_code": "D2"},
        {"item_id": "C", "dimension_code": "D3"},
    ]
    result = select_interview_items(
        available_items=items, already_probed=["A"],
        prior_findings=[{"item_id": "A", "finding_type": "AMBIGUOUS_TERM"}],
        per_session=2,
    )
    assert result["selected_ids"][0] == "A"
    assert "A" in result["revisits"]


def test_item_selection_reports_which_dimensions_remain_unprobed():
    result = select_interview_items(
        available_items=[{"item_id": "A", "dimension_code": "D1"}], per_session=1,
    )
    assert set(result["dimensions_still_unprobed"]) == set(DIMENSION_CODES) - {"D1"}


def test_two_blocking_findings_force_a_rewrite():
    analysis = analyse_interviews([
        {"item_id": "I-1", "participant_id": f"p{i}", "finding_type": "AMBIGUOUS_TERM",
         "dimension_code": "D5", "quote": "「真我」我不知道是指哪个我"}
        for i in range(2)
    ], minimum_interviews=2)
    item = analysis["items"][0]
    assert item["verdict"] == "REWRITE"
    assert analysis["gate_status"] == "BLOCKED"


def test_a_single_blocking_finding_is_review_not_rewrite():
    analysis = analyse_interviews([
        {"item_id": "I-1", "participant_id": "p1", "finding_type": "MISREAD", "dimension_code": "D1"},
        {"item_id": "I-1", "participant_id": "p2", "finding_type": "OK", "dimension_code": "D1"},
    ], minimum_interviews=2)
    assert analysis["items"][0]["verdict"] == "REVIEW"


def test_too_few_participants_cannot_pass_however_clean_the_findings():
    """这条是整个工具包的重点：它不能替人宣布访谈做完了。"""
    analysis = analyse_interviews([
        {"item_id": "I-1", "participant_id": "p1", "finding_type": "OK", "dimension_code": "D1"},
    ], minimum_interviews=5)
    assert analysis["sample_sufficient"] is False
    assert analysis["gate_status"] == "INSUFFICIENT_SAMPLE"


def test_a_clean_sufficient_round_passes():
    findings = [
        {"item_id": f"I-{i}", "participant_id": f"p{i}", "finding_type": "OK",
         "dimension_code": code}
        for i, code in enumerate(DIMENSION_CODES[:5])
    ]
    analysis = analyse_interviews(findings, minimum_interviews=5)
    assert analysis["gate_status"] == "PASS"


def test_uncovered_dimensions_are_reported():
    analysis = analyse_interviews([
        {"item_id": "I-1", "participant_id": "p1", "finding_type": "OK", "dimension_code": "D1"},
    ], minimum_interviews=1)
    assert "D10" in analysis["dimensions_uncovered"]


def test_an_unknown_finding_type_is_refused():
    with pytest.raises(ValueError):
        analyse_interviews([{"item_id": "I", "participant_id": "p", "finding_type": "VIBES"}])


def test_emotional_burden_counts_as_blocking():
    assert "EMOTIONAL_BURDEN" in BLOCKING_FINDINGS


def test_the_ambiguous_term_list_covers_the_religious_ones():
    terms = {entry["term"] for entry in KNOWN_AMBIGUOUS_TERMS}
    assert {"顺服", "属灵", "真我"} <= terms


# ═════════════════════════════════════════════════════════════════════════════
# 评分一致性
# ═════════════════════════════════════════════════════════════════════════════

def test_kappa_is_one_for_perfect_agreement():
    assert cohens_kappa(["E1", "E2", "E3"], ["E1", "E2", "E3"]) == pytest.approx(1.0)


def test_kappa_is_zero_when_agreement_is_only_chance():
    assert cohens_kappa(["E2"] * 5, ["E2"] * 5) == 0.0


def test_kappa_goes_negative_when_raters_systematically_disagree():
    assert cohens_kappa(["E1", "E2", "E1", "E2"], ["E2", "E1", "E2", "E1"]) < 0


def test_mismatched_rater_lengths_are_refused():
    with pytest.raises(ValueError):
        cohens_kappa(["E1"], ["E1", "E2"])


@pytest.mark.parametrize("value,label", [
    (0.1, "SLIGHT"), (0.3, "FAIR"), (0.5, "MODERATE"), (0.7, "SUBSTANTIAL"), (0.9, "ALMOST_PERFECT"),
])
def test_kappa_interpretation_bands(value, label):
    assert interpret_kappa(value) == label


def test_perfect_agreement_passes():
    scorings = [
        {"response_id": f"r{i}", "rater_id": rater, "stage": stage}
        for i, stage in enumerate(["E1", "E2", "E3", "E4"])
        for rater in ("a", "b")
    ]
    report = agreement_report(scorings)
    assert report["status"] == "PASS"
    assert report["exact_agreement"] == 1.0


def test_a_two_stage_gap_blocks_regardless_of_the_headline_number():
    """E1 vs E4 不是措辞问题，是锚点根本没描述可观察行为。"""
    scorings = [{"response_id": f"r{i}", "rater_id": r, "stage": s}
                for i in range(9) for r, s in (("a", "E3"), ("b", "E3"))]
    scorings += [
        {"response_id": "bad", "rater_id": "a", "stage": "E1"},
        {"response_id": "bad", "rater_id": "b", "stage": "E4"},
    ]
    report = agreement_report(scorings)
    assert report["exact_agreement"] >= 0.8
    assert report["status"] == "BLOCKED"
    assert len(report["serious_disagreements"]) == 1


def test_high_percent_with_low_kappa_is_flagged_as_chance_inflated():
    """两位评分者都习惯给 E2，就能靠巧合刷出高一致率——κ 会拆穿它。"""
    scorings = []
    for i in range(9):
        scorings += [
            {"response_id": f"r{i}", "rater_id": "a", "stage": "E2"},
            {"response_id": f"r{i}", "rater_id": "b", "stage": "E2"},
        ]
    scorings += [
        {"response_id": "r9", "rater_id": "a", "stage": "E2"},
        {"response_id": "r9", "rater_id": "b", "stage": "E3"},
    ]
    report = agreement_report(scorings)
    assert report["exact_agreement"] >= 0.9
    assert report["cohens_kappa"] < 0.40
    assert report["chance_inflated"] is True
    assert report["status"] == "REVIEW"


def test_singly_scored_responses_do_not_count():
    report = agreement_report([{"response_id": "r1", "rater_id": "a", "stage": "E2"}])
    assert report["status"] == "INSUFFICIENT_DATA"
    assert report["responses_double_scored"] == 0


def test_an_unknown_stage_is_refused():
    with pytest.raises(ValueError):
        agreement_report([
            {"response_id": "r", "rater_id": "a", "stage": "E9"},
            {"response_id": "r", "rater_id": "b", "stage": "E2"},
        ])


def test_triage_separates_fixable_wording_from_broken_anchors():
    scorings = [
        {"response_id": "r1", "rater_id": "a", "stage": "E2"},
        {"response_id": "r1", "rater_id": "b", "stage": "E3"},
        {"response_id": "r2", "rater_id": "a", "stage": "E1"},
        {"response_id": "r2", "rater_id": "b", "stage": "E5"},
    ]
    triage = triage_disagreements(agreement_report(scorings))
    assert triage["serious_count"] == 1
    assert triage["adjacent_count"] == 1
    assert triage["resolve_first"][0]["response_id"] == "r2"
    assert triage["boundary_pairs_needing_sharper_anchors"][0]["between"] == ["E2", "E3"]


def test_the_module_states_what_still_needs_people():
    described = describe_psychometrics()
    joined = " ".join(described["what_still_needs_humans"])
    assert "访谈" in joined and "第二位评分者" in joined


# ═════════════════════════════════════════════════════════════════════════════
# 事故演练
# ═════════════════════════════════════════════════════════════════════════════

def test_a_production_drill_is_refused():
    with pytest.raises(DrillRefused):
        build_drill_plan(mode="PRODUCTION")


def test_a_sev1_plan_covers_containment_recall_and_postmortem():
    plan = build_drill_plan(severity="SEV1")
    ids = {step["id"] for step in plan["steps"]}
    assert {"CONTAIN", "RECALL", "RECOMPUTE", "POSTMORTEM"} <= ids
    assert plan["containment_posture"] == "PRIVATE_MODE_ONLY"


def test_a_dry_run_never_claims_the_switch_was_pulled():
    """演练工具最容易骗人的地方就在这里。"""
    drill = run_drill(severity="SEV1", mode="DRY_RUN")
    assert drill["verdict"] == "DRY_RUN_ONLY"
    assert drill["complete"] is False
    assert "不证明系统真的被熔断过" in drill["honest_note"]


def test_unconfirmed_human_steps_come_back_as_needs_human():
    drill = run_drill(severity="SEV1", mode="STAGING")
    assert set(drill["steps_needing_human_confirmation"]) == {
        "IDENTIFY_SCOPE", "RECOMPUTE", "NOTIFY", "REOPEN", "POSTMORTEM",
    }
    assert drill["verdict"] == "INCOMPLETE"


def test_a_fully_confirmed_staging_drill_passes():
    human_steps = [step["id"] for step in DRILL_STEPS if not step["verifiable"]]
    drill = run_drill(
        severity="SEV1", mode="STAGING",
        step_durations={step["id"]: step["target_minutes"] for step in DRILL_STEPS},
        human_confirmations={step: True for step in human_steps},
        conducted_by="ethan",
    )
    assert drill["verdict"] == "PASS"
    assert drill["complete"] is True
    assert drill["durations_were_simulated"] is False


def test_a_slow_step_is_reported_rather_than_rounded_away():
    drill = run_drill(
        severity="SEV1", mode="STAGING",
        step_durations={"CONTAIN": 120},
        human_confirmations={step["id"]: True for step in DRILL_STEPS if not step["verifiable"]},
    )
    assert "CONTAIN" in drill["steps_over_target"]
    assert drill["verdict"] == "SLOW"


def test_private_mode_only_turns_off_sharing_but_keeps_data_readable():
    effects = containment_effects("PRIVATE_MODE_ONLY")
    assert effects["flags"]["sharing_allowed"] is False
    assert effects["flags"]["group_features_allowed"] is False
    assert effects["flags"]["existing_data_readable"] is True
    assert effects["reversible"] is True


def test_full_kill_is_the_only_irreversible_posture():
    assert containment_effects("FULL_KILL")["reversible"] is False
    for posture in CONTAINMENT_POSTURES:
        assert containment_effects(posture)["requires_signoff_to_lift"] is True


def test_the_containment_posture_matches_what_the_pilot_gate_actually_enforces():
    """演练宣称的效果必须与运行期真的会发生的事一致。"""
    from formation_twin.emotional_maturity_pilot_gate import capabilities

    flags = containment_effects("PRIVATE_MODE_ONLY")["flags"]
    live = capabilities(flags["assurance_profile"])
    assert live["sharing_allowed"] == flags["sharing_allowed"]
    assert live["group_features_allowed"] == flags["group_features_allowed"]


def test_the_postmortem_step_demands_a_failing_test():
    step = next(item for item in DRILL_STEPS if item["id"] == "POSTMORTEM")
    assert "能失败的测试" in step["check"]


def test_drill_description_is_honest_about_production():
    assert describe_drill()["production_is_refused"] is True


# ═════════════════════════════════════════════════════════════════════════════
# 隐私影响评估
# ═════════════════════════════════════════════════════════════════════════════

def test_the_inventory_is_derived_from_the_migrations():
    inventory = build_data_inventory()
    assert inventory["table_count"] >= 70
    assert inventory["personal_table_count"] >= 70
    assert inventory["derived_from"].endswith("*.sql")


def test_religious_and_family_material_is_marked_special_category():
    inventory = build_data_inventory()
    by_table = {entry["table"]: entry for entry in inventory["tables"]}
    assert by_table["formation_twin_emd_prayer_routings"]["special_category"] is True
    assert by_table["formation_twin_emd_genograms"]["category"] == "FAMILY_HISTORY"
    assert by_table["formation_twin_emd_grief_sessions"]["special_category"] is True


def test_shared_catalogues_are_not_treated_as_personal():
    inventory = build_data_inventory()
    by_table = {entry["table"]: entry for entry in inventory["tables"]}
    assert by_table["formation_twin_emd_items"]["personal"] is False
    assert by_table["formation_twin_emd_items"]["category"] == "SHARED_CATALOGUE"


def test_every_category_declares_a_purpose():
    for entry in build_data_inventory()["tables"]:
        assert entry["purpose"], entry["table"]


def test_both_regimes_are_mapped_when_both_apply():
    assessment = build_privacy_assessment(jurisdictions=["CN", "EU"])
    regimes = {entry["regime"] for entry in assessment["applicable_provisions"]}
    assert regimes == {"PIPL", "GDPR"}


def test_only_the_relevant_regime_is_mapped_for_a_single_jurisdiction():
    assessment = build_privacy_assessment(jurisdictions=["CN"])
    assert {entry["regime"] for entry in assessment["applicable_provisions"]} == {"PIPL"}


def test_the_assessment_refuses_to_call_itself_complete():
    """自动生成的清单不是评估。这条防的就是把草稿当成交付物归档。"""
    assessment = build_privacy_assessment()
    assert assessment["status"] == "DRAFT_PENDING_LEGAL_REVIEW"
    assert assessment["may_be_filed_as_complete"] is False
    assert all(
        question["status"] == "NEEDS_LEGAL_REVIEW"
        for question in assessment["outstanding_legal_questions"]
    )


def test_the_hard_questions_are_named_not_glossed():
    ids = {question["id"] for question in LEGAL_QUESTIONS}
    assert {"LAWFUL_BASIS", "MINORS", "CROSS_BORDER", "RETENTION", "PASTORAL_ACCESS"} <= ids
    for question in LEGAL_QUESTIONS:
        assert question["why_human"], question["id"]


def test_consent_freeness_is_flagged_as_a_judgement_call():
    """牧养关系里的权力不对等会影响同意是否「自由给出」——那是判断，不是配置。"""
    basis = next(q for q in LEGAL_QUESTIONS if q["id"] == "LAWFUL_BASIS")
    assert "权力不对等" in basis["why_human"]


def test_implemented_controls_each_point_at_evidence():
    for control in build_privacy_assessment()["implemented_controls"]:
        assert control["evidence"], control["control"]


def test_automated_decision_limits_are_mapped_to_the_forbidden_use_tier():
    assessment = build_privacy_assessment(jurisdictions=["EU"])
    art22 = next(e for e in assessment["applicable_provisions"] if e["article"] == "Art. 22")
    assert "高影响用途" in art22["engages"]


def test_special_categories_cover_the_material_that_actually_worried_us():
    assert {"RELIGIOUS_BELIEF", "CRISIS_AND_SAFETY", "FAMILY_HISTORY"} <= SPECIAL_CATEGORIES


def test_description_lists_both_regimes():
    assert set(describe_privacy_assessment()["regimes"]) == {"PIPL", "GDPR"}


# ═════════════════════════════════════════════════════════════════════════════
# 自审：这一轮在自己新写的代码里查出的 bug
# ═════════════════════════════════════════════════════════════════════════════

def test_a_system_field_cannot_dodge_the_validator_by_being_named_like_a_user_field():
    """First version matched substrings, so `accepted_stage`, `notes_from_system` and
    `echo_verdict` all counted as "user wrote this" and skipped the language check.
    A validator you can bypass by choosing a field name is not a validator."""
    from formation_twin.emotional_maturity_presentation import validate_ui_payload

    claim = "你的情感成熟度得分为 72 分"
    for field in ("accepted_stage", "notes_from_system", "echo_verdict", "summary"):
        assert validate_ui_payload({field: claim})["valid"] is False, field
    # 真正的用户字段仍然放行
    assert validate_ui_payload({"life_season": claim})["valid"] is True


def test_nested_user_content_is_still_recognised():
    from formation_twin.emotional_maturity_presentation import validate_ui_payload

    payload = {"accepted": {"life_season": "告诉我总分"}, "items": [{"note": "我的总分呢"}]}
    assert validate_ui_payload(payload)["valid"] is True
    assert len(validate_ui_payload(payload)["skipped_user_content"]) == 2


def test_negative_kappa_is_not_reported_as_slight_agreement():
    """κ = -1.0 means the raters are systematically opposite. Calling that "SLIGHT"
    reads as "a little agreement" — the opposite of the truth."""
    from formation_twin.emotional_maturity_psychometrics import agreement_report, interpret_kappa

    assert interpret_kappa(-1.0) == "SYSTEMATIC_DISAGREEMENT"
    report = agreement_report([
        {"response_id": "r1", "rater_id": "a", "stage": "E1"},
        {"response_id": "r1", "rater_id": "b", "stage": "E2"},
        {"response_id": "r2", "rater_id": "a", "stage": "E2"},
        {"response_id": "r2", "rater_id": "b", "stage": "E1"},
    ])
    assert report["cohens_kappa"] < 0
    assert report["kappa_interpretation"] == "SYSTEMATIC_DISAGREEMENT"
    assert report["status"] == "BLOCKED"
    assert "系统性相反" in report["next_action"]


@pytest.mark.parametrize("text", [
    "我不想活了", "我想自杀", "他昨天又打我", "我被他打了",
    "他掐我脖子", "他对我动手", "他威胁说要杀了我", "我活不下去了",
])
def test_real_harm_is_still_sealed_safety(text):
    from formation_twin.emotional_maturity_training_optout import classify_material

    assert classify_material(field="notes", text=text)["sensitivity"] == "P4_SEALED_SAFETY"


@pytest.mark.parametrize("text", [
    "他动手做饭", "会议记录：动手能力评估", "打我电话", "我打了个电话",
    "这个项目我们动手早", "想死你了",
])
def test_ordinary_uses_of_violent_sounding_words_are_not_crisis(text):
    """Over-classification is not free: if `动手做饭` is P4, real P4 drowns in noise and
    perfectly ordinary text can never be sent for model-assisted tidying."""
    from formation_twin.emotional_maturity_training_optout import classify_material

    assert classify_material(field="notes", text=text)["sensitivity"] != "P4_SEALED_SAFETY"


def test_there_is_exactly_one_ddl_parser():
    """The privacy inventory used to carry its own copy. Two parsers under a privacy
    check is how a coverage gap gets built."""
    from pathlib import Path as _Path

    backend = _Path(__file__).resolve().parents[1]
    inline_parsers = []
    for relative in (
        "formation_twin/emotional_maturity_privacy_assessment.py",
        "tests/emd_schema_catalog.py",
    ):
        text = (backend / relative).read_text(encoding="utf-8")
        if "CREATE TABLE (?:IF NOT EXISTS )?" in text:
            inline_parsers.append(relative)
    assert inline_parsers == [], f"second DDL parser found in {inline_parsers}"

    from core.schema_catalog import catalog as shared
    from formation_twin.emotional_maturity_privacy_assessment import build_data_inventory

    inventory = {entry["table"]: entry["personal"] for entry in build_data_inventory()["tables"]}
    for table, personal in inventory.items():
        assert personal == ("email" in shared()[table]), table
