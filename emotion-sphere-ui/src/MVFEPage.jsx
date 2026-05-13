import { useState, useEffect } from 'react'

const API_BASE = (import.meta.env.VITE_API_BASE || '') + '/api/mvfe'

const EMOTION_COLORS = {
  anxiety: '#ffa94d', peace: '#4facfe', hope: '#51cf66', sadness: '#748ffc',
  anger: '#ff6b6b', fear: '#da77f2', joy: '#ffd43b', love: '#ff8787',
  shame: '#9775fa', guilt: '#63e6be', disgust: '#8ce99a', surprise: '#74c0fc',
  gratitude: '#ffec99', envy: '#ffa8a8', loneliness: '#bac8ff', unknown: '#868e96',
}

export default function MVFEPage({ user, onBack }) {
  const [inputText, setInputText] = useState('')
  const [processing, setProcessing] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeView, setActiveView] = useState('dashboard')
  const [error, setError] = useState('')
  const userId = user?.id || user?.email || 'default_user'

  useEffect(() => { loadDashboard() }, [])

  async function loadDashboard() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/dashboard/state?user_id=${userId}&hours=168`)
      if (res.ok) {
        const data = await res.json()
        setDashboardData(data)
      }
    } catch (e) {}
    setLoading(false)
  }

  async function handleProcess() {
    if (!inputText.trim()) return
    setProcessing(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText, user_id: userId }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed') }
      const data = await res.json()
      setLastResult(data)
      setInputText('')
      setActiveView('dashboard')
      await loadDashboard()
    } catch (err) {
      setError(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const d = dashboardData || {}
  const hasData = (d.data_points || 0) > 0

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#060b14', overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#4facfe', fontSize: '20px', cursor: 'pointer', padding: '4px' }}>←</button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#fff', letterSpacing: '0.3px' }}>
            MVFE Runtime Dashboard
            {d.is_mock && <span style={{ fontSize: '10px', color: '#ffa94d', marginLeft: '8px', fontWeight: 400 }}>⚡ preview data</span>}
          </div>
          <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', marginTop: '2px' }}>Human Formation Dynamics Oscilloscope</div>
        </div>
        <button
          onClick={() => setActiveView(activeView === 'dashboard' ? 'input' : 'dashboard')}
          style={{ padding: '6px 14px', borderRadius: '8px', border: '1px solid rgba(79,172,254,0.3)', background: 'rgba(79,172,254,0.08)', color: '#4facfe', fontSize: '12px', cursor: 'pointer' }}
        >
          {activeView === 'dashboard' ? '📝 New Input' : '📊 Dashboard'}
        </button>
      </div>

      {activeView === 'input' && (
        <div style={{ flex: 1, padding: '16px', overflow: 'auto' }}>
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '10px', lineHeight: 1.6 }}>
            描述你此刻的内心状态、正在思考的事情、或面临的决定。<br/>
            系统将提取情绪动态、注意力模式、决策驱动因素，并计算人格塑造轨迹。
          </div>
          <textarea value={inputText} onChange={e => setInputText(e.target.value)} placeholder="此刻我在想..."
            style={{ width: '100%', minHeight: '100px', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#fff', fontSize: '14px', lineHeight: 1.7, resize: 'vertical', outline: 'none' }} />
          <button onClick={handleProcess} disabled={processing || !inputText.trim()}
            style={{ width: '100%', marginTop: '10px', padding: '12px', borderRadius: '10px', border: 'none', background: processing ? 'rgba(79,172,254,0.2)' : 'linear-gradient(135deg, #4facfe, #00f2fe)', color: '#fff', fontSize: '14px', fontWeight: 700, cursor: processing ? 'wait' : 'pointer' }}>
            {processing ? '⏳ Analyzing Formation...' : '🔬 Process Formation Input'}
          </button>
          {error && <div style={{ marginTop: '10px', padding: '10px', borderRadius: '8px', background: 'rgba(255,50,50,0.08)', color: '#ff6b6b', fontSize: '12px' }}>{error}</div>}
          {lastResult && <LastResultCard result={lastResult} />}
        </div>
      )}

      {activeView === 'dashboard' && (
        <div style={{ flex: 1, overflow: 'auto', padding: '12px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px', color: 'rgba(255,255,255,0.3)' }}>
              <div style={{ fontSize: '28px', marginBottom: '12px' }}>🧬</div>
              <div style={{ fontSize: '13px' }}>Loading formation dynamics...</div>
            </div>
          ) : !hasData ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'rgba(255,255,255,0.4)' }}>
              <div style={{ fontSize: '36px', marginBottom: '12px' }}>📭</div>
              <div style={{ fontSize: '14px' }}>No formation data yet</div>
              <div style={{ fontSize: '12px', marginTop: '8px' }}>Click "New Input" to begin</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Panel title="🎭 Emotion Timeline" subtitle="How emotions change over time">
                  <EmotionTimeline data={d.emotion_series || []} />
                </Panel>
                <Panel title="🧬 Formation Drift Curve" subtitle="Are you drifting into a pattern?">
                  <FormationCurve data={d.formation_curve || []} />
                </Panel>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Panel title="👁 Attention Fixation Map" subtitle="Where your consciousness is allocated">
                  <AttentionMap data={d.attention_map || {}} />
                </Panel>
                <Panel title="⚖️ Decision Pattern Flow" subtitle="Approach vs Avoidance over time">
                  <DecisionFlow data={d.decision_flow || []} />
                </Panel>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Panel title="🕸 Causal Graph" subtitle="Emotion → Attention → Decision → Outcome">
                  <CausalGraph />
                </Panel>
                <Panel title="💭 Reflection" subtitle="What the system observes">
                  <ReflectionBox result={lastResult} />
                </Panel>
              </div>
              <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.18)', textAlign: 'center', padding: '6px', lineHeight: 1.5 }}>
                This dashboard displays observational patterns only. It does NOT constitute psychological diagnosis, personality assessment, or behavioral prescription.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Panel({ title, subtitle, children }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '14px', padding: '14px', minHeight: '200px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '10px' }}>
        <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>{title}</div>
        <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', marginTop: '2px' }}>{subtitle}</div>
      </div>
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  )
}

function EmotionTimeline({ data }) {
  if (!data || data.length < 2) return <NoData />
  const w = 360, h = 140, padL = 30, padR = 10, padT = 10, padB = 25
  const chartW = w - padL - padR, chartH = h - padT - padB
  const emotionsSeen = [...new Set(data.map(d => d.primary_emotion))]
  const n = data.length
  const x = i => padL + (i / (n - 1)) * chartW
  const y = v => padT + (1 - v) * chartH
  const paths = emotionsSeen.map(em => {
    let d = ''
    let drawing = false
    data.forEach((pt, i) => {
      const px = x(i), py = y(pt.primary_emotion === em ? pt.intensity : 0)
      if (pt.primary_emotion === em) {
        if (!drawing) { d += `M ${px} ${py} `; drawing = true }
        else { d += `L ${px} ${py} ` }
      } else { drawing = false }
    })
    return { emotion: em, d, color: EMOTION_COLORS[em] || EMOTION_COLORS.unknown }
  }).filter(p => p.d)
  const dots = data.map((d, i) => ({ x: x(i), y: y(d.intensity), color: EMOTION_COLORS[d.primary_emotion] || EMOTION_COLORS.unknown }))
  const timeLabels = [data[0], data[Math.floor(n/2)], data[n-1]].map((d, i) => ({
    x: x(i === 0 ? 0 : i === 1 ? Math.floor(n/2) : n - 1),
    text: d.timestamp ? new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : '',
  }))
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 'auto' }}>
      {[0, 0.25, 0.5, 0.75, 1].map(t => (
        <line key={t} x1={padL} y1={y(t)} x2={w - padR} y2={y(t)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="2,2" />
      ))}
      <text x={padL - 5} y={y(1) + 3} fill="rgba(255,255,255,0.3)" fontSize="8" textAnchor="end">1.0</text>
      <text x={padL - 5} y={y(0.5) + 3} fill="rgba(255,255,255,0.3)" fontSize="8" textAnchor="end">0.5</text>
      <text x={padL - 5} y={y(0) + 3} fill="rgba(255,255,255,0.3)" fontSize="8" textAnchor="end">0</text>
      {paths.map(p => <path key={p.emotion} d={p.d} fill="none" stroke={p.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />)}
      {dots.map((d, i) => (
        <g key={i}><circle cx={d.x} cy={d.y} r="4" fill={d.color} opacity="0.9" />
          <circle cx={d.x} cy={d.y} r="7" fill="none" stroke={d.color} opacity="0.3" strokeWidth="1" /></g>
      ))}
      {timeLabels.map((t, i) => <text key={i} x={t.x} y={h - 4} fill="rgba(255,255,255,0.25)" fontSize="8" textAnchor="middle">{t.text}</text>)}
    </svg>
  )
}

function FormationCurve({ data }) {
  if (!data || data.length < 2) return <NoData />
  const w = 360, h = 140, padL = 30, padR = 10, padT = 10, padB = 25
  const chartW = w - padL - padR, chartH = h - padT - padB
  const n = data.length
  const x = i => padL + (i / (n - 1)) * chartW
  const y = v => padT + (1 - v) * chartH
  const areaPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(d.formation_score || 0)}`).join(' ') +
    ` L ${x(n - 1)} ${y(0)} L ${x(0)} ${y(0)} Z`
  const driftPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(d.drift_score || 0)}`).join(' ')
  const thresholdY = y(0.5)
  const timeLabels = [data[0], data[Math.floor(n/2)], data[n-1]].map((d, i) => ({
    x: x(i === 0 ? 0 : i === 1 ? Math.floor(n/2) : n - 1),
    text: d.timestamp ? new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : '',
  }))
  const latest = data[data.length - 1]
  const isDrifting = (latest.drift_score || 0) > 0.3
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 'auto' }}>
        {[0, 0.25, 0.5, 0.75, 1].map(t => (
          <line key={t} x1={padL} y1={y(t)} x2={w - padR} y2={y(t)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="2,2" />
        ))}
        <line x1={padL} y1={thresholdY} x2={w - padR} y2={thresholdY} stroke="rgba(255,169,77,0.4)" strokeWidth="1" strokeDasharray="4,3" />
        <path d={areaPath} fill="rgba(79,172,254,0.12)" stroke="none" />
        <path d={data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(d.formation_score || 0)}`).join(' ')} fill="none" stroke="#4facfe" strokeWidth="2.5" strokeLinecap="round" />
        <path d={driftPath} fill="none" stroke={isDrifting ? '#ff6b6b' : '#ffa94d'} strokeWidth="1.5" strokeDasharray="4,2" opacity="0.7" />
        <text x={padL - 5} y={y(1) + 3} fill="rgba(255,255,255,0.3)" fontSize="8" textAnchor="end">1.0</text>
        <text x={padL - 5} y={y(0.5) + 3} fill="rgba(255,255,255,0.3)" fontSize="8" textAnchor="end">0.5</text>
        <text x={padL - 5} y={y(0) + 3} fill="rgba(255,255,255,0.3)" fontSize="8" textAnchor="end">0</text>
        <circle cx={x(n - 1)} cy={y(latest.formation_score || 0)} r="5" fill="#4facfe" />
        <circle cx={x(n - 1)} cy={y(latest.formation_score || 0)} r="8" fill="none" stroke="#4facfe" opacity="0.3" strokeWidth="1.5" />
        {timeLabels.map((t, i) => <text key={i} x={t.x} y={h - 4} fill="rgba(255,255,255,0.25)" fontSize="8" textAnchor="middle">{t.text}</text>)}
      </svg>
      <div style={{ display: 'flex', gap: '14px', marginTop: '6px', justifyContent: 'center' }}>
        <LegendDot color="#4facfe" label="Formation Score" />
        <LegendDot color={isDrifting ? '#ff6b6b' : '#ffa94d'} label="Drift Signal" dashed />
        <LegendDot color="rgba(255,169,77,0.6)" label="Risk Threshold" dashed />
      </div>
    </div>
  )
}

