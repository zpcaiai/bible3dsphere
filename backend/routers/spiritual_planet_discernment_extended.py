"""Authenticated product APIs for Spiritual Planet discernment Batches 07-10."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from psycopg2.extras import Json, RealDictCursor

from discernment_platform.extended import CertificationService, FormationTwinService, TheologyEvidenceService, canonical_hash
from discernment_platform.models import (
    CertificationEvaluationCreate,
    CollaborationConsentCreate,
    DisclosureCreate,
    FormationEventCreate,
    FormationReviewRequest,
    IdentityMigrationRequest,
    MeetingPrepCreate,
    RecertificationTriggerCreate,
    RelationshipRepairRequest,
    RelapseTransitionRequest,
    TheologyQueryCreate,
    TheologySourceCreate,
)
from discernment_platform.pastoral_collaboration import (
    Actor,
    ConsentGrant,
    DataLevel,
    PastoralCase,
    AccessPolicyEvaluator,
    build_disclosure,
    build_meeting_prep,
)
from formation_twin.crypto import EncryptedContent, decrypt_text, encrypt_text


router = APIRouter(prefix="/api/v1/platform/discernment", tags=["spiritual-planet-discernment-extended"])
_state: dict[str, Any] = {}
_formation = FormationTwinService()
_theology = TheologyEvidenceService()
_certification = CertificationService()


ROLE_LEVELS = {
    "accountability_partner": {"L0"},
    "small_group_leader": {"L0"},
    "mentor_discipler": {"L0", "L1"},
    "pastor_elder": {"L0", "L1", "L2"},
    "safeguarding_officer": {"L2", "L3"},
    "licensed_professional": {"L2"},
    "governance_review_panel": {"L3"},
}

DISCLOSABLE_FIELDS = {
    "L0": {"user_goal", "current_focus", "agreed_action"},
    "L1": {"worldview_summary", "formation_pattern_summary", "uncertainty", "priority_question"},
    "L2": {"safety_summary", "referral_need", "user_approved_sensitive_summary"},
    "L3": {"governance_timeline", "evidence_sources", "due_process_status"},
}

PROHIBITED_DISCLOSURE_FIELDS = {
    "full_formation_twin", "full_dialogue", "private_third_party_identity", "unverified_inference_as_fact",
    "salvation_status", "clinical_diagnosis", "discipline_verdict",
}
DATA_LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


def init_spiritual_planet_discernment_extended_router(*, get_db, release_db, get_session_user, is_admin=None) -> None:
    _state.update(locals())


def _user(request: Request) -> dict[str, Any]:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _admin(request: Request) -> dict[str, Any]:
    user = _user(request)
    checker = _state.get("is_admin")
    if not checker or not checker(user["email"]):
        raise HTTPException(status_code=403, detail="certification administrator only")
    return user


def _identity(email: str) -> tuple[str, str]:
    email = email.lower()
    return f"personal:{email}", email


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email',%s,true)", (email,))


def _connection():
    if not _state.get("get_db"):
        raise HTTPException(status_code=503, detail="Discernment persistence unavailable")
    return _state["get_db"]()


def _release(conn) -> None:
    _state["release_db"](conn)


def _encrypt(payload: dict[str, Any], *, email: str, record_id: str) -> EncryptedContent:
    return encrypt_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
        associated_data=f"spiritual-planet:{email}:{record_id}".encode(),
    )


def _decrypt(row: dict[str, Any], *, email: str, record_id: str, field: str = "encrypted_payload") -> dict[str, Any]:
    envelope = EncryptedContent(
        key_version=row["encryption_key_version"], nonce=bytes(row["nonce"]),
        ciphertext=bytes(row[field]), sha256=row.get("payload_hash") or row.get("query_hash"),
    )
    value = decrypt_text(envelope, associated_data=f"spiritual-planet:{email}:{record_id}".encode())
    return json.loads(value)


def _fetch_owned_case(cur, case_id: str, email: str) -> dict[str, Any]:
    cur.execute(
        "SELECT * FROM spiritual_planet_discernment_cases WHERE id=%s AND email=%s AND deleted_at IS NULL",
        (case_id, email),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Discernment case not found")
    return dict(row)


def _formation_events(cur, email: str) -> list[dict[str, Any]]:
    cur.execute(
        "SELECT * FROM spiritual_planet_formation_events WHERE email=%s AND status='ACTIVE' AND deleted_at IS NULL ORDER BY occurred_at",
        (email,),
    )
    return [_decrypt(dict(row), email=email, record_id=str(row["id"])) for row in cur.fetchall()]


def _persist_artifact(cur, *, tenant_id: str, email: str, artifact_type: str, payload: dict[str, Any], source_ids: list[str], window_days: int | None = None) -> str:
    artifact_id = str(uuid.uuid4())
    encrypted = _encrypt(payload, email=email, record_id=artifact_id)
    summary = {
        "review_status": payload.get("review_status"), "decision": payload.get("decision"),
        "uncertainty": payload.get("uncertainty"), "limitations": payload.get("limitations", []),
    }
    cur.execute(
        "INSERT INTO spiritual_planet_formation_artifacts"
        "(id,tenant_id,email,artifact_type,window_days,source_event_ids,summary_json,encryption_key_version,nonce,encrypted_payload,payload_hash) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (artifact_id, tenant_id, email, artifact_type, window_days, Json(source_ids), Json(summary),
         encrypted.key_version, encrypted.nonce, encrypted.ciphertext, encrypted.sha256),
    )
    return artifact_id


def _audit(cur, *, tenant_id: str, owner_email: str, actor_email: str, action: str, purpose: str, resource_type: str, resource_id: str | None, reason: str, outcome: str, recipient_email: str | None = None, details: dict[str, Any] | None = None) -> None:
    cur.execute(
        "INSERT INTO spiritual_planet_collaboration_audit"
        "(tenant_id,email,recipient_email,actor_email,action,purpose,resource_type,resource_id,reason,outcome,details_json) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (tenant_id, owner_email, recipient_email, actor_email, action, purpose, resource_type,
         resource_id, reason, outcome, Json(details or {})),
    )


@router.post("/formation/events", status_code=201)
def create_formation_event(body: FormationEventCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    event_id = str(uuid.uuid4())
    payload = body.model_dump(mode="json")
    case_id = payload.pop("case_id", None)
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            if case_id:
                case = _fetch_owned_case(cur, case_id, email)
                if not case["consent_scope_json"].get("allow_longitudinal_memory"):
                    raise HTTPException(status_code=409, detail="Case longitudinal-memory consent is not active")
            result = _formation.ingest(event_id=event_id, email=email, payload=payload)
            if result["review_status"] != "ready":
                raise HTTPException(status_code=409, detail=result)
            encrypted = _encrypt(result["event"], email=email, record_id=event_id)
            cur.execute(
                "INSERT INTO spiritual_planet_formation_events"
                "(id,tenant_id,email,case_id,occurred_at,source_type,evidence_quality,data_level,consent_json,encryption_key_version,nonce,encrypted_payload,payload_hash,chain_summary_json) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (event_id, tenant_id, email, case_id, body.occurred_at, body.source_type, body.evidence_quality,
                 body.data_level, Json({"allow_longitudinal_tracking": True}), encrypted.key_version,
                 encrypted.nonce, encrypted.ciphertext, encrypted.sha256,
                 Json({"chain_id": result["chain"]["chain_id"], "quality_gates": result["quality_gates"]})),
            )
            conn.commit()
        return {"ok": True, "event_id": event_id, "chain": result["chain"], "quality_gates": result["quality_gates"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/formation/events")
def list_formation_events(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT * FROM spiritual_planet_formation_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 200",
                (email,),
            )
            events = [{"id": str(row["id"]), "status": row["status"], "event": _decrypt(dict(row), email=email, record_id=str(row["id"]))} for row in cur.fetchall()]
        return {"ok": True, "events": events}
    finally:
        _release(conn)


@router.delete("/formation/events/{event_id}")
def delete_formation_event(event_id: uuid.UUID, request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "UPDATE spiritual_planet_formation_events SET status='WITHDRAWN',deleted_at=NOW(),updated_at=NOW() WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",
                (str(event_id), email),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Formation event not found")
            conn.commit()
        return {"ok": True, "status": "WITHDRAWN"}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/formation/events/{event_id}/corrections", status_code=201)
def correct_formation_event(event_id: uuid.UUID, body: FormationEventCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    corrected_id = str(uuid.uuid4())
    payload = body.model_dump(mode="json")
    case_id = payload.pop("case_id", None)
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT id,case_id FROM spiritual_planet_formation_events WHERE id=%s AND email=%s AND status='ACTIVE' AND deleted_at IS NULL FOR UPDATE", (str(event_id), email))
            original = cur.fetchone()
            if not original:
                raise HTTPException(status_code=404, detail="Active formation event not found")
            if case_id and original["case_id"] and str(original["case_id"]) != str(case_id):
                raise HTTPException(status_code=409, detail="A correction must remain attached to the original case")
            effective_case_id = case_id or (str(original["case_id"]) if original["case_id"] else None)
            if effective_case_id:
                case = _fetch_owned_case(cur, effective_case_id, email)
                if not case["consent_scope_json"].get("allow_longitudinal_memory"):
                    raise HTTPException(status_code=409, detail="Case longitudinal-memory consent is not active")
            result = _formation.ingest(event_id=corrected_id, email=email, payload=payload)
            if result["review_status"] != "ready":
                raise HTTPException(status_code=409, detail=result)
            encrypted = _encrypt(result["event"], email=email, record_id=corrected_id)
            cur.execute(
                "INSERT INTO spiritual_planet_formation_events"
                "(id,tenant_id,email,case_id,occurred_at,source_type,evidence_quality,data_level,consent_json,encryption_key_version,nonce,encrypted_payload,payload_hash,chain_summary_json,correction_of) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (corrected_id, tenant_id, email, effective_case_id, body.occurred_at, body.source_type,
                 body.evidence_quality, body.data_level, Json({"allow_longitudinal_tracking": True}),
                 encrypted.key_version, encrypted.nonce, encrypted.ciphertext, encrypted.sha256,
                 Json({"chain_id": result["chain"]["chain_id"], "quality_gates": result["quality_gates"]}), str(event_id)),
            )
            cur.execute("UPDATE spiritual_planet_formation_events SET status='CORRECTED',updated_at=NOW() WHERE id=%s AND email=%s", (str(event_id), email))
            conn.commit()
        return {"ok": True, "event_id": corrected_id, "corrects": str(event_id), "chain": result["chain"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/formation/snapshot", status_code=201)
def create_formation_snapshot(request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            events = _formation_events(cur, email)
            snapshot = _formation.snapshot(email=email, events=events)
            artifact_id = _persist_artifact(cur, tenant_id=tenant_id, email=email, artifact_type="SNAPSHOT", payload=snapshot, source_ids=[event["event_id"] for event in events])
            conn.commit()
        return {"ok": True, "artifact_id": artifact_id, "snapshot": snapshot}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/formation/reviews", status_code=201)
def create_formation_review(body: FormationReviewRequest, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            events = _formation_events(cur, email)
            review = _formation.window_review(email=email, events=events, window_days=body.window_days)
            artifact_id = _persist_artifact(cur, tenant_id=tenant_id, email=email, artifact_type="WINDOW_REVIEW", payload=review, source_ids=[event["event_id"] for event in events], window_days=body.window_days)
            conn.commit()
        return {"ok": True, "artifact_id": artifact_id, "review": review}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/formation/relapse", status_code=201)
def transition_relapse(body: RelapseTransitionRequest, request: Request) -> dict[str, Any]:
    return _persist_simple_formation_artifact("RELAPSE", _formation.relapse(body.current, body.target), request)


@router.post("/formation/repairs", status_code=201)
def create_relationship_repair(body: RelationshipRepairRequest, request: Request) -> dict[str, Any]:
    payload = {"repair_id": str(uuid.uuid4()), **body.model_dump(mode="json")}
    return _persist_simple_formation_artifact("RELATIONSHIP_REPAIR", _formation.repair(payload), request)


@router.post("/formation/identity-migrations", status_code=201)
def create_identity_migration(body: IdentityMigrationRequest, request: Request) -> dict[str, Any]:
    payload = {"migration_id": str(uuid.uuid4()), **body.model_dump(mode="json")}
    return _persist_simple_formation_artifact("IDENTITY_MIGRATION", _formation.identity(payload), request)


def _persist_simple_formation_artifact(artifact_type: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            artifact_id = _persist_artifact(cur, tenant_id=tenant_id, email=email, artifact_type=artifact_type, payload=payload, source_ids=[])
            conn.commit()
        return {"ok": True, "artifact_id": artifact_id, "result": payload}
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/collaboration/consents", status_code=201)
def create_collaboration_consent(body: CollaborationConsentCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    if body.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Consent expiry must be in the future")
    if body.reshare_allowed:
        raise HTTPException(status_code=422, detail="Pastoral disclosures cannot be re-shared")
    if not set(body.allowed_categories) <= ROLE_LEVELS[body.recipient_role]:
        raise HTTPException(status_code=403, detail="Role is not permitted for one or more requested data levels")
    consent_id = str(uuid.uuid4())
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "INSERT INTO spiritual_planet_collaboration_consents"
                "(id,tenant_id,email,recipient_email,recipient_role,purpose,allowed_categories_json,allowed_actions_json,expires_at,reshare_allowed) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)",
                (consent_id, tenant_id, email, body.recipient_email, body.recipient_role, body.purpose,
                 Json(body.allowed_categories), Json(body.allowed_actions), body.expires_at),
            )
            _audit(cur, tenant_id=tenant_id, owner_email=email, recipient_email=body.recipient_email, actor_email=email,
                   action="CONSENT_GRANTED", purpose=body.purpose, resource_type="consent", resource_id=consent_id,
                   reason="explicit_user_consent", outcome="ALLOWED", details={"categories": body.allowed_categories})
            conn.commit()
        return {"ok": True, "consent": {"id": consent_id, **body.model_dump(mode="json"), "reshare_allowed": False, "status": "ACTIVE"}}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/collaboration/consents")
def list_collaboration_consents(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT * FROM spiritual_planet_collaboration_consents WHERE email=%s ORDER BY created_at DESC", (email,))
            items = [{**dict(row), "id": str(row["id"])} for row in cur.fetchall()]
        return {"ok": True, "consents": items}
    finally:
        _release(conn)


@router.delete("/collaboration/consents/{consent_id}")
def revoke_collaboration_consent(consent_id: uuid.UUID, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "UPDATE spiritual_planet_collaboration_consents SET status='REVOKED',revoked_at=NOW() WHERE id=%s AND email=%s AND status='ACTIVE' RETURNING recipient_email,purpose",
                (str(consent_id), email),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Active consent not found")
            cur.execute("UPDATE spiritual_planet_collaboration_disclosures SET status='REVOKED',revoked_at=NOW() WHERE consent_id=%s AND email=%s AND status='ACTIVE'", (str(consent_id), email))
            _audit(cur, tenant_id=tenant_id, owner_email=email, recipient_email=row["recipient_email"], actor_email=email,
                   action="CONSENT_REVOKED", purpose=row["purpose"], resource_type="consent", resource_id=str(consent_id),
                   reason="user_revocation", outcome="REVOKED")
            conn.commit()
        return {"ok": True, "status": "REVOKED"}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/collaboration/disclosures", status_code=201)
def create_disclosure(body: DisclosureCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    disclosure_id = str(uuid.uuid4())
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            if body.case_id:
                _fetch_owned_case(cur, str(body.case_id), email)
            cur.execute("SELECT * FROM spiritual_planet_collaboration_consents WHERE id=%s AND email=%s AND status='ACTIVE' AND expires_at>NOW()", (str(body.consent_id), email))
            consent = cur.fetchone()
            if not consent:
                raise HTTPException(status_code=403, detail="Active, unexpired consent is required")
            if consent["purpose"] != body.purpose or body.data_level not in consent["allowed_categories_json"]:
                raise HTTPException(status_code=403, detail="Purpose or data level is outside consent")
            if body.expires_at > consent["expires_at"] or body.expires_at <= datetime.now(timezone.utc):
                raise HTTPException(status_code=422, detail="Disclosure expiry must be future and no later than consent")
            actor = Actor(actor_id=consent["recipient_email"], display_name=consent["recipient_email"], roles=[consent["recipient_role"]], tenant_id=tenant_id)
            grant = ConsentGrant(
                grant_id=str(consent["id"]), subject_user_id=email, recipient_actor_id=actor.actor_id,
                purpose=consent["purpose"], allowed_categories=consent["allowed_categories_json"],
                allowed_actions=consent["allowed_actions_json"], expires_at=consent["expires_at"].isoformat(), status="active",
            )
            case = PastoralCase(case_id=str(body.case_id or uuid.uuid4()), subject_user_id=email, purpose=body.purpose,
                                sensitivity=DataLevel(body.data_level), status="active", assigned_roles=[consent["recipient_role"]])
            policy = AccessPolicyEvaluator().evaluate(actor, case, grant, body.purpose, DataLevel(body.data_level), False)
            if policy["decision"] != "allowed":
                raise HTTPException(status_code=403, detail=policy)
            allowed = set().union(*(
                DISCLOSABLE_FIELDS[level]
                for level in consent["allowed_categories_json"]
                if DATA_LEVEL_ORDER[level] <= DATA_LEVEL_ORDER[body.data_level]
            ))
            disclosure = build_disclosure(
                disclosure_id=disclosure_id, case_id=str(body.case_id or "purpose-only"), recipient_actor_id=actor.actor_id,
                purpose=body.purpose, requested_fields=body.requested_fields, allowed_fields=allowed,
                prohibited_fields=PROHIBITED_DISCLOSURE_FIELDS, expires_at=body.expires_at.isoformat(),
                basis="explicit_user_consent", audit_id=f"audit-{disclosure_id}",
            )
            cur.execute(
                "INSERT INTO spiritual_planet_collaboration_disclosures"
                "(id,tenant_id,email,recipient_email,recipient_role,consent_id,case_id,purpose,data_level,selected_fields_json,redacted_fields_json,basis,reshare_policy,expires_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'forbidden',%s)",
                (disclosure_id, tenant_id, email, consent["recipient_email"], consent["recipient_role"], str(body.consent_id),
                 str(body.case_id) if body.case_id else None, body.purpose, body.data_level,
                 Json(disclosure.selected_fields), Json(disclosure.redacted_fields), disclosure.basis, body.expires_at),
            )
            _audit(cur, tenant_id=tenant_id, owner_email=email, recipient_email=consent["recipient_email"], actor_email=email,
                   action="DISCLOSURE_CREATED", purpose=body.purpose, resource_type="disclosure", resource_id=disclosure_id,
                   reason="minimum_necessary", outcome="ALLOWED", details={"selected": disclosure.selected_fields, "redacted": disclosure.redacted_fields})
            conn.commit()
        return {"ok": True, "disclosure": disclosure.model_dump(mode="json")}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/collaboration/meeting-preps", status_code=201)
def create_meeting_prep(body: MeetingPrepCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    prep_id = str(uuid.uuid4())
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            case = _fetch_owned_case(cur, str(body.case_id), email)
            cur.execute(
                "SELECT d.* FROM spiritual_planet_collaboration_disclosures d JOIN spiritual_planet_collaboration_consents c ON c.id=d.consent_id "
                "WHERE d.consent_id=%s AND d.case_id=%s AND d.email=%s AND d.status='ACTIVE' AND d.expires_at>NOW() AND c.status='ACTIVE' AND c.expires_at>NOW() ORDER BY d.created_at DESC LIMIT 1",
                (str(body.consent_id), str(body.case_id), email),
            )
            disclosure = cur.fetchone()
            if not disclosure:
                raise HTTPException(status_code=403, detail="Active purpose-bound disclosure is required")
            report = case["report_json"]
            evidence_summary = [{
                "summary": report.get("summary", ""), "review_status": report.get("review_status"),
                "evidence_boundary": "AI hypotheses remain hypotheses and are not governance evidence.",
            }]
            prep = build_meeting_prep(
                case_id=str(body.case_id), meeting_purpose=body.meeting_purpose,
                user_selected_focus=body.user_selected_focus[:1], last_agreements=body.last_agreements,
                evidence_summary=evidence_summary, uncertainties=body.uncertainties,
                priority_question=body.priority_question, gospel_truth=body.gospel_truth,
                action_option=body.action_option, do_not_use_language=body.do_not_use_language,
            )
            encrypted = _encrypt(prep, email=email, record_id=prep_id)
            cur.execute(
                "INSERT INTO spiritual_planet_collaboration_meeting_preps"
                "(id,tenant_id,email,recipient_email,disclosure_id,case_id,encryption_key_version,nonce,encrypted_payload,payload_hash,expires_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (prep_id, tenant_id, email, disclosure["recipient_email"], str(disclosure["id"]), str(body.case_id),
                 encrypted.key_version, encrypted.nonce, encrypted.ciphertext, encrypted.sha256, disclosure["expires_at"]),
            )
            _audit(cur, tenant_id=tenant_id, owner_email=email, recipient_email=disclosure["recipient_email"], actor_email=email,
                   action="MEETING_PREP_CREATED", purpose=body.meeting_purpose, resource_type="meeting_prep", resource_id=prep_id,
                   reason="purpose_bound_preparation", outcome="ALLOWED")
            conn.commit()
        return {"ok": True, "prep_id": prep_id, "meeting_prep": prep}
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/collaboration/inbox")
def collaboration_inbox(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT * FROM spiritual_planet_collaboration_disclosures WHERE recipient_email=%s AND status='ACTIVE' AND expires_at>NOW() ORDER BY created_at DESC",
                (email,),
            )
            disclosures = [{**dict(row), "id": str(row["id"]), "consent_id": str(row["consent_id"]), "case_id": str(row["case_id"]) if row["case_id"] else None} for row in cur.fetchall()]
            preps = []
            for disclosure in disclosures:
                cur.execute("SELECT * FROM spiritual_planet_collaboration_meeting_preps WHERE disclosure_id=%s AND recipient_email=%s AND deleted_at IS NULL AND expires_at>NOW()", (disclosure["id"], email))
                for row in cur.fetchall():
                    row = dict(row)
                    preps.append({"id": str(row["id"]), "meeting_prep": _decrypt(row, email=row["email"], record_id=str(row["id"]))})
        return {"ok": True, "disclosures": disclosures, "meeting_preps": preps}
    finally:
        _release(conn)


@router.get("/collaboration/audit")
def collaboration_audit(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT * FROM spiritual_planet_collaboration_audit WHERE email=%s OR recipient_email=%s ORDER BY created_at DESC LIMIT 200", (email, email))
            items = [{**dict(row), "id": str(row["id"]), "resource_id": str(row["resource_id"]) if row["resource_id"] else None} for row in cur.fetchall()]
        return {"ok": True, "audit": items}
    finally:
        _release(conn)


@router.post("/theology/sources", status_code=201)
def create_theology_source(body: TheologySourceCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    if body.rights_status in {"user_owned", "licensed_internal"} and not body.user_confirms_rights:
        raise HTTPException(status_code=422, detail="Explicit rights confirmation is required")
    source_id = str(uuid.uuid4())
    source = {"source_id": source_id, **body.model_dump(mode="json")}
    source.pop("user_confirms_rights", None)
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "INSERT INTO spiritual_planet_theology_sources"
                "(id,tenant_id,email,title,source_type,rights_status,quality_tier,source_json,user_confirms_rights) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (source_id, tenant_id, email, body.title, body.source_type, body.rights_status, body.quality_tier, Json(source), body.user_confirms_rights),
            )
            conn.commit()
        return {"ok": True, "source": source}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/theology/sources")
def list_theology_sources(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT id,source_json,status,created_at FROM spiritual_planet_theology_sources WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC", (email,))
            sources = [{"id": str(row["id"]), "source": row["source_json"], "status": row["status"], "created_at": row["created_at"]} for row in cur.fetchall()]
        return {"ok": True, "sources": sources}
    finally:
        _release(conn)


@router.post("/theology/queries", status_code=201)
def create_theology_query(body: TheologyQueryCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    query_id = str(uuid.uuid4())
    payload = body.model_dump(mode="json")
    source_ids = [str(item) for item in body.source_ids]
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            sources = []
            if source_ids:
                cur.execute("SELECT source_json FROM spiritual_planet_theology_sources WHERE email=%s AND id IN %s AND status='ACTIVE' AND deleted_at IS NULL", (email, tuple(source_ids)))
                sources = [row["source_json"] for row in cur.fetchall()]
            if not payload["required_source_types"]:
                payload["required_source_types"] = sorted({source["source_type"] for source in sources})
            payload["citations"] = [
                {**citation, "source_id": str(citation["source_id"]), "citation_id": f"citation-{index + 1}"}
                for index, citation in enumerate(payload["citations"])
            ]
            result = _theology.query(query_id=query_id, payload=payload, sources=sources)
            encrypted = _encrypt({"request": payload, "result": result}, email=email, record_id=query_id)
            persisted = {
                "query_id": query_id, "review_status": result["review_status"], "answer_status": result["answer_status"],
                "source_filter": {"allowed_count": len(result["source_filter"]["allowed"]), "blocked": result["source_filter"]["blocked"]},
                "scripture_context_gates": result["scripture_context_gates"], "doctrine_governance": result["doctrine_governance"],
                "misuse_detection": result["misuse_detection"], "evidence_graph_hash": canonical_hash(result["evidence_graph"]),
            }
            cur.execute(
                "INSERT INTO spiritual_planet_theology_queries"
                "(id,tenant_id,email,query_hash,intent,review_status,encryption_key_version,nonce,encrypted_query,result_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (query_id, tenant_id, email, canonical_hash(payload["question"]), body.intent, result["review_status"],
                 encrypted.key_version, encrypted.nonce, encrypted.ciphertext, Json(persisted)),
            )
            conn.commit()
        return {"ok": True, "query": result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/theology/queries")
def list_theology_queries(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT id,intent,review_status,result_json,created_at FROM spiritual_planet_theology_queries WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 100", (email,))
            items = [{**dict(row), "id": str(row["id"])} for row in cur.fetchall()]
        return {"ok": True, "queries": items}
    finally:
        _release(conn)


@router.get("/certification/status")
def certification_status(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT id,build_hash,target_scope,status,created_at FROM spiritual_planet_certification_evaluations WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
            row = cur.fetchone()
        return {
            "ok": True,
            "status": ({**dict(row), "id": str(row["id"])} if row else {"status": "NOT_EVALUATED"}),
            "catalog": {"domains": 12, "controls": 58, "version": "1.0.0"},
            "production_claim_boundary": "No production approval exists without complete evidence and release-board signatures.",
        }
    finally:
        _release(conn)


@router.get("/data-export")
def export_extended_data(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT * FROM spiritual_planet_formation_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at", (email,))
            formation_events = [{"id": str(row["id"]), "status": row["status"], "payload": _decrypt(dict(row), email=email, record_id=str(row["id"]))} for row in cur.fetchall()]
            cur.execute("SELECT * FROM spiritual_planet_formation_artifacts WHERE email=%s AND deleted_at IS NULL ORDER BY created_at", (email,))
            formation_artifacts = [{"id": str(row["id"]), "artifact_type": row["artifact_type"], "payload": _decrypt(dict(row), email=email, record_id=str(row["id"]))} for row in cur.fetchall()]
            cur.execute("SELECT source_json,status,created_at FROM spiritual_planet_theology_sources WHERE email=%s AND deleted_at IS NULL ORDER BY created_at", (email,))
            theology_sources = [dict(row) for row in cur.fetchall()]
            cur.execute("SELECT * FROM spiritual_planet_theology_queries WHERE email=%s AND deleted_at IS NULL ORDER BY created_at", (email,))
            theology_queries = [{"id": str(row["id"]), "payload": _decrypt(dict(row), email=email, record_id=str(row["id"]), field="encrypted_query")} for row in cur.fetchall()]
            cur.execute("SELECT * FROM spiritual_planet_collaboration_consents WHERE email=%s ORDER BY created_at", (email,))
            consents = [{**dict(row), "id": str(row["id"])} for row in cur.fetchall()]
            cur.execute("SELECT * FROM spiritual_planet_collaboration_disclosures WHERE email=%s ORDER BY created_at", (email,))
            disclosures = [{**dict(row), "id": str(row["id"])} for row in cur.fetchall()]
            cur.execute("SELECT * FROM spiritual_planet_collaboration_audit WHERE email=%s ORDER BY created_at", (email,))
            audit = [{**dict(row), "id": str(row["id"])} for row in cur.fetchall()]
        return {"ok": True, "export": {"formation_events": formation_events, "formation_artifacts": formation_artifacts,
                "theology_sources": theology_sources, "theology_queries": theology_queries,
                "collaboration_consents": consents, "collaboration_disclosures": disclosures, "collaboration_audit": audit}}
    finally:
        _release(conn)


@router.delete("/extended-data")
def delete_extended_data(request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    tables = [
        "spiritual_planet_collaboration_meeting_preps", "spiritual_planet_collaboration_disclosures",
        "spiritual_planet_collaboration_consents", "spiritual_planet_collaboration_audit",
        "spiritual_planet_formation_artifacts", "spiritual_planet_formation_events",
        "spiritual_planet_theology_queries", "spiritual_planet_theology_sources",
    ]
    try:
        deleted: dict[str, int] = {}
        with conn.cursor() as cur:
            _owner(cur, email)
            for table in tables:
                cur.execute(f"DELETE FROM {table} WHERE email=%s", (email,))
                deleted[table] = cur.rowcount
            conn.commit()
        return {"ok": True, "status": "DELETED", "deleted": deleted}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/admin/certification/evaluations", status_code=201)
def evaluate_certification(body: CertificationEvaluationCreate, request: Request) -> dict[str, Any]:
    reviewer = _admin(request)
    tenant_id, email = _identity(reviewer["email"])
    release_id = str(uuid.uuid4())
    result = _certification.evaluate(release_id=release_id, body=body.model_dump(mode="json"))
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "INSERT INTO spiritual_planet_certification_evaluations(id,tenant_id,email,build_hash,target_scope,status,result_json) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (release_id, tenant_id, email, body.build_hash, body.target_scope, result["status"], Json(result)),
            )
            if certificate := result.get("certificate"):
                cur.execute(
                    "INSERT INTO spiritual_planet_release_certificates"
                    "(id,tenant_id,email,release_id,build_hash,status,certificate_json,signature_hash,expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, email, release_id, body.build_hash, result["status"], Json(certificate), certificate["signature_hash"], body.expires_at),
                )
            conn.commit()
        return {"ok": True, "evaluation": result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/admin/certification/recertification-events", status_code=201)
def create_recertification_event(body: RecertificationTriggerCreate, request: Request) -> dict[str, Any]:
    reviewer = _admin(request)
    tenant_id, email = _identity(reviewer["email"])
    event_id = str(uuid.uuid4())
    result = _certification.recertification(body.trigger_type)
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "INSERT INTO spiritual_planet_recertification_events(id,tenant_id,email,trigger_type,required_domains_json,details_json,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (event_id, tenant_id, email, body.trigger_type, Json(result["required_domains"]), Json(body.details), result["status"]),
            )
            conn.commit()
        return {"ok": True, "event_id": event_id, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)
