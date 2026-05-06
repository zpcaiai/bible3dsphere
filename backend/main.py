import asyncio
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import smtplib
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
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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
    fetch_biblical_example,
    generate_sermon,
    prewarm_cache,
    query_emotion_verses,
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
    raise ValueError('DATABASE_URL environment variable is required')

# 全局数据库连接池
_db_pool = None
_db_type = 'sqlite'  # 'postgresql' 或 'sqlite'

# In-memory verify code store: email -> {code, expires}
_CODE_STORE: dict[str, dict] = {}
CODE_TTL_SECONDS = 600  # 10 minutes for reset codes

# Code generation helper
def _generate_code() -> str:
    """Generate a 6-digit verification code."""
    return f'{random.randint(0, 999999):06d}'

# 安全审计日志锁
_AUDIT_LOCK = threading.Lock()

def _init_database():
    """初始化 PostgreSQL 数据库连接。"""
    global _db_pool, _db_type
    import psycopg2
    from psycopg2 import pool
    _db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
    _db_type = 'postgresql'
    print('[db] PostgreSQL connection pool initialized', flush=True)


def _get_db():
    """获取 PostgreSQL 数据库连接。"""
    return _db_pool.getconn()


def _release_db(conn):
    """释放 PostgreSQL 数据库连接。"""
    _db_pool.putconn(conn)


def _security_audit(event_type: str, email: str = None, ip: str = None, details: dict = None, success: bool = True):
    """记录安全审计日志。"""
    with _AUDIT_LOCK:
        # 打印到日志（生产环境应发送到安全日志系统）
        status = 'SUCCESS' if success else 'FAILED'
        print(f'[SECURITY AUDIT] [{status}] {event_type} | email={email} | ip={ip} | details={details}', flush=True)

        # 写入审计日志表
        try:
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO security_audit (event_type, email, ip_address, details, success, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    ''', (event_type, email, ip[:45] if ip else None, json.dumps(details) if details else '{}', success))
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
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Devotion journals table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS devotion_journals (
                    id           SERIAL PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL,
                    date         DATE NOT NULL,
                    title        VARCHAR(255) NOT NULL DEFAULT '',
                    scripture    VARCHAR(500) DEFAULT '',
                    observation  TEXT DEFAULT '',
                    reflection   TEXT DEFAULT '',
                    application  TEXT DEFAULT '',
                    prayer       TEXT DEFAULT '',
                    mood         VARCHAR(50) DEFAULT '',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(email, date)
                )
            ''')

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
        else:
            # 兼容旧版格式（无前缀）
            salt, digest = stored.split(':', 1)
            return hmac.compare_digest(
                hashlib.sha256((salt + password).encode()).hexdigest(),
                digest
            )
    except Exception:
        return False


