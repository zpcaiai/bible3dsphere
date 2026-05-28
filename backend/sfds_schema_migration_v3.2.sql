-- ============================================================================
-- SFDS Schema Migration v3.2 - Add 12-dimension State Snapshot to Decision Events
-- ============================================================================
-- 问题：decision_support.py _create_decision_event_sync 尝试直接在 sfds_decision_events
--       中存储 12 维度状态快照，但表结构缺少这些字段
-- 解决：添加缺失的 12 维度字段到 sfds_decision_events 表

-- 添加基础 5 维度字段（如果尚不存在）
DO $$
BEGIN
    -- stress_level
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='stress_level') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- anxiety_level
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='anxiety_level') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN anxiety_level INTEGER CHECK (anxiety_level BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- fatigue_level
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='fatigue_level') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN fatigue_level INTEGER CHECK (fatigue_level BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- spiritual_dryness
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='spiritual_dryness') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN spiritual_dryness INTEGER CHECK (spiritual_dryness BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- emotional_stability
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='emotional_stability') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN emotional_stability INTEGER CHECK (emotional_stability BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- 扩展 7 维度字段
    
    -- physical_health
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='physical_health') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN physical_health INTEGER CHECK (physical_health BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- sleep_quality
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='sleep_quality') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- social_connection
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='social_connection') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN social_connection INTEGER CHECK (social_connection BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- financial_pressure
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='financial_pressure') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN financial_pressure INTEGER CHECK (financial_pressure BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- cognitive_clarity
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='cognitive_clarity') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN cognitive_clarity INTEGER CHECK (cognitive_clarity BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- identity_confusion
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='identity_confusion') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN identity_confusion INTEGER CHECK (identity_confusion BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- moral_tension
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='moral_tension') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN moral_tension INTEGER CHECK (moral_tension BETWEEN 0 AND 10) DEFAULT 5;
    END IF;

    -- emotion_logs JSONB 字段（存储情绪日志数组）
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='emotion_logs') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN emotion_logs JSONB DEFAULT '[]'::jsonb;
    END IF;

    -- status 字段（如果不存在，用于兼容旧代码）
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='status') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN status VARCHAR(20) DEFAULT 'analyzing' 
            CHECK (status IN ('analyzing', 'guided', 'decided', 'reviewed', 'archived'));
    END IF;

END $$;

-- 添加注释说明
COMMENT ON COLUMN sfds_decision_events.stress_level IS '压力水平 0-10：外部要求与内部资源的差距';
COMMENT ON COLUMN sfds_decision_events.anxiety_level IS '焦虑水平 0-10：对未来不确定的担忧程度';
COMMENT ON COLUMN sfds_decision_events.fatigue_level IS '疲劳水平 0-10：身心能量耗竭的感受';
COMMENT ON COLUMN sfds_decision_events.spiritual_dryness IS '灵性干涸 0-10：与神连接的感受减弱';
COMMENT ON COLUMN sfds_decision_events.emotional_stability IS '情绪稳定性 0-10：情绪波动的可控程度';
COMMENT ON COLUMN sfds_decision_events.physical_health IS '身体健康 0-10：身体状况与精力水平';
COMMENT ON COLUMN sfds_decision_events.sleep_quality IS '睡眠质量 0-10：休息恢复与睡眠满意度';
COMMENT ON COLUMN sfds_decision_events.social_connection IS '社交连接 0-10：关系网络与支持系统';
COMMENT ON COLUMN sfds_decision_events.financial_pressure IS '财务压力 0-10：经济焦虑与资源担忧';
COMMENT ON COLUMN sfds_decision_events.cognitive_clarity IS '认知清晰 0-10：思维清晰度与专注力';
COMMENT ON COLUMN sfds_decision_events.identity_confusion IS '身份困惑 0-10：自我认知与定位迷茫';
COMMENT ON COLUMN sfds_decision_events.moral_tension IS '道德张力 0-10：价值观冲突与良心挣扎';
COMMENT ON COLUMN sfds_decision_events.emotion_logs IS '情绪日志数组，JSONB格式存储';
COMMENT ON COLUMN sfds_decision_events.status IS '决策处理状态：analyzing/guided/decided/reviewed/archived';

-- 添加复合索引优化查询
CREATE INDEX IF NOT EXISTS idx_decision_events_user_status 
    ON sfds_decision_events(user_id, status) 
    WHERE status IN ('analyzing', 'guided', 'decided');

CREATE INDEX IF NOT EXISTS idx_decision_events_category 
    ON sfds_decision_events(category) 
    WHERE category IS NOT NULL;

-- ============================================================================
-- Migration Complete
-- ============================================================================
SELECT 'Migration v3.2 completed: Added 12-dimension state snapshot columns to sfds_decision_events' AS result;
