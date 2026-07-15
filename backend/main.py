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

# ── 日志基础设施：统一日志入口（不替换既有 print）。LOG_LEVEL 环境变量可调，默认 INFO。──
import logging

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

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

SESSION_COOKIE_NAME = 'biblesphere_session'
SESSION_COOKIE_MAX_AGE = 30 * 24 * 60 * 60


def _request_is_https(request: Request) -> bool:
    forwarded = request.headers.get('x-forwarded-proto', '').split(',', 1)[0].strip().lower()
    return forwarded == 'https' or request.url.scheme == 'https'


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=_request_is_https(request),
        samesite='lax',
        path='/',
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=_request_is_https(request),
        samesite='lax',
        path='/',
    )

# Allowlist of frontend hosts permitted as OAuth login redirect targets.
# Guards against open-redirect + session-token leak via attacker-controlled `frontend` in WeChat `state`.
# Read from env ALLOWED_FRONTENDS (or ALLOWED_ORIGINS), comma-separated origins/URLs; always include known-trusted hosts.
def _extract_host(value: str) -> str:
    try:
        import urllib.parse as _up
        v = (value or '').strip()
        if v and '://' not in v:
            v = 'https://' + v
        return (_up.urlparse(v).hostname or '').lower()
    except Exception:
        return ''

_ALLOWED_FRONTEND_HOSTS = set()
for _src in (os.environ.get('ALLOWED_FRONTENDS', ''), os.environ.get('ALLOWED_ORIGINS', '')):
    for _o in _src.split(','):
        _h = _extract_host(_o)
        if _h:
            _ALLOWED_FRONTEND_HOSTS.add(_h)
# Known-trusted defaults (production domain + local dev)
for _h in ('holiness.uk', 'www.holiness.uk', 'localhost', '127.0.0.1'):
    _ALLOWED_FRONTEND_HOSTS.add(_h)
# Also trust the host of the configured WeChat redirect URI, if any.
_wx_host = _extract_host(WX_REDIRECT_URI)
if _wx_host:
    _ALLOWED_FRONTEND_HOSTS.add(_wx_host)


def _safe_redirect_target(candidate: str, default: str) -> str:
    """Return candidate only if its host is allowlisted (incl. subdomains of allowed hosts); else default."""
    host = _extract_host(candidate)
    if not host:
        return default
    for allowed in _ALLOWED_FRONTEND_HOSTS:
        if host == allowed or host.endswith('.' + allowed):
            return candidate.rstrip('/')
    print(f'[auth][security] rejected non-allowlisted redirect frontend host={host}', flush=True)
    return default

# Email SMTP config (default: sina.com — 465 SSL)
SMTP_HOST = settings.smtp_host
SMTP_PORT = settings.smtp_port
SMTP_USER = settings.smtp_user
SMTP_PASS = settings.smtp_pass
SMTP_FROM = settings.smtp_from

# When true (non-production/local dev ONLY), auth verification codes may be returned in API
# responses if no email service is configured. Never leak codes to clients in production.
_ALLOW_DEV_AUTH_CODE = os.environ.get('ALLOW_DEV_AUTH_CODE', '').strip().lower() in ('1', 'true', 'yes')


def _server_error(exc, msg: str = 'internal error', status_code: int = 500) -> HTTPException:
    """Log the real exception server-side, return a generic HTTPException (no internal detail leak)."""
    try:
        print(f'[server_error] {msg}: {exc!r}', flush=True)
        traceback.print_exc()
    except Exception:
        pass
    return HTTPException(status_code=status_code, detail=msg)
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


def _is_stale_conn_error(exc) -> bool:
    """陈旧/被服务器掐断的连接错误 —— 直接回收换新即可，无需当作故障上报。"""
    import psycopg2 as _pg
    if isinstance(exc, (_pg.OperationalError, _pg.InterfaceError)):
        return True
    m = str(exc).lower()
    return ('ssl connection has been closed' in m
            or 'server closed the connection' in m
            or 'connection already closed' in m
            or 'consuming input failed' in m
            or 'terminating connection' in m
            or 'bad connection' in m
            or 'connection not open' in m)


def _get_db():
    """获取 PostgreSQL 数据库连接（pre-ping + 陈旧连接静默回收）。

    Neon/Render 等托管库会不定期掐断空闲的 SSL 连接
    （"SSL connection has been closed unexpectedly"）。取连接后先做一次轻量
    pre-ping（SELECT 1）探活：
      · 探到已被服务器掐断的陈旧连接 → 静默丢弃并立刻换下一个（不打日志、不 sleep）；
        putconn(close=True) 会把坏连接踢出池，下次 getconn 便新建活连接。
      · 真正连不上库的故障 → 记录并退避重试（保留原 3 次上限）。
    正常抖动下不再刷 "get connection attempt x/3 failed" 的 SSL 噪音日志。"""
    import time as _time
    import psycopg2 as _pg
    from psycopg2.pool import PoolError as _PoolError
    last_exc = None
    stale_recycled = 0
    hard_fail = 0
    for _attempt in range(10):
        conn = None
        try:
            conn = _db_pool.getconn()
            if conn.closed:
                _db_pool.putconn(conn, close=True)
                conn = _db_pool.getconn()
            conn.autocommit = False
            with conn.cursor() as cur:          # pre-ping
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
            if _is_stale_conn_error(exc):
                stale_recycled += 1                # 静默换下一个：不打日志、不 sleep
                continue
            hard_fail += 1
            print(f'[db] get connection attempt {hard_fail}/3 failed: {exc}', flush=True)
            if hard_fail >= 3:
                break
            _time.sleep(0.5 * hard_fail)
    if stale_recycled:
        print(f'[db] recycled {stale_recycled} stale conn(s), still could not get a live connection', flush=True)
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
    init_db_postgresql(_get_db, _release_db, _hash_password, _verify_password)


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


