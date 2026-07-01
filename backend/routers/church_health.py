"""
Church Health OS router — 健康教会九标志 (/api/church-health)
================================================================

把 9Marks 的理念落成属灵星球的「教会健康生态层」。所有端点按登录用户 email 归属，
懒建表（ch_*），隐私优先，AI 不定罪/不赦罪/不执行纪律，遇危机 crisis-first。

端点：
  GET  /api/church-health/meta                元信息（九标志字典 + 边界）
  GET  /api/church-health/marks               九标志字典（meta.marks 别名）
  GET  /api/church-health/membership/me        我的本地教会委身档案
  PUT  /api/church-health/membership           创建/更新委身档案（upsert）
  POST /api/church-health/sermons              保存主日讲道记录
  GET  /api/church-health/sermons/me           我的讲道记录
  POST /api/church-health/sermons/form         讲道回应生成 Agent（可选落库）
  POST /api/church-health/gospel/assess        福音清晰度评估 Agent（落库）
  GET  /api/church-health/gospel/me            我的福音评估历史
  POST /api/church-health/repentance           保存悔改/恢复记录（含危机分流）
  GET  /api/church-health/repentance/me        我的悔改记录
  POST /api/church-health/discipleship         创建门训关系
  GET  /api/church-health/discipleship/me      我的门训关系
  POST /api/church-health/snapshots/compute    计算并保存九标志成长快照
  GET  /api/church-health/snapshots/me         我的最近一次快照 + 历史总分趋势
  GET  /api/church-health/dashboard/overview   实时九标志成长概览（不落库）
  GET  /api/church-health/care-signals         我的关怀信号（privacy-first）
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:  # pragma: no cover - import shim, mirrors other routers
    from backend import church_health_engine as che  # type: ignore
except Exception:  # pragma: no cover
    import church_health_engine as che  # type: ignore

router = APIRouter(prefix="/api/church-health", tags=["church-health"])
_state: Dict[str, Any] = {}


def init_church_health_router(*, get_db, release_db, get_session_user, to_shanghai_iso=None) -> None:
    _state.update({
        "get_db": get_db,
        "release_db": release_db,
        "get_session_user": get_session_user,
        "to_shanghai_iso": to_shanghai_iso,
    })


# ── helpers ──────────────────────────────────────────────────────────────────
def _require_user(request: Request) -> dict:
    getter = _state.get("get_session_user")
    user = getter(request) if getter else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _conn():
    conn = _state["get_db"]()
    che.ensure_tables(conn)
    return conn


def _release(conn) -> None:
    try:
        _state["release_db"](conn)
    except Exception:
        pass


def _iso(dt) -> Optional[str]:
    if dt is None:
        return None
    fn = _state.get("to_shanghai_iso")
    if fn:
        try:
            return fn(dt)
        except Exception:
            pass
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


def _j(v, default):
    """jsonb 列的安全读取：psycopg 多数返回已解析对象，兜底 json.loads。"""
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════════════════════
# Pydantic 请求体
# ═══════════════════════════════════════════════════════════════════════════
class MembershipBody(BaseModel):
    church_name: Optional[str] = Field(default=None, max_length=200)
    church_id: Optional[str] = Field(default=None, max_length=64)
    membership_status: str = Field(default="none", max_length=32)
    baptism_status: str = Field(default="unknown", max_length=32)
    joined_at: Optional[str] = Field(default=None, max_length=10)
    small_group_name: Optional[str] = Field(default=None, max_length=200)
    worship_attendance: bool = False
    small_group_participation: bool = False
    pastoral_connection: bool = False
    service_roles: List[Any] = Field(default_factory=list)
    one_another_notes: Optional[str] = Field(default=None, max_length=2000)
    consent_to_share_with_leader: bool = False
    consent_to_anonymous_aggregate: bool = True
    notes: Optional[str] = Field(default=None, max_length=2000)


class SermonBody(BaseModel):
    church_name: Optional[str] = Field(default=None, max_length=200)
    preacher_name: Optional[str] = Field(default=None, max_length=200)
    sermon_title: Optional[str] = Field(default=None, max_length=300)
    scripture_ref: str = Field(max_length=200)
    sermon_date: Optional[str] = Field(default=None, max_length=10)
    raw_notes: Optional[str] = Field(default="", max_length=8000)
    main_point: Optional[str] = Field(default=None, max_length=2000)
    gospel_connection: Optional[str] = Field(default=None, max_length=2000)
    repentance_prompt: Optional[str] = Field(default=None, max_length=2000)
    faith_prompt: Optional[str] = Field(default=None, max_length=2000)
    obedience_action: Optional[str] = Field(default=None, max_length=2000)
    community_action: Optional[str] = Field(default=None, max_length=2000)
    visibility: str = Field(default="private", max_length=20)


class SermonFormBody(BaseModel):
    scripture_ref: str = Field(max_length=200)
    sermon_title: Optional[str] = Field(default=None, max_length=300)
    raw_notes: str = Field(default="", max_length=8000)
    user_reflection: Optional[str] = Field(default="", max_length=4000)
    church_name: Optional[str] = Field(default=None, max_length=200)
    sermon_date: Optional[str] = Field(default=None, max_length=10)
    save: bool = False


class GospelAssessBody(BaseModel):
    source_type: str = Field(default="user_reflection", max_length=40)
    source_text: str = Field(max_length=8000)


class RepentanceBody(BaseModel):
    sin_pattern: str = Field(max_length=500)
    trigger_context: Optional[str] = Field(default=None, max_length=2000)
    confession_notes: Optional[str] = Field(default=None, max_length=4000)
    repentance_steps: List[Any] = Field(default_factory=list)
    accountability_plan: Optional[str] = Field(default=None, max_length=2000)
    repentance_status: str = Field(default="struggling", max_length=20)
    leader_visibility: str = Field(default="private", max_length=20)


class DiscipleshipBody(BaseModel):
    counterpart: Optional[str] = Field(default=None, max_length=200)
    relation_type: str = Field(default="peer", max_length=20)  # being_discipled/discipling/peer
    goals: List[Any] = Field(default_factory=list)
    meeting_rhythm: Optional[str] = Field(default=None, max_length=200)
    next_meeting_at: Optional[str] = Field(default=None, max_length=32)
    status: str = Field(default="active", max_length=20)


# ═══════════════════════════════════════════════════════════════════════════
# 元信息
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **che.meta()}


@router.get("/marks")
def list_marks() -> dict:
    return {"ok": True, "marks": che.meta()["marks"]}


# ═══════════════════════════════════════════════════════════════════════════
# 成员委身档案
# ═══════════════════════════════════════════════════════════════════════════
_MEMBERSHIP_COLS = (
    "church_name, church_id, membership_status, baptism_status, joined_at, small_group_name, "
    "worship_attendance, small_group_participation, pastoral_connection, service_roles, "
    "one_another_notes, consent_to_share_with_leader, consent_to_anonymous_aggregate, notes, updated_at"
)


def _membership_row_to_dict(row) -> Optional[dict]:
    if not row:
        return None
    return {
        "church_name": row[0], "church_id": row[1], "membership_status": row[2],
        "baptism_status": row[3], "joined_at": _iso(row[4]), "small_group_name": row[5],
        "worship_attendance": bool(row[6]), "small_group_participation": bool(row[7]),
        "pastoral_connection": bool(row[8]), "service_roles": _j(row[9], []),
        "one_another_notes": row[10], "consent_to_share_with_leader": bool(row[11]),
        "consent_to_anonymous_aggregate": bool(row[12]), "notes": row[13], "updated_at": _iso(row[14]),
    }


@router.get("/membership/me")
def get_my_membership(request: Request) -> dict:
    user = _require_user(request)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_MEMBERSHIP_COLS} FROM ch_membership WHERE email=%s", (user["email"],))
            row = cur.fetchone()
        conn.commit()
    finally:
        _release(conn)
    return {"ok": True, "membership": _membership_row_to_dict(row)}


@router.put("/membership")
def upsert_membership(body: MembershipBody, request: Request) -> dict:
    user = _require_user(request)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ch_membership
                    (email, church_name, church_id, membership_status, baptism_status, joined_at,
                     small_group_name, worship_attendance, small_group_participation, pastoral_connection,
                     service_roles, one_another_notes, consent_to_share_with_leader,
                     consent_to_anonymous_aggregate, notes, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
                ON CONFLICT (email) DO UPDATE SET
                    church_name=EXCLUDED.church_name,
                    church_id=EXCLUDED.church_id,
                    membership_status=EXCLUDED.membership_status,
                    baptism_status=EXCLUDED.baptism_status,
                    joined_at=EXCLUDED.joined_at,
                    small_group_name=EXCLUDED.small_group_name,
                    worship_attendance=EXCLUDED.worship_attendance,
                    small_group_participation=EXCLUDED.small_group_participation,
                    pastoral_connection=EXCLUDED.pastoral_connection,
                    service_roles=EXCLUDED.service_roles,
                    one_another_notes=EXCLUDED.one_another_notes,
                    consent_to_share_with_leader=EXCLUDED.consent_to_share_with_leader,
                    consent_to_anonymous_aggregate=EXCLUDED.consent_to_anonymous_aggregate,
                    notes=EXCLUDED.notes,
                    updated_at=now()
                """,
                (user["email"], body.church_name, body.church_id, body.membership_status,
                 body.baptism_status, (body.joined_at or None), body.small_group_name,
                 body.worship_attendance, body.small_group_participation, body.pastoral_connection,
                 json.dumps(body.service_roles), body.one_another_notes,
                 body.consent_to_share_with_leader, body.consent_to_anonymous_aggregate, body.notes),
            )
            cur.execute(f"SELECT {_MEMBERSHIP_COLS} FROM ch_membership WHERE email=%s", (user["email"],))
            row = cur.fetchone()
        conn.commit()
    finally:
        _release(conn)
    return {"ok": True, "membership": _membership_row_to_dict(row)}


