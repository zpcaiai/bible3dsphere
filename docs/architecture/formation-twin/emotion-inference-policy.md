# Emotion Inference Policy

文本候选推断采用三重门控：全局环境开关、真实可用的既有 LLM provider、用户级明确同意与 provider policy。任一条件不满足即 fail closed。模型默认关闭。

输入仅限用户允许分析的加密内容；`STORE_ONLY`、排除、删除、supersede 以及 Crisis `ELEVATED/IMMINENT` 内容禁止调用普通模型。输出必须通过 Pydantic 结构化 Schema；无证据偏移、越界证据、置信度低于 0.45、诊断尝试或属灵评判尝试全部拒绝。

模型只能提出情绪和身体感受候选，不得推断人格、核心信念、偶像、罪、救恩、神的旨意、心理疾病或第三方内心。高置信度不改变治理级别。拒绝或忽略后的候选保留状态，唯一约束阻止同一事件和标签被重复创建。
