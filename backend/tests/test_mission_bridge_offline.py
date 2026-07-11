from pathlib import Path
def test_offline_sync_rejects_high_risk_and_tracks_conflicts():
 source=(Path(__file__).parents[1]/'routers'/'mission_bridge_offline.py').read_text();sql=(Path(__file__).parents[1]/'migrations'/'0181_mission_bridge_offline_sync.sql').read_text()
 assert "risk in ('L2','L3')" in source and '高风险事件不能通过普通离线队列同步' in source
 assert 'mission_bridge_sync_conflicts' in sql and 'base_version' in sql and 'server_version' in sql
