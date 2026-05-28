-- ============================================================
-- 人格塑造、习惯养成、行为追踪系统 - 完整数据库表结构
-- 从 emotion-sphere 项目移植
-- 核心概念：三层动态电路保护机制 + 代币激励系统
-- ============================================================

-- ============================================================
-- 子系统一：行为调节系统 (Behavior Regulation System)
-- 基于福格行为模型 B=MAP (动机×能力×触发)
-- ============================================================

-- 1. 行为调节会话（动态行为工程追踪）
CREATE TABLE IF NOT EXISTS behavior_regulation_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 会话状态
    session_type    VARCHAR(50),  -- habit_task/emotion_regulation/crisis_intervention
    target_habit    VARCHAR(200),
    
    -- 实时系统状态评估 (Fogg模型: B=MAP)
    motivation_level    INTEGER CHECK (motivation_level BETWEEN 1 AND 10),
    ability_level       INTEGER CHECK (ability_level BETWEEN 1 AND 10),
    trigger_strength    INTEGER CHECK (trigger_strength BETWEEN 1 AND 10),
    
    -- 能量等级 (1-5, 用于状态机降级)
    energy_level        INTEGER CHECK (energy_level BETWEEN 1 AND 5),
    
    -- 执行阻力分析
    behavioral_resistance   INTEGER CHECK (behavioral_resistance BETWEEN 1 AND 10),
    cognitive_load          INTEGER CHECK (cognitive_load BETWEEN 1 AND 10),
    emotional_stability     INTEGER CHECK (emotional_stability BETWEEN 1 AND 10),
    attention_state         VARCHAR(20),  -- focused/distracted/scattered
    procrastination_level   INTEGER CHECK (procrastination_level BETWEEN 1 AND 10),
    
    -- 动态调节输出
    selected_tier           VARCHAR(10),  -- Green/Yellow/Red
    min_executable_action   TEXT,         -- 最小可执行动作
    task_downgrade          TEXT,         -- 降级版本
    emotional_compensation  TEXT,         -- 情绪补偿方式
    continuity_advice       TEXT,         -- 连续性建议
    
    -- 执行结果
    was_executed            BOOLEAN DEFAULT FALSE,
    execution_duration_seconds INTEGER,
    completion_percentage   INTEGER CHECK (completion_percentage BETWEEN 0 AND 100),
    
    -- 时间
    started_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at            TIMESTAMP,
    
    -- 防羞耻保护记录
    shame_mitigation_applied BOOLEAN DEFAULT FALSE,
    continuity_preserved    BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_behavior_sessions_user ON behavior_regulation_sessions(user_id);
CREATE INDEX idx_behavior_sessions_time ON behavior_regulation_sessions(started_at DESC);
CREATE INDEX idx_behavior_sessions_energy ON behavior_regulation_sessions(user_id, energy_level);

-- ============================================================
-- 子系统二：习惯状态机系统 (Habit State Machine System)
-- 基于 B.J. Fogg 福格行为模型
-- 三层动态电路保护：Green(完整) / Yellow(标准) / Red(熔断)
-- ============================================================

-- 2. 习惯状态机定义 (FSM - Causal Habit State Machine)
CREATE TABLE IF NOT EXISTS habit_state_machines (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 习惯定义
    habit_name          VARCHAR(200) NOT NULL,
    habit_description   TEXT,
    category            VARCHAR(50),  -- health/work/relationship/creative/spiritual
    
    -- 福格行为模型锚点
    deterministic_anchor    VARCHAR(200),  -- 硬编码锚点 (如"倒第一杯咖啡后")
    trigger_anchor_time     TIME,          -- 可选固定时间
    
    -- 三层状态机定义 (JSON存储各层配置)
    tier_green_config       JSONB,  -- 完整版
    tier_yellow_config      JSONB,  -- 标准版
    tier_red_config         JSONB,    -- 熔断版 (60秒原子动作)
    
    -- 代币系统配置
    token_green_yield       INTEGER DEFAULT 10,
    token_yellow_yield      INTEGER DEFAULT 5,
    token_red_yield         INTEGER DEFAULT 1,
    
    -- 状态
    is_active               BOOLEAN DEFAULT TRUE,
    current_streak_days     INTEGER DEFAULT 0,
    max_streak_days         INTEGER DEFAULT 0,
    total_executions        INTEGER DEFAULT 0,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_execution_at       TIMESTAMP
);

