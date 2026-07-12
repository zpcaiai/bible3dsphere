"""FCM HTTP v1 发送器 — 移动端（Android/iOS）设备推送。

配置：环境变量 ``FCM_SERVICE_ACCOUNT_JSON`` — Firebase 服务账号 JSON 的
**文件路径** 或 **JSON 字符串**（须含 project_id / client_email / private_key）。
未配置时本模块所有函数安全 no-op（仅 debug 日志），不影响应用其余部分。

实现：PyJWT(RS256, cryptography) 自签 OAuth2 JWT → 换取 access token（进程内缓存，
到期前 60s 自动重签）→ POST https://fcm.googleapis.com/v1/projects/{project_id}/messages:send。
不引入任何新第三方依赖（PyJWT/cryptography/httpx 均已在 requirements 中）。

数据面：token 存于 fcm_device_tokens（migrations/0209）。send_to_user() 需要注入
get_db/release_db（与 routers/push.py 相同的 DB 访问模式）；FCM 返回 404 或
UNREGISTERED 的 token 会被标记 revoked_at，之后不再发送。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("fcm")

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
_DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"

_lock = threading.Lock()
# sa_loaded: 服务账号已尝试加载（含失败）；token/token_exp: access token 缓存
_cache: Dict[str, Any] = {"sa": None, "sa_loaded": False, "token": None, "token_exp": 0.0}


def _reset_cache() -> None:
    """清空服务账号与 access token 缓存（配置变更/测试用）。"""
    with _lock:
        _cache.update({"sa": None, "sa_loaded": False, "token": None, "token_exp": 0.0})


def _load_service_account() -> Optional[dict]:
    with _lock:
        if _cache["sa_loaded"]:
            return _cache["sa"]
        _cache["sa_loaded"] = True
        raw = os.environ.get("FCM_SERVICE_ACCOUNT_JSON", "").strip()
        if not raw:
            logger.debug("FCM_SERVICE_ACCOUNT_JSON not set — FCM sender disabled (no-op)")
            return None
        try:
            if raw.startswith("{"):
                sa = json.loads(raw)
            else:
                with open(raw, "r", encoding="utf-8") as f:
                    sa = json.load(f)
            if not (sa.get("project_id") and sa.get("client_email") and sa.get("private_key")):
                raise ValueError("service account json missing project_id/client_email/private_key")
            _cache["sa"] = sa
            logger.info("FCM sender configured for project %s", sa["project_id"])
            return sa
        except Exception as exc:
            logger.warning("FCM service account load failed (sender disabled): %s", exc)
            _cache["sa"] = None
            return None


def is_configured() -> bool:
    """FCM 是否已配置（服务账号可用）。"""
    return _load_service_account() is not None


def _get_access_token() -> Optional[str]:
    """自签 JWT 换 OAuth2 access token，带进程内缓存（到期前 60s 重签）。"""
    sa = _load_service_account()
    if not sa:
        return None
    with _lock:
        if _cache["token"] and _cache["token_exp"] - 60 > time.time():
            return _cache["token"]
    try:
        import jwt  # PyJWT（requirements 已有）
        import httpx

        now = int(time.time())
        token_uri = sa.get("token_uri") or _DEFAULT_TOKEN_URI
        assertion = jwt.encode(
            {"iss": sa["client_email"], "scope": _SCOPE, "aud": token_uri,
             "iat": now, "exp": now + 3600},
            sa["private_key"], algorithm="RS256",
        )
        with httpx.Client(timeout=15) as client:
            resp = client.post(token_uri, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            })
        resp.raise_for_status()
        data = resp.json()
        access = data.get("access_token")
        if not access:
            raise ValueError("no access_token in oauth response")
        with _lock:
            _cache["token"] = access
            _cache["token_exp"] = time.time() + int(data.get("expires_in") or 3600)
        return access
    except Exception as exc:
        logger.warning("FCM access token exchange failed: %s", exc)
        return None


def send_to_token(token: str, title: str, body: str, data: Optional[dict] = None) -> str:
    """给单个设备 token 发送。返回 'ok' | 'unregistered' | 'error' | 'skipped'。

    'unregistered'：FCM 返回 404 或错误体含 UNREGISTERED（token 已失效，调用方应标记 revoked）。
    未配置时返回 'skipped'（no-op）。"""
    sa = _load_service_account()
    if not sa:
        logger.debug("FCM not configured — send_to_token no-op")
        return "skipped"
    access = _get_access_token()
    if not access:
        return "error"
    message = {
        "message": {
            "token": token,
            "notification": {"title": str(title or "")[:200], "body": str(body or "")[:500]},
            "data": {str(k): str(v) for k, v in (data or {}).items()},
        }
    }
    try:
        import httpx
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                _FCM_SEND_URL.format(project_id=sa["project_id"]),
                headers={"Authorization": f"Bearer {access}",
                         "Content-Type": "application/json"},
                json=message,
            )
        if resp.status_code == 200:
            return "ok"
        text = resp.text or ""
        if resp.status_code == 404 or "UNREGISTERED" in text:
            return "unregistered"
        if resp.status_code == 401:
            # access token 失效：清缓存，下次调用重签
            with _lock:
                _cache["token"] = None
                _cache["token_exp"] = 0.0
        logger.warning("FCM send failed HTTP %s: %s", resp.status_code, text[:200])
        return "error"
    except Exception as exc:
        logger.warning("FCM send error: %s", exc)
        return "error"


def send_to_user(email: str, title: str, body: str, data: Optional[dict] = None,
                 *, get_db=None, release_db=None) -> dict:
    """给用户全部有效（revoked_at IS NULL）token 群发。

    返回 {"configured", "sent", "revoked", "errors"}；未配置 FCM、缺 email 或缺
    get_db/release_db 时安全 no-op（sent=0）。404/UNREGISTERED 的 token 标记 revoked_at。"""
    out = {"configured": False, "sent": 0, "revoked": 0, "errors": 0}
    if not is_configured():
        logger.debug("FCM not configured — send_to_user(%s) no-op", email)
        return out
    out["configured"] = True
    if not email or get_db is None or release_db is None:
        logger.debug("FCM send_to_user missing email or db accessors — no-op")
        return out

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT token FROM fcm_device_tokens "
                "WHERE user_email=%s AND revoked_at IS NULL",
                (email,),
            )
            tokens = [r[0] for r in cur.fetchall()]
    finally:
        release_db(conn)
    if not tokens:
        return out

    dead = []
    for tk in tokens:
        res = send_to_token(tk, title, body, data)
        if res == "ok":
            out["sent"] += 1
        elif res == "unregistered":
            dead.append(tk)
        elif res == "error":
            out["errors"] += 1

    if dead:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE fcm_device_tokens SET revoked_at=NOW() "
                    "WHERE token IN %s AND revoked_at IS NULL",
                    (tuple(dead),),
                )
                conn.commit()
            out["revoked"] = len(dead)
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.warning("FCM revoke update failed: %s", exc)
        finally:
            release_db(conn)
    return out
