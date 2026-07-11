import pytest
from mission_os.incidents import IncidentState,authorize_view,l3_close_ready,validate_risk_change,validate_transition
from mission_os.religious_freedom import validate_program_policy
from routers.mission_incidents import router
from fastapi.routing import APIRoute

def test_l3_cannot_be_closed_by_mentor_or_ai_downgraded():
    state=IncidentState('resolved','L3','violence')
    with pytest.raises(PermissionError):validate_transition(state,'closed','mentor')
    with pytest.raises(PermissionError):validate_risk_change('L3','L2','ai','model suggestion')

def test_minor_visibility_is_separate_from_general_safeguarding():
    state=IncidentState('open','L2','child_abuse')
    with pytest.raises(PermissionError):authorize_view(state,'safeguarding_officer')
    authorize_view(state,'child_protection_officer')

def test_l3_close_requires_two_other_human_approvals():
    assert not l3_close_ready([('reviewer-1','approve')],'commander')
    assert l3_close_ready([('reviewer-1','approve'),('reviewer-2','approve')],'commander')

def test_state_machine_rejects_skipping_triage():
    with pytest.raises(ValueError):validate_transition(IncidentState('open','L1','stress'),'resolved','safeguarding_officer')

@pytest.mark.parametrize('policy',[{'careConditionalOnFaith':True},{'aidConditionalOnFaith':True},{'servicePriorityInputs':['conversion_status']}])
def test_care_aid_and_priority_cannot_depend_on_religious_participation(policy):
    with pytest.raises(ValueError):validate_program_policy({'servicePolicy':policy})

def test_vulnerable_groups_cannot_receive_automated_persuasion():
    with pytest.raises(ValueError):validate_program_policy({'messagingPolicy':{'automaticPersuasionTargets':['minor']}})

def test_full_incident_api_contract_exists():
    routes={(r.path,m) for r in router.routes if isinstance(r,APIRoute) for m in r.methods}
    expected={
      ('/api/v1/mission/incidents','POST'),('/api/v1/mission/incidents','GET'),
      ('/api/v1/mission/incidents/{incident_id}','GET'),('/api/v1/mission/incidents/{incident_id}/triage','POST'),
      ('/api/v1/mission/incidents/{incident_id}/assign','POST'),('/api/v1/mission/incidents/{incident_id}/escalate','POST'),
      ('/api/v1/mission/incidents/{incident_id}/resolve','POST'),('/api/v1/mission/incidents/{incident_id}/close','POST'),
      ('/api/v1/mission/incidents/{incident_id}/timeline','GET'),('/api/v1/mission/incidents/{incident_id}/close-review','POST'),
    }
    assert expected<=routes
