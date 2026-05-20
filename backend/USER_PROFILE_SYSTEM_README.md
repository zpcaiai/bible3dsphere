# 用户人格画像标签系统 (User Personality Profile Tag System)

## 系统概述

基于 Formation Engine 8维性格轨迹系统的用户人格画像标签系统，整合情绪、习惯、性格、行为模式的多维标签体系，生成用户唯一的人格画像。

## 核心特性

- **8维度性格轨迹** - humility, fear_tendency, pride_tendency, emotional_stability, truth_alignment, relational_health, resilience, spiritual_clarity
- **10种人格原型** - seeker, steward, warrior, artist, thinker, caregiver, leader, contemplative, activist, diplomat
- **5种主导循环** - fear_control, shame_avoidance, pride_comparison, desire_impulse, truth_stability
- **19个标签类别** - 覆盖情绪、习惯、性格、行为、价值观、关系、认知、灵性等维度
- **智能标签提取** - 支持从文本、情绪打卡、决策事件、习惯执行等多源数据自动提取

## 文件结构

```
backend/
├── user_profile_tag_system.py   # 核心系统实现
├── user_profile_tag_api.py      # FastAPI 接口
├── user_profile_schema.sql      # 数据库Schema
└── USER_PROFILE_SYSTEM_README.md # 本文档
```

## 快速集成

### 1. 数据库初始化

```bash
# 在PostgreSQL中执行
psql -d your_database -f backend/user_profile_schema.sql
```

### 2. 应用集成

```python
# 在 main.py 中
from user_profile_tag_api import setup_profile_system

# 应用启动时初始化
@app.on_event("startup")
async def startup():
    # 假设已有 db_pool
    setup_profile_system(app, db_pool)
```

### 3. 标签自动提取（情绪打卡示例）

```python
from user_profile_tag_api import auto_extract_tags_from_checkin

@app.post("/api/checkin")
async def create_checkin(data: CheckinData, user: User = Depends(get_current_user)):
    # 保存打卡数据
    checkin_id = await save_checkin(user.id, data)
    
    # 自动提取标签（后台异步执行）
    background_tasks.add_task(
        auto_extract_tags_from_checkin,
        user.id,
        data.dict(),
        str(checkin_id)
    )
    
    return {"ok": True, "id": checkin_id}
```

## API 端点

### 标签管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/profile/tags/categories` | 获取所有标签类别 |
| GET | `/api/profile/tags/sources` | 获取标签来源类型 |
| POST | `/api/profile/tags/extract` | 从文本提取标签（不存储） |
| POST | `/api/profile/tags/extract-and-store` | 提取并存储标签 |
| GET | `/api/profile/tags` | 获取用户标签列表 |
| GET | `/api/profile/tags/insights` | 获取标签洞察统计 |
| POST | `/api/profile/tags/manual` | 手动添加标签 |
| DELETE | `/api/profile/tags/{tag_name}` | 停用标签 |
| POST | `/api/profile/tags/{tag_name}/reactivate` | 重新激活标签 |

