# B12 多租户隔离 · 测试清单（冒烟 + DB 集成）

两层验证:
- **L1 纯逻辑冒烟**(沙箱/本地都能跑,无需 DB):`cd backend && python b12_smoke.py` → 应输出 `全部 32 条隔离不变量通过`。
- **L2 DB 集成**(本地起 Postgres + 应用迁移后):按下面逐条手测。

隔离的三条硬不变量(任何一条被打破即不合格):
1. **跨组织不可见**:org A 的领袖看不到 org B 的任何社区数据。
2. **个人成长数据永不入组织视图**:省察/认罪/危机/祷告/记忆/灵修日志即使成员属于某 org,组织侧也读不到(牧者可见度不放开)。
3. **危机/安全永远豁免**:订阅过期/组织停用都不影响危机与安全功能。

---

## 0. 准备

```bash
cd backend
python -m core.migrations          # 应用 0123–0126(org_id、Stripe 字段、审核表)
python b12_smoke.py                 # L1:应 32/32 通过
```

种子数据(psql):两个组织、两个用户、各种角色、一个平台管理员。

```sql
-- 组织
INSERT INTO organizations (id,slug,name,owner_email,status) VALUES
 ('ORGA','orga','教会A','alice@test.com','active'),
 ('ORGB','orgb','教会B','bob@test.com','active') ON CONFLICT DO NOTHING;
-- 成员与角色(role_key:owner/org_admin/pastor/leader/mentor/care_team/member/viewer)
INSERT INTO organization_memberships (id,organization_id,email,role_key,status) VALUES
 ('m1','ORGA','alice@test.com','owner','active'),
 ('m2','ORGA','carol@test.com','member','active'),
 ('m3','ORGA','dave@test.com','leader','active'),
 ('m4','ORGB','bob@test.com','owner','active') ON CONFLICT DO NOTHING;
-- 平台管理员
INSERT INTO platform_admins (email,role_key,status) VALUES
 ('root@test.com','super_admin','active') ON CONFLICT DO NOTHING;
```

> 下面用 `TOKEN_X` 表示该用户登录后的 Bearer token;`$API` 为后端地址。

---

## 1. 跨组织隔离(不变量 1)

| # | 操作 | 期望 |
|---|---|---|
|1.1| Alice(ORGA owner)`GET /api/org-console/ORGA/summary` | 200,返回 ORGA 计数 |
|1.2| Alice 用 ORGB 调 `GET /api/org-console/ORGB/summary` | **403**(非 ORGB 成员)|
|1.3| Bob(ORGB owner)`GET /api/org-console/ORGA/groups` | **403** |
|1.4| Alice 在 ORGA 建组(见 §4),Bob 在 `GET /api/org-console/ORGB/groups` | **看不到** ORGA 的组 |

```bash
curl -s -H "Authorization: Bearer $TOKEN_ALICE" $API/api/org-console/ORGB/summary | jq .detail
# 期望: "not an active member of this organization"
```

## 2. RBAC 角色分级

| # | 角色 | 端点 | 期望 |
|---|---|---|---|
|2.1| member(carol)| `GET /api/org-console/ORGA/summary` (需 manage_groups) | **403** |
|2.2| leader(dave) | `GET /api/org-console/ORGA/summary` | 200 |
|2.3| leader(dave) | `GET /api/org-console/ORGA/members` (需 manage_members) | **403** |
|2.4| owner(alice) | `GET /api/org-console/ORGA/members` | 200 |

## 3. 个人成长数据永不入组织视图(不变量 2 · 最关键)

1. carol(ORGA 成员)创建个人数据:`POST /api/examen/...`、`POST /devotion/journals`、`POST /api/spiritual-memory/items`。
2. Alice/dave 遍历**所有** org-console 端点:`summary / groups / mentor-relationships / members`。
3. **断言**:返回里不含 carol 的省察/日志/记忆任何正文或计数。org-console 只回小组/出勤/配对的**计数与状态**。
4. 代码级保证:`python b12_smoke.py` 的 [4] 段已静态证明 org_console 无 `SELECT reflection/gratitude/struggle/prayer_request`;`core/tenancy.assert_not_personal_domain` 对个人域抛 500。

