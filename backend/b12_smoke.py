#!/usr/bin/env python3
"""
b12_smoke.py — B12 多租户隔离冒烟测试(纯逻辑 + 静态守卫,无需数据库)。

运行:  cd backend && python b12_smoke.py
作用:  在没有 Postgres 的情况下,验证隔离的"硬不变量"是否成立 —— 任何一条断言失败即退出码 1。
       DB 级集成场景见 B12_TENANCY_TEST_CHECKLIST.md。

覆盖:
  1) RBAC 角色→权限矩阵正确(owner=*,member/viewer 受限)。
  2) PRIVATE_PERSONAL_DOMAINS 硬边界:个人隐私域被 assert_not_personal_domain 拦截(牧者可见度不放开)。
  3) require_org_permission 的 403 路径:非成员、角色越权;以及放行路径。
  4) 静态守卫:org_console 每个数据端点都调用 require_org_permission;且绝不 SELECT 危机/个人正文列。
  5) 静态守卫:platform_admin 每个端点都过 _require_admin;危机队列不 SELECT 隐私正文。
  6) 静态守卫:productization entitlements 保留 safety_exception(危机豁免订阅)。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILS = []
PASSES = [0]


def check(name, cond):
    if cond:
        PASSES[0] += 1
        print("  ✓ " + name)
    else:
        FAILS.append(name)
        print("  ✗ FAIL: " + name)


class FakeCursor:
    """最小假游标:execute 记录 SQL,fetchone 返回预置行。"""
    def __init__(self, role_row):
        self._role_row = role_row
        self.last_sql = ""

    def execute(self, sql, params=()):
        self.last_sql = sql

    def fetchone(self):
        return self._role_row


def main():
    from fastapi import HTTPException
    import core.tenancy as T

    print("\n[1] RBAC 角色→权限矩阵")
    check("owner 拥有任意权限(*)", T.has_permission("owner", "anything_at_all"))
    check("member 无 manage_groups", not T.has_permission("member", "manage_groups"))
    check("viewer 无任何权限", not T.has_permission("viewer", "view_group_reports"))
    check("leader 有 view_group_reports", T.has_permission("leader", "view_group_reports"))
    check("leader 无 manage_members", not T.has_permission("leader", "manage_members"))
    check("org_admin 有 manage_members", T.has_permission("org_admin", "manage_members"))
    check("未知角色 → 无权限", not T.has_permission("nope", "view_own"))

    print("\n[2] 个人隐私域硬边界(牧者可见度不放开)")
    for d in ["confession", "crisis", "examen", "spiritual_memory", "personal_notes", "devotion_journal"]:
        raised = False
        try:
            T.assert_not_personal_domain(d)
        except HTTPException as e:
            raised = (e.status_code == 500)
        check("个人域 '%s' 被拒绝纳入 org 作用域" % d, raised)
    # 社区域不应被拦
    ok = True
    try:
        T.assert_not_personal_domain("groups")
    except HTTPException:
        ok = False
    check("社区域 'groups' 允许 org 作用域", ok)

    print("\n[3] require_org_permission 的授权判定")
    # 非成员 → 403
    cur = FakeCursor(None)
    code = None
    try:
        T.require_org_permission(cur, "u@x.com", "ORG1", "manage_groups")
    except HTTPException as e:
        code = e.status_code
    check("非成员 → 403", code == 403)
    # member 角色请求 manage_groups → 403
    cur = FakeCursor(("member",))
    code = None
    try:
        T.require_org_permission(cur, "u@x.com", "ORG1", "manage_groups")
    except HTTPException as e:
        code = e.status_code
    check("member 请求 manage_groups → 403", code == 403)
    # owner → 放行
    cur = FakeCursor(("owner",))
    ctx = None
    try:
        ctx = T.require_org_permission(cur, "u@x.com", "ORG1", "manage_groups")
    except HTTPException:
        ctx = None
    check("owner 请求 manage_groups → 放行", bool(ctx) and ctx.get("role") == "owner")
    # leader → view_group_reports 放行,manage_members 拒绝
    cur = FakeCursor(("leader",))
    ok1 = bool(T.require_org_permission(cur, "u@x.com", "ORG1", "view_group_reports"))
    code = None
    try:
        T.require_org_permission(cur, "u@x.com", "ORG1", "manage_members")
    except HTTPException as e:
        code = e.status_code
    check("leader: view_group_reports 放行 + manage_members 403", ok1 and code == 403)
    # 空 org_id → 400
    cur = FakeCursor(("owner",))
    code = None
    try:
        T.require_org_permission(cur, "u@x.com", "", "manage_groups")
    except HTTPException as e:
        code = e.status_code
    check("空 org_id → 400", code == 400)

    def read(rel):
        with open(os.path.join(HERE, rel), encoding="utf-8") as f:
            return f.read()

    print("\n[4] 静态守卫:org_console 每端点强制 + 不泄隐私")
    oc = read("routers/org_console.py")
    data_eps = oc.count("@router.get") + oc.count("@router.post")
    rbac_calls = oc.count("require_org_permission(")
    check("org_console: require_org_permission 调用数 >= 数据端点-1 (my-role 仅查成员)",
          rbac_calls >= data_eps - 1)
    # 每个 SELECT 都带 org 过滤 or 经 join 到 g.org_id
    check("org_console: 含 org_id 过滤", "org_id=%s" in oc and "g.org_id=%s" in oc)
    sens = re.findall(r"SELECT[^\n]*(reflection|gratitude|struggle|prayer_request)", oc)
    check("org_console: 无 SELECT 取个人正文", len(sens) == 0)

    print("\n[5] 静态守卫:platform_admin 每端点过管理员 + 危机队列不泄正文")
    pa = read("routers/platform_admin.py")
    n_ep = pa.count("@router.get") + pa.count("@router.post")
    n_admin = pa.count("_require_admin(")
    check("platform_admin: _require_admin 覆盖所有端点", n_admin >= n_ep)
    sens2 = re.findall(r"SELECT[^\n;]*(triggering_message|evidence|system_response)", pa, re.IGNORECASE)
    check("platform_admin: 危机队列无 SELECT 取隐私正文", len(sens2) == 0)

    print("\n[6] 静态守卫:危机豁免订阅仍在")
    pr = read("routers/productization.py")
    check("productization: 保留 safety_exception", "safety_exception" in pr)
    check("productization: 危机计数用 user_acknowledged(非不存在的 status 列)",
          "user_acknowledged=FALSE" in pr)

    print("\n[7] 计费优雅降级(不抛硬依赖)")
    bl = read("routers/billing.py")
    check("billing: 未配置 Stripe → billing_not_configured", "billing_not_configured" in bl)
    check("billing: webhook 配置 secret 时验签", "construct_event" in bl)

    print("\n[8] 静态守卫:社区 create-with-org 盖 org_id 且有成员/权限守卫")
    create_specs = [
        ("routers/accountability_group.py", "accountability_groups", "_assert_org_perm"),
        ("routers/mentor.py", "mentor_relationships", "_assert_org_member"),
        ("routers/discipleship.py", "user_discipleship_paths", "_assert_org_member"),
        ("routers/church_integration.py", "church_profiles", "_assert_org_member"),
    ]
    for path, tbl, guard in create_specs:
        src = read(path)
        has_field = "org_id: Optional[str]" in src
        has_guard = (guard + "(") in src
        has_insert = re.search(r"INSERT INTO %s \([^)]*org_id" % re.escape(tbl), src) is not None
        check("%s: 模型org_id + %s 守卫 + INSERT盖org_id" % (path.split("/")[-1], guard),
              has_field and has_guard and has_insert)

    ci = read("routers/church_integration.py")
    check("church check-in create-with-org(CheckinCreate org_id + INSERT 盖 org_id + 唯一组织自动归属)",
          "org_id: Optional[str]" in ci
          and re.search(r"INSERT INTO church_life_checkins \([^)]*org_id", ci) is not None
          and "_auto_member_org" in ci)

    print("\n[9] 静态守卫:社区进度端点 org 过滤 + 不取会谈/步骤正文")
    oc2 = read("routers/org_console.py")
    check("discipleship-progress org 过滤(p.org_id=%s)", "/discipleship" in oc2 and "p.org_id=%s" in oc2)
    check("mentor-progress org 过滤(r.org_id=%s)", "mentor-progress" in oc2 and "r.org_id=%s" in oc2)
    prog = re.findall(r"SELECT[^\n]*(agenda|prayer_notes|step_description|risk_flags)", oc2, re.IGNORECASE)
    check("进度端点无 SELECT 取会谈/步骤正文(agenda/prayer_notes/step_description/risk_flags)", len(prog) == 0)
    check("church-trend org 过滤(church_life_checkins + org_id=%s)",
          "church-trend" in oc2 and "FROM church_life_checkins" in oc2 and "org_id=%s" in oc2)
    check("group-health org 过滤(g.org_id=%s)", "group-health" in oc2 and "g.org_id=%s" in oc2)
    leak2 = re.findall(r"SELECT[^\n]*(next_step)", oc2, re.IGNORECASE)
    check("教会/小组只读端点无 SELECT 取 check-in 正文(next_step)", len(leak2) == 0)
    check("activity-trend 跨域 org 过滤(church_life_checkins UNION + g.org_id=%s)",
          "activity-trend" in oc2 and "church_life_checkins" in oc2 and "g.org_id=%s" in oc2)

    print("\n" + "=" * 48)
    if FAILS:
        print("结果: ✗ %d 通过, %d 失败" % (PASSES[0], len(FAILS)))
        for f in FAILS:
            print("   - " + f)
        return 1
    print("结果: ✓ 全部 %d 条隔离不变量通过" % PASSES[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
