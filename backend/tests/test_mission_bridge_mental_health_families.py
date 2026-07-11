import pytest
from pathlib import Path
from routers.mission_bridge_mental_health_families import RULES,validate_ai_guidance
def test_mental_health_rules_are_non_negotiable():assert len(RULES)==5 and RULES[0]=='永远不建议停药'
def test_unsafe_spiritual_or_medication_advice_is_rejected():
 for text in ('建议停药','这是邪灵附体','因为犯罪才生病'):
  with pytest.raises(ValueError):validate_ai_guidance(text)
def test_medical_records_have_separate_permission_and_opt_in_reminders():
 sql=(Path(__file__).parents[1]/'migrations'/'0171_mission_bridge_mental_health_families.sql').read_text()
 assert 'mental_health.medical.read' in sql and "('facilitator','mental_health.medical.read')" not in sql
 assert 'explicitly_enabled BOOLEAN NOT NULL DEFAULT FALSE' in sql and "access_class='medical_restricted'" in sql
