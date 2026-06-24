"""daily_soul_question router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()

# Dependencies injected from main at startup:
_award_milestone_if_due = None
_get_db = None
_get_session_user = None
_release_db = None
_sanitize_text = None

def init_daily_soul_question_router(**deps):
    globals().update(deps)

@router.get('/api/daily-soul-question')
async def get_daily_soul_question(request: Request) -> dict:
    """Generate today's personalized soul question based on SFDS trajectory."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    today = __import__('datetime').date.today().isoformat()
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check if already answered today
            cur.execute('SELECT question, answer FROM daily_soul_answers WHERE email=%s AND answer_date=%s', (email, today))
            existing = cur.fetchone()
            if existing:
                return {'ok': True, 'question': existing[0], 'answer': existing[1], 'already_answered': True, 'date': today}

            # Get SFDS trajectory for personalized question.
            # sfds_sessions is optional (legacy / not always migrated); degrade
            # gracefully instead of 500ing when the table is absent.
            trajectory = 'unknown'
            dominant_loop = ''
            try:
                cur.execute("SELECT trajectory_direction, dominant_loop FROM sfds_sessions WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (email,))
                sfds_row = cur.fetchone()
                if sfds_row:
                    trajectory = sfds_row[0] or 'unknown'
                    dominant_loop = sfds_row[1] or ''
            except Exception:
                conn.rollback()

            # Get last checkin emotion
            cur.execute("SELECT data FROM user_checkins WHERE email=%s ORDER BY checkin_at DESC LIMIT 1", (email,))
            ck = cur.fetchone()
            last_emotion = ''
            if ck:
                import json as _j
                d = _j.loads(ck[0]) if isinstance(ck[0], str) else ck[0]
                last_emotion = d.get('emotionLabel') or ''
    finally:
        _release_db(conn)

    # Build personalized prompt
    _LOOP_QUESTION_HINTS = {
        'fear_control_loop': '控制与信任、恐惧与交托',
        'shame_avoidance_loop': '羞耻与恩典、逃避与面对',
        'pride_comparison_loop': '骄傲与谦卑、比较与身份认同',
        'desire_impulse_loop': '欲望与节制、冲动与等候神',
        'truth_stability_loop': '真理与稳固、反思与成长',
    }
    hint = _LOOP_QUESTION_HINTS.get(dominant_loop or '', '属灵成长与信心')
    traj_note = {'fragmenting': '正在挣扎、内心破碎', 'stabilizing': '走向稳定、渴望成长', 'improving_clarity': '属灵清晰度提升'}.get(trajectory or '', '属灵操练')
    emotion_note = f'近期情绪：{last_emotion}。' if last_emotion else ''
    today_weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][__import__('datetime').date.today().weekday()]

    system = '你是一位牧者，用简短、直击灵魂的问题帮助基督徒深度自我省察。问题要具体、诚实、不说教、不给答案。中文，20字以内。'
    prompt = f'今天是{today_weekday}。{emotion_note}用户灵命轨迹：{traj_note}，核心课题：{hint}。请生成一个今日专属的灵魂自省问题（不超过25字，不含问候语）：'

    question = ''
    try:
        from query_emotion_verses import _call_llm_with_fallback
        question = _call_llm_with_fallback(
            system_prompt=system,
            user_message=prompt,
            max_tokens=60,
            temperature=0.85,
            tag='soul_question',
        ).strip()
    except Exception:
        pass

    if not question:
        # Fallback static questions per loop
        _FALLBACK = {
            'fear_control_loop': '今天，有什么事情你还没有真正交给神？',
            'shame_avoidance_loop': '今天，你在逃避面对什么？',
            'pride_comparison_loop': '今天，你的价值感来自神还是别人的眼光？',
            'desire_impulse_loop': '今天，你的哪个渴望需要在神面前安静等候？',
            'truth_stability_loop': '今天，神在你生命中哪一处最忠诚地工作？',
        }
        question = _FALLBACK.get(dominant_loop or '', '今天，你最需要在哪里更加诚实地面对自己？')

    # Store question (without answer yet)
    conn2 = _get_db()
    try:
        with conn2.cursor() as cur:
            cur.execute(
                'INSERT INTO daily_soul_answers (email, answer_date, question, dominant_loop, trajectory) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (email, answer_date) DO NOTHING',
                (email, today, question, dominant_loop or '', trajectory or '')
            )
            conn2.commit()
    finally:
        _release_db(conn2)

    return {'ok': True, 'question': question, 'already_answered': False, 'date': today, 'dominant_loop': dominant_loop, 'trajectory': trajectory}


@router.post('/api/daily-soul-question/answer')
async def save_soul_answer(request: Request) -> dict:
    """Save the user's answer to today's soul question."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid JSON')
    answer = _sanitize_text(body.get('answer', '').strip())
    save_to_journal = bool(body.get('save_to_journal', False))
    if not answer:
        raise HTTPException(status_code=400, detail='Answer required')
    today = __import__('datetime').date.today().isoformat()
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE daily_soul_answers SET answer=%s, saved_to_journal=%s WHERE email=%s AND answer_date=%s',
                (answer, save_to_journal, email, today)
            )
            if save_to_journal:
                cur.execute('SELECT question FROM daily_soul_answers WHERE email=%s AND answer_date=%s', (email, today))
                row = cur.fetchone()
                question = row[0] if row else '今日灵魂一问'
                cur.execute('SELECT id FROM devotion_journals WHERE email=%s AND journal_date=%s', (email, today))
                existing = cur.fetchone()
                if existing:
                    cur.execute('UPDATE devotion_journals SET reflection=reflection||%s, updated_at=NOW() WHERE id=%s',
                        (f'\n\n【灵魂一问】{question}\n{answer}', existing[0]))
                else:
                    cur.execute(
                        'INSERT INTO devotion_journals (email, journal_date, title, reflection) VALUES (%s,%s,%s,%s)',
                        (email, today, f'{today} 灵魂省察', f'【灵魂一问】{question}\n{answer}')
                    )
            conn.commit()
        # Check milestones
        _award_milestone_if_due(email, conn)
    finally:
        _release_db(conn)
    return {'ok': True}


@router.get('/api/daily-soul-question/history')
def get_soul_question_history(request: Request, limit: int = Query(default=30, ge=1, le=90)) -> dict:
    """Return past soul Q&A entries for the user."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT answer_date, question, answer, dominant_loop, trajectory, saved_to_journal FROM daily_soul_answers WHERE email=%s AND answer != \'\' ORDER BY answer_date DESC LIMIT %s',
                (email, limit)
            )
            rows = cur.fetchall()
        items = [{'date': str(r[0]), 'question': r[1], 'answer': r[2], 'dominant_loop': r[3], 'trajectory': r[4], 'saved_to_journal': r[5]} for r in rows]
        return {'ok': True, 'items': items}
    finally:
        _release_db(conn)
