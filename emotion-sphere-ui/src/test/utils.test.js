/**
 * Tests for src/utils.js — pure functions only, no network, no DOM.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  verseGroupsFromResult,
  buildComparisonRows,
  formatLoginTime,
  getOrCreateVisitorId,
} from '../utils'

// ── verseGroupsFromResult ────────────────────────────────────────────────────

describe('verseGroupsFromResult', () => {
  const mockResult = {
    verse_summary: {
      cuv: [{ pk_id: 1, text: '爱是恒久忍耐' }],
      esv: [{ pk_id: 1, text: 'Love is patient' }],
    },
  }

  it('returns both languages when filter is "both"', () => {
    const groups = verseGroupsFromResult(mockResult, 'both')
    expect(groups).toHaveLength(2)
    expect(groups[0].language).toBe('cuv')
    expect(groups[1].language).toBe('esv')
  })

  it('returns only cuv when filter is "cuv"', () => {
    const groups = verseGroupsFromResult(mockResult, 'cuv')
    expect(groups).toHaveLength(1)
    expect(groups[0].language).toBe('cuv')
    expect(groups[0].items).toHaveLength(1)
  })

  it('returns only esv when filter is "esv"', () => {
    const groups = verseGroupsFromResult(mockResult, 'esv')
    expect(groups).toHaveLength(1)
    expect(groups[0].language).toBe('esv')
  })

  it('returns empty array when result has no verse_summary', () => {
    expect(verseGroupsFromResult(null, 'both')).toEqual([])
    expect(verseGroupsFromResult({}, 'both')).toEqual([])
  })

  it('handles missing language key gracefully', () => {
    const result = { verse_summary: { cuv: [] } }
    const groups = verseGroupsFromResult(result, 'both')
    expect(groups[1].items).toEqual([])  // esv is missing but returns []
  })
})

// ── buildComparisonRows ──────────────────────────────────────────────────────

describe('buildComparisonRows', () => {
  it('builds merged rows keyed by pk_id', () => {
    const result = {
      verse_summary: {
        cuv: [{ pk_id: 42, text: '中文经文' }],
        esv: [{ pk_id: 42, text: 'English verse' }],
      },
    }
    const rows = buildComparisonRows(result)
    expect(rows).toHaveLength(1)
    expect(rows[0].pk_id).toBe(42)
    expect(rows[0].cuv.text).toBe('中文经文')
    expect(rows[0].esv.text).toBe('English verse')
  })

  it('includes verses that only appear in one language', () => {
    const result = {
      verse_summary: {
        cuv: [{ pk_id: 1, text: 'A' }, { pk_id: 2, text: 'B' }],
        esv: [{ pk_id: 1, text: 'a' }],
      },
    }
    const rows = buildComparisonRows(result)
    expect(rows).toHaveLength(2)
    const row2 = rows.find(r => r.pk_id === 2)
    expect(row2.cuv.text).toBe('B')
    expect(row2.esv).toBeNull()
  })

  it('returns empty array when result has no verse_summary', () => {
    expect(buildComparisonRows(null)).toEqual([])
    expect(buildComparisonRows({})).toEqual([])
  })

  it('uses counterpart to fill missing side', () => {
    const counterpart = { pk_id: 99, text: 'counterpart' }
    const result = {
      verse_summary: {
        cuv: [{ pk_id: 99, text: 'main', counterpart }],
        esv: [],
      },
    }
    const rows = buildComparisonRows(result)
    const row = rows.find(r => r.pk_id === 99)
    expect(row.esv).toEqual(counterpart)
  })
})

// ── formatLoginTime ──────────────────────────────────────────────────────────

describe('formatLoginTime', () => {
  it('returns 刚刚 for timestamps less than 1 minute ago', () => {
    const now = new Date().toISOString()
    expect(formatLoginTime(now)).toBe('刚刚')
  })

  it('returns minutes ago for recent timestamps', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    expect(formatLoginTime(fiveMinAgo)).toBe('5分钟前')
  })

  it('returns hours ago for timestamps within 24h', () => {
    const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString()
    expect(formatLoginTime(threeHoursAgo)).toBe('3小时前')
  })

  it('returns days ago for timestamps within 7 days', () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
    expect(formatLoginTime(twoDaysAgo)).toBe('2天前')
  })

  it('returns M/D format for older timestamps', () => {
    const oldDate = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000)
    const result = formatLoginTime(oldDate.toISOString())
    expect(result).toMatch(/^\d+\/\d+ \d+:\d+$/)
  })

  it('returns empty string for invalid input', () => {
    expect(formatLoginTime('not-a-date')).toBe('')
    expect(formatLoginTime(null)).toBe('')
    expect(formatLoginTime(undefined)).toBe('')
  })
})

// ── getOrCreateVisitorId ─────────────────────────────────────────────────────

describe('getOrCreateVisitorId', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns a non-empty string', () => {
    const id = getOrCreateVisitorId()
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
  })

  it('returns the same ID on repeated calls (persistence)', () => {
    const id1 = getOrCreateVisitorId()
    const id2 = getOrCreateVisitorId()
    expect(id1).toBe(id2)
  })

  it('generates a new ID when storage is cleared', () => {
    const id1 = getOrCreateVisitorId()
    localStorage.clear()
    const id2 = getOrCreateVisitorId()
    // Both valid but may differ (new UUID generated)
    expect(typeof id2).toBe('string')
    expect(id2.length).toBeGreaterThan(0)
  })
})
