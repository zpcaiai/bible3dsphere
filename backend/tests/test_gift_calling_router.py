"""Router integration tests for 恩赐与呼召 (/api/gift) — no real database.

Mirrors test_community_heatmap_resilience: inject fake get_db / release_db /
session-user into the router and call handlers directly. A context-aware
FakeCursor lets us exercise the full persist + assemble paths offline.

Under test:
  * meta exposes the full config + theological boundary.
  * assess runs the engine and persists across all 7 assessment tables,
    commits, and returns the report; auth is enforced; DB errors roll back.
  * profile returns empty_profile when the user has no assessment.
  * assessment/{id} enforces ownership (404 / 403) and reconstructs the report.
  * feedback / review writes return the new id.
"""
import re

import pytest

import gift_calling_engine as engine
from routers import gift_calling as gc
from fastapi import HTTPException

pytestmark = pytest.mark.no_db

USER = {"email": "user@test", "id": 1}


# ── fake psycopg2 connection / cursor ────────────────────────────────────────
class FakeCursor:
    def __init__(self, *, owner_row=None, latest_row=None, assemble=None,
                 fetchall_rows=None, fail_on=None):
        self.calls = []
        self.inserts = []
        self._rid = 0
        self._one = None
        self._all = fetchall_rows or []
        self.owner_row = owner_row
        self.latest_row = latest_row
        self.assemble = assemble or {}
        self.fail_on = fail_on

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        s = " ".join(str(sql).split())
        low = s.lower()
        if self.fail_on and self.fail_on.lower() in low:
            raise RuntimeError("db boom")
        self.calls.append(s)
        mt = re.match(r"insert into (\w+)", low)
        if mt:
            self.inserts.append(mt.group(1))
        if "returning id" in low:
            self._rid += 1
            self._one = (self._rid,)
        elif low.startswith("select email from gift_assessments where id"):
            self._one = self.owner_row
        elif "from gift_assessments where email" in low and "status='completed'" in low.replace(" ", ""):
            self._one = self.latest_row
        elif low.startswith("select id, email, assessment_type"):
            self._one = self.assemble.get("main")
        elif "from strength_profiles where assessment_id" in low:
            self._one = self.assemble.get("strength")
        elif "from fruit_scores where assessment_id" in low:
            self._one = self.assemble.get("fruit")
        elif "from calling_patterns where assessment_id" in low:
            self._one = self.assemble.get("calling")
        elif "from misuse_risks where assessment_id" in low:
            self._one = self.assemble.get("misuse")
        elif "from ministry_matches where assessment_id" in low:
            self._one = self.assemble.get("ministry")
        elif "from growth_plans where assessment_id" in low:
            self._one = self.assemble.get("growth")
        else:
            self._one = None

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def wire(cursor, *, user=USER):
    conn = FakeConn(cursor)
    holder = {"released": 0}

    def get_db():
        return conn

    def release_db(c):
        holder["released"] += 1

    gc.init_gift_calling_router(
        get_db=get_db, release_db=release_db,
        get_session_user=lambda request: user,
        to_shanghai_iso=lambda dt: (dt if isinstance(dt, str) else (dt.isoformat() if dt else None)),
    )
    return conn, holder


# ── meta ─────────────────────────────────────────────────────────────────────
def test_meta_exposes_full_config():
    wire(FakeCursor())
    out = gc.get_meta()
    assert out["ok"] is True
    assert len(out["strengths"]) == 10
    assert len(out["gifts"]) == 15
    assert len(out["fruits"]) == 9
    assert out["boundary_notice"] and out["identity_reminder"]


# ── assess ───────────────────────────────────────────────────────────────────
ASSESS_BODY = gc.AssessBody(
    experiences="长期构建属灵OS，整合神学、AI、哲学，做课程和知识图谱，写代码。",
    interests="护教学、世界观、AI终局、哲学辨析。",
    use_ai=False, theological_boundary_ack=True,
)

ASSESS_TABLES = {
    "gift_assessments", "strength_profiles", "fruit_scores", "calling_patterns",
    "misuse_risks", "ministry_matches", "growth_plans",
}


def test_assess_persists_all_tables_and_commits():
    cur = FakeCursor()
    conn, holder = wire(cur)
    out = gc.post_assess(request=None, body=ASSESS_BODY)
    assert out["ok"] is True
    assert out["assessment_id"] == 1
    assert out["source"] == "heuristic"
    # 写齐 7 张测评表（共同体反馈 / 复盘不在此写）
    assert set(cur.inserts) == ASSESS_TABLES
    assert conn.commits == 1 and conn.rollbacks == 0
    assert holder["released"] == 1
    # 报告八段齐全
    for sec in ("strength_profile", "spiritual_gifts", "fruit_scores", "calling_patterns",
                "misuse_risks", "ministry_matches", "growth_plan"):
        assert sec in out


def test_assess_requires_auth():
    wire(FakeCursor(), user={})  # no email
    with pytest.raises(HTTPException) as ei:
        gc.post_assess(request=None, body=ASSESS_BODY)
    assert ei.value.status_code == 401


