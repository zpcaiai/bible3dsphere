"""
Disciple router — 门徒塑造引擎 (/api/disciple)

  GET  /api/disciple/meta       状态机 / 维度 / 偶像 / 品格 / 11 引擎清单
  GET  /api/disciple/profile    当前用户的属灵画像（数字孪生 + CI + 状态）
  POST /api/disciple/assess     提交反思 → 跑引擎 → 落库 + 更新画像 → 返回完整病历
  GET  /api/disciple/history    评估历史
  POST /api/disciple/mentor     AI 导师单轮问答
  GET  /api/disciple/network    门徒关系网络 + DMI
  POST /api/disciple/network    新增门徒关系
  POST /api/disciple/network/{id}/end   结束一段关系

闭环：每日反思 → 识别信念/偶像/顺服/呼召 → Faith-Hope-Love 评分 → 更新数字孪生
     → 生成今日顺服行动 → (历史聚合) → 状态迁移建议 → 门徒培养 / 倍增路径。
用户以 email 标识。AI 失败时全程有确定性兜底。
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import disciple_engine as engine
except Exception:  # pragma: no cover
    import disciple_engine as engine  # type: ignore

try:
    from backend import disciple_integration as di
except Exception:  # pragma: no cover
    import disciple_integration as di  # type: ignore

try:
    from backend import disciple_graph as dg
except Exception:  # pragma: no cover
    import disciple_graph as dg  # type: ignore

try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/disciple", tags=["disciple"])
_state: Dict[str, Any] = {}


def init_disciple_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


# ─────────────────────────────────────────────────────────────────────────────
# 网络指标：从 disciple_relationships 计算 breadth / 二代 / 深度
# ─────────────────────────────────────────────────────────────────────────────

def _network_metrics(cur, email: str) -> Dict[str, Any]:
    cur.execute(
        "SELECT disciple_email, disciple_name, relationship_type, status, started_at "
        "FROM disciple_relationships WHERE mentor_email=%s AND status='ACTIVE'",
        (email,),
    )
    rows = cur.fetchall()
    breadth = len(rows)
    mentors = 0
    cur.execute(
        "SELECT COUNT(*) FROM disciple_relationships "
        "WHERE disciple_email=%s AND status='ACTIVE'",
        (email,),
    )
    mentors = cur.fetchone()[0]

    # 二代：我的门徒(注册用户)是否也在带人
    disciple_emails = [r[0] for r in rows if r[0]]
    second_gen = 0
    if disciple_emails:
        cur.execute(
            "SELECT COUNT(DISTINCT mentor_email) FROM disciple_relationships "
            "WHERE mentor_email IN %s AND status='ACTIVE'",
            (tuple(disciple_emails),),
        )
        second_gen = cur.fetchone()[0]

    # 复制深度（最多探 5 层）
    depth = 1 if breadth > 0 else 0
    frontier = list(disciple_emails)
    seen = set([email]) | set(frontier)
    for _ in range(4):
        if not frontier:
            break
        cur.execute(
            "SELECT DISTINCT disciple_email FROM disciple_relationships "
            "WHERE mentor_email IN %s AND status='ACTIVE' AND disciple_email <> ''",
            (tuple(frontier),),
        )
        nxt = [r[0] for r in cur.fetchall() if r[0] and r[0] not in seen]
        if not nxt:
            break
        depth += 1
        seen.update(nxt)
        frontier = nxt

    reproduction = (second_gen / breadth) if breadth else 0.0
    # duration：最早一段关系至今的月数
    duration_months = 0
    if rows:
        try:
            from datetime import date
            earliest = min(r[4] for r in rows if r[4])
            duration_months = max(0, (date.today().year - earliest.year) * 12
                                  + (date.today().month - earliest.month))
        except Exception:
            duration_months = 0

    return {
        "breadth": breadth,
        "mentors": mentors,
        "second_generation": second_gen,
        "depth": depth,
        "reproduction_rate": reproduction,
        "duration_months": duration_months,
        "relationships": [
            {"disciple_email": r[0], "disciple_name": r[1],
             "relationship_type": r[2], "status": r[3],
             "started_at": _state["to_shanghai_iso"](r[4]) if r[4] else None}
            for r in rows
        ],
    }


def _load_twin(cur, email: str) -> Dict[str, Any]:
    cur.execute("SELECT twin FROM disciple_profiles WHERE email=%s", (email,))
    row = cur.fetchone()
    if row and row[0]:
        return row[0] if isinstance(row[0], dict) else {}
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta(), "pipeline": dg.graph_topology()}


_DIM_TO_COL = {
    "faith": "faith_score", "hope": "hope_score", "love": "love_score",
    "truth": "truth_score", "prayer": "prayer_score", "obedience": "obedience_score",
    "character": "character_score", "calling": "calling_score", "service": "service_score",
    "mission": "mission_score", "multiplication": "multiplication_score",
}


def _profile_row_to_dict(r, to_iso) -> dict:
    (email, state, nxt, ci, fa, ho, lo, tr, pr, ob, ch, ca, se, mi, mu,
     top_idol, edge, twin, count, updated) = r
    dims = {"faith": float(fa), "hope": float(ho), "love": float(lo), "truth": float(tr),
            "prayer": float(pr), "obedience": float(ob), "character": float(ch),
            "calling": float(ca), "service": float(se), "mission": float(mi),
            "multiplication": float(mu)}
    return {
        "spiritual_state": state, "next_state": nxt,
        "christlikeness_index": float(ci), "dimensions": dims,
        "top_idol": top_idol or None, "growth_edge": edge,
        "assessment_count": count,
        "twin": twin if isinstance(twin, dict) else {},
        "updated_at": to_iso(updated) if updated else None,
    }


@router.get("/profile")
def get_profile(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, spiritual_state, next_state, christlikeness_index, "
                "faith_score, hope_score, love_score, truth_score, prayer_score, "
                "obedience_score, character_score, calling_score, service_score, "
                "mission_score, multiplication_score, top_idol, growth_edge, twin, "
                "assessment_count, updated_at FROM disciple_profiles WHERE email=%s",
                (email,),
            )
            row = cur.fetchone()
            net = _network_metrics(cur, email)
            try:
                provenance = di.gather_unified_twin(cur, email, user_id=user.get("id")).get("provenance", [])
            except Exception:
                provenance = []
    finally:
        _state["release_db"](conn)

    if not row:
        prof = engine.empty_profile()
        prof["assessment_count"] = 0
    else:
        prof = _profile_row_to_dict(row, to_iso)
    prof["network"] = net
    prof["dmi"] = engine.compute_dmi(net)
    prof["provenance"] = provenance
    try:
        prof["graph"] = di.graph_insights(email)
    except Exception:
        prof["graph"] = {"enabled": False, "insights": []}
    return {"ok": True, "profile": prof}


@router.get("/review/{kind}")
def review(request: Request, kind: str) -> dict:
    """周/月复盘：聚合最近 7/30 天评估 + 可选 AI 牧养总结。"""
    user = _require_user(request)
    if kind not in ("weekly", "monthly"):
        raise HTTPException(status_code=400, detail="kind must be weekly|monthly")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            res = di.make_review(cur, user["email"], kind, settings=_settings, use_ai=True)
    finally:
        _state["release_db"](conn)
    return res


@router.get("/graph")
def graph(request: Request) -> dict:
    """Neo4j 属灵图谱洞察（偶像路径 / 复制链 / 影响人数）。未配置则 enabled=False。"""
    user = _require_user(request)
    try:
        return {"ok": True, **di.graph_insights(user["email"])}
    except Exception:
        return {"ok": True, "enabled": False, "insights": []}


@router.get("/milestones")
def milestones(request: Request) -> dict:
    """属灵里程碑/提醒时间线（事件消费者 agent_runs 的产物）。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            items = di.get_milestones(cur, user["email"])
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(items), "items": items}


