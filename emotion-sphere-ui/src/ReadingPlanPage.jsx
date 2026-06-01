/**
 * ReadingPlanPage — 读经计划（结构化通读 + 进度 + 连续天数）
 * 灵修 tab 子页。计划内容来自 readingPlans.js，进度存后端。
 */
import { useEffect, useState } from 'react'
import { PLANS, planById, todayMMDD, seqDayKey } from './readingPlans'
import { fetchReadingStatus, enrollReadingPlan, completeReadingDay, uncompleteReadingDay } from './api'
import { getToken } from './auth'

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }

export default function ReadingPlanPage({ user }) {
  const [planId, setPlanId] = useState('mccheyne')
  const [status, setStatus] = useState(null)
  const [mccheyne, setMccheyne] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const plan = planById(planId)

  useEffect(() => { fetch('/mccheyne.json').then(r => r.json()).then(setMccheyne).catch(() => {}) }, [])
  useEffect(() => { load() }, [planId])

  async function load() {
    const t = getToken(); if (!t) { setLoading(false); return }
    setLoading(true)
    try { setStatus(await fetchReadingStatus(planId, t)) } catch (e) {} finally { setLoading(false) }
  }

  // 今天的 day_key + 经文
  const completed = new Set(status?.completed_keys || [])
  let dayKey = '', refs = []
  if (plan?.kind === 'date') {
    dayKey = todayMMDD()
    const e = mccheyne?.[dayKey]
    if (e) refs = [e.f1, e.f2, e.n1, e.ps].filter(Boolean)
  } else if (plan?.kind === 'seq') {
    let idx = 0
    while (idx < plan.length && completed.has(seqDayKey(idx))) idx++
    if (idx >= plan.length) idx = plan.length - 1
    dayKey = seqDayKey(idx)
    refs = plan.days[idx]?.refs || []
  }
  const todayDone = completed.has(dayKey)
  const pct = plan ? Math.round((status?.completed_count || 0) / plan.length * 100) : 0

  async function toggle() {
    const t = getToken(); if (!t) return
    setBusy(true)
    try {
      if (todayDone) await uncompleteReadingDay(planId, dayKey, t)
      else { await enrollReadingPlan(planId, t); await completeReadingDay(planId, dayKey, t) }
      await load()
    } catch (e) {} finally { setBusy(false) }
  }

  return (
    <div style={{ padding: '14px 16px 90px', maxWidth: 640, margin: '0 auto', color: '#fff' }}>
      {/* 计划选择 */}
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', marginBottom: 14, paddingBottom: 2 }}>
        {PLANS.map(p => (
          <button key={p.id} onClick={() => setPlanId(p.id)} style={{ flexShrink: 0, padding: '8px 14px', borderRadius: 20, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700,
            background: planId === p.id ? `${p.color}28` : 'rgba(255,255,255,0.05)', color: planId === p.id ? p.color : 'rgba(255,255,255,0.55)' }}>{p.name}</button>
        ))}
      </div>

      {plan && (
        <>
          <div style={{ ...card, background: `linear-gradient(135deg, ${plan.color}1c, rgba(255,255,255,0.03))`, borderColor: `${plan.color}44` }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{plan.name}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginTop: 3 }}>{plan.subtitle}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 14 }}>
              <Ring pct={pct} color={plan.color} />
              <div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)' }}>已完成 {status?.completed_count || 0} / {plan.length} 天</div>
                <div style={{ fontSize: 13, color: plan.color, fontWeight: 700, marginTop: 4 }}>🔥 连续 {status?.streak || 0} 天</div>
              </div>
            </div>
          </div>

          <div style={card}>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 10 }}>
              {plan.kind === 'date' ? `今日 · ${dayKey}` : `第 ${parseInt(dayKey.slice(1))} 天`}
            </div>
            {refs.length === 0 ? (
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)' }}>{plan.kind === 'date' && !mccheyne ? '加载中…' : '今日经文加载中…'}</div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {refs.map((r, i) => (
                  <span key={i} style={{ padding: '8px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', fontSize: 13.5 }}>📖 {r}</span>
                ))}
              </div>
            )}
            <button onClick={toggle} disabled={busy || loading} style={{ width: '100%', marginTop: 16, padding: 13, borderRadius: 12, border: 'none', cursor: 'pointer', fontSize: 15, fontWeight: 700,
              background: todayDone ? 'rgba(52,199,89,0.22)' : `linear-gradient(135deg, ${plan.color}, #5ac8fa)`, color: todayDone ? '#34c759' : '#fff' }}>
              {busy ? '处理中…' : todayDone ? '✓ 今日已读（点击撤销）' : '标记今日已读'}
            </button>
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', textAlign: 'center', lineHeight: 1.6 }}>
            读经不为打卡，乃为遇见神。慢慢读，让一句话住在你里面。
          </div>
        </>
      )}
    </div>
  )
}

function Ring({ pct, color }) {
  const r = 26, c = 2 * Math.PI * r, off = c * (1 - pct / 100)
  return (
    <svg width="68" height="68" viewBox="0 0 68 68">
      <circle cx="34" cy="34" r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="6" />
      <circle cx="34" cy="34" r={r} fill="none" stroke={color} strokeWidth="6" strokelinecap="round"
        strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 34 34)" style={{ transition: 'stroke-dashoffset .6s' }} />
      <text x="34" y="38" textAnchor="middle" fill="#fff" fontSize="15" fontWeight="700">{pct}%</text>
    </svg>
  )
}
