"""邮箱注册/登录/重置密码 + 会话查询/登出（/api/auth/me、/api/auth/logout、/api/auth/email/*）—
从 main.py 逐字搬移（路径不变，无 prefix）。

会话签发、验证码存储、邮件发送、审计等安全辅助仍定义在 main.py，通过
init_main_extracted_auth_email() 注入引用；_CODE_STORE/_SESSION_STORE 等可变全局
注入的是同一 dict/Lock 对象，与 main（微信 OAuth 等未拆路由）共享状态。
limiter 与 main.py 一样直接取自 core.ratelimit（同一实例，装饰期即需要）。
"""
import asyncio
import hmac
import random
import time
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

try:
    from backend.core.security import (
        EMAIL_RE,
        hash_password as _hash_password,
        verify_password as _verify_password,
    )
except ImportError:
    from core.security import (
        EMAIL_RE,
        hash_password as _hash_password,
        verify_password as _verify_password,
    )

from core.ratelimit import limiter

router = APIRouter()

# ── main.py 注入的依赖（导入期为占位值，仅在请求期被使用）──
_get_db = None
_release_db = None
_get_session_user = None
_get_user = None
_get_user_by_email = None
_create_user = None
_make_session = None
_set_session_cookie = None
_clear_session_cookie = None
_send_email = None
_generate_code = None
_security_audit = None
_CODE_STORE = None       # dict，与 main 共享同一对象
_CODE_LOCK = None        # threading.Lock，与 main 共享
_SESSION_STORE = None    # dict，与 main 共享
_SESSION_LOCK = None     # threading.Lock，与 main 共享
SESSION_COOKIE_NAME = ''
SMTP_HOST = ''
SMTP_PORT = 0
SMTP_USER = ''
SMTP_PASS = ''
SENDGRID_API_KEY = ''
RESEND_API_KEY = ''
_ALLOW_DEV_AUTH_CODE = False
CODE_TTL_SECONDS = 600


def init_main_extracted_auth_email(*, get_db, release_db, get_session_user,
                                   get_user, get_user_by_email, create_user, make_session,
                                   set_session_cookie, clear_session_cookie,
                                   send_email, generate_code, security_audit,
                                   code_store, code_lock, session_store, session_lock,
                                   session_cookie_name, smtp_host, smtp_port, smtp_user, smtp_pass,
                                   sendgrid_api_key, resend_api_key,
                                   allow_dev_auth_code, code_ttl_seconds) -> None:
    global _get_db, _release_db, _get_session_user
    global _get_user, _get_user_by_email, _create_user, _make_session
    global _set_session_cookie, _clear_session_cookie, _send_email, _generate_code, _security_audit
    global _CODE_STORE, _CODE_LOCK, _SESSION_STORE, _SESSION_LOCK
    global SESSION_COOKIE_NAME, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
    global SENDGRID_API_KEY, RESEND_API_KEY, _ALLOW_DEV_AUTH_CODE, CODE_TTL_SECONDS
    _get_db = get_db
    _release_db = release_db
    _get_session_user = get_session_user
    _get_user = get_user
    _get_user_by_email = get_user_by_email
    _create_user = create_user
    _make_session = make_session
    _set_session_cookie = set_session_cookie
    _clear_session_cookie = clear_session_cookie
    _send_email = send_email
    _generate_code = generate_code
    _security_audit = security_audit
    _CODE_STORE = code_store
    _CODE_LOCK = code_lock
    _SESSION_STORE = session_store
    _SESSION_LOCK = session_lock
    SESSION_COOKIE_NAME = session_cookie_name
    SMTP_HOST = smtp_host
    SMTP_PORT = smtp_port
    SMTP_USER = smtp_user
    SMTP_PASS = smtp_pass
    SENDGRID_API_KEY = sendgrid_api_key
    RESEND_API_KEY = resend_api_key
    _ALLOW_DEV_AUTH_CODE = allow_dev_auth_code
    CODE_TTL_SECONDS = code_ttl_seconds


class EmailSendCodeRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class EmailRegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(default='', max_length=64)


class EmailLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


@router.get('/api/auth/me')
def auth_me(request: Request):
    """Verify session token, return user info."""
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid or expired session')
    return {'ok': True, 'user': user}


