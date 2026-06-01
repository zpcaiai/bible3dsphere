/**
 * IdolatryMonitorPage — 偶像监测 / 依附强度指数 (Attachment Intensity Index)
 *
 * 不定罪、不审判，只温柔地观测：什么正在取代神，成为你内心的中心。
 * 入口：今日心镜 (SoulDashboard) 卡片。
 */
import { useEffect, useState } from 'react'
import {
  fetchIdolatrySignals, assessIdolatry, fetchIdolatryPatterns,
} from './api'
import { getToken } from './auth'

const IDOLS = [
  { type: 'success',          emoji: '🏆', name: '成就 / 表现',  mani: '不成功就觉得自己没价值' },
  { type: 'money',            emoji: '💰', name: '金钱 / 保障',  mani: '安全感完全依赖资产增长' },
  { type: 'approval',         emoji: '👍', name: '认可 / 被看见', mani: '极度在意别人的评价' },
  { type: 'control',          emoji: '🎛️', name: '掌控 / 确定性', mani: '不能接受不确定性' },
  { type: 'relationship',     emoji: '💞', name: '关系 / 某个人', mani: '没有某个人就崩溃' },
  { type: 'comfort',          emoji: '🛋️', name: '舒适 / 安逸',  mani: '一切决定都避免代价' },
  { type: 'spiritual_image',  emoji: '😇', name: '属灵形象',     mani: '用属灵表现证明自己' },
]
const IDOL_MAP = Object.fromEntries(IDOLS.map(i => [i.type, i]))

const DIMS = [
  { key: 'identity_dependency', name: '身份依赖', hint: '我用它来定义「我是谁」、证明我有价值' },
  { key: 'peace_disruption',    name: '平安扰动', hint: '它一旦不顺，我的平安就被打乱' },
  { key: 'fear_of_loss',        name: '害怕失去', hint: '想到失去它，我会强烈不安、恐惧' },
  { key: 'obedience_conflict',  name: '顺服冲突', hint: '为了它，我愿意妥协良心或违背引导' },
  { key: 'attention_capture',   name: '注意捕获', hint: '它占据我最多的思想、比较与焦虑' },
]

const RISK = {
  low:      { label: '自由',     color: '#34c759' },
  moderate: { label: '留意',     color: '#a8e6cf' },
  elevated: { label: '升高',     color: '#ffd43b' },
  high:     { label: '高度依附', color: '#ff8787' },
}

const CORE_QUESTIONS = [
  '我最近最害怕失去什么？',
  '什么东西一旦得不到，我就失去平安？',
  '我最常用什么来证明自己有价值？',
  '什么东西会让我愿意违背良心？',
  '我最近最常思想、最常比较、最常焦虑的是什么？',
  '如果神让我放下它，我最抗拒的是什么？',
]

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 14, marginBottom: 12 }

