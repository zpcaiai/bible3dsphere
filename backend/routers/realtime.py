"""
圣徒相通 (Communion) — Realtime router.

Provides, all under /api:
  • WebSocket  /api/ws/rtc            — presence + WebRTC signaling relay + live 1:1 chat
  • GET        /api/rtc/ice-servers   — STUN + time-limited coturn TURN credentials
  • GET/POST   /api/friends ...        — friend list / requests / accept / remove
  • GET        /api/chat/history       — paged 1:1 history
  • POST       /api/chat/read          — mark a conversation read

Design notes
------------
* Mesh voice calls (2-8 people): the browser holds one RTCPeerConnection per peer.
  This server is ONLY a signaling relay — no media flows through it (zero media cost).
* Presence + room membership live in process memory (`ConnectionManager`). HF Space
  runs a single uvicorn process, so this is fine. If you ever scale to multiple
  workers, move this state to Redis pub/sub.
* REST auth reuses the app's HttpOnly session cookie. WebSocket handshakes consume
  a 30-second single-use ticket issued by POST /api/rtc/ws-ticket, so the long-lived
  session credential never appears in a URL.
* TURN credentials follow the coturn REST scheme (RFC: TURN long-term cred via
  shared secret): username = "<expiry_unix_ts>:<email>", password =
  base64(HMAC_SHA1(TURN_SECRET, username)).

多教会决策备注 (2026-06)
-----------------------
好友关系跨教会保留：用户换教会后与旧教会朋友的好友状态和聊天历史不受影响。
POST /friends/request 增加教会门禁：
  (a) 双方同教会（church_id 非 None 且相同）；
  (b) 目标是公开内容作者（community_posts 或 prayers 有公开记录）；
  (c) 已存在 friendship 行（重复请求/互相接受场景）。
拒绝时返回 404，文案与"用户不存在"完全一致，防止 email 枚举。
GET /friends、accept/remove、chat、WebSocket 一律不改，好友跨教会合法。
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
import threading
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, model_validator
from . import main_extracted_auth_email as auth_sessions
from .admin_common import require_admin

router = APIRouter(prefix="/api", tags=["realtime"])

# Helpers injected from main.py via init_realtime_router(...)
_state: dict[str, Any] = {}

# Max members allowed in one mesh voice room (mesh stays comfortable <= 8).
MAX_ROOM_MEMBERS = 8
WS_TICKET_TTL_SECONDS = 30
_ws_tickets: dict[str, tuple[dict, float, str]] = {}
_ws_ticket_lock = threading.Lock()
WS_SESSION_CHECK_SECONDS = 2


def _request_session_token(request: Request) -> str:
    # Match the owning session helper: HttpOnly cookie precedes Bearer.
    return auth_sessions.session_token(request)


def _live_session(token: str) -> dict | None:
    """Authoritative expiry/revocation/ban/deletion gate, never the legacy warm cache.

    Call only in a worker thread from async WebSocket code.
    """
    if not token:
        return None
    get_db = _state.get('get_db')
    release_db = _state.get('release_db')
    if not callable(get_db):
        return None
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SAVEPOINT sp_rt_live_sess')
            try:
                cur.execute(
                    'SELECT t.data FROM user_tokens t JOIN users u ON lower(u.email)=lower(t.email) '
                    'WHERE t.token=%s AND (t.expires_at IS NULL OR t.expires_at>NOW()) '
                    "AND NOT COALESCE(u.is_banned,FALSE) "
                    "AND t.data->>'id' = u.id::text "
                    "AND lower(t.data->>'email') = lower(u.email) "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM account_deletion_requests r "
                    "WHERE r.user_id = u.id AND r.status IN ('processing', 'completed')"
                    ")",
                    (token,),
                )
            except Exception:
                cur.execute('ROLLBACK TO SAVEPOINT sp_rt_live_sess')
                cur.execute(
                    'SELECT t.data FROM user_tokens t JOIN users u ON lower(u.email)=lower(t.email) '
                    'WHERE t.token=%s AND (t.expires_at IS NULL OR t.expires_at>NOW()) '
                    "AND NOT COALESCE(u.is_banned,FALSE) "
                    "AND t.data->>'id' = u.id::text "
                    "AND lower(t.data->>'email') = lower(u.email)",
                    (token,),
                )
            row = cur.fetchone()
        if row is None:
            return None
        return row[0] if isinstance(row[0], dict) else json.loads(row[0])
    finally:
        if callable(release_db):
            release_db(conn)


def _session_user(request: Request) -> dict | None:
    """Treat requests as anonymous until deferred startup injects auth helpers."""
    get_session_user = _state.get("get_session_user")
    if not callable(get_session_user):
        return None
    return get_session_user(request)


def init_realtime_router(*, get_db, release_db, get_session_user, sanitize_text=None,
                         to_shanghai_iso=None) -> None:
    _state.update(
        get_db=get_db,
        release_db=release_db,
        get_session_user=get_session_user,
        sanitize_text=sanitize_text or (lambda s: s),
        to_shanghai_iso=to_shanghai_iso or (lambda dt: dt.isoformat() if dt else None),
    )
    try:
        # init runs inside the app's event loop (lifespan startup); capture it so
        # sync REST endpoints (which run in a threadpool) can schedule WS pushes.
        _state["loop"] = asyncio.get_running_loop()
    except RuntimeError:
        _state["loop"] = None
    _ensure_tables()


def _schedule(coro) -> None:
    """Run an async coroutine from a sync (threadpool) endpoint. Best-effort."""
    loop = _state.get("loop")
    try:
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:  # fallback: no captured loop
            asyncio.run(coro)
    except Exception as exc:  # pragma: no cover
        print(f"[realtime] schedule failed: {exc}", flush=True)


# ===========================================================================
# Idempotent table creation (mirrors migration 0019 so the feature also works
# before the migration is applied; CI migration remains the source of truth).
# ===========================================================================
_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS friendships (
    id SERIAL PRIMARY KEY,
    requester VARCHAR(255) NOT NULL,
    addressee VARCHAR(255) NOT NULL,
    user_low VARCHAR(255) NOT NULL,
    user_high VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_low, user_high)
);
CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships(requester);
CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships(addressee);
CREATE INDEX IF NOT EXISTS idx_friendships_status ON friendships(status);
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    sender VARCHAR(255) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    kind VARCHAR(20) NOT NULL DEFAULT 'text',
    client_id VARCHAR(64),
    delivered BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_pair ON chat_messages(sender, recipient, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_recipient_unread ON chat_messages(recipient, read_at) WHERE read_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_messages(created_at DESC);
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS recalled_at TIMESTAMP;
CREATE TABLE IF NOT EXISTS group_messages (
    id BIGSERIAL PRIMARY KEY,
    group_id VARCHAR(64) NOT NULL,
    sender VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    kind VARCHAR(20) NOT NULL DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recalled_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_group_messages_gid ON group_messages(group_id, id DESC);
"""
_TABLES_SQL += (Path(__file__).resolve().parents[1] / 'migrations' /
                '0245_social_safety.sql').read_text(encoding='utf-8')


