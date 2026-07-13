"""End-to-end console<->backend contract test (in-memory fake DB).

This drives the *exact* endpoints the Mission OS 工作台 (MissionConsole.jsx) calls,
through the real router + Pydantic + domain-invariant code, without PostgreSQL.
It proves the request/response contract and that domain guards fire, and runs in
any environment. A separate live-DB smoke (scripts/mission_os/migration_smoke.sh)
covers actual migrations + RLS.
"""
import pytest
from fastapi import HTTPException

import routers.mission_fields as fields
import routers.mission_calling as calling
import routers.mission_readiness as readiness
import routers.mission_finance as finance
import routers.mission_deployment as deployment

pytestmark = pytest.mark.no_db


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.conn.sql_log.append(sql)

    def fetchone(self):
        if self.conn.fetchone_queue:
            return self.conn.fetchone_queue.pop(0)
        return ("00000000-0000-0000-0000-000000000001",)

    def fetchall(self):
        if self.conn.fetchall_queue:
            return self.conn.fetchall_queue.pop(0)
        return []


class FakeConn:
    def __init__(self):
        self.sql_log = []
        self.fetchone_queue = []
        self.fetchall_queue = []
        self.committed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeRequest:
    headers = {}


def _wire(mod):
    """Init a router module with an in-memory DB and admin session."""
    conn = FakeConn()
    mod_state_setter = getattr(mod, f"init_{_init_name(mod)}")
    mod_state_setter(
        get_db=lambda: conn,
        release_db=lambda c: None,
        get_session_user=lambda req: {"email": "user@example.org"},
        is_admin=lambda email: True,   # bypass DB permission lookup
    )
    return conn


def _init_name(mod):
    return {
        fields: "mission_fields_router",
        calling: "mission_calling_router",
        readiness: "mission_readiness_router",
        finance: "mission_finance_router",
        deployment: "mission_deployment_router",
    }[mod]


ORG = "church-1"


# ---- Fields panel (Batch 2) ----
def test_console_fields_create_list_assess():
    conn = _wire(fields)
    r = fields.create_field(fields.FieldBody(organizationId=ORG, fieldType="people_group",
                                             canonicalName="Some Group"), FakeRequest())
    assert r["ok"] and r["status"] == "draft"
    conn.fetchall_queue.append([("id1", "people_group", "Some Group", "draft", "unresearched", "unknown", "P1")])
    lst = fields.list_fields(ORG, FakeRequest())
    assert lst["items"][0]["canonicalName"] == "Some Group"
    # assess with a hard block -> blocked recommendation, four independent signals
    conn.fetchone_queue.append(None)  # framework lookup
    a = fields.assess(str("f1"), fields.AssessBody(organizationId=ORG, needScore=1.0, evidenceScore=1.0,
                      readinessScore=1.0, riskLevel="low", hardBlocks=["no_legal_entry_path"]), FakeRequest())
    assert a["status"] == "blocked" and a["recommendation"] != "candidate_for_team_discernment"


def test_console_field_rejects_bad_type():
    _wire(fields)
    with pytest.raises(HTTPException) as e:
        fields.create_field(fields.FieldBody(organizationId=ORG, fieldType="not_a_type",
                                             canonicalName="X"), FakeRequest())
    assert e.value.status_code == 422


# ---- Calling panel (Batch 3) ----
def test_console_calling_create_and_list():
    conn = _wire(calling)
    r = calling.create_journey(calling.JourneyBody(organizationId=ORG, callingOrientation="cross_cultural_mission",
                               fieldInterest="South Asia students"), FakeRequest())
    assert r["status"] == "active_discernment"
    conn.fetchall_queue.append([("j1", "cross_cultural_mission", "South Asia students", "active_discernment", None, None)])
    lst = calling.list_journeys(ORG, FakeRequest())
    assert lst["items"][0]["fieldInterest"] == "South Asia students"


def test_console_calling_rejects_bad_orientation():
    _wire(calling)
    with pytest.raises(HTTPException) as e:
        calling.create_journey(calling.JourneyBody(organizationId=ORG, callingOrientation="nonsense"), FakeRequest())
    assert e.value.status_code == 422


# ---- Readiness panel (Batch 3) ----
def test_console_readiness_create_and_list_exposes_15_dims():
    conn = _wire(readiness)
    r = readiness.create_assessment(readiness.AssessmentBody(organizationId=ORG, workerProfileId="w1"), FakeRequest())
    assert len(r["dimensions"]) == 15
    lst = readiness.list_assessments(ORG, FakeRequest())
    assert "dimensions" in lst and len(lst["dimensions"]) == 15


# ---- Finance panel (Batch 6) ----
def test_console_finance_scenario_guard_and_create():
    _wire(finance)
    # high-risk field without evacuation scenario -> 422 from domain guard
    with pytest.raises(HTTPException) as e:
        finance.create_plan(finance.PlanBody(organizationId=ORG, workerProfileId="w1", highRiskField=True,
                            scenarioTypes=["baseline", "conservative", "support_loss"]), FakeRequest())
    assert e.value.status_code == 422
    ok = finance.create_plan(finance.PlanBody(organizationId=ORG, workerProfileId="w1", highRiskField=True,
                            scenarioTypes=["baseline", "conservative", "support_loss", "evacuation"]), FakeRequest())
    assert ok["status"] == "data_collection"


# ---- Deployment gate panel (Batch 6) ----
def test_console_gate_blocked_ready_and_ai_rejected():
    conn = _wire(deployment)
    # hard block -> blocked, unlocks none
    blocked = deployment.run_deployment_gate(
        deployment.GateRunBody(organizationId=ORG, sendingJourneyId="sj1", candidateId="c1",
                               isPanel=True, hardBlocks=["medical_not_cleared"]), FakeRequest())
    assert blocked["status"] == "blocked" and blocked["unlocks"] == "none"
    # panel, no blocks -> ready, unlocks planning, does NOT activate deployment
    ready = deployment.run_deployment_gate(
        deployment.GateRunBody(organizationId=ORG, sendingJourneyId="sj1", candidateId="c1",
                               isPanel=True, hardBlocks=[]), FakeRequest())
    assert ready["status"] == "ready_for_deployment_planning"
    assert ready["unlocks"] == "deployment_planning" and ready["activatesDeployment"] is False
    # candidate self-approval -> 403
    with pytest.raises(HTTPException) as e:
        deployment.run_deployment_gate(
            deployment.GateRunBody(organizationId=ORG, sendingJourneyId="sj1", candidateId="user@example.org",
                                   isPanel=True, hardBlocks=[]), FakeRequest())
    assert e.value.status_code == 403


def test_console_gate_list():
    conn = _wire(deployment)
    conn.fetchall_queue.append([("g1", "sj1", "blocked", "none", ["medical_not_cleared"], None)])
    lst = deployment.list_gates(ORG, FakeRequest())
    assert lst["items"][0]["gateStatus"] == "blocked"