# ═══════════════════════════════════════════════════════════════════════════
# 讲道记录 + 讲道回应 Agent
# ═══════════════════════════════════════════════════════════════════════════
def _insert_sermon(cur, email: str, b: Dict[str, Any]) -> int:
    cur.execute(
        """
        INSERT INTO ch_sermon_records
            (email, church_name, preacher_name, sermon_title, scripture_ref, sermon_date, raw_notes,
             main_point, gospel_connection, repentance_prompt, faith_prompt, obedience_action,
             community_action, visibility)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """,
        (email, b.get("church_name"), b.get("preacher_name"), b.get("sermon_title"),
         b.get("scripture_ref"), (b.get("sermon_date") or None), b.get("raw_notes"),
         b.get("main_point"), b.get("gospel_connection"), b.get("repentance_prompt"),
         b.get("faith_prompt"), b.get("obedience_action"), b.get("community_action"),
         b.get("visibility", "private")),
    )
    return int(cur.fetchone()[0])


@router.post("/sermons")
def create_sermon(body: SermonBody, request: Request) -> dict:
    user = _require_user(request)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            sid = _insert_sermon(cur, user["email"], body.model_dump())
        conn.commit()
    finally:
        _release(conn)
    return {"ok": True, "id": sid}


@router.get("/sermons/me")
def list_my_sermons(request: Request, limit: int = 30) -> dict:
    user = _require_user(request)
    limit = max(1, min(100, limit))
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, church_name, preacher_name, sermon_title, scripture_ref, sermon_date,
                          main_point, gospel_connection, repentance_prompt, faith_prompt,
                          obedience_action, community_action, visibility, created_at
                   FROM ch_sermon_records WHERE email=%s ORDER BY created_at DESC LIMIT %s""",
                (user["email"], limit),
            )
            rows = cur.fetchall()
        conn.commit()
    finally:
        _release(conn)
    items = [{
        "id": r[0], "church_name": r[1], "preacher_name": r[2], "sermon_title": r[3],
        "scripture_ref": r[4], "sermon_date": _iso(r[5]), "main_point": r[6],
        "gospel_connection": r[7], "repentance_prompt": r[8], "faith_prompt": r[9],
        "obedience_action": r[10], "community_action": r[11], "visibility": r[12],
        "created_at": _iso(r[13]),
    } for r in rows]
    return {"ok": True, "items": items}


@router.post("/sermons/form")
def form_sermon_response(body: SermonFormBody, request: Request) -> dict:
    user = _require_user(request)
    formation = che.run_sermon_formation(
        scripture_ref=body.scripture_ref, raw_notes=body.raw_notes or "",
        user_reflection=body.user_reflection or "", sermon_title=body.sermon_title or "",
        email=user["email"],
    )
    saved_id = None
    if body.save:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                saved_id = _insert_sermon(cur, user["email"], {
                    "church_name": body.church_name, "sermon_title": body.sermon_title,
                    "scripture_ref": body.scripture_ref, "sermon_date": body.sermon_date,
                    "raw_notes": body.raw_notes,
                    "main_point": formation.get("main_point"),
                    "gospel_connection": formation.get("gospel_connection"),
                    "repentance_prompt": formation.get("repentance_prompt"),
                    "faith_prompt": formation.get("faith_prompt"),
                    "obedience_action": formation.get("obedience_action"),
                    "community_action": formation.get("community_action"),
                    "visibility": "private",
                })
            conn.commit()
        finally:
            _release(conn)
    return {"ok": True, "formation": formation, "saved_id": saved_id}


# ═══════════════════════════════════════════════════════════════════════════
# 福音清晰度评估 Agent
# ═══════════════════════════════════════════════════════════════════════════
@router.post("/gospel/assess")
def assess_gospel(body: GospelAssessBody, request: Request) -> dict:
    user = _require_user(request)
    result = che.run_gospel_clarity(body.source_text, source_type=body.source_type, email=user["email"])
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ch_gospel_assessments
                     (email, source_type, source_text, god_score, sin_score, christ_score,
                      response_score, detected_distortions, gentle_reframe, next_teaching)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (user["email"], body.source_type, body.source_text[:8000],
                 int(result.get("god_score", 0)), int(result.get("sin_score", 0)),
                 int(result.get("christ_score", 0)), int(result.get("response_score", 0)),
                 json.dumps(result.get("detected_distortions", [])),
                 result.get("gentle_reframe"), result.get("next_teaching")),
            )
            aid = int(cur.fetchone()[0])
        conn.commit()
    finally:
        _release(conn)
    return {"ok": True, "id": aid, "assessment": result}


@router.get("/gospel/me")
def list_my_gospel(request: Request, limit: int = 20) -> dict:
    user = _require_user(request)
    limit = max(1, min(50, limit))
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, source_type, god_score, sin_score, christ_score, response_score,
                          detected_distortions, gentle_reframe, next_teaching, created_at
                   FROM ch_gospel_assessments WHERE email=%s ORDER BY created_at DESC LIMIT %s""",
                (user["email"], limit),
            )
            rows = cur.fetchall()
        conn.commit()
    finally:
        _release(conn)
    items = [{
        "id": r[0], "source_type": r[1], "god_score": r[2], "sin_score": r[3],
        "christ_score": r[4], "response_score": r[5], "detected_distortions": _j(r[6], []),
        "gentle_reframe": r[7], "next_teaching": r[8], "created_at": _iso(r[9]),
    } for r in rows]
    return {"ok": True, "items": items}