function AttentionMap({ data }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  if (entries.length === 0) return <NoData />
  const maxVal = Math.max(...entries.map(e => e[1]), 0.01)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', paddingTop: '4px' }}>
      {entries.map(([focus, val]) => {
        const pct = (val / maxVal) * 100
        const intensity = val > 0.3 ? 'high' : val > 0.15 ? 'medium' : 'low'
        const barColor = intensity === 'high' ? 'linear-gradient(90deg, #ff6b6b, #ffa94d)' : intensity === 'medium' ? 'linear-gradient(90deg, #ffa94d, #ffd43b)' : 'linear-gradient(90deg, #4facfe, #63e6be)'
        return (
          <div key={focus}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.7)' }}>{focus}</span>
              <span style={{ fontSize: '11px', color: intensity === 'high' ? '#ffa94d' : 'rgba(255,255,255,0.5)', fontWeight: 600 }}>{(val * 100).toFixed(0)}%</span>
            </div>
            <div style={{ height: '6px', borderRadius: '3px', background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
              <div style={{ height: '100%', borderRadius: '3px', width: `${pct}%`, background: barColor, transition: 'width 0.6s ease' }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function DecisionFlow({ data }) {
  if (!data || data.length === 0) return <NoData />
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingTop: '4px' }}>
      <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', marginBottom: '4px' }}>Most recent → earliest</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
        {[...data].reverse().map((d, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ padding: '4px 10px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
              background: d.type === 'approach' ? 'rgba(81,207,102,0.15)' : 'rgba(255,107,107,0.15)',
              color: d.type === 'approach' ? '#51cf66' : '#ff6b6b',
              border: `1px solid ${d.type === 'approach' ? 'rgba(81,207,102,0.3)' : 'rgba(255,107,107,0.3)'}` }}>
              {d.type === 'approach' ? '→ 趋近' : '↔ 回避'}
            </div>
            {i < data.length - 1 && <span style={{ fontSize: '14px', color: 'rgba(255,255,255,0.15)' }}>→</span>}
          </div>
        ))}
      </div>
      <div style={{ marginTop: '8px', padding: '8px', borderRadius: '8px', background: 'rgba(255,255,255,0.03)' }}>
        <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginBottom: '4px' }}>Pattern detection</div>
        <PatternSummary data={data} />
      </div>
    </div>
  )
}

