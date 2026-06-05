"""
多教会 SaaS 数据隔离 — church router.

Endpoints (prefix /api/church):
  GET  /api/church/me               — 我所在的教会信息（含 join_code 仅 owner/admin 可见）
  POST /api/church/create           — 创建教会（无教会者才可建）
  POST /api/church/join             — 凭邀请码加入教会（无教会者才可加入）
  GET  /api/church/members          — 教会成员列表（须有教会）
  POST /api/church/regenerate-code  — 重新生成邀请码（仅 owner/admin）
  POST /api/church/leave            — 退出教会（owner 禁止）

设计注记
--------
* 用户同一时刻最多属于一个教会（church_members.email UNIQUE）
* 邀请码字符集与 voice.py 完全一致，去掉易混淆字符
* church_id 缓存60s，写操作后调 invalidate_church_cache
"""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/church", tags=["church"])

_state: dict[str, Any] = {}

# 邀请码字符集（去掉易混淆字符 0/O/1/I/l）
_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def init_church_router(
    *, get_db, release_db, get_session_user, sanitize_text, to_shanghai_iso=None
) -> None:
    _state.update(
        get_db=get_db,
        release_db=release_db,
        get_session_user=get_session_user,
        sanitize_text=sanitize_text,
        to_shanghai_iso=to_shanghai_iso or (lambda dt: dt.isoformat() if dt else None),
    )
    _ensure_tables()


