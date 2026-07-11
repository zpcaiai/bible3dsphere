"""Fail-closed scoped Mission OS feature flags."""
from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

SCOPE_PRIORITY={"global":0,"environment":1,"tenant":2,"organization":3,"program":4,"user":5}

def env_bool(env:Mapping[str,str],key:str,default:bool=False)->bool:
    value=env.get(key)
    return default if value is None else value.strip().lower() in {"1","true","yes","on"}

@dataclass(frozen=True)
class FlagOverride:
    scope_type:str; scope_id:str; value:bool; starts_at:datetime; expires_at:datetime|None=None
    def active(self,now:datetime)->bool:return self.starts_at<=now and (self.expires_at is None or self.expires_at>now)

def evaluate_flag(*,key:str,default:bool,overrides:Iterable[FlagOverride],scopes:Mapping[str,str],env:Mapping[str,str]|None=None,now:datetime|None=None)->bool:
    env=os.environ if env is None else env; now=now or datetime.now(timezone.utc)
    if env_bool(env,"MISSION_EMERGENCY_OFF"):return False
    if not env_bool(env,"MISSION_OS_ENABLED"):return False
    if key=="mission_ai_enabled" and not env_bool(env,"MISSION_AI_ENABLED"):return False
    selected=None
    for item in overrides:
        if item.scope_type in SCOPE_PRIORITY and item.active(now) and scopes.get(item.scope_type)==item.scope_id:
            candidate=(SCOPE_PRIORITY[item.scope_type],item.starts_at,item.value)
            if selected is None or candidate[:2]>selected[:2]:selected=candidate
    return selected[2] if selected else bool(default)

def load_effective_flag(cur,*,key:str,tenant_id:str,user_id:str,environment:str,organization_id:str|None=None,program_id:str|None=None,env:Mapping[str,str]|None=None)->bool:
    """Load only matching override scopes, then apply fail-closed precedence."""
    cur.execute("SELECT id,default_value FROM mission_feature_flags WHERE key=%s",(key,));row=cur.fetchone()
    if not row:return False
    scopes={"global":"global","environment":environment,"tenant":tenant_id,"user":user_id}
    if organization_id:scopes["organization"]=organization_id
    if program_id:scopes["program"]=program_id
    cur.execute("SELECT scope_type,scope_id,value,starts_at,expires_at FROM mission_feature_flag_overrides WHERE flag_id=%s AND starts_at<=now() AND (expires_at IS NULL OR expires_at>now())",(row[0],))
    overrides=[FlagOverride(r[0],r[1],r[2],r[3],r[4]) for r in cur.fetchall()]
    return evaluate_flag(key=key,default=row[1],overrides=overrides,scopes=scopes,env=env)
