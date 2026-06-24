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
        try:
            from routers.semantic_search import index_content
            _ivals = [str(v) for v in (answers or {}).values() if isinstance(v, str) and v.strip()]
            _iem = user.get('email')
            if _ivals and _iem:
                index_content(email=_iem, source_type="reflection",
                              content=chr(10).join(_ivals),
                              source_id="reflection_survey:" + str(user.get('id') or _iem))
        except Exception:
            pass
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
