from pathlib import Path

import pytest
from fastapi import HTTPException

from mission_bridge_auth import authorize


class Cursor:
    def __init__(self, role=None, allowed=False): self.role=role; self.allowed=allowed; self.calls=[]; self.last=''
    def execute(self,sql,params=()): self.calls.append((sql,params)); self.last=sql
    def fetchone(self):
        if "tenant_memberships" in self.last: return (self.role,) if self.role else None
        if "role_permissions" in self.last: return (1,) if self.allowed else None
        return (1,)


def test_cross_tenant_non_member_is_denied():
    with pytest.raises(HTTPException) as exc: authorize(Cursor(),{"email":"a@example.com"},"program.read","tenant-b")
    assert exc.value.status_code == 403


def test_role_permission_is_checked_server_side():
    cur=Cursor(role="mentor",allowed=False)
    with pytest.raises(HTTPException) as exc: authorize(cur,{"email":"mentor@example.com"},"incident.manage","tenant-a")
    assert exc.value.status_code == 403
    assert any("role_permissions" in sql for sql,_ in cur.calls)


def test_rls_is_enabled_for_sensitive_tables():
    sql=(Path(__file__).parents[1]/"migrations"/"0152_mission_bridge_tenancy.sql").read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "current_setting(''app.tenant_id''" in sql
    assert "mission_bridge_guardian_relationships" in sql
