"""emotion_trajectory router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_release_db = None
_to_shanghai_iso = None

def init_emotion_trajectory_router(**deps):
    globals().update(deps)

@router.get('/api/user/emotion-trajectory')
def get_emotion_trajectory(request: Request, limit: int = Query(default=30, ge=1, le=120)) -> dict:
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    email = user['email']
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT checkin_at, data, emotion_label, mood
                FROM user_checkins
                WHERE email=%s
                ORDER BY checkin_at DESC
                LIMIT %s
                ''',
                (email, limit),
            )
            rows = cur.fetchall()
    finally:
        _release_db(conn)

    items = []
    emotion_counts: dict[str, int] = {}
    mood_counts: dict[str, int] = {}
    for checkin_at, raw_data, emotion_label, mood in rows:
        data = raw_data or {}
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        label = emotion_label or data.get('emotionLabel') or data.get('emotion_label') or ''
        mood_value = mood or data.get('mood') or ''
        scenario = data.get('scenarioDetail') or data.get('scenarioCategory') or ''
        driver = data.get('driverOption') or data.get('driverType') or ''
        if label:
            emotion_counts[label] = emotion_counts.get(label, 0) + 1
        if mood_value:
            mood_counts[mood_value] = mood_counts.get(mood_value, 0) + 1
        items.append({
            'date': _to_shanghai_iso(checkin_at),
            'emotion_label': label,
            'mood': mood_value,
            'scenario': scenario,
            'driver': driver,
        })

    dominant_emotion = max(emotion_counts.items(), key=lambda item: item[1])[0] if emotion_counts else ''
    dominant_mood = max(mood_counts.items(), key=lambda item: item[1])[0] if mood_counts else ''
    return {
        'ok': True,
        'count': len(items),
        'dominant_emotion': dominant_emotion,
        'dominant_mood': dominant_mood,
        'emotion_counts': emotion_counts,
        'mood_counts': mood_counts,
        'items': list(reversed(items)),
    }
