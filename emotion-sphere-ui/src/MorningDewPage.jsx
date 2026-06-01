/**
 * MorningDewPage — 清晨甘露 / Morning Dew（司布真式每日默想，5/10/15 分钟）
 * 灵修 tab 子页。
 */
import { useEffect, useState } from 'react'
import { fetchDewToday } from './api'
import { getToken } from './auth'

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 18, marginBottom: 12 }
const TIERS = [[5, '5 分钟'], [10, '10 分钟'], [15, '15 分钟']]

export default function MorningDewPage() {
  const [tier, setTier] = useState(10)
  const [dew, setDew] = useState(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => { load(tier) }, [tier])
  async function load(t) { setLoading(true); try { setDew(await fetchDewToday(t, getToken())) } catch (e) { setDew(null) } finally { setLoading(false) } }

  return (
    <div style={{ padding: '14px 16px 90px', maxWidth: 660, margin: '0 auto', color: '#fff' }}>
      <div style={{ ...card, background: 'linear-gradient(135deg, rgba(255,212,59,0.10), rgba(90,200,250,0.06))', textAlign: 'center', padding: '20px 16px' }}>
        <div style={{ fontSize: 26, marginBottom: 6 }}>🌅</div>
        <div style={{ fontSize: 17, fontWeight: 700 }}>清晨甘露</div>
        <div style={{ fontSize: 11.5, color: 'rgba(255,255,255,0.5)', marginTop: 3 }}>司布真式默想 · 每早晨都是新的</div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {TIERS.map(([v, l]) => (
          <button key={v} onClick={() => setTier(v)} style={{ flex: 1, padding: 9, borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700, background: tier === v ? 'rgba(255,212,59,0.20)' : 'rgba(255,255,255,0.05)', color: tier === v ? '#ffd43b' : 'rgba(255,255,255,0.5)' }}>{l}</button>
        ))}
      </div>

      {loading ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>正在汲取今晨的甘露…</div>
        : !dew ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>加载失败，请稍后重试</div>
        : (
          <>
            {dew.scripture?.text && (
              <div style={{ ...card, background: 'rgba(255,212,59,0.06)', borderColor: 'rgba(255,212,59,0.2)' }}>
                <div style={{ fontSize: 15, lineHeight: 1.9, color: 'rgba(255,255,255,0.92)', fontStyle: 'italic' }}>「{dew.scripture.text}」</div>
                <div style={{ fontSize: 12.5, color: '#ffd43b', marginTop: 8, textAlign: 'right' }}>—— {dew.scripture.ref}</div>
              </div>
            )}
            <Sec title="默想">{dew.meditation}</Sec>
            {dew.christ && <Sec title="基督连结" color="#a78bfa">{dew.christ}</Sec>}
            {dew.reflection && <Sec title="反思" color="#5ac8fa"><span style={{ fontStyle: 'italic' }}>{dew.reflection}</span></Sec>}
            {dew.prayer && <Sec title="祷告">{dew.prayer}</Sec>}
            {dew.action && <Sec title="今日信心行动" color="#34c759">{dew.action}</Sec>}
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', textAlign: 'center', marginTop: 8, lineHeight: 1.6 }}>
              愿这滴甘露润泽你一整天。默想不为知识，乃为与主相会。
            </div>
          </>
        )}
    </div>
  )
}

function Sec({ title, children, color }) {
  return (
    <div style={card}>
      <div style={{ fontSize: 11, color: color || '#ffd43b', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.85)', lineHeight: 1.95 }}>{children}</div>
    </div>
  )
}
