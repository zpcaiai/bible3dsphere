from pathlib import Path
from routers.mission_bridge_ai_faith import SESSIONS
def test_ai_faith_has_exact_eight_discussions():assert len(SESSIONS)==8 and SESSIONS[-1]=='信仰、理性和个人回应'
def test_ai_faith_is_voluntary_balanced_and_source_aware():
 sql=(Path(__file__).parents[1]/'migrations'/'0166_mission_bridge_ai_faith_pilot.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_ai_faith.py').read_text()
 assert "CHECK(participant_requested=TRUE)" in sql and 'excludedMetric":"决志数量' in sql
 assert '公平呈现重要反对意见' in source and '区分哲学推论与实证结论' in source and 'anonymous' in source
