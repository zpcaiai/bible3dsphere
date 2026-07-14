"""evangelism router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_is_admin = None
_release_db = None
_sanitize_text = None
_to_shanghai_iso = None

def init_evangelism_router(**deps):
    globals().update(deps)

class EvangelismSubmitRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    is_anonymous: bool = False
    kind: str = Field(default='prayer', pattern='^(prayer|testimony)$')


@router.get('/api/evangelism')
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
            # 见证需审核：pending/rejected 只有作者本人和管理员可见
            visible = "deleted_at IS NULL AND (review_status = 'approved' OR email = %s OR %s)"
            cur.execute(
                'SELECT id, email, nickname, content, is_anonymous, amen_count, created_at, updated_at, deleted_at, kind, review_status '
                'FROM evangelism_prayers WHERE ' + visible + ' ORDER BY updated_at DESC LIMIT %s OFFSET %s',
                (email, is_admin, min(limit, 100), offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM evangelism_prayers WHERE ' + visible, (email, is_admin))
            total_active = cur.fetchone()[0]
            total_all = total_active
        items = []
        for row in rows:
            pid, row_email, nick, content, is_anon, amen, created_at, updated_at, deleted_at, kind, review_status = row
            is_own = bool(row_email) and row_email == email
            # 匿名帖：除本人与管理员外，不暴露作者昵称/邮箱
            reveal = is_own or is_admin
            items.append({
                'id': pid,
                'email': row_email if (not is_anon or reveal) else '',
                'nickname': (nick or '弟兄姊妹') if (not is_anon or reveal) else '匿名弟兄姊妹',
                'content': content,
                'is_own': is_own,
                'is_anonymous': bool(is_anon),
                'kind': kind or 'prayer',
                'review_status': review_status or 'approved',
                'amen_count': amen,
                'created_at': _to_shanghai_iso(created_at),
                'updated_at': _to_shanghai_iso(updated_at),
                'deleted_at': _to_shanghai_iso(deleted_at),
            })
        print(f'[evangelism] returning {len(items)} items in {(time.time()-t0)*1000:.0f}ms', flush=True)
        return {'ok': True, 'items': items, 'total': total_active, 'total_all': total_all, 'is_admin': is_admin}
    finally:
        _release_db(conn)


@router.post('/api/evangelism')
def post_evangelism_prayer(payload: EvangelismSubmitRequest, request: Request) -> dict:
    """Submit a new evangelism prayer. Auth optional – guests can post with name 'guest'."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    nickname = user.get('nickname', '') if user else 'guest'
    kind = payload.kind or 'prayer'
    if kind == 'testimony' and not email:
        raise HTTPException(status_code=401, detail='分享见证需要先登录')
    review_status = 'approved' if kind == 'prayer' else 'pending'
    print(f'[evangelism] submit email={email or "guest"} kind={kind} len={len(payload.content)}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO evangelism_prayers (email, nickname, content, is_anonymous, amen_count, kind, review_status) VALUES (%s,%s,%s,%s,0,%s,%s) RETURNING id',
                (email, _sanitize_text(nickname), _sanitize_text(payload.content.strip()), bool(payload.is_anonymous), kind, review_status)
            )
            prayer_id = cur.fetchone()[0]
            conn.commit()
        print(f'[evangelism] saved id={prayer_id}', flush=True)
        if email:
            try:
                import formation_events as _fe
                _fe.record_event(email, "evangelism", "evangelism", title="传福音代祷",
                                 summary=(payload.content or "").strip()[:120] or None, severity="green",
                                 ref_id="evangelism:%s" % prayer_id)
            except Exception:
                pass
        return {'ok': True, 'id': prayer_id, 'review_status': review_status}
    finally:
        _release_db(conn)


class TestimonyReviewRequest(BaseModel):
    approve: bool


