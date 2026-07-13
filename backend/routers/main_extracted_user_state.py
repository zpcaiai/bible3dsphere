"""用户签到 /api/user/checkin、祷告恢复 /api/prayers/{id}/restore、标签画像 /api/user/tags —
从 main.py 逐字搬移（路径不变，无 prefix）。

标签抽取/写入辅助（_extract_tags、_upsert_tags、_get_user_tags）仍定义在 main.py
（/api/chat 的后台标签抽取也在用），通过 init_main_extracted_user_state() 注入引用。
"""
import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

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
_extract_tags = None
_upsert_tags = None
_get_user_tags = None


def init_main_extracted_user_state(*, get_db, release_db, get_session_user, is_admin,
                                   extract_tags, upsert_tags, get_user_tags) -> None:
    global _get_db, _release_db, _get_session_user, _is_admin
    global _extract_tags, _upsert_tags, _get_user_tags
    _get_db = get_db
    _release_db = release_db
    _get_session_user = get_session_user
    _is_admin = is_admin
    _extract_tags = extract_tags
    _upsert_tags = upsert_tags
    _get_user_tags = get_user_tags


class CheckinRequest(BaseModel):
    emotionLabel: str = Field(default='', max_length=64)
    emotionQuery: str = Field(default='', max_length=1000)
    scenarioCategory: str = Field(default='', max_length=64)
    scenarioDetail: str = Field(default='', max_length=128)
    driverType: str = Field(default='', max_length=64)
    driverOption: str = Field(default='', max_length=128)
    mood: str = Field(default='', max_length=16)
    sleep: str = Field(default='', max_length=16)
    energy: str = Field(default='', max_length=16)
    prayerRequest: str = Field(default='', max_length=500)
    gratitude: str = Field(default='', max_length=500)


@router.post('/api/user/checkin')
def post_checkin(payload: CheckinRequest, request: Request) -> dict:
    """Save checkin data and update user tags. Auth optional – tags skipped for guests."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    user_id = user.get('id', email) if user else ''
    print(f'[checkin] received email={email or "guest"} emotion={payload.emotionLabel}', flush=True)
    data = payload.model_dump()
    # Sanitize all string fields in checkin data
    for key in data:
        if isinstance(data[key], str):
            data[key] = _sanitize_text(data[key])

    tags = _extract_tags(data)
    print(f'[checkin] extracted {len(tags)} tags', flush=True)

    if user and email:
        _upsert_tags(email, tags)
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO user_checkins (email, checkin_at, data, emotion_label, mood)
                    VALUES (%s, NOW(), %s, %s, %s)
                    ''',
                    (
                        email,
                        json.dumps(data, ensure_ascii=False),
                        data.get('emotionLabel', ''),
                        data.get('mood', ''),
                    )
                )
                conn.commit()
            print(f'[checkin] saved to db for {email}', flush=True)
        finally:
            _release_db(conn)

        # Record formation event from checkin data
        try:
            import asyncio, uuid as _uuid
            from formation_engine import get_formation_engine
            _DRIVER_TO_PATTERN = {
                'fear': 'fear', 'anxiety': 'fear', 'stress': 'fear',
                'pride': 'pride', 'comparison': 'pride',
                'shame': 'shame', 'guilt': 'shame',
                'desire': 'desire', 'impulse': 'desire',
                'growth': 'growth', 'gratitude': 'growth', 'spiritual': 'spiritual',
                'relational': 'relational', 'relationship': 'relational',
            }
            driver_key = (payload.driverType or '').lower()
            pattern_cats = []
            for k, v in _DRIVER_TO_PATTERN.items():
                if k in driver_key:
                    if v not in pattern_cats:
                        pattern_cats.append(v)
            if not pattern_cats:
                pattern_cats = ['growth']
            mood_intensity = {'high': 8.0, 'medium': 5.0, 'low': 3.0}.get(
                (payload.mood or '').lower(), 5.0
            )
            formation_eng = get_formation_engine()
            session_id = str(_uuid.uuid4())
            insight = formation_eng.analyze_sync(
                user_id=str(user_id),
                pattern_categories=pattern_cats,
                loop_broken=bool(payload.gratitude),
                decision_category='checkin',
                session_id=session_id,
                emotional_intensity=mood_intensity,
                reflection_active=bool(payload.prayerRequest or payload.gratitude),
            )
            dim_deltas = {
                dim: sc.delta
                for dim, sc in insight.current_snapshot.dimensions.items()
            }
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(formation_eng.record_formation_event(
                    user_id=str(user_id),
                    session_id=session_id,
                    pattern_categories=pattern_cats,
                    loop_broken=bool(payload.gratitude),
                    dimension_deltas=dim_deltas,
                    decision_category='checkin',
                ))
            else:
                loop.run_until_complete(formation_eng.record_formation_event(
                    user_id=str(user_id),
                    session_id=session_id,
                    pattern_categories=pattern_cats,
                    loop_broken=bool(payload.gratitude),
                    dimension_deltas=dim_deltas,
                    decision_category='checkin',
                ))
            print(f'[checkin] formation event queued for {user_id}', flush=True)
        except Exception as _fe:
            print(f'[checkin] formation record skipped: {_fe}', flush=True)
    else:
        print('[checkin] guest checkin, tags not persisted', flush=True)

    return {'ok': True, 'tags_extracted': len(tags)}


@router.post('/api/prayers/{prayer_id}/restore')
def restore_prayer(prayer_id: int, request: Request) -> dict:
    """Restore a soft-deleted prayer. Only admin can restore."""
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    if not email:
        raise HTTPException(status_code=401, detail='Login required')
    # Check admin permission
    if not _is_admin(email):
        raise HTTPException(status_code=403, detail='Admin permission required')
    print(f'[prayers] restore id={prayer_id} email={email}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Check if exists and is deleted
            cur.execute('SELECT deleted_at FROM prayers WHERE id = %s', (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Prayer not found')
            if not row[0]:
                raise HTTPException(status_code=400, detail='Prayer is not deleted')
            # Restore (clear deleted_at)
            cur.execute('UPDATE prayers SET deleted_at = NULL WHERE id = %s', (prayer_id,))
            conn.commit()
        print(f'[prayers] restored id={prayer_id}', flush=True)
        return {'ok': True}
    finally:
        _release_db(conn)


@router.get('/api/user/tags')
def get_user_tags(request: Request) -> dict:
    """Return current user's tag profile (for debug/admin use)."""
    user = _get_session_user(request)
    if not user or not user.get('email'):
        raise HTTPException(status_code=401, detail='Not authenticated')
    tags = _get_user_tags(user['email'])
    return {'ok': True, 'tags': tags}
