/**
 * Tests for src/api.js — fetch wrappers.
 * All network calls are mocked via vi.stubGlobal('fetch', ...).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// api.js uses import.meta.env which Vitest provides as an empty object by default
// We need to handle the module's top-level API_BASE resolution

describe('API_BASE resolution', () => {
  it('resolves to /api by default', async () => {
    const { API_BASE } = await import('../api')
    expect(API_BASE).toBe('/api')
  })
})

describe('fetchLayout', () => {
  afterEach(() => vi.restoreAllMocks())

  it('returns items from the API on success', async () => {
    const mockItems = [{ feature_key: 'joy' }, { feature_key: 'peace' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: mockItems, count: 2 }),
    }))

    const { fetchLayout } = await import('../api')
    const result = await fetchLayout()
    expect(result.items).toHaveLength(2)
    expect(result.count).toBe(2)
  })

  it('falls back to static JSON when API fails', async () => {
    const staticItems = [{ feature_key: 'static' }]
    let callCount = 0
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => {
      callCount++
      if (callCount === 1) return Promise.resolve({ ok: false, status: 503 })
      return Promise.resolve({
        ok: true,
        json: async () => staticItems,
      })
    }))

    const { fetchLayout } = await import('../api')
    const result = await fetchLayout()
    expect(result.items).toEqual(staticItems)
    expect(result.count).toBe(1)
  })
})

describe('fetchStats', () => {
  afterEach(() => vi.restoreAllMocks())

  it('returns stats object on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ page_views: 100, unique_visitors: 42 }),
    }))

    const { fetchStats } = await import('../api')
    const result = await fetchStats()
    expect(result.page_views).toBe(100)
    expect(result.unique_visitors).toBe(42)
  })
})

describe('fetchHistory', () => {
  afterEach(() => vi.restoreAllMocks())

  it('returns empty items when backend is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'text/html' },  // non-JSON = backend offline
    }))

    const { fetchHistory } = await import('../api')
    const result = await fetchHistory()
    expect(result.items).toEqual([])
  })

  it('returns history items when API responds', async () => {
    const items = [{ query: '我感到孤独', timestamp: '2024-01-01' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ items }),
    }))

    const { fetchHistory } = await import('../api')
    const result = await fetchHistory()
    expect(result.items).toHaveLength(1)
  })
})

describe('fetchEmotionTrajectory', () => {
  afterEach(() => vi.restoreAllMocks())

  it('returns trajectory data on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ok: true,
        count: 5,
        dominant_emotion: '孤独',
        items: [],
      }),
    }))

    const { fetchEmotionTrajectory } = await import('../api')
    const result = await fetchEmotionTrajectory('test-token')
    expect(result.dominant_emotion).toBe('孤独')
    expect(result.count).toBe(5)
  })

  it('returns null on HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))

    const { fetchEmotionTrajectory } = await import('../api')
    const result = await fetchEmotionTrajectory(null)
    expect(result).toBeNull()
  })
})

describe('fetchTTS', () => {
  afterEach(() => vi.restoreAllMocks())

  it('uses native TTS fallback when backend TTS is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Google TTS is temporarily unavailable.' }),
    }))

    const { fetchTTS } = await import('../api')
    await expect(fetchTTS('测试')).rejects.toThrow('TTS_NOT_CONFIGURED')
  })

  it('uses native TTS fallback when Google TTS upstream fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({ detail: 'Bad gateway' }),
    }))

    const { fetchTTS } = await import('../api')
    await expect(fetchTTS('测试')).rejects.toThrow('TTS_NOT_CONFIGURED')
  })
})

describe('runQuery', () => {
  afterEach(() => vi.restoreAllMocks())

  it('sends POST request with correct payload', async () => {
    const mockResult = { selected_emotions: [], verse_summary: { cuv: [] } }
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => mockResult,
    })
    vi.stubGlobal('fetch', mockFetch)

    const { runQuery } = await import('../api')
    const result = await runQuery({ query: '我感到焦虑', topFeatures: 5, topVerses: 3 })

    expect(mockFetch).toHaveBeenCalledOnce()
    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/query')
    expect(opts.method).toBe('POST')
    const body = JSON.parse(opts.body)
    expect(body.query).toBe('我感到焦虑')
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: { get: () => 'application/json' },
      json: async () => ({ detail: 'Server Error' }),
    }))

    const { runQuery } = await import('../api')
    await expect(runQuery({ query: 'test' })).rejects.toThrow()
  })
})

describe('fetchCommunityHeatmap', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('returns emotions array on success', async () => {
    const payload = {
      window_hours: 24,
      total_checkins: 120,
      emotions: [
        { label: 'peace', count: 42, pct: 35.0, colour: '#87CEEB' },
        { label: 'joy',   count: 28, pct: 23.3, colour: '#FFD700' },
      ],
      generated_at: '2025-05-27T10:00:00Z',
    }
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => payload })))
    const { fetchCommunityHeatmap } = await import('../api')
    const result = await fetchCommunityHeatmap(24, 8)
    expect(result.emotions).toHaveLength(2)
    expect(result.emotions[0].label).toBe('peace')
    expect(result.total_checkins).toBe(120)
  })

  it('returns empty emotions on HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 503 })))
    const { fetchCommunityHeatmap } = await import('../api')
    const result = await fetchCommunityHeatmap()
    expect(result.emotions).toEqual([])
    expect(result.total_checkins).toBe(0)
  })

  it('returns empty emotions on network failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('offline') }))
    const { fetchCommunityHeatmap } = await import('../api')
    const result = await fetchCommunityHeatmap()
    expect(result.emotions).toEqual([])
  })
})
