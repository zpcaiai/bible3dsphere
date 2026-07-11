import pytest
from pathlib import Path
from routers.mission_bridge_transition_youth import PROHIBITED,validate_assignment
def test_transition_youth_requires_partner_and_safeguarding():
 assert len(PROHIBITED)==5
 with pytest.raises(ValueError):validate_assignment('pending',False,False)
 with pytest.raises(ValueError):validate_assignment('cleared',True,False)
def test_schema_blocks_transport_money_unlogged_meetings_and_fundraising():
 sql=(Path(__file__).parents[1]/'migrations'/'0176_mission_bridge_transition_youth.sql').read_text();source=(Path(__file__).parents[1]/'routers'/'mission_bridge_transition_youth.py').read_text()
 assert 'CHECK(private_transport_allowed=FALSE)' in sql and 'CHECK(private_money_allowed=FALSE)' in sql and 'CHECK(logged=TRUE)' in sql and 'CHECK(fundraising_use=FALSE)' in sql
 assert '_active_partner' in source and 'age BETWEEN 16 AND 25' in sql
