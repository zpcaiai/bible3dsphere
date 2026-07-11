from pathlib import Path
from routers.mission_bridge_ministry_families import PRINCIPLES
def test_ministry_family_confidentiality_principles():assert '牧者不能查询配偶或子女记录' in PRINCIPLES
def test_home_church_and_family_have_no_automatic_access():
 sql=(Path(__file__).parents[1]/'migrations'/'0175_mission_bridge_ministry_families.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_ministry_families.py').read_text()
 assert 'CHECK(share_with_home_church=FALSE)' in sql and 'mission_bridge_ministry_family_access_denials' in sql
 assert 'cross_org_required=TRUE' in sql and "'familyAutoAccess':False" in source
