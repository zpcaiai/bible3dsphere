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

export async function fetchRetrievalEvaluation() {
  console.log('[api] fetchRetrievalEvaluation')
  const response = await fetch(`${API_BASE}/retrieval/evaluation`)
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Failed to fetch retrieval evaluation')
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
    throw new Error(`后端服务未运行 (HTTP ${response.status})`)
  }
  const data = await response.json()
  if (!response.ok) {
    let msg = data.error || '请求失败'
    if (Array.isArray(data.detail)) {
      msg = data.detail.map(e => `${e.loc?.join('.') || ''}: ${e.msg}`).join('; ')
    } else if (typeof data.detail === 'string') {
      msg = data.detail
    } else if (data.detail) {
      msg = JSON.stringify(data.detail)
    }
    throw new Error(`[HTTP ${response.status}] ${msg}`)
  }
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

export async function fetchDailySnapshot(token) {
  const response = await fetch(`${API_BASE}/daily-snapshot`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  if (!response.ok) return null
  const data = await response.json()
  return data.ok ? data : null
}

export async function fetchEmotionTrajectory(token, limit = 30) {
  const response = await fetch(`${API_BASE}/user/emotion-trajectory?limit=${limit}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  if (!response.ok) return null
  const data = await response.json()
  return data.ok ? data : null
}

export async function fetchCommunityHeatmap(windowHours = 24, topN = 8) {
  try {
    const params = new URLSearchParams({ window_hours: windowHours, top_n: topN })
    const res = await fetch(`${API_BASE}/community/emotion-heatmap?${params}`)
    if (!res.ok) return { emotions: [], total_checkins: 0 }
    return await res.json()
  } catch {
    return { emotions: [], total_checkins: 0 }
  }
}

export async function fetchMeditationQuestions(reference, text) {
  console.log(`[api] fetchMeditationQuestions ref=${reference}`)
  const response = await fetch(`${API_BASE}/meditation-questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reference, text }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) throw new Error('后端服务未运行')
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Meditation questions failed')
  return data.questions || []
}

// ── A1: 每日灵魂一问 ──────────────────────────────────────────
export async function fetchDailySoulQuestion(token) {
  const response = await fetch(`${API_BASE}/daily-soul-question`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Failed')
  return data
}

export async function saveSoulAnswer(answer, saveToJournal, token) {
  const response = await fetch(`${API_BASE}/daily-soul-question/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ answer, save_to_journal: saveToJournal }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Failed')
  return data
}

export async function fetchSoulQuestionHistory(token) {
  const response = await fetch(`${API_BASE}/daily-soul-question/history`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  const data = await response.json()
  return data.ok ? data.items : []
}

// ── A3: 属灵健康检查 ──────────────────────────────────────────
export async function fetchSpiritualHealthCheck(token) {
  const response = await fetch(`${API_BASE}/spiritual-health-check`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  if (!response.ok) return null
  const data = await response.json()
  return data.ok ? data : null
}

// ── A4: 属灵伙伴 ──────────────────────────────────────────────
export async function fetchPartnerStatus(token) {
  const response = await fetch(`${API_BASE}/spiritual-partner/status`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  if (!response.ok) return null
  const data = await response.json()
  return data.ok ? data : null
}

export async function requestPartner(partnerEmail, token) {
  const response = await fetch(`${API_BASE}/spiritual-partner/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ partner_email: partnerEmail }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Failed')
  return data
}

export async function respondPartner(requester, accept, token) {
  const response = await fetch(`${API_BASE}/spiritual-partner/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ requester, accept }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Failed')
  return data
}

export async function sendEncouragement(token) {
  const response = await fetch(`${API_BASE}/spiritual-partner/encourage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({}),
  })
  const data = await response.json()
  return data
}

// ── A7: 里程碑徽章 ────────────────────────────────────────────
export async function fetchMilestones(token) {
  const response = await fetch(`${API_BASE}/milestones`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  if (!response.ok) return []
  const data = await response.json()
  return data.ok ? data.items : []
}

// ── A10: 圣经通读 ─────────────────────────────────────────────
export async function markChapterRead(book, chapter, highlight, token) {
  const response = await fetch(`${API_BASE}/bible-reading/mark`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ book, chapter, highlight }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Failed')
  return data
}

export async function fetchReadingProgress(token) {
  const response = await fetch(`${API_BASE}/bible-reading/progress`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  })
  if (!response.ok) return { items: [], by_book: {} }
  const data = await response.json()
  return data.ok ? data : { items: [], by_book: {} }
}

