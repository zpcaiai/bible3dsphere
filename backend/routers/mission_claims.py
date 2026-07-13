"""Skill 22/23 API: sources, claims and evidence with AI-candidate guardrails."""
from __future__ import annotations
import json
import uuid
from datetime import date, datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_os
from mission_os.audit import audit
from mission_os.claims import validate_new_claim, can_promote, CLAIM_TYPES

router = APIRouter(prefix='/api/v1/mission/claims', tags=['mission-claims'], dependencies=[Depends(require_mission_os)])
sources_router = APIRouter(prefix='/api/v1/mission/sources', tags=['mission-claims'], dependencies=[Depends(require_mission_os)])
_state = {}


def init_mission_claims_router(*, get_db, release_db, get_session_user, is_admin):
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
    return require_org_permission(cur, email, org_id, 'manage_settings')['role']


class SourceBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    sourceType: str = Field(min_length=2, max_length=48)
    title: str = Field(min_length=1, max_length=300)
    publisherOrOwner: str | None = Field(default=None, max_length=200)
    sensitivityLevel: Literal['P0', 'P1', 'P2', 'P3', 'P4'] = 'P1'


@sources_router.post('')
def create_source(body: SourceBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_sources(tenant_id,source_type,title,publisher_or_owner,sensitivity_level) "
                "VALUES(%s,%s,%s,%s,%s) RETURNING id",
                (body.organizationId, body.sourceType, body.title, body.publisherOrOwner, body.sensitivityLevel))
            sid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_source', resource_id=str(sid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'sourceId': str(sid)}


class ClaimBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    subjectType: str = Field(min_length=1, max_length=80)
    subjectId: str = Field(min_length=1, max_length=64)
    predicate: str = Field(min_length=1, max_length=120)
    humanReadableClaim: str = Field(min_length=1, max_length=1000)
    claimType: str = Field(min_length=2, max_length=48)
    createdByType: Literal['human', 'ai', 'system'] = 'human'
    normalizedValue: dict | None = None
    asOfDate: str | None = None


@router.post('')
def create_claim(body: ClaimBody, request: Request):
    _user_obj, email = _user(request)
    if body.claimType not in CLAIM_TYPES:
        raise HTTPException(422, detail='invalid claim type')
    as_of = None
    if body.asOfDate:
        try:
            as_of = datetime.fromisoformat(body.asOfDate).date()
        except ValueError:
            raise HTTPException(422, detail='asOfDate must be ISO date')
    try:
        status = validate_new_claim(claim_type=body.claimType, created_by_type=body.createdByType,
                                    normalized_value=body.normalizedValue, as_of_date=as_of)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_claims(tenant_id,subject_type,subject_id,predicate,normalized_value_json,human_readable_claim,claim_type,status,as_of_date,created_by_type,created_by_id) "
                "VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.organizationId, body.subjectType, body.subjectId, body.predicate,
                 json.dumps(body.normalizedValue) if body.normalizedValue is not None else None,
                 body.humanReadableClaim, body.claimType, status, as_of, body.createdByType, email))
            cid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role,
                  action='ai_generate' if body.createdByType == 'ai' else 'create',
                  resource_type='mission_claim', resource_id=str(cid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'claimId': str(cid), 'status': status}


class EvidenceBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    sourceId: str = Field(min_length=1)
    evidenceType: str = Field(min_length=2, max_length=48)
    stance: Literal['supports', 'partially_supports', 'contradicts', 'contextualizes', 'supersedes', 'uncertain']
    excerptOrSummary: str | None = Field(default=None, max_length=2000)


@router.post('/{claim_id}/evidence')
def add_evidence(claim_id: str, body: EvidenceBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("SELECT 1 FROM mission_claims WHERE id=%s AND tenant_id=%s", (claim_id, body.organizationId))
            if not cur.fetchone():
                raise HTTPException(404, detail='断言不存在')
            cur.execute(
                "INSERT INTO mission_claim_evidence(tenant_id,claim_id,source_id,evidence_type,stance,excerpt_or_summary,added_by) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.organizationId, claim_id, body.sourceId, body.evidenceType, body.stance, body.excerptOrSummary, email))
            eid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_claim_evidence', resource_id=str(eid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'evidenceId': str(eid)}


class PromoteBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    targetStatus: Literal['under_review', 'supported', 'locally_confirmed', 'disputed', 'rejected']
    hasLocalReviewer: bool = False


@router.post('/{claim_id}/promote')
def promote_claim(claim_id: str, body: PromoteBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("SELECT status,created_by_type FROM mission_claims WHERE id=%s AND tenant_id=%s", (claim_id, body.organizationId))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail='断言不存在')
            current_status, created_by_type = row
            cur.execute("SELECT count(*),count(*) FILTER (WHERE stance IN('supports','partially_supports')) FROM mission_claim_evidence WHERE claim_id=%s AND tenant_id=%s", (claim_id, body.organizationId))
            total, supporting = cur.fetchone()
            try:
                can_promote(current_status=current_status, target_status=body.targetStatus,
                            evidence_count=int(total), supporting_evidence_count=int(supporting),
                            has_local_reviewer=body.hasLocalReviewer, created_by_type=created_by_type)
            except ValueError as exc:
                raise HTTPException(409, detail=str(exc))
            cur.execute("UPDATE mission_claims SET status=%s,updated_at=now() WHERE id=%s AND tenant_id=%s", (body.targetStatus, claim_id, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_claim', resource_id=str(claim_id), result='success', reason=body.targetStatus)
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'claimId': claim_id, 'status': body.targetStatus}
