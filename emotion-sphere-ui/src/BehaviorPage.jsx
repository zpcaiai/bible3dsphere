import { useEffect, useState } from 'react'
import { fetchBehaviorHistory, fetchBehaviorStats, regulateBehavior } from './api'
import { getToken } from './auth'

export default function BehaviorPage({ user, embedded = false }) {
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [regulationInput, setRegulationInput] = useState({
    task: '',
    energyLevel: 3,
    motivation: 5
  })
  const [regulationResult, setRegulationResult] = useState(null)
  const [regulating, setRegulating] = useState(false)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        const token = getToken()
        
        // 并行加载数据
        const [historyData, statsData] = await Promise.all([
          fetchBehaviorHistory(user?.id || 'demo', token, 30).catch(() => ({ items: [] })),
          fetchBehaviorStats(user?.id || 'demo', token).catch(() => null)
        ])
        
        setHistory(historyData?.items || [])
        setStats(statsData)
      } catch (err) {
        console.error('[BehaviorPage] Load error:', err)
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [user])

  const handleRegulate = async () => {
    if (!regulationInput.task.trim()) return
    
    try {
      setRegulating(true)
      const token = getToken()
      const result = await regulateBehavior(
        regulationInput.task,
        regulationInput.energyLevel,
        regulationInput.motivation,
        token
      )
      setRegulationResult(result)
    } catch (err) {
      console.error('[BehaviorPage] Regulate error:', err)
    } finally {
      setRegulating(false)
    }
  }

  if (loading) {
    return (
      <div style={{ 
        padding: '40px 20px', 
        textAlign: 'center',
        color: 'rgba(255,255,255,0.6)'
      }}>
        <div style={{ fontSize: '32px', marginBottom: '16px' }}>📈</div>
        <div>加载行为追踪数据...</div>
      </div>
    )
  }

  // 计算统计数据
  const totalExecutions = history.length
  const completedExecutions = history.filter(h => h.was_completed).length
  const completionRate = totalExecutions > 0 
    ? parseFloat(((completedExecutions / totalExecutions) * 100).toFixed(2))
    : 0

  // 按层级统计
  const tierStats = history.reduce((acc, h) => {
    acc[h.tier_executed] = (acc[h.tier_executed] || 0) + 1
    return acc
  }, {})

  // 最近7天的活动
  const last7Days = history.filter(h => {
    const daysDiff = (new Date() - new Date(h.executed_at)) / (1000 * 60 * 60 * 24)
    return daysDiff <= 7
  })

  // 能量等级分布
  const energyDistribution = history.reduce((acc, h) => {
    const level = h.energy_level || 3
    acc[level] = (acc[level] || 0) + 1
    return acc
  }, {})

  return (
    <div style={{ 
      padding: embedded ? '0' : '20px',
      maxWidth: '1200px',
      margin: '0 auto'
    }}>
      {/* 头部 */}
      <div style={{ 
        background: 'linear-gradient(135deg, rgba(34,197,94,0.2) 0%, rgba(59,130,246,0.2) 100%)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        border: '1px solid rgba(34,197,94,0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
          <div style={{ fontSize: '48px' }}>📈</div>
          <div>
            <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600, color: '#fff' }}>
              行为追踪
            </h2>
            <p style={{ margin: '4px 0 0 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              行为调节历史 · 执行追踪 · 趋势分析
            </p>
          </div>
        </div>

        {/* 核心指标卡片 */}
        <div style={{ 
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '12px'
        }}>
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#4ade80' }}>
              {totalExecutions}
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
              总执行次数
            </div>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#60a5fa' }}>
              {completionRate}%
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
              完成率
            </div>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#fbbf24' }}>
              {last7Days.length}
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
              近7天活动
            </div>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f472b6' }}>
              {stats?.avg_completion_percentage?.toFixed(2) || '0.00'}%
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
              平均完成度
            </div>
          </div>
        </div>
      </div>

      {/* 子标签页 */}
      <div style={{ 
        display: 'flex', 
        gap: '8px', 
        marginBottom: '24px',
        flexWrap: 'wrap'
      }}>
        {[
          { key: 'dashboard', label: '仪表盘', emoji: '📊' },
          { key: 'regulate', label: '行为调节', emoji: '⚡' },
          { key: 'history', label: '执行历史', emoji: '📜' },
          { key: 'tiers', label: '层级分析', emoji: '🎯' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 20px',
              borderRadius: '20px',
              border: 'none',
              background: activeTab === tab.key 
                ? 'linear-gradient(135deg, #22c55e 0%, #3b82f6 100%)' 
                : 'rgba(255,255,255,0.1)',
              color: '#fff',
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>{tab.emoji}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* 仪表盘 */}
      {activeTab === 'dashboard' && (
        <div>
          {/* 行为调节器 */}
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', color: '#fff' }}>
              ⚡ 快速行为调节
            </h3>
            <p style={{ margin: '0 0 16px 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              输入你当前的任务，系统会根据你的能量水平推荐最小可执行动作。
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input
                type="text"
                placeholder="输入任务（例如：写报告、运动、阅读...）"
                value={regulationInput.task}
                onChange={(e) => setRegulationInput({...regulationInput, task: e.target.value})}
                style={{
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: 'rgba(0,0,0,0.2)',
                  color: '#fff',
                  fontSize: '14px'
                }}
              />

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '150px' }}>
                  <label style={{ display: 'block', color: 'rgba(255,255,255,0.6)', fontSize: '12px', marginBottom: '6px' }}>
                    能量水平 (1-5)
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={regulationInput.energyLevel}
                    onChange={(e) => setRegulationInput({...regulationInput, energyLevel: parseInt(e.target.value)})}
                    style={{ width: '100%' }}
                  />
                  <div style={{ textAlign: 'center', color: '#fff', marginTop: '4px' }}>
                    {regulationInput.energyLevel === 1 && '🔴 极低'}
                    {regulationInput.energyLevel === 2 && '🟠 低'}
                    {regulationInput.energyLevel === 3 && '🟡 中等'}
                    {regulationInput.energyLevel === 4 && '🟢 高'}
                    {regulationInput.energyLevel === 5 && '🔵 极高'}
                  </div>
                </div>

                <div style={{ flex: 1, minWidth: '150px' }}>
                  <label style={{ display: 'block', color: 'rgba(255,255,255,0.6)', fontSize: '12px', marginBottom: '6px' }}>
                    动机 (1-10)
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={regulationInput.motivation}
                    onChange={(e) => setRegulationInput({...regulationInput, motivation: parseInt(e.target.value)})}
                    style={{ width: '100%' }}
                  />
                  <div style={{ textAlign: 'center', color: '#fff', marginTop: '4px' }}>
                    {regulationInput.motivation <= 3 && '😴 低'}
                    {regulationInput.motivation > 3 && regulationInput.motivation <= 6 && '😐 中等'}
                    {regulationInput.motivation > 6 && regulationInput.motivation <= 8 && '🙂 高'}
                    {regulationInput.motivation > 8 && '🤩 极高'}
                  </div>
                </div>
              </div>

              <button
                onClick={handleRegulate}
                disabled={!regulationInput.task.trim() || regulating}
                style={{
                  padding: '12px 24px',
                  borderRadius: '8px',
                  border: 'none',
                  background: regulating ? 'rgba(255,255,255,0.2)' : 'linear-gradient(135deg, #22c55e 0%, #3b82f6 100%)',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: regulating ? 'not-allowed' : 'pointer'
                }}
              >
                {regulating ? '分析中...' : '获取调节建议'}
              </button>
            </div>

            {/* 调节结果 */}
            {regulationResult && (
              <div style={{
                marginTop: '20px',
                padding: '20px',
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '12px',
                border: '1px solid rgba(34,197,94,0.3)'
              }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '12px',
                  marginBottom: '16px'
                }}>
                  <span style={{ 
                    padding: '6px 12px',
                    borderRadius: '6px',
                    background: regulationResult.selected_tier === 'Green' ? '#22c55e' : 
                               regulationResult.selected_tier === 'Yellow' ? '#eab308' : '#ef4444',
                    color: '#000',
                    fontWeight: 600,
                    fontSize: '14px'
                  }}>
                    {regulationResult.selected_tier} 电路
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
                    阻力: {regulationResult.current_resistance}/10
                  </span>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '12px', marginBottom: '4px' }}>
                    最小可执行动作
                  </div>
                  <div style={{ color: '#fff', fontSize: '16px', fontWeight: 500 }}>
                    {regulationResult.min_executable_action}
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '12px', marginBottom: '4px' }}>
                    任务降级版本
                  </div>
                  <div style={{ color: '#fff', fontSize: '14px' }}>
                    {regulationResult.task_downgrade}
                  </div>
                </div>

                <div style={{ 
                  padding: '12px',
                  background: 'rgba(251,191,36,0.1)',
                  borderRadius: '8px',
                  border: '1px solid rgba(251,191,36,0.3)',
                  marginBottom: '12px'
                }}>
                  <div style={{ color: '#fbbf24', fontSize: '12px', marginBottom: '4px' }}>
                    💚 情感补偿
                  </div>
                  <div style={{ color: '#fff', fontSize: '14px' }}>
                    {regulationResult.emotional_compensation}
                  </div>
                </div>

                <div style={{ 
                  padding: '12px',
                  background: 'rgba(34,197,94,0.1)',
                  borderRadius: '8px',
                  border: '1px solid rgba(34,197,94,0.3)'
                }}>
                  <div style={{ color: '#4ade80', fontSize: '12px', marginBottom: '4px' }}>
                    💡 连续性建议
                  </div>
                  <div style={{ color: '#fff', fontSize: '14px' }}>
                    {regulationResult.continuity_advice}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 能量分布 */}
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              📊 能量等级分布
            </h3>
            
            <div style={{ display: 'grid', gap: '12px' }}>
              {[1, 2, 3, 4, 5].map(level => {
                const count = energyDistribution[level] || 0
                const total = totalExecutions || 1
                const percentage = parseFloat(((count / total) * 100).toFixed(2))
                
                const colors = {
                  1: '#ef4444',
                  2: '#f97316', 
                  3: '#eab308',
                  4: '#22c55e',
                  5: '#3b82f6'
                }
                
                const labels = {
                  1: '🔴 极低',
                  2: '🟠 低',
                  3: '🟡 中等',
                  4: '🟢 高',
                  5: '🔵 极高'
                }
                
                return (
                  <div key={level} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '80px', fontSize: '14px', color: 'rgba(255,255,255,0.8)' }}>
                      {labels[level]}
                    </div>
                    <div style={{ flex: 1, height: '24px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{
                        width: `${percentage}%`,
                        height: '100%',
                        background: colors[level],
                        borderRadius: '4px',
                        transition: 'width 0.3s'
                      }}/>
                    </div>
                    <div style={{ width: '60px', textAlign: 'right', fontSize: '14px', color: '#fff' }}>
                      {count} ({percentage.toFixed(2)}%)
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* 行为调节标签 */}
      {activeTab === 'regulate' && (
        <div>
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', color: '#fff' }}>
              🧠 行为调节原理
            </h3>
            
            <div style={{ display: 'grid', gap: '16px' }}>
              <div style={{
                background: 'rgba(34,197,94,0.1)',
                borderRadius: '12px',
                padding: '20px',
                border: '1px solid rgba(34,197,94,0.3)'
              }}>
                <h4 style={{ margin: '0 0 12px 0', color: '#4ade80', fontSize: '16px' }}>
                  🟢 Green 电路 (高能量)
                </h4>
                <p style={{ margin: 0, color: 'rgba(255,255,255,0.8)', fontSize: '14px', lineHeight: 1.6 }}>
                  能量 ≥4，低阻力状态。适合执行完整任务版本，保持节奏但不要过度消耗。
                </p>
              </div>

              <div style={{
                background: 'rgba(234,179,8,0.1)',
                borderRadius: '12px',
                padding: '20px',
                border: '1px solid rgba(234,179,8,0.3)'
              }}>
                <h4 style={{ margin: '0 0 12px 0', color: '#eab308', fontSize: '16px' }}>
                  🟡 Yellow 电路 (中等能量)
                </h4>
                <p style={{ margin: 0, color: 'rgba(255,255,255,0.8)', fontSize: '14px', lineHeight: 1.6 }}>
                  能量 =3，正常阻力。任务简化至5分钟版本，完成50%也算成功。
                </p>
              </div>

              <div style={{
                background: 'rgba(239,68,68,0.1)',
                borderRadius: '12px',
                padding: '20px',
                border: '1px solid rgba(239,68,68,0.3)'
              }}>
                <h4 style={{ margin: '0 0 12px 0', color: '#f87171', fontSize: '16px' }}>
                  🔴 Red 电路 (低能量)
                </h4>
                <p style={{ margin: 0, color: 'rgba(255,255,255,0.8)', fontSize: '14px', lineHeight: 1.6 }}>
                  能量 ≤2，高阻力状态。60秒原子动作，任何微小启动都算成功。系统智能降级保护心理连续性。
                </p>
              </div>
            </div>

            <div style={{
              marginTop: '24px',
              padding: '16px',
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '12px'
            }}>
              <h4 style={{ margin: '0 0 12px 0', color: '#fff', fontSize: '14px' }}>
                💡 核心原则
              </h4>
              <ul style={{ margin: 0, padding: '0 0 0 20px', color: 'rgba(255,255,255,0.7)', fontSize: '14px', lineHeight: 1.8 }}>
                <li>行为启动 &gt; 行为完成</li>
                <li>避免羞耻感</li>
                <li>降低认知负担</li>
                <li>小步持续优于短期爆发</li>
                <li>失败时优先保护心理连续性</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* 执行历史 */}
      {activeTab === 'history' && (
        <div>
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              📜 执行历史 (最近30次)
            </h3>

            {history.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'rgba(255,255,255,0.5)' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>📭</div>
                <div>暂无执行记录</div>
                <div style={{ fontSize: '12px', marginTop: '8px' }}>在"行为调节"标签页开始使用</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '12px' }}>
                {history.slice(0, 30).map((item, index) => (
                  <div 
                    key={index}
                    style={{
                      background: 'rgba(0,0,0,0.2)',
                      borderRadius: '10px',
                      padding: '16px',
                      display: 'grid',
                      gridTemplateColumns: 'auto 1fr auto',
                      gap: '16px',
                      alignItems: 'center'
                    }}
                  >
                    {/* 层级标识 */}
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '50%',
                      background: item.tier_executed === 'Green' ? '#22c55e' :
                                  item.tier_executed === 'Yellow' ? '#eab308' : '#ef4444',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      fontWeight: 700,
                      color: '#000'
                    }}>
                      {item.tier_executed?.[0] || '?'}
                    </div>

                    {/* 内容 */}
                    <div>
                      <div style={{ color: '#fff', fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>
                        {item.task || '未知任务'}
                      </div>
                      <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>
                        {new Date(item.executed_at).toLocaleString('zh-CN')}
                      </div>
                    </div>

                    {/* 状态 */}
                    <div style={{ textAlign: 'right' }}>
                      <div style={{
                        color: item.was_completed ? '#4ade80' : '#f87171',
                        fontSize: '14px',
                        fontWeight: 500
                      }}>
                        {item.was_completed ? '✅ 完成' : '⏸️ 部分'}
                      </div>
                      <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px', marginTop: '2px' }}>
                        {item.completion_percentage || 0}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 层级分析 */}
      {activeTab === 'tiers' && (
        <div>
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              🎯 电路层级统计
            </h3>

            <div style={{ display: 'grid', gap: '16px' }}>
              {[
                { tier: 'Green', name: 'Green 电路', color: '#22c55e', desc: '高能量，完整执行' },
                { tier: 'Yellow', name: 'Yellow 电路', color: '#eab308', desc: '中等能量，简化执行' },
                { tier: 'Red', name: 'Red 电路', color: '#ef4444', desc: '低能量，原子动作' }
              ].map(({ tier, name, color, desc }) => {
                const count = tierStats[tier] || 0
                const total = totalExecutions || 1
                const percentage = parseFloat(((count / total) * 100).toFixed(2))
                
                return (
                  <div 
                    key={tier}
                    style={{
                      background: 'rgba(0,0,0,0.2)',
                      borderRadius: '12px',
                      padding: '20px',
                      borderLeft: `4px solid ${color}`
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ color: '#fff', fontWeight: 600, fontSize: '16px' }}>{name}</span>
                      <span style={{ color, fontWeight: 700, fontSize: '20px' }}>{count}</span>
                    </div>
                    <p style={{ margin: '0 0 12px 0', color: 'rgba(255,255,255,0.6)', fontSize: '13px' }}>{desc}</p>
                    <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{
                        width: `${percentage}%`,
                        height: '100%',
                        background: color,
                        borderRadius: '4px'
                      }}/>
                    </div>
                    <div style={{ textAlign: 'right', color: 'rgba(255,255,255,0.5)', fontSize: '12px', marginTop: '4px' }}>
                      {percentage.toFixed(2)}%
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
