# 属灵星球「洞鉴别」Skills 完成度报告

日期：2026-08-05
范围：Batch 01–10 交付包 + `bible3dsphere` 仓库落地

---

## 一、起点：审计发现的 4 个缺口

| # | 缺口 | 状态 |
|---|------|------|
| 1 | Batch 01 无 `src/`、无 `tests/`，validation=unknown | ✅ 已补齐 |
| 2 | 174 个 runtime SKILL.md 未进仓库，registry 无 skill 装载器 | ✅ 已补齐 |
| 3 | SKILL.md 契约与执行体之间断裂，无实现绑定 | ✅ 已补齐 |
| 4 | 只有数据契约测试，无技能行为测试 | ✅ 已补齐 |

---

## 二、第 1 步：Batch 01 补齐

新增 `src/discernment_orchestrator/`（15 个模块）：

- `models.py` — 30+ Pydantic 模型与枚举（E0–E4 证据阶梯、12 类自高信号、10 阶段追问、13 个状态、5 个失败码）
- `taxonomy.py` — 版本化中文词表（主张标记、自高标记与替代解释、欲望链模板、安全模式、经文锚点）
- 10 个技能模块，逐条对应 SKILL.md 契约：
  `intake` / `claims` / `worldview` / `pride` / `desire` / `socratic` / `gospel` / `report` / `safety` / `trace`
- `state.py` — 显式状态机（含非法转移拒绝、失败路由、重试预算）
- `orchestrator.py` — 完整数据流，含高风险中止、同意缺失中止、证据不足中止三条退出路径

新增 `tests/`（13 个测试文件，**120 个测试**）：

- 每个技能 ≥ 5 个单元测试（验收标准要求）
- 10 个端到端测试（验收标准要求 ≥ 3）
- 两个 JSON Schema 的 Draft 2020-12 一致性测试
- **覆盖率 97%**（验收门槛 85%）

`VALIDATION_REPORT.json` 由 `unknown` 更新为 `PASS`；`CHECKSUMS.json` 重新生成；
`_original_archives/batch01.zip` 与 `MASTER_INDEX.json` 同步更新（总包版本 1.0.1）。

---

## 三、第 2 步：Skills 装载器与 skill_id 路由

- **265 个 SKILL.md 全部进入仓库**
  - 174 个 runtime skill → `backend/discernment_platform/data/skills/batchNN/…`
  - 91 个 pack skill → 各 pack 目录（补齐了此前缺失的 domain 32 / hypothesis 9 / doctrine 10）
- 新增 `skills.py`：front-matter + 章节解析器、`SkillContract`、`SkillRegistry`
  - 强校验：7 个必需章节、5 个必需 front-matter 字段、逐批数量、skill_id 唯一性
  - 路由：`get(skill_id)` / `for_batch()` / `pipeline()`（always-on 守卫排在最前）/ `search()`
- `registry.py` 接入：
  - `DiscernmentRegistry.load()` 加载 skills 并交叉校验 **manifest 声明数 == 实际装载数**
  - 新增 `get_skill(skill_id)`、`skill_pipeline(batch)`
  - 新增 pack SKILL.md 存在性校验

---

## 四、第 3 步：174 个技能全部绑定实现

新增 `skill_runtime.py` + `guardrails.py` + `skill_handlers/`（9 个模块）。

### 三种绑定模式，每次调用都自报使用了哪一种

| 模式 | 数量 | 含义 |
|------|------|------|
| `native` | **92** | 由 Python 引擎真实计算，`status=ok`，输出为实算结果 |
| `model` | **82** | 契约需要语言模型：未配置适配器时返回 `requires_model` + **完整渲染的提示词** + 输出信封，**不编造任何内容** |

native 绑定分布：Batch 01 → `batch01_core`（10）；Batch 03/04 → 判别引擎与 hypothesis packs；
Batch 05 → 对话引擎；Batch 06 → doctrine packs 与福音路径引擎；
Batch 07 → `formation_twin`；Batch 08 → `pastoral_collaboration`；
Batch 09 → `theology_knowledge`；Batch 10 → `production_gate`。

### Guardrail 强制执行