function PatternSummary({ data }) {
  const avoidanceCount = data.filter(d => d.type === 'avoidance').length
  const approachCount = data.filter(d => d.type === 'approach').length
  const total = data.length
  const avoidanceRate = total > 0 ? avoidanceCount / total : 0
  if (avoidanceRate > 0.6) {
    return <div style={{ fontSize: '12px', color: '#ffa94d', lineHeight: 1.5 }}>
      ⚠️ <strong>avoidance-dominant pattern detected</strong><br/>
      <span style={{ color: 'rgba(255,255,255,0.5)' }}>{(avoidanceRate * 100).toFixed(0)}% of recent decisions are avoidance-based. This may indicate a fear-driven loop.</span>
    </div>
  }
  if (avoidanceRate < 0.4) {
    return <div style={{ fontSize: '12px', color: '#51cf66', lineHeight: 1.5 }}>
      ✓ <strong>approach-dominant pattern</strong><br/>
      <span style={{ color: 'rgba(255,255,255,0.5)' }}>{(approachCount / total * 100).toFixed(0)}% approach decisions. Forward-moving energy detected.</span>
    </div>
  }
  return <div style={{ fontSize: '12px', color: '#4facfe', lineHeight: 1.5 }}>
    ~ <strong>balanced pattern</strong><br/>
    <span style={{ color: 'rgba(255,255,255,0.5)' }}>Mixed approach/avoidance. No clear dominant loop at this time.</span>
  </div>
}

