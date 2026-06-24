"""Gift & Calling OS — 恩赐与呼召识别引擎 无库单测。

只测确定性核心（use_ai=False）与聚合形状；不触库，标记 ``no_db``。

护栏契约（受测）：
  * 永远返回完整报告（八段）且分数 0~100。
  * 恩赐高但相关果子低时，gift_fruit_alignment 必须标记风险（恩赐≠成熟）。
  * 误用风险随高分恩赐/优势出现，并附福音重构与操练。
  * 报告恒含身份提醒与神学边界。
"""
import json

import pytest

import gift_calling_engine as e

pytestmark = pytest.mark.no_db


# 与产品文档一致的"系统建造/护教学"画像样例
APOLOGIST = {
    "experiences": "长期构建属灵OS系统，整合神学、AI、哲学，做课程和知识图谱，写代码(java/python)做产品架构。",
    "interests": "反复关注护教学、世界观、AI终局、哲学错误、启示录，喜欢辨析谬误。",
    "service": "在小组做查经分享、讲道辅助、带人理解教义。",
    "others_say": "别人常请我讲解圣经、设计课程、分辨观点对不对。",
    "burdens": "为慕道友、青年信徒、AI时代迷茫的知识分子付代价。",
    "skills": "AI工具、Java架构、课程设计、写作、产品设计。",
    "struggles": "压力下容易先看到别人逻辑漏洞、显得尖锐、急躁、有点控制。",
    "faith_journey": "稳定灵修祷告，参加教会。",
}

_SECTIONS = ("strength_profile", "spiritual_gifts", "fruit_scores", "calling_patterns",
             "community_confirmation", "misuse_risks", "ministry_matches", "growth_plan")


def test_report_shape_and_score_bounds():
    r = e.assess(APOLOGIST, use_ai=False)
    assert r["source"] == "heuristic"
    for sec in _SECTIONS:
        assert sec in r, f"missing section {sec}"
    # 所有分数 0~100
    for grp in ("strength_profile", "spiritual_gifts", "fruit_scores"):
        for k, v in r[grp]["scores"].items():
            assert 0 <= v <= 100, (grp, k, v)
    assert 0 <= r["misuse_risks"]["overall_risk_score"] <= 100
    # JSON 可序列化（落库为 JSONB）
    json.dumps(r, ensure_ascii=False)


def test_identity_and_boundary_always_present():
    r = e.assess({}, use_ai=False)
    assert r["identity_reminder"]
    assert r["boundary_notice"]
    # 资料极少 → 置信度 low，但仍返回完整报告
    assert r["confidence"] == "low"
    for sec in _SECTIONS:
        assert sec in r


def test_apologist_profile_detects_teaching_and_discernment():
    r = e.assess(APOLOGIST, use_ai=False)
    gift_keys = {g["key"] for g in r["spiritual_gifts"]["likely_gifts"]}
    assert "teaching" in gift_keys
    assert "discernment" in gift_keys
    # 使命主题应落在护教学辨析型
    assert r["calling_patterns"]["primary_pattern"] == "护教学辨析型"
    # 顶级服事方向应与护教/课程相关
    assert "护教" in r["ministry_matches"]["top_ministry"] or \
           "课程" in r["ministry_matches"]["top_ministry"]


def test_high_gift_low_fruit_flags_alignment_risk():
    """恩赐强但果子证据弱时，gift_fruit_alignment 必须给出 current_risk。"""
    inp = {"experiences": "教导 讲道 查经 课程 释经 系统神学 知识",
           "struggles": "我很急躁，常压迫人，咄咄逼人，记仇，冷漠，尖锐"}
    r = e.assess(inp, use_ai=False)
    aligns = r["fruit_scores"]["gift_fruit_alignment"]
    assert aligns, "expected gift_fruit_alignment entries"
    assert any(a.get("current_risk") for a in aligns)
    # 低果子应拉低均分
    assert r["fruit_scores"]["average_score"] < 60


def test_misuse_risks_have_gospel_reframe_and_practice():
    r = e.assess(APOLOGIST, use_ai=False)
    top = r["misuse_risks"]["top_risks"]
    assert top, "expected at least one top risk"
    for risk in top:
        assert risk.get("gospel_reframe")
        assert risk.get("practice")
        assert 0 <= risk["score"] <= 100
    # 知识型画像应浮现"知识骄傲"或"批判强于建造"
    risk_names = {x["risk"] for x in top}
    assert ("知识骄傲" in risk_names) or ("批判强于建造" in risk_names)


def test_ministry_levels_are_valid_and_gated_by_fruit():
    r = e.assess(APOLOGIST, use_ai=False)
    mm = r["ministry_matches"]
    all_min = mm["recommended_ministries"] + mm["experimental_ministries"]
    assert all_min
    for m in all_min:
        assert m["level"] in ("A", "B", "C", "D")
        assert 0 <= m["match_score"] <= 100
        assert m["first_step"]
    # top_ministry 始终给出（即使 A 级被果子门槛挡下）
    assert mm["top_ministry"]


def test_growth_plan_has_three_phases():
    r = e.assess(APOLOGIST, use_ai=False)
    plan = r["growth_plan"]["plan_json"]
    for phase in ("30_days", "90_days", "180_days"):
        assert phase in plan
        assert plan[phase].get("theme")
    assert r["growth_plan"]["current_phase"] == "30_days"


def test_community_feedback_aggregation_weighted():
    fbs = [
        {"source_type": "pastor", "scores": {"clarity": 5, "love": 4},
         "confirmed_gifts": ["教导"], "concern_areas": ["过于直接"]},
        {"source_type": "recipient", "scores": {"clarity": 3, "love": 5},
         "confirmed_gifts": ["教导"], "concern_areas": []},
    ]
    agg = e.summarize_community_feedback(fbs)
    assert agg["count"] == 2
    assert "教导" in agg["confirmed_gifts"]
    # 牧者权重(0.35) > 被服事者(0.20)，clarity 加权应偏向牧者的 5
    assert agg["weighted_scores"]["clarity"] > 4.0


def test_meta_and_empty_profile_shapes():
    m = e.meta()
    assert len(m["strengths"]) == 10
    assert len(m["gifts"]) == 15
    assert len(m["fruits"]) == 9
    assert m["identity_reminder"] and m["boundary_notice"]
    ep = e.empty_profile()
    assert ep["has_assessment"] is False
    assert "strength_profile" in ep and "growth_plan" in ep


def test_use_ai_false_is_deterministic():
    a = e.assess(APOLOGIST, use_ai=False)
    b = e.assess(APOLOGIST, use_ai=False)
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == \
           json.dumps(b, ensure_ascii=False, sort_keys=True)
