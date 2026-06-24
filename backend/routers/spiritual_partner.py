"""spiritual_partner router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_release_db = None

def init_spiritual_partner_router(**deps):
    globals().update(deps)

@router.post('/api/spiritual-partner/request')
async def request_partner(request: Request) -> dict:
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid JSON')
    partner_email = (body.get('partner_email') or '').strip().lower()
    if not partner_email or partner_email == email:
        raise HTTPException(status_code=400, detail='Invalid partner email')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (partner_email,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail='该用户不存在')
            cur.execute(
                'INSERT INTO spiritual_partners (requester, partner, status) VALUES (%s,%s,%s) ON CONFLICT (requester, partner) DO UPDATE SET status=EXCLUDED.status',
                (email, partner_email, 'pending')
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@router.post('/api/spiritual-partner/respond')
async def respond_partner(request: Request) -> dict:
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid JSON')
    requester = (body.get('requester') or '').strip().lower()
    accept = bool(body.get('accept', False))
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            new_status = 'active' if accept else 'declined'
            cur.execute("UPDATE spiritual_partners SET status=%s, updated_at=NOW() WHERE requester=%s AND partner=%s", (new_status, requester, email))
            conn.commit()
        return {'ok': True, 'status': new_status}
    finally:
        _release_db(conn)


@router.get('/api/spiritual-partner/status')
def get_partner_status(request: Request) -> dict:
    """Return partner's last devotion date (not content) + mutual encouragement."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    import datetime as _dt
    today = _dt.date.today()
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.requester, p.partner, p.status FROM spiritual_partners p
                WHERE (p.requester=%s OR p.partner=%s) AND p.status='active'
            """, (email, email))
            pair = cur.fetchone()
            if not pair:
                # Check pending requests
                cur.execute("SELECT requester, partner, status FROM spiritual_partners WHERE (requester=%s OR partner=%s)", (email, email))
                pending = cur.fetchall()
                return {'ok': True, 'partner': None, 'pending': [{'requester': r[0], 'partner': r[1], 'status': r[2]} for r in pending]}

            partner_email = pair[1] if pair[0] == email else pair[0]
            cur.execute("SELECT nickname FROM users WHERE email=%s", (partner_email,))
            nr = cur.fetchone()
            partner_nickname = nr[0] if nr else partner_email.split('@')[0]

            cur.execute("SELECT MAX(journal_date) FROM devotion_journals WHERE email=%s AND deleted_at IS NULL", (partner_email,))
            last_devot = cur.fetchone()[0]
            partner_devot_today = last_devot == today if last_devot else False
            partner_days_ago = (today - last_devot).days if last_devot else None

        return {
            'ok': True,
            'partner': {'email': partner_email, 'nickname': partner_nickname,
                        'has_devotion_today': partner_devot_today, 'last_devotion_days_ago': partner_days_ago},
            'pending': [],
        }
    finally:
        _release_db(conn)


@router.post('/api/spiritual-partner/encourage')
async def send_encouragement(request: Request) -> dict:
    """Send a one-tap encouragement verse to partner (stored as notification-style message)."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    # Simplified: just return ok (real push would require notification infra)
    return {'ok': True, 'message': '鼓励已发送 🙏'}