function CausalGraph() {
  const w = 340, h = 160
  const nodes = [
    { id: 'emotion', label: 'Emotion', x: 60, y: 40, color: '#ffa94d' },
    { id: 'attention', label: 'Attention', x: 180, y: 40, color: '#4facfe' },
    { id: 'decision', label: 'Decision', x: 300, y: 40, color: '#9775fa' },
    { id: 'outcome', label: 'Outcome', x: 240, y: 120, color: '#63e6be' },
  ]
  const edges = [
    { from: 'emotion', to: 'attention', label: 'DRIVES' },
    { from: 'attention', to: 'decision', label: 'LEADS_TO' },
    { from: 'decision', to: 'outcome', label: 'RESULTS_IN' },
    { from: 'outcome', to: 'emotion', label: 'REINFORCES' },
  ]
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 'auto' }}>
      {edges.map(e => {
        const from = nodes.find(n => n.id === e.from)
        const to = nodes.find(n => n.id === e.to)
        const mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2
        const angle = Math.atan2(to.y - from.y, to.x - from.x) * 180 / Math.PI
        return (
          <g key={`${e.from}-${e.to}`}>
            <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />
            <g transform={`translate(${to.x},${to.y}) rotate(${angle})`}>
              <polygon points="0,0 -6,-3 -6,3" fill="rgba(255,255,255,0.2)" />
            </g>
            <rect x={mx - 22} y={my - 8} width="44" height="14" rx="4" fill="rgba(6,11,20,0.8)" />
            <text x={mx} y={my + 2} fill="rgba(255,255,255,0.35)" fontSize="7" textAnchor="middle">{e.label}</text>
          </g>
        )
      })}
      {nodes.map(n => (
        <g key={n.id}>
          <circle cx={n.x} cy={n.y} r="18" fill={`${n.color}20`} stroke={n.color} strokeWidth="1.5" />
          <text x={n.x} y={n.y + 4} fill={n.color} fontSize="9" textAnchor="middle" fontWeight={600}>{n.label}</text>
        </g>
      ))}
    </svg>
  )
}