@router.post('/api/evangelism/{prayer_id}/review')
def review_evangelism_testimony(prayer_id: int, payload: TestimonyReviewRequest, request: Request) -> dict:
    """Approve/reject a pending testimony. Admin only."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    if not _is_admin(email):
        raise HTTPException(status_code=403, detail='Admin permission required')
    status = 'approved' if payload.approve else 'rejected'
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE evangelism_prayers SET review_status=%s, updated_at=NOW() WHERE id=%s AND kind='testimony' RETURNING id", (status, prayer_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail='Testimony not found')
            conn.commit()
    finally:
        _release_db(conn)
    print(f'[evangelism] testimony {prayer_id} reviewed -> {status} by {email}', flush=True)
    return {'ok': True, 'review_status': status}


# ── 我的挂念（传FY 闭环：挂念名单 / 每日代祷 / 阶段跟踪） ──────────────

CONTACT_STAGES = ('not_yet', 'curious', 'seeking', 'decided', 'baptized', 'walking')
CONTACT_LIMIT = 20


class ContactCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    notes: str = Field(default='', max_length=500)


class ContactUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=60)
    notes: str | None = Field(default=None, max_length=500)
    stage: str | None = Field(default=None)


def _require_email(request: Request) -> str:
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='请先登录')
    return email


def _own_contact(cur, contact_id: int, email: str):
    cur.execute('SELECT id FROM evangelism_contacts WHERE id=%s AND owner_email=%s AND deleted_at IS NULL', (contact_id, email))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail='Contact not found')


@router.get('/api/evangelism/contacts')
def list_evangelism_contacts(request: Request) -> dict:
    """挂念名单 + 今日是否已代祷 + 连续代祷天数。"""
    email = _require_email(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, display_name, stage, notes, created_at, updated_at FROM evangelism_contacts '
                'WHERE owner_email=%s AND deleted_at IS NULL ORDER BY created_at',
                (email,)
            )
            rows = cur.fetchall()
            cur.execute(
                'SELECT contact_id, prayed_on FROM evangelism_prayer_logs WHERE owner_email=%s ORDER BY prayed_on DESC',
                (email,)
            )
            logs = {}
            for cid, day in cur.fetchall():
                logs.setdefault(cid, []).append(day)
    finally:
        _release_db(conn)
    from datetime import date, timedelta
    today = date.today()
    items = []
    for cid, name, stage, notes, created_at, updated_at in rows:
        days = logs.get(cid, [])
        streak = 0
        cursor = today
        day_set = set(days)
        # 今天没祷告则从昨天起算，保持连续感
        if cursor not in day_set:
            cursor = cursor - timedelta(days=1)
        while cursor in day_set:
            streak += 1
            cursor = cursor - timedelta(days=1)
        items.append({
            'id': cid,
            'display_name': name,
            'stage': stage,
            'notes': notes,
            'prayed_today': today in day_set,
            'streak': streak,
            'total_days': len(days),
            'created_at': _to_shanghai_iso(created_at),
        })
    return {'ok': True, 'items': items, 'limit': CONTACT_LIMIT, 'stages': list(CONTACT_STAGES)}


@router.post('/api/evangelism/contacts')
def create_evangelism_contact(payload: ContactCreateRequest, request: Request) -> dict:
    email = _require_email(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM evangelism_contacts WHERE owner_email=%s AND deleted_at IS NULL', (email,))
            if cur.fetchone()[0] >= CONTACT_LIMIT:
                raise HTTPException(status_code=409, detail=f'最多挂念 {CONTACT_LIMIT} 位朋友，先专注为他们祷告吧')
            cur.execute(
                'INSERT INTO evangelism_contacts (owner_email, display_name, notes) VALUES (%s,%s,%s) RETURNING id',
                (email, _sanitize_text(payload.display_name.strip()), _sanitize_text(payload.notes.strip()))
            )
            cid = cur.fetchone()[0]
            conn.commit()
    finally:
        _release_db(conn)
    return {'ok': True, 'id': cid}


@router.put('/api/evangelism/contacts/{contact_id}')
def update_evangelism_contact(contact_id: int, payload: ContactUpdateRequest, request: Request) -> dict:
    email = _require_email(request)
    if payload.stage is not None and payload.stage not in CONTACT_STAGES:
        raise HTTPException(status_code=422, detail='invalid stage')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            _own_contact(cur, contact_id, email)
            sets, params = [], []
            if payload.display_name is not None:
                sets.append('display_name=%s'); params.append(_sanitize_text(payload.display_name.strip()))
            if payload.notes is not None:
                sets.append('notes=%s'); params.append(_sanitize_text(payload.notes.strip()))
            if payload.stage is not None:
                sets.append('stage=%s'); params.append(payload.stage)
            if not sets:
                return {'ok': True}
            sets.append('updated_at=NOW()')
            params.extend([contact_id, email])
            cur.execute(f"UPDATE evangelism_contacts SET {', '.join(sets)} WHERE id=%s AND owner_email=%s", params)
            conn.commit()
    finally:
        _release_db(conn)
    return {'ok': True}


@router.delete('/api/evangelism/contacts/{contact_id}')
def delete_evangelism_contact(contact_id: int, request: Request) -> dict:
    email = _require_email(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            _own_contact(cur, contact_id, email)
            cur.execute('UPDATE evangelism_contacts SET deleted_at=NOW() WHERE id=%s AND owner_email=%s', (contact_id, email))
            conn.commit()
    finally:
        _release_db(conn)
    return {'ok': True}


@router.post('/api/evangelism/contacts/{contact_id}/pray')
def pray_for_evangelism_contact(contact_id: int, request: Request) -> dict:
    """今日代祷打卡（幂等）。"""
    email = _require_email(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            _own_contact(cur, contact_id, email)
            cur.execute(
                'INSERT INTO evangelism_prayer_logs (contact_id, owner_email) VALUES (%s,%s) '
                'ON CONFLICT (contact_id, prayed_on) DO NOTHING',
                (contact_id, email)
            )
            conn.commit()
    finally:
        _release_db(conn)
    return {'ok': True}


@router.post('/api/evangelism/{prayer_id}/amen')
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


@router.put('/api/evangelism/{prayer_id}')
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


@router.delete('/api/evangelism/{prayer_id}')
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


@router.post('/api/evangelism/{prayer_id}/restore')
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