@router.post('/api/auth/logout')
def auth_logout(request: Request, response: Response):
    """Invalidate session token."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header[7:].strip() if auth_header.startswith('Bearer ') else request.cookies.get(SESSION_COOKIE_NAME, '')
    if token:
        with _SESSION_LOCK:
            _SESSION_STORE.pop(token, None)
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM user_tokens WHERE token = %s', (token,))
                conn.commit()
        finally:
            _release_db(conn)
    _clear_session_cookie(response, request)
    return {'ok': True}


# ── 邮件服务就绪状态 ────────────────────────────────────────────────────────
#
# 这个判断原本内联在两个发码路由里，各写一遍。抽出来有三个原因：
#   1. 两处必须永远一致——否则会出现「能注册但重置不了密码」这种半瘫状态；
#   2. 状态需要能被主动查询，而不是只有点了按钮的用户才撞见 503；
#   3. 启动时要能大声说出来，否则注册漏斗可以对所有人断掉而无人察觉
#      （这正是 holiness.uk 上真实发生过的事）。

def _email_service_ready() -> bool:
    """是否配置了任一可用的发信通道。

    注意 SMTP 必须 USER 与 PASS 成对：只配一个等于没配，
    这是个很容易踩的坑（只设 SMTP_HOST 也不算数）。
    """
    return bool(SENDGRID_API_KEY) or bool(RESEND_API_KEY) or (bool(SMTP_USER) and bool(SMTP_PASS))


# 「请稍后重试」是误导——等多久都不会好，这需要运维配置环境变量。
EMAIL_SERVICE_DOWN_DETAIL = '邮箱验证服务当前不可用，暂时无法自助注册或重置密码。这不是你的问题，请联系管理员。'


@router.get('/api/auth/email/status')
def email_service_status() -> dict:
    """公开的自助注册可用性查询（登录页在渲染表单前就要知道）。

    只回布尔与面向用户的说明，不暴露用到了哪家服务商、更不暴露任何密钥。
    """
    ready = _email_service_ready()
    return {
        'ok': True,
        'email_service_ready': ready,
        # 本地/预发用 ALLOW_DEV_AUTH_CODE 时，验证码直接回给客户端，自助注册照样可走
        'self_register_enabled': ready or _ALLOW_DEV_AUTH_CODE,
        'message': '' if ready else EMAIL_SERVICE_DOWN_DETAIL,
    }


@router.post('/api/auth/email/send-code')
@limiter.limit('5/minute')  # 每 IP 每分钟最多 5 次发送请求
async def email_send_code(request: Request, payload: EmailSendCodeRequest):
    """Send a 6-digit verification code to the given email."""
    print(f'[auth] send-code request for email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Check if email already registered
    existing_user = _get_user_by_email(email)
    if existing_user:
        print(f'[auth] email already registered: {email}', flush=True)
        return {'ok': False, 'registered': True, 'message': '该邮箱已注册，请直接登录'}

    # Rate limit: one code per 60 seconds
    with _CODE_LOCK:
        existing = _CODE_STORE.get(email)
        if existing and existing['expires'] - 240 > time.time():
            raise HTTPException(status_code=429, detail='Please wait before requesting another code')

    code = f'{random.randint(0, 999999):06d}'
    expires = time.time() + 300  # 5 minutes
    with _CODE_LOCK:
        _CODE_STORE[email] = {'code': code, 'expires': expires}

    body = (
        f'您的属灵星球验证码：\n\n'
        f'  {code}\n\n'
        f'验证码 5 分钟内有效，请勿转发给他人。\n\n'
        f'Bible Emotion Sphere'
    )

    # If no email service is configured at all, show dev_code for local testing
    if not _email_service_ready():
        print(f'[auth][DEV] verification code for {email}: {code}', flush=True)
        # Only expose the code to the client in explicit local/dev mode; never in production.
        if _ALLOW_DEV_AUTH_CODE:
            return {'ok': True, 'dev_code': code}
        print('[auth][CONFIG] 注册被阻断：未配置任何发信通道'
              '（需 SENDGRID_API_KEY 或 RESEND_API_KEY 或 SMTP_USER+SMTP_PASS）', flush=True)
        raise HTTPException(status_code=503, detail=EMAIL_SERVICE_DOWN_DETAIL)

    try:
        await asyncio.to_thread(_send_email, email, '属灵星球 – 邮箱验证码', body)
        print(f'[auth] verification code sent to {email} via {SMTP_HOST}:{SMTP_PORT}', flush=True)
        return {'ok': True}
    except Exception as exc:
        import traceback
        # SECURITY: never return the verification code to the client on failure. Log server-side only.
        print(f'[auth] email send failed to {email}: {exc}', flush=True)
        print(traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail='验证码发送失败，请稍后重试') from exc


def _needs_bearer_token_in_body(request: Request) -> bool:
    """登录/注册的响应体里，要不要额外附带 session token。

    会话 token 的正路是 HttpOnly + SameSite=Lax 的 cookie：JS 读不到，XSS 也偷不走。
    但前端 fetch 用的是 `credentials: 'same-origin'`——一旦 API 部署在别的域名下
    （VITE_API_BASE 指向跨域后端），cookie 压根不会被发送，此时只剩 Bearer 一条路。

    此前是「一律返回 token」，于是同域部署也白白把凭据暴露在 JS 可读的响应体里；
    而 tests/test_auth.py 断言的正是「同域下 body 里不该有 token」。两边各自都成立，
    只是场景不同——所以按来源判断，而不是二选一：

      · 同源请求（无 Origin 头，或 Origin 与本站同源）→ 不返回 token，只发 cookie
      · 真正的跨域请求                                → 返回 token，让 Bearer 兜底

    判定取保守侧：Origin 或 Host 解析不出来时一律按同源处理（不返回 token）。
    宁可让某个古怪的跨域场景需要显式配置，也不要默认多暴露一份凭据。
    """
    origin = (request.headers.get('origin') or '').strip()
    if not origin:
        # 非 CORS 请求（同源导航、服务端调用、TestClient）根本不会带 Origin
        return False
    try:
        origin_host = urlsplit(origin).netloc.lower()
    except Exception:
        return False
    own_host = (request.headers.get('x-forwarded-host') or request.headers.get('host') or '').strip().lower()
    if not origin_host or not own_host:
        return False
    return origin_host != own_host


@router.post('/api/auth/email/register')
@limiter.limit('10/minute')  # 每 IP 每分钟最多 10 次注册尝试
def email_register(request: Request, response: Response, payload: EmailRegisterRequest):
    """Register with email + verification code + password."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] register attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_email'}, success=False)
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Verify code
    with _CODE_LOCK:
        entry = _CODE_STORE.get(email)
        if not entry or entry['expires'] < time.time():
            _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'code_expired'}, success=False)
            raise HTTPException(status_code=400, detail='Verification code expired, please request a new one')
        if not hmac.compare_digest(entry['code'], payload.code.strip()):
            _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_code'}, success=False)
            raise HTTPException(status_code=400, detail='Incorrect verification code')
        del _CODE_STORE[email]

    if _get_user(email):
        _security_audit('REGISTER_FAILED', email=email, ip=client_ip, details={'reason': 'email_exists'}, success=False)
        raise HTTPException(status_code=409, detail='Email already registered')

    nickname = payload.nickname.strip() or email.split('@')[0]
    public = _create_user(email, nickname, '', None, _hash_password(payload.password))
    token = _make_session(public)
    _security_audit('REGISTER_SUCCESS', email=email, ip=client_ip, details={'nickname': nickname}, success=True)
    print(f'[auth] register ok email={email} nickname={nickname}', flush=True)
    _set_session_cookie(response, request, token)
    # 同域下只发 HttpOnly cookie；只有真正跨域（cookie 发不出去）时才附带 Bearer token。
    body = {'ok': True, 'user': public}
    if _needs_bearer_token_in_body(request):
        body['token'] = token
    return body


