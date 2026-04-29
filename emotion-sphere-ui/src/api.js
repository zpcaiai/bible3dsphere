const configuredApiBase = import.meta.env.VITE_API_BASE?.trim()

function resolveDefaultApiBase() {
  if (typeof window === 'undefined') {
    return '/api'
  }

  return '/api'
}

const API_BASE = configuredApiBase || resolveDefaultApiBase()

export async function fetchLayout() {
  console.log('[api] fetchLayout')
  try {
    const response = await fetch(`${API_BASE}/layout`)
    if (!response.ok) throw new Error('Failed to fetch layout')
    const data = await response.json()
    console.log(`[api] fetchLayout ok: ${data.count} items`)
    return data
  } catch (err) {
    console.log('[api] fetchLayout api failed, fallback to static json', err.message)
    const response = await fetch('/emotion_sphere_layout.json')
    if (!response.ok) throw new Error('Failed to fetch layout (static fallback)')
    const items = await response.json()
    console.log(`[api] fetchLayout static ok: ${items.length} items`)
    return { items, count: items.length }
  }
}

export async function fetchHistory() {
  console.log('[api] fetchHistory')
  const response = await fetch(`${API_BASE}/history`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    const text = await response.text()
    throw new Error(`API returned ${response.status}: ${text.slice(0, 100)}`)
  }
  if (!response.ok) throw new Error('Failed to fetch history')
  const data = await response.json()
  console.log(`[api] fetchHistory ok: ${data.items?.length ?? 0} records`)
  return data
}

export async function fetchStats() {
  console.log('[api] fetchStats')
  const response = await fetch(`${API_BASE}/stats`)
  if (!response.ok) throw new Error('Failed to fetch stats')
  const data = await response.json()
  console.log('[api] fetchStats ok:', data)
  return data
}

export async function trackStats(visitorId) {
  console.log(`[api] trackStats visitorId=${visitorId}`)
  const response = await fetch(`${API_BASE}/stats/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visitorId }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Failed to track stats')
  console.log('[api] trackStats ok:', data)
  return data
}

export async function fetchFeatureDetail(featureKey) {
  console.log(`[api] fetchFeatureDetail key=${featureKey}`)
  const response = await fetch(`${API_BASE}/feature?key=${encodeURIComponent(featureKey)}`)
  if (!response.ok) throw new Error('Failed to fetch feature detail')
  const data = await response.json()
  console.log(`[api] fetchFeatureDetail ok key=${featureKey}`)
  return data
}

export async function runQuery(payload) {
  console.log(`[api] runQuery query=${payload.query?.slice(0, 60)} rerank=${payload.enableRerank}`)
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Query failed')
  console.log(`[api] runQuery ok latency=${data.query_latency_ms}ms features=${data.selected_emotions?.length ?? 0}`)
  return data
}

export async function fetchGuidance(query) {
  console.log(`[api] fetchGuidance query=${query?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/guidance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Guidance failed')
  console.log(`[api] fetchGuidance ok emotions=${data.core_emotions}`)
  return data
}

export async function fetchSermon(query) {
  console.log(`[api] fetchSermon query=${query?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/sermon`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Sermon failed')
  console.log(`[api] fetchSermon ok title=${data.title}`)
  return data
}

export async function fetchBiblicalExample(query) {
  console.log(`[api] fetchBiblicalExample query=${query?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/biblical-example`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Biblical example failed')
  console.log(`[api] fetchBiblicalExample ok person=${data.person} era=${data.era}`)
  return data
}

export async function* sendChat(messages, sessionId, token) {
  console.log(`[api] sendChat session=${sessionId} msgs=${messages.length}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId || '', messages }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    console.error('[api] sendChat error:', err)
    throw new Error(err.detail || err.error || 'Chat failed')
  }
  console.log('[api] sendChat stream started')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let totalChunks = 0
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
        if (obj.delta) totalChunks++
        if (obj.done) console.log(`[api] sendChat stream done session=${obj.session_id} chunks=${totalChunks}`)
        yield obj
      } catch { /* ignore malformed */ }
    }
  }
}

export async function fetchPrayers(limit = 40, offset = 0) {
  console.log(`[api] fetchPrayers limit=${limit} offset=${offset}`)
  const response = await fetch(`${API_BASE}/prayers?limit=${limit}&offset=${offset}`)
  if (!response.ok) throw new Error('Failed to fetch prayers')
  const data = await response.json()
  console.log(`[api] fetchPrayers ok: ${data.items?.length ?? 0}/${data.total} items`)
  return data
}

export async function submitPrayer(content, isAnonymous, token) {
  console.log(`[api] submitPrayer anon=${isAnonymous} len=${content.length}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content, is_anonymous: isAnonymous }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Submit failed')
  console.log(`[api] submitPrayer ok id=${data.id}`)
  return data
}

export async function amenPrayer(prayerId, token) {
  console.log(`[api] amenPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}/amen`, {
    method: 'POST',
    headers,
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Amen failed')
  console.log(`[api] amenPrayer ok id=${prayerId} count=${data.amen_count}`)
  return data
}

export async function submitCheckin(payload, token) {
  console.log(`[api] submitCheckin emotion=${payload.emotionLabel} anon=${!token}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/user/checkin`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Checkin failed')
  console.log(`[api] submitCheckin ok tags=${data.tags_extracted}`)
  return data
}

export async function fetchJournals(token, limit = 50, offset = 0) {
  console.log(`[api] fetchJournals limit=${limit} offset=${offset}`)
  const response = await fetch(`${API_BASE}/devotion/journals?limit=${limit}&offset=${offset}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Fetch journals failed')
  console.log(`[api] fetchJournals ok ${data.items?.length ?? 0}/${data.total}`)
  return data
}

export async function saveJournal(payload, token) {
  console.log(`[api] saveJournal date=${payload.date} title=${payload.title?.slice(0, 30)}`)
  const response = await fetch(`${API_BASE}/devotion/journals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Save journal failed')
  console.log(`[api] saveJournal ok id=${data.journal?.id}`)
  return data
}

export async function deleteJournal(journalId, token) {
  console.log(`[api] deleteJournal id=${journalId}`)
  const response = await fetch(`${API_BASE}/devotion/journals/${journalId}`, {
    method: 'DELETE',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete journal failed')
  console.log(`[api] deleteJournal ok id=${journalId}`)
  return data
}
