import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import random
import re
import secrets
import smtplib
from datetime import datetime, timezone, timedelta

_SHANGHAI_TZ = timezone(timedelta(hours=8))

def _to_shanghai_iso(dt):
    """Convert a naive or aware datetime to Shanghai (UTC+8) ISO string."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime from DB is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_SHANGHAI_TZ).strftime('%Y-%m-%d %H:%M')
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
import sys
import threading
import time
import traceback
from contextlib import asynccontextmanager
from email.mime.text import MIMEText
from html import escape as html_escape
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

# 安全中间件
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from query_emotion_verses import (
    DEFAULT_RERANK_CANDIDATES,
    DEFAULT_RERANK_WEIGHT,
    EMBEDDING_CACHE_FILE,
    FEATURES_FILE,
    assess_psychological_state,
    call_chat,
    fetch_biblical_example,
    generate_sermon,
    prewarm_cache,
    query_emotion_verses,
    _strip_markdown_json,
)
from web_emotion_query import HISTORY_FILE, load_history, save_history_entry

LAYOUT_FILE = ROOT_DIR / 'emotion_sphere_layout.json'
MATCHES_FILE = ROOT_DIR / 'emotion_exemplar_verse_matches.json'
FRONTEND_DIST = ROOT_DIR / 'emotion-sphere-ui' / 'dist'
STATS_FILE = ROOT_DIR / 'visit_stats.json'
STATS_LOCK = threading.Lock()

# HF Spaces persistence configuration
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')
HF_STATS_REPO = os.getenv('HF_STATS_REPO', 'StephenZao/bible-sphere-stats')  # Default stats dataset
HF_STATS_PATH = os.getenv('HF_STATS_PATH', 'visit_stats.json')

# HF Data source for large files removed from Git LFS
HF_DATA_REPO = os.getenv('HF_DATA_REPO', 'StephenZao/biblesphere')
HF_DATA_FILES: list[tuple[str, int]] = [
    # (filename, min_expected_size_bytes)  -  files auto-downloaded if missing or too small
    ('bible_bilingual_metadata.pkl', 15 * 1024 * 1024),       # ~19 MB
    ('bible_bilingual_vector_cuv.npy', 100 * 1024 * 1024),  # ~127 MB
    ('bible_bilingual_vector_esv.npy', 100 * 1024 * 1024),  # ~127 MB
]

# WeChat Open Platform config
WX_APP_ID = os.getenv('WX_APP_ID', '')
WX_APP_SECRET = os.getenv('WX_APP_SECRET', '')
WX_REDIRECT_URI = os.getenv('WX_REDIRECT_URI', 'http://localhost:8000/api/auth/wechat/callback')

# Email SMTP config (default: sina.com — 465 SSL)
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.sina.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465') or '465')
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USER or 'noreply@bible-sphere.com')
RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')

# 数据库配置 (仅 PostgreSQL)
DATABASE_URL = os.getenv('DATABASE_URL', '')
if not DATABASE_URL:
    print('[db] WARNING: DATABASE_URL not set, database features will be unavailable', flush=True)

# 全局数据库连接池
_db_pool = None
_db_type = 'postgresql'

# In-memory verify code store: email -> {code, expires}
_CODE_STORE: dict[str, dict] = {}
CODE_TTL_SECONDS = 600  # 10 minutes for reset codes

# Code generation helper
def _generate_code() -> str:
    """Generate a 6-digit verification code."""
    return f'{random.randint(0, 999999):06d}'

# ── 输入净化：防止 XSS / HTML 注入 ──────────────────────────
_DANGEROUS_TAG_RE = re.compile(r'<\s*/?\s*(script|iframe|object|embed|link|style|form|input|button|svg|math|meta|base)\b[^>]*>', re.IGNORECASE)
_EVENT_HANDLER_RE = re.compile(r'\s*on\w+\s*=', re.IGNORECASE)

def _sanitize_text(text: str | None) -> str:
    """Strip dangerous HTML tags and event handlers from user text input.
    Preserves angle brackets in harmless contexts (e.g. 'a < b')."""
    if not text:
        return text or ''
    # Remove dangerous tags
    cleaned = _DANGEROUS_TAG_RE.sub('', text)
    # Remove event handler attributes that might survive
    cleaned = _EVENT_HANDLER_RE.sub(' ', cleaned)
    return cleaned.strip()

# ── 日期格式校验 ──────────────────────────────────────────────
DATE_RE = re.compile(r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$')

def _validate_date_str(v: str) -> str:
    """Validate YYYY-MM-DD date format."""
    if not DATE_RE.match(v):
        raise ValueError('日期格式不正确，应为 YYYY-MM-DD')
    return v

# 安全审计日志锁
_AUDIT_LOCK = threading.Lock()

def _init_database():
    """初始化 PostgreSQL 数据库连接。"""
    global _db_pool
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import Json
    import psycopg2.extensions as ext
    ext.register_adapter(dict, Json)
    ext.register_adapter(list, Json)
    _db_pool = psycopg2.pool.ThreadedConnectionPool(1, 20, DATABASE_URL)
    print('[db] PostgreSQL connection pool initialized (max=20)', flush=True)


def _get_db():
    """获取 PostgreSQL 数据库连接。"""
    conn = _db_pool.getconn()
    # Reset connection state if it was left in a broken transaction
    if conn.closed:
        _db_pool.putconn(conn, close=True)
        conn = _db_pool.getconn()
    try:
        conn.autocommit = False
        # Test the connection is alive
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
    except Exception:
        try:
            _db_pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = _db_pool.getconn()
    return conn


def _release_db(conn):
    """释放 PostgreSQL 数据库连接，并回滚未提交的事务。"""
    if conn and not conn.closed:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            _db_pool.putconn(conn)
        except Exception:
            pass


def _security_audit(event_type: str, email: str = None, ip: str = None, details: dict = None, success: bool = True):
    """记录安全审计日志。"""
    with _AUDIT_LOCK:
        # 打印到日志（生产环境应发送到安全日志系统）
        status = 'SUCCESS' if success else 'FAILED'
        print(f'[SECURITY AUDIT] [{status}] {event_type} | email={email} | ip={ip} | details={details}', flush=True)

        # 写入审计日志表
        try:
            ip_value = None
            if ip:
                try:
                    ip_value = str(ipaddress.ip_address(ip))
                except ValueError:
                    ip_value = None
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO security_audit (event_type, email, ip_address, details, success, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    ''', (event_type, email, ip_value, json.dumps(details) if details else '{}', success))
                    conn.commit()
            finally:
                _release_db(conn)
        except Exception as exc:
            print(f'[SECURITY AUDIT] Failed to write to database: {exc}', flush=True)


_CODE_LOCK = threading.Lock()

# In-memory session store: token -> user info
_SESSION_STORE: dict[str, dict] = {}
_SESSION_LOCK = threading.Lock()

EMAIL_RE = re.compile(r'^[\w.+\-]+@[\w\-]+\.[\w.\-]+$')


def _init_db() -> None:
    """初始化 PostgreSQL 数据库表。"""
    print('[db] initializing PostgreSQL database tables...', flush=True)
    _init_db_postgresql()


def _init_db_postgresql():
    """初始化 PostgreSQL 数据库表。"""
    conn = _get_db()
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

            # Seed default demo user: John / John
            _default_email = 'john@bible-sphere.com'
            cur.execute('SELECT id FROM users WHERE LOWER(email) = LOWER(%s)', (_default_email,))
            if not cur.fetchone():
                _default_hash = _hash_password('John')
                cur.execute(
                    'INSERT INTO users (email, nickname, avatar, openid, login_type, password_hash) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (email) DO NOTHING',
                    (_default_email, 'John', '', None, 'email', _default_hash),
                )
                print(f'[db] seeded default user: {_default_email} / John', flush=True)

            # Seed demo user personality profile tags for John
            _john_tags = [
                ('焦虑型', 'emotion_type', 2.5, 0.8, 'work_stress'),
                ('恐惧驱动', 'motive', 1.8, 0.75, 'perfectionism'),
                ('工作领域', 'life_domain', 2.2, 0.9, 'career_focus'),
                ('灵修习惯', 'habit_type', 3.0, 0.85, 'daily_devotion'),
                ('探索期', 'life_stage', 1.5, 0.7, 'seeking_direction'),
                ('真实导向', 'value', 2.0, 0.8, 'authenticity'),
            ]

            for tag_name, category, weight, confidence, context_key in _john_tags:
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
                    _default_email, tag_name, category, 'system', confidence, weight,
                    3, True, False, False,
                    json.dumps({'seeded': True, 'context': context_key})
                ))

            print(f'[db] seeded {len(_john_tags)} personality tags for John', flush=True)

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

            conn.commit()
    finally:
        _release_db(conn)

    print('[db] PostgreSQL database initialized ok', flush=True)


# ── Tag extraction ────────────────────────────────────────────

_TAG_WEIGHT_DECAY = 0.85  # decay old weights on re-encounter


def _extract_tags(data: dict) -> list[tuple[str, str, float]]:
    """Convert checkin payload to (tag_key, tag_value, weight) triples."""
    tags: list[tuple[str, str, float]] = []

    def _add(key: str, value: str, w: float = 1.0):
        if value and value.strip():
            tags.append((key, value.strip(), w))

    # Emotion from sphere
    _add('emotion_label', data.get('emotionLabel', ''), 1.2)
    if data.get('emotionQuery', '').strip():
        # Extract up to 3 meaningful keywords from free text (simplified)
        words = [w for w in data['emotionQuery'].split() if len(w) >= 2][:6]
        _add('emotion_text_summary', ' '.join(words), 1.0)

    # Life scenario
    _add('scenario_category', data.get('scenarioCategory', ''), 1.1)
    _add('scenario_detail', data.get('scenarioDetail', ''), 1.1)

    # Behavioral driver
    _add('driver_type', data.get('driverType', ''), 1.3)
    _add('driver_option', data.get('driverOption', ''), 1.2)

    # Mood / wellbeing
    _add('mood', data.get('mood', ''), 0.8)
    _add('sleep', data.get('sleep', ''), 0.7)
    _add('energy', data.get('energy', ''), 0.7)

    # Free-text signals – store compressed keyword hints
    if data.get('prayerRequest', '').strip():
        words = [w for w in data['prayerRequest'].split() if len(w) >= 2][:8]
        _add('prayer_keywords', ' '.join(words), 0.9)
    if data.get('gratitude', '').strip():
        words = [w for w in data['gratitude'].split() if len(w) >= 2][:6]
        _add('gratitude_keywords', ' '.join(words), 0.8)

    return tags


def _upsert_tags(email: str, tags: list[tuple[str, str, float]]) -> None:
    """Merge new tags into user_tags; decay existing weights on update."""
    print(f'[tags] upsert {len(tags)} tags for {email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            for tag_key, tag_value, weight in tags:
                cur.execute(
                    'SELECT weight FROM user_tags WHERE email=%s AND tag_key=%s',
                    (email, tag_key)
                )
                existing = cur.fetchone()
                if existing:
                    # Blend: decay old value, add new signal
                    new_w = round(existing[0] * _TAG_WEIGHT_DECAY + weight, 3)
                    cur.execute(
                        'UPDATE user_tags SET tag_value=%s, weight=%s, updated_at=NOW() WHERE email=%s AND tag_key=%s',
                        (tag_value, new_w, email, tag_key)
                    )
                else:
                    cur.execute(
                        'INSERT INTO user_tags (email, tag_key, tag_value, weight, updated_at) VALUES (%s,%s,%s,%s,NOW())',
                        (email, tag_key, tag_value, weight)
                    )
            conn.commit()
    finally:
        _release_db(conn)


def _get_user_tags(email: str) -> dict[str, str]:
    """Return {tag_key: tag_value} sorted by weight desc, top-15."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT tag_key, tag_value FROM user_tags WHERE email=%s ORDER BY weight DESC LIMIT 15',
                (email,)
            )
            rows = cur.fetchall()
            return {row[0]: row[1] for row in rows}
    finally:
        _release_db(conn)


def _build_user_context_prompt(tags: dict[str, str]) -> str:
    """Convert user tags into a compact context string for prompt injection."""
    if not tags:
        return ''
    lines = []
    label_map = {
        'emotion_label': '当前情绪',
        'emotion_text_summary': '情绪描述关键词',
        'scenario_category': '生活处境类型',
        'scenario_detail': '具体处境',
        'driver_type': '内在驱动类型',
        'driver_option': '行为驱动表现',
        'mood': '今日心情',
        'sleep': '睡眠状态',
        'energy': '精力状态',
        'prayer_keywords': '代祷关键词',
        'gratitude_keywords': '感恩关键词',
        'chat_spiritual_stage': '属灵成长阶段',
        'chat_dominant_emotion': '对话情绪',
        'chat_core_struggle': '核心挣扎',
        'chat_spiritual_need': '属灵需要',
        'chat_life_theme': '生命主题',
        'chat_growth_signal': '成长信号',
        'chat_decline_signal': '低落信号',
    }
    for key, value in tags.items():
        label = label_map.get(key, key)
        lines.append(f'  - {label}：{value}')
    return '【用户背景（仅供参考，请勿直接引用）】\n' + '\n'.join(lines)


# ── Chat tag extraction ───────────────────────────────────────

_CHAT_TAG_EXTRACT_PROMPT = """你是一位属灵辅导助手。请从以下对话中提取用户当前的属灵/心理状态标签。
返回严格 JSON 格式，包含以下字段（值为空字符串表示未识别）：
{
  "spiritual_stage": "属灵成长阶段，如：初信者/成长期/低谷期/复兴期/成熟期",
  "dominant_emotion": "当前主导情绪，如：焦虑/平安/愤怒/盼望/绝望/感恩",
  "core_struggle": "核心挣扎，简短描述，如：对神的信任/自我价值感/人际张力",
  "spiritual_need": "属灵需要，如：需要安慰/需要引导/需要悔改/需要力量",
  "life_theme": "当前生命主题，如：婚姻/职场/信仰危机/成长阵痛/恩典经历",
  "growth_signal": "正向信号，如：开始悔改/寻求神/感恩增加/信心增长（无则留空）",
  "decline_signal": "下降信号，如：疏远神/苦毒加深/绝望增加（无则留空）"
}
只返回 JSON，不要任何说明。"""


def _extract_tags_from_chat_bg(email: str, messages: list[dict]) -> None:
    """Background task: extract spiritual tags from conversation and upsert."""
    print(f'[chat_tags] starting bg extraction for {email}, messages={len(messages)}', flush=True)
    try:
        # Only use last 10 turns to keep context focused
        recent = messages[-10:]
        conv_text = '\n'.join(
            f"{m['role'].upper()}: {m['content']}" for m in recent
        )
        raw = call_chat(_CHAT_TAG_EXTRACT_PROMPT, conv_text)
        raw = _strip_markdown_json(raw)
        parsed = json.loads(raw)

        tags: list[tuple[str, str, float]] = []
        weight_map = {
            'spiritual_stage': 1.4,
            'dominant_emotion': 1.3,
            'core_struggle': 1.3,
            'spiritual_need': 1.2,
            'life_theme': 1.1,
            'growth_signal': 1.5,   # positive signal gets extra boost
            'decline_signal': 1.5,  # decline signal too – important to track
        }
        for key, weight in weight_map.items():
            val = str(parsed.get(key, '')).strip()
            if val:
                tags.append((f'chat_{key}', val, weight))

        if tags:
            _upsert_tags(email, tags)
            print(f'[chat_tags] {email}: extracted {len(tags)} tags', flush=True)
    except Exception as exc:
        print(f'[chat_tags] extraction failed for {email}: {exc}', flush=True)


# ── end Tag extraction ─────────────────────────────────────────