CREATE INDEX idx_habit_machines_user ON habit_state_machines(user_id);
CREATE INDEX idx_habit_machines_active ON habit_state_machines(user_id, is_active);

-- 3. 习惯执行日志 (状态机运行记录)
CREATE TABLE IF NOT EXISTS habit_execution_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    habit_id        UUID REFERENCES habit_state_machines(id) ON DELETE CASCADE,
    
    -- 执行时的系统状态
    energy_level_at_execution   INTEGER CHECK (energy_level_at_execution BETWEEN 1 AND 5),
    selected_tier               VARCHAR(10),  -- Green/Yellow/Red
    
    -- 执行详情
    action_taken                TEXT,       -- 实际执行的动作
    execution_duration_seconds  INTEGER,
    tokens_earned               INTEGER,
    
    -- 结果
    was_completed               BOOLEAN DEFAULT FALSE,
    completion_percentage       INTEGER CHECK (completion_percentage BETWEEN 0 AND 100),
    
    -- 熔断保护记录
    circuit_breaker_triggered   BOOLEAN DEFAULT FALSE,
    anti_guilt_message_shown    BOOLEAN DEFAULT FALSE,
    
    -- 遥测数据
    mood_before     INTEGER CHECK (mood_before BETWEEN 1 AND 10),
    mood_after      INTEGER CHECK (mood_after BETWEEN 1 AND 10),
    
    executed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_habit_logs_user ON habit_execution_logs(user_id);
CREATE INDEX idx_habit_logs_habit ON habit_execution_logs(habit_id);
CREATE INDEX idx_habit_logs_time ON habit_execution_logs(executed_at DESC);

-- ============================================================
-- 子系统三：代币激励系统 (Token Gamification System)
-- 游戏化信用账本
-- ============================================================

-- 4. 用户代币账本 (Gamified Credit Ledger)
CREATE TABLE IF NOT EXISTS user_token_ledgers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    current_balance     INTEGER DEFAULT 0,
    lifetime_earned     INTEGER DEFAULT 0,
    lifetime_spent      INTEGER DEFAULT 0,
    
    -- 统计
    green_tier_count    INTEGER DEFAULT 0,
    yellow_tier_count   INTEGER DEFAULT 0,
    red_tier_count      INTEGER DEFAULT 0,
    
    last_updated        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_token_ledger_user ON user_token_ledgers(user_id);

-- 5. 代币交易记录
CREATE TABLE IF NOT EXISTS token_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    transaction_type    VARCHAR(20),  -- earn/spend/penalty/adjustment
    amount              INTEGER,
    balance_after       INTEGER,
    
    -- 关联
    habit_id            UUID REFERENCES habit_state_machines(id) ON DELETE SET NULL,
    habit_log_id        UUID REFERENCES habit_execution_logs(id) ON DELETE SET NULL,
    
    description         TEXT,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_tx_user ON token_transactions(user_id);
CREATE INDEX idx_token_tx_time ON token_transactions(created_at DESC);

-- 为习惯表添加更新时间触发器
DROP TRIGGER IF EXISTS trg_habit_machines_updated ON habit_state_machines;
CREATE TRIGGER trg_habit_machines_updated 
BEFORE UPDATE ON habit_state_machines 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 子系统四：执行力边缘引导系统 (Edge Execution Intervention)
-- 实时微干预系统
-- ============================================================

