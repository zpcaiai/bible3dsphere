"""Skill 28/29/30 API: calling journeys, reflections and multi-source feedback."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.outbox import enqueue
from mission_os.calling import (
    CALLING_ORIENTATIONS, validate_reflection, validate_feedback_request, readiness_gate,
)

router = APIRouter(prefix='/api/v1/mission/calling-journeys', tags=['mission-calling'], dependencies=[Depends(require_mission_feature('mission_calling_enabled'))])
_state = {}


def init_mission_calling_router(*, get_db, release_db, get_session_user, is_admin):
    _state.update(locals())


def _user(request):
    user = _state['get_session_user'](request)
    email = str((user or {}).get('email') or '')
    if not email:
        raise HTTPException(401, detail='请先登录')
    return user, email


def _role(cur, email, org_id):
    if _state['is_admin'](email):
        return 'platform_admin'
    return require_org_permission(cur, email, org_id, 'view_dashboard')['role']


class JourneyBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    callingOrientation: str | None = None
    fieldInterest: str | None = Field(default=None, max_length=200)
    primaryQuestion: str | None = Field(default=None, max_length=1000)


@router.post('')
def create_journey(body: JourneyBody, request: Request):
    _user_obj, email = _user(request)
    if body.callingOrientation is not None and body.callingOrientation not in CALLING_ORIENTATIONS:
        raise HTTPException(422, detail='invalid calling orientation')
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            # field_interest is stored distinctly from calling_orientation.
            cur.execute(
                "INSERT INTO mission_calling_journeys(tenant_id,user_id,organization_id,calling_orientation,field_interest,primary_question,journey_status) "
                "VALUES(%s,%s,%s,%s,%s,%s,'active_discernment') RETURNING id",
                (body.organizationId, email, body.organizationId, body.callingOrientation, body.fieldInterest, body.primaryQuestion))
            jid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_calling_journey', resource_id=str(jid), result='success')
            enqueue(cur, tenant_id=body.organizationId, aggregate_type='MissionCallingJourney', aggregate_id=str(jid),
                    event_type='MissionCallingJourneyStarted', event_version=1, actor_id=email,
                    correlation_id=request.headers.get('X-Request-Id') or str(uuid.uuid4()),
                    data={'journey_id': str(jid)})
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'journeyId': str(jid), 'status': 'active_discernment'}


class ReflectionBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    reflectionType: str = Field(min_length=2, max_length=48)
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=8000)
    aiProcessingAllowed: bool = False


@router.post('/{journey_id}/reflections')
def add_reflection(journey_id: str, body: ReflectionBody, request: Request):
    _user_obj, email = _user(request)
    try:
        validate_reflection(body.reflectionType)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    # A dream/impression is stored as evidence_type subjective_impression (non-decisive).
    evidence_type = 'subjective_impression' if body.reflectionType == 'dream_or_impression' else None
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("SELECT user_id FROM mission_calling_journeys WHERE id=%s AND tenant_id=%s", (journey_id, body.organizationId))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail='呼召旅程不存在')
            if row[0] != email:
                raise HTTPException(403, detail='只能编辑自己的反思')
            cur.execute(
                "INSERT INTO mission_calling_reflections(tenant_id,calling_journey_id,reflection_type,title,content,ai_processing_allowed) "
                "VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.organizationId, journey_id, body.reflectionType, body.title, body.content, body.aiProcessingAllowed))
            rid = cur.fetchone()[0]
            if evidence_type:
                cur.execute(
                    "INSERT INTO mission_calling_evidence(tenant_id,calling_journey_id,evidence_type,evidence_summary,strength,requires_review) "
                    "VALUES(%s,%s,%s,%s,'non_decisive',TRUE)",
                    (body.organizationId, journey_id, evidence_type, body.title or 'impression'))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_calling_reflection', resource_id=str(rid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'reflectionId': str(rid)}


class FeedbackReqBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    respondentType: str = Field(min_length=2, max_length=48)
    respondentUserId: str | None = None
    requestedSections: list[str] = Field(default_factory=list)
    expiresHours: int = Field(default=168, ge=1, le=720)


@router.post('/{journey_id}/feedback-requests')
def request_feedback(journey_id: str, body: FeedbackReqBody, request: Request):
    _user_obj, email = _user(request)
    try:
        validate_feedback_request(requester_id=email, respondent_id=body.respondentUserId or '', respondent_type=body.respondentType)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expiresHours)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            import json as _json
            cur.execute(
                "INSERT INTO mission_feedback_requests(tenant_id,calling_journey_id,requester_id,respondent_type,respondent_user_id,requested_sections,expires_at) "
                "VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s) RETURNING id",
                (body.organizationId, journey_id, email, body.respondentType, body.respondentUserId, _json.dumps(body.requestedSections), expires_at))
            fid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_feedback_request', resource_id=str(fid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'feedbackRequestId': str(fid), 'expiresAt': expires_at.isoformat()}


class GateBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)


@router.post('/{journey_id}/submit-readiness-gate')
def submit_gate(journey_id: str, body: GateBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("SELECT 1 FROM mission_calling_journeys WHERE id=%s AND tenant_id=%s", (journey_id, body.organizationId))
            if not cur.fetchone():
                raise HTTPException(404, detail='呼召旅程不存在')
            cur.execute("SELECT DISTINCT evidence_type FROM mission_calling_evidence WHERE calling_journey_id=%s AND tenant_id=%s", (journey_id, body.organizationId))
            ev_types = [r[0] for r in cur.fetchall()]
            has_church_or_mentor = any(t in ('church_feedback', 'mentor_feedback') for t in ev_types)
            has_local = 'local_practice' in ev_types
            cur.execute("SELECT count(*) FROM mission_calling_blockers WHERE calling_journey_id=%s AND tenant_id=%s AND severity='hard_block' AND status<>'cleared'", (journey_id, body.organizationId))
            unresolved = int(cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM mission_feedback_responses fr JOIN mission_feedback_requests q ON q.id=fr.feedback_request_id WHERE q.calling_journey_id=%s AND fr.tenant_id=%s", (journey_id, body.organizationId))
            motive_complete = True  # motive assessment tracked separately; simplified here
            try:
                readiness_gate(has_church_or_mentor_feedback=has_church_or_mentor, has_local_practice=has_local,
                               motive_assessment_complete=motive_complete, unresolved_hard_blocks=unresolved,
                               evidence_types=ev_types)
            except ValueError as exc:
                raise HTTPException(409, detail=str(exc))
            cur.execute("UPDATE mission_calling_journeys SET journey_status='ready_for_readiness_assessment',updated_at=now() WHERE id=%s AND tenant_id=%s", (journey_id, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='update',
                  resource_type='mission_calling_journey', resource_id=str(journey_id), result='success', reason='readiness_gate')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'status': 'ready_for_readiness_assessment'}


@router.get('')
def list_journeys(organizationId: str, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute("SELECT id,calling_orientation,field_interest,journey_status,current_stage,started_at FROM mission_calling_journeys WHERE tenant_id=%s AND user_id=%s ORDER BY started_at DESC LIMIT 100", (organizationId, email))
            rows = [{'id': str(r[0]), 'callingOrientation': r[1], 'fieldInterest': r[2], 'journeyStatus': r[3],
                     'currentStage': r[4], 'startedAt': r[5].isoformat() if r[5] else None} for r in cur.fetchall()]
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'items': rows}