_runtime_ready = threading.Event()
_runtime_ready.set()  # Preserve direct TestClient/import usage before lifespan starts.
_runtime_init_error: str | None = None


async def _initialize_runtime(app: FastAPI) -> None:
    """Initialize DB, migrate old data, download model files, pre-warm cache at startup."""
    # 汇总打印 import 失败而被禁用的可选 router（详见 _log_router_import_failure）
    if _FAILED_ROUTER_IMPORTS:
        logging.getLogger("startup").warning(
            "%d optional router(s) failed to import and are DISABLED: %s",
            len(_FAILED_ROUTER_IMPORTS), ", ".join(_FAILED_ROUTER_IMPORTS),
        )
        print(f"[startup] WARNING: routers disabled due to import failure: {', '.join(_FAILED_ROUTER_IMPORTS)}", flush=True)
    else:
        logging.getLogger("startup").info("all optional routers imported successfully")
    # 初始化数据库连接（优先 PostgreSQL）
    if DATABASE_URL:
        try:
            await asyncio.to_thread(_init_database)
            # Base tables are idempotent and must exist before versioned
            # migrations that alter or reference them on a fresh deployment.
            await asyncio.to_thread(_init_db)
            try:
                applied = await asyncio.to_thread(run_migrations, DATABASE_URL)
                if applied:
                    versions = ', '.join(record.version for record in applied)
                    print(f'[db] migrations applied: {versions}', flush=True)
                else:
                    print('[db] migrations up to date', flush=True)
            except Exception as exc:
                print(f'[db] WARNING: migration runner failed: {exc}', flush=True)
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

    # === expansion batch2 (2026-07): 8 new formation engines ===
    try:
        init_assurance_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] assurance router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: assurance router init failed: {exc}', flush=True)
    try:
        init_forgiveness_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] forgiveness router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: forgiveness router init failed: {exc}', flush=True)
    try:
        init_fellowship_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] fellowship router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: fellowship router init failed: {exc}', flush=True)
    try:
        init_rule_of_life_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] rule_of_life router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: rule_of_life router init failed: {exc}', flush=True)
    try:
        init_fear_of_god_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] fear_of_god router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: fear_of_god router init failed: {exc}', flush=True)
    try:
        init_eucharisteo_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] eucharisteo router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: eucharisteo router init failed: {exc}', flush=True)
    try:
        init_holiness_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] holiness router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: holiness router init failed: {exc}', flush=True)
    try:
        init_neighbor_love_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] neighbor_love router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: neighbor_love router init failed: {exc}', flush=True)

    # === expansion batch3 (2026-07): 5 secondary continents ===
    try:
        init_hope_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] hope router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: hope router init failed: {exc}', flush=True)
    try:
        init_prayer_school_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] prayer_school router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: prayer_school router init failed: {exc}', flush=True)
    try:
        init_contemplation_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] contemplation router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: contemplation router init failed: {exc}', flush=True)
    try:
        init_incarnation_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] incarnation router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: incarnation router init failed: {exc}', flush=True)
    try:
        init_wisdom_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] wisdom router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: wisdom router init failed: {exc}', flush=True)

    # === expansion batch4 (2026-07): 10 person-of-God + pastoral engines ===
    try:
        init_holy_spirit_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] holy_spirit router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: holy_spirit router init failed: {exc}', flush=True)
    try:
        init_adoption_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] adoption router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: adoption router init failed: {exc}', flush=True)
    try:
        init_cross_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] cross router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: cross router init failed: {exc}', flush=True)
    try:
        init_fear_of_man_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] fear_of_man router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: fear_of_man router init failed: {exc}', flush=True)
    try:
        init_providence_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] providence router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: providence router init failed: {exc}', flush=True)
    try:
        init_repentance_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] repentance router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: repentance router init failed: {exc}', flush=True)
    try:
        init_doubt_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] doubt router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: doubt router init failed: {exc}', flush=True)
    try:
        init_generosity_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] generosity router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: generosity router init failed: {exc}', flush=True)
    try:
        init_humility_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] humility router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: humility router init failed: {exc}', flush=True)
    try:
        init_word_delight_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] word_delight router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: word_delight router init failed: {exc}', flush=True)

    # === expansion batch5 (2026-07): 13 emotional/pastoral/life-stage engines ===
    try:
        init_anger_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] anger router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: anger router init failed: {exc}', flush=True)
    try:
        init_loneliness_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] loneliness router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: loneliness router init failed: {exc}', flush=True)
    try:
        init_perfectionism_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] perfectionism router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: perfectionism router init failed: {exc}', flush=True)
    try:
        init_envy_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] envy router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: envy router init failed: {exc}', flush=True)
    try:
        init_burnout_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] burnout router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: burnout router init failed: {exc}', flush=True)
    try:
        init_comfort_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] comfort router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: comfort router init failed: {exc}', flush=True)
    try:
        init_prodigal_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] prodigal router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: prodigal router init failed: {exc}', flush=True)
    try:
        init_acedia_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] acedia router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: acedia router init failed: {exc}', flush=True)
    try:
        init_conscience_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] conscience router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: conscience router init failed: {exc}', flush=True)
    try:
        init_second_coming_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] second_coming router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: second_coming router init failed: {exc}', flush=True)
    try:
        init_chronic_suffering_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] chronic_suffering router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: chronic_suffering router init failed: {exc}', flush=True)
    try:
        init_parenting_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] parenting router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: parenting router init failed: {exc}', flush=True)
    try:
        init_aging_router(get_db=_get_db, release_db=_release_db,
                        get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        print('[routers] aging router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: aging router init failed: {exc}', flush=True)

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
        init_attention_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            to_shanghai_iso=_to_shanghai_iso,
            is_admin=_is_admin,
        )
        print('[routers] attention router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: attention router init failed: {exc}', flush=True)

    try:
        init_mission_feature_guard(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
        )
        init_mission_bridge_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_training_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge training router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge training router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_content_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge content router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge content router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_agents_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge agents router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge agents router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_local_leader_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge local leader router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge local leader router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_attention_pilot_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge attention pilot router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge attention pilot router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_ai_faith_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge AI faith router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge AI faith router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_mobile_workers_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge mobile workers router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge mobile workers router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_night_shift_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge night shift router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge night shift router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_mobile_families_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge mobile families router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge mobile families router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_elder_caregivers_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge elder caregivers router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge elder caregivers router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_mental_health_families_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge mental health families router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge mental health families router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_accessibility_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge accessibility router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge accessibility router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_church_harm_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge church harm router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge church harm router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_family_transitions_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge family transitions router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge family transitions router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_ministry_families_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge ministry families router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge ministry families router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_transition_youth_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge transition youth router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge transition youth router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_reentry_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge reentry router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge reentry router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_operations_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge operations router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge operations router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_outcomes_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge outcomes router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge outcomes router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_analytics_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge analytics router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge analytics router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_offline_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge offline router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge offline router init failed: {exc}', flush=True)

    try:
        init_mission_bridge_localization_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission bridge localization router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission bridge localization router init failed: {exc}', flush=True)

    try:
        init_mission_features_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission features router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission features router init failed: {exc}', flush=True)

    try:
        init_mission_outbox_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission outbox router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission outbox router init failed: {exc}', flush=True)

    try:
        init_mission_audit_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission audit router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission audit router init failed: {exc}', flush=True)

    try:
        init_mission_incidents_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission incidents router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission incidents router init failed: {exc}', flush=True)

    try:
        init_mission_organizations_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission organizations router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission organizations router init failed: {exc}', flush=True)

    try:
        init_mission_field_classification_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission field-classification router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission field-classification router init failed: {exc}', flush=True)

    try:
        init_mission_sensitive_export_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission sensitive-export router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission sensitive-export router init failed: {exc}', flush=True)

    try:
        init_mission_fields_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission fields router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission fields router init failed: {exc}', flush=True)

    try:
        init_mission_claims_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission claims router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission claims router init failed: {exc}', flush=True)

    try:
        init_mission_calling_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission calling router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission calling router init failed: {exc}', flush=True)

    try:
        init_mission_readiness_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission readiness router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission readiness router init failed: {exc}', flush=True)

    try:
        init_mission_training_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission training router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission training router init failed: {exc}', flush=True)

    try:
        init_mission_certification_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission certification router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission certification router init failed: {exc}', flush=True)

    try:
        init_mission_sending_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission sending router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission sending router init failed: {exc}', flush=True)

    try:
        init_mission_partnership_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission partnership router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission partnership router init failed: {exc}', flush=True)

    try:
        init_mission_learning_portal_router(get_db=_get_db, release_db=_release_db, get_session_user=_get_session_user, is_admin=_is_admin)
        print('[routers] mission learning/supporter portal initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission learning/supporter portal init failed: {exc}', flush=True)

    try:
        init_mission_finance_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission finance router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission finance router init failed: {exc}', flush=True)

    try:
        init_mission_deployment_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission deployment router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission deployment router init failed: {exc}', flush=True)

    try:
        init_mission_roadmap_router(
            get_db=_get_db,
            release_db=_release_db,
            get_session_user=_get_session_user,
            is_admin=_is_admin,
        )
        print('[routers] mission roadmap router initialized', flush=True)
    except Exception as exc:
        print(f'[routers] WARNING: mission roadmap router init failed: {exc}', flush=True)

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

    print('[startup] runtime initialization complete', flush=True)


