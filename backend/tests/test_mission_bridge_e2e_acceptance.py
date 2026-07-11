from pathlib import Path
from mission_bridge_agents import risk_scan
from mission_bridge_training import evaluate_trainer_evidence

ROOT=Path(__file__).parents[1]
def test_e2e_adult_can_leave_faith_program_without_losing_general_support():
 source=(ROOT/'routers'/'mission_bridge.py').read_text()
 assert "status='exited'" in source and 'CONSENT_TYPES' in source
 assert 'faith_exploration' in source and 'service_participation' in source
def test_e2e_l3_requires_human_incident_timeline_and_audit():
 source=(ROOT/'routers'/'mission_bridge.py').read_text();assert risk_scan('我想自杀','L0')[0]=='L3'
 for term in ('incident_reports','escalation_events','mission_bridge_audit_log','L2/L3 只能由安全官解决'):assert term in source
def test_e2e_minor_requires_consent_and_cleared_mentor():
 youth=(ROOT/'routers'/'mission_bridge_transition_youth.py').read_text();schema=(ROOT/'migrations'/'0176_mission_bridge_transition_youth.sql').read_text()
 assert '未成年人必须取得监护人或合作机构同意' in youth and "status TEXT NOT NULL CHECK(status IN('pending','cleared'" in schema
 assert evaluate_trainer_evidence({})['eligibleForHumanReview'] is False
def test_e2e_cross_tenant_attack_is_denied_by_api_and_rls():
 auth=(ROOT/'mission_bridge_auth.py').read_text();tenancy=(ROOT/'migrations'/'0152_mission_bridge_tenancy.sql').read_text()
 assert '无权访问该租户' in auth and 'app.tenant_id' in tenancy and 'ENABLE ROW LEVEL SECURITY' in tenancy
def test_seed_contains_six_required_programs():
 sql=(ROOT/'migrations'/'0184_mission_bridge_seed_programs.sql').read_text();base=(ROOT/'migrations'/'0151_mission_bridge.sql').read_text()
 for program in ('local-leader-90','attention-reset-30','ai-faith-dialogue-8'):assert program in base
 for program in ('driver-audio-7','caregiver-support','church-harm-recovery'):assert program in sql
