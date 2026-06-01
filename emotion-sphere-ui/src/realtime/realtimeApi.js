// 圣徒相通 — REST helpers for friends, chat history, and ICE servers.
import { API_BASE } from '../api'
import { getToken } from '../auth'

function authHeaders(extra = {}) {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

async function jsonOrThrow(res) {
  const ct = res.headers.get('content-type') || ''
  if (!ct.includes('application/json')) throw new Error('后端服务不可用')
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || '请求失败')
  return data
}

/** Build the WebSocket URL for /api/ws/rtc, carrying the auth token as a query param. */
export function buildWsUrl() {
  const token = getToken()
  let base = API_BASE // e.g. "https://x.hf.space/api" or "/api"
  if (/^https?:\/\//i.test(base)) {
    base = base.replace(/^http/i, 'ws')
  } else {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    base = `${proto}//${window.location.host}${base.startsWith('/') ? base : '/' + base}`
  }
  return `${base}/ws/rtc?token=${encodeURIComponent(token)}`
}

export async function fetchIceServers() {
  const res = await fetch(`${API_BASE}/rtc/ice-servers`, { headers: authHeaders() })
  const data = await jsonOrThrow(res)
  return data.iceServers || [{ urls: ['stun:stun.l.google.com:19302'] }]
}

export async function fetchFriends() {
  const res = await fetch(`${API_BASE}/friends`, { headers: authHeaders() })
  return jsonOrThrow(res)
}

export async function requestFriend(email) {
  const res = await fetch(`${API_BASE}/friends/request`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ email }),
  })
  return jsonOrThrow(res)
}

export async function acceptFriend(email) {
  const res = await fetch(`${API_BASE}/friends/accept`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ email }),
  })
  return jsonOrThrow(res)
}

export async function removeFriend(email) {
  const res = await fetch(`${API_BASE}/friends/remove`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ email }),
  })
  return jsonOrThrow(res)
}

export async function fetchChatHistory(peer, { limit = 50, beforeId = 0 } = {}) {
  const params = new URLSearchParams({ peer, limit: String(limit) })
  if (beforeId) params.set('before_id', String(beforeId))
  const res = await fetch(`${API_BASE}/chat/history?${params}`, { headers: authHeaders() })
  return jsonOrThrow(res)
}

export async function markRead(peer) {
  const res = await fetch(`${API_BASE}/chat/read`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ peer }),
  })
  return jsonOrThrow(res)
}

/** 查询后端是否启用语音（LiveKit）。失败时安全返回 false。 */
export async function fetchVoiceEnabled() {
  try {
    const res = await fetch(`${API_BASE}/voice/config`, { headers: authHeaders() })
    const d = await jsonOrThrow(res)
    return !!d.enabled
  } catch { return false }
}

/** 取 1对1 秒拨语音的 LiveKit 凭据。返回 { url, token, room, identity, name, peer, peer_name }。 */
export async function fetchDirectVoiceToken(peer, room = '') {
  const res = await fetch(`${API_BASE}/voice/direct/token`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ peer, room }),
  })
  return jsonOrThrow(res)
}
