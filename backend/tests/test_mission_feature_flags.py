from datetime import datetime,timedelta,timezone
from fastapi.routing import APIRoute
from mission_os.feature_flags import FlagOverride,evaluate_flag,load_effective_flag
from routers.mission_features import router
from routers.mission_bridge import _mission_gate
from mission_feature_guard import init_mission_feature_guard
from starlette.requests import Request
from fastapi import HTTPException
import pytest
NOW=datetime(2026,7,11,tzinfo=timezone.utc)
def test_fail_closed_and_emergency_off():
    assert not evaluate_flag(key="mission_deployment_enabled",default=True,overrides=[],scopes={},env={"MISSION_OS_ENABLED":"false"},now=NOW)
    assert not evaluate_flag(key="mission_os_enabled",default=True,overrides=[],scopes={},env={"MISSION_EMERGENCY_OFF":"true"},now=NOW)
def test_specific_active_override_wins_expired_ignored():
    items=[FlagOverride("global","global",False,NOW-timedelta(days=2)),FlagOverride("tenant","t1",True,NOW-timedelta(days=1)),FlagOverride("user","u1",False,NOW-timedelta(hours=1),NOW-timedelta(minutes=1))]
    assert evaluate_flag(key="mission_training_enabled",default=False,overrides=items,scopes={"global":"global","tenant":"t1","user":"u1"},env={"MISSION_OS_ENABLED":"true"},now=NOW)
def test_admin_routes_exist():
    routes={(r.path,m) for r in router.routes if isinstance(r,APIRoute) for m in r.methods}
    assert ("/api/v1/mission/features","GET") in routes and ("/api/v1/mission/features/{key}/overrides","PUT") in routes

class Cur:
    def __init__(self):self.one=('flag-id',True)
    def execute(self,*args):pass
    def fetchone(self):return self.one
    def fetchall(self):return []
class Conn:
    def cursor(self):
        class Ctx:
            def __enter__(self):self.cur=Cur();return self.cur
            def __exit__(self,*args):pass
        return Ctx()

def request(path):return Request({'type':'http','method':'GET','path':path,'headers':[],'query_string':b''})

def test_direct_non_safety_api_is_rejected_when_environment_gate_is_off(monkeypatch):
    monkeypatch.setenv('MISSION_OS_ENABLED','false')
    init_mission_feature_guard(get_db=lambda:Conn(),release_db=lambda conn:None,get_session_user=lambda req:{'email':'u1'})
    with pytest.raises(HTTPException) as exc:_mission_gate(request('/api/mission-bridge/dashboard'))
    assert exc.value.status_code==503

def test_safety_and_privacy_paths_remain_available_when_module_is_off(monkeypatch):
    monkeypatch.setenv('MISSION_OS_ENABLED','false')
    _mission_gate(request('/api/mission-bridge/incidents'))
    _mission_gate(request('/api/mission-bridge/privacy/export'))

def test_master_flag_requires_environment_and_database_enablement():
    cur=Cur()
    assert load_effective_flag(cur,key='mission_os_enabled',tenant_id='t',user_id='u',environment='test',env={'MISSION_OS_ENABLED':'true'})
    cur=Cur()
    assert not load_effective_flag(cur,key='mission_os_enabled',tenant_id='t',user_id='u',environment='test',env={'MISSION_OS_ENABLED':'false'})