function ReflectionBox({ result }) {
  if (!result) {
    return (
      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.35)', lineHeight: 1.7, padding: '8px 0' }}>
        Submit a formation input to generate reflective insights.
        <div style={{ marginTop: '12px', padding: '10px', borderRadius: '8px', background: 'rgba(79,172,254,0.05)', borderLeft: '2px solid rgba(79,172,254,0.3)' }}>
          <span style={{ color: '#4facfe', fontStyle: 'italic' }}>💡 What is most alive in you right now?</span>
        </div>
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.75)', lineHeight: 1.7 }}>
        {result.reflection?.state_interpretation}
      </div>
      {result.reflection?.loop_detection && result.reflection.loop_detection !== 'No clear loop detected.' && (
        <div style={{ fontSize: '11px', color: '#ffa94d', padding: '6px 8px', borderRadius: '6px', background: 'rgba(255,169,77,0.08)' }}>
          🔄 {result.reflection.loop_detection}
        </div>
      )}
      {result.reflection?.risk_assessment && (
        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', lineHeight: 1.5 }}>
          ⚠️ {result.reflection.risk_assessment}
        </div>
      )}
      <div style={{ marginTop: '4px', padding: '10px', borderRadius: '8px', background: 'rgba(79,172,254,0.06)', borderLeft: '2px solid rgba(79,172,254,0.3)' }}>
        <span style={{ fontSize: '10px', color: '#4facfe', fontWeight: 600 }}>💡 REFLECTIVE QUESTION</span>
        <div style={{ fontSize: '13px', color: '#a0d4f7', fontStyle: 'italic', marginTop: '4px' }}>
          {result.reflection?.reflective_question}
        </div>
      </div>
    </div>
  )
}

function LastResultCard({ result }) {
  return (
    <div style={{ marginTop: '14px', padding: '12px', borderRadius: '10px', background: 'rgba(79,172,254,0.05)', border: '1px solid rgba(79,172,254,0.15)' }}>
      <div style={{ fontSize: '12px', fontWeight: 700, color: '#4facfe', marginBottom: '8px' }}>✅ Last Analysis</div>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <MiniMetric label="Emotion" value={result.emotion?.primary_emotion} color="#ffa94d" />
        <MiniMetric label="Intensity" value={`${((result.emotion?.intensity || 0) * 100).toFixed(0)}%`} color="#ff6b6b" />
        <MiniMetric label="Decision" value={result.decision?.type === 'approach' ? '→ Approach' : '↔ Avoidance'} color={result.decision?.type === 'approach' ? '#51cf66' : '#ff6b6b'} />
        <MiniMetric label="Formation" value={`${((result.formation?.formation_score || 0) * 100).toFixed(0)}%`} color="#4facfe" />
        <MiniMetric label="Drift" value={`${((result.formation?.drift_score || 0) * 100).toFixed(0)}%`} color="#ffa94d" />
      </div>
    </div>
  )
}

function MiniMetric({ label, value, color }) {
  return (
    <div style={{ padding: '4px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.4)' }}>{label}</div>
      <div style={{ fontSize: '12px', color, fontWeight: 700 }}>{value}</div>
    </div>
  )
}

function NoData() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'rgba(255,255,255,0.2)', fontSize: '12px' }}>
      No data available
    </div>
  )
}

function LegendDot({ color, label, dashed }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      <div style={{ width: '10px', height: dashed ? '1px' : '3px', borderRadius: '2px', background: color, borderTop: dashed ? `1px dashed ${color}` : 'none' }} />
      <span style={{ fontSize: '9px', color: 'rgba(255,255,255,0.4)' }}>{label}</span>
    </div>
  )
}