export async function fetchTranslate(text, targetLang = 'en') {
  console.log(`[api] fetchTranslate target=${targetLang} text=${text?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, target_lang: targetLang }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Translation failed')
  console.log(`[api] fetchTranslate ok len=${data.translation?.length}`)
  return data.translation
}

export async function fetchFaithQA(question) {
  console.log(`[api] fetchFaithQA question=${question?.slice(0, 60)}`)
  const response = await fetch(`${API_BASE}/faith-qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Faith QA failed')
  console.log(`[api] fetchFaithQA ok summary=${data.question_summary?.slice(0, 40)}`)
  return data
}

export async function fetchVersePrayer(reference, text) {
  console.log(`[api] fetchVersePrayer ref=${reference}`)
  const response = await fetch(`${API_BASE}/verse-prayer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reference, text }),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || '祷告生成失败')
  console.log(`[api] fetchVersePrayer ok len=${data.prayer?.length}`)
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

export async function fetchPrayers(limit = 40, offset = 0, token = null) {
  console.log(`[api] fetchPrayers limit=${limit} offset=${offset}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers?limit=${limit}&offset=${offset}`, { headers })
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

export async function updatePrayerStatus(prayerId, status, token) {
  console.log(`[api] updatePrayerStatus id=${prayerId} status=${status}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}/status`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ status }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Update status failed')
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

export async function restorePrayer(prayerId, token) {
  console.log(`[api] restorePrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/prayers/${prayerId}/restore`, {
    method: 'POST',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Restore failed')
  console.log(`[api] restorePrayer ok id=${prayerId}`)
  return data
}

// ── Evangelism Prayers (传福音祷告墙) ─────────────────────────

export async function fetchEvangelismPrayers(limit = 40, offset = 0, token = null) {
  console.log(`[api] fetchEvangelismPrayers limit=${limit} offset=${offset}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism?limit=${limit}&offset=${offset}`, { headers })
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

export async function restoreEvangelismPrayer(prayerId, token) {
  console.log(`[api] restoreEvangelismPrayer id=${prayerId}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/evangelism/${prayerId}/restore`, {
    method: 'POST',
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Restore failed')
  console.log(`[api] restoreEvangelismPrayer ok id=${prayerId}`)
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
  const body = {
    date: payload.date || '',
    title: payload.title || '',
    preacher: payload.preacher || '',
    scripture: payload.scripture || '',
    summary: payload.summary || '',
    questions: payload.questions || [],
    bible_study: payload.bibleStudy || payload.bible_study || '',
    practices: payload.practices || [],
    reflection: payload.reflection || '',
    lesson: payload.lesson || '',
    conclusion: payload.conclusion || '',
    encouragement: payload.encouragement || '',
    phase: payload.phase || 'active',
  }
  const response = await fetch(`${API_BASE}/sermon/journals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
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

// ── User Profile API ─────────────────────────────────────────

export async function updateUserProfile(payload, token) {
  console.log(`[api] updateUserProfile nickname=${payload.nickname}`)
  const response = await fetch(`${API_BASE}/user/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行（请先启动 backend/main.py）')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || 'Update profile failed')
  console.log(`[api] updateUserProfile ok nickname=${data.nickname}`)
  return data
}

// ── Google Cloud Text-to-Speech ─────────────────────────────────
export async function fetchTTS(text, language_code = 'zh-CN', voice_name = 'zh-CN-XiaoxiaoNeural') {
  console.log(`[api] fetchTTS text=${text?.slice(0, 60)}... lang=${language_code}`)
  const response = await fetch(`${API_BASE}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language_code, voice_name }),
  })
  
  // 502/503 表示后端 TTS 未配置或上游不可用，前端应 fallback 到浏览器原生 TTS
  if ([502, 503].includes(response.status)) {
    console.log('[api] fetchTTS backend unavailable, fallback to native TTS')
    throw new Error('TTS_NOT_CONFIGURED')
  }
  
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'TTS failed')
  }
  
  // 返回音频 Blob
  const audioBlob = await response.blob()
  console.log(`[api] fetchTTS ok blob=${audioBlob.size} bytes`)
  return audioBlob
}


