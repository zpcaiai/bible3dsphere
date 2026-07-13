"""Skill 61/62/63 API: financial plans, support campaigns and fund expenses."""
from __future__ import annotations
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.finance import (
    SCENARIO_TYPES, assert_scenarios_complete, scan_campaign, pledge_grants_no_governance,
    assert_expense_approval,
)

_deployment_gate = require_mission_feature('mission_deployment_enabled')
router = APIRouter(prefix='/api/v1/mission/financial-plans', tags=['mission-finance'], dependencies=[Depends(_deployment_gate)])
campaign_router = APIRouter(prefix='/api/v1/mission/support-campaigns', tags=['mission-finance'], dependencies=[Depends(_deployment_gate)])
expense_router = APIRouter(prefix='/api/v1/mission/expense-requests', tags=['mission-finance'], dependencies=[Depends(_deployment_gate)])
_state = {}


def init_mission_finance_router(*, get_db, release_db, get_session_user, is_admin):
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


class PlanBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    workerProfileId: str = Field(min_length=1)
    baseCurrency: str = Field(default='USD', max_length=8)
    householdSize: int = Field(default=1, ge=1, le=20)
    highRiskField: bool = False
    hasChildren: bool = False
    scenarioTypes: list[str] = Field(default_factory=lambda: ['baseline', 'conservative', 'support_loss'])


@router.post('')
def create_plan(body: PlanBody, request: Request):
    _user_obj, email = _user(request)
    for s in body.scenarioTypes:
        if s not in SCENARIO_TYPES:
            raise HTTPException(422, detail=f'invalid scenario type: {s}')
    try:
        assert_scenarios_complete(body.scenarioTypes, high_risk_field=body.highRiskField, has_children=body.hasChildren)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_financial_plans(tenant_id,worker_profile_id,base_currency,household_size,plan_status,created_by) "
                "VALUES(%s,%s,%s,%s,'data_collection',%s) RETURNING id",
                (body.organizationId, body.workerProfileId, body.baseCurrency, body.householdSize, email))
            pid = cur.fetchone()[0]
            for s in body.scenarioTypes:
                cur.execute("INSERT INTO mission_budget_scenarios(tenant_id,financial_plan_id,scenario_key,scenario_type) VALUES(%s,%s,%s,%s)",
                            (body.organizationId, pid, s, s))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_financial_plan', resource_id=str(pid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'financialPlanId': str(pid), 'status': 'data_collection'}


class CampaignPublishBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    campaignId: str = Field(min_length=1)
    tactics: list[str] = Field(default_factory=list)
    contentKeys: list[str] = Field(default_factory=list)


@campaign_router.post('/publish')
def publish_campaign(body: CampaignPublishBody, request: Request):
    _user_obj, email = _user(request)
    findings = scan_campaign(tactics=body.tactics, content_keys=body.contentKeys)
    if findings:
        raise HTTPException(422, detail=f'fundraising ethics findings: {findings}')
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("UPDATE mission_support_campaigns SET campaign_status='published',content_reviewed=TRUE,updated_at=now() WHERE id=%s AND tenant_id=%s AND content_reviewed=TRUE",
                        (body.campaignId, body.organizationId))
            if cur.rowcount == 0:
                raise HTTPException(409, detail='活动不存在或未通过内容审核')
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_support_campaign', resource_id=str(body.campaignId), result='success', reason='published')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'status': 'published'}


class ExpenseApproveBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    expenseRequestId: str = Field(min_length=1)
    requesterId: str = Field(min_length=1)
    amount: float = Field(ge=0)
    dualThreshold: float = Field(default=1000, ge=0)
    existingApprovals: int = Field(default=0, ge=0)


@expense_router.post('/approve')
def approve_expense(body: ExpenseApproveBody, request: Request):
    _user_obj, email = _user(request)
    try:
        assert_expense_approval(requester_id=body.requesterId, approver_id=email, amount=body.amount,
                                approvals=body.existingApprovals + 1, dual_threshold=body.dualThreshold)
    except ValueError as exc:
        raise HTTPException(403, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("INSERT INTO mission_expense_approvals(tenant_id,expense_request_id,approver_id,decision) VALUES(%s,%s,%s,'approve') ON CONFLICT DO NOTHING",
                        (body.organizationId, body.expenseRequestId, email))
            cur.execute("UPDATE mission_expense_requests SET approvals_count=approvals_count+1,updated_at=now() WHERE id=%s AND tenant_id=%s",
                        (body.expenseRequestId, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_expense_request', resource_id=str(body.expenseRequestId), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'expenseRequestId': body.expenseRequestId, 'approved': True}


@router.get('')
def list_plans(organizationId: str, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute("SELECT p.id,p.worker_profile_id,p.base_currency,p.household_size,p.plan_status,p.created_at,count(s.id) FROM mission_financial_plans p LEFT JOIN mission_budget_scenarios s ON s.financial_plan_id=p.id WHERE p.tenant_id=%s GROUP BY p.id ORDER BY p.created_at DESC LIMIT 200", (organizationId,))
            rows = [{'id': str(r[0]), 'workerProfileId': r[1], 'baseCurrency': r[2], 'householdSize': r[3],
                     'planStatus': r[4], 'createdAt': r[5].isoformat() if r[5] else None, 'scenarioCount': int(r[6])} for r in cur.fetchall()]
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'items': rows}