@router.post("/cron/notify")
def cron_notify(request: Request) -> dict:
    """定时任务入口：把未通知的 nudge/里程碑经 Web Push 推出。需 X-Cron-Secret。
    （/api/push/run-due 已自动捎带；此端点供单独触发/补发。）"""
    secret = getattr(_settings, "push_cron_secret", "") if _settings else ""
    if not secret or request.headers.get("X-Cron-Secret", "") != secret:
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        try:
            from routers.push import _send_one, _configured
        except Exception:
            from backend.routers.push import _send_one, _configured  # type: ignore
    except Exception:
        return {"ok": True, "configured": False, "sent": 0}
    if not _configured():
        return {"ok": True, "configured": False, "sent": 0}
    res = di.notify_pending_push(_state["get_db"], _state["release_db"], _send_one)
    return {"ok": True, "configured": True, **res}


@router.post("/cron/worker")
def cron_worker(request: Request) -> dict:
    """定时任务入口：跑一圈独立 worker（消费全部未处理事件 + 推送）。需 X-Cron-Secret。
    供没有常驻进程的部署用 cron 周期触发；与常驻 worker 二选一即可。"""
    secret = getattr(_settings, "push_cron_secret", "") if _settings else ""
    if not secret or request.headers.get("X-Cron-Secret", "") != secret:
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        try:
            from disciple_worker import run_once
        except Exception:
            from backend.disciple_worker import run_once  # type: ignore
        stats = run_once(_state["get_db"], _state["release_db"])
        return {"ok": True, **stats}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class AssessBody(BaseModel):
    journal: str = Field(default="", max_length=6000)
    scripture: str = Field(default="", max_length=1000)
    prayer: str = Field(default="", max_length=3000)
    event: str = Field(default="", max_length=3000)
    feeling: str = Field(default="", max_length=2000)
    want: str = Field(default="", max_length=2000)
    fear: str = Field(default="", max_length=2000)
    use_ai: bool = True


