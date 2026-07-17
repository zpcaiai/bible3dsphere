# Emotional Snapshot Model

系统生成 `CURRENT_EMOTIONAL_STATE`、`DAILY_EMOTIONAL_SUMMARY` 与 `WEEKLY_EMOTIONAL_TREND` 三类不可变快照。每份快照包含窗口、数据状态、覆盖率、用户自述区、规则计算区、待确认候选区、不确定性、限制、引擎版本、输入哈希和版本链。

用户自述区可包含情绪、身体感受以及最近一次精力、压力、睡眠记录；规则区包含 `emotional-rules-1.0` 的方向、数据点数量、中位数和范围；模型区只包含 `PENDING` 候选。三块在存储、API 与 UI 中独立展示。

少于三个不同日期的数据返回 `INSUFFICIENT_DATA`，而不是画出误导性趋势。覆盖率仅是记录完整度。快照不包含总分、心理健康分、长期人格结论或属灵等级。相同输入哈希复用快照；输入或用户纠正变化时创建新版本并 supersede 当前版本。