def _ensure_tables() -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(_TABLES_SQL)
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[realtime] ensure_tables warning: {exc}", flush=True)
    finally:
        _state["release_db"](conn)


# ===========================================================================
# Connection / presence / room manager (in-memory, single-process)
# ===========================================================================
class ConnectionManager:
    def __init__(self) -> None:
        # email -> set of live WebSocket connections (multi-device/tab support)
        self.connections: dict[str, set[WebSocket]] = {}
        self.sessions: dict[WebSocket, tuple[str, str]] = {}
        self.send_locks: dict[WebSocket, asyncio.Lock] = {}
        self.readiness: dict[WebSocket, asyncio.Event] = {}
        # room_id -> set of member emails
        self.rooms: dict[str, set[str]] = {}
        # email -> set of room_ids the user is currently in
        self.user_rooms: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, email: str, ws: WebSocket, token: str, user_id: str) -> bool:
        """Register a socket. Returns True if this is the user's first connection."""
        async with self._lock:
            first = email not in self.connections or not self.connections[email]
            self.connections.setdefault(email, set()).add(ws)
            self.sessions[ws] = (token, user_id)
            self.send_locks[ws] = asyncio.Lock()
            self.readiness[ws] = asyncio.Event()
            return first

    async def authorized(self, email: str, ws: WebSocket) -> bool:
        binding = self.sessions.get(ws)
        if not binding:
            return False
        try:
            user = await asyncio.to_thread(_live_session, binding[0])
            return bool(user and user.get('email') == email and
                        str(user.get('id')) == binding[1])
        except Exception:
            # DB unavailability never authorizes private delivery.
            return False

    async def watch_session(self, email: str, ws: WebSocket) -> None:
        while ws in self.sessions:
            await asyncio.sleep(WS_SESSION_CHECK_SECONDS)
            if not await self.authorized(email, ws):
                await self.close_socket(ws)
                return

    async def close_socket(self, ws: WebSocket) -> None:
        lock = self.send_locks.get(ws)
        if lock is None:
            return
        async with lock:
            with suppress(Exception):
                await ws.close(code=4401)

    async def send_to_socket(self, email: str, ws: WebSocket, message: dict) -> bool | None:
        ready = self.readiness.get(ws)
        if ready is None:
            return False
        if message.get('type') != 'ready':
            try:
                # Wait outside the send lock: ready itself must acquire it.
                await asyncio.wait_for(ready.wait(), timeout=10)
            except asyncio.TimeoutError:
                return False
        lock = self.send_locks.get(ws)
        if lock is None:
            return False
        async with lock:
            if not await self.authorized(email, ws):
                with suppress(Exception):
                    await ws.close(code=4401)
                return False
            source = message.get('from') or message.get('email') or message.get('peer') or message.get('with')
            if message.get('type') == 'group_chat':
                source = (message.get('message') or {}).get('sender')
            if source and source != email:
                if not await asyncio.to_thread(_delivery_allowed, email, source):
                    # Content filtering must not disconnect a healthy recipient.
                    return None
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
                if message.get('type') == 'ready':
                    ready.set()
                return True
            except Exception:
                return False

    async def disconnect(self, email: str, ws: WebSocket) -> tuple[bool, set[str]]:
        """Remove a socket. Returns (now_offline, rooms_left_if_offline)."""
        async with self._lock:
            self.sessions.pop(ws, None)
            self.send_locks.pop(ws, None)
            ready = self.readiness.pop(ws, None)
            if ready is not None:
                ready.set()  # Wake pending deliveries; binding is already gone.
            socks = self.connections.get(email)
            if socks and ws in socks:
                socks.discard(ws)
            now_offline = not self.connections.get(email)
            left_rooms: set[str] = set()
            if now_offline:
                self.connections.pop(email, None)
                left_rooms = self.user_rooms.pop(email, set())
                for rid in left_rooms:
                    members = self.rooms.get(rid)
                    if members:
                        members.discard(email)
                        if not members:
                            self.rooms.pop(rid, None)
            return now_offline, left_rooms

    def is_online(self, email: str) -> bool:
        return bool(self.connections.get(email))

    def online_among(self, emails: list[str]) -> list[str]:
        return [e for e in emails if self.is_online(e)]

    async def send_to_user(self, email: str, message: dict) -> None:
        socks = list(self.connections.get(email, ()))
        dead = []
        for ws in socks:
            if await self.send_to_socket(email, ws, message) is False:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(email, ws)

    async def join_room(self, room_id: str, email: str) -> list[str]:
        """Add user to room. Returns the list of existing members (excluding the joiner)."""
        async with self._lock:
            members = self.rooms.setdefault(room_id, set())
            existing = [m for m in members if m != email]
            members.add(email)
            self.user_rooms.setdefault(email, set()).add(room_id)
            return existing

    async def leave_room(self, room_id: str, email: str) -> list[str]:
        """Remove user from room. Returns remaining members."""
        async with self._lock:
            members = self.rooms.get(room_id, set())
            members.discard(email)
            urooms = self.user_rooms.get(email)
            if urooms:
                urooms.discard(room_id)
            remaining = list(members)
            if not members:
                self.rooms.pop(room_id, None)
            return remaining

    def room_members(self, room_id: str) -> list[str]:
        return list(self.rooms.get(room_id, set()))

    def room_size(self, room_id: str) -> int:
        return len(self.rooms.get(room_id, set()))


manager = ConnectionManager()


# ===========================================================================
# Friendship helpers
# ===========================================================================
def _norm_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def users_blocked(cur, a: str, b: str) -> bool:
    if not a or not b:
        return False
    cur.execute(
        'SELECT 1 FROM user_blocks WHERE '
        '(lower(blocker_email)=lower(%s) AND lower(blocked_email)=lower(%s)) OR '
        '(lower(blocker_email)=lower(%s) AND lower(blocked_email)=lower(%s)) LIMIT 1',
        (a, b, b, a),
    )
    return cur.fetchone() is not None


def _delivery_allowed(viewer: str, source: str) -> bool:
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            return not users_blocked(cur, viewer, source)
    finally:
        _state['release_db'](conn)


def _lock_social_pair(cur, a: str, b: str) -> None:
    cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                (json.dumps(_norm_pair(a, b)),))


