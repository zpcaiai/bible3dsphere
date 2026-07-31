"""Authenticated product API for Spiritual Planet discernment Batches 01-06."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from psycopg2.extras import Json, RealDictCursor

from discernment_platform import DialogueEngine, DiscernmentEngine, GospelPathEngine, get_registry
from discernment_platform.models import (
    AdminReviewDecision,
    DialogueStart,
    DialogueTurn,
    DiscernmentCaseCreate,
    GospelPathRequest,
    ReviewRequest,
)


router = APIRouter(prefix="/api/v1/platform/discernment", tags=["spiritual-planet-discernment"])
_state: dict[str, Any] = {}
_engine = DiscernmentEngine()
_dialogue = DialogueEngine()
_gospel = GospelPathEngine()


def init_spiritual_planet_discernment_router(*, get_db, release_db, get_session_user, is_admin=None) -> None:
    _state.update(locals())


def _user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _admin(request: Request) -> dict:
    user = _user(request)
    checker = _state.get("is_admin")
    if not checker or not checker(user["email"]):
        raise HTTPException(status_code=403, detail="discernment reviewer only")
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


def _case_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "title": row["title"], "subject_type": row["subject_type"],
        "user_goal": row["user_goal"], "faith_context": row["faith_context"],
        "sensitivity": row["sensitivity"], "workflow_state": row["workflow_state"],
        "review_status": row["review_status"], "created_at": row["created_at"], "updated_at": row["updated_at"],
        "summary": (row.get("report_json") or {}).get("summary", ""),
    }


def _fetch_case(cur, case_id: uuid.UUID, email: str) -> dict[str, Any]:
    cur.execute(
        "SELECT * FROM spiritual_planet_discernment_cases WHERE id=%s AND email=%s AND deleted_at IS NULL",
        (str(case_id), email),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Discernment case not found")
    return dict(row)


@router.get("/catalog")
def catalog(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, "catalog": get_registry().catalog()}


@router.post("/cases", status_code=201)
def create_case(body: DiscernmentCaseCreate, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    case_id = str(uuid.uuid4())
    report = _engine.analyze(case_id=case_id, case=body)
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "INSERT INTO spiritual_planet_discernment_cases"
                "(id,tenant_id,email,title,subject_type,user_goal,faith_context,sensitivity,consent_scope_json,input_json,report_json,engine_versions_json,workflow_state,review_status) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    case_id, tenant_id, email, body.title, body.subject_type, body.user_goal,
                    body.faith_context, body.sensitivity, Json(body.consent_scope.model_dump(mode="json")),
                    Json(body.model_dump(mode="json")), Json(report), Json(report["engine_versions"]),
                    report["trace"][-1]["state"], report["review_status"],
                ),
            )
            for item in body.source_items:
                cur.execute(
                    "INSERT INTO spiritual_planet_discernment_evidence"
                    "(tenant_id,email,case_id,source_type,locator,excerpt,evidence_level,independence_group,limitations_json) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (tenant_id, email, case_id, item.source_type, item.locator, item.quote, item.evidence_level, item.independence_group, Json(item.limitations)),
                )
            conn.commit()
        return {"ok": True, "case": {"id": case_id, "title": body.title, "review_status": report["review_status"]}, "report": report}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.get("/cases")
def list_cases(request: Request, limit: int = Query(default=30, ge=1, le=100)) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT id,title,subject_type,user_goal,faith_context,sensitivity,workflow_state,review_status,report_json,created_at,updated_at "
                "FROM spiritual_planet_discernment_cases WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT %s",
                (email, limit),
            )
            items = [_case_summary(dict(row)) for row in cur.fetchall()]
        return {"ok": True, "cases": items}
    finally:
        _release(conn)


@router.get("/cases/{case_id}")
def get_case(case_id: uuid.UUID, request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            row = _fetch_case(cur, case_id, email)
            cur.execute(
                "SELECT actor_type,action,note,correction_json,created_at FROM spiritual_planet_discernment_reviews "
                "WHERE case_id=%s AND email=%s ORDER BY created_at",
                (str(case_id), email),
            )
            reviews = [dict(item) for item in cur.fetchall()]
        return {"ok": True, "case": _case_summary(row), "input": row["input_json"], "report": row["report_json"], "gospel_path": row["gospel_path_json"], "reviews": reviews}
    finally:
        _release(conn)


@router.post("/cases/{case_id}/reanalyze")
def reanalyze_case(case_id: uuid.UUID, request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            row = _fetch_case(cur, case_id, email)
            case = DiscernmentCaseCreate.model_validate(row["input_json"])
            report = _engine.analyze(case_id=str(case_id), case=case)
            cur.execute(
                "UPDATE spiritual_planet_discernment_cases SET report_json=%s,engine_versions_json=%s,workflow_state=%s,review_status=%s,updated_at=NOW() "
                "WHERE id=%s AND email=%s",
                (Json(report), Json(report["engine_versions"]), report["trace"][-1]["state"], report["review_status"], str(case_id), email),
            )
            conn.commit()
        return {"ok": True, "report": report}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.delete("/cases/{case_id}")
def delete_case(case_id: uuid.UUID, request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "UPDATE spiritual_planet_discernment_cases SET deleted_at=NOW(),review_status='withdrawn',updated_at=NOW() "
                "WHERE id=%s AND email=%s AND deleted_at IS NULL RETURNING id",
                (str(case_id), email),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Discernment case not found")
            cur.execute("UPDATE spiritual_planet_discernment_dialogue_sessions SET deleted_at=NOW(),status='EXITED_BY_USER' WHERE case_id=%s AND email=%s", (str(case_id), email))
            conn.commit()
        return {"ok": True, "status": "withdrawn"}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/cases/{case_id}/dialogue", status_code=201)
def start_dialogue(case_id: uuid.UUID, body: DialogueStart, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    session_id = str(uuid.uuid4())
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            row = _fetch_case(cur, case_id, email)
            state = _dialogue.initialize(session_id=session_id, case_id=str(case_id), report=row["report_json"], faith_context=row["faith_context"])
            cur.execute(
                "INSERT INTO spiritual_planet_discernment_dialogue_sessions"
                "(id,tenant_id,email,case_id,status,stage,difficulty,gospel_consent,state_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (session_id, tenant_id, email, str(case_id), state["status"], state["stage"], state["difficulty"], state["gospel_consent"], Json(state)),
            )
            first = state["turns"][0]
            cur.execute(
                "INSERT INTO spiritual_planet_discernment_dialogue_turns(tenant_id,email,session_id,turn_index,speaker,content,stage,difficulty) VALUES(%s,%s,%s,0,'assistant',%s,%s,%s)",
                (tenant_id, email, session_id, first["content"], first["stage"], state["difficulty"]),
            )
            conn.commit()
        return {"ok": True, "session": state, "preferred_depth": body.preferred_depth}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/dialogues/{session_id}/turns")
def dialogue_turn(session_id: uuid.UUID, body: DialogueTurn, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute(
                "SELECT s.*,c.sensitivity FROM spiritual_planet_discernment_dialogue_sessions s "
                "JOIN spiritual_planet_discernment_cases c ON c.id=s.case_id "
                "WHERE s.id=%s AND s.email=%s AND s.deleted_at IS NULL AND c.deleted_at IS NULL FOR UPDATE",
                (str(session_id), email),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Dialogue session not found")
            old_state = row["state_json"]
            state = _dialogue.receive(old_state, answer=body.answer, gospel_consent=body.gospel_consent, sensitivity=row["sensitivity"])
            start_index = len(old_state.get("turns", []))
            for offset, turn in enumerate(state["turns"][start_index:]):
                cur.execute(
                    "INSERT INTO spiritual_planet_discernment_dialogue_turns"
                    "(tenant_id,email,session_id,turn_index,speaker,content,stage,difficulty,safety_event_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (tenant_id, email, str(session_id), start_index + offset, turn["speaker"], turn["content"], turn.get("stage"), state["difficulty"], Json(state.get("safety_events", [])[-1] if state.get("safety_events") else {})),
                )
            cur.execute(
                "UPDATE spiritual_planet_discernment_dialogue_sessions SET status=%s,stage=%s,difficulty=%s,gospel_consent=%s,state_json=%s,updated_at=NOW(),completed_at=CASE WHEN %s='COMPLETED' THEN NOW() ELSE completed_at END WHERE id=%s AND email=%s",
                (state["status"], state["stage"], state["difficulty"], state["gospel_consent"], Json(state), state["status"], str(session_id), email),
            )
            conn.commit()
        return {"ok": True, "session": state}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/dialogues/{session_id}/pause")
def pause_dialogue(session_id: uuid.UUID, request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            cur.execute("SELECT state_json FROM spiritual_planet_discernment_dialogue_sessions WHERE id=%s AND email=%s AND deleted_at IS NULL FOR UPDATE", (str(session_id), email))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Dialogue session not found")
            state = row["state_json"]
            state.update(status="PAUSED_BY_USER", current_question=None)
            cur.execute("UPDATE spiritual_planet_discernment_dialogue_sessions SET status='PAUSED_BY_USER',state_json=%s,updated_at=NOW() WHERE id=%s AND email=%s", (Json(state), str(session_id), email))
            conn.commit()
        return {"ok": True, "session": state}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/cases/{case_id}/gospel-path")
def gospel_path(case_id: uuid.UUID, body: GospelPathRequest, request: Request) -> dict[str, Any]:
    user = _user(request)
    _, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            row = _fetch_case(cur, case_id, email)
            case = DiscernmentCaseCreate.model_validate(row["input_json"])
            report = row["report_json"]
            plan = _gospel.build(
                case_id=str(case_id), presenting_issue=case.raw_input, faith_context=case.faith_context,
                consent_scope=case.consent_scope.model_dump(), pride_hypotheses=report.get("pride_hypotheses", []),
                desire_map=report.get("desire_map", []), sensitivity=case.sensitivity,
                preferred_depth=body.preferred_depth, church_context=body.church_context,
            )
            cur.execute("UPDATE spiritual_planet_discernment_cases SET gospel_path_json=%s,updated_at=NOW() WHERE id=%s AND email=%s", (Json(plan), str(case_id), email))
            conn.commit()
        return {"ok": True, "gospel_path": plan}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/cases/{case_id}/reviews", status_code=201)
def create_review(case_id: uuid.UUID, body: ReviewRequest, request: Request) -> dict[str, Any]:
    user = _user(request)
    tenant_id, email = _identity(user["email"])
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _owner(cur, email)
            _fetch_case(cur, case_id, email)
            cur.execute(
                "INSERT INTO spiritual_planet_discernment_reviews(tenant_id,email,case_id,actor_type,actor_id,action,note,correction_json) VALUES(%s,%s,%s,'USER',%s,%s,%s,%s) RETURNING id,created_at",
                (tenant_id, email, str(case_id), email, body.action, body.note, Json(body.correction)),
            )
            review = dict(cur.fetchone())
            if body.action == "WITHDRAW":
                cur.execute("UPDATE spiritual_planet_discernment_cases SET review_status='withdrawn',updated_at=NOW() WHERE id=%s AND email=%s", (str(case_id), email))
            elif body.action == "REQUEST_REVIEW":
                cur.execute("UPDATE spiritual_planet_discernment_cases SET review_status='human_review_required',updated_at=NOW() WHERE id=%s AND email=%s", (str(case_id), email))
            conn.commit()
        return {"ok": True, "review": {"id": str(review["id"]), "action": body.action, "created_at": review["created_at"]}}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


@router.post("/admin/cases/{case_id}/review")
def admin_review(case_id: uuid.UUID, body: AdminReviewDecision, request: Request) -> dict[str, Any]:
    reviewer = _admin(request)
    reviewer_email = reviewer["email"].lower()
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM spiritual_planet_discernment_cases WHERE id=%s AND deleted_at IS NULL FOR UPDATE", (str(case_id),))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Discernment case not found")
            owner_email = row["email"]
            _owner(cur, owner_email)
            status = "ready" if body.decision == "APPROVED" else "blocked" if body.decision == "BLOCKED" else "human_review_required"
            cur.execute(
                "INSERT INTO spiritual_planet_discernment_reviews(tenant_id,email,case_id,actor_type,actor_id,action,note) VALUES(%s,%s,%s,'ADMIN_REVIEWER',%s,%s,%s)",
                (row["tenant_id"], owner_email, str(case_id), reviewer_email, body.decision, body.note),
            )
            cur.execute("UPDATE spiritual_planet_discernment_cases SET review_status=%s,updated_at=NOW() WHERE id=%s", (status, str(case_id)))
            conn.commit()
        return {"ok": True, "review_status": status}
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)
