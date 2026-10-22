"""Sermon Journal (主日信息) routes — 从 main.py 逐字搬移（路径不变，无 prefix）。

对 main.py 内部辅助函数的依赖通过 init_main_extracted_sermon() 在
include_router 之前注入，本模块与 main 没有 import 期耦合。
"""
import json
import time
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

try:
    from backend.core.security import sanitize_text as _sanitize_text
except ImportError:
    from core.security import sanitize_text as _sanitize_text

router = APIRouter()

# ── main.py 注入的依赖（导入期为 None，仅在请求期被调用）──
_get_db = None
_release_db = None
_get_session_user = None
_is_admin = None
_to_shanghai_iso = None


def init_main_extracted_sermon(*, get_db, release_db, get_session_user, is_admin, to_shanghai_iso) -> None:
    global _get_db, _release_db, _get_session_user, _is_admin, _to_shanghai_iso
    _get_db = get_db
    _release_db = release_db
    _get_session_user = get_session_user
    _is_admin = is_admin
    _to_shanghai_iso = to_shanghai_iso


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
    create_only: bool = False
    expected_id: int | None = Field(default=None, ge=1)
    expected_updated_at: str | None = Field(default=None, max_length=100)

    @field_validator('questions', 'practices')
    @classmethod
    def validate_list_items(cls, v):
        """Ensure list items are strings with reasonable length."""
        return [str(item)[:2000] for item in v[:20]]


class SermonShareRequest(BaseModel):
    shared: bool


def _row_to_sermon(row, shared=False) -> dict:
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
        # This is an optimistic-write token, not a minute-rounded display label.
        'updated_at': row[16].isoformat() if row[16] else None,
        'shared': shared,
    }


def _shared_ids(cur, ids):
    if not ids:
        return set()
    cur.execute('SELECT source_sermon_id FROM personal_notes WHERE source_sermon_id = ANY(%s) AND shared=TRUE AND deleted_at IS NULL', (ids,))
    return {row[0] for row in cur.fetchall()}


def _projection_text(journal):
    sections = []
    for field, label in [('date', '讲道日期'), ('title', '标题'), ('preacher', '讲员'),
                         ('summary', '摘要'), ('questions', '引导问题'),
                         ('bible_study', '查经'), ('practices', '本周实践'),
                         ('reflection', '反思'), ('lesson', '领受'),
                         ('encouragement', '勉励'), ('conclusion', '结语')]:
        value = journal[field]
        if isinstance(value, list):
            value = '\n'.join(value)
        if value:
            sections.append(f'{label}：{value}')
    return '\n\n'.join(sections)


@router.get('/api/sermon/journals')
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
            shared_ids = _shared_ids(cur, [row[0] for row in rows])
        items = [_row_to_sermon(r, r[0] in shared_ids) for r in rows]
        print(f'[sermon] list ok {len(items)}/{total} in {(time.time()-t0)*1000:.0f}ms', flush=True)
        return {'ok': True, 'items': items, 'total': total, 'is_admin': is_admin,
                'share_state_supported': True,
                'write_guards': {'create_only': True, 'identity': True, 'updated_at': True}}
    finally:
        _release_db(conn)


