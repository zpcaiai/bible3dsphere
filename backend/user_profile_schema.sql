-- ============================================================================
-- 用户人格画像标签系统数据库Schema
-- User Personality Profile Tag System Schema
-- 
-- 模块:
-- 1. 用户标签主表
-- 2. 标签事件关联表
-- 3. 人格画像快照表
-- 4. 标签时间序列表
-- 5. 视图和索引
-- ============================================================================

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

-- ============================================================================
-- 1. 用户标签主表
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_profile_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基本信息
    user_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    tag_category TEXT NOT NULL,
    tag_subcategory TEXT,
    
    -- 来源和置信度
    source TEXT NOT NULL,                    -- emotion_checkin, decision_event, manual, etc.
    confidence REAL DEFAULT 0.5 CHECK (confidence BETWEEN 0.0 AND 1.0),
    
    -- 权重系统
    weight REAL DEFAULT 1.0 CHECK (weight BETWEEN 0.0 AND 10.0),
    
    -- 时间追踪
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1,
    
    -- 历史权重变化（用于趋势分析）
    history_weights JSONB DEFAULT '[]',      -- [[timestamp, weight], ...]
    
    -- 上下文信息
    context_snapshot JSONB DEFAULT '{}',     -- 标签产生的上下文
    related_emotions JSONB DEFAULT '[]',     -- 相关情绪标签
    related_decisions JSONB DEFAULT '[]',    -- 相关决策ID
    related_habits JSONB DEFAULT '[]',       -- 相关习惯ID
    source_events JSONB DEFAULT '[]',        -- 来源事件引用 ["type:id", ...]
    
    -- 状态管理
    is_active BOOLEAN DEFAULT TRUE,
    is_manually_added BOOLEAN DEFAULT FALSE,
    is_system_core BOOLEAN DEFAULT FALSE,    -- 是否为核心标签（不易删除）
    
    -- 唯一约束：每个用户的标签名称唯一
    UNIQUE(user_id, tag_name)
);

-- 标签表索引
CREATE INDEX IF NOT EXISTS idx_profile_tags_user_id 
    ON user_profile_tags(user_id);

