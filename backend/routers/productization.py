"""
Productization router — 组织/RBAC/计划/订阅/管理 (/api/productization)

组织: POST/GET /orgs, GET /orgs/{id}, POST /orgs/{id}/members, POST /orgs/{id}/check-permission
计划: GET /plans, GET /subscription, POST /subscribe, POST /entitlements/check
管理: GET /admin/overview (平台管理员), GET /ops/health

注意:这是产品化层自身后端,非"把所有模块按 org 隔离"的全量多租户改造。
安全例外:危机/安全流程永不因订阅被阻断;entitlement 仅信息性。email 标识用户。
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/productization", tags=["productization"])

_state: Dict[str, Any] = {}

# 角色 → 权限集(简化 RBAC)
from core.tenancy import ROLE_PERMS as _ROLE_PERMS  # B12: 单一事实来源(core/tenancy)


def init_productization_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _jl(v):
    if v is None: return {}
    if isinstance(v, (dict, list)): return v
    try: return json.loads(v)
    except Exception: return {}


def _role(cur, org_id: str, email: str) -> Optional[str]:
    cur.execute("SELECT role_key FROM organization_memberships WHERE organization_id=%s AND email=%s AND status='active'", (org_id, email))
    r = cur.fetchone()
    return r[0] if r else None


def _has_perm(role: str, perm: str) -> bool:
    perms = _ROLE_PERMS.get(role, set())
    return "*" in perms or perm in perms


# ── 组织 ──────────────────────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str = Field(..., max_length=200)
    organization_type: str = Field(default="church", max_length=24)


@router.post("/orgs")
def create_org(request: Request, body: OrgCreate) -> dict:
    user = _require_user(request); email = user["email"]
    oid = uuid.uuid4().hex
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")[:60] + "-" + oid[:6]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO organizations (id, slug, name, organization_type, owner_email) VALUES (%s,%s,%s,%s,%s)",
                        (oid, slug, body.name, body.organization_type, email))
            cur.execute("INSERT INTO organization_memberships (id, organization_id, email, role_key, status) "
                        "VALUES (%s,%s,%s,'owner','active')", (uuid.uuid4().hex, oid, email))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "organization_id": oid, "slug": slug}


@router.get("/orgs")
def list_orgs(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT o.id, o.name, o.organization_type, o.status, m.role_key "
                        "FROM organizations o JOIN organization_memberships m ON o.id=m.organization_id "
                        "WHERE m.email=%s AND m.status='active' ORDER BY o.created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "organizations": [
        {"id": r[0], "name": r[1], "organization_type": r[2], "status": r[3], "my_role": r[4]} for r in rows
    ]}


@router.get("/orgs/{oid}")
def get_org(oid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _role(cur, oid, user["email"])
            if not role:
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT id, name, organization_type, status, owner_email FROM organizations WHERE id=%s", (oid,))
            o = cur.fetchone()
            members = []
            if _has_perm(role, "manage_members"):
                cur.execute("SELECT email, role_key, status FROM organization_memberships WHERE organization_id=%s AND status='active'", (oid,))
                members = [{"email": m[0], "role_key": m[1], "status": m[2]} for m in cur.fetchall()]
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "organization": {"id": o[0], "name": o[1], "organization_type": o[2], "status": o[3],
            "my_role": role, "members": members}}


class MemberAdd(BaseModel):
    email: str = Field(..., max_length=255)
    role_key: str = Field(default="member", max_length=20)


@router.post("/orgs/{oid}/members")
def add_member(oid: str, request: Request, body: MemberAdd) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _role(cur, oid, user["email"])
            if not _has_perm(role or "", "manage_members"):
                raise HTTPException(status_code=403, detail="no permission to manage members")
            cur.execute("INSERT INTO organization_memberships (id, organization_id, email, role_key) VALUES (%s,%s,%s,%s) "
                        "ON CONFLICT (organization_id, email) DO UPDATE SET role_key=EXCLUDED.role_key, status='active', updated_at=NOW()",
                        (uuid.uuid4().hex, oid, body.email, body.role_key))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"add failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True}


class PermCheck(BaseModel):
    permission: str = Field(..., max_length=40)


@router.post("/orgs/{oid}/check-permission")
def check_permission(oid: str, request: Request, body: PermCheck) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _role(cur, oid, user["email"])
    finally:
        _state["release_db"](conn)
    return {"ok": True, "role": role, "allowed": bool(role and _has_perm(role, body.permission))}


# ── 计划 / 订阅 ───────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan_key, display_name, plan_type, billing_interval, price_cents, entitlements FROM product_plans WHERE public=TRUE ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plans": [
        {"plan_key": r[0], "display_name": r[1], "plan_type": r[2], "billing_interval": r[3],
         "price_cents": r[4], "entitlements": _jl(r[5])} for r in rows
    ]}


def _active_sub(cur, email: str):
    cur.execute("SELECT plan_key, status, current_period_end FROM subscriptions WHERE email=%s AND status IN ('active','trialing') "
                "ORDER BY created_at DESC LIMIT 1", (email,))
    return cur.fetchone()


@router.get("/subscription")
def get_subscription(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            s = _active_sub(cur, user["email"])
            plan_key = s[0] if s else "free_individual"
            cur.execute("SELECT display_name, entitlements FROM product_plans WHERE plan_key=%s", (plan_key,))
            p = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "subscription": {"plan_key": plan_key, "status": s[1] if s else "free",
            "plan_name": p[0] if p else plan_key, "entitlements": _jl(p[1]) if p else {}}}


class Subscribe(BaseModel):
    plan_key: str = Field(..., max_length=40)


@router.post("/subscribe")
def subscribe(request: Request, body: Subscribe) -> dict:
    """MVP:手动设定订阅(真实计费由 Stripe 适配器接管,此处不收款)。"""
    user = _require_user(request); email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan_type, price_cents FROM product_plans WHERE plan_key=%s", (body.plan_key,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="plan not found")
            plan_type, price_cents = row[0], (row[1] or 0)
            # SECURITY: self-serve activation is only allowed for free plans. Paid plans must go
            # through billing/Stripe — never let a user self-set a paid plan to active.
            is_free = (str(plan_type or "").lower() in ("free", "free_individual")) and int(price_cents) == 0
            if not is_free:
                raise HTTPException(status_code=402,
                                    detail="付费计划需通过结算流程(Stripe)开通,不能自助激活")
            cur.execute("UPDATE subscriptions SET status='canceled', updated_at=NOW() WHERE email=%s AND status IN ('active','trialing')", (email,))
            cur.execute("INSERT INTO subscriptions (id, email, plan_key, scope, status, current_period_end) "
                        "VALUES (%s,%s,%s,'user','active', NOW() + INTERVAL '30 days')", (uuid.uuid4().hex, email, body.plan_key))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        print(f"[productization] subscribe failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="subscribe failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan_key": body.plan_key, "note": "真实收款需接 Stripe 适配器;此处为手动开通。"}


class EntitlementCheck(BaseModel):
    entitlement_key: str = Field(..., max_length=40)


@router.post("/entitlements/check")
def check_entitlement(request: Request, body: EntitlementCheck) -> dict:
    user = _require_user(request)
    # 安全例外:危机/安全相关权益恒为真,永不因计费阻断
    if body.entitlement_key in ("crisis_triage", "safety_plan", "crisis"):
        return {"ok": True, "entitlement_key": body.entitlement_key, "allowed": True, "reason": "safety_exception"}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            s = _active_sub(cur, user["email"])
            plan_key = s[0] if s else "free_individual"
            cur.execute("SELECT entitlements FROM product_plans WHERE plan_key=%s", (plan_key,))
            p = cur.fetchone()
    finally:
        _state["release_db"](conn)
    ent = _jl(p[0]) if p else {}
    val = ent.get(body.entitlement_key, False)
    return {"ok": True, "entitlement_key": body.entitlement_key, "plan_key": plan_key, "value": val,
            "allowed": bool(val)}


# ── 管理 / 运维 ───────────────────────────────────────────────────────────────

def _is_platform_admin(cur, email: str) -> bool:
    cur.execute("SELECT 1 FROM platform_admins WHERE email=%s AND status='active'", (email,))
    return cur.fetchone() is not None


@router.get("/admin/overview")
def admin_overview(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _is_platform_admin(cur, user["email"]):
                raise HTTPException(status_code=403, detail="platform admin only")
            def c(sql):
                try: cur.execute(sql); r = cur.fetchone(); return (r[0] or 0) if r else 0
                except Exception: return 0
            data = {
                "organizations": c("SELECT COUNT(*) FROM organizations"),
                "org_members": c("SELECT COUNT(*) FROM organization_memberships WHERE status='active'"),
                "active_subscriptions": c("SELECT COUNT(*) FROM subscriptions WHERE status='active'"),
                "open_crisis_events": c("SELECT COUNT(*) FROM crisis_events WHERE user_acknowledged=FALSE"),
            }
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "overview": data}


@router.get("/ops/health")
def ops_health(request: Request) -> dict:
    _require_user(request)
    db_ok = True
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1"); cur.fetchone()
    except Exception:
        db_ok = False
    finally:
        try: _state["release_db"](conn)
        except Exception: pass
    return {"ok": True, "status": "healthy" if db_ok else "degraded", "database": db_ok}
