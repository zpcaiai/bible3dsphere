"""Worldview Formation OS — optional OpenAI semantic-enhancement layer tests.

Contract under test (no DB, no network — LLM is monkeypatched):
  * Degrades cleanly: when the LLM returns None, output == deterministic output.
  * Prose-only merge: AI may overwrite whitelisted prose fields ONLY; scripture
    refs / bible persons / doctrine tags / scores are NEVER overwritten by AI.
  * Crisis-first: a high/imminent suffering input NEVER invokes the LLM.
"""
import pytest

import worldview_llm as llm
import truth_mapper_engine as tm
import worldview_diagnoser_engine as diag
import narrative_engine as narr
import suffering_engine as se

pytestmark = pytest.mark.no_db


def test_degrades_when_enhance_returns_none(monkeypatch):
    monkeypatch.setattr(llm, "enhance", lambda *a, **k: None)
    txt = "如果我不能赚很多钱，我的人生就失败了。"
    base = diag.diagnose(text=txt, use_ai=False)
    aied = diag.diagnose(text=txt, use_ai=True)
    assert aied == base
    assert "source" not in aied


def test_truth_map_merges_prose_only_and_protects_scripture(monkeypatch):
    fake = {
        "biblicalTruth": "AI润色后的真理",
        "gospelReframe": "AI润色后的福音重构",
        # 这些是 AI 试图“越权”覆盖的字段 —— 必须被忽略：
        "scriptureRefs": ["伪造9:9"],
        "recommendedBiblePersons": ["虚构人物"],
        "doctrineTags": ["fabricated"],
    }
    monkeypatch.setattr(llm, "enhance", lambda *a, **k: fake)
    base = tm.map_one(domain="money", idol_category="money", lie="金钱是我的安全感来源。", use_ai=False)
    out = tm.map_one(domain="money", idol_category="money", lie="金钱是我的安全感来源。", use_ai=True)

    # prose 被合并
    assert out["biblicalTruth"] == "AI润色后的真理"
    assert out["gospelReframe"] == "AI润色后的福音重构"
    assert out["source"] == "ai"
    # 经文 / 人物 / 教义 受保护，绝不被 AI 覆盖
    assert out["scriptureRefs"] == base["scriptureRefs"]
    assert "伪造9:9" not in out["scriptureRefs"]
    assert "太6:19-34" in out["scriptureRefs"]
    assert out["recommendedBiblePersons"] == base["recommendedBiblePersons"]
    assert out["doctrineTags"] == base["doctrineTags"]


def test_narrative_merges_prose_keeps_scripture(monkeypatch):
    fake = {"newNarrative": "AI 新叙事", "gospelTruth": "AI 福音真理",
            "scriptureRefs": ["伪造1:1"]}
    monkeypatch.setattr(llm, "enhance", lambda *a, **k: fake)
    base = narr.rewrite(raw_text="我必须超过别人，否则我就是失败者。", idol_category="success", use_ai=False)
    out = narr.rewrite(raw_text="我必须超过别人，否则我就是失败者。", idol_category="success", use_ai=True)
    assert out["newNarrative"] == "AI 新叙事"
    assert out["gospelTruth"] == "AI 福音真理"
    assert out["scriptureRefs"] == base["scriptureRefs"]
    assert "伪造1:1" not in out["scriptureRefs"]


def test_suffering_engine_bypasses_worldview_llm(monkeypatch):
    # suffering 现在走 llm_provider（带 theological_safety + Mock 兜底），
    # 不经过本 prose 增强层；worldview_llm.enhance 不应被调用，且危机安全契约成立。
    calls = []
    monkeypatch.setattr(llm, "enhance", lambda *a, **k: (calls.append(1), {"x": 1})[1])
    r = se.analyze_suffering("u@test.com", "我不想活了，今晚就想结束这一切。")
    assert calls == []                       # 未触达 worldview_llm
    assert r["is_crisis"] is True
    assert r["requires_real_person"] is True
    assert r["real_person_actions"]


def test_available_and_meta_never_raise():
    assert isinstance(llm.available(), bool)
    m = llm.meta()
    assert isinstance(m.get("available"), bool)
    assert "经文" in m.get("note", "")


# ── structured AI (generate_json + schemas) ──────────────────────────────────
def test_diagnoser_structured_maps_into_contract(monkeypatch):
    monkeypatch.setattr(llm, "generate_structured", lambda system, payload, name, **k: {
        "summary": "结构化AI总结",
        "dominant_distortions": ["技术救世主义"],
        "renewal_focus": ["安息"],
        "risk_level": "medium",
        "findings": [{
            "dimension_code": "technology", "expressed_belief": "AI 决定我的未来",
            "belief_type": "implicit", "distortion_type": "技术救世",
            "biblical_counter_truth": "神掌权", "scripture_anchors": ["诗20:7"],
            "evidence": "AI 会淘汰我", "confidence": 0.8, "recommended_practices": ["安息"],
        }],
    } if name == "WorldviewAgentOutput" else None)
    r = diag.diagnose(text="我最近很焦虑，觉得 AI 会淘汰我，如果我不能赚很多钱，我的人生就失败了。", use_ai=True)
    assert r["profileSummary"] == "结构化AI总结"
    ai_beliefs = [b for b in r["extractedBeliefs"] if b.get("source") == "ai"]
    assert any(b["beliefStatement"] == "AI 决定我的未来" for b in ai_beliefs)
    assert r["dimensionScores"]                       # 评分仍确定性
    assert "技术救世主义" in r["dominantPatterns"]


def test_truth_mapper_structured_keeps_canonical_scripture(monkeypatch):
    monkeypatch.setattr(llm, "generate_structured", lambda system, payload, name, **k: {
        "primary_theme": "安全感", "risk_level": "medium", "summary": "映射AI总结",
        "findings": [{
            "category": "money", "finding_type": "idolatry", "title": "金钱偶像",
            "description": "AI重构文字", "severity": 4, "confidence": 0.8,
            "possible_root": "恐惧", "gospel_truth": "神是供应者AI",
            "scripture_anchors": ["腓4:19"], "recommended_practice_types": ["奉献"],
            "requires_pastor_attention": False, "risk_level": "medium",
        }],
    } if name == "DiagnosisAgentOutput" else None)
    res = tm.map_beliefs([{"domain": "money", "beliefStatement": "金钱是我的安全感来源。",
                           "idolHint": "money"}], use_ai=True)
    m = res["mappings"][0]
    assert m["biblicalTruth"] == "神是供应者AI"
    assert m["gospelReframe"] == "AI重构文字"
    assert m["severity"] == 4 and m.get("source") == "ai"
    assert m["scriptureRefs"][0] == "太6:19-34"        # canonical 在前
    assert "腓4:19" in m["scriptureRefs"]              # AI 经文并入不覆盖
    assert "约瑟" in m["recommendedBiblePersons"]       # 人物保持确定性
    assert res.get("source") == "ai"


def test_structured_degrades_offline(monkeypatch):
    # 离线（无真实 provider）：generate_structured 返回 None，输出 == 确定性
    monkeypatch.setattr(llm, "generate_structured", lambda *a, **k: None)
    monkeypatch.setattr(llm, "enhance", lambda *a, **k: None)
    base = diag.diagnose(text="如果我不能赚很多钱，我的人生就失败了。", use_ai=False)
    aied = diag.diagnose(text="如果我不能赚很多钱，我的人生就失败了。", use_ai=True)
    assert aied == base