# ═══════════════════════════════════════════════════════════════════════════
# 悔改 / 恢复记录（含危机分流）
# ═══════════════════════════════════════════════════════════════════════════
@router.post("/repentance")
def create_repentance(body: RepentanceBody, request: Request) -> dict:
    user = _require_user(request)
    crisis = che.detect_crisis(body.sin_pattern, body.trigger_context, body.confession_notes)
    risk_level = "crisis" if crisis else "low"
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ch_repentance_patterns
                     (email, sin_pattern, trigger_context, confession_notes, repentance_steps,
                      accountability_plan, repentance_status, risk_level, leader_visibility)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (user["email"], body.sin_pattern, body.trigger_context, body.confession_notes,
                 json.dumps(body.repentance_steps), body.accountability_plan,
                 body.repentance_status, risk_level, body.leader_visibility),
            )
            rid = int(cur.fetchone()[0])
        conn.commit()
    finally:
        _release(conn)
    resp = {
        "ok": True, "id": rid, "risk_level": risk_level,
        "guidance": {
            "type": "restoration",
            "message": "记录已私密保存（默认仅你可见）。恢复不是独自面对——考虑与可信的门训伙伴、"
                       "小组长或牧者同行。AI 不定罪、不赦罪、不执行纪律。",
        },
    }
    if crisis:
        resp["crisis"] = True
        resp["crisis_notice"] = ("你所描述的情况涉及安全风险。请优先寻求真人帮助：立即联系信任的人、"
                                 "牧者/长老，或当地紧急/心理危机热线。属灵星球不能替代专业与真人的即时帮助。")
    return resp


