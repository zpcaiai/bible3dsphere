"""Non-negotiable religious-freedom program rules."""
from typing import Any,Mapping

FORBIDDEN_CONDITIONS=frozenset({'religious_participation','faith_course_completed','conversion_status','worship_attendance','baptism_status'})
VULNERABLE_GROUPS=frozenset({'minor','aid_recipient','medical_patient','detainee','refugee','domestic_violence_survivor'})

def validate_program_policy(definition:Mapping[str,Any])->None:
    policy=definition.get('servicePolicy') or {}
    if policy.get('careConditionalOnFaith') is True:raise ValueError('care cannot be conditional on faith participation')
    if policy.get('aidConditionalOnFaith') is True:raise ValueError('aid cannot be conditional on faith participation')
    priority=set(policy.get('servicePriorityInputs') or [])
    if priority & FORBIDDEN_CONDITIONS:raise ValueError('religious behavior cannot affect service priority')
    messaging=definition.get('messagingPolicy') or {}
    targets=set(messaging.get('automaticPersuasionTargets') or [])
    if targets & VULNERABLE_GROUPS:raise ValueError('automatic persuasion to vulnerable groups is forbidden')
    if definition.get('exitPolicy',{}).get('penaltyForDecliningFaithActivity'):raise ValueError('declining religious activity cannot cause a penalty')
