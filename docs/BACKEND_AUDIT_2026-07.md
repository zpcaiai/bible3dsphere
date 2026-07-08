# 后端全量审计报告 — bible3dsphere（2026-07）

## 2026-07-08 闭环复查状态

本文件保留 2026-07 初始审计全文，下面是当前代码复查后的状态，避免把已修项继续当作未闭环缺口：

- “必须最先修”10 项中，当前代码已看到闭环：微信 OAuth redirect 白名单、危机扫描改走双语 triage、film 生成/状态/SSE/下载鉴权与任务归属、订阅自助提权阻断、验证码不在生产回传、strongholds upsert 加 user_id 守卫、管理员改为 `ADMIN_EMAILS` 环境变量、`.env.example` 补齐实际读取 key、Vercel cron 不再把 secret 放在 URL、Stripe webhook 缺签名密钥 fail-closed。
- 同步修复的相关完整性项：`/api/habits/{habit_id}/log` 增加 habit 归属校验；仓库删除被追踪的 `.DS_Store`。
- 仍需作为后续工程治理跟进：DB 层 RLS/FK/cascade、账号注销/右擦除、LLM 入口统一、embedding 维度统一、错误处理去 `detail=str(exc)`、PII 日志脱敏、Docker/依赖锁定、CI no-db 子集常态化。这些不是当前扩充/前端 i18n 闭环阻断项，但属于产品级上线前的长期完整性工作。

> 范围：`backend/`（390 个 Python 文件 / ~106k LOC / ~135 引擎 + 162 路由 + ~140 迁移）。
> 前端 `bible3dsphereWeb` 未挂载，本轮**未审计前端**——重新添加该文件夹后再补。
> 方法：4 路并行深审（API 层 / 核心引擎与编排 / 数据与安全 / 配置与部署），机械扫描（无语法错误、无硬编码密钥、f-string SQL 均为静态列名 + `%s` 参数，非注入）。

值得肯定的基础：SQL 全参数化、bcrypt cost-12、256-bit 会话 token、逐记录 IDOR 检查（fetch→比对 session email→403）在多数路由一致到位、org/platform 控制台 RBAC 干净、crisis-share 有看护者核验+邮箱脱敏+审计、危机风险下限“模型只能升不能降”的设计很好。问题集中在少数 auth/危机安全缺口，以及系统性的错误处理与 LLM 集成碎片化。

---

## 🔴 一、必须最先修（Fix first — 高风险且具体）

1. **微信回调开放重定向 + 会话 token 外泄 → 账号接管**
   `main.py:3280` `wechat_callback`：`redirect_target` 取自攻击者可控的 base64 `state` 里的 `custom_frontend`，随后把新签发的 `session_token` 拼进 `RedirectResponse(f'{redirect_target}/?token={session_token}')`。构造登录链接即可把受害者 token 送到任意域名。
   **修复**：前端域名白名单，非白名单直接拒绝。

2. **危机安全的双语盲区（对心理健康类应用最高价值）**
   - `safety_scan.py:24` + `crisis_engine.py:658`：挂在 ~24 个自由文本端点（日记/省察/笔记/记忆/试探等）的被动兜底只调用 `detect_spiritual_crisis()`——**仅中文、仅属灵子类**正则，**不匹配直接自杀意念**（“想死/自杀/kill myself”），且完全不匹配英文。
   - `crisis_engine.py:165-181`：唯一能到 `risk="red"` 的强/情境标记全是中文；英文急性计划（"I bought pills, ending it tonight"）最高只到 orange，`red_emergency_message` 与看护者 SMS 升级永不触发。
   **修复**：被动兜底改走完整 `triage()`（含英文+SI 模式）；给 RED 列表补英文急性/means-acquired 标记。

3. **film 路由完全无鉴权（触发付费生成）**
   `routers/film_studio.py:870-951`：`/api/film/start`、`/start-ppt`、`/status/{jid}`、`/sse/{jid}` 无任何 session 校验，任何人可触发 Kling/Gemini/ElevenLabs 付费生成并读任意任务（仅 5/min + 全局并发锁）。
   **修复**：start/status/sse/download 一律要求 session user，并将任务归属到请求者。

4. **订阅自助提权**
   `routers/productization.py:216-238` `/subscribe`：任意登录用户可把自己订阅设为任意 `plan_key`（含付费档）`status='active'`，无支付/管理员校验；`entitlements/check` 直接读它。
   **修复**：仅允许免费档，真实升级走 Stripe/管理员。

