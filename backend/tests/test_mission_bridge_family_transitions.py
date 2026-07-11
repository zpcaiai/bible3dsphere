from pathlib import Path
from routers.mission_bridge_family_transitions import PATHWAYS
def test_family_transition_pathways_are_distinct():assert set(PATHWAYS)=={'single_parent','divorced','widowed'}
def test_remarriage_is_not_a_default_goal():
 sql=(Path(__file__).parents[1]/'migrations'/'0174_mission_bridge_single_parent_grief.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_family_transitions.py').read_text()
 assert 'remarriage_goal BOOLEAN' in sql and 'remarriage_goal=NULL' in source and '不以再婚作为默认目标' in source
 for table in ('childcare_resources','family_budgets','grief_logs','holiday_support_plans','transition_family_activities','transition_peer_links','transition_referrals'):assert f'mission_bridge_{table}' in sql
