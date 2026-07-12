# 后端重构路线图（backend/main.py 拆分与可维护性）

> 更新：2026-07-12。本文档由本轮 FastAPI 后端优化收尾时生成，
> 记录已完成的拆分、main.py 剩余结构、后续分阶段计划与回归测试清单。

## 一、本轮已完成

### 1. routers/attention.py → routers/attention/ 包
- 原单文件约 4497 行、94 条路由，已机械拆分为 11 个子模块：
  `_common`（共享 router + init）、`_models`、`covenant`、`focus`、`admin`、
  `reports`、`_social`、`accountability`、`groups`、`diagnosis`、`warfare`。
- `__init__.py` 按原文件顺序导入子模块（路由注册顺序不变），并把全部模块级
  符号重导出，`from routers.attention import router, init_attention_router, ...`
  与 monkeypatch 式访问保持兼容。
- 已验证：新旧路由（方法+路径）94 条逐字一致；包可独立导入且注册 94 条路由。
- 旧 `routers/attention.py` 已删除（git 状态显示 deleted 属预期）。

### 2. main.py 首批拆分（路径原样、逐字搬移、init 注入依赖）
| 新模块 | 路由 | 注入依赖 |
|---|---|---|
| `routers/main_extracted_sermon.py` | `/api/sermon/journals`（GET/POST）、`/api/sermon/journals/{id}`（GET/DELETE） | get_db、release_db、get_session_user、is_admin、to_shanghai_iso |
| `routers/main_extracted_health.py` | `/health`、`/health/live`、`/health/ready`、`/api/ai-status`、`/api/health/db` | get_db、release_db、get_db_pool（getter，因 `_db_pool` 是可变全局）、ai_status_payload、database_url |
| `routers/main_extracted_edu_media.py` | `/api/sunday-school/videos`（GET/POST）、`/api/seekers-class/courses` | get_db、release_db、handle_exc |

- 模式与库内既有 `init_xxx_router`（如 routers/diagnosis.py）一致：模块级占位
  `_get_db = None` 等，`init_...()` 在 `app.include_router()` 之前由 main.py 注入。
- 效果：main.py 330,322 → 307,050 字节（7534 → 6997 行），@app 直接路由 48 → 36。
- `_ai_status_payload` 保留在 main.py（`/api/home-bootstrap` 也在用），以引用注入。

### 3. 健壮性与可观测性（前序完成，本轮复核通过）
- logging 基础配置（LOG_LEVEL 环境变量，默认 INFO；不覆盖既有 handler）。
- 可选 router import 失败：`_log_router_import_failure()` 统一记录，
  lifespan 启动时汇总告警；None 兜底语义不变（路由缺席但服务可启动）。
- 全局 `@app.exception_handler(Exception)`：分类返回 503/422/500 干净 JSON，
  不拦截 HTTPException（HTTPException 走独立的 5xx 日志 handler，4xx 原样透传）。

## 二、第二轮拆分（本轮，2026-07-12）：36 → 7 条 @app 路由

main.py 307,050 → 210,895 字节（6,997 → 4,820 行）。按既有 init 注入模式新增 7 个模块，
并把 `/api/health`、`/` 并入既有 main_extracted_health.py：

| 新模块 | 路由 | 注入依赖（要点） |
|---|---|---|
| `routers/main_extracted_user_state.py` | `/api/user/checkin`、`/api/prayers/{id}/restore`、`/api/user/tags` | get_db、release_db、get_session_user、is_admin、extract_tags、upsert_tags、get_user_tags（标签辅助仍在 main，/api/chat 后台抽取共用） |
| `routers/main_extracted_auth_email.py` | `/api/auth/me`、`/api/auth/logout`、`/api/auth/email/*`（send-code/register/login/send-reset-code/reset-password，共 7 条） | 会话签发/验证码/邮件/审计等 12 个函数 + `_CODE_STORE`/`_SESSION_STORE` 等可变全局按**同一对象**注入（与 main 内微信 OAuth 共享状态）；limiter 直接取自 core.ratelimit（装饰期需要，同一实例） |
| `routers/main_extracted_translate.py` | `/api/translate-batch`（含 `_translate_cached`） | get_db、release_db、call_chat、DATABASE_URL；limiter 同上 |
| `routers/main_extracted_behavior.py` | `/api/behavior/regulate`、`/history`、`/stats` | get_db、release_db、get_session_user |
| `routers/main_extracted_habits.py` | `/api/habits/*` ×8 + `/api/route`（连同模型类与 `_catmull_rom_chain`/`_sea_route` 整块搬） | get_db、release_db、get_session_user、settings（对象注入，避免 core.config 双实例） |
| `routers/main_extracted_devotion.py` | `/api/daily-devotion-personal`（含 `_devotion_cache`/`_DIM_THEMES`/`_GROWTH_STAGES`） | get_session_user、is_english |
| `routers/main_extracted_bible.py` | `/api/scripture`、`/api/bible/study`、`/api/bible/video`（含全部经文解析/CSV 索引辅助） | ROOT_DIR、GOOGLE_TTS_API_KEY、_handle_exc |
| `routers/main_extracted_health.py`（追加） | 新收 `/api/health`（综合体检）与 `/`（根路由） | 复用既有注入，无新增参数 |

