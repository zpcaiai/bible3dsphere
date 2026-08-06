"""Authenticated, fail-closed Sunday School AI-formation API (Batches 01-12)."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from psycopg2.extras import Json, RealDictCursor

from ai_formation import BATCHES, MODULE_MANIFEST, TRACKS
from ai_formation.catalog import RELEASE_GATES
from ai_formation.content_audit import REQUIRED_REVIEW_ATTESTATIONS
from ai_formation.contracts import (
    ContentPublicationRequest,
    ContentReviewCreate,
    RecordEnvelopeCreate,
    RecordEnvelopePatch,
    RecordStateTransition,
    RecordType,
    ReleaseDecisionCreate,
    ReleaseEvidenceV1,
    SafetyCheckRequest,
    ScenarioChoiceRequest,
    ScenarioSessionV1,
    ScenarioStartRequest,
    validate_record_payload,
)
from ai_formation.policy import assess_pastoral_safety, evaluate_release_evidence
from ai_formation.spec_registry import SpecValidationError, resolve_schema, schema_catalog, validate_spec_payload


router = APIRouter(prefix="/api/v1/sunday-school/ai-formation", tags=["sunday-school-ai-formation"])
_state: dict[str, Any] = {}
_DB_STATES = {"draft", "active", "paused", "completed", "archived", "deleted"}
_REVIEW_AUTHORITY_ENV = {
    "theology_reviewer": "AI_FORMATION_THEOLOGY_REVIEWERS",
    "pastoral_reviewer": "AI_FORMATION_PASTORAL_REVIEWERS",
    "child_safety_reviewer": "AI_FORMATION_CHILD_SAFETY_REVIEWERS",
    "rights_reviewer": "AI_FORMATION_PRIVACY_RIGHTS_REVIEWERS",
    "content_reviewer": "AI_FORMATION_CONTENT_REVIEWERS",
    "accessibility_reviewer": "AI_FORMATION_ACCESSIBILITY_REVIEWERS",
    "release_reviewer": "AI_FORMATION_RELEASE_AUTHORITIES",
}
_HUMAN_GATE_AUTHORITY = {
    "theology": "AI_FORMATION_THEOLOGY_REVIEWERS",
    "pastoral_safety": "AI_FORMATION_PASTORAL_REVIEWERS",
    "child_safety": "AI_FORMATION_CHILD_SAFETY_REVIEWERS",
    "privacy_security": "AI_FORMATION_PRIVACY_RIGHTS_REVIEWERS",
    "accessibility_manual": "AI_FORMATION_ACCESSIBILITY_REVIEWERS",
    "content_quality": "AI_FORMATION_CONTENT_REVIEWERS",
}


def init_ai_formation_router(*, get_db, release_db, get_session_user, is_admin=None) -> None:
    _state.update(locals())


def _enabled() -> bool:
    return os.getenv("SUNDAY_SCHOOL_AI_FORMATION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _user(request: Request) -> dict[str, Any]:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _admin(request: Request) -> dict[str, Any]:
    user = _user(request)
    checker = _state.get("is_admin")
    if not checker or not checker(user["email"]):
        raise HTTPException(status_code=403, detail="AI formation reviewer permission required")
    return user


def _authorized_email(email: str, env_name: str) -> bool:
    allowed = {
        item.strip().casefold()
        for item in os.getenv(env_name, "").split(",")
        if item.strip()
    }
    return email.strip().casefold() in allowed


def _require_named_authority(email: str, env_name: str, detail: str) -> None:
    if not _authorized_email(email, env_name):
        raise HTTPException(status_code=403, detail=detail)


def _require_enabled() -> None:
    if not _enabled():
        raise HTTPException(status_code=404, detail="AI formation module is not enabled")


def _identity(email: str) -> tuple[str, str]:
    normalized = email.strip().lower()
    return f"personal:{normalized}", normalized


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email',%s,true)", (email,))


def _write_audit(
    cur, *, actor_email: str, action: str, resource_type: str,
    resource_id: str, reason_codes: list[str], owner_email: str | None = None,
) -> None:
    owner = (owner_email or actor_email).strip().lower()
    tenant_id, owner = _identity(owner)
    _owner(cur, owner)
    cur.execute(
        "INSERT INTO sunday_school_ai_formation_audit"
        "(tenant_id,email,actor_email,action,resource_type,resource_id,reason_codes_json) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s)",
        (tenant_id, owner, actor_email, action, resource_type, resource_id, Json(reason_codes)),
    )


def _connection():
    if not _state.get("get_db"):
        raise HTTPException(status_code=503, detail="AI formation persistence unavailable")
    return _state["get_db"]()


def _saved_learner_context(cur, tenant_id: str, email: str) -> dict[str, str] | None:
    cur.execute(
        "SELECT COALESCE(payload_json->>'age_band',payload_json->>'ageBand') AS age_band,"
        "COALESCE(payload_json->>'role','learner') AS role "
        "FROM sunday_school_ai_formation_records "
        "WHERE tenant_id=%s AND email=%s AND deleted_at IS NULL "
        "AND (record_type='learner_context' OR schema_name='learner-context') "
        "ORDER BY updated_at DESC LIMIT 1",
        (tenant_id, email),
    )
    row = cur.fetchone()
    return dict(row) if row and row.get("age_band") else None


def _release(conn) -> None:
    _state["release_db"](conn)


def _idempotent_replay(existing: dict[str, Any] | None, *, payload_hash: str, record_type: str) -> dict[str, Any] | None:
    if not existing:
        return None
    if existing.get("payload_hash") != payload_hash or existing.get("record_type") != record_type:
        raise HTTPException(status_code=409, detail="Idempotency key was already used for a different record")
    replay = dict(existing)
    replay.pop("payload_hash", None)
    return replay


def _normalize_record(body: RecordEnvelopeCreate, *, tenant_id: str, email: str) -> tuple[str | None, str | None, str, dict[str, Any]]:
    schema_name = body.schema_name or body.record_type
    try:
        item = resolve_schema(schema_name)
    except SpecValidationError:
        try:
            legacy_type = RecordType(body.record_type)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Unknown record schema: {schema_name}") from exc
        normalized = validate_record_payload(legacy_type, body.payload)
        return None, None, str(normalized.get("version", "1.0.0")), normalized
    try:
        batch_id, version, normalized = validate_spec_payload(
            item["key"], body.payload, tenant_id=tenant_id, learner_id=email
        )
    except SpecValidationError as exc:
        detail = {"message": str(exc), "path": exc.path, "schema": item["key"]}
        raise HTTPException(status_code=422, detail=detail) from exc
    return batch_id, item["key"], version, normalized


def _validate_existing(schema_name: str | None, record_type: str, payload: dict[str, Any], *, tenant_id: str, email: str) -> tuple[str, dict[str, Any]]:
    if schema_name:
        try:
            _batch, version, normalized = validate_spec_payload(
                schema_name, payload, tenant_id=tenant_id, learner_id=email
            )
            return version, normalized
        except SpecValidationError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "path": exc.path, "schema": schema_name}) from exc
    try:
        normalized = validate_record_payload(RecordType(record_type), payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unknown stored record type") from exc
    return str(normalized.get("version", "1.0.0")), normalized


@router.get("/manifest")
def manifest(request: Request) -> dict[str, Any]:
    _user(request)
    return {
        "ok": True,
        "enabled": _enabled(),
        "manifest": MODULE_MANIFEST,
        "tracks": TRACKS,
        "batches": BATCHES,
        "schemaCount": len(schema_catalog()),
        "contentPolicy": {
            "learnerContentRequiresApprovedReview": True,
            "generatedContentAutoPublishAllowed": False,
            "currentSeedState": "review_pending",
        },
    }


@router.get("/schemas")
def schemas(request: Request, batch_id: str | None = Query(default=None, pattern=r"^(0[1-9]|1[0-2])$")) -> dict[str, Any]:
    _user(request)
    return {"ok": True, "schemas": schema_catalog(batch_id=batch_id, include_schema=True)}


@router.post("/safety/check")
def safety_check(body: SafetyCheckRequest, request: Request) -> dict[str, Any]:
    _user(request)
    decision = assess_pastoral_safety(body.text, age_band=body.age_band, locale=body.locale)
    return {"ok": True, "decision": decision, "inputPersisted": False, "analyticsContainsInput": False}


@router.post("/records", status_code=201)
def create_record(body: RecordEnvelopeCreate, request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    batch_id, schema_name, schema_version, normalized = _normalize_record(body, tenant_id=tenant_id, email=email)
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    record_id = str(uuid.uuid4())
    requested_status = str(normalized.get("status", "active"))
    status = requested_status if requested_status in _DB_STATES - {"deleted"} else "active"
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT id,record_type,schema_name,payload_json,payload_hash,status,revision,created_at "
                "FROM sunday_school_ai_formation_records "
                "WHERE tenant_id=%s AND email=%s AND idempotency_key=%s AND deleted_at IS NULL",
                (tenant_id, email, body.idempotency_key),
            )
            duplicate = _idempotent_replay(cur.fetchone(), payload_hash=payload_hash, record_type=body.record_type)
            if duplicate:
                conn.commit()
                return {"ok": True, "record": duplicate, "idempotentReplay": True}
            cur.execute(
                "INSERT INTO sunday_school_ai_formation_records"
                "(id,tenant_id,email,batch_id,record_type,schema_name,schema_version,payload_json,payload_hash,status,revision,idempotency_key,retention_until) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,NOW()+(%s * INTERVAL '1 day')) "
                "RETURNING id,batch_id,record_type,schema_name,schema_version,payload_json,status,revision,created_at,retention_until",
                (
                    record_id, tenant_id, email, batch_id, body.record_type, schema_name, schema_version,
                    Json(normalized), payload_hash, status, body.idempotency_key, body.retention_days,
                ),
            )
            record = dict(cur.fetchone())
            _write_audit(
                cur, actor_email=email, action="record.created", resource_type=body.record_type,
                resource_id=record_id, reason_codes=["USER_EXPLICIT_SUBMISSION"],
            )
            conn.commit()
        return {"ok": True, "record": record, "idempotentReplay": False}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/records")
def list_records(
    request: Request,
    record_type: str | None = None,
    batch_id: str | None = Query(default=None, pattern=r"^(0[1-9]|1[0-2])$"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT id,batch_id,record_type,schema_name,schema_version,payload_json,status,revision,created_at,updated_at,retention_until "
                "FROM sunday_school_ai_formation_records "
                "WHERE tenant_id=%s AND email=%s AND deleted_at IS NULL "
                "AND (%s IS NULL OR record_type=%s) AND (%s IS NULL OR batch_id=%s) "
                "ORDER BY created_at DESC LIMIT %s",
                (tenant_id, email, record_type, record_type, batch_id, batch_id, limit),
            )
            items = [dict(row) for row in cur.fetchall()]
        return {"ok": True, "records": items}
    finally:
        _release(conn)


@router.patch("/records/{record_id}")
def update_record(record_id: uuid.UUID, body: RecordEnvelopePatch, request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT record_type,schema_name,revision FROM sunday_school_ai_formation_records "
                "WHERE id=%s AND tenant_id=%s AND email=%s AND deleted_at IS NULL FOR UPDATE",
                (str(record_id), tenant_id, email),
            )
            current = cur.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="AI formation record not found")
            if current["revision"] != body.expected_revision:
                raise HTTPException(status_code=409, detail="Record was updated by another request")
            schema_version, normalized = _validate_existing(
                current["schema_name"], current["record_type"], body.payload, tenant_id=tenant_id, email=email
            )
            canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            cur.execute(
                "UPDATE sunday_school_ai_formation_records SET payload_json=%s,payload_hash=%s,schema_version=%s,"
                "revision=revision+1,updated_at=NOW() WHERE id=%s AND revision=%s "
                "RETURNING id,batch_id,record_type,schema_name,schema_version,payload_json,status,revision,updated_at",
                (Json(normalized), payload_hash, schema_version, str(record_id), body.expected_revision),
            )
            updated = dict(cur.fetchone())
            _write_audit(
                cur, actor_email=email, action="record.updated", resource_type=current["record_type"],
                resource_id=str(record_id), reason_codes=["USER_EXPLICIT_UPDATE"],
            )
            conn.commit()
        return {"ok": True, "record": updated}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/records/{record_id}/transition")
def transition_record(record_id: uuid.UUID, body: RecordStateTransition, request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    allowed = {
        ("draft", "activate"): "active", ("active", "pause"): "paused",
        ("paused", "resume"): "active", ("active", "complete"): "completed",
        ("paused", "complete"): "completed", ("draft", "archive"): "archived",
        ("active", "archive"): "archived", ("paused", "archive"): "archived",
        ("completed", "archive"): "archived",
    }
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT status,revision FROM sunday_school_ai_formation_records "
                "WHERE id=%s AND tenant_id=%s AND email=%s AND deleted_at IS NULL FOR UPDATE",
                (str(record_id), tenant_id, email),
            )
            current = cur.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="AI formation record not found")
            if current["revision"] != body.expected_revision:
                raise HTTPException(status_code=409, detail="Record was updated by another request")
            target = allowed.get((current["status"], body.transition))
            if not target:
                raise HTTPException(status_code=409, detail=f"Illegal transition: {current['status']} -> {body.transition}")
            cur.execute(
                "UPDATE sunday_school_ai_formation_records SET status=%s,revision=revision+1,updated_at=NOW(),"
                "paused_at=CASE WHEN %s='paused' THEN NOW() ELSE paused_at END "
                "WHERE id=%s AND revision=%s RETURNING id,status,revision,updated_at",
                (target, target, str(record_id), body.expected_revision),
            )
            updated = dict(cur.fetchone())
            _write_audit(
                cur, actor_email=email, action=f"record.{body.transition}", resource_type="record",
                resource_id=str(record_id), reason_codes=["USER_EXPLICIT_TRANSITION"],
            )
            conn.commit()
        return {"ok": True, "record": updated}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.delete("/records/{record_id}")
def delete_record(record_id: uuid.UUID, request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "UPDATE sunday_school_ai_formation_records SET status='deleted',payload_json='{}'::jsonb,"
                "payload_hash=%s,deleted_at=NOW(),updated_at=NOW(),revision=revision+1 "
                "WHERE id=%s AND tenant_id=%s AND email=%s AND deleted_at IS NULL RETURNING id",
                (hashlib.sha256(b"{}").hexdigest(), str(record_id), tenant_id, email),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="AI formation record not found")
            _write_audit(
                cur, actor_email=email, action="record.deleted", resource_type="record",
                resource_id=str(record_id), reason_codes=["USER_DATA_RIGHT_EXERCISED"],
            )
            conn.commit()
        return {"ok": True, "status": "deleted"}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/data-rights/export")
def export_records(request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT id,batch_id,record_type,schema_name,schema_version,payload_json,status,revision,created_at,updated_at "
                "FROM sunday_school_ai_formation_records WHERE tenant_id=%s AND email=%s AND deleted_at IS NULL "
                "ORDER BY created_at,id",
                (tenant_id, email),
            )
            records = [dict(row) for row in cur.fetchall()]
        return {
            "ok": True, "moduleId": MODULE_MANIFEST["moduleId"], "owner": email,
            "records": records, "excludesOtherPeopleData": True,
        }
    finally:
        _release(conn)


@router.delete("/data-rights/records")
def delete_all_records(request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "UPDATE sunday_school_ai_formation_records SET status='deleted',payload_json='{}'::jsonb,"
                "payload_hash=%s,deleted_at=NOW(),updated_at=NOW(),revision=revision+1 "
                "WHERE tenant_id=%s AND email=%s AND deleted_at IS NULL",
                (hashlib.sha256(b"{}").hexdigest(), tenant_id, email),
            )
            deleted = cur.rowcount
            _write_audit(
                cur, actor_email=email, action="records.deleted_all", resource_type="record_collection",
                resource_id=MODULE_MANIFEST["moduleId"], reason_codes=["USER_DATA_RIGHT_EXERCISED"],
            )
            conn.commit()
        return {"ok": True, "deletedRecords": deleted, "auditMetadataRetained": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/content")
def approved_content(
    request: Request,
    batch_id: str | None = Query(default=None, pattern=r"^(0[1-9]|1[0-2])$"),
    age_band: str | None = Query(default=None, pattern=r"^(0_6|7_12|13_15|16_18|adult)$"),
) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            context = _saved_learner_context(cur, tenant_id, email)
            stored_age_band = context["age_band"] if context else None
            if not stored_age_band:
                return {"ok": True, "content": [], "contextRequired": True}
            if age_band and age_band != stored_age_band:
                raise HTTPException(status_code=403, detail="Requested age band does not match the saved learner context")
            cur.execute(
                "SELECT id,batch_id,content_kind,version,content_sha256,authority_level,age_bands_json,content_json,published_at "
                "FROM sunday_school_ai_formation_content "
                "WHERE review_status='approved' AND published_at IS NOT NULL AND retired_at IS NULL "
                "AND (%s IS NULL OR batch_id=%s) AND age_bands_json ? %s ORDER BY batch_id,id,version",
                (batch_id, batch_id, stored_age_band),
            )
            items = [dict(row) for row in cur.fetchall()]
        return {"ok": True, "content": items, "contextRequired": False, "ageBand": stored_age_band}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


_SCENARIO_AUDIENCE = {
    "0_6": "elementary", "7_12": "elementary", "13_15": "younger_teen",
    "16_18": "older_teen", "adult": "adult",
}
_SCENARIO_CHOICES = (
    {"id": "observe", "label": "观察事实"},
    {"id": "pause", "label": "暂停再选择"},
    {"id": "seek_help", "label": "向可信的人求助"},
    {"id": "repair", "label": "进入责任与修复"},
    {"id": "skip", "label": "跳过这个情境"},
    {"id": "complete", "label": "完成并进入复盘"},
)


def _approved_scenarios(cur, context: dict[str, str]) -> list[dict[str, Any]]:
    cur.execute(
        "SELECT id,version,content_sha256,content_json FROM sunday_school_ai_formation_content "
        "WHERE batch_id='10' AND content_kind='scenario-runtime-scenarios.seed' "
        "AND review_status='approved' AND published_at IS NOT NULL AND retired_at IS NULL "
        "ORDER BY published_at DESC,version DESC"
    )
    audiences = {_SCENARIO_AUDIENCE[context["age_band"]], context.get("role", "learner")}
    results: list[dict[str, Any]] = []
    for row in cur.fetchall():
        for scenario in row["content_json"].get("scenarios", []):
            if audiences.intersection(scenario.get("audience", [])):
                results.append({
                    "id": scenario["id"], "title": scenario["title"], "trigger": scenario["trigger"],
                    "formationTension": scenario["formation_tension"], "safeOutcomes": scenario["safe_outcomes"],
                    "contentId": row["id"], "contentVersion": row["version"], "contentSha256": row["content_sha256"],
                })
    return results


@router.get("/scenarios")
def list_scenarios(request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            context = _saved_learner_context(cur, tenant_id, email)
            if not context:
                return {"ok": True, "scenarios": [], "contextRequired": True}
            return {"ok": True, "scenarios": _approved_scenarios(cur, context), "contextRequired": False}
    finally:
        _release(conn)


@router.post("/scenarios/sessions", status_code=201)
def start_scenario_session(body: ScenarioStartRequest, request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            context = _saved_learner_context(cur, tenant_id, email)
            if not context:
                raise HTTPException(status_code=409, detail="Saved learner context is required before scenarios")
            scenario = next((item for item in _approved_scenarios(cur, context) if item["id"] == body.scenario_id), None)
            if not scenario:
                raise HTTPException(status_code=404, detail="Approved age-appropriate scenario not found")
            payload = ScenarioSessionV1(
                scenario_id=scenario["id"], scenario_version=scenario["contentVersion"],
                current_node_id="opening", choice_ids=[], status="active",
            ).model_dump(mode="json")
            canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            cur.execute(
                "SELECT id,record_type,payload_json,payload_hash,status,revision,created_at "
                "FROM sunday_school_ai_formation_records WHERE tenant_id=%s AND email=%s "
                "AND idempotency_key=%s AND deleted_at IS NULL",
                (tenant_id, email, body.idempotency_key),
            )
            replay = _idempotent_replay(cur.fetchone(), payload_hash=payload_hash, record_type="scenario_session")
            if replay:
                conn.commit()
                return {"ok": True, "session": replay, "scenario": scenario, "choices": _SCENARIO_CHOICES, "idempotentReplay": True}
            session_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO sunday_school_ai_formation_records"
                "(id,tenant_id,email,batch_id,record_type,schema_version,payload_json,payload_hash,status,revision,idempotency_key,retention_until) "
                "VALUES(%s,%s,%s,'10','scenario_session','1.0.0',%s,%s,'active',1,%s,NOW()+(%s * INTERVAL '1 day')) "
                "RETURNING id,payload_json,status,revision,created_at,retention_until",
                (session_id, tenant_id, email, Json(payload), payload_hash, body.idempotency_key, body.retention_days),
            )
            session = dict(cur.fetchone())
            _write_audit(
                cur, actor_email=email, action="scenario.started", resource_type="scenario_session",
                resource_id=session_id, reason_codes=["APPROVED_VERSION_PINNED"],
            )
            conn.commit()
        return {"ok": True, "session": session, "scenario": scenario, "choices": _SCENARIO_CHOICES, "idempotentReplay": False}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/scenarios/sessions/{session_id}/choices")
def choose_scenario_path(session_id: uuid.UUID, body: ScenarioChoiceRequest, request: Request) -> dict[str, Any]:
    _require_enabled()
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT payload_json,status,revision FROM sunday_school_ai_formation_records "
                "WHERE id=%s AND tenant_id=%s AND email=%s AND record_type='scenario_session' "
                "AND deleted_at IS NULL FOR UPDATE",
                (str(session_id), tenant_id, email),
            )
            current = cur.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Scenario session not found")
            if current["revision"] != body.expected_revision:
                raise HTTPException(status_code=409, detail="Scenario session was updated by another request")
            if current["status"] != "active":
                raise HTTPException(status_code=409, detail="Scenario session is not active")
            payload = dict(current["payload_json"])
            choices = [*payload.get("choice_ids", []), body.choice]
            payload["choice_ids"] = choices
            payload["current_node_id"] = body.choice
            status = "active"
            if body.choice in {"skip", "complete"}:
                status = "completed"
                payload["status"] = "completed"
            elif body.choice == "safety_interrupt":
                status = "paused"
                payload["status"] = "safety_interrupted"
            normalized = ScenarioSessionV1.model_validate(payload).model_dump(mode="json")
            canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            cur.execute(
                "UPDATE sunday_school_ai_formation_records SET payload_json=%s,payload_hash=%s,status=%s,"
                "revision=revision+1,updated_at=NOW() WHERE id=%s AND revision=%s "
                "RETURNING id,payload_json,status,revision,updated_at",
                (
                    Json(normalized), hashlib.sha256(canonical.encode("utf-8")).hexdigest(), status,
                    str(session_id), body.expected_revision,
                ),
            )
            session = dict(cur.fetchone())
            _write_audit(
                cur, actor_email=email, action=f"scenario.{body.choice}", resource_type="scenario_session",
                resource_id=str(session_id), reason_codes=["BOUNDED_CHOICE_NO_FREE_TEXT"],
            )
            conn.commit()
        return {"ok": True, "session": session, "rawFreeTextPersisted": False, "personalityProfileGenerated": False}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/content/review-queue")
def content_review_queue(request: Request, batch_id: str | None = None) -> dict[str, Any]:
    _admin(request)
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id,batch_id,content_kind,version,content_sha256,authority_level,review_status,"
                "required_reviews_json,age_bands_json,source_provenance_json,created_by,updated_at,published_at,retired_at "
                "FROM sunday_school_ai_formation_content WHERE (%s IS NULL OR batch_id=%s) "
                "ORDER BY batch_id,id,version",
                (batch_id, batch_id),
            )
            items = [dict(row) for row in cur.fetchall()]
        return {"ok": True, "content": items}
    finally:
        _release(conn)


@router.get("/content/{content_id}/versions/{version}")
def content_version_detail(content_id: str, version: str, request: Request) -> dict[str, Any]:
    _admin(request)
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id,batch_id,content_kind,version,content_sha256,authority_level,review_status,"
                "required_reviews_json,age_bands_json,content_json,source_provenance_json,created_by,"
                "created_at,updated_at,published_at,retired_at "
                "FROM sunday_school_ai_formation_content WHERE id=%s AND version=%s",
                (content_id, version),
            )
            content = cur.fetchone()
            if not content:
                raise HTTPException(status_code=404, detail="Content version not found")
            cur.execute(
                "SELECT id,reviewer_email,reviewer_role,decision,content_sha256,reason_codes_json,note,created_at "
                "FROM sunday_school_ai_formation_content_reviews WHERE content_id=%s AND content_version=%s "
                "ORDER BY created_at DESC",
                (content_id, version),
            )
            reviews = [dict(row) for row in cur.fetchall()]
            latest = _latest_reviews(cur, content_id, version, content["content_sha256"])
            approved_roles = {
                row["reviewer_role"] for row in latest if row["decision"] == "approve"
            }
            required_roles = list(content["required_reviews_json"])
        return {
            "ok": True,
            "content": dict(content),
            "reviews": reviews,
            "reviewSummary": {
                "approvedRoles": sorted(approved_roles),
                "pendingRoles": [role for role in required_roles if role not in approved_roles],
                "requiredAttestations": {
                    role: REQUIRED_REVIEW_ATTESTATIONS[role] for role in required_roles
                },
            },
        }
    finally:
        _release(conn)


def _latest_reviews(cur, content_id: str, version: str, content_sha256: str) -> list[dict[str, Any]]:
    cur.execute(
        "SELECT DISTINCT ON (reviewer_role) reviewer_role,reviewer_email,decision,content_sha256,created_at "
        "FROM sunday_school_ai_formation_content_reviews "
        "WHERE content_id=%s AND content_version=%s AND content_sha256=%s "
        "ORDER BY reviewer_role,created_at DESC",
        (content_id, version, content_sha256),
    )
    return [dict(row) for row in cur.fetchall()]


@router.post("/content/{content_id}/versions/{version}/reviews", status_code=201)
def review_content(content_id: str, version: str, body: ContentReviewCreate, request: Request) -> dict[str, Any]:
    reviewer = _admin(request)
    _require_named_authority(
        reviewer["email"], _REVIEW_AUTHORITY_ENV[body.reviewer_role],
        f"Authenticated reviewer is not authorized for role {body.reviewer_role}",
    )
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT content_sha256,required_reviews_json,created_by FROM sunday_school_ai_formation_content "
                "WHERE id=%s AND version=%s FOR UPDATE",
                (content_id, version),
            )
            content = cur.fetchone()
            if not content:
                raise HTTPException(status_code=404, detail="Content version not found")
            if content["content_sha256"] != body.content_sha256:
                raise HTTPException(status_code=409, detail="Content hash changed; review is stale")
            if reviewer["email"].lower() == str(content["created_by"]).lower():
                raise HTTPException(status_code=409, detail="Author cannot review the same content version")
            if body.reviewer_role not in content["required_reviews_json"]:
                raise HTTPException(status_code=422, detail="Reviewer role is not required for this content")
            if body.decision == "approve":
                required_attestations = set(REQUIRED_REVIEW_ATTESTATIONS[body.reviewer_role])
                supplied_attestations = set(body.reason_codes)
                missing_attestations = sorted(required_attestations - supplied_attestations)
                if missing_attestations:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "message": "Approval is missing required human-review attestations",
                            "missingAttestations": missing_attestations,
                        },
                    )
            cur.execute(
                "INSERT INTO sunday_school_ai_formation_content_reviews"
                "(content_id,content_version,content_sha256,reviewer_email,reviewer_role,decision,reason_codes_json,note) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (
                    content_id, version, body.content_sha256, reviewer["email"], body.reviewer_role,
                    body.decision, Json(body.reason_codes), body.note,
                ),
            )
            review_id = str(cur.fetchone()["id"])
            reviews = _latest_reviews(cur, content_id, version, body.content_sha256)
            approvals = {row["reviewer_role"]: row for row in reviews if row["decision"] == "approve"}
            required = set(content["required_reviews_json"])
            distinct_reviewers = {row["reviewer_email"].lower() for row in approvals.values()}
            approved = required.issubset(approvals) and len(distinct_reviewers) == len(required)
            rejected = any(row["decision"] in {"reject", "request_changes"} for row in reviews)
            status = "approved" if approved and not rejected else "pastoral_review" if reviews else "theology_review"
            cur.execute(
                "UPDATE sunday_school_ai_formation_content SET review_status=%s,updated_at=NOW() WHERE id=%s AND version=%s",
                (status, content_id, version),
            )
            _write_audit(
                cur, actor_email=reviewer["email"], action="content.reviewed", resource_type="content_version",
                resource_id=f"{content_id}@{version}", reason_codes=body.reason_codes,
            )
            conn.commit()
        return {"ok": True, "reviewId": review_id, "reviewStatus": status, "publishable": status == "approved"}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/content/{content_id}/versions/{version}/publish")
def publish_content(content_id: str, version: str, body: ContentPublicationRequest, request: Request) -> dict[str, Any]:
    publisher = _admin(request)
    _require_named_authority(
        publisher["email"], "AI_FORMATION_PUBLISHERS",
        "Authenticated administrator is not an authorized AI formation publisher",
    )
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT content_sha256,review_status,required_reviews_json,created_by "
                "FROM sunday_school_ai_formation_content "
                "WHERE id=%s AND version=%s FOR UPDATE",
                (content_id, version),
            )
            content = cur.fetchone()
            if not content:
                raise HTTPException(status_code=404, detail="Content version not found")
            if content["content_sha256"] != body.content_sha256 or content["review_status"] != "approved":
                raise HTTPException(status_code=409, detail="Only the exact fully approved content hash can publish")
            reviews = _latest_reviews(cur, content_id, version, body.content_sha256)
            approvals = {row["reviewer_role"]: row for row in reviews if row["decision"] == "approve"}
            required = set(content["required_reviews_json"])
            distinct_reviewers = {row["reviewer_email"].lower() for row in approvals.values()}
            if not required.issubset(approvals) or len(distinct_reviewers) != len(required):
                raise HTTPException(status_code=409, detail="Required exact-hash approvals are incomplete or not independent")
            reviewer_emails = {row["reviewer_email"].lower() for row in approvals.values()}
            if publisher["email"].lower() in reviewer_emails or publisher["email"].lower() == str(content["created_by"]).lower():
                raise HTTPException(status_code=409, detail="Publisher must be separate from author and reviewers")
            cur.execute(
                "UPDATE sunday_school_ai_formation_content SET published_at=NOW(),retired_at=NULL,updated_at=NOW() "
                "WHERE id=%s AND version=%s RETURNING published_at",
                (content_id, version),
            )
            published_at = cur.fetchone()["published_at"]
            _write_audit(
                cur, actor_email=publisher["email"], action="content.published", resource_type="content_version",
                resource_id=f"{content_id}@{version}", reason_codes=[body.reason_code],
            )
            conn.commit()
        return {"ok": True, "publishedAt": published_at, "publishedBy": publisher["email"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/content/{content_id}/versions/{version}/retire")
def retire_content(content_id: str, version: str, request: Request) -> dict[str, Any]:
    admin = _admin(request)
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sunday_school_ai_formation_content SET retired_at=NOW(),updated_at=NOW() "
                "WHERE id=%s AND version=%s AND published_at IS NOT NULL AND retired_at IS NULL RETURNING id",
                (content_id, version),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=409, detail="Published active content version not found")
            _write_audit(
                cur, actor_email=admin["email"], action="content.retired", resource_type="content_version",
                resource_id=f"{content_id}@{version}", reason_codes=["AUTHORIZED_RETIREMENT"],
            )
            conn.commit()
        return {"ok": True, "status": "retired", "retiredBy": admin["email"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/certification/status")
def certification_status(
    request: Request,
    artifact_id: str | None = None,
    artifact_version: str | None = None,
    environment: str | None = None,
    artifact_sha256: str | None = None,
) -> dict[str, Any]:
    _admin(request)
    scope_complete = all((artifact_id, artifact_version, environment, artifact_sha256))
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            evidence: list[dict[str, Any]] = []
            if scope_complete:
                cur.execute(
                    "SELECT artifact_id,artifact_version,environment,artifact_sha256,gate,result,command,exit_code,executed_at,human_reviewer "
                    "FROM sunday_school_ai_formation_release_evidence WHERE artifact_id=%s "
                    "AND artifact_version=%s AND environment=%s AND artifact_sha256=%s ORDER BY executed_at ASC",
                    (artifact_id, artifact_version, environment, artifact_sha256),
                )
                evidence = [dict(row) for row in cur.fetchall()]
            cur.execute(
                "SELECT id,artifact_id,artifact_version,environment,artifact_sha256,decision,rollout_percent,authorized_by,rollback_owner,incident_owner,"
                "blocker_snapshot_json,created_at FROM sunday_school_ai_formation_release_decisions "
                "ORDER BY created_at DESC LIMIT 20"
            )
            decisions = [dict(row) for row in cur.fetchall()]
        certification = evaluate_release_evidence(evidence) if scope_complete else {
            "status": "NOT_CERTIFIED", "automatedApproval": False,
            "humanReleaseDecisionRequired": True, "blockers": ["ARTIFACT_SCOPE_REQUIRED"],
            "evaluatedGates": [],
        }
        return {
            "ok": True, "scopeComplete": scope_complete, "certification": certification,
            "requiredGates": RELEASE_GATES, "evidence": evidence, "decisions": decisions,
        }
    finally:
        _release(conn)


@router.post("/certification/evidence", status_code=201)
def add_release_evidence(body: ReleaseEvidenceV1, request: Request) -> dict[str, Any]:
    admin = _admin(request)
    authority_env = _HUMAN_GATE_AUTHORITY.get(body.gate)
    if authority_env:
        if not body.human_reviewer or body.human_reviewer.strip().casefold() != admin["email"].strip().casefold():
            raise HTTPException(status_code=403, detail="Human gate evidence must be submitted by the named reviewer")
        _require_named_authority(
            admin["email"], authority_env,
            f"Authenticated reviewer is not authorized for human gate {body.gate}",
        )
    evidence_id = str(uuid.uuid4())
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sunday_school_ai_formation_release_evidence"
                "(id,artifact_id,artifact_version,environment,artifact_sha256,gate,result,command,exit_code,executed_at,human_reviewer,recorded_by) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    evidence_id, body.artifact_id, body.artifact_version, body.environment,
                    body.artifact_sha256, body.gate, body.result, body.command, body.exit_code,
                    body.executed_at, body.human_reviewer, admin["email"],
                ),
            )
            _write_audit(
                cur, actor_email=admin["email"], action="release.evidence_recorded", resource_type="release_evidence",
                resource_id=evidence_id, reason_codes=[body.gate, body.result],
            )
            conn.commit()
        return {"ok": True, "evidenceId": evidence_id, "releaseAutomaticallyApproved": False}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/certification/release-decisions", status_code=201)
def create_release_decision(body: ReleaseDecisionCreate, request: Request) -> dict[str, Any]:
    admin = _admin(request)
    _require_named_authority(
        admin["email"], "AI_FORMATION_RELEASE_AUTHORITIES",
        "Authenticated administrator is not an authorized AI formation release authority",
    )
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT artifact_id,artifact_version,environment,artifact_sha256,gate,result,command,exit_code,executed_at,human_reviewer "
                "FROM sunday_school_ai_formation_release_evidence "
                "WHERE artifact_id=%s AND artifact_version=%s AND environment=%s AND artifact_sha256=%s "
                "ORDER BY executed_at ASC",
                (body.artifact_id, body.artifact_version, body.environment, body.artifact_sha256),
            )
            certification = evaluate_release_evidence([dict(row) for row in cur.fetchall()])
            releasing = body.decision in {"approved", "limited_rollout"}
            if releasing and certification["status"] != "READY_FOR_HUMAN_DECISION":
                raise HTTPException(status_code=409, detail={"message": "Release gates are not ready", "blockers": certification["blockers"]})
            decision_id = str(uuid.uuid4())
            blockers = certification["blockers"] if certification["blockers"] else body.reason_codes
            cur.execute(
                "INSERT INTO sunday_school_ai_formation_release_decisions"
                "(id,artifact_id,artifact_version,environment,artifact_sha256,decision,rollout_percent,authorized_by,rollback_owner,incident_owner,blocker_snapshot_json) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    decision_id, body.artifact_id, body.artifact_version, body.environment,
                    body.artifact_sha256, body.decision,
                    body.rollout_percent, admin["email"], body.rollback_owner, body.incident_owner, Json(blockers),
                ),
            )
            _write_audit(
                cur, actor_email=admin["email"], action="release.decision_recorded", resource_type="release_decision",
                resource_id=decision_id, reason_codes=body.reason_codes,
            )
            conn.commit()
        return {"ok": True, "decisionId": decision_id, "automatedDecision": False, "certification": certification}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/admin/retention/purge")
def purge_expired_records(request: Request) -> dict[str, Any]:
    admin = _admin(request)
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sunday_school_ai_formation_records SET status='deleted',payload_json='{}'::jsonb,"
                "payload_hash=%s,deleted_at=COALESCE(deleted_at,NOW()),updated_at=NOW(),revision=revision+1 "
                "WHERE retention_until < NOW() AND payload_json <> '{}'::jsonb",
                (hashlib.sha256(b"{}").hexdigest(),),
            )
            purged = cur.rowcount
            _write_audit(
                cur, actor_email=admin["email"], action="retention.purged", resource_type="record_collection",
                resource_id=MODULE_MANIFEST["moduleId"], reason_codes=["RETENTION_EXPIRED"],
            )
            conn.commit()
        return {"ok": True, "purgedRecords": purged, "executedBy": admin["email"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)
