import { useEffect, useState } from 'react'
import { fetchFormationProfile, fetchFormationDimensions } from './api'
import { getToken } from './auth'

const REFLECTION_CATEGORIES = [
  {
    key: 'god_relationship',
    label: '\u7b2c\u4e00\u985e\uff1a\u8207\u795e\u7684\u95dc\u4fc2\uff08\u6838\u5fc3\u6839\u57fa\uff09',
    emoji: '\u{1F54F}',
    color: '#fbbf24',
    lesson: '\u4fe1\u9760\u3001\u89aa\u8fd1\u795e\u3001\u807d\u5f9e\u8056\u9748',
    questions: [
      '\u6211\u6bcf\u5929/\u6bcf\u9031\u8207\u795e\u89aa\u5bc6\u76f8\u4ea4\uff08\u8b80\u7d93+\u7977\u544a\uff09\u7684\u6642\u9593\u548c\u54c1\u8cea\u5982\u4f55\uff1f\u662f\u5426\u6d41\u65bc\u5f62\u5f0f\uff1f',
      '\u7576\u6211\u9047\u5230\u56f0\u96e3\u6642\uff0c\u7b2c\u4e00\u53cd\u61c9\u662f\u5012\u9760\u795e\u3001\u9084\u662f\u5148\u9760\u81ea\u5df1\u6216\u4ed6\u4eba\uff1f',
      '\u6211\u6700\u8fd1\u5728\u8b80\u7d93\u6216\u807d\u9053\u6642\uff0c\u795e\u6700\u5e38\u611f\u52d5\u6216\u8cac\u5099\u6211\u7684\u7d93\u6587\u6216\u4e3b\u984c\u662f\u4ec0\u9ebc\uff1f',
      '\u6211\u662f\u5426\u771f\u6b63\u76f8\u4fe1\u795e\u5728\u6211\u751f\u547d\u4e2d\u638c\u6b0a\uff0c\u4e26\u70ba\u6211\u6709\u7f8e\u597d\u7684\u8a08\u5283\uff1f\uff08\u6709\u6c92\u6709\u96b1\u85cf\u7684\u4e0d\u4fe1\u6216\u57cb\u6028\uff1f\uff09',
    ]
  },
  {
    key: 'character',
    label: '\u7b2c\u4e8c\u985e\uff1a\u54c1\u683c\u8207\u5167\u5fc3\uff08\u8056\u9748\u679c\u5b50\uff09',
    emoji: '\u{1F33F}',
    color: '#4ade80',
    lesson: '\u5fcd\u8010\u3001\u8b19\u5351\u3001\u9952\u6046\u3001\u7bc0\u5236',
    questions: [
      '\u5728\u58d3\u529b\u3001\u59d4\u5c48\u6216\u88ab\u6279\u8a55\u6642\uff0c\u6211\u6700\u5e38\u8868\u73fe\u51fa\u4ec0\u9ebc\u60c5\u7dd2\u6216\u884c\u70ba\uff1f\uff08\u5982\u61a4\u6012\u3001\u9000\u7e2e\u3001\u63a7\u8a34\uff09',
      '\u6211\u751f\u547d\u4e2d\u7f3a\u5c11\u8056\u9748\u679c\u5b50\uff08\u52a0\u62c9\u592a\u66f85:22-23\uff09\u6700\u660e\u986f\u7684\u662f\u54ea\u4e00\u9805\uff1f\uff08\u4ec1\u611b\u3001\u559c\u6a02\u3001\u548c\u5e73\u3001\u5fcd\u8010\u3001\u6069\u6148\u3001\u826f\u5584\u3001\u4fe1\u5be6\u3001\u6e29\u67d4\u3001\u7bc0\u5236\uff09',
      '\u6211\u662f\u5426\u5bb9\u6613\u5ac9\u598d\u3001\u6bd4\u8f03\u3001\u6216\u5728\u610f\u4ed6\u4eba\u5c0d\u6211\u7684\u770b\u6cd5\uff1f',
      '\u6211\u5728\u5c0f\u4e8b\u4e0a\u662f\u5426\u8aa0\u5be6\u3001\u5b88\u6642\u3001\u76e1\u8cac\uff1f\u6709\u54ea\u4e9b\u300c\u5c0f\u7f6a\u300d\u6211\u5e38\u5e38\u8f15\u5ffd\uff1f',
    ]
  },
  {
    key: 'relationships',
    label: '\u7b2c\u4e09\u985e\uff1a\u4eba\u969b\u95dc\u4fc2\u8207\u5718\u5951',
    emoji: '\u{1F91D}',
    color: '#f472b6',
    lesson: '\u611b\u4eba\u5982\u5df1\u3001\u9952\u6046\u3001\u8b19\u5351\u670d\u4e8b',
    questions: [
      '\u6211\u8207\u6700\u89aa\u8fd1\u7684\u4eba\uff08\u914d\u5076\u3001\u5bb6\u4eba\u3001\u670b\u53cb\uff09\u6700\u8fd1\u6700\u5e38\u767c\u751f\u7684\u885d\u7a81\u662f\u4ec0\u9ebc\uff1f\u80cc\u5f8c\u7684\u539f\u56e0\u662f\uff1f',
      '\u6211\u662f\u5426\u4e3b\u52d5\u95dc\u5fc3\u4ed6\u4eba\u3001\u9952\u6046\u4ed6\u4eba\uff0c\u9084\u662f\u5bb9\u6613\u8a18\u6068\u6216\u8ad6\u65b7\uff1f',
      '\u5728\u6559\u6703\u6216\u5c0f\u7d44\u4e2d\uff0c\u6211\u662f\u7a4d\u6975\u5efa\u9020\u4ed6\u4eba\uff0c\u9084\u662f\u6bd4\u8f03\u88ab\u52d5\u6216\u53ea\u7d22\u53d6\uff1f',
      '\u6211\u662f\u5426\u5bb3\u6015\u88ab\u62d2\u7d55\uff0c\u800c\u4e0d\u6562\u771f\u5be6\u654e\u958b\u81ea\u5df1\u7684\u8edf\u5f31\uff1f',
    ]
  },
  {
    key: 'trials',
    label: '\u7b2c\u56db\u985e\uff1a\u8a66\u7df4\u8207\u8a66\u63a2\uff08\u795e\u5e38\u7528\u7684\u300c\u6559\u5ba4\u300d\uff09',
    emoji: '\u{1F525}',
    color: '#f87171',
    lesson: '\u9806\u670d\u3001\u653e\u4e0b\u5076\u50cf\u3001\u5728\u60a3\u96e3\u4e2d\u559c\u6a02',
    questions: [
      '\u904e\u53bb\u534a\u5e74\u5230\u4e00\u5e74\uff0c\u6211\u6700\u5e38\u91cd\u8907\u9047\u5230\u7684\u8a66\u7df4\u6216\u6328\u6298\u662f\u4ec0\u9ebc\uff1f',
      '\u5728\u9019\u4e9b\u8a66\u7df4\u4e2d\uff0c\u6211\u6700\u5e38\u554f\u795e\u300c\u70ba\u4ec0\u9ebc\u300d\uff0c\u9084\u662f\u554f\u300c\u4f60\u8981\u6559\u5c0e\u6211\u4ec0\u9ebc\u300d\uff1f',
      '\u6211\u6709\u54ea\u4e9b\u53cd\u8986\u7684\u8a66\u63a2\u6216\u8001\u6211\u7fd2\u6163\uff08\u4f8b\u5982\u61f6\u60f0\u3001\u8caa\u5a6a\u3001\u8272\u6b32\u3001\u6182\u616e\uff09\uff1f',
      '\u5982\u679c\u795e\u73fe\u5728\u8981\u6211\u300c\u653e\u4e0b\u300d\u67d0\u6a23\u6771\u897f\uff08\u4eba\u3001\u4e8b\u3001\u7269\u3001\u7fd2\u6163\uff09\uff0c\u6211\u6700\u6368\u4e0d\u5f97\u7684\u662f\u4ec0\u9ebc\uff1f',
    ]
  },
  {
    key: 'calling',
    label: '\u7b2c\u4e94\u985e\uff1a\u4e8b\u5949\u3001\u547c\u53ec\u8207\u679c\u5b50',
    emoji: '\u{1F3AF}',
    color: '#60a5fa',
    lesson: '\u5fe0\u5fc3\u3001\u50b3\u798f\u97f3\u3001\u7d50\u679c\u5b50',
    questions: [
      '\u6211\u5982\u4f55\u4f7f\u7528\u795e\u7d66\u6211\u7684\u6642\u9593\u3001\u91d1\u9322\u3001\u6069\u8cdc\uff1f\u662f\u5426\u4ee5\u795e\u570b\u70ba\u512a\u5148\uff1f',
      '\u6211\u5728\u8077\u5834\u3001\u5bb6\u5ead\u6216\u6559\u6703\u4e2d\u7684\u898b\u8b49\uff0c\u662f\u5426\u8b93\u4eba\u770b\u898b\u57fa\u7763\u7684\u4e0d\u540c\uff1f',
      '\u6211\u662f\u5426\u6e05\u695a\u81ea\u5df1\u76ee\u524d\u7684\u547c\u53ec\uff1f\u6709\u6c92\u6709\u5728\u9003\u907f\u6216\u62d6\u5ef6\uff1f',
      '\u8eab\u908a\u7684\u4eba\uff08\u5305\u62ec\u672a\u4fe1\u8005\uff09\u56e0\u70ba\u6211\u7684\u751f\u547d\u800c\u66f4\u9760\u8fd1\u795e\u4e86\u55ce\uff1f',
    ]
  }
]

