const TOKEN_KEY = 'bible-sphere-token'
const USER_KEY = 'bible-sphere-user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setCachedUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export async function fetchCurrentUser() {
  const token = getToken()
  if (!token) return null
  try {
    const res = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const contentType = res.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      throw new Error('后端服务未运行（请先启动 backend/main.py）')
    }
    if (!res.ok) {
      clearToken()
      return null
    }
    const data = await res.json()
    if (data.ok && data.user) {
      setCachedUser(data.user)
      return data.user
    }
    clearToken()
    return null
  } catch {
    return null
  }
}

export async function logout() {
  const token = getToken()
  if (token) {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch {
      // ignore
    }
  }
  clearToken()
}

export function redirectToWechatLogin() {
  window.location.href = '/api/auth/wechat/login'
}

export async function sendEmailCode(email) {
  const res = await fetch('/api/auth/email/send-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Failed to send code')
  return data
}

export async function registerWithEmail(email, code, password, nickname = '') {
  const res = await fetch('/api/auth/email/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code, password, nickname }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Registration failed')
  if (data.token) {
    setToken(data.token)
    if (data.user) setCachedUser(data.user)
  }
  return data
}

export async function loginWithEmail(email, password) {
  const res = await fetch('/api/auth/email/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Login failed')
  if (data.token) {
    setToken(data.token)
    if (data.user) setCachedUser(data.user)
  }
  return data
}

export function extractTokenFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) {
    setToken(token)
    // Clean up URL
    const url = new URL(window.location.href)
    url.searchParams.delete('token')
    window.history.replaceState({}, '', url.toString())
    return token
  }
  return null
}
