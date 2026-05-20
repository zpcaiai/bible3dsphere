import { useEffect, useState } from 'react'
import { fetchFormationProfile, fetchFormationDimensions } from './api'
import { getToken } from './auth'

export default function PersonalityPage({ user, embedded = false }) {
  const [profile, setProfile] = useState(null)
  const [dimensions, setDimensions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        const token = getToken()
        
        // 并行加载数据
        const [profileData, dimsData] = await Promise.all([
          fetchFormationProfile(user?.id || 'demo', token).catch(() => null),
          fetchFormationDimensions(token).catch(() => null)
        ])
        
        setProfile(profileData)
        setDimensions(dimsData?.dimensions || [])
      } catch (err) {
        console.error('[PersonalityPage] Load error:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [user])

  if (loading) {
    return (
      <div style={{ 
        padding: '40px 20px', 
        textAlign: 'center',
        color: 'rgba(255,255,255,0.6)'
      }}>
        <div style={{ fontSize: '32px', marginBottom: '16px' }}>🔮</div>
        <div>加载人格塑造档案...</div>
      </div>
    )
  }

  // 获取性格维度分数
  const getDimensionScore = (key) => {
    if (!profile?.profile?.state_vector) return 0.5
    return profile.profile.state_vector[key] || 0.5
  }

  // 获取形成弧线
  const getFormationArc = () => {
    return profile?.profile?.formation_arc || 'unknown'
  }

  // 获取轨迹方向
  const getTrajectoryDirection = () => {
    return profile?.profile?.trajectory_direction || 'unknown'
  }

  // 获取主导循环
  const getDominantLoop = () => {
    return profile?.profile?.dominant_loop || '暂无数据'
  }

  // 维度颜色映射
  const dimensionColors = {
    humility: '#4ade80',
    fear_tendency: '#f87171',
    pride_tendency: '#fb923c',
    emotional_stability: '#60a5fa',
    truth_alignment: '#a78bfa',
    relational_health: '#f472b6',
    resilience: '#2dd4bf',
    spiritual_clarity: '#fbbf24'
  }

  // 维度中文名称
  const dimensionNames = {
    humility: '谦逊',
    fear_tendency: '恐惧倾向',
    pride_tendency: '骄傲倾向',
    emotional_stability: '情绪稳定',
    truth_alignment: '真理对齐',
    relational_health: '关系健康',
    resilience: '韧性',
    spiritual_clarity: '灵性清晰'
  }

  // 弧线描述
  const arcDescriptions = {
    breaking_through: { emoji: '🌅', text: '突破期', desc: '健康的维度正在增强' },
    deepening_loops: { emoji: '🔄', text: '循环深化', desc: '需要注意的行为模式' },
    stabilizing: { emoji: '⚖️', text: '稳定期', desc: '整体趋于平衡' },
    unknown: { emoji: '❓', text: '未知', desc: '数据不足' }
  }

  // 轨迹方向描述
  const trajectoryDescriptions = {
    stabilizing: { emoji: '📈', text: '趋于稳定', color: '#4ade80' },
    fragmenting: { emoji: '⚠️', text: '趋于分散', color: '#f87171' },
    improving_clarity: { emoji: '✨', text: '清晰度提升', color: '#60a5fa' },
    increasing_volatility: { emoji: '📉', text: '波动性增加', color: '#fb923c' },
    cyclical: { emoji: '🔄', text: '周期性', color: '#fbbf24' },
    unknown: { emoji: '❓', text: '未知', color: '#9ca3af' }
  }

  const arc = arcDescriptions[getFormationArc()] || arcDescriptions.unknown
  const trajectory = trajectoryDescriptions[getTrajectoryDirection()] || trajectoryDescriptions.unknown

  return (
    <div style={{ 
      padding: embedded ? '0' : '20px',
      maxWidth: '1200px',
      margin: '0 auto'
    }}>
      {/* 头部 */}
      <div style={{ 
        background: 'linear-gradient(135deg, rgba(139,92,246,0.2) 0%, rgba(59,130,246,0.2) 100%)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        border: '1px solid rgba(139,92,246,0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
          <div style={{ fontSize: '48px' }}>🔮</div>
          <div>
            <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600, color: '#fff' }}>
              人格塑造
            </h2>
            <p style={{ margin: '4px 0 0 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              性格轨迹分析 · 不是静态分数，而是动态信号
            </p>
          </div>
        </div>

        {/* 核心指标卡片 */}
        <div style={{ 
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginTop: '20px'
        }}>
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>{arc.emoji}</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>形成弧线</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>{arc.text}</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>{arc.desc}</div>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>{trajectory.emoji}</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>轨迹方向</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: trajectory.color }}>{trajectory.text}</div>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔄</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>主导循环</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{getDominantLoop()}</div>
          </div>

          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📊</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>数据点数</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>
              {profile?.profile?.data_points || 0}
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
          { key: 'overview', label: '总览', emoji: '📊' },
          { key: 'dimensions', label: '维度分析', emoji: '🎯' },
          { key: 'loops', label: '循环模式', emoji: '🔄' },
          { key: 'reflection', label: '反思问题', emoji: '💭' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 20px',
              borderRadius: '20px',
              border: 'none',
              background: activeTab === tab.key 
                ? 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)' 
                : 'rgba(255,255,255,0.1)',
              color: '#fff',
              fontSize: '14px',
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

      {/* 内容区域 */}
      {activeTab === 'overview' && (
        <div>
          {/* 8维雷达图说明 */}
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              🎯 八维性格轨迹向量
            </h3>
            <p style={{ margin: '0 0 20px 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              这些数值表示行为倾向（0.05-0.95），不是道德评分。0.5是基线，偏离表示倾向性。
            </p>

            <div style={{ 
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
              gap: '16px'
            }}>
              {Object.entries(dimensionNames).map(([key, name]) => {
                const score = getDimensionScore(key)
                const color = dimensionColors[key]
                const delta = profile?.profile?.deltas?.[key] || 0
                
                return (
                  <div 
                    key={key}
                    style={{
                      background: 'rgba(0,0,0,0.2)',
                      borderRadius: '12px',
                      padding: '16px',
                      borderLeft: `4px solid ${color}`
                    }}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <span style={{ color: '#fff', fontWeight: 500 }}>{name}</span>
                      <span style={{ 
                        color: color,
                        fontWeight: 600,
                        fontSize: '16px'
                      }}>
                        {(score * 100).toFixed(0)}%
                      </span>
                    </div>
                    
                    {/* 进度条 */}
                    <div style={{
                      height: '8px',
                      background: 'rgba(255,255,255,0.1)',
                      borderRadius: '4px',
                      overflow: 'hidden',
                      marginBottom: '8px'
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${score * 100}%`,
                        background: `linear-gradient(90deg, ${color}80, ${color})`,
                        borderRadius: '4px',
                        transition: 'width 0.5s ease'
                      }}/>
                    </div>

                    {/* 基线标记 */}
                    <div style={{ position: 'relative', height: '4px' }}>
                      <div style={{
                        position: 'absolute',
                        left: '50%',
                        top: '-6px',
                        width: '2px',
                        height: '10px',
                        background: 'rgba(255,255,255,0.3)',
                        transform: 'translateX(-50%)'
                      }}/>
                    </div>

                    {/* 变化指示 */}
                    {delta !== 0 && (
                      <div style={{ 
                        marginTop: '8px',
                        fontSize: '12px',
                        color: delta > 0 ? '#4ade80' : '#f87171'
                      }}>
                        {delta > 0 ? '↗' : '↘'} {Math.abs(delta * 100).toFixed(1)}%
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 免责声明 */}
          <div style={{
            background: 'rgba(251,191,36,0.1)',
            borderRadius: '12px',
            padding: '16px',
            border: '1px solid rgba(251,191,36,0.3)'
          }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <span style={{ fontSize: '20px' }}>⚠️</span>
              <div>
                <div style={{ fontWeight: 600, color: '#fbbf24', marginBottom: '4px' }}>重要声明</div>
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                  人格塑造系统提供的是结构化的反思镜像，而非精神权威。所有洞察都是概率性的。
                  人类的自由、恩典和奥秘总是超越任何模型所能捕捉的。这不是道德评判，而是轨迹信号。
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'dimensions' && (
        <div>
          {dimensions.map((dim, index) => (
            <div 
              key={dim.key}
              style={{
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '12px',
                padding: '20px',
                marginBottom: '16px'
              }}
            >
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px',
                marginBottom: '12px'
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: dimensionColors[dim.key] || '#888'
                }}/>
                <h4 style={{ margin: 0, color: '#fff', fontSize: '16px' }}>
                  {dim.label}
                </h4>
              </div>
              
              <p style={{ margin: '0 0 12px 0', color: 'rgba(255,255,255,0.7)', fontSize: '14px' }}>
                {dim.description}
              </p>
              
              <div style={{ 
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '8px',
                padding: '12px',
                fontSize: '13px',
                color: 'rgba(255,255,255,0.6)',
                fontStyle: 'italic'
              }}>
                💭 {dim.reflective_question}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'loops' && (
        <div>
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              🔄 主导行为循环
            </h3>
            
            <div style={{ display: 'grid', gap: '16px' }}>
              {[
                { key: 'fear_control_loop', name: '恐惧控制循环', desc: '恐惧 → 控制 → 过度工作 → 燃尽 → 恐惧', color: '#f87171' },
                { key: 'shame_avoidance_loop', name: '羞耻回避循环', desc: '羞耻 → 回避 → 拖延 → 焦虑', color: '#fb923c' },
                { key: 'pride_comparison_loop', name: '骄傲比较循环', desc: '骄傲 → 比较 → 焦虑 → 不稳定', color: '#fbbf24' },
                { key: 'desire_impulse_loop', name: '欲望冲动循环', desc: '欲望 → 冲动行为 → 后悔 → 欲望', color: '#a78bfa' },
                { key: 'truth_stability_loop', name: '真理稳定循环', desc: '面对真理 → 反思 → 稳定（健康）', color: '#4ade80' }
              ].map(loop => (
                <div 
                  key={loop.key}
                  style={{
                    background: getDominantLoop() === loop.key 
                      ? `${loop.color}20` 
                      : 'rgba(0,0,0,0.2)',
                    borderRadius: '12px',
                    padding: '16px',
                    border: getDominantLoop() === loop.key 
                      ? `2px solid ${loop.color}` 
                      : '1px solid rgba(255,255,255,0.1)'
                  }}
                >
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    gap: '12px',
                    marginBottom: '8px'
                  }}>
                    <span style={{ 
                      fontSize: '12px',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: loop.color,
                      color: '#000',
                      fontWeight: 600
                    }}>
                      {getDominantLoop() === loop.key ? '当前主导' : '循环类型'}
                    </span>
                    <span style={{ color: '#fff', fontWeight: 500 }}>{loop.name}</span>
                  </div>
                  <p style={{ margin: 0, color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
                    {loop.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'reflection' && (
        <div>
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              💭 反思性问题
            </h3>
            <p style={{ margin: '0 0 20px 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              这些问题不是为了得到"正确答案"，而是为了培养自我觉察。选择最能触动你的问题深入思考。
            </p>

            <div style={{ display: 'grid', gap: '16px' }}>
              {dimensions.map((dim, index) => (
                <div 
                  key={dim.key}
                  style={{
                    background: 'rgba(0,0,0,0.2)',
                    borderRadius: '12px',
                    padding: '20px',
                    borderLeft: `4px solid ${dimensionColors[dim.key] || '#888'}`
                  }}
                >
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '8px'
                  }}>
                    <span style={{ fontSize: '20px' }}>💭</span>
                    <span style={{ color: '#fff', fontWeight: 500 }}>{dim.label}</span>
                  </div>
                  <p style={{ 
                    margin: 0, 
                    color: 'rgba(255,255,255,0.8)', 
                    fontSize: '15px',
                    lineHeight: 1.6,
                    fontStyle: 'italic'
                  }}>
                    "{dim.reflective_question}"
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
