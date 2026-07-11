from pathlib import Path
from mission_bridge_agents import AGENTS,orchestrate,risk_scan
def test_all_eight_agents_use_structured_output():
 assert len(AGENTS)==8
 for key in AGENTS:
  result=orchestrate(key,'我需要一些帮助')
  assert result['output']['agent']==key and result['output']['autoSend'] is False
def test_risk_can_only_stay_or_increase():assert risk_scan('普通近况','L2')[0]=='L2' and risk_scan('我想自杀','L0')[0]=='L3'
def test_recommendations_are_limited_and_never_enroll():
 result=orchestrate('program_recommendation','请推荐',goal='改善生活',programs=[{'id':str(i),'title':str(i)} for i in range(8)])['output']
 assert len(result['recommendations'])==3 and 'enrolled' not in result
def test_agent_schema_has_audit_review_and_red_team_tables():
 sql=(Path(__file__).parents[1]/'migrations'/'0163_mission_bridge_agents.sql').read_text()
 for name in ('prompt_registry','model_runs','agent_runs','human_reviews','red_team_cases','agent_audit_log'):assert f'mission_bridge_{name}' in sql
 assert 'auto_messages_enabled=FALSE' in sql
 assert "('public','intake','1.0.0'" in sql and 'explicit self harm' in sql
 source=(Path(__file__).parents[1]/'routers'/'mission_bridge_agents.py').read_text();assert 'mission_bridge_model_cost_events' in source and 'agent.manage' in source