@router.get("/repentance/me")
def list_my_repentance(request: Request, limit: int = 30) -> dict:
    user = _require_user(request)
    limit = max(1, min(100, limit))
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, sin_pattern, trigger_context, confession_notes, repentance_steps,
                          accountability_plan, repentance_status, risk_level, created_at
                   FROM ch_repentance_patterns WHERE email=%s ORDER BY created_at DESC LIMIT %s""",
                (user["email"], limit),
            )
            rows = cur.fetchall()
        conn.commit()
    finally:
        _release(conn)
    items = [{
        "id": r[0], "sin_pattern": r[1], "trigger_context": r[2], "confession_notes": r[3],
        "repentance_steps": _j(r[4], []), "accountability_plan": r[5], "repentance_status": r[6],
        "risk_level": r[7], "created_at": _iso(r[8]),
    } for r in rows]
    return {"ok": True, "items": items}


# ═══════════════════════════════════════════════════════════════════════════
# 门训关系
# ═══════════════════════════════════════════════════════════════════════════
@router.post("/discipleship")
def create_discipleship(body: DiscipleshipBody, request: Request) -> dict:
    user = _require_user(request)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ch_discipleship
                     (email, counterpart, relation_type, goals, meeting_rhythm, next_meeting_at, status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (user["email"], body.counterpart, body.relation_type, json.dumps(body.goals),
                 body.meeting_rhythm, (body.next_meeting_at or None), body.status),
            )
            did = int(cur.fetchone()[0])
        conn.commit()
    finally:
        _release(conn)
    return {"ok": True, "id": did}


@router.get("/discipleship/me")
def list_my_discipleship(request: Request) -> dict:
    user = _require_user(request)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, counterpart, relation_type, goals, meeting_rhythm, last_meeting_at,
                          next_meeting_at, status, created_at
                   FROM ch_discipleship WHERE email=%s ORDER BY created_at DESC""",
                (user["email"],),
            )
            rows = cur.fetchall()
        conn.commit()
    finally:
        _release(conn)
    items = [{
        "id": r[0], "counterpart": r[1], "relation_type": r[2], "goals": _j(r[3], []),
        "meeting_rhythm": r[4], "last_meeting_at": _iso(r[5]), "next_meeting_at": _iso(r[6]),
        "status": r[7], "created_at": _iso(r[8]),
    } for r in rows]
    return {"ok": True, "items": items}


