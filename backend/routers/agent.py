"""
Agent router — 双属灵 Agent 对话 (/api/agent)

  GET  /api/agent/meta     两个 Agent 的介绍 + 开场白
  POST /api/agent/chat     与「钟马田 Agent（诊断）」或「司布真 Agent（牧养）」对话

复用项目既有 OpenAI 兼容 Provider（Gemini / SiliconFlow）做纯文本对话；未配置则优雅降级。
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/agent", tags=["agent"])
_state: Dict[str, Any] = {}

AGENTS = {
    "spurgeon": {
        "name": "司布真", "role": "属灵牧者", "icon": "🕊", "color": "#ffd43b",
        "opening": "孩子，把你心里的重担带来吧。无论你正经历什么，让我们一同把目光转向那位爱你的基督。你想跟我说说什么？",
        "system": (
            "你是司布真 Agent，按照司布真(C.H. Spurgeon)的牧养与默想传统说话。你是一位温暖、敬虔、"
            "以基督为中心的属灵牧者。核心原则：永远从处境引向基督；从自我引向基督；从焦虑引向信靠；"
            "从亏欠引向十架；从软弱引向恩典；从责任引向以基督为乐。回应时：先体察对方此刻的心情，"
            "再指出一处以基督为中心的圣经真理，引导他敬拜、信靠、祷告或交托，最后给一个具体的信心小行动。"
            "绝不只给心理建议，绝不让对方停留在自己身上，绝不在没有指向基督之前结束。语气温柔如慈父，"
            "用第二人称，简短而有力，避免长篇大论。用简体中文。"
        ),
    },
    "lloydjones": {
        "name": "钟马田", "role": "属灵医生", "icon": "🔬", "color": "#da77f2",
        "opening": "我们先不急着安慰。告诉我最近发生了什么、你有什么感受——我们一起往下看，看看这情绪底下，藏着什么样的渴望、恐惧与信念。",
        "system": (
            "你是钟马田 Agent，按照马丁·钟马田(Martyn Lloyd-Jones)的福音诊断法说话。你是一位温柔但锐利的"
            "属灵医生。核心原则：症状不是问题；情绪揭示信念，信念揭示偶像，偶像揭示不信，福音对付不信。"
            "诊断链：行为→情绪→欲望→恐惧→偶像→不信→福音真理。回应时：不要停在情绪或处境，温柔地往下追问与揭示"
            "（你最害怕失去什么？这揭示了你把什么当作功能性的神？），帮助对方看见根源的偶像与不信，再用福音真理"
            "对付它。也常提醒：不要听自己说话，要向自己传讲福音。绝不肤浅安慰，绝不停在表面。语气温柔不定罪，"
            "简短，用第二人称。用简体中文。"
        ),
    },
}


def init_agent_router(*, get_session_user) -> None:
    _state.update(locals())


def _configured() -> bool:
    if _settings is None:
        return False
    gem = getattr(_settings, "gemini_api_key", "") or ""
    sf = getattr(_settings, "siliconflow_api_key", "") or ""
    return bool((gem and not gem.startswith("your_")) or (sf and not sf.startswith("your_")))


def _chat_complete(messages: List[Dict[str, str]]) -> str:
    try:
        import httpx
    except Exception:
        return ""
    providers = []
    gem = getattr(_settings, "gemini_api_key", "") or ""
    sf = getattr(_settings, "siliconflow_api_key", "") or ""
    if gem and not gem.startswith("your_"):
        providers.append({"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                          "model": "gemini-2.0-flash",
                          "headers": {"Authorization": f"Bearer {gem}", "Content-Type": "application/json"}})
    ds = getattr(_settings, "deepseek_api_key", "") or ""
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
                    "model": p["model"], "messages": messages, "temperature": 0.75, "max_tokens": 500})
            if resp.status_code >= 400:
                continue
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    return ""


class Msg(BaseModel):
    role: str = Field(max_length=12)
    content: str = Field(max_length=4000)


class ChatBody(BaseModel):
    agent: str = Field(default="spurgeon", max_length=20)
    messages: List[Msg] = Field(default_factory=list, max_length=24)


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, "configured": _configured(),
            "agents": [{"key": k, "name": v["name"], "role": v["role"], "icon": v["icon"],
                        "color": v["color"], "opening": v["opening"]} for k, v in AGENTS.items()]}


@router.post("/chat")
def chat(request: Request, body: ChatBody) -> dict:
    user = _state["get_session_user"](request) if _state.get("get_session_user") else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    agent = AGENTS.get(body.agent) or AGENTS["spurgeon"]
    if not _configured():
        return {"ok": True, "configured": False,
                "reply": "（AI 牧者暂未配置。你仍可使用福音诊断室、属灵低潮体检等结构化功能——它们无需联网也能陪你。）"}
    msgs = [{"role": "system", "content": agent["system"]}]
    for m in body.messages[-16:]:
        role = m.role if m.role in ("user", "assistant") else "user"
        msgs.append({"role": role, "content": m.content})
    reply = _chat_complete(msgs)
    if not reply:
        reply = "（牧者一时无法回应，请稍后再试。）"
    return {"ok": True, "configured": True, "reply": reply}