CREATE INDEX IF NOT EXISTS idx_profile_tags_user_active 
    ON user_profile_tags(user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_profile_tags_category 
    ON user_profile_tags(tag_category);

CREATE INDEX IF NOT EXISTS idx_profile_tags_user_category 
    ON user_profile_tags(user_id, tag_category);

CREATE INDEX IF NOT EXISTS idx_profile_tags_weight 
    ON user_profile_tags(weight DESC);

CREATE INDEX IF NOT EXISTS idx_profile_tags_user_weight 
    ON user_profile_tags(user_id, weight DESC);

CREATE INDEX IF NOT EXISTS idx_profile_tags_source 
    ON user_profile_tags(source);

CREATE INDEX IF NOT EXISTS idx_profile_tags_last_seen 
    ON user_profile_tags(last_seen_at DESC);

-- 模糊搜索索引（标签名称）
CREATE INDEX IF NOT EXISTS idx_profile_tags_name_trgm 
    ON user_profile_tags USING gin (tag_name gin_trgm_ops);

-- ============================================================================
-- 2. 标签事件关联表
-- ============================================================================

CREATE TABLE IF NOT EXISTS tag_event_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id UUID NOT NULL REFERENCES user_profile_tags(id) ON DELETE CASCADE,
    
    -- 事件信息
    event_type TEXT NOT NULL,                -- emotion_checkin, decision_event, etc.
    event_id TEXT NOT NULL,                  -- 关联的事件ID
    event_data JSONB DEFAULT '{}',           -- 事件数据快照
    
    -- 提取的上下文
    extracted_keywords TEXT[],               -- 提取时匹配的关键词
    extraction_confidence REAL DEFAULT 0.5,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tag_event_links_tag_id 
    ON tag_event_links(tag_id);

CREATE INDEX IF NOT EXISTS idx_tag_event_links_event 
    ON tag_event_links(event_type, event_id);

CREATE INDEX IF NOT EXISTS idx_tag_event_links_created 
    ON tag_event_links(created_at DESC);

-- ============================================================================
-- 3. 人格画像快照表
-- ============================================================================

CREATE TABLE IF NOT EXISTS personality_profile_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    
    -- 生成时间
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 人格原型和模式
    personality_archetype TEXT,              -- seeker, steward, warrior, etc.
    dominant_loop TEXT,                      -- fear_control_loop, truth_stability_loop, etc.
    trajectory_direction TEXT,               -- stabilizing, fragmenting, etc.
    
    -- 8维性格状态向量（Formation State Vector）
    humility_score REAL CHECK (humility_score BETWEEN 0.05 AND 0.95),
    fear_tendency_score REAL CHECK (fear_tendency_score BETWEEN 0.05 AND 0.95),
    pride_tendency_score REAL CHECK (pride_tendency_score BETWEEN 0.05 AND 0.95),
    emotional_stability_score REAL CHECK (emotional_stability_score BETWEEN 0.05 AND 0.95),
    truth_alignment_score REAL CHECK (truth_alignment_score BETWEEN 0.05 AND 0.95),
    relational_health_score REAL CHECK (relational_health_score BETWEEN 0.05 AND 0.95),
    resilience_score REAL CHECK (resilience_score BETWEEN 0.05 AND 0.95),
    spiritual_clarity_score REAL CHECK (spiritual_clarity_score BETWEEN 0.05 AND 0.95),
    
    -- 状态向量元数据
    vector_confidence REAL DEFAULT 0.5,
    vector_data_points INTEGER DEFAULT 0,
    
    -- 标签聚合（快照时）
    top_emotion_tags JSONB DEFAULT '[]',
    top_behavior_tags JSONB DEFAULT '[]',
    top_value_tags JSONB DEFAULT '[]',
    top_relationship_tags JSONB DEFAULT '[]',
    life_dominant_domains JSONB DEFAULT '[]',
    
    -- 模式识别
    recurring_patterns JSONB DEFAULT '[]',
    growth_indicators JSONB DEFAULT '[]',
    risk_factors JSONB DEFAULT '[]',
    
    -- 时间维度指标
    profile_stability REAL DEFAULT 0.5,      -- 画像稳定性 0-1
    change_velocity REAL DEFAULT 0.0,        -- 变化速度
    trend_direction TEXT DEFAULT 'stable',     -- improving|declining|stable|volatile
    
    -- 叙事描述
    profile_summary TEXT,
    core_narrative TEXT,
    growth_pathway TEXT,
    
    -- 版本控制
    version INTEGER DEFAULT 1,
    is_current BOOLEAN DEFAULT TRUE,
    
    -- 计算元数据
    calculation_method TEXT DEFAULT 'automatic',  -- automatic|manual|assessment
    included_decision_ids UUID[],
    included_checkin_ids UUID[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 画像快照索引
CREATE INDEX IF NOT EXISTS idx_profile_snapshots_user_id 
    ON personality_profile_snapshots(user_id);

CREATE INDEX IF NOT EXISTS idx_profile_snapshots_user_current 
    ON personality_profile_snapshots(user_id, is_current) WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS idx_profile_snapshots_generated 
    ON personality_profile_snapshots(generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_profile_snapshots_archetype 
    ON personality_profile_snapshots(personality_archetype);

CREATE INDEX IF NOT EXISTS idx_profile_snapshots_loop 
    ON personality_profile_snapshots(dominant_loop);

-- ============================================================================
-- 4. 标签时间序列表（用于追踪标签权重变化）
-- ============================================================================

CREATE TABLE IF NOT EXISTS tag_weight_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id UUID NOT NULL REFERENCES user_profile_tags(id) ON DELETE CASCADE,
    
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    weight REAL NOT NULL,
    
    -- 变化原因
    change_reason TEXT,                      -- new_occurrence, decay, boost, etc.
    source_event_type TEXT,
    source_event_id TEXT,
    
    -- 当时的状态
    occurrence_count_at_record INTEGER,
    confidence_at_record REAL
);

CREATE INDEX IF NOT EXISTS idx_tag_weight_history_tag_id 
    ON tag_weight_history(tag_id);

CREATE INDEX IF NOT EXISTS idx_tag_weight_history_recorded 
    ON tag_weight_history(recorded_at DESC);

-- ============================================================================
-- 5. 标签统计汇总表（物化视图）
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_tag_statistics (
    user_id TEXT PRIMARY KEY,
    
    -- 统计信息
    total_tags INTEGER DEFAULT 0,
    active_tags INTEGER DEFAULT 0,
    manually_added_tags INTEGER DEFAULT 0,
    
    -- 分类统计
    emotion_tags_count INTEGER DEFAULT 0,
    behavior_tags_count INTEGER DEFAULT 0,
    value_tags_count INTEGER DEFAULT 0,
    relationship_tags_count INTEGER DEFAULT 0,
    
    -- 权重统计
    average_weight REAL DEFAULT 0,
    max_weight REAL DEFAULT 0,
    
    -- 时间统计
    oldest_tag_at TIMESTAMP WITH TIME ZONE,
    newest_tag_at TIMESTAMP WITH TIME ZONE,
    
    -- 活跃标签TOP5
    top_tags JSONB DEFAULT '[]',
    
    -- 更新时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tag_stats_user_id 
    ON user_tag_statistics(user_id);

CREATE INDEX IF NOT EXISTS idx_tag_stats_updated 
    ON user_tag_statistics(updated_at DESC);

-- ============================================================================
-- 6. 标签相似度矩阵（用于推荐和相关性分析）
-- ============================================================================

CREATE TABLE IF NOT EXISTS tag_similarity_matrix (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    
    tag_a TEXT NOT NULL,
    tag_b TEXT NOT NULL,
    
    -- 相似度分数（共现频率、上下文相似度等）
    co_occurrence_score REAL DEFAULT 0,
    context_similarity REAL DEFAULT 0,
    temporal_proximity REAL DEFAULT 0,
    
    -- 综合相似度
    overall_similarity REAL DEFAULT 0,
    
    -- 共同出现的事件
    common_events_count INTEGER DEFAULT 0,
    common_events JSONB DEFAULT '[]',
    
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, tag_a, tag_b)
);

CREATE INDEX IF NOT EXISTS idx_tag_similarity_user 
    ON tag_similarity_matrix(user_id);

CREATE INDEX IF NOT EXISTS idx_tag_similarity_pair 
    ON tag_similarity_matrix(tag_a, tag_b);

CREATE INDEX IF NOT EXISTS idx_tag_similarity_score 
    ON tag_similarity_matrix(overall_similarity DESC);

-- ============================================================================
-- 7. 触发器函数
-- ============================================================================

-- 自动更新标签最后 seen 时间
CREATE OR REPLACE FUNCTION update_tag_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_seen_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 当标签权重变化时记录历史
CREATE OR REPLACE FUNCTION record_tag_weight_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.weight IS DISTINCT FROM NEW.weight THEN
        INSERT INTO tag_weight_history (
            tag_id, recorded_at, weight, 
            occurrence_count_at_record, confidence_at_record
        ) VALUES (
            NEW.id, NOW(), NEW.weight,
            NEW.occurrence_count, NEW.confidence
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 应用触发器
DROP TRIGGER IF EXISTS tag_weight_change_trigger ON user_profile_tags;
CREATE TRIGGER tag_weight_change_trigger
    AFTER UPDATE ON user_profile_tags
    FOR EACH ROW
    EXECUTE FUNCTION record_tag_weight_change();

-- ============================================================================
-- 8. 物化视图刷新函数
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_user_tag_statistics(p_user_id TEXT)
RETURNS VOID AS $$
DECLARE
    v_total INTEGER;
    v_active INTEGER;
    v_manual INTEGER;
    v_avg_weight REAL;
    v_max_weight REAL;
    v_oldest TIMESTAMP WITH TIME ZONE;
    v_newest TIMESTAMP WITH TIME ZONE;
    v_top_tags JSONB;
BEGIN
    -- 计算统计值
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE is_active = TRUE),
        COUNT(*) FILTER (WHERE is_manually_added = TRUE),
        AVG(weight),
        MAX(weight),
        MIN(first_seen_at),
        MAX(last_seen_at)
    INTO v_total, v_active, v_manual, v_avg_weight, v_max_weight, v_oldest, v_newest
    FROM user_profile_tags
    WHERE user_id = p_user_id;
    
    -- 获取TOP标签
    SELECT jsonb_agg(sub)
    INTO v_top_tags
    FROM (
        SELECT jsonb_build_object(
            'name', tag_name,
            'category', tag_category,
            'weight', weight,
            'occurrences', occurrence_count
        ) as sub
        FROM user_profile_tags
        WHERE user_id = p_user_id AND is_active = TRUE
        ORDER BY weight DESC
        LIMIT 5
    ) t;
    
    -- 分类统计
    INSERT INTO user_tag_statistics (
        user_id, total_tags, active_tags, manually_added_tags,
        average_weight, max_weight, 
        oldest_tag_at, newest_tag_at, top_tags, updated_at
    ) VALUES (
        p_user_id, v_total, v_active, v_manual,
        COALESCE(v_avg_weight, 0), COALESCE(v_max_weight, 0),
        v_oldest, v_newest, COALESCE(v_top_tags, '[]'::jsonb), NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        total_tags = EXCLUDED.total_tags,
        active_tags = EXCLUDED.active_tags,
        manually_added_tags = EXCLUDED.manually_added_tags,
        average_weight = EXCLUDED.average_weight,
        max_weight = EXCLUDED.max_weight,
        oldest_tag_at = EXCLUDED.oldest_tag_at,
        newest_tag_at = EXCLUDED.newest_tag_at,
        top_tags = EXCLUDED.top_tags,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. 视图定义
-- ============================================================================

-- 活跃用户标签视图
CREATE OR REPLACE VIEW v_active_user_tags AS
SELECT 
    user_id,
    tag_name,
    tag_category,
    weight,
    confidence,
    occurrence_count,
    last_seen_at,
    CASE 
        WHEN weight >= 6 AND occurrence_count >= 5 THEN 'core'
        WHEN weight >= 4 AND occurrence_count >= 3 THEN 'stable'
        WHEN weight >= 2 THEN 'emerging'
        ELSE 'fading'
    END as tag_stability
FROM user_profile_tags
WHERE is_active = TRUE;

-- 用户标签分布视图
CREATE OR REPLACE VIEW v_user_tag_distribution AS
SELECT 
    user_id,
    tag_category,
    COUNT(*) as tag_count,
    AVG(weight) as avg_weight,
    MAX(weight) as max_weight,
    SUM(occurrence_count) as total_occurrences,
    MAX(last_seen_at) as last_activity
FROM user_profile_tags
WHERE is_active = TRUE
GROUP BY user_id, tag_category;

-- 人格画像当前版本视图
CREATE OR REPLACE VIEW v_current_personality_profiles AS
SELECT *
FROM personality_profile_snapshots
WHERE is_current = TRUE;

-- 标签共现视图（用于相似度分析）
CREATE OR REPLACE VIEW v_tag_cooccurrence AS
WITH user_tags AS (
    SELECT user_id, tag_name, UNNEST(source_events) as event_ref
    FROM user_profile_tags
    WHERE is_active = TRUE AND array_length(source_events, 1) > 0
)
SELECT 
    a.user_id,
    a.tag_name as tag_a,
    b.tag_name as tag_b,
    COUNT(*) as cooccurrence_count
FROM user_tags a
JOIN user_tags b ON a.user_id = b.user_id 
    AND a.event_ref = b.event_ref 
    AND a.tag_name < b.tag_name  -- 避免重复
GROUP BY a.user_id, a.tag_name, b.tag_name;

-- ============================================================================
-- 10. 数据清理和维护函数
-- ============================================================================

-- 清理过期低权重标签
CREATE OR REPLACE FUNCTION cleanup_inactive_tags(
    p_inactive_days INTEGER DEFAULT 90,
    p_min_weight REAL DEFAULT 0.3
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    UPDATE user_profile_tags
    SET is_active = FALSE
    WHERE last_seen_at < NOW() - INTERVAL '1 day' * p_inactive_days
    AND weight < p_min_weight
    AND is_system_core = FALSE;
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

-- 归档旧画像快照
CREATE OR REPLACE FUNCTION archive_old_snapshots(
    p_keep_count INTEGER DEFAULT 10
)
RETURNS INTEGER AS $$
DECLARE
    v_archived INTEGER;
BEGIN
    WITH ranked_snapshots AS (
        SELECT id, user_id,
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY generated_at DESC) as rn
        FROM personality_profile_snapshots
        WHERE is_current = FALSE
    )
    UPDATE personality_profile_snapshots
    SET is_current = FALSE  -- 标记为已归档
    WHERE id IN (
        SELECT id FROM ranked_snapshots WHERE rn > p_keep_count
    );
    
    GET DIAGNOSTICS v_archived = ROW_COUNT;
    RETURN v_archived;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 11. 初始化数据（可选）
-- ============================================================================

-- 标签类别枚举映射表（供查询使用）
CREATE TABLE IF NOT EXISTS tag_category_metadata (
    category TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT,
    display_order INTEGER,
    color_code TEXT
);

INSERT INTO tag_category_metadata (category, display_name, description, display_order, color_code)
VALUES 
    ('emotion_type', '情绪类型', '用户常体验的情绪状态', 1, '#FF6B6B'),
    ('emotion_pattern', '情绪模式', '情绪的变化规律', 2, '#FF8787'),
    ('habit_type', '习惯类型', '日常习惯分类', 3, '#4ECDC4'),
    ('habit_consistency', '习惯坚持度', '维持习惯的稳定性', 4, '#45B7AA'),
    ('character_trait', '性格特质', '基于Formation Vector的性格', 5, '#96CEB4'),
    ('behavior', '行为模式', '典型行为反应', 6, '#FFEAA7'),
    ('response_style', '应对风格', '面对压力的方式', 7, '#FDCB6E'),
    ('stress_reaction', '压力反应', '压力下的反应模式', 8, '#E17055'),
    ('life_domain', '生活领域', '关注的生命领域', 9, '#74B9FF'),
    ('life_stage', '人生阶段', '当前人生阶段', 10, '#0984E3'),
    ('value', '价值观', '核心价值优先级', 11, '#A29BFE'),
    ('motive', '动机类型', '驱动行为的动机', 12, '#6C5CE7'),
    ('relationship', '关系类型', '关系中的表现模式', 13, '#FD79A8'),
    ('attachment', '依恋风格', '人际关系依恋模式', 14, '#E84393'),
    ('social', '社交偏好', '社交互动偏好', 15, '#FDCB6E'),
    ('cognitive', '认知风格', '思考和信息处理', 16, '#00B894'),
    ('spiritual', '灵性状态', '灵性生命状态', 17, '#00CEC9'),
    ('decision', '决策风格', '做决定时的风格', 18, '#E17055')
ON CONFLICT (category) DO NOTHING;

-- ============================================================================
-- 12. 权限设置（根据需要调整）
-- ============================================================================

-- 注释掉的权限设置，根据需要取消注释并调整
-- GRANT SELECT, INSERT, UPDATE ON user_profile_tags TO app_role;
-- GRANT SELECT, INSERT ON tag_event_links TO app_role;
-- GRANT SELECT, INSERT ON personality_profile_snapshots TO app_role;
-- GRANT SELECT ON v_active_user_tags TO app_role;
-- GRANT SELECT ON v_user_tag_distribution TO app_role;
-- GRANT SELECT ON v_current_personality_profiles TO app_role;
