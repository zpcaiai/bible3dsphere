"""Worldview Formation OS (Kingdom Lens OS) — stateless engine test suite.

Covers the spec's validation cases for all 10 agents. These tests do not touch
the database, so they are marked ``no_db``.

Safety contract under test:
  * Crisis-first: high/imminent risk skips ALL theological analysis.
  * Suffering high-risk never emits suffering-type classification.
  * Formation never issues heavy plans to crisis/burnout users.
"""
import pytest

import worldview_orchestrator as orch
import worldview_diagnoser_engine as diag
import idolatry_engine as idol
import truth_mapper_engine as tm
import narrative_engine as narr
import apologetics_engine as apol
import cultural_engine as culture
import vocation_worldview_engine as vocation
import suffering_engine as suffering
import decision_formation_engine as decision
import formation_practice_engine as practice

pytestmark = pytest.mark.no_db


# ── Agent 1: Worldview Diagnoser ──────────────────────────────────────────────
def test_diagnoser_detects_four_domains():
    r = diag.diagnose(text="我最近很焦虑，觉得 AI 会淘汰我，如果我不能赚很多钱，我的人生就失败了。")
    got = set(r["detectedDomains"])
    assert {"technology", "money", "self", "work"} <= got
    for a in ("idol_detector", "biblical_truth_mapper", "vocation_worldview"):
        assert a in r["recommendedNextAgents"]


def test_diagnoser_scores_lower_when_distorted():
    r = diag.diagnose(text="如果我不能赚很多钱，我的人生就失败了。")
    money = [s for s in r["dimensionScores"] if s["domain"] == "money"]
    assert money and money[0]["score"] < 60


# ── Agent 2: Idol Detector (13 types) ─────────────────────────────────────────
def test_idol_types_extended_to_13():
    assert len(idol.IDOL_TYPES) == 13
    for t in ("knowledge", "technology", "self_realization",
              "national_political", "victimhood", "power"):
        assert t in idol.IDOL_INDEX


# ── Agent 3: Biblical Truth Mapper ────────────────────────────────────────────
def test_truth_map_money():
    m = tm.map_one(domain="money", idol_category="money", lie="金钱是我的安全感来源。")
    assert "太6:19-34" in m["scriptureRefs"]
    assert "约瑟" in m["recommendedBiblePersons"]


# ── Agent 4: Narrative Rewriter ───────────────────────────────────────────────
def test_narrative_achievement_rewrite():
    n = narr.rewrite(raw_text="我必须在事业上超过别人，否则我就是失败者。",
                     idol_category="success", domain="work")
    assert n["hiddenIdol"] == "success"
    assert len(n["practicePlan"]) >= 3


# ── Agent 5: Apologetics Lens ─────────────────────────────────────────────────
def test_apologetics_ai_presuppositions():
    a = apol.analyze("从圣经世界观看，AI 终局应该怎么看？")
    assert a["topic"] == "technology_ai"
    assert any("救世" in p or "智能" in p for p in a["detectedPresuppositions"])
    assert any("救主" in c or "恐惧" in c for c in a["pastoralCautions"])
    assert "vocation_worldview" in a["recommendedNextAgents"]


# ── Agent 6: Cultural Discernment ─────────────────────────────────────────────
def test_culture_techno_salvationism():
    c = culture.discern("现在 AI 发展太快了，不跟上就会被淘汰，我必须拼命学习所有 AI 工具。")
    assert any("技术救世" in s for s in c["detectedSpirits"])
    assert any("安息" in p for p in c["counterPractices"])


# ── Agent 7: Vocation Worldview ───────────────────────────────────────────────
def test_vocation_ai_product_idols_and_risks():
    v = vocation.analyze("我想做 AI 属灵产品，但也很想快速赚钱，证明自己。")
    assert "success" in v["possibleIdols"] and "money" in v["possibleIdols"]
    assert any("操控" in r or "依赖" in r for r in v["ethicalRisks"])
    assert "decision_formation" in v["recommendedNextAgents"]


# ── Agent 8: Suffering Theology (SAFETY-CRITICAL) ─────────────────────────────
def test_suffering_imminent_floors_to_crisis_with_real_help():
    # 新版 suffering_engine：detect_crisis 兜底抬高风险；高危必含真实求助步骤。
    r = suffering.analyze_suffering("u@test.com", "我不想活了，今晚就想结束这一切。")
    assert r["risk_level"] in ("high", "critical")
    assert r["is_crisis"] is True
    assert r["requires_real_person"] is True
    assert r["real_person_actions"]                      # 绝不只给经文
    joined = "".join(r["real_person_actions"])
    assert any(k in joined for k in ("联系", "牧者", "紧急", "危机"))


def test_suffering_low_risk_not_crisis():
    r = suffering.analyze_suffering("u@test.com", "我努力创业很久还是失败，很灰心。")
    assert r["risk_level"] in ("low", "medium")
    assert r["is_crisis"] is False
    assert "disclaimer" in r and "AI 不是牧者" in r["disclaimer"]


# ── Agent 9: Decision Formation ───────────────────────────────────────────────
def test_decision_counsel_recommended():
    d = decision.analyze("我要不要全职做 AI 属灵星球？", "我很想快速成功，也怕错过窗口。", urgency="high")
    assert d["counselNeeded"] is True
    assert len(d["wisdomQuestions"]) >= 5
    assert d["nextFaithfulStep"]


# ── Agent 10: Formation Practice ──────────────────────────────────────────────
def test_practice_seven_day_plan():
    p = practice.generate_plan(focus_idols=["success", "control"], duration_days=7, intensity="normal")
    for kw in ("成就", "控制", "交托", "忠心"):
        assert kw in p["planTitle"]
    assert sorted({t["day"] for t in p["tasks"]}) == list(range(1, 8))
    for need in ("daily_meditation", "sabbath_rest", "anti_idol", "repentance_prayer", "service"):
        assert need in p["selectedPractices"]
    assert any("表现主义" in w for w in p["warningSigns"])


def test_practice_crisis_downgrades_to_gentle():
    p = practice.generate_plan(focus_idols=["success"], duration_days=30,
                               intensity="deep", safety={"crisis": True})
    assert p["intensity"] == "gentle"


# ── Orchestrator: crisis-first guard + closed loop ────────────────────────────
def test_orchestrator_blocks_high_risk():
    safe, a = orch.crisis_guard("我不想活了，今晚就想结束这一切。")
    assert safe is False
    assert a["crisisRiskLevel"] in ("high", "imminent")
    assert a["recommendedNextAgents"] == ["suffering_theology"]


def test_orchestrator_idols_derived_from_diagnosis():
    # 闭环：未传 signals 时，idols 仍应来自诊断信念的 idolHint（而非恒为空）。
    res = orch.run_pipeline(user_id="u1", text="如果我不能赚很多钱，我的人生就失败了。")
    assert "idol_detector" in res["stagesRun"]
    targets = (res.get("idols") or {}).get("suggestedTargets", [])
    assert "success" in targets or "money" in targets


def test_orchestrator_runs_full_loop_on_normal_text():
    res = orch.run_pipeline(user_id="u1", text="如果我不能赚很多钱，我的人生就失败了。AI 也让我害怕被淘汰。")
    assert res["blocked"] is False
    assert "worldview_diagnoser" in res["stagesRun"]
    assert "biblical_truth_mapper" in res["stagesRun"]
    assert "narrative_rewriter" in res["stagesRun"]
    assert res["narrative"]["hiddenIdol"] in ("success", "money", "technology")
