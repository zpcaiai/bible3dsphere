"""
core/tenancy.py — B12 多租户隔离的共享强制层(单一事实来源)。

设计原则:
  · 个人成长数据(省察/认罪/危机/祷告/记忆/灵修日志/灵魂一问/偶像)保持 email 私有 ——
    本模块永不暴露它们,即使组织角色再高也不行(牧者可见度不放开)。
    PRIVATE_PERSONAL_DOMAINS 为硬边界黑名单;assert_not_personal_domain() 守卫误用。
  · 仅"社区/组织"数据(小组/教会/导师/门徒路径)按 org 作用域 + RBAC 强制。
  · 危机/安全路径永远豁免:不得在危机端点上调用本模块的强制函数。

成员表:organization_memberships(organization_id, email, role_key, status)。
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List

from fastapi import HTTPException

# 角色 → 权限(单一事实来源;productization 复用本表)
ROLE_PERMS: Dict[str, set] = {
    "owner": {"*"},
    "org_admin": {"manage_members", "manage_settings", "view_analytics", "manage_groups", "manage_billing"},
    "pastor": {"view_pastoral_care_summary", "view_analytics", "manage_groups"},
    "leader": {"manage_groups", "view_group_reports"},
    "mentor": {"view_mentor_summary"},
    "care_team": {"view_care_cases"},
    "member": {"view_own"},
    "viewer": set(),
}

# 显式禁止经 RBAC 暴露的个人隐私域 —— 组织/牧者永不可见(默认隔离的硬边界)
PRIVATE_PERSONAL_DOMAINS = frozenset({
    "confession", "crisis", "examen", "prayer_journal", "spiritual_memory",
    "personal_notes", "devotion_journal", "soul_question", "idolatry", "temptation",
})


def has_permission(role: Optional[str], perm: str) -> bool:
    perms = ROLE_PERMS.get(role or "", set())
    return "*" in perms or perm in perms


def assert_not_personal_domain(domain: str) -> None:
    """守卫:任何把个人隐私域纳入组织作用域的代码路径,立即 500 —— 这是设计错误,不是运行时错误。"""
    if domain in PRIVATE_PERSONAL_DOMAINS:
        raise HTTPException(status_code=500,
                            detail="tenancy violation: '%s' is private personal data and must never be org-scoped" % domain)


def resolve_role(cur, org_id: str, email: str) -> Optional[str]:
    """返回 active 成员的 role_key,非成员/无效 → None。绝不抛出。"""
    try:
        cur.execute("SELECT role_key FROM organization_memberships "
                    "WHERE organization_id=%s AND email=%s AND status='active'", (org_id, email))
        r = cur.fetchone()
        return r[0] if r else None
    except Exception:
        return None


def list_memberships(cur, email: str) -> List[Dict[str, Any]]:
    """该用户所有 active 成员资格。绝不抛出。"""
    try:
        cur.execute("SELECT organization_id, role_key, status FROM organization_memberships "
                    "WHERE email=%s AND status='active' ORDER BY created_at ASC", (email,))
        return [{"org_id": r[0], "role": r[1], "status": r[2]} for r in cur.fetchall()]
    except Exception:
        return []


def member_org_ids(cur, email: str) -> List[str]:
    return [m["org_id"] for m in list_memberships(cur, email)]


def require_membership(cur, email: str, org_id: str) -> str:
    """要求调用者是该 org 的 active 成员(任意角色)。非 org_id→400;非成员→403。返回 role_key。

    用于"把社区资源归属到我所属的组织"这类成员级动作(角色矩阵非层级,故不能用单一权限表达)。
    """
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id required")
    role = resolve_role(cur, org_id, email)
    if not role:
        raise HTTPException(status_code=403, detail="not an active member of this organization")
    return role


def require_org_permission(cur, email: str, org_id: str, perm: str) -> Dict[str, Any]:
    """组织作用域 + RBAC 强制。

    非 org_id → 400;非 active 成员 → 403;角色无权 → 403。返回 {org_id, role}。
    注意:危机/安全路径绝不调用本函数 —— 它们必须无条件可用。
    """
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id required")
    role = resolve_role(cur, org_id, email)
    if not role:
        raise HTTPException(status_code=403, detail="not an active member of this organization")
    if not has_permission(role, perm):
        raise HTTPException(status_code=403, detail="role '%s' lacks permission '%s'" % (role, perm))
    return {"org_id": org_id, "role": role}
