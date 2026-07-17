"""Deterministic, inference-free life-event normalization."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .contracts import (
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


SOURCE_ADAPTERS: dict[str, dict[str, Any]] = {
    "prayer": {
        "source_type": SourceType.PRAYER_OS,
        "event_type": LifeEventType.PRAYER_ACTIVITY,
        "allowed": {"session_id", "occurred_at", "duration_seconds", "prayer_category", "user_defined_tags", "entry_exists"},
        "blocked": {"content", "prayer_text", "person_identity", "medical_details", "legal_details"},
    },
    "holy_habit": {
        "source_type": SourceType.HOLY_HABIT_ENGINE,
        "event_type": LifeEventType.HABIT_ACTIVITY,
        "allowed": {"habit_id", "occurred_at", "status", "habit_category"},
        "blocked": {"private_note", "accountability_partner_message", "raw_notification_content"},
    },
    "devotion": {
        "source_type": SourceType.DEVOTION_SYSTEM,
        "event_type": LifeEventType.DEVOTION_ACTIVITY,
        "allowed": {"session_id", "occurred_at", "completed", "duration_seconds", "scripture_reference", "user_defined_tags"},
        "blocked": {"content", "reflection", "prayer_text"},
    },
    "attention": {
        "source_type": SourceType.ATTENTION_OS,
        "event_type": LifeEventType.ATTENTION_ACTIVITY,
        "allowed": {"session_id", "occurred_at", "duration_seconds", "user_reported_distraction", "summary_metric"},
        "blocked": {"browsing_history", "chat_content", "app_content", "contacts", "location"},
    },
    "crisis": {
        "source_type": SourceType.CRISIS_CARE_SYSTEM,
        "event_type": LifeEventType.CRISIS_STATUS_EVENT,
        "allowed": {"case_reference", "occurred_at", "risk_level", "formation_flow_resumable", "status"},
        "blocked": {"content", "crisis_text", "safety_plan", "contact_information", "medical_record", "method_details"},
    },
    "formation": {
        "source_type": SourceType.FORMATION_ENGINE,
        "event_type": LifeEventType.FORMATION_ACTIVITY,
        "allowed": {"plan_id", "practice_id", "occurred_at", "status", "practice_type"},
        "blocked": {"effectiveness_judgment", "spiritual_score"},
    },
    "worldview": {
        "source_type": SourceType.WORLDVIEW_OS,
        "event_type": LifeEventType.FORMATION_ACTIVITY,
        "allowed": {"reflection_id", "occurred_at", "user_confirmed", "user_rejected", "belief_label"},
        "blocked": {"unconfirmed_inference", "hidden_motive"},
    },
    "gift_calling": {
        "source_type": SourceType.GIFT_CALLING_OS,
        "event_type": LifeEventType.CALLING_ACTIVITY,
        "allowed": {"assessment_id", "occurred_at", "status", "assessment_result", "user_reflection"},
        "blocked": {"divine_determination", "absolute_calling"},
    },
    "church": {
        "source_type": SourceType.CHURCH_HEALTH_OS,
        "event_type": LifeEventType.CHURCH_ACTIVITY,
        "allowed": {"activity_id", "occurred_at", "activity_type", "attended", "user_recorded"},
        "blocked": {"pastoral_note", "discipline_record", "admin_spiritual_rating", "member_identity"},
    },
}


def minimize_module_payload(source_module: str, payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    adapter = SOURCE_ADAPTERS.get(source_module)
    if not adapter:
        raise ValueError("unsupported source module")
    allowed = adapter["allowed"]
    accepted = {key: payload[key] for key in sorted(allowed) if key in payload}
    discarded = sorted(key for key in payload if key not in allowed)
    return accepted, discarded


def idempotency_key(*, tenant_id: str, user_id: str, source_type: str, client_event_id: str) -> str:
    raw = "\x1f".join([tenant_id, user_id, source_type, client_event_id])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_event(
    *,
    tenant_id: str,
    profile_id: str,
    user_id: str,
    event_type: LifeEventType,
    source_type: SourceType,
    source_module: str,
    source_record_id: str | None,
    source_event_id: str | None,
    occurred_at: datetime,
    timezone_name: str,
    context: dict[str, Any] | None,
    self_report: dict[str, Any] | None,
    observed_facts: list[dict[str, Any]] | None,
    content_reference: dict[str, Any] | None,
    processing_preference: ProcessingPreference,
    safety_level: str = "NONE",
    status: LifeEventStatus = LifeEventStatus.ACCEPTED,
    accepted_fields: list[str] | None = None,
    discarded_fields: list[str] | None = None,
    event_subtype: str | None = None,
) -> CanonicalLifeEvent:
    now = datetime.now(timezone.utc)
    occurred = occurred_at
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=ZoneInfo(timezone_name))
    statement_type = StatementType.USER_REPORTED_FACT if self_report is not None else StatementType.OBSERVED_EVENT
    facts = []
    for fact in observed_facts or []:
        facts.append({**fact, "statement_type": StatementType.OBSERVED_EVENT.value})
    return CanonicalLifeEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        profile_id=profile_id,
        subject_user_id=user_id,
        event_type=event_type,
        event_subtype=event_subtype,
        occurred_at=occurred,
        recorded_at=now,
        timezone=timezone_name,
        source=LifeEventSource(
            source_type=source_type,
            source_module=source_module,
            source_record_id=source_record_id,
            source_event_id=source_event_id,
        ),
        context=context or {},
        self_report=self_report,
        behavioral_facts=facts,
        content_reference=content_reference,
        safety=SafetyMetadata(screened=True, safety_level=safety_level),
        consent=ConsentMetadata(
            consent_scope=("MANUAL_INPUT_PROCESSING" if self_report is not None else f"{source_module.upper()}_METADATA_READ"),
            processing_preference=processing_preference,
        ),
        provenance=ProvenanceMetadata(
            statement_types=[statement_type],
            processing_steps=["schema_validation", "consent_validation", "safety_screen", "field_allowlist", "canonical_mapping"],
            accepted_fields=accepted_fields or [],
            discarded_field_names=discarded_fields or [],
        ),
        status=status,
        created_at=now,
    )


def canonical_json(event: CanonicalLifeEvent) -> dict[str, Any]:
    return json.loads(event.model_dump_json())
