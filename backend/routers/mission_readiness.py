"""Skill 34/36 API: 15-dimension readiness, panel decision and AI-draft guardrails."""
from __future__ import annotations
import json
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.readiness import (
    READINESS_DIMENSIONS, validate_dimension, assert_not_protected_downgrade,
    resolve_readiness_level, can_decide_deployment_candidate,
)
from mission_os.ai_boundaries import scan_output, sanitize_decision_field, requires_human_review

router = APIRouter(prefix='/api/v1/mission/readiness-assessments', tags=['mission-readiness'], dependencies=[Depends(require_mission_feature('mission_readiness_enabled'))])
_state = {}


def init_mission_readiness_router(*, get_db, release_db, get_session_user, is_admin):
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


class AssessmentBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    workerProfileId: str = Field(min_length=1)
    callingJourneyId: str | None = None


@router.post('')
def create_assessment(body: AssessmentBody, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_readiness_assessments(tenant_id,worker_profile_id,calling_journey_id,assessment_status) "
                "VALUES(%s,%s,%s,'self_assessment') RETURNING id",
                (body.organizationId, body.workerProfileId, body.callingJourneyId))
            aid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_readiness_assessment', resource_id=str(aid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'assessmentId': str(aid), 'status': 'self_assessment', 'dimensions': list(READINESS_DIMENSIONS)}


class DimensionBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    dimensionKey: str = Field(min_length=2, max_length=64)
    finalLevel: str = Field(min_length=2, max_length=48)
    blocking: bool = False
    downgradeReasonCodes: list[str] = Field(default_factory=list)
    explanation: str | None = Field(default=None, max_length=2000)


@router.post('/{assessment_id}/dimensions')
def set_dimension(assessment_id: str, body: DimensionBody, request: Request):
    _user_obj, email = _user(request)
    try:
        validate_dimension(body.dimensionKey, body.finalLevel)
        # protected attributes may never be the sole justification for a downgrade
        if body.finalLevel in ('significant_concern', 'developing'):
            assert_not_protected_downgrade(body.downgradeReasonCodes)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_readiness_dimensions(tenant_id,assessment_id,dimension_key,final_level,blocking,explanation) "
                "VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,assessment_id,dimension_key) DO UPDATE SET final_level=EXCLUDED.final_level,blocking=EXCLUDED.blocking,explanation=EXCLUDED.explanation",
                (body.organizationId, assessment_id, body.dimensionKey, body.finalLevel, body.blocking, body.explanation))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='update',
                  resource_type='mission_readiness_dimension', resource_id=f'{assessment_id}:{body.dimensionKey}', result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'dimensionKey': body.dimensionKey, 'finalLevel': body.finalLevel}


class PanelDecisionBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    workerUserId: str = Field(min_length=1)
    isPanel: bool = False
    hardBlocks: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=3, max_length=2000)


@router.post('/{assessment_id}/panel-decision')
def panel_decision(assessment_id: str, body: PanelDecisionBody, request: Request):
    _user_obj, email = _user(request)
    try:
        can_decide_deployment_candidate(decider_type='human', is_panel=body.isPanel,
                                        candidate_id=body.workerUserId, decider_id=email,
                                        hard_blocks=body.hardBlocks)
    except ValueError as exc:
        raise HTTPException(403, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_readiness_decisions(tenant_id,assessment_id,decision_type,readiness_level,rationale,decided_by,is_panel) "
                "VALUES(%s,%s,'deployment_candidate','deployment_candidate',%s,%s,%s) RETURNING id",
                (body.organizationId, assessment_id, body.rationale, email, body.isPanel))
            did = cur.fetchone()[0]
            cur.execute("UPDATE mission_readiness_assessments SET readiness_level='deployment_candidate',assessment_status='completed',reviewed_by=%s,updated_at=now() WHERE id=%s AND tenant_id=%s",
                        (email, assessment_id, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_readiness_assessment', resource_id=str(assessment_id), result='success', reason='deployment_candidate')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'decisionId': str(did), 'readinessLevel': 'deployment_candidate'}


class AiDraftBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    draft: dict = Field(default_factory=dict)
    outputText: str = ''
    triggers: list[str] = Field(default_factory=list)


@router.post('/{assessment_id}/ai-draft')
def ai_draft(assessment_id: str, body: AiDraftBody, request: Request):
    """Store an AI draft after forcing decision=null, scanning for policy findings,
    and flagging human review. The AI can never decide readiness."""
    _user_obj, email = _user(request)
    findings = scan_output(body.outputText)
    safe = sanitize_decision_field(body.draft)  # decision -> None, requires_human_review -> True
    needs_review = requires_human_review(body.triggers) or bool(findings)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            for f in findings:
                cur.execute("INSERT INTO mission_ai_policy_findings(tenant_id,model_run_id,finding_type,severity,summary,action_taken) VALUES(%s,%s,%s,'high','ai calling output',%s)",
                            (body.organizationId, str(assessment_id), f, 'blocked_and_rewritten'))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='ai_generate',
                  resource_type='mission_readiness_assessment', resource_id=str(assessment_id),
                  result='blocked' if findings else 'success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'draft': safe, 'policyFindings': findings, 'requiresHumanReview': needs_review}


@router.get('')
def list_assessments(organizationId: str, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute("SELECT id,worker_profile_id,assessment_status,readiness_level,created_at FROM mission_readiness_assessments WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200", (organizationId,))
            rows = [{'id': str(r[0]), 'workerProfileId': r[1], 'assessmentStatus': r[2], 'readinessLevel': r[3],
                     'createdAt': r[4].isoformat() if r[4] else None} for r in cur.fetchall()]
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'items': rows, 'dimensions': list(READINESS_DIMENSIONS)}
