import asyncio
import base64
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
from fastapi.responses import RedirectResponse, JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from typing import List

# 安全中间件
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from backend.core.config import settings
    from backend.core.migrations import run_migrations
    from backend.core.security import (
        BCRYPT_AVAILABLE,
        EMAIL_RE,
        hash_password as _hash_password,
        sanitize_text as _sanitize_text,
        validate_date_str as _validate_date_str,
        verify_password as _verify_password,
    )
except ImportError:
    from core.config import settings
    from core.migrations import run_migrations
    from core.security import (
        BCRYPT_AVAILABLE,
        EMAIL_RE,
        hash_password as _hash_password,
        sanitize_text as _sanitize_text,
        validate_date_str as _validate_date_str,
        verify_password as _verify_password,
    )

from query_emotion_verses import (
    DEFAULT_RERANK_CANDIDATES,
    DEFAULT_RERANK_WEIGHT,
    EMBEDDING_CACHE_FILE,
    FEATURES_FILE,
    assess_psychological_state,
    call_chat,
    fetch_biblical_example,
    generate_faith_qa,
    generate_sermon,
    prewarm_cache,
    query_emotion_verses,
    _strip_markdown_json,
)
from web_emotion_query import HISTORY_FILE, load_history, save_history_entry

LAYOUT_FILE = ROOT_DIR / 'emotion_sphere_layout.json'
MATCHES_FILE = ROOT_DIR / 'emotion_exemplar_verse_matches.json'
STATS_FILE = ROOT_DIR / 'visit_stats.json'
STATS_LOCK = threading.Lock()
EVALUATION_CASES_FILE = ROOT_DIR / 'evaluation' / 'retrieval_cases.json'
EVALUATION_REPORT_FILE = ROOT_DIR / 'evaluation' / 'reports' / 'retrieval_eval_latest.json'
ARTIFACT_MANIFEST_FILE = ROOT_DIR / 'artifact_manifest.json'

# HF Spaces persistence configuration
HF_TOKEN = settings.hf_token
HF_STATS_REPO = settings.hf_stats_repo
HF_STATS_PATH = settings.hf_stats_path

# HF Data source for large files removed from Git LFS
HF_DATA_REPO = settings.hf_data_repo
HF_DATA_FILES: list[tuple[str, int]] = [
    # (filename, min_expected_size_bytes)  -  files auto-downloaded if missing or too small
    ('bible_bilingual_metadata.pkl', 15 * 1024 * 1024),       # ~19 MB
    ('bible_bilingual_vector_cuv.npy', 100 * 1024 * 1024),  # ~127 MB
    ('bible_bilingual_vector_esv.npy', 100 * 1024 * 1024),  # ~127 MB
]

# 大向量/元数据下载源：优先 R2(cdn.holiness.uk/npy)，回退 HF Space。可用 VECTOR_DATA_BASE_URL 覆盖。
VECTOR_DATA_BASE_URL = os.environ.get('VECTOR_DATA_BASE_URL', 'https://cdn.holiness.uk/npy').rstrip('/')

# WeChat Open Platform config
WX_APP_ID = settings.wx_app_id
WX_APP_SECRET = settings.wx_app_secret
WX_REDIRECT_URI = settings.wx_redirect_uri

# Email SMTP config (default: sina.com — 465 SSL)
SMTP_HOST = settings.smtp_host
SMTP_PORT = settings.smtp_port
SMTP_USER = settings.smtp_user
SMTP_PASS = settings.smtp_pass
SMTP_FROM = settings.smtp_from
RESEND_API_KEY = settings.resend_api_key
SENDGRID_API_KEY = settings.sendgrid_api_key

# 数据库配置 (仅 PostgreSQL)
DATABASE_URL = settings.database_url
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


def _load_json_file(path: Path, default):
    try:
        if not path.exists():
            return default
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as exc:
        print(f'[json] WARNING: failed to load {path}: {exc}', flush=True)
        return default


