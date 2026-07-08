"""
Structured backend for Batches 9-13.

Prefix: /api/formation-advanced

This complements the generic /api/formation-os record store with concrete
tables for doctrine learning, AI tutor consent/profile, formation analytics,
productization, and master-build acceptance evidence.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/formation-advanced", tags=["formation-advanced"])

_state: Dict[str, Any] = {}

DOCTRINE_TOPICS = [
    {"key": "scripture", "title": "Scripture and Revelation", "anchors": ["2 Tim 3:16", "Heb 1:1-2"]},
    {"key": "trinity", "title": "Trinity", "anchors": ["Matt 28:19", "2 Cor 13:14"]},
    {"key": "creation_fall", "title": "Creation and Fall", "anchors": ["Gen 1-3", "Rom 5:12"]},
    {"key": "christology", "title": "Christology", "anchors": ["John 1:1-18", "Col 1:15-20"]},
    {"key": "salvation", "title": "Salvation by Grace", "anchors": ["Eph 2:8-10", "Rom 3:21-26"]},
    {"key": "church", "title": "Church and Sacraments", "anchors": ["Acts 2:42", "Eph 4:1-16"]},
    {"key": "last_things", "title": "New Creation and Hope", "anchors": ["Rev 21-22", "1 Cor 15"]},
]

SUBSCRIPTION_PLANS = [
    {"key": "personal", "name": "Personal Formation", "price_cents": 0, "features": ["private formation", "AI tutor", "local analytics"]},
    {"key": "group", "name": "Group Formation", "price_cents": 1900, "features": ["accountability groups", "mentor-safe summaries"]},
    {"key": "church", "name": "Church OS", "price_cents": 9900, "features": ["tenant isolation", "admin console", "pastoral workflows"]},
    {"key": "institution", "name": "Institution", "price_cents": 29900, "features": ["audit exports", "custom policy", "usage governance"]},
]


def init_formation_advanced_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load(value: Any, default: Any = None) -> Any:
    if value is None:
        return [] if default is None else default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return [] if default is None else default


def _iso(value: Any) -> str:
    if value is None:
        return ""
    conv = _state.get("to_shanghai_iso")
    return conv(value) if conv else str(value)


def _crisis(text: str) -> dict:
    try:
        from safety_scan import scan_crisis
        return scan_crisis(text) or {}
    except Exception:
        lowered = (text or "").lower()
        high = any(term in lowered for term in ["suicide", "self harm", "kill myself", "自杀", "自残"])
        return {"risk_level": "high", "route": "crisis"} if high else {}


@router.get("/meta")
def meta(request: Request) -> dict:
    _require_user(request)
    return {
        "ok": True,
        "modules": [
            {"batch": 9, "key": "bible_doctrine", "endpoints": ["/bible-doctrine/topics", "/bible-doctrine/paths"]},
            {"batch": 10, "key": "formation_agent", "endpoints": ["/formation-agent/profile", "/formation-agent/recommendations"]},
            {"batch": 11, "key": "formation_analytics", "endpoints": ["/analytics/dashboard", "/analytics/reports"]},
            {"batch": 12, "key": "productization", "endpoints": ["/productization/tenants", "/productization/subscriptions"]},
            {"batch": 13, "key": "master_build", "endpoints": ["/master-build/registry", "/master-build/acceptance-matrix"]},
        ],
        "safety_contract": "Consent before sharing; crisis before coaching; grace before metrics.",
    }


@router.get("/bible-doctrine/topics")
def doctrine_topics(request: Request) -> dict:
    _require_user(request)
    return {"ok": True, "topics": DOCTRINE_TOPICS}


class DoctrinePathCreate(BaseModel):
    topic_key: str = Field(default="christology", max_length=80)
    tradition_context: str = Field(default="", max_length=120)
    duration_days: int = Field(default=30, ge=1, le=365)
    goals: List[str] = Field(default_factory=list)


@router.post("/bible-doctrine/paths")
def create_doctrine_path(request: Request, body: DoctrinePathCreate) -> dict:
    user = _require_user(request)
    path_id = uuid.uuid4().hex
    topic = next((item for item in DOCTRINE_TOPICS if item["key"] == body.topic_key), DOCTRINE_TOPICS[3])
    lessons = [
        {"key": f"{topic['key']}_intro", "title": f"{topic['title']} overview", "anchors": topic["anchors"]},
        {"key": f"{topic['key']}_biblical", "title": "Trace the biblical storyline", "anchors": topic["anchors"]},
        {"key": f"{topic['key']}_formation", "title": "Formation implications", "anchors": topic["anchors"]},
    ]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE doctrine_learning_paths SET status='archived', updated_at=NOW() WHERE email=%s AND status='active'", (user["email"],))
            cur.execute(
                "INSERT INTO doctrine_learning_paths (id, email, topic_key, tradition_context, duration_days, goals, lessons) "
                "VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                (path_id, user["email"], topic["key"], body.tradition_context, body.duration_days, _json(body.goals), _json(lessons)),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] create failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "path_id": path_id, "topic": topic, "lessons": lessons}


@router.get("/bible-doctrine/paths/active")
def active_doctrine_path(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, topic_key, tradition_context, duration_days, goals, lessons, created_at FROM doctrine_learning_paths "
                "WHERE email=%s AND status='active' ORDER BY created_at DESC LIMIT 1",
                (user["email"],),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "path": None}
    return {"ok": True, "path": {"id": row[0], "topic_key": row[1], "tradition_context": row[2] or "",
            "duration_days": row[3], "goals": _load(row[4]), "lessons": _load(row[5]), "created_at": _iso(row[6])}}


class DoctrineProgressBody(BaseModel):
    lesson_key: str = Field(..., max_length=120)
    status: str = Field(default="completed", max_length=20)
    reflection: str = Field(default="", max_length=4000)


@router.post("/bible-doctrine/paths/{path_id}/progress")
def record_doctrine_progress(path_id: str, request: Request, body: DoctrineProgressBody) -> dict:
    user = _require_user(request)
    progress_id = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM doctrine_learning_paths WHERE id=%s AND email=%s", (path_id, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="path not found")
            cur.execute(
                "INSERT INTO doctrine_lesson_progress (id, path_id, email, lesson_key, status, reflection) VALUES (%s,%s,%s,%s,%s,%s)",
                (progress_id, path_id, user["email"], body.lesson_key, body.status, body.reflection),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] progress failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="progress failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "progress_id": progress_id}


@router.get("/bible-doctrine/graph/search")
def doctrine_graph_search(request: Request, query: str = Query(default="", max_length=200)) -> dict:
    _require_user(request)
    q = (query or "").lower()
    topics = [t for t in DOCTRINE_TOPICS if not q or q in t["key"] or q in t["title"].lower()]
    if not topics:
        topics = DOCTRINE_TOPICS[:3]
    return {"ok": True, "nodes": topics, "edges": [
        {"from": "scripture", "to": "christology", "relationship": "reveals"},
        {"from": "christology", "to": "salvation", "relationship": "grounds"},
        {"from": "salvation", "to": "church", "relationship": "forms_people"},
    ]}


class ApologeticsDialogueBody(BaseModel):
    question: str = Field(..., max_length=4000)
    topic_key: str = Field(default="general", max_length=80)
    audience_context: str = Field(default="", max_length=1000)


@router.post("/bible-doctrine/apologetics/dialogues")
def create_apologetics_dialogue(request: Request, body: ApologeticsDialogueBody) -> dict:
    user = _require_user(request)
    did = uuid.uuid4().hex
    response = {
        "posture": "charitable, non-coercive, and Scripture-shaped",
        "answer_outline": ["clarify the real question", "name the secular assumption fairly", "frame with creation-fall-redemption-hope", "invite honest next conversation"],
        "boundaries": ["do not weaponize doctrine", "do not pretend certainty where Scripture is silent"],
    }
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO apologetics_dialogues (id, email, topic_key, question, audience_context, response) "
                "VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
                (did, user["email"], body.topic_key, body.question, body.audience_context, _json(response)),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] create failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "dialogue_id": did, "response": response}


@router.get("/bible-doctrine/apologetics/dialogues")
def list_apologetics_dialogues(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, topic_key, question, response, created_at FROM apologetics_dialogues WHERE email=%s ORDER BY created_at DESC LIMIT 50", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "dialogues": [{"id": r[0], "topic_key": r[1], "question": r[2], "response": _load(r[3], {}), "created_at": _iso(r[4])} for r in rows]}


class AgentProfileBody(BaseModel):
    season: str = Field(default="stable_growth", max_length=80)
    consent_ai_tutor: bool = Field(default=True)
    consent_mentor_summary: bool = Field(default=False)
    formation_focuses: List[str] = Field(default_factory=list)
    boundaries: List[str] = Field(default_factory=list)


@router.post("/formation-agent/profiles")
def upsert_agent_profile(request: Request, body: AgentProfileBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ai_formation_profiles (email, season, consent_ai_tutor, consent_mentor_summary, formation_focuses, boundaries) "
                "VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb) "
                "ON CONFLICT (email) DO UPDATE SET season=EXCLUDED.season, consent_ai_tutor=EXCLUDED.consent_ai_tutor, "
                "consent_mentor_summary=EXCLUDED.consent_mentor_summary, formation_focuses=EXCLUDED.formation_focuses, "
                "boundaries=EXCLUDED.boundaries, updated_at=NOW()",
                (user["email"], body.season, body.consent_ai_tutor, body.consent_mentor_summary, _json(body.formation_focuses), _json(body.boundaries)),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] profile failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="profile failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.get("/formation-agent/profile")
def get_agent_profile(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT season, consent_ai_tutor, consent_mentor_summary, formation_focuses, boundaries, updated_at FROM ai_formation_profiles WHERE email=%s", (user["email"],))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "profile": None}
    return {"ok": True, "profile": {"season": row[0], "consent_ai_tutor": bool(row[1]),
            "consent_mentor_summary": bool(row[2]), "formation_focuses": _load(row[3]), "boundaries": _load(row[4]), "updated_at": _iso(row[5])}}


class RecommendationBody(BaseModel):
    context_text: str = Field(default="", max_length=4000)
    max_items: int = Field(default=3, ge=1, le=5)


@router.post("/formation-agent/recommendations")
def create_recommendation(request: Request, body: RecommendationBody) -> dict:
    user = _require_user(request)
    risk = _crisis(body.context_text)
    if risk:
        return {"ok": True, "safety": risk, "recommendations": ["先寻求即时真人帮助，再处理普通成长计划。"]}
    items = [
        {"module": "scripture", "action": "Read one short passage and write one honest response."},
        {"module": "prayer", "action": "Pray one sentence of surrender before the next task."},
        {"module": "community", "action": "Message one trusted person with a simple update."},
        {"module": "habit", "action": "Choose one practice to simplify today."},
        {"module": "mission", "action": "Do one concrete act of love in your current role."},
    ][: body.max_items]
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ai_formation_recommendations (id, email, context_text, recommendations) VALUES (%s,%s,%s,%s::jsonb)",
                        (rid, user["email"], body.context_text, _json(items)))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] recommend failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="recommend failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "recommendation_id": rid, "recommendations": items}


class TutorConversationBody(BaseModel):
    message: str = Field(..., max_length=6000)
    conversation_type: str = Field(default="formation", max_length=40)


@router.post("/formation-agent/conversations")
def create_tutor_conversation(request: Request, body: TutorConversationBody) -> dict:
    user = _require_user(request)
    risk = _crisis(body.message)
    if risk:
        reply = "This sounds like it may need immediate human care. Please contact a trusted person, pastor, local emergency service, or crisis support now."
    else:
        reply = "I can help you notice grace, choose one small next step, and keep this within Scripture, church, and safety boundaries."
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ai_tutor_conversations (id, email, conversation_type, user_message, assistant_reply, safety_flags) "
                        "VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
                        (cid, user["email"], body.conversation_type, body.message, reply, _json(risk)))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] conversation failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="conversation failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "conversation_id": cid, "reply": reply, "safety": risk}


@router.get("/formation-agent/conversations")
def list_tutor_conversations(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, conversation_type, user_message, assistant_reply, safety_flags, created_at FROM ai_tutor_conversations WHERE email=%s ORDER BY created_at DESC LIMIT 50", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "conversations": [{"id": r[0], "conversation_type": r[1], "user_message": r[2],
            "assistant_reply": r[3], "safety": _load(r[4], {}), "created_at": _iso(r[5])} for r in rows]}


class MetricSnapshotBody(BaseModel):
    metrics: Dict[str, Any] = Field(default_factory=dict)
    grace_evidence: List[str] = Field(default_factory=list)
    period_key: str = Field(default="week", max_length=40)


@router.post("/analytics/snapshots")
def create_metric_snapshot(request: Request, body: MetricSnapshotBody) -> dict:
    user = _require_user(request)
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_metric_snapshots (id, email, period_key, metrics, grace_evidence) VALUES (%s,%s,%s,%s::jsonb,%s::jsonb)",
                        (sid, user["email"], body.period_key, _json(body.metrics), _json(body.grace_evidence)))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] snapshot failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="snapshot failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "snapshot_id": sid}


@router.get("/analytics/dashboard")
def analytics_dashboard(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT period_key, metrics, grace_evidence, created_at FROM formation_metric_snapshots WHERE email=%s ORDER BY created_at DESC LIMIT 12", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    snapshots = [{"period_key": r[0], "metrics": _load(r[1], {}), "grace_evidence": _load(r[2]), "created_at": _iso(r[3])} for r in rows]
    return {"ok": True, "dashboard": {"snapshots": snapshots, "not_holiness_score": True,
            "summary": "Metrics are mirrors for discernment, not proof of worth."}}


class ReportBody(BaseModel):
    title: str = Field(default="Formation Review", max_length=200)
    report_scope: str = Field(default="private", max_length=40)
    content: Dict[str, Any] = Field(default_factory=dict)
    mentor_safe: bool = Field(default=False)


@router.post("/analytics/reports")
def create_formation_report(request: Request, body: ReportBody) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_review_reports (id, email, title, report_scope, content, mentor_safe) VALUES (%s,%s,%s,%s,%s::jsonb,%s)",
                        (rid, user["email"], body.title, body.report_scope, _json(body.content), body.mentor_safe))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] report failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="report failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "report_id": rid}


@router.get("/analytics/reports")
def list_formation_reports(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, report_scope, content, mentor_safe, created_at FROM formation_review_reports WHERE email=%s ORDER BY created_at DESC LIMIT 50", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "reports": [{"id": r[0], "title": r[1], "report_scope": r[2], "content": _load(r[3], {}),
            "mentor_safe": bool(r[4]), "created_at": _iso(r[5])} for r in rows]}


class IntegrityAuditBody(BaseModel):
    audit_type: str = Field(default="privacy", max_length=40)
    findings: List[str] = Field(default_factory=list)


@router.post("/analytics/integrity-audits")
def create_integrity_audit(request: Request, body: IntegrityAuditBody) -> dict:
    user = _require_user(request)
    aid = uuid.uuid4().hex
    status = "attention_needed" if body.findings else "passed"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_integrity_audits (id, email, audit_type, status, findings) VALUES (%s,%s,%s,%s,%s::jsonb)",
                        (aid, user["email"], body.audit_type, status, _json(body.findings)))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] audit failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="audit failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "audit_id": aid, "status": status}


class TenantCreate(BaseModel):
    name: str = Field(..., max_length=200)
    tenant_type: str = Field(default="church", max_length=40)


@router.post("/productization/tenants")
def create_tenant(request: Request, body: TenantCreate) -> dict:
    user = _require_user(request)
    tid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_tenants (id, name, tenant_type, owner_email) VALUES (%s,%s,%s,%s)",
                        (tid, body.name, body.tenant_type, user["email"]))
            cur.execute("INSERT INTO formation_tenant_members (id, tenant_id, email, role) VALUES (%s,%s,%s,'owner')",
                        (uuid.uuid4().hex, tid, user["email"]))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] tenant failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="tenant failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "tenant_id": tid}


@router.get("/productization/tenants")
def list_tenants(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT t.id, t.name, t.tenant_type, t.status, m.role FROM formation_tenants t "
                        "JOIN formation_tenant_members m ON t.id=m.tenant_id WHERE m.email=%s ORDER BY t.created_at DESC",
                        (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "tenants": [{"id": r[0], "name": r[1], "tenant_type": r[2], "status": r[3], "my_role": r[4]} for r in rows]}


class TenantMemberBody(BaseModel):
    email: str = Field(..., max_length=255)
    role: str = Field(default="member", max_length=40)


@router.post("/productization/tenants/{tenant_id}/members")
def add_tenant_member(tenant_id: str, request: Request, body: TenantMemberBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM formation_tenant_members WHERE tenant_id=%s AND email=%s", (tenant_id, user["email"]))
            row = cur.fetchone()
            if not row or row[0] not in ("owner", "admin"):
                raise HTTPException(status_code=403, detail="tenant admin required")
            cur.execute("INSERT INTO formation_tenant_members (id, tenant_id, email, role) VALUES (%s,%s,%s,%s)",
                        (uuid.uuid4().hex, tenant_id, body.email, body.role))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] member failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="member failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.get("/productization/subscription-plans")
def subscription_plans(request: Request) -> dict:
    _require_user(request)
    return {"ok": True, "plans": SUBSCRIPTION_PLANS, "crisis_soft_fail": True}


class SubscriptionBody(BaseModel):
    tenant_id: str = Field(default="", max_length=64)
    plan_key: str = Field(default="personal", max_length=40)
    billing_status: str = Field(default="trialing", max_length=40)


@router.post("/productization/subscriptions")
def create_subscription(request: Request, body: SubscriptionBody) -> dict:
    user = _require_user(request)
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_subscriptions (id, email, tenant_id, plan_key, billing_status) VALUES (%s,%s,%s,%s,%s)",
                        (sid, user["email"], body.tenant_id, body.plan_key, body.billing_status))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] subscription failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="subscription failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "subscription_id": sid}


class ModerationCaseBody(BaseModel):
    tenant_id: str = Field(default="", max_length=64)
    case_type: str = Field(default="content", max_length=40)
    severity: str = Field(default="low", max_length=20)
    summary: str = Field(default="", max_length=4000)


@router.post("/productization/moderation-cases")
def create_moderation_case(request: Request, body: ModerationCaseBody) -> dict:
    user = _require_user(request)
    mid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_moderation_cases (id, tenant_id, reporter_email, case_type, severity, summary) "
                        "VALUES (%s,%s,%s,%s,%s,%s)",
                        (mid, body.tenant_id, user["email"], body.case_type, body.severity, body.summary))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] moderation failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="moderation failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "case_id": mid}


@router.get("/productization/deployment-health")
def deployment_health(request: Request) -> dict:
    _require_user(request)
    return {"ok": True, "health": {"database": "migration-backed", "tenant_isolation": "email+tenant scoped",
            "admin_audit": "enabled", "runbooks": ["health", "backup", "incident", "rollback"]}}


@router.get("/master-build/registry")
def master_registry(request: Request) -> dict:
    _require_user(request)
    return {"ok": True, "registry": {"batches": list(range(1, 14)), "skills": 52,
            "backend_boundaries": ["generic formation-os", "structured B7", "structured B9-13"]}}


class MasterBuildRunBody(BaseModel):
    run_type: str = Field(default="full_stack_validation", max_length=80)
    status: str = Field(default="planned", max_length=40)
    evidence: Dict[str, Any] = Field(default_factory=dict)


@router.post("/master-build/runs")
def create_master_run(request: Request, body: MasterBuildRunBody) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO master_build_runs (id, email, run_type, status, evidence) VALUES (%s,%s,%s,%s,%s::jsonb)",
                        (rid, user["email"], body.run_type, body.status, _json(body.evidence)))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] run failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="run failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "run_id": rid}


@router.get("/master-build/runs")
def list_master_runs(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, run_type, status, evidence, created_at FROM master_build_runs WHERE email=%s ORDER BY created_at DESC LIMIT 50", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "runs": [{"id": r[0], "run_type": r[1], "status": r[2], "evidence": _load(r[3], {}), "created_at": _iso(r[4])} for r in rows]}


class AcceptanceCheckBody(BaseModel):
    batch: int = Field(..., ge=1, le=13)
    check_key: str = Field(..., max_length=120)
    status: str = Field(default="passed", max_length=40)
    evidence: Dict[str, Any] = Field(default_factory=dict)


@router.post("/master-build/acceptance-checks")
def create_acceptance_check(request: Request, body: AcceptanceCheckBody) -> dict:
    user = _require_user(request)
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO master_acceptance_checks (id, email, batch, check_key, status, evidence) VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
                        (cid, user["email"], body.batch, body.check_key, body.status, _json(body.evidence)))
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[error] acceptance failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="acceptance failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "check_id": cid}


@router.get("/master-build/acceptance-matrix")
def acceptance_matrix(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT batch, check_key, status, evidence, created_at FROM master_acceptance_checks WHERE email=%s ORDER BY batch, created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "matrix": [{"batch": r[0], "check_key": r[1], "status": r[2], "evidence": _load(r[3], {}), "created_at": _iso(r[4])} for r in rows],
            "required_checks": ["routes", "migrations", "tests", "build", "safety", "consent", "tenant_isolation"]}