def test_assess_rolls_back_on_db_error():
    cur = FakeCursor(fail_on="insert into gift_assessments")
    conn, _ = wire(cur)
    with pytest.raises(HTTPException) as ei:
        gc.post_assess(request=None, body=ASSESS_BODY)
    assert ei.value.status_code == 500
    assert conn.rollbacks == 1 and conn.commits == 0


# ── profile ──────────────────────────────────────────────────────────────────
def test_profile_empty_when_no_assessment():
    wire(FakeCursor(latest_row=None))
    out = gc.get_profile(request=None)
    assert out["ok"] is True
    assert out["profile"]["has_assessment"] is False
    assert "strength_profile" in out["profile"]


# ── assessment/{id} ownership + assemble ─────────────────────────────────────
def _assemble_rows():
    return {
        "main": (7, "user@test", "ai_generated", "completed", "我的恩赐", "概要",
                 {"source": "ai", "spiritual_gifts": {"likely_gifts": [{"gift": "教导", "score": 84}]},
                  "community_confirmation": {"count": 0}, "identity_reminder": "在基督里"},
                 "high", True, None, None),
        "strength": (88, 70, 60, 65, 55, 62, 90, 72, 86, 58,
                     [{"name": "系统思考", "score": 88}], [], [], [], [], "优势概要"),
        "fruit": (70, 65, 60, 55, 62, 68, 64, 58, 66, 63.0,
                  ["仁爱"], ["温柔"], [{"gift_or_strength": "教导", "current_risk": "需温柔"}], [], "果子概要"),
        "calling": ("护教学辨析型", ["系统建造型"], {"apologetics_discernment": 88}, ["关注AI与信仰"],
                    [], ["AI终局"], {"strengths": ["系统思考"]}, "用系统化方法帮助信徒建立世界观。",
                    ["做3次小组分享"], ["需共同体确认"], "使命概要"),
        "misuse": (57, [{"risk": "知识骄傲", "score": 72, "gospel_reframe": "在基督里被接纳", "practice": "先肯定对方"}],
                   {"pride": 72}, ["祷告省察"], ["牧者审核"], ["在基督里被接纳"], ["不愿听反馈"], "风险概要"),
        "ministry": ("护教学课程开发", 88,
                     [{"ministry": "护教学课程开发", "level": "A", "match_score": 88}],
                     [{"ministry": "主日学材料设计", "level": "B"}], [], ["牧者审核"], "服事概要"),
        "growth": (3, "not_started", {"30_days": {"theme": "认识恩赐与盲点"}}, [{"day": "每日", "practice": "省察"}],
                   ["更爱神"], ["以成果衡量价值"], "30_days", "计划概要"),
    }


def test_get_assessment_returns_full_report_for_owner():
    wire(FakeCursor(owner_row=("user@test",), assemble=_assemble_rows()))
    out = gc.get_assessment(request=None, aid=7)
    assert out["ok"] is True
    r = out["report"]
    assert r["strength_profile"]["scores"]["cognitive"] == 88
    assert r["fruit_scores"]["scores"]["love"] == 70
    assert r["calling_patterns"]["primary_pattern"] == "护教学辨析型"
    assert r["misuse_risks"]["overall_risk_score"] == 57
    assert r["ministry_matches"]["top_ministry"] == "护教学课程开发"
    assert r["growth_plan"]["plan_json"]["30_days"]["theme"]
    # spiritual_gifts comes from agent_outputs JSONB
    assert r["spiritual_gifts"]["likely_gifts"][0]["gift"] == "教导"


def test_get_assessment_404_when_missing():
    wire(FakeCursor(owner_row=None))
    with pytest.raises(HTTPException) as ei:
        gc.get_assessment(request=None, aid=999)
    assert ei.value.status_code == 404


def test_get_assessment_403_for_other_user():
    wire(FakeCursor(owner_row=("someone_else@test",)))
    with pytest.raises(HTTPException) as ei:
        gc.get_assessment(request=None, aid=7)
    assert ei.value.status_code == 403


# ── feedback / review writes ─────────────────────────────────────────────────
def test_feedback_submit_returns_id_and_writes_table():
    cur = FakeCursor()
    conn, _ = wire(cur)
    out = gc.post_feedback(request=None, body=gc.FeedbackBody(
        source_type="pastor", scores={"clarity": 5, "love": 4}, confirmed_gifts=["教导"]))
    assert out["ok"] is True and out["id"] == 1
    assert cur.inserts == ["community_feedback"]
    assert conn.commits == 1


def test_feedback_list_returns_aggregate():
    wire(FakeCursor(fetchall_rows=[]))
    out = gc.get_feedback(request=None)
    assert out["ok"] is True
    assert "aggregate" in out and out["count"] == 0


def test_review_submit_returns_id_and_writes_table():
    cur = FakeCursor()
    conn, _ = wire(cur)
    out = gc.post_review(request=None, body=gc.ReviewBody(
        review_type="self_review", observations="服事后弟兄被造就。",
        action_items=[{"action": "下月小组分享", "owner": "user"}]))
    assert out["ok"] is True and out["id"] == 1
    assert cur.inserts == ["review_logs"]
    assert conn.commits == 1