def _hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码（若可用），否则使用 SHA256+salt。"""
    if BCRYPT_AVAILABLE:
        # bcrypt 自动处理 salt，cost factor 12（约 250ms）
        return 'bcrypt:' + bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    # 降级方案：SHA256 + 随机 salt
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f'sha256:{salt}:{digest}'


def _verify_password(password: str, stored: str) -> bool:
    """验证密码，支持 bcrypt 和旧版 SHA256。"""
    try:
        if not stored or stored.strip() == '':
            print('[auth] verify_password: empty stored hash', flush=True)
            return False
        if stored.startswith('bcrypt:'):
            if not BCRYPT_AVAILABLE:
                return False
            hash_value = stored[7:]  # 移除 'bcrypt:' 前缀
            return bcrypt.checkpw(password.encode('utf-8'), hash_value.encode('utf-8'))
        elif stored.startswith('sha256:'):
            _, salt, digest = stored.split(':', 2)
            return hmac.compare_digest(
                hashlib.sha256((salt + password).encode()).hexdigest(),
                digest
            )
        elif ':' in stored:
            # 兼容旧版格式（无前缀，但包含冒号分隔的 salt:digest）
            salt, digest = stored.split(':', 1)
            return hmac.compare_digest(
                hashlib.sha256((salt + password).encode()).hexdigest(),
                digest
            )
        else:
            print(f'[auth] verify_password: unknown hash format, length={len(stored)}', flush=True)
            return False
    except Exception as exc:
        print(f'[auth] verify_password error: {exc}', flush=True)
        return False


def _get_user(email: str) -> dict | None:
    """Get user by email (case-insensitive lookup)."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, email, nickname, avatar, openid, unionid, login_type, password_hash, created_at FROM users WHERE LOWER(email) = LOWER(%s)', (email,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'email': row[1], 'nickname': row[2], 'avatar': row[3],
                'openid': row[4], 'unionid': row[5], 'login_type': row[6], 'password_hash': row[7] or '',
                'created_at': row[8].timestamp() if row[8] else None
            }
    finally:
        _release_db(conn)


def _create_user(email: str, nickname: str, avatar: str, openid: str | None, password_hash: str) -> dict:
    print(f'[auth] creating user email={email} nickname={nickname}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO users (email, nickname, avatar, openid, login_type, password_hash) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id',
                (email, nickname, avatar, openid, 'email', password_hash),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        return {
            'id': user_id,
            'email': email,
            'nickname': nickname,
            'avatar': avatar,
            'openid': openid,
            'unionid': None,
            'login_type': 'email',
            'created_at': time.time(),
        }
    finally:
        _release_db(conn)


def _migrate_json_users() -> None:
    """One-time migration: import users.json into PostgreSQL if it exists."""
    json_file = ROOT_DIR / 'users.json'
    if not json_file.exists():
        return
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                for email, u in users.items():
                    cur.execute(
                        '''INSERT INTO users (email, nickname, avatar, openid, login_type, password_hash)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (email) DO NOTHING''',
                        (email, u.get('nickname', ''), u.get('avatar', ''), u.get('openid') or None, u.get('login_type', 'email'), u.get('password_hash', '')),
                    )
                conn.commit()
            json_file.rename(json_file.with_suffix('.json.bak'))
            print('[db] Migrated users.json → PostgreSQL', flush=True)
        finally:
            _release_db(conn)
    except Exception as exc:
        print(f'[db] Migration skipped: {exc}', flush=True)


def _send_email(to: str, subject: str, body: str) -> None:
    """Send email via SendGrid, Resend API, or SMTP fallback."""
    # 1. Try SendGrid first (most reliable, no domain verification needed)
    if SENDGRID_API_KEY:
        try:
            resp = httpx.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={'Authorization': f'Bearer {SENDGRID_API_KEY}', 'Content-Type': 'application/json'},
                json={
                    'personalizations': [{'to': [{'email': to}]}],
                    'from': {'email': SMTP_FROM or 'noreply@bible-sphere.com'},
                    'subject': subject,
                    'content': [{'type': 'text/plain', 'value': body}],
                },
                timeout=20,
            )
            resp.raise_for_status()
            print(f'[email] SendGrid OK to {to}', flush=True)
            return
        except Exception as exc:
            detail = str(exc)
            try:
                if hasattr(exc, 'response') and exc.response is not None:
                    detail += f' | body: {exc.response.text}'
            except Exception:
                pass
            print(f'[email] SendGrid failed: {detail}', flush=True)
            # Fall through to Resend

    # 2. Try Resend API (requires domain verification for non-owner emails)
    if RESEND_API_KEY:
        # Use configured SMTP_FROM (e.g., noreply@holiness.uk) or fallback to resend.dev
        from_addr = SMTP_FROM if SMTP_FROM else 'onboarding@resend.dev'
        try:
            resp = httpx.post(
                'https://api.resend.com/emails',
                headers={'Authorization': f'Bearer {RESEND_API_KEY}', 'Content-Type': 'application/json'},
                json={
                    'from': from_addr,
                    'to': [to],
                    'subject': subject,
                    'text': body,
                },
                timeout=20,
            )
            resp.raise_for_status()
            print(f'[email] Resend OK to {to}: {resp.json().get("id", "no-id")}', flush=True)
            return
        except Exception as exc:
            detail = str(exc)
            try:
                if hasattr(exc, 'response') and exc.response is not None:
                    detail += f' | body: {exc.response.text}'
            except Exception:
                pass
            print(f'[email] Resend failed: {detail}', flush=True)
            # Fall through to SMTP

    # 3. Fallback to SMTP (sina, qq, etc.)
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.set_debuglevel(1)  # Print SMTP debug to stdout for troubleshooting
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_FROM, [to], msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.set_debuglevel(1)
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_FROM, [to], msg.as_string())


