/**
 * DailyDevotionPage — 晨恩日新 灵修日历
 *
 * 展示「晨恩日新——福音灵修日引」（保罗·区普）按日历日期组织的365篇内容。
 * 支持整体朗读和分段朗读（与镜鉴 tab 保持一致）。
 */

import { useEffect, useMemo, useState } from 'react'
import { API_BASE } from './api.js'
import { TTSButton, TTSFullBar } from './useGlobalAudio.jsx'

// ── Chinese month / day labels ────────────────────────────────────────────────
const MONTH_LABELS = ['一月','二月','三月','四月','五月','六月',
                      '七月','八月','九月','十月','十一月','十二月']
const WEEKDAY_LABELS = ['日','一','二','三','四','五','六']

// ── Calendar helpers ──────────────────────────────────────────────────────────
function daysInMonth(year, month) {   // month: 1-12
  return new Date(year, month, 0).getDate()
}
function firstWeekday(year, month) {  // 0=Sun
  return new Date(year, month - 1, 1).getDay()
}

// ── Styles ────────────────────────────────────────────────────────────────────
const S = {
  page: {
    position: 'relative',
    minHeight: '100vh',
    background: 'linear-gradient(160deg,#0d1117 0%,#0a1628 60%,#060d1f 100%)',
    color: '#fff',
    fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
    overflowY: 'auto',
    paddingBottom: 40,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '16px 16px 8px',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
    position: 'sticky',
    top: 0,
    zIndex: 10,
    background: 'rgba(13,17,23,0.92)',
    backdropFilter: 'blur(12px)',
  },
  backBtn: {
    background: 'none',
    border: 'none',
    color: 'rgba(255,255,255,0.6)',
    fontSize: 20,
    cursor: 'pointer',
    padding: '2px 6px',
    lineHeight: 1,
  },
  titleBlock: {
    flex: 1,
  },
  titleMain: {
    fontSize: 16,
    fontWeight: 700,
    color: '#fff',
    margin: 0,
  },
  titleSub: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.4)',
    marginTop: 1,
  },
  // Calendar
  calWrap: {
    margin: '12px 16px 0',
    background: 'rgba(255,255,255,0.04)',
    borderRadius: 14,
    overflow: 'hidden',
    border: '1px solid rgba(255,255,255,0.07)',
  },
  calNav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 14px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  calNavBtn: {
    background: 'none',
    border: 'none',
    color: 'rgba(255,255,255,0.55)',
    fontSize: 18,
    cursor: 'pointer',
    padding: '2px 8px',
    borderRadius: 6,
  },
  calMonthLabel: {
    fontSize: 14,
    fontWeight: 600,
    color: '#fff',
  },
  calGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(7,1fr)',
    padding: '6px 8px 8px',
    gap: 2,
  },
  calWeekday: {
    textAlign: 'center',
    fontSize: 10,
    color: 'rgba(255,255,255,0.3)',
    padding: '2px 0 4px',
  },
  calDay: (isToday, isSelected, hasContent) => ({
    textAlign: 'center',
    padding: '5px 0',
    borderRadius: 8,
    fontSize: 12,
    cursor: hasContent ? 'pointer' : 'default',
    color: isSelected ? '#000'
          : isToday ? '#34c759'
          : hasContent ? 'rgba(255,255,255,0.85)'
          : 'rgba(255,255,255,0.15)',
    background: isSelected ? '#34c759'
              : isToday ? 'rgba(52,199,89,0.12)'
              : 'transparent',
    fontWeight: isToday || isSelected ? 700 : 400,
    border: isToday && !isSelected ? '1px solid rgba(52,199,89,0.4)' : '1px solid transparent',
    transition: 'background 0.15s',
  }),
  // Devotion card
  card: {
    margin: '14px 16px 0',
    background: 'rgba(255,255,255,0.04)',
    borderRadius: 16,
    border: '1px solid rgba(255,255,255,0.07)',
    overflow: 'hidden',
  },
  cardHeader: {
    padding: '14px 16px 12px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    background: 'rgba(52,199,89,0.05)',
  },
  cardDate: {
    fontSize: 11,
    color: 'rgba(52,199,89,0.8)',
    marginBottom: 6,
    fontWeight: 600,
    letterSpacing: 1,
  },
  cardBody: {
    padding: '14px 16px',
  },
  sectionLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    fontWeight: 700,
    color: 'rgba(255,255,255,0.4)',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 6,
    marginTop: 14,
  },
  quoteBox: {
    background: 'rgba(255,215,0,0.06)',
    borderLeft: '3px solid rgba(255,215,0,0.4)',
    borderRadius: '0 8px 8px 0',
    padding: '10px 12px',
    fontSize: 14,
    lineHeight: 1.65,
    color: 'rgba(255,255,255,0.9)',
    fontStyle: 'italic',
    marginBottom: 2,
  },
  bodyText: {
    fontSize: 14,
    lineHeight: 1.75,
    color: 'rgba(255,255,255,0.82)',
    whiteSpace: 'pre-wrap',
  },
  scriptureBox: {
    background: 'rgba(90,200,250,0.08)',
    borderRadius: 8,
    padding: '8px 12px',
    fontSize: 13,
    color: 'rgba(90,200,250,0.9)',
    marginTop: 2,
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px 20px',
    color: 'rgba(255,255,255,0.3)',
    fontSize: 14,
  },
}

