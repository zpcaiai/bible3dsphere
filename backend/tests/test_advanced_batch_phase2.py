"""
tests/test_advanced_batch_phase2.py — Advanced Batch · Phase 2

Pure-logic tests (no database) for the four new modules:
  M1 LLM Provider Layer · M3 Care Dashboard · M6 Suffering/Crisis · M2 RLS file.

Run:  pytest tests/test_advanced_batch_phase2.py -m no_db
"""
import os
import sys
import json
import datetime as dt

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm_provider as lp           # noqa: E402
import llm_schemas as ls            # noqa: E402
import theological_safety as tsafe  # noqa: E402
import care_engine as ce            # noqa: E402
import suffering_engine as se       # noqa: E402
import diagnosis_agent as da        # noqa: E402

pytestmark = pytest.mark.no_db


# ── Module 1: provider + schemas + safety ───────────────────────────────────
def test_mock_provider_schema_valid_and_low_risk():
    out = lp.generate_json("sys", {"reflection": "只有成功我才觉得有价值"}, ls.DiagnosisAgentOutput)
    assert isinstance(out, ls.DiagnosisAgentOutput)
    assert out.risk_level == "low"
    assert out.findings and out.findings[0].requires_pastor_attention is False


def test_crisis_floor_forces_pastor_attention():
    out = lp.generate_json("sys", {"reflection": "我不想活了，活不下去"}, ls.DiagnosisAgentOutput)
    assert out.risk_level == "critical"
    assert out.findings[0].requires_pastor_attention is True


class _FakeProvider(lp.LLMProvider):
    name = "fake"

    def __init__(self, texts):
        super().__init__()
        self._texts = list(texts)

    def complete(self, messages, *, temperature=0.3, max_tokens=None):
        return lp.ProviderResponse(text=self._texts.pop(0))


def test_generate_json_retries_once_then_succeeds(monkeypatch):
    valid = json.dumps({"primary_theme": "x", "risk_level": "low", "summary": "s", "findings": []})
    fake = _FakeProvider(["this is not json", valid])
    monkeypatch.setattr(lp, "get_provider", lambda *a, **k: fake)
    out = lp.generate_json("sys", {"k": "v"}, ls.DiagnosisAgentOutput)
    assert out.summary == "s" and out.risk_level == "low"


def test_generate_json_raises_after_second_failure(monkeypatch):
    fake = _FakeProvider(["nope", "still nope"])
    monkeypatch.setattr(lp, "get_provider", lambda *a, **k: fake)
    with pytest.raises(lp.LLMValidationError):
        lp.generate_json("sys", {"k": "v"}, ls.DiagnosisAgentOutput)


def test_redaction_hides_secrets_and_shrinks_user_text():
    red = lp._redact({"Authorization": "Bearer abc.def", "x_api_key": "k",
                      "messages": [{"role": "user", "content": "私密" * 100}]})
    assert red["Authorization"] == "***REDACTED***"
    assert red["x_api_key"] == "***REDACTED***"
    assert "redacted len=" in red["messages"][0]["content"]


@pytest.mark.parametrize("text,level", [
    ("everything is fine", "low"),
    ("I feel hopeless and can't go on", "high"),
    ("我想死，不想活了", "critical"),
    ("最近压力有点大", "low"),
])
def test_detect_crisis_levels(text, level):
    assert tsafe.detect_crisis(text)["risk_level"] == level


def test_safety_blocks_red_lines_and_passes_gospel():
    svc = tsafe.TheologicalSafetyService()
    bad = svc.review("你痛苦是因为你信心不足，只要祷告就会立刻好。", agent_name="t", log=False)
    assert bad.verdict == "blocked"
    codes = {f["code"] for f in bad.flags}
    assert "prosperity_faith_blame" in codes
    good = svc.review("在基督里你的身份先于表现被神接纳。", agent_name="t", log=False)
    assert good.verdict == "pass"


def test_safety_blocks_ai_replaces_pastor_claim():
    svc = tsafe.TheologicalSafetyService()
    r = svc.review("放心，AI 可以替代牧者陪你走过危机。", agent_name="t", log=False)
    assert r.verdict == "blocked"