export default function IdolatryMonitorPage({ user, onBack, onNeedLogin }) {
  const [view, setView] = useState('intro')       // intro | result | history
  const [ratings, setRatings] = useState({})       // type -> {target_name, ...dims}
  const [expanded, setExpanded] = useState(null)
  const [suggested, setSuggested] = useState([])
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = getToken()
    if (!token) return
    fetchIdolatrySignals(token)
      .then(r => setSuggested(r.suggested_targets || []))
      .catch(() => {})
  }, [])

  function toggleIdol(type) {
    setExpanded(expanded === type ? null : type)
    if (!ratings[type]) {
      setRatings(r => ({ ...r, [type]: { target_name: '', identity_dependency: 0.5, peace_disruption: 0.5, fear_of_loss: 0.5, obedience_conflict: 0.3, attention_capture: 0.5 } }))
    }
  }
  function setDim(type, key, val) {
    setRatings(r => ({ ...r, [type]: { ...r[type], [key]: val } }))
  }
  function removeIdol(type) {
    setRatings(r => { const n = { ...r }; delete n[type]; return n })
    if (expanded === type) setExpanded(null)
  }

  async function submit() {
    const token = getToken()
    if (!token) { onNeedLogin && onNeedLogin(); return }
    const list = Object.entries(ratings).map(([type, v]) => ({ target_type: type, ...v }))
    if (list.length === 0) { setError('请至少选择一项来省察'); return }
    setLoading(true); setError('')
    try {
      const r = await assessIdolatry({ ratings: list, use_signals: true }, token)
      setResult(r); setView('result')
      window.scrollTo({ top: 0 })
    } catch (e) { setError(e.message || '提交失败') }
    finally { setLoading(false) }
  }

  async function openHistory() {
    const token = getToken()
    if (!token) { onNeedLogin && onNeedLogin(); return }
    setLoading(true); setError('')
    try { const r = await fetchIdolatryPatterns(token, 20); setHistory(r.sessions || []); setView('history') }
    catch (e) { setError(e.message || '加载失败') }
    finally { setLoading(false) }
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* 顶栏 */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onBack} style={backBtn}>‹</button>
          <div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>偶像监测</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>依附强度指数 · Attachment Intensity</div>
          </div>
        </div>
        <button onClick={view === 'history' ? () => setView('intro') : openHistory} style={pill}>
          {view === 'history' ? '← 返回省察' : '历史'}
        </button>
      </div>

      <div style={{ padding: '14px 16px 100px', maxWidth: 720, margin: '0 auto' }}>
        {error && <div style={{ ...card, borderColor: 'rgba(255,135,135,0.4)', color: '#ff8787', fontSize: 13 }}>{error}</div>}

        {view === 'intro' && (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(139,92,246,0.14), rgba(236,72,153,0.10))', borderColor: 'rgba(139,92,246,0.2)' }}>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>🧭 看见内心的中心</div>
              <div style={{ fontSize: 13, lineHeight: 1.7, color: 'rgba(255,255,255,0.78)' }}>
                这不是要判断「你在拜偶像」。它只温柔地观测：有什么东西，正在悄悄取代神，
                成为你安全感、价值感、盼望、身份与顺服的中心。看见它，是恢复自由的第一步。
              </div>
            </div>

            <div style={{ ...card }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 10 }}>先安静下来，问自己：</div>
              {CORE_QUESTIONS.map((q, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, fontSize: 12.5, color: 'rgba(255,255,255,0.66)', lineHeight: 1.6, marginBottom: 6 }}>
                  <span style={{ color: 'rgba(139,92,246,0.8)' }}>{i + 1}.</span><span>{q}</span>
                </div>
              ))}
            </div>

            {suggested.length > 0 && (
              <div style={{ ...card, borderColor: 'rgba(255,212,59,0.25)' }}>
                <div style={{ fontSize: 12, color: '#ffd43b', fontWeight: 700, marginBottom: 6 }}>✦ 根据你近期的状态，或许值得先省察：</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {suggested.map(t => IDOL_MAP[t] && (
                    <span key={t} onClick={() => toggleIdol(t)} style={{ padding: '4px 10px', borderRadius: 14, background: 'rgba(255,212,59,0.14)', color: '#ffd43b', fontSize: 12, cursor: 'pointer' }}>
                      {IDOL_MAP[t].emoji} {IDOL_MAP[t].name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.5)', margin: '4px 4px 10px' }}>选择 1–7 个目标，温柔地为它打分</div>
            {IDOLS.map(idol => {
              const active = !!ratings[idol.type]
              const open = expanded === idol.type
              return (
                <div key={idol.type} style={{ ...card, borderColor: active ? 'rgba(139,92,246,0.4)' : 'rgba(255,255,255,0.08)' }}>
                  <div onClick={() => toggleIdol(idol.type)} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                    <span style={{ fontSize: 22 }}>{idol.emoji}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>{idol.name}</div>
                      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{idol.mani}</div>
                    </div>
                    {active && <span style={{ fontSize: 11, color: '#a78bfa' }}>已选 {open ? '▲' : '▼'}</span>}
                    {!active && <span style={{ fontSize: 20, color: 'rgba(255,255,255,0.3)' }}>+</span>}
                  </div>
                  {open && active && (
                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                      <input
                        value={ratings[idol.type].target_name}
                        onChange={e => setDim(idol.type, 'target_name', e.target.value)}
                        placeholder="具体指什么？(可选，如「升职」「某个人」)"
                        style={input}
                      />
                      {DIMS.map(d => (
                        <div key={d.key} style={{ marginTop: 12 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                            <span style={{ color: 'rgba(255,255,255,0.78)' }}>{d.name}</span>
                            <span style={{ color: '#a78bfa', fontWeight: 700 }}>{Math.round(ratings[idol.type][d.key] * 100)}</span>
                          </div>
                          <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>{d.hint}</div>
                          <input type="range" min="0" max="1" step="0.05" value={ratings[idol.type][d.key]}
                            onChange={e => setDim(idol.type, d.key, parseFloat(e.target.value))}
                            style={{ width: '100%', accentColor: '#a78bfa' }} />
                        </div>
                      ))}
                      <button onClick={() => removeIdol(idol.type)} style={{ marginTop: 10, background: 'none', border: 'none', color: 'rgba(255,135,135,0.7)', fontSize: 12, cursor: 'pointer' }}>移除这一项</button>
                    </div>
                  )}
                </div>
              )
            })}

            <button onClick={submit} disabled={loading} style={primaryBtn}>
              {loading ? '正在省察…' : `完成省察 (${Object.keys(ratings).length})`}
            </button>
            <div style={footNote}>本工具旨在辅助属灵辨识与自我省察，不构成定罪、心理诊断或属灵权威指导。</div>
          </>
        )}

        {view === 'result' && result && (
          <ResultView result={result} onAgain={() => { setResult(null); setView('intro') }} />
        )}

        {view === 'history' && (
          <HistoryView sessions={history} loading={loading} />
        )}
      </div>
    </div>
  )
}

function ResultView({ result, onAgain }) {
  return (
    <>
      <div style={{ ...card, background: 'linear-gradient(135deg, rgba(52,199,89,0.10), rgba(90,200,250,0.08))' }}>
        <div style={{ fontSize: 12, color: 'rgba(52,199,89,0.8)', fontWeight: 700, marginBottom: 8 }}>✦ 整体观察</div>
        <div style={{ fontSize: 13.5, lineHeight: 1.75, color: 'rgba(255,255,255,0.85)' }}>{result.summary}</div>
      </div>

      {(result.patterns || []).map((p, i) => (
        <PatternCard key={i} p={p} />
      ))}

      <button onClick={onAgain} style={{ ...primaryBtn, background: 'rgba(255,255,255,0.08)' }}>再做一次省察</button>
    </>
  )
}

function PatternCard({ p }) {
  const r = RISK[p.risk_level] || RISK.low
  const pct = Math.round((p.intensity || 0) * 100)
  return (
    <div style={{ ...card, borderColor: `${r.color}40` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 20 }}>{p.meta?.emoji}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>{p.meta?.name}{p.target_name ? ` · ${p.target_name}` : ''}</div>
        </div>
        <span style={{ fontSize: 11, fontWeight: 700, color: r.color, padding: '2px 8px', borderRadius: 10, background: `${r.color}22` }}>{r.label}</span>
      </div>

      {/* AII bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', width: 64, flexShrink: 0 }}>依附强度</span>
        <div style={{ flex: 1, height: 8, background: 'rgba(255,255,255,0.08)', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: r.color, borderRadius: 4, transition: 'width .6s' }} />
        </div>
        <span style={{ fontSize: 12, fontWeight: 700, color: r.color, width: 30, textAlign: 'right' }}>{pct}</span>
      </div>

      <div style={{ fontSize: 13, lineHeight: 1.7, color: 'rgba(255,255,255,0.78)', margin: '10px 0' }}>{p.explanation}</div>

      {/* Graph chain */}
      {p.graph?.chain && (
        <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 10, padding: 12, marginBottom: 10 }}>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 8 }}>🔗 依附回路</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 4 }}>
            {p.graph.chain.map((n, idx) => (
              <span key={n.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 11, padding: '3px 8px', borderRadius: 8, background: 'rgba(255,135,135,0.12)', color: '#ffb3b3' }}>{n.label}</span>
                {idx < p.graph.chain.length - 1 && <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11 }}>→</span>}
              </span>
            ))}
          </div>
          {(p.graph.breaks || []).slice(0, 2).map((b, idx) => (
            <div key={idx} style={{ marginTop: 8, fontSize: 11.5, color: '#51cf66', display: 'flex', gap: 6 }}>
              <span>✝</span><span>{b.note || b.principle}</span>
            </div>
          ))}
        </div>
      )}

      {/* Suggestions */}
      {p.suggestions && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 6 }}>建议</div>
          {p.suggestions.map((s, idx) => (
            <div key={idx} style={{ display: 'flex', gap: 8, fontSize: 12.5, color: 'rgba(255,255,255,0.74)', lineHeight: 1.6, marginBottom: 5 }}>
              <span style={{ color: '#5ac8fa' }}>{idx + 1}.</span><span>{s}</span>
            </div>
          ))}
        </div>
      )}

      {/* Scripture */}
      {p.scripture && (
        <div style={{ borderLeft: '3px solid rgba(167,139,250,0.5)', paddingLeft: 10, fontSize: 12.5, color: 'rgba(255,255,255,0.7)', fontStyle: 'italic' }}>
          「{p.scripture.text}」<span style={{ color: 'rgba(167,139,250,0.8)', fontStyle: 'normal' }}> —— {p.scripture.ref}</span>
        </div>
      )}
    </div>
  )
}

