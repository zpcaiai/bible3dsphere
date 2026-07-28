# EMD-OS Batch 8 Report — Twin、身份、祷告、习惯、牧养与群体整合（EM-62 ~ EM-70）

Date: 2026-07-28
Scope: 把情感成熟证据接回 Formation Twin，并与身份系统、祷告系统、习惯系统、牧养与教会群体打通。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_integration.py                   引擎（EM-62 ~ EM-70）
backend/migrations/0230_formation_twin_emd_integration.sql                 9 张表 + 索引 + Owner RLS
backend/migrations/rollback/0230_..._down.sql                              手动回滚
backend/routers/formation_twin_emotional_maturity.py                       新增 10 个端点
backend/tests/test_formation_twin_emotional_maturity_integration.py        40 个测试
```

## 2. 九项不可突破的整合原则

1. **证据类型不得混写**：可观察行为 / 用户解释 / 系统假设 / 经审核神学命题 / 牧者判断 / 用户确认整合。
2. **只有用户确认过的可写类型才进入长期 Twin**；其余全部 `held_back` 并注明原因。
3. **用户拥有最终纠正权**：撤回会触发重算、撤销派生分享、停止提醒，并保留版本记录（不静默保留）。
4. **属灵内容只能来自可版本化神学包**：`神现在对你说 / 神给你的命定 / 神允许这次失败是为了` 一律拦截；
   数据库层 `CHECK(free_generation_allowed = FALSE)`。
5. **牧者与小组长默认零权限**：日记、祷告正文、家庭历史、依恋材料、童年材料、未发送草稿、危机记录
   全部列入 `NEVER_SHAREABLE_FIELDS`，出现即 `UnsafeContentError`。
6. **群体反馈不能高于用户证据**：单条权重上限 0.3，高权力来源再减半，数据库层 `CHECK(weight <= 0.3)`。
7. **小组不得治疗化、不得监控化**：强制披露与组长查看记录直接 `REJECTED`，数据库层双 CHECK 兜底。
8. **一切分享都是字段级、可预览、可删改、有期限、可撤回**：`SHARED` 状态必须同时具备到期时间与用户批准。
9. **情感成熟度永不用于服事资格、按立、纪律或属灵排名**；含此类措辞的群体反馈以 `ELIGIBILITY_MISUSE` 排除。

## 3. 各 Skill 要点

- **EM-64 祷告路由**：情绪 → 哀歌／认罪／祈求／交托／感恩／省察／静默／代祷；危机状态下先走安全流程，
  祷告只能作为附加支持；中性框架下改为非宗教替代方案。
- **EM-65 生活规则编译**：每日 ≤3、每周 ≤3、关系 ≤2（低容量减半），每个习惯必须有「两分钟最小版本」，
  并显式声明「漏掉一天不算失败」「不用打卡数量代表成长」。
- **EM-66 跨系统编排**：情感／身份／祷告／习惯／群体／复测六条轨道，同时最多 3 条，
  避免各系统各自派任务；安全状态优先。
- **EM-68 转介协调**：当伤害与教会权力相关时，**不把用户转介回同一权力结构**；系统从不代为联系。

## 4. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/integration/overview
POST /api/v1/formation-twin/emotional-maturity/integration/twin-bridge
POST /api/v1/formation-twin/emotional-maturity/integration/identity
POST /api/v1/formation-twin/emotional-maturity/integration/prayer
POST /api/v1/formation-twin/emotional-maturity/integration/rule-of-life
POST /api/v1/formation-twin/emotional-maturity/integration/plan
POST /api/v1/formation-twin/emotional-maturity/integration/pastoral-summary
POST /api/v1/formation-twin/emotional-maturity/integration/handoff
POST /api/v1/formation-twin/emotional-maturity/integration/group-practice
POST /api/v1/formation-twin/emotional-maturity/integration/community-feedback
```

## 5. 测试结果

```text
tests/test_formation_twin_emotional_maturity_integration.py    40 passed
```