# ── Module 3: care dashboard (fake cursor) ──────────────────────────────────
class _FakeCursor:
    def __init__(self, rows):
        self.rows, self._res = rows, None

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        if "FROM care_signals" in s and "WHERE church_id" in s:
            self._res = [r for r in self.rows if (params[1] or r[-1])]
        elif "COUNT(*) FROM church_members" in s:
            self._res = [(9,)]
        elif "nickname FROM users" in s:
            self._res = [(None,)]
        else:
            self._res = []

    def fetchall(self):
        return [r[:-1] for r in (self._res or [])]

    def fetchone(self):
        return (self._res or [[None]])[0]


def _rows():
    now = dt.datetime(2026, 6, 24, 10, 0)
    # (...9 cols..., leader_visible_test_flag)
    return [
        ("11", "a@x.com", "prayer_request", "medium", "t", "授权摘要", "act", True, now, True),
        ("22", "b@x.com", "crisis_linked", "critical", "t", "危机", "act", True, now, True),
        ("33", "c@x.com", "needs_1on1", "high", "t", "牧者跟进", "act", True, now, False),  # pastor-only
    ]


def test_leader_cannot_see_pastor_only_signal():
    d = ce.build_dashboard(_FakeCursor(_rows()), 1, "small_group_leader")
    assert {i["signal_id"] for i in d["items"]} == {"11", "22"}


def test_pastor_sees_all_and_counts_correct():
    d = ce.build_dashboard(_FakeCursor(_rows()), 1, "pastor")
    assert {i["signal_id"] for i in d["items"]} == {"11", "22", "33"}
    assert d["summary"]["high_risk_count"] == 2  # critical + high
    assert d["summary"]["prayer_requests_count"] == 1


def test_dashboard_leaks_no_private_fields_and_sorts_critical_first():
    d = ce.build_dashboard(_FakeCursor(_rows()), 1, "small_group_leader")
    allowed = {"signal_id", "user_id", "display_name", "signal_level", "signal_type",
               "title", "summary", "suggested_action", "requires_followup",
               "high_touch_notice", "last_updated_at"}
    for it in d["items"]:
        assert set(it) <= allowed
    assert d["items"][0]["signal_level"] == "critical"
    assert d["items"][0]["high_touch_notice"] == ce.HIGH_TOUCH_NOTICE


def test_care_role_gating():
    assert not ce.can_view_care("member")
    assert ce.can_view_care("small_group_leader")
    assert ce.can_view_care("pastor")
    assert ce.is_pastor_level("pastor") and not ce.is_pastor_level("small_group_leader")


# ── Module 6: suffering / crisis ────────────────────────────────────────────
def test_normal_suffering_gives_lament_and_scripture_not_crisis():
    r = se.analyze_suffering("u@x.com", "最近我很痛苦，感觉神很远，不知道为什么经历这些。")
    assert r["is_crisis"] is False
    assert r["analysis"]["scripture_anchors"]
    assert r["analysis"]["care_plan"] is not None


def test_crisis_suffering_names_real_person_never_scripture_only():
    r = se.analyze_suffering("u@x.com", "我不想活了，撑不下去，想伤害自己")
    assert r["is_crisis"] is True
    assert r["risk_level"] in ("high", "critical")
    assert r["real_person_actions"], "crisis must name real-human next steps"


def test_diagnosis_agent_full_path():
    assert da.run_diagnosis("u@x.com", {"reflection": "只有成功才有价值"})["risk_level"] == "low"
    crisis = da.run_diagnosis("u@x.com", {"reflection": "我没有希望了，活不下去"})
    assert crisis["risk_level"] == "critical" and crisis["requires_real_person"]


# ── Module 2: RLS file presence / shape ─────────────────────────────────────
def test_supabase_rls_file_is_present_and_sane():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "supabase_rls.sql")
    assert os.path.exists(path)
    sql = open(path, encoding="utf-8").read()
    assert sql.count("DO $$") == sql.count("END $$")
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "app.current_email()" in sql
    assert "care_signals" in sql and "shared_reports" in sql and "audit_logs" in sql
