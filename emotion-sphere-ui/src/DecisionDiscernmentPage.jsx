/**
 * DecisionDiscernmentPage — 决策辨识（司布真版，Skill 6）
 * 神的旨意不是算出来的，而是在与神同行中辨明的。今日心镜 overlay。
 */
import { useState } from 'react'
import { runDiscernment } from './api'
import { getToken } from './auth'

const SLIDERS = [
  { key: 'faith', name: '需要的信心', color: '#5ac8fa' },
  { key: 'obedience', name: '带来的顺服', color: '#34c759' },
  { key: 'love', name: '出于爱', color: '#ff8787' },
  { key: 'fear', name: '被恐惧驱动', color: '#ffa94d' },
]
const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }
const QLABEL = { greater_faith: '更需要信心', greater_obedience: '更带来顺服', reflects_christ: '更反映基督的爱', fear_driven: '更被恐惧驱动' }

export default function DecisionDiscernmentPage({ user, onBack, onNeedLogin }) {
  const [situation, setSituation] = useState('')
  const [opts, setOpts] = useState([
    { label: '', faith: 5, obedience: 5, love: 5, fear: 5 },
    { label: '', faith: 5, obedience: 5, love: 5, fear: 5 },
  ])
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function setOpt(i, k, v) { setOpts(o => o.map((x, j) => j === i ? { ...x, [k]: v } : x)) }

  async function run() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return }
    if (!opts[0].label.trim() || !opts[1].label.trim()) { setError('请先写下两个选项'); return }
    setBusy(true); setError('')
    try { const r = await runDiscernment({ situation, options: opts, use_ai: true }, t); setResult(r); window.scrollTo({ top: 0 }) }
    catch (e) { setError(e.message || '辨识失败') } finally { setBusy(false) }
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <button onClick={result ? () => setResult(null) : onBack} style={backBtn}>‹</button>
        <div><div style={{ fontSize: 17, fontWeight: 600 }}>决策辨识</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>司布真 · 在与神同行中辨明</div></div>
      </div>

      <div style={{ padding: '14px 16px 100px', maxWidth: 680, margin: '0 auto' }}>
        {error && <div style={{ ...card, borderColor: 'rgba(255,135,135,0.4)', color: '#ff8787', fontSize: 13 }}>{error}</div>}

        {!result ? (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(90,200,250,0.10), rgba(139,92,246,0.06))' }}>
              <div style={{ fontSize: 13, lineHeight: 1.8, color: 'rgba(255,255,255,0.82)' }}>
                这不是收益计算器。我们不问「哪条路更划算」，而问：<strong style={{ color: '#5ac8fa' }}>哪条路更需要信心、更带来顺服、更少被恐惧驱动</strong>。
              </div>
            </div>
            <div style={card}>
              <label style={lbl}>我正在面对的决定</label>
              <textarea value={situation} onChange={e => setSituation(e.target.value)} rows={2} placeholder="如：要不要换城市 / 接受这份工作 / 结束这段关系…" style={inp} />
            </div>
            {opts.map((o, i) => (
              <div key={i} style={card}>
                <div style={{ fontSize: 12, color: '#a78bfa', fontWeight: 700, marginBottom: 8 }}>选项 {String.fromCharCode(65 + i)}</div>
                <input value={o.label} onChange={e => setOpt(i, 'label', e.target.value)} placeholder={`第 ${i + 1} 个选项是…`} style={inp} />
                {SLIDERS.map(s => (
                  <div key={s.key} style={{ marginTop: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <span style={{ color: 'rgba(255,255,255,0.72)' }}>{s.name}</span>
                      <span style={{ color: s.color, fontWeight: 700 }}>{o[s.key]}</span>
                    </div>
                    <input type="range" min="0" max="10" step="1" value={o[s.key]} onChange={e => setOpt(i, s.key, parseInt(e.target.value))} style={{ width: '100%', accentColor: s.color }} />
                  </div>
                ))}
              </div>
            ))}
            <button onClick={run} disabled={busy} style={{ width: '100%', padding: 14, borderRadius: 12, border: 'none', background: 'linear-gradient(135deg, #5ac8fa, #8b5cf6)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer' }}>{busy ? '辨明中…' : '开始辨识'}</button>
          </>
        ) : (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(52,199,89,0.10), rgba(90,200,250,0.08))' }}>
              <div style={{ fontSize: 13.5, lineHeight: 1.85, color: 'rgba(255,255,255,0.88)' }}>{result.summary}</div>
            </div>

            <div style={{ ...card }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 12 }}>司布真的提问</div>
              {Object.entries(QLABEL).map(([k, label]) => {
                const idx = result.questions?.[k]
                const ans = idx === 0 || idx === 1 ? result.options[idx]?.label : '两者相近'
                const warn = k === 'fear_driven'
                return (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.6)', flexShrink: 0 }}>{label}</span>
                    <span style={{ fontSize: 12.5, fontWeight: 700, color: warn ? '#ffa94d' : '#5ac8fa', textAlign: 'right' }}>{ans}</span>
                  </div>
                )
              })}
            </div>

            <div style={{ ...card, borderColor: 'rgba(52,199,89,0.3)' }}>
              <div style={{ fontSize: 11, color: '#34c759', fontWeight: 700, marginBottom: 6 }}>信心建议</div>
              <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.85)', lineHeight: 1.8 }}>{result.recommendation}</div>
            </div>

            {(result.blind_spots || []).length > 0 && (
              <div style={card}>
                <div style={{ fontSize: 11, color: '#ffa94d', fontWeight: 700, marginBottom: 6 }}>盲点提醒</div>
                {result.blind_spots.map((b, i) => <div key={i} style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.78)', lineHeight: 1.7, marginBottom: 5 }}>· {b}</div>)}
              </div>
            )}
            {(result.idols || []).length > 0 && (
              <div style={card}>
                <div style={{ fontSize: 11, color: '#ff8787', fontWeight: 700, marginBottom: 6 }}>潜在偶像</div>
                {result.idols.map((b, i) => <div key={i} style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.78)', lineHeight: 1.7, marginBottom: 5 }}>· {b}</div>)}
              </div>
            )}

            <div style={card}>
              <div style={{ fontSize: 11, color: '#a78bfa', fontWeight: 700, marginBottom: 6 }}>祷告方向</div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.8 }}>{result.prayer}</div>
            </div>
            {result.scripture?.text && (
              <div style={{ ...card, borderLeft: '3px solid rgba(167,139,250,0.5)', borderRadius: 8 }}>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.78)', fontStyle: 'italic' }}>「{result.scripture.text}」<span style={{ color: '#a78bfa', fontStyle: 'normal' }}> —— {result.scripture.ref}</span></div>
              </div>
            )}
            <button onClick={() => setResult(null)} style={{ width: '100%', padding: 13, borderRadius: 12, border: 'none', background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.7)', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>再辨识一次</button>
          </>
        )}
      </div>
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
const lbl = { display: 'block', fontSize: 12, color: 'rgba(255,255,255,0.6)', marginBottom: 6 }
const inp = { width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 13, resize: 'vertical' }
