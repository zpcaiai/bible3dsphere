import pytest
from pathlib import Path
from routers.mission_bridge_reentry import PRIVACY,predict_recidivism
def test_reentry_privacy_and_ai_prohibition():
 assert '不使用AI预测再犯罪风险' in PRIVACY
 with pytest.raises(RuntimeError):predict_recidivism({})
def test_criminal_records_are_restricted_and_identity_exposure_blocked():
 sql=(Path(__file__).parents[1]/'migrations'/'0177_mission_bridge_reentry.sql').read_text()
 assert 'reentry.criminal_record.read' in sql and "('facilitator','reentry.criminal_record.read')" not in sql
 assert "access_class='criminal_restricted'" in sql and 'CHECK(long_term_label IS NULL)' in sql
 assert 'CHECK(testimony_identity_exposure=FALSE)' in sql and 'CHECK(fundraising_identity_exposure=FALSE)' in sql