async def _run_runtime_initialization(app: FastAPI) -> None:
    """Run deferred startup work and publish readiness only after it completes."""
    global _runtime_init_error
    try:
        await _initialize_runtime(app)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _runtime_init_error = f'{type(exc).__name__}: {exc}'
        logging.getLogger('startup').exception('runtime initialization failed')
    else:
        _runtime_init_error = None
        _runtime_ready.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start serving health checks before heavyweight HF runtime initialization."""
    global _runtime_init_error
    _runtime_ready.clear()
    _runtime_init_error = None
    defer_startup = os.getenv('DEFER_STARTUP_INITIALIZATION', '').strip().lower() in {
        '1', 'true', 'yes', 'on',
    }
    startup_task = None
    if defer_startup:
        print('[startup] deferred initialization enabled; health endpoint is available', flush=True)
        startup_task = asyncio.create_task(
            _run_runtime_initialization(app),
            name='runtime-initialization',
        )
        app.state.runtime_initialization_task = startup_task
    else:
        await _initialize_runtime(app)
        _runtime_ready.set()

    try:
        yield
    finally:
        if startup_task is not None and not startup_task.done():
            startup_task.cancel()
            try:
                await startup_task
            except asyncio.CancelledError:
                pass


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
from routers.speech import router as speech_router
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
# === expansion batch2 (2026-07): 8 new formation engines ===
from routers.assurance import router as assurance_router, init_assurance_router
from routers.forgiveness import router as forgiveness_router, init_forgiveness_router
from routers.fellowship import router as fellowship_router, init_fellowship_router
from routers.rule_of_life import router as rule_of_life_router, init_rule_of_life_router
from routers.fear_of_god import router as fear_of_god_router, init_fear_of_god_router
from routers.eucharisteo import router as eucharisteo_router, init_eucharisteo_router
from routers.holiness import router as holiness_router, init_holiness_router
from routers.neighbor_love import router as neighbor_love_router, init_neighbor_love_router
# === expansion batch3 (2026-07): 5 secondary continents ===
from routers.hope import router as hope_router, init_hope_router
from routers.prayer_school import router as prayer_school_router, init_prayer_school_router
from routers.contemplation import router as contemplation_router, init_contemplation_router
from routers.incarnation import router as incarnation_router, init_incarnation_router
from routers.wisdom import router as wisdom_router, init_wisdom_router
# === expansion batch4 (2026-07): 10 person-of-God + pastoral engines ===
from routers.holy_spirit import router as holy_spirit_router, init_holy_spirit_router
from routers.adoption import router as adoption_router, init_adoption_router
from routers.cross import router as cross_router, init_cross_router
from routers.fear_of_man import router as fear_of_man_router, init_fear_of_man_router
from routers.providence import router as providence_router, init_providence_router
from routers.repentance import router as repentance_router, init_repentance_router
from routers.doubt import router as doubt_router, init_doubt_router
from routers.generosity import router as generosity_router, init_generosity_router
from routers.humility import router as humility_router, init_humility_router
from routers.word_delight import router as word_delight_router, init_word_delight_router
# === expansion batch5 (2026-07): 13 emotional/pastoral/life-stage engines ===
from routers.anger import router as anger_router, init_anger_router
from routers.loneliness import router as loneliness_router, init_loneliness_router
from routers.perfectionism import router as perfectionism_router, init_perfectionism_router
from routers.envy import router as envy_router, init_envy_router
from routers.burnout import router as burnout_router, init_burnout_router
from routers.comfort import router as comfort_router, init_comfort_router
from routers.prodigal import router as prodigal_router, init_prodigal_router
from routers.acedia import router as acedia_router, init_acedia_router
from routers.conscience import router as conscience_router, init_conscience_router
from routers.second_coming import router as second_coming_router, init_second_coming_router
from routers.chronic_suffering import router as chronic_suffering_router, init_chronic_suffering_router
from routers.parenting import router as parenting_router, init_parenting_router
from routers.aging import router as aging_router, init_aging_router
from routers.books import router as books_router, init_books_router
from routers.accountability import router as accountability_router, init_accountability_router
from routers.confession import router as confession_router, init_confession_router
from routers.export import router as export_router, init_export_router
from routers.gospel import router as gospel_router, init_gospel_router
from routers.spiritual_formation import router as spiritual_formation_router, init_spiritual_formation_router
from routers.attention import router as attention_router, init_attention_router
from routers.mission_bridge import router as mission_bridge_router, v1_router as mission_bridge_v1_router, init_mission_bridge_router
from routers.mission_bridge_training import router as mission_bridge_training_router, init_mission_bridge_training_router
from routers.mission_bridge_content import router as mission_bridge_content_router, init_mission_bridge_content_router
from routers.mission_bridge_agents import router as mission_bridge_agents_router, init_mission_bridge_agents_router
from routers.mission_bridge_local_leader import router as mission_bridge_local_leader_router, init_mission_bridge_local_leader_router
from routers.mission_bridge_attention_pilot import router as mission_bridge_attention_pilot_router, init_mission_bridge_attention_pilot_router
from routers.mission_bridge_ai_faith import router as mission_bridge_ai_faith_router, init_mission_bridge_ai_faith_router
from routers.mission_bridge_mobile_workers import router as mission_bridge_mobile_workers_router, init_mission_bridge_mobile_workers_router
from routers.mission_bridge_night_shift import router as mission_bridge_night_shift_router, init_mission_bridge_night_shift_router
from routers.mission_bridge_mobile_families import router as mission_bridge_mobile_families_router, init_mission_bridge_mobile_families_router
from routers.mission_bridge_elder_caregivers import router as mission_bridge_elder_caregivers_router, init_mission_bridge_elder_caregivers_router
from routers.mission_bridge_mental_health_families import router as mission_bridge_mental_health_families_router, init_mission_bridge_mental_health_families_router
from routers.mission_bridge_accessibility import router as mission_bridge_accessibility_router, init_mission_bridge_accessibility_router
from routers.mission_bridge_church_harm import router as mission_bridge_church_harm_router, init_mission_bridge_church_harm_router
from routers.mission_bridge_family_transitions import router as mission_bridge_family_transitions_router, init_mission_bridge_family_transitions_router
from routers.mission_bridge_ministry_families import router as mission_bridge_ministry_families_router, init_mission_bridge_ministry_families_router
from routers.mission_bridge_transition_youth import router as mission_bridge_transition_youth_router, init_mission_bridge_transition_youth_router
from routers.mission_bridge_reentry import router as mission_bridge_reentry_router, init_mission_bridge_reentry_router
from routers.mission_bridge_operations import router as mission_bridge_operations_router, init_mission_bridge_operations_router
from routers.mission_bridge_outcomes import router as mission_bridge_outcomes_router, init_mission_bridge_outcomes_router
from routers.mission_bridge_analytics import router as mission_bridge_analytics_router, init_mission_bridge_analytics_router
from routers.mission_bridge_offline import router as mission_bridge_offline_router, init_mission_bridge_offline_router
from routers.mission_bridge_localization import router as mission_bridge_localization_router, init_mission_bridge_localization_router
from routers.mission_features import router as mission_features_router, init_mission_features_router
from routers.mission_outbox import router as mission_outbox_router, init_mission_outbox_router
from routers.mission_audit import router as mission_audit_router, init_mission_audit_router
from routers.mission_incidents import router as mission_incidents_router, init_mission_incidents_router
from routers.mission_organizations import router as mission_organizations_router, init_mission_organizations_router
from routers.mission_field_classification import router as mission_field_classification_router, grants_router as mission_field_grants_router, init_mission_field_classification_router
from routers.mission_sensitive_export import router as mission_sensitive_export_router, init_mission_sensitive_export_router
from routers.mission_fields import router as mission_fields_router, init_mission_fields_router
from routers.mission_claims import router as mission_claims_router, sources_router as mission_sources_router, init_mission_claims_router
from routers.mission_calling import router as mission_calling_router, init_mission_calling_router
from routers.mission_readiness import router as mission_readiness_router, init_mission_readiness_router
from routers.mission_training import router as mission_training_router, lang_router as mission_language_router, init_mission_training_router
from routers.mission_certification import router as mission_certification_router, practicum_router as mission_practicum_router, init_mission_certification_router
from routers.mission_sending import router as mission_sending_router, init_mission_sending_router
from routers.mission_partnership import teams_router as mission_teams_router, partners_router as mission_partners_router, support_router as mission_support_router, init_mission_partnership_router
from routers.mission_finance import router as mission_financial_plans_router, campaign_router as mission_campaign_router, expense_router as mission_expense_router, init_mission_finance_router
from routers.mission_deployment import identity_router as mission_identity_router, credential_router as mission_credential_router, family_router as mission_family_router, gate_router as mission_gate_router, compliance_router as mission_compliance_router, init_mission_deployment_router
from routers.mission_learning_portal import course_router as mission_course_router, supporter_router as mission_supporter_portal_router, init_mission_learning_portal_router
from routers.mission_roadmap import router as mission_roadmap_router, init_mission_roadmap_router
from mission_feature_guard import init_mission_feature_guard
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

# 可选 router 的 import 失败不再只是静默降级为 None：统一记录 + startup 汇总告警。
_FAILED_ROUTER_IMPORTS: list[str] = []


def _log_router_import_failure(name: str, exc: BaseException) -> None:
    _FAILED_ROUTER_IMPORTS.append(name)
    logging.getLogger("startup").warning("Router %s failed to import: %s", name, exc)

try:
    from routers.admin_common import init_admin_router as _init_admin_router
except Exception as _admin_import_exc:
    _init_admin_router = None
    print(f"[routers] WARNING: admin common import failed: {_admin_import_exc}", flush=True)
    _log_router_import_failure("admin_common", _admin_import_exc)
try:
    from routers.admin_users import router as admin_users_router
except Exception as _admin_import_exc:
    admin_users_router = None
    print(f"[routers] WARNING: admin_users router import failed: {_admin_import_exc}", flush=True)
    _log_router_import_failure("admin_users", _admin_import_exc)
try:
    from routers.admin_content import router as admin_content_router
except Exception as _admin_import_exc:
    admin_content_router = None
    print(f"[routers] WARNING: admin_content router import failed: {_admin_import_exc}", flush=True)
    _log_router_import_failure("admin_content", _admin_import_exc)
try:
    from routers.admin_catalog import router as admin_catalog_router
except Exception as _admin_import_exc:
    admin_catalog_router = None
    print(f"[routers] WARNING: admin_catalog router import failed: {_admin_import_exc}", flush=True)
    _log_router_import_failure("admin_catalog", _admin_import_exc)
try:
    from routers.admin_ops import router as admin_ops_router
except Exception as _admin_import_exc:
    admin_ops_router = None
    print(f"[routers] WARNING: admin_ops router import failed: {_admin_import_exc}", flush=True)
    _log_router_import_failure("admin_ops", _admin_import_exc)
_ADMIN_ROUTERS_LOADED = _init_admin_router is not None and any(
    router is not None
    for router in (
        admin_users_router,
        admin_content_router,
        admin_catalog_router,
        admin_ops_router,
    )
)
try:
    from routers.mvfe_stats import router as mvfe_stats_router, init_mvfe_stats_router
except Exception as _e:
    mvfe_stats_router = None
    print(f'[routers] mvfe_stats import skipped: {_e}', flush=True)
    _log_router_import_failure('mvfe_stats', _e)

app = FastAPI(title='Bible Emotion Sphere API', lifespan=lifespan)


@app.middleware('http')
async def runtime_readiness_guard(request: Request, call_next):
    """Keep probes responsive while deferred startup initializes dependencies."""
    if not _runtime_ready.is_set() and request.url.path not in {'/', '/health', '/health/live'}:
        detail = 'runtime initialization in progress'
        if _runtime_init_error:
            detail = 'runtime initialization failed'
        return JSONResponse(
            status_code=503,
            content={'status': 'starting', 'detail': detail},
            headers={'Retry-After': '5', 'Cache-Control': 'no-store'},
        )
    return await call_next(request)
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
app.include_router(speech_router)
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
# === expansion batch2 (2026-07): 8 new formation engines ===
app.include_router(assurance_router)
app.include_router(forgiveness_router)
app.include_router(fellowship_router)
app.include_router(rule_of_life_router)
app.include_router(fear_of_god_router)
app.include_router(eucharisteo_router)
app.include_router(holiness_router)
app.include_router(neighbor_love_router)
# === expansion batch3 (2026-07): 5 secondary continents ===
app.include_router(hope_router)
app.include_router(prayer_school_router)
app.include_router(contemplation_router)
app.include_router(incarnation_router)
app.include_router(wisdom_router)
# === expansion batch4 (2026-07): 10 person-of-God + pastoral engines ===
app.include_router(holy_spirit_router)
app.include_router(adoption_router)
app.include_router(cross_router)
app.include_router(fear_of_man_router)
app.include_router(providence_router)
app.include_router(repentance_router)
app.include_router(doubt_router)
app.include_router(generosity_router)
app.include_router(humility_router)
app.include_router(word_delight_router)
# === expansion batch5 (2026-07): 13 emotional/pastoral/life-stage engines ===
app.include_router(anger_router)
app.include_router(loneliness_router)
app.include_router(perfectionism_router)
app.include_router(envy_router)
app.include_router(burnout_router)
app.include_router(comfort_router)
app.include_router(prodigal_router)
app.include_router(acedia_router)
app.include_router(conscience_router)
app.include_router(second_coming_router)
app.include_router(chronic_suffering_router)
app.include_router(parenting_router)
app.include_router(aging_router)
app.include_router(books_router)
app.include_router(accountability_router)
app.include_router(confession_router)
app.include_router(export_router)
app.include_router(gospel_router)
app.include_router(spiritual_formation_router)
app.include_router(attention_router)
app.include_router(mission_bridge_router)
app.include_router(mission_bridge_v1_router)
app.include_router(mission_bridge_training_router)
app.include_router(mission_bridge_content_router)
app.include_router(mission_bridge_agents_router)
app.include_router(mission_bridge_local_leader_router)
app.include_router(mission_bridge_attention_pilot_router)
app.include_router(mission_bridge_ai_faith_router)
app.include_router(mission_bridge_mobile_workers_router)
app.include_router(mission_bridge_night_shift_router)
app.include_router(mission_bridge_mobile_families_router)
app.include_router(mission_bridge_elder_caregivers_router)
app.include_router(mission_bridge_mental_health_families_router)
app.include_router(mission_bridge_accessibility_router)
app.include_router(mission_bridge_church_harm_router)
app.include_router(mission_bridge_family_transitions_router)
app.include_router(mission_bridge_ministry_families_router)
app.include_router(mission_bridge_transition_youth_router)
app.include_router(mission_bridge_reentry_router)
app.include_router(mission_bridge_operations_router)
app.include_router(mission_bridge_outcomes_router)
app.include_router(mission_bridge_analytics_router)
app.include_router(mission_bridge_offline_router)
app.include_router(mission_bridge_localization_router)
app.include_router(mission_features_router)
app.include_router(mission_outbox_router)
app.include_router(mission_audit_router)
app.include_router(mission_incidents_router)
app.include_router(mission_organizations_router)
app.include_router(mission_field_classification_router)
app.include_router(mission_field_grants_router)
app.include_router(mission_sensitive_export_router)
app.include_router(mission_fields_router)
app.include_router(mission_claims_router)
app.include_router(mission_sources_router)
app.include_router(mission_calling_router)
app.include_router(mission_readiness_router)
app.include_router(mission_training_router)
app.include_router(mission_language_router)
app.include_router(mission_certification_router)
app.include_router(mission_practicum_router)
app.include_router(mission_sending_router)
app.include_router(mission_teams_router)
app.include_router(mission_partners_router)
app.include_router(mission_support_router)
app.include_router(mission_financial_plans_router)
app.include_router(mission_campaign_router)
app.include_router(mission_expense_router)
app.include_router(mission_identity_router)
app.include_router(mission_credential_router)
app.include_router(mission_family_router)
app.include_router(mission_gate_router)
app.include_router(mission_compliance_router)
app.include_router(mission_course_router)
app.include_router(mission_supporter_portal_router)
app.include_router(mission_roadmap_router)
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
if admin_ops_router is not None:
    app.include_router(admin_ops_router)

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
    logging.getLogger('app').error(
        'Unhandled %s on %s %s', err_name, request.method, request.url.path, exc_info=exc,
    )
    return JSONResponse(status_code=500, content={'ok': False, 'detail': 'Internal server error'})


# ── 5xx 结构化日志：捕获显式 raise 的 HTTPException(>=500) ──────────────
# 客户端 detail 已改为通用消息(不再泄漏内部异常);此处把真正的异常(from exc 链)
# 写入服务端日志,补回可观测性。4xx 原样透传,响应体不变。
from starlette.exceptions import HTTPException as _StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler as _default_http_handler


@app.exception_handler(_StarletteHTTPException)
async def http_5xx_logging_handler(request: Request, exc: _StarletteHTTPException):
    """Log server-side details for 5xx HTTPExceptions; client response is unchanged."""
    if exc.status_code >= 500:
        cause = exc.__cause__ or exc.__context__ or exc
        print(f'[ERROR] HTTP {exc.status_code} on {request.method} {request.url.path}: '
              f'{type(cause).__name__}: {cause}', flush=True)
        if cause is not exc and getattr(cause, "__traceback__", None) is not None:
            traceback.print_exception(type(cause), cause, cause.__traceback__)
    return await _default_http_handler(request, exc)


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


# ── /api/health 已并入 routers/main_extracted_health.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──


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
async def wechat_callback(request: Request, code: str = Query(min_length=1), state: str = Query(default='')):
    """Exchange code for openid and establish an HttpOnly browser session."""
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
    session_token = _make_session(user_record)
    
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
                    # SECURITY: only honor allowlisted hosts; otherwise fall back to trusted default
                    redirect_target = _safe_redirect_target(custom_frontend, redirect_target)
            elif custom_frontend:
                redirect_target = _safe_redirect_target(custom_frontend, redirect_target)
                
            print(f'[auth] state parsed: type={redirect_type}, is_mobile={is_mobile}', flush=True)
        except Exception:
            # Old format state or invalid, use default redirect
            pass
    
    response = RedirectResponse(redirect_target)
    _set_session_cookie(response, request, session_token)
    return response


# （/api/auth/me 与 /api/auth/logout 已拆分至 routers/main_extracted_auth_email.py）


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


# （/api/auth/email/* 已拆分至 routers/main_extracted_auth_email.py）


def _get_session_user(request: Request) -> dict | None:
    """Extract session from HttpOnly cookie, with Bearer compatibility for native clients."""
    auth = request.headers.get('Authorization', '')
    token = request.cookies.get(SESSION_COOKIE_NAME, '')
    if not token and auth.startswith('Bearer '):
        token = auth[7:].strip()
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

# Admin allowlist from env (comma-separated emails). Replaces hardcoded backdoors.
# Listed emails are treated as admin in addition to the DB role check.
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get('ADMIN_EMAILS', '').split(',')
    if e.strip()
}


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
    if email.strip().lower() in ADMIN_EMAILS:
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


# ── 邮箱认证 + me/logout 已拆分至 routers/main_extracted_auth_email.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──
from routers.main_extracted_auth_email import (
    router as _auth_email_router,
    init_main_extracted_auth_email,
)
init_main_extracted_auth_email(
    get_db=_get_db,
    release_db=_release_db,
    get_session_user=_get_session_user,
    get_user=_get_user,
    get_user_by_email=_get_user_by_email,
    create_user=_create_user,
    make_session=_make_session,
    set_session_cookie=_set_session_cookie,
    clear_session_cookie=_clear_session_cookie,
    send_email=_send_email,
    generate_code=_generate_code,
    security_audit=_security_audit,
    code_store=_CODE_STORE,
    code_lock=_CODE_LOCK,
    session_store=_SESSION_STORE,
    session_lock=_SESSION_LOCK,
    session_cookie_name=SESSION_COOKIE_NAME,
    smtp_host=SMTP_HOST,
    smtp_port=SMTP_PORT,
    smtp_user=SMTP_USER,
    smtp_pass=SMTP_PASS,
    sendgrid_api_key=SENDGRID_API_KEY,
    resend_api_key=RESEND_API_KEY,
    allow_dev_auth_code=_ALLOW_DEV_AUTH_CODE,
    code_ttl_seconds=CODE_TTL_SECONDS,
)
app.include_router(_auth_email_router)


# ── 签到/祷告恢复/标签画像已拆分至 routers/main_extracted_user_state.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──
from routers.main_extracted_user_state import (
    router as _user_state_router,
    init_main_extracted_user_state,
)
init_main_extracted_user_state(
    get_db=_get_db,
    release_db=_release_db,
    get_session_user=_get_session_user,
    is_admin=_is_admin,
    extract_tags=_extract_tags,
    upsert_tags=_upsert_tags,
    get_user_tags=_get_user_tags,
)
app.include_router(_user_state_router)


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
            # Admin allowlist via env ADMIN_EMAILS (no hardcoded backdoor)
            if email.strip().lower() in ADMIN_EMAILS:
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

# （/api/user/checkin 与 /api/prayers/{id}/restore 已拆分至 routers/main_extracted_user_state.py）


# ── Evangelism Prayers (传福音祷告墙) ─────────────────────────

# （原 DevotionJournalSaveRequest/_row_to_journal 为 journal 拆分后的死代码，已删除；正式版本在 routers/journal.py）

# ── end Devotion Journal ──────────────────────────────────────


# ── Sermon Journal (主日信息) ─────────────────────────────────

# 已拆分至 routers/main_extracted_sermon.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md）
from routers.main_extracted_sermon import (
    router as _sermon_journal_router,
    init_main_extracted_sermon,
)
init_main_extracted_sermon(
    get_db=_get_db,
    release_db=_release_db,
    get_session_user=_get_session_user,
    is_admin=_is_admin,
    to_shanghai_iso=_to_shanghai_iso,
)
app.include_router(_sermon_journal_router)


# ── end Sermon Journal ────────────────────────────────────────


# ── Personal Notes (我的日记) ─────────────────────────────────

# （/api/user/tags 已拆分至 routers/main_extracted_user_state.py）


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








def _ai_status_payload() -> dict:
    """AI 服务降级状态（配额/余额耗尽时前端给出维护提示）。"""
    try:
        from query_emotion_verses import get_ai_status
        return get_ai_status()
    except Exception:
        return {"degraded": False, "quota_exhausted": False, "balance_insufficient": False}




# 健康/存活/AI 状态端点已拆分至 routers/main_extracted_health.py（路径不变，逐字搬移）
from routers.main_extracted_health import (
    router as _health_router,
    init_main_extracted_health,
)
init_main_extracted_health(
    get_db=_get_db,
    release_db=_release_db,
    get_db_pool=lambda: _db_pool,
    runtime_ready=_runtime_ready.is_set,
    ai_status_payload=_ai_status_payload,
    database_url=DATABASE_URL,
)
app.include_router(_health_router)


# ── 翻译已拆分至 routers/main_extracted_translate.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──
from routers.main_extracted_translate import (
    router as _translate_router,
    init_main_extracted_translate,
)
init_main_extracted_translate(
    get_db=_get_db,
    release_db=_release_db,
    call_chat_fn=call_chat,
    database_url=DATABASE_URL,
)
app.include_router(_translate_router)


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




# ── '/' 根路由已并入 routers/main_extracted_health.py（路径不变，逐字搬移） ──


# ── Google Cloud Text-to-Speech Endpoint ─────────────────────────────
class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000, description="要合成的文本")
    language_code: str = Field(default='cmn-CN', description="语言代码，如 cmn-CN, en-US")
    voice_name: str = Field(default='cmn-CN-Wavenet-A', description="指定语音名称")


# 可选：使用环境变量 GOOGLE_APPLICATION_CREDENTIALS 或 GOOGLE_API_KEY
GOOGLE_TTS_API_KEY = settings.google_tts_api_key




# ── Dating Priority (交友原则排序) ──────────────────────────────

# Pydantic 模型
# ── 行为调节系统已拆分至 routers/main_extracted_behavior.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──
from routers.main_extracted_behavior import (
    router as _behavior_router,
    init_main_extracted_behavior,
)
init_main_extracted_behavior(
    get_db=_get_db,
    release_db=_release_db,
    get_session_user=_get_session_user,
)
app.include_router(_behavior_router)


# ── 反思问卷 API ─────────────────────────────────────────────

# ── 习惯状态机 + /api/route 已拆分至 routers/main_extracted_habits.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──
from routers.main_extracted_habits import (
    router as _habits_router,
    init_main_extracted_habits,
)
init_main_extracted_habits(
    get_db=_get_db,
    release_db=_release_db,
    get_session_user=_get_session_user,
    settings_obj=settings,
)
app.include_router(_habits_router)


# ── 千人千面每日灵修已拆分至 routers/main_extracted_devotion.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──
from routers.main_extracted_devotion import (
    router as _devotion_router,
    init_main_extracted_devotion,
)
init_main_extracted_devotion(
    get_session_user=_get_session_user,
    is_english_fn=is_english,
)
app.include_router(_devotion_router)


# ── 经文查阅/查经/圣经视频已拆分至 routers/main_extracted_bible.py（路径不变，逐字搬移；见 docs/REFACTOR_PLAN.md） ──
from routers.main_extracted_bible import (
    router as _bible_router,
    init_main_extracted_bible,
)
init_main_extracted_bible(
    root_dir=ROOT_DIR,
    google_tts_api_key=GOOGLE_TTS_API_KEY,
    handle_exc=_handle_exc,
)
app.include_router(_bible_router)

# ── Sunday School 视频 + Seekers Class 课程已拆分至 routers/main_extracted_edu_media.py（路径不变，逐字搬移） ──
from routers.main_extracted_edu_media import (
    router as _edu_media_router,
    init_main_extracted_edu_media,
)
init_main_extracted_edu_media(
    get_db=_get_db,
    release_db=_release_db,
    handle_exc=_handle_exc,
)
app.include_router(_edu_media_router)



# ── Backend-rendered standalone pages ──


# === EXPANSION PACK (content-theology-expansion) — additive, idempotent; append-only, do not edit mid-file ===
try:
    _EXPANSION_PACK_WIRED
except NameError:
    _EXPANSION_PACK_WIRED = True
    try:
        from routers.expansion_pack import router as _expansion_pack_router, init_expansion_pack as _init_expansion_pack
        _expansion_pack_count = None
        try:
            _expansion_pack_count = _init_expansion_pack(get_db=_get_db, release_db=_release_db,
                                                         get_session_user=_get_session_user, to_shanghai_iso=_to_shanghai_iso)
        except Exception as _e_exp:
            print(f"[routers] WARNING: expansion pack init failed: {_e_exp}", flush=True)
        app.include_router(_expansion_pack_router)
        if _expansion_pack_count is None:
            print("[routers] base expansion pack wired; batch routers are registered separately", flush=True)
        else:
            print(f"[routers] base expansion pack ({_expansion_pack_count} modules) wired; batch routers are registered separately", flush=True)
    except Exception as _e_exp:
        print(f"[routers] WARNING: expansion pack import failed: {_e_exp}", flush=True)