@router.post('/api/sermon/journals')
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
            # Serialize the owner/date key even before an entry exists. This
            # also makes concurrent create-only requests deterministic.
            cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                        (json.dumps([email, payload.date], ensure_ascii=False),))
            cur.execute(
                'SELECT id, deleted_at, updated_at FROM sermon_journals WHERE email=%s AND sermon_date=%s FOR UPDATE', (email, payload.date)
            )
            existing = cur.fetchone()
            if existing and existing[1] is not None:
                raise HTTPException(status_code=409, detail='This date belongs to a deleted journal; restore it before editing')
            if payload.create_only and existing:
                raise HTTPException(status_code=409, detail='A journal already exists for this date; open it for editing')
            if payload.expected_id is not None and (not existing or existing[0] != payload.expected_id):
                raise HTTPException(status_code=409, detail='Journal identity changed; reload before saving')
            if payload.expected_updated_at is not None and (
                not existing or existing[2] is None or existing[2].isoformat() != payload.expected_updated_at
            ):
                raise HTTPException(status_code=409, detail='Journal changed since it was opened; reload before saving')
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
            cur.execute('SELECT id, email, sermon_date, title, preacher, scripture, summary, questions, bible_study, practices, reflection, lesson, conclusion, encouragement, phase, created_at, updated_at FROM sermon_journals WHERE id=%s', (journal_id,))
            row = cur.fetchone()
            journal = _row_to_sermon(row, journal_id in _shared_ids(cur, [journal_id]))
            cur.execute('UPDATE personal_notes SET scripture=%s, observation=%s, updated_at=NOW() WHERE source_sermon_id=%s',
                        (journal['scripture'], _projection_text(journal), journal_id))
            conn.commit()
        return {'ok': True, 'journal': journal}
    except BaseException:
        conn.rollback()
        raise
    finally:
        _release_db(conn)


@router.get('/api/sermon/journals/{journal_id}')
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
            shared = journal_id in _shared_ids(cur, [journal_id])
        if not row:
            raise HTTPException(status_code=404, detail='Journal not found')
        return {'ok': True, 'journal': _row_to_sermon(row, shared), 'is_admin': is_admin}
    finally:
        _release_db(conn)


@router.delete('/api/sermon/journals/{journal_id}')
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
            cur.execute('SELECT deleted_at FROM sermon_journals WHERE id=%s FOR UPDATE', (journal_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Journal not found')
            if row[0]:
                raise HTTPException(status_code=404, detail='Journal not found')
            # Soft delete
            cur.execute('UPDATE sermon_journals SET deleted_at = NOW() WHERE id=%s', (journal_id,))
            cur.execute('UPDATE personal_notes SET shared=FALSE, shared_at=NULL, deleted_at=NOW(), updated_at=NOW() WHERE source_sermon_id=%s', (journal_id,))
            conn.commit()
        print(f'[sermon] soft deleted id={journal_id}', flush=True)
        return {'ok': True}
    except BaseException:
        conn.rollback()
        raise
    finally:
        _release_db(conn)


@router.post('/api/sermon/journals/{journal_id}/share')
def toggle_share_sermon(journal_id: int, request: Request, payload: SermonShareRequest | None = None) -> dict:
    """Publish/withdraw the owner's canonical sermon on the shared-note wall.

    Locking the source serializes toggles, edits and deletion. The projection
    and source always commit together; sharing never exposes an email address.
    """
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, email, sermon_date, title, preacher, scripture, summary, questions, bible_study, practices, reflection, lesson, conclusion, encouragement, phase, created_at, updated_at FROM sermon_journals WHERE id=%s AND deleted_at IS NULL FOR UPDATE', (journal_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Journal not found')
            if row[1] != user['email']:
                raise HTTPException(status_code=403, detail='Only the creator can share/unshare')
            journal = _row_to_sermon(row)
            shared = payload.shared if payload is not None else journal_id not in _shared_ids(cur, [journal_id])
            author = _sanitize_text(str(user.get('nickname') or '讲道分享'))[:100]
            cur.execute('''INSERT INTO personal_notes
                           (id,email,note_date,scripture,observation,shared,author,source_sermon_id,shared_at)
                           VALUES (%s,%s,CURRENT_DATE,%s,%s,%s,%s,%s,CASE WHEN %s THEN NOW() ELSE NULL END)
                           ON CONFLICT(source_sermon_id) DO UPDATE SET
                           scripture=EXCLUDED.scripture, observation=EXCLUDED.observation,
                           shared=EXCLUDED.shared, author=EXCLUDED.author,
                           shared_at=EXCLUDED.shared_at, deleted_at=NULL, updated_at=NOW()''',
                        (str(uuid.uuid4()), row[1], journal['scripture'], _projection_text(journal),
                         shared, author, journal_id, shared))
            conn.commit()
        return {'ok': True, 'shared': shared}
    except BaseException:
        conn.rollback()
        raise
    finally:
        _release_db(conn)
