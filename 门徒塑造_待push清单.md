# 门徒塑造引擎 — 待 push 清单 / 环境变量 / 真机验证

> 本会话从「代祷 tab 加门徒塑造子 tab」一路做到完整 DFOS：11 引擎 + 10 态状态机 + 像基督指数 + 数字孪生 + 倍增网络 / 整合层（统一孪生·统一导师·真 Neo4j·周月复盘）/ 事件流 + 消费者 + 里程碑 + 异步 Web Push / 独立 worker + DAG 编排 + formation 身份统一。
> 全部 `.py` ast 与前端 `@babel` 解析通过；核心逻辑用 stub 自测通过。沙箱无 fastapi/DB/Neo4j/pywebpush，**未跑真运行时**——push 后需真机验证一轮。

---

## 1. 文件清单（按 commit 分批）

### 批次 A — 门徒塑造核心（若已 push 可跳过）
- 新增 `backend/disciple_engine.py` — 10 态状态机/11 维/CI/9 偶像/8 品格/DMI/11 引擎/AI 导师七段
- 新增 `backend/routers/disciple.py` — `/api/disciple/*`
- 新增 `backend/migrations/0035_disciple_formation.sql`
- 改 `backend/main.py` — 表 init + 注册 router
- 新增 `emotion-sphere-ui/src/DiscipleFormationView.jsx`
- 改 `emotion-sphere-ui/src/api.js`、`emotion-sphere-ui/src/PrayerWallPage.jsx`

### 批次 B — 整合层
- 新增 `backend/disciple_integration.py` — 统一孪生/统一导师/Neo4j/周月复盘/事件流
- 新增 `backend/migrations/0036_domain_events.sql`
- 改 `backend/routers/disciple.py`、`backend/main.py`

### 批次 C — 事件消费者 + 里程碑
- 新增 `backend/migrations/0037_agent_runs.sql`
- 改 `backend/disciple_integration.py`（process_user_events/get_milestones）、`backend/routers/disciple.py`、`backend/main.py`
- 改 `emotion-sphere-ui/src/DiscipleFormationView.jsx`、`emotion-sphere-ui/src/api.js`

### 批次 D — 异步 Web Push
- 改 `backend/disciple_integration.py`（notify_pending_push）、`backend/routers/push.py`（run_due 捎带）、`backend/routers/disciple.py`（/cron/notify）、`backend/main.py`（agent_runs.notified 列）、`backend/migrations/0037_agent_runs.sql`

### 批次 E — worker + DAG + formation 统一
- 新增 `backend/disciple_worker.py` — 独立异步 worker
- 新增 `backend/disciple_graph.py` — 零依赖 DAG 编排
- 新增 `backend/migrations/0038_formation_uid_to_email.sql` — 回填 user_id→email
- 改 `backend/formation_engine.py`（_canon_uid 读写归一）、`backend/routers/disciple.py`（走 DAG + /cron/worker）、`backend/main.py`（lifespan 启 worker）

### 另：慕道班（独立功能，若还没 push）
- 新增 `backend/migrations/0023_seekers_class_courses.sql`
- 改 `backend/main.py`、`emotion-sphere-ui/src/EvangelismPage.jsx`、`emotion-sphere-ui/src/api.js`

> 一次性全提交也行：`git add -A`（确认没有不想带的改动），或按上面分批。迁移 0035–0038（+0023）push 到 GitHub main 后由 CI 在 Neon 生效。无新增二进制资源，不涉及 LFS。

---

## 2. 一把梭 git（Mac 终端）

```bash
cd /Users/stephen/Documents/Projects/DoctorPro/bible3dsphere
rm .git/*.lock 2>/dev/null
ls .git/rebase-merge .git/rebase-apply 2>/dev/null   # 应无输出

git add backend/ emotion-sphere-ui/src/
git status            # 核对清单
git commit -m "feat(门徒塑造): DFOS 全量 — 引擎/整合层/事件消费/异步推送/worker/DAG/formation统一"
git push origin main
```

---