// ── Share Wall (分享墙) ─────────────────────────────────────

export async function fetchSharedNotes(token = null, page = 1, limit = 20) {
  console.log(`[api] fetchSharedNotes page=${page}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/shared/notes?page=${page}&limit=${limit}`, { headers })
  if (response.status === 401) {
    return { ok: false, requireLogin: true, items: [], total: 0, pages: 0 }
  }
  if (!response.ok) throw new Error('Failed to fetch shared notes')
  const data = await response.json()
  console.log(`[api] fetchSharedNotes ok: ${data.items?.length ?? 0}/${data.total} items page=${page}`)
  return data
}

export async function toggleShareSermonJournal(journalId, token = null) {
  console.log(`[api] toggleShareSermonJournal id=${journalId}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['X-Auth-Token'] = token
  const response = await fetch(`${API_BASE}/sermon/journals/${journalId}/share`, {
    method: 'POST',
    headers,
  })
  if (response.status === 403) throw new Error('Only the creator can share/unshare')
  if (!response.ok) throw new Error('Failed to toggle share')
  return response.json()
}

export async function toggleShareNote(noteId, token = null) {
  console.log(`[api] toggleShareNote id=${noteId}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/personal/notes/${noteId}/share`, {
    method: 'POST',
    headers,
  })
  if (response.status === 401) throw new Error('Login required')
  if (response.status === 403) throw new Error('Only the creator can share/unshare')
  if (!response.ok) throw new Error('Failed to toggle share')
  return await response.json()
}

export async function amenSharedNote(noteId, token) {
  console.log(`[api] amenSharedNote id=${noteId}`)
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/shared/notes/${noteId}/amen`, { method: 'POST', headers })
  if (response.status === 401) throw new Error('Login required')
  if (!response.ok) throw new Error('Amen failed')
  return await response.json()
}

// ── Recycle Bin API ──────────────────────────────────────────

export async function fetchRecycleBin(token) {
  console.log('[api] fetchRecycleBin')
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/recycle-bin`, { headers })
  if (response.status === 401) throw new Error('Login required')
  if (!response.ok) {
    let detail = 'Failed to fetch recycle bin'
    try {
      const errData = await response.json()
      detail = errData.detail || errData.error || detail
    } catch {}
    throw new Error(detail)
  }
  return await response.json()
}

export async function restoreRecycleItem(type, id, token) {
  console.log(`[api] restoreRecycleItem type=${type} id=${id}`)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const response = await fetch(`${API_BASE}/recycle-bin/${type}/${id}/restore`, {
    method: 'POST',
    headers,
  })
  if (response.status === 401) throw new Error('Login required')
  if (response.status === 403) throw new Error('Not authorized')
  if (response.status === 404) throw new Error('Item not found')
  if (!response.ok) throw new Error('Restore failed')
  return await response.json()
}


// ── 人格塑造、习惯养成、行为追踪 API ───────────────────────

export async function regulateBehavior(task, energyLevel = 3, motivation = 5, token = null) {
  console.log(`[api] regulateBehavior task=${task} energy=${energyLevel}`)
  const response = await fetch(`${API_BASE}/behavior/regulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ task, energy_level: energyLevel, motivation })
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '行为调节失败')
  console.log(`[api] regulateBehavior tier=${data.selected_tier}`)
  return data
}

