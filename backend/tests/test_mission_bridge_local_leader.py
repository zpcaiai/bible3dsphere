from pathlib import Path
from routers.mission_bridge_local_leader import WEEKS
def test_local_leader_has_exact_twelve_week_path():assert len(WEEKS)==12 and '权力、保密和反操控' in WEEKS
def test_local_leader_deliverables_and_ai_boundaries():
 sql=(Path(__file__).parents[1]/'migrations'/'0164_mission_bridge_local_leader.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_local_leader.py').read_text()
 for name in ('leader_workspaces','scripture_observations','leader_case_simulations','leadership_reviews','peer_supervisions','sermon_self_reviews','apprentice_plans','offline_resources'):assert f'mission_bridge_{name}' in sql
 assert '不默认生成可照读讲章' in sql and '神告诉你' in source