### 人格画像

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/profile/profile` | 获取人格画像 |
| POST | `/api/profile/profile` | 使用Formation向量生成画像 |
| GET | `/api/profile/summary` | 获取画像摘要 |
| GET | `/api/profile/archetypes` | 获取人格原型定义 |
| GET | `/api/profile/dominant-loops` | 获取主导循环定义 |
| GET | `/api/profile/trajectory-directions` | 获取轨迹方向定义 |

## 标签类别

### 1. 情绪维度
- **emotion_type**: 焦虑型、抑郁型、愤怒型、喜悦型、平静型、孤独型等
- **emotion_pattern**: 情绪波动型、情绪压抑型、情绪外放型、情绪稳定型等

### 2. 习惯维度
- **habit_type**: 灵修习惯、健康习惯、学习习惯、社交习惯等
- **habit_consistency**: 高度自律、间歇性努力、启动困难、容易放弃等
- **routine**: 早起型、夜猫子、规律作息、紊乱作息等

### 3. 性格维度
- **character_trait**: 谦逊型、自信型、谨慎型、冒险型、坚韧型等
- **formation_dim**: 对应8维状态向量的性格指标

### 4. 行为模式
- **behavior**: 逃避型、完美主义、拖延型、冲动型、控制型、讨好型等
- **response_style**: 问题解决型、情绪导向型、寻求支持型、独自承担型等
- **stress_reaction**: 压力下焦虑、压力下愤怒、压力下退缩、压力下奋进等

### 5. 生活领域
- **life_domain**: 工作领域、家庭领域、关系领域、健康领域、信仰领域等
- **life_stage**: 探索期、建立期、稳定期、转型期、危机期、恢复期等

### 6. 价值观与动机
- **value**: 安全感导向、成就导向、被爱导向、真实导向、成长导向等
- **motive**: 恐惧驱动、骄傲驱动、爱驱动、欲望驱动、责任驱动等

### 7. 关系与社交
- **relationship**: 亲密关系、亲子关系、职场关系、友谊关系等
- **attachment**: 安全依恋、焦虑依恋、回避依恋、混乱依恋等
- **social**: 外向型、内向型、小圈子型、广泛社交型等

### 8. 认知与灵性
- **cognitive**: 全或无思维、灾难化思维、理性分析型、直觉感受型等
- **spiritual**: 灵性干枯、被弃感、怀疑期、认罪悔改、感恩灵修等
- **decision**: 快速决策、拖延决策、寻求共识、分析型、直觉型等

## 人格原型识别

### Seeker (探索者)
- 必需标签: 探索期, 好奇
- 偏好标签: 寻求引导, 学习型, 迷茫型, 盼望型
- Formation特征: spiritual_clarity 0.4-0.7, humility 0.5-0.8

### Steward (管家)
- 必需标签: 责任驱动, 高度自律
- 偏好标签: 管家, 照顾者, 服务型, 谨慎型
- Formation特征: resilience 0.5-0.8, relational_health 0.5-0.8

### Warrior (战士)
- 必需标签: 坚韧型
- 偏好标签: 战士, 勇敢, 对抗, 压力下奋进
- Formation特征: resilience 0.6-0.9, fear_tendency 0.2-0.5

### Artist (艺术家)
- 必需标签: 艺术家, 创造
- 偏好标签: 敏感, 情感丰富, 直觉型, 喜悦型
- Formation特征: emotional_stability 0.3-0.6

### Thinker (思考者)
- 必需标签: 思考者, 理性分析型
- 偏好标签: 分析, 研究, 逻辑, 深度思考
- Formation特征: truth_alignment 0.6-0.9, humility 0.5-0.8

### Caregiver (照顾者)
- 必需标签: 爱驱动, 照顾者
- 偏好标签: 同理心, 滋养, 支持, 服务型
- Formation特征: relational_health 0.6-0.9

### Leader (领袖)
- 必需标签: 领袖, 果断
- 偏好标签: 影响, 承担责任, 快速决策, 自信型
- Formation特征: truth_alignment 0.5-0.8

### Contemplative (默观者)
- 必需标签: 默观者, 内省
- 偏好标签: 安静, 深度思考, 灵修习惯, 平静型
- Formation特征: spiritual_clarity 0.6-0.9, humility 0.6-0.9

### Activist (行动者)
- 必需标签: 行动者, 热情
- 偏好标签: 驱动, 追求改变, 使命, 兴奋型
- Formation特征: resilience 0.5-0.8, truth_alignment 0.5-0.8

### Diplomat (外交家)
- 必需标签: 外交家, 和谐
- 偏好标签: 调解, 避免冲突, 共识, 和平
- Formation特征: relational_health 0.6-0.9, fear_tendency 0.3-0.6

## 主导循环模式

### Fear-Control Loop (恐惧-控制循环)
```
fear → control → overwork → burnout → fear
```
- 识别标签: 恐惧驱动, 控制型, 焦虑型, 压力下退缩
- 成长焦点: 安全感建立, 信任练习, 放手训练
- 建议实践: 每日交托祷告, 小步冒险, 控制清单觉察

### Shame-Avoidance Loop (羞耻-逃避循环)
```
shame → avoidance → procrastination → anxiety
```
- 识别标签: 羞愧型, 逃避型, 羞耻感, 情绪压抑型
- 成长焦点: 自我接纳, 脆弱练习, 恩典内化
- 建议实践: 羞耻日记, 安全分享, 恩典默想

### Pride-Comparison Loop (骄傲-比较循环)
```
pride → comparison → anxiety → instability
```
- 识别标签: 骄傲驱动, 竞争型, 寻求认可型, 完美主义
- 成长焦点: 价值锚定, 感恩练习, 服务他人
- 建议实践: 每日感恩, 匿名服务, 价值清单

### Desire-Impulse Loop (欲望-冲动循环)
```
desire → impulsive_action → regret → desire
```
- 识别标签: 欲望驱动, 冲动型, 容易放弃, 拖延型
- 成长焦点: 延迟满足, 意图觉察, 替代满足
- 建议实践: STOP技巧, 欲望日记, 健康替代

### Truth-Stability Loop (真理-稳定循环 - 健康)
```
truth-facing → reflection → stability
```
- 识别标签: 灵性清晰, 情绪稳定型, 真实导向, 成长导向
- 成长焦点: 深化truth_alignment, 分享真理, 引导他人
- 建议实践: 真理默想, 智慧分享, 导师角色

## 权重计算算法

### 权重来源加成
```python
SOURCE_WEIGHT_BOOST = {
    'manual': 1.5,              # 手动添加权重最高
    'assessment': 1.3,          # 测评结果
    'formation': 1.2,           # Formation分析
    'decision_event': 1.1,      # 决策事件
    'emotion_checkin': 1.0,     # 情绪打卡
    'habit_execution': 0.9,     # 习惯执行
    'journal_entry': 0.9,       # 日记记录
    'chat_interaction': 0.8,    # 对话交互
    'prayer_request': 0.8,      # 祷告请求
    'behavior_regulation': 0.8, # 行为调节
    'system': 0.7,              # 系统推断
}
```

### 时间衰减
```python
RECENCY_DECAY = 0.92  # 7天衰减系数
decayed_weight = old_weight * (0.92 ^ (days_since_last / 7))
```

### 权重更新公式
```python
new_weight = min(decayed_weight + (confidence * source_boost * 0.5), MAX_WEIGHT)
```

## 使用示例

### 1. 从情绪打卡提取标签

```python
checkin_data = {
    'emotionLabel': '焦虑',
    'emotionQuery': '最近工作压力很大，感觉很焦虑',
    'scenarioCategory': '工作',
    'driverType': '恐惧',
    'mood': '疲惫',
}