@router.post("/assess")
def assess(request: Request, body: AssessBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    inputs = body.model_dump()

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            twin = _load_twin(cur, email)
            net = _network_metrics(cur, email)
            cur.execute("SELECT spiritual_state FROM disciple_profiles WHERE email=%s", (email,))
            _prow = cur.fetchone()
            prev_state = _prow[0] if _prow else None
            # 形式化 DAG 编排：归一化→取记忆(统一孪生)→评估→融合偶像/品格→状态迁移→合成
            result, _trace = dg.run_formation(
                cur, email, user_id=user.get("id"), inputs=inputs,
                twin=twin, network=net, settings=_settings, use_ai=body.use_ai)
            result["pipeline_trace"] = _trace

            dims = result["dimensions"]
            # upsert profile + 把最新快照写进 twin
            new_twin = {"dims": dims, "idol_scores": result["idol_scores"],
                        "character_scores": result["character_scores"],
                        "top_idol": result.get("top_idol"),
                        "growth_edge": result["growth_edge"]}
            cols = {_DIM_TO_COL[k]: dims[k] for k in dims}
            cur.execute(
                """
                INSERT INTO disciple_profiles
                    (email, spiritual_state, next_state, christlikeness_index,
                     faith_score, hope_score, love_score, truth_score, prayer_score,
                     obedience_score, character_score, calling_score, service_score,
                     mission_score, multiplication_score, top_idol, growth_edge, twin,
                     assessment_count, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,NOW())
                ON CONFLICT (email) DO UPDATE SET
                    spiritual_state=EXCLUDED.spiritual_state,
                    next_state=EXCLUDED.next_state,
                    christlikeness_index=EXCLUDED.christlikeness_index,
                    faith_score=EXCLUDED.faith_score, hope_score=EXCLUDED.hope_score,
                    love_score=EXCLUDED.love_score, truth_score=EXCLUDED.truth_score,
                    prayer_score=EXCLUDED.prayer_score, obedience_score=EXCLUDED.obedience_score,
                    character_score=EXCLUDED.character_score, calling_score=EXCLUDED.calling_score,
                    service_score=EXCLUDED.service_score, mission_score=EXCLUDED.mission_score,
                    multiplication_score=EXCLUDED.multiplication_score,
                    top_idol=EXCLUDED.top_idol, growth_edge=EXCLUDED.growth_edge,
                    twin=EXCLUDED.twin,
                    assessment_count=disciple_profiles.assessment_count+1,
                    updated_at=NOW()
                """,
                (email, result["spiritual_state"], result.get("next_state") or "",
                 result["christlikeness_index"],
                 cols["faith_score"], cols["hope_score"], cols["love_score"],
                 cols["truth_score"], cols["prayer_score"], cols["obedience_score"],
                 cols["character_score"], cols["calling_score"], cols["service_score"],
                 cols["mission_score"], cols["multiplication_score"],
                 result.get("top_idol") or "", result["growth_edge"], _Json(new_twin)),
            )
            cur.execute(
                "INSERT INTO disciple_assessments "
                "(email, journal, scripture, prayer, spiritual_state, "
                " christlikeness_index, growth_edge, top_idol, next_step, source, report) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (email, body.journal.strip()[:6000], body.scripture.strip()[:1000],
                 body.prayer.strip()[:3000], result["spiritual_state"],
                 result["christlikeness_index"], result["growth_edge"],
                 result.get("top_idol") or "", result.get("next_step", ""),
                 result.get("source", "heuristic"), _Json(result)),
            )
            # 领域事件流
            di.log_event(cur, "disciple_assessment", email, "ReflectionAssessed",
                         {"state": result["spiritual_state"],
                          "ci": result["christlikeness_index"],
                          "top_idol": result.get("top_idol"),
                          "source": result.get("source")})
            if prev_state and prev_state != result["spiritual_state"]:
                di.log_event(cur, "disciple_profile", email, "SpiritualStateChanged",
                             {"from": prev_state, "to": result["spiritual_state"]})
            if result.get("top_idol"):
                di.log_event(cur, "disciple_profile", email, "IdolDetected",
                             {"idol": result["top_idol"], "risk": result.get("risk_level")})
            # 事件消费者：跑规则 Agent → agent_runs，产出里程碑/提醒
            try:
                result["reactions"] = di.process_user_events(cur, email)
            except Exception:
                result["reactions"] = []
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="assess failed")
    finally:
        _state["release_db"](conn)

    # 回流 formation（看见偶像/顺服 → 轻推塑造倾向）
    try:
        from formation_bridge import record_formation
        pats = ["growth"]
        if result.get("top_idol"):
            pats.append("fear")
        record_formation(user.get("id"), pats, loop_broken=True,
                         reflection_active=True, emotional_intensity=4.0,
                         decision_category="disciple")
    except Exception:
        pass

    # Neo4j 图谱同步（事务外，未配置则静默降级）
    try:
        di.sync_graph(email, result, net.get("relationships"))
    except Exception:
        pass

    try:
        import diagnosis_hub
        diagnosis_hub.record_from_disciple(email, None, result)
    except Exception:
        pass
    return {"ok": True, **result}


