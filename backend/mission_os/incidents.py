"""Safeguarding state, risk and role invariants independent of FastAPI."""
from dataclasses import dataclass

RISK_ORDER={'L0':0,'L1':1,'L2':2,'L3':3}
TRANSITIONS={
 'open':{'triaged'},'triaged':{'assigned'},'assigned':{'action_in_progress'},
 'action_in_progress':{'monitoring','resolved'},'monitoring':{'action_in_progress','resolved'},
 'resolved':{'closed','reopened'},'closed':{'reopened'},'reopened':{'triaged'},
}
SAFETY_ROLES=frozenset({'platform_admin','safeguarding_officer','child_protection_officer','incident_commander'})
CHILD_CATEGORIES=frozenset({'minor_safety','child_abuse','child_protection'})

@dataclass(frozen=True)
class IncidentState:
    status:str;risk_level:str;category:str

def authorize_view(state:IncidentState,role:str,is_reporter:bool=False)->None:
    if is_reporter:return
    if state.category in CHILD_CATEGORIES and role not in {'platform_admin','child_protection_officer'}:raise PermissionError('child protection role required')
    if state.risk_level in {'L2','L3'} and role not in SAFETY_ROLES:raise PermissionError('safeguarding role required')

def validate_transition(state:IncidentState,to_status:str,role:str)->None:
    if to_status not in TRANSITIONS.get(state.status,set()):raise ValueError('invalid incident transition')
    if state.risk_level in {'L2','L3'} and role not in SAFETY_ROLES:raise PermissionError('L2/L3 require safeguarding role')
    if state.risk_level=='L3' and to_status=='closed' and role not in {'platform_admin','incident_commander'}:raise PermissionError('L3 close requires incident commander')

def validate_risk_change(current:str,target:str,actor_type:str,reason:str)->None:
    if target not in RISK_ORDER or current not in RISK_ORDER:raise ValueError('invalid risk level')
    if RISK_ORDER[target]<RISK_ORDER[current]:
        if actor_type=='ai':raise PermissionError('AI cannot downgrade risk')
        if len(reason.strip())<12:raise ValueError('human downgrade reason required')

def l3_close_ready(reviews:list[tuple[str,str]],actor_id:str)->bool:
    approvals={reviewer for reviewer,decision in reviews if decision=='approve' and reviewer!=actor_id}
    return len(approvals)>=2