`guardrails.py` 把 SKILL.md 的 Guardrails 散文映射为 **22 个可执行规则族**，例如：

- `evidence_level_floor` — E0–E2 不得标记为结论
- `no_salvation_judgment` / `no_spiritual_abuse` / `no_clinical_diagnosis`
- `no_mind_reading` — 动机类判断必须带替代解释与证据等级
- `no_fabricated_evidence` — 引用的证据 id 必须在输入中存在
- `no_ai_self_certification` — C3/C4 控制项无人工复核不得判通过
- `rollback_required` / `no_silent_expiry` / `no_score_override`
- `consent_required` / `minimize_pii` / `tenant_isolation`

全语料 **1185 条 guardrail**：**535 条被自动规则覆盖**，其余 650 条标记为
`manual_review` 并逐条上报——**没有一条被静默丢弃**。

违反 guardrail 的输出会被置为 `blocked`，不会返回给用户。

### 失败处理

每个技能的 Failure Handling 章节映射为结构化失败码
（`INSUFFICIENT_EVIDENCE` / `HIGH_RISK_REVIEW` / `USER_CONSENT_REQUIRED` /
`UNSUPPORTED_THEOLOGICAL_CLAIM` / `MODEL_OUTPUT_INVALID` /
`MISSING_REQUIRED_INPUT` / `GUARDRAIL_VIOLATION`），并附 trace（输入/输出/提示词哈希、延迟、适配器）。

---

## 五、第 4 步：行为测试

| 测试文件 | 数量 | 内容 |
|---------|------|------|
| `test_skill_contracts.py` | 16 | 174 个契约解析、逐批数量、必需章节、id 唯一性、manifest 一致性 |
| `test_skill_guardrails.py` | 22 | 22 个规则族逐一验证；确认无 guardrail 被静默丢弃 |
| `test_skill_runtime.py` | 19 | 174 个技能全部可调用；模型适配器接受/拒绝；提示词渲染；失败码映射 |
| `test_skill_bindings.py` | 39 | Batch 01–10 绑定行为 |
| `test_skill_bindings_deep.py` | 42 | Batch 05–10 用真实 payload 驱动引擎（这一轮抓出并修复了 9 处签名不匹配） |
| `tests/batch01_core/` | 120 | Batch 01 全套单元 + 端到端测试 |
| **合计** | **258** | 全部通过 |

新增层覆盖率 **94%**。

---

## 六、当前真实状态

✅ 174 个技能全部可按 `skill_id` 调度，无一崩溃
✅ 92 个由真实代码计算
⚠️ 82 个走模型契约绑定——已渲染完整提示词与输出信封，但**需要接入 LLM 适配器才能产出内容**
⚠️ guardrail 自动覆盖 45%（535/1185），其余需人工复核（已逐条标记）

### 下一步建议

1. 实现一个 `ModelAdapter`（OpenAI / Anthropic / 本地），82 个契约绑定即可产出真实结构化输出
2. 继续扩展 guardrail 规则族，把 `manual_review` 比例降下来
3. 为 82 个模型绑定技能补黄金样例（golden set），用于回归评测

---

## 七、改动清单

**新增**
```
backend/discernment_platform/skills.py
backend/discernment_platform/skill_runtime.py
backend/discernment_platform/guardrails.py
backend/discernment_platform/batch01_core/            (15 个模块)
backend/discernment_platform/skill_handlers/          (11 个模块)
backend/discernment_platform/data/skills/             (174 个 SKILL.md)
backend/discernment_platform/data/{domain,hypothesis,doctrine}_packs/*/SKILL.md  (51 个)
backend/tests/test_skill_contracts.py
backend/tests/test_skill_guardrails.py
backend/tests/test_skill_runtime.py
backend/tests/test_skill_bindings.py
backend/tests/test_skill_bindings_deep.py
backend/tests/batch01_core/                           (13 个测试文件 + fixtures)
```

**修改**
```
backend/discernment_platform/registry.py     (skills 装载 + skill_id 路由 + 交叉校验)
backend/discernment_platform/__init__.py     (导出新 API)
```

传输用的临时压缩包已移入仓库根目录的 `_to_delete/`，可自行删除。
