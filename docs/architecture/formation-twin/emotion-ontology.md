# Emotion Ontology

本体是开放、非诊断、非互斥的词汇表，版本为 `1.0`，中英文资源分别位于 `backend/formation_twin/emotion_ontology.zh-CN.json` 与 `emotion_ontology.en.json`。

标准标签覆盖喜乐、平安、爱、盼望、感恩、悲伤、哀伤、孤单、愤怒、恐惧、担忧、羞耻、内疚、麻木、困惑等日常情感描述，并提供 `MIXED`、`UNKNOWN` 和 `OTHER`。无法映射的用户词不会被丢弃，而是保留为 `OTHER.custom_label`。多种情绪可以同时存在，中文别名只做可逆规范化，不宣称跨文化一一对应。

本体明确排除抑郁症、双相、依恋障碍、人格类型、创伤诊断、属灵等级、救恩状态等标签。“平安”“交托”等宗教语言不会自动变成稳定心理状态或属灵事实。valence、arousal、dominance 仅可作为辅助字段，不能覆盖用户选择的名称。