-- 6. 执行力崩溃检测日志 (实时边缘监测)
CREATE TABLE IF NOT EXISTS execution_paralysis_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 检测到的崩溃信号
    paralysis_type  VARCHAR(50),  -- distraction/procrastination/anxiety_avoidance/emotional_collapse
    detected_signals JSONB[],     -- [{signal_type, description, intensity}]
    
    -- 原始任务上下文
    raw_backlog_task    TEXT,     -- 用户正在拖延的大任务
    edge_context        JSONB,    -- {hardware, location, time, battery, noise_level}
    
    -- 环境遥测
    tab_switch_count    INTEGER,  -- 检测到的高频切换次数
    idle_duration_seconds INTEGER, -- 无意义浏览/空闲时长
    window_thrashing    BOOLEAN DEFAULT FALSE,  -- 系统抖动标志
    
    -- 干预执行
    intervention_triggered  BOOLEAN DEFAULT FALSE,
    ignition_sequence_delivered TEXT, -- 2分钟点火序列内容
    user_responded      BOOLEAN DEFAULT FALSE,
    response_latency_seconds INTEGER, -- 用户响应延迟
    
    -- 结果
    ignition_completed  BOOLEAN DEFAULT FALSE,
    task_restarted      BOOLEAN DEFAULT FALSE,
    post_intervention_mood INTEGER CHECK (post_intervention_mood BETWEEN 1 AND 10),
    
    detected_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    intervened_at       TIMESTAMP,
    completed_at        TIMESTAMP
);

CREATE INDEX idx_paralysis_logs_user ON execution_paralysis_logs(user_id);
CREATE INDEX idx_paralysis_logs_time ON execution_paralysis_logs(detected_at DESC);
CREATE INDEX idx_paralysis_logs_type ON execution_paralysis_logs(paralysis_type);

-- 7. 微调度器会话 (实时微干预追踪)
CREATE TABLE IF NOT EXISTS micro_scheduler_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    paralysis_log_id UUID REFERENCES execution_paralysis_logs(id) ON DELETE SET NULL,
    
    -- 会话状态
    session_status  VARCHAR(20) DEFAULT 'active', -- active/paused/completed/abandoned
    
    -- 任务解耦链
    original_task       TEXT,       -- 原始大任务
    decoupled_chain     JSONB[],    -- [{step_id, action, duration_sec, completed}]
    current_step_index  INTEGER DEFAULT 0,
    
    -- 环境隔离配置
    context_isolation   JSONB,      -- {hidden_tabs, muted_notifications, focused_window}
    noise_floor_level   INTEGER CHECK (noise_floor_level BETWEEN 1 AND 10),
    
    -- 实时反馈
    telemetry_signals   JSONB[],    -- 用户反馈信号序列
    last_user_signal_at TIMESTAMP,
    
    -- 成果
    steps_completed     INTEGER DEFAULT 0,
    total_steps         INTEGER,
    micro_momentum_score INTEGER CHECK (micro_momentum_score BETWEEN 1 AND 100),
    
    started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_step_at        TIMESTAMP,
    completed_at        TIMESTAMP
);

CREATE INDEX idx_micro_scheduler_user ON micro_scheduler_sessions(user_id);
CREATE INDEX idx_micro_scheduler_status ON micro_scheduler_sessions(session_status);

-- 8. 执行意图模板库 (Implementation Intentions Library)
CREATE TABLE IF NOT EXISTS implementation_intentions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 意图定义 (If-Then 格式)
    intention_name      VARCHAR(200),
    if_trigger          TEXT,       -- "如果..." (环境锚点)
    then_action         TEXT,       -- "那么..." (原子动作)
    
    -- 上下文匹配条件
    applicable_contexts JSONB,      -- [{time_range, location, energy_level, device_type}]
    
    -- 效果统计
    usage_count         INTEGER DEFAULT 0,
    success_rate        INTEGER CHECK (success_rate BETWEEN 0 AND 100),
    
    -- 状态
    is_template         BOOLEAN DEFAULT FALSE,  -- 是否系统模板
    is_active           BOOLEAN DEFAULT TRUE,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at        TIMESTAMP
);