def _room_access(room: str, me: str, peer: str | None = None) -> bool:
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            if room.startswith('vd_'):
                cur.execute('SELECT user_low,user_high FROM direct_voice_rooms WHERE id=%s AND expires_at>NOW()', (room,))
                row = cur.fetchone()
                if not row or me not in row or (peer is not None and (peer not in row or peer == me)):
                    return False
                return _are_friends(cur, row[0], row[1])
            if room.startswith('vg_'):
                cur.execute('SELECT 1 FROM voice_group_members m JOIN voice_groups g ON g.id=m.group_id '
                            'WHERE m.group_id=%s AND m.email=%s AND g.is_active=TRUE', (room[3:], me))
                if not cur.fetchone():
                    return False
                if peer is not None:
                    cur.execute('SELECT 1 FROM voice_group_members WHERE group_id=%s AND email=%s', (room[3:], peer))
                    return cur.fetchone() is not None and not users_blocked(cur, me, peer)
                return True
            return False
    finally:
        _state['release_db'](conn)


def _visible_room_peers(me: str, peers: list[str]) -> list[str]:
    if not peers:
        return []
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT p.peer FROM unnest(%s::text[]) WITH ORDINALITY AS p(peer, ord) "
                "WHERE NOT EXISTS ("
                "SELECT 1 FROM user_blocks b "
                "WHERE (lower(b.blocker_email)=lower(%s) AND lower(b.blocked_email)=lower(p.peer)) "
                "OR (lower(b.blocked_email)=lower(%s) AND lower(b.blocker_email)=lower(p.peer))"
                ") ORDER BY p.ord",
                (list(peers), me, me),
            )
            return [r[0] for r in cur.fetchall()]
    finally:
        _state['release_db'](conn)


def _validate_safety_resource_id(resource_type: str, resource_id: int | str | None, *, allow_none: bool = False) -> int | str | None:
    if resource_type == 'user':
        return resource_id
    if resource_id is None or isinstance(resource_id, bool):
        if allow_none:
            return None
        raise ValueError('resource_id is required')
    if resource_type == 'shared_note':
        sid = str(resource_id).strip()
        if not sid or len(sid) > 128:
            raise ValueError('shared_note resource_id must be 1..128 chars')
        return sid
    try:
        ival = int(resource_id) if isinstance(resource_id, (int, str)) and str(resource_id).strip().isdigit() else None
    except Exception:
        ival = None
    if isinstance(resource_id, int) and not isinstance(resource_id, bool):
        ival = resource_id
    if ival is None or ival < 1 or ival > 9223372036854775807:
        raise ValueError('resource_id must be a positive 64-bit integer')
    return ival


class SafetyUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class SafetyReportRequest(BaseModel):
    resource_type: Literal['user', 'direct_message', 'group_message',
                           'community_post', 'community_comment', 'prayer', 'testimony', 'shared_note']
    resource_id: int | str | None = Field(default=None)
    target_email: str = Field(default='', max_length=255)
    category: Literal['harassment', 'hate', 'sexual', 'violence', 'spam', 'child_safety', 'other']

    @model_validator(mode='after')
    def _check_id(self):
        self.resource_id = _validate_safety_resource_id(self.resource_type, self.resource_id, allow_none=(self.resource_type == 'user'))
        return self


class SafetyReviewRequest(BaseModel):
    disposition: Literal['dismissed', 'escalated']


class SafetyContentRequest(BaseModel):
    resource_type: Literal['direct_message', 'group_message', 'community_post',
                           'community_comment', 'prayer', 'testimony', 'shared_note']
    resource_id: int | str

    @model_validator(mode='after')
    def _check_id(self):
        self.resource_id = _validate_safety_resource_id(self.resource_type, self.resource_id, allow_none=False)
        return self


class SafetyBlockRecordRequest(BaseModel):
    id: uuid.UUID


def _safety_user(request: Request) -> dict:
    user = _live_session(_request_session_token(request))
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Authentication required')
    return user


def _public_report_target(cur, kind: str, resource_id: int | str | None, me: str) -> str | None:
    from psycopg2 import sql
    from .community_feed import get_user_church_id
    cid = get_user_church_id(cur, me)
    if kind == 'community_comment':
        cur.execute('SELECT c.email FROM community_comments c JOIN community_posts p ON p.id=c.post_id '
                    'WHERE c.id=%s AND c.deleted_at IS NULL AND p.deleted_at IS NULL '
                    'AND (p.is_public=TRUE OR p.church_id=%s)', (resource_id, cid))
    else:
        tables = {'community_post': 'community_posts', 'prayer': 'prayers', 'testimony': 'testimonies'}
        cur.execute(sql.SQL('SELECT email FROM {} WHERE id=%s AND deleted_at IS NULL '
                            'AND (is_public=TRUE OR church_id=%s)').format(sql.Identifier(tables[kind])),
                    (resource_id, cid))
    row = cur.fetchone()
    return row[0] if row else None


def _content_report_target(cur, kind: str, resource_id: int | str | None, me: str) -> str | None:
    if kind == 'direct_message':
        cur.execute('SELECT sender FROM chat_messages WHERE id=%s AND recipient=%s', (resource_id, me))
    elif kind == 'group_message':
        cur.execute('SELECT m.sender FROM group_messages m JOIN voice_group_members v '
                    'ON v.group_id=m.group_id WHERE m.id=%s AND v.email=%s', (resource_id, me))
    elif kind == 'shared_note':
        cur.execute(
            'SELECT email FROM personal_notes WHERE id=%s AND shared=TRUE AND deleted_at IS NULL',
            (str(resource_id),),
        )
    else:
        return _public_report_target(cur, kind, resource_id, me)
    row = cur.fetchone()
    return row[0] if row else None


def _expire_direct_voice_rooms_for_pair(cur, a: str, b: str) -> None:
    cur.execute("SELECT to_regclass('direct_voice_rooms') IS NOT NULL")
    if not cur.fetchone()[0]:
        return
    lo_p, hi_p = _norm_pair(a, b)
    cur.execute(
        "UPDATE direct_voice_rooms SET expires_at = NOW() "
        "WHERE ((lower(user_low)=lower(%s) AND lower(user_high)=lower(%s)) "
        "OR (lower(user_low)=lower(%s) AND lower(user_high)=lower(%s))) "
        "AND expires_at > NOW()",
        (lo_p, hi_p, hi_p, lo_p),
    )


@router.get('/safety/blocks')
def safety_blocks(request: Request) -> dict:
    me = _safety_user(request)['email']
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id,blocked_email,identity_known,created_at FROM user_blocks '
                        'WHERE blocker_email=%s ORDER BY created_at', (me,))
            rows = cur.fetchall()
            return {'blocked': [r[1] for r in rows if r[2]],
                    'items': [{'id': str(r[0]), 'label': r[1] if r[2] else '',
                               'blocked_at': r[3].isoformat()} for r in rows]}
    finally:
        _state['release_db'](conn)


