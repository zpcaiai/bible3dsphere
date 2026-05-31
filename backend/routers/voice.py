"""
语音群组 (Voice Rooms) — LiveKit-backed group voice calling.

Provides, all under /api:
  • GET    /api/voice/config              — 前端探测语音功能是否已配置 (LiveKit 是否就绪)
  • GET    /api/voice/groups              — 我所在的语音群列表
  • POST   /api/voice/groups              — 建群 (创建者自动成为 owner 成员)
  • POST   /api/voice/groups/join         — 凭邀请码加入群
  • GET    /api/voice/groups/{gid}/members— 群成员名单
  • POST   /api/voice/groups/{gid}/token  — 签发 LiveKit 进房 JWT (校验成员资格)
  • POST   /api/voice/groups/{gid}/leave  — 退群
  • DELETE /api/voice/groups/{gid}        — 解散群 (仅 owner)

设计要点
--------
* 媒体层用 LiveKit 托管 SFU（Zoom 级音质：Opus + RED 抗丢包 + Krisp AI 降噪 +
  服务端回声消除 + 自带 TURN）。本服务**不转发音频**，只做成员管理 + 签发进房令牌，
  因此零媒体成本、可扩到多人。
* LiveKit 房间名 = "vg_<group_id>"，参与者身份 identity = email，name = 昵称。
* 令牌用 PyJWT 按 LiveKit 的 access-token 规范直接签发 (HS256, video grant)，
  无需额外引入 livekit server SDK。

环境变量
--------
  LIVEKIT_URL        wss://<project>.livekit.cloud   (前端连接地址)
  LIVEKIT_API_KEY    LiveKit 项目 API Key
  LIVEKIT_API_SECRET LiveKit 项目 API Secret
  LIVEKIT_TOKEN_TTL  进房令牌有效期秒数 (默认 21600 = 6h)
未配置 KEY/SECRET 时，/voice/config 返回 enabled=false，前端给出引导提示。
"""
from __future__ import annotations

import os
import time
import uuid
import secrets
from typing import Any

import jwt  # PyJWT —— 已在 backend/requirements.txt
from fastapi import APIRouter, HTTPException, Path, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/voice", tags=["voice"])

_state: dict[str, Any] = {}

# 邀请码字符集（去掉易混淆字符 0/O/1/I/l）
_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def init_voice_router(*, get_db, release_db, get_session_user, to_shanghai_iso=None) -> None:
    _state.update(
        get_db=get_db,
        release_db=release_db,
        get_session_user=get_session_user,
        to_shanghai_iso=to_shanghai_iso or (lambda dt: dt.isoformat() if dt else None),
    )
    _ensure_tables()


