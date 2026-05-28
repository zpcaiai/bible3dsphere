import { useEffect, useState } from 'react'
import { fetchBehaviorHistory, fetchBehaviorStats, regulateBehavior, fetchHabits } from './api'
import { getToken } from './auth'

export default function BehaviorPage({ user, embedded = false, onNeedLogin }) {
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [habits, setHabits] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('regulate')
  const [regulationInput, setRegulationInput] = useState({
    task: '',
    energyLevel: 3,
    motivation: 5
  })
  const [regulationResult, setRegulationResult] = useState(null)
  const [regulating, setRegulating] = useState(false)
  const [regulateError, setRegulateError] = useState(null)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        const token = getToken()
        
        // 并行加载数据
        const [historyData, statsData, habitsData] = await Promise.all([
          fetchBehaviorHistory(user?.id || 'demo', token, 30).catch(() => ({ items: [] })),
          fetchBehaviorStats(user?.id || 'demo', token).catch(() => null),
          fetchHabits(token).catch(() => ({ items: [] }))
        ])
        
        setHistory(historyData?.items || [])
        setStats(statsData)
        setHabits(habitsData?.items || [])
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
    if (!user) {
      onNeedLogin?.('登录后才能保存行为调节记录，已输入的内容不会丢失')
      return
    }

    setRegulateError(null)
    setRegulationResult(null)

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
      setRegulateError(err.message || '后端服务未运行，请先启动后端服务')
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
          { key: 'regulate', label: '行为调节', emoji: '⚡' },
          { key: 'history', label: '执行历史', emoji: '📜' },
          { key: 'unity', label: '知行合一', emoji: '🌿' },
          { key: 'dashboard', label: '仪表盘', emoji: '📊' }
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
          {/* 电路层级统计 */}
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px'
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
                  <div key={tier} style={{
                    background: 'rgba(0,0,0,0.2)',
                    borderRadius: '12px',
                    padding: '20px',
                    borderLeft: `4px solid ${color}`
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ color: '#fff', fontWeight: 600, fontSize: '16px' }}>{name}</span>
                      <span style={{ color, fontWeight: 700, fontSize: '20px' }}>{count}</span>
                    </div>
                    <p style={{ margin: '0 0 12px 0', color: 'rgba(255,255,255,0.6)', fontSize: '13px' }}>{desc}</p>
                    <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ width: `${percentage}%`, height: '100%', background: color, borderRadius: '4px' }}/>
                    </div>
                    <div style={{ textAlign: 'right', color: 'rgba(255,255,255,0.5)', fontSize: '12px', marginTop: '4px' }}>
                      {percentage.toFixed(2)}%
                    </div>
                  </div>
                )
              })}
            </div>
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

          {/* 行为调节输入区 */}
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px',
            marginTop: '24px'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', color: '#fff' }}>
              ⚡ 立即调节
            </h3>
            <p style={{ margin: '0 0 16px 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              输入你当前的任务，系统会根据你的能量水平推荐最小可执行动作，并评估属灵对齐。
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

              {regulateError && (
                <div style={{
                  marginTop: '12px',
                  padding: '12px 16px',
                  background: 'rgba(239,68,68,0.15)',
                  borderRadius: '8px',
                  border: '1px solid rgba(239,68,68,0.4)',
                  color: '#fca5a5',
                  fontSize: '13px'
                }}>
                  ⚠️ {regulateError}
                </div>
              )}
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

                {/* 属灵对齐评估 */}
                {regulationResult.spiritual_alignment && (
                  <div style={{
                    marginTop: '16px',
                    padding: '16px',
                    background: regulationResult.spiritual_alignment.aligned ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                    borderRadius: '12px',
                    border: `2px solid ${regulationResult.spiritual_alignment.aligned ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)'}`,
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      marginBottom: '12px'
                    }}>
                      <span style={{ fontSize: '20px' }}>
                        {regulationResult.spiritual_alignment.aligned ? '✅' : '⚠️'}
                      </span>
                      <div>
                        <div style={{
                          color: regulationResult.spiritual_alignment.aligned ? '#4ade80' : '#f87171',
                          fontSize: '14px',
                          fontWeight: 600
                        }}>
                          属灵对齐评估 · {regulationResult.spiritual_alignment.aligned ? '与神的道对齐' : '需要调整对齐'}
                        </div>
                        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px' }}>
                          对齐度: {regulationResult.spiritual_alignment.alignment_score}/100 · {regulationResult.spiritual_alignment.scripture_reference}
                        </div>
                      </div>
                    </div>

                    <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px', lineHeight: 1.6, marginBottom: '10px' }}>
                      {regulationResult.spiritual_alignment.assessment}
                    </div>

                    <div style={{
                      padding: '8px 12px',
                      background: 'rgba(255,255,255,0.05)',
                      borderRadius: '6px',
                      marginBottom: '10px'
                    }}>
                      <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px', marginBottom: '4px' }}>
                        📖 经文原则
                      </div>
                      <div style={{ color: '#fbbf24', fontSize: '13px', fontStyle: 'italic' }}>
                        {regulationResult.spiritual_alignment.principle}
                      </div>
                    </div>

                    {regulationResult.spiritual_alignment.misalignment_areas && regulationResult.spiritual_alignment.misalignment_areas.length > 0 && (
                      <div style={{ marginBottom: '10px' }}>
                        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '6px', fontWeight: 500 }}>
                          🔍 不对齐领域
                        </div>
                        {regulationResult.spiritual_alignment.misalignment_areas.map((area, idx) => (
                          <div key={idx} style={{
                            display: 'inline-block',
                            padding: '4px 10px',
                            background: 'rgba(239,68,68,0.15)',
                            borderRadius: '4px',
                            color: '#fca5a5',
                            fontSize: '12px',
                            marginRight: '6px',
                            marginBottom: '4px'
                          }}>
                            {area}
                          </div>
                        ))}
                      </div>
                    )}

                    {regulationResult.spiritual_alignment.alignment_actions && regulationResult.spiritual_alignment.alignment_actions.length > 0 && (
                      <div>
                        <div style={{ color: regulationResult.spiritual_alignment.aligned ? '#4ade80' : '#fbbf24', fontSize: '12px', marginBottom: '6px', fontWeight: 500 }}>
                          {regulationResult.spiritual_alignment.aligned ? '🌟 深化建议' : '🛠️ 参考对齐行动'}
                        </div>
                        <div style={{ display: 'grid', gap: '6px' }}>
                          {regulationResult.spiritual_alignment.alignment_actions.map((action, idx) => (
                            <div key={idx} style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '8px',
                              padding: '8px 12px',
                              background: 'rgba(255,255,255,0.05)',
                              borderRadius: '6px'
                            }}>
                              <span style={{ color: regulationResult.spiritual_alignment.aligned ? '#4ade80' : '#fbbf24', fontSize: '14px', marginTop: '2px' }}>
                                {idx + 1}.
                              </span>
                              <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '13px', lineHeight: 1.5 }}>
                                {action}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
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
                <div style={{ fontSize: '12px', marginTop: '8px' }}>在"行为调节"标签页使用行为调节，或在"习惯养成"里执行习惯</div>
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
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>
                          {new Date(item.executed_at).toLocaleString('zh-CN')}
                        </div>
                        <div style={{
                          padding: '2px 7px', borderRadius: '4px', fontSize: '11px', fontWeight: 500,
                          background: item.source === 'habit' ? 'rgba(52,199,89,0.15)' : 'rgba(0,122,255,0.15)',
                          color: item.source === 'habit' ? '#34c759' : '#007aff',
                        }}>
                          {item.source === 'habit' ? '🌱 习惯' : '⚡ 行为调节'}
                        </div>
                        {item.tokens_earned != null && (
                          <div style={{ color: '#ffd700', fontSize: '11px' }}>🪙 +{item.tokens_earned}</div>
                        )}
                        {item.spiritual_alignment && (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: item.spiritual_alignment.aligned ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                            color: item.spiritual_alignment.aligned ? '#4ade80' : '#f87171',
                            fontSize: '11px',
                            fontWeight: 500
                          }}>
                            {item.spiritual_alignment.aligned ? '✅' : '⚠️'}
                            {item.spiritual_alignment.aligned ? '对齐' : '需调整'}
                            {item.spiritual_alignment.alignment_score > 0 && ` · ${item.spiritual_alignment.alignment_score}`}
                          </div>
                        )}
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

      {/* 知行合一达成率 */}
      {activeTab === 'unity' && (() => {
        const habitExecs = history.filter(h => h.source === 'habit')
        const habitCompleted = habitExecs.filter(h => h.was_completed).length
        const totalHabits = habits.length
        const executedHabitIds = new Set(habitExecs.map(h => h.habit_id).filter(Boolean))
        const coveredHabits = executedHabitIds.size

        const execRate = habitExecs.length > 0
          ? parseFloat(((habitCompleted / habitExecs.length) * 100).toFixed(1))
          : 0
        const coverRate = totalHabits > 0
          ? parseFloat(((coveredHabits / totalHabits) * 100).toFixed(1))
          : 0
        const unityRate = totalHabits > 0
          ? parseFloat((((habitCompleted + coveredHabits) / (habitExecs.length + totalHabits || 1)) * 100).toFixed(1))
          : execRate

        const getColor = (rate) => rate >= 75 ? '#4ade80' : rate >= 50 ? '#eab308' : '#f87171'
        const getLabel = (rate) => rate >= 75 ? '稳固成长' : rate >= 50 ? '持续操练中' : '需要更多行道'

        return (
          <div style={{ display: 'grid', gap: '20px' }}>
            {/* 主达成率卡片 */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(34,197,94,0.15) 0%, rgba(59,130,246,0.15) 100%)',
              borderRadius: '16px',
              padding: '28px',
              border: '1px solid rgba(34,197,94,0.3)',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)', marginBottom: '8px' }}>
                🌿 知行合一达成率
              </div>
              <div style={{
                fontSize: '64px',
                fontWeight: 800,
                color: getColor(unityRate),
                lineHeight: 1,
                marginBottom: '8px'
              }}>
                {unityRate}%
              </div>
              <div style={{
                display: 'inline-block',
                padding: '4px 14px',
                borderRadius: '20px',
                background: `${getColor(unityRate)}22`,
                color: getColor(unityRate),
                fontSize: '13px',
                fontWeight: 600,
                marginBottom: '20px'
              }}>
                {getLabel(unityRate)}
              </div>

              {/* 进度环形条 */}
              <div style={{
                height: '12px',
                background: 'rgba(255,255,255,0.1)',
                borderRadius: '6px',
                overflow: 'hidden',
                marginBottom: '8px'
              }}>
                <div style={{
                  width: `${unityRate}%`,
                  height: '100%',
                  background: `linear-gradient(90deg, ${getColor(unityRate)}, #3b82f6)`,
                  borderRadius: '6px',
                  transition: 'width 0.6s ease'
                }}/>
              </div>
              <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
                基于习惯执行完成率 × 习惯覆盖率
              </div>
            </div>

            {/* 两项子指标 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '12px',
                padding: '20px',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>
                  ✅ 习惯执行完成率
                </div>
                <div style={{ fontSize: '32px', fontWeight: 700, color: getColor(execRate) }}>
                  {execRate}%
                </div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
                  {habitCompleted} / {habitExecs.length} 次完成
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginTop: '10px' }}>
                  <div style={{ width: `${execRate}%`, height: '100%', background: getColor(execRate), borderRadius: '3px' }}/>
                </div>
              </div>

              <div style={{
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '12px',
                padding: '20px',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>
                  📋 习惯覆盖率
                </div>
                <div style={{ fontSize: '32px', fontWeight: 700, color: getColor(coverRate) }}>
                  {coverRate}%
                </div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
                  {coveredHabits} / {totalHabits || '--'} 个习惯已执行
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginTop: '10px' }}>
                  <div style={{ width: `${coverRate}%`, height: '100%', background: getColor(coverRate), borderRadius: '3px' }}/>
                </div>
              </div>
            </div>

            {/* 雅各书鼓励卡 */}
            <div style={{
              background: 'rgba(251,191,36,0.08)',
              borderRadius: '16px',
              padding: '24px',
              border: '1px solid rgba(251,191,36,0.3)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <span style={{ fontSize: '22px' }}>📖</span>
                <div>
                  <div style={{ color: '#fbbf24', fontWeight: 600, fontSize: '15px' }}>雅各书 1:22</div>
                  <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>James 1:22</div>
                </div>
              </div>

              <div style={{
                color: '#fff',
                fontSize: '16px',
                lineHeight: 1.9,
                fontStyle: 'italic',
                marginBottom: '16px',
                paddingLeft: '12px',
                borderLeft: '3px solid rgba(251,191,36,0.5)'
              }}>
                "你们要行道，不要单单听道，自己欺哄自己。"
              </div>

              <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: '13px', lineHeight: 1.7, marginBottom: '16px' }}>
                听道是起点，行道才是果子。每一次习惯执行，都是把所听的道，
                落实成生命的行动；每一次坚持，都是信心在生活中的见证。
              </div>

              {unityRate < 50 && (
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(239,68,68,0.1)',
                  borderRadius: '8px',
                  border: '1px solid rgba(239,68,68,0.25)',
                  color: '#fca5a5',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  marginBottom: '12px'
                }}>
                  💡 现在还有空间成长。先从一个习惯开始行动，哪怕只完成5分钟——
                  这一步，就是行道的开始。（雅各书 2:17 — "信心若没有行为就是死的"）
                </div>
              )}

              {unityRate >= 50 && unityRate < 75 && (
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(234,179,8,0.1)',
                  borderRadius: '8px',
                  border: '1px solid rgba(234,179,8,0.25)',
                  color: '#fde68a',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  marginBottom: '12px'
                }}>
                  🌱 你正在操练行道！继续保持，不要因偶尔中断灰心——
                  重要的是每次都重新站起来。（雅各书 1:4 — "忍耐也当成功，使你们成全完备"）
                </div>
              )}

              {unityRate >= 75 && (
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(34,197,94,0.1)',
                  borderRadius: '8px',
                  border: '1px solid rgba(34,197,94,0.25)',
                  color: '#86efac',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  marginBottom: '12px'
                }}>
                  🌟 你是行道之人！神的话语正在你身上结出果子。
                  继续让每一个小行动成为荣耀神的见证。（雅各书 1:25 — "察看那全备、使人自由之律法的……这人所行的必然得福"）
                </div>
              )}

              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.04)',
                borderRadius: '8px',
                color: 'rgba(255,255,255,0.4)',
                fontSize: '12px'
              }}>
                <span>💬</span>
                <span>知行合一达成率 = 习惯执行完成率 × 习惯覆盖率的综合评估，反映你将所知化为所行的程度。</span>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
