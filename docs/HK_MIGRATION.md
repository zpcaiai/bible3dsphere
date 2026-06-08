# 后端 + 数据库迁移到香港 —— 操作手册

> 目标：把后端从 Hugging Face Space（欧美）迁到香港节点，并让数据库与后端就近，
> 把国内访问的单请求延迟从 ~1.3s 降到 ~150–250ms。香港区**无需 ICP 备案**。

## 0. 现状盘点（迁移前必读）

- 部署形态：单 `Dockerfile`，`uvicorn main:app --port 7860`，HF Space（docker sdk）。
- 数据库：通过**单个环境变量 `DATABASE_URL`** 连接（psycopg2 连接池）；当前是 Neon（美区）。
- 启动自动跑迁移：`run_migrations(DATABASE_URL)`，共 47 个 `backend/migrations/*.sql`。
- 大向量文件（`bible_bilingual_metadata.pkl` 19MB、两个 `*.npy` 各 122MB）**运行时从
  `cdn.holiness.uk/npy`（R2）自动下载**，不在镜像里 → 迁移时只需给持久卷缓存，省心。
- 重依赖：`torch` + `sentence-transformers`（CPU 推理）→ 镜像大、内存需 ≥2GB（建议 4GB）。
- 部署链：push 到 GitHub `zpcaiai/bible3dsphere` → `hf_sync.yml` 同步到 HF。迁移后这条保留做备份/回滚。

---

## 1. 选型

### 推荐：香港 VPS + docker-compose（后端 + 自建 Postgres 同机）

一台香港云主机上用 docker-compose 同时跑 FastAPI 和 Postgres，数据库与后端走 localhost
（后端↔DB <1ms），只有「用户→后端」一跳跨境到香港（~100ms）。延迟最低、成本最省、可控性最强。

- 选品：腾讯云轻量应用服务器（香港）/ 阿里云香港 ECS / Vultr 东京·首尔·香港 等。
- 配置：**2 vCPU / 4GB RAM / 60GB SSD** 起步（torch + 模型 + PG 同机，4GB 才稳）。
- 成本：约 ¥40–80/月。
- 注意：香港主机到大陆带宽有波动，高峰可能抖动；如需更稳可叠加 CDN（见 §6）。

### 备选 A：Fly.io（`hkg` 区）+ Neon（Singapore `ap-southeast-1`）

全托管、免运维。后端在香港，DB 在新加坡（Neon 无香港区），后端↔DB ~35ms（可接受）。
适合不想自己管服务器的情况。Fly 小机 `shared-cpu-1x` 内存给到 2GB（torch 偏紧，建议 1x@2GB 或 2GB+）。

### 备选 B：保留 HF + 香港反代缓存（过渡）

香港放一台 nginx/Cloudflare Worker，缓存 GET、回源 HF。改动最小，但动态接口首字节仍受 HF 影响，
只算过渡方案，不根治。

> 下文以**推荐方案（香港 VPS + 同机 PG）**为主线给步骤；备选 A 的差异在每步标注。

---

## 2. 数据库迁移：Neon → 香港 Postgres

### 2.1 从 Neon 导出
在任意能连 Neon 的机器（你的 Mac 即可，已装 `postgresql` 客户端）：

```bash
# Neon 连接串（在 Neon 控制台复制，形如 postgres://user:pass@ep-xxx.neon.tech/dbname?sslmode=require）
export NEON_URL='postgres://...neon.tech/...?sslmode=require'

# 完整逻辑备份（含数据 + 结构 + 序列），排除 owner/权限避免目标库报错
pg_dump "$NEON_URL" \
  --no-owner --no-privileges \
  --format=custom \
  --file=neon_backup.dump

# 看一眼大小确认成功
ls -lh neon_backup.dump
```

### 2.2 在香港主机起 Postgres（同机方案）
见 §3 的 docker-compose，会带起一个 `postgres:16` 容器并挂持久卷。起来后导入：

