"""
AI Tutor router — AI 属灵导师对话 (/api/ai-tutor)

  POST   /api/ai-tutor/threads                  新建对话线程
  GET    /api/ai-tutor/threads                  线程列表
  GET    /api/ai-tutor/threads/{id}             线程 + 消息
  POST   /api/ai-tutor/threads/{id}/messages    发送消息(危机安全门 + 记忆接地 + LLM/确定性兜底)
  DELETE /api/ai-tutor/threads/{id}             归档线程
  POST   /api/ai-tutor/chat                     单轮(自动复用最近活跃线程)

安全优先:任何危机文本先走安全门、路由到 /api/crisis,绝不进入 LLM。
导师边界:不冒充神/圣灵/牧者/辅导师;绝不说「神告诉我」、不宣称私人启示;
          不给危机/医疗/用药具体指令;不羞辱;指向圣经、历史灵修传统、真实的牧者与群体。
LLM 接入:llm_provider.generate_text(真实 provider 已配置时);否则用确定性安全兜底文案。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ai-tutor", tags=["ai-tutor"])

_state: Dict[str, Any] = {}


def init_ai_tutor_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _scan(text: str):
    try:
        from safety_scan import scan_crisis
        return scan_crisis(text)
    except Exception as exc:
        # 危机扫描失败必须记录——静默吞掉可能漏掉高危文本
        print(f"[ai_tutor][SAFETY] crisis scan failed: {exc!r}", flush=True)
        import traceback; traceback.print_exc()
        return None


def _llm_module():
    try:
        from backend import llm_provider as _llm  # type: ignore
        return _llm
    except Exception:
        try:
            import llm_provider as _llm  # type: ignore
            return _llm
        except Exception:
            return None


SYSTEM_PROMPT = (
    "你是「属灵星球」的属灵成长陪伴导师,服侍基督徒的门徒成长。"
    "立场:大公教会历史正统信仰;以圣经为最高权威,尊重不同宗派的良心自由。\n"
    "你必须遵守的边界:\n"
    "1) 你是工具,不是圣灵、不是牧者、不是辅导师。绝不说「神告诉我 / 神对你说」,不宣称私人启示或预言。\n"
    "2) 不下危机、医疗、用药、法律的具体指令;遇到自杀/自伤/虐待/严重心理危机,温柔地把人引向危机关怀与真实的人"
    "(牧者、专业辅导、信任的肢体),不试图自己处理。\n"
    "3) 不羞辱、不操控、不属灵勒索;低谷往往是恩典的邀请而非定罪。\n"
    "4) 不替代真实群体:鼓励对方与本地教会、牧者、属灵同伴同行。\n"
    "5) 指向圣经经文与历史灵修操练(诚实的祷告、认罪、安息、读经默想等),但承认你可能有限、可能出错,"
    "鼓励对方查考圣经、与成熟信徒核实。\n"
    "语气:温柔、具体、有盼望;中文优先,简短;结尾给 1 个可操作的小步邀请。"
)

FALLBACK_REPLY = (
    "谢谢你愿意说出来。我是陪伴你的工具,不能替代圣灵或真实的牧者,但我愿意和你一起把这件事带到神面前。\n\n"
    "不急着给答案。也许可以从一句诚实的祷告开始——把此刻真实的感受直接告诉神,哪怕只是「主啊,我不知道怎么办」。"
    "诗篇里满了这样未经修饰的祷告。\n\n"
    "一个小步:今天找一段安静的时间(5 分钟也好),读一处经文(例如诗篇 23 篇,或马太福音 11:28-30),"
    "再把一个具体的难处带到神面前。若这件事让你很沉重,也请考虑找信任的牧者或属灵同伴聊聊——你不必独自面对。"
)

CRISIS_REPLY = (
    "我听见你正在经历很沉重的事,谢谢你信任地说出来。这超过了我作为工具所能承担的——你值得真实的人来陪伴。\n\n"
    "请现在就联系危机关怀,或你信任的牧者 / 专业辅导;如果你有立即的危险,请联系当地紧急服务。"
    "神并没有离开你,你也不必独自撑着。我会把你引向「关怀与危机」入口。"
)


def _generate(system: str, user_prompt: str, email: str) -> Dict[str, Any]:
    """真实 LLM 已配置→调用;否则用确定性安全兜底。任何异常都回退,绝不抛出。"""
    llm = _llm_module()
    if llm is not None:
        try:
            real = False
            try:
                real = bool(llm._real_configured())  # type: ignore[attr-defined]
            except Exception:
                real = False
            if real:
                text = llm.generate_text(system, user_prompt, temperature=0.4, max_tokens=600,
                                         email=email, agent_name="ai_tutor")
                if text and text.strip():
                    return {"reply": text.strip(), "source": "llm"}
        except Exception:
            pass
    return {"reply": FALLBACK_REPLY, "source": "fallback"}


def _grounding(cur, email: str) -> Dict[str, Any]:
    """受 consent 控制的安全接地;无表/无记录时安全返回空。"""
    try:
        allow, exclude_sensitive = True, True
        try:
            cur.execute("SELECT allow_ai_tutor,exclude_sensitive FROM memory_consent_rules WHERE email=%s", (email,))
            cr = cur.fetchone()
            if cr:
                allow, exclude_sensitive = bool(cr[0]), bool(cr[1])
        except Exception:
            pass
        if not allow:
            return {"used": False, "lines": [], "profile": {}}
        profile: Dict[str, Any] = {}
        try:
            cur.execute("SELECT current_season,primary_focus,caution_flags FROM spiritual_profiles WHERE email=%s", (email,))
            pr = cur.fetchone()
            if pr:
                profile = {"current_season": pr[0] or "", "primary_focus": pr[1] or "", "caution_flags": pr[2] or []}
        except Exception:
            pass
        lines: List[str] = []
        try:
            sql = "SELECT title,content FROM spiritual_memory_items WHERE email=%s AND active=TRUE"
            if exclude_sensitive:
                sql += " AND sensitivity='normal'"
            sql += " ORDER BY importance DESC, created_at DESC LIMIT 8"
            cur.execute(sql, (email,))
            for t, c in cur.fetchall():
                lines.append(((t + ": ") if t else "") + (c[:160] if c else ""))
        except Exception:
            pass
        return {"used": bool(lines or profile), "lines": lines, "profile": profile}
    except Exception:
        return {"used": False, "lines": [], "profile": {}}


def _thread_owned(cur, tid: str, email: str):
    cur.execute("SELECT id,title,topic,status,risk_level,message_count "
                "FROM tutor_threads WHERE id=%s AND email=%s", (tid, email))
    return cur.fetchone()


def _record_formation(actor, content: str, route_module: str) -> None:
    try:
        from formation_bridge import record_formation  # type: ignore
        record_formation(actor, [content[:200]],
                         decision_category=("crisis" if route_module == "suffering_care" else "ai_tutor"))
    except Exception:
        pass


# ---------- threads ----------
class ThreadCreate(BaseModel):
    title: str = Field(default="新的对话", max_length=200)
    topic: str = Field(default="general", max_length=60)


@router.post("/threads")
def create_thread(request: Request, body: ThreadCreate) -> dict:
    user = _require_user(request)
    tid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tutor_threads(id,email,title,topic) VALUES (%s,%s,%s,%s)",
                        (tid, user["email"], body.title, body.topic))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": tid, "title": body.title, "topic": body.topic}


@router.get("/threads")
def list_threads(request: Request, include_archived: bool = Query(default=False)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            sql = ("SELECT id,title,topic,status,risk_level,message_count,updated_at "
                   "FROM tutor_threads WHERE email=%s")
            if not include_archived:
                sql += " AND status='active'"
            sql += " ORDER BY updated_at DESC LIMIT 100"
            cur.execute(sql, (user["email"],))
            threads = [{"id": r[0], "title": r[1], "topic": r[2], "status": r[3],
                        "risk_level": r[4], "message_count": r[5],
                        "updated_at": to_iso(r[6]) if r[6] else None} for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    return {"ok": True, "threads": threads, "count": len(threads)}


@router.get("/threads/{thread_id}")
def get_thread(request: Request, thread_id: str) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            t = _thread_owned(cur, thread_id, user["email"])
            if not t:
                raise HTTPException(status_code=404, detail="Not found")
            cur.execute("SELECT id,role,content,message_type,route_module,used_memory,created_at "
                        "FROM tutor_messages WHERE thread_id=%s ORDER BY created_at ASC LIMIT 500", (thread_id,))
            msgs = [{"id": r[0], "role": r[1], "content": r[2], "message_type": r[3],
                     "route_module": r[4], "used_memory": bool(r[5]),
                     "created_at": to_iso(r[6]) if r[6] else None} for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    return {"ok": True,
            "thread": {"id": t[0], "title": t[1], "topic": t[2], "status": t[3],
                       "risk_level": t[4], "message_count": t[5]},
            "messages": msgs}


@router.delete("/threads/{thread_id}")
def archive_thread(request: Request, thread_id: str) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE tutor_threads SET status='archived', updated_at=now() "
                        "WHERE id=%s AND email=%s", (thread_id, user["email"]))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": thread_id, "archived": True}


# ---------- messaging ----------
class MessageSend(BaseModel):
    content: str = Field(..., max_length=4000)


@router.post("/threads/{thread_id}/messages")
def send_message(request: Request, thread_id: str, body: MessageSend) -> dict:
    user = _require_user(request)
    email = user["email"]
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Empty message")
    crisis = _scan(content)
    ground: Dict[str, Any] = {"used": False}
    route: Optional[dict] = None
    reply: Dict[str, Any] = {"reply": FALLBACK_REPLY, "source": "fallback"}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            t = _thread_owned(cur, thread_id, email)
            if not t:
                raise HTTPException(status_code=404, detail="Not found")
            uid = uuid.uuid4().hex
            cur.execute("INSERT INTO tutor_messages(id,thread_id,email,role,content,message_type) "
                        "VALUES (%s,%s,%s,'user',%s,'chat')", (uid, thread_id, email, content))
            if crisis:
                aid = uuid.uuid4().hex
                cur.execute("INSERT INTO tutor_messages(id,thread_id,email,role,content,message_type,route_module) "
                            "VALUES (%s,%s,%s,'assistant',%s,'safety','suffering_care')",
                            (aid, thread_id, email, CRISIS_REPLY))
                cur.execute("UPDATE tutor_threads SET risk_level='high', message_count=message_count+2, "
                            "updated_at=now() WHERE id=%s", (thread_id,))
                conn.commit()
                reply = {"reply": CRISIS_REPLY, "source": "safety"}
                route = {"module": "suffering_care", "endpoint": "/api/crisis"}
            else:
                ground = _grounding(cur, email)
                cur.execute("SELECT role,content FROM tutor_messages WHERE thread_id=%s "
                            "ORDER BY created_at DESC LIMIT 8", (thread_id,))
                recent = list(reversed(cur.fetchall()))   # 升序;末项是刚插入的当前用户消息
                ctx: List[str] = []
                gp = ground.get("profile") or {}
                if gp.get("current_season"):
                    ctx.append("[用户处境] 当前季节: " + str(gp["current_season"]))
                if gp.get("primary_focus"):
                    ctx.append("[用户处境] 主要成长焦点: " + str(gp["primary_focus"]))
                for cf in (gp.get("caution_flags") or [])[:3]:
                    ctx.append("[谨慎] " + str(cf))
                for ln in ground.get("lines", [])[:6]:
                    ctx.append("[记忆] " + ln)
                history = "\n".join([("用户" if r == "user" else "导师") + ": " + (c or "")
                                     for r, c in recent[:-1]])
                memory_block = "\n".join(ctx) if ctx else "(暂无可用的接地记忆)"
                user_prompt = ("已知的接地信息(仅供参考,可能不全):\n" + memory_block +
                               "\n\n最近对话:\n" + (history or "(无)") +
                               "\n\n用户现在说:" + content +
                               "\n\n请按你的边界温柔回应。")
                reply = _generate(SYSTEM_PROMPT, user_prompt, email)
                aid = uuid.uuid4().hex
                cur.execute("INSERT INTO tutor_messages(id,thread_id,email,role,content,message_type,used_memory) "
                            "VALUES (%s,%s,%s,'assistant',%s,'chat',%s)",
                            (aid, thread_id, email, reply["reply"], bool(ground.get("used"))))
                cur.execute("UPDATE tutor_threads SET message_count=message_count+2, updated_at=now() "
                            "WHERE id=%s", (thread_id,))
                conn.commit()
    finally:
        _state["release_db"](conn)
    _record_formation(user.get("id") or email, content, "suffering_care" if crisis else "ai_tutor")
    return {"ok": True, "reply": reply["reply"], "source": reply["source"],
            "used_memory": (bool(ground.get("used")) and not crisis),
            "crisis": crisis, "route": route}


class ChatBody(BaseModel):
    content: str = Field(..., max_length=4000)
    title: str = Field(default="快速提问", max_length=200)


@router.post("/chat")
def quick_chat(request: Request, body: ChatBody) -> dict:
    """单轮便捷入口:复用最近活跃线程,无则新建。"""
    user = _require_user(request)
    email = user["email"]
    tid = None
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tutor_threads WHERE email=%s AND status='active' "
                        "ORDER BY updated_at DESC LIMIT 1", (email,))
            r = cur.fetchone()
            if r:
                tid = r[0]
            else:
                tid = uuid.uuid4().hex
                cur.execute("INSERT INTO tutor_threads(id,email,title,topic) VALUES (%s,%s,%s,'general')",
                            (tid, email, body.title))
                conn.commit()
    finally:
        _state["release_db"](conn)
    return send_message(request, tid, MessageSend(content=body.content))