@router.post('/api/auth/email/login')
@limiter.limit('20/minute')  # 每 IP 每分钟最多 20 次登录尝试
def email_login(request: Request, response: Response, payload: EmailLoginRequest):
    """Login with email + password."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] login attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    user_record = _get_user(email)
    if not user_record:
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip, details={'reason': 'user_not_found'}, success=False)
        print(f'[auth] login failed: invalid credential email={email}', flush=True)
        raise HTTPException(status_code=401, detail='Invalid email or password')
    stored_hash = user_record.get('password_hash', '')
    print(f'[auth] user found, hash prefix={stored_hash[:30] if stored_hash else "EMPTY"}, len={len(stored_hash)}', flush=True)
    if not _verify_password(payload.password, stored_hash):
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip, details={'reason': 'wrong_password', 'hash_len': len(stored_hash)}, success=False)
        print(f'[auth] login failed: invalid credential email={email}', flush=True)
        raise HTTPException(status_code=401, detail='Invalid email or password')
    if user_record.get('is_banned'):
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip, details={'reason': 'banned'}, success=False)
        raise HTTPException(status_code=403, detail='账号已被停用，请联系管理员')
    public = {k: v for k, v in user_record.items() if k != 'password_hash'}
    token = _make_session(public)
    _security_audit('LOGIN_SUCCESS', email=email, ip=client_ip, details={'nickname': public.get('nickname')}, success=True)
    print(f'[auth] login ok email={email} nickname={public.get("nickname")}', flush=True)
    _set_session_cookie(response, request, token)
    # 同上：cookie 是正路，token 只在跨域（cookie 无法送达）时作为兜底返回。
    body = {'ok': True, 'user': public}
    if _needs_bearer_token_in_body(request):
        body['token'] = token
    return body


class EmailResetPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=128)


@router.post('/api/auth/email/send-reset-code')
@limiter.limit('3/minute')  # 每 IP 每分钟最多 3 次重置密码请求
async def email_send_reset_code(request: Request, payload: EmailSendCodeRequest):
    """Send a verification code to reset password (email must be registered)."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] send-reset-code request for email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        _security_audit('PASSWORD_RESET_CODE_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_email'}, success=False)
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Check if email is registered
    user = _get_user(email)
    if not user:
        _security_audit('PASSWORD_RESET_CODE_FAILED', email=email, ip=client_ip, details={'reason': 'email_not_registered'}, success=False)
        print(f'[auth] send-reset-code failed: email not registered {email}', flush=True)
        raise HTTPException(status_code=404, detail='该邮箱未注册，请先注册')

    code = _generate_code()
    now = time.time()
    with _CODE_LOCK:
        _CODE_STORE[email] = {'code': code, 'expires': now + CODE_TTL_SECONDS}

    body = f"""您好！

您正在重置属灵星球账户的密码。验证码：{code}

请在 10 分钟内输入此验证码完成密码重置。如非本人操作，请忽略此邮件。

属灵星球
"""

    if not _email_service_ready():
        print(f'[auth][DEV] reset verification code for {email}: {code}', flush=True)
        # Only expose the code to the client in explicit local/dev mode; never in production.
        if _ALLOW_DEV_AUTH_CODE:
            return {'ok': True, 'dev_code': code}
        print('[auth][CONFIG] 密码重置被阻断：未配置任何发信通道', flush=True)
        raise HTTPException(status_code=503, detail=EMAIL_SERVICE_DOWN_DETAIL)

    try:
        await asyncio.to_thread(_send_email, email, '属灵星球 – 密码重置验证码', body)
        print(f'[auth] reset verification code sent to {email}', flush=True)
        return {'ok': True}
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail='Failed to send email, please try again later')


