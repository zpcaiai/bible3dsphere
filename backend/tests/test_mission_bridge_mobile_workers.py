from pathlib import Path
def test_mobile_workers_are_audio_first_and_location_minimized():
 sql=(Path(__file__).parents[1]/'migrations'/'0167_mission_bridge_mobile_workers.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_mobile_workers.py').read_text()
 assert 'duration_minutes IN(3,5,7)' in sql and 'position_seconds' in sql
 assert 'audio_only' in source and '行驶状态下禁止文本输入' in source and '仅允许城市级位置' in source
 assert 'latitude' not in sql and 'longitude' not in sql
