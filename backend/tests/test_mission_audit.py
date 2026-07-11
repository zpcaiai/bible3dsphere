from pathlib import Path
import pytest
from mission_os.audit import add_lineage,audit,ip_hash
from routers.mission_audit import _recent_mfa,router
from fastapi.routing import APIRoute
from datetime import datetime,timedelta,timezone

class Cursor:
    def __init__(self):self.calls=[]
    def execute(self,sql,params=()):self.calls.append((sql,params))

def test_audit_records_field_names_and_hash_not_remote_ip():
    cur=Cursor();audit(cur,tenant_id='t1',actor_id='u1',actor_role='auditor',action='approve',resource_type='deployment',resource_id='d1',result='success',changed_fields=['status'],remote_ip='203.0.113.7',ip_salt='s')
    sql,params=cur.calls[0]
    assert 'INSERT INTO mission_audit_logs' in sql and '203.0.113.7' not in repr(params)
    assert ip_hash('203.0.113.7','s') in params and ['status'] in params

def test_sensitive_fields_and_unknown_actions_are_rejected():
    with pytest.raises(ValueError):audit(Cursor(),tenant_id='t',actor_id='u',actor_role='x',action='approve',resource_type='x',resource_id='1',result='x',changed_fields=['reflection'])
    with pytest.raises(ValueError):audit(Cursor(),tenant_id='t',actor_id='u',actor_role='x',action='silently_read',resource_type='x',resource_id='1',result='x')

def test_lineage_is_reference_based_and_idempotent():
    cur=Cursor();add_lineage(cur,tenant_id='t',derived_type='report',derived_id='r1',source_type='claim',source_id='c1',transformation_type='summarize',model_run_id='m1')
    assert 'ON CONFLICT DO NOTHING' in cur.calls[0][0]

def test_migration_has_rls_immutable_audit_breakglass_and_lineage():
    sql=(Path(__file__).parents[1]/'migrations'/'0160_mission_os_audit_lineage.sql').read_text()
    for phrase in ('ENABLE ROW LEVEL SECURITY','mission audit logs are immutable','mission_break_glass_access','mission_data_lineage'):
        assert phrase in sql

def test_breakglass_requires_recent_verified_mfa():
    now=datetime.now(timezone.utc)
    assert _recent_mfa({'mfa_verified':True,'mfa_verified_at':now.isoformat()})
    assert not _recent_mfa({'mfa_verified':True,'mfa_verified_at':(now-timedelta(minutes=11)).isoformat()})
    assert not _recent_mfa({'mfa_verified':False,'mfa_verified_at':now.isoformat()})

def test_audit_lineage_and_breakglass_routes_exist():
    routes={(r.path,m) for r in router.routes if isinstance(r,APIRoute) for m in r.methods}
    assert ('/api/v1/mission/audit','GET') in routes
    assert ('/api/v1/mission/data-lineage/{resource_type}/{resource_id}','GET') in routes
    assert ('/api/v1/mission/break-glass','POST') in routes
