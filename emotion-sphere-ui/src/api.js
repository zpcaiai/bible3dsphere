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
  if (!response.ok) throw new Error('Failed to fetch history')
  return response.json()
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
