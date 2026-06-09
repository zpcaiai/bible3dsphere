"""
Guardian router — 属灵守护者 / AI Companion Sprite (/api/guardian)

  POST /api/guardian/message            聊天（safety→emotion→reply→memory→pattern→idol→growth）
  POST /api/guardian/checkin/emotion    情绪打卡
  POST /api/guardian/checkin/spiritual  属灵状态打卡（信/望/爱）
  POST /api/guardian/prayer             保存祷告 / 标记应允
  GET  /api/guardian/prayer             祷告列表
  POST /api/guardian/devotion           保存 SOAP 灵修
  GET  /api/guardian/devotion           今日经文 + 灵修列表
  GET  /api/guardian/profile            Guardian 档案 + 成长阶段
  GET  /api/guardian/state              Guardian 实时状态 + 最近信望爱
  GET  /api/guardian/memories           长期记忆
  GET  /api/guardian/insights           行为模式 + 偶像信号 + 情绪分布
  GET  /api/guardian/push-prefs         守护者云推送(关怀消息)开关状态
  POST /api/guardian/push-prefs         切换云推送开关（订阅本身走 /api/push/subscribe）

定位：属灵同行者，不是神/牧者/医生/心理咨询师的替代。
LLM 未配置时自动使用 guardian_engine 的模板回复，功能完整可用。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    import guardian_engine as ge
except ImportError:  # pragma: no cover
    from backend import guardian_engine as ge  # type: ignore

try:
    from core.config import get_settings
    _settings = get_settings()
except Exception:  # pragma: no cover
    _settings = None

router = APIRouter(prefix="/api/guardian", tags=["guardian"])

_state: Dict[str, Any] = {}


def init_guardian_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_email(request: Request) -> str:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user["email"]


def _uid() -> str:
    return uuid.uuid4().hex


# ─────────────────────────────────────────────────────────────────────────────
# LLM（与 routers/agent.py 同一 provider 链；未配置则返回 ""）
# ─────────────────────────────────────────────────────────────────────────────

def _llm_configured() -> bool:
    if _settings is None:
        return False
    for key in ("gemini_api_key", "deepseek_api_key", "siliconflow_api_key"):
        v = getattr(_settings, key, "") or ""
        if v and not v.startswith("your_"):
            return True
    return False


def _chat_complete(messages: List[Dict[str, str]]) -> str:
    if not _llm_configured():
        return ""
    try:
        from lang_context import apply_lang_messages as _apply_lang
        messages = _apply_lang(messages)
    except Exception:
        pass
    try:
        import httpx
    except Exception:
        return ""
    providers = []
    gem = getattr(_settings, "gemini_api_key", "") or ""
    ds = getattr(_settings, "deepseek_api_key", "") or ""
    sf = getattr(_settings, "siliconflow_api_key", "") or ""
    if gem and not gem.startswith("your_"):
        providers.append({"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                          "model": "gemini-2.0-flash",
                          "headers": {"Authorization": f"Bearer {gem}", "Content-Type": "application/json"}})
    if ds and not ds.startswith("your_"):
        providers.append({"url": "https://api.deepseek.com/chat/completions",
                          "model": "deepseek-chat",
                          "headers": {"Authorization": f"Bearer {ds}", "Content-Type": "application/json"}})
    if sf and not sf.startswith("your_"):
        providers.append({"url": "https://api.siliconflow.cn/v1/chat/completions",
                          "model": "deepseek-ai/DeepSeek-V3",
                          "headers": {"Authorization": f"Bearer {sf}", "Content-Type": "application/json"}})
    for p in providers:
        try:
            with httpx.Client(timeout=40) as client:
                resp = client.post(p["url"], headers=p["headers"], json={
                    "model": p["model"], "messages": messages,
                    "temperature": 0.7, "max_tokens": 500})
            if resp.status_code >= 400:
                continue
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _db():
    return _state["get_db"]()


def _release(conn) -> None:
    _state["release_db"](conn)


def _to_iso(dt) -> str:
    return _state["to_shanghai_iso"](dt) if dt else ""


def _ensure_profile(cur, email: str) -> tuple:
    cur.execute("SELECT id, name, form_stage, intimacy_level, personality_style, visual_skin "
                "FROM guardian_profiles WHERE email=%s", (email,))
    row = cur.fetchone()
    if row:
        return row
    pid = _uid()
    cur.execute("INSERT INTO guardian_profiles (id, email) VALUES (%s, %s)", (pid, email))
    return (pid, "守护者", "seed", 1, "gentle", "flame")


def _ensure_state(cur, email: str) -> tuple:
    cur.execute("SELECT id, current_mood, spiritual_state, energy_level, sprite_state, "
                "last_interaction_at FROM guardian_states WHERE email=%s", (email,))
    row = cur.fetchone()
    if row:
        return row
    sid = _uid()
    cur.execute("INSERT INTO guardian_states (id, email) VALUES (%s, %s)", (sid, email))
    return (sid, "calm", "steady", 80, "idle", None)


def _update_state(cur, email: str, mood: str, spiritual: str, sprite: str) -> None:
    cur.execute(
        "UPDATE guardian_states SET current_mood=%s, spiritual_state=%s, sprite_state=%s, "
        "last_interaction_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE email=%s",
        (mood, spiritual, sprite, email))


def _refresh_growth(cur, email: str) -> str:
    cur.execute("SELECT DISTINCT DATE(created_at) FROM guardian_messages WHERE email=%s "
                "ORDER BY 1", (email,))
    active_days = [str(r[0]) for r in cur.fetchall()]
    cur.execute("SELECT (SELECT COUNT(*) FROM guardian_prayer_entries WHERE email=%s) + "
                "(SELECT COUNT(*) FROM guardian_devotion_entries WHERE email=%s)",
                (email, email))
    pd_count = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT COUNT(*) FROM guardian_prayer_entries WHERE email=%s AND "
                "category='intercession'", (email,))
    helped = int(cur.fetchone()[0] or 0) > 0
    stage = ge.compute_form_stage(active_days, pd_count, helped)
    cur.execute("UPDATE guardian_profiles SET form_stage=%s, updated_at=CURRENT_TIMESTAMP "
                "WHERE email=%s AND form_stage <> %s", (stage, email, stage))
    return stage


# ─────────────────────────────────────────────────────────────────────────────
# 跨模块用户画像（个性化回复的数据源）
# ─────────────────────────────────────────────────────────────────────────────

def _safe_rows(cur, sql: str, params: tuple) -> list:
    """用 SAVEPOINT 保护的查询：表不存在/查询失败时返回 []，不影响主事务。"""
    try:
        cur.execute("SAVEPOINT guardian_ctx")
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.execute("RELEASE SAVEPOINT guardian_ctx")
        return rows
    except Exception:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT guardian_ctx")
        except Exception:
            pass
        return []


def _clip(s, n: int = 60) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


def _gather_user_context(cur, email: str, display_name: str = "") -> List[str]:
    """从星球各模块温柔地收集这位用户的真实处境（全部查询失败安全）。"""
    ctx: List[str] = []
    if display_name:
        ctx.append(f"用户的称呼：{display_name}")

    # 每日省察（依纳爵 Examen）
    rows = _safe_rows(cur, "SELECT consolation, desolation, gratitude, tomorrow_step, "
                           "consolation_level, entry_date FROM examen_entries "
                           "WHERE email=%s ORDER BY entry_date DESC LIMIT 1", (email,))
    if rows:
        r = rows[0]
        bits = []
        if r[0]:
            bits.append(f"安慰时刻：{_clip(r[0])}")
        if r[1]:
            bits.append(f"枯涩时刻：{_clip(r[1])}")
        if r[3]:
            bits.append(f"明日微顺服：{_clip(r[3])}")
        if bits:
            ctx.append(f"最近一次省察（{r[5]}，亲近感{r[4]}/10）：" + "；".join(bits))

    # 感恩记录
    rows = _safe_rows(cur, "SELECT content FROM gratitude_entries WHERE email=%s "
                           "ORDER BY created_at DESC LIMIT 3", (email,))
    if rows:
        ctx.append("最近的感恩：" + "；".join(_clip(r[0], 40) for r in rows))

    # 福音诊断室（钟马田诊断链）
    rows = _safe_rows(cur, "SELECT event, feeling, fear FROM gospel_diagnoses "
                           "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
    if rows and any(rows[0]):
        r = rows[0]
        ctx.append(f"最近一次福音诊断：事件「{_clip(r[0], 40)}」，感受「{_clip(r[1], 30)}」，"
                   f"害怕「{_clip(r[2], 30)}」")

    # 属灵低潮体检
    rows = _safe_rows(cur, "SELECT index_score, level, summary FROM spiritual_checkups "
                           "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
    if rows:
        r = rows[0]
        ctx.append(f"属灵体检：指数{round(r[0] or 0, 1)}（{r[1] or '—'}）{_clip(r[2], 50)}")

    # 信望爱打卡
    rows = _safe_rows(cur, "SELECT faith_level, hope_level, love_level, spiritual_state "
                           "FROM guardian_spiritual_checkins WHERE email=%s "
                           "ORDER BY created_at DESC LIMIT 1", (email,))
    if rows:
        r = rows[0]
        ctx.append(f"最近信望爱打卡：信{r[0]}/望{r[1]}/爱{r[2]}，属灵季节：{r[3]}")

    # 进行中的祷告
    rows = _safe_rows(cur, "SELECT title FROM guardian_prayer_entries WHERE email=%s "
                           "AND status='ongoing' ORDER BY created_at DESC LIMIT 3", (email,))
    if rows:
        ctx.append("仍在等候的祷告：" + "；".join(_clip(r[0], 24) for r in rows))

    # 偶像信号（最近一条，仅作背景）
    rows = _safe_rows(cur, "SELECT idol_type, signal FROM guardian_idol_signals "
                           "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
    if rows:
        ctx.append(f"曾温和觉察到的倾向：{rows[0][0]}（{_clip(rows[0][1], 40)}）")

    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# POST /message
# ─────────────────────────────────────────────────────────────────────────────

class MessageBody(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    mode: str = Field(default="companion", max_length=24)


@router.post("/message")
def post_message(request: Request, body: MessageBody) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = user["email"]
    display_name = (user.get("name") or user.get("nickname") or "").strip()
    mode = body.mode if body.mode in ge.VALID_MODES else "companion"
    text = body.message.strip()

    conn = _db()
    try:
        cur = conn.cursor()
        profile = _ensure_profile(cur, email)
        _ensure_state(cur, email)
        cur.execute("INSERT INTO guardian_messages (id, email, role, content, mode) "
                    "VALUES (%s, %s, 'user', %s, %s)", (_uid(), email, text, mode))

        # 1. SafetyGuard
        risk = ge.check_safety(text)
        if risk == "high":
            reply = ge.high_risk_reply()
            cur.execute("INSERT INTO guardian_messages (id, email, role, content, mode) "
                        "VALUES (%s, %s, 'assistant', %s, %s)", (_uid(), email, reply, mode))
            _update_state(cur, email, "sadness", "struggling", "comforting")
            conn.commit()
            return {"ok": True, "reply": reply, "spriteState": "comforting",
                    "detectedEmotion": {"emotionType": "sadness", "intensity": 9, "trigger": None},
                    "suggestedAction": "contact-trusted-person", "memorySaved": False}

        # 2. 情绪 + 属灵状态
        emotion = ge.analyze_emotion(text)
        spiritual = ge.assess_spiritual(text)
        if emotion["emotionType"] != "neutral":
            cur.execute("INSERT INTO guardian_emotion_events (id, email, emotion_type, intensity, source) "
                        "VALUES (%s, %s, %s, %s, 'chat')",
                        (_uid(), email, emotion["emotionType"], emotion["intensity"]))

        # 3. 生成回复
        suggested_action = None
        if mode == "prayer":
            cur.execute("SELECT COUNT(*) FROM guardian_messages WHERE email=%s AND "
                        "mode='prayer' AND role='assistant'", (email,))
            turns = int(cur.fetchone()[0] or 0) % (len(ge.ACTS_STEPS) + 1)
            guide = ge.acts_guide(turns)
            reply = guide["reply"]
            if guide["done"]:
                suggested_action = "save-prayer"
        elif mode == "devotion":
            cur.execute("SELECT COUNT(*) FROM guardian_messages WHERE email=%s AND "
                        "mode='devotion' AND role='assistant'", (email,))
            turns = int(cur.fetchone()[0] or 0) % (len(ge.SOAP_STEPS) + 1)
            guide = ge.soap_guide(turns)
            reply = guide["reply"]
            if guide["done"]:
                suggested_action = "save-devotion"
        else:
            reply = ""
            if _llm_configured():
                cur.execute("SELECT memory_type, content FROM guardian_memories WHERE email=%s "
                            "ORDER BY created_at DESC LIMIT 8", (email,))
                memories = [f"[{r[0]}] {r[1]}" for r in cur.fetchall()]
                cur.execute("SELECT emotion_type, intensity FROM guardian_emotion_events "
                            "WHERE email=%s ORDER BY created_at DESC LIMIT 5", (email,))
                recent = [f"{r[0]}({r[1]}/10)" for r in cur.fetchall()]
                user_context = _gather_user_context(cur, email, display_name)
                _lang = (request.headers.get('X-Lang') or 'zh').lower()
                system = ge.build_system_prompt(mode, profile[1], profile[2], memories,
                                                recent, user_context, lang=_lang)
                cur.execute("SELECT role, content FROM guardian_messages WHERE email=%s "
                            "ORDER BY created_at DESC LIMIT 12", (email,))
                history = list(reversed(cur.fetchall()))
                msgs = [{"role": "system", "content": system}]
                for role, content in history:
                    msgs.append({"role": role if role in ("user", "assistant") else "user",
                                 "content": content})
                reply = _chat_complete(msgs)
            if not reply:
                reply = ge.mock_reply(emotion["emotionType"])
                note = spiritual.get("gentleNote")
                if note:
                    reply += f"\n\n{note}"
                # 模板模式下的轻量个性化：情绪平稳时温柔回访一件等候中的祷告
                if emotion["emotionType"] == "neutral" and mode in ("companion", "growth"):
                    rows = _safe_rows(cur, "SELECT title FROM guardian_prayer_entries "
                                           "WHERE email=%s AND status='ongoing' "
                                           "ORDER BY created_at ASC LIMIT 1", (email,))
                    if rows:
                        reply += (f"\n\n（也想轻轻问一句：你之前记下的祷告「{_clip(rows[0][0], 20)}」，"
                                  "最近有什么进展吗？我仍在与你一同等候。）")

        if risk == "medium":
            reply += ge.medium_risk_suffix()

        # 4. 记忆提取
        memory_saved = False
        mem = ge.extract_memory(text)
        if mem:
            cur.execute("INSERT INTO guardian_memories (id, email, memory_type, content, importance) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (_uid(), email, mem["memoryType"], mem["content"], mem["importance"]))
            memory_saved = True

        # 5. 行为模式 + 偶像信号
        cur.execute("SELECT emotion_type FROM guardian_emotion_events WHERE email=%s "
                    "ORDER BY created_at DESC LIMIT 20", (email,))
        pattern = ge.detect_pattern([r[0] for r in cur.fetchall()])
        if pattern:
            cur.execute(
                "INSERT INTO guardian_behavior_patterns "
                "(id, email, pattern_type, trigger, typical_response, spiritual_root, confidence) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (email, pattern_type) DO UPDATE SET "
                "confidence=EXCLUDED.confidence, last_seen_at=CURRENT_TIMESTAMP",
                (_uid(), email, pattern["patternType"], pattern["trigger"],
                 pattern["typicalResponse"], pattern["spiritualRoot"], pattern["confidence"]))
        idol = ge.detect_idol_signal(text)
        if idol:
            cur.execute("INSERT INTO guardian_idol_signals "
                        "(id, email, idol_type, signal, intensity, evidence, suggestion) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (_uid(), email, idol["idolType"], idol["signal"], idol["intensity"],
                         idol["evidence"], idol["suggestion"]))
            if mode == "idol-monitor":
                reply += f"\n\n（温柔的觉察：{idol['signal']}。{idol['suggestion']}）"

        # 6. 状态 + 成长
        sprite = ge.sprite_state_for(mode, emotion["emotionType"], emotion["intensity"])
        _update_state(cur, email, emotion["emotionType"], spiritual["spiritualState"], sprite)
        cur.execute("INSERT INTO guardian_messages (id, email, role, content, mode) "
                    "VALUES (%s, %s, 'assistant', %s, %s)", (_uid(), email, reply, mode))
        _refresh_growth(cur, email)
        conn.commit()

        return {"ok": True, "reply": reply, "spriteState": sprite,
                "detectedEmotion": emotion, "suggestedAction": suggested_action,
                "memorySaved": memory_saved}
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# Check-ins
# ─────────────────────────────────────────────────────────────────────────────

class EmotionCheckInBody(BaseModel):
    emotionType: str = Field(default="neutral", max_length=24)
    intensity: int = Field(default=5, ge=1, le=10)
    trigger: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=2000)


@router.post("/checkin/emotion")
def checkin_emotion(request: Request, body: EmotionCheckInBody) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        _ensure_state(cur, email)
        eid = _uid()
        cur.execute("INSERT INTO guardian_emotion_events "
                    "(id, email, emotion_type, intensity, trigger, note, source) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'checkin')",
                    (eid, email, body.emotionType, body.intensity,
                     body.trigger or None, body.note or None))
        cur.execute("UPDATE guardian_states SET current_mood=%s, "
                    "last_interaction_at=CURRENT_TIMESTAMP WHERE email=%s",
                    (body.emotionType, email))
        conn.commit()
        return {"ok": True, "id": eid}
    finally:
        _release(conn)


class SpiritualCheckInBody(BaseModel):
    faithLevel: int = Field(default=5, ge=1, le=10)
    hopeLevel: int = Field(default=5, ge=1, le=10)
    loveLevel: int = Field(default=5, ge=1, le=10)
    spiritualState: str = Field(default="steady", max_length=24)
    note: str = Field(default="", max_length=2000)


@router.post("/checkin/spiritual")
def checkin_spiritual(request: Request, body: SpiritualCheckInBody) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        _ensure_state(cur, email)
        cid = _uid()
        cur.execute("INSERT INTO guardian_spiritual_checkins "
                    "(id, email, faith_level, hope_level, love_level, spiritual_state, note) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (cid, email, body.faithLevel, body.hopeLevel, body.loveLevel,
                     body.spiritualState, body.note or None))
        cur.execute("UPDATE guardian_states SET spiritual_state=%s, "
                    "last_interaction_at=CURRENT_TIMESTAMP WHERE email=%s",
                    (body.spiritualState, email))
        conn.commit()
        return {"ok": True, "id": cid}
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# Prayer
# ─────────────────────────────────────────────────────────────────────────────

class PrayerBody(BaseModel):
    action: str = Field(default="create", max_length=16)  # create|markAnswered
    id: str = Field(default="", max_length=64)
    title: str = Field(default="", max_length=120)
    content: str = Field(default="", max_length=4000)
    category: str = Field(default="supplication", max_length=24)


@router.post("/prayer")
def post_prayer(request: Request, body: PrayerBody) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        if body.action == "markAnswered" and body.id:
            cur.execute("UPDATE guardian_prayer_entries SET status='answered', "
                        "answered_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP "
                        "WHERE id=%s AND email=%s", (body.id, email))
            conn.commit()
            return {"ok": True, "id": body.id}
        content = body.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="content is required")
        pid = _uid()
        cur.execute("INSERT INTO guardian_prayer_entries (id, email, title, content, category) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (pid, email, body.title or content[:20], content, body.category))
        _refresh_growth(cur, email)
        conn.commit()
        return {"ok": True, "id": pid}
    finally:
        _release(conn)


@router.get("/prayer")
def list_prayers(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, category, status, answered_at, created_at "
                    "FROM guardian_prayer_entries WHERE email=%s "
                    "ORDER BY created_at DESC LIMIT %s", (email, limit))
        entries = [{"id": r[0], "title": r[1] or "", "content": r[2] or "",
                    "category": r[3], "status": r[4],
                    "answeredAt": _to_iso(r[5]), "createdAt": _to_iso(r[6])}
                   for r in cur.fetchall()]
        return {"ok": True, "entries": entries}
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# Devotion
# ─────────────────────────────────────────────────────────────────────────────

class DevotionBody(BaseModel):
    scripture: str = Field(default="", max_length=255)
    observation: str = Field(default="", max_length=4000)
    application: str = Field(default="", max_length=4000)
    prayer: str = Field(default="", max_length=4000)


@router.post("/devotion")
def post_devotion(request: Request, body: DevotionBody) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        did = _uid()
        cur.execute("INSERT INTO guardian_devotion_entries "
                    "(id, email, scripture, observation, application, prayer) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (did, email, body.scripture or ge.scripture_of_the_day()["reference"],
                     body.observation or None, body.application or None, body.prayer or None))
        _refresh_growth(cur, email)
        conn.commit()
        return {"ok": True, "id": did}
    finally:
        _release(conn)


@router.get("/devotion")
def list_devotions(request: Request, limit: int = Query(default=30, ge=1, le=100)) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, scripture, observation, application, prayer, created_at "
                    "FROM guardian_devotion_entries WHERE email=%s "
                    "ORDER BY created_at DESC LIMIT %s", (email, limit))
        entries = [{"id": r[0], "scripture": r[1] or "", "observation": r[2] or "",
                    "application": r[3] or "", "prayer": r[4] or "",
                    "createdAt": _to_iso(r[5])} for r in cur.fetchall()]
        return {"ok": True, "scriptureOfTheDay": ge.scripture_of_the_day(), "entries": entries}
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# Profile / State / Memories / Insights
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/profile")
def get_profile(request: Request) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        profile = _ensure_profile(cur, email)
        conn.commit()
        stage = profile[2] or "seed"
        return {"ok": True,
                "profile": {"name": profile[1], "formStage": stage,
                            "intimacyLevel": profile[3],
                            "personalityStyle": profile[4], "visualSkin": profile[5]},
                "stageInfo": ge.STAGE_INFO.get(stage, ge.STAGE_INFO["seed"]),
                "stageProgress": ge.stage_progress(stage)}
    finally:
        _release(conn)


@router.get("/state")
def get_state(request: Request) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        st = _ensure_state(cur, email)
        cur.execute("SELECT faith_level, hope_level, love_level FROM guardian_spiritual_checkins "
                    "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        latest = cur.fetchone()
        conn.commit()
        return {"ok": True,
                "state": {"currentMood": st[1], "spiritualState": st[2],
                          "energyLevel": st[3], "spriteState": st[4],
                          "lastInteractionAt": _to_iso(st[5])},
                "latestCheckIn": ({"faithLevel": latest[0], "hopeLevel": latest[1],
                                   "loveLevel": latest[2]} if latest else None)}
    finally:
        _release(conn)


@router.get("/memories")
def get_memories(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, memory_type, content, importance, created_at "
                    "FROM guardian_memories WHERE email=%s "
                    "ORDER BY created_at DESC LIMIT %s", (email, limit))
        memories = [{"id": r[0], "memoryType": r[1], "content": r[2],
                     "importance": r[3], "createdAt": _to_iso(r[4])}
                    for r in cur.fetchall()]
        return {"ok": True, "memories": memories}
    finally:
        _release(conn)


@router.get("/insights")
def get_insights(request: Request) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, pattern_type, trigger, typical_response, spiritual_root, "
                    "confidence FROM guardian_behavior_patterns WHERE email=%s", (email,))
        patterns = [{"id": r[0], "patternType": r[1], "trigger": r[2],
                     "typicalResponse": r[3], "spiritualRoot": r[4], "confidence": r[5]}
                    for r in cur.fetchall()]
        cur.execute("SELECT id, idol_type, signal, intensity, evidence, suggestion, created_at "
                    "FROM guardian_idol_signals WHERE email=%s "
                    "ORDER BY created_at DESC LIMIT 10", (email,))
        idols = [{"id": r[0], "idolType": r[1], "signal": r[2], "intensity": r[3],
                  "evidence": r[4], "suggestion": r[5], "createdAt": _to_iso(r[6])}
                 for r in cur.fetchall()]
        cur.execute("SELECT emotion_type, COUNT(*) FROM guardian_emotion_events "
                    "WHERE email=%s GROUP BY emotion_type ORDER BY 2 DESC LIMIT 12", (email,))
        emotion_counts = {r[0]: int(r[1]) for r in cur.fetchall()}
        return {"ok": True, "patterns": patterns, "idolSignals": idols,
                "emotionCounts": emotion_counts}
    finally:
        _release(conn)


# ─────────────────────────────────────────────────────────────────────────────
# 云推送（守护者关怀消息）开关 — 订阅/VAPID 走 /api/push/*，此处只管 guardian 偏好
# ─────────────────────────────────────────────────────────────────────────────
class PushPrefsBody(BaseModel):
    care_push_on: bool = True


@router.get("/push-prefs")
def get_push_prefs(request: Request) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        _ensure_profile(cur, email)
        conn.commit()
        cur.execute("SELECT COALESCE(care_push_on, TRUE) FROM guardian_profiles "
                    "WHERE email=%s", (email,))
        row = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM push_subscriptions "
                    "WHERE email=%s AND enabled=TRUE", (email,))
        subs = cur.fetchone()
        return {"ok": True, "carePushOn": bool(row[0]) if row else True,
                "subscribed": bool(subs and subs[0])}
    finally:
        _release(conn)


@router.post("/push-prefs")
def set_push_prefs(request: Request, body: PushPrefsBody) -> dict:
    email = _require_email(request)
    conn = _db()
    try:
        cur = conn.cursor()
        _ensure_profile(cur, email)
        cur.execute("UPDATE guardian_profiles SET care_push_on=%s, updated_at=NOW() "
                    "WHERE email=%s", (body.care_push_on, email))
        conn.commit()
        return {"ok": True, "carePushOn": body.care_push_on}
    finally:
        _release(conn)
