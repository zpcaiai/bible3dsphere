"""personal_notes router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_release_db = None
_sanitize_text = None
_to_shanghai_iso = None
_validate_date_str = None

def init_personal_notes_router(**deps):
    globals().update(deps)

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
    """row columns: id,email,note_date,scripture,observation,reflection,application,prayer,mood,shared,author,avatar,created_at,updated_at[,shared_at][,amen_count]"""
    d = {
        'id': row[0],
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
    if len(row) > 14:
        d['sharedAt'] = _to_shanghai_iso(row[14])
    if len(row) > 15:
        d['amen_count'] = row[15] or 0
    return d


@router.get('/api/personal/notes')
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


@router.post('/api/personal/notes')
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


@router.delete('/api/personal/notes/{note_id}')
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

@router.get('/api/shared/notes')
def get_shared_notes(request: Request, page: int = 1, limit: int = 20) -> dict:
    """Return shared notes with pagination. email is NOT exposed. Sorted by shared_at DESC."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']
    limit = min(limit, 50)
    offset = (max(page, 1) - 1) * limit
    print(f'[shared] list page={page} limit={limit} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Count total for pagination metadata
            cur.execute('SELECT COUNT(*) FROM personal_notes WHERE shared=TRUE AND deleted_at IS NULL')
            total = cur.fetchone()[0]
            # Fetch page — select email only for is_own check, not returned to client
            # Also LEFT JOIN amen count
            cur.execute(
                '''
                SELECT pn.id, pn.email, pn.note_date, pn.scripture, pn.observation, pn.reflection,
                       pn.application, pn.prayer, pn.mood, pn.shared, pn.author, pn.avatar,
                       pn.created_at, pn.updated_at, pn.shared_at,
                       COALESCE(ni.amen_count, 0) AS amen_count
                FROM personal_notes pn
                LEFT JOIN (
                    SELECT note_id, COUNT(*) AS amen_count
                    FROM note_interactions WHERE action=\'amen\'
                    GROUP BY note_id
                ) ni ON ni.note_id = pn.id
                WHERE pn.shared=TRUE AND pn.deleted_at IS NULL
                ORDER BY pn.shared_at DESC
                LIMIT %s OFFSET %s
                ''',
                (limit, offset)
            )
            rows = cur.fetchall()
            # Check which notes current user has amen-ed
            ids = [r[0] for r in rows]
            amen_by_me = set()
            if ids:
                cur.execute(
                    'SELECT note_id FROM note_interactions WHERE email=%s AND action=\'amen\' AND note_id IN %s',
                    (email, tuple(ids))
                )
                amen_by_me = {r[0] for r in cur.fetchall()}
        items = []
        for r in rows:
            note = _row_to_personal_note(r)
            note['is_own'] = r[1] == email  # use raw email for check then discard
            note['amen_by_me'] = r[0] in amen_by_me
            items.append(note)
        print(f'[shared] returning {len(items)}/{total} items page={page}', flush=True)
        return {'ok': True, 'items': items, 'total': total, 'page': page, 'pages': (total + limit - 1) // limit}
    finally:
        _release_db(conn)


@router.post('/api/personal/notes/{note_id}/share')
def toggle_share_note(note_id: str, request: Request) -> dict:
    """Toggle share status. Sets shared_at when sharing (not updated_at). Only owner can act."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']
    print(f'[shared] toggle share note_id={note_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT email, shared FROM personal_notes WHERE id=%s', (note_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Note not found')
            owner_email, currently_shared = row
            if owner_email != email:
                raise HTTPException(status_code=403, detail='Only the creator can share/unshare')
            new_shared = not currently_shared
            if new_shared:
                # Sharing: write shared_at timestamp, do NOT touch updated_at
                cur.execute(
                    'UPDATE personal_notes SET shared=%s, shared_at=NOW() WHERE id=%s',
                    (True, note_id)
                )
            else:
                # Unsharing: clear shared_at
                cur.execute(
                    'UPDATE personal_notes SET shared=%s, shared_at=NULL WHERE id=%s',
                    (False, note_id)
                )
            conn.commit()
        print(f'[shared] note_id={note_id} shared={new_shared}', flush=True)
        return {'ok': True, 'shared': new_shared}
    finally:
        _release_db(conn)


@router.post('/api/shared/notes/{note_id}/amen')
def amen_shared_note(note_id: str, request: Request) -> dict:
    """Toggle amen on a shared note. Prevents duplicate amens per user."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT shared FROM personal_notes WHERE id=%s AND deleted_at IS NULL', (note_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                raise HTTPException(status_code=404, detail='Note not found or not shared')
            # Check if already amen-ed
            cur.execute(
                "SELECT id FROM note_interactions WHERE note_id=%s AND email=%s AND action='amen'",
                (note_id, email)
            )
            existing = cur.fetchone()
            if existing:
                # Un-amen
                cur.execute(
                    "DELETE FROM note_interactions WHERE note_id=%s AND email=%s AND action='amen'",
                    (note_id, email)
                )
                conn.commit()
                cur.execute("SELECT COUNT(*) FROM note_interactions WHERE note_id=%s AND action='amen'", (note_id,))
                count = cur.fetchone()[0]
                return {'ok': True, 'amen_by_me': False, 'amen_count': count}
            else:
                # Amen
                cur.execute(
                    "INSERT INTO note_interactions (note_id, email, action) VALUES (%s,%s,'amen') ON CONFLICT DO NOTHING",
                    (note_id, email)
                )
                conn.commit()
                cur.execute("SELECT COUNT(*) FROM note_interactions WHERE note_id=%s AND action='amen'", (note_id,))
                count = cur.fetchone()[0]
                return {'ok': True, 'amen_by_me': True, 'amen_count': count}
    finally:
        _release_db(conn)


# ── end Share Wall ───────────────────────────────────────────


# ── Recycle Bin (回收站) ─────────────────────────────────────
