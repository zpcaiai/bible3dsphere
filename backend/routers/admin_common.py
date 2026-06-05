"""
admin_common.py — 管理端共享状态、鉴权与审计辅助。

被 admin_users / admin_content / admin_catalog 共同 import；
由 init_admin_router(**deps) 一次性注入依赖。
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, Request

# ─────────────────────────────────────────────────────────────────────────────
# 共享状态
# ─────────────────────────────────────────────────────────────────────────────
_state: dict[str, Any] = {}


def init_admin_router(
    *,
    get_db,
    release_db,
    get_session_user,
    is_admin,
    invalidate_admin_cache,
    revoke_user_sessions,
    sanitize_text,
    to_shanghai_iso,
    hash_password,
) -> None:
    """一次性注入所有依赖（admin_users/content/catalog 共享此 _state）。"""
    _state.update(
        get_db=get_db,
        release_db=release_db,
        get_session_user=get_session_user,
        is_admin=is_admin,
        invalidate_admin_cache=invalidate_admin_cache,
        revoke_user_sessions=revoke_user_sessions,
        sanitize_text=sanitize_text,
        to_shanghai_iso=to_shanghai_iso,
        hash_password=hash_password,
    )
    _ensure_tables()


# ─────────────────────────────────────────────────────────────────────────────
# 幂等建表（镜像 0042；CI migration 仍是权威来源）
# ─────────────────────────────────────────────────────────────────────────────
_TABLES_SQL = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin  BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_reason TEXT DEFAULT '';

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id           BIGSERIAL    PRIMARY KEY,
    admin_email  VARCHAR(255) NOT NULL,
    action       VARCHAR(60)  NOT NULL,
    target_type  VARCHAR(40)  NOT NULL DEFAULT '',
    target_id    TEXT         NOT NULL DEFAULT '',
    detail       JSONB        NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_target  ON admin_audit_log(target_type, target_id);

ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS pinned_at TIMESTAMPTZ;
"""


def _ensure_tables() -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            for stmt in _TABLES_SQL.strip().split(";\n"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        cur.execute(stmt)
                    except Exception as exc:
                        print(f"[admin_common] ensure_tables warning: {exc}", flush=True)
                        conn.rollback()
        conn.commit()
    except Exception as exc:
        print(f"[admin_common] ensure_tables error: {exc}", flush=True)
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 鉴权
# ─────────────────────────────────────────────────────────────────────────────
def require_admin(request: Request) -> dict:
    """返回已登录的管理员 user dict；否则抛 401/403。"""
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    if not _state["is_admin"](user["email"]):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    return user


# ─────────────────────────────────────────────────────────────────────────────
# 审计写入（与业务在同一事务中调用）
# ─────────────────────────────────────────────────────────────────────────────
def audit(
    cur,
    admin_email: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    detail: dict | None = None,
) -> None:
    """向 admin_audit_log 写一条审计记录（须在同一事务 cursor 中调用）。"""
    try:
        from psycopg2.extras import Json as _Json
        detail_val = _Json(detail or {})
    except Exception:
        detail_val = json.dumps(detail or {})
    cur.execute(
        """
        INSERT INTO admin_audit_log
            (admin_email, action, target_type, target_id, detail)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (admin_email, action, target_type, str(target_id), detail_val),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 通用分页辅助
# ─────────────────────────────────────────────────────────────────────────────
def paginate(page: int, page_size: int) -> tuple[int, int]:
    """返回 (limit, offset)；page_size 最大 100。"""
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    return page_size, (page - 1) * page_size
