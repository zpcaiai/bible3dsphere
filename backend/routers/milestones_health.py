"""milestones_health router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_release_db = None

def init_milestones_health_router(**deps):
    globals().update(deps)

@router.get('/api/milestones')
def get_milestones(request: Request) -> dict:
    """Return all earned milestones for the user."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT badge_key, earned_at FROM milestone_events WHERE email=%s ORDER BY earned_at DESC", (email,))
            rows = cur.fetchall()
        _BADGE_META = {
            'devotion_streak_7':  ('🌿', '旷野七日',    '连续7天灵修，你已走过旷野'),
            'devotion_streak_30': ('🕯️', '月光守望',   '连续30天灵修，如月光常照'),
            'prayer_wall_10':     ('🙏', '守望者',       '已提交10条代祷，成为他人的守望'),
            'prayer_answered_3':  ('✝️', '信心见证者',  '3个祷告已蒙恩答应，你的信心日历有了见证'),
            'soul_q_7':           ('🔍', '七日自省者',   '已回答7次灵魂一问，诚实面对自己'),
            'soul_q_30':          ('💎', '月月省察',     '坚持30次灵魂省察，生命持续更新'),
            'bible_book_done':    ('📖', '书卷完成者',   '读完整卷圣经，遇见神的完整话语'),
        }
        items = []
        for badge_key, earned_at in rows:
            meta = _BADGE_META.get(badge_key, ('🏅', badge_key, ''))
            items.append({'key': badge_key, 'icon': meta[0], 'name': meta[1], 'desc': meta[2], 'earned_at': str(earned_at)[:10]})
        return {'ok': True, 'items': items}
    finally:
        _release_db(conn)


@router.get('/api/spiritual-health-check')
def get_spiritual_health_check(request: Request) -> dict:
    """A3: Check for regression signals and return care message if needed."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    import datetime as _dt
    today = _dt.date.today()
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Days since last devotion
            cur.execute("SELECT MAX(journal_date) FROM devotion_journals WHERE email=%s AND deleted_at IS NULL", (email,))
            last_devot = cur.fetchone()[0]
            days_no_devot = (today - last_devot).days if last_devot else 999

            # Days since last checkin
            cur.execute("SELECT MAX(checkin_at::date) FROM user_checkins WHERE email=%s", (email,))
            last_ck = cur.fetchone()[0]
            days_no_checkin = (today - last_ck).days if last_ck else 999

            # Recent trajectory (sfds_sessions may not exist in all deployments)
            recent_trajs = []
            try:
                cur.execute("SELECT trajectory_direction FROM sfds_sessions WHERE user_id=%s ORDER BY created_at DESC LIMIT 3", (email,))
                recent_trajs = [r[0] for r in cur.fetchall()]
            except Exception:
                conn.rollback()  # clear aborted txn so the pooled connection stays usable
            fragmenting_count = sum(1 for t in recent_trajs if t == 'fragmenting')

        alert_level = None
        message = None
        verse = None

        if days_no_devot >= 5 or days_no_checkin >= 5:
            alert_level = 'gentle'
            message = f'好久不见，不知你最近还好吗？已经 {max(days_no_devot, days_no_checkin)} 天没有在这里停留了。'
            verse = '「我们在患难中，也是欢欢喜喜的；因为知道患难生忍耐，忍耐生老练，老练生盼望。」——罗马书 5:3-4'
        elif fragmenting_count >= 2:
            alert_level = 'care'
            message = '神的眼目看顾你。这段时间内心的挣扎，祂都知道。'
            verse = '「你们要将一切的忧虑卸给神，因为他顾念你们。」——彼得前书 5:7'

        return {
            'ok': True,
            'alert_level': alert_level,
            'message': message,
            'verse': verse,
            'days_no_devotion': days_no_devot,
            'days_no_checkin': days_no_checkin,
            'fragmenting_streak': fragmenting_count,
        }
    finally:
        _release_db(conn)
