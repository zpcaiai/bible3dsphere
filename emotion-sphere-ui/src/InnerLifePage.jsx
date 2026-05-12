import { useState } from 'react'
import { API_BASE } from './api'
import { getToken } from './auth'

const sfdsUrl = (path) => `${API_BASE}/sfds${path}`

/**
 * 内在生命页面 — 包含三个子模块:
 * 1. 人格塑造 (Formation) — 8维度轨迹
 * 2. 生命成长 (Growth) — 属灵季节 + 趋势
 * 3. 决策支撑 (Decision) — SFDS决策分辨
 */
export default function InnerLifePage({ user, onBack }) {
  const [subTab, setSubTab] = useState('formation')
  const token = getToken()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-app, #0d1117)', color: '#e6e6e6' }}>
      {/* 顶部标题 + 返回 */}
      <header style={{
        display: 'flex', alignItems: 'center', padding: '16px 20px',
        background: 'rgba(20,25,35,0.95)', borderBottom: '1px solid rgba(255,255,255,0.06)',
        position: 'sticky', top: 0, zIndex: 50,
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', color: '#a0aec0', fontSize: '22px', padding: '4px 12px 4px 0', cursor: 'pointer'
        }}>←</button>
        <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0, letterSpacing: '-0.3px' }}>内在生命</h1>
      </header>

      {/* 子 Tab 切换 */}
      <div style={{
        display: 'flex', gap: '4px', padding: '12px 16px',
        background: 'rgba(20,25,35,0.8)', borderBottom: '1px solid rgba(255,255,255,0.04)',
        position: 'sticky', top: '57px', zIndex: 49,
      }}>
        {[
          { key: 'formation', label: '人格塑造', icon: '🧬' },
          { key: 'growth', label: '生命成长', icon: '🌱' },
          { key: 'decision', label: '决策支撑', icon: '⚖️' },
        ].map(t => (
          <button key={t.key} onClick={() => setSubTab(t.key)} style={{
            flex: 1, padding: '10px 8px', borderRadius: '10px',
            background: subTab === t.key ? 'rgba(90,154,143,0.2)' : 'transparent',
            border: subTab === t.key ? '1px solid rgba(90,154,143,0.4)' : '1px solid transparent',
            color: subTab === t.key ? '#7dd3c0' : '#8a94a6',
            fontSize: '13px', fontWeight: 500, cursor: 'pointer',
            transition: 'all 0.2s',
          }}>
            <span style={{ fontSize: '16px', display: 'block', marginBottom: '2px' }}>{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div style={{ padding: '16px' }}>
        {subTab === 'formation' && <FormationPanel token={token} />}
        {subTab === 'growth' && <GrowthPanel token={token} />}
        {subTab === 'decision' && <DecisionPanel token={token} />}
      </div>
    </div>
  )
}


/* ────────────────────────── 人格塑造 ────────────────────────── */
function FormationPanel({ token }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadProfile = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(sfdsUrl('/v3/formation/profile/current_user'), {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setProfile(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const dimensions = [
    { key: 'humility', label: '谦卑', color: '#7dd3c0' },
    { key: 'fear_tendency', label: '恐惧倾向', color: '#f6ad55', inverse: true },
    { key: 'pride_tendency', label: '骄傲倾向', color: '#fc8181', inverse: true },
    { key: 'emotional_stability', label: '情绪稳定', color: '#68d391' },
    { key: 'truth_alignment', label: '真理对齐', color: '#63b3ed' },
    { key: 'relational_health', label: '关系健康', color: '#b794f4' },
    { key: 'resilience', label: '韧性', color: '#f6e05e' },
    { key: 'spiritual_clarity', label: '属灵清晰', color: '#76e4f7' },
  ]

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 8px 0' }}>人格塑造轨迹</h2>
        <p style={{ fontSize: '13px', color: '#8a94a6', margin: 0 }}>
          品格 = 轨迹，而非静态分数。这里呈现8个行为倾向维度的变化趋势。
        </p>
      </div>

      {!profile && !loading && (
        <button onClick={loadProfile} style={{
          width: '100%', padding: '14px', borderRadius: '12px',
          background: 'linear-gradient(135deg, #5a9a8f 0%, #4a7a72 100%)',
          border: 'none', color: '#fff', fontSize: '15px', fontWeight: 500,
          cursor: 'pointer', marginBottom: '16px',
        }}>
          加载我的人格档案
        </button>
      )}

      {loading && <LoadingSpinner text="正在加载人格档案..." />}
      {error && <ErrorCard message={error} onRetry={loadProfile} />}

      {profile && profile.state_vector && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {dimensions.map(d => {
            const val = profile.state_vector[d.key] || 0.5
            const delta = profile.dimension_scores?.find(s => s.dimension === d.key)?.delta || 0
            return (
              <div key={d.key} style={{
                background: 'rgba(255,255,255,0.03)', borderRadius: '10px', padding: '12px 16px',
                border: '1px solid rgba(255,255,255,0.06)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 500 }}>{d.label}</span>
                  <span style={{ fontSize: '12px', color: delta > 0 ? '#68d391' : delta < 0 ? '#fc8181' : '#8a94a6' }}>
                    {delta > 0 ? '↑' : delta < 0 ? '↓' : '→'} {(val * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${val * 100}%`, height: '100%', background: d.color,
                    borderRadius: '3px', transition: 'width 0.5s ease',
                  }} />
                </div>
              </div>
            )
          })}

          {profile.trajectory_direction && (
            <div style={{
              marginTop: '12px', padding: '14px', borderRadius: '10px',
              background: 'rgba(90,154,143,0.1)', border: '1px solid rgba(90,154,143,0.2)',
            }}>
              <div style={{ fontSize: '13px', color: '#7dd3c0', fontWeight: 500, marginBottom: '4px' }}>
                当前轨迹方向
              </div>
              <div style={{ fontSize: '15px' }}>
                {profile.trajectory_direction === 'stabilizing' && '趋于稳定 🌿'}
                {profile.trajectory_direction === 'improving_clarity' && '清晰度提升 ✨'}
                {profile.trajectory_direction === 'fragmenting' && '需要关注 ⚠️'}
                {profile.trajectory_direction === 'increasing_volatility' && '波动增加 🌊'}
                {profile.trajectory_direction === 'cyclical' && '周期循环 🔄'}
                {profile.trajectory_direction === 'unknown' && '数据积累中 📊'}
              </div>
            </div>
          )}

          {profile.dominant_loop && profile.dominant_loop !== 'none' && (
            <div style={{
              padding: '14px', borderRadius: '10px',
              background: 'rgba(246,173,85,0.1)', border: '1px solid rgba(246,173,85,0.2)',
            }}>
              <div style={{ fontSize: '13px', color: '#f6ad55', fontWeight: 500, marginBottom: '4px' }}>
                主导循环模式
              </div>
              <div style={{ fontSize: '14px' }}>
                {profile.dominant_loop.replace(/_/g, ' ')}
              </div>
            </div>
          )}

          {profile.reflective_question && (
            <div style={{
              marginTop: '8px', padding: '14px 16px', borderRadius: '10px',
              background: 'rgba(99,179,237,0.08)', border: '1px solid rgba(99,179,237,0.15)',
              fontStyle: 'italic', fontSize: '14px', color: '#a0c4e8',
            }}>
              💭 {profile.reflective_question}
            </div>
          )}
        </div>
      )}

      {profile && !profile.state_vector && (
        <div style={{ textAlign: 'center', padding: '32px 16px', color: '#8a94a6' }}>
          <div style={{ fontSize: '40px', marginBottom: '12px' }}>🌱</div>
          <p style={{ margin: '0 0 8px 0', fontWeight: 500 }}>尚未积累足够数据</p>
          <p style={{ fontSize: '13px', margin: 0 }}>
            继续记录灵修日记和情绪打卡，系统将逐渐为你呈现人格成长轨迹
          </p>
        </div>
      )}
    </div>
  )
}


/* ────────────────────────── 生命成长 ────────────────────────── */
function GrowthPanel({ token }) {
  const [timeline, setTimeline] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadTimeline = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(sfdsUrl('/v3/formation/dimensions'), {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setTimeline(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const seasonEmoji = {
    growth: '🌿', consolation: '☀️', desolation: '🌧️',
    dark_night: '🌑', plateau: '⛰️', confused: '🌫️',
    breakthrough: '🌈',
  }

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 8px 0' }}>生命成长</h2>
        <p style={{ fontSize: '13px', color: '#8a94a6', margin: 0 }}>
          属灵生命有四季。觉察自己正处于什么季节，是成长的起点。
        </p>
      </div>

      {!timeline && !loading && (
        <button onClick={loadTimeline} style={{
          width: '100%', padding: '14px', borderRadius: '12px',
          background: 'linear-gradient(135deg, #68d391 0%, #4a9a6f 100%)',
          border: 'none', color: '#fff', fontSize: '15px', fontWeight: 500,
          cursor: 'pointer', marginBottom: '16px',
        }}>
          查看生命成长维度
        </button>
      )}

      {loading && <LoadingSpinner text="正在加载..." />}
      {error && <ErrorCard message={error} onRetry={loadTimeline} />}

      {timeline && (
        <div>
          {/* 维度说明 */}
          {timeline.dimensions && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              {timeline.dimensions.map((dim, i) => (
                <div key={i} style={{
                  background: 'rgba(255,255,255,0.03)', borderRadius: '10px', padding: '12px 14px',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}>
                  <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>{dim.name || dim.dimension}</div>
                  <div style={{ fontSize: '12px', color: '#8a94a6' }}>{dim.description}</div>
                </div>
              ))}
            </div>
          )}

          {/* 主导循环类型 */}
          {timeline.dominant_loops && (
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px', color: '#a0aec0' }}>5种主导循环模式</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {timeline.dominant_loops.map((loop, i) => (
                  <span key={i} style={{
                    padding: '6px 12px', borderRadius: '16px', fontSize: '12px',
                    background: 'rgba(90,154,143,0.15)', color: '#7dd3c0',
                    border: '1px solid rgba(90,154,143,0.25)',
                  }}>
                    {loop.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 说明 */}
          {timeline.state_vector_note && (
            <div style={{
              padding: '14px', borderRadius: '10px',
              background: 'rgba(99,179,237,0.08)', border: '1px solid rgba(99,179,237,0.15)',
              fontSize: '13px', color: '#a0c4e8',
            }}>
              ℹ️ {timeline.state_vector_note}
            </div>
          )}
        </div>
      )}

      {/* 灵修建议卡片 */}
      <div style={{
        marginTop: '24px', padding: '16px', borderRadius: '12px',
        background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
      }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px' }}>📖 属灵操练建议</h3>
        <ul style={{ margin: 0, padding: '0 0 0 16px', fontSize: '13px', color: '#a0aec0', lineHeight: '1.8' }}>
          <li>每日灵修（Lectio Divina）：静默 → 诵读 → 默想 → 祷告</li>
          <li>情绪省察（Examen）：觉察今天最感恩 / 最困扰的时刻</li>
          <li>关系操练：主动联络一位许久没联络的朋友</li>
          <li>身体律动：步行祷告 15 分钟</li>
        </ul>
      </div>
    </div>
  )
}


/* ────────────────────────── 决策支撑 ────────────────────────── */
function DecisionPanel({ token }) {
  const [decisions, setDecisions] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showNewForm, setShowNewForm] = useState(false)
  const [formData, setFormData] = useState({ title: '', category: 'career', description: '', urgency: 5 })
  const [submitting, setSubmitting] = useState(false)

  const loadDecisions = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(sfdsUrl('/decisions?user_id=current_user'), {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setDecisions(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const submitDecision = async () => {
    if (!formData.title.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch(sfdsUrl('/decisions?user_id=current_user'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: formData.title,
          category: formData.category,
          description: formData.description,
          urgency: formData.urgency,
        })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setShowNewForm(false)
      setFormData({ title: '', category: 'career', description: '', urgency: 5 })
      loadDecisions()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const categories = [
    { value: 'career', label: '职业', emoji: '💼' },
    { value: 'relationship', label: '关系', emoji: '💕' },
    { value: 'temptation', label: '试探', emoji: '⚠️' },
    { value: 'calling', label: '呼召', emoji: '🎯' },
    { value: 'financial', label: '财务', emoji: '💰' },
    { value: 'health', label: '健康', emoji: '🏥' },
    { value: 'ministry', label: '事工', emoji: '⛪' },
  ]

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 8px 0' }}>决策支撑</h2>
        <p style={{ fontSize: '13px', color: '#8a94a6', margin: 0 }}>
          陪伴你分辨内心的声音 — 系统是镜子，不是裁判。
        </p>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <button onClick={() => setShowNewForm(true)} style={{
          flex: 1, padding: '12px', borderRadius: '10px',
          background: 'linear-gradient(135deg, #5a9a8f 0%, #4a7a72 100%)',
          border: 'none', color: '#fff', fontSize: '14px', fontWeight: 500, cursor: 'pointer',
        }}>
          + 新决定
        </button>
        <button onClick={loadDecisions} style={{
          padding: '12px 20px', borderRadius: '10px',
          background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
          color: '#a0aec0', fontSize: '14px', cursor: 'pointer',
        }}>
          刷新
        </button>
      </div>

      {/* 新决定表单 */}
      {showNewForm && (
        <div style={{
          background: 'rgba(255,255,255,0.03)', borderRadius: '12px', padding: '16px',
          border: '1px solid rgba(255,255,255,0.08)', marginBottom: '16px',
        }}>
          <input
            placeholder="你正在面对什么决定？"
            value={formData.title}
            onChange={e => setFormData({ ...formData, title: e.target.value })}
            style={{
              width: '100%', padding: '12px', borderRadius: '8px', marginBottom: '10px',
              background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
              color: '#e6e6e6', fontSize: '14px', outline: 'none',
            }}
          />
          <textarea
            placeholder="描述一下情况... (可选)"
            value={formData.description}
            onChange={e => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            style={{
              width: '100%', padding: '12px', borderRadius: '8px', marginBottom: '10px',
              background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
              color: '#e6e6e6', fontSize: '14px', outline: 'none', resize: 'vertical',
            }}
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
            {categories.map(c => (
              <button key={c.value} onClick={() => setFormData({ ...formData, category: c.value })} style={{
                padding: '6px 12px', borderRadius: '16px', fontSize: '12px',
                background: formData.category === c.value ? 'rgba(90,154,143,0.3)' : 'rgba(255,255,255,0.05)',
                border: formData.category === c.value ? '1px solid rgba(90,154,143,0.5)' : '1px solid rgba(255,255,255,0.1)',
                color: formData.category === c.value ? '#7dd3c0' : '#8a94a6', cursor: 'pointer',
              }}>
                {c.emoji} {c.label}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={submitDecision} disabled={submitting || !formData.title.trim()} style={{
              flex: 1, padding: '12px', borderRadius: '8px',
              background: formData.title.trim() ? '#5a9a8f' : '#3a4a47',
              border: 'none', color: '#fff', fontSize: '14px', cursor: formData.title.trim() ? 'pointer' : 'not-allowed',
            }}>
              {submitting ? '提交中...' : '开始分辨'}
            </button>
            <button onClick={() => setShowNewForm(false)} style={{
              padding: '12px 20px', borderRadius: '8px',
              background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
              color: '#8a94a6', fontSize: '14px', cursor: 'pointer',
            }}>
              取消
            </button>
          </div>
        </div>
      )}

      {loading && <LoadingSpinner text="加载决策记录..." />}
      {error && <ErrorCard message={error} onRetry={loadDecisions} />}

      {/* 决策列表 */}
      {decisions && decisions.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {decisions.map((d, i) => (
            <div key={d.id || i} style={{
              background: 'rgba(255,255,255,0.03)', borderRadius: '10px', padding: '14px',
              border: '1px solid rgba(255,255,255,0.06)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>{d.title}</div>
                  <div style={{ fontSize: '12px', color: '#8a94a6' }}>
                    {categories.find(c => c.value === d.category)?.emoji} {categories.find(c => c.value === d.category)?.label || d.category}
                    {d.created_at && ` · ${new Date(d.created_at).toLocaleDateString('zh-CN')}`}
                  </div>
                </div>
                <span style={{
                  padding: '4px 8px', borderRadius: '12px', fontSize: '11px',
                  background: d.status === 'decided' ? 'rgba(104,211,145,0.15)' : 'rgba(246,173,85,0.15)',
                  color: d.status === 'decided' ? '#68d391' : '#f6ad55',
                }}>
                  {d.status === 'decided' ? '已决定' : d.status === 'guided' ? '已指引' : '分辨中'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {decisions && decisions.length === 0 && (
        <div style={{ textAlign: 'center', padding: '32px 16px', color: '#8a94a6' }}>
          <div style={{ fontSize: '40px', marginBottom: '12px' }}>🤔</div>
          <p style={{ margin: '0 0 8px 0', fontWeight: 500 }}>还没有决策记录</p>
          <p style={{ fontSize: '13px', margin: 0 }}>点击"新决定"开始记录</p>
        </div>
      )}
    </div>
  )
}


/* ────────────────────────── 共用组件 ────────────────────────── */
function LoadingSpinner({ text }) {
  return (
    <div style={{ textAlign: 'center', padding: '32px 16px', color: '#8a94a6' }}>
      <div style={{ fontSize: '24px', marginBottom: '8px', animation: 'spin 1s linear infinite' }}>⏳</div>
      <p style={{ margin: 0, fontSize: '14px' }}>{text}</p>
    </div>
  )
}

function ErrorCard({ message, onRetry }) {
  return (
    <div style={{
      padding: '14px', borderRadius: '10px',
      background: 'rgba(252,129,129,0.1)', border: '1px solid rgba(252,129,129,0.2)',
      marginBottom: '16px',
    }}>
      <div style={{ fontSize: '13px', color: '#fc8181', marginBottom: '8px' }}>
        加载失败: {message}
      </div>
      {onRetry && (
        <button onClick={onRetry} style={{
          padding: '6px 14px', borderRadius: '6px', fontSize: '12px',
          background: 'rgba(252,129,129,0.15)', border: '1px solid rgba(252,129,129,0.3)',
          color: '#fc8181', cursor: 'pointer',
        }}>
          重试
        </button>
      )}
    </div>
  )
}
