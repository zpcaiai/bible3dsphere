"""
Confession router — 认罪与赦免 (/api/confession)

为保护隐私，**不存储认罪正文**。POST /record 仅：
  - 回流一次 formation 事件（认罪悔改=破除羞耻/骄傲循环，导向成长）
  - 返回一节「赦免的确据」经文
与「偶像监测」天然成对：看见 → 认罪 → 领受赦免 → 重新把神放在中心。
"""
from __future__ import annotations

import random
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/confession", tags=["confession"])
_state: Dict[str, Any] = {}

ASSURANCE = [
    {"ref": "约一1:9", "text": "我们若认自己的罪，神是信实的，是公义的，必要赦免我们的罪，洗净我们一切的不义。"},
    {"ref": "诗103:12", "text": "东离西有多远，他叫我们的过犯离我们也有多远。"},
    {"ref": "赛1:18", "text": "你们的罪虽像朱红，必变成雪白；虽红如丹颜，必白如羊毛。"},
    {"ref": "弥7:19", "text": "必再怜悯我们，将我们的罪孽踏在脚下，又将我们的一切罪投于深海。"},
    {"ref": "罗8:1", "text": "如今，那些在基督耶稣里的就不定罪了。"},
    {"ref": "诗32:5", "text": "我向你陈明我的罪，不隐瞒我的恶……你就赦免我的罪恶。"},
]


def init_confession_router(*, get_session_user) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/record")
def record(request: Request) -> dict:
    user = _require_user(request)
    try:
        from formation_bridge import record_formation
        record_formation(user.get("id"), ["growth"], loop_broken=True,
                         reflection_active=True, emotional_intensity=4.0,
                         decision_category="confession")
    except Exception:
        pass
    return {"ok": True, "scripture": random.choice(ASSURANCE)}