def _get_user(email: str) -> dict | None:
    """Get user by email (case-insensitive lookup)."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, email, nickname, avatar, openid, unionid, login_type, created_at FROM users WHERE LOWER(email) = LOWER(%s)', (email,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'email': row[1], 'nickname': row[2], 'avatar': row[3],
                'openid': row[4], 'unionid': row[5], 'login_type': row[6], 'created_at': row[7].timestamp() if row[7] else None
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
    now = time.time()
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
    _init_database()
    _init_db()
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
    yield


# 初始化速率限制器（Redis 可选，默认内存存储）
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title='Bible Emotion Sphere API', lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    # HSTS（仅在 HTTPS 环境）
    if request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


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

    if 'errcode' in data:
        raise HTTPException(status_code=401, detail=f'WeChat error: {data.get("errmsg", data)}')

    openid = data.get('openid', '')
    unionid = data.get('unionid', '')
    access_token = data.get('access_token', '')

    # Fetch basic user info from WeChat
    user_info = {}
    if access_token and openid:
        async with httpx.AsyncClient() as client:
            info_resp = await client.get(
                'https://api.weixin.qq.com/sns/userinfo',
                params={'access_token': access_token, 'openid': openid, 'lang': 'zh_CN'},
                timeout=10,
            )
        user_info = info_resp.json()

    # Get or create user in database
    now = time.time()
    with _get_db() as conn:
        # Try to find existing user by openid
        existing = conn.execute(
            'SELECT id, email, nickname, avatar, openid, unionid FROM users WHERE openid = ?',
            (openid,)
        ).fetchone()
        
        if existing:
            # Update user info
            user_id = existing['id']
            conn.execute(
                '''UPDATE users SET 
                   nickname = COALESCE(NULLIF(?, ''), nickname),
                   avatar = COALESCE(NULLIF(?, ''), avatar),
                   unionid = COALESCE(?, unionid)
                   WHERE id = ?''',
                (user_info.get('nickname', ''), user_info.get('headimgurl', ''), unionid, user_id)
            )
            conn.commit()
            user_record = {
                'id': user_id,
                'openid': openid,
                'unionid': unionid or existing['unionid'],
                'nickname': user_info.get('nickname') or existing['nickname'] or '',
                'avatar': user_info.get('headimgurl') or existing['avatar'] or '',
                'email': existing['email'],
            }
        else:
            # Create new WeChat user
            cursor = conn.execute(
                '''INSERT INTO users (openid, unionid, nickname, avatar, login_type, created_at)
                   VALUES (?, ?, ?, ?, 'wechat', ?)''',
                (openid, unionid, user_info.get('nickname', ''), user_info.get('headimgurl', ''), now)
            )
            conn.commit()
            user_id = cursor.lastrowid
            user_record = {
                'id': user_id,
                'openid': openid,
                'unionid': unionid,
                'nickname': user_info.get('nickname', ''),
                'avatar': user_info.get('headimgurl', ''),
                'email': None,
            }
    
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
    if not _verify_password(payload.password, user_record.get('password_hash', '')):
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip, details={'reason': 'wrong_password'}, success=False)
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
    except Exception as exc:
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


@app.post('/api/user/checkin')
def post_checkin(payload: CheckinRequest, request: Request) -> dict:
    """Save checkin data and update user tags. Auth optional – tags skipped for guests."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    print(f'[checkin] received email={email or "guest"} emotion={payload.emotionLabel}', flush=True)
    data = payload.model_dump()

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
def get_prayers(limit: int = 40, offset: int = 0) -> dict:
    """Return public prayer list (newest first)."""
    print(f'[prayers] list request limit={limit} offset={offset}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, nickname, content, is_anonymous, amen_count, created_at '
                'FROM prayers ORDER BY created_at DESC LIMIT %s OFFSET %s',
                (min(limit, 100), offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM prayers')
            total = cur.fetchone()[0]
        items = []
        for row in rows:
            pid, nickname, content, is_anon, amen, created_at = row
            items.append({
                'id': pid,
                'nickname': '匿名弟兄姊妹' if is_anon else (nickname or '弟兄姊妹'),
                'content': content,
                'amen_count': amen,
                'created_at': created_at.isoformat() if created_at else None,
            })
        print(f'[prayers] returning {len(items)}/{total} items', flush=True)
        return {'ok': True, 'items': items, 'total': total}
    finally:
        _release_db(conn)


@app.post('/api/prayers')
def post_prayer(payload: PrayerSubmitRequest, request: Request) -> dict:
    """Submit a new prayer. Auth optional – guests can post anonymously."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    nickname = user.get('nickname', '') if user else ''
    print(f'[prayers] submit email={email or "guest"} anon={payload.is_anonymous} len={len(payload.content)}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO prayers (email, nickname, content, is_anonymous, amen_count) VALUES (%s,%s,%s,%s,0) RETURNING id',
                (email, nickname, payload.content.strip(), payload.is_anonymous)
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
                'UPDATE prayers SET amen_count = amen_count + 1 WHERE id = %s',
                (prayer_id,)
            )
            updated = cur.rowcount
            conn.commit()
        if not updated:
            print(f'[prayers] amen failed: prayer_id={prayer_id} not found', flush=True)
            raise HTTPException(status_code=404, detail='Prayer not found')
        with conn.cursor() as cur:
            cur.execute('SELECT amen_count FROM prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
        new_count = row[0] if row else 0
        print(f'[prayers] amen ok prayer_id={prayer_id} amen_count={new_count}', flush=True)
        return {'ok': True, 'amen_count': new_count}
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


def _row_to_journal(row) -> dict:
    return {
        'id': row[0],
        'email': row[1],
        'date': row[2],
        'title': row[3],
        'scripture': row[4],
        'observation': row[5],
        'reflection': row[6],
        'application': row[7],
        'prayer': row[8],
        'mood': row[9],
        'created_at': row[10].isoformat() if row[10] else None,
        'updated_at': row[11].isoformat() if row[11] else None,
    }


@app.get('/api/devotion/journals')
def get_journals(request: Request, limit: int = 50, offset: int = 0) -> dict:
    """List current user's devotion journals, newest first."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    print(f'[devotion] list journals email={email} limit={limit} offset={offset}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, email, date, title, scripture, observation, reflection, application, prayer, mood, created_at, updated_at '
                'FROM devotion_journals WHERE email=%s ORDER BY date DESC, updated_at DESC LIMIT %s OFFSET %s',
                (email, min(limit, 200), offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM devotion_journals WHERE email=%s', (email,))
            total = cur.fetchone()[0]
        items = [_row_to_journal(r) for r in rows]
        print(f'[devotion] list ok {len(items)}/{total}', flush=True)
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
    print(f'[devotion] save journal email={email} date={payload.date} title={payload.title[:30]}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM devotion_journals WHERE email=%s AND date=%s', (email, payload.date)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    '''UPDATE devotion_journals
                       SET title=%s, scripture=%s, observation=%s, reflection=%s, application=%s, prayer=%s, mood=%s, updated_at=NOW()
                       WHERE email=%s AND date=%s''',
                    (payload.title, payload.scripture, payload.observation, payload.reflection,
                     payload.application, payload.prayer, payload.mood, email, payload.date)
                )
                journal_id = existing[0]
                print(f'[devotion] updated id={journal_id}', flush=True)
            else:
                cur.execute(
                    '''INSERT INTO devotion_journals
                       (email, date, title, scripture, observation, reflection, application, prayer, mood)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
                    (email, payload.date, payload.title, payload.scripture, payload.observation,
                     payload.reflection, payload.application, payload.prayer, payload.mood)
                )
                journal_id = cur.fetchone()[0]
                print(f'[devotion] created id={journal_id}', flush=True)
            conn.commit()
            cur.execute('SELECT id, email, date, title, scripture, observation, reflection, application, prayer, mood, created_at, updated_at FROM devotion_journals WHERE id=%s', (journal_id,))
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
                'SELECT id, email, date, title, scripture, observation, reflection, application, prayer, mood, created_at, updated_at FROM devotion_journals WHERE id=%s AND email=%s',
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
    """Delete a journal entry owned by the current user."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    print(f'[devotion] delete journal id={journal_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'DELETE FROM devotion_journals WHERE id=%s AND email=%s', (journal_id, email)
            )
            deleted = cur.rowcount
            conn.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail='Journal not found')
        print(f'[devotion] deleted id={journal_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── end Devotion Journal ──────────────────────────────────────


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

    messages_for_api = [{'role': 'system', 'content': system_content}]
    for m in payload.messages:
        messages_for_api.append({'role': m.role, 'content': m.content})

    # Save user message to DB
    last_user_msg = next(
        (m.content for m in reversed(payload.messages) if m.role == 'user'), None
    )
    if last_user_msg and email:
        with _get_db() as conn:
            conn.execute(
                'INSERT INTO conversation_messages (email, session_id, role, content, created_at) VALUES (?,?,?,?,?)',
                (email, session_id, 'user', last_user_msg, time.time())
            )
            conn.commit()
        print(f'[chat] user message saved session={session_id} len={len(last_user_msg)}', flush=True)

    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        api_key = 'AIzaSyDIWBd3M1DO6-16RukYO4_K9rLBWV0ZHGs'

    req_body = {
        'model': 'gemini-2.0-flash',
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
        async with _httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                'POST',
                'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                json=req_body,
                headers=headers_api,
            ) as resp:
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

        # After streaming done: save assistant reply + trigger tag extraction
        full_reply = ''.join(assistant_chunks)
        print(f'[chat] stream done session={session_id} reply_len={len(full_reply)}', flush=True)
        if full_reply and email:
            with _get_db() as conn:
                conn.execute(
                    'INSERT INTO conversation_messages (email, session_id, role, content, created_at) VALUES (?,?,?,?,?)',
                    (email, session_id, 'assistant', full_reply, time.time())
                )
                conn.commit()
            print(f'[chat] assistant reply saved session={session_id}', flush=True)

            # Trigger tag extraction every 3 user turns (avoid over-calling LLM)
            with _get_db() as conn:
                count = conn.execute(
                    'SELECT COUNT(*) as c FROM conversation_messages WHERE email=? AND role="user"',
                    (email,)
                ).fetchone()['c']
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
        return FileResponse(FRONTEND_DIST / 'index.html')
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
        return FileResponse(FRONTEND_DIST / 'index.html')

    raise HTTPException(status_code=404, detail='Frontend build output not found. Run npm run build in emotion-sphere-ui first.')
