"""
Discipleship Pathway router — 门徒成长路径 (/api/discipleship)

  GET  /api/discipleship/stages           阶段库
  POST /api/discipleship/assessments      门徒阶段自评（推断当前阶段）
  POST /api/discipleship/recommend        按阶段推荐路径与步骤
  POST /api/discipleship/paths            创建路径
  GET  /api/discipleship/paths/active     当前路径(含步骤)
  POST /api/discipleship/paths/{id}/steps 添加步骤
  PATCH/api/discipleship/steps/{id}       更新步骤状态
  POST /api/discipleship/paths/{id}/review 路径回顾

阶段是成长辅助,不是身份/高低;成长慢不羞辱;有教会创伤先医治再推进教会参与。email 标识用户。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/discipleship", tags=["discipleship"])

_state: Dict[str, Any] = {}

_ORDER = ["seeker", "new_believer", "rooted_disciple", "practicing_disciple", "serving_member",
          "mature_disciple", "leader_in_training", "disciple_maker", "missionary_sent", "elder_like_maturity"]


def init_discipleship_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _jl(v):
    import json
    if v is None: return []
    if isinstance(v, (list, dict)): return v
    try: return json.loads(v)
    except Exception: return []


def _infer_stage(a: dict) -> str:
    """从自评分数粗略推断阶段。"""
    conn = a.get("church_connection_level", "none")
    avg = (a.get("scripture_practice_level", 0) + a.get("prayer_practice_level", 0)
           + a.get("community_level", 0) + a.get("service_level", 0)) / 4.0
    serve = a.get("service_level", 0)
    if conn in ("none", "visiting") and avg <= 2:
        return "new_believer" if avg >= 1 else "seeker"
    if avg <= 4:
        return "rooted_disciple"
    if serve >= 5 and avg >= 6:
        return "serving_member"
    if avg <= 6:
        return "practicing_disciple"
    if avg >= 8 and serve >= 7:
        return "mature_disciple"
    return "serving_member"


@router.get("/stages")
def list_stages(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT stage_key, display_name, description, core_marks, recommended_practices, next_stage_key FROM discipleship_stages ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "stages": [
        {"stage_key": r[0], "display_name": r[1], "description": r[2] or "", "core_marks": _jl(r[3]),
         "recommended_practices": _jl(r[4]), "next_stage_key": r[5] or ""} for r in rows
    ]}


class AssessmentCreate(BaseModel):
    self_report_stage_key: str = Field(default="", max_length=30)
    church_connection_level: str = Field(default="none", max_length=20)
    scripture_practice_level: int = Field(default=0, ge=0, le=10)
    prayer_practice_level: int = Field(default=0, ge=0, le=10)
    community_level: int = Field(default=0, ge=0, le=10)
    service_level: int = Field(default=0, ge=0, le=10)
    notes: str = Field(default="", max_length=2000)


@router.post("/assessments")
def create_assessment(request: Request, body: AssessmentCreate) -> dict:
    user = _require_user(request); email = user["email"]
    data = body.model_dump()
    stage = _infer_stage(data)
    aid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO discipleship_assessments (id, email, assessed_stage_key, self_report_stage_key, "
                "church_connection_level, scripture_practice_level, prayer_practice_level, community_level, service_level, notes) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (aid, email, stage, body.self_report_stage_key, body.church_connection_level,
                 body.scripture_practice_level, body.prayer_practice_level, body.community_level, body.service_level, body.notes),
            )
            conn.commit()
            cur.execute("SELECT display_name, next_stage_key FROM discipleship_stages WHERE stage_key=%s", (stage,))
            sr = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "assessment_id": aid, "assessed_stage": stage,
            "assessed_stage_name": sr[0] if sr else stage, "suggested_target_stage": (sr[1] if sr else ""),
            "note": "阶段只是帮助你看清下一步,不是评判你的属灵价值。"}


def _steps_for(stage: str) -> List[dict]:
    by = {
        "seeker": [("读马可福音或约翰福音", "scripture", "scripture_formation"), ("找一个安全的教会或小组连接", "community", "discipleship_community")],
        "new_believer": [("受洗预备对话", "baptism", "church_integration"), ("学习祷告基础(祷告规则)", "prayer", "prayer_communion"), ("连接一位导师", "mentoring", "mentor")],
        "rooted_disciple": [("完成基要教义入门", "doctrine", "bible_doctrine"), ("建立祷告规则", "prayer", "prayer_communion"), ("探索教会成员", "community", "church_integration")],
        "practicing_disciple": [("完成 30 天生活规则", "habit", "holy_habit"), ("加入或建立问责小组", "community", "accountability_group"), ("做一次德性塑造", "virtue", "virtue_vice")],
        "serving_member": [("完成恩赐评估", "service", "gift_calling"), ("尝试一个低风险服事", "service", "ministry_match"), ("设定安息界限", "rest", "holy_habit")],
        "mature_disciple": [("接受导师训练", "mentoring", "mentor"), ("建立门训节奏", "leadership", "discipleship_community")],
    }
    items = by.get(stage, [("与导师一起定下下一步", "mentoring", "mentor")])
    return [{"step_title": t, "step_type": ty, "related_module": m} for (t, ty, m) in items]


@router.post("/recommend")
def recommend(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT assessed_stage_key FROM discipleship_assessments WHERE email=%s ORDER BY assessment_date DESC LIMIT 1", (user["email"],))
            r = cur.fetchone()
            stage = r[0] if r else "rooted_disciple"
            cur.execute("SELECT next_stage_key FROM discipleship_stages WHERE stage_key=%s", (stage,))
            nr = cur.fetchone()
            target = nr[0] if nr and nr[0] else stage
    finally:
        _state["release_db"](conn)
    return {"ok": True, "current_stage": stage, "target_stage": target, "duration_days": 90,
            "recommended_steps": _steps_for(stage)}


class PathCreate(BaseModel):
    current_stage_key: str = Field(default="", max_length=30)
    target_stage_key: str = Field(default="", max_length=30)
    duration_days: int = Field(default=90, ge=7, le=365)
    auto_steps: bool = Field(default=True)


@router.post("/paths")
def create_path(request: Request, body: PathCreate) -> dict:
    user = _require_user(request); email = user["email"]
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE user_discipleship_paths SET status='archived' WHERE email=%s AND status='active'", (email,))
            cur.execute("INSERT INTO user_discipleship_paths (id, email, current_stage_key, target_stage_key, duration_days) "
                        "VALUES (%s,%s,%s,%s,%s)", (pid, email, body.current_stage_key, body.target_stage_key, body.duration_days))
            if body.auto_steps and body.current_stage_key:
                for i, st in enumerate(_steps_for(body.current_stage_key)):
                    cur.execute("INSERT INTO discipleship_path_steps (id, path_id, email, step_title, step_type, related_module, sort_order) "
                                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                                (uuid.uuid4().hex, pid, email, st["step_title"], st["step_type"], st["related_module"], i))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "path_id": pid}


@router.get("/paths/active")
def active_path(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, current_stage_key, target_stage_key, duration_days, start_date FROM user_discipleship_paths "
                        "WHERE email=%s AND status='active' ORDER BY created_at DESC LIMIT 1", (user["email"],))
            p = cur.fetchone()
            steps = []
            if p:
                cur.execute("SELECT id, step_title, step_description, step_type, related_module, status FROM discipleship_path_steps "
                            "WHERE path_id=%s ORDER BY sort_order", (p[0],))
                steps = [{"id": s[0], "step_title": s[1], "step_description": s[2] or "", "step_type": s[3],
                          "related_module": s[4] or "", "status": s[5]} for s in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    if not p:
        return {"ok": True, "path": None}
    return {"ok": True, "path": {"id": p[0], "title": p[1], "current_stage_key": p[2], "target_stage_key": p[3],
            "duration_days": p[4], "start_date": str(p[5]), "steps": steps}}


class StepCreate(BaseModel):
    step_title: str = Field(..., max_length=200)
    step_description: str = Field(default="", max_length=2000)
    step_type: str = Field(default="custom", max_length=20)
    related_module: str = Field(default="", max_length=40)


@router.post("/paths/{pid}/steps")
def add_step(pid: str, request: Request, body: StepCreate) -> dict:
    user = _require_user(request)
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM user_discipleship_paths WHERE id=%s AND email=%s", (pid, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="path not found")
            cur.execute("SELECT COALESCE(MAX(sort_order),-1)+1 FROM discipleship_path_steps WHERE path_id=%s", (pid,))
            order = cur.fetchone()[0]
            cur.execute("INSERT INTO discipleship_path_steps (id, path_id, email, step_title, step_description, step_type, related_module, sort_order) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (sid, pid, user["email"], body.step_title, body.step_description, body.step_type, body.related_module, order))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "step_id": sid}


class StepUpdate(BaseModel):
    status: str = Field(..., max_length=12)


@router.patch("/steps/{sid}")
def update_step(sid: str, request: Request, body: StepUpdate) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE discipleship_path_steps SET status=%s, updated_at=NOW() WHERE id=%s AND email=%s",
                        (body.status, sid, user["email"]))
            conn.commit(); n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"update failed: {exc}")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="step not found")
    return {"ok": True}


@router.post("/paths/{pid}/review")
def review(pid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM user_discipleship_paths WHERE id=%s AND email=%s", (pid, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="path not found")
            cur.execute("SELECT COUNT(*) FILTER (WHERE status='completed'), COUNT(*) FROM discipleship_path_steps WHERE path_id=%s", (pid,))
            done, total = cur.fetchone()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    insights = []
    if total and done >= total:
        insights.append("你已完成这条路径的全部步骤——为神在你身上的工作感恩,可以和导师一起看下一阶段。")
    elif done:
        insights.append(f"已完成 {done}/{total} 步,稳步前行。成长是恩典里的忠心,不是赶进度。")
    else:
        insights.append("还没开始也没关系,挑一个最小的步骤开始即可。")
    return {"ok": True, "summary": {"completed": done or 0, "total": total or 0}, "insights": insights}
