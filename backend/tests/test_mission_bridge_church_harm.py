from pathlib import Path
from routers.mission_bridge_church_harm import PRINCIPLES,STAGES
def test_church_harm_has_six_survivor_led_stages():assert len(STAGES)==6 and STAGES[-1].startswith('自主决定')
def test_original_church_has_no_automatic_access():
 sql=(Path(__file__).parents[1]/'migrations'/'0173_mission_bridge_church_harm.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_church_harm.py').read_text()
 assert 'CHECK(share_with_original_church=FALSE)' in sql and "('facilitator','church_harm.independent_review')" not in sql
 assert "'sharedWithOriginalChurch':False" in source
 assert '不首先劝回原教会' in PRINCIPLES and "reviewChannel':'independent" in source