@router.post('/safety/blocks')
def safety_block(request: Request, payload: SafetyUserRequest) -> dict:
    me = _safety_user(request)['email']
    target = payload.email.strip().lower()
    if target == me:
        raise HTTPException(status_code=400, detail='Cannot block yourself')
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _lock_social_pair(cur, me, target)
            cur.execute('SELECT 1 FROM users WHERE email=%s', (target,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail='User unavailable')
            cur.execute('INSERT INTO user_blocks(blocker_email,blocked_email,source_key) VALUES(%s,%s,%s) '
                        'ON CONFLICT DO NOTHING', (me, target, 'known:' + target))
            _expire_direct_voice_rooms_for_pair(cur, me, target)
        conn.commit()
        return {'blocked': True}
    finally:
        _state['release_db'](conn)


@router.post('/safety/unblock')
def safety_unblock(request: Request, payload: SafetyUserRequest) -> dict:
    me = _safety_user(request)['email']
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM user_blocks WHERE blocker_email=%s AND blocked_email=%s AND identity_known=TRUE',
                        (me, payload.email.strip().lower()))
        conn.commit()
        return {'blocked': False}
    finally:
        _state['release_db'](conn)


@router.post('/safety/blocks/from-content')
def safety_block_content(request: Request, payload: SafetyContentRequest) -> dict:
    me = _safety_user(request)['email']
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            target = _content_report_target(cur, payload.resource_type, payload.resource_id, me)
            if not target:
                raise HTTPException(status_code=404, detail='Content unavailable')
            if target == me:
                raise HTTPException(status_code=400, detail='Cannot block yourself')
            _lock_social_pair(cur, me, target)
            cur.execute('SELECT 1 FROM users WHERE email=%s', (target,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail='User unavailable')
            # Dedupe only by the reference the caller already knows. Sharing a
            # row with an email-based block would create an anonymous-author oracle.
            source = f'content:{payload.resource_type}:{payload.resource_id}'
            cur.execute('INSERT INTO user_blocks(blocker_email,blocked_email,identity_known,source_key) VALUES(%s,%s,FALSE,%s) '
                        'ON CONFLICT DO NOTHING', (me, target, source))
            _expire_direct_voice_rooms_for_pair(cur, me, target)
        conn.commit()
        return {'blocked': True}
    finally:
        _state['release_db'](conn)


@router.post('/safety/unblock-record')
def safety_unblock_record(request: Request, payload: SafetyBlockRecordRequest) -> dict:
    me = _safety_user(request)['email']
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM user_blocks WHERE id=%s AND blocker_email=%s', (str(payload.id), me))
        conn.commit()
        return {'blocked': False}
    finally:
        _state['release_db'](conn)


@router.post('/safety/reports')
def safety_report(request: Request, payload: SafetyReportRequest) -> dict:
    me = _safety_user(request)['email']
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            if payload.resource_type == 'user':
                target = payload.target_email.strip().lower()
                cur.execute('SELECT 1 FROM users WHERE email=%s', (target,))
                visible = cur.fetchone() is not None
                key = target
            else:
                target = _content_report_target(cur, payload.resource_type, payload.resource_id, me)
                visible = target is not None
                key = str(payload.resource_id)
            if not visible:
                raise HTTPException(status_code=404, detail='Content unavailable')
            if target == me:
                raise HTTPException(status_code=400, detail='Cannot report yourself')
            cur.execute('INSERT INTO social_reports(id,reporter_email,target_email,resource_type,resource_key,category) '
                        'VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT '
                        '(reporter_email,resource_type,resource_key,category) DO UPDATE SET id=social_reports.id '
                        'RETURNING id,status',
                        (str(uuid.uuid4()), me, target, payload.resource_type, key, payload.category))
            report_id, status = cur.fetchone()
        conn.commit()
        return {'id': str(report_id), 'status': status}
    finally:
        _state['release_db'](conn)


@router.get('/safety/moderation/reports')
def safety_review_queue(request: Request) -> dict:
    me = _safety_user(request)['email']
    require_admin(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,resource_type,resource_key,category,status,created_at FROM social_reports "
                        "WHERE status<>'closed' ORDER BY created_at LIMIT 100")
            return {'reports': [{'id': str(r[0]), 'resource_type': r[1], 'resource_key': r[2],
                                 'category': r[3], 'status': r[4], 'created_at': r[5].isoformat()}
                                for r in cur.fetchall()]}
    finally:
        _state['release_db'](conn)


@router.post('/safety/moderation/reports/{report_id}/review')
def safety_review(report_id: uuid.UUID, request: Request, payload: SafetyReviewRequest) -> dict:
    me = _safety_user(request)['email']
    require_admin(request)
    status = 'closed' if payload.disposition == 'dismissed' else 'under_review'
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE social_reports SET status=%s,disposition=%s,reviewer_email=%s,reviewed_at=NOW() '
                        'WHERE id=%s RETURNING id', (status, payload.disposition, me, str(report_id)))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail='Report unavailable')
        conn.commit()
        return {'id': str(report_id), 'status': status}
    finally:
        _state['release_db'](conn)


def _are_friends(cur, a: str, b: str) -> bool:
    if users_blocked(cur, a, b):
        return False
    lo, hi = _norm_pair(a, b)
    cur.execute(
        "SELECT 1 FROM friendships WHERE user_low=%s AND user_high=%s AND status='accepted'",
        (lo, hi),
    )
    return cur.fetchone() is not None


def _friend_emails(cur, email: str) -> list[str]:
    cur.execute(
        "SELECT CASE WHEN lower(friendships.user_low)=lower(%s) THEN friendships.user_high ELSE friendships.user_low END AS peer_email "
        "FROM friendships WHERE (lower(friendships.user_low)=lower(%s) OR lower(friendships.user_high)=lower(%s)) "
        "AND friendships.status='accepted' "
        "AND NOT EXISTS ("
        "SELECT 1 FROM user_blocks b "
        "WHERE (lower(b.blocker_email)=lower(%s) AND lower(b.blocked_email)=lower(CASE WHEN lower(friendships.user_low)=lower(%s) THEN friendships.user_high ELSE friendships.user_low END)) "
        "OR (lower(b.blocked_email)=lower(%s) AND lower(b.blocker_email)=lower(CASE WHEN lower(friendships.user_low)=lower(%s) THEN friendships.user_high ELSE friendships.user_low END))"
        ")",
        (email, email, email, email, email, email, email),
    )
    return [other for (other,) in cur.fetchall()]


