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


@router.post('/api/evangelism')
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
