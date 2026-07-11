# Mission OS 文档索引

属灵星球 Mission OS —— 从禾场情报到部署预备的宣教工人生命周期系统。
应用内可折叠路线图：「宣教」Tab →「宣教」子标签 →「🛰️ Mission OS 路线图」
（前端：`bible3dsphereWeb/src/features/mission-os/roadmap/`）。

## 文档

- [roadmap.md](./roadmap.md) — Batch 0–6 全量路线图与完成定义。
- [integration-map.md](./integration-map.md) — 端到端生命周期主线与跨批依赖。
- [RUNBOOK.md](./RUNBOOK.md) — 迁移 smoke + 工作台联调的一键运行手册（需带 DB 的环境）。
- 验收报告：
  - [batch-1-validation-report.md](./batch-1-validation-report.md) — 身份/多租户/权限/隐私/同意
  - [reuse-matrix-batch-1.md](./reuse-matrix-batch-1.md) — Batch 1 复用-缺口矩阵
  - [batch-2-validation-report.md](./batch-2-validation-report.md) — 禾场情报系统
  - [batch-3-validation-report.md](./batch-3-validation-report.md) — 呼召辨识/恩赐/准备度
  - [batch-4-validation-report.md](./batch-4-validation-report.md) — 装备/课程/语言/实习
  - [batch-5-validation-report.md](./batch-5-validation-report.md) — 差派教会/机构/团队/伙伴
  - [batch-6-validation-report.md](./batch-6-validation-report.md) — 财务/合规/医疗/家庭/安全/撤离

## 实现总览（Batch 1–6）

| 项 | 数量 |
|---|---|
| `mission_os` 领域模块（纯 Python 不变式） | 19（含 `pipeline.py` 主线） |
| 数据库迁移（0186–0207，均 tenant_id + RLS） | 22 |
| FastAPI 路由（`routers/mission_*`） | 16 |
| API 端点 | 62（Mission OS Batch 1–6，不含 MissionBridge） |
| 测试文件（`tests/test_mission_*`） | 8 |
| Mission 测试 | 281 通过 |
| 在线路线图 | Batch 0–6 / 72 Skill |
| 前端 | 路线图查看器 + **Mission OS 工作台**（`features/mission-os/{roadmap,console,api}`） |

## 前端 UI

「宣教」子标签内三视图切换：**🌉 邻舍之桥 · 🧭 工作台 · 🛰️ 路线图**。

- **工作台（MissionConsole）**：按生命周期主线组织的操作台，面板覆盖
  禾场情报(B2)→呼召辨识/准备度(B3)→装备训练(B4)→差派申请/委员会/团队/伙伴(B5)→财务/合法身份/家庭/合规/加密证件 Vault(B6)→Deployment Gate(B6)，
  接真实后端 API（`features/mission-os/api/missionApi.js` → `/api/v1/mission/...`），
  含 加载 / 空 / 错误 / 无权限 四态；按组织隔离，无组织上下文时给出引导。
- **路线图（MissionOSRoadmap）**：只读，Batch 0–6 / 72 Skill 可折叠。

## 运行测试

```bash
cd backend
python3 -m pytest tests/test_mission_*.py -q      # 需 pytest + fastapi + pydantic
```

`no_db` 标记的测试覆盖领域不变式、API 契约、迁移文本断言与跨批集成。
2026-07-11 已使用 Postgres.app 临时 PostgreSQL 从空库执行 190 个项目迁移；
0186–0206 的 21 个代表表、RLS 与 tenant policy 均通过，并由非 owner
`mission_app` 验证 tenant-b 无法读取 tenant-a 数据。CI 入口为
`backend/scripts/mission_os/migration_smoke.sh`。

## 加密 Vault

迁移 `0207_mission_os_encrypted_vault.sql` 增加密文 secret/file、密钥版本与安全访问授权表。
证件号和最多 10 MiB 的证件文件使用 AES-256-GCM，AAD 绑定 tenant/resource/field；数据库只保存密文、nonce、摘要和 key version，密钥由 `MISSION_VAULT_KEYS` JSON keyring 注入。缺少密钥时 fail-closed。下载要求最近 10 分钟真实 MFA、安全会话与不可变审计。

2026-07-11 已在第二个临时真实 PostgreSQL 空库执行 191 个迁移；三张 Vault 表 RLS 全部启用，非 owner 跨租户查询结果为 0。

## 边界与终态

- 无 Batch 7。Deployment Readiness Gate 的 `ready_for_deployment_planning`
  即系统自动化终态；其后的实际出发/抵达/现场运营属于运营侧，不由自动化 Gate 触发。
- 任何自动化阶段都不会把工人标记为「已出发」（`pipeline.deployment_activates_worker() == False`）。