def _require_user(request: Request) -> dict:
    user = _session_user(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    return user


# ===========================================================================
# ICE / TURN credentials (coturn REST shared-secret scheme)
# ===========================================================================
@router.get("/rtc/ice-servers")
def ice_servers(request: Request) -> dict:
    """Return STUN + (optionally) time-limited TURN credentials for WebRTC.

    Env:
      STUN_URLS  comma-separated, default Google public STUN
      TURN_URLS  comma-separated coturn URLs, e.g. "turn:turn.holiness.uk:3478,turns:turn.holiness.uk:5349"
      TURN_SECRET  coturn static-auth-secret (use-auth-secret). If unset, only STUN returned.
      TURN_TTL   credential lifetime seconds (default 3600)
    """
    user = _session_user(request)
    email = (user or {}).get("email", "guest")

    stun_urls = [u.strip() for u in os.environ.get(
        "STUN_URLS", "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302"
    ).split(",") if u.strip()]

    ice: list[dict] = [{"urls": stun_urls}] if stun_urls else []

    turn_urls = [u.strip() for u in os.environ.get("TURN_URLS", "").split(",") if u.strip()]
    turn_secret = os.environ.get("TURN_SECRET", "").strip()
    if turn_urls and turn_secret:
        ttl = int(os.environ.get("TURN_TTL", "3600"))
        expiry = int(time.time()) + ttl
        username = f"{expiry}:{email}"
        digest = hmac.new(turn_secret.encode(), username.encode(), hashlib.sha1).digest()
        credential = base64.b64encode(digest).decode()
        ice.append({"urls": turn_urls, "username": username, "credential": credential})

    return {"ok": True, "iceServers": ice, "ttl": int(os.environ.get("TURN_TTL", "3600"))}


# ===========================================================================
# Friends REST
# ===========================================================================
class FriendActionRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


@router.get("/friends")
def list_friends(request: Request) -> dict:
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # Single SQL query with NOT EXISTS user_blocks + lateral unread/last-message (zero N+1 loops)
            cur.execute(
                """
                WITH visible_friends AS (
                    SELECT CASE WHEN lower(f.user_low)=lower(%s) THEN f.user_high ELSE f.user_low END AS fe
                    FROM friendships f
                    WHERE (lower(f.user_low)=lower(%s) OR lower(f.user_high)=lower(%s))
                      AND f.status='accepted'
                      AND NOT EXISTS (
                          SELECT 1 FROM user_blocks b
                          WHERE (lower(b.blocker_email)=lower(%s) AND lower(b.blocked_email)=lower(CASE WHEN lower(f.user_low)=lower(%s) THEN f.user_high ELSE f.user_low END))
                             OR (lower(b.blocked_email)=lower(%s) AND lower(b.blocker_email)=lower(CASE WHEN lower(f.user_low)=lower(%s) THEN f.user_high ELSE f.user_low END))
                      )
                )
                SELECT vf.fe,
                       COALESCE(u.nickname, ''),
                       COALESCE(u.avatar, ''),
                       COALESCE(unr.cnt, 0),
                       lm.body,
                       lm.created_at
                FROM visible_friends vf
                LEFT JOIN users u ON lower(u.email) = lower(vf.fe)
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS cnt
                    FROM chat_messages cm
                    WHERE cm.sender = vf.fe AND cm.recipient = %s AND cm.read_at IS NULL
                ) unr ON TRUE
                LEFT JOIN LATERAL (
                    SELECT cm.body, cm.created_at
                    FROM chat_messages cm
                    WHERE (cm.sender = %s AND cm.recipient = vf.fe)
                       OR (cm.sender = vf.fe AND cm.recipient = %s)
                    ORDER BY cm.created_at DESC
                    LIMIT 1
                ) lm ON TRUE
                """,
                (me, me, me, me, me, me, me, me, me, me),
            )
            friends = []
            for fe, raw_nick, raw_avatar, unread, last_body, last_created in cur.fetchall():
                friends.append({
                    "email": fe,
                    "nickname": raw_nick or fe.split("@")[0],
                    "avatar": raw_avatar or "",
                    "online": manager.is_online(fe),
                    "unread": int(unread or 0),
                    "last_message": last_body if last_body else "",
                    "last_at": _state["to_shanghai_iso"](last_created) if last_created else None,
                })

            # incoming pending requests filtered in SQL via NOT EXISTS user_blocks
            cur.execute(
                """
                SELECT f.requester, f.created_at, COALESCE(u.nickname, ''), COALESCE(u.avatar, '')
                FROM friendships f
                LEFT JOIN users u ON lower(u.email) = lower(f.requester)
                WHERE lower(f.addressee) = lower(%s)
                  AND f.status = 'pending'
                  AND NOT EXISTS (
                      SELECT 1 FROM user_blocks b
                      WHERE (lower(b.blocker_email)=lower(%s) AND lower(b.blocked_email)=lower(f.requester))
                         OR (lower(b.blocked_email)=lower(%s) AND lower(b.blocker_email)=lower(f.requester))
                  )
                ORDER BY f.created_at DESC
                """,
                (me, me, me),
            )
            incoming = [{
                "email": req_email,
                "nickname": req_nick or req_email.split("@")[0],
                "avatar": req_avatar or "",
                "created_at": _state["to_shanghai_iso"](created),
            } for req_email, created, req_nick, req_avatar in cur.fetchall()]
        # sort: online first, then unread desc, then recent
        friends.sort(key=lambda x: (not x["online"], -x["unread"]))
        return {"ok": True, "friends": friends, "incoming": incoming}
    finally:
        _state["release_db"](conn)


@router.post("/friends/request")
def request_friend(request: Request, body: FriendActionRequest) -> dict:
    me = _require_user(request)["email"]
    target = body.email.strip().lower()
    if target == me:
        raise HTTPException(status_code=400, detail="不能添加自己为好友")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _lock_social_pair(cur, me, target)
            if users_blocked(cur, me, target):
                raise HTTPException(status_code=404, detail='User unavailable')
            # 目标用户必须存在（统一 404，防 email 枚举）
            cur.execute("SELECT email FROM users WHERE email=%s", (target,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="该用户不存在")
            lo, hi = _norm_pair(me, target)
            cur.execute(
                "SELECT status, requester FROM friendships WHERE user_low=%s AND user_high=%s",
                (lo, hi),
            )
            existing = cur.fetchone()
            if existing:
                status, _req = existing
                if status == "accepted":
                    return {"ok": True, "status": "accepted", "message": "你们已经是好友"}
                # If the OTHER person already requested me, accept it.
                if status == "pending" and _req == target:
                    cur.execute(
                        "UPDATE friendships SET status='accepted', updated_at=NOW() "
                        "WHERE user_low=%s AND user_high=%s",
                        (lo, hi),
                    )
                    conn.commit()
                    _schedule(_notify_friend_change(target, me))
                    return {"ok": True, "status": "accepted"}
                # (c) 已存在好友行（已发送过请求），跳过门禁
                return {"ok": True, "status": "pending", "message": "好友请求已发送"}

            # ── 教会门禁（新发请求才需要过）──────────────────────────────────
            # 条件 (a): 双方同教会且均有教会
            cur.execute(
                "SELECT church_id FROM church_members WHERE email=%s", (me,)
            )
            my_row = cur.fetchone()
            cur.execute(
                "SELECT church_id FROM church_members WHERE email=%s", (target,)
            )
            tgt_row = cur.fetchone()
            my_cid = my_row[0] if my_row else None
            tgt_cid = tgt_row[0] if tgt_row else None
            same_church = (my_cid is not None and tgt_cid is not None and my_cid == tgt_cid)

            if not same_church:
                # 条件 (b): 目标是公开内容作者
                cur.execute(
                    "SELECT 1 FROM community_posts "
                    "WHERE email=%s AND is_public=TRUE AND deleted_at IS NULL LIMIT 1",
                    (target,),
                )
                has_public_post = cur.fetchone() is not None
                if not has_public_post:
                    cur.execute(
                        "SELECT 1 FROM prayers "
                        "WHERE email=%s AND is_public=TRUE AND is_anonymous=FALSE "
                        "AND deleted_at IS NULL LIMIT 1",
                        (target,),
                    )
                    has_public_prayer = cur.fetchone() is not None
                else:
                    has_public_prayer = False

                if not has_public_post and not has_public_prayer:
                    # 拒绝时文案与"用户不存在"完全一致，防止 email 枚举
                    raise HTTPException(status_code=404, detail="该用户不存在")
            # ─────────────────────────────────────────────────────────────────

            cur.execute(
                "INSERT INTO friendships (requester, addressee, user_low, user_high, status) "
                "VALUES (%s, %s, %s, %s, 'pending')",
                (me, target, lo, hi),
            )
        conn.commit()
        _schedule(manager.send_to_user(target, {"type": "friend_request", "from": me}))
        return {"ok": True, "status": "pending"}
    finally:
        _state["release_db"](conn)


@router.post("/friends/accept")
def accept_friend(request: Request, body: FriendActionRequest) -> dict:
    me = _require_user(request)["email"]
    requester = body.email.strip().lower()
    lo, hi = _norm_pair(me, requester)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _lock_social_pair(cur, me, requester)
            if users_blocked(cur, me, requester):
                raise HTTPException(status_code=403, detail='User unavailable')
            cur.execute(
                "UPDATE friendships SET status='accepted', updated_at=NOW() "
                "WHERE user_low=%s AND user_high=%s AND addressee=%s AND status='pending'",
                (lo, hi, me),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="没有待处理的好友请求")
        conn.commit()
        _schedule(_notify_friend_change(me, requester))
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/friends/remove")
def remove_friend(request: Request, body: FriendActionRequest) -> dict:
    me = _require_user(request)["email"]
    other = body.email.strip().lower()
    lo, hi = _norm_pair(me, other)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM friendships WHERE user_low=%s AND user_high=%s", (lo, hi))
        conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


async def _notify_friend_change(a: str, b: str) -> None:
    for x, y in ((a, b), (b, a)):
        await manager.send_to_user(x, {"type": "friend_added", "with": y, "online": manager.is_online(y)})


# ===========================================================================
# Chat history REST
# ===========================================================================
@router.get("/chat/history")
def chat_history(
    request: Request,
    peer: str = Query(..., min_length=3, max_length=255),
    limit: int = Query(default=50, ge=1, le=200),
    before_id: int = Query(default=0, ge=0),
) -> dict:
    me = _require_user(request)["email"]
    peer = peer.strip().lower()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if users_blocked(cur, me, peer):
                raise HTTPException(status_code=403, detail='Conversation unavailable')
            params: list[Any] = [me, peer, peer, me]
            extra = ""
            if before_id:
                extra = "AND id < %s "
                params.append(before_id)
            params.append(limit)
            cur.execute(
                "SELECT id, sender, recipient, body, kind, client_id, read_at, created_at, recalled_at "
                "FROM chat_messages "
                "WHERE ((sender=%s AND recipient=%s) OR (sender=%s AND recipient=%s)) "
                f"{extra}"
                "ORDER BY id DESC LIMIT %s",
                tuple(params),
            )
            rows = cur.fetchall()
        msgs = [{
            "id": r[0], "sender": r[1], "recipient": r[2],
            "body": "" if r[8] is not None else r[3],
            "kind": r[4], "client_id": r[5],
            "read": r[6] is not None,
            "created_at": _state["to_shanghai_iso"](r[7]),
            "recalled": r[8] is not None,
        } for r in reversed(rows)]
        return {"ok": True, "messages": msgs}
    finally:
        _state["release_db"](conn)


class ReadRequest(BaseModel):
    peer: str = Field(min_length=3, max_length=255)


@router.post("/chat/read")
def mark_read(request: Request, body: ReadRequest) -> dict:
    me = _require_user(request)["email"]
    peer = body.peer.strip().lower()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chat_messages SET read_at=NOW() "
                "WHERE sender=%s AND recipient=%s AND read_at IS NULL",
                (peer, me),
            )
        conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


def _persist_message(sender: str, recipient: str, body: str, kind: str,
                     client_id: str | None, delivered: bool) -> dict | None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _lock_social_pair(cur, sender, recipient)
            if users_blocked(cur, sender, recipient):
                return None
            cur.execute(
                "INSERT INTO chat_messages (sender, recipient, body, kind, client_id, delivered) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, created_at",
                (sender, recipient, body, kind, client_id, delivered),
            )
            mid, created = cur.fetchone()
        conn.commit()
        return {"id": mid, "created_at": _state["to_shanghai_iso"](created)}
    finally:
        _state["release_db"](conn)


# ===========================================================================
# WebSocket: presence + signaling + live chat
# ===========================================================================
@router.post("/rtc/ws-ticket")
def create_ws_ticket(request: Request, response: Response) -> dict:
    """Issue a short-lived, single-use WebSocket credential for the current session."""
    token = _request_session_token(request)
    user = _live_session(token)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Authentication required")
    ticket = secrets.token_urlsafe(32)
    # A wall-clock correction must never extend a process-local ticket's TTL.
    now = time.monotonic()
    with _ws_ticket_lock:
        # Opportunistically prune expired tickets to keep the in-memory store bounded.
        for key, entry in list(_ws_tickets.items()):
            if entry[1] <= now:
                _ws_tickets.pop(key, None)
        # Keep the originating credential only in this short-lived server-side
        # entry. Neither the response nor WebSocket URL contains it. Re-check
        # the original session at consumption so logout revokes unused tickets.
        _ws_tickets[ticket] = (dict(user), now + WS_TICKET_TTL_SECONDS, token)
    response.headers['Cache-Control'] = 'no-store'
    return {"ticket": ticket, "expires_in": WS_TICKET_TTL_SECONDS}


def _consume_ws_ticket(ticket: str) -> tuple[dict, str] | None:
    if not ticket:
        return None
    with _ws_ticket_lock:
        entry = _ws_tickets.pop(ticket, None)
    if not entry or entry[1] <= time.monotonic():
        return None
    current = _live_session(entry[2])
    if not current or current.get('email') != entry[0].get('email'):
        return None
    if str(current.get('id')) != str(entry[0].get('id')):
        return None
    return current, entry[2]


@router.websocket("/ws/rtc")
async def ws_rtc(websocket: WebSocket) -> None:
    # The URL contains only a 30-second, single-use ticket. Long-lived session
    # credentials remain confined to the HttpOnly cookie and never reach logs.
    try:
        consumed = await asyncio.to_thread(_consume_ws_ticket, websocket.query_params.get("ticket", ""))
    except Exception:
        consumed = None
    user, token = consumed if consumed else (None, '')
    if not user or not user.get("email"):
        await websocket.close(code=4401)
        return
    email = user["email"]
    await websocket.accept()

    def _load_friends():
        # 阻塞式 psycopg2 查询放到线程池，避免卡住事件循环。
        conn = _state["get_db"]()
        try:
            with conn.cursor() as cur:
                return _friend_emails(cur, email)
        finally:
            _state["release_db"](conn)

    _state['loop'] = asyncio.get_running_loop()
    first = await manager.connect(email, websocket, token, str(user.get('id')))
    watcher = asyncio.create_task(manager.watch_session(email, websocket))
    try:
        # Tell this client who it is + which friends are currently online.
        friends = await asyncio.to_thread(_load_friends)
        ready_sent = await manager.send_to_socket(email, websocket, {
            "type": "ready", "email": email,
            "online_friends": manager.online_among(friends),
        })
        if not ready_sent:
            return

        # Broadcast presence -> friends (only on the user's first connection)
        if first:
            for fe in friends:
                await manager.send_to_user(fe, {"type": "presence", "email": email, "online": True})

        while True:
            raw = await websocket.receive_text()
            if not await manager.authorized(email, websocket):
                await manager.close_socket(websocket)
                break
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            await _handle_ws_message(email, websocket, msg)
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # pragma: no cover
        print(f"[realtime] ws error for {email}: {exc}", flush=True)
    finally:
        watcher.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await watcher
        now_offline, left_rooms = await manager.disconnect(email, websocket)
        if now_offline:
            # Notify rooms the user dropped from, then friends about offline.
            for rid in left_rooms:
                for member in manager.room_members(rid):
                    await manager.send_to_user(member, {
                        "type": "peer_left", "room": rid, "peer": email,
                    })
            friends = await asyncio.to_thread(_load_friends)
            for fe in friends:
                await manager.send_to_user(fe, {"type": "presence", "email": email, "online": False})


async def _handle_ws_message(email: str, ws: WebSocket, msg: dict) -> None:
    mtype = msg.get("type")

    # ---- 1:1 live chat ------------------------------------------------------
    if mtype == "chat":
        to = (msg.get("to") or "").strip().lower()
        body = (msg.get("body") or "").strip()
        if not to or not body:
            return
        body = _state["sanitize_text"](body)[:4000]
        kind = msg.get("kind", "text")
        client_id = msg.get("client_id")
        # Verify friendship (privacy: only friends can DM).
        # 阻塞式 psycopg2 调用放到线程池，避免卡住事件循环。
        def _check_friends():
            conn = _state["get_db"]()
            try:
                with conn.cursor() as cur:
                    return _are_friends(cur, email, to)
            finally:
                _state["release_db"](conn)
        if not await asyncio.to_thread(_check_friends):
            await manager.send_to_socket(email, ws, {"type": "error", "code": "not_friends",
                                           "client_id": client_id})
            return
        delivered = manager.is_online(to)
        rec = await asyncio.to_thread(_persist_message, email, to, body, kind, client_id, delivered)
        if rec is None:
            await manager.send_to_socket(email, ws, {'type': 'error', 'code': 'user_unavailable', 'client_id': client_id})
            return
        payload = {
            "type": "chat", "id": rec["id"], "from": email, "to": to,
            "body": body, "kind": kind, "client_id": client_id,
            "created_at": rec["created_at"],
        }
        await manager.send_to_user(to, payload)
        # Echo back to sender (ack with server id + all sender's devices)
        await manager.send_to_user(email, {**payload, "self": True})
        return

    if mtype == "typing":
        to = (msg.get("to") or "").strip().lower()
        if to and to != email:
            def _check_typing_friends():
                conn = _state["get_db"]()
                try:
                    with conn.cursor() as cur:
                        return _are_friends(cur, email, to)
                finally:
                    _state["release_db"](conn)
            if await asyncio.to_thread(_check_typing_friends):
                await manager.send_to_user(to, {"type": "typing", "from": email})
        return

    # ---- Voice call room: join / leave -------------------------------------
    if mtype == "join_room":
        room_id = (msg.get("room") or "").strip()
        if not room_id:
            return
        if not await asyncio.to_thread(_room_access, room_id, email):
            await manager.send_to_socket(email, ws, {'type': 'error', 'code': 'room_unavailable'})
            return
        if manager.room_size(room_id) >= MAX_ROOM_MEMBERS and email not in manager.room_members(room_id):
            await manager.send_to_socket(email, ws, {"type": "room_full", "room": room_id})
            return
        existing = await manager.join_room(room_id, email)
        # Membership/blocks may have changed while waiting for the room lock.
        if not await asyncio.to_thread(_room_access, room_id, email):
            await manager.leave_room(room_id, email)
            await manager.send_to_socket(email, ws, {'type': 'error', 'code': 'room_unavailable'})
            return
        existing = await asyncio.to_thread(_visible_room_peers, email, existing)
        # Tell the joiner the existing members (joiner initiates offers to them).
        sent = await manager.send_to_socket(email, ws, {
            "type": "room_peers", "room": room_id, "peers": existing,
        })
        if not sent:
            return
        # Tell existing members a new peer joined.
        for member in existing:
            await manager.send_to_user(member, {"type": "peer_joined", "room": room_id, "peer": email})
        return

    if mtype == "leave_room":
        room_id = (msg.get("room") or "").strip()
        if not room_id:
            return
        remaining = await manager.leave_room(room_id, email)
        for member in remaining:
            await manager.send_to_user(member, {"type": "peer_left", "room": room_id, "peer": email})
        return

    # ---- Invite a friend into a call ---------------------------------------
    if mtype == "call_invite":
        to = (msg.get("to") or "").strip().lower()
        room_id = (msg.get("room") or "").strip()
        if not to or not room_id:
            return
        def _check_invite_friends():
            conn = _state["get_db"]()
            try:
                with conn.cursor() as cur:
                    return _are_friends(cur, email, to)
            finally:
                _state["release_db"](conn)
        ok = await asyncio.to_thread(_check_invite_friends)
        ok = ok and await asyncio.to_thread(_room_access, room_id, email, to)
        if ok:
            await manager.send_to_user(to, {
                "type": "call_invite", "from": email, "room": room_id,
                "title": msg.get("title", "语音通话"),
                "video": bool(msg.get("video")),  # 视频通话标志，接听端据此进房即开摄像头
            })
        return

    if mtype == "call_decline":
        to = (msg.get("to") or "").strip().lower()
        room_id = (msg.get('room') or '').strip()
        if to and await asyncio.to_thread(_room_access, room_id, email, to):
            await manager.send_to_user(to, {"type": "call_decline", "from": email, "room": msg.get("room")})
        return

    # ---- WebRTC signaling relay (offer / answer / ICE candidate) -----------
    if mtype in ("offer", "answer", "candidate"):
        to = (msg.get("to") or "").strip().lower()
        room_id = (msg.get("room") or "").strip()
        if not to:
            return
        if not await asyncio.to_thread(_room_access, room_id, email, to):
            return
        # Relay verbatim; tag the true sender so the recipient can't be spoofed.
        await manager.send_to_user(to, {
            "type": mtype, "from": email, "room": room_id,
            "sdp": msg.get("sdp"), "candidate": msg.get("candidate"),
        })
        return


# ===========================================================================
# 消息撤回（1对1，2分钟内） + 群文字聊天（基于 voice_groups 成员体系）
# ===========================================================================
RECALL_WINDOW_MINUTES = 2


class RecallRequest(BaseModel):
    id: int = Field(gt=0)


@router.post("/chat/recall")
def recall_message(request: Request, body: RecallRequest) -> dict:
    """撤回自己发出的 1对1 消息（发出后 2 分钟内）。"""
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chat_messages SET recalled_at=NOW() "
                "WHERE id=%s AND sender=%s AND recalled_at IS NULL "
                f"AND created_at > NOW() - INTERVAL '{RECALL_WINDOW_MINUTES} minutes' "
                "RETURNING recipient",
                (body.id, me),
            )
            row = cur.fetchone()
            if not row:
                cur.execute("SELECT sender, recalled_at FROM chat_messages WHERE id=%s", (body.id,))
                info = cur.fetchone()
                conn.commit()
                if not info or info[0] != me:
                    raise HTTPException(status_code=404, detail="消息不存在")
                if info[1] is not None:
                    return {"ok": True, "already": True}
                raise HTTPException(status_code=400, detail="发出超过 2 分钟，无法撤回")
            recipient = row[0]
        conn.commit()
        payload = {"type": "chat_recall", "id": body.id, "peer": me}
        _schedule(manager.send_to_user(recipient, payload))
        # 同步通知自己的其他设备/标签页
        _schedule(manager.send_to_user(me, {"type": "chat_recall", "id": body.id, "peer": recipient, "self": True}))
        return {"ok": True}
    finally:
        _state["release_db"](conn)


