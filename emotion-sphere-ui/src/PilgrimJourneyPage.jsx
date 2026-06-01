/**
 * PilgrimJourneyPage — 第六大陆 · 天路客（本仁《天路历程》游戏化）
 * 据近期状态定位你此刻身处天路历程的哪一处。作为今日心镜 overlay，go() 跳转相关功能。
 */
import { useEffect, useState } from 'react'
import { fetchPilgrimCurrent, fetchPilgrimJourney } from './api'
import { getToken } from './auth'

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }

export default function PilgrimJourneyPage({ onClose, go }) {
  const [data, setData] = useState(null)
  const [journey, setJourney] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('now')

  useEffect(() => {
    const t = getToken()
    fetchPilgrimCurrent(t).then(setData).catch(() => {}).finally(() => setLoading(false))
    fetchPilgrimJourney(t).then(r => setJourney(r.visits || [])).catch(() => {})
  }, [])

  const cur = data?.place
  const places = data?.places || []

  return (
    <div style={{ width: '100%', height: '100%', background: 'radial-gradient(circle at 50% 10%, rgba(81,207,102,0.12), #05060c 62%)', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100, background: 'rgba(5,6,12,0.7)', backdropFilter: 'blur(10px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onClose} style={backBtn}>‹</button>
          <div><div style={{ fontSize: 17, fontWeight: 600 }}>天路客</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)' }}>本仁《天路历程》· 你此刻走到哪里</div></div>
        </div>
        <button onClick={() => setTab(tab === 'now' ? 'map' : 'now')} style={pill}>{tab === 'now' ? '路线图' : '当前'}</button>
      </div>

      <div style={{ padding: '8px 16px 110px', maxWidth: 640, margin: '0 auto' }}>
        {loading ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>正在辨认你脚下的路…</div>
          : !cur ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>先做几次打卡/省察，我才能认出你走到了哪里</div>
          : tab === 'now' ? (
            <>
              <div style={{ textAlign: 'center', padding: '10px 0 4px' }}>
                <div style={{ fontSize: 50 }}>{cur.icon}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: cur.color, marginTop: 4 }}>{cur.name}</div>
                <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.45)', letterSpacing: 1 }}>{cur.en}</div>
              </div>
              <div style={{ ...card, background: `linear-gradient(135deg, ${cur.color}1f, rgba(255,255,255,0.02))`, borderColor: `${cur.color}44` }}>
                <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.85)', lineHeight: 1.85 }}>{cur.meaning}</div>
              </div>
              <Row label="危险" color="#ff8787">{cur.danger}</Row>
              <Row label="出路" color="#34c759">{cur.way}</Row>
              {cur.scripture?.text && (
                <div style={{ ...card, borderLeft: `3px solid ${cur.color}88`, borderRadius: 8 }}>
                  <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.82)', fontStyle: 'italic', lineHeight: 1.8 }}>「{cur.scripture.text}」</div>
                  <div style={{ fontSize: 12, color: cur.color, marginTop: 6, textAlign: 'right' }}>—— {cur.scripture.ref}</div>
                </div>
              )}
              {cur.cta && go && (
                <button onClick={() => go(cur.cta.target)} style={{ width: '100%', padding: 14, borderRadius: 12, border: 'none', cursor: 'pointer', fontSize: 15, fontWeight: 700, background: `linear-gradient(135deg, ${cur.color}, #5ac8fa)`, color: '#fff' }}>{cur.cta.label} ›</button>
              )}
            </>
          ) : (
            <div style={{ ...card, padding: '8px 16px 16px' }}>
              {places.map((p, i) => {
                const here = p.key === data.current
                return (
                  <div key={p.key} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: i < places.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none', opacity: here ? 1 : 0.6 }}>
                    <span style={{ fontSize: 22, width: 28, textAlign: 'center' }}>{p.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13.5, fontWeight: here ? 800 : 600, color: here ? p.color : 'rgba(255,255,255,0.8)' }}>{p.name}{here && ' · 你在这里'}</div>
                      <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)' }}>{p.en}</div>
                    </div>
                    {here && <span style={{ fontSize: 11, color: p.color, fontWeight: 700 }}>◉</span>}
                  </div>
                )
              })}
            </div>
          )}
        {tab === 'now' && journey.length > 1 && (
          <div style={{ ...card, marginTop: 4 }}>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 8 }}>你近来的天路足迹</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {journey.slice(0, 8).reverse().map((v, i) => (
                <span key={i} style={{ fontSize: 11, padding: '3px 8px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.6)' }}>{v.name}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ label, color, children }) {
  return <div style={card}><div style={{ fontSize: 11, color: color, fontWeight: 700, marginBottom: 5 }}>{label}</div><div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.75 }}>{children}</div></div>
}
const backBtn = { background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
const pill = { background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 14, padding: '6px 12px', color: 'rgba(255,255,255,0.7)', fontSize: 12, cursor: 'pointer' }
