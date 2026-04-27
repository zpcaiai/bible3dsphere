const configuredApiBase = import.meta.env.VITE_API_BASE?.trim()

function resolveDefaultApiBase() {
  if (typeof window === 'undefined') {
    return '/api'
  }

  return '/api'
}

const API_BASE = configuredApiBase || resolveDefaultApiBase()

export async function fetchLayout() {
  const response = await fetch(`${API_BASE}/layout`)
  if (!response.ok) throw new Error('Failed to fetch layout')
  return response.json()
}

export async function fetchHistory() {
  const response = await fetch(`${API_BASE}/history`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    const text = await response.text()
    throw new Error(`API returned ${response.status}: ${text.slice(0, 100)}`)
  }
  if (!response.ok) throw new Error('Failed to fetch history')
  return response.json()
}

export async function fetchStats() {
  const response = await fetch(`${API_BASE}/stats`)
  if (!response.ok) throw new Error('Failed to fetch stats')
  return response.json()
}

export async function trackStats(visitorId) {
  const response = await fetch(`${API_BASE}/stats/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visitorId }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Failed to track stats')
  return data
}

export async function fetchFeatureDetail(featureKey) {
  const response = await fetch(`${API_BASE}/feature?key=${encodeURIComponent(featureKey)}`)
  if (!response.ok) throw new Error('Failed to fetch feature detail')
  return response.json()
}

export async function runQuery(payload) {
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Query failed')
  return data
}

export async function fetchGuidance(query) {
  const response = await fetch(`${API_BASE}/guidance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Guidance failed')
  return data
}

export async function fetchSermon(query) {
  const response = await fetch(`${API_BASE}/sermon`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Sermon failed')
  return data
}

export async function fetchBiblicalExample(query) {
  const response = await fetch(`${API_BASE}/biblical-example`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Biblical example failed')
  return data
}

export async function* sendChat(messages, sessionId, token) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId || '', messages }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || err.error || 'Chat failed')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        const obj = JSON.parse(raw)
        yield obj
      } catch { /* ignore malformed */ }
    }
  }
}

export async function submitCheckin(payload, token) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/user/checkin`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Checkin failed')
  return data
}
