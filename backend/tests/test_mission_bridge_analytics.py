from pathlib import Path
from routers.mission_bridge_analytics import ANALYSES
def test_all_ten_analysis_types_exist():assert len(ANALYSES)==10 and 'referral_closure' in ANALYSES
def test_experiment_safety_constraints_are_database_enforced():
 sql=(Path(__file__).parents[1]/'migrations'/'0180_mission_bridge_analytics_experiments.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_analytics.py').read_text()
 assert 'CHECK(basic_care_unaffected=TRUE)' in sql and 'CHECK(coercive_messaging=FALSE)' in sql
 assert 'anonymous_subject_hash' in sql and 'research_disclosed' in sql
 assert '高风险群体实验必须先通过安全审查' in source and '转化率不能作为唯一优化目标' in source
