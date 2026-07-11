# 后端审计修复报告 — bible3dsphere（2026-07）

配套文档：`docs/BACKEND_AUDIT_2026-07.md`（问题清单）。本文件记录**已修复**内容、**需你手动执行**的部分，以及**仍待跟进**项。
全后端 `python3 -m compileall backend` 通过（0 语法错误）。修复通过 4 路并行子任务 + 主线补全完成。

> 注意：本环境无法访问你的数据库/部署环境,也无法安装完整依赖栈,因此**运行时未跑通 442+ 测试**。所有改动为编译级验证 + 局部逻辑冒烟。上线前请在你的环境跑测试。

---

## 一、已修复（代码，编译通过）

### 安全 / 鉴权（main.py + routers）
- 微信回调开放重定向 + token 外泄 → 前端域名白名单(`ALLOWED_FRONTENDS`/`ALLOWED_ORIGINS`),非白名单回退可信前端,token 不再发往任意域。
- 硬编码管理员后门 `zpclord@sina.com` → 改为环境变量 `ADMIN_EMAILS`(逗号分隔)+ DB 角色。
- film 路由无鉴权 → start/status/sse/download 全部要求 session user,任务归属请求者,越权 403/404。
- 订阅自助提权 `/subscribe` → 仅允许免费档,付费档拒绝(需走 Stripe)。
- 验证码在发信失败时回传 → 改为仅在显式 `ALLOW_DEV_AUTH_CODE=1` 下返回,生产返回 503,绝不泄码。
- strongholds 跨租户覆盖 IDOR → `ON CONFLICT (id) DO UPDATE ... WHERE user_id=%s`,冲突归属他人则不更新。
- habit_id IDOR → 写入/更新前 `SELECT 1 FROM habit_state_machines WHERE id=%s AND user_id=%s` 归属校验。
- Stripe webhook 缺密钥跳过验签 → 缺 `STRIPE_WEBHOOK_SECRET` 时 fail-closed 503,不再信任 payload。
- mentor 关系角色 → 加入枚举校验;church_integration `create_reentry` → 补 `org_id` 字段(原本必 500)。
- formation_agent 连接泄漏 → 释放移入 `finally`。
- 输入边界 → feedback 等 limit 加钳制;translate_batch 加 Pydantic 模型。
- db-seed cron 鉴权 → `api/db-seed.js` 改为接受 `Authorization: Bearer $CRON_SECRET`(Vercel Cron 自动携带),兼容手动 `?token=ADMIN_TOKEN`,两者皆未配置则 500 fail-closed;`vercel.json` cron 路径去掉 URL 内密钥。(`node --check` 通过)

### 危机安全(最高优先)
- 被动兜底 `safety_scan.scan_crisis()` → 改走完整 `crisis_engine.triage()`(含中/英文 + 直接自杀意念/自伤/伤人/医疗急症),不再只用仅中文的 `detect_spiritual_crisis`。
- `crisis_engine` RED 标记 → 补英文急性标记(`kill myself`/`end my life`/`overdose`/`hang myself`/`bought pills` 等)与计划语言,英文急性意念现可触发 red 紧急升级。
- `guardian_engine` → 补英文高危词,不再拖 RED 路径后腿(留 TODO 合并词表)。

### LLM / 向量可靠性
- ~48 个引擎的死 AI 路径 → 新增 `backend/engine_ai.py` 的 `call_ai()` + `llm_provider.complete_text()`,48 个引擎改调之,`call_llm`(不存在)引用清零。`use_ai` 现真正生效。
- `embed_text` 失败不再返回 16 维 mock → 返回 None;`semantic_engine.rank` 遇 None/维度不符降级为不排序透传,不再静默空结果。
- `preference_vector.fuse_query_with_preference` → 融合前断言等维,不符则记日志并返回原查询向量(不再 numpy 广播崩溃)。
- `worldview_orchestrator.crisis_guard` → `triage()` 包 try/except,失败走降级透传(fail-safe)。
- `llm_provider` → 4xx(400/401/403)立即抛出不重试;`generate_text/json/complete_text` 加默认 `max_tokens=2048`;httpx 改模块级 keep-alive 复用。
- `vector_search.generate_embedding` → 加超时 + 重试 + 优雅降级。
- 引擎 `STATES[N]` 硬索引 → 越界回退 `STATES[0]`(消除 IndexError 隐患)。

### 数据 / 并发 / 资源
- `notify_pending_push` → 三段式:取行→释放连接→网络发送(逐条标记已送达,防重发)→短事务收尾,不再持连接跨 200 次 push。
- `_safe` → 用 SAVEPOINT 局部回滚,不再回滚整个共享事务。
- formation 事件 → 新增 `record_formation_event_sync()` 同步直写,`record_formation` 仅在真正写入后返回 True(修复线程池里 `get_event_loop` 静默丢事件)。
- `disciple_graph` 下游节点 → 守卫缺失 `result`,短路而非级联 KeyError。
- `disciple_worker.run_once` → 按用户取/放连接,不再整轮持有单连接。
- `diagnosis_hub.record_diagnosis` → `_acquire()` 移入 try。
- `core/deps._CHURCH_CACHE` → 容量上限 + TTL 驱逐 + 锁。
- `core/ratelimit.client_ip` → 取右起可信 XFF(`TRUSTED_PROXY_HOPS`,默认 1),不再被最左伪造绕过。
- `core/config.ALLOWED_ORIGINS` → 默认改为已知安全域(holiness.uk + localhost),不再默认 `*`。

