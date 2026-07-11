# Mission OS 运行手册 — 迁移 smoke + 工作台联调

> 这两步需要一个能跑 PostgreSQL 的环境（本地 Docker 或任意 Postgres）。
> 在 CI 沙箱里跑不了（无 Docker、无法安装 PG）；在你的机器上按下面命令即可。

## ① 迁移 smoke（迁移全链 + RLS 实测）

**A. 有 Docker（推荐，自带一次性 PG + 非超级用户角色，RLS 真正生效）**

```bash
cd bible3dsphere
make mission-os-smoke          # = backend/scripts/mission_os/migration_smoke.sh
```

**B. 已有一个 Postgres**

```bash
cd bible3dsphere/backend
DATABASE_URL=postgresql://user:pass@host:5432/db \
  python3 scripts/mission_os/migration_smoke.py
```

**期望输出（PASS）**

```
[SMOKE] applying all migrations from empty ...
[SMOKE] run_migrations applied N migration(s)
[SMOKE] all 21 sample tables present
[SMOKE] RLS + tenant-isolation policy verified on all sample tables
[SMOKE] behavioural tenant isolation holds (tenant-b sees 0 of tenant-a rows)
[SMOKE] PASS
```

> 说明：脚本以「拥有者角色建表 → app 角色验证」的方式跑，确保 RLS 行为可被真正观察到。
> 若你直接用 superuser/owner 连接，PG 会按设计旁路 RLS，脚本会打印提示而非误报失败。

## ② 起后端 + 前端，浏览器点测工作台

现有 compose 已包含 **postgres + api + web**，且 **api 启动时自动跑迁移**
（`main.py` 调 `run_migrations`）——所以 ② 同时覆盖了 ①。

```bash
cd bible3dsphere
docker compose -f docker-compose.mission-bridge.yml up -d --build
# api:  http://localhost:8000        web: http://localhost:5173
```

1. 打开 `http://localhost:5173`，登录（本地开发可用 dev auth code，见 `ALLOW_DEV_AUTH_CODE`）。
2. 进入 **宣教 Tab → 宣教子标签 → 🧭 工作台**。

**关键前置：工作台按组织隔离，需要一个组织 + 你在其中有 `manage_settings`/`view_dashboard` 权限，否则面板会显示「需要组织上下文 / 无权限」。**
先建一个组织并给自己授权（用现有组织控制台，或直接在 DB 里 seed）：

```sql
-- 连到 compose 的 postgres：
--   docker compose -f docker-compose.mission-bridge.yml exec postgres \
--     psql -U mission_bridge -d mission_bridge
-- 用你的登录邮箱替换 you@example.org
INSERT INTO organizations(id,name,organization_type)
  VALUES ('church-1','测试教会','church') ON CONFLICT DO NOTHING;
INSERT INTO mission_bridge_tenant_memberships(tenant_id,user_id,role_key,status)
  VALUES ('church-1','you@example.org','tenant_admin','active') ON CONFLICT DO NOTHING;
```

> 前端目前把 `organizationId` 作为 prop 传给工作台；若你的账号已属于某组织，
> EvangelismPage 会带上它。如未接入组织选择，可临时在 `EvangelismPage` 里
> 传 `organizationId="church-1"` 联调。

**逐面板点测（13 个阶段）**：禾场情报 → 呼召辨识 → 工人准备度 → 装备训练 →
差派申请 → 差派委员会 → 团队与伙伴 → 部署财务 → 合法身份 → 家庭准备 →
合规审核 → 证件 Vault → 部署就绪 Gate。

**重点验证（这些不变式在真库上也应成立）**：

- 禾场 · 评估：勾选任一硬阻塞 → 结果 `blocked`、推荐≠可进入。
- 财务：高风险 Field 不含 `evacuation` 情景 → 创建报 422。
- 部署 Gate：不勾 Panel → 拒绝；勾硬阻塞 → `blocked`；候选人 ID = 当前登录邮箱 → 403（禁自审）；
  无阻塞 + Panel → `ready_for_deployment_planning`，`unlocks=deployment_planning`，`activatesDeployment=false`。
- 证件 Vault：证件号只显 `****尾3位`；下载走 step-up 安全会话。

## 关掉

```bash
docker compose -f docker-compose.mission-bridge.yml down        # 保留数据
docker compose -f docker-compose.mission-bridge.yml down -v     # 连数据一起删
```

## 代码侧已验证（无需 DB）

- `make mission-os-test` → **mission no_db 测试 169 通过**（含 8 项内存假库 e2e 联调 + 30 端点前后端契约锁）。
- 前端 18 个 `missionApi` 调用全部命中真实后端端点；13 个工作台面板组件均已定义并映射。
