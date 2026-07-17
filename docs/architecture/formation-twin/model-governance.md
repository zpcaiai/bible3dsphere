# Model Governance

模型运行复用系统现有 provider，不创建旁路基础设施。每次授权调用只记录 request id、provider policy、模型名/版本、提示词模板版本、Schema 版本、结果状态、延迟/用量（如 provider 返回）和脱敏错误码；不记录输入正文或模型原始敏感输出。

当前版本为提示词 `emotion-extraction-1.0`、Schema `emotion-candidates-1.0`、引擎 `emotional-state-engine-1.0`。结构化输出需经过边界、证据和禁止领域检查。未经用户确认的结果不能进入用户事实、规则趋势或后续属灵形成判断。

用户可确认、部分确认、重标注、否定或不回答。确认行为新建 `USER_CONFIRMED_INFERENCE`，不会原地篡改模型记录。授权变更写入元数据事件；完整文本不进入 domain event。数据导出包含治理状态，彻底擦除会按外键顺序删除全部 Batch 3 表。