CREATE INDEX idx_intentions_user ON implementation_intentions(user_id);
CREATE INDEX idx_intentions_template ON implementation_intentions(is_template);

-- ============================================================
-- 视图与统计
-- ============================================================

-- 9. 用户习惯执行仪表盘视图
CREATE OR REPLACE VIEW user_habit_dashboard AS
SELECT 
    u.id as user_id,
    
    -- 活跃习惯数
    (SELECT COUNT(*) FROM habit_state_machines 
     WHERE user_id = u.id AND is_active = TRUE) as active_habits,
    
    -- 今日执行数
    (SELECT COUNT(*) FROM habit_execution_logs 
     WHERE user_id = u.id AND executed_at >= CURRENT_DATE) as today_executions,
    
    -- 当前连胜天数 (取最大)
    (SELECT MAX(current_streak_days) FROM habit_state_machines 
     WHERE user_id = u.id AND is_active = TRUE) as max_current_streak,
    
    -- 代币余额
    (SELECT current_balance FROM user_token_ledgers 
     WHERE user_id = u.id) as token_balance,
    
    -- 最近执行的习惯
    (SELECT habit_name FROM habit_execution_logs hel
     JOIN habit_state_machines hsm ON hel.habit_id = hsm.id
     WHERE hel.user_id = u.id 
     ORDER BY hel.executed_at DESC LIMIT 1) as last_habit_name,
    
    -- 熔断保护触发次数（本周）
    (SELECT COUNT(*) FROM habit_execution_logs 
     WHERE user_id = u.id 
     AND circuit_breaker_triggered = TRUE
     AND executed_at >= CURRENT_DATE - INTERVAL '7 days') as circuit_breaker_count,

    -- 各层级执行统计
    (SELECT COUNT(*) FROM habit_execution_logs 
     WHERE user_id = u.id AND selected_tier = 'Green') as green_executions,
    (SELECT COUNT(*) FROM habit_execution_logs 
     WHERE user_id = u.id AND selected_tier = 'Yellow') as yellow_executions,
    (SELECT COUNT(*) FROM habit_execution_logs 
     WHERE user_id = u.id AND selected_tier = 'Red') as red_executions,
     
    -- 连续执行天数
    (SELECT COUNT(DISTINCT DATE(executed_at)) FROM habit_execution_logs 
     WHERE user_id = u.id 
     AND executed_at >= CURRENT_DATE - INTERVAL '30 days') as active_days_30

FROM users u;

-- 10. 习惯执行趋势视图 (近30天)
CREATE OR REPLACE VIEW habit_execution_trends AS
SELECT 
    user_id,
    DATE(executed_at) as execution_date,
    COUNT(*) as total_executions,
    SUM(CASE WHEN selected_tier = 'Green' THEN 1 ELSE 0 END) as green_count,
    SUM(CASE WHEN selected_tier = 'Yellow' THEN 1 ELSE 0 END) as yellow_count,
    SUM(CASE WHEN selected_tier = 'Red' THEN 1 ELSE 0 END) as red_count,
    SUM(CASE WHEN was_completed THEN 1 ELSE 0 END) as completed_count,
    SUM(tokens_earned) as tokens_earned_day,
    AVG(mood_after - mood_before) as mood_delta_avg
FROM habit_execution_logs
WHERE executed_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY user_id, DATE(executed_at)
ORDER BY execution_date DESC;

-- ============================================================
-- 版本标记
-- ============================================================
-- 移植来源: emotion-sphere 项目
-- 移植日期: 2025-05-19
-- 核心概念: 三层动态电路保护 + 代币激励 + 行为工程学
-- 理论基础: B.J. Fogg 福格行为模型 B=MAP (行为=动机×能力×触发)
-- ============================================================
