# 用户人格画像标签系统 - 数据库表结构汇总

## 概述

本次添加的6张表构成完整的用户人格画像标签系统，集成到 `main.py` 的 `_init_db_postgresql()` 函数中，会在应用启动时自动创建。

## 表结构清单

### 1. user_profile_tags (用户标签主表)
存储所有用户的人格画像标签

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键，自动生成 |
| user_id | TEXT | 用户ID（email） |
| tag_name | TEXT | 标签名称 |
| tag_category | TEXT | 标签类别 |
| tag_subcategory | TEXT | 子类别（可选） |
| source | TEXT | 来源类型 |
| confidence | REAL | 置信度 0.0-1.0 |
| weight | REAL | 权重 0.0-10.0 |
| first_seen_at | TIMESTAMP | 首次出现时间 |
| last_seen_at | TIMESTAMP | 最后出现时间 |
| occurrence_count | INTEGER | 出现次数 |
| history_weights | JSONB | 权重历史 [[timestamp, weight], ...] |
| context_snapshot | JSONB | 上下文快照 |
| related_emotions | JSONB | 相关情绪标签 |
| related_decisions | JSONB | 相关决策ID |
| related_habits | JSONB | 相关习惯ID |
| source_events | JSONB | 来源事件引用 |
| is_active | BOOLEAN | 是否活跃 |
| is_manually_added | BOOLEAN | 是否手动添加 |
| is_system_core | BOOLEAN | 是否核心标签 |

**索引**: user_id, (user_id, is_active), tag_category, weight, last_seen_at

---

### 2. tag_event_links (标签事件关联表)
追踪标签的来源事件，支持溯源分析

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tag_id | UUID | 关联标签ID（外键） |
| event_type | TEXT | 事件类型 |
| event_id | TEXT | 事件ID |
| event_data | JSONB | 事件数据快照 |
| extracted_keywords | TEXT[] | 提取的关键词 |
| extraction_confidence | REAL | 提取置信度 |
| created_at | TIMESTAMP | 创建时间 |

**外键**: tag_id → user_profile_tags(id) ON DELETE CASCADE

---

### 3. personality_profile_snapshots (人格画像快照表)
存储人格画像历史版本，支持变化追踪

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | TEXT | 用户ID |
| generated_at | TIMESTAMP | 生成时间 |
| personality_archetype | TEXT | 人格原型（seeker/warrior等） |
| dominant_loop | TEXT | 主导循环模式 |
| trajectory_direction | TEXT | 轨迹方向 |
| humility_score | REAL | 8维状态向量-谦逊 0.05-0.95 |
| fear_tendency_score | REAL | 8维状态向量-恐惧倾向 |
| pride_tendency_score | REAL | 8维状态向量-骄傲倾向 |
| emotional_stability_score | REAL | 8维状态向量-情绪稳定 |
| truth_alignment_score | REAL | 8维状态向量-真理对齐 |
| relational_health_score | REAL | 8维状态向量-关系健康 |
| resilience_score | REAL | 8维状态向量-韧性 |
| spiritual_clarity_score | REAL | 8维状态向量-灵性清晰 |
| vector_confidence | REAL | 向量置信度 |
| top_emotion_tags | JSONB | 情绪标签聚合 |
| top_behavior_tags | JSONB | 行为标签聚合 |
| top_value_tags | JSONB | 价值观标签聚合 |
| top_relationship_tags | JSONB | 关系标签聚合 |
| life_dominant_domains | JSONB | 主导生活领域 |
| recurring_patterns | JSONB | 重复模式 |
| growth_indicators | JSONB | 成长指标 |
| risk_factors | JSONB | 风险因素 |
| profile_stability | REAL | 画像稳定性 |
| change_velocity | REAL | 变化速度 |
| trend_direction | TEXT | 趋势方向 |
| profile_summary | TEXT | 画像摘要 |
| core_narrative | TEXT | 核心叙事 |
| growth_pathway | TEXT | 成长路径 |
| version | INTEGER | 版本号 |
| is_current | BOOLEAN | 是否当前版本 |

---

### 4. tag_weight_history (标签权重历史表)
记录标签权重变化轨迹，用于趋势分析

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tag_id | UUID | 关联标签ID（外键） |
| recorded_at | TIMESTAMP | 记录时间 |
| weight | REAL | 当时权重 |
| change_reason | TEXT | 变化原因 |
| source_event_type | TEXT | 来源事件类型 |
| source_event_id | TEXT | 来源事件ID |
| occurrence_count_at_record | INTEGER | 当时的出现次数 |
| confidence_at_record | REAL | 当时的置信度 |

