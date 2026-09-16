# 放量运行手册

模型绑定技能的分阶段上线流程。原生技能（92 个）不受此约束，它们是确定性 Python，始终运行。

---

## 一、四个阶段

| 阶段 | 模型是否调用 | 输出是否权威 | 是否强制人工复核 |
|------|------------|------------|----------------|
| `disabled` | 否 | — | — |
| `shadow` | 是 | **否**（仅作对照） | 是 |
| `pilot` | 是 | 是 | 是 |
| `production` | 是 | 是 | 否 |

`disabled` 返回 `blocked_by_rollout`，不会伪装成正常结果。
`shadow` 返回 `status="shadow"` 且 `authoritative=False` —— 调用方不得据此行动。

**guardrail 在所有阶段一律生效**：shadow 阶段的违规输出同样被置为 `blocked`。

---

## 二、当前计划（`data/config/rollout.json`）

| 批次 | 阶段 | 理由 |
|------|------|------|
| batch01 | production | 全部原生，无模型绑定 |
| batch03 网红热点分析 | **pilot** | 只用公开材料，牧养风险低 |
| batch04 自高自义模型 | **pilot** | 只出假设，从不出判决 |
| batch05 苏格拉底对话 | shadow | 直接对用户说话 |
| batch06 律法—福音路径 | shadow | 教义内容 |
| batch07 Formation Twin | shadow | 纵向个人数据 |
| batch08 牧者协作 | shadow | 涉及保护与访问控制 |
| batch09 释经与证据 | **pilot** | 引文绑定，可审计 |
| batch10 发布门 | shadow | C3/C4 必须人工签署 |

两个技能被单独钉在 shadow，即使所属批次是 pilot：
`scrupulosity-and-trauma-guardian`、`public-person-reputation-guardian`。

`batch08` 与 `batch10` 标记为 `HUMAN_SIGNOFF_BATCHES` —— 即使提到 production，
其高危控制项仍强制 `human_review_required`，模型不得自证。

---

## 三、升级一个批次的标准流程

### 1. 先离线自检

```bash
python tools/run_golden_set.py --provider scripted --policy file --batch batch05
```

期望 `regressions: 0`。这一步只验证形状与 guardrail，不花任何 API 额度。

### 2. 接真实 provider 跑该批次

```bash
export DISCERNMENT_MODEL_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

python tools/run_golden_set.py \
    --provider anthropic \
    --policy file \
    --batch batch05 \
    --show-prompts \
    --out reports/batch05-$(date +%F).json
```

所有调用都过 `RecordingAdapter`，报告里有完整 prompt 与响应。

### 3. 人工读 transcript

重点看四件事，而不只看 `regressions` 数字：

- **形状差异**（`shape_diffs`）—— 结构变了说明下游解析会碎
- **guardrail 违规**（`guardrail_violations`）—— 一条都不能放过
- **curated 案例的内容**（`tier: curated`）—— 形状对但含义错，只有人能看出来
- **`limitations` 是否诚实** —— 模型是否在证据不足时仍给出结论

### 4. 升级

改 `data/config/rollout.json`，或用环境变量临时提升：

```bash
export DISCERNMENT_ROLLOUT_BATCH05=pilot
```

### 5. 回滚

```bash
export DISCERNMENT_ROLLOUT_BATCH05=shadow   # 或 disabled
```

回滚不需要改代码，也不需要重新部署镜像。

---

## 四、放量顺序建议

```
shadow ──(读 transcript，看 curated 内容)──> pilot ──(积累人工复核样本)──> production
```

- **batch03 / 04 / 09**：已在 pilot。积累一段时间的人工复核记录后可考虑 production。
- **batch05 / 06**：涉及直接对话与教义表述，建议在 shadow 停留更久，并与原生引擎输出做对照。
- **batch07 / 08**：涉及个人纵向数据与保护义务，升级前需要隐私与保护条线签字。
- **batch10**：不建议升到 production。发布门由模型自证，与 `no_ai_self_certification` guardrail 的意图直接冲突。

---

## 五、随时可查的状态

```python
from backend.discernment_platform import get_runtime
get_runtime().rollout_report()
# {'policy': {...}, 'model_bound_skills': 82,
#  'by_stage': {'pilot': 34, 'shadow': 48}, 'authoritative': 34, 'blocked': []}
```

每次调用的结果里也带着当次决定：

```python
result.rollout       # {'stage': 'pilot', 'batch_key': 'batch03', 'reason': '...'}
result.authoritative # 调用方唯一该判断的字段
```