@router.get("/history")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT journal, spiritual_state, christlikeness_index, growth_edge, "
                "top_idol, next_step, source, created_at FROM disciple_assessments "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "journal": r[0], "spiritual_state": r[1],
        "christlikeness_index": float(r[2]) if r[2] is not None else None,
        "growth_edge": r[3], "top_idol": r[4] or None,
        "next_step": r[5], "source": r[6], "created_at": to_iso(r[7]),
    } for r in rows]
    return {"ok": True, "count": len(items), "items": items}


class MentorBody(BaseModel):
    question: str = Field(default="", max_length=2000)
    use_ai: bool = True


@router.post("/mentor")
def mentor(request: Request, body: MentorBody) -> dict:
    user = _require_user(request)
    twin, ctx = {}, {}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            twin = _load_twin(cur, user["email"])
            try:
                ctx = di.gather_mentor_context(cur, user["email"])
            except Exception:
                ctx = {}
    finally:
        _state["release_db"](conn)
    res = engine.mentor_reply(body.question, twin=twin,
                              settings=_settings, use_ai=body.use_ai,
                              context=di.mentor_context_text(ctx))
    return res


@router.get("/network")
def get_network(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            net = _network_metrics(cur, user["email"])
    finally:
        _state["release_db"](conn)
    return {"ok": True, "network": net, "dmi": engine.compute_dmi(net)}


class RelationshipBody(BaseModel):
    disciple_name: str = Field(default="", max_length=120)
    disciple_email: str = Field(default="", max_length=255)
    relationship_type: str = Field(default="DISCIPLER", max_length=20)
    growth_goals: list = Field(default_factory=list)


@router.post("/network")
def add_relationship(request: Request, body: RelationshipBody) -> dict:
    user = _require_user(request)
    if not body.disciple_name.strip() and not body.disciple_email.strip():
        raise HTTPException(status_code=400, detail="需要门徒姓名或邮箱")
    rtype = body.relationship_type if body.relationship_type in (
        "MENTOR", "DISCIPLER", "SPIRITUAL_PARENT", "PEER") else "DISCIPLER"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO disciple_relationships "
                "(mentor_email, disciple_email, disciple_name, relationship_type, growth_goals) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (user["email"], body.disciple_email.strip(), body.disciple_name.strip(),
                 rtype, _Json(body.growth_goals or [])),
            )
            new_id = cur.fetchone()[0]
            net = _network_metrics(cur, user["email"])
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="add failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": new_id, "network": net, "dmi": engine.compute_dmi(net)}


@router.post("/network/{rel_id}/end")
def end_relationship(request: Request, rel_id: int) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE disciple_relationships SET status='ENDED', ended_at=CURRENT_DATE "
                "WHERE id=%s AND mentor_email=%s",
                (rel_id, user["email"]),
            )
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}