def _make_session(user_record: dict) -> str:
    token = secrets.token_urlsafe(32)
    email = user_record.get('email', '')
    data_json = json.dumps(user_record, ensure_ascii=False)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO user_tokens (token, email, data, created_at, expires_at)
                   VALUES (%s, %s, %s, NOW(), NOW() + INTERVAL '30 days')
                   ON CONFLICT (token) DO UPDATE
                   SET email = EXCLUDED.email, data = EXCLUDED.data,
                       created_at = EXCLUDED.created_at, expires_at = EXCLUDED.expires_at''',
                (token, email, data_json)
            )
            conn.commit()
    finally:
        _release_db(conn)
    with _SESSION_LOCK:
        _SESSION_STORE[token] = user_record
    return token


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    topFeatures: int = Field(default=5, ge=1, le=20)
    topVerses: int = Field(default=5, ge=1, le=20)
    languageFilter: str = Field(default='both')
    includeGuidance: bool = False
    enableRerank: bool = False
    rerankCandidates: int = Field(default=DEFAULT_RERANK_CANDIDATES, ge=1, le=100)
    rerankWeight: float = Field(default=DEFAULT_RERANK_WEIGHT, ge=0.0, le=1.0)
    rerankMode: str = Field(default='llm')


class GuidanceRequest(BaseModel):
    query: str = Field(min_length=1)


class SermonRequest(BaseModel):
    query: str = Field(min_length=1)


class PunctuationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class VisitTrackRequest(BaseModel):
    visitorId: str = Field(min_length=1, max_length=128)


class WechatTokenVerifyRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class ChatMessageItem(BaseModel):
    role: str = Field(pattern='^(user|assistant)$')
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    session_id: str = Field(default='', max_length=64)
    messages: list[ChatMessageItem] = Field(min_length=1, max_length=40)


class CheckinRequest(BaseModel):
    emotionLabel: str = Field(default='', max_length=64)
    emotionQuery: str = Field(default='', max_length=1000)
    scenarioCategory: str = Field(default='', max_length=64)
    scenarioDetail: str = Field(default='', max_length=128)
    driverType: str = Field(default='', max_length=64)
    driverOption: str = Field(default='', max_length=128)
    mood: str = Field(default='', max_length=16)
    sleep: str = Field(default='', max_length=16)
    energy: str = Field(default='', max_length=16)
    prayerRequest: str = Field(default='', max_length=500)
    gratitude: str = Field(default='', max_length=500)


class EmailSendCodeRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class EmailRegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(default='', max_length=64)


class EmailLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def _download_hf_data_files() -> None:
    """Download large model files from Hugging Face if missing or too small (LFS pointer)."""
    import urllib.request

    for filename, min_size in HF_DATA_FILES:
        path = ROOT_DIR / filename
        current_size = path.stat().st_size if path.exists() else 0

        if current_size >= min_size:
            print(f'[startup] {filename}: {current_size / 1024 / 1024:.1f} MB - OK', flush=True)
            continue

        url = f'https://huggingface.co/spaces/{HF_DATA_REPO}/resolve/main/{filename}'
        print(f'[startup] {filename}: {current_size} bytes (need {min_size / 1024 / 1024:.0f} MB) - downloading from HF...', flush=True)
        print(f'[startup] URL: {url}', flush=True)

        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'bible-sphere-backend/1.0')
            with urllib.request.urlopen(req, timeout=120) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                chunk_size = 1024 * 1024  # 1 MB chunks
                downloaded = 0

                with open(path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = downloaded / total_size * 100
                            if downloaded % (5 * chunk_size) < chunk_size:
                                print(f'[startup] {filename}: {pct:.0f}% ({downloaded / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB)', flush=True)

            final_size = path.stat().st_size
            print(f'[startup] {filename}: downloaded {final_size / 1024 / 1024:.1f} MB', flush=True)

            if final_size < min_size:
                print(f'[startup] WARNING: {filename} size {final_size} < expected {min_size}, may be incomplete', flush=True)
        except Exception as exc:
            print(f'[startup] ERROR downloading {filename}: {exc}', flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB, migrate old data, download model files, pre-warm cache at startup."""
    # 初始化数据库连接（优先 PostgreSQL）
    if DATABASE_URL:
        try:
            _init_database()
            _init_db()
            # 初始化决策支撑系统表
            try:
                conn = _get_db()
                try:
                    with conn.cursor() as cur:
                        cur.execute(SFDS_TABLES_SQL)
                        conn.commit()
                        print('[sfds] decision support tables initialized', flush=True)
                finally:
                    _release_db(conn)
            except Exception as exc:
                print(f'[sfds] WARNING: SFDS tables init failed: {exc}', flush=True)
            # 执行 v3.2 migration（添加 12 维度字段）
            try:
                conn = _get_db()
                try:
                    with conn.cursor() as cur:
                        cur.execute(SFDS_MIGRATION_V32_SQL)
                        conn.commit()
                        print('[sfds] v3.2 migration applied (12-dimension columns)', flush=True)
                finally:
                    _release_db(conn)
            except Exception as exc:
                print(f'[sfds] WARNING: v3.2 migration failed: {exc}', flush=True)
            
            # 创建 behavior_history 表 (Neon 兼容版本，无 hypertable)
            try:
                conn = _get_db()
                try:
                    with conn.cursor() as cur:
                        cur.execute('''
                            CREATE TABLE IF NOT EXISTS sfds_behavior_history (
                                id BIGSERIAL PRIMARY KEY,
                                user_id TEXT NOT NULL,
                                session_id TEXT NOT NULL,
                                executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                task TEXT NOT NULL,
                                original_task TEXT,
                                energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 5) DEFAULT 3,
                                motivation INTEGER CHECK (motivation BETWEEN 1 AND 10) DEFAULT 5,
                                tier_executed VARCHAR(20) NOT NULL DEFAULT 'Yellow',
                                min_executable_action TEXT,
                                task_downgrade TEXT,
                                emotional_compensation TEXT,
                                continuity_advice TEXT,
                                was_completed BOOLEAN NOT NULL DEFAULT FALSE,
                                completion_percentage INTEGER CHECK (completion_percentage BETWEEN 0 AND 100) DEFAULT 0,
                                resistance_at_start INTEGER CHECK (resistance_at_start BETWEEN 1 AND 10),
                                system_energy_state VARCHAR(20) DEFAULT 'normal',
                                shame_prevented BOOLEAN NOT NULL DEFAULT FALSE,
                                spiritual_alignment TEXT
                            )
                        ''')
                        cur.execute('CREATE INDEX IF NOT EXISTS idx_sfds_behavior_user_time ON sfds_behavior_history (user_id, executed_at DESC)')
                        cur.execute('CREATE INDEX IF NOT EXISTS idx_sfds_behavior_tier ON sfds_behavior_history (user_id, tier_executed)')
                        # 为已存在的表添加 spiritual_alignment 字段
                        try:
                            cur.execute('ALTER TABLE sfds_behavior_history ADD COLUMN IF NOT EXISTS spiritual_alignment TEXT')
                            conn.commit()
                        except Exception:
                            pass
                        conn.commit()
                        print('[sfds] behavior_history table initialized', flush=True)
                finally:
                    _release_db(conn)
            except Exception as exc:
                print(f'[sfds] WARNING: behavior_history init failed: {exc}', flush=True)
            # 初始化 SFDS 存储（即使表创建失败也要初始化，表可能已存在）
            try:
                init_sfds_storage(_db_pool)
                print('[sfds] SFDS storage initialized', flush=True)
            except Exception as exc:
                print(f'[sfds] WARNING: SFDS storage init failed: {exc}', flush=True)
            # 初始化 V2 引擎 (Graph + Temporal)
            try:
                init_v2_engine(_db_pool)
                print('[sfds] V2 engine (graph + temporal) initialized', flush=True)
            except Exception as exc:
                print(f'[sfds] WARNING: V2 engine init failed: {exc}', flush=True)
        except Exception as exc:
            print(f'[db] ERROR: database init failed: {exc}', flush=True)
    else:
        print('[db] Skipping database init (DATABASE_URL not set)', flush=True)
    if DATABASE_URL:
        _migrate_json_users()
    try:
        await asyncio.to_thread(_download_hf_data_files)
    except Exception as exc:
        print(f'[startup] download failed: {exc}', flush=True)
    try:
        await asyncio.to_thread(prewarm_cache)
        print('[startup] cache pre-warmed', flush=True)
    except Exception as exc:
        print(f'[startup] prewarm failed: {exc}', flush=True)
    # 初始化 MVFE Formation Engine
    try:
        await asyncio.to_thread(init_mvfe, _db_pool)
        print('[mvfe] Formation Engine initialized', flush=True)
    except Exception as exc:
        print(f'[mvfe] WARNING: MVFE init failed: {exc}', flush=True)
    # 初始化 V3 Formation Engine (sfds)
    try:
        from formation_engine import init_formation_engine
        init_formation_engine(_db_pool)
        print('[formation] V3 Formation Engine initialized with db_pool', flush=True)
    except Exception as exc:
        print(f'[formation] WARNING: V3 Formation Engine init failed: {exc}', flush=True)
    # 初始化用户标签系统
    try:
        from user_tag_system import init_tag_store
        init_tag_store(_db_pool)
        print('[tags] User Tag System initialized', flush=True)
    except Exception as exc:
        print(f'[tags] WARNING: User Tag System init failed: {exc}', flush=True)
    yield


# 初始化速率限制器（Redis 可选，默认内存存储）
limiter = Limiter(key_func=get_remote_address)

# 导入决策支撑系统 (V1 + V2)
from decision_support import router as sfds_router, SFDS_TABLES_SQL, init_sfds_storage, init_v2_engine

# SFDS v3.2 Migration SQL - Add 12-dimension state snapshot columns
SFDS_MIGRATION_V32_SQL = """
-- 添加缺失的 12 维度字段到 sfds_decision_events
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='stress_level') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='anxiety_level') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN anxiety_level INTEGER CHECK (anxiety_level BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='fatigue_level') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN fatigue_level INTEGER CHECK (fatigue_level BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='spiritual_dryness') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN spiritual_dryness INTEGER CHECK (spiritual_dryness BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='emotional_stability') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN emotional_stability INTEGER CHECK (emotional_stability BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='physical_health') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN physical_health INTEGER CHECK (physical_health BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='sleep_quality') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='social_connection') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN social_connection INTEGER CHECK (social_connection BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='financial_pressure') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN financial_pressure INTEGER CHECK (financial_pressure BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='cognitive_clarity') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN cognitive_clarity INTEGER CHECK (cognitive_clarity BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='identity_confusion') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN identity_confusion INTEGER CHECK (identity_confusion BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='moral_tension') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN moral_tension INTEGER CHECK (moral_tension BETWEEN 0 AND 10) DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='emotion_logs') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN emotion_logs JSONB DEFAULT '[]'::jsonb;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='sfds_decision_events' AND column_name='status') THEN
        ALTER TABLE sfds_decision_events ADD COLUMN status TEXT DEFAULT 'analyzing';
    END IF;
END $$;
"""

# 导入 MVFE (Minimum Viable Formation Engine)
from mvfe.setup import init_mvfe
from mvfe.api.routes import router as mvfe_router

# 导入用户标签系统
from user_tag_routes import router as user_tag_router

app = FastAPI(title='Bible Emotion Sphere API', lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 包含决策支撑系统路由
app.include_router(sfds_router)

# 包含 MVFE 路由
app.include_router(mvfe_router)

# 包含用户标签系统路由
app.include_router(user_tag_router)

# 安全 CORS 配置（生产环境应限制具体域名）
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
if '*' in ALLOWED_ORIGINS:
    # 开发环境
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['*'],
        expose_headers=['X-RateLimit-Limit', 'X-RateLimit-Remaining'],
    )
else:
    # 生产环境
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'X-Requested-With'],
        expose_headers=['X-RateLimit-Limit', 'X-RateLimit-Remaining'],
    )

# 安全响应头中间件
@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    # 安全响应头
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # Content-Security-Policy: 禁止内联脚本，防止 XSS 攻击
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self' https: wss:; "
        "frame-ancestors 'none'"
    )
    # HSTS（仅在 HTTPS 环境）
    if request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log exact validation errors for debugging 422s."""
    errors = json.loads(json.dumps(exc.errors(), default=str))
    print(f'[VALIDATION ERROR] {request.method} {request.url.path}: {errors}', flush=True)
    return JSONResponse(
        status_code=422,
        content={'detail': errors, 'body': str(exc.body) if hasattr(exc, 'body') else None}
    )


# ── 全局异常处理器：提升健壮性 ────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions to return clean JSON errors and avoid leaking stack traces."""
    # DB pool exhaustion
    err_name = type(exc).__name__
    if 'PoolError' in err_name or 'pool' in str(exc).lower():
        print(f'[ERROR] DB pool exhausted: {exc}', flush=True)
        return JSONResponse(status_code=503, content={'ok': False, 'detail': 'Service temporarily unavailable. Please retry.'})
    # Connection errors
    if 'OperationalError' in err_name or 'InterfaceError' in err_name:
        print(f'[ERROR] DB connection error: {exc}', flush=True)
        return JSONResponse(status_code=503, content={'ok': False, 'detail': 'Database connection error. Please retry.'})
    # Pydantic validation errors (should be caught by FastAPI, but just in case)
    if 'ValidationError' in err_name:
        print(f'[ERROR] Validation: {exc}', flush=True)
        return JSONResponse(status_code=422, content={'ok': False, 'detail': str(exc)})
    # Generic fallback
    print(f'[ERROR] Unhandled {err_name}: {exc}', flush=True)
    traceback.print_exc()
    return JSONResponse(status_code=500, content={'ok': False, 'detail': 'Internal server error'})


def load_json_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def build_feature_match_map() -> dict[str, dict]:
    match_map = {}
    for item in load_json_file(MATCHES_FILE):
        key = f"{item.get('layer')}:{item.get('feature_id')}"
        match_map[key] = item
    return match_map


def _hf_hub_upload(stats: dict) -> bool:
    """Upload stats to HF Hub as a JSON file. Returns True on success."""
    if not HF_TOKEN:
        return False
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=HF_TOKEN)
        # Ensure repo exists (create if not)
        try:
            api.repo_info(repo_id=HF_STATS_REPO, repo_type='dataset')
        except Exception:
            api.create_repo(repo_id=HF_STATS_REPO, repo_type='dataset', private=False, exist_ok=True)
        # Upload file content
        content = json.dumps(stats, ensure_ascii=False, indent=2)
        from io import BytesIO
        api.upload_file(
            path_or_fileobj=BytesIO(content.encode('utf-8')),
            path_in_repo=HF_STATS_PATH,
            repo_id=HF_STATS_REPO,
            repo_type='dataset',
            commit_message=f'Update stats: {stats["page_views"]} views, {stats["unique_visitors"]} visitors'
        )
        print(f'[stats] uploaded to HF Hub: {HF_STATS_REPO}/{HF_STATS_PATH}', flush=True)
        return True
    except Exception as exc:
        print(f'[stats] HF Hub upload failed: {exc}', flush=True)
        return False


def _hf_hub_download() -> dict | None:
    """Download stats from HF Hub. Returns dict on success, None on failure."""
    if not HF_TOKEN:
        return None
    try:
        from huggingface_hub import hf_hub_download
        from io import BytesIO
        # Try to download the stats file
        path = hf_hub_download(
            repo_id=HF_STATS_REPO,
            filename=HF_STATS_PATH,
            repo_type='dataset',
            token=HF_TOKEN
        )
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f'[stats] loaded from HF Hub: {HF_STATS_REPO}/{HF_STATS_PATH}', flush=True)
        return {
            'page_views': int(data.get('page_views', 0)),
            'unique_visitors': int(data.get('unique_visitors', 0)),
            'visitor_ids': list(data.get('visitor_ids', [])),
        }
    except Exception as exc:
        print(f'[stats] HF Hub download skipped: {exc}', flush=True)
        return None


def load_visit_stats() -> dict:
    # Try HF Hub first if token is available
    if HF_TOKEN:
        hf_stats = _hf_hub_download()
        if hf_stats is not None:
            # Merge HF data with local if both exist
            if STATS_FILE.exists():
                local = _load_local_stats()
                # Use whichever has more visitors (assumes that's the more complete dataset)
                if len(hf_stats.get('visitor_ids', [])) >= len(local.get('visitor_ids', [])):
                    return hf_stats
                else:
                    # Local has more data, save to HF Hub
                    _hf_hub_upload(local)
                    return local
            return hf_stats
    # Fall back to local file
    return _load_local_stats()


def _load_local_stats() -> dict:
    if not STATS_FILE.exists():
        return {'page_views': 0, 'unique_visitors': 0, 'visitor_ids': []}
    with open(STATS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return {
        'page_views': int(data.get('page_views', 0)),
        'unique_visitors': int(data.get('unique_visitors', 0)),
        'visitor_ids': list(data.get('visitor_ids', [])),
    }


def save_visit_stats(stats: dict) -> None:
    # Always save locally
    with open(STATS_FILE, 'w', encoding='utf-8') as file:
        json.dump(stats, file, ensure_ascii=False, indent=2)
    # Also upload to HF Hub if token is available
    if HF_TOKEN:
        _hf_hub_upload(stats)


def public_visit_stats(stats: dict) -> dict:
    return {
        'page_views': int(stats.get('page_views', 0)),
        'unique_visitors': int(stats.get('unique_visitors', 0)),
    }


def track_visit(visitor_id: str) -> dict:
    normalized_id = visitor_id.strip()
    with STATS_LOCK:
        stats = load_visit_stats()
        stats['page_views'] = int(stats.get('page_views', 0)) + 1
        visitor_ids = set(stats.get('visitor_ids', []))
        if normalized_id not in visitor_ids:
            visitor_ids.add(normalized_id)
        stats['visitor_ids'] = sorted(visitor_ids)
        stats['unique_visitors'] = len(stats['visitor_ids'])
        save_visit_stats(stats)
        return public_visit_stats(stats)


@app.get('/api/health')
def health() -> dict:
    return {'ok': True}


@app.get('/api/auth/wechat/login')
def wechat_login():
    """Redirect to WeChat OAuth2 authorization page (PC QR code)."""
    if not WX_APP_ID:
        raise HTTPException(status_code=500, detail='WX_APP_ID not configured')
    state = secrets.token_urlsafe(16)
    url = (
        'https://open.weixin.qq.com/connect/qrconnect'
        f'?appid={WX_APP_ID}'
        f'&redirect_uri={WX_REDIRECT_URI}'
        '&response_type=code'
        '&scope=snsapi_login'
        f'&state={state}'
        '#wechat_redirect'
    )
    return RedirectResponse(url)


@app.get('/api/auth/wechat/mobile')
def wechat_mobile_login(
    scope: str = Query(default='snsapi_userinfo', pattern='^(snsapi_base|snsapi_userinfo)$'),
    redirect_type: str = Query(default='mobile', pattern='^(mobile|pc)$'),
    frontend_url: str = Query(default=''),
):
    """WeChat H5 OAuth2 authorization (for mobile browser within WeChat).
    
    Args:
        scope: snsapi_base (silent, only openid) or snsapi_userinfo (with consent, gets nickname/avatar)
        redirect_type: 'mobile' for H5 page, 'pc' for desktop
        frontend_url: Optional custom frontend URL to redirect back to
    """
    if not WX_APP_ID:
        raise HTTPException(status_code=500, detail='WX_APP_ID not configured')
    
    # Build state with redirect info
    state_data = {
        'type': redirect_type,
        'scope': scope,
        'frontend': frontend_url or '',
        'random': secrets.token_urlsafe(8),
    }
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode().rstrip('=')
    
    # Mobile OAuth2 uses different endpoint than PC QR connect
    url = (
        'https://open.weixin.qq.com/connect/oauth2/authorize'
        f'?appid={WX_APP_ID}'
        f'&redirect_uri={WX_REDIRECT_URI}'
        '&response_type=code'
        f'&scope={scope}'
        f'&state={state}'
        '#wechat_redirect'
    )
    return RedirectResponse(url)


@app.get('/api/auth/wechat/callback')
async def wechat_callback(code: str = Query(min_length=1), state: str = Query(default='')):
    """Exchange code for openid and create session token."""
    print(f'[auth] wechat callback received code={code[:8]}... state={state}', flush=True)
    if not WX_APP_ID or not WX_APP_SECRET:
        raise HTTPException(status_code=500, detail='WeChat credentials not configured')

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                'https://api.weixin.qq.com/sns/oauth2/access_token',
                params={
                    'appid': WX_APP_ID,
                    'secret': WX_APP_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                },
                timeout=10,
            )
        data = resp.json()
    except Exception as exc:
        print(f'[auth] wechat access_token request failed: {exc}', flush=True)
        raise HTTPException(status_code=502, detail='微信服务暂时不可用，请稍后重试') from exc

    if 'errcode' in data:
        raise HTTPException(status_code=401, detail=f'WeChat error: {data.get("errmsg", data)}')

    openid = data.get('openid', '')
    unionid = data.get('unionid', '')
    access_token = data.get('access_token', '')

    # Fetch basic user info from WeChat (non-critical: degrade gracefully)
    user_info = {}
    if access_token and openid:
        try:
            async with httpx.AsyncClient() as client:
                info_resp = await client.get(
                    'https://api.weixin.qq.com/sns/userinfo',
                    params={'access_token': access_token, 'openid': openid, 'lang': 'zh_CN'},
                    timeout=10,
                )
            user_info = info_resp.json()
        except Exception as exc:
            print(f'[auth] wechat userinfo fetch failed (non-critical): {exc}', flush=True)

    # Get or create user in database
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Try to find existing user by openid
            cur.execute(
                'SELECT id, email, nickname, avatar, openid, unionid FROM users WHERE openid = %s',
                (openid,)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update user info
                user_id = existing[0]
                cur.execute(
                    '''UPDATE users SET 
                       nickname = COALESCE(NULLIF(%s, ''), nickname),
                       avatar = COALESCE(NULLIF(%s, ''), avatar),
                       unionid = COALESCE(%s, unionid)
                       WHERE id = %s''',
                    (user_info.get('nickname', ''), user_info.get('headimgurl', ''), unionid, user_id)
                )
                conn.commit()
                user_record = {
                    'id': user_id,
                    'openid': openid,
                    'unionid': unionid or existing[5],
                    'nickname': user_info.get('nickname') or existing[2] or '',
                    'avatar': user_info.get('headimgurl') or existing[3] or '',
                    'email': existing[1],
                }
            else:
                # Create new WeChat user
                cur.execute(
                    '''INSERT INTO users (openid, unionid, nickname, avatar, login_type)
                       VALUES (%s, %s, %s, %s, 'wechat') RETURNING id''',
                    (openid, unionid, user_info.get('nickname', ''), user_info.get('headimgurl', ''))
                )
                user_id = cur.fetchone()[0]
                conn.commit()
                user_record = {
                    'id': user_id,
                    'openid': openid,
                    'unionid': unionid,
                    'nickname': user_info.get('nickname', ''),
                    'avatar': user_info.get('headimgurl', ''),
                    'email': None,
                }
    finally:
        _release_db(conn)
    
    # Create session
    session_token = secrets.token_urlsafe(32)
    with _SESSION_LOCK:
        _SESSION_STORE[session_token] = user_record
    
    print(f'[auth] wechat login ok openid={openid} user_id={user_id} nickname={user_record["nickname"]}', flush=True)
    
    # Parse state to determine redirect target
    redirect_target = WX_REDIRECT_URI.rsplit('/api/', 1)[0]  # default PC redirect
    is_mobile = False
    
    if state:
        try:
            # Try to parse as JSON (new mobile format)
            state_padding = state + '=' * (4 - len(state) % 4)
            state_data = json.loads(base64.urlsafe_b64decode(state_padding).decode())
            redirect_type = state_data.get('type', 'pc')
            custom_frontend = state_data.get('frontend', '')
            
            if redirect_type == 'mobile':
                is_mobile = True
                # For mobile, use custom frontend URL if provided, otherwise same domain
                if custom_frontend:
                    redirect_target = custom_frontend.rstrip('/')
            elif custom_frontend:
                redirect_target = custom_frontend.rstrip('/')
                
            print(f'[auth] state parsed: type={redirect_type}, is_mobile={is_mobile}', flush=True)
        except Exception:
            # Old format state or invalid, use default redirect
            pass
    
    return RedirectResponse(f'{redirect_target}/?token={session_token}')


@app.get('/api/auth/me')
def auth_me(request: Request):
    """Verify session token, return user info."""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid or expired session')
    return {'ok': True, 'user': user}


@app.post('/api/auth/logout')
def auth_logout(request: Request):
    """Invalidate session token."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header[7:].strip() if auth_header.startswith('Bearer ') else ''
    if token:
        with _SESSION_LOCK:
            _SESSION_STORE.pop(token, None)
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM user_tokens WHERE token = %s', (token,))
                conn.commit()
        finally:
            _release_db(conn)
    return {'ok': True}


# ==================== WeChat Mini Program Login ====================

class MiniProgramLoginRequest(BaseModel):
    code: str = Field(min_length=1)
    appid: str = Field(default='', max_length=64)
    user_info: dict = Field(default_factory=dict)


class MiniProgramUpdateProfileRequest(BaseModel):
    nickname: str = Field(default='', max_length=64)
    avatar: str = Field(default='', max_length=512)
    gender: int = Field(default=0, ge=0, le=2)
    city: str = Field(default='', max_length=64)
    province: str = Field(default='', max_length=64)
    country: str = Field(default='', max_length=64)


@app.post('/api/auth/wechat/miniprogram/login')
async def wechat_miniprogram_login(request: Request, payload: MiniProgramLoginRequest):
    """WeChat Mini Program login - exchange code for openid and create session.
    
    This endpoint is used by WeChat Mini Programs to authenticate users.
    The Mini Program calls wx.login() to get a code, then sends it here.
    """
    print(f'[auth] miniprogram login request code={payload.code[:8]}...', flush=True)
    
    if not WX_APP_ID or not WX_APP_SECRET:
        raise HTTPException(status_code=500, detail='WeChat Mini Program credentials not configured')
    
    # Use provided appid or fall back to configured one
    appid = payload.appid or WX_APP_ID
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                'https://api.weixin.qq.com/sns/jscode2session',
                params={
                    'appid': appid,
                    'secret': WX_APP_SECRET,
                    'js_code': payload.code,
                    'grant_type': 'authorization_code',
                },
                timeout=10,
            )
        data = resp.json()
    except Exception as exc:
        print(f'[auth] miniprogram jscode2session request failed: {exc}', flush=True)
        raise HTTPException(status_code=502, detail='微信服务暂时不可用，请稍后重试') from exc
    
    if 'errcode' in data:
        print(f'[auth] miniprogram login failed: {data}', flush=True)
        raise HTTPException(status_code=401, detail=f'WeChat error: {data.get("errmsg", data)}')
    
    openid = data.get('openid', '')
    unionid = data.get('unionid', '')
    
    if not openid:
        raise HTTPException(status_code=401, detail='Failed to get openid from WeChat')
    
    print(f'[auth] miniprogram login success openid={openid[:16]}...', flush=True)
    
    # Get or create user in database
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Try to find existing user by openid
            cur.execute(
                'SELECT id, email, nickname, avatar, openid, unionid FROM users WHERE openid = %s',
                (openid,)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update user info
                user_id = existing[0]
                cur.execute(
                    '''UPDATE users SET 
                       unionid = COALESCE(%s, unionid),
                       login_type = 'wechat_miniprogram',
                       last_login_at = NOW()
                       WHERE id = %s''',
                    (unionid, user_id)
                )
                conn.commit()
                user_record = {
                    'id': user_id,
                    'openid': openid,
                    'unionid': unionid or existing[5],
                    'nickname': existing[2] or '',
                    'avatar': existing[3] or '',
                    'email': existing[1],
                    'login_type': 'wechat_miniprogram',
                }
            else:
                # Create new WeChat Mini Program user
                # Generate a placeholder email using openid
                placeholder_email = f'wxmp_{openid[:16]}@wechat.miniprogram'
                cur.execute(
                    '''INSERT INTO users (openid, unionid, email, nickname, avatar, login_type, created_at)
                       VALUES (%s, %s, %s, %s, %s, 'wechat_miniprogram', NOW()) RETURNING id''',
                    (openid, unionid, placeholder_email, '', '')
                )
                user_id = cur.fetchone()[0]
                conn.commit()
                user_record = {
                    'id': user_id,
                    'openid': openid,
                    'unionid': unionid,
                    'nickname': '',
                    'avatar': '',
                    'email': placeholder_email,
                    'login_type': 'wechat_miniprogram',
                }
    finally:
        _release_db(conn)
    
    # Create session
    session_token = _make_session(user_record)
    
    print(f'[auth] miniprogram login ok user_id={user_id} openid={openid[:16]}...', flush=True)
    
    return {'ok': True, 'token': session_token, 'user': user_record}


@app.post('/api/auth/wechat/miniprogram/update-profile')
async def wechat_miniprogram_update_profile(
    request: Request, 
    payload: MiniProgramUpdateProfileRequest
):
    """Update user profile with info from WeChat Mini Program (wx.getUserProfile).
    
    This should be called after login to update nickname and avatar.
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='Login required')
    
    user_id = user.get('id')
    if not user_id:
        raise HTTPException(status_code=400, detail='Invalid user session')
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE users SET 
                   nickname = COALESCE(NULLIF(%s, ''), nickname),
                   avatar = COALESCE(NULLIF(%s, ''), avatar),
                   gender = %s,
                   city = COALESCE(NULLIF(%s, ''), city),
                   province = COALESCE(NULLIF(%s, ''), province),
                   country = COALESCE(NULLIF(%s, ''), country)
                   WHERE id = %s''',
                (payload.nickname, payload.avatar, payload.gender, 
                 payload.city, payload.province, payload.country, user_id)
            )
            conn.commit()
            
            # Fetch updated user
            cur.execute(
                'SELECT id, email, nickname, avatar, openid, unionid, login_type FROM users WHERE id = %s',
                (user_id,)
            )
            row = cur.fetchone()
            updated_user = {
                'id': row[0], 'email': row[1], 'nickname': row[2], 'avatar': row[3],
                'openid': row[4], 'unionid': row[5], 'login_type': row[6],
            }
    finally:
        _release_db(conn)
    
    # Update session
    token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    if token:
        with _SESSION_LOCK:
            _SESSION_STORE[token] = updated_user
    
    return {'ok': True, 'user': updated_user}