# ===========================================================================
# 幂等建表（镜像 migration 0041；CI migration 仍是权威来源）
# ===========================================================================
_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS churches (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(120) NOT NULL,
    slug         VARCHAR(64),
    owner_email  VARCHAR(255) NOT NULL DEFAULT '',
    join_code    VARCHAR(12)  NOT NULL UNIQUE,
    is_default   BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_churches_default ON churches(is_default) WHERE is_default = TRUE;
CREATE TABLE IF NOT EXISTS church_members (
    church_id  INTEGER      NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
    email      VARCHAR(255) NOT NULL UNIQUE,
    role       VARCHAR(20)  NOT NULL DEFAULT 'member',
    joined_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (church_id, email)
);
CREATE INDEX IF NOT EXISTS idx_church_members_church ON church_members(church_id);
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS church_id INTEGER;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE prayers ADD COLUMN IF NOT EXISTS church_id INTEGER;
ALTER TABLE prayers ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE voice_groups ADD COLUMN IF NOT EXISTS church_id INTEGER;
"""


def _ensure_tables() -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(_TABLES_SQL)
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[church] ensure_tables warning: {exc}", flush=True)
    finally:
        _state["release_db"](conn)


# ===========================================================================
# 辅助
# ===========================================================================
def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def _gen_join_code(cur) -> str:
    """生成 churches 表中未占用的邀请码。"""
    for _ in range(12):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        cur.execute("SELECT 1 FROM churches WHERE join_code=%s", (code,))
        if cur.fetchone() is None:
            return code
    # 极低概率回退到更长的码
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(10))


def _get_my_church(cur, email: str) -> dict | None:
    """返回该用户的教会行 + 成员数，或 None。"""
    cur.execute(
        "SELECT cm.church_id, cm.role, c.name, c.join_code, c.owner_email, c.is_active "
        "FROM church_members cm JOIN churches c ON c.id = cm.church_id "
        "WHERE cm.email=%s",
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return None
    cid, role, name, join_code, owner_email, is_active = row
    cur.execute("SELECT COUNT(*) FROM church_members WHERE church_id=%s", (cid,))
    member_count = cur.fetchone()[0]
    return {
        "id": cid,
        "name": name,
        "role": role,
        "member_count": member_count,
        "is_active": is_active,
        # join_code 仅 owner/admin 可见
        "join_code": join_code if role in ("owner", "admin") else None,
    }


def _invalidate(email: str) -> None:
    try:
        from core.deps import invalidate_church_cache
    except ImportError:
        try:
            from backend.core.deps import invalidate_church_cache
        except ImportError:
            return
    invalidate_church_cache(email)


# ===========================================================================
# Endpoints
# ===========================================================================
@router.get("/me")
def church_me(request: Request) -> dict:
    """返回我所在的教会信息，未加入任何教会则 church=null。"""
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            church = _get_my_church(cur, me)
        return {"ok": True, "church": church}
    finally:
        _state["release_db"](conn)


class CreateChurchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.post("/create")
def create_church(request: Request, body: CreateChurchRequest) -> dict:
    """创建新教会。已有教会者返回 409。"""
    me = _require_user(request)["email"]
    name = _state["sanitize_text"](body.name.strip())
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # 检查是否已有教会
            cur.execute("SELECT 1 FROM church_members WHERE email=%s", (me,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="你已经属于一个教会，无法再创建")
            code = _gen_join_code(cur)
            cur.execute(
                "INSERT INTO churches (name, owner_email, join_code) "
                "VALUES (%s, %s, %s) RETURNING id",
                (name, me, code),
            )
            cid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO church_members (church_id, email, role) VALUES (%s, %s, 'owner')",
                (cid, me),
            )
            conn.commit()
        _invalidate(me)
        return {"ok": True, "church_id": cid, "join_code": code}
    finally:
        _state["release_db"](conn)


class JoinChurchRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


@router.post("/join")
def join_church(request: Request, body: JoinChurchRequest) -> dict:
    """凭邀请码加入教会。已有教会者返回 409。"""
    me = _require_user(request)["email"]
    code = body.code.strip().upper()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM church_members WHERE email=%s", (me,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="你已经属于一个教会")
            cur.execute(
                "SELECT id FROM churches WHERE join_code=%s AND is_active=TRUE",
                (code,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="邀请码无效")
            cid = row[0]
            cur.execute(
                "INSERT INTO church_members (church_id, email, role) "
                "VALUES (%s, %s, 'member') ON CONFLICT (email) DO NOTHING",
                (cid, me),
            )
            conn.commit()
        _invalidate(me)
        return {"ok": True, "church_id": cid}
    finally:
        _state["release_db"](conn)


@router.get("/members")
def list_members(request: Request) -> dict:
    """返回教会成员列表（须有教会）。"""
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT church_id FROM church_members WHERE email=%s", (me,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=403, detail="你尚未加入任何教会")
            cid = row[0]
            cur.execute(
                "SELECT cm.email, cm.role, cm.joined_at, u.nickname, u.avatar "
                "FROM church_members cm LEFT JOIN users u ON u.email = cm.email "
                "WHERE cm.church_id=%s "
                "ORDER BY (cm.role='owner') DESC, (cm.role='admin') DESC, cm.joined_at ASC",
                (cid,),
            )
            members = [
                {
                    "email": r[0],
                    "role": r[1],
                    "joined_at": _state["to_shanghai_iso"](r[2]),
                    "nickname": r[3] or r[0].split("@")[0],
                    "avatar": r[4] or "",
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "members": members}
    finally:
        _state["release_db"](conn)


@router.post("/regenerate-code")
def regenerate_code(request: Request) -> dict:
    """重新生成邀请码（仅 owner/admin）。"""
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT church_id, role FROM church_members WHERE email=%s", (me,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=403, detail="你尚未加入任何教会")
            cid, role = row
            if role not in ("owner", "admin"):
                raise HTTPException(status_code=403, detail="只有管理员可以重置邀请码")
            new_code = _gen_join_code(cur)
            cur.execute(
                "UPDATE churches SET join_code=%s WHERE id=%s",
                (new_code, cid),
            )
            conn.commit()
        return {"ok": True, "join_code": new_code}
    finally:
        _state["release_db"](conn)


@router.post("/leave")
def leave_church(request: Request) -> dict:
    """退出教会。owner 禁止退出（需先转让或解散教会）。"""
    me = _require_user(request)["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT church_id, role FROM church_members WHERE email=%s", (me,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="你尚未加入任何教会")
            cid, role = row
            if role == "owner":
                raise HTTPException(status_code=400, detail="教会创始人无法退出，请先转让或解散教会")
            cur.execute(
                "DELETE FROM church_members WHERE church_id=%s AND email=%s",
                (cid, me),
            )
            conn.commit()
        _invalidate(me)
        return {"ok": True}
    finally:
        _state["release_db"](conn)
