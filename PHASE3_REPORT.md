# 第三阶段完成报告：黄金样例集 · 回放工具 · 分阶段放量

日期：2026-08-05
接续 `SKILLS_COMPLETION_REPORT.md`、`PHASE2_REPORT.md`

---

## 一、黄金样例集：82 个模型绑定技能全覆盖

`data/golden/batchNN/<skill_id>.json`，每个技能一份。

| 层级 | 数量 | 含义 |
|------|------|------|
| `curated` | **12** | 人工撰写，同时锁定**输出形状与内容质量** |
| `structural` | 70 | 锁定输出形状 |
| **合计** | **82** | 与模型绑定技能一一对应 |

**关键约束：黄金样例本身必须通过它所属契约的全部 guardrail。**
生成器在写盘前先把每份样例过一遍真实 runtime，被 `blocked` 的样例根本不会落地。
这样 guardrail 层就有了一份持续被真实内容检验的语料，而不只是被单元测试的合成输入检验。

### curated 的 12 个是首轮放量批次的入口技能

- **batch03**：`identity-persona-separator`、`narrative-rhetoric-analyzer`、
  `business-model-monetization-analyzer`、`manipulation-trust-risk-detector`
- **batch04**：`hypothesis-composer`、`self-justification-engine`、
  `scrupulosity-and-trauma-guardian`、`integrated-pride-report-composer`
- **batch09**：`scripture-context-resolver`、`greek-morphology-syntax-analyzer`、
  `systematic-doctrine-claim-builder`、`theology-answer-composer-and-red-team`

两个场景贯穿其中：batch03/04 用「成功主义网红」案例（与 Batch 01 fixture 语料一致），
batch09 用罗马书 8:1 的释经查询。内容是真的 —— 例如 batch09 的
`κατάκριμα` 分析带词形、语料用法、NA28/TR 异文说明与传统归属标注。

形状对但含义错的输出，只有 curated 层能抓住。

### 生成过程中发现的真实问题

第一轮 82 份样例里有 16 份回放失败。原因：生成器把 guardrail 补偿字段
（`_care_note`、`_scripture_context`）加在了**输出信封之外**，而 runtime 会把结果裁剪到契约声明的键。
那些字段被丢弃 → 形状差异。已改为把补偿内容放进已声明的输出键内部。

这正是黄金样例的价值：它抓住了一个「测试全绿但线上会碎」的类别。

---

## 二、回放工具：`tools/run_golden_set.py`

放量前的闸门。所有调用都经 `RecordingAdapter`，报告里留有完整 prompt 与响应 —— **重点是人去看模型说了什么，而不只是看它能不能被解析**。

```bash
# 离线自检，不花额度
python tools/run_golden_set.py --provider scripted --policy file

# 单批次接真实 provider，写 transcript
ANTHROPIC_API_KEY=... python tools/run_golden_set.py \
    --provider anthropic --batch batch03 --show-prompts --out reports/b03.json
```

支持按批次 / 技能 / 层级筛选，退出码可直接接 CI：
`0` 无回归 · `1` 有回归 · `2` 配置或凭证问题（缺 key、未知 provider、空选集都给干净的一行错误，不吐 traceback）。

报告包含：形状差异、guardrail 违规、rollout 阶段、token 用量、live 与 golden 输出对照、transcript。

---

## 三、分阶段放量：`rollout.py`

四个阶段，信任度递增：

| 阶段 | 调模型 | 输出权威 | 强制人工复核 |
|------|-------|---------|------------|
| `disabled` | 否 | — | — |
| `shadow` | 是 | **否** | 是 |
| `pilot` | 是 | 是 | 是 |
| `production` | 是 | 是 | 否 |

`disabled` 返回 `blocked_by_rollout` —— 不会让调用方把沉默当成干净结果。
`shadow` 返回 `status="shadow"`、`authoritative=False`。
**guardrail 在所有阶段一律生效**，shadow 阶段的违规输出同样 `blocked`。

### 首轮计划（已随包提供，`data/config/rollout.json`）

