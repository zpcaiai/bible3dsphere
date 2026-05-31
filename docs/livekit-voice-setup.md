# 多人群语音通话配置 (LiveKit SFU · Zoom 级音质)

「语音通话」tab：登录用户可以**建群**、把**邀请码**发给弟兄姊妹，多人加入后进行**实时群语音**。
媒体层用 [LiveKit](https://livekit.io) 托管 SFU——和 Zoom 同类的服务端转发架构：

- **Opus 编码 + RED 冗余**：丢包下仍清晰，不卡顿
- **服务端回声消除 / 降噪 / 自动增益**：浏览器原生 AEC/NS/AGC + 可选 Krisp AI 降噪
- **自带 TURN**：严格 NAT / 4G 下也能连通，无需自建 coturn
- **可扩到多人**：5-10 人甚至更多，音频不经过本服务（零媒体成本）

后端只做两件事：群成员管理 + 签发进房 JWT（`backend/routers/voice.py`）。

---

## 1. 注册 LiveKit Cloud（免费）

1. 打开 https://cloud.livekit.io ，注册并新建一个 Project。
2. 进入 **Settings → Keys**，点 **Create Key**，得到三项：
   - **Project URL**，形如 `wss://your-project-xxxx.livekit.cloud`
   - **API Key**
   - **API Secret**

免费额度对小群（5-10 人）完全够用。

## 2. 配置环境变量

在后端（HF Space → Settings → Secrets，本地则写 `.env`）设置：

```
LIVEKIT_URL=wss://your-project-xxxx.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxx
LIVEKIT_TOKEN_TTL=21600        # 进房令牌有效期(秒)，可选
```

> 未配置时，`/api/voice/config` 返回 `enabled=false`，前端会显示配置引导，**不影响其它功能**。

## 3. 部署

- 后端随正常部署生效（迁移 `0020_voice_groups.sql` 在推送到 GitHub main 时由 CI 应用到 Neon）。
- 前端新增依赖 `livekit-client` 和（可选）`@livekit/krisp-noise-filter`，Vercel / HF 构建时自动 `npm install`。

## 4. 使用

1. 首页快捷入口 → **🎙 语音通话**。
2. 输入群名 → **建群**，得到 6 位邀请码。
3. 把邀请码发给弟兄姊妹，他们在同一页 **加入** 输入邀请码即可入群。
4. 点群上的 **📞 进入** 开始通话。控制条：静音 / AI 降噪 / 挂断。说话时头像会发光。

---

## 接口一览（`/api/voice/*`，均需登录 Bearer token）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/voice/config` | 探测语音是否已配置 |
| GET | `/voice/groups` | 我所在的群列表 |
| POST | `/voice/groups` | 建群 `{name, max_members?}` |
| POST | `/voice/groups/join` | 凭邀请码加入 `{join_code}` |
| GET | `/voice/groups/{gid}/members` | 群成员名单 |
| POST | `/voice/groups/{gid}/token` | 签发 LiveKit 进房 JWT |
| POST | `/voice/groups/{gid}/leave` | 退群（群主退群=解散） |
| DELETE | `/voice/groups/{gid}` | 解散群（仅群主） |

## 进阶

- **Krisp AI 降噪**：通话内点「AI降噪」即按需启用（LiveKit Cloud 项目支持；不支持时静默回退到浏览器原生降噪）。
- **自托管 LiveKit**：把 `LIVEKIT_URL` 指向自建 `livekit-server` 即可，令牌签发逻辑不变。
- **录音 / 转写**：可后续接 LiveKit Egress / Agents，无需改动现有建群逻辑。
