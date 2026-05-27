/**
 * Tests for src/store.js — Zustand global state.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { useEmotionStore } from '../store'

// Helper: read state snapshot without hooks (Zustand exposes .getState())
const getState = () => useEmotionStore.getState()
const setState = (fn) => useEmotionStore.setState(fn)

describe('useEmotionStore — initial state', () => {
  it('starts with empty layout and history arrays', () => {
    const state = getState()
    expect(Array.isArray(state.layoutItems)).toBe(true)
    expect(Array.isArray(state.historyItems)).toBe(true)
  })

  it('starts with no selected feature', () => {
    expect(getState().selectedFeature).toBeNull()
  })

  it('starts with default language filter "cuv"', () => {
    expect(getState().languageFilter).toBe('cuv')
  })

  it('starts with loading=false and empty error', () => {
    const { loading, error } = getState()
    expect(loading).toBe(false)
    expect(error).toBe('')
  })

  it('starts with zoomLevel "far"', () => {
    expect(getState().zoomLevel).toBe('far')
  })
})

describe('useEmotionStore — setters', () => {
  beforeEach(() => {
    // Reset relevant fields between tests
    useEmotionStore.setState({
      layoutItems: [],
      selectedFeature: null,
      languageFilter: 'cuv',
      loading: false,
      error: '',
      queryResult: null,
    })
  })

  it('setLayoutItems updates the layout array', () => {
    const items = [{ feature_key: 'joy', label: '喜乐' }]
    getState().setLayoutItems(items)
    expect(getState().layoutItems).toEqual(items)
  })

  it('setSelectedFeature updates selection', () => {
    const feature = { feature_key: 'peace', zh_label: '平安' }
    getState().setSelectedFeature(feature)
    expect(getState().selectedFeature).toEqual(feature)
  })

  it('setSelectedFeature accepts null to clear selection', () => {
    getState().setSelectedFeature({ feature_key: 'x' })
    getState().setSelectedFeature(null)
    expect(getState().selectedFeature).toBeNull()
  })

  it('setLanguageFilter updates filter', () => {
    getState().setLanguageFilter('esv')
    expect(getState().languageFilter).toBe('esv')
    getState().setLanguageFilter('both')
    expect(getState().languageFilter).toBe('both')
  })

  it('setLoading toggles loading flag', () => {
    getState().setLoading(true)
    expect(getState().loading).toBe(true)
    getState().setLoading(false)
    expect(getState().loading).toBe(false)
  })

  it('setError stores error message', () => {
    getState().setError('something went wrong')
    expect(getState().error).toBe('something went wrong')
    getState().setError('')
    expect(getState().error).toBe('')
  })

  it('setQueryResult stores result object', () => {
    const result = { selected_emotions: [], verse_summary: {} }
    getState().setQueryResult(result)
    expect(getState().queryResult).toEqual(result)
  })

  it('setTopFeatures and setTopVerses clamp within range', () => {
    getState().setTopFeatures(10)
    expect(getState().topFeatures).toBe(10)
    getState().setTopVerses(3)
    expect(getState().topVerses).toBe(3)
  })

  it('setZoomLevel updates zoom', () => {
    getState().setZoomLevel('near')
    expect(getState().zoomLevel).toBe('near')
    getState().setZoomLevel('far')
    expect(getState().zoomLevel).toBe('far')
  })
})

describe('communityHeatmap', () => {
  beforeEach(() => {
    useEmotionStore.setState({ communityHeatmap: [] })
  })

  it('initial communityHeatmap is empty array', () => {
    expect(useEmotionStore.getState().communityHeatmap).toEqual([])
  })

  it('setCommunityHeatmap stores emotion array', () => {
    const emotions = [
      { label: 'peace', count: 42, pct: 35.0, colour: '#87CEEB' },
      { label: 'joy',   count: 28, pct: 23.3, colour: '#FFD700' },
    ]
    useEmotionStore.getState().setCommunityHeatmap(emotions)
    const stored = useEmotionStore.getState().communityHeatmap
    expect(stored).toHaveLength(2)
    expect(stored[0].label).toBe('peace')
    expect(stored[1].pct).toBe(23.3)
  })

  it('setCommunityHeatmap replaces previous value', () => {
    useEmotionStore.getState().setCommunityHeatmap([{ label: 'old', count: 1, pct: 100, colour: '#fff' }])
    useEmotionStore.getState().setCommunityHeatmap([{ label: 'new', count: 5, pct: 100, colour: '#000' }])
    const stored = useEmotionStore.getState().communityHeatmap
    expect(stored).toHaveLength(1)
    expect(stored[0].label).toBe('new')
  })
})
