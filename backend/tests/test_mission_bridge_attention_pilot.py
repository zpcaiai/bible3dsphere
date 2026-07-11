from pathlib import Path
from routers.mission_bridge_attention_pilot import FLOW
def test_attention_pilot_has_complete_recovery_flow():assert FLOW==['触发识别','环境改造','替代行为','每日短操练','同伴守望','失败恢复','身份和价值重建']
def test_attention_pilot_reuses_existing_module_and_enforces_privacy():
 sql=(Path(__file__).parents[1]/'migrations'/'0165_mission_bridge_attention_pilot.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_attention_pilot.py').read_text()
 assert 'attention_focus_sessions' in source and 'attention_accountability_relationships' in source
 assert 'CHECK(specific_content_stored=FALSE)' in sql and 'CHECK(private=TRUE)' in sql and '不保存具体搜索词' in source