tag_ids = extract_and_store_tags(
    user_id='user_001',
    data=checkin_data,
    source_type='emotion_checkin',
    event_id='checkin_123'
)
```

### 2. 生成人格画像

```python
formation_vector = {
    'humility': 0.6,
    'fear_tendency': 0.7,
    'pride_tendency': 0.4,
    'emotional_stability': 0.5,
    'truth_alignment': 0.6,
    'relational_health': 0.5,
    'resilience': 0.6,
    'spiritual_clarity': 0.5,
}

profile = generate_user_profile('user_001', formation_vector)
print(profile['personality_archetype'])  # 'warrior'
print(profile['dominant_loop'])          # 'fear_control_loop'
print(profile['profile_summary'])      # 你是一个warrior型的人...
```

### 3. 获取标签洞察

```python
insights = tag_store.get_tag_insights('user_001')
print(insights['category_distribution'])
print(insights['stable_tags'])
print(insights['emerging_tags'])
```

## 数据库表

### user_profile_tags (主标签表)
- 存储所有用户标签
- 支持权重、置信度、时间衰减
- JSONB字段存储上下文和历史

### tag_event_links (标签事件关联)
- 追踪标签的来源事件
- 支持标签溯源分析

### personality_profile_snapshots (画像快照)
- 存储人格画像历史版本
- 支持画像变化追踪
- 包含8维状态向量

### tag_weight_history (权重历史)
- 记录标签权重变化轨迹
- 支持趋势分析

### user_tag_statistics (统计汇总)
- 用户标签统计聚合
- 优化查询性能

## 维护任务

### 定期时间衰减
```sql
-- 每7天执行一次
SELECT cleanup_inactive_tags(90, 0.3);
```

### 刷新统计
```sql
-- 为特定用户刷新统计
SELECT refresh_user_tag_statistics('user_id');
```

### 归档旧快照
```sql
-- 只保留最近10个快照
SELECT archive_old_snapshots(10);
```

## 扩展开发

### 添加新标签类别

1. 在 `TagCategory` 枚举中添加新类别
2. 在 `TAG_PATTERNS` 中添加标签模式
3. 在数据库 `tag_category_metadata` 中添加元数据

### 自定义人格原型

1. 在 `PersonalityArchetype` 枚举中添加
2. 在 `ARCHETYPE_RULES` 中定义识别规则
3. 在 `_generate_narrative` 中添加叙事模板

### 集成新的数据源

```python
def extract_from_new_source(data: Dict) -> TagExtractionResult:
    tags = []
    # 自定义提取逻辑
    return TagExtractionResult(tags=tags, source_type='new_source')
```

## 注意事项

1. **隐私保护**: 标签数据属于敏感个人信息，确保符合隐私法规
2. **数据质量**: 自动提取的标签需要置信度过滤，建议阈值0.5+
3. **时间衰减**: 定期运行衰减任务，保持标签活跃度合理
4. **用户控制**: 允许用户查看、隐藏或删除自己的标签
5. **解释性**: 向用户说明标签的来源和意义

## 未来扩展

- [ ] 标签相似度推荐
- [ ] 群体人格画像分析
- [ ] 标签与经文/灵修内容关联
- [ ] 人格画像可视化仪表板
- [ ] 基于画像的个性化内容推荐
