from pathlib import Path
from routers.mission_bridge_outcomes import FORBIDDEN_RANKINGS
def test_forbidden_rankings_are_complete():assert len(FORBIDDEN_RANKINGS)==5 and '基于AI推测的信心分数' in FORBIDDEN_RANKINGS
def test_outcome_metrics_use_four_layers_and_seven_north_stars():
 sql=(Path(__file__).parents[1]/'migrations'/'0179_mission_bridge_outcomes.sql').read_text()
 assert sql.count("'north_star'")>=8
 for layer in ('service','growth','safety','replication'):assert f"'{layer}'" in sql
 assert 'CHECK(personal_ranking_allowed=FALSE)' in sql
