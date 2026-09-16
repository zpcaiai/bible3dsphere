# ModelAdapter 启用指南

82 个「模型契约绑定」技能默认返回 `requires_model`（只给提示词与输出信封，不编造内容）。
配置一个适配器后，它们才会产出真实结构化输出。

## 一、环境变量（推荐）

```bash
# 不设置 = NullAdapter = 保持「绝不编造」的默认行为
export DISCERNMENT_MODEL_PROVIDER=anthropic     # anthropic | openai | gemini | local | null

export DISCERNMENT_MODEL_NAME=claude-opus-4-5   # 可选，各 provider 有默认值
export DISCERNMENT_MODEL_MAX_ATTEMPTS=2         # 可选，结构修复重试次数
export DISCERNMENT_MODEL_TEMPERATURE=0.0        # 可选
export DISCERNMENT_MODEL_MAX_TOKENS=4096        # 可选

export ANTHROPIC_API_KEY=sk-ant-...             # provider=anthropic 时必需
# export OPENAI_API_KEY=sk-...                  # provider=openai 时必需
# export GEMINI_API_KEY=...                     # provider=gemini 时必需（GOOGLE_API_KEY 亦可）
```

Gemini：

```bash
export DISCERNMENT_MODEL_PROVIDER=gemini
export DISCERNMENT_MODEL_NAME=gemini-2.5-pro    # 模型名变动快，建议显式指定
export GEMINI_API_KEY=...
```

Gemini 走 Generative Language REST API，只用 stdlib `urllib`，不需要装
`google-generativeai`。API key 放在 `x-goog-api-key` 请求头里，不进 URL、不进访问日志。
`responseMimeType: application/json` 强制模型只输出 JSON。

本地模型（Ollama / LM Studio / vLLM / llama.cpp，任何 OpenAI 兼容端点）：

```bash
export DISCERNMENT_MODEL_PROVIDER=local
export DISCERNMENT_MODEL_BASE_URL=http://localhost:11434/v1
export DISCERNMENT_MODEL_NAME=qwen2.5:14b
```

本地路径只用 stdlib `urllib`，不需要任何第三方 SDK —— 在封闭部署里也可用。

## 二、代码内构造

```python
from backend.discernment_platform import SkillRuntime, AnthropicAdapter

runtime = SkillRuntime(adapter=AnthropicAdapter(model="claude-opus-4-5"))
result = runtime.invoke("content-corpus-curator", {"case_id": "c1", ...})
```

## 三、四种适配器

| 适配器 | 用途 |
|--------|------|
| `AnthropicAdapter` | Claude，走官方 `anthropic` SDK |
| `OpenAIAdapter` | GPT，走官方 `openai` SDK，强制 `json_object` 响应格式 |
| `GeminiAdapter` | Gemini，走 REST API，零第三方依赖，header 鉴权 |
| `LocalOpenAIAdapter` | 任意 OpenAI 兼容本地端点，零第三方依赖 |
| `ScriptedAdapter` | 回放预设结果，用于黄金样例回归与离线开发 |
| `RecordingAdapter` | 包装以上任意一个，记录每次交互供审计或回放 |

## 四、四条不随 provider 改变的保证

无论用哪个 provider，`BaseModelAdapter` 统一提供：

1. **JSON 提取** —— 容忍 ```json 围栏、前置说明文字；数组或非对象一律拒绝
2. **Schema 校验** —— 缺少契约声明的任何一个输出键即判 `MODEL_OUTPUT_INVALID`
3. **修复重试** —— 缺键时自动追加修复指令重问，并明确要求「未知就填 null，绝不臆造」
4. **用量记账** —— input/output token 与尝试次数写入每次调用的 trace

## 五、Guardrail 仍然在模型之后把关

模型返回的内容同样要过完整的 guardrail 层。违反者状态置为 `blocked`，不会返回给用户。
测试 `test_guardrails_still_gate_model_output` 固定了这一行为。

## 六、建议的上线顺序

1. 先用 `ScriptedAdapter` 建一批黄金样例，锁住期望输出形状
2. 用 `RecordingAdapter` 包裹真实 provider 跑一轮，人工看 transcript
3. 从低风险 batch（03/04/09）开始放量，Batch 05/06/08 涉及牧养与安全，最后放
4. Batch 10 的 C3/C4 控制项按 guardrail 规定仍需人工签署，不得由模型自证
