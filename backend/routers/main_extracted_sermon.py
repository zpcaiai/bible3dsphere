"""Sermon Journal (主日信息) routes — 从 main.py 逐字搬移（路径不变，无 prefix）。

对 main.py 内部辅助函数的依赖通过 init_main_extracted_sermon() 在
include_router 之前注入，本模块与 main 没有 import 期耦合。
"""
import json
import time

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
        items = [_row_to_sermon(r) for r in rows]
        print(f'[sermon] list ok {len(items)}/{total} in {(time.time()-t0)*1000:.0f}ms', flush=True)
        return {'ok': True, 'items': items, 'total': total, 'is_admin': is_admin}
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
        if not row:
            raise HTTPException(status_code=404, detail='Journal not found')
        return {'ok': True, 'journal': _row_to_sermon(row), 'is_admin': is_admin}
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
