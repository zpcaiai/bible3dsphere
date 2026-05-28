import { useState, useCallback, useEffect } from 'react'
import { API_BASE } from './api'
import { getOrCreateVisitorId } from './utils'

const DATA = {
  dx_focus: [
    '属灵生命的真实委身度',
    '外形吸引力',
    '"好相处"',
    '情绪稳定性',
    '明确婚恋意图',
    '消费观',
    '呼召与使命同路人',
    '内在品格',
    '生活习惯与理念',
    '年龄适宜',
  ],
  dx_block: [
    '性格强势或不稳定',
    '消费观严重不合',
    '忽略对方',
    '信仰背景冲突',
    '健康隐患或不良习惯',
  ],
  zm_focus: [
    '属灵生命的真实委身度',
    '稳定的经济能力',
    '安全舒适感',
    '真诚可沟通',
    '三观与信仰背景同频',
    '原生家庭和睦',
    '明确的未来规划',
    '责任与担当',
    '优先被选择感',
    '主动推进关系',
  ],
  zm_block: [
    '控制欲强',
    '原生家庭复杂或世俗',
    '生活懒惰或严重不良习惯',
    '性格幼稚不成熟',
    '信仰冷淡',
  ],
}

export default function DatingPriorityPage({ onBack }) {
  // 'dx' = 弟兄对姐妹, 'zm' = 姐妹对弟兄
  const [perspective, setPerspective] = useState(null)
  const [focusOrder, setFocusOrder] = useState([])
  const [blockOrder, setBlockOrder] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [showStats, setShowStats] = useState(false)
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)

  const focusList = perspective === 'dx' ? DATA.dx_focus : DATA.zm_focus
  const blockList = perspective === 'dx' ? DATA.dx_block : DATA.zm_block

  const handleSelect = useCallback((item, type) => {
    if (type === 'focus') {
      setFocusOrder(prev => {
        if (prev.includes(item)) {
          return prev.filter(x => x !== item)
        }
        return [...prev, item]
      })
    } else {
      setBlockOrder(prev => {
        if (prev.includes(item)) {
          return prev.filter(x => x !== item)
        }
        return [...prev, item]
      })
    }
  }, [])

  const handleSubmit = async () => {
    if (focusOrder.length === 0 && blockOrder.length === 0) return
    setSubmitting(true)
    try {
      const visitorId = getOrCreateVisitorId()
      const res = await fetch(`${API_BASE}/dating-priority/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          visitor_id: visitorId,
          perspective,
          focus_order: focusOrder,
          block_order: blockOrder,
        }),
      })
      if (res.ok) {
        setSubmitted(true)
        loadStats()
      }
    } catch (e) {
      console.error('[dating] submit error:', e)
    } finally {
      setSubmitting(false)
    }
  }

  const loadStats = async () => {
    if (!perspective) return
    setStatsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/dating-priority/stats?perspective=${perspective}`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      console.error('[dating] stats error:', e)
    } finally {
      setStatsLoading(false)
    }
  }

  useEffect(() => {
    if (showStats && perspective) loadStats()
  }, [showStats, perspective])

  const resetAll = () => {
    setFocusOrder([])
    setBlockOrder([])
    setSubmitted(false)
  }

  const changePerspective = (p) => {
    setPerspective(p)
    setFocusOrder([])
    setBlockOrder([])
    setSubmitted(false)
    setShowStats(false)
    setStats(null)
  }

  // Styles
  const pageStyle = {
    minHeight: '100vh',
    background: '#0d1117',
    color: '#e6e6e6',
    display: 'flex',
    flexDirection: 'column',
  }
  const headerStyle = {
    display: 'flex', alignItems: 'center', padding: '16px 20px',
    background: 'rgba(20,25,35,0.95)', borderBottom: '1px solid rgba(255,255,255,0.06)',
    position: 'sticky', top: 0, zIndex: 50,
  }
  const sectionTitle = {
    fontSize: '15px', fontWeight: 600, margin: '20px 0 10px',
    color: '#e6e6e6', display: 'flex', alignItems: 'center', gap: '8px',
  }
  const chipBase = {
    padding: '10px 16px',
    borderRadius: '10px',
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(255,255,255,0.04)',
    color: 'rgba(255,255,255,0.8)',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.15s',
    position: 'relative',
    textAlign: 'left',
    lineHeight: 1.4,
  }
  const chipSelected = {
    ...chipBase,
    background: 'rgba(79,172,254,0.15)',
    borderColor: '#4facfe',
    color: '#fff',
  }
  const badgeStyle = {
    position: 'absolute', top: '-6px', right: '-6px',
    width: '20px', height: '20px', borderRadius: '50%',
    background: '#4facfe', color: '#fff', fontSize: '11px', fontWeight: 700,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  }
  const perspBtn = (active) => ({
    flex: 1, padding: '14px', borderRadius: '12px', border: 'none',
    background: active ? '#4facfe' : 'rgba(255,255,255,0.06)',
    color: active ? '#fff' : 'rgba(255,255,255,0.6)',
    fontSize: '15px', fontWeight: 600, cursor: 'pointer',
    transition: 'all 0.2s',
  })

  // Choose perspective screen
  if (!perspective) {
    return (
      <div style={pageStyle}>
        <header style={headerStyle}>
          <button onClick={onBack} style={{
            background: 'none', border: 'none', color: '#a0aec0', fontSize: '22px', padding: '4px 12px 4px 0', cursor: 'pointer'
          }}>←</button>
          <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>交友原则排序</h1>
        </header>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', gap: '24px' }}>
          <div style={{ fontSize: '48px' }}>💒</div>
          <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.5)', textAlign: 'center', maxWidth: '300px', lineHeight: 1.6 }}>
            请选择你的视角：<br/>点选顺序即为你的优先级排序
          </p>
          <div style={{ display: 'flex', gap: '12px', width: '100%', maxWidth: '320px' }}>
            <button onClick={() => changePerspective('dx')} style={perspBtn(false)}>
              🙋‍♂️ 弟兄对姐妹
            </button>
            <button onClick={() => changePerspective('zm')} style={perspBtn(false)}>
              🙋‍♀️ 姐妹对弟兄
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={pageStyle}>
      <header style={headerStyle}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', color: '#a0aec0', fontSize: '22px', padding: '4px 12px 4px 0', cursor: 'pointer'
        }}>←</button>
        <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0, flex: 1 }}>交友原则排序</h1>
        <button onClick={resetAll} style={{
          background: 'rgba(255,59,48,0.15)', border: 'none', color: '#ff6b6b',
          fontSize: '13px', padding: '6px 12px', borderRadius: '8px', cursor: 'pointer',
        }}>🔄 重置</button>
      </header>

      {/* Perspective toggle */}
      <div style={{ padding: '12px 20px', display: 'flex', gap: '8px' }}>
        <button onClick={() => changePerspective('dx')} style={perspBtn(perspective === 'dx')}>
          🙋‍♂️ 弟兄→姐妹
        </button>
        <button onClick={() => changePerspective('zm')} style={perspBtn(perspective === 'zm')}>
          🙋‍♀️ 姐妹→弟兄
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 20px 100px' }}>
        {/* 关注点 */}
        <div style={sectionTitle}>
          <span>💚</span>
          <span>关注点</span>
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.35)', fontWeight: 400 }}>
            (已选 {focusOrder.length}/{focusList.length})
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {focusList.map((item) => {
            const idx = focusOrder.indexOf(item)
            const selected = idx >= 0
            return (
              <button
                key={item}
                onClick={() => handleSelect(item, 'focus')}
                style={selected ? chipSelected : chipBase}
              >
                {selected && <span style={badgeStyle}>{idx + 1}</span>}
                {item}
              </button>
            )
          })}
        </div>

        {/* 阻力点 */}
        <div style={sectionTitle}>
          <span>🚫</span>
          <span>阻力点</span>
          <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.35)', fontWeight: 400 }}>
            (已选 {blockOrder.length}/{blockList.length})
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {blockList.map((item) => {
            const idx = blockOrder.indexOf(item)
            const selected = idx >= 0
            return (
              <button
                key={item}
                onClick={() => handleSelect(item, 'block')}
                style={selected ? { ...chipSelected, borderColor: '#ff6b6b', background: 'rgba(255,107,107,0.12)' } : chipBase}
              >
                {selected && <span style={{ ...badgeStyle, background: '#ff6b6b' }}>{idx + 1}</span>}
                {item}
              </button>
            )
          })}
        </div>

        {/* 排序结果 + 提交 */}
        {(focusOrder.length > 0 || blockOrder.length > 0) && (
          <div style={{ marginTop: '28px', padding: '16px', borderRadius: '14px', background: 'rgba(79,172,254,0.06)', border: '1px solid rgba(79,172,254,0.15)' }}>
            <div style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px', color: '#4facfe' }}>
              📋 你的优先级排序
            </div>
            {focusOrder.length > 0 && (
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>💚 关注点排序：</div>
                {focusOrder.map((item, i) => (
                  <div key={item} style={{ fontSize: '14px', padding: '4px 0', color: '#e6e6e6' }}>
                    <span style={{ color: '#4facfe', fontWeight: 600, marginRight: '8px' }}>{i + 1}.</span>{item}
                  </div>
                ))}
              </div>
            )}
            {blockOrder.length > 0 && (
              <div>
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>🚫 阻力点排序：</div>
                {blockOrder.map((item, i) => (
                  <div key={item} style={{ fontSize: '14px', padding: '4px 0', color: '#e6e6e6' }}>
                    <span style={{ color: '#ff6b6b', fontWeight: 600, marginRight: '8px' }}>{i + 1}.</span>{item}
                  </div>
                ))}
              </div>
            )}

            {/* 提交按钮 */}
            {!submitted ? (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                style={{
                  width: '100%', marginTop: '16px', padding: '14px', borderRadius: '12px',
                  border: 'none', background: submitting ? 'rgba(120,120,128,0.3)' : '#4facfe',
                  color: '#fff', fontSize: '15px', fontWeight: 600, cursor: submitting ? 'not-allowed' : 'pointer',
                }}
              >
                {submitting ? '⏳ 提交中...' : '✅ 提交我的排序'}
              </button>
            ) : (
              <div style={{ marginTop: '16px', textAlign: 'center', color: '#51cf66', fontSize: '14px', fontWeight: 600 }}>
                ✅ 已提交！感谢你的参与
              </div>
            )}
          </div>
        )}

        {/* 查看统计按钮 */}
        {perspective && (
          <div style={{ marginTop: '16px' }}>
            <button
              onClick={() => setShowStats(!showStats)}
              style={{
                width: '100%', padding: '12px', borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)',
                color: 'rgba(255,255,255,0.7)', fontSize: '14px', cursor: 'pointer',
              }}
            >
              {showStats ? '🔼 收起统计' : '📊 查看大家的排序统计'}
            </button>
          </div>
        )}

        {/* 统计结果 */}
        {showStats && (
          <div style={{ marginTop: '16px', padding: '16px', borderRadius: '14px', background: 'rgba(81,207,102,0.06)', border: '1px solid rgba(81,207,102,0.15)' }}>
            <div style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px', color: '#51cf66' }}>
              📊 群体排序统计 ({perspective === 'dx' ? '弟兄→姐妹' : '姐妹→弟兄'})
            </div>
            {statsLoading ? (
              <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.5)', padding: '20px' }}>加载中...</div>
            ) : !stats || stats.total === 0 ? (
              <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', padding: '20px' }}>暂无数据，等待更多人参与</div>
            ) : (
              <>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginBottom: '12px' }}>
                  共 {stats.total} 人参与
                </div>
                {stats.focus_stats.length > 0 && (
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>💚 关注点（按平均排序）：</div>
                    {stats.focus_stats.map((s, i) => (
                      <div key={s.item} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0', fontSize: '13px' }}>
                        <span style={{ color: '#4facfe', fontWeight: 700, minWidth: '24px' }}>{i + 1}.</span>
                        <span style={{ flex: 1, color: '#e6e6e6' }}>{s.item}</span>
                        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>
                          均{s.avg_rank} | {s.selection_rate}%选
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {stats.block_stats.length > 0 && (
                  <div>
                    <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>🚫 阻力点（按平均排序）：</div>
                    {stats.block_stats.map((s, i) => (
                      <div key={s.item} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0', fontSize: '13px' }}>
                        <span style={{ color: '#ff6b6b', fontWeight: 700, minWidth: '24px' }}>{i + 1}.</span>
                        <span style={{ flex: 1, color: '#e6e6e6' }}>{s.item}</span>
                        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>
                          均{s.avg_rank} | {s.selection_rate}%选
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