验证（全部通过）：逐模块 py_compile + 独立导入核对（方法,路径）逐字一致；
`import main` 后 app 上 36 条原路由全部注册、无重复；基线逐行比对，除下述
“主动删除的死代码”外无内容丢失；`pytest -m no_db` 904 passed，仅存 2 个
**改动前即失败**的既有失败（routers.realtime 契约缺 `/api/rtc/ws-ticket`、
app 级契约在离线环境可选 router 缺席）。

### 本轮有意的非逐字改动（3 处，均已核实）
1. **main_extracted_behavior**：补 `import uuid`。原 main.py 模块级从未 import uuid，
   `behavior_regulate` 里 `uuid.uuid4()` 一直 NameError 被日志 try/except 吞掉、
   行为历史落库从未生效；补上后按原始意图工作（sfds_behavior_history 开始真正写入）。
2. **main_extracted_devotion**：`with get_db() as (conn, cur)` 中 `get_db` 在原 main.py
   即未定义（NameError 被 except 吞、formation 分数永远走默认值）。**逐字保留**未修复，
   模块 docstring 有注记；后续如要修复应改为注入 `_get_db`/`_release_db` 并改写取数段。
3. **删除死代码**：main.py 里残留的 `DevotionJournalSaveRequest`/`_row_to_journal`
   （journal 域早已拆到 routers/journal.py，二者无任何引用）。

## 三、main.py 剩余结构（4,820 行，7 条 @app 路由）与后续

| 保留项 | 原因 |
|---|---|
| 微信 OAuth/小程序 5 条（`/api/auth/wechat/login`、`/mobile`、`/callback`、`/miniprogram/login`、`/miniprogram/update-profile`） | OAuth 回调 + 会话签发 + WX secret 配置深耦合，安全敏感；建议单独一轮带完整回归再拆（拆法与 main_extracted_auth_email 相同：状态对象注入） |
| `/api/chat` | 流式 SSE + 标签画像 + 多 provider 闭包，依赖 `_SPIRITUAL_CHAT_SYSTEM`、`_extract_tags_from_chat_bg` 等；可拆但收益低、回归面大 |
| `/api/home-bootstrap` | 聚合十几个域（layout/ai_status/history），天然属于 main |
| 启动/基础设施（lifespan、DB 池、迁移、中间件、异常处理器、include_router 接线） | main 的本职，不外搬 |

后续（原阶段 4 清理项仍然有效）：
- `main_extracted_*` 改名为正式域名模块或并入既有同域 router；
- 把 40+ 个 try/except import 收敛成声明式 router 注册表；
- print → logging 渐进迁移（见下文第五节）。

## 四、attention 包后续建议（legacy 文件已删）

回归测试清单（上线前至少跑一遍）：
- [ ] `python3 -c "import routers.attention as a; assert len(a.router.routes) == 94"`（backend 目录）；
- [ ] `pytest backend/tests -k attention`（含 tests/test_route_contracts.py 中 attention 相关路径契约）；
- [ ] 启动冒烟：uvicorn 起服务后 `GET /health/ready`，再抽查
  `/api/attention/...` 下 covenant / focus / groups / reports 各一条读路由；
- [ ] 确认部署产物（Dockerfile COPY / HF Space 同步）按目录收包，不会遗漏
  `routers/attention/` 子文件；
- [ ] 若有外部脚本 `from routers.attention import <私有名>`，`__init__.py` 已重导出
  全部符号，但重名符号以先导入的模块为准（`setdefault`），新增同名符号时留意。

后续可选优化：`__init__.py` 的通配重导出改为显式 `__all__`；把 `_models` 中的
Pydantic 模型按域下沉到各子模块。

## 五、print → logging 迁移建议

