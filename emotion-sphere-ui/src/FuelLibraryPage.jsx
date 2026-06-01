/**
 * FuelLibraryPage — 养料库（按「用户困扰」组织，多传统洞见自动组装）
 * 内容只是燃料。今日心镜 overlay。
 */
import { useEffect, useState } from 'react'
import { fetchFuelMeta, fetchFuelPack } from './api'

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }

export default function FuelLibraryPage({ onClose }) {
  const [struggles, setStruggles] = useState([])
  const [pack, setPack] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => { fetchFuelMeta().then(r => setStruggles(r.struggles || [])).catch(() => {}) }, [])
  async function open(key) { setLoading(true); try { const r = await fetchFuelPack(key, 0); setPack(r.pack) } catch (e) {} finally { setLoading(false) } }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <button onClick={pack ? () => setPack(null) : onClose} style={backBtn}>‹</button>
        <div><div style={{ fontSize: 17, fontWeight: 600 }}>养料库</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>按你的困扰取用 · 内容只是燃料</div></div>
      </div>

      <div style={{ padding: '14px 16px 100px', maxWidth: 660, margin: '0 auto' }}>
        {!pack ? (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(139,92,246,0.10), rgba(90,200,250,0.06))' }}>
              <div style={{ fontSize: 13, lineHeight: 1.75, color: 'rgba(255,255,255,0.8)' }}>
                不按作者分区，而按你此刻的困扰组织。选一个，我把经文与多位属灵前辈的洞见为你组装成一份养料。
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10 }}>
              {struggles.map(s => (
                <button key={s.key} onClick={() => open(s.key)} style={{ cursor: 'pointer', borderRadius: 14, padding: '18px 14px', textAlign: 'center', background: `linear-gradient(135deg, ${s.color}22, rgba(255,255,255,0.02))`, border: `1px solid ${s.color}40`, color: '#fff' }}>
                  <div style={{ fontSize: 26, marginBottom: 6 }}>{s.icon}</div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>{s.name}</div>
                </button>
              ))}
            </div>
            {loading && <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)', marginTop: 12 }}>正在组装养料…</div>}
          </>
        ) : (
          <>
            <div style={{ textAlign: 'center', padding: '8px 0 12px' }}>
              <div style={{ fontSize: 40 }}>{pack.icon}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: pack.color, marginTop: 4 }}>{pack.name}</div>
            </div>
            <div style={card}>
              <div style={{ fontSize: 11, color: pack.color, fontWeight: 700, marginBottom: 10 }}>📖 经文</div>
              {pack.scriptures.map((sc, i) => (
                <div key={i} style={{ marginBottom: 10, borderLeft: `3px solid ${pack.color}66`, paddingLeft: 10 }}>
                  <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.85)', lineHeight: 1.8, fontStyle: 'italic' }}>「{sc.text}」</div>
                  <div style={{ fontSize: 11.5, color: pack.color, marginTop: 3 }}>—— {sc.ref}</div>
                </div>
              ))}
            </div>
            <div style={card}>
              <div style={{ fontSize: 11, color: pack.color, fontWeight: 700, marginBottom: 4 }}>💡 多位前辈的洞见</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginBottom: 10 }}>（以下为各传统神学强调的意译概述，非逐字引语）</div>
              {pack.voices.map((v, i) => (
                <div key={i} style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#a78bfa', marginBottom: 3 }}>{v.tag}</div>
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.8 }}>{v.insight}</div>
                </div>
              ))}
            </div>
            {pack.extra && <div style={card}><div style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.85 }}>{pack.extra}</div></div>}
            <div style={{ ...card, borderColor: 'rgba(90,200,250,0.3)' }}>
              <div style={{ fontSize: 11, color: '#5ac8fa', fontWeight: 700, marginBottom: 4 }}>操练</div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.7 }}>{pack.practice}</div>
            </div>
            <div style={{ ...card, borderColor: 'rgba(167,139,250,0.3)' }}>
              <div style={{ fontSize: 11, color: '#a78bfa', fontWeight: 700, marginBottom: 4 }}>祷告</div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.8 }}>{pack.prayer}</div>
            </div>
            <button onClick={() => setPack(null)} style={{ width: '100%', padding: 13, borderRadius: 12, border: 'none', background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.7)', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>选另一个困扰</button>
          </>
        )}
      </div>
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