def _require_group_member(cur, gid: str, me: str) -> None:
    cur.execute("SELECT 1 FROM voice_group_members WHERE group_id=%s AND email=%s", (gid, me))
    if not cur.fetchone():
        raise HTTPException(status_code=403, detail="不是该群成员")


def _group_member_emails(cur, gid: str) -> list[str]:
    cur.execute("SELECT email FROM voice_group_members WHERE group_id=%s", (gid,))
    return [r[0] for r in cur.fetchall()]


def _nickname_of(cur, email: str) -> str:
    cur.execute("SELECT nickname FROM users WHERE email=%s", (email,))
    row = cur.fetchone()
    return (row[0] if row and row[0] else email.split("@")[0])


@router.get("/groups/{gid}/chat")
def group_chat_history(
    request: Request,
    gid: str,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: int = Query(default=0, ge=0),
) -> dict:
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, gid, me)
            params: list[Any] = [gid, me, me]
            extra = ""
            if before_id:
                extra = "AND id < %s "
                params.append(before_id)
            params.append(limit)
            cur.execute(
                "SELECT id, sender, body, kind, created_at, recalled_at "
                "FROM group_messages WHERE group_id=%s "
                "AND NOT EXISTS (SELECT 1 FROM user_blocks b WHERE "
                "(b.blocker_email=%s AND b.blocked_email=group_messages.sender) OR "
                "(b.blocked_email=%s AND b.blocker_email=group_messages.sender)) "
                f"{extra}"
                "ORDER BY id DESC LIMIT %s",
                tuple(params),
            )
            rows = cur.fetchall()
            nick_cache: dict[str, str] = {}
            def nick(e: str) -> str:
                if e not in nick_cache:
                    nick_cache[e] = _nickname_of(cur, e)
                return nick_cache[e]
            msgs = [{
                "id": r[0], "sender": r[1], "sender_name": nick(r[1]),
                "body": "" if r[5] is not None else r[2],
                "kind": r[3],
                "created_at": _state["to_shanghai_iso"](r[4]),
                "recalled": r[5] is not None,
            } for r in reversed(rows)]
        return {"ok": True, "messages": msgs}
    finally:
        _state["release_db"](conn)


class GroupChatSendRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


@router.post("/groups/{gid}/chat")
def group_chat_send(request: Request, gid: str, payload: GroupChatSendRequest) -> dict:
    me = _require_user(request)["email"]
    text = payload.body.strip()
    if not text:
        raise HTTPException(status_code=400, detail="消息不能为空")
    sanitize = _state.get("sanitize_text")
    if sanitize:
        text = sanitize(text)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, gid, me)
            cur.execute(
                "INSERT INTO group_messages (group_id, sender, body) "
                "VALUES (%s, %s, %s) RETURNING id, created_at",
                (gid, me, text),
            )
            mid, created = cur.fetchone()
            members = _group_member_emails(cur, gid)
            sender_name = _nickname_of(cur, me)
        conn.commit()
        message = {
            "id": mid, "sender": me, "sender_name": sender_name,
            "body": text, "kind": "text",
            "created_at": _state["to_shanghai_iso"](created), "recalled": False,
        }
        for member in members:
            _schedule(manager.send_to_user(member, {
                "type": "group_chat", "group": gid, "message": message,
            }))
        return {"ok": True, "message": message}
    finally:
        _state["release_db"](conn)


@router.post("/groups/{gid}/chat/recall")
def group_chat_recall(request: Request, gid: str, body: RecallRequest) -> dict:
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, gid, me)
            cur.execute(
                "UPDATE group_messages SET recalled_at=NOW() "
                "WHERE id=%s AND group_id=%s AND sender=%s AND recalled_at IS NULL "
                f"AND created_at > NOW() - INTERVAL '{RECALL_WINDOW_MINUTES} minutes' "
                "RETURNING id",
                (body.id, gid, me),
            )
            if not cur.fetchone():
                conn.commit()
                raise HTTPException(status_code=400, detail="只能撤回自己 2 分钟内发出的消息")
            members = _group_member_emails(cur, gid)
        conn.commit()
        for member in members:
            _schedule(manager.send_to_user(member, {
                "type": "group_chat_recall", "group": gid, "id": body.id, "by": me,
            }))
        return {"ok": True}
    finally:
        _state["release_db"](conn)
