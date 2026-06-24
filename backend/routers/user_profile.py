"""user_profile router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_release_db = None
_sanitize_text = None

def init_user_profile_router(**deps):
    globals().update(deps)

class UserUpdateRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    avatar: str = Field(default='', max_length=500)


@router.put('/api/user/profile')
def update_user_profile(payload: UserUpdateRequest, request: Request) -> dict:
    """Update current user profile (nickname, avatar)."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')

    s_nickname = _sanitize_text(payload.nickname)
    print(f'[user] update profile email={email} nickname={s_nickname}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET nickname = %s, avatar = %s WHERE LOWER(email) = LOWER(%s)',
                (s_nickname, payload.avatar, email)
            )
            conn.commit()
        print(f'[user] profile updated email={email}', flush=True)
        return {'ok': True, 'nickname': s_nickname, 'avatar': payload.avatar}
    finally:
        _release_db(conn)


@router.get('/api/daily-snapshot')
def get_daily_snapshot(request: Request) -> dict:
    """Return a lightweight daily spiritual snapshot for the logged-in user."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    today = __import__('datetime').date.today().isoformat()
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Last checkin
            cur.execute(
                "SELECT data, checkin_at FROM user_checkins WHERE email=%s ORDER BY checkin_at DESC LIMIT 1",
                (email,)
            )
            row = cur.fetchone()
            last_checkin = None
            last_emotion = None
            if row:
                import json as _j
                d = _j.loads(row[0]) if isinstance(row[0], str) else row[0]
                last_emotion = d.get('emotionLabel') or d.get('emotion_label') or ''
                last_checkin = str(row[1])[:10] if row[1] else None

            # Today devotion
            cur.execute(
                "SELECT id FROM devotion_journals WHERE email=%s AND journal_date=%s AND deleted_at IS NULL",
                (email, today)
            )
            has_devotion_today = cur.fetchone() is not None

            # SFDS trajectory
            trajectory = None
            dominant_loop = None
            try:
                cur.execute(
                    "SELECT trajectory_direction, dominant_loop FROM sfds_sessions WHERE user_id=%s ORDER BY created_at DESC LIMIT 1",
                    (user.get('id'),)
                )
                sfds_row = cur.fetchone()
                if sfds_row:
                    trajectory = sfds_row[0]
                    dominant_loop = sfds_row[1]
            except Exception:
                conn.rollback()

            # Pending prayer count (authored by user, not answered)
            cur.execute(
                "SELECT COUNT(*) FROM prayers WHERE email=%s AND deleted_at IS NULL AND status IS DISTINCT FROM 'answered'",
                (email,)
            )
            pending_prayers = cur.fetchone()[0]

        _TRAJECTORY_LABELS = {
            'stabilizing': ('🌱', '稳定成长中'),
            'improving_clarity': ('✨', '属灵清晰度提升'),
            'fragmenting': ('🌊', '内心正在挣扎'),
            'increasing_volatility': ('⚡', '情绪波动较大'),
            'cyclical': ('🔄', '循环模式中'),
        }
        traj_icon, traj_label = _TRAJECTORY_LABELS.get(trajectory or '', ('🔮', ''))

        return {
            'ok': True,
            'today': today,
            'last_emotion': last_emotion,
            'last_checkin': last_checkin,
            'has_devotion_today': has_devotion_today,
            'trajectory': trajectory,
            'trajectory_icon': traj_icon,
            'trajectory_label': traj_label,
            'dominant_loop': dominant_loop,
            'pending_prayers': pending_prayers,
        }
    finally:
        _release_db(conn)