@router.post('/api/auth/email/reset-password')
@limiter.limit('5/minute')  # 每 IP 每分钟最多 5 次重置尝试
def email_reset_password(request: Request, payload: EmailResetPasswordRequest):
    """Reset password with verification code."""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] reset-password attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_email'}, success=False)
        raise HTTPException(status_code=400, detail='Invalid email address')

    # Verify code
    with _CODE_LOCK:
        entry = _CODE_STORE.get(email)
        if not entry or entry['expires'] < time.time():
            _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'code_expired'}, success=False)
            raise HTTPException(status_code=400, detail='Verification code expired, please request a new one')
        if not hmac.compare_digest(entry['code'], payload.code.strip()):
            _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'invalid_code'}, success=False)
            raise HTTPException(status_code=400, detail='Incorrect verification code')
        del _CODE_STORE[email]

    # Check if user exists
    user_record = _get_user(email)
    if not user_record:
        _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip, details={'reason': 'user_not_found'}, success=False)
        raise HTTPException(status_code=404, detail='User not found')

    # Update password
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET password_hash = %s WHERE LOWER(email) = LOWER(%s)',
                (_hash_password(payload.password), email)
            )
            conn.commit()
    finally:
        _release_db(conn)

    _security_audit('PASSWORD_RESET_SUCCESS', email=email, ip=client_ip, details={}, success=True)
    print(f'[auth] password reset ok email={email}', flush=True)
    return {'ok': True, 'message': 'Password reset successfully, please login with new password'}