// ── Main component ────────────────────────────────────────────────────────────

// ── ScriptureVerses: fetch & display full verse text ─────────────────────────
const SV = {
  wrapper: { marginTop: 10 },
  loading: { fontSize: 12, color: 'rgba(90,200,250,0.5)', padding: '6px 0' },
  verseRow: {
    display: 'flex', gap: 8, padding: '5px 0',
    borderBottom: '1px solid rgba(90,200,250,0.08)', alignItems: 'flex-start',
  },
  verseNum: {
    fontSize: 11, fontWeight: 700, color: 'rgba(90,200,250,0.55)',
    minWidth: 22, paddingTop: 2, flexShrink: 0,
  },
  verseText: { fontSize: 14, lineHeight: 1.75, color: 'rgba(255,255,255,0.88)' },
  refLabel: {
    fontSize: 11, color: 'rgba(90,200,250,0.55)', marginBottom: 6,
    fontWeight: 600, letterSpacing: '0.04em',
  },
}

function ScriptureVerses({ scriptureRef }) {
  const [verses, setVerses] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!scriptureRef) return
    setLoading(true)
    setVerses(null)
    setError(null)
    fetch(`${API_BASE}/scripture?ref=${encodeURIComponent(scriptureRef)}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok && d.verses?.length) setVerses(d)
        else setError(d.error || '暂无经文')
      })
      .catch(() => setError('加载失败'))
      .finally(() => setLoading(false))
  }, [scriptureRef])

  if (loading) return <div style={SV.loading}>加载经文中…</div>
  if (error) return <div style={SV.loading}>{error}</div>
  if (!verses) return null

  const { book, chapter, verses: list } = verses
  const ttsAll = list.map(v => v.text).join('　')

  return (
    <div style={SV.wrapper}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <div style={SV.refLabel}>{book} {chapter}章 · 共{list.length}节</div>
        <div style={{ flex: 1 }} />
        <TTSButton text={ttsAll} />
      </div>
      {list.map(v => (
        <div key={v.verse} style={SV.verseRow}>
          <span style={SV.verseNum}>{v.verse}</span>
          <span style={SV.verseText}>{v.text}</span>
        </div>
      ))}
    </div>
  )
}

export default function DailyDevotionPage({ onBack }) {
  const today = new Date()
  const todayKey = `${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`

  const [devotions, setDevotions] = useState(null)
  const [loading, setLoading] = useState(true)
  const [viewMonth, setViewMonth] = useState(today.getMonth() + 1) // 1-12
  const [viewYear]  = useState(today.getFullYear())
  const [selectedKey, setSelectedKey] = useState(todayKey)

  // Load devotions.json from public folder
  useEffect(() => {
    fetch('/devotions.json')
      .then(r => r.json())
      .then(data => {
        setDevotions(data.devotions || data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  // Calendar grid cells for current month
  const calCells = useMemo(() => {
    const total = daysInMonth(viewYear, viewMonth)
    const offset = firstWeekday(viewYear, viewMonth)
    const cells = []
    for (let i = 0; i < offset; i++) cells.push(null)
    for (let d = 1; d <= total; d++) cells.push(d)
    return cells
  }, [viewYear, viewMonth])

  const devotion = devotions?.[selectedKey]

  function buildTTSText(d) {
    if (!d) return ''
    const parts = []
    if (d.quote) parts.push(d.quote)
    if (d.body) parts.push(d.body)
    if (d.scripture) parts.push('更多的信息和勉励：' + d.scripture)
    return parts.join('\n\n')
  }

  if (loading) {
    return (
      <div style={S.page}>
        <div style={{ ...S.emptyState, paddingTop: 80 }}>
          <div style={{ fontSize: 28, marginBottom: 12 }}>📖</div>
          加载灵修内容…
        </div>
      </div>
    )
  }

  if (!devotions) {
    return (
      <div style={S.page}>
        <div style={S.emptyState}>
          <div style={{ fontSize: 28, marginBottom: 12 }}>😔</div>
          灵修内容暂时无法加载
        </div>
      </div>
    )
  }

  return (
    <div style={S.page}>
      {/* ── Header ── */}
      <div style={S.header}>
        {onBack && (
          <button style={S.backBtn} onClick={onBack}>‹</button>
        )}
        <div style={S.titleBlock}>
          <div style={S.titleMain}>晨恩日新</div>
          <div style={S.titleSub}>保罗·区普 · 福音灵修日引 · 365天</div>
        </div>
        <div style={{ fontSize: 11, color: 'rgba(52,199,89,0.8)', fontWeight: 600 }}>
          {MONTH_LABELS[viewMonth-1]}
        </div>
      </div>

      {/* ── Calendar ── */}
      <div style={S.calWrap}>
        <div style={S.calNav}>
          <button
            style={S.calNavBtn}
            onClick={() => setViewMonth(m => m === 1 ? 12 : m - 1)}
          >‹</button>
          <span style={S.calMonthLabel}>{MONTH_LABELS[viewMonth-1]}</span>
          <button
            style={S.calNavBtn}
            onClick={() => setViewMonth(m => m === 12 ? 1 : m + 1)}
          >›</button>
        </div>

        <div style={S.calGrid}>
          {WEEKDAY_LABELS.map(w => (
            <div key={w} style={S.calWeekday}>{w}</div>
          ))}
          {calCells.map((day, i) => {
            if (!day) return <div key={`e${i}`} />
            const key = `${String(viewMonth).padStart(2,'0')}-${String(day).padStart(2,'0')}`
            const isToday = key === todayKey
            const isSel = key === selectedKey
            const has = !!devotions[key]
            return (
              <div
                key={key}
                style={S.calDay(isToday, isSel, has)}
                onClick={() => has && setSelectedKey(key)}
              >
                {day}
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Devotion Card ── */}
      {devotion ? (
        <div style={S.card}>
          <div style={S.cardHeader}>
            <div style={S.cardDate}>
              {MONTH_LABELS[devotion.month - 1]} · 第 {devotion.day} 日
            </div>

            {/* 整体朗读 */}
            <TTSFullBar
              buildText={() => buildTTSText(devotion)}
              label="整体朗读"
            />
          </div>

          <div style={S.cardBody}>

            {/* 金句 */}
            {devotion.quote && (
              <>
                <div style={S.sectionLabel}>
                  <span>✨ 今日金句</span>
                  <TTSButton text={devotion.quote} />
                </div>
                <div style={S.quoteBox}>{devotion.quote}</div>
              </>
            )}

            {/* 正文 */}
            {devotion.body && (
              <>
                <div style={{ ...S.sectionLabel, marginTop: 18 }}>
                  <span>📖 灵修正文</span>
                  <TTSButton text={devotion.body} />
                </div>
                <div style={S.bodyText}>{devotion.body}</div>
              </>
            )}

            {/* 经文参考 — 完整经文 */}
            {devotion.scripture && (
              <>
                <div style={{ ...S.sectionLabel, marginTop: 18 }}>
                  <span>📜 更多信息与勉励</span>
                </div>
                <div style={{ ...S.scriptureBox, paddingBottom: 4 }}>
                  <div style={{ fontSize: 12, color: 'rgba(90,200,250,0.7)', marginBottom: 6, fontStyle: 'italic' }}>
                    {devotion.scripture}
                  </div>
                  <ScriptureVerses scriptureRef={devotion.scripture} />
                </div>
              </>
            )}

          </div>
        </div>
      ) : (
        <div style={S.emptyState}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📅</div>
          {selectedKey
            ? '该日期暂无灵修内容'
            : '请选择日期查看灵修内容'}
        </div>
      )}
    </div>
  )
}
