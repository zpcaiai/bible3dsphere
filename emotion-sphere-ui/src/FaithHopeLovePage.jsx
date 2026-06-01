/**
 * FaithHopeLovePage — 第七大陆 · 信望爱星系（Faith-Hope-Love Formation Engine）
 * 由 formation 八维推导「信/望/爱/像基督」四指数 + 9 品格评估。今日心镜 overlay。
 */
import { useEffect, useState } from 'react'
import { fetchFormationProfile, evaluateVirtues } from './api'
import { getToken } from './auth'

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }
const INDEX_META = [
  { key: 'faith', name: '信靠', color: '#5ac8fa' },
  { key: 'hope', name: '盼望', color: '#51cf66' },
  { key: 'love', name: '爱人', color: '#ff8787' },
  { key: 'christlikeness', name: '像基督', color: '#a78bfa' },
]

export default function FaithHopeLovePage({ user, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = getToken()
    const uid = user?.id || user?.user_id
    ;(async () => {
      let sv = {}
      try {
        const prof = await fetchFormationProfile(uid, t)
        sv = prof?.state_vector || prof?.profile?.state_vector || prof?.formation?.state_vector || {}
      } catch (e) {}
      try { setData(await evaluateVirtues(sv, t)) } catch (e) { setData({ has_data: false }) }
      finally { setLoading(false) }
    })()
  }, [])

  return (
    <div style={{ width: '100%', height: '100%', background: 'radial-gradient(circle at 50% 8%, rgba(167,139,250,0.18), #05060c 60%)', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, position: 'sticky', top: 0, zIndex: 100, background: 'rgba(5,6,12,0.7)', backdropFilter: 'blur(10px)' }}>
        <button onClick={onClose} style={backBtn}>‹</button>
        <div><div style={{ fontSize: 17, fontWeight: 600 }}>信望爱星系</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)' }}>不是学了多少，而是被塑造成什么样的人</div></div>
      </div>

      <div style={{ padding: '8px 16px 110px', maxWidth: 640, margin: '0 auto' }}>
        {loading ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>正在点亮你的星系…</div>
          : !data?.has_data ? (
            <div style={{ ...card, textAlign: 'center', padding: '30px 16px' }}>
              <div style={{ fontSize: 30, marginBottom: 8 }}>🌌</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>星系尚未点亮</div>
              <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.55)', lineHeight: 1.7 }}>完成一些打卡、省察与诊断，这里会呈现你真实的信望爱成长。</div>
            </div>
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10, marginBottom: 14 }}>
                {INDEX_META.map(m => {
                  const pct = Math.round((data.indices?.[m.key] || 0) * 100)
                  return (
                    <div key={m.key} style={{ borderRadius: 16, padding: '16px 14px', background: `radial-gradient(circle at 30% 25%, ${m.color}33, rgba(255,255,255,0.02))`, border: `1px solid ${m.color}44`, textAlign: 'center' }}>
                      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)' }}>{m.name}</div>
                      <div style={{ fontSize: 30, fontWeight: 800, color: m.color, margin: '4px 0' }}>{pct}</div>
                      <Bar pct={pct} color={m.color} />
                    </div>
                  )
                })}
              </div>

              {data.summary && (
                <div style={{ ...card, background: 'linear-gradient(135deg, rgba(167,139,250,0.12), rgba(90,200,250,0.06))' }}>
                  <div style={{ fontSize: 13.5, lineHeight: 1.85, color: 'rgba(255,255,255,0.86)' }}>{data.summary}</div>
                </div>
              )}

              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', margin: '4px 4px 10px', fontWeight: 700 }}>九个属灵品格</div>
              {(data.virtues || []).map(v => (
                <div key={v.key} style={card}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 14.5, fontWeight: 700 }}>{v.name} <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>{v.en}</span></span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: v.color }}>{Math.round(v.score * 100)} · {v.level}</span>
                  </div>
                  <Bar pct={Math.round(v.score * 100)} color={v.color} />
                  <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.72)', lineHeight: 1.7, marginTop: 10 }}>🌱 {v.grow}</div>
                  <div style={{ fontSize: 12.5, color: '#5ac8fa', marginTop: 6 }}>操练：{v.practice}</div>
                  {v.scripture?.text && (
                    <div style={{ borderLeft: `3px solid ${v.color}88`, paddingLeft: 10, marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.68)', fontStyle: 'italic' }}>
                      「{v.scripture.text}」<span style={{ color: v.color, fontStyle: 'normal' }}> —— {v.scripture.ref}</span>
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
      </div>
    </div>
  )
}

function Bar({ pct, color }) {
  return <div style={{ height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
    <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width .6s' }} /></div>
}
const backBtn = { background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
