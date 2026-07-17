# Emotional State Engine

Batch 3 把现有生命事件、签到、日志授权、安全网关和事件总线整合为一个可重建的情感状态镜像，不生成心理诊断、属灵判断或综合健康分。

处理链固定为：读取当前用户的 `ACCEPTED` 生命事件 → 排除删除、`STORE_ONLY` 与 `EXCLUDE_FROM_TWIN` → 提取用户明确填写的情绪、身体、精力、压力和睡眠 → 运行版本化确定性规则 → 在双重授权下可选运行文本候选模型 → 保存不可变快照。`ROUTED_TO_CRISIS` 事件不进入普通情感处理，Crisis Care 仍是唯一危机判断来源。

来源契约不可互换：`USER_REPORT/USER_REPORTED_FACT`、`RULE/RULE_DERIVED_METRIC`、`MODEL/MODEL_INFERENCE`、`USER_CONFIRMED/USER_CONFIRMED_INFERENCE`。模型候选只有经用户确认后才新建 `USER_CONFIRMED` 记录，原候选保留审计状态。

环境开关：`FORMATION_TWIN_EMOTION_ENGINE_ENABLED` 默认开，`FORMATION_TWIN_EMOTION_TRENDS_ENABLED` 默认开，`FORMATION_TWIN_MODEL_INFERENCE_ENABLED` 默认关。用户级授权可以进一步关闭引擎、趋势或模型，但不能越过全局开关。

重建是 owner-scoped、输入哈希幂等且保留历史版本。原事件被修改、删除或排除后，相关观察会在重建时失效；控制动作也会立即让当前快照过期。
