"""PostgreSQL schema DDL (CREATE TABLE / ALTER / INDEX) + first-run seed.

Extracted verbatim from main._init_db_postgresql() to slim main.py.
Idempotent (IF NOT EXISTS). Connection + password helpers are injected
to avoid a circular import with main.
"""

import json
import os
import secrets


DEFAULT_DEMO_EMAIL = 'john@bible-sphere.com'


def demo_user_config():
    """Return fail-closed demo-user settings for first-run database setup."""
    enabled = os.getenv('SEED_DEMO_USER', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    email = (os.getenv('DEMO_USER_EMAIL') or DEFAULT_DEMO_EMAIL).strip().lower()
    password = os.getenv('DEMO_USER_PASSWORD', '')
    if enabled and ('@' not in email or email.startswith('@') or email.endswith('@')):
        raise RuntimeError('SEED_DEMO_USER requires a valid DEMO_USER_EMAIL')
    if enabled and len(password) < 12:
        raise RuntimeError('SEED_DEMO_USER requires DEMO_USER_PASSWORD with at least 12 characters')
    return enabled, email, password


def has_historical_demo_password(stored_hash, verify_password):
    """Identify only the original public demo credential before disabling it."""
    return bool(stored_hash) and verify_password('John', stored_hash)


def init_db_postgresql(get_db, release_db, hash_password, verify_password):
    """初始化 PostgreSQL 数据库表。"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Users table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id          SERIAL PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL UNIQUE,
                    nickname    VARCHAR(100) NOT NULL DEFAULT '',
                    avatar      VARCHAR(500) DEFAULT '',
                    openid      VARCHAR(255) UNIQUE,
                    unionid     VARCHAR(255),
                    login_type  VARCHAR(20) NOT NULL DEFAULT 'email',
                    password_hash VARCHAR(255) NOT NULL DEFAULT '',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Security audit log table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS security_audit (
                    id          SERIAL PRIMARY KEY,
                    event_type  VARCHAR(50) NOT NULL,
                    email       VARCHAR(255),
                    ip_address  INET,
                    user_agent  TEXT DEFAULT '',
                    details     JSONB DEFAULT '{}',
                    success     BOOLEAN DEFAULT TRUE,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_security_audit_email ON security_audit(email) WHERE email IS NOT NULL')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_security_audit_created ON security_audit(created_at DESC)')

            # User tags table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_tags (
                    email       VARCHAR(255) NOT NULL,
                    tag_key     VARCHAR(100) NOT NULL,
                    tag_value   VARCHAR(255) NOT NULL,
                    weight      REAL DEFAULT 1.0,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (email, tag_key)
                )
            ''')

            # User checkins table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_checkins (
                    id          SERIAL PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    checkin_at  TIMESTAMP NOT NULL,
                    data        JSONB NOT NULL,
                    emotion_label VARCHAR(100) DEFAULT '',
                    mood        VARCHAR(50) DEFAULT ''
                )
            ''')

            # Conversation messages table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id          SERIAL PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL DEFAULT '',
                    session_id  VARCHAR(255) NOT NULL,
                    role        VARCHAR(50) NOT NULL,
                    content     TEXT NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Prayers table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS prayers (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL DEFAULT '',
                    nickname     VARCHAR(100) NOT NULL DEFAULT '',
                    content      TEXT NOT NULL,
                    is_anonymous BOOLEAN DEFAULT FALSE,
                    amen_count   INTEGER DEFAULT 0,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at   TIMESTAMP DEFAULT NULL
                )
            ''')
            # Add columns if not exists (for existing tables)
            cur.execute('''
                ALTER TABLE prayers 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            cur.execute('''
                ALTER TABLE prayers 
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_prayers_deleted_at ON prayers(deleted_at) WHERE deleted_at IS NULL')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_prayers_updated ON prayers(updated_at DESC)')
            cur.execute('''
                ALTER TABLE prayers
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT NULL
            ''')

            # Evangelism prayers table (传福音祷告墙)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS evangelism_prayers (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL DEFAULT '',
                    nickname     VARCHAR(100) NOT NULL DEFAULT '',
                    content      TEXT NOT NULL,
                    is_anonymous BOOLEAN DEFAULT FALSE,
                    amen_count   INTEGER DEFAULT 0,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at   TIMESTAMP DEFAULT NULL
                )
            ''')
            # Add columns if not exists (for existing tables)
            cur.execute('''
                ALTER TABLE evangelism_prayers 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            cur.execute('''
                ALTER TABLE evangelism_prayers 
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_evangelism_deleted_at ON evangelism_prayers(deleted_at) WHERE deleted_at IS NULL')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_evangelism_updated ON evangelism_prayers(updated_at DESC)')

            # Devotion journals table (兼容 schema.sql 的列名)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS devotion_journals (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL,
                    journal_date DATE NOT NULL,
                    title        VARCHAR(255) NOT NULL DEFAULT '',
                    scripture_text TEXT DEFAULT '',
                    observation  TEXT DEFAULT '',
                    reflection   TEXT DEFAULT '',
                    application  TEXT DEFAULT '',
                    prayer       TEXT DEFAULT '',
                    mood         VARCHAR(50) DEFAULT '',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at   TIMESTAMP DEFAULT NULL,
                    UNIQUE(email, journal_date)
                )
            ''')
            # Add deleted_at column if not exists (for existing tables)
            cur.execute('''
                ALTER TABLE devotion_journals 
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_devotion_deleted_at ON devotion_journals(deleted_at) WHERE deleted_at IS NULL')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_devotion_email_updated ON devotion_journals(email, updated_at DESC)')

            # Personal notes table (我的日记)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS personal_notes (
                    id           VARCHAR(50) PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL,
                    note_date    DATE NOT NULL,
                    scripture    TEXT DEFAULT '',
                    observation  TEXT DEFAULT '',
                    reflection   TEXT DEFAULT '',
                    application  TEXT DEFAULT '',
                    prayer       TEXT DEFAULT '',
                    mood         VARCHAR(50) DEFAULT '',
                    shared       BOOLEAN DEFAULT FALSE,
                    author       VARCHAR(100) DEFAULT '',
                    avatar       TEXT DEFAULT '',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at   TIMESTAMP DEFAULT NULL
                )
            ''')
            # Migration: add deleted_at if missing
            cur.execute("""
                DO $$ BEGIN
                    ALTER TABLE personal_notes ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL;
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """)
            # Migration: add shared_at column (分享时间戳，独立于编辑时间)
            cur.execute("""
                DO $$ BEGIN
                    ALTER TABLE personal_notes ADD COLUMN shared_at TIMESTAMP DEFAULT NULL;
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """)
            # Note interactions table (阿们/点赞，防重复)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS note_interactions (
                    id         SERIAL PRIMARY KEY,
                    note_id    VARCHAR(50) NOT NULL,
                    email      VARCHAR(255) NOT NULL,
                    action     VARCHAR(20) DEFAULT \'amen\',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(note_id, email, action)
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_note_interactions_note_id ON note_interactions(note_id)')

            # Sermon journals table (主日信息)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS sermon_journals (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL,
                    sermon_date  TEXT NOT NULL,
                    title        VARCHAR(255) NOT NULL DEFAULT '',
                    preacher     VARCHAR(100) DEFAULT '',
                    scripture    TEXT DEFAULT '',
                    summary      TEXT DEFAULT '',
                    questions    JSONB DEFAULT '[]',
                    bible_study  TEXT DEFAULT '',
                    practices    JSONB DEFAULT '[]',
                    reflection   TEXT DEFAULT '',
                    lesson       TEXT DEFAULT '',
                    conclusion   TEXT DEFAULT '',
                    encouragement TEXT DEFAULT '',
                    phase        VARCHAR(20) DEFAULT 'active',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at   TIMESTAMP DEFAULT NULL,
                    UNIQUE(email, sermon_date)
                )
            ''')
            # Add deleted_at column if not exists (for existing tables)
            cur.execute('''
                ALTER TABLE sermon_journals 
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL
            ''')
            cur.execute('''
                ALTER TABLE sermon_journals
                ALTER COLUMN sermon_date TYPE TEXT USING sermon_date::TEXT
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_sermon_deleted_at ON sermon_journals(deleted_at) WHERE deleted_at IS NULL')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_sermon_email_updated ON sermon_journals(email, updated_at DESC)')

            # User tokens table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_tokens (
                    token       VARCHAR(255) PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    data        JSONB NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at  TIMESTAMP,
                    ip_address  INET
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_tokens_email ON user_tokens(email)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_tokens_expires ON user_tokens(expires_at)')

            # User roles table (for role-based access control)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_roles (
                    id          SERIAL PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL UNIQUE,
                    role        VARCHAR(50) NOT NULL DEFAULT 'user',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_roles_email ON user_roles(email)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role)')

            # Dating priority submissions table (交友原则排序)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS dating_priority_submissions (
                    id           SERIAL PRIMARY KEY,
                    visitor_id   VARCHAR(255) NOT NULL,
                    perspective  VARCHAR(10) NOT NULL,
                    focus_order  JSONB NOT NULL DEFAULT '[]',
                    block_order  JSONB NOT NULL DEFAULT '[]',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dating_priority_visitor ON dating_priority_submissions(visitor_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dating_priority_persp ON dating_priority_submissions(perspective)')

            # ============================================================================
            # 用户人格画像标签系统表结构 (User Personality Profile Tag System)
            # ============================================================================

            # 1. 用户标签主表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_profile_tags (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id TEXT NOT NULL,
                    tag_name TEXT NOT NULL,
                    tag_category TEXT NOT NULL,
                    tag_subcategory TEXT,
                    source TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5 CHECK (confidence BETWEEN 0.0 AND 1.0),
                    weight REAL DEFAULT 1.0 CHECK (weight BETWEEN 0.0 AND 10.0),
                    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    occurrence_count INTEGER DEFAULT 1,
                    history_weights JSONB DEFAULT '[]',
                    context_snapshot JSONB DEFAULT '{}',
                    related_emotions JSONB DEFAULT '[]',
                    related_decisions JSONB DEFAULT '[]',
                    related_habits JSONB DEFAULT '[]',
                    source_events JSONB DEFAULT '[]',
                    is_active BOOLEAN DEFAULT TRUE,
                    is_manually_added BOOLEAN DEFAULT FALSE,
                    is_system_core BOOLEAN DEFAULT FALSE,
                    UNIQUE(user_id, tag_name)
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_user_id ON user_profile_tags(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_user_active ON user_profile_tags(user_id, is_active)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_category ON user_profile_tags(tag_category)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_user_category ON user_profile_tags(user_id, tag_category)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_weight ON user_profile_tags(weight DESC)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_user_weight ON user_profile_tags(user_id, weight DESC)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_source ON user_profile_tags(source)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_tags_last_seen ON user_profile_tags(last_seen_at DESC)')

            # 2. 标签事件关联表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tag_event_links (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tag_id UUID NOT NULL REFERENCES user_profile_tags(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    event_data JSONB DEFAULT '{}',
                    extracted_keywords TEXT[],
                    extraction_confidence REAL DEFAULT 0.5,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_tag_event_links_tag_id ON tag_event_links(tag_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_tag_event_links_event ON tag_event_links(event_type, event_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_tag_event_links_created ON tag_event_links(created_at DESC)')

            # 3. 人格画像快照表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS personality_profile_snapshots (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id TEXT NOT NULL,
                    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    personality_archetype TEXT,
                    dominant_loop TEXT,
                    trajectory_direction TEXT,
                    humility_score REAL CHECK (humility_score BETWEEN 0.05 AND 0.95),
                    fear_tendency_score REAL CHECK (fear_tendency_score BETWEEN 0.05 AND 0.95),
                    pride_tendency_score REAL CHECK (pride_tendency_score BETWEEN 0.05 AND 0.95),
                    emotional_stability_score REAL CHECK (emotional_stability_score BETWEEN 0.05 AND 0.95),
                    truth_alignment_score REAL CHECK (truth_alignment_score BETWEEN 0.05 AND 0.95),
                    relational_health_score REAL CHECK (relational_health_score BETWEEN 0.05 AND 0.95),
                    resilience_score REAL CHECK (resilience_score BETWEEN 0.05 AND 0.95),
                    spiritual_clarity_score REAL CHECK (spiritual_clarity_score BETWEEN 0.05 AND 0.95),
                    vector_confidence REAL DEFAULT 0.5,
                    vector_data_points INTEGER DEFAULT 0,
                    top_emotion_tags JSONB DEFAULT '[]',
                    top_behavior_tags JSONB DEFAULT '[]',
                    top_value_tags JSONB DEFAULT '[]',
                    top_relationship_tags JSONB DEFAULT '[]',
                    life_dominant_domains JSONB DEFAULT '[]',
                    recurring_patterns JSONB DEFAULT '[]',
                    growth_indicators JSONB DEFAULT '[]',
                    risk_factors JSONB DEFAULT '[]',
                    profile_stability REAL DEFAULT 0.5,
                    change_velocity REAL DEFAULT 0.0,
                    trend_direction TEXT DEFAULT 'stable',
                    profile_summary TEXT,
                    core_narrative TEXT,
                    growth_pathway TEXT,
                    version INTEGER DEFAULT 1,
                    is_current BOOLEAN DEFAULT TRUE,
                    calculation_method TEXT DEFAULT 'automatic',
                    included_decision_ids UUID[],
                    included_checkin_ids UUID[],
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_snapshots_user_id ON personality_profile_snapshots(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_snapshots_user_current ON personality_profile_snapshots(user_id, is_current) WHERE is_current = TRUE')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_profile_snapshots_generated ON personality_profile_snapshots(generated_at DESC)')

            # 4. 标签权重历史表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tag_weight_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tag_id UUID NOT NULL REFERENCES user_profile_tags(id) ON DELETE CASCADE,
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    weight REAL NOT NULL,
                    change_reason TEXT,
                    source_event_type TEXT,
                    source_event_id TEXT,
                    occurrence_count_at_record INTEGER,
                    confidence_at_record REAL
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_tag_weight_history_tag_id ON tag_weight_history(tag_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_tag_weight_history_recorded ON tag_weight_history(recorded_at DESC)')

            # 5. 用户标签统计汇总表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_tag_statistics (
                    user_id TEXT PRIMARY KEY,
                    total_tags INTEGER DEFAULT 0,
                    active_tags INTEGER DEFAULT 0,
                    manually_added_tags INTEGER DEFAULT 0,
                    emotion_tags_count INTEGER DEFAULT 0,
                    behavior_tags_count INTEGER DEFAULT 0,
                    value_tags_count INTEGER DEFAULT 0,
                    relationship_tags_count INTEGER DEFAULT 0,
                    average_weight REAL DEFAULT 0,
                    max_weight REAL DEFAULT 0,
                    oldest_tag_at TIMESTAMP WITH TIME ZONE,
                    newest_tag_at TIMESTAMP WITH TIME ZONE,
                    top_tags JSONB DEFAULT '[]',
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')

            # 6. 标签类别元数据表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tag_category_metadata (
                    category TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    display_order INTEGER,
                    color_code TEXT
                )
            ''')

            print('[db] User Personality Profile Tag System tables created', flush=True)

            # Initialize admin user (zpclord@sina.com)
            cur.execute('''
                INSERT INTO user_roles (email, role) VALUES (%s, %s)
                ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role, updated_at = NOW()
            ''', ('zpclord@sina.com', 'admin'))

            demo_enabled, demo_email, demo_password = demo_user_config()
            if demo_enabled:
                demo_hash = hash_password(demo_password)
                cur.execute('SELECT id FROM users WHERE LOWER(email)=LOWER(%s)', (demo_email,))
                existing_demo = cur.fetchone()
                if existing_demo:
                    cur.execute(
                        'UPDATE users SET password_hash=%s, login_type=%s, updated_at=NOW() WHERE id=%s',
                        (demo_hash, 'email', existing_demo[0]),
                    )
                else:
                    cur.execute(
                        '''
                        INSERT INTO users (email, nickname, avatar, openid, login_type, password_hash)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ''',
                        (demo_email, 'Demo User', '', None, 'email', demo_hash),
                    )
                print(f'[db] configured opt-in demo user: {demo_email}', flush=True)

                demo_tags = [
                    ('焦虑型', 'emotion_type', 2.5, 0.8, 'work_stress'),
                    ('恐惧驱动', 'motive', 1.8, 0.75, 'perfectionism'),
                    ('工作领域', 'life_domain', 2.2, 0.9, 'career_focus'),
                    ('灵修习惯', 'habit_type', 3.0, 0.85, 'daily_devotion'),
                    ('探索期', 'life_stage', 1.5, 0.7, 'seeking_direction'),
                    ('真实导向', 'value', 2.0, 0.8, 'authenticity'),
                ]
                for tag_name, category, weight, confidence, context_key in demo_tags:
                    cur.execute('''
                        INSERT INTO user_profile_tags (
                            user_id, tag_name, tag_category, source, confidence, weight,
                            occurrence_count, is_active, is_manually_added, is_system_core,
                            context_snapshot, first_seen_at, last_seen_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (user_id, tag_name) DO UPDATE SET
                            weight = EXCLUDED.weight,
                            confidence = EXCLUDED.confidence,
                            last_seen_at = NOW(),
                            occurrence_count = user_profile_tags.occurrence_count + 1
                    ''', (
                        demo_email, tag_name, category, 'system', confidence, weight,
                        3, True, False, False,
                        json.dumps({'seeded': True, 'context': context_key})
                    ))
                print(f'[db] seeded {len(demo_tags)} demo personality tags', flush=True)
            else:
                # Neutralize only the historical public password, preserving accounts
                # whose owner has already changed the credential.
                cur.execute(
                    'SELECT id, password_hash FROM users WHERE LOWER(email)=LOWER(%s)',
                    (DEFAULT_DEMO_EMAIL,),
                )
                historical_demo = cur.fetchone()
                if historical_demo and has_historical_demo_password(historical_demo[1], verify_password):
                    locked_hash = hash_password(secrets.token_urlsafe(48))
                    cur.execute(
                        'UPDATE users SET password_hash=%s, updated_at=NOW() WHERE id=%s',
                        (locked_hash, historical_demo[0]),
                    )
                    print('[db] disabled historical default demo credential', flush=True)

            # Seed tag category metadata
            _tag_categories = [
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
                ('decision', '决策风格', '做决定时的风格', 18, '#E17055'),
            ]

            for category, display_name, description, order, color in _tag_categories:
                cur.execute('''
                    INSERT INTO tag_category_metadata (category, display_name, description, display_order, color_code)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (category) DO NOTHING
                ''', (category, display_name, description, order, color))

            print(f'[db] seeded {len(_tag_categories)} tag category metadata', flush=True)

            # ── A1: 每日灵魂一问答案 ──────────────────────────────────────
            cur.execute('''
                CREATE TABLE IF NOT EXISTS daily_soul_answers (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL,
                    answer_date  DATE NOT NULL,
                    question     TEXT NOT NULL DEFAULT '',
                    answer       TEXT NOT NULL DEFAULT '',
                    dominant_loop VARCHAR(60) DEFAULT '',
                    trajectory   VARCHAR(40) DEFAULT '',
                    saved_to_journal BOOLEAN DEFAULT FALSE,
                    created_at   TIMESTAMP DEFAULT NOW()
                )
            ''')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_soul_answers_email_date ON daily_soul_answers(email, answer_date)')

            # ── A4: 属灵伙伴 ──────────────────────────────────────────────
            cur.execute('''
                CREATE TABLE IF NOT EXISTS spiritual_partners (
                    id           SERIAL PRIMARY KEY,
                    requester    VARCHAR(255) NOT NULL,
                    partner      VARCHAR(255) NOT NULL,
                    status       VARCHAR(20) DEFAULT 'pending',
                    created_at   TIMESTAMP DEFAULT NOW(),
                    updated_at   TIMESTAMP DEFAULT NOW()
                )
            ''')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_partners_pair ON spiritual_partners(requester, partner)')

            # ── A7: 里程碑徽章 ────────────────────────────────────────────
            cur.execute('''
                CREATE TABLE IF NOT EXISTS milestone_events (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL,
                    badge_key    VARCHAR(60) NOT NULL,
                    earned_at    TIMESTAMP DEFAULT NOW()
                )
            ''')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_milestone_email_badge ON milestone_events(email, badge_key)')

            # ── A10: 圣经通读进度 ─────────────────────────────────────────
            cur.execute('''
                CREATE TABLE IF NOT EXISTS bible_reading_progress (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL,
                    book         VARCHAR(30) NOT NULL,
                    chapter      INTEGER NOT NULL,
                    highlight    TEXT DEFAULT '',
                    read_at      TIMESTAMP DEFAULT NOW(),
                    plan_id      VARCHAR(20) DEFAULT '1year'
                )
            ''')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_reading_email_book_ch ON bible_reading_progress(email, book, chapter)')

            # Sunday school videos table (主日学视频)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS sunday_school_videos (
                    id             SERIAL PRIMARY KEY,
                    title          VARCHAR(255) NOT NULL DEFAULT '',
                    alias          VARCHAR(255) DEFAULT '',
                    teacher        VARCHAR(100) DEFAULT '',
                    scripture      TEXT DEFAULT '',
                    description    TEXT DEFAULT '',
                    video_url      TEXT NOT NULL,
                    thumbnail_url  TEXT DEFAULT '',
                    duration_sec   INTEGER DEFAULT 0,
                    sort_order     INTEGER DEFAULT 0,
                    is_visible     BOOLEAN DEFAULT TRUE,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_ssv_sort ON sunday_school_videos(sort_order, created_at) WHERE is_visible = TRUE')
            # Migration: add alias column if not exists
            try:
                cur.execute("ALTER TABLE sunday_school_videos ADD COLUMN IF NOT EXISTS alias VARCHAR(255) DEFAULT ''")
            except Exception:
                pass

            # Seekers class courses table (慕道班课程 — 文字/PPT/视频)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS seekers_class_courses (
                    id             SERIAL PRIMARY KEY,
                    title          VARCHAR(255) NOT NULL DEFAULT '',
                    teacher        VARCHAR(100) DEFAULT '',
                    scripture      TEXT DEFAULT '',
                    description    TEXT DEFAULT '',
                    text_url       TEXT DEFAULT '',
                    ppt_url        TEXT DEFAULT '',
                    video_url      TEXT DEFAULT '',
                    duration_sec   INTEGER DEFAULT 0,
                    sort_order     INTEGER DEFAULT 0,
                    is_visible     BOOLEAN DEFAULT TRUE,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_scc_sort ON seekers_class_courses(sort_order, created_at) WHERE is_visible = TRUE')

            # 门徒塑造引擎 (Disciple Formation Engine) — profiles / assessments / relationships
            cur.execute("""
                CREATE TABLE IF NOT EXISTS disciple_profiles (
                    email                VARCHAR(255) PRIMARY KEY,
                    spiritual_state      VARCHAR(40)  NOT NULL DEFAULT 'SEEKER',
                    next_state           VARCHAR(40)  DEFAULT '',
                    christlikeness_index NUMERIC(5,2) DEFAULT 0,
                    faith_score          NUMERIC(5,2) DEFAULT 50,
                    hope_score           NUMERIC(5,2) DEFAULT 50,
                    love_score           NUMERIC(5,2) DEFAULT 50,
                    truth_score          NUMERIC(5,2) DEFAULT 50,
                    prayer_score         NUMERIC(5,2) DEFAULT 50,
                    obedience_score      NUMERIC(5,2) DEFAULT 50,
                    character_score      NUMERIC(5,2) DEFAULT 50,
                    calling_score        NUMERIC(5,2) DEFAULT 50,
                    service_score        NUMERIC(5,2) DEFAULT 50,
                    mission_score        NUMERIC(5,2) DEFAULT 50,
                    multiplication_score NUMERIC(5,2) DEFAULT 50,
                    top_idol             VARCHAR(40)  DEFAULT '',
                    growth_edge          VARCHAR(40)  DEFAULT 'faith',
                    twin                 JSONB        DEFAULT '{}'::jsonb,
                    assessment_count     INTEGER      DEFAULT 0,
                    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    updated_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS disciple_assessments (
                    id                   BIGSERIAL PRIMARY KEY,
                    email                VARCHAR(255) NOT NULL,
                    journal              TEXT DEFAULT '',
                    scripture            TEXT DEFAULT '',
                    prayer               TEXT DEFAULT '',
                    spiritual_state      VARCHAR(40) DEFAULT 'SEEKER',
                    christlikeness_index NUMERIC(5,2) DEFAULT 0,
                    growth_edge          VARCHAR(40) DEFAULT '',
                    top_idol             VARCHAR(40) DEFAULT '',
                    next_step            TEXT DEFAULT '',
                    source               VARCHAR(20) DEFAULT 'heuristic',
                    report               JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute('CREATE INDEX IF NOT EXISTS idx_disciple_assess_email ON disciple_assessments(email, created_at DESC)')
            cur.execute("""
                CREATE TABLE IF NOT EXISTS disciple_relationships (
                    id                BIGSERIAL PRIMARY KEY,
                    mentor_email      VARCHAR(255) NOT NULL,
                    disciple_email    VARCHAR(255) DEFAULT '',
                    disciple_name     VARCHAR(120) DEFAULT '',
                    relationship_type VARCHAR(20) NOT NULL DEFAULT 'DISCIPLER',
                    status            VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                    growth_goals      JSONB DEFAULT '[]'::jsonb,
                    started_at        DATE DEFAULT CURRENT_DATE,
                    ended_at          DATE,
                    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_disciple_rel_mentor ON disciple_relationships(mentor_email) WHERE status = 'ACTIVE'")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_disciple_rel_disciple ON disciple_relationships(disciple_email) WHERE status = 'ACTIVE'")

            # 门徒塑造整合层 — 领域事件流 (Domain Events)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS domain_events (
                    id             BIGSERIAL PRIMARY KEY,
                    aggregate_type VARCHAR(60)  NOT NULL,
                    aggregate_id   VARCHAR(255) NOT NULL,
                    event_type     VARCHAR(80)  NOT NULL,
                    payload        JSONB        NOT NULL DEFAULT '{}'::jsonb,
                    processed      BOOLEAN      DEFAULT FALSE,
                    processed_at   TIMESTAMP,
                    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_domain_events_unprocessed ON domain_events(processed, created_at) WHERE processed = FALSE")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_domain_events_aggregate ON domain_events(aggregate_type, aggregate_id, created_at DESC)")

            # 门徒塑造整合层 — Agent 运行记录 (事件消费者产物)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id             BIGSERIAL PRIMARY KEY,
                    email          VARCHAR(255) NOT NULL,
                    agent_name     VARCHAR(60)  NOT NULL,
                    event_type     VARCHAR(80)  DEFAULT '',
                    input_payload  JSONB        DEFAULT '{}'::jsonb,
                    output_payload JSONB        DEFAULT '{}'::jsonb,
                    status         VARCHAR(20)  NOT NULL DEFAULT 'DONE',
                    notified       BOOLEAN      DEFAULT FALSE,
                    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS notified BOOLEAN DEFAULT FALSE")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_email ON agent_runs(email, created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_unnotified ON agent_runs(notified, created_at) WHERE notified = FALSE")

            # ── 属灵塑造扩展 6 模块 (爱之秩序 / 恩典身份 / 信经问答 / 生命规则+辨识 / 十架哀歌 / 圣礼年历) ──
            # 爱之秩序星图 — Ordo Amoris 记录
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ordo_amoris_records (
                    id             VARCHAR(64)  PRIMARY KEY,
                    email          VARCHAR(255) NOT NULL,
                    input_text     TEXT         DEFAULT '',
                    selected_keys  JSONB        DEFAULT '[]'::jsonb,
                    matches        JSONB        DEFAULT '[]'::jsonb,
                    response       JSONB        DEFAULT '{}'::jsonb,
                    love_order_map JSONB        DEFAULT '[]'::jsonb,
                    route          VARCHAR(40)  DEFAULT 'ordo_amoris',
                    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ordo_amoris_email ON ordo_amoris_records(email, created_at DESC)")

            # 与基督联合 / 恩典身份日志
            cur.execute("""
                CREATE TABLE IF NOT EXISTS grace_identity_logs (
                    id          VARCHAR(64)  PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    input_text  TEXT         DEFAULT '',
                    scenario    VARCHAR(60)  DEFAULT '',
                    response    JSONB        DEFAULT '{}'::jsonb,
                    route       VARCHAR(40)  DEFAULT 'grace_identity',
                    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_grace_identity_email ON grace_identity_logs(email, created_at DESC)")

            # 信经与教理问答 — 完成进度
            cur.execute("""
                CREATE TABLE IF NOT EXISTS creed_catechism_progress (
                    email        VARCHAR(255) NOT NULL,
                    item_key     VARCHAR(80)  NOT NULL,
                    pathway      VARCHAR(40)  DEFAULT '',
                    completed_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (email, item_key)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_creed_catechism_email ON creed_catechism_progress(email, completed_at DESC)")

            # 生命规则生成器 — 保存的规则
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rule_of_life_rules (
                    id          VARCHAR(64)  PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    profile     JSONB        DEFAULT '{}'::jsonb,
                    rule        JSONB        DEFAULT '{}'::jsonb,
                    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_rule_of_life_email ON rule_of_life_rules(email, created_at DESC)")

            # 依纳爵辨识罗盘 — 辨识案例
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rule_discernment_cases (
                    id             VARCHAR(64)  PRIMARY KEY,
                    email          VARCHAR(255) NOT NULL,
                    decision_title VARCHAR(200) DEFAULT '',
                    input_payload  JSONB        DEFAULT '{}'::jsonb,
                    result         JSONB        DEFAULT '{}'::jsonb,
                    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_rule_discernment_email ON rule_discernment_cases(email, created_at DESC)")

            # 十架神学 / 哀歌 — 哀歌记录
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cross_lament_records (
                    id            VARCHAR(64)  PRIMARY KEY,
                    email         VARCHAR(255) NOT NULL,
                    category_key  VARCHAR(40)  DEFAULT '',
                    input_text    TEXT         DEFAULT '',
                    frame         JSONB        DEFAULT '{}'::jsonb,
                    route         VARCHAR(40)  DEFAULT 'cross_lament_hope',
                    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_cross_lament_email ON cross_lament_records(email, created_at DESC)")

            # 圣礼与教会年历 — 主日预备记录
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sacrament_lord_day (
                    id          VARCHAR(64)  PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    season_key  VARCHAR(40)  DEFAULT '',
                    prep        JSONB        DEFAULT '{}'::jsonb,
                    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sacrament_lord_day_email ON sacrament_lord_day(email, created_at DESC)")

            conn.commit()
    finally:
        release_db(conn)

    print('[db] PostgreSQL database initialized ok', flush=True)