function HistoryView({ sessions, loading }) {
  if (loading) return <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>加载中…</div>
  if (!sessions || sessions.length === 0) return <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>还没有省察记录</div>
  return sessions.map(s => {
    const r = RISK[s.risk_level] || RISK.low
    const name = IDOL_MAP[s.top_target]?.name || '—'
    return (
      <div key={s.session_id} style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>{IDOL_MAP[s.top_target]?.emoji} {name}</span>
          <span style={{ fontSize: 11, color: r.color, fontWeight: 700 }}>{r.label} · {Math.round((s.top_intensity || 0) * 100)}</span>
        </div>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginBottom: 8 }}>{(s.created_at || '').slice(0, 16).replace('T', ' ')}</div>
        <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>{s.summary}</div>
      </div>
    )
  })
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
const pill = { background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 14, padding: '6px 12px', color: 'rgba(255,255,255,0.7)', fontSize: 12, cursor: 'pointer' }
const input = { width: '100%', boxSizing: 'border-box', padding: '8px 10px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 13 }
const primaryBtn = { width: '100%', marginTop: 10, padding: '14px', borderRadius: 12, border: 'none', background: 'linear-gradient(135deg, #8b5cf6, #ec4899)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer' }
const footNote = { fontSize: 10, color: 'rgba(255,255,255,0.25)', textAlign: 'center', marginTop: 16, lineHeight: 1.6 }