---

### 5. user_tag_statistics (用户标签统计汇总表)
用户标签统计聚合，优化查询性能

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT | 用户ID（主键） |
| total_tags | INTEGER | 总标签数 |
| active_tags | INTEGER | 活跃标签数 |
| manually_added_tags | INTEGER | 手动添加数 |
| emotion_tags_count | INTEGER | 情绪标签数 |
| behavior_tags_count | INTEGER | 行为标签数 |
| value_tags_count | INTEGER | 价值观标签数 |
| relationship_tags_count | INTEGER | 关系标签数 |
| average_weight | REAL | 平均权重 |
| max_weight | REAL | 最大权重 |
| oldest_tag_at | TIMESTAMP | 最早标签时间 |
| newest_tag_at | TIMESTAMP | 最新标签时间 |
| top_tags | JSONB | TOP5标签 [{name, category, weight}] |
| updated_at | TIMESTAMP | 更新时间 |

---

### 6. tag_category_metadata (标签类别元数据表)
标签类别定义和显示信息

| 字段 | 类型 | 说明 |
|------|------|------|
| category | TEXT | 类别标识（主键） |
| display_name | TEXT | 显示名称 |
| description | TEXT | 描述 |
| display_order | INTEGER | 显示顺序 |
| color_code | TEXT | 颜色代码（如 #FF6B6B） |

---

## 可选演示数据

演示用户和以下 6 条人格画像标签默认不创建。仅在隔离的演示环境显式设置
`SEED_DEMO_USER=true`、`DEMO_USER_EMAIL` 和不少于 12 位的
`DEMO_USER_PASSWORD` 时创建；生产环境应保持关闭。

| 标签名称 | 类别 | 权重 | 置信度 | 上下文 |
|----------|------|------|--------|--------|
| 焦虑型 | emotion_type | 2.5 | 0.8 | 工作压力 |
| 恐惧驱动 | motive | 1.8 | 0.75 | 完美主义 |
| 工作领域 | life_domain | 2.2 | 0.9 | 职业专注 |
| 灵修习惯 | habit_type | 3.0 | 0.85 | 每日灵修 |
| 探索期 | life_stage | 1.5 | 0.7 | 寻求方向 |
| 真实导向 | value | 2.0 | 0.8 | 真实性 |

---

## 18种标签类别

1. **emotion_type** - 情绪类型（焦虑型、喜悦型等）
2. **emotion_pattern** - 情绪模式（情绪波动型等）
3. **habit_type** - 习惯类型（灵修习惯、健康习惯等）
4. **habit_consistency** - 习惯坚持度（高度自律等）
5. **character_trait** - 性格特质（谦逊型等）
6. **behavior** - 行为模式（逃避型、完美主义等）
7. **response_style** - 应对风格（问题解决型等）
8. **stress_reaction** - 压力反应（压力下焦虑等）
9. **life_domain** - 生活领域（工作领域、家庭领域等）
10. **life_stage** - 人生阶段（探索期、稳定期等）
11. **value** - 价值观（安全感导向、成就导向等）
12. **motive** - 动机类型（恐惧驱动、爱驱动等）
13. **relationship** - 关系类型（亲密关系、职场关系等）
14. **attachment** - 依恋风格（安全依恋等）
15. **social** - 社交偏好（外向型、内向型等）
16. **cognitive** - 认知风格（理性分析型等）
17. **spiritual** - 灵性状态（灵性干枯、感恩灵修等）
18. **decision** - 决策风格（快速决策、拖延决策等）

---

## 部署说明

所有表结构和初始数据会在应用启动时通过 `_init_db_postgresql()` 自动执行：

```sql
-- Neon PostgreSQL 会自动执行 main.py 中的 CREATE TABLE IF NOT EXISTS 语句
-- 所有数据插入使用 ON CONFLICT 避免重复
```

### 手动执行（如需单独初始化）

```bash
# 使用 psql 连接到 Neon 数据库
psql $DATABASE_URL -f backend/user_profile_schema.sql

# 或使用 Python 脚本
python -c "from backend.main import _init_db; _init_db()"
```

---

## 关联文件

| 文件 | 说明 |
|------|------|
| `main.py` | 数据库初始化代码（487-714行） |
| `user_profile_tag_system.py` | 核心系统实现 |
| `user_profile_tag_api.py` | FastAPI 接口 |
| `user_profile_schema.sql` | 完整Schema定义 |
| `USER_PROFILE_SYSTEM_README.md` | 系统完整文档 |