### 配置 / 部署 / 卫生
- `.env.example` → 按代码实读 env 重写,115 个真实 key 分组;移除 13 个无用 key;`VITE_*` 移入"前端仓库"注释区。
- `Dockerfile` → 加非 root 用户;装 CPU-only torch(不再拉 CUDA);加 HEALTHCHECK。(LibreOffice/ffmpeg 是否可移除留待确认)
- `backend/requirements.txt` → 浮动 `>=` 加上界;修正不存在的 `requests==2.33.1`→`2.32.3`。
- `backend/tests/conftest.py` → app 导入加保护,`pytest --collect-only` 现可收集 681 项(不含真实 DB)。
- 迁移文件(新增,**未应用**):`0144_enforce_ownership_not_null.sql`、`0145_right_to_erasure.sql` + `README_right_to_erasure.md`(擦除函数覆盖 164 email-keyed + 4 user_id 表)。
- git 卫生:`.idea/`、`archive/`(旧前端)、根目录一次性脚本、`_perm_probe.txt`、重复 `pytest.ini` 已 `git rm --cached`(共 62 项暂存删除,保留磁盘);`.dockerignore` 扩展排除 tests/env/缓存/大备份;root `requirements.txt`、`render.yaml`、`netlify.toml` 标记 DEPRECATED。

---

## 二、需要你手动执行（我无法在此环境完成）

1. **清 git 锁并提交**:`.git/index.lock` 是空文件但本挂载不允许 unlink。请在你本机执行 `rm -f .git/index.lock`,然后 `git status` / `git diff` 复核,`git rm requirements.txt`(补完删除),再分批提交。
2. **应用迁移**:`0144` 若 `subscriptions` 存在 NULL email 会失败——先清理/回填;`0145` 是擦除函数,需另建 `POST /api/account/erase` 端点调用(见下待跟进)。
3. **配置新环境变量(生产)**:`ADMIN_EMAILS`、`CRON_SECRET`(Vercel Cron)、`ALLOWED_FRONTENDS`/`ALLOWED_ORIGINS`、`TRUSTED_PROXY_HOPS`;**`ALLOW_DEV_AUTH_CODE` 生产务必不设**。
4. **填真实密钥**:`.env.example` 现列 115 项,按需填入部署环境。
5. **Embedding 供应商余额**(见你贴的运行日志):siliconflow 返回 `403 余额不足`、deepinfra 返回 `402 需付费`,导致所有 embedding 失败、回退合成随机向量(`0/20 ok`,语义排序失效)。**充值任一供应商**,或按下方改进项接本地模型。
6. **跑测试**:在你有依赖 + Postgres 的环境跑 `pytest backend`(681 项),上线前验证。

---

## 三、仍待跟进（本轮未做 / 需决策）

- **错误信息泄漏清扫**:✅ 已完成。128 处 `status_code=500` 的内部异常泄漏(`detail=str(exc)` / `detail=f"...: {exc}"`)已跨 55 个路由文件统一改为通用/仅动作标签消息(保留 `from exc` 异常链与已有的服务端日志如 `handle_exc`)。全部编译通过。剩余 13 处为**有意保留**:`except ValueError/PermissionError` 的 4xx 校验消息(面向用户的合法提示)+ 2 处 main.py 仅用于服务端 `print` 日志(不回传客户端)。建议后续加一个全局 500 日志中间件,弥补移除 detail 后的可观测性。
- **流式 handler 的同步阻塞**:`post_chat` / 微信异步 handler 内的同步 DB 调用未包裹(包裹流式响应有破坏语义风险),需谨慎重构。`realtime.py` 的 WS 已用 `to_thread` 处理。
- **右擦除端点**:`0145` 擦除函数未接端点,需在 main.py 加鉴权后的 `POST /api/account/erase`。
- **DB 层多租户防线**:RLS(`supabase_rls.sql`)仍未启用、无到 users 的 FK。是否在 Neon 上启用 RLS(per-request GUC)是架构决策。
- **规模化**:限流/会话内存态 → 横向扩容前接 Redis。
- **Embedding 合成回退质量**:当前所有付费 embedding 供应商挂掉时回退"合成随机向量",语义检索基本失效。改进:改用本地 `sentence-transformers`(BGE-M3,已在依赖里)作为离线回退,质量远好于随机向量。
- **仓库瘦身**:`.git` 343MB(19MB pkl + LFS 向量),如需缩小 clone 用 git-filter-repo/BFG 重写历史(破坏性,未做)。
- **前端 `bible3dsphereWeb` 未审计/未修**——重新挂载后单独一轮。
