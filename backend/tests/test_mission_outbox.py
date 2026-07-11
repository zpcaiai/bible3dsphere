from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from mission_os.outbox import OutboxEvent, deliver, enqueue, mark_failed
from routers.mission_outbox import router


class Cursor:
    def __init__(self, rows=None): self.calls=[];self.rows=list(rows or [])
    def execute(self, sql, params=()): self.calls.append((sql,params))
    def fetchone(self): return self.rows.pop(0) if self.rows else None


def test_enqueue_uses_callers_cursor_and_versioned_redacted_payload():
    cur=Cursor();event_id=enqueue(cur,tenant_id="t1",aggregate_type="MissionProgram",aggregate_id="p1",event_type="MissionTrainingPlanCreated",event_version=1,actor_id="u1",correlation_id="r1",data={"plan_id":"p1"},event_id="e1")
    assert event_id=="e1" and len(cur.calls)==1
    assert "INSERT INTO mission_outbox_events" in cur.calls[0][0]
    with pytest.raises(ValueError):
        enqueue(cur,tenant_id="t1",aggregate_type="X",aggregate_id="1",event_type="XCreated",event_version=1,actor_id="u",correlation_id="r",data={"reflection":"private"})


def test_completed_delivery_is_idempotent():
    cur=Cursor(rows=[("completed",)]);called=[]
    state=deliver(cur,OutboxEvent("e1","t1","X",{},0),"formation",lambda payload:called.append(payload))
    assert state=="duplicate" and called==[]


def test_eighth_failure_enters_dead_letter():
    cur=Cursor();state=mark_failed(cur,OutboxEvent("e1","t1","X",{},7),RuntimeError("provider token must not leak"))
    assert state=="dead_letter"
    assert any("mission_dead_letter_events" in sql for sql,_ in cur.calls)


def test_outbox_admin_routes_and_migration_contract():
    routes={(r.path,m) for r in router.routes if isinstance(r,APIRoute) for m in r.methods}
    assert ("/api/v1/mission/system/outbox","GET") in routes
    assert ("/api/v1/mission/system/outbox/{event_id}/replay","POST") in routes
    sql=(Path(__file__).parents[1]/"migrations"/"0157_mission_os_outbox.sql").read_text()
    assert "FOR UPDATE" not in sql
    assert all(name in sql for name in ("mission_outbox_events","mission_event_deliveries","mission_dead_letter_events","ENABLE ROW LEVEL SECURITY"))


def test_mission_workflows_enqueue_before_their_transaction_commit():
    source=(Path(__file__).parents[1]/"routers"/"mission_bridge.py").read_text()
    for event_type in ("MissionProgramEnrollmentStarted","MissionTrainingMilestoneCompleted","MissionIncidentCreated"):
        position=source.index(f'event_type="{event_type}"')
        assert source.index("conn.commit()",position)>position
