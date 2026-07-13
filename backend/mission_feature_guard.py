"""Shared master and module gates for every non-safety Mission OS API."""
from __future__ import annotations
import os
from fastapi import HTTPException,Request
from mission_os.feature_flags import load_effective_flag

_state={}
def init_mission_feature_guard(*,get_db,release_db,get_session_user):_state.update(locals())

def require_mission_os(request:Request)->None:
    _require_flags(request, ('mission_os_enabled',))

def require_mission_feature(key:str):
    """Return a FastAPI dependency enforcing master + module feature flags."""
    def dependency(request:Request)->None:
        _require_flags(request, ('mission_os_enabled', key))
    dependency.__name__=f'require_{key}'
    return dependency

def _require_flags(request:Request,keys:tuple[str,...])->None:
    user=_state['get_session_user'](request);email=str((user or {}).get('email') or '')
    if not email:raise HTTPException(401,detail='请先登录')
    tenant=(request.headers.get('X-Tenant-Id') or 'public')[:80];conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            environment=os.getenv('APP_ENV') or os.getenv('NODE_ENV') or 'production'
            enabled={key:load_effective_flag(cur,key=key,tenant_id=tenant,user_id=email,environment=environment) for key in keys}
    finally:_state['release_db'](conn)
    if not enabled['mission_os_enabled']:raise HTTPException(503,detail='Mission OS 当前未启用')
    disabled=[key for key in keys[1:] if not enabled[key]]
    if disabled:raise HTTPException(503,detail=f'Mission OS 模块当前未启用: {disabled[0]}')
