"""bible_reading router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_release_db = None
_sanitize_text = None

def init_bible_reading_router(**deps):
    globals().update(deps)

@router.post('/api/bible-reading/mark')
async def mark_chapter_read(request: Request) -> dict:
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid JSON')
    book = _sanitize_text(body.get('book', '').strip())
    chapter = int(body.get('chapter', 0))
    highlight = _sanitize_text(body.get('highlight', '').strip())
    plan_id = body.get('plan_id', '1year')
    if not book or not chapter:
        raise HTTPException(status_code=400, detail='book and chapter required')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO bible_reading_progress (email, book, chapter, highlight, plan_id) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (email, book, chapter) DO UPDATE SET highlight=%s, read_at=NOW()',
                (email, book, chapter, highlight, plan_id, highlight)
            )
            conn.commit()
            try:
                import formation_events as _fe
                _fe.record_event(email, "bible_reading", "reading", domain=book,
                                 title="读经：%s%d" % (book, chapter),
                                 summary=(highlight or "")[:120] or None, severity="green",
                                 ref_id="read:%s:%d" % (book, chapter))
            except Exception:
                pass
            # Check if whole book done
            _BOOK_CHAPTERS = {
                '创世记': 50,'出埃及记': 40,'利未记': 27,'民数记': 36,'申命记': 34,
                '约书亚记': 24,'士师记': 21,'路得记': 4,'撒母耳记上': 31,'撒母耳记下': 24,
                '列王纪上': 22,'列王纪下': 25,'诗篇': 150,'箴言': 31,'传道书': 12,
                '以赛亚书': 66,'耶利米书': 52,'以西结书': 48,'但以理书': 12,
                '马太福音': 28,'马可福音': 16,'路加福音': 24,'约翰福音': 21,
                '使徒行传': 28,'罗马书': 16,'哥林多前书': 16,'哥林多后书': 13,
                '加拉太书': 6,'以弗所书': 6,'腓立比书': 4,'歌罗西书': 4,
                '帖撒罗尼迦前书': 5,'帖撒罗尼迦后书': 3,'提摩太前书': 6,'提摩太后书': 4,
                '提多书': 3,'腓利门书': 1,'希伯来书': 13,'雅各书': 5,
                '彼得前书': 5,'彼得后书': 3,'约翰一书': 5,'约翰二书': 1,'约翰三书': 1,
                '犹大书': 1,'启示录': 22,
            }
            total_chapters = _BOOK_CHAPTERS.get(book, 0)
            if total_chapters:
                cur.execute("SELECT COUNT(*) FROM bible_reading_progress WHERE email=%s AND book=%s", (email, book))
                done = cur.fetchone()[0]
                if done >= total_chapters:
                    cur.execute("INSERT INTO milestone_events (email, badge_key) VALUES (%s,%s) ON CONFLICT DO NOTHING", (email, f'bible_book_{book[:6]}'))
                    conn.commit()
                    return {'ok': True, 'book_completed': True, 'book': book}
        return {'ok': True, 'book_completed': False}
    finally:
        _release_db(conn)


@router.get('/api/bible-reading/progress')
def get_reading_progress(request: Request) -> dict:
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT book, chapter, highlight, read_at FROM bible_reading_progress WHERE email=%s ORDER BY read_at DESC", (email,))
            rows = cur.fetchall()
        items = [{'book': r[0], 'chapter': r[1], 'highlight': r[2], 'read_at': str(r[3])[:10]} for r in rows]
        # Group by book
        from collections import defaultdict
        by_book = defaultdict(list)
        for it in items:
            by_book[it['book']].append(it['chapter'])
        return {'ok': True, 'items': items, 'by_book': dict(by_book)}
    finally:
        _release_db(conn)
