"""recycle_bin router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_is_admin = None
_release_db = None
_to_shanghai_iso = None

def init_recycle_bin_router(**deps):
    globals().update(deps)

@router.get('/api/recycle-bin')
def get_recycle_bin(request: Request) -> dict:
    """List all soft-deleted items for the current user across all tables. Auto-purge items >30 days."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']
    print(f'[recycle] list email={email}', flush=True)
    try:
        conn = _get_db()
    except Exception as db_exc:
        print(f'[recycle] database connection failed: {db_exc}', flush=True)
        raise HTTPException(status_code=503, detail='Database connection failed') from db_exc
    try:
        with conn.cursor() as cur:
            # Auto-purge items deleted > 30 days ago
            cutoff = "NOW() - INTERVAL '30 days'"
            cur.execute(f'DELETE FROM prayers WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM evangelism_prayers WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM devotion_journals WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM personal_notes WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            cur.execute(f'DELETE FROM sermon_journals WHERE email=%s AND deleted_at IS NOT NULL AND deleted_at < {cutoff}', (email,))
            conn.commit()

            items = []

            # Prayers
            cur.execute(
                'SELECT id, content, nickname, deleted_at FROM prayers WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'prayer', 'type_label': '代祷', 'id': r[0], 'title': (r[1] or '')[:60], 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Evangelism
            cur.execute(
                'SELECT id, content, nickname, deleted_at FROM evangelism_prayers WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'evangelism', 'type_label': '传FY', 'id': r[0], 'title': (r[1] or '')[:60], 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Devotion journals
            cur.execute(
                'SELECT id, title, scripture, deleted_at FROM devotion_journals WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'devotion', 'type_label': '灵修日记', 'id': r[0], 'title': r[1] or r[2] or '(无标题)', 'subtitle': '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Personal notes
            cur.execute(
                'SELECT id, scripture, mood, deleted_at FROM personal_notes WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'personal', 'type_label': '我的日记', 'id': r[0], 'title': r[1] or '(无经文)', 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

            # Sermon journals
            cur.execute(
                'SELECT id, title, preacher, deleted_at FROM sermon_journals WHERE email=%s AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
                (email,)
            )
            for r in cur.fetchall():
                items.append({'type': 'sermon', 'type_label': '主日信息', 'id': r[0], 'title': r[1] or '(无标题)', 'subtitle': r[2] or '', 'deleted_at': _to_shanghai_iso(r[3])})

        # Sort all by deleted_at desc
        items.sort(key=lambda x: x['deleted_at'] or '', reverse=True)
        print(f'[recycle] returning {len(items)} items', flush=True)
        return {'ok': True, 'items': items}
    except Exception as exc:
        print(f'[recycle] query error: {exc}', flush=True)
        raise HTTPException(status_code=500, detail=f'Recycle bin query failed: {exc}') from exc
    finally:
        _release_db(conn)


@router.post('/api/recycle-bin/{item_type}/{item_id}/restore')
def restore_recycle_item(item_type: str, item_id: str, request: Request) -> dict:
    """Restore a soft-deleted item. Owner can restore their own items."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Login required')
    email = user['email']

    table_map = {
        'prayer': 'prayers',
        'evangelism': 'evangelism_prayers',
        'devotion': 'devotion_journals',
        'personal': 'personal_notes',
        'sermon': 'sermon_journals',
    }
    table = table_map.get(item_type)
    if not table:
        raise HTTPException(status_code=400, detail=f'Unknown type: {item_type}')

    print(f'[recycle] restore type={item_type} id={item_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f'SELECT email, deleted_at FROM {table} WHERE id=%s', (item_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Item not found')
            owner_email, deleted_at = row
            if not deleted_at:
                raise HTTPException(status_code=400, detail='Item is not deleted')
            if owner_email != email and not _is_admin(email):
                raise HTTPException(status_code=403, detail='Not authorized')
            cur.execute(f'UPDATE {table} SET deleted_at=NULL WHERE id=%s', (item_id,))
            conn.commit()
        print(f'[recycle] restored type={item_type} id={item_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


# ── end Recycle Bin ──────────────────────────────────────────
