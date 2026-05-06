-- ============================================
-- 圣经3D球数据库表结构设计
-- 模块: 主日、灵修、分享墙、祷告、日记
-- PostgreSQL 兼容
-- ============================================

-- ============================================
-- 1. 主日模块 (Sunday)
-- ============================================

-- 主日礼拜/活动表
CREATE TABLE IF NOT EXISTS sunday_services (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,           -- 礼拜主题
    service_date    DATE NOT NULL,                   -- 礼拜日期
    service_time    TIME DEFAULT '10:00:00',         -- 礼拜时间
    speaker         VARCHAR(100) DEFAULT '',         -- 讲道人
    scripture       TEXT DEFAULT '',                -- 经文
    theme           VARCHAR(200) DEFAULT '',         -- 主题
    description     TEXT DEFAULT '',                -- 描述/简介
    location        VARCHAR(200) DEFAULT '',         -- 地点
    max_capacity    INTEGER DEFAULT 200,            -- 最大容量
    status          VARCHAR(20) DEFAULT 'upcoming',  -- upcoming/active/completed/cancelled
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sunday_services_date ON sunday_services(service_date);
CREATE INDEX IF NOT EXISTS idx_sunday_services_status ON sunday_services(status);

-- 主日签到/参与记录表
CREATE TABLE IF NOT EXISTS sunday_attendance (
    id              SERIAL PRIMARY KEY,
    service_id      INTEGER NOT NULL REFERENCES sunday_services(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,           -- 参与者邮箱
    nickname        VARCHAR(100) DEFAULT '',         -- 昵称
    check_in_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seat_number     VARCHAR(20) DEFAULT '',          -- 座位号
    notes           TEXT DEFAULT '',                -- 备注
    feedback        TEXT DEFAULT '',                -- 反馈/感想
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service_id, email)                        -- 每个用户每场只能签到一次
);

CREATE INDEX IF NOT EXISTS idx_sunday_attendance_service ON sunday_attendance(service_id);
CREATE INDEX IF NOT EXISTS idx_sunday_attendance_email ON sunday_attendance(email);
CREATE INDEX IF NOT EXISTS idx_sunday_attendance_checkin ON sunday_attendance(check_in_time);

-- 主日奉献记录表
CREATE TABLE IF NOT EXISTS sunday_offerings (
    id              SERIAL PRIMARY KEY,
    service_id      INTEGER REFERENCES sunday_services(id) ON DELETE SET NULL,
    email           VARCHAR(255) DEFAULT '',           -- 奉献者（可选匿名）
    amount          DECIMAL(10,2) NOT NULL,           -- 奉献金额
    offering_type   VARCHAR(50) DEFAULT 'tithe',    -- tithe/offerings/special/missions
    note            VARCHAR(200) DEFAULT '',           -- 备注
    is_anonymous    BOOLEAN DEFAULT FALSE,            -- 是否匿名
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sunday_offerings_service ON sunday_offerings(service_id);
CREATE INDEX IF NOT EXISTS idx_sunday_offerings_email ON sunday_offerings(email);

-- ============================================
-- 2. 灵修模块 (Devotion) - 已有表优化版
-- ============================================

-- 灵修计划/模板表
CREATE TABLE IF NOT EXISTS devotion_plans (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,           -- 计划名称
    description     TEXT DEFAULT '',                -- 描述
    duration_days   INTEGER DEFAULT 30,              -- 持续天数
    created_by      VARCHAR(255) DEFAULT '',         -- 创建者
    is_public       BOOLEAN DEFAULT TRUE,             -- 是否公开
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 灵修日记表 (基于现有表增强)
CREATE TABLE IF NOT EXISTS devotion_journals (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,             -- 用户邮箱
    plan_id         INTEGER REFERENCES devotion_plans(id) ON DELETE SET NULL,
    
    -- 基本信息
    journal_date    DATE NOT NULL,                    -- 灵修日期
    title           VARCHAR(200) DEFAULT '',           -- 标题
    
    -- 经文与内容 (SOAP 方法)
    scripture_ref   VARCHAR(200) DEFAULT '',           -- 经文引用
    scripture_text  TEXT DEFAULT '',                  -- 经文内容
    
    observation     TEXT DEFAULT '',                  -- 观察 (O)
    reflection      TEXT DEFAULT '',                  -- 反思 (R)
    application     TEXT DEFAULT '',                  -- 应用 (A)
    prayer          TEXT DEFAULT '',                  -- 祷告 (P)
    
    -- 情感与状态
    mood            VARCHAR(50) DEFAULT '',            -- 心情
    emotion_tags    TEXT[] DEFAULT '{}',              -- 情感标签数组
    spiritual_state INTEGER CHECK (spiritual_state BETWEEN 1 AND 5), -- 灵命状态 1-5
    
    -- 多媒体支持
    images          TEXT[] DEFAULT '{}',              -- 图片 URLs
    voice_note_url  VARCHAR(500) DEFAULT '',           -- 语音笔记
    
    -- 分享设置
    is_shared       BOOLEAN DEFAULT FALSE,            -- 是否分享到分享墙
    share_privacy   VARCHAR(20) DEFAULT 'private',    -- private/friends/public
    
    -- 互动统计
    likes_count     INTEGER DEFAULT 0,
    comments_count  INTEGER DEFAULT 0,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(email, journal_date)                       -- 每天只能一篇灵修日记
);

CREATE INDEX IF NOT EXISTS idx_devotion_journals_email ON devotion_journals(email);
CREATE INDEX IF NOT EXISTS idx_devotion_journals_date ON devotion_journals(journal_date);
CREATE INDEX IF NOT EXISTS idx_devotion_journals_plan ON devotion_journals(plan_id);
CREATE INDEX IF NOT EXISTS idx_devotion_journals_shared ON devotion_journals(is_shared) WHERE is_shared = TRUE;

-- 灵修日记评论表
CREATE TABLE IF NOT EXISTS devotion_journal_comments (
    id              SERIAL PRIMARY KEY,
    journal_id      INTEGER NOT NULL REFERENCES devotion_journals(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,           -- 评论者
    nickname        VARCHAR(100) DEFAULT '',
    content         TEXT NOT NULL,
    parent_id       INTEGER REFERENCES devotion_journal_comments(id) ON DELETE CASCADE, -- 回复评论
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_journal_comments_journal ON devotion_journal_comments(journal_id);
CREATE INDEX IF NOT EXISTS idx_journal_comments_parent ON devotion_journal_comments(parent_id);

-- ============================================
-- 3. 分享墙模块 (Sharing Wall)
-- ============================================

-- 分享墙内容表
CREATE TABLE IF NOT EXISTS sharing_wall (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) DEFAULT '',           -- 发布者（可匿名）
    nickname        VARCHAR(100) DEFAULT '',            -- 昵称
    
    -- 内容
    content_type    VARCHAR(20) DEFAULT 'text',        -- text/image/video/audio/scripture/testimony
    title           VARCHAR(200) DEFAULT '',             -- 标题
    content         TEXT NOT NULL,                     -- 内容
    media_urls      TEXT[] DEFAULT '{}',              -- 媒体文件 URLs
    
    -- 分类标签
    category        VARCHAR(50) DEFAULT 'general',     -- general/testimony/praise/prayer/verse/question
    tags            TEXT[] DEFAULT '{}',              -- 标签数组
    
    -- 情感分析
    emotion_score   DECIMAL(3,2),                     -- 情感分数 -1.0 到 1.0
    emotion_label   VARCHAR(50) DEFAULT '',            -- 情感标签
    
    -- 隐私设置
    is_anonymous    BOOLEAN DEFAULT FALSE,            -- 是否匿名
    privacy_level   VARCHAR(20) DEFAULT 'public',      -- public/friends/private
    
    -- 互动统计
    likes_count     INTEGER DEFAULT 0,
    comments_count  INTEGER DEFAULT 0,
    shares_count    INTEGER DEFAULT 0,
    views_count     INTEGER DEFAULT 0,
    
    -- 审核状态
    status          VARCHAR(20) DEFAULT 'approved',    -- pending/approved/rejected
    moderated_by    VARCHAR(255) DEFAULT '',
    moderated_at    TIMESTAMP,
    
    -- 来源（如果是从灵修/祷告同步）
    source_type     VARCHAR(50) DEFAULT '',            -- devotion/prayer/journal
    source_id       INTEGER,                           -- 源内容ID
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sharing_wall_email ON sharing_wall(email);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_category ON sharing_wall(category);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_status ON sharing_wall(status);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_created ON sharing_wall(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_tags ON sharing_wall USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_anonymous ON sharing_wall(is_anonymous) WHERE is_anonymous = FALSE;

-- 分享墙点赞表
CREATE TABLE IF NOT EXISTS sharing_wall_likes (
    id              SERIAL PRIMARY KEY,
    share_id        INTEGER NOT NULL REFERENCES sharing_wall(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(share_id, email)                          -- 每个用户只能点赞一次
);

CREATE INDEX IF NOT EXISTS idx_sharing_likes_share ON sharing_wall_likes(share_id);

-- 分享墙评论表
CREATE TABLE IF NOT EXISTS sharing_wall_comments (
    id              SERIAL PRIMARY KEY,
    share_id        INTEGER NOT NULL REFERENCES sharing_wall(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    nickname        VARCHAR(100) DEFAULT '',
    content         TEXT NOT NULL,
    parent_id       INTEGER REFERENCES sharing_wall_comments(id) ON DELETE CASCADE,
    likes_count     INTEGER DEFAULT 0,
    is_anonymous    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sharing_comments_share ON sharing_wall_comments(share_id);

-- ============================================
-- 4. 祷告模块 (Prayer) - 基于现有表增强
-- ============================================

-- 祷告墙表 (增强版)
CREATE TABLE IF NOT EXISTS prayers (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) DEFAULT '',           -- 发布者
    nickname        VARCHAR(100) DEFAULT '',            -- 昵称
    
    -- 祷告内容
    title           VARCHAR(200) DEFAULT '',             -- 标题
    content         TEXT NOT NULL,                     -- 祷告内容
    
    -- 分类
    category        VARCHAR(50) DEFAULT 'general',     -- healing/family/work/ministry/praise/confession/other
    urgency         VARCHAR(20) DEFAULT 'normal',      -- low/normal/high/urgent
    
    -- 隐私
    is_anonymous    BOOLEAN DEFAULT TRUE,              -- 祷告默认匿名
    privacy_level   VARCHAR(20) DEFAULT 'public',      -- public/church/private/prayer_team
    
    -- 状态
    status          VARCHAR(20) DEFAULT 'active',      -- active/answered/archived
    answered_at     TIMESTAMP,                         -- 蒙应允时间
    answer_note     TEXT DEFAULT '',                  -- 见证/蒙应允笔记
    
    -- 互动
    amen_count      INTEGER DEFAULT 0,                 -- 阿们数
    views_count     INTEGER DEFAULT 0,
    
    -- 提醒设置
    reminder_days   INTEGER[] DEFAULT '{}',            -- 提醒重复日期 [1,3,7]
    last_reminder   TIMESTAMP,                         -- 上次提醒时间
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prayers_email ON prayers(email);
CREATE INDEX IF NOT EXISTS idx_prayers_category ON prayers(category);
CREATE INDEX IF NOT EXISTS idx_prayers_status ON prayers(status);
CREATE INDEX IF NOT EXISTS idx_prayers_urgency ON prayers(urgency);
CREATE INDEX IF NOT EXISTS idx_prayers_created ON prayers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prayers_anonymous ON prayers(is_anonymous) WHERE is_anonymous = FALSE;

-- 阿们记录表 (谁为哪个祷告点了阿们)
CREATE TABLE IF NOT EXISTS prayer_amens (
    id              SERIAL PRIMARY KEY,
    prayer_id       INTEGER NOT NULL REFERENCES prayers(id) ON DELETE CASCADE,
    email           VARCHAR(255) DEFAULT '',           -- 可为空（匿名阿们）
    nickname        VARCHAR(100) DEFAULT '',
    note            TEXT DEFAULT '',                  -- 代祷笔记
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(prayer_id, email)                          -- 每个用户只能阿们一次
);

CREATE INDEX IF NOT EXISTS idx_prayer_amens_prayer ON prayer_amens(prayer_id);

-- 代祷承诺表 (承诺为某个祷告持续代祷)
CREATE TABLE IF NOT EXISTS prayer_commitments (
    id              SERIAL PRIMARY KEY,
    prayer_id       INTEGER NOT NULL REFERENCES prayers(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    commitment_type VARCHAR(20) DEFAULT '7_days',     -- 7_days/30_days/until_answered
    end_date        DATE,                              -- 承诺结束日期
    reminder_enabled BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(prayer_id, email)
);

CREATE INDEX IF NOT EXISTS idx_prayer_commitments_prayer ON prayer_commitments(prayer_id);
CREATE INDEX IF NOT EXISTS idx_prayer_commitments_email ON prayer_commitments(email);

-- 祷告更新/见证表 (祷告进展更新)
CREATE TABLE IF NOT EXISTS prayer_updates (
    id              SERIAL PRIMARY KEY,
    prayer_id       INTEGER NOT NULL REFERENCES prayers(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    content         TEXT NOT NULL,                     -- 更新内容
    update_type     VARCHAR(20) DEFAULT 'progress',   -- progress/breakthrough/answered
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prayer_updates_prayer ON prayer_updates(prayer_id);

-- ============================================
-- 5. 日记模块 (Personal Journal)
-- ============================================

-- 个人日记表 (区别于灵修日记，更私人的记录)
CREATE TABLE IF NOT EXISTS personal_journals (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    
    -- 基本信息
    journal_date    DATE NOT NULL,
    title           VARCHAR(200) NOT NULL,
    
    -- 内容 (自由格式)
    content         TEXT NOT NULL,
    mood            VARCHAR(50) DEFAULT '',            -- 心情
    weather         VARCHAR(50) DEFAULT '',            -- 天气
    location        VARCHAR(200) DEFAULT '',           -- 地点
    
    -- 分类
    category        VARCHAR(50) DEFAULT 'daily',     -- daily/gratitude/confession/lesson/dream
    
    -- 情感标签
    emotion_tags    TEXT[] DEFAULT '{}',
    
    -- 多媒体
    images          TEXT[] DEFAULT '{}',
    voice_url       VARCHAR(500) DEFAULT '',
    
    -- 关联
    related_scripture VARCHAR(200) DEFAULT '',          -- 相关经文
    related_prayer_id INTEGER REFERENCES prayers(id) ON DELETE SET NULL,
    
    -- 隐私 (个人日记默认私密)
    privacy_level   VARCHAR(20) DEFAULT 'private',   -- private/family/mentor
    
    -- 分享设置
    is_favorite     BOOLEAN DEFAULT FALSE,             -- 收藏
    is_shared       BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(email, journal_date)
);

CREATE INDEX IF NOT EXISTS idx_personal_journals_email ON personal_journals(email);
CREATE INDEX IF NOT EXISTS idx_personal_journals_date ON personal_journals(journal_date);
CREATE INDEX IF NOT EXISTS idx_personal_journals_category ON personal_journals(category);
CREATE INDEX IF NOT EXISTS idx_personal_journals_favorite ON personal_journals(is_favorite) WHERE is_favorite = TRUE;

-- 日记模板表 (快速记录模板)
CREATE TABLE IF NOT EXISTS journal_templates (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    description     TEXT DEFAULT '',
    template_type   VARCHAR(50) DEFAULT 'gratitude',   -- gratitude/confession/sermon/dream/5w1h
    structure       JSONB NOT NULL,                    -- 模板结构 JSON
    is_system       BOOLEAN DEFAULT FALSE,             -- 系统预设模板
    created_by      VARCHAR(255) DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 6. 统计与成就表 (用户参与度)
-- ============================================

-- 用户活动统计表
CREATE TABLE IF NOT EXISTS user_activity_stats (
    email           VARCHAR(255) PRIMARY KEY,
    
    -- 主日参与
    sunday_attendance_count INTEGER DEFAULT 0,
    last_sunday_attendance TIMESTAMP,
    
    -- 灵修
    devotion_streak_days INTEGER DEFAULT 0,           -- 连续灵修天数
    total_devotions   INTEGER DEFAULT 0,
    last_devotion_date DATE,
    
    -- 祷告
    prayers_posted    INTEGER DEFAULT 0,
    prayers_amened    INTEGER DEFAULT 0,
    prayer_commitments_count INTEGER DEFAULT 0,
    
    -- 分享
    shares_posted     INTEGER DEFAULT 0,
    shares_liked      INTEGER DEFAULT 0,
    
    -- 日记
    total_journals    INTEGER DEFAULT 0,
    
    -- 综合
    last_active_at    TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户成就徽章表
CREATE TABLE IF NOT EXISTS user_badges (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    badge_type      VARCHAR(50) NOT NULL,             -- devotion_streak_7/prayer_warrior/sharer/...
    badge_name      VARCHAR(100) NOT NULL,
    description     TEXT DEFAULT '',
    awarded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(email, badge_type)
);

CREATE INDEX IF NOT EXISTS idx_user_badges_email ON user_badges(email);

-- ============================================
-- 7. 触发器函数 (自动更新 updated_at)
-- ============================================

-- 创建自动更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有需要自动更新的表创建触发器
CREATE TRIGGER update_sunday_services_updated_at BEFORE UPDATE ON sunday_services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devotion_plans_updated_at BEFORE UPDATE ON devotion_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devotion_journals_updated_at BEFORE UPDATE ON devotion_journals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sharing_wall_updated_at BEFORE UPDATE ON sharing_wall
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prayers_updated_at BEFORE UPDATE ON prayers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_personal_journals_updated_at BEFORE UPDATE ON personal_journals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 用户活动统计自动更新触发器
CREATE OR REPLACE FUNCTION update_user_activity_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_activity_stats (email, last_active_at)
    VALUES (NEW.email, CURRENT_TIMESTAMP)
    ON CONFLICT (email) DO UPDATE
    SET last_active_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- 8. 视图 (方便查询)
-- ============================================

-- 用户灵修统计视图
CREATE OR REPLACE VIEW user_devotion_stats AS
SELECT 
    email,
    COUNT(*) as total_journals,
    COUNT(*) FILTER (WHERE is_shared = TRUE) as shared_count,
    MAX(journal_date) as last_journal_date,
    COUNT(DISTINCT DATE_TRUNC('month', journal_date)) as active_months
FROM devotion_journals
GROUP BY email;

-- 祷告墙统计视图
CREATE OR REPLACE VIEW prayer_wall_stats AS
SELECT 
    category,
    COUNT(*) as total_prayers,
    COUNT(*) FILTER (WHERE status = 'active') as active_prayers,
    COUNT(*) FILTER (WHERE status = 'answered') as answered_prayers,
    SUM(amen_count) as total_amens
FROM prayers
GROUP BY category;

-- 分享墙热门内容视图
CREATE OR REPLACE VIEW sharing_wall_trending AS
SELECT 
    sw.*,
    (sw.likes_count * 2 + sw.comments_count * 3 + sw.views_count * 0.1) as trending_score
FROM sharing_wall sw
WHERE sw.status = 'approved' AND sw.created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY trending_score DESC;