## 4. create-with-org(盖 org_id)

```bash
# leader dave 在 ORGA 建组并归属 ORGA
curl -s -X POST -H "Authorization: Bearer $TOKEN_DAVE" -H 'Content-Type: application/json' \
  -d '{"name":"周三小组","org_id":"ORGA"}' $API/api/accountability-group/groups
# 期望 200;随后 GET /api/org-console/ORGA/groups 能看到「周三小组」
```

| # | 操作 | 期望 |
|---|---|---|
|4.1| dave(leader)建组 `org_id=ORGA` | 200,组出现在 ORGA 控制台 |
|4.2| carol(member,无 manage_groups)建组 `org_id=ORGA` | **403**(accountability 需 manage_groups)|
|4.3| carol 建**导师关系** `org_id=ORGA`(成员级) | 200(`_assert_org_member` 仅要求是成员)|
|4.4| carol 建关系 `org_id=ORGB`(非成员)| **403** |
|4.5| 不带 org_id 建任何资源 | 200,`org_id=NULL`,保持个人私有、组织看不到 |

## 5. claim 既有组

| # | 操作 | 期望 |
|---|---|---|
|5.1| dave 创建无 org 的组,再 `POST /api/org-console/ORGA/groups/{gid}/claim` | 200,组归 ORGA |
|5.2| 非创建者 claim 他人的组 | **403** |
|5.3| 已属 ORGB 的组被 ORGA claim | **403** |

## 6. 危机/安全豁免(不变量 3)

| # | 操作 | 期望 |
|---|---|---|
|6.1| `POST /api/productization/entitlements/check {"entitlement_key":"crisis_triage"}` 在**免费/过期**账户 | `allowed=true, reason=safety_exception` |
|6.2| 平台停用 ORGA(`POST /api/platform/orgs/ORGA/suspend`)后,ORGA 成员触发危机文本 | 危机路由 `/api/crisis` 仍正常,安全门不受影响 |
|6.3| AI 导师发危机文本 | 进安全分支、不进 LLM、给 `/api/crisis`(见 ai_tutor)|

## 7. 平台管理台 / 审核(仅 platform_admins)

| # | 操作 | 期望 |
|---|---|---|
|7.1| 非管理员调 `GET /api/platform/overview` | **403** "platform admin only" |
|7.2| root 调 `GET /api/platform/moderation/crisis-queue` | 200;**不含** `triggering_message/evidence/system_response` |
|7.3| root `POST /api/platform/moderation/crisis/{id}/review {"action":"reviewed"}` | 200,写入 `crisis_moderation_reviews` |
|7.4| root `POST /api/platform/orgs/ORGA/suspend` 再 `/reactivate` | 200,`organizations.status` 切换,写 `platform_moderation_log` |

## 8. Stripe 计费(解耦)

| # | 环境 | 操作 | 期望 |
|---|---|---|---|
|8.1| 未配置 `STRIPE_SECRET_KEY` | `POST /api/billing/checkout` | **503** `billing_not_configured`(并提示危机免费)|
|8.2| 配置好 key+price | `POST /api/billing/checkout {"plan_key":"church_pro"}` | 200,返回 `checkout_url` |
|8.3| 配置 `STRIPE_WEBHOOK_SECRET` | 伪造签名 POST `/api/billing/webhook` | **400** invalid signature |
|8.4| 正确签名 `checkout.session.completed` | webhook | `subscriptions` 行 `status=active, billing_provider=stripe, stripe_subscription_id` 写入 |

env 需要:`STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、`STRIPE_PRICE_<PLAN_KEY 大写>`、`PUBLIC_BASE_URL`。
Stripe 后台把 webhook 指向 `$PUBLIC_BASE_URL/api/billing/webhook`,用测试卡 `4242 4242 4242 4242` 跑通。

---

## 通过标准

- L1:`b12_smoke.py` 32/32。
- L2:§1–§8 全绿,**特别是 §3**(个人数据零泄漏)与 §6(危机豁免)。
- 任一条 §1/§3/§6 失败 → 不得上线,属隔离/隐私缺陷。