```bash
# 把备份拷到香港主机
scp neon_backup.dump root@<HK_HOST>:/root/

# 在香港主机上，恢复进 compose 里的 postgres 容器
docker compose exec -T postgres pg_restore \
  --no-owner --no-privileges --clean --if-exists \
  -U bible -d biblesphere < /root/neon_backup.dump
```

- 应用启动时还会自动跑 `run_migrations`，对已存在的表是幂等的（迁移脚本应带 `IF NOT EXISTS`）；
  如某条迁移非幂等报错，可先 `--clean` 恢复后再让应用补齐增量。
- **备选 A（Neon Singapore）**：不用 pg_dump，直接在 Neon 控制台新建 `ap-southeast-1` 项目，
  用 `pg_dump | pg_restore` 把美区数据导到新加坡项目，再把新连接串作为 `DATABASE_URL`。

### 2.3 校验
```bash
docker compose exec postgres psql -U bible -d biblesphere -c "\dt" | head
docker compose exec postgres psql -U bible -d biblesphere -c "SELECT count(*) FROM users;"
```

---

## 3. Dockerfile / docker-compose 调整

现有 `Dockerfile` 基本不用改（它已是标准 uvicorn:7860）。新增一个 `docker-compose.yml`
在仓库根目录，把 API + Postgres + 持久卷编排起来：

```yaml
# docker-compose.yml（仓库根目录，新增）
services:
  postgres:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_USER: bible
      POSTGRES_PASSWORD: ${PG_PASSWORD}      # 在 .env 里设强密码
      POSTGRES_DB: biblesphere
    volumes:
      - pgdata:/var/lib/postgresql/data
    # 不对外暴露端口，仅容器内网访问（更安全）

  api:
    build: .
    restart: always
    depends_on: [postgres]
    environment:
      # 同机走 service 名 postgres，端口 5432
      DATABASE_URL: postgres://bible:${PG_PASSWORD}@postgres:5432/biblesphere
      ALLOWED_ORIGINS: https://holiness.uk,https://www.holiness.uk
      VECTOR_DATA_BASE_URL: https://cdn.holiness.uk/npy
      # —— 把 HF Space 里配的密钥全部搬过来（见 §4）——
      HF_TOKEN: ${HF_TOKEN}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      SILICONFLOW_API_KEY: ${SILICONFLOW_API_KEY}
      GOOGLE_TTS_API_KEY: ${GOOGLE_TTS_API_KEY}
      WX_APP_ID: ${WX_APP_ID}
      WX_APP_SECRET: ${WX_APP_SECRET}
      WX_REDIRECT_URI: https://api.holiness.uk/api/auth/wechat/callback
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASS: ${SMTP_PASS}
      RESEND_API_KEY: ${RESEND_API_KEY}
      VAPID_PUBLIC_KEY: ${VAPID_PUBLIC_KEY}
      VAPID_PRIVATE_KEY: ${VAPID_PRIVATE_KEY}
      VAPID_SUBJECT: ${VAPID_SUBJECT}
      PUSH_CRON_SECRET: ${PUSH_CRON_SECRET}
    volumes:
      # 缓存运行时下载的 270MB 向量/pkl，避免每次重启重下
      - vectordata:/app/backend
    ports:
      - "127.0.0.1:7860:7860"     # 只绑本地，由前置 nginx/caddy 转发 TLS

volumes:
  pgdata:
  vectordata:
```

> 持久卷 `vectordata` 挂到 `/app/backend` 是为了缓存 `*.npy/*.pkl`（它们与 main.py 同目录下载）。
> 若担心覆盖代码文件，可改为把向量文件目录单独配置（用 `VECTOR_DATA_DIR` 若支持，或挂子目录）。
> 起容器后首次启动会从 R2 下 270MB，约 1–2 分钟，之后命中缓存秒起。

TLS / 反代（同机加一个 caddy 自动签证书，最省事）：

```bash
# /etc/caddy/Caddyfile
api.holiness.uk {
    reverse_proxy 127.0.0.1:7860
}
```

启动：

```bash
cd /root/bible3dsphere
cp .env.example .env && vim .env     # 填 PG_PASSWORD 和所有密钥
docker compose up -d --build
docker compose logs -f api           # 看到 uvicorn running + 向量下载完成
```

