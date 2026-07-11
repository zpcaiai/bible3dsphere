"""Central server-side authorization for MissionBridge resources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException


@dataclass(frozen=True)
class AuthorizationContext:
    user_id: str
    tenant_id: str
    role: str
    action: str


def set_tenant_context(cur, tenant_id: str) -> None:
    cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))


def resolve_role(cur, user_id: str, tenant_id: str, program_id: Optional[str] = None) -> Optional[str]:
    if program_id:
        cur.execute("SELECT role_key FROM mission_bridge_program_memberships WHERE tenant_id=%s AND program_id=%s AND user_id=%s AND status='active' ORDER BY created_at DESC LIMIT 1",(tenant_id,program_id,user_id))
        row=cur.fetchone()
        if row: return str(row[0])
    cur.execute("SELECT role_key FROM mission_bridge_tenant_memberships WHERE tenant_id=%s AND user_id=%s AND status='active' ORDER BY created_at DESC LIMIT 1",(tenant_id,user_id))
    row=cur.fetchone()
    return str(row[0]) if row else ("participant" if tenant_id == "public" else None)


def authorize(cur, user: dict, action: str, tenant_id: str, *, program_id: Optional[str] = None, platform_admin: bool = False) -> AuthorizationContext:
    user_id=str(user.get("email") or user.get("id") or "")
    if not user_id: raise HTTPException(401,detail="请先登录")
    set_tenant_context(cur,tenant_id)
    if platform_admin: return AuthorizationContext(user_id,tenant_id,"platform_admin",action)
    role=resolve_role(cur,user_id,tenant_id,program_id)
    if not role: raise HTTPException(403,detail="无权访问该租户")
    cur.execute("SELECT 1 FROM mission_bridge_role_permissions WHERE role_key=%s AND permission_key=%s",(role,action))
    if not cur.fetchone(): raise HTTPException(403,detail="权限不足")
    return AuthorizationContext(user_id,tenant_id,role,action)
