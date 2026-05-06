-- ============================================
-- PostgreSQL 索引优化脚本
-- 为所有表创建高性能索引
-- ============================================

-- ============================================
-- 0. 统计模块索引优化
-- ============================================

-- page_views 表复合索引
CREATE INDEX IF NOT EXISTS idx_page_views_visitor_time ON page_views(visitor_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_page_views_path_time ON page_views(page_path, viewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_page_views_email_time ON page_views(email, viewed_at DESC) WHERE email != '';
CREATE INDEX IF NOT EXISTS idx_page_views_device_type ON page_views(device_type, viewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_page_views_browser ON page_views(browser, viewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_page_views_country ON page_views(country, viewed_at DESC) WHERE country != '';
CREATE INDEX IF NOT EXISTS idx_page_views_utm ON page_views(utm_source, utm_medium) WHERE utm_source != '';
CREATE INDEX IF NOT EXISTS idx_page_views_auth ON page_views(is_authenticated, viewed_at DESC);

-- 时间范围查询优化 (BRIN索引适用于大数据量时间序列)
CREATE INDEX IF NOT EXISTS idx_page_views_viewed_at_brin ON page_views USING BRIN(viewed_at) 
    WITH (pages_per_range = 128);

-- visitor_sessions 表索引
CREATE INDEX IF NOT EXISTS idx_visitor_sessions_browser_os ON visitor_sessions(browser, os);
CREATE INDEX IF NOT EXISTS idx_visitor_sessions_country ON visitor_sessions(country) WHERE country != '';
CREATE INDEX IF NOT EXISTS idx_visitor_sessions_returning_time ON visitor_sessions(is_returning, last_visit_at DESC);
CREATE INDEX IF NOT EXISTS idx_visitor_sessions_total_visits ON visitor_sessions(total_visits DESC) WHERE total_visits > 1;

-- active_sessions 表索引
CREATE INDEX IF NOT EXISTS idx_active_sessions_page ON active_sessions(page_path);
CREATE INDEX IF NOT EXISTS idx_active_sessions_auth_page ON active_sessions(is_authenticated, page_path);

-- ============================================
-- 1. 主日模块索引优化
-- ============================================

-- sunday_services 复合索引
CREATE INDEX IF NOT EXISTS idx_sunday_services_date_status ON sunday_services(service_date, status);
CREATE INDEX IF NOT EXISTS idx_sunday_services_speaker ON sunday_services(speaker) WHERE speaker != '';

-- sunday_attendance 复合索引
CREATE INDEX IF NOT EXISTS idx_sunday_attendance_service_email ON sunday_attendance(service_id, email);
CREATE INDEX IF NOT EXISTS idx_sunday_attendance_checkin ON sunday_attendance(check_in_time DESC);

-- sunday_offerings 索引
CREATE INDEX IF NOT EXISTS idx_sunday_offerings_service_type ON sunday_offerings(service_id, offering_type);
CREATE INDEX IF NOT EXISTS idx_sunday_offerings_amount ON sunday_offerings(amount DESC);

-- ============================================
-- 2. 灵修模块索引优化
-- ============================================

-- devotion_plans 索引
CREATE INDEX IF NOT EXISTS idx_devotion_plans_public ON devotion_plans(is_public, created_at) WHERE is_public = TRUE;

-- devotion_journals 复合索引
CREATE INDEX IF NOT EXISTS idx_devotion_journals_email_date ON devotion_journals(email, journal_date DESC);
CREATE INDEX IF NOT EXISTS idx_devotion_journals_email_plan ON devotion_journals(email, plan_id) WHERE plan_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_devotion_journals_shared_date ON devotion_journals(is_shared, journal_date DESC) WHERE is_shared = TRUE;
CREATE INDEX IF NOT EXISTS idx_devotion_journals_mood ON devotion_journals(mood) WHERE mood != '';
CREATE INDEX IF NOT EXISTS idx_devotion_journals_scripture ON devotion_journals(scripture_ref) WHERE scripture_ref != '';
CREATE INDEX IF NOT EXISTS idx_devotion_journals_spiritual ON devotion_journals(spiritual_state, journal_date DESC) WHERE spiritual_state IS NOT NULL;

-- 数组索引 (用于标签搜索)
CREATE INDEX IF NOT EXISTS idx_devotion_journals_emotion_tags ON devotion_journals USING GIN(emotion_tags);
CREATE INDEX IF NOT EXISTS idx_devotion_journals_images ON devotion_journals USING GIN(images);

-- devotion_journal_comments 索引
CREATE INDEX IF NOT EXISTS idx_journal_comments_journal_created ON devotion_journal_comments(journal_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_comments_parent ON devotion_journal_comments(parent_id, created_at) WHERE parent_id IS NOT NULL;

-- ============================================
-- 3. 分享墙模块索引优化
-- ============================================

-- sharing_wall 复合索引
CREATE INDEX IF NOT EXISTS idx_sharing_wall_email_created ON sharing_wall(email, created_at DESC) WHERE email != '';
CREATE INDEX IF NOT EXISTS idx_sharing_wall_category_created ON sharing_wall(category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_status_created ON sharing_wall(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_emotion ON sharing_wall(emotion_label, emotion_score) WHERE emotion_label != '';
CREATE INDEX IF NOT EXISTS idx_sharing_wall_privacy ON sharing_wall(privacy_level, is_anonymous, status) 
    WHERE privacy_level IN ('public', 'friends');
CREATE INDEX IF NOT EXISTS idx_sharing_wall_source ON sharing_wall(source_type, source_id) WHERE source_type != '';

-- 热门内容查询优化 (点赞、评论、浏览数)
CREATE INDEX IF NOT EXISTS idx_sharing_wall_engagement ON sharing_wall(likes_count DESC, comments_count DESC, created_at DESC) 
    WHERE status = 'approved';

-- 数组索引
CREATE INDEX IF NOT EXISTS idx_sharing_wall_tags ON sharing_wall USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_sharing_wall_media ON sharing_wall USING GIN(media_urls);

-- sharing_wall_likes 索引
CREATE INDEX IF NOT EXISTS idx_sharing_likes_share_created ON sharing_wall_likes(share_id, created_at DESC);

-- sharing_wall_comments 索引
CREATE INDEX IF NOT EXISTS idx_sharing_comments_share_created ON sharing_wall_comments(share_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sharing_comments_parent ON sharing_wall_comments(parent_id) WHERE parent_id IS NOT NULL;

-- ============================================
-- 4. 祷告模块索引优化
-- ============================================

-- prayers 复合索引
CREATE INDEX IF NOT EXISTS idx_prayers_email_created ON prayers(email, created_at DESC) WHERE email != '';
CREATE INDEX IF NOT EXISTS idx_prayers_category_status ON prayers(category, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prayers_urgency ON prayers(urgency, status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_prayers_status_answered ON prayers(status, answered_at) WHERE status = 'answered';
CREATE INDEX IF NOT EXISTS idx_prayers_amen_count ON prayers(amen_count DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prayers_privacy ON prayers(privacy_level, is_anonymous, status);
CREATE INDEX IF NOT EXISTS idx_prayers_reminder ON prayers USING GIN(reminder_days);

-- prayer_amens 复合索引
CREATE INDEX IF NOT EXISTS idx_prayer_amens_prayer_created ON prayer_amens(prayer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prayer_amens_email ON prayer_amens(email) WHERE email != '';

-- prayer_commitments 索引
CREATE INDEX IF NOT EXISTS idx_prayer_commitments_email ON prayer_commitments(email, end_date);
CREATE INDEX IF NOT EXISTS idx_prayer_commitments_prayer ON prayer_commitments(prayer_id, created_at);

-- prayer_updates 索引
CREATE INDEX IF NOT EXISTS idx_prayer_updates_prayer_type ON prayer_updates(prayer_id, update_type, created_at DESC);

-- ============================================
-- 5. 日记模块索引优化
-- ============================================

-- personal_journals 复合索引
CREATE INDEX IF NOT EXISTS idx_personal_journals_email_date ON personal_journals(email, journal_date DESC);
CREATE INDEX IF NOT EXISTS idx_personal_journals_email_category ON personal_journals(email, category);
CREATE INDEX IF NOT EXISTS idx_personal_journals_email_favorite ON personal_journals(email, is_favorite) WHERE is_favorite = TRUE;
CREATE INDEX IF NOT EXISTS idx_personal_journals_email_shared ON personal_journals(email, is_shared) WHERE is_shared = TRUE;
CREATE INDEX IF NOT EXISTS idx_personal_journals_mood ON personal_journals(mood) WHERE mood != '';
CREATE INDEX IF NOT EXISTS idx_personal_journals_related_prayer ON personal_journals(related_prayer_id) WHERE related_prayer_id IS NOT NULL;

-- 数组索引
CREATE INDEX IF NOT EXISTS idx_personal_journals_emotion_tags ON personal_journals USING GIN(emotion_tags);
CREATE INDEX IF NOT EXISTS idx_personal_journals_images ON personal_journals USING GIN(images);

-- journal_templates 索引
CREATE INDEX IF NOT EXISTS idx_journal_templates_type ON journal_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_journal_templates_system ON journal_templates(is_system, template_type) WHERE is_system = TRUE;

-- ============================================
-- 6. 用户统计和成就索引优化
-- ============================================

-- user_activity_stats 索引
CREATE INDEX IF NOT EXISTS idx_user_activity_stats_last_active ON user_activity_stats(last_active_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_stats_devotion ON user_activity_stats(devotion_streak_days DESC) WHERE devotion_streak_days > 0;
CREATE INDEX IF NOT EXISTS idx_user_activity_stats_prayers ON user_activity_stats(prayers_posted DESC) WHERE prayers_posted > 0;
CREATE INDEX IF NOT EXISTS idx_user_activity_stats_sunday ON user_activity_stats(sunday_attendance_count DESC) WHERE sunday_attendance_count > 0;

-- user_badges 索引
CREATE INDEX IF NOT EXISTS idx_user_badges_email ON user_badges(email);
CREATE INDEX IF NOT EXISTS idx_user_badges_type ON user_badges(badge_type);

-- ============================================
-- 7. 用户表索引优化 (现有表)
-- ============================================

-- users 表索引
CREATE INDEX IF NOT EXISTS idx_users_login_type ON users(login_type);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at DESC);

-- user_tags 复合索引
CREATE INDEX IF NOT EXISTS idx_user_tags_email_weight ON user_tags(email, weight DESC);
CREATE INDEX IF NOT EXISTS idx_user_tags_key ON user_tags(tag_key, tag_value);

-- user_checkins 索引
CREATE INDEX IF NOT EXISTS idx_user_checkins_email ON user_checkins(email, checkin_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_checkins_date ON user_checkins(checkin_at DESC);

-- conversation_messages 索引
CREATE INDEX IF NOT EXISTS idx_conversation_messages_session ON conversation_messages(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_email ON conversation_messages(email, created_at DESC) WHERE email != '';

-- security_audit 复合索引
CREATE INDEX IF NOT EXISTS idx_security_audit_event ON security_audit(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_audit_success ON security_audit(success, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_audit_ip ON security_audit(ip) WHERE ip != '';

-- user_tokens 索引
CREATE INDEX IF NOT EXISTS idx_user_tokens_expires ON user_tokens(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================
-- 8. 全文搜索索引 (可选，需要时启用)
-- ============================================

-- devotion_journals 全文搜索
-- CREATE INDEX IF NOT EXISTS idx_devotion_journals_fts ON devotion_journals 
--     USING GIN(to_tsvector('chinese', observation || ' ' || reflection || ' ' || application || ' ' || prayer));

-- sharing_wall 全文搜索
-- CREATE INDEX IF NOT EXISTS idx_sharing_wall_fts ON sharing_wall 
--     USING GIN(to_tsvector('chinese', title || ' ' || content));

-- prayers 全文搜索
-- CREATE INDEX IF NOT EXISTS idx_prayers_fts ON prayers 
--     USING GIN(to_tsvector('chinese', title || ' ' || content));

-- personal_journals 全文搜索
-- CREATE INDEX IF NOT EXISTS idx_personal_journals_fts ON personal_journals 
--     USING GIN(to_tsvector('chinese', title || ' ' || content));

-- ============================================
-- 索引统计信息更新
-- ============================================

-- 更新所有表的统计信息，帮助查询优化器做出更好的决策
ANALYZE page_views;
ANALYZE visitor_sessions;
ANALYZE daily_stats;
ANALYZE sunday_services;
ANALYZE sunday_attendance;
ANALYZE devotion_journals;
ANALYZE sharing_wall;
ANALYZE prayers;
ANALYZE personal_journals;
ANALYZE users;

-- 查看索引创建结果
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
-- ORDER BY tablename, indexname;
