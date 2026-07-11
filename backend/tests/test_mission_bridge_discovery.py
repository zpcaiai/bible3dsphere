from pathlib import Path
import pytest
from pydantic import ValidationError
from routers.mission_bridge import InterviewBody, NeedBody


def test_interview_requires_at_least_one_response():
    with pytest.raises(ValidationError): InterviewBody(participantKind="community_member",consentConfirmed=True,responses=[])


def test_ai_need_stays_candidate_until_human_confirmation():
    need=NeedBody(label="夜班后缺少休息",category="rest",source="ai_candidate")
    assert need.source == "ai_candidate" and need.confirmed is False


def test_discovery_schema_preserves_community_voice_and_boundaries():
    sql=(Path(__file__).parents[1]/"migrations"/"0154_mission_bridge_discovery.sql").read_text(encoding="utf-8")
    assert "community_self_description" in sql
    assert "expressed_by_community" in sql
    assert "service_boundary" in sql
