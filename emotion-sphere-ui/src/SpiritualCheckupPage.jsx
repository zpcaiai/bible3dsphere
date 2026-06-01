/**
 * SpiritualCheckupPage — 属灵低潮体检（钟马田《属灵低潮》）
 * 「不要听自己，要向自己传讲福音。」入口：今日心镜卡片。
 */
import { useState } from 'react'
import { submitCheckup } from './api'
import { getToken } from './auth'

const SYMPTOMS = [
  { key: 'joylessness', name: '失去喜乐', hint: '提不起劲，喜乐淡了' },
  { key: 'assurance_loss', name: '失去确据', hint: '怀疑自己是否被爱/得救' },
  { key: 'self_condemnation', name: '自我控告', hint: '反复责备自己' },
  { key: 'hopelessness', name: '失去盼望', hint: '看不到出路' },
  { key: 'circumstance', name: '只盯环境', hint: '被处境牵着走' },
  { key: 'dryness', name: '属灵枯干', hint: '读经祷告像例行公事' },
  { key: 'anxiety', name: '焦虑不安', hint: '心里常担忧、绷紧' },
  { key: 'discouragement', name: '灰心丧志', hint: '想放弃' },
]
const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }

export default function SpiritualCheckupPage({ user, onBack, onNeedLogin }) {
  const [vals, setVals] = useState(Object.fromEntries(SYMPTOMS.map(s => [s.key, 0])))
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return }
    setBusy(true); setError('')
    try { const r = await submitCheckup(vals, t); setResult(r); window.scrollTo({ top: 0 }) }
    catch (e) { setError(e.message || '体检失败') } finally { setBusy(false) }
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <button onClick={result ? () => setResult(null) : onBack} style={backBtn}>‹</button>
        <div><div style={{ fontSize: 17, fontWeight: 600 }}>属灵低潮体检</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>钟马田 · 属灵医生</div></div>
      </div>

      <div style={{ padding: '14px 16px 100px', maxWidth: 660, margin: '0 auto' }}>
        {error && <div style={{ ...card, borderColor: 'rgba(255,135,135,0.4)', color: '#ff8787', fontSize: 13 }}>{error}</div>}

        {!result ? (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(218,119,242,0.10), rgba(90,200,250,0.06))' }}>
              <div style={{ fontSize: 13.5, lineHeight: 1.85, color: 'rgba(255,255,255,0.85)' }}>
                「我们大部分的不快乐，是因为<strong style={{ color: '#da77f2' }}>听自己说话</strong>，
                而不是<strong style={{ color: '#34c759' }}>向自己传讲福音</strong>。」—— 钟马田
              </div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 8 }}>诚实地为最近的状态打分（0 = 没有，10 = 很强）。</div>
            </div>
            {SYMPTOMS.map(s => (
              <div key={s.key} style={card}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13.5 }}>
                  <span style={{ fontWeight: 600 }}>{s.name}</span>
                  <span style={{ color: vals[s.key] >= 6 ? '#ff8787' : vals[s.key] >= 4 ? '#ffd43b' : '#34c759', fontWeight: 700 }}>{vals[s.key]}</span>
                </div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>{s.hint}</div>
                <input type="range" min="0" max="10" step="1" value={vals[s.key]} onChange={e => setVals(v => ({ ...v, [s.key]: parseInt(e.target.value) }))} style={{ width: '100%', accentColor: '#da77f2' }} />
              </div>
            ))}
            <button onClick={submit} disabled={busy} style={{ width: '100%', padding: 14, borderRadius: 12, border: 'none', background: 'linear-gradient(135deg, #da77f2, #5ac8fa)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer' }}>{busy ? '诊断中…' : '生成体检报告'}</button>
          </>
        ) : (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(218,119,242,0.12), rgba(52,199,89,0.08))' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>低潮指数</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: result.level === '高' ? '#ff8787' : result.level === '中' ? '#ffd43b' : '#34c759' }}>{Math.round((result.index || 0) * 100)} · {result.level}</span>
              </div>
              <div style={{ fontSize: 13.5, lineHeight: 1.85, color: 'rgba(255,255,255,0.88)' }}>{result.summary}</div>
            </div>

            {result.preach && (
              <div style={{ ...card, borderColor: 'rgba(52,199,89,0.35)', background: 'rgba(52,199,89,0.06)' }}>
                <div style={{ fontSize: 11, color: '#34c759', fontWeight: 700, marginBottom: 6 }}>🔊 向自己传讲</div>
                <div style={{ fontSize: 14.5, lineHeight: 1.8, color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>{result.preach}</div>
              </div>
            )}

            {(result.items || []).map((it, i) => (
              <div key={i} style={card}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#da77f2', marginBottom: 10 }}>{it.name}</div>
                {[['根源', it.root, '#ff8787'], ['所缺的福音', it.deficit, '#ffd43b'], ['操练', it.practice, '#5ac8fa'], ['祷告', it.prayer, '#a78bfa']].map(([k, v, c], j) => v && (
                  <div key={j} style={{ marginBottom: 9 }}>
                    <div style={{ fontSize: 11, color: c, fontWeight: 700, marginBottom: 3 }}>{k}</div>
                    <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.7 }}>{v}</div>
                  </div>
                ))}
                {it.scripture?.text && (
                  <div style={{ borderLeft: '3px solid rgba(167,139,250,0.5)', paddingLeft: 10, fontSize: 12.5, color: 'rgba(255,255,255,0.72)', fontStyle: 'italic', marginTop: 6 }}>
                    「{it.scripture.text}」<span style={{ color: 'rgba(167,139,250,0.85)', fontStyle: 'normal' }}> —— {it.scripture.ref}</span>
                  </div>
                )}
              </div>
            ))}
            <button onClick={() => setResult(null)} style={{ width: '100%', padding: 13, borderRadius: 12, border: 'none', background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.7)', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>再做一次</button>
          </>
        )}
      </div>
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
