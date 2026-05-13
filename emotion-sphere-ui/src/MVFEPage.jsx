import { useState, useEffect } from 'react'

const API_BASE = (import.meta.env.VITE_API_BASE || '') + '/api/mvfe'

export default function MVFEPage({ user, onBack }) {
  const [inputText, setInputText] = useState('')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [formationState, setFormationState] = useState(null)
  const [activeTab, setActiveTab] = useState('input') // input | state | history
  const [error, setError] = useState('')

  const userId = user?.id || user?.email || 'default_user'

  useEffect(() => {
    loadState()
    loadHistory()
  }, [])

  async function loadState() {
    try {
      const res = await fetch(`${API_BASE}/state/${userId}`)
      if (res.ok) {
        const data = await res.json()
        setFormationState(data.state)
      }
    } catch {}
  }

  async function loadHistory() {
    try {
      const res = await fetch(`${API_BASE}/history/${userId}?limit=10`)
      if (res.ok) {
        const data = await res.json()
        setHistory(data.events || [])
      }
    } catch {}
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
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Processing failed')
      }
      const data = await res.json()
      setResult(data)
      setActiveTab('state')
      loadState()
      loadHistory()
    } catch (err) {
      setError(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const tabStyle = (tab) => ({
    flex: 1,
    padding: '10px',
    border: 'none',
    background: activeTab === tab ? 'rgba(99,179,237,0.2)' : 'transparent',
    color: activeTab === tab ? '#63b3ed' : 'rgba(255,255,255,0.6)',
    fontWeight: activeTab === tab ? 700 : 400,
    fontSize: '13px',
    cursor: 'pointer',
    borderBottom: activeTab === tab ? '2px solid #63b3ed' : '2px solid transparent',
    transition: 'all 0.2s',
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#0a0f1e' }}>
      {/* Header */}
      <div style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#63b3ed', fontSize: '18px', cursor: 'pointer' }}>←</button>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>内在生命 · Formation Engine</div>
          <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>Human Formation Dynamics System</div>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <button style={tabStyle('input')} onClick={() => setActiveTab('input')}>📝 输入</button>
        <button style={tabStyle('state')} onClick={() => setActiveTab('state')}>🧬 状态</button>
        <button style={tabStyle('history')} onClick={() => setActiveTab('history')}>📊 历史</button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>

        {/* INPUT TAB */}
        {activeTab === 'input' && (
          <div>
            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginBottom: '12px' }}>
              输入你当前的想法、感受或正在面对的决策。系统将提取情绪动态、注意力模式、决策驱动因素，并计算人格塑造轨迹。
            </div>
            <textarea
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              placeholder="描述你此刻的内心状态、正在思考的事情、或面临的决定..."
              style={{
                width: '100%',
                minHeight: '140px',
                padding: '14px',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.1)',
                background: 'rgba(255,255,255,0.04)',
                color: '#fff',
                fontSize: '14px',
                lineHeight: 1.7,
                resize: 'vertical',
                outline: 'none',
              }}
            />
            <button
              onClick={handleProcess}
              disabled={processing || !inputText.trim()}
              style={{
                width: '100%',
                marginTop: '12px',
                padding: '14px',
                borderRadius: '12px',
                border: 'none',
                background: processing ? 'rgba(99,179,237,0.3)' : 'linear-gradient(135deg, #4facfe, #00f2fe)',
                color: '#fff',
                fontSize: '15px',
                fontWeight: 600,
                cursor: processing ? 'wait' : 'pointer',
              }}
            >
              {processing ? '⏳ 分析中...' : '🔬 开始 Formation 分析'}
            </button>
            {error && <div style={{ marginTop: '12px', padding: '10px', borderRadius: '8px', background: 'rgba(255,50,50,0.1)', color: '#ff6b6b', fontSize: '13px' }}>{error}</div>}
          </div>
        )}

        {/* STATE TAB */}
        {activeTab === 'state' && (
          <div>
            {result ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* Emotion */}
                <StateCard title="🎭 情绪状态" data={result.emotion}>
                  <MetricBar label="主情绪" value={result.emotion.primary_emotion} />
                  <MetricBar label="强度" value={result.emotion.intensity} isNum />
                  <MetricBar label="不确定性" value={result.emotion.uncertainty} isNum />
                  {result.emotion.secondary_emotions?.length > 0 && (
                    <div style={{ marginTop: '6px' }}>
                      <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>次级: </span>
                      {result.emotion.secondary_emotions.map(e => (
                        <span key={e} style={{ fontSize: '11px', background: 'rgba(99,179,237,0.15)', padding: '2px 8px', borderRadius: '10px', marginRight: '4px', color: '#a0d4f7' }}>{e}</span>
                      ))}
                    </div>
                  )}
                </StateCard>

                {/* Attention */}
                <StateCard title="🎯 注意力" data={result.attention}>
                  <MetricBar label="焦点" value={result.attention.focus} />
                  <MetricBar label="固着度" value={result.attention.fixation_score} isNum />
                  <MetricBar label="漂移风险" value={result.attention.drift_risk} isNum />
                </StateCard>

                {/* Decision */}
                <StateCard title="⚖️ 决策模式" data={result.decision}>
                  <MetricBar label="类型" value={result.decision.type === 'approach' ? '趋近' : '回避'} />
                  <MetricBar label="恐惧驱动" value={result.decision.drivers?.fear} isNum />
                  <MetricBar label="自我驱动" value={result.decision.drivers?.ego} isNum />
                  <MetricBar label="爱驱动" value={result.decision.drivers?.love} isNum />
                </StateCard>

                {/* Formation */}
                <StateCard title="🧬 Formation" data={result.formation}>
                  <MetricBar label="塑造分数" value={result.formation.formation_score} isNum highlight />
                  <MetricBar label="漂移分数" value={result.formation.drift_score} isNum />
                  <MetricBar label="稳定性" value={result.formation.stability_score} isNum />
                </StateCard>

                {/* Reflection */}
                <StateCard title="💭 反思" data={null}>
                  <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.8)', lineHeight: 1.7 }}>
                    <p style={{ margin: '0 0 8px' }}>{result.reflection.state_interpretation}</p>
                    {result.reflection.loop_detection && result.reflection.loop_detection !== 'No clear loop detected.' && (
                      <p style={{ margin: '0 0 8px', color: '#ffa94d' }}>🔄 {result.reflection.loop_detection}</p>
                    )}
                    {result.reflection.risk_assessment && (
                      <p style={{ margin: '0 0 8px', color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>⚠️ {result.reflection.risk_assessment}</p>
                    )}
                    <div style={{ marginTop: '12px', padding: '10px', background: 'rgba(99,179,237,0.06)', borderRadius: '8px', borderLeft: '3px solid rgba(99,179,237,0.4)' }}>
                      <span style={{ fontSize: '12px', color: '#63b3ed' }}>💡 </span>
                      <span style={{ fontSize: '13px', color: '#a0d4f7', fontStyle: 'italic' }}>{result.reflection.reflective_question}</span>
                    </div>
                  </div>
                </StateCard>

                {/* Disclaimer */}
                <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.25)', padding: '8px', textAlign: 'center', lineHeight: 1.5 }}>
                  {result.reflection.disclaimer}
                </div>
              </div>
            ) : formationState ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <StateCard title="📈 当前 Formation State" data={null}>
                  <MetricBar label="塑造分数" value={formationState.formation_score} isNum highlight />
                  <MetricBar label="漂移分数" value={formationState.drift_score} isNum />
                  <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', marginTop: '8px' }}>
                    更新于: {formationState.updated_at || 'N/A'}
                  </div>
                </StateCard>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: 'rgba(255,255,255,0.4)' }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>🧬</div>
                <div style={{ fontSize: '14px' }}>暂无 Formation 数据</div>
                <div style={{ fontSize: '12px', marginTop: '8px' }}>在"输入"标签页提交你的想法开始分析</div>
              </div>
            )}
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div>
            {history.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: 'rgba(255,255,255,0.4)' }}>
                <div style={{ fontSize: '14px' }}>暂无历史记录</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {history.map(evt => (
                  <div key={evt.id} style={{
                    padding: '12px',
                    borderRadius: '10px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '11px', color: '#63b3ed', fontWeight: 600 }}>{evt.type}</span>
                      <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>{evt.created_at?.slice(0,16)?.replace('T',' ')}</span>
                    </div>
                    {evt.payload?.input && (
                      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', lineHeight: 1.5 }}>
                        {evt.payload.input.slice(0, 100)}{evt.payload.input.length > 100 ? '...' : ''}
                      </div>
                    )}
                    {evt.payload?.emotion && (
                      <div style={{ marginTop: '6px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '8px', background: 'rgba(255,165,0,0.15)', color: '#ffa94d' }}>
                          {evt.payload.emotion.primary_emotion} ({(evt.payload.emotion.intensity * 100).toFixed(0)}%)
                        </span>
                        <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '8px', background: 'rgba(99,179,237,0.15)', color: '#63b3ed' }}>
                          {evt.payload.decision?.type === 'approach' ? '趋近' : '回避'}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function StateCard({ title, data, children }) {
  return (
    <div style={{
      padding: '14px',
      borderRadius: '12px',
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px' }}>{title}</div>
      {children}
    </div>
  )
}

function MetricBar({ label, value, isNum, highlight }) {
  const displayValue = isNum ? (typeof value === 'number' ? (value * 100).toFixed(0) + '%' : '—') : (value || '—')
  const barWidth = isNum && typeof value === 'number' ? `${value * 100}%` : '0%'
  const barColor = highlight ? '#4facfe' : 'rgba(99,179,237,0.4)'

  return (
    <div style={{ marginBottom: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>{label}</span>
        <span style={{ fontSize: '12px', color: highlight ? '#4facfe' : 'rgba(255,255,255,0.8)', fontWeight: highlight ? 700 : 400 }}>{displayValue}</span>
      </div>
      {isNum && typeof value === 'number' && (
        <div style={{ height: '3px', borderRadius: '2px', background: 'rgba(255,255,255,0.06)' }}>
          <div style={{ height: '100%', borderRadius: '2px', background: barColor, width: barWidth, transition: 'width 0.5s ease' }} />
        </div>
      )}
    </div>
  )
}
