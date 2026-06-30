"""Worldview Formation OS — persistence wiring tests (no real DB).

Uses a fake DB connection/cursor that records every (sql, params) so we can assert
the structured-AI fields actually reach the worldview tables:
  * worldview_beliefs  ← biblical_evaluation (biblicalCounterTruth) + related_scripture_refs
  * distorted_beliefs  ← severity + gospel_reframe + scripture_refs + requires_pastor_attention
"""
import types

import pytest

from routers import worldview as wv

pytestmark = pytest.mark.no_db


class _FakeCursor:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.log.append((sql, params))

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _FakeConn:
    def __init__(self):
        self.log = []

    def cursor(self):
        return _FakeCursor(self.log)

    def commit(self):
        pass

    def rollback(self):
        pass


def _init(fake):
    wv.init_worldview_router(
        get_db=lambda: fake,
        release_db=lambda c: None,
        get_session_user=lambda r: {"email": "u@test.com"},
        to_shanghai_iso=lambda x: str(x),
    )


def _find(log, table):
    return [(s, p) for (s, p) in log if f"INSERT INTO {table} " in s]


def _param_text(params):
    parts = []
    for item in params:
        parts.append(str(getattr(item, "adapted", item)))
    return " ".join(parts)


def test_diagnosis_persists_ai_belief_fields():
    fake = _FakeConn()
    _init(fake)
    body = types.SimpleNamespace(text="AI 会淘汰我", source_type="journal")
    result = {
        "crisis": {"riskLevelRaw": "green"},
        "idols": {"suggestedTargets": []},
        "diagnosis": {
            "detectedDomains": ["technology"],
            "dimensionScores": [{"domain": "technology", "score": 36.0,
                                 "confidence": 0.6, "evidence": [], "explanation": "x"}],
            "extractedBeliefs": [{
                "domain": "technology", "beliefStatement": "AI 决定我的未来",
                "status": "distorted", "confidence": 0.8, "evidence": "AI 会淘汰我",
                "emotionalFruit": [], "behavioralFruit": [],
                "biblicalCounterTruth": "神掌权，技术不是救主", "scriptureAnchors": ["诗20:7"],
            }],
            "overallScore": 40.0, "profileSummary": "s",
        },
    }
    wv._persist_diagnosis("u@test.com", body, result)

    beliefs = _find(fake.log, "worldview_beliefs")
    assert beliefs, "no worldview_beliefs insert recorded"
    sql, params = beliefs[0]
    assert "biblical_evaluation" in sql and "related_scripture_refs" in sql
    flat = _param_text(params)
    assert "神掌权，技术不是救主" in flat        # biblicalCounterTruth → biblical_evaluation
    # scriptureAnchors → related_scripture_refs (JSONB; sandbox _Json fallback escapes unicode)
    assert "20:7" in flat


def test_truthmap_persists_ai_mapping_fields():
    fake = _FakeConn()
    _init(fake)
    beliefs = [{"domain": "money", "beliefStatement": "金钱是我的安全感来源。", "idolHint": "money"}]
    mappings = [{
        "lieStatement": "金钱是我的安全感来源。",
        "biblicalTruth": "神是供应者AI", "gospelReframe": "AI重构文字",
        "scriptureRefs": ["太6:19-34", "腓4:19"], "severity": 4,
        "requiresPastorAttention": True, "possibleRoot": "恐惧",
        "practiceSuggestions": ["奉献"],
    }]
    wv._persist_distortions("u@test.com", beliefs, mappings)

    rows = _find(fake.log, "distorted_beliefs")
    assert rows, "no distorted_beliefs insert recorded"
    sql, params = rows[0]
    for col in ("severity", "gospel_reframe", "scripture_refs",
                "requires_pastor_attention", "possible_root"):
        assert col in sql, f"missing column {col}"
    assert 4 in params                            # severity from mapping
    flat = _param_text(params)
    assert "AI重构文字" in flat                    # gospelReframe → gospel_reframe (plain str)
    # scripture_refs persisted as JSONB (escape-robust check: punctuation survives)
    assert "6:19-34" in flat and "4:19" in flat
    assert "恐惧" in flat                          # possible_root (plain str)


def test_audit_omits_bigserial_id():
    # 回归：agent_runs.id 是 BIGSERIAL，_audit 不得显式传 id（否则插入失败、审计静默丢失）。
    fake = _FakeConn()
    _init(fake)
    wv._audit("u@test.com", "worldview_diagnoser", {"a": 1}, {"b": 2})
    runs = _find(fake.log, "agent_runs")
    assert runs, "no agent_runs insert recorded"
    sql, params = runs[0]
    assert sql.split("VALUES")[0].strip().startswith("INSERT INTO agent_runs (email")
    assert "id," not in sql.split("VALUES")[0]      # 不含 id 列
    assert params[0] == "u@test.com" and len(params) == 7