# ===========================================================================
# 幂等建表 (镜像 migration 0020；CI migration 仍是权威来源)
# ===========================================================================
_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS voice_groups (
    id           VARCHAR(64)  PRIMARY KEY,
    name         VARCHAR(120) NOT NULL DEFAULT '语音祷告群',
    owner        VARCHAR(255) NOT NULL,
    join_code    VARCHAR(12)  NOT NULL UNIQUE,
    max_members  INTEGER      NOT NULL DEFAULT 10,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    archived_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_voice_groups_owner  ON voice_groups(owner);
CREATE INDEX IF NOT EXISTS idx_voice_groups_active ON voice_groups(is_active) WHERE is_active = TRUE;
CREATE TABLE IF NOT EXISTS voice_group_members (
    group_id   VARCHAR(64)  NOT NULL,
    email      VARCHAR(255) NOT NULL,
    role       VARCHAR(20)  NOT NULL DEFAULT 'member',
    joined_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, email)
);
CREATE INDEX IF NOT EXISTS idx_voice_group_members_email ON voice_group_members(email);
CREATE INDEX IF NOT EXISTS idx_voice_group_members_group ON voice_group_members(group_id);
"""


def _ensure_tables() -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(_TABLES_SQL)
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[voice] ensure_tables warning: {exc}", flush=True)
    finally:
        _state["release_db"](conn)


# ===========================================================================
# LiveKit 配置 + 令牌签发
# ===========================================================================
def _livekit_cfg() -> dict:
    return {
        "url": os.environ.get("LIVEKIT_URL", "").strip(),
        "key": os.environ.get("LIVEKIT_API_KEY", "").strip(),
        "secret": os.environ.get("LIVEKIT_API_SECRET", "").strip(),
        "ttl": int(os.environ.get("LIVEKIT_TOKEN_TTL", "21600")),
    }


def _livekit_enabled(cfg: dict | None = None) -> bool:
    cfg = cfg or _livekit_cfg()
    return bool(cfg["url"] and cfg["key"] and cfg["secret"])


def _mint_livekit_token(identity: str, name: str, room: str, cfg: dict,
                        can_publish: bool = True) -> str:
    """按 LiveKit access-token 规范用 HS256 签发 JWT。

    Claims 结构 (LiveKit 约定):
      iss = API Key, sub = identity, name = 显示名, nbf/iat/exp = 时间窗,
      video = { room, roomJoin, canPublish, canSubscribe, canPublishData }
    """
    now = int(time.time())
    claims = {
        "iss": cfg["key"],
        "sub": identity,
        "name": name,
        "nbf": now,
        "iat": now,
        "exp": now + cfg["ttl"],
        "video": {
            "room": room,
            "roomJoin": True,
            "canPublish": can_publish,
            "canSubscribe": True,
            "canPublishData": True,
        },
    }
    token = jwt.encode(claims, cfg["secret"], algorithm="HS256")
    # PyJWT >= 2 returns str
    return token if isinstance(token, str) else token.decode("utf-8")


# ===========================================================================
# 辅助
# ===========================================================================
def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def _gen_join_code(cur) -> str:
    """生成未占用的邀请码。"""
    for _ in range(12):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        cur.execute("SELECT 1 FROM voice_groups WHERE join_code=%s", (code,))
        if cur.fetchone() is None:
            return code
    # 极低概率回退到更长的码
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(10))


def _nickname_of(cur, email: str) -> str:
    cur.execute("SELECT nickname FROM users WHERE email=%s", (email,))
    row = cur.fetchone()
    return (row[0] if row and row[0] else email.split("@")[0])


def _group_summary(cur, gid: str, me: str) -> dict | None:
    cur.execute(
        "SELECT id, name, owner, join_code, max_members, is_active, created_at "
        "FROM voice_groups WHERE id=%s",
        (gid,),
    )
    g = cur.fetchone()
    if not g or not g[5]:
        return None
    cur.execute("SELECT COUNT(*) FROM voice_group_members WHERE group_id=%s", (gid,))
    member_count = cur.fetchone()[0]
    return {
        "id": g[0],
        "name": g[1],
        "owner": g[2],
        "join_code": g[3],
        "max_members": g[4],
        "member_count": member_count,
        "is_owner": g[2] == me,
        "room": f"vg_{g[0]}",
        "created_at": _state["to_shanghai_iso"](g[6]),
    }


# ===========================================================================
# Endpoints
# ===========================================================================
@router.get("/config")
def voice_config(request: Request) -> dict:
    """前端探测语音功能是否就绪。enabled=false 时引导管理员配置 LiveKit。"""
    cfg = _livekit_cfg()
    return {
        "ok": True,
        "enabled": _livekit_enabled(cfg),
        "url": cfg["url"] if _livekit_enabled(cfg) else "",
        "provider": "livekit",
    }


@router.get("/groups")
def list_groups(request: Request) -> dict:
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT group_id FROM voice_group_members WHERE email=%s ORDER BY joined_at DESC",
                (me,),
            )
            gids = [r[0] for r in cur.fetchall()]
            groups = [s for gid in gids if (s := _group_summary(cur, gid, me))]
        return {"ok": True, "groups": groups, "enabled": _livekit_enabled()}
    finally:
        _state["release_db"](conn)


class CreateGroupRequest(BaseModel):
    name: str = Field(default="语音祷告群", min_length=1, max_length=120)
    max_members: int = Field(default=10, ge=2, le=50)


@router.post("/groups")
def create_group(request: Request, body: CreateGroupRequest) -> dict:
    me = _require_user(request)["email"]
    gid = uuid.uuid4().hex[:16]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            code = _gen_join_code(cur)
            cur.execute(
                "INSERT INTO voice_groups (id, name, owner, join_code, max_members) "
                "VALUES (%s, %s, %s, %s, %s)",
                (gid, body.name.strip(), me, code, body.max_members),
            )
            cur.execute(
                "INSERT INTO voice_group_members (group_id, email, role) "
                "VALUES (%s, %s, 'owner') ON CONFLICT DO NOTHING",
                (gid, me),
            )
            conn.commit()
            summary = _group_summary(cur, gid, me)
        return {"ok": True, "group": summary}
    finally:
        _state["release_db"](conn)


class JoinGroupRequest(BaseModel):
    join_code: str = Field(min_length=4, max_length=12)


@router.post("/groups/join")
def join_group(request: Request, body: JoinGroupRequest) -> dict:
    me = _require_user(request)["email"]
    code = body.join_code.strip().upper()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, max_members FROM voice_groups "
                "WHERE join_code=%s AND is_active=TRUE",
                (code,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="邀请码无效或群已解散")
            gid, max_members = row
            cur.execute("SELECT 1 FROM voice_group_members WHERE group_id=%s AND email=%s", (gid, me))
            already = cur.fetchone() is not None
            if not already:
                cur.execute("SELECT COUNT(*) FROM voice_group_members WHERE group_id=%s", (gid,))
                if cur.fetchone()[0] >= max_members:
                    raise HTTPException(status_code=409, detail="该群人数已满")
                cur.execute(
                    "INSERT INTO voice_group_members (group_id, email, role) "
                    "VALUES (%s, %s, 'member') ON CONFLICT DO NOTHING",
                    (gid, me),
                )
                conn.commit()
            summary = _group_summary(cur, gid, me)
        return {"ok": True, "group": summary, "already_member": already}
    finally:
        _state["release_db"](conn)


@router.get("/groups/{gid}/members")
def group_members(request: Request, gid: str = Path(...)) -> dict:
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM voice_group_members WHERE group_id=%s AND email=%s", (gid, me))
            if cur.fetchone() is None:
                raise HTTPException(status_code=403, detail="你不在该群中")
            cur.execute(
                "SELECT m.email, m.role, m.joined_at, u.nickname, u.avatar "
                "FROM voice_group_members m LEFT JOIN users u ON u.email = m.email "
                "WHERE m.group_id=%s ORDER BY (m.role='owner') DESC, m.joined_at ASC",
                (gid,),
            )
            members = [{
                "email": r[0],
                "role": r[1],
                "nickname": (r[3] or r[0].split("@")[0]),
                "avatar": r[4] or "",
                "is_me": r[0] == me,
                "joined_at": _state["to_shanghai_iso"](r[2]),
            } for r in cur.fetchall()]
        return {"ok": True, "members": members}
    finally:
        _state["release_db"](conn)


@router.post("/groups/{gid}/token")
def issue_token(request: Request, gid: str = Path(...)) -> dict:
    """签发 LiveKit 进房令牌。仅群成员可获取。"""
    me = _require_user(request)["email"]
    cfg = _livekit_cfg()
    if not _livekit_enabled(cfg):
        raise HTTPException(status_code=503, detail="语音服务尚未配置 (缺少 LiveKit 凭证)")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM voice_groups WHERE id=%s AND is_active=TRUE", (gid,)
            )
            grow = cur.fetchone()
            if not grow:
                raise HTTPException(status_code=404, detail="群不存在或已解散")
            cur.execute("SELECT 1 FROM voice_group_members WHERE group_id=%s AND email=%s", (gid, me))
            if cur.fetchone() is None:
                raise HTTPException(status_code=403, detail="你不在该群中")
            display_name = _nickname_of(cur, me)
            group_name = grow[0]
    finally:
        _state["release_db"](conn)

    room = f"vg_{gid}"
    token = _mint_livekit_token(identity=me, name=display_name, room=room, cfg=cfg)
    return {
        "ok": True,
        "url": cfg["url"],
        "token": token,
        "room": room,
        "identity": me,
        "name": display_name,
        "group_name": group_name,
    }


@router.post("/groups/{gid}/leave")
def leave_group(request: Request, gid: str = Path(...)) -> dict:
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT owner FROM voice_groups WHERE id=%s", (gid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="群不存在")
            is_owner = row[0] == me
            cur.execute(
                "DELETE FROM voice_group_members WHERE group_id=%s AND email=%s", (gid, me)
            )
            if is_owner:
                # 群主退群 -> 解散整个群
                cur.execute(
                    "UPDATE voice_groups SET is_active=FALSE, archived_at=NOW() WHERE id=%s",
                    (gid,),
                )
                cur.execute("DELETE FROM voice_group_members WHERE group_id=%s", (gid,))
            conn.commit()
        return {"ok": True, "disbanded": is_owner}
    finally:
        _state["release_db"](conn)


@router.delete("/groups/{gid}")
def disband_group(request: Request, gid: str = Path(...)) -> dict:
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT owner FROM voice_groups WHERE id=%s", (gid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="群不存在")
            if row[0] != me:
                raise HTTPException(status_code=403, detail="只有群主可以解散群")
            cur.execute(
                "UPDATE voice_groups SET is_active=FALSE, archived_at=NOW() WHERE id=%s", (gid,)
            )
            cur.execute("DELETE FROM voice_group_members WHERE group_id=%s", (gid,))
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)
