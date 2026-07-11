from pathlib import Path
from routers.mission_bridge_mobile_families import MODULES
def test_mobile_family_has_all_nine_modules():assert len(MODULES)==9 and '儿童阅读' in MODULES and '信仰探索' in MODULES
def test_child_and_finance_boundaries_are_enforced():
 sql=(Path(__file__).parents[1]/'migrations'/'0185_mission_bridge_mobile_families.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_mobile_families.py').read_text()
 assert 'mission_bridge_family_adults' in sql and 'mission_bridge_family_children' in sql
 assert 'school_name TEXT' in sql and 'hukou' not in sql.lower() and "CHECK(marketing_eligible=FALSE)" in sql
 assert "access_class='restricted'" in sql and '家庭信仰讨论必须由家庭主动选择' in source
