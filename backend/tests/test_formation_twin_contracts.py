from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import pytest

from core.timeutil import parse_iso8601
from pydantic import ValidationError

from formation_twin.contracts import (
    CanonicalLifeEvent,
    ConsentMetadata,
    LifeEventSource,
    LifeEventStatus,
    LifeEventType,
    ProcessingPreference,
    ProvenanceMetadata,
    SafetyMetadata,
    SourceType,
    StatementType,
)
from formation_twin.crypto import decrypt_text, encrypt_text
from formation_twin.normalizer import idempotency_key, minimize_module_payload, normalize_event


pytestmark = pytest.mark.no_db


def _event(**overrides):
    now = datetime.now(timezone.utc)
    values = {
        "event_id": uuid4(),
        "tenant_id": "personal:test@example.com",
        "profile_id": str(uuid4()),
        "subject_user_id": "test@example.com",
        "event_type": LifeEventType.DAILY_CHECKIN,
        "occurred_at": now,
        "recorded_at": now,
        "timezone": "Asia/Shanghai",
        "source": LifeEventSource(source_type=SourceType.USER_STRUCTURED_INPUT, source_module="formation_twin"),
        "self_report": {"overall_state": 7, "statement_type": "USER_REPORTED_FACT"},
        "safety": SafetyMetadata(),
        "consent": ConsentMetadata(consent_scope="MANUAL_INPUT_PROCESSING"),
        "provenance": ProvenanceMetadata(
            statement_types=[StatementType.USER_REPORTED_FACT], processing_steps=["schema_validation"]
        ),
        "status": LifeEventStatus.ACCEPTED,
        "created_at": now,
    }
    values.update(overrides)
    return CanonicalLifeEvent(**values)


def test_canonical_contract_requires_aware_datetimes_and_iana_timezone():
    with pytest.raises(ValidationError, match="timezone-aware"):
        _event(occurred_at=datetime(2026, 7, 17, 9, 0))
    with pytest.raises(ValidationError, match="IANA"):
        _event(timezone="Shanghai")


@pytest.mark.parametrize("field", ["content", "journal_text", "transcript", "crisis_text", "prayer_text"])
def test_canonical_contract_rejects_sensitive_body(field):
    with pytest.raises(ValidationError, match="sensitive"):
        _event(self_report={field: "must never enter the canonical event"})


def test_canonical_contract_rejects_nested_sensitive_body():
    with pytest.raises(ValidationError, match="sensitive"):
        _event(self_report={"details": [{"private_note": "nested private body"}]})


def test_normalizer_is_explicit_and_inference_free():
    event = normalize_event(
        tenant_id="personal:test@example.com",
        profile_id=str(uuid4()),
        user_id="test@example.com",
        event_type=LifeEventType.DAILY_CHECKIN,
        source_type=SourceType.USER_STRUCTURED_INPUT,
        source_module="formation_twin",
        source_record_id="checkin-1",
        source_event_id=None,
        occurred_at=datetime.now(timezone.utc),
        timezone_name="Asia/Shanghai",
        context={"life_domains": ["WORK"]},
        self_report={"overall_state": 4, "statement_type": "USER_REPORTED_FACT"},
        observed_facts=None,
        content_reference={"content_record_id": "opaque-ref", "content_included_in_event": False},
        processing_preference=ProcessingPreference.STORE_ONLY,
        accepted_fields=["overall_state"],
    )

    payload = event.model_dump(mode="json")
    assert payload["provenance"]["statement_types"] == ["USER_REPORTED_FACT"]
    assert "SYSTEM_INFERENCE" not in str(payload)
    assert "spiritual_score" not in str(payload)
    assert payload["content_reference"]["content_included_in_event"] is False


def test_module_adapter_keeps_allowlist_and_discards_values():
    accepted, discarded = minimize_module_payload(
        "prayer",
        {
            "session_id": "p-1",
            "duration_seconds": 240,
            "prayer_category": "gratitude",
            "prayer_text": "private prayer body",
            "person_identity": "private person",
            "unknown": "discard me",
        },
    )

    assert accepted == {"duration_seconds": 240, "prayer_category": "gratitude", "session_id": "p-1"}
    assert discarded == ["person_identity", "prayer_text", "unknown"]
    assert "private prayer body" not in str(discarded)


def test_idempotency_key_is_stable_and_subject_scoped():
    first = idempotency_key(
        tenant_id="tenant-a", user_id="one@example.com", source_type="USER_STRUCTURED_INPUT", client_event_id="client-1"
    )
    replay = idempotency_key(
        tenant_id="tenant-a", user_id="one@example.com", source_type="USER_STRUCTURED_INPUT", client_event_id="client-1"
    )
    other_user = idempotency_key(
        tenant_id="tenant-a", user_id="two@example.com", source_type="USER_STRUCTURED_INPUT", client_event_id="client-1"
    )
    assert first == replay
    assert first != other_user


def test_sensitive_content_uses_authenticated_encryption(monkeypatch):
    monkeypatch.setenv("FORMATION_TWIN_ENCRYPTION_KEY", "11" * 32)
    plaintext = "This is private journal content."
    associated_data = b"test@example.com:content-1"

    envelope = encrypt_text(plaintext, associated_data=associated_data)

    assert plaintext.encode() not in envelope.ciphertext
    assert decrypt_text(envelope, associated_data=associated_data) == plaintext
    with pytest.raises(Exception):
        decrypt_text(envelope, associated_data=b"another-user:content-1")


def test_checked_in_json_schema_validates_the_python_contract_sample():
    schema_path = Path(__file__).parents[1] / "formation_twin" / "canonical-life-event.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    event = _event().model_dump(mode="json")

    assert set(schema["required"]) <= set(event)
    assert event["event_type"] in schema["properties"]["event_type"]["enum"]
    assert event["status"] in schema["properties"]["status"]["enum"]
    assert event["event_version"] == schema["properties"]["event_version"]["const"]
    assert event["data_classification"] == schema["properties"]["data_classification"]["const"]
    # Pydantic 序列化 UTC 时会输出 `Z` 后缀，而 `datetime.fromisoformat` 直到 3.11
    # 才接受它——用共享的解析器，断言的是「带时区」而不是「跑在哪个 Python 上」。
    assert parse_iso8601(event["occurred_at"]).utcoffset() is not None
    assert parse_iso8601(event["recorded_at"]).utcoffset() is not None

    assert set(schema["properties"]["event_type"]["enum"]) == {item.value for item in LifeEventType}
    assert set(schema["properties"]["status"]["enum"]) == {item.value for item in LifeEventStatus}
    assert set(schema["properties"]["provenance"]["properties"]["statement_types"]["items"]["enum"]) == {
        item.value for item in StatementType
    }