- **pilot**：batch03（公开材料，牧养风险低）、batch04（只出假设不出判决）、batch09（引文绑定，可审计）
- **shadow**：batch05/06（直接对话与教义）、batch07（纵向个人数据）、batch08（保护与访问控制）、batch10（发布门）
- **单独钉在 shadow**：`scrupulosity-and-trauma-guardian`、`public-person-reputation-guardian`

当前效果：82 个模型绑定技能中 **34 个权威（pilot）、48 个 shadow**。

`batch08` / `batch10` 标记为 `HUMAN_SIGNOFF_BATCHES` —— 即使提到 production，
高危控制项仍强制人工复核。让模型自证发布门与 `no_ai_self_certification` guardrail 的意图直接冲突。

### 默认不改变现有行为

`SkillRuntime(...)` 直接构造时默认 `unrestricted`；只有进程级的 `get_runtime()`
才从环境变量装配分阶段策略。回滚不需要改代码：

```bash
export DISCERNMENT_ROLLOUT_BATCH05=shadow   # 或 disabled
```

详细流程见 `ROLLOUT_RUNBOOK.md`。

---

## 四、测试

| 文件 | 数量 |
|------|------|
| `test_golden_set.py` | **35** |
| `test_rollout.py` | **44** |
| `test_golden_harness.py` | **26** |
| 前两阶段 | 395 |
| **合计** | **500 全部通过** |

新增层覆盖率 **95%**（rollout 100% / golden 97% / model_adapter 96% / guardrails 95%）。

### 这一轮抓到的真实缺陷

1. **`_HANDLERS` 空表**：原生 handler 只在 `get_runtime()` 里注册，直接构造
   `SkillRuntime` 会看到空表，把 174 个技能全当成模型绑定。已有测试是靠调用顺序碰巧通过的 ——
   一个潜伏的顺序依赖。已改为在构造函数里保证注册。
2. **`plan or DEFAULT_PLAN`**：显式传入空计划会被静默替换成默认计划。
   已改为区分 `None` 与 `{}`。
3. **黄金样例的信封外字段**（见上）。

---

## 五、当前完整状态

| 层 | 状态 |
|----|------|
| 174 个技能 | 全部可调度，92 原生 + 82 模型绑定 |
| guardrail | 66 个规则族，1208 条全覆盖，违规即 `blocked` |
| 模型适配器 | 4 种 provider，统一解析 / 校验 / 修复重试 / 用量记账 |
| 黄金样例 | 82 份，12 份人工撰写，全部通过自身 guardrail |
| 回放工具 | 可按批次运行，留完整 transcript，退出码可接 CI |
| 放量控制 | 4 阶段，34 权威 / 48 shadow，环境变量即可回滚 |
| 测试 | 500 通过，新增层覆盖率 95% |

### 下一步（需要你的 API key 才能做的部分）

1. `export ANTHROPIC_API_KEY=...` 后按 `ROLLOUT_RUNBOOK.md` 第三节跑 batch03
2. 读 transcript，特别是 4 个 curated 案例的内容质量
3. 确认无误后逐步把 batch05/06 从 shadow 提到 pilot

我做不了第 1 步 —— 这个环境没有你的凭证，也不该有。工具和闸门都已就位。

---

## 六、改动清单

**新增**
```
backend/discernment_platform/golden.py
backend/discernment_platform/rollout.py
backend/discernment_platform/data/golden/            (82 份黄金样例)
backend/discernment_platform/data/config/rollout.json
backend/tests/test_golden_set.py
backend/tests/test_rollout.py
backend/tests/test_golden_harness.py
tools/build_golden_set.py                            (结构性样例生成器)
tools/curate_golden_set.py                           (人工样例)
tools/run_golden_set.py                              (回放与 transcript 工具)
ROLLOUT_RUNBOOK.md
```

**修改**
```
backend/discernment_platform/skill_runtime.py   (rollout 门控；构造时注册 handler；SkillResult.authoritative)
backend/discernment_platform/__init__.py        (导出 golden 与 rollout API)
```
