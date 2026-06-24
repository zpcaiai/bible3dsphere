"""reflection router — extracted from main.py (deps injected at init)."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# Dependencies injected from main at startup:
_get_db = None
_get_session_user = None
_release_db = None

def init_reflection_router(**deps):
    globals().update(deps)

@router.post('/api/reflection/save')
async def save_reflection(request: Request):
    """保存用户反思问卷答案（UPSERT）"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='无效请求体')
    answers = body.get('answers', {})
    if not isinstance(answers, dict):
        raise HTTPException(status_code=400, detail='answers 必须是对象')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO reflection_surveys (user_id, answers, updated_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (user_id) DO UPDATE
                   SET answers = EXCLUDED.answers, updated_at = NOW()''',
                (str(user['id']), json.dumps(answers, ensure_ascii=False))
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@router.get('/api/reflection/load')
def load_reflection(user_id: str = None, request: Request = None):
    """加载用户反思问卷答案"""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT answers, updated_at FROM reflection_surveys WHERE user_id = %s',
                (str(user['id']),)
            )
            row = cur.fetchone()
            if not row:
                return {'answers': {}, 'updated_at': None}
            answers = row[0] if isinstance(row[0], dict) else json.loads(row[0] or '{}')
            return {
                'answers': answers,
                'updated_at': row[1].isoformat() if row[1] else None
            }
    finally:
        _release_db(conn)