def _load_retrieval_observability_from_db() -> tuple[dict | None, dict | None]:
    if not _db_pool:
        return None, None
    conn = None
    try:
        conn = _get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT top_k, summary, cases, source_path, created_at
                FROM retrieval_eval_runs
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            eval_row = cur.fetchone()
            cur.execute(
                """
                SELECT payload, source_path, created_at
                FROM artifact_manifests
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            manifest_row = cur.fetchone()

        report = None
        if eval_row:
            report = {
                'top_k': eval_row[0],
                'summary': eval_row[1] or {},
                'cases': eval_row[2] or [],
                'source_path': eval_row[3],
                'loaded_from': 'database',
                'created_at': _to_shanghai_iso(eval_row[4]),
            }

        manifest = None
        if manifest_row:
            manifest = manifest_row[0] or {}
            if isinstance(manifest, dict):
                manifest = {
                    **manifest,
                    'source_path': manifest_row[1],
                    'loaded_from': 'database',
                    'created_at': _to_shanghai_iso(manifest_row[2]),
                }
        return report, manifest
    except Exception as exc:
        print(f'[retrieval-eval] DB load skipped: {exc}', flush=True)
        return None, None
    finally:
        if conn is not None:
            _release_db(conn)

# 安全审计日志锁
_AUDIT_LOCK = threading.Lock()

def _init_database():
    """初始化 PostgreSQL 数据库连接。"""
    global _db_pool
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import Json
    import psycopg2.extensions as ext
    # 仅把 dict 自动适配为 JSONB（无歧义）。不要再全局注册 list→Json：
    # 它会把传给「IN 多值过滤」的 Python list 误序列化成 JSON 字符串，
    # 触发 "malformed array literal" 而被 except 静默吞掉。规则：多值过滤一律用
    # tuple()+`IN %s`；写 JSONB 请显式 json.dumps(...) 或 psycopg2.extras.Json(...)。
    # 回归守护见 tests/test_db_param_safety.py。
    ext.register_adapter(dict, Json)
    _db_pool = psycopg2.pool.ThreadedConnectionPool(
        2, 50, DATABASE_URL,
        connect_timeout=10,
        keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3,
    )
    print('[db] PostgreSQL connection pool initialized (min=2, max=50, keepalive on)', flush=True)


def _get_db():
    """获取 PostgreSQL 数据库连接。

    带退避重试：Render/Neon 等托管库会不定期掐断空闲或握手中的 SSL 连接
    （"SSL connection has been closed unexpectedly"），新建连接瞬时失败时
    重试 3 次而不是直接把 503 抛给用户。"""
    import time as _time
    import psycopg2 as _pg
    from psycopg2.pool import PoolError as _PoolError
    last_exc = None
    for _attempt in range(3):
        conn = None
        try:
            conn = _db_pool.getconn()
            if conn.closed:
                _db_pool.putconn(conn, close=True)
                conn = _db_pool.getconn()
            conn.autocommit = False
            # Test the connection is alive
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
            return conn
        except Exception as exc:
            if conn is not None:
                try:
                    _db_pool.putconn(conn, close=True)
                except Exception:
                    pass
            if not isinstance(exc, (_pg.Error, _PoolError)):
                raise
            last_exc = exc
            print(f'[db] get connection attempt {_attempt + 1}/3 failed: {exc}', flush=True)
            _time.sleep(0.5 * (_attempt + 1))
    raise last_exc


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

def _init_db() -> None:
    """初始化 PostgreSQL 数据库表。"""
    print('[db] initializing PostgreSQL database tables...', flush=True)
    _init_db_postgresql()


def _init_db_postgresql():
    """初始化 PostgreSQL 数据库表（schema DDL 见 db_schema.py）。"""
    from db_schema import init_db_postgresql
    init_db_postgresql(_get_db, _release_db, _hash_password)


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


def _get_user(email: str) -> dict | None:
    """Get user by email (case-insensitive lookup)."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    'SELECT id, email, nickname, avatar, openid, unionid, login_type, '
                    'password_hash, created_at, is_admin, is_banned '
                    'FROM users WHERE LOWER(email) = LOWER(%s)',
                    (email,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    'id': row[0], 'email': row[1], 'nickname': row[2], 'avatar': row[3],
                    'openid': row[4], 'unionid': row[5], 'login_type': row[6],
                    'password_hash': row[7] or '',
                    'created_at': row[8].timestamp() if row[8] else None,
                    'is_admin': bool(row[9]),
                    'is_banned': bool(row[10]),
                }
            except Exception:
                conn.rollback()
                cur.execute(
                    'SELECT id, email, nickname, avatar, openid, unionid, login_type, '
                    'password_hash, created_at FROM users WHERE LOWER(email) = LOWER(%s)',
                    (email,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    'id': row[0], 'email': row[1], 'nickname': row[2], 'avatar': row[3],
                    'openid': row[4], 'unionid': row[5], 'login_type': row[6],
                    'password_hash': row[7] or '',
                    'created_at': row[8].timestamp() if row[8] else None,
                    'is_admin': False,
                    'is_banned': False,
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
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_FROM, [to], msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
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


def _fetch_to_file(url: str, path, filename: str) -> int:
    """下载单个 URL 到文件，返回最终字节数；失败抛异常。"""
    import urllib.request
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'bible-sphere-backend/1.0')
    with urllib.request.urlopen(req, timeout=120) as response:
        total_size = int(response.headers.get('Content-Length', 0))
        chunk_size = 1024 * 1024  # 1 MB
        downloaded = 0
        with open(path, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size and downloaded % (5 * chunk_size) < chunk_size:
                    pct = downloaded / total_size * 100
                    print(f'[startup] {filename}: {pct:.0f}% ({downloaded / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB)', flush=True)
    return path.stat().st_size


def _download_hf_data_files() -> None:
    """下载大向量/元数据文件（缺失或过小则下）。下载源优先 R2(VECTOR_DATA_BASE_URL)，回退 HF Space。"""
    for filename, min_size in HF_DATA_FILES:
        path = ROOT_DIR / filename
        current_size = path.stat().st_size if path.exists() else 0
        if current_size >= min_size:
            print(f'[startup] {filename}: {current_size / 1024 / 1024:.1f} MB - OK', flush=True)
            continue

        candidates = [
            (f'{VECTOR_DATA_BASE_URL}/{filename}', 'R2'),
            (f'https://huggingface.co/spaces/{HF_DATA_REPO}/resolve/main/{filename}', 'HF'),
        ]
        print(f'[startup] {filename}: {current_size} bytes (need {min_size / 1024 / 1024:.0f} MB) - downloading...', flush=True)
        ok = False
        for url, src in candidates:
            try:
                print(f'[startup] try {src}: {url}', flush=True)
                final_size = _fetch_to_file(url, path, filename)
                if final_size < min_size:
                    print(f'[startup] WARNING: {filename} from {src} size {final_size} < expected {min_size}, 尝试下一个源', flush=True)
                    continue
                print(f'[startup] {filename}: downloaded {final_size / 1024 / 1024:.1f} MB from {src}', flush=True)
                ok = True
                break
            except Exception as exc:
                print(f'[startup] {src} 下载失败 {filename}: {exc}', flush=True)
        if not ok:
            print(f'[startup] ERROR: {filename} 所有下载源均失败', flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB, migrate old data, download model files, pre-warm cache at startup."""
    # 初始化数据库连接（优先 PostgreSQL）
    if DATABASE_URL:
        try:
            _init_database()
            try:
                applied = run_migrations(DATABASE_URL)
                if applied:
                    versions = ', '.join(record.version for record in applied)
                    print(f'[db] migrations applied: {versions}', flush=True)
                else:
                    print('[db] migrations up to date', flush=True)
            except Exception as exc:
                print(f'[db] WARNING: migration runner failed: {exc}', flush=True)
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
            # 初始化 reflection_surveys 表
            try:
                conn = _get_db()
                try:
                    with conn.cursor() as cur:
                        cur.execute('''
                            CREATE TABLE IF NOT EXISTS reflection_surveys (
                                id           BIGSERIAL PRIMARY KEY,
                                user_id      TEXT NOT NULL,
                                answers      JSONB NOT NULL DEFAULT '{}',
                                updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                        ''')
                        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_reflection_surveys_user ON reflection_surveys (user_id)')
                        conn.commit()
                        print('[sfds] reflection_surveys table initialized', flush=True)
                finally:
                    _release_db(conn)
            except Exception as exc:
                print(f'[sfds] WARNING: reflection_surveys init failed: {exc}', flush=True)
            # 初始化习惯状态机表 — each table in its own block so failures are isolated
            for _ddl, _label in [
                ('''CREATE TABLE IF NOT EXISTS habit_state_machines (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        habit_name TEXT NOT NULL,
                        deterministic_anchor TEXT DEFAULT '',
                        tier_green_config JSONB DEFAULT '{}'::jsonb,
                        tier_yellow_config JSONB DEFAULT '{}'::jsonb,
                        tier_red_config JSONB DEFAULT '{}'::jsonb,
                        token_green_yield INTEGER DEFAULT 10,
                        token_yellow_yield INTEGER DEFAULT 5,
                        token_red_yield INTEGER DEFAULT 1,
                        is_active BOOLEAN DEFAULT TRUE,
                        current_streak_days INTEGER DEFAULT 0,
                        total_executions INTEGER DEFAULT 0,
                        last_execution_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )''', 'habit_state_machines'),
                ('''CREATE TABLE IF NOT EXISTS habit_executions (
                        id SERIAL PRIMARY KEY,
                        habit_id INTEGER REFERENCES habit_state_machines(id) ON DELETE CASCADE,
                        user_id TEXT NOT NULL,
                        tier_executed TEXT NOT NULL,
                        was_completed BOOLEAN DEFAULT FALSE,
                        completion_percentage INTEGER DEFAULT 0,
                        mood_before INTEGER DEFAULT 5,
                        mood_after INTEGER DEFAULT 5,
                        tokens_earned INTEGER DEFAULT 0,
                        executed_at TIMESTAMPTZ DEFAULT NOW()
                    )''', 'habit_executions'),
                ('''CREATE TABLE IF NOT EXISTS habit_execution_logs (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        habit_id TEXT NOT NULL,
                        energy_level_at_execution INTEGER DEFAULT 3,
                        selected_tier TEXT NOT NULL DEFAULT 'Yellow',
                        tokens_earned INTEGER DEFAULT 5,
                        was_completed BOOLEAN DEFAULT FALSE,
                        completion_percentage INTEGER DEFAULT 0,
                        circuit_breaker_triggered BOOLEAN DEFAULT FALSE,
                        mood_before INTEGER DEFAULT 5,
                        mood_after INTEGER DEFAULT 5,
                        executed_at TIMESTAMPTZ DEFAULT NOW()
                    )''', 'habit_execution_logs'),
                ('''CREATE TABLE IF NOT EXISTS user_token_ledgers (
                        user_id TEXT PRIMARY KEY,
                        current_balance INTEGER DEFAULT 0,
                        lifetime_earned INTEGER DEFAULT 0,
                        last_updated TIMESTAMPTZ DEFAULT NOW()
                    )''', 'user_token_ledgers'),
                ('''CREATE TABLE IF NOT EXISTS token_transactions (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        transaction_type TEXT NOT NULL DEFAULT 'earn',
                        amount INTEGER NOT NULL,
                        balance_after INTEGER DEFAULT 0,
                        habit_id TEXT,
                        habit_log_id BIGINT,
                        description TEXT DEFAULT '',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )''', 'token_transactions'),
                ('''CREATE OR REPLACE VIEW user_habit_dashboard AS
                    SELECT
                        hsm.user_id,
                        COUNT(DISTINCT hsm.id) FILTER (WHERE hsm.is_active) AS active_habits,
                        COUNT(hel.id) FILTER (WHERE hel.executed_at >= CURRENT_DATE) AS today_executions,
                        COALESCE(MAX(hsm.current_streak_days), 0) AS max_current_streak,
                        COALESCE(MAX(utl.current_balance), 0) AS token_balance,
                        (SELECT hsm2.habit_name FROM habit_state_machines hsm2
                         WHERE hsm2.user_id = hsm.user_id AND hsm2.is_active
                         ORDER BY hsm2.last_execution_at DESC NULLS LAST LIMIT 1) AS last_habit_name,
                        COUNT(hel.id) FILTER (WHERE hel.circuit_breaker_triggered) AS circuit_breaker_count
                    FROM habit_state_machines hsm
                    LEFT JOIN habit_execution_logs hel ON hel.user_id = hsm.user_id
                    LEFT JOIN user_token_ledgers utl ON utl.user_id = hsm.user_id
                    GROUP BY hsm.user_id''', 'user_habit_dashboard view'),
            ]:
                try:
                    conn = _get_db()
                    try:
                        with conn.cursor() as cur:
                            cur.execute(_ddl)
                        conn.commit()
                        print(f'[habits] {_label} ready', flush=True)
                    finally:
                        _release_db(conn)
                except Exception as exc:
                    print(f'[habits] WARNING: {_label} init failed: {exc}', flush=True)
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

    # ── 初始化 Domain routers ─────────────────────────────────────────────────
    try:
        from core.deps import init_deps
        init_deps(_db_pool, settings)
        try:
            import llm_provider as _llm_provider
            _llm_provider.set_db_accessors(_get_db, _release_db)
            print('[llm] provider event logging wired', flush=True)
        except Exception as _exc:
            print(f'[llm] WARNING: provider logging not wired: {_exc}', flush=True)
        print('[routers] core deps initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: deps init failed: {exc}', flush=True)

    # Telemetry -- must be first so all routers inherit the tracer provider
    try:
        setup_telemetry(service_name='bible3dsphere-backend')
        print('[telemetry] OpenTelemetry initialized', flush=True)
    except Exception as exc:
        print(f'[telemetry] WARNING: setup_telemetry failed: {exc}', flush=True)

    try:
        init_stats_router(
            stats_lock=STATS_LOCK,
            load_visit_stats=load_visit_stats,
            public_visit_stats=public_visit_stats,
            track_visit=track_visit,
            load_json_file=load_json_file,
            build_feature_match_map=build_feature_match_map,
            load_history=load_history,
            load_retrieval_observability_from_db=_load_retrieval_observability_from_db,
            load_json_file_raw=_load_json_file,
            layout_file=LAYOUT_FILE,
            evaluation_cases_file=EVALUATION_CASES_FILE,
            evaluation_report_file=EVALUATION_REPORT_FILE,
            artifact_manifest_file=ARTIFACT_MANIFEST_FILE,
            root_dir=ROOT_DIR,
        )
        print('[routers] stats router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: stats router init failed: {exc}', flush=True)

    try:
        init_verse_router(
            query_emotion_verses=query_emotion_verses,
            assess_psychological_state=assess_psychological_state,
            fetch_biblical_example=fetch_biblical_example,
            generate_sermon=generate_sermon,
            generate_faith_qa=generate_faith_qa,
            call_chat=call_chat,
            save_history_entry=save_history_entry,
            get_session_user=_get_session_user,
            get_user_tags=_get_user_tags,
            build_user_context_prompt=_build_user_context_prompt,
            startup_check=_startup_check,
            handle_exc=_handle_exc,
            features_file=FEATURES_FILE,
            matches_file=ROOT_DIR / 'emotion_exemplar_verse_matches.json',
            embedding_cache_file=ROOT_DIR / 'emotion_feature_embedding_cache.json',
            root_dir=ROOT_DIR,
            debug=_DEBUG,
            google_tts_api_key=GOOGLE_TTS_API_KEY,
            elevenlabs_api_key=settings.elevenlabs_api_key,
            elevenlabs_voice_id=settings.elevenlabs_voice_id,
            elevenlabs_model=settings.elevenlabs_model,
        )
        print('[routers] verse router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: verse router init failed: {exc}', flush=True)

    try:
        init_journal_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            sanitize_text=_sanitize_text,
            validate_date_str=_validate_date_str,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] journal router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: journal router init failed: {exc}', flush=True)
    try:
        init_emotion_trajectory_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _release_db=_release_db,
            _to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] emotion_trajectory router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: emotion_trajectory router init failed: {exc}', flush=True)
    try:
        init_milestones_health_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _release_db=_release_db,
        )
        print('[routers] milestones_health router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: milestones_health router init failed: {exc}', flush=True)
    try:
        init_daily_soul_question_router(
            _award_milestone_if_due=_award_milestone_if_due,
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _release_db=_release_db,
            _sanitize_text=_sanitize_text,
        )
        print('[routers] daily_soul_question router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: daily_soul_question router init failed: {exc}', flush=True)
    try:
        init_user_profile_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _release_db=_release_db,
            _sanitize_text=_sanitize_text,
        )
        print('[routers] user_profile router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: user_profile router init failed: {exc}', flush=True)
    try:
        init_recycle_bin_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _is_admin=_is_admin,
            _release_db=_release_db,
            _to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] recycle_bin router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: recycle_bin router init failed: {exc}', flush=True)
    try:
        init_reflection_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _release_db=_release_db,
        )
        print('[routers] reflection router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: reflection router init failed: {exc}', flush=True)
    try:
        init_dating_priority_router(
            _get_db=_get_db,
            _release_db=_release_db,
        )
        print('[routers] dating_priority router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: dating_priority router init failed: {exc}', flush=True)
    try:
        init_personal_notes_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _release_db=_release_db,
            _sanitize_text=_sanitize_text,
            _to_shanghai_iso=_to_shanghai_iso,
            _validate_date_str=_validate_date_str,
        )
        print('[routers] personal_notes router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: personal_notes router init failed: {exc}', flush=True)
    try:
        init_evangelism_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _is_admin=_is_admin,
            _release_db=_release_db,
            _sanitize_text=_sanitize_text,
            _to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] evangelism router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: evangelism router init failed: {exc}', flush=True)
    try:
        init_bible_reading_router(
            _get_db=_get_db,
            _get_session_user=_get_session_user,
            _release_db=_release_db,
            _sanitize_text=_sanitize_text,
        )
        print('[routers] bible_reading router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: bible_reading router init failed: {exc}', flush=True)
    try:
        init_spiritual_partner_router(
            _get_session_user=_get_session_user,
            _get_db=_get_db,
            _release_db=_release_db,
        )
        print('[routers] spiritual_partner router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: spiritual_partner router init failed: {exc}', flush=True)

    try:
        init_prayer_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
            sanitize_text=_sanitize_text,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] prayer router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: prayer router init failed: {exc}', flush=True)

    try:
        init_testimony_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
            sanitize_text=_sanitize_text,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] testimony router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: testimony router init failed: {exc}', flush=True)

    try:
        init_realtime_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            sanitize_text=_sanitize_text,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] realtime router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: realtime router init failed: {exc}', flush=True)

    try:
        init_voice_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] voice router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: voice router init failed: {exc}', flush=True)

    try:
        init_meetings_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
        )
        print('[routers] meetings router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: meetings router init failed: {exc}', flush=True)

    try:
        init_personal_store_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
        )
        print('[routers] personal-store router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: personal-store router init failed: {exc}', flush=True)

    try:
        init_idolatry_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] idolatry router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: idolatry router init failed: {exc}', flush=True)

    try:
        init_worldview_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] worldview router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: worldview router init failed: {exc}', flush=True)

    try:
        init_worldview_lenses_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] worldview-lenses router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: worldview-lenses router init failed: {exc}', flush=True)

    try:
        init_waiting_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] waiting router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: waiting router init failed: {exc}', flush=True)

    try:
        init_pastoral_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
        )
        print('[routers] pastoral router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: pastoral router init failed: {exc}', flush=True)

    try:
        init_examen_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] examen router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: examen router init failed: {exc}', flush=True)

    try:
        init_productization_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] productization router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: productization router init failed: {exc}', flush=True)

    try:
        init_analytics_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] analytics router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: analytics router init failed: {exc}', flush=True)

    try:
        init_platform_admin_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] platform_admin router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: platform_admin router init failed: {exc}', flush=True)

    try:
        init_billing_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] billing router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: billing router init failed: {exc}', flush=True)

    try:
        init_org_console_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] org_console router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: org_console router init failed: {exc}', flush=True)

    try:
        init_ai_tutor_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] ai_tutor router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: ai_tutor router init failed: {exc}', flush=True)

    try:
        init_spiritual_memory_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] spiritual_memory router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: spiritual_memory router init failed: {exc}', flush=True)

    try:
        init_formation_agent_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] formation_agent router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: formation_agent router init failed: {exc}', flush=True)

    try:
        init_timeline_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] timeline router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: timeline router init failed: {exc}', flush=True)

    try:
        init_doctrine_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] doctrine router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: doctrine router init failed: {exc}', flush=True)

    try:
        init_church_integration_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] church_integration router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: church_integration router init failed: {exc}', flush=True)

    try:
        init_discipleship_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] discipleship router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: discipleship router init failed: {exc}', flush=True)

    try:
        init_accountability_group_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] accountability_group router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: accountability_group router init failed: {exc}', flush=True)

    try:
        init_mentor_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] mentor router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mentor router init failed: {exc}', flush=True)

    try:
        init_fasting_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] fasting router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: fasting router init failed: {exc}', flush=True)

    try:
        init_sabbath_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] sabbath router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: sabbath router init failed: {exc}', flush=True)

    try:
        init_fruit_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] fruit router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: fruit router init failed: {exc}', flush=True)

    try:
        init_temptation_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] temptation router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: temptation router init failed: {exc}', flush=True)

    try:
        init_presence_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] presence router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: presence router init failed: {exc}', flush=True)

    try:
        init_prayer_rule_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] prayer_rule router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: prayer_rule router init failed: {exc}', flush=True)

    try:
        init_intercession_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] intercession router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: intercession router init failed: {exc}', flush=True)

    try:
        init_lectio_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] lectio router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: lectio router init failed: {exc}', flush=True)

    try:
        init_psalm_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] psalm router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: psalm router init failed: {exc}', flush=True)

    try:
        init_mission_life_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] mission_life router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission_life router init failed: {exc}', flush=True)

    try:
        init_batch7_13_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] batch7_13 formation-os router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: batch7_13 router init failed: {exc}', flush=True)

    try:
        init_formation_advanced_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] formation_advanced router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: formation_advanced router init failed: {exc}', flush=True)

    try:
        init_batch1_4_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] batch1_4 formation-os router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: batch1_4 router init failed: {exc}', flush=True)

    try:
        init_guardian_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] guardian router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: guardian router init failed: {exc}', flush=True)

    try:
        init_crisis_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] crisis router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: crisis router init failed: {exc}', flush=True)

    try:
        init_push_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
        )
        print('[routers] push router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: push router init failed: {exc}', flush=True)

    try:
        init_reading_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
        )
        print('[routers] reading router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: reading router init failed: {exc}', flush=True)

    try:
        init_memory_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] memory router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: memory router init failed: {exc}', flush=True)

    try:
        init_gratitude_router(get_db=_get_db, release_db=_release_db,
                              get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] gratitude router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: gratitude router init failed: {exc}', flush=True)

    try:
        init_books_router(get_db=_get_db, release_db=_release_db,
                          get_session_user=_get_session_user)
        print('[routers] books router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: books router init failed: {exc}', flush=True)

    try:
        init_accountability_router(get_db=_get_db, release_db=_release_db,
                                   get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] accountability router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: accountability router init failed: {exc}', flush=True)

    try:
        init_confession_router(get_session_user=_get_session_user)
        print('[routers] confession router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: confession router init failed: {exc}', flush=True)

    try:
        init_export_router(get_db=_get_db, release_db=_release_db,
                           get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] export router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: export router init failed: {exc}', flush=True)

    try:
        init_gospel_router(get_db=_get_db, release_db=_release_db,
                           get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] gospel router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: gospel router init failed: {exc}', flush=True)

    try:
        init_spiritual_formation_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
            root_dir=ROOT_DIR,
        )
        print('[routers] spiritual formation router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: spiritual formation router init failed: {exc}', flush=True)

    try:
        init_strongholds_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
            root_dir=ROOT_DIR,
        )
        print('[routers] strongholds router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: strongholds router init failed: {exc}', flush=True)

    try:
        init_stronghold_rag_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            root_dir=ROOT_DIR,
        )
        print('[routers] stronghold RAG router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: stronghold RAG router init failed: {exc}', flush=True)

    try:
        init_disciple_router(get_db=_get_db, release_db=_release_db,
                             get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] disciple router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: disciple router init failed: {exc}', flush=True)

    try:
        init_gift_calling_router(get_db=_get_db, release_db=_release_db,
                                 get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] gift_calling router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: gift_calling router init failed: {exc}', flush=True)

    try:
        init_care_router(get_db=_get_db, release_db=_release_db,
                         get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] care router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: care router init failed: {exc}', flush=True)

    try:
        init_suffering_router(get_db=_get_db, release_db=_release_db,
                              get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] suffering router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: suffering router init failed: {exc}', flush=True)

    try:
        init_dew_router(get_db=_get_db, release_db=_release_db)
        print('[routers] dew router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: dew router init failed: {exc}', flush=True)

    try:
        init_checkup_router(get_db=_get_db, release_db=_release_db,
                            get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] checkup router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: checkup router init failed: {exc}', flush=True)

    try:
        init_pilgrim_router(get_db=_get_db, release_db=_release_db,
                            get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] pilgrim router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: pilgrim router init failed: {exc}', flush=True)

    try:
        init_virtues_router(get_session_user=_get_session_user)
        print('[routers] virtues router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: virtues router init failed: {exc}', flush=True)

    try:
        init_discern_router(get_db=_get_db, release_db=_release_db,
                            get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] discern router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: discern router init failed: {exc}', flush=True)

    try:
        init_ordo_amoris_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] ordo_amoris router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: ordo_amoris router init failed: {exc}', flush=True)

    try:
        init_grace_identity_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] grace_identity router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: grace_identity router init failed: {exc}', flush=True)

    try:
        init_creed_catechism_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] creed_catechism router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: creed_catechism router init failed: {exc}', flush=True)

    try:
        init_rule_discernment_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] rule_discernment router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: rule_discernment router init failed: {exc}', flush=True)

    try:
        init_cross_lament_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] cross_lament router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: cross_lament router init failed: {exc}', flush=True)

    try:
        init_sacrament_calendar_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] sacrament_calendar router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: sacrament_calendar router init failed: {exc}', flush=True)

    try:
        init_fuel_router()
        print('[routers] fuel router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: fuel router init failed: {exc}', flush=True)

    try:
        init_agent_router(get_session_user=_get_session_user)
        print('[routers] agent router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: agent router init failed: {exc}', flush=True)

    try:
        init_church_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            sanitize_text=_sanitize_text,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] church router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: church router init failed: {exc}', flush=True)

    try:
        init_church_health_router(get_db=_get_db, release_db=_release_db,
                                  get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] church_health router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: church_health router init failed: {exc}', flush=True)

    try:
        init_theological_safety_router(get_db=_get_db, release_db=_release_db,
                                       get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] theological_safety router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: theological_safety router init failed: {exc}', flush=True)

    try:
        init_weekly_review_router(get_db=_get_db, release_db=_release_db,
                                  get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] weekly_review router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: weekly_review router init failed: {exc}', flush=True)

    try:
        init_semantic_search_router(get_db=_get_db, release_db=_release_db,
                                    get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] semantic_search router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: semantic_search router init failed: {exc}', flush=True)

    try:
        init_diagnosis_router(get_db=_get_db, release_db=_release_db,
                              get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] diagnosis router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: diagnosis router init failed: {exc}', flush=True)

    try:
        init_community_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
        )
        print('[routers] community router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: community router init failed: {exc}', flush=True)

    try:
        init_community_feed_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
            sanitize_text=_sanitize_text,
            to_shanghai_iso=_to_shanghai_iso,
        )
        print('[routers] community_feed router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: community_feed router init failed: {exc}', flush=True)

    try:
        from query_emotion_verses import get_embeddings as _get_emb
        init_feedback_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            get_embeddings=_get_emb,
            features_file=str(ROOT_DIR / 'emotion_features.json'),
            matches_file=str(ROOT_DIR / 'emotion_feature_matches.json'),
            cache_file=str(ROOT_DIR / 'emotion_feature_embedding_cache.json'),
        )
        print('[routers] feedback router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: feedback router init failed: {exc}', flush=True)

    try:
        if 'init_mvfe_stats_router' in dir():
            init_mvfe_stats_router(
                get_db=_get_db,
                release_db=_release_db,
                get_session_user=_get_session_user,
            )
            print('[routers] mvfe_stats router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mvfe_stats router init failed: {exc}', flush=True)

    try:
        if _ADMIN_ROUTERS_LOADED:
            _init_admin_router(
                get_db=_get_db,
                release_db=_release_db,
                get_session_user=_get_session_user,
                is_admin=_is_admin,
                invalidate_admin_cache=_invalidate_admin_cache,
                revoke_user_sessions=_revoke_user_sessions,
                sanitize_text=_sanitize_text,
                to_shanghai_iso=_to_shanghai_iso,
                hash_password=_hash_password,
            )
            print("[routers] admin routers initialized", flush=True)
    except Exception as exc:
        print(f"[routers] WARNING: admin routers init failed: {exc}", flush=True)

    # 门徒塑造独立异步 worker（由 DISCIPLE_WORKER_ENABLED 显式开启；serverless 勿开）
    try:
        from disciple_worker import start_background_worker
        if start_background_worker(_get_db, _release_db):
            print('[disciple_worker] background worker started', flush=True)
    except Exception as exc:
        print(f'[disciple_worker] WARNING: start failed: {exc}', flush=True)

    yield


# 速率限制器：见 core/ratelimit.py（按真实客户端 IP=X-Forwarded-For 计数 + 全局上限）
from core.ratelimit import limiter

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

# ── Domain routers (new modular structure) ────────────────────────────────────
from telemetry import setup_telemetry
from routers.stats import router as stats_router, init_stats_router
from routers.verse import router as verse_router, init_verse_router
from routers.film_studio import router as film_studio_router
from routers.journal import router as journal_router, init_journal_router
from routers.prayer import router as prayer_router, init_prayer_router
from routers.emotion_trajectory import router as emotion_trajectory_router, init_emotion_trajectory_router
from routers.milestones_health import router as milestones_health_router, init_milestones_health_router
from routers.daily_soul_question import router as daily_soul_question_router, init_daily_soul_question_router
from routers.user_profile import router as user_profile_router, init_user_profile_router
from routers.recycle_bin import router as recycle_bin_router, init_recycle_bin_router
from routers.reflection import router as reflection_router, init_reflection_router
from routers.dating_priority import router as dating_priority_router, init_dating_priority_router
from routers.personal_notes import router as personal_notes_router, init_personal_notes_router
from routers.evangelism import router as evangelism_router, init_evangelism_router
from routers.bible_reading import router as bible_reading_router, init_bible_reading_router
from routers.spiritual_partner import router as spiritual_partner_router, init_spiritual_partner_router
from routers.testimony import router as testimony_router, init_testimony_router
from routers.community import router as community_router, init_community_router
from routers.community_feed import router as community_feed_router, init_community_feed_router
from routers.feedback import router as feedback_router, init_feedback_router
from routers.geo import router as geo_router
from routers.bible_map import router as bible_map_router
from routers.characters import router as characters_router
from routers.bible_search import router as bible_search_router
from routers.call_minutes import router as call_minutes_router
from routers.realtime import router as realtime_router, init_realtime_router
from routers.voice import router as voice_router, init_voice_router
from routers.meetings import router as meetings_router, init_meetings_router
from routers.personal_store import router as personal_store_router, init_personal_store_router
from routers.idolatry import router as idolatry_router, init_idolatry_router
from routers.worldview import router as worldview_router, init_worldview_router
from routers.worldview_lenses import router as worldview_lenses_router, init_worldview_lenses_router
from routers.formation import router as formation_router
from routers.discernment import router as discernment_router
from routers.care import router as care_router, init_care_router
from routers.suffering import router as suffering_router, init_suffering_router
from routers.waiting import router as waiting_router, init_waiting_router
from routers.pastoral import router as pastoral_router, init_pastoral_router
from routers.examen import router as examen_router, init_examen_router
from routers.productization import router as productization_router, init_productization_router
from routers.analytics import router as analytics_router, init_analytics_router
from routers.platform_admin import router as platform_admin_router, init_platform_admin_router
from routers.billing import router as billing_router, init_billing_router
from routers.org_console import router as org_console_router, init_org_console_router
from routers.ai_tutor import router as ai_tutor_router, init_ai_tutor_router
from routers.spiritual_memory import router as spiritual_memory_router, init_spiritual_memory_router
from routers.formation_agent import router as formation_agent_router, init_formation_agent_router
from routers.timeline import router as timeline_router, init_timeline_router
from routers.doctrine import router as doctrine_router, init_doctrine_router
from routers.church_integration import router as church_integration_router, init_church_integration_router
from routers.discipleship import router as discipleship_router, init_discipleship_router
from routers.accountability_group import router as accountability_group_router, init_accountability_group_router
from routers.mentor import router as mentor_router, init_mentor_router
from routers.fasting import router as fasting_router, init_fasting_router
from routers.sabbath import router as sabbath_router, init_sabbath_router
from routers.fruit import router as fruit_router, init_fruit_router
from routers.temptation import router as temptation_router, init_temptation_router
from routers.presence import router as presence_router, init_presence_router
from routers.prayer_rule import router as prayer_rule_router, init_prayer_rule_router
from routers.intercession import router as intercession_router, init_intercession_router
from routers.lectio import router as lectio_router, init_lectio_router
from routers.psalm import router as psalm_router, init_psalm_router
from routers.mission_life import router as mission_life_router, init_mission_life_router
from routers.guardian import router as guardian_router, init_guardian_router
from routers.crisis import router as crisis_router, init_crisis_router
from routers.push import router as push_router, init_push_router
from routers.reading import router as reading_router, init_reading_router
from routers.memory import router as memory_router, init_memory_router
from routers.gratitude import router as gratitude_router, init_gratitude_router
from routers.books import router as books_router, init_books_router
from routers.accountability import router as accountability_router, init_accountability_router
from routers.confession import router as confession_router, init_confession_router
from routers.export import router as export_router, init_export_router
from routers.gospel import router as gospel_router, init_gospel_router
from routers.spiritual_formation import router as spiritual_formation_router, init_spiritual_formation_router
from routers.strongholds import router as strongholds_router, init_strongholds_router
from routers.stronghold_rag import router as stronghold_rag_router, init_stronghold_rag_router
from routers.disciple import router as disciple_router, init_disciple_router
from routers.gift_calling import router as gift_calling_router, init_gift_calling_router
from routers.batch1_4 import router as batch1_4_router, init_batch1_4_router
from routers.batch7_13 import router as batch7_13_router, init_batch7_13_router
from routers.formation_advanced import router as formation_advanced_router, init_formation_advanced_router
from routers.dew import router as dew_router, init_dew_router
from routers.checkup import router as checkup_router, init_checkup_router
from routers.pilgrim import router as pilgrim_router, init_pilgrim_router
from routers.virtues import router as virtues_router, init_virtues_router
from routers.discern import router as discern_router, init_discern_router
from routers.ordo_amoris import router as ordo_amoris_router, init_ordo_amoris_router
from routers.grace_identity import router as grace_identity_router, init_grace_identity_router
from routers.creed_catechism import router as creed_catechism_router, init_creed_catechism_router
from routers.rule_discernment import router as rule_discernment_router, init_rule_discernment_router
from routers.cross_lament import router as cross_lament_router, init_cross_lament_router
from routers.sacrament_calendar import router as sacrament_calendar_router, init_sacrament_calendar_router
from routers.fuel import router as fuel_router, init_fuel_router
from routers.agent import router as agent_router, init_agent_router
from routers.church import router as church_router, init_church_router
from routers.church_health import router as church_health_router, init_church_health_router
from routers.theological_safety import router as theological_safety_router, init_theological_safety_router
from routers.weekly_review import router as weekly_review_router, init_weekly_review_router
from routers.semantic_search import router as semantic_search_router, init_semantic_search_router
from routers.diagnosis import router as diagnosis_router, init_diagnosis_router
try:
    from routers.admin_common import init_admin_router as _init_admin_router
    from routers.admin_users import router as admin_users_router
    from routers.admin_content import router as admin_content_router
    from routers.admin_catalog import router as admin_catalog_router
    _ADMIN_ROUTERS_LOADED = True
except Exception as _admin_import_exc:
    _ADMIN_ROUTERS_LOADED = False
    admin_users_router = admin_content_router = admin_catalog_router = None
    print(f"[routers] WARNING: admin routers import failed: {_admin_import_exc}", flush=True)
try:
    from routers.mvfe_stats import router as mvfe_stats_router, init_mvfe_stats_router
except Exception as _e:
    mvfe_stats_router = None
    print(f'[routers] mvfe_stats import skipped: {_e}', flush=True)

app = FastAPI(title='Bible Emotion Sphere API', lifespan=lifespan)
# ── UI language propagation (mobile/web ?lang= or X-Lang header) ──
try:
    from lang_context import LanguageMiddleware as _LanguageMiddleware
    app.add_middleware(_LanguageMiddleware)
    print('[i18n] LanguageMiddleware registered', flush=True)
except Exception as _e_lang:
    print(f'[i18n] LanguageMiddleware unavailable: {_e_lang}', flush=True)
try:
    from lang_context import is_english, english_suffix, localize_system_prompt, apply_lang_messages
except Exception:
    def is_english():
        return False
    def english_suffix():
        return ''
    def localize_system_prompt(p):
        return p
    def apply_lang_messages(m):
        return m
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# 全局默认限速对所有路由生效（含未单独装饰的昂贵端点），防刷防 DoS/成本放大
app.add_middleware(SlowAPIMiddleware)

# 包含决策支撑系统路由
app.include_router(sfds_router)

# 包含 MVFE 路由
app.include_router(mvfe_router)

# 包含用户标签系统路由
app.include_router(user_tag_router)

# Domain routers
app.include_router(stats_router)
app.include_router(verse_router)
app.include_router(emotion_trajectory_router)
app.include_router(milestones_health_router)
app.include_router(daily_soul_question_router)
app.include_router(user_profile_router)
app.include_router(recycle_bin_router)
app.include_router(reflection_router)
app.include_router(dating_priority_router)
app.include_router(personal_notes_router)
app.include_router(evangelism_router)
app.include_router(bible_reading_router)
app.include_router(spiritual_partner_router)
app.include_router(film_studio_router)
app.include_router(journal_router)
app.include_router(prayer_router)
app.include_router(testimony_router)
app.include_router(community_router)
app.include_router(church_router)
app.include_router(theological_safety_router)
app.include_router(weekly_review_router)
app.include_router(semantic_search_router)
app.include_router(diagnosis_router)
app.include_router(community_feed_router)
app.include_router(feedback_router)
app.include_router(geo_router)
app.include_router(bible_map_router)
app.include_router(characters_router)
app.include_router(bible_search_router)
app.include_router(call_minutes_router)
app.include_router(realtime_router)
app.include_router(voice_router)
app.include_router(meetings_router)
app.include_router(personal_store_router)
app.include_router(idolatry_router)
app.include_router(worldview_router)
app.include_router(worldview_lenses_router)
app.include_router(formation_router)
app.include_router(discernment_router)
app.include_router(waiting_router)
app.include_router(pastoral_router)
app.include_router(examen_router)
app.include_router(productization_router)
app.include_router(analytics_router)
app.include_router(platform_admin_router)
app.include_router(billing_router)
app.include_router(org_console_router)
app.include_router(ai_tutor_router)
app.include_router(spiritual_memory_router)
app.include_router(formation_agent_router)
app.include_router(timeline_router)
app.include_router(doctrine_router)
app.include_router(church_integration_router)
app.include_router(church_health_router)
app.include_router(discipleship_router)
app.include_router(accountability_group_router)
app.include_router(mentor_router)
app.include_router(fasting_router)
app.include_router(sabbath_router)
app.include_router(fruit_router)
app.include_router(temptation_router)
app.include_router(presence_router)
app.include_router(prayer_rule_router)
app.include_router(intercession_router)
app.include_router(lectio_router)
app.include_router(psalm_router)
app.include_router(mission_life_router)
app.include_router(guardian_router)
app.include_router(crisis_router)
app.include_router(push_router)
app.include_router(reading_router)
app.include_router(memory_router)
app.include_router(gratitude_router)
app.include_router(books_router)
app.include_router(accountability_router)
app.include_router(confession_router)
app.include_router(export_router)
app.include_router(gospel_router)
app.include_router(spiritual_formation_router)
app.include_router(strongholds_router)
app.include_router(stronghold_rag_router)
app.include_router(disciple_router)
app.include_router(gift_calling_router)
app.include_router(batch1_4_router)
app.include_router(batch7_13_router)
app.include_router(formation_advanced_router)
app.include_router(care_router)
app.include_router(suffering_router)
app.include_router(dew_router)
app.include_router(checkup_router)
app.include_router(pilgrim_router)
app.include_router(virtues_router)
app.include_router(discern_router)
app.include_router(ordo_amoris_router)
app.include_router(grace_identity_router)
app.include_router(creed_catechism_router)
app.include_router(rule_discernment_router)
app.include_router(cross_lament_router)
app.include_router(sacrament_calendar_router)
app.include_router(fuel_router)
app.include_router(agent_router)
if mvfe_stats_router is not None:
    app.include_router(mvfe_stats_router)
if admin_users_router is not None:
    app.include_router(admin_users_router)
if admin_content_router is not None:
    app.include_router(admin_content_router)
if admin_catalog_router is not None:
    app.include_router(admin_catalog_router)

# 安全 CORS 配置（生产环境应限制具体域名）
ALLOWED_ORIGINS = settings.allowed_origins
if '*' in ALLOWED_ORIGINS:
    # 开发环境
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=False,  # '*' 源不可与凭证并用；本站用 Bearer Token 故无需 cookie 凭证
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
        "worker-src 'self' blob:; "
        "child-src 'self' blob:; "
        "frame-ancestors 'none'"
    )
    # HSTS（仅在 HTTPS 环境）
    if request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# 请求体大小硬上限：防超大 payload 撑爆内存（上传走 multipart，普通 JSON 远小于此）
MAX_BODY_BYTES = 25 * 1024 * 1024  # 25 MB


@app.middleware('http')
async def limit_body_size(request: Request, call_next):
    cl = request.headers.get('content-length')
    if cl:
        try:
            if int(cl) > MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content={'ok': False, 'detail': 'Request body too large.'})
        except ValueError:
            pass
    return await call_next(request)


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
    # 加载神经科学特征 (layer:feature_id 格式)
    for item in load_json_file(MATCHES_FILE):
        key = f"{item.get('layer')}:{item.get('feature_id')}"
        match_map[key] = item
    # 从 layout 加载所有特征，补全缺失的神经科学特征和生成特征
    for item in load_json_file(LAYOUT_FILE):
        key = item.get('feature_key')
        if not key:
            continue
        if key in match_map:
            continue  # 已存在，跳过
        layer = item.get('layer')
        if layer == 'generated':
            # 构造生成特征数据
            match_map[key] = {
                'feature_id': item.get('feature_id'),
                'layer': 'generated',
                'model_id': 'generated',
                'source_keyword': item.get('source_keyword', 'emotion'),
                'explanation': item.get('explanation', item.get('zh_label', '')),
                'exemplar_texts': [],
                'matches': {'cuv': [], 'esv': []},
                'zh_label': item.get('zh_label'),
                'short_en': item.get('short_en'),
                '_is_generated': True,
            }
        else:
            # 补全缺失的神经科学特征
            match_map[key] = {
                'feature_id': item.get('feature_id'),
                'layer': layer,
                'model_id': item.get('model_id', 'llama3.1-8b'),
                'source_keyword': item.get('source_keyword', ''),
                'explanation': item.get('explanation', item.get('zh_label', '')),
                'exemplar_texts': [],
                'matches': {'cuv': [], 'esv': []},
                'zh_label': item.get('zh_label'),
                'short_en': item.get('short_en'),
                '_is_fallback': True,  # 标记为降级数据
            }
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
    """Comprehensive health check — reports status of all critical subsystems.

    Response shape::

        {
          "ok": true,
          "status": "healthy",        // "healthy" | "degraded" | "unhealthy"
          "components": {
            "database": {"status": "ok",      "latency_ms": 2.1},
            "vector_index": {"status": "ok",   "feature_count": 1024},
            "embedding_service": {"status": "ok"},
            "mvfe_orchestrator": {"status": "ok"}
          },
          "version": "bible3dsphere/1.0"
        }
    """
    import time as _time
    components: dict = {}
    overall_ok = True

    # 1. Database connectivity
    conn = None
    try:
        _t0 = _time.perf_counter()
        conn = _get_db()
        with conn.cursor() as _cur:
            _cur.execute("SELECT 1")
        _lat = round((_time.perf_counter() - _t0) * 1000, 1)
        components["database"] = {"status": "ok", "latency_ms": _lat}
    except Exception as _e:
        components["database"] = {"status": "error", "detail": str(_e)[:120]}
        overall_ok = False
    finally:
        if conn is not None:
            _release_db(conn)

    # 2. Vector index (in-memory cache)
    try:
        from query_emotion_verses import _CACHE_FEATURES, _CACHE_FEATURE_EMBEDDINGS
        if _CACHE_FEATURES and _CACHE_FEATURE_EMBEDDINGS is not None:
            components["vector_index"] = {
                "status": "ok",
                "feature_count": len(_CACHE_FEATURES),
                "embedding_shape": list(_CACHE_FEATURE_EMBEDDINGS.shape),
            }
        else:
            components["vector_index"] = {"status": "cold", "detail": "cache not loaded yet"}
    except Exception as _e:
        components["vector_index"] = {"status": "error", "detail": str(_e)[:80]}

    # 3. Embedding service reachability (non-blocking check via cached state)
    try:
        import os as _os
        has_key = bool(_os.getenv("SILICONFLOW_API_KEY", ""))
        components["embedding_service"] = {
            "status": "ok" if has_key else "degraded",
            "provider": "SiliconFlow/BGE-M3",
            "key_configured": has_key,
        }
        if not has_key:
            overall_ok = False
    except Exception as _e:
        components["embedding_service"] = {"status": "error", "detail": str(_e)[:80]}

    # 4. MVFE orchestrator
    try:
        from mvfe.core.orchestrator import Orchestrator
        components["mvfe_orchestrator"] = {"status": "ok", "class": "Orchestrator"}
    except Exception as _e:
        components["mvfe_orchestrator"] = {"status": "error", "detail": str(_e)[:80]}
        overall_ok = False

    status = "healthy" if overall_ok else "degraded"
    degraded = [k for k, v in components.items() if v.get("status") not in ("ok", "cold")]
    if len(degraded) >= 2:
        status = "unhealthy"

    return {
        "ok": overall_ok,
        "status": status,
        "components": components,
        "version": "bible3dsphere/1.0",
    }


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
        f'您的属灵星球验证码：\n\n'
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
        await asyncio.to_thread(_send_email, email, '属灵星球 – 邮箱验证码', body)
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
    if user_record.get('is_banned'):
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip, details={'reason': 'banned'}, success=False)
        raise HTTPException(status_code=403, detail='账号已被停用，请联系管理员')
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

您正在重置属灵星球账户的密码。验证码：{code}

请在 10 分钟内输入此验证码完成密码重置。如非本人操作，请忽略此邮件。

属灵星球
"""

    has_email_service = bool(SENDGRID_API_KEY) or bool(RESEND_API_KEY) or (bool(SMTP_USER) and bool(SMTP_PASS))
    if not has_email_service:
        print(f'[auth][DEV] reset verification code for {email}: {code}', flush=True)
        return {'ok': True, 'dev_code': code}

    try:
        await asyncio.to_thread(_send_email, email, '属灵星球 – 密码重置验证码', body)
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
                data = row[0]
                user = data if isinstance(data, dict) else json.loads(data)
                with _SESSION_LOCK:
                    _SESSION_STORE[token] = user
                return user
        finally:
            _release_db(conn)
    except Exception as _e:
        print(f'[session] DB fallback failed: {_e}', flush=True)
        return None


_ADMIN_CACHE: dict[str, tuple[bool, float]] = {}
_ADMIN_CACHE_TTL = 300  # 5 minutes


def _invalidate_admin_cache(email: str) -> None:
    """Clear cached admin status for a user."""
    _ADMIN_CACHE.pop(email, None)


def _revoke_user_sessions(email: str) -> None:
    """Delete all tokens for a user from DB and memory store."""
    try:
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM user_tokens WHERE email = %s', (email,))
                conn.commit()
        finally:
            _release_db(conn)
    except Exception as _exc:
        print(f'[admin] revoke_user_sessions DB error: {_exc}', flush=True)
    with _SESSION_LOCK:
        to_del = [t for t, u in _SESSION_STORE.items() if u.get('email') == email]
        for t in to_del:
            del _SESSION_STORE[t]


def _is_admin(email: str) -> bool:
    """Check if a user has admin role (cached 5 min)."""
    if not email:
        return False
    if email == 'zpclord@sina.com':
        return True
    now = time.time()
    cached = _ADMIN_CACHE.get(email)
    if cached and (now - cached[1]) < _ADMIN_CACHE_TTL:
        return cached[0]
    conn = _get_db()
    try:
        result = False
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM users WHERE email=%s AND is_admin=TRUE "
                    "UNION ALL SELECT 1 FROM user_roles WHERE email=%s AND role='admin')",
                    (email, email),
                )
                result = bool(cur.fetchone()[0])
            except Exception:
                conn.rollback()
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


# ══════════════════════════════════════════════════════════════
# A1: 每日灵魂一问
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# A3: 倒退预警 + A7: 里程碑
# ══════════════════════════════════════════════════════════════

def _award_milestone_if_due(email: str, conn=None) -> list:
    """Check and award any newly-earned milestones. Returns list of new badge_keys."""
    owned_conn = conn is None
    if owned_conn:
        conn = _get_db()
    new_badges = []
    try:
        with conn.cursor() as cur:
            # Count consecutive devotion days
            cur.execute("SELECT journal_date FROM devotion_journals WHERE email=%s AND deleted_at IS NULL ORDER BY journal_date DESC LIMIT 30", (email,))
            devotion_dates = [r[0] for r in cur.fetchall()]
            streak = 0
            import datetime as _dt
            for i, d in enumerate(devotion_dates):
                expected = _dt.date.today() - _dt.timedelta(days=i)
                if d == expected:
                    streak += 1
                else:
                    break

            # Count prayer amens
            cur.execute("SELECT COUNT(*) FROM prayers WHERE email=%s AND deleted_at IS NULL", (email,))
            prayer_count = cur.fetchone()[0]

            # Count answered prayers
            cur.execute("SELECT COUNT(*) FROM prayers WHERE email=%s AND status='answered'", (email,))
            answered_count = cur.fetchone()[0]

            # Count soul answers
            cur.execute("SELECT COUNT(*) FROM daily_soul_answers WHERE email=%s AND answer != ''", (email,))
            soul_count = cur.fetchone()[0]

            # Get existing badges
            cur.execute("SELECT badge_key FROM milestone_events WHERE email=%s", (email,))
            earned = {r[0] for r in cur.fetchall()}

            _BADGE_CHECKS = [
                ('devotion_streak_7',   streak >= 7,       '🌿 旷野七日',    '连续7天灵修，你已走过旷野'),
                ('devotion_streak_30',  streak >= 30,       '🕯️ 月光守望',   '连续30天灵修，如月光常照'),
                ('prayer_wall_10',      prayer_count >= 10, '🙏 守望者',      '已提交10条代祷，成为他人的守望'),
                ('prayer_answered_3',   answered_count >= 3,'✝️ 信心见证者',  '3个祷告已蒙恩答应，你的信心日历有了见证'),
                ('soul_q_7',            soul_count >= 7,    '🔍 七日自省者',  '已回答7次灵魂一问，诚实面对自己'),
                ('soul_q_30',           soul_count >= 30,   '💎 月月省察',    '坚持30次灵魂省察，生命持续更新'),
            ]

            for badge_key, condition, badge_name, badge_desc in _BADGE_CHECKS:
                if condition and badge_key not in earned:
                    cur.execute('INSERT INTO milestone_events (email, badge_key) VALUES (%s,%s) ON CONFLICT DO NOTHING', (email, badge_key))
                    new_badges.append({'key': badge_key, 'name': badge_name, 'desc': badge_desc})

            if new_badges:
                conn.commit()
    except Exception as e:
        print(f'[milestone] error: {e}', flush=True)
    finally:
        if owned_conn:
            _release_db(conn)
    return new_badges


# ══════════════════════════════════════════════════════════════
# A4: 属灵伙伴配对
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# A10: 圣经通读轨迹
# ══════════════════════════════════════════════════════════════

@app.post('/api/user/checkin')
def post_checkin(payload: CheckinRequest, request: Request) -> dict:
    """Save checkin data and update user tags. Auth optional – tags skipped for guests."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    user_id = user.get('id', email) if user else ''
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
                    '''
                    INSERT INTO user_checkins (email, checkin_at, data, emotion_label, mood)
                    VALUES (%s, NOW(), %s, %s, %s)
                    ''',
                    (
                        email,
                        json.dumps(data, ensure_ascii=False),
                        data.get('emotionLabel', ''),
                        data.get('mood', ''),
                    )
                )
                conn.commit()
            print(f'[checkin] saved to db for {email}', flush=True)
        finally:
            _release_db(conn)

        # Record formation event from checkin data
        try:
            import asyncio, uuid as _uuid
            from formation_engine import get_formation_engine
            _DRIVER_TO_PATTERN = {
                'fear': 'fear', 'anxiety': 'fear', 'stress': 'fear',
                'pride': 'pride', 'comparison': 'pride',
                'shame': 'shame', 'guilt': 'shame',
                'desire': 'desire', 'impulse': 'desire',
                'growth': 'growth', 'gratitude': 'growth', 'spiritual': 'spiritual',
                'relational': 'relational', 'relationship': 'relational',
            }
            driver_key = (payload.driverType or '').lower()
            pattern_cats = []
            for k, v in _DRIVER_TO_PATTERN.items():
                if k in driver_key:
                    if v not in pattern_cats:
                        pattern_cats.append(v)
            if not pattern_cats:
                pattern_cats = ['growth']
            mood_intensity = {'high': 8.0, 'medium': 5.0, 'low': 3.0}.get(
                (payload.mood or '').lower(), 5.0
            )
            formation_eng = get_formation_engine()
            session_id = str(_uuid.uuid4())
            insight = formation_eng.analyze_sync(
                user_id=str(user_id),
                pattern_categories=pattern_cats,
                loop_broken=bool(payload.gratitude),
                decision_category='checkin',
                session_id=session_id,
                emotional_intensity=mood_intensity,
                reflection_active=bool(payload.prayerRequest or payload.gratitude),
            )
            dim_deltas = {
                dim: sc.delta
                for dim, sc in insight.current_snapshot.dimensions.items()
            }
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(formation_eng.record_formation_event(
                    user_id=str(user_id),
                    session_id=session_id,
                    pattern_categories=pattern_cats,
                    loop_broken=bool(payload.gratitude),
                    dimension_deltas=dim_deltas,
                    decision_category='checkin',
                ))
            else:
                loop.run_until_complete(formation_eng.record_formation_event(
                    user_id=str(user_id),
                    session_id=session_id,
                    pattern_categories=pattern_cats,
                    loop_broken=bool(payload.gratitude),
                    dimension_deltas=dim_deltas,
                    decision_category='checkin',
                ))
            print(f'[checkin] formation event queued for {user_id}', flush=True)
        except Exception as _fe:
            print(f'[checkin] formation record skipped: {_fe}', flush=True)
    else:
        print('[checkin] guest checkin, tags not persisted', flush=True)

    return {'ok': True, 'tags_extracted': len(tags)}


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

    # Localize the system prompt so the assistant replies in English when asked.
    system_content = localize_system_prompt(system_content)

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

    gemini_api_key = settings.gemini_api_key
    siliconflow_api_key = settings.siliconflow_api_key

    # Provider list: Gemini primary, SiliconFlow fallback
    _chat_providers = [
        {
            'name': 'Gemini',
            'url': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
            'model': 'gemini-2.0-flash',
            'headers': {'Authorization': f'Bearer {gemini_api_key}', 'Content-Type': 'application/json'},
        },
    ]
    deepseek_api_key = getattr(settings, 'deepseek_api_key', '')
    if deepseek_api_key:
        _chat_providers.append({
            'name': 'DeepSeek',
            'url': 'https://api.deepseek.com/chat/completions',
            'model': 'deepseek-chat',
            'headers': {'Authorization': f'Bearer {deepseek_api_key}', 'Content-Type': 'application/json'},
        })
    if siliconflow_api_key:
        _chat_providers.append({
            'name': 'SiliconFlow',
            'url': 'https://api.siliconflow.cn/v1/chat/completions',
            'model': 'deepseek-ai/DeepSeek-V3',
            'headers': {'Authorization': f'Bearer {siliconflow_api_key}', 'Content-Type': 'application/json'},
        })

    assistant_chunks: list[str] = []

    async def generate():
        try:
            async with _httpx.AsyncClient(timeout=60) as client:
                streamed_ok = False
                for provider in _chat_providers:
                    print(f'[chat] trying provider={provider["name"]} model={provider["model"]}', flush=True)
                    req_body = {
                        'model': provider['model'],
                        'messages': [{'role': 'system', 'content': system_content}] + messages_for_api,
                        'temperature': 0.75,
                        'max_tokens': 600,
                        'stream': True,
                    }
                    try:
                        async with client.stream('POST', provider['url'], json=req_body, headers=provider['headers']) as resp:
                            if resp.status_code >= 400:
                                print(f'[chat] {provider["name"]} HTTP {resp.status_code}, trying fallback', flush=True)
                            else:
                                streamed_ok = True
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
                        print(f'[chat] {provider["name"]} error: {exc}, trying fallback', flush=True)
                    if streamed_ok:
                        break
                if not streamed_ok:
                    yield f'data: {json.dumps({"delta": "AI服务暂时不可用，请稍后重试。"}, ensure_ascii=False)}\n\n'
        except Exception as exc:
            print(f'[chat] generate error: {exc}', flush=True)
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






def _ai_status_payload() -> dict:
    """AI 服务降级状态（配额/余额耗尽时前端给出维护提示）。"""
    try:
        from query_emotion_verses import get_ai_status
        return get_ai_status()
    except Exception:
        return {"degraded": False, "quota_exhausted": False, "balance_insufficient": False}




@app.get('/api/ai-status')
def get_ai_status_endpoint(response: Response) -> dict:
    response.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=300'
    return _ai_status_payload()


def _translate_cached(text: str, target: str) -> str:
    """翻译单条文本，命中/写入 translations_cache。失败返回 ''。"""
    import hashlib
    text = str(text or '').strip()
    if target not in ('en', 'zh'):
        target = 'en'
    if not text:
        return ''
    if len(text) > 4000:
        text = text[:4000]
    h = hashlib.sha1(f'{text}|{target}'.encode('utf-8')).hexdigest()
    if DATABASE_URL:
        conn = None
        try:
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute('SELECT translated FROM translations_cache WHERE hash=%s', (h,))
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)
    if target == 'en':
        sys_prompt = ('You are a translator for a Chinese Christian app. Translate the user text to '
                      'natural, reverent English using standard English Bible proper nouns. '
                      'Output ONLY the translation.')
    else:
        sys_prompt = ('你是中文基督教应用的翻译。把用户文本翻成自然、敬虔的简体中文，'
                      '圣经专名用通用中文译名。只输出译文。')
    try:
        out = call_chat(sys_prompt, text).strip().strip('"').strip()
    except Exception:
        out = ''
    if not out:
        return ''
    if DATABASE_URL:
        conn = None
        try:
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO translations_cache(hash,target,translated) VALUES(%s,%s,%s) '
                    'ON CONFLICT (hash) DO NOTHING', (h, target, out))
                conn.commit()
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)
    return out




@app.post('/api/translate-batch')
@limiter.limit('60/minute')
def translate_batch(payload: dict, request: Request, response: Response) -> dict:
    """批量按需翻译（EN 模式自动翻译列表）。
    { texts:[...], target|target_lang } → { ok, translations:[...] }
    （与输入等长，失败项回退原文）。

    性能优化：把原来"逐条串行(每条一次 DB 往返 + 一次 LLM 往返)"改为
      ① 一次性批量查缓存（单次 SQL，命中即返回）
      ② 仅对未命中文本去重后并发机翻（线程池，I/O 并行）
      ③ 一次性批量写回缓存（单条 INSERT）
    整屏翻译延迟从"逐条累加(~2s+)"降到约"单次 LLM 往返(~0.7s)"。"""
    import hashlib
    from concurrent.futures import ThreadPoolExecutor

    p = payload or {}
    texts = p.get('texts')
    if not isinstance(texts, list):
        texts = []
    target = str(p.get('target') or p.get('target_lang') or 'en').lower()
    if target not in ('en', 'zh'):
        target = 'en'
    texts = [str(t or '')[:2000] for t in texts][:100]  # 限长，防成本/内存放大
    response.headers['Cache-Control'] = 'private, max-age=86400'

    stripped = [t.strip() for t in texts]

    def _h(src: str) -> str:
        return hashlib.sha1(f'{src}|{target}'.encode('utf-8')).hexdigest()

    hashes = [(_h(s) if s else None) for s in stripped]
    result_map: dict = {}  # hash -> translated

    # ① 一次性批量查缓存
    uniq_hashes = list({h for h in hashes if h})
    if DATABASE_URL and uniq_hashes:
        conn = None
        try:
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT hash, translated FROM translations_cache WHERE hash IN %s',
                    (tuple(uniq_hashes),))
                for hh, tr in cur.fetchall():
                    result_map[hh] = tr
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)

    if target == 'en':
        sys_prompt = ('You are a translator for a Chinese Christian app. Translate the user text to '
                      'natural, reverent English using standard English Bible proper nouns. '
                      'Output ONLY the translation.')
    else:
        sys_prompt = ('你是中文基督教应用的翻译。把用户文本翻成自然、敬虔的简体中文，'
                      '圣经专名用通用中文译名。只输出译文。')

    # ② 未命中文本去重（dict 天然去重，相同文本只翻一次）后并发机翻
    misses: dict = {}
    for s, h in zip(stripped, hashes):
        if h and h not in result_map and h not in misses:
            misses[h] = s

    def _one(item):
        hh, src = item
        try:
            out_txt = call_chat(sys_prompt, src).strip().strip('"').strip()
        except Exception:
            out_txt = ''
        return hh, out_txt

    if misses:
        workers = min(8, len(misses))
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                for hh, out_txt in ex.map(_one, list(misses.items())):
                    if out_txt:
                        result_map[hh] = out_txt
        except Exception:
            pass

    # ③ 一次性批量写回缓存
    new_rows = [(h, target, result_map[h]) for h in misses if result_map.get(h)]
    if DATABASE_URL and new_rows:
        conn = None
        try:
            from psycopg2.extras import execute_values
            conn = _get_db()
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    'INSERT INTO translations_cache(hash,target,translated) VALUES %s '
                    'ON CONFLICT (hash) DO NOTHING',
                    new_rows)
                conn.commit()
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)

    # ④ 按原顺序产出，空串/失败回退原文
    out = []
    for orig, s, h in zip(texts, stripped, hashes):
        out.append(orig if not s else (result_map.get(h) or orig))
    return {'ok': True, 'translations': out, 'target_lang': target}


@app.get('/api/home-bootstrap')
def get_home_bootstrap(request: Request, response: Response) -> dict:
    """首屏聚合：一次请求返回 layout + ai_status + history，
    把多次跨境往返（每次约 1.3s）压成一次，显著加快首屏数据加载。
    每段独立容错，任一失败不影响其余。"""
    out: dict = {}
    try:
        layout = load_json_file(LAYOUT_FILE)
        out['layout'] = {'items': layout, 'count': len(layout)}
    except Exception:
        out['layout'] = {'items': [], 'count': 0}
    try:
        out['ai_status'] = _ai_status_payload()
    except Exception:
        out['ai_status'] = {"degraded": False}
    try:
        out['history'] = {'items': load_history()}
    except Exception:
        out['history'] = {'items': []}
    # 含会话相关历史 → 仅浏览器私有缓存，短 TTL
    response.headers['Cache-Control'] = 'private, max-age=30'
    return out








# ── debug flag: set DEBUG_API=1 in HF Space secrets to expose tracebacks ──
_DEBUG = settings.debug_api


def _handle_exc(exc: Exception) -> None:
    """Always print full traceback to stdout (visible in HF Logs)."""
    print('=' * 72, flush=True)
    print('API ERROR:', type(exc).__name__, str(exc), flush=True)
    traceback.print_exc()
    print('=' * 72, flush=True)






class VersePrayerRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=1000)






class MeditationQuestionsRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=500)






_startup_checked = False


def _startup_check() -> None:
    """Print key file sizes and paths to HF Logs on first query."""
    global _startup_checked
    if _startup_checked:
        return
    _startup_checked = True
    print('── Startup check ──', flush=True)
    print(f'ROOT_DIR : {ROOT_DIR}', flush=True)
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




class FaithQARequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)




@app.get('/')
def serve_root():
    """API root — frontend is hosted independently at holiness.uk."""
    return JSONResponse({'service': 'biblesphere-api', 'status': 'ok', 'frontend': 'https://holiness.uk', 'docs': '/docs'})


# ── Google Cloud Text-to-Speech Endpoint ─────────────────────────────
class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000, description="要合成的文本")
    language_code: str = Field(default='cmn-CN', description="语言代码，如 cmn-CN, en-US")
    voice_name: str = Field(default='cmn-CN-Wavenet-A', description="指定语音名称")


# 可选：使用环境变量 GOOGLE_APPLICATION_CREDENTIALS 或 GOOGLE_API_KEY
GOOGLE_TTS_API_KEY = settings.google_tts_api_key




# ── Dating Priority (交友原则排序) ──────────────────────────────

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


class FormationToHabitsRequest(BaseModel):
    """从人格塑造计划批量创建习惯的请求"""
    user_id: str = Field(min_length=1)
    plan_items: List[str] = Field(min_length=1, max_length=10)
    plan_type: str = Field(default='short', pattern='^(short|mid)$')


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
        user = _get_session_user(request)
        if user:
            conn = None
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
            except Exception as log_exc:
                print(f'[behavior_regulate] Log error: {log_exc}', flush=True)
            finally:
                if conn is not None:
                    _release_db(conn)
        
        return result
    except Exception as exc:
        print(f'[behavior_regulate] Failed: {exc}', flush=True)
        tier = "Red" if payload.energy_level <= 2 else ("Yellow" if payload.energy_level <= 3 else "Green")
        return {
            "degraded": True,
            "selected_tier": tier,
            "min_executable_action": f"尝试{payload.task}的最小版本" if tier == "Red" else f"开始{payload.task}",
            "emotional_compensation": "系统智能降级，保持连续性",
            "continuity_advice": "任何微小启动都算成功",
            "spiritual_alignment": {
                "aligned": True,
                "alignment_score": 50,
                "assessment": "系统降级运行，属灵对齐评估暂不可用",
                "scripture_reference": "箴3:5-6",
                "principle": "你要专心仰赖耶和华，不可倚靠自己的聪明",
                "misalignment_areas": [],
                "alignment_actions": ["稍后重试", "检查后端服务日志"],
                "category": "系统降级"
            }
        }


@app.get('/api/behavior/history')
def get_behavior_history(user_id: str = None, limit: int = 30, request: Request = None):
    """获取用户的行为调节历史"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    target_user_id = user_id or str(user['id'])
    
    # 只能查询自己的数据
    if str(target_user_id) != str(user['id']):
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
                'spiritual_alignment': _parse_json_safe(r[10]),
                'source': 'behavior'
            } for r in rows]

            # Also pull habit execution logs and merge
            try:
                cur.execute(
                    '''SELECT hel.id, hsm.habit_name, hel.energy_level_at_execution,
                              hel.selected_tier, hel.was_completed, hel.completion_percentage,
                              hel.mood_before, hel.mood_after, hel.tokens_earned, hel.executed_at
                       FROM habit_execution_logs hel
                       LEFT JOIN habit_state_machines hsm ON hsm.id::text = hel.habit_id
                       WHERE hel.user_id = %s
                       ORDER BY hel.executed_at DESC
                       LIMIT %s''',
                    (target_user_id, limit)
                )
                habit_rows = cur.fetchall()
                for hr in habit_rows:
                    items.append({
                        'id': 'h_' + str(hr[0]),
                        'task': hr[1] or '习惯执行',
                        'energy_level': hr[2],
                        'motivation': None,
                        'tier_executed': hr[3],
                        'min_executable_action': None,
                        'was_completed': hr[4],
                        'completion_percentage': hr[5],
                        'executed_at': hr[9].isoformat() if hr[9] else None,
                        'system_energy_state': None,
                        'spiritual_alignment': None,
                        'mood_before': hr[6],
                        'mood_after': hr[7],
                        'tokens_earned': hr[8],
                        'source': 'habit'
                    })
            except Exception as habit_exc:
                print(f'[behavior_history] habit log merge failed: {habit_exc}', flush=True)

            # Sort merged list by executed_at descending
            items.sort(key=lambda x: x['executed_at'] or '', reverse=True)
            items = items[:limit]

        return {'items': items, 'count': len(items)}
    finally:
        _release_db(conn)


@app.get('/api/behavior/stats')
def get_behavior_stats(user_id: str = None, request: Request = None):
    """获取用户的行为调节统计"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    target_user_id = user_id or str(user['id'])
    
    if str(target_user_id) != str(user['id']):
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

            # 计算Red电路占比（反映疲劳趋势）
            red_count = tier_distribution.get('Red', 0)
            red_tier_ratio = round((red_count / total_regulations * 100), 1) if total_regulations > 0 else 0

            # 最近30天能量趋势（判断疲劳累积）
            cur.execute(
                '''SELECT AVG(energy_level) as avg_energy_30d,
                       COUNT(CASE WHEN energy_level <= 2 THEN 1 END) as low_energy_count
                   FROM sfds_behavior_history 
                   WHERE user_id = %s AND executed_at > NOW() - INTERVAL '30 days' ''',
                (target_user_id,)
            )
            trend_row = cur.fetchone()
            avg_energy_30d = round(trend_row[0] or 3, 1) if trend_row else 3
            low_energy_count_30d = trend_row[1] or 0 if trend_row else 0

            # 最近习惯执行统计（关联sfds_formation_metrics中的数据）
            cur.execute(
                '''SELECT COUNT(*), AVG(energy_level_at_execution)
                   FROM habit_execution_logs 
                   WHERE user_id = %s AND executed_at > NOW() - INTERVAL '7 days' ''',
                (target_user_id,)
            )
            habit_row = cur.fetchone()
            recent_habit_executions = habit_row[0] or 0
            avg_habit_energy = round(habit_row[1] or 3, 1) if habit_row else 3

        return {
            'total_regulations': total_regulations,
            'completed_regulations': completed_regulations,
            'completion_rate': round((completed_regulations / total_regulations * 100), 1) if total_regulations > 0 else 0,
            'avg_completion_percentage': avg_completion_percentage,
            'avg_energy_level': avg_energy_level,
            'tier_distribution': tier_distribution,
            'last_7_days_regulations': last_7_days,
            # 新增决策相关字段
            'red_tier_ratio': red_tier_ratio,
            'fatigue_trend': 'high' if red_tier_ratio > 30 or avg_energy_30d < 2.5 else 'moderate' if red_tier_ratio > 15 else 'normal',
            'avg_energy_30d': avg_energy_30d,
            'low_energy_episodes_30d': low_energy_count_30d,
            'recent_habit_executions_7d': recent_habit_executions,
            'avg_habit_energy_7d': avg_habit_energy,
            'behavior_consistency_score': round((last_7_days / 7) * 10, 1)  # 每日平均执行次数 × 10
        }
    finally:
        _release_db(conn)


# ── 反思问卷 API ─────────────────────────────────────────────

# ── 习惯养成状态机 API ───────────────────────────────────────

@app.post('/api/habits/create')
def create_habit_endpoint(payload: HabitCreateRequest, request: Request):
    """
    创建习惯状态机 - 三层动态电路保护
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    try:
        from backend.habit_behavior_engine import create_habit as _create_habit_fn
        result = _create_habit_fn(payload.habit_name, payload.anchor, payload.energy_level)
        
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
        import traceback
        print(f'[habits_create] Failed: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get('/api/habits')
def list_habits(request: Request):
    """获取用户的习惯列表"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
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
                    'green': r[7] if isinstance(r[7], dict) else {},
                    'yellow': r[8] if isinstance(r[8], dict) else {},
                    'red': r[9] if isinstance(r[9], dict) else {}
                }
            } for r in rows]
            
            return {'items': items, 'total': len(items)}
    except Exception as exc:
        import traceback
        print(f'[list_habits] ERROR user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        _release_db(conn)


@app.post('/api/habits/{habit_id}/execute')
def execute_habit(habit_id: str, payload: HabitExecuteRequest, request: Request):
    """
    执行习惯状态机 - 根据当前能量动态选择层级
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
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
                    'green': row[2] if isinstance(row[2], dict) else {},
                    'yellow': row[3] if isinstance(row[3], dict) else {},
                    'red': row[4] if isinstance(row[4], dict) else {}
                }
            }
        
        # 执行状态机
        from backend.habit_behavior_engine import habit_fsm
        execution = habit_fsm.execute_habit(habit_config, payload.energy_level)
        
        return execution.to_dict()
        
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        print(f'[execute_habit] ERROR habit_id={habit_id} user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        _release_db(conn)


@app.post('/api/habits/{habit_id}/log')
def log_habit_execution(habit_id: str, payload: HabitLogRequest, request: Request):
    """
    记录习惯执行结果，更新代币和连胜
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
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


class HabitNoteRequest(BaseModel):
    note: str = Field(default='', max_length=2000)


@app.post('/api/habits/{habit_id}/note')
def save_habit_note(habit_id: str, payload: HabitNoteRequest, request: Request):
    """Persist today's per-habit note WITHOUT counting a habit execution."""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    note = (payload.note or '')[:2000]
    today = __import__('datetime').date.today()
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO habit_daily_notes (user_id, habit_id, note_date, note, updated_at)
                   VALUES (%s, %s, %s, %s, NOW())
                   ON CONFLICT (user_id, habit_id, note_date)
                   DO UPDATE SET note = EXCLUDED.note, updated_at = NOW()""",
                (user_id, habit_id, today, note),
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


def _catmull_rom_chain(pts, samples_per_seg: int = 14):
    """Smooth curve through ``pts`` ([[lng,lat],...]) via Catmull-Rom — gives a
    natural sailing arc instead of a straight line. Endpoints duplicated."""
    if len(pts) < 2:
        return list(pts)
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s_i in range(samples_per_seg):
            t = s_i / samples_per_seg
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append([round(x, 5), round(y, 5)])
    out.append([round(pts[-1][0], 5), round(pts[-1][1], 5)])
    return out


def _sea_route(clean):
    """Realistic sea route along shipping lanes (searoute if installed),
    otherwise a smooth Catmull-Rom sailing arc through the ports. Never a
    straight line."""
    # Prefer real maritime routing if the optional `searoute` package is present.
    try:
        import searoute as _sr  # optional; add `searoute` to requirements to enable
        full = []
        for i in range(len(clean) - 1):
            o = clean[i]
            d = clean[i + 1]
            route = _sr.searoute(o, d)
            coords = route['geometry']['coordinates']
            if i > 0 and coords:
                coords = coords[1:]
            full.extend([[round(float(c[0]), 5), round(float(c[1]), 5)] for c in coords])
        if len(full) >= 2:
            return full
    except Exception as exc:
        print(f'[route] searoute unavailable, using sailing arc: {exc}', flush=True)
    return _catmull_rom_chain(clean)


class RouteRequest(BaseModel):
    coordinates: list = Field(default_factory=list)  # [[lng,lat], ...] in order
    profile: str = Field(default='foot-walking', max_length=24)


@app.post('/api/route')
def plan_route(payload: RouteRequest):
    """Walking-route proxy (OpenRouteService) with DB cache.

    Returns {ok, geometry:[[lng,lat],...]} for land journeys. On any failure
    (no API key, sea legs ORS can't route, distance limits, timeout) returns
    {ok: false} so clients fall back to a straight line.
    """
    coords = payload.coordinates or []
    # Validate / sanitise: 2..50 numeric [lng,lat] pairs.
    clean = []
    for c in coords[:50]:
        try:
            lng = float(c[0]); lat = float(c[1])
        except Exception:
            continue
        if -180 <= lng <= 180 and -90 <= lat <= 90:
            clean.append([round(lng, 5), round(lat, 5)])
    if len(clean) < 2:
        return {'ok': False, 'reason': 'need>=2 coords'}
    profile = payload.profile if payload.profile in (
        'foot-walking', 'foot-hiking', 'driving-car', 'sea') else 'foot-walking'

    import hashlib
    key = hashlib.sha1(
        (profile + '|' + ';'.join(f'{a},{b}' for a, b in clean)).encode()
    ).hexdigest()

    # 1) cache lookup
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute('SELECT geometry FROM route_cache WHERE cache_key=%s', (key,))
                row = cur.fetchone()
                if row and row[0]:
                    geom = row[0] if isinstance(row[0], list) else json.loads(row[0])
                    return {'ok': True, 'geometry': geom, 'cached': True}
            except Exception:
                conn.rollback()
    finally:
        _release_db(conn)

    # 2) sea legs → maritime/sailing route (no API key needed)
    if profile == 'sea':
        geom = _sea_route(clean)
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        'INSERT INTO route_cache (cache_key, geometry) VALUES (%s, %s) '
                        'ON CONFLICT (cache_key) DO NOTHING',
                        (key, json.dumps(geom)),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
        finally:
            _release_db(conn)
        return {'ok': True, 'geometry': geom}

    # 3) call OpenRouteService
    ors_key = os.environ.get('ORS_API_KEY', '') or getattr(settings, 'ors_api_key', '') or ''
    if not ors_key or ors_key.startswith('your_'):
        return {'ok': False, 'reason': 'no_key'}
    try:
        url = f'https://api.openrouteservice.org/v2/directions/{profile}/geojson'
        with httpx.Client(timeout=20) as client:
            resp = client.post(url, headers={
                'Authorization': ors_key,
                'Content-Type': 'application/json',
            }, json={'coordinates': clean})
        if resp.status_code >= 400:
            return {'ok': False, 'reason': f'ors {resp.status_code}'}
        data = resp.json()
        geom = data['features'][0]['geometry']['coordinates']
        geom = [[round(float(p[0]), 5), round(float(p[1]), 5)] for p in geom]
    except Exception as exc:
        print(f'[route] ORS failed: {exc}', flush=True)
        return {'ok': False, 'reason': 'ors_error'}

    # 3) store in cache (best-effort)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    'INSERT INTO route_cache (cache_key, geometry) VALUES (%s, %s) '
                    'ON CONFLICT (cache_key) DO NOTHING',
                    (key, json.dumps(geom)),
                )
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        _release_db(conn)

    return {'ok': True, 'geometry': geom}


@app.get('/api/habits/today')
def habits_today(request: Request):
    """Per-habit today state: done (from execution logs) + note (from daily notes)."""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    today = __import__('datetime').date.today()
    conn = _get_db()
    try:
        merged: dict = {}
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """SELECT habit_id, BOOL_OR(was_completed)
                       FROM habit_execution_logs
                       WHERE user_id = %s AND executed_at::date = %s
                       GROUP BY habit_id""",
                    (user_id, today),
                )
                for r in cur.fetchall():
                    merged.setdefault(str(r[0]), {})['done'] = bool(r[1])
            except Exception:
                conn.rollback()
            try:
                cur.execute(
                    "SELECT habit_id, note FROM habit_daily_notes WHERE user_id = %s AND note_date = %s",
                    (user_id, today),
                )
                for r in cur.fetchall():
                    merged.setdefault(str(r[0]), {})['note'] = r[1] or ''
            except Exception:
                conn.rollback()
        items = [
            {'habit_id': k, 'done': v.get('done', False), 'note': v.get('note', '')}
            for k, v in merged.items()
        ]
        return {'items': items}
    finally:
        _release_db(conn)


@app.get('/api/habits/dashboard')
def habits_dashboard(request: Request):
    """习惯系统仪表盘"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Try view first, fall back to direct query if view doesn't exist
            try:
                cur.execute(
                    '''SELECT active_habits, today_executions, max_current_streak,
                              token_balance, last_habit_name, circuit_breaker_count
                       FROM user_habit_dashboard 
                       WHERE user_id = %s''',
                    (user_id,)
                )
                row = cur.fetchone()
            except Exception as view_exc:
                print(f'[habits_dashboard] view query failed, using direct query: {view_exc}', flush=True)
                conn.rollback()
                cur.execute(
                    '''SELECT
                           COUNT(DISTINCT id) FILTER (WHERE is_active) AS active_habits,
                           0 AS today_executions,
                           COALESCE(MAX(current_streak_days), 0) AS max_current_streak,
                           0 AS token_balance,
                           NULL AS last_habit_name,
                           0 AS circuit_breaker_count
                       FROM habit_state_machines
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
    except Exception as exc:
        import traceback
        print(f'[habits_dashboard] ERROR user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        _release_db(conn)


@app.post('/api/habits/create-from-formation')
def create_habits_from_formation(payload: FormationToHabitsRequest, request: Request):
    """
    从人格塑造计划批量创建习惯
    将反思问卷生成的灵修计划自动同步为习惯状态机
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = str(user['id'])
    
    # 验证用户只能为自己创建习惯
    if user_id != payload.user_id:
        raise HTTPException(status_code=403, detail='只能为自己的账户创建习惯')
    
    created_count = 0
    created_habits = []
    
    try:
        from backend.habit_behavior_engine import create_habit as _create_habit_fn
        
        conn = _get_db()
        try:
            for item in payload.plan_items:
                # 生成习惯名称（从计划文本中提取关键词）
                habit_name = item[:50] if len(item) <= 50 else item[:47] + '...'
                
                # 根据计划类型设置不同的默认能量等级
                default_energy = 3 if payload.plan_type == 'short' else 4
                
                # 调用引擎创建习惯配置
                result = _create_habit_fn(habit_name, '', default_energy)
                
                # 保存到数据库
                with conn.cursor() as cur:
                    fsm_config = result.get('habit_config', {})
                    cur.execute(
                        '''INSERT INTO habit_state_machines 
                           (user_id, habit_name, deterministic_anchor, 
                            tier_green_config, tier_yellow_config, tier_red_config,
                            token_green_yield, token_yellow_yield, token_red_yield,
                            source_type, source_ref)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING id''',
                        (
                            user_id, 
                            habit_name, 
                            result.get('deterministic_anchor', ''),
                            json.dumps(fsm_config.get('Green', {})),
                            json.dumps(fsm_config.get('Yellow', {})),
                            json.dumps(fsm_config.get('Red', {})),
                            result.get('token_yield', 5),
                            max(3, result.get('token_yield', 5) - 1),
                            1,  # Red tier minimum yield
                            'formation_plan',  # 标记来源
                            payload.plan_type  # short or mid
                        )
                    )
                    row = cur.fetchone()
                    created_id = str(row[0])
                    created_count += 1
                    created_habits.append({
                        'id': created_id,
                        'name': habit_name,
                        'tier': result.get('selected_tier', 'Yellow')
                    })
            
            conn.commit()
            
        finally:
            _release_db(conn)
        
        return {
            'ok': True,
            'created_count': created_count,
            'habits': created_habits,
            'plan_type': payload.plan_type,
            'message': f'成功创建 {created_count} 个来自人格塑造计划的习惯'
        }
        
    except Exception as exc:
        import traceback
        print(f'[create_habits_from_formation] ERROR user_id={user_id}: {exc}\n{traceback.format_exc()}', flush=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# 千人千面每日灵修 — Personalized Daily Devotion
# ─────────────────────────────────────────────────────────────────────────────
import datetime as _dt

# In-memory daily devotion cache: {email+date → result}
_devotion_cache: dict = {}

_DIM_THEMES = {
    'humility': {
        'label': '谦卑',
        'verse': '腓立比书2:3',
        'text': '凡事不可结党，不可贪图虚浮的荣耀；只要存心谦卑，各人看别人比自己强。',
        'theme': '谦卑服事',
    },
    'fear_tendency': {
        'label': '信靠超越恐惧',
        'verse': '以赛亚书41:10',
        'text': '你不要害怕，因为我与你同在；你不要惊惶，因为我是你的神。我必坚固你，我必帮助你，我必用我公义的右手扶持你。',
        'theme': '信靠代替恐惧',
    },
    'pride_tendency': {
        'label': '柔和谦卑',
        'verse': '雅各书4:6',
        'text': '「神阻挡骄傲的人，赐恩给谦卑的人。」',
        'theme': '降服胜过骄傲',
    },
    'emotional_stability': {
        'label': '心灵平静',
        'verse': '约翰福音14:27',
        'text': '我留下平安给你们，我将我的平安赐给你们。我所赐的不像世人所赐的。你们心里不要忧愁，也不要胆怯。',
        'theme': '神赐平安',
    },
    'truth_alignment': {
        'label': '行在真道中',
        'verse': '约翰福音8:32',
        'text': '你们必晓得真理，真理必叫你们得以自由。',
        'theme': '活在真理里',
    },
    'relational_health': {
        'label': '爱的相交',
        'verse': '约翰一书4:7',
        'text': '亲爱的弟兄啊，我们应当彼此相爱，因为爱是从神来的。凡有爱心的，都是由神而生，并且认识神。',
        'theme': '彼此相爱',
    },
    'resilience': {
        'label': '在苦难中得胜',
        'verse': '罗马书8:28',
        'text': '我们晓得万事都互相效力，叫爱神的人得益处，就是按他旨意被召的人。',
        'theme': '苦难中有盼望',
    },
    'spiritual_clarity': {
        'label': '灵命清醒',
        'verse': '歌罗西书3:16',
        'text': '当用各样的智慧，把基督的道理丰丰富富地存在心里，用诗章、颂词、灵歌彼此教导，互相劝戒，心被恩感，歌颂神。',
        'theme': '以基督为中心',
    },
}

_GROWTH_STAGES = {
    'blind_spot': ('🌱', '盲点期', '今日愿意放开自我防御，以温柔接受真理。'),
    'growing':    ('🌿', '成长期', '今日操练所知，让知识变成生命的果实。'),
    'stable':     ('🌳', '稳定期', '今日分享所得，以服事他人巩固自己的成长。'),
}


@app.get('/api/daily-devotion-personal')
def get_daily_devotion_personal(request: Request) -> dict:
    """
    千人千面每日灵修 — 根据用户灵命状态（formation）生成个性化灵修内容。
    每日缓存一次，保证不重复调用LLM。
    """
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')

    email = user.get('email', '')
    today = str(_dt.date.today())
    cache_key = f"{email}:{today}:{'en' if is_english() else 'zh'}"

    if cache_key in _devotion_cache:
        return _devotion_cache[cache_key]

    # ── 1. 获取 formation 数据（从 SFDS 快照） ──
    formation_scores: dict = {}
    try:
        with get_db() as (conn, cur):
            cur.execute(
                """SELECT dimension_key, score FROM sfds_formation_snapshots
                   WHERE email=%s ORDER BY created_at DESC LIMIT 24""",
                (email,)
            )
            rows = cur.fetchall()
            for dim, score in rows:
                if dim not in formation_scores:
                    formation_scores[dim] = float(score)
    except Exception:
        pass

    # Fallback defaults if no data
    if not formation_scores:
        formation_scores = {
            'humility': 0.5, 'fear_tendency': 0.5, 'pride_tendency': 0.5,
            'emotional_stability': 0.5, 'truth_alignment': 0.5,
            'relational_health': 0.5, 'resilience': 0.5, 'spiritual_clarity': 0.5,
        }

    # ── 2. 选出今日聚焦维度（最需成长的） ──
    # For inverse dims (fear, pride), high score = needs attention
    inverse_dims = {'fear_tendency', 'pride_tendency'}
    focus_scores = {}
    for dim, score in formation_scores.items():
        if dim in inverse_dims:
            focus_scores[dim] = score  # high = needs more attention
        else:
            focus_scores[dim] = 1.0 - score  # low = needs more growth

    # Pick the dimension most needing attention (deterministic but rotates by day-of-year)
    doy = _dt.date.today().timetuple().tm_yday
    sorted_dims = sorted(focus_scores.items(), key=lambda x: (-x[1], x[0]))
    # Rotate through top-3 by day
    top3 = [d for d, _ in sorted_dims[:3]]
    focus_dim = top3[doy % len(top3)]

    theme_data = _DIM_THEMES.get(focus_dim, _DIM_THEMES['humility'])

    # ── 3. 确定成长阶段 ──
    raw_score = formation_scores.get(focus_dim, 0.5)
    if focus_dim in inverse_dims:
        normalized = raw_score
    else:
        normalized = raw_score

    if normalized < 0.35:
        stage_key = 'blind_spot'
    elif normalized < 0.65:
        stage_key = 'growing'
    else:
        stage_key = 'stable'
    stage_icon, stage_label, stage_action = _GROWTH_STAGES[stage_key]

    # ── 4. 生成个性化灵修文 ──
    devotion_text = ''
    prayer_text = ''
    try:
        from query_emotion_verses import _call_llm_with_fallback
        nickname = user.get('nickname') or user.get('name') or '弟兄姐妹'

        system_prompt = (
            "你是一位温柔、敬虔的基督徒属灵导师。请根据用户当前的灵命聚焦维度，"
            "写一段120-180字的每日灵修文。\n"
            "要求：\n"
            "- 从圣经经文切入，自然联系今日主题\n"
            "- 用温柔、鼓励的语气，不说教，不批评\n"
            "- 结尾给出一个今日具体的可行操练（一句话）\n"
            "- 直接输出正文，不要标题"
        )
        user_msg = (
            f"用户昵称：{nickname}\n"
            f"今日聚焦：{theme_data['theme']}（{theme_data['label']}）\n"
            f"经文：{theme_data['verse']}——「{theme_data['text']}」\n"
            f"成长阶段：{stage_label} {stage_icon}"
        )
        devotion_text = _call_llm_with_fallback(
            system_prompt=system_prompt,
            user_message=user_msg,
            max_tokens=350,
            temperature=0.75,
            tag="personal-devotion",
        )

        # Short prayer
        prayer_system = "你是祷告代写者，请根据今日灵修主题写一段50-80字的祷告文，用第一人称，以「奉主耶稣基督的名祷告，阿们。」结束。"
        prayer_text = _call_llm_with_fallback(
            system_prompt=prayer_system,
            user_message=f"今日主题：{theme_data['theme']}\n经文：{theme_data['verse']}",
            max_tokens=200,
            temperature=0.7,
            tag="personal-prayer",
        )
    except Exception as e:
        devotion_text = f"「{theme_data['text']}」\n\n今日愿你在{theme_data['theme']}上经历神的恩典。{stage_action}"
        prayer_text = f"主啊，今日我将{theme_data['label']}这一功课交托给你。帮助我在今天的生活中活出你的话语。奉主耶稣基督的名祷告，阿们。"

    result = {
        'focus_dim': focus_dim,
        'focus_label': theme_data['label'],
        'theme': theme_data['theme'],
        'verse_ref': theme_data['verse'],
        'verse_text': theme_data['text'],
        'stage': stage_key,
        'stage_icon': stage_icon,
        'stage_label': stage_label,
        'stage_action': stage_action,
        'devotion_text': devotion_text,
        'prayer_text': prayer_text,
        'date': today,
    }
    _devotion_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 经文查阅 API  /api/scripture
# 解析中文经文引用（如"诗篇第一百一十五篇"、"哥林多后书五章1至10节"）
# 返回对应和合本经文正文
# ─────────────────────────────────────────────────────────────────────────────
import re as _re
import csv as _csv
from functools import lru_cache as _lru_cache
from pathlib import Path as _Path

# ── 书卷名映射（中文 → 和合本标准名，处理常见别名）────────────────────────────
_BOOK_ZH_CANON = {
    '创世记': '创世记', '创': '创世记',
    '出埃及记': '出埃及记', '出': '出埃及记',
    '利未记': '利未记', '利': '利未记',
    '民数记': '民数记', '民': '民数记',
    '申命记': '申命记', '申': '申命记',
    '约书亚记': '约书亚记', '书': '约书亚记',
    '士师记': '士师记', '士': '士师记',
    '路得记': '路得记', '得': '路得记',
    '撒母耳记上': '撒母耳记上', '撒上': '撒母耳记上',
    '撒母耳记下': '撒母耳记下', '撒下': '撒母耳记下',
    '列王纪上': '列王纪上', '王上': '列王纪上',
    '列王纪下': '列王纪下', '王下': '列王纪下',
    '历代志上': '历代志上', '代上': '历代志上',
    '历代志下': '历代志下', '代下': '历代志下',
    '以斯拉记': '以斯拉记', '拉': '以斯拉记',
    '尼希米记': '尼希米记', '尼': '尼希米记',
    '以斯帖记': '以斯帖记', '斯': '以斯帖记',
    '约伯记': '约伯记', '伯': '约伯记',
    '诗篇': '诗篇', '诗': '诗篇',
    '箴言': '箴言', '箴': '箴言',
    '传道书': '传道书', '传': '传道书',
    '雅歌': '雅歌', '歌': '雅歌',
    '以赛亚书': '以赛亚书', '赛': '以赛亚书',
    '耶利米书': '耶利米书', '耶': '耶利米书',
    '耶利米哀歌': '耶利米哀歌', '哀': '耶利米哀歌',
    '以西结书': '以西结书', '结': '以西结书',
    '但以理书': '但以理书', '但': '但以理书',
    '何西阿书': '何西阿书', '何': '何西阿书',
    '约珥书': '约珥书', '珥': '约珥书',
    '阿摩司书': '阿摩司书', '摩': '阿摩司书',
    '俄巴底亚书': '俄巴底亚书', '俄': '俄巴底亚书',
    '约拿书': '约拿书', '拿': '约拿书',
    '弥迦书': '弥迦书', '弥': '弥迦书',
    '那鸿书': '那鸿书', '鸿': '那鸿书',
    '哈巴谷书': '哈巴谷书', '哈': '哈巴谷书',
    '西番雅书': '西番雅书', '番': '西番雅书',
    '哈该书': '哈该书', '该': '哈该书',
    '撒迦利亚书': '撒迦利亚书', '亚': '撒迦利亚书',
    '玛拉基书': '玛拉基书', '玛': '玛拉基书',
    '马太福音': '马太福音', '太': '马太福音',
    '马可福音': '马可福音', '可': '马可福音',
    '路加福音': '路加福音', '路': '路加福音',
    '约翰福音': '约翰福音', '约': '约翰福音',
    '使徒行传': '使徒行传', '徒': '使徒行传',
    '罗马书': '罗马书', '罗': '罗马书',
    '哥林多前书': '哥林多前书', '林前': '哥林多前书',
    '哥林多后书': '哥林多后书', '林后': '哥林多后书',
    '加拉太书': '加拉太书', '加': '加拉太书',
    '以弗所书': '以弗所书', '弗': '以弗所书',
    '腓立比书': '腓立比书', '腓': '腓立比书',
    '歌罗西书': '歌罗西书', '西': '歌罗西书',
    '帖撒罗尼迦前书': '帖撒罗尼迦前书', '帖前': '帖撒罗尼迦前书',
    '帖撒罗尼迦后书': '帖撒罗尼迦后书', '帖后': '帖撒罗尼迦后书',
    '提摩太前书': '提摩太前书', '提前': '提摩太前书',
    '提摩太后书': '提摩太后书', '提后': '提摩太后书',
    '提多书': '提多书', '多': '提多书',
    '腓利门书': '腓利门书', '门': '腓利门书',
    '希伯来书': '希伯来书', '来': '希伯来书',
    '雅各书': '雅各书', '雅': '雅各书',
    '彼得前书': '彼得前书', '彼前': '彼得前书',
    '彼得后书': '彼得后书', '彼后': '彼得后书',
    '约翰一书': '约翰一书', '约壹': '约翰一书',
    '约翰二书': '约翰二书', '约贰': '约翰二书',
    '约翰三书': '约翰三书', '约叁': '约翰三书',
    '犹大书': '犹大书', '犹': '犹大书',
    '启示录': '启示录', '启': '启示录',
}

# ── 中文数字 → 阿拉伯数字 ───────────────────────────────────────────────────
_CN_DIGIT = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
             '六': 6, '七': 7, '八': 8, '九': 9}
_CN_UNIT  = {'十': 10, '百': 100, '千': 1000}

def _cn2int(s: str) -> int | None:
    """Convert a Chinese number string like '一百一十五' → 115."""
    s = s.strip()
    if not s:
        return None
    if s.lstrip('-').isdigit():
        return int(s)
    # Handle plain Arabic digits mixed in
    result = 0
    tmp = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c in _CN_DIGIT:
            tmp = _CN_DIGIT[c]
            i += 1
        elif c in _CN_UNIT:
            unit = _CN_UNIT[c]
            if tmp == 0 and unit == 10:
                tmp = 1  # 十五 → 15
            result += tmp * unit
            tmp = 0
            i += 1
        elif c.isdigit():
            # Arabic digit
            num_s = ''
            while i < len(s) and s[i].isdigit():
                num_s += s[i]
                i += 1
            tmp = int(num_s)
        else:
            i += 1
    result += tmp
    return result if result > 0 else None


def _parse_scripture_ref(ref: str) -> tuple[str | None, int | None, int | None, int | None]:
    """
    Parse a Chinese scripture reference into (book, chapter, verse_start, verse_end).
    Examples:
      '诗篇第一百一十五篇'        → ('诗篇', 115, None, None)
      '哥林多后书五章 1至10节'    → ('哥林多后书', 5, 1, 10)
      '路加福音十二章13至21节'    → ('路加福音', 12, 13, 21)
      '以赛亚书40:12-31'          → ('以赛亚书', 40, 12, 31)
    """
    ref = ref.strip()

    # ── book name: try longest match first ──────────────────────────────────
    book = None
    rest = ref
    # Sort by length descending so "哥林多后书" matches before "哥林多"
    for name in sorted(_BOOK_ZH_CANON.keys(), key=len, reverse=True):
        canon = _BOOK_ZH_CANON[name]
        if ref.startswith(name):
            book = canon
            rest = ref[len(name):]
            break

    if book is None:
        return None, None, None, None

    # ── Strip leading 第/卷 ──────────────────────────────────────────────────
    rest = _re.sub(r'^[第卷]\s*', '', rest)

    # ── Arabic colon notation: 40:12-31 ────────────────────────────────────
    m = _re.match(r'^(\d+)[：:章]\s*(\d+)\s*[-–至到]\s*(\d+)', rest)
    if m:
        return book, int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = _re.match(r'^(\d+)[：:章]\s*(\d+)', rest)
    if m:
        return book, int(m.group(1)), int(m.group(2)), int(m.group(2))

    # ── Chapter in Chinese nums ─────────────────────────────────────────────
    m = _re.match(r'^([零一二三四五六七八九十百千\d]+)[篇章卷]', rest)
    chapter = None
    if m:
        chapter = _cn2int(m.group(1))
        rest = rest[m.end():]
    elif _re.match(r'^(\d+)', rest):
        m2 = _re.match(r'^(\d+)', rest)
        chapter = int(m2.group(1))
        rest = rest[m2.end():]

    if chapter is None:
        return book, None, None, None

    # ── Clean up spaces ──────────────────────────────────────────────────────
    rest = rest.strip()
    if not rest or rest in ('篇', '章', '卷', ''):
        return book, chapter, None, None

    # ── Verse range: Arabic ──────────────────────────────────────────────────
    m = _re.match(r'(\d+)\s*[-–至到]\s*(\d+)', rest)
    if m:
        return book, chapter, int(m.group(1)), int(m.group(2))

    # ── Chinese verse range ──────────────────────────────────────────────────
    m = _re.match(r'([零一二三四五六七八九十百千\d]+)[至到节]?\s*[-–至到]\s*([零一二三四五六七八九十百千\d]+)', rest)
    if m:
        return book, chapter, _cn2int(m.group(1)), _cn2int(m.group(2))

    # ── Single verse ────────────────────────────────────────────────────────
    m = _re.match(r'(\d+)', rest)
    if m:
        v = int(m.group(1))
        return book, chapter, v, v

    return book, chapter, None, None


@_lru_cache(maxsize=1)
def _load_cuv_index() -> dict:
    """Load cuv_bible.csv into {(book, chapter, verse) → text} once."""
    idx: dict[tuple, str] = {}
    path = ROOT_DIR / 'bible' / 'cuv_bible.csv'
    if not path.exists():
        return idx
    with open(path, 'r', encoding='utf-8') as f:
        for row in _csv.DictReader(f):
            try:
                key = (row['book'].strip(), int(row['chapter']), int(row['verse']))
                idx[key] = row['text'].strip().replace(' ', '')  # strip CUV spaces
            except (ValueError, KeyError):
                pass
    return idx


@_lru_cache(maxsize=1)
def _load_booknum_to_zh() -> dict:
    """book number(int) -> canonical Chinese book name, from cuv_bible.csv."""
    m: dict = {}
    path = ROOT_DIR / 'bible' / 'cuv_bible.csv'
    if not path.exists():
        return m
    with open(path, 'r', encoding='utf-8') as f:
        for row in _csv.DictReader(f):
            try:
                m[int(row['book number'])] = row['book'].strip()
            except (ValueError, KeyError):
                pass
    return m


@_lru_cache(maxsize=1)
def _load_esv_index() -> dict:
    """Load esv_bible.csv into {(book_zh, chapter, verse) -> english text}.
    Keyed by the canonical Chinese book name (via shared 'book number') so it
    drops into get_scripture's existing lookup loop unchanged."""
    idx: dict = {}
    path = ROOT_DIR / 'bible' / 'esv_bible.csv'
    if not path.exists():
        return idx
    num2zh = _load_booknum_to_zh()
    with open(path, 'r', encoding='utf-8') as f:
        for row in _csv.DictReader(f):
            try:
                book_zh = num2zh.get(int(row['book number']))
                if not book_zh:
                    continue
                key = (book_zh, int(row['chapter']), int(row['verse']))
                idx[key] = row['text'].strip()
            except (ValueError, KeyError):
                pass
    return idx


@_lru_cache(maxsize=1)
def _load_zh_to_en_book() -> dict:
    """canonical Chinese book name -> English book name (from esv_bible.csv)."""
    num2zh = _load_booknum_to_zh()
    num2en: dict = {}
    path = ROOT_DIR / 'bible' / 'esv_bible.csv'
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            for row in _csv.DictReader(f):
                try:
                    num2en[int(row['book number'])] = row['book'].strip()
                except (ValueError, KeyError):
                    pass
    return {zh: num2en[n] for n, zh in num2zh.items() if n in num2en}


def _zh_to_en_book(zh: str):
    return _load_zh_to_en_book().get(zh)


@app.get('/api/scripture')
def get_scripture(ref: str, request: Request, max_verses: int = 200):
    """
    Parse a Chinese scripture reference and return the verse text.
    Query param: ref=<reference string>  e.g. ref=诗篇第一百一十五篇
    """
    ref = ref.strip()
    if not ref:
        raise HTTPException(status_code=400, detail='ref is required')

    book, chapter, v_start, v_end = _parse_scripture_ref(ref)

    if book is None:
        return {'ok': False, 'ref': ref, 'error': '无法识别书卷名', 'verses': []}

    _en = (request.headers.get('X-Lang') or 'zh').lower().startswith('en')
    idx = _load_esv_index() if _en else _load_cuv_index()

    # Determine verse range
    verses_out = []
    if chapter is None:
        # Shouldn't happen, but return nothing
        return {'ok': False, 'ref': ref, 'error': '无法识别章节', 'verses': []}

    if v_start is None:
        # Whole chapter
        v = 1
        while v <= max_verses:
            key = (book, chapter, v)
            if key in idx:
                verses_out.append({'verse': v, 'text': idx[key]})
                v += 1
            else:
                break
    else:
        end = v_end if v_end else v_start
        end = min(end, v_start + max_verses - 1)
        for v in range(v_start, end + 1):
            key = (book, chapter, v)
            if key in idx:
                verses_out.append({'verse': v, 'text': idx[key]})

    return {
        'ok': True,
        'version': 'esv' if _en else 'cuv',
        'ref': ref,
        'book': book,
        'chapter': chapter,
        'verse_start': v_start,
        'verse_end': v_end,
        'verses': verses_out,
    }

# ── Bible Study (查经) ──────────────────────────────────────────────────────

class BibleStudyVerseItem(BaseModel):
    verse: int
    text: str = Field(max_length=300)

class BibleStudyRequest(BaseModel):
    book: str = Field(min_length=1, max_length=30)
    chapter: int = Field(ge=1, le=200)
    verses: list[BibleStudyVerseItem] = Field(max_length=200)

# In-memory cache for generated Bible studies (book, chapter) → study dict
_bible_study_cache: dict[tuple, dict] = {}

@app.post('/api/bible/study')
def generate_bible_study(payload: BibleStudyRequest, request: Request) -> dict:
    """Generate a rich 10-section Bible study for a chapter using LLM; results are cached in-memory."""
    _en = (request.headers.get('X-Lang') or 'zh').lower().startswith('en')
    _lang = 'en' if _en else 'zh'
    cache_key = (payload.book, payload.chapter, _lang)
    if cache_key in _bible_study_cache:
        print(f'[bible-study] cache hit {payload.book} {payload.chapter}', flush=True)
        return {'ok': True, 'study': _bible_study_cache[cache_key], 'cached': True}

    verses_text = '\n'.join(f'{v.verse}\u3000{v.text}' for v in payload.verses)
    ref = f'{payload.book}第{payload.chapter}章'
    print(f'[bible-study] generating ref={ref} verses={len(payload.verses)}', flush=True)

    system_prompt = (
        '你是一位精通圣经原文（希伯来文/希腊文）、系统神学、教会历史和牧者关怀的圣经教师，' 
        '同时擅长中国文化处境化解经。请根据提供的经文，生成一份极为详尽、可供小组查经和个人灵修使用的中文查经材料。\n'
        '严格以合法JSON对象格式返回，不要加Markdown代码块标记。\n'
        '返回格式（所有字段均为中文字符串，除verse_by_verse为数组）:\n'
        '{\n'
        '  "overview": "章节概览：本章主题、结构轮廓、在整卷书/整本圣经中的位置与承上启下作用（200-300字）",\n'
        '  "context": "历史文化背景：作者、写作时代、地理环境、当时的政治宗教文化背景、写作目的；兼顾中国读者的文化联结（250-350字）",\n'
        '  "structure": "段落结构分析：将本章分为3-5个自然段，每段给出小标题和1-2句核心内容，体现章节的叙事/论证逻辑（150-250字）",\n'
        '  "verse_by_verse": [\n'
        '    // 对每一节经文单独详解，格式如下，共N项（N=经文总节数）:\n'
        '    {\n'
        '      "verse": 1,\n'
        '      "comment": "对本节经文的详细解经（120-200字）：解释字词、语法与修辞，说明作者意图，回应可能的疑问",\n'
        '      "word": "本节最重要的一个关键词（希伯来文或希腊文音译+原义）及其神学意涵（50-100字）",\n'
        '      "apply": "本节对当代信徒最直接的一句应用提示（30-60字，以"你/我们"开头）"\n'
        '    }\n'
        '  ],\n'
        '  "key_words": "本章3-5个最重要的神学词语：每词附原文音译、字义、在圣经中的神学发展脉络及本章用法（250-350字）",\n'
        '  "cross_refs": "串珠平行经文：列出5-7处重要相关经文（含新旧约），每处附一句说明其与本章的关联（250-350字）",\n'
        '  "theology": "核心神学主题：提炼本章2-3个核心神学命题，每个命题展开论述其圣经神学与系统神学意义（250-350字）",\n'
        '  "echoes": "历史印证：举2-4个具体史实——早期教父、宗教改革家、宣教士、中国教会历史人物——如何活出或应用本章真理（250-350字）",\n'
        '  "application": "时代应用：分四个维度——个人灵命、家庭婚姻、教会团契、社会职场——各写一段具体的榜样、教训或劝勉（300-400字）",\n'
        '  "practice": "操练建议：5条具体可操作的日常灵命操练，每条含做法、频率与预期生命改变（250-350字）",\n'
        '  "prayer": "祷告引导：一篇150-200字的祷告文，基于本章真理，使用第一人称复数（我们），涵盖认罪、感恩、祈求、委身四个层次"\n'
        '}'
    )

    if _en:
        book_en = _zh_to_en_book(payload.book) or payload.book
        ref = f'{book_en} {payload.chapter}'
        system_prompt = (
            'You are a Bible teacher fluent in the original languages (Hebrew/Greek), systematic theology, church history, and pastoral care. '
            'Based on the provided passage, produce a thorough English Bible-study resource suitable for small-group study and personal devotion.\n'
            'Return ONLY a valid JSON object, with no Markdown code fences.\n'
            'Format (all fields are English strings except verse_by_verse which is an array):\n'
            '{\n'
            '  "overview": "Chapter overview: theme, structural outline, and its place and role within the book and the whole Bible (200-300 words)",\n'
            '  "context": "Historical and cultural background: author, era, geography, political/religious/cultural setting, and purpose of writing (250-350 words)",\n'
            '  "structure": "Paragraph structure: divide the chapter into 3-5 natural sections, each with a heading and 1-2 sentences of core content (150-250 words)",\n'
            '  "verse_by_verse": [\n'
            '    {\n'
            '      "verse": 1,\n'
            '      "comment": "Detailed exegesis of this verse (120-200 words): words, grammar, rhetoric, the intent of the author, and likely questions",\n'
            '      "word": "The single most important key word of this verse (Hebrew or Greek transliteration plus meaning) and its theological significance (50-100 words)",\n'
            '      "apply": "One direct application of this verse for believers today (30-60 words, beginning with You or We)"\n'
            '    }\n'
            '  ],\n'
            '  "key_words": "3-5 most important theological terms of the chapter: each with original-language transliteration, meaning, biblical-theological development, and its use here (250-350 words)",\n'
            '  "cross_refs": "Cross references: 5-7 important related passages (Old and New Testament), each with one sentence on its connection to this chapter (250-350 words)",\n'
            '  "theology": "Core theological themes: 2-3 central propositions, each developed in its biblical and systematic-theological significance (250-350 words)",\n'
            '  "echoes": "Historical witness: 2-4 concrete examples (early church fathers, Reformers, missionaries, notable believers) who lived out or applied the truth of this chapter (250-350 words)",\n'
            '  "application": "Application for today across four dimensions - personal walk, family and marriage, church and fellowship, society and workplace - each a concrete paragraph of example, lesson, or exhortation (300-400 words)",\n'
            '  "practice": "5 concrete, actionable daily spiritual practices, each with method, frequency, and expected transformation (250-350 words)",\n'
            '  "prayer": "A 150-200 word prayer based on the truth of this chapter, in first-person plural (we), covering confession, thanksgiving, petition, and commitment"\n'
            '}'
        )
        user_message = f'Passage: {ref} ({len(payload.verses)} verses)\n\n{verses_text}'
    else:
        user_message = f'经文章节：{ref}（共{len(payload.verses)}节）\n\n{verses_text}'

    try:
        from query_emotion_verses import _call_llm_with_fallback, _strip_markdown_json
        raw = _call_llm_with_fallback(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=6000,
            temperature=0.68,
            tag='bible-study',
        )
        clean = _strip_markdown_json(raw)
        study = json.loads(clean)
    except json.JSONDecodeError:
        study = {'overview': raw, 'parse_error': True}
    except Exception as exc:
        _handle_exc(exc)
        raise HTTPException(status_code=503, detail=('Bible study generation failed; LLM temporarily unavailable' if _en else '查经生成失败，LLM暂不可用'))

    _bible_study_cache[cache_key] = study
    print(f'[bible-study] ok ref={ref} sections={list(study.keys())}', flush=True)
    return {'ok': True, 'study': study}


# ── Bible Video Generation ─────────────────────────────────────────────────────

class VideoVerseItem(BaseModel):
    verse: int
    text: str = Field(..., max_length=500)

class VideoRequest(BaseModel):
    book:    str = Field(..., min_length=1, max_length=30)
    chapter: int = Field(..., ge=0, le=150)
    verses:  List[VideoVerseItem]

@app.post('/api/bible/video')
async def generate_bible_video_endpoint(payload: VideoRequest, request: Request):
    """
    生成圣经章节短视频 (720×1280 MP4, 9:16竖屏)。
    最多 12 节；TTS 配音 + 渐变背景 + 字幕帧。
    大约需要 60-180 秒，请耐心等待。
    无需登录——经文视频属公开内容。
    """

    try:
        from video_gen import generate_bible_video
    except ImportError:
        try:
            from backend.video_gen import generate_bible_video
        except ImportError:
            raise HTTPException(status_code=500, detail='视频生成模块未安装')

    verses_data = [{'verse': v.verse, 'text': v.text} for v in payload.verses]
    try:
        mp4_bytes = await generate_bible_video(
            book=payload.book,
            chapter=payload.chapter,
            verses=verses_data,
            api_key=GOOGLE_TTS_API_KEY or None,
        )
    except Exception as e:
        print(f'[video] 生成失败: {e}', flush=True)
        raise HTTPException(status_code=500, detail=f'视频生成失败: {str(e)}')

    filename = f'{payload.book}{payload.chapter}章.mp4'
    return Response(
        content=mp4_bytes,
        media_type='video/mp4',
        headers={
            'Content-Disposition': f'attachment; filename*=UTF-8''{filename}',
            'Content-Length': str(len(mp4_bytes)),
        },
    )


# ── Sunday School Videos (主日学视频) ────────────────────────────────────────


_VIDEO_BASE_URL  = 'https://cdn.holiness.uk/biblical-films/'
_VIDEO_PREFIX    = 'biblical-films/'
_VIDEO_LISTING_CACHE: dict = {}
_VIDEO_CACHE_TTL = 120


def _list_videos_via_r2_api() -> list:
    account_id  = os.environ.get('R2_ACCOUNT_ID', '').strip()
    access_key  = os.environ.get('R2_ACCESS_KEY_ID', '').strip()
    secret_key  = os.environ.get('R2_SECRET_ACCESS_KEY', '').strip()
    bucket_name = os.environ.get('R2_BUCKET_NAME', '').strip()
    prefix      = os.environ.get('R2_VIDEO_PREFIX', _VIDEO_PREFIX).strip()
    if not all([account_id, access_key, secret_key, bucket_name]):
        raise ValueError('R2 env vars not configured')
    import boto3
    client = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto',
    )
    VIDEO_EXTS = ('.mp4', '.mov', '.webm', '.m4v')
    paginator = client.get_paginator('list_objects_v2')
    videos = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            fname = obj['Key'].split('/')[-1]
            if not fname or not any(fname.lower().endswith(e) for e in VIDEO_EXTS):
                continue
            ts = obj['LastModified'].timestamp() if obj.get('LastModified') else 0.0
            videos.append({'filename': fname, 'modified_ts': ts, 'url': _VIDEO_BASE_URL + fname})
    return videos


def _parse_html_xml_listing(text: str) -> list:
    import re
    videos = []
    if '<ListBucketResult' in text or '<Key>' in text:
        keys  = re.findall(r'<Key>([^<]+\.(?:mp4|mov|webm|m4v))</Key>', text, re.IGNORECASE)
        dates = re.findall(r'<LastModified>([^<]+)</LastModified>', text)
        for i, key in enumerate(keys):
            fname = key.split('/')[-1]
            ts = 0.0
            if i < len(dates):
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(dates[i].replace('Z', '+00:00')).timestamp()
                except Exception:
                    pass
            videos.append({'filename': fname, 'modified_ts': ts, 'url': _VIDEO_BASE_URL + fname})
        if videos:
            return videos
    for href in re.findall(r'href=["\']([^"\'?#]+\.(?:mp4|mov|webm|m4v))', text, re.IGNORECASE):
        fname = href.split('/')[-1]
        videos.append({'filename': fname, 'modified_ts': 0.0, 'url': _VIDEO_BASE_URL + fname})
    return videos


@app.get('/api/sunday-school/videos')
async def list_sunday_school_videos(request: Request, debug: bool = False) -> dict:
    """List sunday school videos from database table sunday_school_videos.
    Add ?debug=1 to bypass cache."""
    import time
    now = time.time()

    if not debug and _VIDEO_LISTING_CACHE.get('ts', 0) + _VIDEO_CACHE_TTL > now:
        return {'ok': True, 'videos': _VIDEO_LISTING_CACHE['videos'], 'cached': True}

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, alias, teacher, scripture, description,
                       video_url, thumbnail_url, duration_sec, sort_order, created_at
                FROM sunday_school_videos
                WHERE is_visible = TRUE
                ORDER BY sort_order ASC, created_at DESC
                """
            )
            rows = cur.fetchall()

        videos = [
            {
                'id':            r[0],
                'title':         r[1] or '',
                'alias':         r[2] or '',
                'display_title': r[2] or r[1] or '',  # 优先使用 alias
                'teacher':       r[3] or '',
                'scripture':     r[4] or '',
                'description':   r[5] or '',
                'video_url':     r[6] or '',
                'thumbnail_url': r[7] or '',
                'duration_sec':  r[8] or 0,
                'sort_order':    r[9] or 0,
                'created_at':    r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ]

        print(f'[sunday-school] DB query ok — {len(videos)} videos', flush=True)
    finally:
        _release_db(conn)

    if not debug:
        _VIDEO_LISTING_CACHE['ts'] = now
        _VIDEO_LISTING_CACHE['videos'] = videos

    result: dict = {'ok': True, 'videos': videos, 'method': 'database', 'cached': False}
    return result


class SundaySchoolVideoPayload(BaseModel):
    title:         str  = Field(default='', max_length=255)
    alias:         str  = Field(default='', max_length=255)
    teacher:       str  = Field(default='', max_length=100)
    scripture:     str  = Field(default='')
    description:   str  = Field(default='')
    video_url:     str  = Field(..., min_length=1)
    thumbnail_url: str  = Field(default='')
    duration_sec:  int  = Field(default=0, ge=0)
    sort_order:    int  = Field(default=0)


@app.post('/api/sunday-school/videos')
def add_sunday_school_video(payload: SundaySchoolVideoPayload, request: Request) -> dict:
    """Admin-only: insert a new video record. Requires X-Admin-Token header."""
    admin_token = request.headers.get('X-Admin-Token', '')
    expected = os.environ.get('ADMIN_TOKEN', '')
    if not expected or admin_token != expected:
        raise HTTPException(status_code=403, detail='Admin token required')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO sunday_school_videos
                    (title, alias, teacher, scripture, description, video_url, thumbnail_url, duration_sec, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                payload.title.strip(),
                payload.alias.strip(),
                payload.teacher.strip(),
                payload.scripture.strip(),
                payload.description.strip(),
                payload.video_url.strip(),
                payload.thumbnail_url.strip(),
                payload.duration_sec,
                payload.sort_order,
            ))
            new_id = cur.fetchone()[0]
            conn.commit()
        return {'ok': True, 'id': new_id}
    except Exception as exc:
        _handle_exc(exc)
        raise HTTPException(status_code=500, detail='Failed to insert video')
    finally:
        _release_db(conn)



# ── Seekers Class Courses (慕道班课程 — 文字/PPT/视频) ───────────────────────────

_SEEKERS_BASE_URL = 'https://cdn.holiness.uk/seekers-class/'
_SEEKERS_PREFIX   = 'seekers-class/'
# 慕道班固定课程顺序（按文件名关键字匹配；未匹配的排在最后按文件名排序）
_SEEKERS_ORDER = ['认识圣经', '认识创造', '认识罪', '认识耶稣', '认识洗礼']
_SEEKERS_CACHE: dict = {}
_SEEKERS_CACHE_TTL = 120

# extension -> media_type
_SEEKERS_MEDIA_MAP = {
    '.mp4': 'video', '.mov': 'video', '.webm': 'video', '.m4v': 'video',
    '.ppt': 'ppt', '.pptx': 'ppt', '.key': 'ppt',
    '.pdf': 'ppt',
    '.txt': 'text', '.md': 'text', '.doc': 'text', '.docx': 'text',
}


def _seekers_media_type(fname: str) -> str:
    low = fname.lower()
    for ext, mt in _SEEKERS_MEDIA_MAP.items():
        if low.endswith(ext):
            return mt
    return ''


def _list_seekers_via_r2_api() -> list:
    account_id  = os.environ.get('R2_ACCOUNT_ID', '').strip()
    access_key  = os.environ.get('R2_ACCESS_KEY_ID', '').strip()
    secret_key  = os.environ.get('R2_SECRET_ACCESS_KEY', '').strip()
    bucket_name = os.environ.get('R2_BUCKET_NAME', '').strip()
    prefix      = os.environ.get('R2_SEEKERS_PREFIX', _SEEKERS_PREFIX).strip()
    if not all([account_id, access_key, secret_key, bucket_name]):
        raise ValueError('R2 env vars not configured')
    import boto3
    client = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto',
    )
    paginator = client.get_paginator('list_objects_v2')
    files = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            fname = obj['Key'].split('/')[-1]
            if not fname:
                continue
            mt = _seekers_media_type(fname)
            if not mt:
                continue
            ts = obj['LastModified'].timestamp() if obj.get('LastModified') else 0.0
            files.append({'filename': fname, 'media_type': mt, 'modified_ts': ts,
                          'url': _SEEKERS_BASE_URL + fname})
    return files


@app.get('/api/seekers-class/courses')
async def list_seekers_class_courses(request: Request, debug: bool = False) -> dict:
    """List 慕道班 course resources (text / ppt / video) from R2.
    Mirrors the Sunday-school listing: R2 API primary, HTTP listing fallback.
    Each item carries a media_type so the client renders the right card."""
    import time, httpx
    now = time.time()

    if not debug and _SEEKERS_CACHE.get('ts', 0) + _SEEKERS_CACHE_TTL > now:
        return {'ok': True, 'courses': _SEEKERS_CACHE['courses'], 'cached': True}

    raw: list = []
    method_used = 'none'
    debug_info: dict = {}

    try:
        raw = _list_seekers_via_r2_api()
        method_used = 'r2_api'
        print(f'[seekers-class] R2 API ok — {len(raw)} files', flush=True)
    except ValueError as e:
        debug_info['r2_skip'] = str(e)
    except Exception as e:
        debug_info['r2_error'] = str(e)
        print(f'[seekers-class] R2 error: {e}', flush=True)

    if not raw:
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(_SEEKERS_BASE_URL)
            debug_info['http_status'] = resp.status_code
            debug_info['http_preview'] = resp.text[:500]
            if resp.status_code == 200:
                import re
                for key in re.findall(r'<Key>([^<]+)</Key>', resp.text):
                    fname = key.split('/')[-1]
                    mt = _seekers_media_type(fname)
                    if mt:
                        raw.append({'filename': fname, 'media_type': mt,
                                    'modified_ts': 0.0, 'url': _SEEKERS_BASE_URL + fname})
                if not raw:
                    for href in re.findall(r'href=["\']([^"\'?#]+)', resp.text):
                        fname = href.split('/')[-1]
                        mt = _seekers_media_type(fname)
                        if mt:
                            raw.append({'filename': fname, 'media_type': mt,
                                        'modified_ts': 0.0, 'url': _SEEKERS_BASE_URL + fname})
                method_used = 'http_listing'
                print(f'[seekers-class] HTTP listing — {len(raw)} files', flush=True)
        except Exception as e:
            debug_info['http_error'] = str(e)
            print(f'[seekers-class] HTTP error: {e}', flush=True)

    def _seekers_sort_key(v):
        for idx, kw in enumerate(_SEEKERS_ORDER):
            if kw in v['filename']:
                return (idx, v['filename'])
        return (len(_SEEKERS_ORDER), v['filename'])
    raw.sort(key=_seekers_sort_key)
    courses = [
        {
            'id':          i + 1,
            'title':       v['filename'].rsplit('.', 1)[0].replace('-', ' ').replace('_', ' '),
            'filename':    v['filename'],
            'media_type':  v['media_type'],
            'url':         v['url'],
            'modified_ts': v['modified_ts'],
        }
        for i, v in enumerate(raw)
    ]

    if not debug:
        _SEEKERS_CACHE['ts'] = now
        _SEEKERS_CACHE['courses'] = courses

    result: dict = {'ok': True, 'courses': courses, 'method': method_used, 'cached': False}
    if debug:
        result['debug'] = debug_info
    return result



# ── Backend-rendered standalone pages ──


# === EXPANSION PACK (content-theology-expansion) — additive, idempotent; append-only, do not edit mid-file ===
try:
    _EXPANSION_PACK_WIRED
except NameError:
    _EXPANSION_PACK_WIRED = True
    try:
        from routers.expansion_pack import router as _expansion_pack_router, init_expansion_pack as _init_expansion_pack
        try:
            _init_expansion_pack(get_db=_get_db, release_db=_release_db,
                                 get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        except Exception as _e_exp:
            print(f"[routers] WARNING: expansion pack init failed: {_e_exp}", flush=True)
        app.include_router(_expansion_pack_router)
        print("[routers] expansion pack (12 modules) wired", flush=True)
    except Exception as _e_exp:
        print(f"[routers] WARNING: expansion pack import failed: {_e_exp}", flush=True)
