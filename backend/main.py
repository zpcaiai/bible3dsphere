import asyncio
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import smtplib
import sqlite3
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
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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

# WeChat Open Platform config
WX_APP_ID = os.getenv('WX_APP_ID', '')
WX_APP_SECRET = os.getenv('WX_APP_SECRET', '')
WX_REDIRECT_URI = os.getenv('WX_REDIRECT_URI', 'http://localhost:8000/api/auth/wechat/callback')

# Email SMTP config
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USER)

# SQLite database
DB_FILE = ROOT_DIR / 'bible_sphere.db'

# In-memory verify code store: email -> {code, expires}
_CODE_STORE: dict[str, dict] = {}
_CODE_LOCK = threading.Lock()

# In-memory session store: token -> user info
_SESSION_STORE: dict[str, dict] = {}
_SESSION_LOCK = threading.Lock()

EMAIL_RE = re.compile(r'^[\w.+\-]+@[\w\-]+\.[\w.\-]+$')


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email      TEXT PRIMARY KEY,
                nickname   TEXT NOT NULL DEFAULT '',
                avatar     TEXT NOT NULL DEFAULT '',
                openid     TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_tags (
                email      TEXT NOT NULL,
                tag_key    TEXT NOT NULL,
                tag_value  TEXT NOT NULL,
                weight     REAL NOT NULL DEFAULT 1.0,
                updated_at REAL NOT NULL,
                PRIMARY KEY (email, tag_key)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_checkins (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL,
                checkin_at REAL NOT NULL,
                data       TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        ''')
        conn.commit()


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
    now = time.time()
    with _get_db() as conn:
        for tag_key, tag_value, weight in tags:
            existing = conn.execute(
                'SELECT weight FROM user_tags WHERE email=? AND tag_key=?',
                (email, tag_key)
            ).fetchone()
            if existing:
                # Blend: decay old value, add new signal
                new_w = round(existing['weight'] * _TAG_WEIGHT_DECAY + weight, 3)
                conn.execute(
                    'UPDATE user_tags SET tag_value=?, weight=?, updated_at=? WHERE email=? AND tag_key=?',
                    (tag_value, new_w, now, email, tag_key)
                )
            else:
                conn.execute(
                    'INSERT INTO user_tags (email, tag_key, tag_value, weight, updated_at) VALUES (?,?,?,?,?)',
                    (email, tag_key, tag_value, weight, now)
                )
        conn.commit()


def _get_user_tags(email: str) -> dict[str, str]:
    """Return {tag_key: tag_value} sorted by weight desc, top-15."""
    with _get_db() as conn:
        rows = conn.execute(
            'SELECT tag_key, tag_value FROM user_tags WHERE email=? ORDER BY weight DESC LIMIT 15',
            (email,)
        ).fetchall()
    return {row['tag_key']: row['tag_value'] for row in rows}


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
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f'{salt}:{digest}'


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(':', 1)
        return hmac.compare_digest(hashlib.sha256((salt + password).encode()).hexdigest(), digest)
    except Exception:
        return False


def _get_user(email: str) -> dict | None:
    with _get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    return dict(row) if row else None


def _create_user(email: str, nickname: str, avatar: str, openid: str, password_hash: str) -> dict:
    created_at = time.time()
    with _get_db() as conn:
        conn.execute(
            'INSERT INTO users (email, nickname, avatar, openid, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (email, nickname, avatar, openid, password_hash, created_at),
        )
        conn.commit()
    return {'email': email, 'nickname': nickname, 'avatar': avatar, 'openid': openid, 'created_at': created_at}


def _migrate_json_users() -> None:
    """One-time migration: import users.json into SQLite if it exists."""
    json_file = ROOT_DIR / 'users.json'
    if not json_file.exists():
        return
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        with _get_db() as conn:
            for email, u in users.items():
                conn.execute(
                    'INSERT OR IGNORE INTO users (email, nickname, avatar, openid, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (email, u.get('nickname', ''), u.get('avatar', ''), u.get('openid', ''), u.get('password_hash', ''), u.get('created_at', time.time())),
                )
            conn.commit()
        json_file.rename(json_file.with_suffix('.json.bak'))
        print('[db] Migrated users.json → SQLite', flush=True)
    except Exception as exc:
        print(f'[db] Migration skipped: {exc}', flush=True)


def _send_email(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
        s.ehlo()
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_FROM, [to], msg.as_string())


def _make_session(user_record: dict) -> str:
    token = secrets.token_urlsafe(32)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB, migrate old data, pre-warm cache at startup."""
    _init_db()
    _migrate_json_users()
    try:
        await asyncio.to_thread(prewarm_cache)
        print('[startup] cache pre-warmed', flush=True)
    except Exception as exc:
        print(f'[startup] prewarm failed: {exc}', flush=True)
    yield


app = FastAPI(title='Bible Emotion Sphere API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


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
    """Redirect to WeChat OAuth2 authorization page."""
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


@app.get('/api/auth/wechat/callback')
async def wechat_callback(code: str = Query(min_length=1), state: str = Query(default='')):
    """Exchange code for openid and create session token."""
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

    # Fetch basic user info
    user_info = {}
    if access_token and openid:
        async with httpx.AsyncClient() as client:
            info_resp = await client.get(
                'https://api.weixin.qq.com/sns/userinfo',
                params={'access_token': access_token, 'openid': openid, 'lang': 'zh_CN'},
                timeout=10,
            )
        user_info = info_resp.json()

    session_token = secrets.token_urlsafe(32)
    user_record = {
        'openid': openid,
        'unionid': unionid,
        'nickname': user_info.get('nickname', ''),
        'avatar': user_info.get('headimgurl', ''),
        'created_at': time.time(),
    }
    with _SESSION_LOCK:
        _SESSION_STORE[session_token] = user_record

    frontend_url = WX_REDIRECT_URI.rsplit('/api/', 1)[0]
    return RedirectResponse(f'{frontend_url}/?token={session_token}')


@app.get('/api/auth/me')
def auth_me(request: Request):
    """Verify session token, return user info."""
    auth_header = request.headers.get('Authorization', '')
    token = ''
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
    if not token:
        token = request.query_params.get('token', '')
    if not token:
        raise HTTPException(status_code=401, detail='Not authenticated')
    with _SESSION_LOCK:
        user = _SESSION_STORE.get(token)
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
    return {'ok': True}


@app.post('/api/auth/email/send-code')
async def email_send_code(payload: EmailSendCodeRequest):
    """Send a 6-digit verification code to the given email."""
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Rate limit: one code per 60 seconds
    with _CODE_LOCK:
        existing = _CODE_STORE.get(email)
        if existing and existing['expires'] - 240 > time.time():
            raise HTTPException(status_code=429, detail='Please wait before requesting another code')

    code = f'{random.randint(0, 999999):06d}'
    expires = time.time() + 300  # 5 minutes
    with _CODE_LOCK:
        _CODE_STORE[email] = {'code': code, 'expires': expires}

    if not SMTP_USER or not SMTP_PASS:
        # Dev mode: print code to console
        print(f'[DEV] Email verification code for {email}: {code}', flush=True)
        return {'ok': True, 'dev_code': code}

    body = (
        f'您的情感星球验证码：\n\n'
        f'  {code}\n\n'
        f'验证码 5 分钟内有效，请勿转发给他人。\n\n'
        f'Bible Emotion Sphere'
    )
    try:
        await asyncio.to_thread(_send_email, email, '情感星球 – 邮箱验证码', body)
    except Exception as exc:
        print(f'[email] send failed: {exc}', flush=True)
        raise HTTPException(status_code=502, detail='Failed to send email, please check SMTP config')
    return {'ok': True}


@app.post('/api/auth/email/register')
def email_register(payload: EmailRegisterRequest):
    """Register with email + verification code + password."""
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Verify code
    with _CODE_LOCK:
        entry = _CODE_STORE.get(email)
        if not entry or entry['expires'] < time.time():
            raise HTTPException(status_code=400, detail='Verification code expired, please request a new one')
        if not hmac.compare_digest(entry['code'], payload.code.strip()):
            raise HTTPException(status_code=400, detail='Incorrect verification code')
        del _CODE_STORE[email]

    if _get_user(email):
        raise HTTPException(status_code=409, detail='Email already registered')

    nickname = payload.nickname.strip() or email.split('@')[0]
    public = _create_user(email, nickname, '', '', _hash_password(payload.password))
    token = _make_session(public)
    return {'ok': True, 'token': token, 'user': public}


@app.post('/api/auth/email/login')
def email_login(payload: EmailLoginRequest):
    """Login with email + password."""
    email = payload.email.strip().lower()
    user_record = _get_user(email)
    if not user_record:
        raise HTTPException(status_code=401, detail='Email not registered')
    if not _verify_password(payload.password, user_record.get('password_hash', '')):
        raise HTTPException(status_code=401, detail='Incorrect password')
    public = {k: v for k, v in user_record.items() if k != 'password_hash'}
    token = _make_session(public)
    return {'ok': True, 'token': token, 'user': public}


def _get_session_user(request: Request) -> dict | None:
    """Extract user record from session token in Authorization header."""
    auth = request.headers.get('Authorization', '')
    token = auth[7:].strip() if auth.startswith('Bearer ') else request.query_params.get('token', '')
    if not token:
        return None
    with _SESSION_LOCK:
        return _SESSION_STORE.get(token)


@app.post('/api/user/checkin')
def post_checkin(payload: CheckinRequest, request: Request) -> dict:
    """Save checkin data and update user tags. Auth optional – tags skipped for guests."""
    user = _get_session_user(request)
    data = payload.model_dump()

    tags = _extract_tags(data)

    if user and user.get('email'):
        email = user['email']
        _upsert_tags(email, tags)
        # Store full checkin record
        with _get_db() as conn:
            conn.execute(
                'INSERT INTO user_checkins (email, checkin_at, data) VALUES (?,?,?)',
                (email, time.time(), json.dumps(data, ensure_ascii=False))
            )
            conn.commit()

    return {'ok': True, 'tags_extracted': len(tags)}


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

    api_key = os.getenv('SILICONFLOW_API_KEY', '')
    if not api_key:
        from query_emotion_verses import SILICONFLOW_API_KEY as _key
        api_key = _key

    req_body = {
        'model': 'deepseek-ai/DeepSeek-V3',
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
                'https://api.siliconflow.cn/v1/chat/completions',
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
        if full_reply and email:
            with _get_db() as conn:
                conn.execute(
                    'INSERT INTO conversation_messages (email, session_id, role, content, created_at) VALUES (?,?,?,?,?)',
                    (email, session_id, 'assistant', full_reply, time.time())
                )
                conn.commit()

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
    try:
        return assess_psychological_state(payload.query.strip())
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@app.post('/api/biblical-example')
def get_biblical_example(payload: GuidanceRequest) -> dict:
    try:
        return fetch_biblical_example(payload.query.strip())
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@app.post('/api/query')
async def post_query(payload: QueryRequest, request: Request) -> dict:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail='Missing query')

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
    try:
        result = await asyncio.to_thread(generate_sermon, query_text)
        return result
    except Exception as exc:
        _handle_exc(exc)
        detail = {'error': str(exc), 'traceback': traceback.format_exc()} if _DEBUG else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


if FRONTEND_DIST.exists():
    app.mount('/assets', StaticFiles(directory=FRONTEND_DIST / 'assets'), name='assets')


@app.get('/{full_path:path}')
def serve_frontend(full_path: str, request: Request):
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='Not found')

    if FRONTEND_DIST.exists():
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / 'index.html')

    raise HTTPException(status_code=404, detail='Frontend build output not found. Run npm run build in emotion-sphere-ui first.')
