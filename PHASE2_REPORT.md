# 第二阶段完成报告：Guardrail 全覆盖 + ModelAdapter

日期：2026-08-05
接续 `SKILLS_COMPLETION_REPORT.md`

---

## 执行顺序说明

先做 guardrail，后做 ModelAdapter。理由：适配器一旦接上，82 个技能立刻开始产出模型内容，
而这些内容全部要穿过 guardrail 层。在过滤器只拦得住 45% 的时候开闸，是把风险放在前面。

---

## 一、Guardrail：45% → 100%

| 指标 | 之前 | 现在 |
|------|------|------|
| 规则族 | 22 | **66** |
| guardrail 判定总数 | 1185 | 1208 |
| 自动覆盖 | 535（45%） | **1208（100%）** |
| 需人工复核 | 650 | **0** |

新增 44 个规则族，全部是对输出载荷的真实检查，不是关键词占位。按域分：

**牧养与创伤**
`no_trauma_invalidation`（否定所报伤害）、`no_forced_reconciliation`（施虐语境谈饶恕却不谈安全也会触发）、
`no_scrupulosity_amplification`、`no_victim_blaming`、`no_abusive_scripture_application`

**福音质量**
`no_moralism`（给了行为清单却无基督）、`no_cheap_grace`（福音输出未提罪与悔改）、
`no_prosperity_promises`、`no_denominational_overreach`（D2/D3 教义未标传统归属）、
`no_salvation_scoring`、`no_single_maturity_score`、`no_blanket_demonisation`、`distinguish_grace_levels`

**对话与纵向**
`no_hidden_multi_question`（数问号，>1 即拦）、`no_deterministic_prediction`（含 probability≥1）、
`no_public_person_private_twin`、`no_unsupported_certainty`（确定性措辞需 E3/E4 支撑）

**治理与访问**
`no_disabling_recertification`、`no_unlimited_pastoral_access`（披露缺到期或用途）、
`no_surveillance_accountability`、`no_hidden_resharing`（共享无同意依据或审计号）、
`no_internal_only_abuse`、`no_professional_claims_without_review`、`no_replacing_professional_care`、
`high_risk_domain_routing`

**释经与版权**
`no_proof_texting`、`no_strong_number_only`、`no_copyright_leakage`（引文长度 + 权利状态双查）、
`no_offline_external_verification`

**公众人物分析**
`no_harassment_tooling`、`no_dignity_violation`、`no_extreme_sampling`、`no_malice_from_rhetoric`、
`no_commercialisation_as_sin`、`no_platform_manipulation`、`no_private_family_analysis`、
`aggregate_by_default`、`no_divine_verdict_on_virality`、`no_counterfactual_excusing_harm`、
`no_entertainment_criminalisation`、`no_clip_as_whole_person`、`sensitive_attributes_restricted`、
`hide_internal_inferences`、`monetization_risk_dimensions`

未知的自定义 guardrail 仍会走 `manual_review` 上报 —— 这条兜底路径保留着，只是当前语料已无未覆盖项。

---

## 二、ModelAdapter：82 个技能可以跑通了

新增 `model_adapter.py`。运行时不接触任何厂商 SDK，只面向一个协议：
`complete(prompt, *, schema) -> dict`。

| 适配器 | 说明 |
|--------|------|
| `AnthropicAdapter` | Claude，官方 SDK |
| `OpenAIAdapter` | GPT，官方 SDK，强制 `json_object` |
| `LocalOpenAIAdapter` | 任意 OpenAI 兼容本地端点（Ollama / LM Studio / vLLM / llama.cpp），**只用 stdlib urllib，零第三方依赖** |
| `ScriptedAdapter` | 回放预设结果，用于黄金样例与离线开发 |
| `RecordingAdapter` | 包装任意适配器，记录每次交互供审计 |

`BaseModelAdapter` 统一了四件事，因此换 provider 不改变任何保证：

1. **JSON 提取** —— 容忍围栏与前置文字；数组/非对象一律拒绝
2. **Schema 校验** —— 缺任一契约输出键即 `MODEL_OUTPUT_INVALID`
3. **修复重试** —— 自动追加修复指令重问，明确「未知填 null，绝不臆造」
4. **用量记账** —— token 与尝试次数进 trace

启用方式见 `MODEL_ADAPTER_SETUP.md`。默认（`DISCERNMENT_MODEL_PROVIDER` 未设）仍是
`NullAdapter` —— 也就是说这次改动**不会自动改变现有部署的行为**，必须显式开启。

---

## 三、测试

| 文件 | 数量 |
|------|------|
| `test_skill_guardrails_extended.py` | **86**（每个新规则族一正一反，防止规则「全触发」或「永不触发」） |
| `test_model_adapter.py` | **51**（JSON 提取 8 种形态、重试与耗尽、三个 provider 的成功/错误/用量/无 key 路径、工厂、运行时集成） |
| 原有 | 258 |
| **合计** | **395 全部通过** |

新增层覆盖率 **94%**（guardrails 94% / model_adapter 96% / skill_runtime 91% / skills 92%）。

### 这一轮测试抓到的真实缺陷

`complete()` 先创建局部 `Usage`，`_generate()` 把 provider 返回的 token 写到 `self.last_usage`，
但循环结束时 `self.last_usage = usage` 又把它覆盖掉 —— token 永远是 0。
三个 provider 的用量测试同时失败，暴露了它。已改为循环前先绑定，并在重试间累加。

其中三条测试值得单独说：

- `test_guardrails_still_gate_model_output` —— 模型输出违反 guardrail 时必须 `blocked`，不得返回
- `test_clean_output_does_not_trip_every_rule` —— 一份良性输出跑全部 174 个契约的 guardrail，零误报
- `test_every_shipped_guardrail_line_now_has_a_rule` —— 语料里不能再有未覆盖的 guardrail 行

---

## 四、当前状态

✅ 174 个技能全部可调度，92 个原生计算，82 个模型绑定（配好适配器即产出）
✅ guardrail 1208 条全部自动覆盖，违反即 `blocked`
✅ 395 个测试通过，新增层覆盖率 94%
✅ 默认行为不变：未配置 provider 时仍是「绝不编造」

### 剩下的事

1. 为 82 个模型绑定技能建黄金样例集（`ScriptedAdapter` 已经是现成的载体）
2. 接真实 provider 跑一轮，用 `RecordingAdapter` 看 transcript 再放量
3. guardrail 规则是保守设计（结构缺失才报），后续可按线上误报/漏报数据调紧

---

## 五、改动清单

**新增**
```
backend/discernment_platform/model_adapter.py
backend/tests/test_skill_guardrails_extended.py
backend/tests/test_model_adapter.py
MODEL_ADAPTER_SETUP.md
```

**修改**
```
backend/discernment_platform/guardrails.py    (22 → 66 个规则族)
backend/discernment_platform/skill_runtime.py (适配器由环境变量装配；trace 记录 token 用量)
backend/discernment_platform/__init__.py      (导出适配器 API)
```
