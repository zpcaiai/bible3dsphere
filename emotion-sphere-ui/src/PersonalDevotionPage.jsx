/**
 * PersonalDevotionPage — 千人千面每日灵修 + 麦琴读经计划
 *
 * 根据用户灵命状态生成个性化灵修内容，并显示今日麦琴读经计划章节。
 */

import React, { useEffect, useState } from 'react'
import { TTSButton, TTSFullBar } from './useGlobalAudio.jsx'
import { API_BASE } from './api.js'

// ── Mobile detection (responsive layout) ─────────────────────────────────────
function useIsMobile() {
  const [mobile, setMobile] = React.useState(() => window.innerWidth < 480)
  React.useEffect(() => {
    const fn = () => setMobile(window.innerWidth < 480)
    window.addEventListener('resize', fn)
    return () => window.removeEventListener('resize', fn)
  }, [])
  return mobile
}



const API = API_BASE

// ── ScriptureVerses: fetch & display full chapter text ────────────────────────
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
    fetch(`${API}/scripture?ref=${encodeURIComponent(scriptureRef)}`)
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

  return (
    <div style={SV.wrapper}>
      <div style={SV.refLabel}>{book} {chapter}章 · 共{list.length}节</div>
      {list.map(v => (
        <div key={v.verse} style={SV.verseRow}>
          <span style={SV.verseNum}>{v.verse}</span>
          <span style={SV.verseText}>{v.text}</span>
        </div>
      ))}
    </div>
  )
}

// ── ExpandableScripture: collapsible full chapter ─────────────────────────────
function ExpandableScripture({ scriptureRef }) {
  const [expanded, setExpanded] = useState(false)
  if (!scriptureRef) return null
  return (
    <div style={{ marginTop: 8 }}>
      <button
        onClick={() => setExpanded(v => !v)}
        style={{
          background: 'rgba(90,200,250,0.08)', border: '1px solid rgba(90,200,250,0.2)',
          borderRadius: 20, color: 'rgba(90,200,250,0.85)', fontSize: 12,
          padding: '4px 12px', cursor: 'pointer', fontWeight: 600,
        }}
      >
        {expanded ? '▲ 收起经文' : '▼ 展开全章经文'}
      </button>
      {expanded && <ScriptureVerses scriptureRef={scriptureRef} />}
    </div>
  )
}

