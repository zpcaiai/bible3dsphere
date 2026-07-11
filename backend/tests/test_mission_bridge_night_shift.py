from pathlib import Path
def test_night_shift_is_shift_based_not_streak_based():
 sql=(Path(__file__).parents[1]/'migrations'/'0168_mission_bridge_night_shift.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_night_shift.py').read_text()
 assert 'shift_started_at' in sql and 'notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE' in sql
 assert '按班次记录，不按自然日计算连续签到' in source and '夜班前3分钟预备' in source
 for metric in ('averageSleepMinutes','averageLoneliness','trustedRelationship'):assert metric in source