def _get_user_by_email(email: str) -> dict | None:
    """Check if a user with the given email exists in the database (case-insensitive)."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, email, nickname, avatar, login_type, created_at FROM users WHERE LOWER(email) = LOWER(%s)', (email,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'email': row[1], 'nickname': row[2], 'avatar': row[3],
                'login_type': row[4], 'created_at': row[5].timestamp() if row[5] else None
            }
    finally:
        _release_db(conn)


@app.post('/api/auth/email/send-code')
@limiter.limit('5/minute')  # 每 IP 每分钟最多 5 次发送请求
async def email_send_code(request: Request, payload: EmailSendCodeRequest):
    """Send a 6-digit verification code to the given email."""
    print(f'[auth] send-code request for email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Check if email already registered
    existing_user = _get_user_by_email(email)
    if existing_user:
        print(f'[auth] email already registered: {email}', flush=True)
        return {'ok': False, 'registered': True, 'message': '该邮箱已注册，请直接登录'}

    # Rate limit: one code per 60 seconds
    with _CODE_LOCK:
        existing = _CODE_STORE.get(email)
        if existing and existing['expires'] - 240 > time.time():
            raise HTTPException(status_code=429, detail='Please wait before requesting another code')

    code = f'{random.randint(0, 999999):06d}'
    expires = time.time() + 300  # 5 minutes
    with _CODE_LOCK:
        _CODE_STORE[email] = {'code': code, 'expires': expires}

    body = (
        f'您的情感星球验证码：\n\n'
        f'  {code}\n\n'
        f'验证码 5 分钟内有效，请勿转发给他人。\n\n'
        f'Bible Emotion Sphere'
    )

    # If no email service is configured at all, show dev_code for local testing
    has_email_service = bool(SENDGRID_API_KEY) or bool(RESEND_API_KEY) or (bool(SMTP_USER) and bool(SMTP_PASS))
    if not has_email_service:
        print(f'[auth][DEV] verification code for {email}: {code}', flush=True)
        return {'ok': True, 'dev_code': code}

    try:
        await asyncio.to_thread(_send_email, email, '情感星球 – 邮箱验证码', body)
        print(f'[auth] verification code sent to {email} via {SMTP_HOST}:{SMTP_PORT}', flush=True)
        return {'ok': True}
    except Exception as exc:
        import traceback
        err_str = str(exc)
        print(f'[auth] email send failed to {email}: {err_str}', flush=True)
        print(traceback.format_exc(), flush=True)
        # Fallback: return dev_code so the user can still register
        print(f'[auth][FALLBACK] returning dev_code for {email}: {code}', flush=True)
        return {'ok': True, 'dev_code': code, 'warning': 'Email delivery failed. Use the code displayed below.'}


@app.post('/api/auth/email/register')
@limiter.limit('10/minute')  # 每 IP 每分钟最多 10 次注册尝试
def email_register(request: Request, payload: EmailRegisterRequest):
    """Register with email + verification code + password."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] register attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_email'}, success=False)
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Verify code
    with _CODE_LOCK:
        entry = _CODE_STORE.get(email)
        if not entry or entry['expires'] < time.time():
            _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'code_expired'}, success=False)
            raise HTTPException(status_code=400, detail='Verification code expired, please request a new one')
        if not hmac.compare_digest(entry['code'], payload.code.strip()):
            _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_code'}, success=False)
            raise HTTPException(status_code=400, detail='Incorrect verification code')
        del _CODE_STORE[email]

    if _get_user(email):
        _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'email_exists'}, success=False)
        raise HTTPException(status_code=409, detail='Email already registered')

    nickname = payload.nickname.strip() or email.split('@')[0]
    public = _create_user(email, nickname, '', None, _hash_password(payload.password))
    token = _make_session(public)
    _security_audit('REGISTER_SUCCESS', email=email, ip=client_ip, details={'nickname': nickname}, success=True)
    print(f'[auth] register ok email={email} nickname={nickname}', flush=True)
    return {'ok': True, 'token': token, 'user': public}


@app.post('/api/auth/email/login')
@limiter.limit('20/minute')  # 每 IP 每分钟最多 20 次登录尝试
def email_login(request: Request, payload: EmailLoginRequest):
    """Login with email + password."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] login attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    user_record = _get_user(email)
    if not user_record:
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip, details={'reason': 'user_not_found'}, success=False)
        print(f'[auth] login failed: invalid credential email={email}', flush=True)
        raise HTTPException(status_code=401, detail='Invalid email or password')
    stored_hash = user_record.get('password_hash', '')
    print(f'[auth] user found, hash prefix={stored_hash[:30] if stored_hash else "EMPTY"}, len={len(stored_hash)}', flush=True)
    if not _verify_password(payload.password, stored_hash):
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip, details={'reason': 'wrong_password', 'hash_len': len(stored_hash)}, success=False)
        print(f'[auth] login failed: invalid credential email={email}', flush=True)
        raise HTTPException(status_code=401, detail='Invalid email or password')
    public = {k: v for k, v in user_record.items() if k != 'password_hash'}
    token = _make_session(public)
    _security_audit('LOGIN_SUCCESS', email=email, ip=client_ip, details={'nickname': public.get('nickname')}, success=True)
    print(f'[auth] login ok email={email} nickname={public.get("nickname")}', flush=True)
    return {'ok': True, 'token': token, 'user': public}


class EmailResetPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=128)


@app.post('/api/auth/email/send-reset-code')
@limiter.limit('3/minute')  # 每 IP 每分钟最多 3 次重置密码请求
async def email_send_reset_code(request: Request, payload: EmailSendCodeRequest):
    """Send a verification code to reset password (email must be registered)."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] send-reset-code request for email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        _security_audit('PASSWORD_RESET_CODE_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_email'}, success=False)
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Check if email is registered
    user = _get_user(email)
    if not user:
        _security_audit('PASSWORD_RESET_CODE_FAILED', email=email, ip=client_ip, details={'reason': 'email_not_registered'}, success=False)
        print(f'[auth] send-reset-code failed: email not registered {email}', flush=True)
        raise HTTPException(status_code=404, detail='该邮箱未注册，请先注册')

    code = _generate_code()
    now = time.time()
    with _CODE_LOCK:
        _CODE_STORE[email] = {'code': code, 'expires': now + CODE_TTL_SECONDS}

    body = f"""您好！

您正在重置情感星球账户的密码。验证码：{code}

请在 10 分钟内输入此验证码完成密码重置。如非本人操作，请忽略此邮件。

情感星球
"""

    has_email_service = bool(SENDGRID_API_KEY) or bool(RESEND_API_KEY) or (bool(SMTP_USER) and bool(SMTP_PASS))
    if not has_email_service:
        print(f'[auth][DEV] reset verification code for {email}: {code}', flush=True)
        return {'ok': True, 'dev_code': code}

    try:
        await asyncio.to_thread(_send_email, email, '情感星球 – 密码重置验证码', body)
        print(f'[auth] reset verification code sent to {email}', flush=True)
        return {'ok': True}
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail='Failed to send email, please try again later')


@app.post('/api/auth/email/reset-password')
@limiter.limit('5/minute')  # 每 IP 每分钟最多 5 次重置尝试
def email_reset_password(request: Request, payload: EmailResetPasswordRequest):
    """Reset password with verification code."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] reset-password attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_email'}, success=False)
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Verify code
    with _CODE_LOCK:
        entry = _CODE_STORE.get(email)
        if not entry or entry['expires'] < time.time():
            _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'code_expired'}, success=False)
            raise HTTPException(status_code=400, detail='Verification code expired, please request a new one')
        if not hmac.compare_digest(entry['code'], payload.code.strip()):
            _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_code'}, success=False)
            raise HTTPException(status_code=400, detail='Incorrect verification code')
        del _CODE_STORE[email]

    # Check if user exists
    user_record = _get_user(email)
    if not user_record:
        _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'user_not_found'}, success=False)
        raise HTTPException(status_code=404, detail='User not found')

    # Update password
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET password_hash = %s WHERE LOWER(email) = LOWER(%s)',
                (_hash_password(payload.password), email)
            )
            conn.commit()
    finally:
        _release_db(conn)

    _security_audit('PASSWORD_RESET_SUCCESS', email=email, ip=client_ip, details={}, success=True)
    print(f'[auth] password reset ok email={email}', flush=True)
    return {'ok': True, 'message': 'Password reset successfully, please login with new password'}


def _get_session_user(request: Request) -> dict | None:
    """Extract user record from session token in Authorization header."""
    auth = request.headers.get('Authorization', '')
    token = auth[7:].strip() if auth.startswith('Bearer ') else request.query_params.get('token', '')
    if not token:
        return None
    with _SESSION_LOCK:
        user = _SESSION_STORE.get(token)
    if user is not None:
        return user
    # Fallback: load from DB if memory was lost (e.g. Render cold-start)
    try:
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT data, expires_at FROM user_tokens WHERE token = %s',
                    (token,)
                )
                row = cur.fetchone()
                if row is None:
                    return None
                expires_at = row[1]
                if expires_at and expires_at.timestamp() < time.time():
                    cur.execute('DELETE FROM user_tokens WHERE token = %s', (token,))
                    conn.commit()
                    return None
                user = json.loads(row[0])
                with _SESSION_LOCK:
                    _SESSION_STORE[token] = user
                return user
        finally:
            _release_db(conn)
    except Exception:
        return None


_ADMIN_CACHE: dict[str, tuple[bool, float]] = {}
_ADMIN_CACHE_TTL = 300  # 5 minutes

def _is_admin(email: str) -> bool:
    """Check if a user has admin role (cached 5 min)."""
    if not email:
        return False
    # Hardcoded admin fallback — no DB needed
    if email == 'zpclord@sina.com':
        return True
    now = time.time()
    cached = _ADMIN_CACHE.get(email)
    if cached and (now - cached[1]) < _ADMIN_CACHE_TTL:
        return cached[0]
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT role FROM user_roles WHERE email = %s', (email,))
            row = cur.fetchone()
            result = bool(row and row[0] == 'admin')
        _ADMIN_CACHE[email] = (result, now)
        return result
    finally:
        _release_db(conn)


def _get_user_role(email: str) -> str:
    """Get user role, default to 'user' if not found."""
    if not email:
        return 'user'
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT role FROM user_roles WHERE email = %s', (email,))
            row = cur.fetchone()
            if row:
                return row[0]
            # Hardcoded admin
            if email == 'zpclord@sina.com':
                return 'admin'
        return 'user'
    finally:
        _release_db(conn)


class UserUpdateRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    avatar: str = Field(default='', max_length=500)


@app.put('/api/user/profile')
def update_user_profile(payload: UserUpdateRequest, request: Request) -> dict:
    """Update current user profile (nickname, avatar)."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')

    s_nickname = _sanitize_text(payload.nickname)
    print(f'[user] update profile email={email} nickname={s_nickname}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET nickname = %s, avatar = %s WHERE LOWER(email) = LOWER(%s)',
                (s_nickname, payload.avatar, email)
            )
            conn.commit()
        print(f'[user] profile updated email={email}', flush=True)
        return {'ok': True, 'nickname': s_nickname, 'avatar': payload.avatar}
    finally:
        _release_db(conn)


@app.post('/api/user/checkin')
def post_checkin(payload: CheckinRequest, request: Request) -> dict:
    """Save checkin data and update user tags. Auth optional – tags skipped for guests."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    print(f'[checkin] received email={email or "guest"} emotion={payload.emotionLabel}', flush=True)
    data = payload.model_dump()
    # Sanitize all string fields in checkin data
    for key in data:
        if isinstance(data[key], str):
            data[key] = _sanitize_text(data[key])

    tags = _extract_tags(data)
    print(f'[checkin] extracted {len(tags)} tags', flush=True)

    if user and email:
        _upsert_tags(email, tags)
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO user_checkins (email, checkin_at, data) VALUES (%s, NOW(), %s)',
                    (email, json.dumps(data, ensure_ascii=False))
                )
                conn.commit()
            print(f'[checkin] saved to db for {email}', flush=True)
        finally:
            _release_db(conn)
    else:
        print('[checkin] guest checkin, tags not persisted', flush=True)

    return {'ok': True, 'tags_extracted': len(tags)}


class PrayerSubmitRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    is_anonymous: bool = False


@app.get('/api/prayers')
def get_prayers(request: Request, limit: int = Query(default=40, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> dict:
    """Return public prayer list. Authenticated users get ownership/admin metadata."""
    t0 = time.time()
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    is_admin = _is_admin(email)
    print(f'[prayers] list request email={email or "guest"} admin={is_admin} limit={limit} offset={offset}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # All authenticated users can see all non-deleted community prayers
            cur.execute(
                'SELECT id, email, nickname, content, is_anonymous, amen_count, created_at, updated_at, deleted_at '
                'FROM prayers WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s',
                (min(limit, 100), offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM prayers WHERE deleted_at IS NULL')
            total_active = cur.fetchone()[0]
            total_all = total_active
        items = []
        for row in rows:
            pid, row_email, nickname, content, is_anon, amen, created_at, updated_at, deleted_at = row
            items.append({
                'id': pid,
                'email': row_email,
                'nickname': nickname or '弟兄姊妹',
                'content': content,
                'is_own': row_email == email,
                'amen_count': amen,
                'created_at': _to_shanghai_iso(created_at),
                'updated_at': _to_shanghai_iso(updated_at),
                'deleted_at': _to_shanghai_iso(deleted_at),
            })
        print(f'[prayers] returning {len(items)} items in {(time.time()-t0)*1000:.0f}ms', flush=True)
        return {'ok': True, 'items': items, 'total': total_active, 'total_all': total_all, 'is_admin': is_admin}
    finally:
        _release_db(conn)


@app.post('/api/prayers')
def post_prayer(payload: PrayerSubmitRequest, request: Request) -> dict:
    """Submit a new prayer. Auth optional – guests can post with name 'guest'."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    nickname = user.get('nickname', '') if user else 'guest'
    print(f'[prayers] submit email={email or "guest"} len={len(payload.content)}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO prayers (email, nickname, content, is_anonymous, amen_count) VALUES (%s,%s,%s,%s,0) RETURNING id',
                (email, _sanitize_text(nickname), _sanitize_text(payload.content.strip()), False)
            )
            prayer_id = cur.fetchone()[0]
            conn.commit()
        print(f'[prayers] saved id={prayer_id}', flush=True)
        return {'ok': True, 'id': prayer_id}
    finally:
        _release_db(conn)


