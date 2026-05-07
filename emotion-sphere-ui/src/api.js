const configuredApiBase = import.meta.env.VITE_API_BASE?.trim()

function resolveDefaultApiBase() {
  if (typeof window === 'undefined') {
    return '/api'
  }

  const hostname = window.location.hostname
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return '/api'  // 本地开发使用 Vite proxy
  }

  // Hugging Space / Netlify / Render：后端和前端同域名，使用相对路径
  if (hostname.includes('hf.space') || hostname.includes('netlify.app') || hostname.includes('onrender.com')) {
    return '/api'
  }

  return '/api'
}

export const API_BASE = configuredApiBase || resolveDefaultApiBase()

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
    console.log('[api] fetchHistory backend unavailable, returning empty')
    return { items: [], total: 0 }
  }
  if (!response.ok) throw new Error('Failed to fetch history')
  const data = await response.json()
  console.log(`[api] fetchHistory ok: ${data.items?.length ?? 0} records`)
  return data
}

export async function fetchStats() {
  console.log('[api] fetchStats')
  const response = await fetch(`${API_BASE}/stats`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Failed to track stats')
  console.log('[api] trackStats ok:', data)
  return data
}

export async function fetchFeatureDetail(featureKey) {
  console.log(`[api] fetchFeatureDetail key=${featureKey}`)
  const response = await fetch(`${API_BASE}/feature?key=${encodeURIComponent(featureKey)}`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json') && !contentType.includes('text/event-stream')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Amen failed')
  console.log(`[api] amenPrayer ok id=${prayerId} count=${data.amen_count}`)
  return data
}

export async function updatePrayer(prayerId, content, token) {
  console.log(`[api] updatePrayer id=${prayerId}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ content: content.trim() }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Update failed')
  console.log(`[api] updatePrayer ok id=${prayerId}`)
  return data
}

export async function deletePrayer(prayerId, token) {
  console.log(`[api] deletePrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}`, {
    method: 'DELETE',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete failed')
  console.log(`[api] deletePrayer ok id=${prayerId}`)
  return data
}

// ── Evangelism Prayers (传福音祷告墙) ─────────────────────────

export async function fetchEvangelismPrayers(limit = 40, offset = 0) {
  console.log(`[api] fetchEvangelismPrayers limit=${limit} offset=${offset}`)
  const response = await fetch(`${API_BASE}/evangelism?limit=${limit}&offset=${offset}`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  if (!response.ok) throw new Error('Failed to fetch evangelism prayers')
  const data = await response.json()
  console.log(`[api] fetchEvangelismPrayers ok: ${data.items?.length ?? 0}/${data.total} items`)
  return data
}

export async function submitEvangelismPrayer(content, isAnonymous, token) {
  console.log(`[api] submitEvangelismPrayer anon=${isAnonymous} len=${content.length}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content: content.trim(), is_anonymous: isAnonymous }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Submit failed')
  console.log(`[api] submitEvangelismPrayer ok id=${data.id}`)
  return data
}

export async function amenEvangelismPrayer(prayerId, token) {
  console.log(`[api] amenEvangelismPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}/amen`, {
    method: 'POST',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Amen failed')
  console.log(`[api] amenEvangelismPrayer ok id=${prayerId} count=${data.amen_count}`)
  return data
}

export async function updateEvangelismPrayer(prayerId, content, token) {
  console.log(`[api] updateEvangelismPrayer id=${prayerId}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ content: content.trim() }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Update failed')
  console.log(`[api] updateEvangelismPrayer ok id=${prayerId}`)
  return data
}

export async function deleteEvangelismPrayer(prayerId, token) {
  console.log(`[api] deleteEvangelismPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}`, {
    method: 'DELETE',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete failed')
  console.log(`[api] deleteEvangelismPrayer ok id=${prayerId}`)
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
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
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete journal failed')
  console.log(`[api] deleteJournal ok id=${journalId}`)
  return data
}

// ── Sermon Journal API ─────────────────────────────────────

export async function fetchSermonJournals(token, limit = 50, offset = 0) {
  console.log(`[api] fetchSermonJournals limit=${limit} offset=${offset}`)
  const response = await fetch(`${API_BASE}/sermon/journals?limit=${limit}&offset=${offset}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Fetch sermon journals failed')
  console.log(`[api] fetchSermonJournals ok ${data.items?.length ?? 0}/${data.total}`)
  return data
}

export async function saveSermonJournal(payload, token) {
  console.log(`[api] saveSermonJournal date=${payload.date} title=${payload.title?.slice(0, 30)}`)
  const response = await fetch(`${API_BASE}/sermon/journals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Save sermon journal failed')
  console.log(`[api] saveSermonJournal ok id=${data.journal?.id}`)
  return data
}

export async function deleteSermonJournal(journalId, token) {
  console.log(`[api] deleteSermonJournal id=${journalId}`)
  const response = await fetch(`${API_BASE}/sermon/journals/${journalId}`, {
    method: 'DELETE',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete sermon journal failed')
  console.log(`[api] deleteSermonJournal ok id=${journalId}`)
  return data
}

// ── Personal Notes API (我的日记) ──────────────────────────

export async function fetchPersonalNotes(token) {
  console.log(`[api] fetchPersonalNotes`)
  const response = await fetch(`${API_BASE}/personal/notes`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Fetch personal notes failed')
  console.log(`[api] fetchPersonalNotes ok ${data.items?.length ?? 0}`)
  return data
}

export async function savePersonalNote(payload, token) {
  console.log(`[api] savePersonalNote id=${payload.id} date=${payload.date}`)
  const response = await fetch(`${API_BASE}/personal/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Save personal note failed')
  console.log(`[api] savePersonalNote ok id=${data.note?.id}`)
  return data
}

export async function deletePersonalNote(noteId, token) {
  console.log(`[api] deletePersonalNote id=${noteId}`)
  const response = await fetch(`${API_BASE}/personal/notes/${noteId}`, {
    method: 'DELETE',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Delete personal note failed')
  console.log(`[api] deletePersonalNote ok id=${noteId}`)
  return data
}