现状：main.py 仍有约 500 处 `print(..., flush=True)`；logging 基础设施已就位
（basicConfig + LOG_LEVEL），全局异常与 5xx 已双写 print + logging。

建议渐进迁移，不搞一次性替换：
1. **约定**：新代码一律 `logging.getLogger(<域名>)`；`[startup]`/`[db]`/`[ERROR]`
   等前缀映射为 logger 名（startup、db、app…），级别按语义（WARNING/ERROR 优先迁移）。
2. **第一批**：lifespan 启动序列与迁移日志（`[startup]`、`[db]`、`[sfds]`），
   这些最需要级别过滤与时间戳。
3. **第二批**：异常路径的 `print(f'[ERROR] ...')` 全部并入 logger.error(exc_info=...)，
   移除 print 双写。
4. **第三批**：各路由内的调试 print（如 `[sermon]`、`[behavior_regulate]`）降为
   logger.debug/info；拆分搬移时顺手完成（extracted 模块可各自 `logger = logging.getLogger(__name__)`）。
5. 部署侧确认日志采集读 stdout 即可（basicConfig 默认 stderr，如平台只采 stdout
   需加 `stream=sys.stdout`）。

## 六、遗留风险与注意事项

- `.git/index.lock` 存在，本轮未做任何 git 写操作；解锁后需一次性提交：
  attention.py 删除、attention/ 包、3 个 main_extracted_* 模块、main.py、
  docs/REFACTOR_PLAN.md，并 `git rm requirements.txt`（根目录废弃文件，头部已标注）。
- 离线环境无法完整 `import main`（依赖 torch/sentence-transformers 等重依赖），
  首次部署后务必看 lifespan 汇总告警 “optional router(s) failed to import”。
- `main_extracted_health` 的 `/api/health/db` 读取连接池私有计数（`_pool`/`_used`），
  psycopg2 升级时留意。
- `main_extracted_edu_media` 里 `_list_videos_via_r2_api`/`_parse_html_xml_listing`
  按原样搬移，但当前 sunday-school 路由走 DB，两个函数疑似死代码，可在下轮确认后删除。
- 第二轮拆分：`main_extracted_auth_email` 与 main 通过**共享同一** `_CODE_STORE`/
  `_SESSION_STORE`/锁对象工作；若日后把这些全局改成重新赋值（而非原地修改），
  两边会失联，须改成 getter 注入。
- `main_extracted_behavior` 补 `import uuid` 后 sfds_behavior_history 开始真正落库，
  上线后留意该表写入量与约束（此前一直没写进去过）。
- 既有失败（与本轮无关，待修）：tests/test_route_contracts.py 中 routers.realtime
  契约缺 `('POST','/api/rtc/ws-ticket')`。

## 七、FCM 设备推送（本轮新增，移动端服务端推送）

- 迁移 `backend/migrations/0209_fcm_device_tokens.sql`：表 `fcm_device_tokens`
  （id/user_email/token UNIQUE/platform android|ios/created_at/last_seen_at/revoked_at）。
- `backend/fcm_sender.py`：FCM HTTP v1 发送器。PyJWT(RS256)+httpx 自签 OAuth2 JWT 换
  access token（进程内缓存，到期前 60s 重签）；环境变量 **`FCM_SERVICE_ACCOUNT_JSON`**
  = 服务账号 JSON 的文件路径或 JSON 字符串；未配置时全部函数安全 no-op（debug 日志）。
  `send_to_user(email,title,body,data,*,get_db,release_db)` 群发该用户全部有效 token，
  404/UNREGISTERED 自动标记 revoked_at。未新增任何第三方依赖。
- `routers/push.py` 新增：`POST /api/push/fcm/register`（登录用户 upsert，重复 token
  改挂当前用户并解除 revoked）、`POST /api/push/fcm/unregister`、`GET /api/push/fcm/status`；
  `/test` 与 `/run-due` 在 web push 发送处并联调用 fcm_sender（try/except 隔离；run-due
  按 (email, 晨/晚档) 去重，且在释放 DB 连接后才发，避免嵌套占用连接池）。
- 测试：`backend/tests/test_push_fcm.py`（no_db，TestClient 单挂 push router + 假 DB 注入）7 例。
- 遗留：仅安装移动端、从未订阅 web push 的用户不会收到 run-due 晨/晚提醒（FCM 目前
  跟随 push_subscriptions 的到点判定）；如需独立调度，需给 fcm_device_tokens 加
  last_*_sent 列与偏好，另开迁移。