## 3. 环境变量（都可选，不配也能跑——对应能力降级）

| 变量 | 作用 | 不配时 |
|---|---|---|
| `GEMINI_API_KEY` / `SILICONFLOW_API_KEY` | AI 增强（评估/导师/复盘）| 回退确定性分析，功能仍可用 |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | Web Push（与晨更/晚祷共用）| 不推送，站内仍有里程碑/提醒 |
| `PUSH_CRON_SECRET` | 保护 `/cron/*` 定时入口 | `/cron/*` 返回 403 |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | 属灵图谱同步/洞察 | enabled=false，其余照常 |
| `DISCIPLE_WORKER_ENABLED=1` | 开常驻后台 worker | 不开；用 inline 消费 + push cron 捎带 + `/cron/worker` |
| `DISCIPLE_WORKER_INTERVAL` | worker 轮询秒数（默认 300）| 用默认 |

> 注：以上多为本项目已有变量（AI、VAPID、PUSH_CRON_SECRET、NEO4J）。**新增的只有** `DISCIPLE_WORKER_ENABLED` / `DISCIPLE_WORKER_INTERVAL`，且仅在你想用常驻 worker 时才需要。
> 慕道班另需 R2 变量（与诗歌/主日学共用）+ 可选 `R2_SEEKERS_PREFIX`（默认 `seekers-class/`）。

### 通知触发方式（三选一/可叠加）
1. 已有的 `/api/push/run-due` 定时任务跑时，**自动捎带** disciple 推送（零额外配置）。
2. 开 `DISCIPLE_WORKER_ENABLED=1`，常驻线程每 N 秒自动消费+推送（适合 render/HF 持久进程）。
3. 外部 cron 周期 POST `/api/disciple/cron/worker`（带 `X-Cron-Secret`），适合无常驻进程的部署。

---

## 4. 真机验证步骤（push 部署完成后）

1. **入口**：代祷 tab → 顶部子标签出现「🧬 门徒塑造」。
2. **反思评估**：进「✍️ 反思」写几句（带点情绪/挣扎，如「被否定时焦虑，但有交托，也在带一位弟兄」）→ 提交。期望：返回当前属灵状态 + CI + 导师七段；若攒够次数会弹「周复盘就绪」nudge。
3. **概览**：CI、状态阶梯、11 维度条、今日顺服、DMI 显示；若你之前用过偶像监测/等候/体检/福音诊断，应看到「🔗 画像数据来源」标签（证明整合层吸收成功）。
4. **引擎**：11 张卡可展开，看每个引擎的分析。
5. **导师**：问一句（如「该不该换工作，怎么分辨」），看是否带着既有牧养记忆回答。
6. **门徒**：添加一位门徒 → DMI/网络更新；配了 Neo4j 才有「🕸 属灵图谱洞察」。
7. **复盘**：周/月复盘出聚合 + 牧养总结；底部「🏛 属灵里程碑」随状态变化累积。
8. **推送**（配了 VAPID）：先在站内订阅晨更/晚祷推送；触发一次 nudge 后，等 push cron 或手动 `curl -X POST .../api/disciple/cron/worker -H "X-Cron-Secret: <secret>"`，看手机是否收到「🧬 …」通知。

### 快速冒烟（命令行）
```bash
# 元信息（含 DAG 拓扑）
curl -s https://<域名>/api/disciple/meta | jq '.states|length, .engines|length, .pipeline'
# 手动触发 worker（替换 secret）
curl -s -X POST https://<域名>/api/disciple/cron/worker -H "X-Cron-Secret: <PUSH_CRON_SECRET>"
```

---

## 5. 已知边界 / 非阻断
- 沙箱无法跑 fastapi/真 DB，运行时未验证——以真机为准。
- formation 历史中「匿名无 email 用户」的旧 id-keyed 行不会被 0038 回填（无 email 可映射），属预期。
- 事件消费当前 inline + worker 两条路；LangGraph 式自主 agent（分支/循环/人在环）按需再上，节点签名已对齐迁移成本低。