// ── McCheyne reading plan (loaded from public/mccheyne.json) ──────────────────
function useMcCheyne() {
  const [plan, setPlan] = useState(null)
  useEffect(() => {
    fetch('/mccheyne.json')
      .then(r => r.json())
      .then(setPlan)
      .catch(() => setPlan({}))
  }, [])

  const today = new Date()
  const key = `${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  return plan ? (plan[key] || null) : undefined
}

// ── Styles ────────────────────────────────────────────────────────────────────
const bg = 'linear-gradient(160deg,#0d1117 0%,#0a1628 60%,#060d1f 100%)'

const S = {
  page: { minHeight: '100%', background: bg, color: '#fff', fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif', paddingBottom: 'calc(env(safe-area-inset-bottom) + 20px)' },
  section: { margin: '10px 12px 0', borderRadius: 14, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' },
  sectionHeader: (color) => ({ padding: '10px 14px', background: color || 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', rowGap: 6 }),
  sectionBody: { padding: '14px 16px' },
  label: { fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.4)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 },
  verse: { background: 'rgba(255,215,0,0.07)', borderLeft: '3px solid rgba(255,215,0,0.45)', borderRadius: '0 8px 8px 0', padding: '10px 12px', fontSize: 14, lineHeight: 1.7, color: 'rgba(255,255,255,0.92)', fontStyle: 'italic' },
  body: { fontSize: 13, lineHeight: 1.75, color: 'rgba(255,255,255,0.82)', whiteSpace: 'pre-wrap' },
  prayer: { fontSize: 13, lineHeight: 1.8, color: 'rgba(255,200,100,0.85)', fontStyle: 'italic', background: 'rgba(255,159,10,0.07)', borderRadius: 10, padding: '10px 12px' },
  stageTag: (key) => ({
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
    background: key === 'blind_spot' ? 'rgba(248,113,113,0.18)' : key === 'growing' ? 'rgba(251,191,36,0.18)' : 'rgba(74,222,128,0.18)',
    color: key === 'blind_spot' ? '#f87171' : key === 'growing' ? '#fbbf24' : '#4ade80',
    border: `1px solid ${key === 'blind_spot' ? 'rgba(248,113,113,0.3)' : key === 'growing' ? 'rgba(251,191,36,0.3)' : 'rgba(74,222,128,0.3)'}`,
  }),
  mcChapter: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(90,200,250,0.1)', border: '1px solid rgba(90,200,250,0.2)', borderRadius: 20, fontSize: 13, color: '#5ac8fa', margin: '4px 4px 4px 0', flexShrink: 0 },
}

// ── Personal devotion card ────────────────────────────────────────────────────
function PersonalCard({ user, token }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Cache key for today
  const cacheKey = `personal_devot_${new Date().toISOString().slice(0, 10)}_${user?.email || ''}`

  useEffect(() => {
    if (!user) return
    // Check localStorage cache
    try {
      const cached = localStorage.getItem(cacheKey)
      if (cached) {
        setData(JSON.parse(cached))
        return
      }
    } catch { /**/ }

    setLoading(true)
    fetch(`${API}/daily-devotion-personal`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => {
        setData(d)
        try { localStorage.setItem(cacheKey, JSON.stringify(d)) } catch { /**/ }
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [user?.email])

  if (!user) {
    return (
      <div style={{ ...S.section, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 16px', textAlign: 'center', gap: 8 }}>
        <div style={{ fontSize: 32 }}>🌟</div>
        <div style={{ fontSize: 15, color: 'rgba(255,255,255,0.8)' }}>登录后查看个性化灵修</div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>根据你的灵命状态每天生成专属灵修内容</div>
      </div>
    )
  }

  if (loading) {
    return (
      <div style={S.section}>
        <div style={{ padding: '32px 16px', textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>
          <div style={{ fontSize: 28, marginBottom: 10 }}>✨</div>
          正在为你生成今日灵修…
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={S.section}>
        <div style={{ padding: '24px 16px', textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>
          {error ? `加载失败: ${error}` : '暂无个性化灵修内容'}
        </div>
      </div>
    )
  }

  const ttsText = [
    `今日聚焦：${data.theme}`,
    `${data.verse_ref}——${data.verse_text}`,
    data.devotion_text,
    `今日祷告：${data.prayer_text}`,
  ].join('\n\n')

  return (
    <div style={S.section}>
      {/* Header */}
      <div style={S.sectionHeader('rgba(90,200,250,0.07)')}>
        <span style={{ fontSize: 18 }}>🌟</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'rgba(255,255,255,0.95)' }}>今日个性化灵修</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>
            聚焦 · {data.theme}
          </div>
        </div>
        <span style={S.stageTag(data.stage)}>{data.stage_icon} {data.stage_label}</span>
        <TTSFullBar buildText={() => ttsText} label="朗读" />
      </div>

      <div style={S.sectionBody}>
        {/* Verse */}
        <div style={S.label}>
          <span>✨ 今日经文</span>
          <TTSButton text={`${data.verse_ref}——${data.verse_text}`} />
        </div>
        <div style={{ marginBottom: 4, fontSize: 11, color: 'rgba(90,200,250,0.7)', fontWeight: 600 }}>{data.verse_ref}</div>
        <div style={S.verse}>「{data.verse_text}」</div>
        <ScriptureVerses scriptureRef={data.verse_ref} />

        {/* Devotion text */}
        <div style={{ ...S.label, marginTop: 16 }}>
          <span>📖 灵修默想</span>
          <TTSButton text={data.devotion_text} />
        </div>
        <div style={S.body}>{data.devotion_text}</div>

        {/* Prayer */}
        <div style={{ ...S.label, marginTop: 16 }}>
          <span>🙏 今日祷告</span>
          <TTSButton text={data.prayer_text} />
        </div>
        <div style={S.prayer}>{data.prayer_text}</div>

        {/* Stage action */}
        <div style={{ marginTop: 14, padding: '10px 12px', background: 'rgba(255,255,255,0.04)', borderRadius: 10, fontSize: 13, color: 'rgba(255,255,255,0.65)' }}>
          💡 <strong style={{ color: 'rgba(255,255,255,0.85)' }}>今日可行一步</strong> — {data.stage_action}
        </div>
      </div>
    </div>
  )
}

// ── McCheyne reading plan card ────────────────────────────────────────────────
function McCheyneCard() {
  const reading = useMcCheyne()

  const today = new Date()
  const dayStr = `${today.getMonth() + 1}月${today.getDate()}日`

  const chapters = reading
    ? [
        { label: '家庭晨读', icon: '🌅', ref: reading.f1, type: 'ot' },
        { label: '家庭晚读', icon: '🌙', ref: reading.f2, type: 'ot' },
        { label: '个人读经 (新约)', icon: '✝️', ref: reading.n1, type: 'nt' },
        { label: '个人读经 (诗篇)', icon: '🎵', ref: reading.ps, type: 'ps' },
      ]
    : []

  const ttsFull = reading
    ? `今日麦琴读经计划，${dayStr}。家庭晨读：${reading.f1}。家庭晚读：${reading.f2}。个人新约：${reading.n1}。个人诗篇：${reading.ps}。`
    : ''

  return (
    <div style={S.section}>
      {/* Header */}
      <div style={S.sectionHeader('rgba(52,199,89,0.06)')}>
        <span style={{ fontSize: 18 }}>📖</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'rgba(255,255,255,0.95)' }}>麦琴读经计划</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>{dayStr} · 麦契尼一年读经计划</div>
        </div>
        {reading && <TTSFullBar buildText={() => ttsFull} label="朗读" />}
      </div>

      <div style={S.sectionBody}>
        {reading === undefined ? (
          <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>加载中…</div>
        ) : reading === null ? (
          <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>今日读经计划暂无数据</div>
        ) : (
          <>
            {/* Chapter grid */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
              {chapters.map(ch => (
                <div key={ch.label} style={S.mcChapter}>
                  <span>{ch.icon}</span>
                  <span style={{ fontWeight: 600 }}>{ch.ref}</span>
                  <TTSButton text={`${ch.label}：${ch.ref}`} />
                </div>
              ))}
            </div>

            {/* Detailed list */}
            {chapters.map(ch => (
              <div key={ch.label} style={{ marginBottom: 12 }}>
                <div style={S.label}>
                  <span>{ch.icon} {ch.label}</span>
                  <TTSButton text={`${ch.label}：${ch.ref}`} />
                </div>
                <div style={{ fontSize: 15, fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>{ch.ref}</div>
                <ExpandableScripture scriptureRef={ch.ref} />
              </div>
            ))}

            <div style={{ marginTop: 8, padding: '8px 12px', background: 'rgba(52,199,89,0.06)', borderRadius: 10, fontSize: 12, color: 'rgba(52,199,89,0.7)', textAlign: 'center' }}>
              麦契尼一年读经计划 · 每日4章 · 一年读完圣经
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function PersonalDevotionPage({ user, token }) {
  return (
    <div style={S.page}>
      <PersonalCard user={user} token={token} />
      <McCheyneCard />
    </div>
  )
}
