"""Formation Twin Batch 2 API.

This router is deliberately inference-free: it accepts explicit self-reports
and allow-listed source-module facts, encrypts sensitive text, and publishes
metadata-only canonical events to the existing domain_events table.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator
from psycopg2.extras import Json

from formation_twin.contracts import LifeEventStatus, LifeEventType, ProcessingPreference, SourceType
from formation_twin.crypto import EncryptedContent, decrypt_text, encrypt_text
from formation_twin.data_quality import owner_quality_report
from formation_twin.normalizer import (
    SOURCE_ADAPTERS,
    idempotency_key,
    minimize_module_payload,
    normalize_event,
)


router = APIRouter(prefix="/api/v1/formation-twin", tags=["formation-twin"])
_state: dict[str, Any] = {}

TIMEZONE = "Asia/Shanghai"
CHECKIN_TYPES = {"MORNING_CHECKIN", "MIDDAY_CHECKIN", "EVENING_CHECKIN", "QUICK_CHECKIN", "CUSTOM_CHECKIN"}
JOURNAL_TYPES = {
    "FREE_JOURNAL", "EVENT_REFLECTION", "GRATITUDE_JOURNAL", "SUFFERING_JOURNAL",
    "RELATIONSHIP_REFLECTION", "WORK_REFLECTION", "SPIRITUAL_REFLECTION", "TEMPTATION_RECORD",
    "CONFESSION_RECORD", "ANSWERED_PRAYER_REFLECTION", "LIFE_TRANSITION_RECORD",
}
LIFE_DOMAINS = {
    "SPIRITUAL_LIFE", "EMOTIONAL_LIFE", "PHYSICAL_HEALTH", "MENTAL_HEALTH", "FAMILY", "MARRIAGE",
    "PARENTING", "FRIENDSHIP", "CHURCH", "MINISTRY", "WORK", "STUDY", "FINANCE", "SEXUALITY",
    "ATTENTION", "REST", "SLEEP", "GRIEF", "SUFFERING", "CALLING", "COMMUNITY", "PERSONAL", "OTHER",
}


def init_formation_twin_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _identity(email: str) -> tuple[str, str]:
    tenant_id = f"personal:{email.lower()}"
    profile_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"formation-twin:{email.lower()}"))
    return tenant_id, profile_id


def _aware(value: datetime | None, timezone_name: str = TIMEZONE) -> datetime:
    if value is None:
        return datetime.now(ZoneInfo(timezone_name))
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(status_code=422, detail="occurred_at must include a timezone")
    return value


def _safety(text: str) -> tuple[str, dict | None]:
    if not text.strip():
        return "NONE", None
    try:
        from safety_scan import scan_crisis
        result = scan_crisis(text)
    except Exception:
        result = None
    if not result:
        return "NONE", None
    level = {"yellow": "CONCERN", "orange": "ELEVATED", "red": "IMMINENT"}.get(result.get("riskLevel"), "CONCERN")
    return level, result


def _store_sensitive(
    cur,
    *,
    tenant_id: str,
    profile_id: str,
    email: str,
    content_type: str,
    text: str,
    processing_preference: ProcessingPreference,
    retention_policy: str = "UNTIL_USER_DELETES",
) -> tuple[str, dict] | tuple[None, None]:
    if not text.strip():
        return None, None
    content_id = str(uuid.uuid4())
    encrypted = encrypt_text(text, associated_data=f"{email}:{content_id}".encode())
    cur.execute(
        "INSERT INTO formation_twin_sensitive_contents "
        "(id,tenant_id,profile_id,email,content_type,nonce,encrypted_content,content_hash,encryption_key_version,retention_policy,processing_preference) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            content_id, tenant_id, profile_id, email, content_type, encrypted.nonce, encrypted.ciphertext,
            encrypted.sha256, encrypted.key_version, retention_policy, processing_preference.value,
        ),
    )
    return content_id, {
        "content_storage_type": "AES_256_GCM_INTERNAL",
        "content_record_id": content_id,
        "content_hash": encrypted.sha256,
        "content_included_in_event": False,
    }


def _read_sensitive(cur, *, content_id: str, email: str) -> str:
    cur.execute(
        "SELECT encryption_key_version,nonce,encrypted_content,content_hash FROM formation_twin_sensitive_contents "
        "WHERE id=%s AND email=%s AND deleted_at IS NULL",
        (content_id, email),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sensitive content not found")
    envelope = EncryptedContent(key_version=row[0], nonce=bytes(row[1]), ciphertext=bytes(row[2]), sha256=row[3])
    return decrypt_text(envelope, associated_data=f"{email}:{content_id}".encode())


def _persist_event(cur, *, event, client_event_id: str, idem_key: str, content_reference_id: str | None = None) -> str:
    data = event.model_dump(mode="json")
    cur.execute("SELECT id FROM formation_twin_life_events WHERE idempotency_key=%s", (idem_key,))
    duplicate = cur.fetchone()
    if duplicate:
        return str(duplicate[0])
    cur.execute(
        "INSERT INTO formation_twin_life_events "
        "(id,tenant_id,profile_id,email,event_type,event_subtype,event_version,occurred_at,recorded_at,original_timezone,"
        "source_type,source_module,source_record_id,source_event_id,client_event_id,idempotency_key,context_json,self_report_json,"
        "behavioral_facts_json,spiritual_practice_facts_json,relationship_facts_json,content_reference_id,safety_json,consent_json,"
        "provenance_json,data_classification,processing_preference,status,exclude_from_twin_processing,normalization_version,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            str(event.event_id), event.tenant_id, event.profile_id, event.subject_user_id, event.event_type.value,
            event.event_subtype, event.event_version, event.occurred_at, event.recorded_at, event.timezone,
            event.source.source_type.value, event.source.source_module, event.source.source_record_id,
            event.source.source_event_id, client_event_id, idem_key, Json(data["context"]), Json(data.get("self_report")),
            Json(data["behavioral_facts"]), Json(data["spiritual_practice_facts"]), Json(data["relationship_facts"]),
            content_reference_id, Json(data["safety"]), Json(data["consent"]), Json(data["provenance"]),
            event.data_classification, event.consent.processing_preference.value, event.status.value,
            event.consent.processing_preference == ProcessingPreference.EXCLUDE_FROM_TWIN,
            event.provenance.normalization_version, event.created_at,
        ),
    )
    # Existing event bus receives metadata only.
    cur.execute(
        "INSERT INTO domain_events (aggregate_type,aggregate_id,event_type,payload) VALUES (%s,%s,%s,%s)",
        (
            "formation_twin", event.subject_user_id, f"formation_twin.life_event_{event.status.value.lower()}",
            Json({
                "event_id": str(event.event_id), "event_type": event.event_type.value,
                "source_module": event.source.source_module, "event_version": event.event_version,
                "has_sensitive_content_reference": bool(content_reference_id),
            }),
        ),
    )
    return str(event.event_id)


def _write_receipt(cur, *, tenant_id: str, email: str, source_type: str, source_event_id: str | None,
                   client_event_id: str | None, canonical_event_id: str | None, status: str,
                   failure_code: str | None = None, replay: bool = False) -> None:
    cur.execute(
        "INSERT INTO formation_twin_ingestion_receipts "
        "(id,tenant_id,email,source_type,source_event_id,client_event_id,canonical_event_id,processing_status,failure_code,idempotent_replay) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (str(uuid.uuid4()), tenant_id, email, source_type, source_event_id, client_event_id, canonical_event_id, status, failure_code, replay),
    )


class EmotionInput(BaseModel):
    emotion: str = Field(min_length=1, max_length=48)
    intensity: int | None = Field(default=None, ge=0, le=10)


class BodyStateInput(BaseModel):
    body_label: str = Field(min_length=1, max_length=60)
    body_region: str | None = Field(default=None, max_length=60)
    intensity: int | None = Field(default=None, ge=0, le=10)


class CheckinBody(BaseModel):
    client_event_id: str = Field(min_length=8, max_length=160)
    checkin_type: str = "QUICK_CHECKIN"
    occurred_at: datetime | None = None
    timezone: str = TIMEZONE
    overall_state: int | None = Field(default=None, ge=0, le=10)
    energy_level: int | None = Field(default=None, ge=0, le=10)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    sleep_quality: int | None = Field(default=None, ge=0, le=10)
    primary_emotions: list[EmotionInput] = Field(default_factory=list, max_length=5)
    body_states: list[BodyStateInput] = Field(default_factory=list, max_length=5)
    connection_with_god: str | None = Field(default=None, max_length=30)
    connection_with_people: str | None = Field(default=None, max_length=30)
    gratitude: str = Field(default="", max_length=1000)
    struggle: str = Field(default="", max_length=2000)
    support_needed: str = Field(default="", max_length=1000)
    short_note: str = Field(default="", max_length=2000)
    life_domains: list[str] = Field(default_factory=list, max_length=8)
    processing_preference: ProcessingPreference = ProcessingPreference.STORE_ONLY

    @field_validator("checkin_type")
    @classmethod
    def valid_checkin_type(cls, value):
        if value not in CHECKIN_TYPES:
            raise ValueError("unsupported checkin type")
        return value

    @field_validator("life_domains")
    @classmethod
    def valid_domains(cls, value):
        if any(item not in LIFE_DOMAINS for item in value):
            raise ValueError("unsupported life domain")
        return value

    @model_validator(mode="after")
    def at_least_one_state(self):
        if self.overall_state is None and self.energy_level is None and self.stress_level is None and not self.primary_emotions and not self.body_states:
            raise ValueError("record at least one explicit state")
        return self


class JournalBody(BaseModel):
    client_event_id: str = Field(min_length=8, max_length=160)
    journal_type: str = "FREE_JOURNAL"
    title: str = Field(default="", max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    occurred_at: datetime | None = None
    timezone: str = TIMEZONE
    life_domains: list[str] = Field(default_factory=list, max_length=8)
    user_selected_emotions: list[EmotionInput] = Field(default_factory=list, max_length=5)
    processing_preference: ProcessingPreference = ProcessingPreference.STORE_ONLY

    @field_validator("journal_type")
    @classmethod
    def valid_journal_type(cls, value):
        if value not in JOURNAL_TYPES:
            raise ValueError("unsupported journal type")
        return value

    @field_validator("life_domains")
    @classmethod
    def valid_domains(cls, value):
        if any(item not in LIFE_DOMAINS for item in value):
            raise ValueError("unsupported life domain")
        return value


class TranscriptBody(BaseModel):
    transcript: str = Field(min_length=1, max_length=20000)


class ManualEventBody(BaseModel):
    client_event_id: str = Field(min_length=8, max_length=160)
    event_type: LifeEventType
    occurred_at: datetime
    timezone: str = TIMEZONE
    life_domains: list[str] = Field(default_factory=list, max_length=8)
    summary: str = Field(default="", max_length=4000)
    user_selected_emotions: list[EmotionInput] = Field(default_factory=list, max_length=5)
    processing_preference: ProcessingPreference = ProcessingPreference.STORE_ONLY


class ModuleEventBody(BaseModel):
    subject_user_id: str = Field(min_length=3, max_length=255)
    source_module: str
    source_event_id: str = Field(min_length=1, max_length=160)
    occurred_at: datetime
    timezone: str = TIMEZONE
    payload: dict[str, Any]


class EraseBody(BaseModel):
    confirmation: Literal["ERASE_FORMATION_TWIN_DATA"]


def _create_checkin(cur, *, email: str, body: CheckinBody, supersedes: tuple | None = None) -> dict:
    tenant_id, profile_id = _identity(email)
    source_type = SourceType.USER_STRUCTURED_INPUT.value
    idem = idempotency_key(tenant_id=tenant_id, user_id=email, source_type=source_type, client_event_id=body.client_event_id)
    cur.execute("SELECT id,status FROM formation_twin_life_events WHERE idempotency_key=%s", (idem,))
    duplicate = cur.fetchone()
    if duplicate:
        return {"event_id": str(duplicate[0]), "status": duplicate[1], "idempotent_replay": True}

    occurred = _aware(body.occurred_at, body.timezone)
    text = "\n".join(part for part in [body.gratitude, body.struggle, body.support_needed, body.short_note] if part.strip())
    content_id, content_reference = _store_sensitive(
        cur, tenant_id=tenant_id, profile_id=profile_id, email=email, content_type="CHECKIN_NOTE", text=text,
        processing_preference=body.processing_preference,
    )
    safety_level, crisis = _safety(text)
    status = LifeEventStatus.ROUTED_TO_CRISIS if crisis else LifeEventStatus.ACCEPTED
    self_report = {
        "overall_state": body.overall_state, "energy_level": body.energy_level, "stress_level": body.stress_level,
        "sleep_quality": body.sleep_quality, "connection_with_god": body.connection_with_god,
        "connection_with_people": body.connection_with_people,
        "emotions": [{**item.model_dump(), "statement_type": "USER_REPORTED_FACT"} for item in body.primary_emotions],
        "body_states": [{**item.model_dump(), "statement_type": "USER_REPORTED_FACT"} for item in body.body_states],
        "statement_type": "USER_REPORTED_FACT",
    }
    self_report = {key: value for key, value in self_report.items() if value not in (None, [], "")}
    checkin_id = str(uuid.uuid4())
    event = normalize_event(
        tenant_id=tenant_id, profile_id=profile_id, user_id=email, event_type=LifeEventType.DAILY_CHECKIN,
        event_subtype=body.checkin_type, source_type=SourceType.USER_STRUCTURED_INPUT, source_module="formation_twin",
        source_record_id=checkin_id, source_event_id=None, occurred_at=occurred, timezone_name=body.timezone,
        context={"life_domains": body.life_domains, "user_tags": []}, self_report=self_report, observed_facts=None,
        content_reference=content_reference, processing_preference=body.processing_preference,
        safety_level=safety_level, status=status, accepted_fields=sorted(self_report.keys()),
    )
    event_id = _persist_event(cur, event=event, client_event_id=body.client_event_id, idem_key=idem, content_reference_id=content_id)
    cur.execute(
        "INSERT INTO formation_twin_daily_checkins "
        "(id,tenant_id,profile_id,email,checkin_type,overall_state,energy_level,stress_level,sleep_quality,connection_with_god,"
        "connection_with_people,self_report_json,sensitive_content_id,canonical_event_id,processing_preference,occurred_at,revision,supersedes_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            checkin_id, tenant_id, profile_id, email, body.checkin_type, body.overall_state, body.energy_level,
            body.stress_level, body.sleep_quality, body.connection_with_god, body.connection_with_people,
            Json(self_report), content_id, event_id, body.processing_preference.value, occurred,
            (supersedes[1] + 1 if supersedes else 1), (supersedes[0] if supersedes else None),
        ),
    )
    if supersedes:
        cur.execute("UPDATE formation_twin_life_events SET status='SUPERSEDED' WHERE id=%s AND email=%s", (supersedes[2], email))
        cur.execute("UPDATE formation_twin_daily_checkins SET updated_at=now() WHERE id=%s AND email=%s", (supersedes[0], email))
    _write_receipt(cur, tenant_id=tenant_id, email=email, source_type=source_type, source_event_id=None,
                   client_event_id=body.client_event_id, canonical_event_id=event_id, status=status.value)
    return {"event_id": event_id, "checkin_id": checkin_id, "status": status.value, "idempotent_replay": False,
            "processing": {"safety_screened": True, "normalized": True, "published": True}, "crisis": crisis}


@router.post("/checkins")
def create_checkin(request: Request, body: CheckinBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            result = _create_checkin(cur, email=user["email"], body=body)
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/checkins")
def list_checkins(request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,checkin_type,overall_state,energy_level,stress_level,sleep_quality,connection_with_god,"
                "connection_with_people,self_report_json,processing_preference,occurred_at,recorded_at,revision,canonical_event_id "
                "FROM formation_twin_daily_checkins WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT %s OFFSET %s",
                (user["email"], limit, offset),
            )
            rows = cur.fetchall()
        return {"ok": True, "items": [{
            "id": str(r[0]), "checkin_type": r[1], "overall_state": r[2], "energy_level": r[3], "stress_level": r[4],
            "sleep_quality": r[5], "connection_with_god": r[6], "connection_with_people": r[7], "self_report": r[8] or {},
            "processing_preference": r[9], "occurred_at": r[10].isoformat(), "recorded_at": r[11].isoformat(),
            "revision": r[12], "event_id": str(r[13]),
        } for r in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/checkins/{checkin_id}")
def get_checkin(checkin_id: str, request: Request) -> dict:
    items = list_checkins(request, limit=200, offset=0)["items"]
    item = next((entry for entry in items if entry["id"] == checkin_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Check-in not found")
    return {"ok": True, "checkin": item}


@router.patch("/checkins/{checkin_id}")
def revise_checkin(checkin_id: str, request: Request, body: CheckinBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,revision,canonical_event_id FROM formation_twin_daily_checkins WHERE id=%s AND email=%s AND deleted_at IS NULL", (checkin_id, user["email"]))
            old = cur.fetchone()
            if not old:
                raise HTTPException(status_code=404, detail="Check-in not found")
            result = _create_checkin(cur, email=user["email"], body=body, supersedes=old)
            cur.execute(
                "INSERT INTO formation_twin_event_revisions (id,tenant_id,email,event_id,revision,change_type,previous_event_id,created_by) "
                "VALUES (%s,%s,%s,%s,%s,'SUPERSEDE',%s,%s)",
                (str(uuid.uuid4()), _identity(user["email"])[0], user["email"], result["event_id"], old[1] + 1, old[2], user["email"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/checkins/{checkin_id}")
def delete_checkin(checkin_id: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE formation_twin_daily_checkins SET deleted_at=now() WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING canonical_event_id,sensitive_content_id",
                (checkin_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Check-in not found")
            cur.execute("UPDATE formation_twin_life_events SET status='DELETED',deleted_at=now() WHERE id=%s AND email=%s", (row[0], user["email"]))
            if row[1]:
                cur.execute("UPDATE formation_twin_sensitive_contents SET deleted_at=now(),encrypted_content='\\x'::bytea WHERE id=%s AND email=%s", (row[1], user["email"]))
            conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


def _create_journal(cur, *, email: str, body: JournalBody, supersedes: tuple | None = None) -> dict:
    tenant_id, profile_id = _identity(email)
    idem = idempotency_key(tenant_id=tenant_id, user_id=email, source_type=SourceType.USER_MANUAL_INPUT.value, client_event_id=body.client_event_id)
    cur.execute("SELECT id,status FROM formation_twin_life_events WHERE idempotency_key=%s", (idem,))
    duplicate = cur.fetchone()
    if duplicate:
        return {"event_id": str(duplicate[0]), "status": duplicate[1], "idempotent_replay": True}
    journal_id = str(uuid.uuid4())
    content_id, content_reference = _store_sensitive(
        cur, tenant_id=tenant_id, profile_id=profile_id, email=email, content_type="LIFE_JOURNAL", text=body.content,
        processing_preference=body.processing_preference,
    )
    safety_level, crisis = _safety(body.content)
    status = LifeEventStatus.ROUTED_TO_CRISIS if crisis else LifeEventStatus.ACCEPTED
    self_report = {
        "journal_type": body.journal_type,
        "entry_exists": True,
        "emotions": [{**item.model_dump(), "statement_type": "USER_REPORTED_FACT"} for item in body.user_selected_emotions],
        "statement_type": "USER_REPORTED_FACT",
    }
    occurred = _aware(body.occurred_at, body.timezone)
    event = normalize_event(
        tenant_id=tenant_id, profile_id=profile_id, user_id=email, event_type=LifeEventType.JOURNAL_ENTRY,
        event_subtype=body.journal_type, source_type=SourceType.USER_MANUAL_INPUT, source_module="formation_twin",
        source_record_id=journal_id, source_event_id=None, occurred_at=occurred, timezone_name=body.timezone,
        context={"life_domains": body.life_domains, "user_tags": []}, self_report=self_report, observed_facts=None,
        content_reference=content_reference, processing_preference=body.processing_preference,
        safety_level=safety_level, status=status,
        accepted_fields=["journal_type", "life_domains", "user_selected_emotions", "occurred_at", "content_reference"],
    )
    event_id = _persist_event(cur, event=event, client_event_id=body.client_event_id, idem_key=idem, content_reference_id=content_id)
    cur.execute(
        "INSERT INTO formation_twin_journals "
        "(id,tenant_id,profile_id,email,journal_type,title,sensitive_content_id,canonical_event_id,processing_preference,life_domains,"
        "user_selected_emotions,occurred_at,revision,supersedes_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            journal_id, tenant_id, profile_id, email, body.journal_type, body.title, content_id, event_id,
            body.processing_preference.value, Json(body.life_domains), Json([item.model_dump() for item in body.user_selected_emotions]),
            occurred, (supersedes[1] + 1 if supersedes else 1), (supersedes[0] if supersedes else None),
        ),
    )
    if supersedes:
        cur.execute("UPDATE formation_twin_life_events SET status='SUPERSEDED' WHERE id=%s AND email=%s", (supersedes[2], email))
        cur.execute("UPDATE formation_twin_journals SET status='SUPERSEDED',updated_at=now() WHERE id=%s AND email=%s", (supersedes[0], email))
    _write_receipt(cur, tenant_id=tenant_id, email=email, source_type=SourceType.USER_MANUAL_INPUT.value,
                   source_event_id=None, client_event_id=body.client_event_id, canonical_event_id=event_id, status=status.value)
    return {"journal_id": journal_id, "event_id": event_id, "status": status.value, "idempotent_replay": False, "crisis": crisis}


@router.post("/journals")
def create_journal(request: Request, body: JournalBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            result = _create_journal(cur, email=user["email"], body=body)
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/journals")
def list_journals(request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,journal_type,title,processing_preference,life_domains,user_selected_emotions,occurred_at,recorded_at,revision,canonical_event_id "
                "FROM formation_twin_journals WHERE email=%s AND deleted_at IS NULL AND status<>'SUPERSEDED' "
                "ORDER BY occurred_at DESC LIMIT %s OFFSET %s", (user["email"], limit, offset),
            )
            rows = cur.fetchall()
        return {"ok": True, "items": [{
            "id": str(r[0]), "journal_type": r[1], "title": r[2] or "", "processing_preference": r[3],
            "life_domains": r[4] or [], "user_selected_emotions": r[5] or [], "occurred_at": r[6].isoformat(),
            "recorded_at": r[7].isoformat(), "revision": r[8], "event_id": str(r[9]),
        } for r in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/journals/{journal_id}")
def get_journal(journal_id: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,journal_type,title,sensitive_content_id,processing_preference,life_domains,user_selected_emotions,occurred_at,revision "
                "FROM formation_twin_journals WHERE id=%s AND email=%s AND deleted_at IS NULL", (journal_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Journal not found")
            content = _read_sensitive(cur, content_id=str(row[3]), email=user["email"])
        return {"ok": True, "journal": {
            "id": str(row[0]), "journal_type": row[1], "title": row[2] or "", "content": content,
            "processing_preference": row[4], "life_domains": row[5] or [], "user_selected_emotions": row[6] or [],
            "occurred_at": row[7].isoformat(), "revision": row[8],
        }}
    finally:
        _state["release_db"](conn)


@router.patch("/journals/{journal_id}")
def revise_journal(journal_id: str, request: Request, body: JournalBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,revision,canonical_event_id FROM formation_twin_journals WHERE id=%s AND email=%s AND deleted_at IS NULL", (journal_id, user["email"]))
            old = cur.fetchone()
            if not old:
                raise HTTPException(status_code=404, detail="Journal not found")
            result = _create_journal(cur, email=user["email"], body=body, supersedes=old)
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/journals/{journal_id}")
def delete_journal(journal_id: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE formation_twin_journals SET deleted_at=now(),status='DELETED' WHERE id=%s AND email=%s AND deleted_at IS NULL "
                "RETURNING canonical_event_id,sensitive_content_id", (journal_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Journal not found")
            cur.execute("UPDATE formation_twin_life_events SET status='DELETED',deleted_at=now() WHERE id=%s AND email=%s", (row[0], user["email"]))
            cur.execute("UPDATE formation_twin_sensitive_contents SET deleted_at=now(),encrypted_content='\\x'::bytea WHERE id=%s AND email=%s", (row[1], user["email"]))
            conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/journals/{journal_id}/restore")
def restore_journal(journal_id: str, request: Request) -> dict:
    user = _require_user(request)
    raise HTTPException(status_code=409, detail="Permanently purged journal content cannot be restored")


@router.post("/voice-journals/upload")
async def upload_voice_journal(
    request: Request,
    file: UploadFile = File(...),
    consent_confirmed: bool = Form(False),
    delete_audio_after_transcription: bool = Form(True),
) -> dict:
    user = _require_user(request)
    if not consent_confirmed:
        raise HTTPException(status_code=403, detail="VOICE_PROCESSING consent is required")
    content_type = (file.content_type or "audio/webm").split(";")[0].lower()
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="Only audio uploads are supported")
    audio = await file.read(10 * 1024 * 1024 + 1)
    if not audio:
        raise HTTPException(status_code=400, detail="Audio upload is empty")
    if len(audio) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio upload is too large")
    from routers.speech import transcribe_audio_bytes
    result = await transcribe_audio_bytes(audio, content_type=content_type)
    transcript = result.get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=422, detail="No transcript was produced")
    tenant_id, profile_id = _identity(user["email"])
    voice_id = str(uuid.uuid4())
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            content_id, _ = _store_sensitive(
                cur, tenant_id=tenant_id, profile_id=profile_id, email=user["email"], content_type="VOICE_TRANSCRIPT",
                text=transcript, processing_preference=ProcessingPreference.STORE_ONLY,
                retention_policy="UNTIL_USER_CONFIRMS_OR_DELETES",
            )
            cur.execute(
                "INSERT INTO formation_twin_voice_journals "
                "(id,tenant_id,profile_id,email,transcript_sensitive_content_id,transcription_status,detected_language,audio_retention_policy,audio_sha256,audio_deleted_at) "
                "VALUES (%s,%s,%s,%s,%s,'USER_REVIEW_REQUIRED',%s,%s,%s,now())",
                (
                    voice_id, tenant_id, profile_id, user["email"], content_id, result.get("detected_language"),
                    "DELETE_AFTER_TRANSCRIPTION" if delete_audio_after_transcription else "TRANSIENT_ONLY",
                    hashlib.sha256(audio).hexdigest(),
                ),
            )
            conn.commit()
        return {"ok": True, "voice_journal_id": voice_id, "status": "USER_REVIEW_REQUIRED", "transcript": transcript,
                "detected_language": result.get("detected_language"), "audio_persisted": False}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/voice-journals/{voice_id}")
def get_voice_journal(voice_id: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,transcript_sensitive_content_id,transcription_status,detected_language,user_confirmed,audio_retention_policy,created_at,confirmed_at "
                "FROM formation_twin_voice_journals WHERE id=%s AND email=%s AND deleted_at IS NULL", (voice_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Voice journal not found")
            transcript = _read_sensitive(cur, content_id=str(row[1]), email=user["email"])
        return {"ok": True, "voice_journal": {
            "id": str(row[0]), "transcript": transcript, "status": row[2], "detected_language": row[3],
            "user_confirmed": row[4], "audio_retention_policy": row[5], "created_at": row[6].isoformat(),
            "confirmed_at": row[7].isoformat() if row[7] else None,
        }}
    finally:
        _state["release_db"](conn)


@router.patch("/voice-journals/{voice_id}/transcript")
def update_voice_transcript(voice_id: str, request: Request, body: TranscriptBody) -> dict:
    user = _require_user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT transcript_sensitive_content_id,user_confirmed FROM formation_twin_voice_journals WHERE id=%s AND email=%s AND deleted_at IS NULL", (voice_id, user["email"]))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Voice journal not found")
            if row[1]:
                raise HTTPException(status_code=409, detail="Confirmed transcript is immutable")
            content_id, _ = _store_sensitive(
                cur, tenant_id=tenant_id, profile_id=profile_id, email=user["email"], content_type="VOICE_TRANSCRIPT",
                text=body.transcript, processing_preference=ProcessingPreference.STORE_ONLY,
                retention_policy="UNTIL_USER_CONFIRMS_OR_DELETES",
            )
            cur.execute("UPDATE formation_twin_sensitive_contents SET deleted_at=now(),encrypted_content='\\x'::bytea WHERE id=%s AND email=%s", (row[0], user["email"]))
            cur.execute("UPDATE formation_twin_voice_journals SET transcript_sensitive_content_id=%s,transcription_status='USER_REVIEW_REQUIRED' WHERE id=%s AND email=%s", (content_id, voice_id, user["email"]))
            conn.commit()
        return {"ok": True, "status": "USER_REVIEW_REQUIRED"}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/voice-journals/{voice_id}/confirm")
def confirm_voice_journal(voice_id: str, request: Request) -> dict:
    user = _require_user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT transcript_sensitive_content_id,user_confirmed,created_at FROM formation_twin_voice_journals "
                "WHERE id=%s AND email=%s AND deleted_at IS NULL", (voice_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Voice journal not found")
            if row[1]:
                cur.execute("SELECT canonical_event_id FROM formation_twin_voice_journals WHERE id=%s", (voice_id,))
                return {"ok": True, "event_id": str(cur.fetchone()[0]), "idempotent_replay": True}
            transcript = _read_sensitive(cur, content_id=str(row[0]), email=user["email"])
            safety_level, crisis = _safety(transcript)
            status = LifeEventStatus.ROUTED_TO_CRISIS if crisis else LifeEventStatus.ACCEPTED
            idem = idempotency_key(tenant_id=tenant_id, user_id=user["email"], source_type=SourceType.USER_VOICE_INPUT.value, client_event_id=voice_id)
            event = normalize_event(
                tenant_id=tenant_id, profile_id=profile_id, user_id=user["email"], event_type=LifeEventType.VOICE_JOURNAL,
                event_subtype="USER_CONFIRMED_TRANSCRIPT", source_type=SourceType.USER_VOICE_INPUT, source_module="formation_twin",
                source_record_id=voice_id, source_event_id=None, occurred_at=row[2], timezone_name=TIMEZONE,
                context={}, self_report={"entry_exists": True, "statement_type": "USER_REPORTED_FACT"}, observed_facts=None,
                content_reference={"content_storage_type": "AES_256_GCM_INTERNAL", "content_record_id": str(row[0]), "content_included_in_event": False},
                processing_preference=ProcessingPreference.STORE_ONLY, safety_level=safety_level, status=status,
                accepted_fields=["user_confirmed_transcript_reference"],
            )
            event_id = _persist_event(cur, event=event, client_event_id=voice_id, idem_key=idem, content_reference_id=str(row[0]))
            cur.execute(
                "UPDATE formation_twin_voice_journals SET user_confirmed=TRUE,transcription_status='CONFIRMED',confirmed_at=now(),canonical_event_id=%s WHERE id=%s AND email=%s",
                (event_id, voice_id, user["email"]),
            )
            conn.commit()
        return {"ok": True, "event_id": event_id, "status": status.value, "crisis": crisis, "idempotent_replay": False}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/voice-journals/{voice_id}")
def delete_voice_journal(voice_id: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE formation_twin_voice_journals SET deleted_at=now(),transcription_status='DELETED' WHERE id=%s AND email=%s AND deleted_at IS NULL "
                "RETURNING transcript_sensitive_content_id,canonical_event_id", (voice_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Voice journal not found")
            cur.execute("UPDATE formation_twin_sensitive_contents SET deleted_at=now(),encrypted_content='\\x'::bytea WHERE id=%s AND email=%s", (row[0], user["email"]))
            if row[1]:
                cur.execute("UPDATE formation_twin_life_events SET status='DELETED',deleted_at=now() WHERE id=%s AND email=%s", (row[1], user["email"]))
            conn.commit()
        return {"ok": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/life-events")
def create_manual_event(request: Request, body: ManualEventBody) -> dict:
    user = _require_user(request)
    tenant_id, profile_id = _identity(user["email"])
    idem = idempotency_key(
        tenant_id=tenant_id,
        user_id=user["email"],
        source_type=SourceType.USER_STRUCTURED_INPUT.value,
        client_event_id=body.client_event_id,
    )
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,status FROM formation_twin_life_events WHERE idempotency_key=%s", (idem,))
            duplicate = cur.fetchone()
            if duplicate:
                conn.commit()
                return {"ok": True, "event_id": str(duplicate[0]), "status": duplicate[1], "idempotent_replay": True}

            content_id, content_reference = _store_sensitive(
                cur,
                tenant_id=tenant_id,
                profile_id=profile_id,
                email=user["email"],
                content_type="MANUAL_EVENT_SUMMARY",
                text=body.summary,
                processing_preference=body.processing_preference,
            )
            safety_level, crisis = _safety(body.summary)
            event_status = LifeEventStatus.ROUTED_TO_CRISIS if crisis else LifeEventStatus.ACCEPTED
            self_report = {
                "emotions": [
                    {**item.model_dump(), "statement_type": "USER_REPORTED_FACT"}
                    for item in body.user_selected_emotions
                ],
                "statement_type": "USER_REPORTED_FACT",
            }
            event = normalize_event(
                tenant_id=tenant_id,
                profile_id=profile_id,
                user_id=user["email"],
                event_type=body.event_type,
                source_type=SourceType.USER_STRUCTURED_INPUT,
                source_module="formation_twin",
                source_record_id=None,
                source_event_id=None,
                occurred_at=_aware(body.occurred_at, body.timezone),
                timezone_name=body.timezone,
                context={"life_domains": body.life_domains, "user_tags": []},
                self_report=self_report,
                observed_facts=None,
                content_reference=content_reference,
                processing_preference=body.processing_preference,
                safety_level=safety_level,
                status=event_status,
                accepted_fields=["emotions", "life_domains"],
            )
            event_id = _persist_event(
                cur,
                event=event,
                client_event_id=body.client_event_id,
                idem_key=idem,
                content_reference_id=content_id,
            )
            _write_receipt(
                cur,
                tenant_id=tenant_id,
                email=user["email"],
                source_type=SourceType.USER_STRUCTURED_INPUT.value,
                source_event_id=None,
                client_event_id=body.client_event_id,
                canonical_event_id=event_id,
                status=event_status.value,
            )
            conn.commit()
        return {
            "ok": True,
            "event_id": event_id,
            "status": event_status.value,
            "crisis": crisis,
            "idempotent_replay": False,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/life-events")
@router.get("/timeline")
def timeline(
    request: Request,
    source_module: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    user = _require_user(request)
    clauses = ["email=%s", "deleted_at IS NULL"]
    params: list[Any] = [user["email"]]
    if source_module:
        clauses.append("source_module=%s"); params.append(source_module)
    if event_type:
        clauses.append("event_type=%s"); params.append(event_type)
    if status:
        clauses.append("status=%s"); params.append(status)
    params.extend([limit, offset])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,event_type,event_subtype,occurred_at,recorded_at,original_timezone,source_type,source_module,context_json,"
                "self_report_json,safety_json,consent_json,provenance_json,data_classification,processing_preference,status,"
                "exclude_from_twin_processing,revision,content_reference_id FROM formation_twin_life_events WHERE "
                + " AND ".join(clauses) + " ORDER BY occurred_at DESC,id DESC LIMIT %s OFFSET %s", tuple(params),
            )
            rows = cur.fetchall()
        return {"ok": True, "items": [{
            "event_id": str(r[0]), "event_type": r[1], "event_subtype": r[2], "occurred_at": r[3].isoformat(),
            "recorded_at": r[4].isoformat(), "timezone": r[5], "source_type": r[6], "source_module": r[7],
            "context": r[8] or {}, "self_report": r[9] or {}, "safety": r[10] or {}, "consent": r[11] or {},
            "provenance": r[12] or {}, "data_classification": r[13], "processing_preference": r[14], "status": r[15],
            "exclude_from_twin_processing": r[16], "revision": r[17], "has_sensitive_content_reference": bool(r[18]),
        } for r in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/life-events/{event_id}")
def get_life_event(event_id: str, request: Request) -> dict:
    data = timeline(request, limit=200, offset=0)
    item = next((event for event in data["items"] if event["event_id"] == event_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Life event not found")
    return {"ok": True, "event": item}


def _set_event_control(event_id: str, request: Request, *, excluded: bool | None = None, deleted: bool = False) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_email', %s, true)", (user["email"],))
            if deleted:
                cur.execute("UPDATE formation_twin_life_events SET status='DELETED',deleted_at=now(),exclude_from_twin_processing=TRUE WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id", (event_id, user["email"]))
            else:
                cur.execute("UPDATE formation_twin_life_events SET exclude_from_twin_processing=%s,status=%s WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id", (excluded, "EXCLUDED" if excluded else "ACCEPTED", event_id, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Life event not found")
            cur.execute(
                "UPDATE formation_twin_emotional_snapshots SET superseded_at=now() "
                "WHERE email=%s AND superseded_at IS NULL",
                (user["email"],),
            )
            cur.execute(
                "UPDATE formation_twin_formation_snapshots SET superseded_at=now() WHERE email=%s AND superseded_at IS NULL",
                (user["email"],),
            )
            if deleted or excluded:
                cur.execute(
                    "UPDATE formation_twin_reflection_contexts SET invalidated_at=now() "
                    "WHERE email=%s AND invalidated_at IS NULL AND user_capacity_json->'source_event_ids' ? %s",
                    (user["email"], event_id),
                )
                cur.execute(
                    "UPDATE formation_twin_reflection_mirrors SET status='INVALIDATED',invalidated_at=now() "
                    "WHERE email=%s AND status='ACTIVE' AND context_id IN "
                    "(SELECT id FROM formation_twin_reflection_contexts WHERE email=%s AND invalidated_at IS NOT NULL)",
                    (user["email"], user["email"]),
                )
                cur.execute(
                    "UPDATE formation_twin_intervention_proposals SET lifecycle_status='INVALIDATED',invalidated_at=now() "
                    "WHERE email=%s AND lifecycle_status='PROPOSED' AND context_id IN "
                    "(SELECT id FROM formation_twin_reflection_contexts WHERE email=%s AND invalidated_at IS NOT NULL)",
                    (user["email"], user["email"]),
                )
                cur.execute(
                    "UPDATE formation_twin_risk_conditions SET invalidated_at=now() WHERE email=%s "
                    "AND invalidated_at IS NULL AND evidence_references_json @> %s::jsonb",
                    (user["email"], Json([{"reference_id": event_id}])),
                )
                if cur.rowcount:
                    cur.execute(
                        "UPDATE formation_twin_risk_snapshots SET invalidated_at=now() "
                        "WHERE email=%s AND invalidated_at IS NULL",
                        (user["email"],),
                    )
                    cur.execute(
                        "UPDATE formation_twin_early_warnings SET delivery_status='INVALIDATED',deleted_at=now() "
                        "WHERE email=%s AND deleted_at IS NULL AND risk_snapshot_id IN "
                        "(SELECT id FROM formation_twin_risk_snapshots WHERE email=%s AND invalidated_at IS NOT NULL)",
                        (user["email"], user["email"]),
                    )
            next_status = "DELETED" if deleted else ("EXCLUDED" if excluded else "ACTIVE")
            if deleted or excluded:
                cur.execute(
                    "UPDATE formation_twin_formation_nodes SET processing_status=%s,deleted_at=CASE WHEN %s THEN now() ELSE deleted_at END WHERE email=%s AND life_event_id=%s AND deleted_at IS NULL",
                    (next_status, deleted, user["email"], event_id),
                )
                cur.execute(
                    "UPDATE formation_twin_formation_chains SET processing_status=%s,excluded_from_context=TRUE,deleted_at=CASE WHEN %s THEN now() ELSE deleted_at END WHERE email=%s AND life_event_id=%s AND deleted_at IS NULL",
                    (next_status, deleted, user["email"], event_id),
                )
                if deleted:
                    for table_name in (
                        "formation_twin_identity_statements", "formation_twin_interpretations", "formation_twin_belief_statements",
                        "formation_twin_desire_observations", "formation_twin_fear_observations", "formation_twin_temptation_observations",
                        "formation_twin_behavior_observations", "formation_twin_outcome_observations",
                    ):
                        cur.execute(f"UPDATE {table_name} SET deleted_at=now() WHERE email=%s AND life_event_id=%s AND deleted_at IS NULL", (user["email"], event_id))
            else:
                cur.execute("UPDATE formation_twin_formation_nodes SET processing_status='ACTIVE' WHERE email=%s AND life_event_id=%s AND processing_status='EXCLUDED' AND deleted_at IS NULL", (user["email"], event_id))
                cur.execute("UPDATE formation_twin_formation_chains SET processing_status='ACTIVE',excluded_from_context=FALSE WHERE email=%s AND life_event_id=%s AND processing_status='EXCLUDED' AND deleted_at IS NULL", (user["email"], event_id))
            conn.commit()
        return {"ok": True, "event_id": event_id, "excluded": bool(excluded), "deleted": deleted}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/life-events/{event_id}/exclude")
def exclude_life_event(event_id: str, request: Request) -> dict:
    return _set_event_control(event_id, request, excluded=True)


@router.post("/life-events/{event_id}/include")
def include_life_event(event_id: str, request: Request) -> dict:
    return _set_event_control(event_id, request, excluded=False)


@router.delete("/life-events/{event_id}")
def delete_life_event(event_id: str, request: Request) -> dict:
    return _set_event_control(event_id, request, deleted=True)


@router.get("/data-sources")
def data_sources(request: Request) -> dict:
    user = _require_user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            for source, config in SOURCE_ADAPTERS.items():
                cur.execute(
                    "INSERT INTO formation_twin_source_connections (id,tenant_id,profile_id,email,source_module,status,consent_scope,allowed_fields,blocked_fields) "
                    "VALUES (%s,%s,%s,%s,%s,'PAUSED',%s,%s,%s) ON CONFLICT (tenant_id,profile_id,source_module) DO NOTHING",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], source, f"{source.upper()}_METADATA_READ", Json(sorted(config["allowed"])), Json(sorted(config["blocked"]))),
                )
            conn.commit()
            cur.execute(
                "SELECT source_module,status,consent_scope,allowed_fields,blocked_fields,last_event_received_at,last_successful_sync_at,last_failure_code "
                "FROM formation_twin_source_connections WHERE email=%s ORDER BY source_module", (user["email"],),
            )
            rows = cur.fetchall()
        return {"ok": True, "items": [{
            "source_module": r[0], "status": r[1], "consent_scope": r[2], "allowed_fields": r[3] or [],
            "blocked_fields": r[4] or [], "last_event_received_at": r[5].isoformat() if r[5] else None,
            "last_successful_sync_at": r[6].isoformat() if r[6] else None, "last_failure_code": r[7],
        } for r in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/data-quality")
def data_quality(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            report = owner_quality_report(cur, email=user["email"])
        return {"ok": True, "scope": "current_user", **report}
    finally:
        _state["release_db"](conn)


@router.get("/export")
def export_formation_twin_data(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_email', %s, true)", (user["email"],))
            cur.execute(
                "SELECT id,event_type,event_subtype,occurred_at,recorded_at,original_timezone,source_type,source_module,"
                "context_json,self_report_json,safety_json,consent_json,provenance_json,status,exclude_from_twin_processing "
                "FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at",
                (user["email"],),
            )
            events = cur.fetchall()
            cur.execute(
                "SELECT checkin.id,checkin.checkin_type,checkin.overall_state,checkin.energy_level,checkin.stress_level,"
                "checkin.sleep_quality,checkin.connection_with_god,checkin.connection_with_people,checkin.self_report_json,"
                "checkin.sensitive_content_id,checkin.occurred_at,checkin.processing_preference "
                "FROM formation_twin_daily_checkins checkin WHERE checkin.email=%s AND checkin.deleted_at IS NULL ORDER BY checkin.occurred_at",
                (user["email"],),
            )
            checkins = cur.fetchall()
            cur.execute(
                "SELECT journal.id,journal.journal_type,journal.title,journal.sensitive_content_id,journal.occurred_at,journal.processing_preference "
                "FROM formation_twin_journals journal WHERE journal.email=%s AND journal.deleted_at IS NULL AND journal.status<>'SUPERSEDED' ORDER BY journal.occurred_at",
                (user["email"],),
            )
            journals = cur.fetchall()
            cur.execute(
                "SELECT voice.id,voice.transcript_sensitive_content_id,voice.transcription_status,voice.detected_language,voice.user_confirmed,voice.created_at "
                "FROM formation_twin_voice_journals voice WHERE voice.email=%s AND voice.deleted_at IS NULL ORDER BY voice.created_at",
                (user["email"],),
            )
            voices = cur.fetchall()
            cur.execute(
                "SELECT id,emotion_label,custom_label,intensity,source_kind,statement_type,occurred_at,confidence,user_review_status,processing_status,life_event_id "
                "FROM formation_twin_emotion_observations WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at",
                (user["email"],),
            )
            emotion_observations = cur.fetchall()
            cur.execute(
                "SELECT id,snapshot_type,window_start,window_end,data_status,data_coverage_json,user_reported_state_json,rule_derived_state_json,current_candidates_json,limitations_json,version,engine_version,created_at "
                "FROM formation_twin_emotional_snapshots WHERE email=%s AND superseded_at IS NULL ORDER BY created_at",
                (user["email"],),
            )
            emotional_snapshots = cur.fetchall()
            cur.execute(
                "SELECT id,title,episode_type,creation_method,started_at,ended_at,life_domains,primary_emotions,secondary_emotions,status,user_review_status "
                "FROM formation_twin_emotional_episodes WHERE email=%s AND deleted_at IS NULL ORDER BY started_at",
                (user["email"],),
            )
            emotional_episodes = cur.fetchall()
            cur.execute(
                "SELECT id,node_type,content,life_event_id,source_kind,statement_type,scope,confidence,alternatives_json,evidence_json,user_review_status,processing_status,expires_at,occurred_at,created_at "
                "FROM formation_twin_formation_nodes WHERE email=%s AND deleted_at IS NULL ORDER BY created_at",
                (user["email"],),
            )
            formation_nodes = cur.fetchall()
            cur.execute(
                "SELECT id,title,life_event_id,creation_method,scope,completeness,user_review_status,processing_status,limitations_json,alternative_of_chain_id,excluded_from_context,version,created_at "
                "FROM formation_twin_formation_chains WHERE email=%s AND deleted_at IS NULL ORDER BY created_at",
                (user["email"],),
            )
            formation_chains = cur.fetchall()
            cur.execute(
                "SELECT id,snapshot_type,window_start,window_end,data_status,user_reported_json,observed_relations_json,confirmed_patterns_json,pending_hypotheses_json,grace_recovery_json,directions_json,tensions_json,reflective_questions_json,limitations_json,coverage_json,version,engine_version,created_at "
                "FROM formation_twin_formation_snapshots WHERE email=%s AND superseded_at IS NULL ORDER BY created_at",
                (user["email"],),
            )
            formation_snapshots = cur.fetchall()
            cur.execute(
                "SELECT id,title,pattern_type,description,scope_json,lifecycle_status,confidence_json,evidence_quality,"
                "source_kind,statement_type,user_review_status,alternative_explanations_json,limitations_json,"
                "first_observed_at,last_observed_at,last_confirmed_at,review_due_at,version,engine_version,created_at "
                "FROM formation_twin_patterns WHERE email=%s AND deleted_at IS NULL ORDER BY created_at",
                (user["email"],),
            )
            temporal_patterns = cur.fetchall()
            cur.execute(
                "SELECT id,title,season_type,started_at,ended_at,time_precision,life_domains,roles_json,user_description,"
                "source_kind,user_review_status,active,created_at FROM formation_twin_life_seasons "
                "WHERE email=%s AND deleted_at IS NULL ORDER BY started_at",
                (user["email"],),
            )
            life_seasons = cur.fetchall()
            cur.execute(
                "SELECT id,review_type,window_start,window_end,review_payload_json,status,created_at,completed_at,skipped_at "
                "FROM formation_twin_pattern_reviews WHERE email=%s ORDER BY created_at",
                (user["email"],),
            )
            pattern_reviews = cur.fetchall()
            reflection_exports = {}
            for export_key, table_name in (
                ("contexts", "formation_twin_reflection_contexts"),
                ("mirrors", "formation_twin_reflection_mirrors"),
                ("questions", "formation_twin_reflection_questions"),
                ("answers", "formation_twin_reflection_answers"),
                ("proposals", "formation_twin_intervention_proposals"),
                ("decisions", "formation_twin_intervention_decisions"),
                ("executions", "formation_twin_intervention_executions"),
                ("effect_reviews", "formation_twin_intervention_effect_reviews"),
                ("preferences", "formation_twin_intervention_preferences"),
                ("weekly_reviews", "formation_twin_weekly_reviews"),
                ("settings", "formation_twin_reflection_settings"),
            ):
                cur.execute(
                    f"SELECT to_jsonb(item)-'email' FROM {table_name} item WHERE email=%s ORDER BY created_at",
                    (user["email"],),
                )
                reflection_exports[export_key] = [row[0] for row in cur.fetchall()]
            protection_exports = {}
            for export_key, table_name in (
                ("temptation_cycles", "formation_twin_temptation_cycles"),
                ("cycle_nodes", "formation_twin_temptation_cycle_nodes"),
                ("cycle_edges", "formation_twin_temptation_cycle_edges"),
                ("risk_conditions", "formation_twin_risk_conditions"),
                ("risk_snapshots", "formation_twin_risk_snapshots"),
                ("early_warnings", "formation_twin_early_warnings"),
                ("warning_feedback", "formation_twin_warning_feedback"),
                ("protection_actions", "formation_twin_protection_actions"),
                ("protection_plans", "formation_twin_protection_plans"),
                ("support_contacts", "formation_twin_support_contacts"),
                ("support_requests", "formation_twin_support_requests"),
                ("recovery_records", "formation_twin_recovery_records"),
                ("recovery_reviews", "formation_twin_recovery_reviews"),
                ("risk_settings", "formation_twin_risk_settings"),
            ):
                cur.execute(
                    f"SELECT to_jsonb(item)-'email'-'tenant_id'-'profile_id' FROM {table_name} item WHERE email=%s ORDER BY created_at",
                    (user["email"],),
                )
                protection_exports[export_key] = [row[0] for row in cur.fetchall()]
            checkin_export = [{
                "id": str(row[0]), "checkin_type": row[1], "overall_state": row[2], "energy_level": row[3],
                "stress_level": row[4], "sleep_quality": row[5], "connection_with_god": row[6],
                "connection_with_people": row[7], "self_report": row[8] or {},
                "private_note": _read_sensitive(cur, content_id=str(row[9]), email=user["email"]) if row[9] else "",
                "occurred_at": row[10].isoformat(), "processing_preference": row[11],
            } for row in checkins]
            journal_export = [{
                "id": str(row[0]), "journal_type": row[1], "title": row[2] or "",
                "content": _read_sensitive(cur, content_id=str(row[3]), email=user["email"]),
                "occurred_at": row[4].isoformat(), "processing_preference": row[5],
            } for row in journals]
            voice_export = [{
                "id": str(row[0]),
                "transcript": _read_sensitive(cur, content_id=str(row[1]), email=user["email"]),
                "status": row[2], "detected_language": row[3], "user_confirmed": row[4],
                "created_at": row[5].isoformat(),
            } for row in voices]
        return {
            "ok": True,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "events": [{
                "event_id": str(row[0]), "event_type": row[1], "event_subtype": row[2],
                "occurred_at": row[3].isoformat(), "recorded_at": row[4].isoformat(), "timezone": row[5],
                "source_type": row[6], "source_module": row[7], "context": row[8] or {},
                "self_report": row[9] or {}, "safety": row[10] or {}, "consent": row[11] or {},
                "provenance": row[12] or {}, "status": row[13], "excluded": row[14],
            } for row in events],
            "checkins": checkin_export,
            "journals": journal_export,
            "voice_journals": voice_export,
            "emotion_observations": [{
                "id": str(row[0]), "emotion_label": row[1], "custom_label": row[2], "intensity": row[3],
                "source_kind": row[4], "statement_type": row[5], "occurred_at": row[6].isoformat(),
                "confidence": float(row[7]) if row[7] is not None else None, "user_review_status": row[8],
                "processing_status": row[9], "life_event_id": str(row[10]) if row[10] else None,
            } for row in emotion_observations],
            "emotional_snapshots": [{
                "id": str(row[0]), "snapshot_type": row[1], "window_start": row[2].isoformat(),
                "window_end": row[3].isoformat(), "data_status": row[4], "data_coverage": row[5],
                "user_reported": row[6], "rule_derived": row[7], "possible_model_candidates": row[8],
                "limitations": row[9], "version": row[10], "engine_version": row[11], "created_at": row[12].isoformat(),
            } for row in emotional_snapshots],
            "emotional_episodes": [{
                "id": str(row[0]), "title": row[1], "episode_type": row[2], "creation_method": row[3],
                "started_at": row[4].isoformat(), "ended_at": row[5].isoformat() if row[5] else None,
                "life_domains": row[6], "primary_emotions": row[7], "secondary_emotions": row[8],
                "status": row[9], "user_review_status": row[10],
            } for row in emotional_episodes],
            "formation_nodes": [{
                "id": str(row[0]), "node_type": row[1], "content": row[2],
                "life_event_id": str(row[3]) if row[3] else None, "source_kind": row[4],
                "statement_type": row[5], "scope": row[6],
                "confidence": float(row[7]) if row[7] is not None else None,
                "alternatives": row[8], "evidence": row[9], "user_review_status": row[10],
                "processing_status": row[11], "expires_at": row[12].isoformat() if row[12] else None,
                "occurred_at": row[13].isoformat(), "created_at": row[14].isoformat(),
            } for row in formation_nodes],
            "formation_chains": [{
                "id": str(row[0]), "title": row[1], "life_event_id": str(row[2]) if row[2] else None,
                "creation_method": row[3], "scope": row[4], "completeness": float(row[5]),
                "user_review_status": row[6], "processing_status": row[7], "limitations": row[8],
                "alternative_of_chain_id": str(row[9]) if row[9] else None,
                "excluded_from_context": row[10], "version": row[11], "created_at": row[12].isoformat(),
            } for row in formation_chains],
            "formation_snapshots": [{
                "id": str(row[0]), "snapshot_type": row[1], "window_start": row[2].isoformat(),
                "window_end": row[3].isoformat(), "data_status": row[4], "user_reported": row[5],
                "observed_relations": row[6], "confirmed_patterns": row[7], "pending_hypotheses": row[8],
                "grace_and_recovery": row[9], "formation_directions": row[10], "tensions": row[11],
                "reflective_questions": row[12], "limitations": row[13], "record_coverage": row[14],
                "version": row[15], "engine_version": row[16], "created_at": row[17].isoformat(),
            } for row in formation_snapshots],
            "temporal_patterns": [{
                "id": str(row[0]), "title": row[1], "pattern_type": row[2], "description": row[3],
                "scope": row[4], "lifecycle_status": row[5], "confidence": row[6], "evidence_quality": row[7],
                "source_kind": row[8], "statement_type": row[9], "user_review_status": row[10],
                "alternative_explanations": row[11], "limitations": row[12],
                "first_observed_at": row[13].isoformat(), "last_observed_at": row[14].isoformat(),
                "last_confirmed_at": row[15].isoformat() if row[15] else None,
                "review_due_at": row[16].isoformat(), "version": row[17], "engine_version": row[18],
                "created_at": row[19].isoformat(),
            } for row in temporal_patterns],
            "life_seasons": [{
                "id": str(row[0]), "title": row[1], "season_type": row[2],
                "started_at": row[3].isoformat(), "ended_at": row[4].isoformat() if row[4] else None,
                "time_precision": row[5], "life_domains": row[6], "roles": row[7],
                "user_description": row[8], "source_kind": row[9], "user_review_status": row[10],
                "active": row[11], "created_at": row[12].isoformat(),
            } for row in life_seasons],
            "pattern_reviews": [{
                "id": str(row[0]), "review_type": row[1], "window_start": row[2].isoformat(),
                "window_end": row[3].isoformat(), "review": row[4], "status": row[5],
                "created_at": row[6].isoformat(), "completed_at": row[7].isoformat() if row[7] else None,
                "skipped_at": row[8].isoformat() if row[8] else None,
            } for row in pattern_reviews],
            "reflection_intervention": reflection_exports,
            "temptation_risk_protection": protection_exports,
        }
    finally:
        _state["release_db"](conn)


@router.delete("/erase")
def erase_formation_twin_data(request: Request, body: EraseBody) -> dict:
    user = _require_user(request)
    tenant_id, profile_id = _identity(user["email"])
    try:
        from formation_twin.formation_graph import erase_profile_graph
        graph_erasure = erase_profile_graph(tenant_id=tenant_id, profile_id=profile_id)
    except Exception:
        graph_erasure = {"status": "UNAVAILABLE", "deleted": 0}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_email', %s, true)", (user["email"],))
            for statement in (
                "DELETE FROM formation_twin_recovery_reviews WHERE email=%s",
                "DELETE FROM formation_twin_warning_feedback WHERE email=%s",
                "DELETE FROM formation_twin_support_requests WHERE email=%s",
                "DELETE FROM formation_twin_protection_actions WHERE email=%s",
                "DELETE FROM formation_twin_early_warnings WHERE email=%s",
                "DELETE FROM formation_twin_risk_snapshots WHERE email=%s",
                "DELETE FROM formation_twin_risk_conditions WHERE email=%s",
                "DELETE FROM formation_twin_temptation_cycle_edges WHERE email=%s",
                "DELETE FROM formation_twin_temptation_cycle_nodes WHERE email=%s",
                "DELETE FROM formation_twin_protection_plans WHERE email=%s",
                "DELETE FROM formation_twin_support_contacts WHERE email=%s",
                "DELETE FROM formation_twin_temptation_cycles WHERE email=%s",
                "DELETE FROM formation_twin_recovery_records WHERE email=%s",
                "DELETE FROM formation_twin_risk_settings WHERE email=%s",
                "DELETE FROM formation_twin_weekly_reviews WHERE email=%s",
                "DELETE FROM formation_twin_intervention_effect_reviews WHERE email=%s",
                "DELETE FROM formation_twin_intervention_executions WHERE email=%s",
                "DELETE FROM formation_twin_intervention_decisions WHERE email=%s",
                "DELETE FROM formation_twin_intervention_proposals WHERE email=%s",
                "DELETE FROM formation_twin_reflection_answers WHERE email=%s",
                "DELETE FROM formation_twin_reflection_questions WHERE email=%s",
                "DELETE FROM formation_twin_reflection_mirrors WHERE email=%s",
                "DELETE FROM formation_twin_reflection_contexts WHERE email=%s",
                "DELETE FROM formation_twin_intervention_preferences WHERE email=%s",
                "DELETE FROM formation_twin_reflection_settings WHERE email=%s",
                "DELETE FROM formation_twin_temporal_graph_syncs WHERE email=%s",
                "DELETE FROM formation_twin_pattern_processing_checkpoints WHERE email=%s",
                "DELETE FROM formation_twin_pattern_rebuild_jobs WHERE email=%s",
                "DELETE FROM formation_twin_long_term_snapshots WHERE email=%s",
                "DELETE FROM formation_twin_interpretation_preferences WHERE email=%s",
                "DELETE FROM formation_twin_pattern_reviews WHERE email=%s",
                "DELETE FROM formation_twin_trajectory_points WHERE email=%s",
                "DELETE FROM formation_twin_trajectories WHERE email=%s",
                "DELETE FROM formation_twin_pattern_life_seasons WHERE email=%s",
                "DELETE FROM formation_twin_life_seasons WHERE email=%s",
                "DELETE FROM formation_twin_pattern_lifecycle_events WHERE email=%s",
                "DELETE FROM formation_twin_pattern_confidence_history WHERE email=%s",
                "DELETE FROM formation_twin_pattern_evidence WHERE email=%s",
                "DELETE FROM formation_twin_patterns WHERE email=%s",
                "DELETE FROM formation_twin_event_cluster_members WHERE email=%s",
                "DELETE FROM formation_twin_event_clusters WHERE email=%s",
                "DELETE FROM formation_twin_temporal_windows WHERE email=%s",
                "DELETE FROM formation_twin_temporal_settings WHERE email=%s",
                "DELETE FROM formation_twin_graph_syncs WHERE email=%s",
                "DELETE FROM formation_twin_formation_reviews WHERE email=%s",
                "DELETE FROM formation_twin_chain_edges WHERE email=%s",
                "DELETE FROM formation_twin_chain_nodes WHERE email=%s",
                "DELETE FROM formation_twin_formation_edges WHERE email=%s",
                "DELETE FROM formation_twin_formation_evidence WHERE email=%s",
                "DELETE FROM formation_twin_formation_snapshots WHERE email=%s",
                "DELETE FROM formation_twin_formation_chains WHERE email=%s",
                "DELETE FROM formation_twin_formation_nodes WHERE email=%s",
                "DELETE FROM formation_twin_formation_model_runs WHERE email=%s",
                "DELETE FROM formation_twin_identity_statements WHERE email=%s",
                "DELETE FROM formation_twin_interpretations WHERE email=%s",
                "DELETE FROM formation_twin_belief_statements WHERE email=%s",
                "DELETE FROM formation_twin_desire_observations WHERE email=%s",
                "DELETE FROM formation_twin_fear_observations WHERE email=%s",
                "DELETE FROM formation_twin_temptation_observations WHERE email=%s",
                "DELETE FROM formation_twin_behavior_observations WHERE email=%s",
                "DELETE FROM formation_twin_outcome_observations WHERE email=%s",
                "DELETE FROM formation_twin_formation_settings WHERE email=%s",
                "DELETE FROM formation_twin_emotion_evidence WHERE email=%s",
                "DELETE FROM formation_twin_inference_reviews WHERE email=%s",
                "DELETE FROM formation_twin_episode_events WHERE email=%s",
                "DELETE FROM formation_twin_emotional_snapshots WHERE email=%s",
                "DELETE FROM formation_twin_emotion_rule_results WHERE email=%s",
                "DELETE FROM formation_twin_emotion_model_runs WHERE email=%s",
                "DELETE FROM formation_twin_body_observations WHERE email=%s",
                "DELETE FROM formation_twin_energy_stress_observations WHERE email=%s",
                "DELETE FROM formation_twin_emotion_observations WHERE email=%s",
                "DELETE FROM formation_twin_emotional_episodes WHERE email=%s",
                "DELETE FROM formation_twin_emotion_settings WHERE email=%s",
                "DELETE FROM formation_twin_event_revisions WHERE email=%s",
                "DELETE FROM formation_twin_ingestion_receipts WHERE email=%s",
                "DELETE FROM formation_twin_daily_checkins WHERE email=%s",
                "DELETE FROM formation_twin_journals WHERE email=%s",
                "DELETE FROM formation_twin_voice_journals WHERE email=%s",
                "DELETE FROM formation_twin_life_events WHERE email=%s",
                "DELETE FROM formation_twin_sensitive_contents WHERE email=%s",
                "DELETE FROM formation_twin_ingestion_failures WHERE email=%s",
                "DELETE FROM formation_twin_source_connections WHERE email=%s",
            ):
                cur.execute(statement, (user["email"],))
            cur.execute(
                "INSERT INTO domain_events (aggregate_type,aggregate_id,event_type,payload) VALUES (%s,%s,%s,%s)",
                ("formation_twin", user["email"], "formation_twin.user_data_erased", Json({"tenant_id": tenant_id})),
            )
            conn.commit()
        return {
            "ok": True,
            "erased": True,
            "complete": graph_erasure.get("status") == "ERASED",
            "graph_erasure": graph_erasure,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


def _set_source(source: str, request: Request, status: str) -> dict:
    if source not in SOURCE_ADAPTERS:
        raise HTTPException(status_code=404, detail="Unknown source")
    data_sources(request)
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE formation_twin_source_connections SET status=%s,updated_at=now() WHERE email=%s AND source_module=%s", (status, user["email"], source))
            conn.commit()
        return {"ok": True, "source_module": source, "status": status}
    finally:
        _state["release_db"](conn)


@router.put("/data-sources/{source}/pause")
def pause_source(source: str, request: Request) -> dict:
    return _set_source(source, request, "PAUSED")


@router.put("/data-sources/{source}/resume")
def resume_source(source: str, request: Request) -> dict:
    return _set_source(source, request, "ACTIVE")


@router.post("/internal/module-events")
def ingest_module_event(
    body: ModuleEventBody,
    x_formation_twin_service_key: str | None = Header(default=None),
) -> dict:
    expected = os.getenv("FORMATION_TWIN_SERVICE_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Formation Twin service identity is not configured")
    if not x_formation_twin_service_key or not hmac.compare_digest(
        hashlib.sha256(x_formation_twin_service_key.encode()).digest(),
        hashlib.sha256(expected.encode()).digest(),
    ):
        raise HTTPException(status_code=401, detail="Invalid service identity")
    if body.source_module not in SOURCE_ADAPTERS:
        raise HTTPException(status_code=422, detail="Unsupported source module")
    email = body.subject_user_id
    tenant_id, profile_id = _identity(email)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM formation_twin_source_connections WHERE email=%s AND source_module=%s", (email, body.source_module))
            connection = cur.fetchone()
            if not connection or connection[0] != "ACTIVE":
                _write_receipt(cur, tenant_id=tenant_id, email=email, source_type=SOURCE_ADAPTERS[body.source_module]["source_type"].value,
                               source_event_id=body.source_event_id, client_event_id=None, canonical_event_id=None,
                               status=LifeEventStatus.BLOCKED_NO_CONSENT.value, failure_code="SOURCE_NOT_AUTHORIZED")
                conn.commit()
                return {"ok": True, "status": "BLOCKED_NO_CONSENT"}
            accepted, discarded = minimize_module_payload(body.source_module, body.payload)
            adapter = SOURCE_ADAPTERS[body.source_module]
            idem = idempotency_key(tenant_id=tenant_id, user_id=email, source_type=adapter["source_type"].value, client_event_id=body.source_event_id)
            event = normalize_event(
                tenant_id=tenant_id, profile_id=profile_id, user_id=email, event_type=adapter["event_type"],
                source_type=adapter["source_type"], source_module=body.source_module, source_record_id=None,
                source_event_id=body.source_event_id, occurred_at=_aware(body.occurred_at, body.timezone), timezone_name=body.timezone,
                context={}, self_report=None, observed_facts=[accepted], content_reference=None,
                processing_preference=ProcessingPreference.ALLOW_FUTURE_ANALYSIS, accepted_fields=sorted(accepted), discarded_fields=discarded,
            )
            event_id = _persist_event(cur, event=event, client_event_id=body.source_event_id, idem_key=idem)
            cur.execute("UPDATE formation_twin_source_connections SET last_event_received_at=now(),last_successful_sync_at=now() WHERE email=%s AND source_module=%s", (email, body.source_module))
            _write_receipt(cur, tenant_id=tenant_id, email=email, source_type=adapter["source_type"].value,
                           source_event_id=body.source_event_id, client_event_id=None, canonical_event_id=event_id,
                           status=LifeEventStatus.ACCEPTED.value)
            conn.commit()
        return {"ok": True, "status": "ACCEPTED", "event_id": event_id, "discarded_field_names": discarded}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)
