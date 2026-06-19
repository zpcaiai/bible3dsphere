# 危机守护 · 协作后台隐私 / 合规评审

针对「牧者/咨询师协作」（当事人把危机信息有限地分享给牧者/咨询师）的一次隐私与合规评审。
结论：**冒名查看风险已被现有身份模型挡住**，并已加多道防御与透明审计。下面是威胁模型、已落地的控制、以及需要你们人工完成的事项。

---

## 1. 威胁模型：会不会被人冒名查看？

最关心的问题：**有没有办法在不控制某邮箱的情况下，拿到一个「登录邮箱 = 该邮箱」的会话，从而查看分享给那个人的危机信息？**

逐条核查（`backend/main.py` 鉴权流程）：

| 路径 | 是否能拿到任意邮箱的会话 | 依据 |
| --- | --- | --- |
| 邮箱注册 `/api/auth/email/register` | **否** | 强制邮箱验证码（`hmac.compare_digest`，码发到该邮箱），且 `users.email` `UNIQUE` |
| 邮箱登录 `/api/auth/email/login` | 否 | 需密码；账号本就由上面验证过的邮箱创建 |
| 密码重置 `/api/auth/email/reset-password` | 否 | 需重置码（发到邮箱）；且只改密码，不改邮箱 |
| 改资料 `/api/user/profile` | 否 | 只更新 `nickname/avatar`，**不可改 email** |
| 微信登录 `/api/auth/wechat/callback` | 否 | 微信账号 `email = NULL`（按 openid 建号），**拿不到 email**，根本匹配不上任何分享 |
| 改 / 绑定邮箱 | 不存在该端点 | 全仓库无「未验证即改邮箱」的路径 |

**结论**：要持有「登录邮箱 = X」的会话，必须用 X 注册并完成 X 收到的邮箱验证码 —— 即必须控制 X 这个邮箱。`email` 唯一且注册后不可变。**不存在冒名查看的通道。**

---

## 2. 已落地的控制（代码层）

1. **身份匹配按服务端会话**：协作所有端点用 `_require_email(request)` / `_require_verified_caregiver(request)` 从**服务端会话**取邮箱，从不信任前端传入的身份。
2. **防御纵深 · 仅验证过的邮箱账号可当牧者**：`_require_verified_caregiver()` 额外要求账号 `login_type == 'email'`（邮箱注册=已验证）。微信账号（无 email）被双重挡住。已加单元测试。
3. **明确授权 + 可撤销**：分享由当事人发起（`POST /shares`），可随时 `DELETE /shares/{id}` 撤销。
4. **最小必要（scope）**：当事人勾选 `status / safety_plan / events`，牧者只能看到勾选范围。
5. **角色收紧**：`CRISIS_CAREGIVER_ROLES` 环境变量（默认 `pastor,counselor,small_group_leader`）约束可授权角色。
6. **透明审计**：每次牧者查看写入 `crisis_share_views`；当事人能看到「已被查看 N 次（最近 …）」并可展开**逐条查看记录**（`GET /shares/{id}/views`）。
7. **未注册提示**：授权时检测对方邮箱是否已注册，未注册标「未注册」并提示对方需先用该邮箱注册登录。
8. **不带控告**：只读摘要文案强调「陪伴而非审判」。

---

## 3. 数据留存与合规

- `crisis_events.triggering_message` 默认**不存原文**（仅 red 事件保留以便人工跟进），可删除（`DELETE /events/{id}`）。
- 危机记录、安全计划、守护人均按 `user_id`（邮箱）隔离，用户可自行删除。
- 守护人短信通知必须 `consent_enabled`，且发送意图/状态写入 `crisis_events.escalation_actions` 审计。

---

## 4. 需要你们人工完成（我无法代办）

1. **填写凭据（密钥不应由 AI 代填）**：在 `.env` 配置
   - 短信：`TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER`，或自建网关 `CRISIS_NOTIFY_WEBHOOK_URL`；
   - 角色收紧（可选）：`CRISIS_CAREGIVER_ROLES`。
   占位符已在 `.env.example`。未配置时系统优雅降级（只记录意图、提示改用热线），不影响功能。
2. **正式合规评审签字**：本文件是工程视角的自评，建议法务/隐私负责人据此走一次正式评审与记录。
3. **可选增强**：
   - 对当事人邮箱在牧者侧做脱敏展示（如 `a***@x.com`）。
   - 给协作分享设置有效期 / 到期自动失效。
   - 把「查看记录」也通过站内信通知当事人（当前为当事人主动查看）。

---

## 5. 验证

- 后端 `pytest tests/test_crisis_engine.py`：**42 passed**（含 `_require_verified_caregiver` 网关：邮箱账号通过、微信→403、无邮箱→401）。
- 前端 `vitest src/features/crisis-care`：**18 passed**。
- `/api/crisis` 共 25 个端点；`GET /shares/{id}/views` 仅分享者本人可读。

---

## 6. 后续增强（已落地）

- **当事人邮箱脱敏**：牧者侧（`caregiver/shares` 列表与只读摘要）显示的当事人邮箱在**后端**即脱敏为 `a***@x.com`，
  原文不进入牧者的网络响应（`_mask_email`）。当事人侧仍看自己选的牧者全邮箱。
- **分享到期失效**：`crisis_care_shares.expires_at`；授权时可选「长期 / 30 天 / 90 天」（`expiresInDays`）。
  牧者侧查询自动过滤 `expires_at <= NOW()` 的分享（看不到、也读不到摘要）；当事人侧显示「到期/已过期」。
- 验证：后端 **43 passed**（含 `_mask_email` / `_share_expiry`），前端 **18 passed**，`vite build` clean。
