from pathlib import Path
from routers.mission_bridge_elder_caregivers import AI_BOUNDARIES
def test_elder_caregiver_ai_boundaries_are_explicit():assert AI_BOUNDARIES[:4]==['不诊断失智','不提供药物方案','不承诺病情改善','不责备照护者产生愤怒']
def test_exhaustion_escalates_to_existing_incident_system():
 source=(Path(__file__).parents[1]/'routers'/'mission_bridge_elder_caregivers.py').read_text();sql=(Path(__file__).parents[1]/'migrations'/'0170_mission_bridge_elder_caregivers.sql').read_text()
 assert 'incident_reports' in source and "level in ('L2','L3')" in source
 for table in ('caregiver_assessments','caregiver_support_groups','family_responsibility_meetings','respite_requests','caregiver_expressions','caregiver_resources'):assert f'mission_bridge_{table}' in sql
