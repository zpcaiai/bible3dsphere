# 安全与健壮性方案 / Security & Robustness Plan

目标：在面对任意用户的恶意访问与输入时，保证网站可用性、正常运行不受干扰，并保护用户数据。
范围：后端 FastAPI（`backend/`，部署 HF Spaces）+ 前端（`bible3dsphere-frontend`，Vercel）+ Neon Postgres。

本文件既是**方案**也是**实施记录**。已实施项标 ✅，待办项标 ☐。

---

## 0. 现状评估（审计结论）

经一次完整后端审计，以下高风险面**已经做得很好，无需返工**：

- **SQL 注入** — 全部查询参数化（`cur.execute(sql, params)`）；动态 SQL 仅拼接白名单表名/常量列名，无用户数据进入 SQL 串。
- **越权 / IDOR** — 状态变更端点统一「取行 → 比对会话 email → 否则 403」；导出/读取端点统一 `WHERE email=%s` 按会话作用域；管理读取经 `require_admin` 把关。
- **口令哈希** — bcrypt cost 12，SHA 回退用 `hmac.compare_digest`，无明文。
- **会话** — 不可猜的 256-bit 随机 token（非 JWT，无算法混淆风险），DB 落库 + 30 天过期清理。
- **安全响应头** — 已设 CSP / X-Frame-Options(DENY) / nosniff / Referrer-Policy / HSTS(HTTPS)。
- **无硬编码密钥默认值** — 配置全部来自环境变量，空串兜底。

真正的暴露面集中在**成本/DoS（付费外部 API 端点不限流）**与若干具体缺陷。下列为本轮实施。

---

## 1. 已实施（本轮 · 不破坏现网）

### 1.1 全局限流：按真实客户端 IP + 全站默认上限 ✅
- 新增 `backend/core/ratelimit.py`：共享 `limiter`，`key_func` 改为 **`X-Forwarded-For`（左起首个真实客户端 IP）** → `X-Real-IP` → socket 兜底。
  - **为什么重要**：uvicorn 未带 `--proxy-headers`，原 `get_remote_address` 取到的是反向代理 IP（所有用户相同）。若按它限流，会把全站用户一起限掉。改后限流**真正按用户**生效。
- `Limiter(default_limits=["600/minute"])` + `app.add_middleware(SlowAPIMiddleware)`：**所有路由**（含未单独装饰的端点）默认每 IP 600/min 上限，挡住自动化刷量/洪水，正常浏览（含自动翻译微批）远低于此。

### 1.2 付费 / 昂贵端点单独收紧 + 入参限长 ✅
| 端点 | 限制 | 备注 |
|---|---|---|
| `POST /api/tts`（ElevenLabs 计费） | 30/min | + `request` 参数 |
| `POST /api/translate`（LLM） | 60/min | |
| `POST /api/punctuation`（LLM） | 30/min | |
| `POST /api/translate-batch` | 60/min | 每条文本截断 ≤2000 字、列表 ≤100 |
| `POST /api/bible-map/ai`（OpenAI） | 20/min | `name` 截断 ≤200 |
| `POST /api/film/start`、`/start-ppt`（Kling 文生视频） | 5/min | 见 1.3 |

### 1.3 影片工作室加固 ✅
- **不再接受客户端传入的 `anthropic_key`/`gemini_key`**（防把任意第三方 key 注入服务端调用）；一律用服务端环境变量。
- `story_text`/`story` 限长 ≤20000，`num_scenes` 限 1–60。
- `start-ppt` 上传受全局 25MB 请求体上限保护（见 1.5）。

### 1.4 路径穿越修复 ✅
- `GET /api/film/download/{fname}`、`GET /film-clips/{fname}`：拒绝含 `/`、`\`、`..`、以 `.` 开头的文件名，避免读取目录外文件；错误改为干净的 404。

### 1.5 其它 ✅
- **请求体硬上限 25MB**（`limit_body_size` 中间件，按 `Content-Length`）：防超大 payload 撑内存。
- **CORS**：通配 `*` 分支 `allow_credentials=False`（`*` 与凭证并用本就违规；本站用 Bearer Token 无需 cookie 凭证）。
- **定时任务密钥**：`/api/push/run-due` 改 `hmac.compare_digest` 常量时间比较，消除时序侧信道。
- **SMTP 调试日志**：移除 `set_debuglevel(1)`（曾把含 AUTH 的会话打到 HF 日志）。

---

## 2. ⚠️ 上线必做的运维配置（不改代码也要做）

1. **设置 `ALLOWED_ORIGINS` 环境变量**为你的正式域名（如 `https://你的域名,https://*.vercel.app`）。
   当前默认 `*`，生产应锁定具体域名——这是**最重要的一步**。
2. 确认已设：`PUSH_CRON_SECRET`、`DATABASE_URL`、各 `*_API_KEY`、`SMTP_*`、`WX_APP_SECRET`、`R2_*`。
3. 定期**轮换**外部 API Key 与 SMTP 口令；HF Space secrets 不入 git。

---

## 3. ☐ 建议的后续加固（本轮未做，按优先级）

- ☐ **影片端点鉴权**：`/api/film/*` 不被公开前端调用，建议加管理员鉴权（仅限流仍可能被滥用）。
- ☐ **异常信息泄露**：约 50 处 `raise HTTPException(500, detail=str(exc))` 可能回吐 DB/内部路径，应服务端记日志、对外返回通用文案。
- ☐ **管理员判断去硬编码**：`_is_admin` 内 `email == 'zpclord@sina.com'` 改为读 `ADMIN_EMAILS` 环境变量 / DB 角色。
- ☐ **多实例限流**：若将来横向扩展，`slowapi` 内存存储需换 **Redis**（`storage_uri`），否则各进程各算。
- ☐ **边缘防护**：前置 Cloudflare/WAF（Bot 拦截、L7 DDoS、全局速率），比应用层限流更抗洪。
- ☐ **依赖扫描**：CI 接 `pip-audit` / `npm audit` / Dependabot，定期升级。
- ☐ **登录暴力破解**：现有 20/min 登录限流之外，可加账号级失败计数 + 渐进锁定。
- ☐ **前端**：审查任何 `dangerouslySetInnerHTML`；确保所有用户生成内容渲染走 React 默认转义；CSP 进一步收紧 `script-src`（去 `unsafe-inline`/`unsafe-eval`，如可行）。

---

## 4. 部署前验证清单

- [ ] `python -m py_compile` 全过（本轮已过）。
- [ ] 本地起服务，冒烟测试：匿名翻译/TTS 正常；同一 IP 超限返回 429；影片下载非法文件名返回 404。
- [ ] 确认 `ALLOWED_ORIGINS` 已在 HF Space 配置为正式域名。
- [ ] 观察 HF 日志无 SMTP AUTH 明文、无异常 500 栈泄露。