**备选 A（Fly.io）**：不用 compose。`fly launch --region hkg`，`fly secrets set DATABASE_URL=... GEMINI_API_KEY=...`，
挂一个 `fly volumes create vectordata --region hkg --size 1` 给向量缓存。Dockerfile 直接复用。

---

## 4. 环境变量清单（从 HF Space 搬到新主机）

从代码 `backend/core/config.py` 提取，逐项在 HF Space Settings → Variables/Secrets 里复制过来：

| 变量 | 用途 | 必需 |
|---|---|---|
| `DATABASE_URL` | 数据库连接（新值指向香港 PG） | ✅ |
| `ALLOWED_ORIGINS` | CORS，填 `https://holiness.uk,https://www.holiness.uk` | ✅ |
| `HF_TOKEN` | 访问统计/数据回写 HF | 视功能 |
| `GEMINI_API_KEY` / `DEEPSEEK_API_KEY` / `SILICONFLOW_API_KEY` | AI 模型 | ✅(至少一个) |
| `GOOGLE_TTS_API_KEY` | 语音合成 | 视功能 |
| `WX_APP_ID` / `WX_APP_SECRET` / `WX_REDIRECT_URI` | 微信登录（回调域名改成新域名） | 视功能 |
| `SMTP_*` / `RESEND_API_KEY` / `SENDGRID_API_KEY` | 邮件 | 视功能 |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | Web Push | 视功能 |
| `PUSH_CRON_SECRET` | 推送 cron 鉴权 | 视功能 |
| `VECTOR_DATA_BASE_URL` | 向量下载源（默认 R2，无需改） | 默认即可 |

> ⚠️ 微信回调 `WX_REDIRECT_URI` 改成新后端域名后，要去微信开放平台同步更新授权回调域。

---

## 5. 前端 API_BASE 切换

前端 `bible3dsphere-frontend/src/api.js` 的 `resolveDefaultApiBase()` 里写死了
`holiness.uk → https://stephenzao-biblesphere.hf.space/api`。两种切法（任选）：

**方式一（推荐，零改码）**：在 Vercel 项目 Environment Variables 加
`VITE_API_BASE = https://api.holiness.uk/api`，重新部署即可（代码已优先读 `VITE_API_BASE`）。

**方式二（改码）**：把该行改成新域名：
```js
if (hostname === 'holiness.uk' || hostname === 'www.holiness.uk') return 'https://api.holiness.uk/api'
```

DNS：在你的域名服务商把 `api.holiness.uk` A 记录指向香港主机 IP（备选 A 则 CNAME 到 Fly 域名）。

---

## 6. 切换流程与回滚

1. 香港主机按 §2–§3 起好，`curl https://api.holiness.uk/api/ai-status` 返回 200。
2. 数据校验（§2.3）行数与 Neon 一致。
3. 前端切 `VITE_API_BASE` 到新域名，Vercel 部署，灰度观察。
4. 用浏览器实测：DevTools Network 里各 `/api/*` 的 TTFB 应从 ~1.3s 降到 ~0.2s 级。
5. **回滚**：把 `VITE_API_BASE` 改回 HF 域名重新部署即可（HF Space 与 GitHub 同步保留着，随时兜底）。
6. 稳定运行 1–2 周后，再考虑停用 HF Space（或保留作灾备）。

### 数据一致性提醒
切换瞬间若有用户在写库，Neon 与香港 PG 会有极小时间窗的数据差。建议：
- 选低峰时段切；或切换前对 Neon 设只读、做最后一次增量 `pg_dump` 再导入香港，再切前端。

---

## 7.（可选）进一步压低延迟

- 香港主机前面套 Cloudflare（橙云），对 §Cache-Control 标了 `public` 的接口（layout/ai-status）做边缘缓存。
- 若将来要 <50ms 且接受备案：迁国内云（阿里/腾讯大陆区）+ 域名 ICP 备案。
- 后端↔Neon 若走备选 A，确认 Fly `hkg` 与 Neon `ap-southeast-1` 实测 RTT，必要时把热点查询加缓存。
