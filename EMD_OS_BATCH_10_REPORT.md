# EMD-OS Batch 10 Report — 生产认证与事故治理（EM-78 ~ EM-87）

Date: 2026-07-28
Scope: 情感成熟诊断域的最终生产保障层。**融入既有 `backend/production_governance` 包**，
不另起系统：场景模拟（`scenarios.py`）、评测注册表（`evaluation.py`）与发布闸门（`release.py`）
继续沿用，本批次补上 EMD 域特有的用途分级、心理测量治理、公平性、领域安全、隐私、红队、
变更控制、发布认证与事故召回。

## 1. 交付物

```text
backend/production_governance/emd_certification.py                        引擎（EM-78 ~ EM-87）
backend/migrations/0232_production_governance_emd_certification.sql       5 张治理表 + 索引
backend/migrations/rollback/0232_..._down.sql                             手动回滚
backend/routers/production_governance.py                                  新增 10 个 /api/v1/assurance/emd 端点（仅管理员）
backend/tests/test_production_governance_emd_certification.py             48 个测试
```

## 2. 用途分级与永久禁止

IU-0 内容教育 / IU-1 私人反思 / IU-2 个体化训练 / IU-3 真人牧养支持 / IU-4 教会群体实践 /
**IU-X 永久禁止**。IU-X 包含临床诊断、替代危机服务、得救与圣灵同在判断、按立与纪律决定、
雇佣保险信贷决定、公开排名、未经同意分享、被动监听、单次测评定人格、自动外部动作。
`IU-X 不能通过增加免责声明获得认证`，且数据库层 `CHECK(intended_use_tier <> 'IU_X_FORBIDDEN' OR decision = 'NO_GO')`。

## 3. 十道发布闸门

G0 用途 / G1 心理测量 / G2 数据质量 / G3 公平性 / G4 领域安全 / G5 隐私 / G6 LLM 安全 /
G7 工程 / G8 人类运营 / G9 独立签署。其中 **G0、G2、G4、G5、G6、G7、G9 为阻断闸门**，
任一失败即 NO-GO，`average_cannot_cover_red_gate = True`，总平均分不能覆盖红灯。
九个必要签署缺一不可（含 `independent_reviewer`）。

## 4. 各闸门的硬规则

- **EM-79 心理测量**：PM0–PM5 + PMX；`精神疾病诊断 / 属灵成熟总分 / 教会资格与纪律 / 与其他用户排名`
  在任何证据水平下都永久禁止；只完成自评验证时不得宣称现实行为能力已验证；阈值明确标为试点默认值。
- **EM-80 数据质量**：八个领域各自评级，跨租户混入、无法追溯、无有效同意、删除后仍参与评分、
  模拟标为现实、重复计分等属关键错误，单条即阻断；重复率 >0.5%、双评率 <20%、关键字段有效性 <100% 触发闸门失败。
- **EM-81 公平性**：某语言危机漏报增加、某宗派被判更成熟、女性或某年龄群被贴「情绪化」、
  非宗教用户被强制祷告、残障用户无法撤回同意、低识字用户因回答短被评低 —— 六条硬阻断。
  样本不足不得宣称公平，问题可只限制某语言或某功能而非全局通过。
- **EM-82 领域安全**：15 类领域伤害必须全部覆盖，7 类为零容忍；人类评审组必须包含
  心理健康专业人员、牧养神学审核者与有教会权力伤害经验的用户代表，且不得有利益冲突者。
- **EM-83 隐私**：P0–P4 敏感级；同意分项且不得与模型改进捆绑；删除必须传播到 11 个目标
  （含向量库、缓存、报表、Twin、导出包、共享摘要、备份）；模型训练默认关闭；牧者不得有角色级访问。
- **EM-84 红队**：14 个攻击面必须全部覆盖；跨租户泄露／未授权发送／未授权删除／同意绕过／
  安全路由被覆盖／高影响工具无需确认 —— 六项零容忍；T4 高影响工具默认不授予 LLM 自主权限。
- **EM-85 变更控制**：实际变更级别由引擎判定而非申请人；模型家族、Rubric、外部工具、分享能力、
  用户群、司法辖区、数据用途变化一律 MAJOR；一句 Prompt 若影响安全路由同样升级为 MAJOR；
  Canary 强制关闭对外分享。
- **EM-87 事故**：SEV0 触发 `GLOBAL_KILL_SWITCH` 并 REVOKE 证书；SEV1/SEV2 SUSPEND 证书并强制召回；
  「只修复代码不能关闭事故」写进返回值，数据库层 `CHECK(closed_at IS NULL OR (recall_completed AND regression_test_added))`。

## 5. 证书边界

内部证书只证明「某一个明确版本、在某一种明确用途、针对某一类明确用户、经过某套明确测试、
在给定限制下获准运行」。它**不证明**临床心理测验认证、精神疾病诊断能力、ISO/IEC 42001 或 27001
外部认证、全球法律合规，或任何属灵成熟资格。数据库层 `CHECK(external_certification_claimed = FALSE)`。

## 6. 新增 API（管理员）

```http
GET  /api/v1/assurance/emd/overview
POST /api/v1/assurance/emd/classify-use
POST /api/v1/assurance/emd/psychometric-review
POST /api/v1/assurance/emd/data-quality-audit
POST /api/v1/assurance/emd/fairness-audit
POST /api/v1/assurance/emd/domain-safety
POST /api/v1/assurance/emd/privacy-assessment
POST /api/v1/assurance/emd/security-redteam
POST /api/v1/assurance/emd/changes
POST /api/v1/assurance/emd/certify
POST /api/v1/assurance/emd/incidents
```

## 7. 测试结果与当前状态

```text
tests/test_production_governance_emd_certification.py    48 passed
```

```json
{
  "architecture_status": "DESIGN_COMPLETE",
  "implementation_status": "EM-01 ~ EM-87 IMPLEMENTED, NOT_VERIFIED_IN_PRODUCTION",
  "psychometric_status": "NOT_EVALUATED",
  "privacy_status": "NOT_ASSESSED",
  "security_status": "NOT_REDTEAMED",
  "production_certificate": "NOT_ISSUED"
}
```

代码闸门已经就位，但真实的心理测量研究、隐私影响评估、红队执行与人类签署尚未发生。
在这些证据真实存在之前，本域只能按 `IU-1 私人自我反思 / exploratory` 对外呈现。
