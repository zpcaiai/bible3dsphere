"""Immutable, narrative-free Mission OS audit and lineage writes."""
from __future__ import annotations
import hashlib
from typing import Iterable

ALLOWED_ACTIONS=frozenset({'view_sensitive_resource','create','update','delete','approve','reject','pause','resume','assign','export','download','share','impersonate','break_glass_access','ai_generate','ai_accept','ai_reject','outbox_replay','feature_flag_override'})
FORBIDDEN_FIELD_NAMES=frozenset({'password','token','passport','summary','reflection','narrative','exact_location','local_contact'})

def ip_hash(ip:str|None,salt:str)->str|None:
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest() if ip else None

def audit(cur,*,tenant_id:str,actor_id:str,actor_role:str,action:str,resource_type:str,resource_id:str,result:str,
          changed_fields:Iterable[str]=(),reason:str|None=None,request_id:str|None=None,trace_id:str|None=None,
          remote_ip:str|None=None,ip_salt:str="mission-audit",user_agent:str|None=None)->None:
    fields=tuple(sorted(set(changed_fields)))
    if action not in ALLOWED_ACTIONS:raise ValueError("unsupported audit action")
    if any(f.lower() in FORBIDDEN_FIELD_NAMES for f in fields):raise ValueError("sensitive field name cannot enter audit")
    ua=(user_agent or "")[:120] or None
    cur.execute("INSERT INTO mission_audit_logs(tenant_id,actor_id,actor_role,action,resource_type,resource_id,field_names_changed,reason,request_id,trace_id,ip_hash,user_agent_summary,result) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(tenant_id,actor_id,actor_role,action,resource_type,resource_id,list(fields),reason,request_id,trace_id,ip_hash(remote_ip,ip_salt),ua,result))

def add_lineage(cur,*,tenant_id:str,derived_type:str,derived_id:str,source_type:str,source_id:str,transformation_type:str,model_run_id:str|None=None)->None:
    cur.execute("INSERT INTO mission_data_lineage(tenant_id,derived_resource_type,derived_resource_id,source_resource_type,source_resource_id,transformation_type,model_run_id) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",(tenant_id,derived_type,derived_id,source_type,source_id,transformation_type,model_run_id))