export async function createHabit(habitName, anchor = '', energyLevel = 3, token) {
  console.log(`[api] createHabit name=${habitName}`)
  const response = await fetch(`${API_BASE}/habits/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ habit_name: habitName, anchor, energy_level: energyLevel })
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '创建习惯失败')
  console.log(`[api] createHabit ok id=${data.saved_habit_id}`)
  return data
}

export async function fetchHabits(token) {
  console.log(`[api] fetchHabits`)
  const response = await fetch(`${API_BASE}/habits`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取习惯列表失败')
  console.log(`[api] fetchHabits ok count=${data.items?.length || 0}`)
  return data
}

export async function executeHabit(habitId, energyLevel = 3, token) {
  console.log(`[api] executeHabit ${habitId} energy=${energyLevel}`)
  const response = await fetch(`${API_BASE}/habits/${habitId}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ habit_id: habitId, energy_level: energyLevel })
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '执行习惯失败')
  console.log(`[api] executeHabit tier=${data.selected_tier}`)
  return data
}

export async function logHabitExecution(habitId, tierExecuted, wasCompleted, completionPercentage, moodBefore, moodAfter, token) {
  console.log(`[api] logHabitExecution ${habitId} tier=${tierExecuted} completed=${wasCompleted}`)
  const response = await fetch(`${API_BASE}/habits/${habitId}/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
    body: JSON.stringify({ 
      habit_id: habitId, 
      tier_executed: tierExecuted,
      was_completed: wasCompleted,
      completion_percentage: completionPercentage,
      mood_before: moodBefore,
      mood_after: moodAfter
    })
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '记录执行失败')
  console.log(`[api] logHabitExecution tokens=${data.tokens_earned}`)
  return data
}

export async function fetchHabitsDashboard(token) {
  console.log(`[api] fetchHabitsDashboard`)
  const response = await fetch(`${API_BASE}/habits/dashboard`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取仪表盘失败')
  console.log(`[api] fetchHabitsDashboard tokens=${data.token_balance}`)
  return data
}

// ==================== Formation Engine (人格塑造) API ====================

export async function fetchFormationProfile(userId, token) {
  console.log(`[api] fetchFormationProfile userId=${userId}`)
  const response = await fetch(`${API_BASE}/sfds/v3/formation/profile/${userId}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取人格塑造档案失败')
  console.log(`[api] fetchFormationProfile schema=${data.schema}`)
  return data
}

export async function fetchFormationDimensions(token) {
  console.log(`[api] fetchFormationDimensions`)
  const response = await fetch(`${API_BASE}/sfds/v3/formation/dimensions`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取维度定义失败')
  console.log(`[api] fetchFormationDimensions dimensions=${data.dimensions?.length}`)
  return data
}

// ==================== Reflection Survey API ====================

export async function saveReflectionAnswers(userId, answers, token) {
  const response = await fetch(`${API_BASE}/reflection/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ user_id: String(userId), answers })
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) throw new Error('后端服务未运行')
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '保存失败')
  return data
}

export async function fetchReflectionAnswers(userId, token) {
  const response = await fetch(`${API_BASE}/reflection/load?user_id=${userId}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) throw new Error('后端服务未运行')
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '加载失败')
  return data
}

// ==================== Behavior Tracking (行为追踪) API ====================

export async function fetchBehaviorHistory(userId, token, limit = 30) {
  console.log(`[api] fetchBehaviorHistory userId=${userId} limit=${limit}`)
  const response = await fetch(`${API_BASE}/behavior/history?user_id=${userId}&limit=${limit}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取行为历史失败')
  console.log(`[api] fetchBehaviorHistory count=${data.items?.length}`)
  return data
}

export async function fetchBehaviorStats(userId, token) {
  console.log(`[api] fetchBehaviorStats userId=${userId}`)
  const response = await fetch(`${API_BASE}/behavior/stats?user_id=${userId}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '获取行为统计失败')
  console.log(`[api] fetchBehaviorStats total_regulations=${data.total_regulations}`)
  return data
}

// ==================== Formation → Habits Sync API ====================

export async function createHabitsFromFormationPlan(userId, planItems, planType, token) {
  console.log(`[api] createHabitsFromFormationPlan userId=${userId} items=${planItems.length}`)
  const response = await fetch(`${API_BASE}/habits/create-from-formation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({
      user_id: userId,
      plan_items: planItems,
      plan_type: planType // 'short' | 'mid'
    })
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('后端服务未运行')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || '从人格塑造计划创建习惯失败')
  console.log(`[api] createHabitsFromFormationPlan created=${data.created_count}`)
  return data
}
