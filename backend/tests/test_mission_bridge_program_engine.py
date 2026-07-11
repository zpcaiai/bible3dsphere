import pytest
from pydantic import ValidationError
from mission_bridge_program import validate_for_publish

def valid():
 return {'id':'pilot-x','version':'1.0.0','groupType':'workers','title':'Worker pilot','description':'A sufficiently clear pilot description','consentRequirements':['service_participation'],'safeguardingProfile':{'noCoercion':True,'professionalReferral':True},'durationWeeks':4,'cadence':'weekly','sessionMode':'hybrid','pathways':[{'key':'standard','title':'Standard','steps':[{'key':'s1','title':'Listen first'}]}],'riskTriggers':['self_harm'],'referralTypes':['medical'],'outcomeMetrics':['trusted_relationship']}

def test_valid_program_definition(): assert validate_for_publish(valid()).version=='1.0.0'
def test_publish_rejects_missing_safeguarding():
 data=valid();data['safeguardingProfile']={}
 with pytest.raises(ValidationError):validate_for_publish(data)
def test_version_is_semver_and_steps_required():
 data=valid();data['version']='latest'
 with pytest.raises(ValidationError):validate_for_publish(data)
