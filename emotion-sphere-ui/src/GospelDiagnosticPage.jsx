/**
 * GospelDiagnosticPage — 福音诊断室 / Gospel Diagnostic Lab
 * 钟马田诊断（挖到偶像与不信）+ 司布真牧养（带回基督）。
 * 入口：今日心镜 (SoulDashboard) 卡片。
 */
import { useState } from 'react'
import { diagnoseGospel, fetchGospelHistory } from './api'
import { getToken } from './auth'

const STEPS = [
  { key: 'event',   q: '发生了什么事？', ph: '客观地描述这件事，像在跟朋友讲…' },
  { key: 'feeling', q: '你感受到什么？', ph: '焦虑、愤怒、羞耻、悲伤、空虚…' },
  { key: 'want',    q: '你真正想要的是什么？', ph: '在这感受底下，你渴望得到 / 留住什么？' },
  { key: 'fear',    q: '你最害怕失去什么？', ph: '如果它没了，你会崩溃的是什么？' },
  { key: 'belief',  q: '这让你相信了关于神 / 自己的什么？', ph: '诚实地写，哪怕是「神不管我」…' },
]
const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }

export default function GospelDiagnosticPage({ user, onBack, onNeedLogin }) {
  const [view, setView] = useState('form')   // form | result | history
  const [step, setStep] = useState(0)
  const [vals, setVals] = useState({ event: '', feeling: '', want: '', fear: '', belief: '' })
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function set(k, v) { setVals(s => ({ ...s, [k]: v })) }
  const cur = STEPS[step]

  async function submit() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return }
    setBusy(true); setError('')
    try { const r = await diagnoseGospel({ ...vals, use_ai: true }, t); setResult(r); setView('result'); window.scrollTo({ top: 0 }) }
    catch (e) { setError(e.message || '诊断失败') } finally { setBusy(false) }
  }
  async function openHistory() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return }
    try { const r = await fetchGospelHistory(t); setHistory(r.items || []); setView('history') } catch (e) { setError(e.message) }
  }
  function restart() { setVals({ event: '', feeling: '', want: '', fear: '', belief: '' }); setStep(0); setResult(null); setView('form') }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onBack} style={backBtn}>‹</button>
          <div><div style={{ fontSize: 17, fontWeight: 600 }}>福音诊断室</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>钟马田诊断 · 司布真牧养</div></div>
        </div>
        <button onClick={view === 'history' ? () => setView('form') : openHistory} style={pill}>{view === 'history' ? '← 返回' : '病历'}</button>
      </div>

      <div style={{ padding: '14px 16px 100px', maxWidth: 680, margin: '0 auto' }}>
        {error && <div style={{ ...card, borderColor: 'rgba(255,135,135,0.4)', color: '#ff8787', fontSize: 13 }}>{error}</div>}

        {view === 'form' && (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(139,92,246,0.12), rgba(90,200,250,0.06))' }}>
              <div style={{ fontSize: 13, lineHeight: 1.75, color: 'rgba(255,255,255,0.82)' }}>
                症状不是问题。让我们一层层往下看——情绪揭示信念，信念揭示偶像，偶像揭示不信；
                而福音，正是对付不信的良药。
              </div>
            </div>
            <div style={card}>
              <div style={{ fontSize: 11, color: '#a78bfa', fontWeight: 700, marginBottom: 8 }}>第 {step + 1} / {STEPS.length} 问</div>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>{cur.q}</div>
              <textarea value={vals[cur.key]} onChange={e => set(cur.key, e.target.value)} rows={3} placeholder={cur.ph}
                style={{ width: '100%', boxSizing: 'border-box', padding: '12px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 14, resize: 'vertical' }} />
              <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                {step > 0 && <button onClick={() => setStep(step - 1)} style={{ ...btn('rgba(255,255,255,0.08)'), color: 'rgba(255,255,255,0.7)', flex: 1 }}>上一步</button>}
                {step < STEPS.length - 1
                  ? <button onClick={() => setStep(step + 1)} style={{ ...btn('linear-gradient(135deg,#8b5cf6,#5ac8fa)'), flex: 2 }}>下一步</button>
                  : <button onClick={submit} disabled={busy} style={{ ...btn('linear-gradient(135deg,#8b5cf6,#5ac8fa)'), flex: 2 }}>{busy ? '诊断中…' : '生成属灵病历'}</button>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 5, justifyContent: 'center' }}>
              {STEPS.map((_, i) => <div key={i} style={{ width: 7, height: 7, borderRadius: '50%', background: i <= step ? '#a78bfa' : 'rgba(255,255,255,0.18)' }} />)}
            </div>
          </>
        )}

        {view === 'result' && result && (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(52,199,89,0.10), rgba(139,92,246,0.08))' }}>
              <div style={{ fontSize: 11, color: 'rgba(52,199,89,0.8)', fontWeight: 700, marginBottom: 8 }}>✦ 属灵病历</div>
              <div style={{ fontSize: 13.5, lineHeight: 1.85, color: 'rgba(255,255,255,0.88)' }}>{result.summary}</div>
            </div>

            {/* 钟马田 · 诊断 */}
            <div style={{ ...card, borderColor: 'rgba(218,119,242,0.3)' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#da77f2', marginBottom: 12 }}>🔬 钟马田 · 诊断（挖到根）</div>
              {[['情绪', result.emotion], ['渴望', result.desire], ['害怕失去', result.fear_named], ['偶像', result.idol_name], ['底层的不信', result.unbelief]].map(([k, v], i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 9 }}>
                  <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', width: 64, flexShrink: 0, paddingTop: 2 }}>{k}</span>
                  <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)', lineHeight: 1.6 }}>{v}</span>
                </div>
              ))}
            </div>

            {/* 司布真 · 牧养 */}
            <div style={{ ...card, borderColor: 'rgba(255,212,59,0.3)' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#ffd43b', marginBottom: 12 }}>🕊 司布真 · 牧养（带回基督）</div>
              <Block label="福音真理">{result.gospel_truth}</Block>
              {result.scripture?.text && (
                <div style={{ borderLeft: '3px solid rgba(167,139,250,0.5)', paddingLeft: 10, margin: '10px 0', fontSize: 13, color: 'rgba(255,255,255,0.78)', fontStyle: 'italic' }}>
                  「{result.scripture.text}」<span style={{ color: 'rgba(167,139,250,0.85)', fontStyle: 'normal' }}> —— {result.scripture.ref}</span>
                </div>
              )}
              <Block label="默想">{result.meditation}</Block>
              <Block label="祷告">{result.prayer}</Block>
              <Block label="今日信心行动" color="#5ac8fa">{result.action}</Block>
            </div>

            <button onClick={restart} style={{ ...btn('rgba(255,255,255,0.08)'), color: 'rgba(255,255,255,0.7)' }}>再做一次诊断</button>
          </>
        )}

        {view === 'history' && (
          history.length === 0
            ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>还没有诊断记录</div>
            : history.map((h, i) => (
              <div key={i} style={card}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{h.idol_name} · {h.emotion}</span>
                  <span style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)' }}>{(h.created_at || '').slice(0, 10)}</span>
                </div>
                {h.event && <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 6 }}>{h.event}</div>}
                <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.78)', lineHeight: 1.6 }}>{h.gospel_truth}</div>
                {h.action && <div style={{ fontSize: 12, color: '#5ac8fa', marginTop: 6 }}>→ {h.action}</div>}
              </div>
            ))
        )}
      </div>
    </div>
  )
}

function Block({ label, children, color }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 11, color: color || '#a78bfa', fontWeight: 700, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.82)', lineHeight: 1.8 }}>{children}</div>
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
const pill = { background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 14, padding: '6px 12px', color: 'rgba(255,255,255,0.7)', fontSize: 12, cursor: 'pointer' }
function btn(bg) { return { padding: 13, borderRadius: 12, border: 'none', cursor: 'pointer', fontSize: 14.5, fontWeight: 700, background: bg, color: '#fff' } }