const FREQUENCY_OPTIONS = [
  { value: 9, label: '\u7d93\u5e38', color: '#4ade80', desc: '8\u201310\u5206' },
  { value: 5, label: '\u6709\u6642', color: '#fbbf24', desc: '4\u20137\u5206' },
  { value: 2, label: '\u5f88\u5c11', color: '#f87171', desc: '1\u20133\u5206' },
]

export default function PersonalityPage({ user, embedded = false }) {
  const [profile, setProfile] = useState(null)
  const [dimensions, setDimensions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('reflection')
  const [reflectionAnswers, setReflectionAnswers] = useState({})

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
          { key: 'reflection', label: '反思问题', emoji: '�' },
          { key: 'dimensions', label: '维度分析', emoji: '🎯' },
          { key: 'loops', label: '循环模式', emoji: '🔄' },
          { key: 'overview', label: '总览', emoji: '�' }
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
                        {(score * 100).toFixed(2)}%
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
                        {delta > 0 ? '↗' : '↘'} {Math.abs(delta * 100).toFixed(2)}%
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
          {/* 分组说明 */}
          <div style={{
            background: 'rgba(99,102,241,0.12)',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '24px',
            border: '1px solid rgba(99,102,241,0.3)',
            fontSize: '13px',
            color: 'rgba(255,255,255,0.7)',
            lineHeight: 1.6
          }}>
            <strong style={{ color: '#818cf8' }}>📌 维度解读说明：</strong> 所有数值为行为倾向（0.05–0.95），<strong>0.5 是基线</strong>。健康维度越高越好；循环倾向维度越低越健康。变化方向（↗↘）反映近期趋势，不是终身标签。
          </div>

          {/* 健康维度组 */}
          <div style={{ marginBottom: '32px' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              marginBottom: '16px'
            }}>
              <span style={{ fontSize: '18px' }}>🌱</span>
              <h3 style={{ margin: 0, fontSize: '16px', color: '#4ade80', fontWeight: 600 }}>健康成长维度</h3>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginLeft: '4px' }}>越高越好</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {['humility', 'emotional_stability', 'truth_alignment', 'relational_health', 'resilience', 'spiritual_clarity'].map(key => {
                const score = getDimensionScore(key)
                const color = dimensionColors[key]
                const delta = profile?.profile?.deltas?.[key] || 0
                const dimInfo = dimensions.find(d => d.key === key) || {}
                const name = dimensionNames[key]
                const pct = Math.round(score * 100)
                const isHigh = score >= 0.65
                const isLow = score <= 0.35
                const statusLabel = isHigh ? { text: '强', color: '#4ade80' } : isLow ? { text: '待培育', color: '#f87171' } : { text: '基线', color: '#fbbf24' }
                return (
                  <div key={key} style={{
                    background: 'rgba(0,0,0,0.25)',
                    borderRadius: '14px',
                    padding: '18px',
                    borderLeft: `4px solid ${color}`,
                    position: 'relative'
                  }}>
                    {/* 标题行 */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: color }} />
                        <span style={{ color: '#fff', fontWeight: 600, fontSize: '15px' }}>{name}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {delta !== 0 && (
                          <span style={{ fontSize: '12px', color: delta > 0 ? '#4ade80' : '#f87171', fontWeight: 600 }}>
                            {delta > 0 ? '↗' : '↘'}{Math.abs(delta * 100).toFixed(2)}%
                          </span>
                        )}
                        <span style={{
                          fontSize: '11px', padding: '2px 8px', borderRadius: '10px',
                          background: `${statusLabel.color}25`, color: statusLabel.color, fontWeight: 600
                        }}>{statusLabel.text}</span>
                        <span style={{ color: color, fontWeight: 700, fontSize: '18px' }}>{(score * 100).toFixed(2)}%</span>
                      </div>
                    </div>
                    {/* 进度条 */}
                    <div style={{ height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px', position: 'relative' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: `linear-gradient(90deg, ${color}70, ${color})`, borderRadius: '4px', transition: 'width 0.6s ease' }} />
                      {/* 基线标记 */}
                      <div style={{ position: 'absolute', left: '50%', top: 0, width: '2px', height: '100%', background: 'rgba(255,255,255,0.25)' }} />
                    </div>
                    {/* 描述 */}
                    {dimInfo.description && (
                      <p style={{ margin: '0 0 10px 0', color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: 1.5 }}>
                        {dimInfo.description}
                      </p>
                    )}
                    {/* 反思问题 */}
                    {dimInfo.reflective_question && (
                      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
                        💭 {dimInfo.reflective_question}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 循环倾向维度组 */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <span style={{ fontSize: '18px' }}>⚠️</span>
              <h3 style={{ margin: 0, fontSize: '16px', color: '#f87171', fontWeight: 600 }}>循环倾向维度</h3>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginLeft: '4px' }}>越低越健康</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {['fear_tendency', 'pride_tendency'].map(key => {
                const score = getDimensionScore(key)
                const color = dimensionColors[key]
                const delta = profile?.profile?.deltas?.[key] || 0
                const dimInfo = dimensions.find(d => d.key === key) || {}
                const name = dimensionNames[key]
                const pct = Math.round(score * 100)
                const isHigh = score >= 0.65
                const isLow = score <= 0.35
                const statusLabel = isHigh ? { text: '活跃', color: '#f87171' } : isLow ? { text: '受控', color: '#4ade80' } : { text: '基线', color: '#fbbf24' }
                return (
                  <div key={key} style={{
                    background: 'rgba(0,0,0,0.25)',
                    borderRadius: '14px',
                    padding: '18px',
                    borderLeft: `4px solid ${color}`
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: color }} />
                        <span style={{ color: '#fff', fontWeight: 600, fontSize: '15px' }}>{name}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {delta !== 0 && (
                          <span style={{ fontSize: '12px', color: delta > 0 ? '#f87171' : '#4ade80', fontWeight: 600 }}>
                            {delta > 0 ? '↗' : '↘'}{Math.abs(delta * 100).toFixed(2)}%
                          </span>
                        )}
                        <span style={{
                          fontSize: '11px', padding: '2px 8px', borderRadius: '10px',
                          background: `${statusLabel.color}25`, color: statusLabel.color, fontWeight: 600
                        }}>{statusLabel.text}</span>
                        <span style={{ color: color, fontWeight: 700, fontSize: '18px' }}>{(score * 100).toFixed(2)}%</span>
                      </div>
                    </div>
                    <div style={{ height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px', position: 'relative' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: `linear-gradient(90deg, ${color}70, ${color})`, borderRadius: '4px', transition: 'width 0.6s ease' }} />
                      <div style={{ position: 'absolute', left: '50%', top: 0, width: '2px', height: '100%', background: 'rgba(255,255,255,0.25)' }} />
                    </div>
                    {dimInfo.description && (
                      <p style={{ margin: '0 0 10px 0', color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: 1.5 }}>
                        {dimInfo.description}
                      </p>
                    )}
                    {dimInfo.reflective_question && (
                      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
                        💭 {dimInfo.reflective_question}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 综合解读 */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(59,130,246,0.12) 100%)',
            borderRadius: '14px',
            padding: '20px',
            border: '1px solid rgba(139,92,246,0.25)'
          }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#c4b5fd', fontSize: '15px' }}>🔭 综合轨迹解读</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
              {[
                { label: '最强维度', value: (() => { const entries = Object.entries(dimensionNames); const best = entries.filter(([k]) => !['fear_tendency','pride_tendency'].includes(k)).sort(([a],[b]) => getDimensionScore(b) - getDimensionScore(a))[0]; return best ? `${best[1]} (${(getDimensionScore(best[0])*100).toFixed(2)}%)` : '—' })(), color: '#4ade80' },
                { label: '最需培育', value: (() => { const entries = Object.entries(dimensionNames); const worst = entries.filter(([k]) => !['fear_tendency','pride_tendency'].includes(k)).sort(([a],[b]) => getDimensionScore(a) - getDimensionScore(b))[0]; return worst ? `${worst[1]} (${(getDimensionScore(worst[0])*100).toFixed(2)}%)` : '—' })(), color: '#f87171' },
                { label: '形成弧线', value: `${arc.emoji} ${arc.text}`, color: '#fbbf24' },
                { label: '轨迹方向', value: `${trajectory.emoji} ${trajectory.text}`, color: trajectory.color },
              ].map(item => (
                <div key={item.label} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '10px', padding: '12px' }}>
                  <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', marginBottom: '4px' }}>{item.label}</div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: item.color }}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>
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
          {/* 目的说明 */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(59,130,246,0.15) 100%)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '20px',
            border: '1px solid rgba(139,92,246,0.3)'
          }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '18px', color: '#fff' }}>
              💭 灵性塑造反思问卷
            </h3>
            <p style={{ margin: '0 0 16px 0', color: 'rgba(255,255,255,0.85)', fontSize: '14px', lineHeight: 1.8 }}>
              神在你生命中特别要塑造你成为耶稣基督那样慈爱怜悯、柔和谦卑、舍己爱人、俯就卑微的罪人，完全顺服天父的旨意这样的品格。要对付的根源问题，或要学习的功课（如信靠、饶恕、顺服、谦卑等）。透过一套有结构的自省题目，你可以系统地找出重复模式、试炼焦点与盲点，帮助你明白神目前的「功课」是什么。
            </p>

            {/* 操作指引 */}
            <div style={{
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '12px',
              padding: '16px 18px',
              marginBottom: '16px'
            }}>
              <div style={{ fontSize: '13px', color: '#a78bfa', fontWeight: 600, marginBottom: '10px' }}>🙏 开始前</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', lineHeight: 1.7 }}>
                用祷告开始（诗篇139:23-24），求圣灵光照。
              </div>
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#a78bfa', fontWeight: 600, marginBottom: '10px' }}>📝 作答原则</div>
              <div style={{ display: 'grid', gap: '6px' }}>
                {[
                  '诚实回答，不急着写「正确答案」。',
                  '写下具体例子。',
                  '完成后找出共同主题（例如多次提到「愤怒」或「不信」），那很可能就是当前生命功课。',
                  '每3–6个月重做一次，观察变化。'
                ].map((tip, i) => (
                  <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '13px', color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
                    <span style={{ color: '#a78bfa', flexShrink: 0 }}>·</span>
                    <span>{tip}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 分析与应用步骤 */}
            <div style={{
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '12px',
              padding: '16px 18px'
            }}>
              <div style={{ fontSize: '13px', color: '#60a5fa', fontWeight: 600, marginBottom: '10px' }}>🔍 分析与应用步骤（逻辑归纳）</div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {[
                  { n: '1', text: '找出模式：哪些题目你的答案最负面或最常出现同一主题？' },
                  { n: '2', text: '连结圣经：针对该主题查考相关经文（例如若是不饶恕，就看马太福音6:14-15）。' },
                  { n: '3', text: '写下当前生命功课：例如「神要我学习在工作中信靠祂的供应，而不是忧虑」。' },
                  { n: '4', text: '制定行动：用生命之轮或之前的地图，设计具体操练（例如每日为该功课用ACTS祷告）。' },
                  { n: '5', text: '找人确认：与成熟基督徒或小组分享，让他们帮助你看见可能忽略的盲点。' },
                ].map(step => (
                  <div key={step.n} style={{ display: 'flex', gap: '10px', fontSize: '13px', color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
                    <span style={{
                      flexShrink: 0,
                      width: '20px', height: '20px',
                      borderRadius: '50%',
                      background: 'rgba(96,165,250,0.25)',
                      color: '#60a5fa',
                      fontWeight: 700,
                      fontSize: '11px',
                      display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>{step.n}</span>
                    <span>{step.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 频率说明 */}
          <div style={{
            display: 'flex', gap: '16px', flexWrap: 'wrap',
            padding: '12px 16px',
            background: 'rgba(255,255,255,0.04)',
            borderRadius: '10px',
            marginBottom: '20px'
          }}>
            <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.45)', alignSelf: 'center' }}>标记频率：</span>
            {FREQUENCY_OPTIONS.map(opt => (
              <div key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: opt.color }} />
                <span style={{ fontSize: '13px', color: opt.color, fontWeight: 600 }}>{opt.label}</span>
                <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>{opt.desc}</span>
              </div>
            ))}
          </div>

          {REFLECTION_CATEGORIES.map((cat, catIdx) => {
            const catAnswered = cat.questions.filter((_, qi) => reflectionAnswers[`${cat.key}_${qi}`] !== undefined).length
            return (
              <div key={cat.key} style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '16px',
                padding: '24px',
                marginBottom: '20px',
                borderLeft: `4px solid ${cat.color}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '22px' }}>{cat.emoji}</span>
                    <span style={{ color: cat.color, fontWeight: 700, fontSize: '15px' }}>{cat.label}</span>
                  </div>
                  <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
                    {catAnswered}/{cat.questions.length}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.45)', marginBottom: '18px', paddingLeft: '32px' }}>
                  可能功课：{cat.lesson}
                </div>

                <div style={{ display: 'grid', gap: '14px' }}>
                  {cat.questions.map((q, qi) => {
                    const ansKey = `${cat.key}_${qi}`
                    const chosen = reflectionAnswers[ansKey]
                    return (
                      <div key={qi} style={{
                        background: 'rgba(255,255,255,0.04)',
                        borderRadius: '12px',
                        padding: '16px 18px',
                        border: chosen !== undefined
                          ? `1px solid ${FREQUENCY_OPTIONS.find(o => o.value === chosen)?.color}60`
                          : '1px solid rgba(255,255,255,0.08)'
                      }}>
                        <div style={{
                          fontSize: '14px',
                          color: 'rgba(255,255,255,0.9)',
                          lineHeight: 1.65,
                          marginBottom: '14px'
                        }}>
                          <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: '12px', marginRight: '8px' }}>
                            Q{catIdx * 4 + qi + 1}
                          </span>
                          {q}
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          {FREQUENCY_OPTIONS.map(opt => {
                            const isSelected = chosen === opt.value
                            return (
                              <button
                                key={opt.value}
                                onClick={() => setReflectionAnswers(prev => ({
                                  ...prev,
                                  [ansKey]: isSelected ? undefined : opt.value
                                }))}
                                style={{
                                  padding: '6px 16px',
                                  borderRadius: '20px',
                                  border: `1px solid ${opt.color}`,
                                  background: isSelected ? opt.color : 'transparent',
                                  color: isSelected ? '#000' : opt.color,
                                  fontSize: '13px',
                                  fontWeight: isSelected ? 700 : 400,
                                  cursor: 'pointer',
                                  transition: 'all 0.15s'
                                }}
                              >
                                {opt.label}
                              </button>
                            )
                          })}
                          {chosen !== undefined && (
                            <span style={{
                              fontSize: '12px',
                              color: 'rgba(255,255,255,0.35)',
                              alignSelf: 'center',
                              marginLeft: '4px'
                            }}>
                              {FREQUENCY_OPTIONS.find(o => o.value === chosen)?.desc}
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}

          {/* 答题进度汇总 */}
          {(() => {
            const total = REFLECTION_CATEGORIES.reduce((s, c) => s + c.questions.length, 0)
            const answered = Object.keys(reflectionAnswers).filter(k => reflectionAnswers[k] !== undefined).length
            const pct = Math.round((answered / total) * 100)
            if (answered === 0) return null
            const freqCounts = FREQUENCY_OPTIONS.reduce((acc, o) => {
              acc[o.label] = Object.values(reflectionAnswers).filter(v => v === o.value).length
              return acc
            }, {})
            return (
              <div style={{
                background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(59,130,246,0.12) 100%)',
                borderRadius: '14px',
                padding: '20px',
                border: '1px solid rgba(139,92,246,0.25)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ color: '#c4b5fd', fontWeight: 600, fontSize: '15px' }}>📋 答题汇总</span>
                  <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>{answered}/{total} 题</span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '16px' }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, #8b5cf6, #3b82f6)', borderRadius: '4px', transition: 'width 0.4s ease' }} />
                </div>
                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  {FREQUENCY_OPTIONS.map(opt => (
                    <div key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: opt.color }} />
                      <span style={{ color: opt.color, fontWeight: 600, fontSize: '14px' }}>{opt.label}</span>
                      <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px' }}>{freqCounts[opt.label]} 题</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}
          {/* 重要提醒 */}
          <div style={{
            background: 'rgba(251,191,36,0.08)',
            borderRadius: '14px',
            padding: '20px',
            marginTop: '20px',
            border: '1px solid rgba(251,191,36,0.25)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <span style={{ fontSize: '18px' }}>⚠️</span>
              <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: '15px' }}>重要提醒</span>
            </div>
            <div style={{ display: 'grid', gap: '10px' }}>
              {[
                { ref: '罗马书12:2', text: '这不是为了自我定罪，而是邀请神来更新。' },
                { ref: '希伯来书12:5-11', text: '生命功课常在重复的痛苦或试炼中显露，神是用爱来修剪。' },
                { ref: '加拉太书5:16', text: '靠恩典而行：认清功课后，立刻认罪、接受赦免，并倚靠圣灵改变。' },
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <span style={{ flexShrink: 0, fontSize: '13px', color: '#fbbf24', marginTop: '1px' }}>·</span>
                  <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.75)', lineHeight: 1.65 }}>
                    {item.text}
                    <span style={{ marginLeft: '6px', fontSize: '12px', color: 'rgba(251,191,36,0.6)' }}>（{item.ref}）</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