@app.post('/api/prayers/{prayer_id}/amen')
def amen_prayer(prayer_id: int, request: Request) -> dict:
    """Increment amen count for a prayer."""
    print(f'[prayers] amen prayer_id={prayer_id}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE prayers SET amen_count = amen_count + 1 WHERE id = %s AND deleted_at IS NULL',
                (prayer_id,)
            )
            updated = cur.rowcount
            conn.commit()
        if not updated:
            print(f'[prayers] amen failed: prayer_id={prayer_id} not found or deleted', flush=True)
            raise HTTPException(status_code=404, detail='Prayer not found')
        with conn.cursor() as cur:
            cur.execute('SELECT amen_count FROM prayers WHERE id = %s AND deleted_at IS NULL', (prayer_id,))
            row = cur.fetchone()
        new_count = row[0] if row else 0
        print(f'[prayers] amen ok prayer_id={prayer_id} amen_count={new_count}', flush=True)
        return {'ok': True, 'amen_count': new_count}
    finally:
        _release_db(conn)


class PrayerUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


@app.put('/api/prayers/{prayer_id}')
def update_prayer(prayer_id: int, payload: PrayerUpdateRequest, request: Request) -> dict:
    """Update a prayer owned by the current user."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    print(f'[prayers] update id={prayer_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check ownership and not deleted
            cur.execute('SELECT email, deleted_at FROM prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Prayer not found')
            owner_email, deleted_at = row
            if deleted_at:
                raise HTTPException(status_code=404, detail='Prayer not found')
            if owner_email != email:
                raise HTTPException(status_code=403, detail='Not authorized')
            # Update
            cur.execute(
                'UPDATE prayers SET content = %s, updated_at = NOW() WHERE id = %s',
                (_sanitize_text(payload.content.strip()), prayer_id)
            )
            conn.commit()
        print(f'[prayers] updated id={prayer_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


@app.delete('/api/prayers/{prayer_id}')
def delete_prayer(prayer_id: int, request: Request) -> dict:
    """Soft delete a prayer. Owner can delete their own; admin can delete any."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    is_admin = _is_admin(email)
    print(f'[prayers] delete id={prayer_id} email={email} admin={is_admin}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check ownership and not already deleted
            cur.execute('SELECT email, deleted_at FROM prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Prayer not found')
            owner_email, deleted_at = row
            if deleted_at:
                raise HTTPException(status_code=404, detail='Prayer not found')
            # Check permission: owner or admin
            if owner_email != email and not is_admin:
                raise HTTPException(status_code=403, detail='Not authorized')
            # Soft delete (set deleted_at)
            cur.execute('UPDATE prayers SET deleted_at = NOW() WHERE id = %s', (prayer_id,))
            conn.commit()
        print(f'[prayers] soft deleted id={prayer_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


@app.post('/api/prayers/{prayer_id}/restore')
def restore_prayer(prayer_id: int, request: Request) -> dict:
    """Restore a soft-deleted prayer. Only admin can restore."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    # Check admin permission
    if not _is_admin(email):
        raise HTTPException(status_code=403, detail='Admin permission required')
    print(f'[prayers] restore id={prayer_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check if exists and is deleted
            cur.execute('SELECT deleted_at FROM prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Prayer not found')
            if not row[0]:
                raise HTTPException(status_code=400, detail='Prayer is not deleted')
            # Restore (clear deleted_at)
            cur.execute('UPDATE prayers SET deleted_at = NULL WHERE id = %s', (prayer_id,))
            conn.commit()
        print(f'[prayers] restored id={prayer_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── Evangelism Prayers (传福音祷告墙) ─────────────────────────

class EvangelismSubmitRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    is_anonymous: bool = False


@app.get('/api/evangelism')
def get_evangelism_prayers(request: Request, limit: int = Query(default=40, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> dict:
    """Return public evangelism prayer list. Authenticated users get ownership/admin metadata."""
    t0 = time.time()
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    is_admin = _is_admin(email)
    print(f'[evangelism] list request email={email or "guest"} admin={is_admin} limit={limit} offset={offset}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # All authenticated users can see all non-deleted community posts
            cur.execute(
                'SELECT id, email, nickname, content, is_anonymous, amen_count, created_at, updated_at, deleted_at '
                'FROM evangelism_prayers WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s',
                (min(limit, 100), offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM evangelism_prayers WHERE deleted_at IS NULL')
            total_active = cur.fetchone()[0]
            total_all = total_active
        items = []
        for row in rows:
            pid, row_email, nick, content, is_anon, amen, created_at, updated_at, deleted_at = row
            items.append({
                'id': pid,
                'email': row_email,
                'nickname': nick or '弟兄姊妹',
                'content': content,
                'is_own': row_email == email,
                'amen_count': amen,
                'created_at': _to_shanghai_iso(created_at),
                'updated_at': _to_shanghai_iso(updated_at),
                'deleted_at': _to_shanghai_iso(deleted_at),
            })
        print(f'[evangelism] returning {len(items)} items in {(time.time()-t0)*1000:.0f}ms', flush=True)
        return {'ok': True, 'items': items, 'total': total_active, 'total_all': total_all, 'is_admin': is_admin}
    finally:
        _release_db(conn)


@app.post('/api/evangelism')
def post_evangelism_prayer(payload: EvangelismSubmitRequest, request: Request) -> dict:
    """Submit a new evangelism prayer. Auth optional – guests can post with name 'guest'."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    nickname = user.get('nickname', '') if user else 'guest'
    print(f'[evangelism] submit email={email or "guest"} len={len(payload.content)}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO evangelism_prayers (email, nickname, content, is_anonymous, amen_count) VALUES (%s,%s,%s,%s,0) RETURNING id',
                (email, _sanitize_text(nickname), _sanitize_text(payload.content.strip()), False)
            )
            prayer_id = cur.fetchone()[0]
            conn.commit()
        print(f'[evangelism] saved id={prayer_id}', flush=True)
        return {'ok': True, 'id': prayer_id}
    finally:
        _release_db(conn)


@app.post('/api/evangelism/{prayer_id}/amen')
def amen_evangelism_prayer(prayer_id: int, request: Request) -> dict:
    """Increment amen count for an evangelism prayer."""
    print(f'[evangelism] amen prayer_id={prayer_id}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE evangelism_prayers SET amen_count = amen_count + 1 WHERE id = %s AND deleted_at IS NULL',
                (prayer_id,)
            )
            updated = cur.rowcount
            conn.commit()
        if not updated:
            print(f'[evangelism] amen failed: prayer_id={prayer_id} not found or deleted', flush=True)
            raise HTTPException(status_code=404, detail='Prayer not found')
        with conn.cursor() as cur:
            cur.execute('SELECT amen_count FROM evangelism_prayers WHERE id = %s AND deleted_at IS NULL', (prayer_id,))
            row = cur.fetchone()
        new_count = row[0] if row else 0
        print(f'[evangelism] amen ok prayer_id={prayer_id} amen_count={new_count}', flush=True)
        return {'ok': True, 'amen_count': new_count}
    finally:
        _release_db(conn)


class EvangelismUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


@app.put('/api/evangelism/{prayer_id}')
def update_evangelism_prayer(prayer_id: int, payload: EvangelismUpdateRequest, request: Request) -> dict:
    """Update an evangelism prayer owned by the current user."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    print(f'[evangelism] update id={prayer_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT email, deleted_at FROM evangelism_prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Prayer not found')
            owner_email, deleted_at = row
            if deleted_at:
                raise HTTPException(status_code=404, detail='Prayer not found')
            if owner_email != email:
                raise HTTPException(status_code=403, detail='Not authorized')
            cur.execute(
                'UPDATE evangelism_prayers SET content = %s, updated_at = NOW() WHERE id = %s',
                (_sanitize_text(payload.content.strip()), prayer_id)
            )
            conn.commit()
        print(f'[evangelism] updated id={prayer_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


@app.delete('/api/evangelism/{prayer_id}')
def delete_evangelism_prayer(prayer_id: int, request: Request) -> dict:
    """Soft delete an evangelism prayer. Owner can delete their own; admin can delete any."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    is_admin = _is_admin(email)
    print(f'[evangelism] delete id={prayer_id} email={email} admin={is_admin}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT email, deleted_at FROM evangelism_prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Prayer not found')
            owner_email, deleted_at = row
            if deleted_at:
                raise HTTPException(status_code=404, detail='Prayer not found')
            if owner_email != email and not is_admin:
                raise HTTPException(status_code=403, detail='Not authorized')
            cur.execute('UPDATE evangelism_prayers SET deleted_at = NOW() WHERE id = %s', (prayer_id,))
            conn.commit()
        print(f'[evangelism] soft deleted id={prayer_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


@app.post('/api/evangelism/{prayer_id}/restore')
def restore_evangelism_prayer(prayer_id: int, request: Request) -> dict:
    """Restore a soft-deleted evangelism prayer. Only admin can restore."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    # Check admin permission
    if not _is_admin(email):
        raise HTTPException(status_code=403, detail='Admin permission required')
    print(f'[evangelism] restore id={prayer_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check if exists and is deleted
            cur.execute('SELECT deleted_at FROM evangelism_prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Prayer not found')
            if not row[0]:
                raise HTTPException(status_code=400, detail='Prayer is not deleted')
            # Restore (clear deleted_at)
            cur.execute('UPDATE evangelism_prayers SET deleted_at = NULL WHERE id = %s', (prayer_id,))
            conn.commit()
        print(f'[evangelism] restored id={prayer_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── Devotion Journal ─────────────────────────────────────────

class DevotionJournalSaveRequest(BaseModel):
    date: str = Field(min_length=1, max_length=10)          # YYYY-MM-DD
    title: str = Field(default='', max_length=200)
    scripture: str = Field(default='', max_length=500)
    observation: str = Field(default='', max_length=2000)
    reflection: str = Field(default='', max_length=2000)
    application: str = Field(default='', max_length=2000)
    prayer: str = Field(default='', max_length=2000)
    mood: str = Field(default='', max_length=20)

    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        return _validate_date_str(v)


def _row_to_journal(row) -> dict:
    return {
        'id': row[0],
        'email': row[1],
        'date': str(row[2]) if row[2] else '',  # journal_date as date string
        'title': row[3] or '',
        'scripture': row[4] or '',  # scripture_text
        'observation': row[5] or '',
        'reflection': row[6] or '',
        'application': row[7] or '',
        'prayer': row[8] or '',
        'mood': row[9] or '',
        'created_at': _to_shanghai_iso(row[10]),
        'updated_at': _to_shanghai_iso(row[11]),
    }


@app.get('/api/devotion/journals')
def get_journals(request: Request, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)) -> dict:
    """List current user's devotion journals, newest first."""
    t0 = time.time()
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    print(f'[devotion] list journals email={email} limit={limit} offset={offset}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, email, journal_date, title, scripture_text, observation, reflection, application, prayer, mood, created_at, updated_at '
                'FROM devotion_journals WHERE email=%s AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s',
                (email, min(limit, 200), offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM devotion_journals WHERE email=%s AND deleted_at IS NULL', (email,))
            total = cur.fetchone()[0]
        items = [_row_to_journal(r) for r in rows]
        print(f'[devotion] list ok {len(items)}/{total} in {(time.time()-t0)*1000:.0f}ms', flush=True)
        return {'ok': True, 'items': items, 'total': total}
    finally:
        _release_db(conn)


@app.post('/api/devotion/journals')
def save_journal(payload: DevotionJournalSaveRequest, request: Request) -> dict:
    """Create or update journal entry for a given date (upsert by date)."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    # Sanitize all text inputs
    s_title = _sanitize_text(payload.title)
    s_scripture = _sanitize_text(payload.scripture)
    s_observation = _sanitize_text(payload.observation)
    s_reflection = _sanitize_text(payload.reflection)
    s_application = _sanitize_text(payload.application)
    s_prayer = _sanitize_text(payload.prayer)
    s_mood = _sanitize_text(payload.mood)
    print(f'[devotion] save journal email={email} date={payload.date} title={s_title[:30]}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM devotion_journals WHERE email=%s AND journal_date=%s', (email, payload.date)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    '''UPDATE devotion_journals
                       SET title=%s, scripture_text=%s, observation=%s, reflection=%s, application=%s, prayer=%s, mood=%s, updated_at=NOW()
                       WHERE email=%s AND journal_date=%s''',
                    (s_title, s_scripture, s_observation, s_reflection,
                     s_application, s_prayer, s_mood, email, payload.date)
                )
                journal_id = existing[0]
                print(f'[devotion] updated id={journal_id}', flush=True)
            else:
                cur.execute(
                    '''INSERT INTO devotion_journals
                       (email, journal_date, title, scripture_text, observation, reflection, application, prayer, mood)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
                    (email, payload.date, s_title, s_scripture, s_observation,
                     s_reflection, s_application, s_prayer, s_mood)
                )
                journal_id = cur.fetchone()[0]
                print(f'[devotion] created id={journal_id}', flush=True)
            conn.commit()
            cur.execute('SELECT id, email, journal_date, title, scripture_text, observation, reflection, application, prayer, mood, created_at, updated_at FROM devotion_journals WHERE id=%s', (journal_id,))
            row = cur.fetchone()
        return {'ok': True, 'journal': _row_to_journal(row)}
    finally:
        _release_db(conn)


@app.get('/api/devotion/journals/{journal_id}')
def get_journal(journal_id: int, request: Request) -> dict:
    """Get a single journal by id."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    print(f'[devotion] get journal id={journal_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, email, journal_date, title, scripture_text, observation, reflection, application, prayer, mood, created_at, updated_at FROM devotion_journals WHERE id=%s AND email=%s AND deleted_at IS NULL',
                (journal_id, email)
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Journal not found')
        return {'ok': True, 'journal': _row_to_journal(row)}
    finally:
        _release_db(conn)


@app.delete('/api/devotion/journals/{journal_id}')
def delete_journal(journal_id: int, request: Request) -> dict:
    """Soft delete a journal entry. Owner can delete their own; admin can delete any."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    is_admin = _is_admin(email)
    print(f'[devotion] delete journal id={journal_id} email={email} admin={is_admin}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check ownership and not already deleted
            cur.execute('SELECT email, deleted_at FROM devotion_journals WHERE id=%s', (journal_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Journal not found')
            owner_email, deleted_at = row
            if deleted_at:
                raise HTTPException(status_code=404, detail='Journal not found')
            # Check permission: owner or admin
            if owner_email != email and not is_admin:
                raise HTTPException(status_code=403, detail='Not authorized')
            # Soft delete
            cur.execute('UPDATE devotion_journals SET deleted_at = NOW() WHERE id=%s', (journal_id,))
            conn.commit()
        print(f'[devotion] soft deleted id={journal_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── end Devotion Journal ──────────────────────────────────────


# ── Sermon Journal (主日信息) ─────────────────────────────────

class SermonJournalSaveRequest(BaseModel):
    date: str = Field(min_length=1, max_length=50)          # 格式: 2026年5月3日,第13周
    title: str = Field(default='', max_length=255)
    preacher: str = Field(default='', max_length=100)
    scripture: str = Field(default='', max_length=500)
    summary: str = Field(default='', max_length=5000)
    questions: list[str] = Field(default_factory=list)
    bible_study: str = Field(default='', max_length=5000)
    practices: list[str] = Field(default_factory=list)
    reflection: str = Field(default='', max_length=5000)
    lesson: str = Field(default='', max_length=5000)
    conclusion: str = Field(default='', max_length=5000)
    encouragement: str = Field(default='', max_length=5000)
    phase: str = Field(default='active', max_length=20)

    @field_validator('questions', 'practices')
    @classmethod
    def validate_list_items(cls, v):
        """Ensure list items are strings with reasonable length."""
        return [str(item)[:2000] for item in v[:20]]


def _row_to_sermon(row) -> dict:
    return {
        'id': row[0],
        'email': row[1],
        'date': str(row[2]) if row[2] else '',  # sermon_date stored as text
        'title': row[3] or '',
        'preacher': row[4] or '',
        'scripture': row[5] or '',
        'summary': row[6] or '',
        'questions': row[7] if row[7] else [],
        'bible_study': row[8] or '',
        'practices': row[9] if row[9] else [],
        'reflection': row[10] or '',
        'lesson': row[11] or '',
        'conclusion': row[12] or '',
        'encouragement': row[13] or '',
        'phase': row[14] or 'active',
        'created_at': _to_shanghai_iso(row[15]),
        'updated_at': _to_shanghai_iso(row[16]),
    }


@app.get('/api/sermon/journals')
def get_sermon_journals(request: Request, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)) -> dict:
    """List all sermon journals (admin can view all, users view all for read-only access)."""
    t0 = time.time()
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    is_admin = _is_admin(email)
    print(f'[sermon] list journals email={email} admin={is_admin} limit={limit} offset={offset}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # All authenticated users can view all sermon journals (not deleted)
            cur.execute(
                'SELECT id, email, sermon_date, title, preacher, scripture, summary, questions, bible_study, practices, reflection, lesson, conclusion, encouragement, phase, created_at, updated_at '
                'FROM sermon_journals WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s',
                (min(limit, 200), offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM sermon_journals WHERE deleted_at IS NULL')
            total = cur.fetchone()[0]
        items = [_row_to_sermon(r) for r in rows]
        print(f'[sermon] list ok {len(items)}/{total} in {(time.time()-t0)*1000:.0f}ms', flush=True)
        return {'ok': True, 'items': items, 'total': total, 'is_admin': is_admin}
    finally:
        _release_db(conn)


@app.post('/api/sermon/journals')
def save_sermon_journal(payload: SermonJournalSaveRequest, request: Request) -> dict:
    """Create or update the current user's sermon journal entry (upsert by date)."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    # Sanitize text inputs
    s_title = _sanitize_text(payload.title)
    s_preacher = _sanitize_text(payload.preacher)
    s_scripture = _sanitize_text(payload.scripture)
    s_summary = _sanitize_text(payload.summary)
    s_questions = [_sanitize_text(q) for q in payload.questions]
    s_bible_study = _sanitize_text(payload.bible_study)
    s_practices = [_sanitize_text(p) for p in payload.practices]
    s_reflection = _sanitize_text(payload.reflection)
    s_lesson = _sanitize_text(payload.lesson)
    s_conclusion = _sanitize_text(payload.conclusion)
    s_encouragement = _sanitize_text(payload.encouragement)
    s_phase = _sanitize_text(payload.phase)
    print(f'[sermon] save journal email={email} date={payload.date} title={s_title[:30]}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM sermon_journals WHERE email=%s AND sermon_date=%s', (email, payload.date)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    '''UPDATE sermon_journals
                       SET title=%s, preacher=%s, scripture=%s, summary=%s, questions=%s, bible_study=%s, practices=%s, reflection=%s, lesson=%s, conclusion=%s, encouragement=%s, phase=%s, updated_at=NOW()
                       WHERE email=%s AND sermon_date=%s''',
                    (s_title, s_preacher, s_scripture, s_summary,
                     json.dumps(s_questions), s_bible_study, json.dumps(s_practices),
                     s_reflection, s_lesson, s_conclusion, s_encouragement,
                     s_phase, email, payload.date)
                )
                journal_id = existing[0]
                print(f'[sermon] updated id={journal_id}', flush=True)
            else:
                cur.execute(
                    '''INSERT INTO sermon_journals
                       (email, sermon_date, title, preacher, scripture, summary, questions, bible_study, practices, reflection, lesson, conclusion, encouragement, phase)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
                    (email, payload.date, s_title, s_preacher, s_scripture,
                     s_summary, json.dumps(s_questions), s_bible_study,
                     json.dumps(s_practices), s_reflection, s_lesson,
                     s_conclusion, s_encouragement, s_phase)
                )
                journal_id = cur.fetchone()[0]
                print(f'[sermon] created id={journal_id}', flush=True)
            conn.commit()
            cur.execute('SELECT id, email, sermon_date, title, preacher, scripture, summary, questions, bible_study, practices, reflection, lesson, conclusion, encouragement, phase, created_at, updated_at FROM sermon_journals WHERE id=%s', (journal_id,))
            row = cur.fetchone()
        return {'ok': True, 'journal': _row_to_sermon(row)}
    finally:
        _release_db(conn)


@app.get('/api/sermon/journals/{journal_id}')
def get_sermon_journal(journal_id: int, request: Request) -> dict:
    """Get a single sermon journal by id. All authenticated users can view any journal."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    is_admin = _is_admin(email)
    print(f'[sermon] get journal id={journal_id} email={email} admin={is_admin}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # All authenticated users can view any sermon journal
            cur.execute(
                'SELECT id, email, sermon_date, title, preacher, scripture, summary, questions, bible_study, practices, reflection, lesson, conclusion, encouragement, phase, created_at, updated_at FROM sermon_journals WHERE id=%s AND deleted_at IS NULL',
                (journal_id,)
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Journal not found')
        return {'ok': True, 'journal': _row_to_sermon(row), 'is_admin': is_admin}
    finally:
        _release_db(conn)


@app.delete('/api/sermon/journals/{journal_id}')
def delete_sermon_journal(journal_id: int, request: Request) -> dict:
    """Soft delete a sermon journal entry. Only admin can delete."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    # Check admin permission
    if not _is_admin(email):
        raise HTTPException(status_code=403, detail='Admin permission required')
    print(f'[sermon] delete journal id={journal_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check not already deleted
            cur.execute('SELECT deleted_at FROM sermon_journals WHERE id=%s', (journal_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Journal not found')
            if row[0]:
                raise HTTPException(status_code=404, detail='Journal not found')
            # Soft delete
            cur.execute('UPDATE sermon_journals SET deleted_at = NOW() WHERE id=%s', (journal_id,))
            conn.commit()
        print(f'[sermon] soft deleted id={journal_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── end Sermon Journal ────────────────────────────────────────


# ── Personal Notes (我的日记) ─────────────────────────────────

class PersonalNoteSaveRequest(BaseModel):
    id: str = Field(default='', max_length=50)
    date: str = Field(min_length=1, max_length=10)          # YYYY-MM-DD
    scripture: str = Field(default='', max_length=500)
    observation: str = Field(default='', max_length=5000)
    reflection: str = Field(default='', max_length=5000)
    application: str = Field(default='', max_length=5000)
    prayer: str = Field(default='', max_length=5000)
    mood: str = Field(default='', max_length=50)
    shared: bool = False
    author: str = Field(default='', max_length=100)
    avatar: str = Field(default='', max_length=500)

    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        return _validate_date_str(v)


def _row_to_personal_note(row) -> dict:
    return {
        'id': row[0],
        'email': row[1],
        'date': str(row[2]) if row[2] else '',
        'scripture': row[3] or '',
        'observation': row[4] or '',
        'reflection': row[5] or '',
        'application': row[6] or '',
        'prayer': row[7] or '',
        'mood': row[8] or '',
        'shared': bool(row[9]),
        'author': row[10] or '',
        'avatar': row[11] or '',
        'createdAt': _to_shanghai_iso(row[12]),
        'updatedAt': _to_shanghai_iso(row[13]),
    }


@app.get('/api/personal/notes')
def get_personal_notes(request: Request) -> dict:
    """List current user's personal notes, newest first."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    print(f'[personal] list notes email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, email, note_date, scripture, observation, reflection, application, prayer, mood, shared, author, avatar, created_at, updated_at '
                'FROM personal_notes WHERE email=%s AND deleted_at IS NULL ORDER BY updated_at DESC, created_at DESC',
                (email,)
            )
            rows = cur.fetchall()
        items = [_row_to_personal_note(r) for r in rows]
        print(f'[personal] list ok {len(items)}', flush=True)
        return {'ok': True, 'items': items}
    finally:
        _release_db(conn)


@app.post('/api/personal/notes')
def save_personal_note(payload: PersonalNoteSaveRequest, request: Request) -> dict:
    """Create or update a personal note."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    note_id = payload.id or str(int(time.time() * 1000))
    # Sanitize text inputs
    s_scripture = _sanitize_text(payload.scripture)
    s_observation = _sanitize_text(payload.observation)
    s_reflection = _sanitize_text(payload.reflection)
    s_application = _sanitize_text(payload.application)
    s_prayer = _sanitize_text(payload.prayer)
    s_mood = _sanitize_text(payload.mood)
    s_author = _sanitize_text(payload.author)
    print(f'[personal] save note id={note_id} email={email} date={payload.date}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM personal_notes WHERE id=%s AND email=%s', (note_id, email)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    '''UPDATE personal_notes
                       SET note_date=%s, scripture=%s, observation=%s, reflection=%s, application=%s, prayer=%s, mood=%s, shared=%s, author=%s, avatar=%s, updated_at=NOW()
                       WHERE id=%s AND email=%s''',
                    (payload.date, s_scripture, s_observation, s_reflection,
                     s_application, s_prayer, s_mood, payload.shared,
                     s_author, payload.avatar, note_id, email)
                )
                print(f'[personal] updated id={note_id}', flush=True)
            else:
                cur.execute(
                    '''INSERT INTO personal_notes
                       (id, email, note_date, scripture, observation, reflection, application, prayer, mood, shared, author, avatar)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (note_id, email, payload.date, s_scripture, s_observation,
                     s_reflection, s_application, s_prayer, s_mood,
                     payload.shared, s_author, payload.avatar)
                )
                print(f'[personal] created id={note_id}', flush=True)
            conn.commit()
            cur.execute(
                'SELECT id, email, note_date, scripture, observation, reflection, application, prayer, mood, shared, author, avatar, created_at, updated_at FROM personal_notes WHERE id=%s',
                (note_id,)
            )
            row = cur.fetchone()
        return {'ok': True, 'note': _row_to_personal_note(row)}
    finally:
        _release_db(conn)


@app.delete('/api/personal/notes/{note_id}')
def delete_personal_note(note_id: str, request: Request) -> dict:
    """Soft delete a personal note owned by the current user."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    print(f'[personal] delete note id={note_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT email, deleted_at FROM personal_notes WHERE id=%s', (note_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Note not found')
            owner_email, deleted_at = row
            if deleted_at:
                raise HTTPException(status_code=404, detail='Note not found')
            if owner_email != email:
                raise HTTPException(status_code=403, detail='Not authorized')
            cur.execute(
                'UPDATE personal_notes SET deleted_at=NOW(), shared=FALSE WHERE id=%s', (note_id,)
            )
            conn.commit()
        print(f'[personal] soft deleted id={note_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── end Personal Notes ────────────────────────────────────────


# ── Share Wall (分享墙) ──────────────────────────────────────

@app.get('/api/shared/notes')
def get_shared_notes(request: Request) -> dict:
    """Return all shared notes (requires login). Shows notes from all users where shared=true."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']
    print(f'[shared] list notes email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, email, note_date, scripture, observation, reflection, application, prayer, mood, shared, author, avatar, created_at, updated_at '
                'FROM personal_notes WHERE shared=TRUE AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 100'
            )
            rows = cur.fetchall()
        items = []
        for r in rows:
            note = _row_to_personal_note(r)
            note['is_own'] = r[1] == email
            items.append(note)
        print(f'[shared] returning {len(items)} items', flush=True)
        return {'ok': True, 'items': items}
    finally:
        _release_db(conn)


@app.post('/api/personal/notes/{note_id}/share')
def toggle_share_note(note_id: str, request: Request) -> dict:
    """Toggle share status for a personal note. Only the owner can share/unshare."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']
    print(f'[shared] toggle share note_id={note_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute('SELECT email, shared FROM personal_notes WHERE id=%s', (note_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Note not found')
            owner_email, currently_shared = row
            if owner_email != email:
                raise HTTPException(status_code=403, detail='Only the creator can share/unshare')
            # Toggle
            new_shared = not currently_shared
            cur.execute('UPDATE personal_notes SET shared=%s, updated_at=NOW() WHERE id=%s', (new_shared, note_id))
            conn.commit()
        print(f'[shared] note_id={note_id} shared={new_shared}', flush=True)
        return {'ok': True, 'shared': new_shared}
    finally:
        _release_db(conn)


# ── end Share Wall ───────────────────────────────────────────


# ── Recycle Bin (回收站) ─────────────────────────────────────

@app.get('/api/recycle-bin')
def get_recycle_bin(request: Request) -> dict:
    """List all soft-deleted items for the current user across all tables. Auto-purge items >30 days."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']
    print(f'[recycle] list email={email}', flush=True)
    try:
        conn = _get_db()
    except Exception as db_exc:
        print(f'[recycle] database connection failed: {db_exc}', flush=True)
        raise HTTPException(status_code=503, detail='Database connection failed') from db_exc
    try:
        with conn.cursor() as cur:
            # Auto-purge items deleted > 30 days ago
            cutoff = "NOW() - INTERVAL '30 days'"
            cur.execute(f'DELETE FROM prayers WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM evangelism_prayers WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM devotion_journals WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM personal_notes WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM sermon_journals WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            conn.commit()

            items = []

            # Prayers
            cur.execute(
                'SELECT id, content, nickname, deleted_at FROM prayers WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'prayer', 'type_label': '代祷', 'id': r[0], 'title': (r[1] or '')[:60], 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Evangelism
            cur.execute(
                'SELECT id, content, nickname, deleted_at FROM evangelism_prayers WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'evangelism', 'type_label': '传FY', 'id': r[0], 'title': (r[1] or '')[:60], 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Devotion journals
            cur.execute(
                'SELECT id, title, scripture, deleted_at FROM devotion_journals WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'devotion', 'type_label': '灵修日记', 'id': r[0], 'title': r[1] or r[2] or '(无标题)', 'subtitle': '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Personal notes
            cur.execute(
                'SELECT id, scripture, mood, deleted_at FROM personal_notes WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'personal', 'type_label': '我的日记', 'id': r[0], 'title': r[1] or '(无经文)', 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Sermon journals
            cur.execute(
                'SELECT id, title, preacher, deleted_at FROM sermon_journals WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'sermon', 'type_label': '主日信息', 'id': r[0], 'title': r[1] or '(无标题)', 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

        # Sort all by deleted_at desc
        items.sort(key=lambda x: x['deleted_at'] or '', reverse=True)
        print(f'[recycle] returning {len(items)} items', flush=True)
        return {'ok': True, 'items': items}
    except Exception as exc:
        print(f'[recycle] query error: {exc}', flush=True)
        raise HTTPException(status_code=500, detail=f'Recycle bin query failed: {exc}') from exc
    finally:
        _release_db(conn)


@app.post('/api/recycle-bin/{item_type}/{item_id}/restore')
def restore_recycle_item(item_type: str, item_id: str, request: Request) -> dict:
    """Restore a soft-deleted item. Owner can restore their own items."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']

    table_map = {
        'prayer': 'prayers',
        'evangelism': 'evangelism_prayers',
        'devotion': 'devotion_journals',
        'personal': 'personal_notes',
        'sermon': 'sermon_journals',
    }
    table = table_map.get(item_type)
    if not table:
        raise HTTPException(status_code=400, detail=f'Unknown type: {item_type}')

    print(f'[recycle] restore type={item_type} id={item_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f'SELECT email, deleted_at FROM {table} WHERE id=%s', (item_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Item not found')
            owner_email, deleted_at = row
            if not deleted_at:
                raise HTTPException(status_code=400, detail='Item is not deleted')
            if owner_email != email and not _is_admin(email):
                raise HTTPException(status_code=403, detail='Not authorized')
            cur.execute(f'UPDATE {table} SET deleted_at=NULL WHERE id=%s', (item_id,))
            conn.commit()
        print(f'[recycle] restored type={item_type} id={item_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── end Recycle Bin ──────────────────────────────────────────


@app.get('/api/user/tags')
def get_user_tags(request: Request) -> dict:
    """Return current user's tag profile (for debug/admin use)."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    tags = _get_user_tags(user['email'])
    return {'ok': True, 'tags': tags}


_SPIRITUAL_CHAT_SYSTEM = """你是一位温暖、智慧、以圣经为根基的属灵同伴，陪伴用户处理生命中的挣扎、困惑与成长。

你的回应方式：
- 先真诚地倾听与认同用户的感受，不急于给答案
- 用圣经的光来温柔地引导，引用经文时注明出处（中文和合本）
- 鼓励用户自己思考和祷告，而非只给出答案
- 语言简洁、亲切，如同牧者或属灵朋友
- 每次回应不超过 300 字
- 如果用户的问题涉及危机（自杀/严重抑郁），优先关怀并建议寻求专业帮助

你不是：
- 不是神学考试机器
- 不是给出标准答案的工具
- 不给医疗或法律建议"""


@app.post('/api/chat')
async def post_chat(payload: ChatRequest, request: Request):
    """Streaming spiritual chat with automatic background tag extraction."""
    from fastapi.responses import StreamingResponse
    import httpx as _httpx

    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    session_id = payload.session_id or secrets.token_urlsafe(12)
    print(f'[chat] request email={email or "guest"} session={session_id} msgs={len(payload.messages)}', flush=True)

    # Build messages with user context injected into system prompt
    system_content = _SPIRITUAL_CHAT_SYSTEM
    if email:
        tags = _get_user_tags(email)
        if tags:
            system_content = system_content + '\n\n' + _build_user_context_prompt(tags)

    messages_for_api = []
    for m in payload.messages:
        messages_for_api.append({'role': m.role, 'content': m.content})

    # Save user message to DB
    last_user_msg = next(
        (m.content for m in reversed(payload.messages) if m.role == 'user'), None
    )
    if last_user_msg and email:
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO conversation_messages (email, session_id, role, content, created_at) VALUES (%s,%s,%s,%s,NOW())',
                    (email, session_id, 'user', last_user_msg)
                )
                conn.commit()
            print(f'[chat] user message saved session={session_id} len={len(last_user_msg)}', flush=True)
        finally:
            _release_db(conn)

    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        api_key = 'AIzaSyDIWBd3M1DO6-16RukYO4_K9rLBWV0ZHGs'

    req_body = {
        'model': 'gemini-2.0-flash',
        'system': system_content,
        'messages': messages_for_api,
        'temperature': 0.75,
        'max_tokens': 600,
        'stream': True,
    }
    headers_api = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    assistant_chunks: list[str] = []

    async def generate():
        try:
            async with _httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    'POST',
                    'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                    json=req_body,
                    headers=headers_api,
                ) as resp:
                    if resp.status_code == 429:
                        print(f'[chat] Gemini 429 quota exceeded', flush=True)
                        yield f'data: {json.dumps({"delta": "抱歉，AI服务当前请求过多，请稍后再试。"}, ensure_ascii=False)}\n\n'
                        return
                    if resp.status_code == 401:
                        print(f'[chat] Gemini 401 invalid api key', flush=True)
                        yield f'data: {json.dumps({"delta": "AI API密钥无效或已过期，请联系管理员检查GEMINI_API_KEY配置。"}, ensure_ascii=False)}\n\n'
                        return
                    if resp.status_code == 403:
                        print(f'[chat] Gemini 403 permission denied', flush=True)
                        yield f'data: {json.dumps({"delta": "AI API密钥权限不足，无法访问该模型。"}, ensure_ascii=False)}\n\n'
                        return
                    if resp.status_code >= 400:
                        print(f'[chat] Gemini error {resp.status_code}', flush=True)
                        yield f'data: {json.dumps({"delta": f"AI服务暂时不可用（错误码:{resp.status_code}），请稍后重试。"}, ensure_ascii=False)}\n\n'
                        return
                    async for line in resp.aiter_lines():
                        if not line.startswith('data: '):
                            continue
                        data_str = line[6:].strip()
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk['choices'][0]['delta'].get('content', '')
                            if delta:
                                assistant_chunks.append(delta)
                                yield f'data: {json.dumps({"delta": delta}, ensure_ascii=False)}\n\n'
                        except Exception:
                            continue
        except Exception as exc:
            print(f'[chat] streaming error: {exc}', flush=True)
            yield f'data: {json.dumps({"delta": "网络连接异常，请稍后重试。"}, ensure_ascii=False)}\n\n'

        # After streaming done: save assistant reply + trigger tag extraction
        full_reply = ''.join(assistant_chunks)
        print(f'[chat] stream done session={session_id} reply_len={len(full_reply)}', flush=True)
        if full_reply and email:
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO conversation_messages (email, session_id, role, content, created_at) VALUES (%s,%s,%s,%s,NOW())',
                        (email, session_id, 'assistant', full_reply)
                    )
                    conn.commit()
                print(f'[chat] assistant reply saved session={session_id}', flush=True)
            finally:
                _release_db(conn)

            # Trigger tag extraction every 3 user turns (avoid over-calling LLM)
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT COUNT(*) FROM conversation_messages WHERE email=%s AND role=%s',
                        (email, 'user')
                    )
                    count = cur.fetchone()[0]
            finally:
                _release_db(conn)
            if count % 3 == 0:
                all_msgs = [{'role': m.role, 'content': m.content} for m in payload.messages]
                all_msgs.append({'role': 'assistant', 'content': full_reply})
                asyncio.create_task(
                    asyncio.to_thread(_extract_tags_from_chat_bg, email, all_msgs)
                )

        yield f'data: {json.dumps({"done": True, "session_id": session_id}, ensure_ascii=False)}\n\n'

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@app.get('/health')
def health_check() -> dict:
    return {
        'status': 'ok',
        'db': 'connected' if _db_pool else 'no_database_url',
        'database_url_set': bool(DATABASE_URL),
    }


@app.get('/api/stats')
def get_stats() -> dict:
    with STATS_LOCK:
        return public_visit_stats(load_visit_stats())


@app.post('/api/stats/track')
def post_track_stats(payload: VisitTrackRequest) -> dict:
    return track_visit(payload.visitorId)


@app.get('/api/layout')
def get_layout() -> dict:
    layout = load_json_file(LAYOUT_FILE)
    return {'items': layout, 'count': len(layout)}


@app.get('/api/history')
def get_history() -> dict:
    return {'items': load_history()}


@app.get('/api/feature')
def get_feature(key: str = Query(min_length=1)) -> dict:
    item = build_feature_match_map().get(key)
    if item is None:
        raise HTTPException(status_code=404, detail='Feature not found')
    return item


# ── debug flag: set DEBUG_API=1 in HF Space secrets to expose tracebacks ──
_DEBUG = os.getenv('DEBUG_API', '0') == '1'


def _handle_exc(exc: Exception) -> None:
    """Always print full traceback to stdout (visible in HF Logs)."""
    print('=' * 72, flush=True)
    print('API ERROR:', type(exc).__name__, str(exc), flush=True)
    traceback.print_exc()
    print('=' * 72, flush=True)


@app.post('/api/guidance')
def get_guidance(payload: GuidanceRequest) -> dict:
    q = payload.query.strip()
    print(f'[guidance] request query={q[:60]}...', flush=True)
    try:
        result = assess_psychological_state(q)
        print(f'[guidance] ok emotions={result.get("core_emotions", [])}', flush=True)
        return result
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@app.post('/api/biblical-example')
def get_biblical_example(payload: GuidanceRequest) -> dict:
    q = payload.query.strip()
    print(f'[biblical_example] request query={q[:60]}...', flush=True)
    try:
        result = fetch_biblical_example(q)
        print(f'[biblical_example] ok person={result.get("person")} era={result.get("era")}', flush=True)
        return result
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


class VersePrayerRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=1000)


@app.post('/api/verse-prayer')
def generate_verse_prayer(payload: VersePrayerRequest) -> dict:
    """根据经文生成一段祷告文"""
    ref = payload.reference.strip()
    text = payload.text.strip()
    print(f'[verse-prayer] request ref={ref} text={text[:40]}...', flush=True)
    try:
        from query_emotion_verses import post_with_retry, chat_url_and_headers, GEMINI_CHAT_MODEL
        _chat_url, _chat_headers = chat_url_and_headers()
        prompt = f"""你是一位温柔、敬虔的祷告代笔者。请根据以下经文，写一段约100-150字的祷告文。
要求：
- 用第一人称（"主啊…"、"天父…"）
- 语气谦卑、恳切、充满信心
- 紧扣经文内容和属灵含义
- 结尾以"奉主耶稣基督的名祷告，阿们。"结束
- 直接输出祷告文，不要标题或解释

经文：{ref}
"{text}"
"""
        resp = post_with_retry(
            _chat_url,
            {
                "model": GEMINI_CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.8,
            },
            _chat_headers
        )
        prayer = resp.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        print(f'[verse-prayer] ok len={len(prayer)}', flush=True)
        return {"prayer": prayer, "reference": ref}
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@app.post('/api/punctuation')
async def add_punctuation(payload: PunctuationRequest) -> dict:
    text = payload.text.strip()
    print(f'[punctuation] request text={text[:60]}...', flush=True)
    try:
        # 使用 LLM 进行语义分析和标点添加
        prompt = f"""你是一个中文语义分析和标点专家。请为以下中文文本添加合适的标点符号。

原文：{text}

任务要求：
1. 深入理解文本的语义和情感
2. 根据语义逻辑进行正确的断句（不是简单的字词匹配）
3. 在语义完整的地方使用句号（。）
4. 在语气停顿的地方使用逗号（，）
5. 在疑问语气后使用问号（？）
6. 在强烈情感表达后使用感叹号（！）
7. 多句话之间必须正确分段
8. 绝对不能删除或修改原文的任何字词
9. 只添加标点符号，不做任何其他改动

示例：
原文：我感到很痛苦也很想被安慰但仍然想抓住一点盼望
结果：我感到很痛苦，也很想被安慰，但仍然想抓住一点盼望。

原文：神啊你在哪里为什么我感觉不到你的存在
结果：神啊，你在哪里？为什么我感觉不到你的存在？

请直接返回添加标点后的文本，不要添加任何解释或评论。"""
        
        # 调用 Gemini LLM API
        from query_emotion_verses import post_with_retry, chat_url_and_headers, GEMINI_CHAT_MODEL
        
        _chat_url, _chat_headers = chat_url_and_headers()
        print(f'[punctuation] calling LLM url={_chat_url} model={GEMINI_CHAT_MODEL}', flush=True)
        try:
            response = post_with_retry(
                _chat_url,
                {
                    'model': GEMINI_CHAT_MODEL,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                },
                _chat_headers
            )
        except Exception as api_exc:
            print(f'[punctuation] LLM API error: {api_exc}, returning original text', flush=True)
            return {'text': text, 'fallback': True}
        
        print(f'[punctuation] raw response keys={list(response.keys())}', flush=True)
        punctuated_text = response.get('choices', [{}])[0].get('message', {}).get('content', text).strip()
        # 去除可能的引号包裹
        if punctuated_text.startswith('"') and punctuated_text.endswith('"'):
            punctuated_text = punctuated_text[1:-1]
        if punctuated_text.startswith('「') and punctuated_text.endswith('」'):
            punctuated_text = punctuated_text[1:-1]
        print(f'[punctuation] ok result={punctuated_text[:80]}', flush=True)
        
        return {'text': punctuated_text}
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@app.post('/api/query')
async def post_query(payload: QueryRequest, request: Request) -> dict:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail='Missing query')
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    print(f'[query] request email={email or "guest"} query={query_text[:60]}... rerank={payload.enableRerank}', flush=True)
    _startup_check()

    # Build enriched query with user context tags (invisible to UI)
    user = _get_session_user(request)
    enriched_query = query_text
    if user and user.get('email'):
        tags = _get_user_tags(user['email'])
        if tags:
            context_prompt = _build_user_context_prompt(tags)
            enriched_query = f'{context_prompt}\n\n【用户当前提问】\n{query_text}'

    try:
        started_at = time.perf_counter()
        # Run blocking I/O + numpy in a thread so the event loop stays responsive
        result = await asyncio.to_thread(
            query_emotion_verses,
            enriched_query,
            payload.topFeatures,
            payload.topVerses,
            FEATURES_FILE,
            str(ROOT_DIR / 'emotion_exemplar_verse_matches.json'),
            str(ROOT_DIR / 'emotion_feature_embedding_cache.json'),
            False,   # guidance always via separate /api/guidance call
            payload.enableRerank,
            payload.rerankCandidates,
            payload.rerankWeight,
            payload.rerankMode,
        )
        result['query_latency_ms'] = round((time.perf_counter() - started_at) * 1000, 2)
        features_found = len(result.get('selected_emotions', []))
        print(f'[query] ok latency={result["query_latency_ms"]}ms features={features_found}', flush=True)
        await asyncio.to_thread(save_history_entry, query_text, payload.topFeatures, payload.topVerses, payload.languageFilter, result)
        return result
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


_startup_checked = False


def _startup_check() -> None:
    """Print key file sizes and paths to HF Logs on first query."""
    global _startup_checked
    if _startup_checked:
        return
    _startup_checked = True
    print('── Startup check ──', flush=True)
    print(f'ROOT_DIR : {ROOT_DIR}', flush=True)
    print(f'FRONTEND_DIST : {FRONTEND_DIST}  exists={FRONTEND_DIST.exists()}', flush=True)
    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / 'assets'
        print(f'  assets dir: {assets_dir}  exists={assets_dir.exists()}', flush=True)
        if assets_dir.exists():
            js_files = list(assets_dir.glob('*.js'))
            print(f'  JS files in assets: {len(js_files)}', flush=True)
    for name, path in [
        ('layout', LAYOUT_FILE),
        ('matches', MATCHES_FILE),
        ('features', Path(FEATURES_FILE)),
        ('emb_cache', Path(EMBEDDING_CACHE_FILE)),
    ]:
        exists = path.exists()
        size = path.stat().st_size if exists else -1
        print(f'  {name}: {path}  exists={exists}  size={size}', flush=True)
    # Check for common large files that might be LFS pointers
    for pattern in ('*.npy', '*.pkl', '*.bin'):
        for p in sorted(ROOT_DIR.glob(pattern)):
            print(f'  {p.name}: {p.stat().st_size} bytes', flush=True)
    print('──────────────────', flush=True)


@app.post('/api/sermon')
async def post_sermon(payload: SermonRequest) -> dict:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail='Missing query')
    print(f'[sermon] request query={query_text[:60]}...', flush=True)
    t0 = time.perf_counter()
    try:
        result = await asyncio.to_thread(generate_sermon, query_text)
        latency = round((time.perf_counter() - t0) * 1000, 2)
        print(f'[sermon] ok latency={latency}ms title={result.get("title", "")}', flush=True)
        return result
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@app.get('/')
def serve_root():
    """Serve the frontend index.html at root path."""
    if FRONTEND_DIST.exists():
        return FileResponse(
            FRONTEND_DIST / 'index.html',
            headers={'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache'},
        )
    raise HTTPException(status_code=404, detail='Frontend build output not found.')


if FRONTEND_DIST.exists():
    app.mount('/assets', StaticFiles(directory=FRONTEND_DIST / 'assets'), name='assets')


@app.get('/{full_path:path}')
def serve_frontend(full_path: str, request: Request):
    """Serve frontend files or fallback to index.html for SPA routing."""
    # Don't handle API routes here
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='Not found')

    # Don't handle static assets that should be mounted
    if full_path.startswith('assets/'):
        raise HTTPException(status_code=404, detail='Asset not found')

    if FRONTEND_DIST.exists():
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        # SPA fallback - serve index.html for all non-file routes
        return FileResponse(
            FRONTEND_DIST / 'index.html',
            headers={'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache'},
        )

    raise HTTPException(status_code=404, detail='Frontend build output not found. Run npm run build in emotion-sphere-ui first.')


# ── Google Cloud Text-to-Speech Endpoint ─────────────────────────────
class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000, description="要合成的文本")
    language_code: str = Field(default='cmn-CN', description="语言代码，如 cmn-CN, en-US")
    voice_name: str = Field(default='cmn-CN-Wavenet-A', description="指定语音名称")


# 可选：使用环境变量 GOOGLE_APPLICATION_CREDENTIALS 或 GOOGLE_API_KEY
GOOGLE_TTS_API_KEY = os.getenv('GOOGLE_TTS_API_KEY', '')


@app.post('/api/tts')
async def text_to_speech(payload: TTSRequest):
    """
    使用 Google Cloud Text-to-Speech 生成高质量语音。
    需要设置 GOOGLE_TTS_API_KEY 环境变量。
    如果未设置，返回 503 错误让前端 fallback 到浏览器原生 TTS。
    """
    if not GOOGLE_TTS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail='Google TTS API Key not configured. Set GOOGLE_TTS_API_KEY environment variable.'
        )
    
    try:
        # 优先使用 google-cloud-texttospeech 客户端库
        from google.cloud import texttospeech
        
        # 创建客户端（使用 API Key 需要通过环境变量或显式传入）
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=payload.text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=payload.language_code,
            name=payload.voice_name if payload.voice_name else None,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.9,  # 稍慢，更自然
            pitch=0.0,
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return Response(
            content=response.audio_content,
            media_type='audio/mpeg',
            headers={'Content-Disposition': 'inline; filename="tts.mp3"'}
        )
        
    except ImportError:
        # 如果客户端库不可用，使用 REST API 直接调用
        try:
            import base64
            
            url = f'https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}'
            
            data = {
                'input': {'text': payload.text},
                'voice': {
                    'languageCode': payload.language_code,
                    'name': payload.voice_name or 'cmn-CN-Wavenet-A',
                    'ssmlGender': 'FEMALE'
                },
                'audioConfig': {
                    'audioEncoding': 'MP3',
                    'speakingRate': 0.9,
                    'pitch': 0.0
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=data)
                
                if resp.status_code != 200:
                    error_detail = resp.text
                    print(f'[TTS] Google API error: {resp.status_code} {error_detail}')
                    raise HTTPException(
                        status_code=502,
                        detail=f'Google TTS API error: {resp.status_code}'
                    )
                
                result = resp.json()
                audio_content = base64.b64decode(result['audioContent'])
                
                return Response(
                    content=audio_content,
                    media_type='audio/mpeg',
                    headers={'Content-Disposition': 'inline; filename="tts.mp3"'}
                )
                
        except Exception as e:
            print(f'[TTS] Error calling Google API: {e}')
            raise HTTPException(status_code=500, detail=f'TTS generation failed: {str(e)}')
            
    except Exception as e:
        print(f'[TTS] Error: {e}')
        raise HTTPException(status_code=500, detail=f'TTS generation failed: {str(e)}')


# ── Dating Priority (交友原则排序) ──────────────────────────────

class DatingPrioritySubmitRequest(BaseModel):
    visitor_id: str = Field(min_length=1, max_length=255)
    perspective: str = Field(pattern='^(dx|zm)$')
    focus_order: list = Field(default=[])
    block_order: list = Field(default=[])


@app.post('/api/dating-priority/submit')
def submit_dating_priority(payload: DatingPrioritySubmitRequest) -> dict:
    """Save a user's dating priority ranking."""
    print(f'[dating] submit visitor={payload.visitor_id[:8]}... persp={payload.perspective} focus={len(payload.focus_order)} block={len(payload.block_order)}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO dating_priority_submissions (visitor_id, perspective, focus_order, block_order)
                VALUES (%s, %s, %s, %s)
            ''', (payload.visitor_id, payload.perspective,
                  json.dumps(payload.focus_order), json.dumps(payload.block_order)))
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@app.get('/api/dating-priority/stats')
def get_dating_priority_stats(perspective: str = Query(pattern='^(dx|zm)$')) -> dict:
    """Get aggregated statistics for dating priority rankings.
    Returns average rank position for each option across all submissions.
    """
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT focus_order, block_order FROM dating_priority_submissions
                WHERE perspective = %s
            ''', (perspective,))
            rows = cur.fetchall()

        total = len(rows)
        if total == 0:
            return {'ok': True, 'total': 0, 'focus_stats': [], 'block_stats': []}

        # Aggregate: for each item, collect all rank positions assigned by users
        focus_ranks = {}  # item -> list of rank positions (1-indexed)
        block_ranks = {}

        for row in rows:
            focus_list = row[0] if isinstance(row[0], list) else json.loads(row[0]) if row[0] else []
            block_list = row[1] if isinstance(row[1], list) else json.loads(row[1]) if row[1] else []

            for rank, item in enumerate(focus_list, 1):
                if item not in focus_ranks:
                    focus_ranks[item] = []
                focus_ranks[item].append(rank)

            for rank, item in enumerate(block_list, 1):
                if item not in block_ranks:
                    block_ranks[item] = []
                block_ranks[item].append(rank)

        # Calculate stats: avg rank, selection count
        def calc_stats(ranks_dict):
            stats = []
            for item, ranks in ranks_dict.items():
                avg_rank = sum(ranks) / len(ranks)
                stats.append({
                    'item': item,
                    'avg_rank': round(avg_rank, 2),
                    'times_selected': len(ranks),
                    'selection_rate': round(len(ranks) / total * 100, 1),
                })
            stats.sort(key=lambda x: x['avg_rank'])
            return stats

        return {
            'ok': True,
            'total': total,
            'focus_stats': calc_stats(focus_ranks),
            'block_stats': calc_stats(block_ranks),
        }
    finally:
        _release_db(conn)


# ============================================================
# 人格塑造、习惯养成、行为追踪系统 API (从emotion-sphere移植)
# ============================================================

# Pydantic 模型
class BehaviorRegulateRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    energy_level: int = Field(default=3, ge=1, le=5)
    motivation: int = Field(default=5, ge=1, le=10)


class HabitCreateRequest(BaseModel):
    habit_name: str = Field(min_length=1, max_length=200)
    anchor: str = Field(default='', max_length=200)
    energy_level: int = Field(default=3, ge=1, le=5)


class HabitExecuteRequest(BaseModel):
    habit_id: str = Field(min_length=1)
    energy_level: int = Field(default=3, ge=1, le=5)


class HabitLogRequest(BaseModel):
    habit_id: str = Field(min_length=1)
    tier_executed: str = Field(default='Yellow')
    was_completed: bool = Field(default=False)
    completion_percentage: int = Field(default=0, ge=0, le=100)
    mood_before: int = Field(default=5, ge=1, le=10)
    mood_after: int = Field(default=5, ge=1, le=10)


# ── 行为调节系统 API ─────────────────────────────────────────

@app.post('/api/behavior/regulate')
def behavior_regulate(payload: BehaviorRegulateRequest, request: Request):
    """
    行为调节引擎 - 动态行为工程学
    基于当前能量和动机水平，推荐最小可执行动作
    """
    try:
        from backend.habit_behavior_engine import regulate_behavior
        result = regulate_behavior(payload.task, payload.energy_level)
        
        # 记录到行为历史 (异步记录，不阻塞响应)
        user = _get_user_from_request(request)
        if user:
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    cur.execute(
                        '''INSERT INTO sfds_behavior_history 
                           (user_id, session_id, task, energy_level, motivation, tier_executed,
                            min_executable_action, task_downgrade, emotional_compensation, continuity_advice, spiritual_alignment)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (user['id'], str(uuid.uuid4()), payload.task, payload.energy_level, 
                         getattr(payload, 'motivation', 5), result.get('selected_tier', 'Yellow'),
                         result.get('min_executable_action', ''), result.get('task_downgrade', ''),
                         result.get('emotional_compensation', ''), result.get('continuity_advice', ''),
                         json.dumps(result.get('spiritual_alignment', {}), ensure_ascii=False))
                    )
                    conn.commit()
                _release_db(conn)
            except Exception as log_exc:
                print(f'[behavior_regulate] Log error: {log_exc}', flush=True)
        
        return result
    except Exception as exc:
        print(f'[behavior_regulate] Failed: {exc}', flush=True)
        tier = "Red" if payload.energy_level <= 2 else ("Yellow" if payload.energy_level <= 3 else "Green")
        return {
            "degraded": True,
            "selected_tier": tier,
            "min_executable_action": f"尝试{payload.task}的最小版本" if tier == "Red" else f"开始{payload.task}",
            "emotional_compensation": "系统智能降级，保持连续性",
            "continuity_advice": "任何微小启动都算成功"
        }


@app.get('/api/behavior/history')
def get_behavior_history(user_id: str = None, limit: int = 30, request: Request = None):
    """获取用户的行为调节历史"""
    user = _require_user(request)
    target_user_id = user_id or user['id']
    
    # 只能查询自己的数据
    if target_user_id != user['id']:
        raise HTTPException(status_code=403, detail='只能查看自己的数据')
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, task, energy_level, motivation, tier_executed,
                          min_executable_action, was_completed, completion_percentage,
                          executed_at, system_energy_state, spiritual_alignment
                   FROM sfds_behavior_history 
                   WHERE user_id = %s
                   ORDER BY executed_at DESC
                   LIMIT %s''',
                (target_user_id, limit)
            )
            rows = cur.fetchall()
            
            def _parse_json_safe(val):
                if not val:
                    return None
                try:
                    return json.loads(val)
                except Exception:
                    return None

            items = [{
                'id': str(r[0]),
                'task': r[1],
                'energy_level': r[2],
                'motivation': r[3],
                'tier_executed': r[4],
                'min_executable_action': r[5],
                'was_completed': r[6],
                'completion_percentage': r[7],
                'executed_at': r[8].isoformat() if r[8] else None,
                'system_energy_state': r[9],
                'spiritual_alignment': _parse_json_safe(r[10])
            } for r in rows]
            
        return {'items': items, 'count': len(items)}
    finally:
        _release_db(conn)


@app.get('/api/behavior/stats')
def get_behavior_stats(user_id: str = None, request: Request = None):
    """获取用户的行为调节统计"""
    user = _require_user(request)
    target_user_id = user_id or user['id']
    
    if target_user_id != user['id']:
        raise HTTPException(status_code=403, detail='只能查看自己的数据')
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 总体统计
            cur.execute(
                '''SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_completed THEN 1 ELSE 0 END) as completed,
                    AVG(completion_percentage) as avg_completion,
                    AVG(energy_level) as avg_energy
                   FROM sfds_behavior_history 
                   WHERE user_id = %s''',
                (target_user_id,)
            )
            row = cur.fetchone()
            
            total_regulations = row[0] or 0
            completed_regulations = row[1] or 0
            avg_completion_percentage = round(row[2] or 0, 1)
            avg_energy_level = round(row[3] or 3, 1)
            
            # 层级分布
            cur.execute(
                '''SELECT tier_executed, COUNT(*) 
                   FROM sfds_behavior_history 
                   WHERE user_id = %s
                   GROUP BY tier_executed''',
                (target_user_id,)
            )
            tier_distribution = {r[0]: r[1] for r in cur.fetchall()}
            
            # 最近7天统计
            cur.execute(
                '''SELECT COUNT(*) 
                   FROM sfds_behavior_history 
                   WHERE user_id = %s AND executed_at > NOW() - INTERVAL '7 days' ''',
                (target_user_id,)
            )
            last_7_days = cur.fetchone()[0] or 0
            
        return {
            'total_regulations': total_regulations,
            'completed_regulations': completed_regulations,
            'completion_rate': round((completed_regulations / total_regulations * 100), 1) if total_regulations > 0 else 0,
            'avg_completion_percentage': avg_completion_percentage,
            'avg_energy_level': avg_energy_level,
            'tier_distribution': tier_distribution,
            'last_7_days_regulations': last_7_days
        }
    finally:
        _release_db(conn)


# ── 习惯养成状态机 API ───────────────────────────────────────

@app.post('/api/habits/create')
def create_habit(payload: HabitCreateRequest, request: Request):
    """
    创建习惯状态机 - 三层动态电路保护
    """
    user = _require_user(request)
    user_id = user['id']
    
    try:
        from backend.habit_behavior_engine import create_habit
        result = create_habit(payload.habit_name, payload.anchor, payload.energy_level)
        
        # 保存到数据库
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                fsm_config = result.get('habit_config', {})
                cur.execute(
                    '''INSERT INTO habit_state_machines 
                       (user_id, habit_name, deterministic_anchor, 
                        tier_green_config, tier_yellow_config, tier_red_config,
                        token_green_yield, token_yellow_yield, token_red_yield)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id''',
                    (user_id, payload.habit_name, fsm_config.get('deterministic_anchor', ''),
                     json.dumps(fsm_config.get('tier_configs', {}).get('green', {})),
                     json.dumps(fsm_config.get('tier_configs', {}).get('yellow', {})),
                     json.dumps(fsm_config.get('tier_configs', {}).get('red', {})),
                     10, 5, 1)
                )
                row = cur.fetchone()
                conn.commit()
                result['saved_habit_id'] = str(row[0])
        finally:
            _release_db(conn)
        
        return result
        
    except Exception as exc:
        print(f'[habits_create] Failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='创建习惯失败')


@app.get('/api/habits')
def list_habits(request: Request):
    """获取用户的习惯列表"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, habit_name, deterministic_anchor, is_active,
                          current_streak_days, total_executions, last_execution_at,
                          tier_green_config, tier_yellow_config, tier_red_config
                   FROM habit_state_machines 
                   WHERE user_id = %s AND is_active = TRUE
                   ORDER BY created_at DESC''',
                (user_id,)
            )
            rows = cur.fetchall()
            
            items = [{
                'id': str(r[0]),
                'habit_name': r[1],
                'anchor': r[2],
                'is_active': r[3],
                'current_streak': r[4],
                'total_executions': r[5],
                'last_execution': r[6].isoformat() if r[6] else None,
                'tier_configs': {
                    'green': r[7],
                    'yellow': r[8],
                    'red': r[9]
                }
            } for r in rows]
            
            return {'items': items, 'total': len(items)}
    finally:
        _release_db(conn)


@app.post('/api/habits/{habit_id}/execute')
def execute_habit(habit_id: str, payload: HabitExecuteRequest, request: Request):
    """
    执行习惯状态机 - 根据当前能量动态选择层级
    """
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        # 获取习惯配置
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT habit_name, deterministic_anchor,
                          tier_green_config, tier_yellow_config, tier_red_config
                   FROM habit_state_machines 
                   WHERE id = %s AND user_id = %s''',
                (habit_id, user_id)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail='习惯未找到')
            
            habit_config = {
                'habit_name': row[0],
                'deterministic_anchor': row[1],
                'tier_configs': {
                    'green': row[2],
                    'yellow': row[3],
                    'red': row[4]
                }
            }
        
        # 执行状态机
        from backend.habit_behavior_engine import habit_fsm
        execution = habit_fsm.execute_habit(habit_config, payload.energy_level)
        
        return execution.to_dict()
        
    finally:
        _release_db(conn)


@app.post('/api/habits/{habit_id}/log')
def log_habit_execution(habit_id: str, payload: HabitLogRequest, request: Request):
    """
    记录习惯执行结果，更新代币和连胜
    """
    user = _require_user(request)
    user_id = user['id']
    
    # 代币计算
    tier_tokens = {'Green': 10, 'Yellow': 5, 'Red': 1}
    tokens_earned = tier_tokens.get(payload.tier_executed, 5)
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 记录执行日志
            cur.execute(
                '''INSERT INTO habit_execution_logs 
                   (user_id, habit_id, energy_level_at_execution, selected_tier,
                    tokens_earned, was_completed, completion_percentage,
                    circuit_breaker_triggered, mood_before, mood_after)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id''',
                (user_id, habit_id, 3, payload.tier_executed,
                 tokens_earned, payload.was_completed, payload.completion_percentage,
                 payload.tier_executed == 'Red',
                 payload.mood_before, payload.mood_after)
            )
            log_id = cur.fetchone()[0]
            
            # 更新习惯统计
            if payload.was_completed:
                cur.execute(
                    '''UPDATE habit_state_machines 
                       SET total_executions = total_executions + 1,
                           last_execution_at = NOW(),
                           current_streak_days = CASE 
                               WHEN last_execution_at >= CURRENT_DATE - INTERVAL '1 day' 
                               THEN current_streak_days + 1 
                               ELSE 1 
                           END
                       WHERE id = %s''',
                    (habit_id,)
                )
            
            # 更新代币账本
            cur.execute(
                '''INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (user_id) 
                   DO UPDATE SET 
                       current_balance = user_token_ledgers.current_balance + %s,
                       lifetime_earned = user_token_ledgers.lifetime_earned + %s,
                       last_updated = NOW()''',
                (user_id, tokens_earned, tokens_earned, tokens_earned, tokens_earned)
            )
            
            # 记录代币交易
            cur.execute(
                '''INSERT INTO token_transactions 
                   (user_id, transaction_type, amount, balance_after, habit_id, habit_log_id, description)
                   VALUES (%s, %s, %s, 
                       (SELECT current_balance FROM user_token_ledgers WHERE user_id = %s),
                       %s, %s, %s)''',
                (user_id, 'earn', tokens_earned, user_id, 
                 habit_id, log_id, f'{payload.tier_executed} tier execution')
            )
            
            conn.commit()
            
            return {
                'ok': True,
                'log_id': str(log_id),
                'tokens_earned': tokens_earned,
                'circuit_breaker_triggered': payload.tier_executed == 'Red',
                'anti_guilt_message': '系统已切换至保护模式。连胜保持。核心控制回路完整性100%。' 
                    if payload.tier_executed == 'Red' else None
            }
            
    finally:
        _release_db(conn)


@app.get('/api/habits/dashboard')
def habits_dashboard(request: Request):
    """习惯系统仪表盘"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT active_habits, today_executions, max_current_streak,
                          token_balance, last_habit_name, circuit_breaker_count
                   FROM user_habit_dashboard 
                   WHERE user_id = %s''',
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return {
                    'active_habits': 0,
                    'today_executions': 0,
                    'current_streak': 0,
                    'token_balance': 0,
                    'circuit_breaker_count': 0
                }
            
            return {
                'active_habits': row[0] or 0,
                'today_executions': row[1] or 0,
                'current_streak': row[2] or 0,
                'token_balance': row[3] or 0,
                'last_habit_name': row[4],
                'circuit_breaker_count': row[5] or 0
            }
    finally:
        _release_db(conn)
