"""Shared backend gate for every non-safety Mission OS API."""
from __future__ import annotations
import os
from fastapi import HTTPException,Request
from mission_os.feature_flags import load_effective_flag

_state={}
def init_mission_feature_guard(*,get_db,release_db,get_session_user):_state.update(locals())

def require_mission_os(request:Request)->None:
    user=_state['get_session_user'](request);email=str((user or {}).get('email') or '')
    if not email:raise HTTPException(401,detail='请先登录')
    tenant=(request.headers.get('X-Tenant-Id') or 'public')[:80];conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            enabled=load_effective_flag(cur,key='mission_os_enabled',tenant_id=tenant,user_id=email,environment=os.getenv('APP_ENV') or os.getenv('NODE_ENV') or 'production')
    finally:_state['release_db'](conn)
    if not enabled:raise HTTPException(503,detail='Mission OS 当前未启用')