# ═══════════════════════════════════════════════════════════════════════════
# 证据聚合 → 九标志成长概览
# ═══════════════════════════════════════════════════════════════════════════
def _gather_evidence(cur, email: str) -> Dict[str, Dict[str, Any]]:
    ev: Dict[str, Dict[str, Any]] = {code: {} for code in che.MARK_CODES}

    # membership
    cur.execute(
        """SELECT membership_status, worship_attendance, small_group_participation,
                  pastoral_connection, service_roles FROM ch_membership WHERE email=%s""",
        (email,),
    )
    m = cur.fetchone()
    if m:
        ev["membership"] = {
            "membership_status": m[0], "worship_attendance": bool(m[1]),
            "small_group_participation": bool(m[2]), "pastoral_connection": bool(m[3]),
            "service_roles": _j(m[4], []),
        }
        # leadership（对成员而言：是否在健康带领之下被牧养）
        ev["leadership"] = {
            "care_followup": 100 if m[3] else 0,
            "word_centered_guidance": 0,  # 由讲道记录补充
        }

    # gospel_clarity（最近一次）
    cur.execute(
        """SELECT god_score, sin_score, christ_score, response_score, detected_distortions
           FROM ch_gospel_assessments WHERE email=%s ORDER BY created_at DESC LIMIT 1""",
        (email,),
    )
    g = cur.fetchone()
    if g:
        ev["gospel_clarity"] = {
            "god_score": g[0], "sin_score": g[1], "christ_score": g[2],
            "response_score": g[3], "detected_distortions": _j(g[4], []),
        }
        # conversion 借用福音理解作为弱信号
        ev["conversion"] = {
            "faith_understanding": g[3], "repentance_understanding": g[1],
            "testimony_clarity": g[2], "church_life_readiness": 0,
        }

    # expository_preaching（最近一次 + 计数）
    cur.execute("SELECT COUNT(*) FROM ch_sermon_records WHERE email=%s", (email,))
    sermons_count = int((cur.fetchone() or [0])[0])
    cur.execute(
        """SELECT raw_notes, main_point, gospel_connection, obedience_action
           FROM ch_sermon_records WHERE email=%s ORDER BY created_at DESC LIMIT 1""",
        (email,),
    )
    s = cur.fetchone()
    if s or sermons_count:
        ev["expository_preaching"] = {
            "has_notes": bool(s[0]) if s else False,
            "has_main_point": bool(s[1]) if s else False,
            "has_gospel_connection": bool(s[2]) if s else False,
            "has_obedience_action": bool(s[3]) if s else False,
            "sermons_recorded": sermons_count,
        }
        ev.setdefault("leadership", {})["word_centered_guidance"] = 100 if sermons_count else 0

    # discipline（最近一次悔改记录）
    cur.execute(
        """SELECT confession_notes, repentance_steps, accountability_plan, repentance_status, risk_level
           FROM ch_repentance_patterns WHERE email=%s ORDER BY created_at DESC LIMIT 1""",
        (email,),
    )
    d = cur.fetchone()
    if d:
        steps = _j(d[1], [])
        ev["discipline"] = {
            "confession_notes": bool(d[0]),
            "repentance_steps_count": len(steps) if isinstance(steps, list) else 0,
            "accountability_plan": bool(d[2]),
            "repentance_status": d[3],
            "risk_level": d[4],
        }

    # discipleship
    cur.execute(
        "SELECT relation_type, goals, status FROM ch_discipleship WHERE email=%s",
        (email,),
    )
    rels = cur.fetchall()
    if rels:
        being = any(r[0] == "being_discipled" for r in rels)
        discipling = any(r[0] == "discipling" for r in rels)
        has_goals = any(_j(r[1], []) for r in rels)
        active = any(r[2] == "active" for r in rels)
        ev["discipleship"] = {
            "being_discipled": being, "discipling_others": discipling,
            "weekly_growth_review": has_goals, "service_and_imitation": active,
        }
    return ev