5. **验证码在发信失败时回传给客户端**
   `main.py:3557` `email_send_code`：`except` 兜底返回 `{'ok': True, 'dev_code': code}`。攻击者诱发 SMTP 失败即可拿到验证码注册任意邮箱。
   **修复**：绝不回传 code，服务端记日志，返回通用错误。

6. **strongholds 跨租户覆盖（IDOR）**
   `routers/strongholds.py:474-489` `upsert_scan`：`INSERT ... ON CONFLICT (id) DO UPDATE` 用客户端提供的 `payload.id`，冲突子句无 `user_id` 守卫，可覆盖他人扫描内容。
   **修复**：`DO UPDATE ... WHERE stronghold_scans.user_id=%s`。

7. **硬编码管理员后门**
   `main.py:3790` / `:3830`：`_is_admin()` / `_get_user_role()` 对 `email=='zpclord@sina.com'` 无条件返回 admin，绕过 DB 角色且不可配置（SECURITY.md §3 已列 TODO 但仍在跑）。
   **修复**：改 `ADMIN_EMAILS` 环境变量 / DB 角色。

8. **.env.example 与真实密钥严重不同步（部署即坏）**
   缺 ~55 个代码实际读取的 key，含 `STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、`JWT_SECRET_KEY`、`ANTHROPIC_API_KEY`、`HF_TOKEN`、`R2_ACCESS_KEY_ID/SECRET`、`VAPID_PRIVATE_KEY`、`SENDGRID/RESEND_API_KEY` 等；同时多列 ~26 个已废弃 key。
   **修复**：按 `getenv` 扫描重生成，拆出前端 `VITE_*`。

9. **vercel.json cron 鉴权实际失效**
   `"/api/db-seed?token=${ADMIN_TOKEN}"`：Vercel 不会把环境变量插值进 cron 路径，发出的是字面量 `${ADMIN_TOKEN}`，db-seed 鉴权形同虚设（且密钥入 URL 是反模式）。
   **修复**：改用请求头 `CRON_SECRET`，在函数内校验。

10. **Stripe webhook 缺密钥时跳过验签**
    `routers/billing.py:113-127`：`STRIPE_WEBHOOK_SECRET` 未配置时直接信任 payload 调 `_apply_event`，任何人可伪造订阅事件。
    **修复**：缺密钥时拒绝（503/400），fail-closed。

---

## 🟠 二、数据完整性与多租户隔离

- **DB 层隔离是“纸面”而非现实**：`supabase_rls.sql` 自述为“前瞻性”且**未启用**，线上是 raw psycopg2、Supabase Auth 不在前面。~240 个 email-keyed 表**无 RLS、无到 users 的 FK、无 cascade**——隔离 100% 依赖应用层每处 `WHERE email=%s`。今天这条纪律确实一致，但任何一次漏写就是无声跨租户泄漏，且无第二道防线。
  **建议**：在 Neon 上按 per-request session GUC 启用 RLS；或明确记录“仅应用层隔离”并加 CI lint——每个个人表查询必须带 email 谓词。
- **无账号注销 / 数据擦除端点**：跨 240 表长期存储危机与心理健康 PII，却无右擦除流程（grep `delete-account/注销/DELETE FROM users` 皆无）。对心理健康类应用是合规与留存风险。
- **ownership 列可空**：`migrations/0105:13`、`0116:11`、`0122:44` 等 `created_by_email/email` 可空或 `DEFAULT ''`，可能出现落在租户过滤之外的 NULL/'' owner 行。私有表 ownership 列应 `NOT NULL`。
- **habit_id IDOR**：`main.py:5276-5311` `log_habit_execution` 用请求 `habit_id` 无归属校验，可刷他人 streak。加 `WHERE id=%s AND user_id=%s`。

## 🟠 三、LLM / 向量可靠性（功能“看着有其实没生效”）

- **~48 个引擎的 AI 增强是死代码**：`anger_engine.py:146-159`（+47 个同构引擎）`_call_ai` 先调 `llm_provider.call_llm`（**该函数不存在**）再退到 `waiting_engine.call_ai_provider(prompt)`，但后者签名要 `List[Dict]`，传字符串 → HTTP 400 → None。`use_ai=True` 静默从不增强，`ai_used` 恒 False 且无错误上报。
  **修复**：构造真正的 messages 列表，统一走 `llm_provider`，删掉 `call_llm` 引用。
- **embedding 失败静默返回 16 维 mock** → 语义检索静默零结果：`llm_provider.py:519-524` `embed_text` 任意失败退到 16 维 mock，`semantic_engine.py:67` 丢掉维度不符的行，embedding API 一抖动搜索就返回空而非报错。
- **embedding 维度三处不一致**：mock=16 / vector_search OpenAI=1536 / preference_vector BGE-M3=1024；`fuse_query_with_preference` 无维度检查直接 `(1-a)*q + a*pref` → numpy 广播错误/垃圾值。统一 embedding 源与维度，融合前断言等维。
- **非重试 4xx 仍被重试**：`llm_provider.py:279-296`，400/401 被外层 `except` 吞掉照样退避重试，浪费延迟并掩盖鉴权/配置错误。
- **无默认 max_tokens**：`llm_provider.py:428-508`，调用方不传时输出长度与成本无界。
- **每请求新建 httpx.Client**：`llm_provider.py`、`worldview_llm.py:191`、`waiting_engine.py:395`，无连接复用，高并发下每次 TLS 握手开销。改模块级复用 client。
- **危机 triage 未包 try/except**：`worldview_orchestrator.py:112` `crisis_guard` 处理了 `ce is None` 但没保护 `ce.triage()`，安全关键路径异常会整体崩 `run_pipeline` 而非 fail-safe。

## 🟠 四、并发 / 资源 / 数据丢失

- **持有 DB 连接期间做阻塞 web-push**：`disciple_integration.py:684-737`，`with conn.cursor()` 内串行发最多 200 条 push，连接池会耗尽；且整个大事务，中途崩溃会重发已送达的 push。先取行→释放连接→网络发送→再取连接短事务标记。
- **formation 事件静默丢失**：`formation_bridge.py:59-71`、`formation_pipeline.py:503-533` 在同步线程池里用 `asyncio.get_event_loop()/ensure_future` 写库；worker 线程里 `get_event_loop()` 抛错被吞→事件被跳过，`record_formation` 仍返回 True。选定同步写入路径。
- **`_safe` 回滚整个共享事务**：`disciple_integration.py:73-82` 出错即 `cur.connection.rollback()`，丢弃该连接上其他挂起写入。改用 SAVEPOINT 或独立读连接。
- **WebSocket / 部分 async handler 里跑同步 psycopg2**：`routers/realtime.py:592-760`、`main.py:4314/3152/3327/3434`，每条消息阻塞事件循环。用 `asyncio.to_thread`/executor 或改 `def`。
- **模块级缓存无界/无锁**：`core/deps.py:143-166` `_CHURCH_CACHE` 只覆盖不驱逐，按邮箱数永久增长。加容量上限/定期清理。
- **X-Forwarded-For 取最左**：`core/ratelimit.py:192-204` 客户端可控，轮换 XFF 绕过限流。改取右起可信跳数。

## 🟡 五、错误处理与 PII 卫生（系统性）

- **~174 处 `raise HTTPException(500, detail=str(exc))`** 把 DB/schema/栈细节泄给客户端。统一：服务端记日志 + 返回通用消息（共享 error helper）。
- **大量 `except Exception: pass` 吞掉失败写入/审计**：模板引擎路由的 analyze 持久化、`billing.py:135-173`、`platform_admin.py:160-165`、`admin_ops.py:29-51`、`ai_tutor.py:44-45`（危机扫描！）、`analytics.py:39-43`、`community.py:118-123` 等。即便响应可成功也要记失败。
- **邮箱明文进日志（38+ 处）**：`evangelism.py:134`、`personal_notes.py:113`、`main.py:320` 等，把可识别用户与敏感属灵/危机行为关联进 HF 共享日志。改用 hash/前缀（`telemetry.py` 已有 `id_prefix[:8]` 模型）。
- **session token 走 `?token=` query 参数**：`main.py:3723`，token 会进访问日志/浏览历史/Referer。仅走 Authorization 头。
- **CORS 默认 `*`**：`core/config.py:31`，生产若未设 `ALLOWED_ORIGINS` 则全开（当前该分支强制 `allow_credentials=False` 且用 Bearer，风险被缓解）。给非通配默认或 prod 未设即 fail-closed。
- **限流/会话为进程内内存**：横向扩 HF 副本会绕过 600/min 且分裂会话（会话有 DB 兜底，限流没有）。扩容前接 Redis。

## 🟡 六、输入校验与正确性

- `routers/church_integration.py:265` `create_reentry` 读 `body.org_id` 但 `ReentryCreate` 无该字段 → **每次调用必 500**（AttributeError）。补字段或删逻辑。
- `formation_agent.py:139-146 / 164-171`：`except: pass` 路径连接只在成功分支释放 → 连接泄漏。放 `finally`。
- 列表/枚举类字段普遍缺 `ge/le`/`Literal`：`main.py:4936/5029/6208`、`feedback.py:159`（负 limit → `LIMIT -1` 500）、`personal_notes.py:84`、`memory.py:91/109`；`care.py:166`、`gift_calling.py`（`scores` 无界 int）、`strongholds.py:416` 等 mass-assignment。用 `Query(ge=,le=)` + `Literal`/`conint`。
- `mentor.py:106-132` `create_rel`：可对任意 `counterpart_email` 单方面建关系且 `my_role` 自由串，无接受步骤。加 pending→active 接受流 + 角色 `Literal`。
- `admin_content.py:658-703` recycle-bin：全量拉 6 表软删行在 Python 里拼排切。把 `LIMIT/OFFSET` 下推 SQL。

## 🟡 七、配置 / 部署 / 仓库卫生

- **Docker 以 root 运行**（无 `USER`）；**单阶段镜像**装默认 CUDA `torch` + sentence-transformers + libreoffice + ffmpeg + poppler → 多 GB、HF 构建慢。加非 root 用户；pin CPU-only torch wheel；砍不必要的 LibreOffice；考虑多阶段。
- **依赖大量浮动 `>=`**（torch、anthropic、boto3、google-genai、neo4j、psycopg2-binary…）→ 构建不可复现。pin 精确版本或加上界/锁文件。
- **root `requirements.txt` 是孤儿**：Dockerfile/render 都用 `backend/requirements.txt`；且与 backend 冲突（edge-tts >=6.1 vs >=7.0）、pin 可疑（pandas==3.0.2）。删除或明确 scope。
- **部署配置三处漂移**：Dockerfile/HF（7860, Neon）、`render.yaml`（8000, 免费 Render PG）、`netlify.toml`（仍构建已迁走的 emotion-sphere-ui）。只有 HF+Neon 是真的；后两者过时误导，清理。
- **仓库里的死物**：`.idea/`（8 文件）、`archive/`（47 文件旧 Next 前端）、根目录一次性脚本（`biblical_film_studio.py`、`video_studio_server.py`、`generate_david_goliath.py`、`fix_sphere.py`、`commit_b10_b12.sh`）、重复 `pytest.ini`、`.git` 343MB（19MB pkl 原始 blob + LFS 向量）。git rm / 移入 scripts / 视需要 history rewrite。
- **测试大而跑不动**：442 个测试函数 / 46 文件，但 `conftest.py` 导入时即 `import main` 并硬编码 `localhost:5431`，无依赖栈+无 live PG 时连 `--collect-only` 都失败。把 `main` 导入放进 fixture、给 DB 测试打标，让 CI 能跑 no-db 子集。
- `.dockerignore` 未排除 `backend/tests`、迁移、docs → 测试与 SQL 被打进运行镜像。

---

## 八、架构级改进建议（非 bug，但回报高）

1. **抽引擎基类**：~48+ 个近乎复制的 `*_engine.py`（STATES+_pick+analyze+build_prompt+_call_ai+_detect_crisis+formation_signal）。上面的“死 AI 路径”和 `STATES[N]` 硬索引 landmine 都被复制 ~48 次，各要改 ~48 处。抽 base/mixin，一处修复全局生效。
2. **统一 LLM 入口**：现有三条独立入口（unified `llm_provider` / legacy `waiting_engine.call_ai_provider` / `vector_search` 自带 `AsyncOpenAI`），retry/timeout/维度/错误行为各不相同。全部收敛到 `llm_provider`。
3. **去掉“伪装成未配置”的降级**：普遍 `except: pass/return None` 让缺表、签名不符、维度不符都长得像“功能未开”。每个降级路径加结构化日志/指标。
4. **危机安全词表合一**：`guardian_engine.py:82`、`crisis_engine._TYPE_RULES`、`detect_spiritual_crisis` 三套漂移词表，合并为单一双语 lexicon。
5. **右擦除 + FK/cascade**：给个人表加到 users 的 FK 与 cascade，并实现账号删除流程。

---

## 九、本轮未覆盖 / 后续
- **前端 `bible3dsphereWeb` 未审计**——重新挂载后补一轮（对应做 auth token 存储、XSS、API base、PWA、可访问性等）。
- 建议先修“一、必须最先修”10 项 + “二”的危机双语盲区，再处理系统性错误处理与 LLM 统一。