def _compute_overview(email: str) -> Dict[str, Any]:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            evidence = _gather_evidence(cur, email)
        conn.commit()
    finally:
        _release(conn)
    return che.compute_overview(evidence)


@router.get("/dashboard/overview")
def dashboard_overview(request: Request) -> dict:
    user = _require_user(request)
    overview = _compute_overview(user["email"])
    return {"ok": True, "overview": overview}


@router.post("/snapshots/compute")
def compute_snapshot(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    overview = _compute_overview(email)
    batch_id = uuid.uuid4().hex
    conn = _conn()
    try:
        with conn.cursor() as cur:
            for mk in overview["marks"]:
                cur.execute(
                    """INSERT INTO ch_mark_snapshots
                         (email, batch_id, mark_code, score, band, evidence, risks,
                          recommendations, overall_score)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (email, batch_id, mk["mark_code"], mk["score"], mk["band"],
                     json.dumps(mk["evidence"]), json.dumps(mk["risks"]),
                     json.dumps(mk["recommendations"]), overview["overall_score"]),
                )
        conn.commit()
    finally:
        _release(conn)
    return {"ok": True, "batch_id": batch_id, "overview": overview}


@router.get("/snapshots/me")
def my_snapshots(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _conn()
    try:
        with conn.cursor() as cur:
            # 最近一批
            cur.execute(
                "SELECT batch_id FROM ch_mark_snapshots WHERE email=%s ORDER BY created_at DESC LIMIT 1",
                (email,),
            )
            row = cur.fetchone()
            latest = None
            if row:
                bid = row[0]
                cur.execute(
                    """SELECT mark_code, score, band, evidence, risks, recommendations,
                              overall_score, created_at
                       FROM ch_mark_snapshots WHERE email=%s AND batch_id=%s
                       ORDER BY created_at""",
                    (email, bid),
                )
                mrows = cur.fetchall()
                marks = [{
                    "mark_code": r[0], "score": r[1], "band": r[2], "evidence": _j(r[3], {}),
                    "risks": _j(r[4], []), "recommendations": _j(r[5], []),
                } for r in mrows]
                latest = {
                    "batch_id": bid,
                    "overall_score": mrows[0][6] if mrows else 0,
                    "created_at": _iso(mrows[0][7]) if mrows else None,
                    "marks": marks,
                }
            # 历史总分趋势（每批一个点）
            cur.execute(
                """SELECT batch_id, MAX(overall_score) AS overall, MAX(created_at) AS at
                   FROM ch_mark_snapshots WHERE email=%s
                   GROUP BY batch_id ORDER BY at DESC LIMIT 20""",
                (email,),
            )
            trend = [{"batch_id": r[0], "overall_score": r[1], "created_at": _iso(r[2])}
                     for r in cur.fetchall()]
        conn.commit()
    finally:
        _release(conn)
    return {"ok": True, "latest": latest, "trend": list(reversed(trend))}


# ═══════════════════════════════════════════════════════════════════════════
# 关怀信号（privacy-first：本人视角；领袖聚合交由既有 /api/care 系统）
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/care-signals")
def my_care_signals(request: Request) -> dict:
    """
    返回「本人」视角的关怀信号：由当前九标志概览的风险/最弱标志实时派生，
    外加任何已登记的 ch_care_signals。不暴露他人隐私；领袖端的群体聚合请走 /api/care。
    """
    user = _require_user(request)
    email = user["email"]
    overview = _compute_overview(email)

    signals: List[Dict[str, Any]] = []
    for mk in overview["marks"]:
        for risk in mk.get("risks", []):
            signals.append({
                "source": "mark_risk", "mark_code": mk["mark_code"],
                "severity": risk.get("severity", "medium"),
                "type": risk.get("type"), "summary": risk.get("description", ""),
            })
    # 最弱两个标志的「下一步」作为温和提醒
    weak_recs: List[Dict[str, Any]] = []
    weak_set = set(overview.get("weakest", []))
    for mk in overview["marks"]:
        if mk["mark_code"] in weak_set and mk.get("recommendations"):
            rec = mk["recommendations"][0]
            weak_recs.append({"mark_code": mk["mark_code"], "name_zh": mk["name_zh"],
                              "title": rec.get("title"), "description": rec.get("description")})

    stored: List[Dict[str, Any]] = []
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, signal_type, severity, summary, recommended_action, created_at, resolved_at
                   FROM ch_care_signals WHERE email=%s ORDER BY created_at DESC LIMIT 30""",
                (email,),
            )
            stored = [{
                "id": r[0], "signal_type": r[1], "severity": r[2], "summary": r[3],
                "recommended_action": r[4], "created_at": _iso(r[5]), "resolved_at": _iso(r[6]),
            } for r in cur.fetchall()]
        conn.commit()
    finally:
        _release(conn)

    return {
        "ok": True,
        "overall_band": overview["band"],
        "live_signals": signals,
        "next_steps": weak_recs,
        "stored_signals": stored,
        "boundary": "关怀信号以帮助与恢复为目的，不作控告或纪律执行；如涉及安全风险请优先真人求助。",
    }
