import { useEffect, useState } from 'react'
import { API_BASE } from './api'
import { getToken } from './auth'

const sfdsUrl = (path) => `${API_BASE}/sfds${path}`

// 决策类别选项
const decisionCategories = [
  { value: 'career', label: '职业/工作', emoji: '💼' },
  { value: 'relationship', label: '人际关系', emoji: '💕' },
  { value: 'temptation', label: '试探/诱惑', emoji: '⚠️' },
  { value: 'calling', label: '呼召/使命', emoji: '🎯' },
  { value: 'financial', label: '财务/金钱', emoji: '💰' },
  { value: 'health', label: '健康/身体', emoji: '🏥' },
  { value: 'ministry', label: '事工/服事', emoji: '⛪' },
  { value: 'other', label: '其他', emoji: '📝' },
]

// 情绪类型选项
const emotionTypes = [
  { value: 'fear', label: '恐惧/害怕', emoji: '😨' },
  { value: 'anxiety', label: '焦虑/担心', emoji: '😰' },
  { value: 'anger', label: '愤怒/生气', emoji: '😠' },
  { value: 'joy', label: '喜乐/开心', emoji: '😊' },
  { value: 'peace', label: '平安/宁静', emoji: '😌' },
  { value: 'love', label: '爱/温暖', emoji: '🥰' },
  { value: 'sadness', label: '悲伤/难过', emoji: '😢' },
  { value: 'confusion', label: '困惑/迷茫', emoji: '😕' },
  { value: 'hope', label: '盼望/期待', emoji: '🌟' },
  { value: 'doubt', label: '怀疑/不确定', emoji: '❓' },
  { value: 'desire', label: '渴望/向往', emoji: '✨' },
  { value: 'lust', label: '欲望/贪恋', emoji: '🔥' },
]

// 灵性原则
const spiritualPrinciples = [
  { id: '1', text: '凡事察验，善美的要持守', ref: '帖前5:21' },
  { id: '2', text: '你要保守你心，胜过保守一切', ref: '箴4:23' },
  { id: '3', text: '不要恐惧，因为我与你同在', ref: '赛41:10' },
  { id: '4', text: '看别人比自己强', ref: '腓2:3' },
  { id: '5', text: '凭果子认出他们来', ref: '太7:20' },
  { id: '6', text: '爱比成功更高', ref: '林前13:1-3' },
  { id: '7', text: '真理比舒适更重要', ref: '约8:32' },
  { id: '8', text: '谦卑在智慧以先', ref: '箴11:2' },
  { id: '9', text: '安息是属灵操练', ref: '可6:31' },
  { id: '10', text: '顺服神，不顺从人', ref: '徒5:29' },
  { id: '11', text: '愿意受苦而不愿犯罪', ref: '来11:25' },
  { id: '12', text: '患难生忍耐，忍耐生老练', ref: '罗5:3-4' },
]

export default function DecisionSupportPage({ user, onBack, embedded = false }) {
  const [activeTab, setActiveTab] = useState('new') // new, history, principles
  const [loading, setLoading] = useState(false)
  const [decisions, setDecisions] = useState([])
  const [selectedDecision, setSelectedDecision] = useState(null)

  // 新决策表单状态
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    urgency: 3,
    importance: 3,
    stressLevel: 5,
    anxietyLevel: 5,
    fatigueLevel: 5,
    spiritualDryness: 5,
    emotionalStability: 5,
    emotions: [],
  })

  // 结果展示
  const [analysisResult, setAnalysisResult] = useState(null)

  // 加载决策历史
  useEffect(() => {
    if (activeTab === 'history') {
      loadDecisions()
    }
  }, [activeTab])

  const loadDecisions = async () => {
    try {
      const token = getToken()
      const res = await fetch(sfdsUrl('/decisions'), {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('加载失败')
      const data = await res.json()
      setDecisions(data)
    } catch (err) {
      console.error('加载决策历史失败:', err)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const token = getToken()
      
      // 构建提交数据
      const payload = {
        title: formData.title,
        description: formData.description,
        category: formData.category,
        urgency: formData.urgency,
        importance: formData.importance,
        state_snapshot: {
          stress_level: formData.stressLevel,
          anxiety_level: formData.anxietyLevel,
          fatigue_level: formData.fatigueLevel,
          spiritual_dryness: formData.spiritualDryness,
          emotional_stability: formData.emotionalStability,
        },
        emotion_logs: formData.emotions.map((e, i) => ({
          emotion_type: e.type,
          intensity: e.intensity,
          trigger: e.trigger,
          timestamp: new Date(Date.now() - i * 60000).toISOString(),
        })),
        context_factors: {
          user_note: formData.description,
        },
      }

      const res = await fetch(sfdsUrl('/decisions'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '提交失败')
      }

      const result = await res.json()
      
      // 等待分析完成（轮询）
      await pollForAnalysis(result.id)
      
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  const pollForAnalysis = async (decisionId) => {
    const token = getToken()
    let attempts = 0
    const maxAttempts = 30 // 最多等待30秒

    while (attempts < maxAttempts) {
      const res = await fetch(sfdsUrl(`/decisions/${decisionId}`), {
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (res.ok) {
        const data = await res.json()
        
        if (data.status === 'guided' && data.guidance) {
          setAnalysisResult(data)
          return
        }
        
        if (data.status === 'analyzing') {
          await new Promise(r => setTimeout(r, 1000))
          attempts++
          continue
        }
      }
      
      break
    }
  }

  const addEmotion = () => {
    setFormData(prev => ({
      ...prev,
      emotions: [...prev.emotions, { type: '', intensity: 5, trigger: '' }],
    }))
  }

  const updateEmotion = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      emotions: prev.emotions.map((e, i) => 
        i === index ? { ...e, [field]: value } : e
      ),
    }))
  }

  const removeEmotion = (index) => {
    setFormData(prev => ({
      ...prev,
      emotions: prev.emotions.filter((_, i) => i !== index),
    }))
  }

  // 渲染导航标签
  const renderTabs = () => (
    <div style={{
      display: 'flex',
      gap: '8px',
      padding: '12px 16px',
      borderBottom: '1px solid rgba(255,255,255,0.1)',
      background: 'rgba(28,28,30,0.8)',
      position: 'sticky',
      top: 0,
      zIndex: 10,
    }}>
      {[
        { key: 'new', label: '新决策', emoji: '🆕' },
        { key: 'history', label: '历史', emoji: '📜' },
        { key: 'principles', label: '原则', emoji: '📖' },
      ].map(tab => (
        <button
          key={tab.key}
          onClick={() => {
            setActiveTab(tab.key)
            setAnalysisResult(null)
          }}
          style={{
            flex: 1,
            padding: '10px 12px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === tab.key ? '#007aff' : 'rgba(120,120,128,0.2)',
            color: activeTab === tab.key ? '#fff' : 'rgba(255,255,255,0.6)',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <span>{tab.emoji}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  )

  // 渲染新决策表单
  const renderNewDecisionForm = () => (
    <>
    <form id="decision-form" onSubmit={handleSubmit} style={{ padding: '16px' }}>
      {/* 决策标题 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>决策标题 *</label>
        <input
          type="text"
          value={formData.title}
          onChange={e => setFormData(prev => ({ ...prev, title: e.target.value }))}
          placeholder="例如：是否应该接受这份工作邀请？"
          style={inputStyle}
          required
        />
      </div>

      {/* 决策类别 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>决策类别 *</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {decisionCategories.map(cat => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, category: cat.value }))}
              style={{
                padding: '8px 12px',
                borderRadius: '20px',
                border: formData.category === cat.value ? '2px solid #007aff' : '1px solid rgba(255,255,255,0.2)',
                background: formData.category === cat.value ? 'rgba(0,122,255,0.2)' : 'rgba(255,255,255,0.05)',
                color: '#fff',
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 紧急与重要程度 */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>紧急程度: {formData.urgency}/5</label>
          <input
            type="range"
            min="1"
            max="5"
            value={formData.urgency}
            onChange={e => setFormData(prev => ({ ...prev, urgency: parseInt(e.target.value) }))}
            style={{ width: '100%' }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>重要程度: {formData.importance}/5</label>
          <input
            type="range"
            min="1"
            max="5"
            value={formData.importance}
            onChange={e => setFormData(prev => ({ ...prev, importance: parseInt(e.target.value) }))}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* 当前状态快照 */}
      <div style={{ 
        background: 'rgba(0,122,255,0.1)', 
        borderRadius: '12px', 
        padding: '16px',
        marginBottom: '16px',
      }}>
        <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: '#007aff' }}>
          🔍 当前状态快照
        </div>
        
        {[
          { key: 'stressLevel', label: '压力水平', icon: '😰' },
          { key: 'anxietyLevel', label: '焦虑水平', icon: '😨' },
          { key: 'fatigueLevel', label: '疲劳程度', icon: '😴' },
          { key: 'spiritualDryness', label: '灵性干涸', icon: '🏜️' },
          { key: 'emotionalStability', label: '情绪稳定', icon: '😌' },
        ].map(item => (
          <div key={item.key} style={{ marginBottom: '10px' }}>
            <label style={{ ...labelStyle, fontSize: '13px' }}>
              {item.icon} {item.label}: {formData[item.key]}/10
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={formData[item.key]}
              onChange={e => setFormData(prev => ({ ...prev, [item.key]: parseInt(e.target.value) }))}
              style={{ width: '100%' }}
            />
          </div>
        ))}
      </div>

      {/* 情绪记录 */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label style={labelStyle}>当前情绪</label>
          <button
            type="button"
            onClick={addEmotion}
            style={{
              padding: '4px 12px',
              borderRadius: '16px',
              border: 'none',
              background: '#34c759',
              color: '#fff',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            + 添加情绪
          </button>
        </div>
        
        {formData.emotions.map((emotion, index) => (
          <div 
            key={index}
            style={{
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '10px',
              padding: '12px',
              marginBottom: '8px',
            }}
          >
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <select
                value={emotion.type}
                onChange={e => updateEmotion(index, 'type', e.target.value)}
                style={{ ...inputStyle, flex: 1 }}
              >
                <option value="">选择情绪类型</option>
                {emotionTypes.map(e => (
                  <option key={e.value} value={e.value}>
                    {e.emoji} {e.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removeEmotion(index)}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#ff3b30',
                  color: '#fff',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                删除
              </button>
            </div>
            
            <div style={{ marginBottom: '8px' }}>
              <label style={{ ...labelStyle, fontSize: '12px' }}>
                强度: {emotion.intensity}/10
              </label>
              <input
                type="range"
                min="0"
                max="10"
                value={emotion.intensity}
                onChange={e => updateEmotion(index, 'intensity', parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
            
            <input
              type="text"
              value={emotion.trigger}
              onChange={e => updateEmotion(index, 'trigger', e.target.value)}
              placeholder="触发原因（可选）"
              style={{ ...inputStyle, fontSize: '13px' }}
            />
          </div>
        ))}
      </div>

      {/* 决策描述 */}
      <div style={{ marginBottom: '20px' }}>
        <label style={labelStyle}>详细描述 *</label>
        <textarea
          value={formData.description}
          onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
          placeholder="描述你的处境、选择、顾虑..."
          style={{ ...inputStyle, minHeight: '120px', resize: 'vertical' }}
          required
        />
      </div>

      {/* 底部占位，为固定按钮留出空间 */}
      <div style={{ height: '80px' }} />
    </form>

    {/* 固定在底部的提交按钮 */}
    <button
      type="submit"
      form="decision-form"
      disabled={loading || !formData.title || !formData.category}
      style={{
        position: 'sticky',
        bottom: 0,
        left: 0,
        right: 0,
        width: '100%',
        padding: '14px',
        borderRadius: '12px',
        border: 'none',
        background: loading ? 'rgba(120,120,128,0.3)' : '#007aff',
        color: '#fff',
        fontSize: '16px',
        fontWeight: 600,
        cursor: loading ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        marginTop: 'auto',
      }}
    >
      {loading ? (
        <>
          <span className="spinner" style={{ 
            width: '18px', 
            height: '18px', 
            border: '2px solid rgba(255,255,255,0.3)',
            borderTopColor: '#fff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
          <span>正在分析...</span>
        </>
      ) : (
        <>
          <span>🔍</span>
          <span>开始辨识分析</span>
        </>
      )}
    </button>
    </>
  )

  // 渲染分析结果
  const renderAnalysisResult = () => {
    if (!analysisResult) return null
    
    const { motive_analysis, discernment_result, guidance } = analysisResult
    
    return (
      <div style={{ padding: '16px' }}>
        <div style={{
          background: 'linear-gradient(135deg, #007aff, #5e5ce6)',
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '20px',
          color: '#fff',
        }}>
          <div style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>
            ✨ 辨识分析完成
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9 }}>
            基于当前状态，系统已完成动机分析与来源辨识
          </div>
        </div>

        {/* 动机分析 */}
        {motive_analysis && (
          <div style={resultCardStyle}>
            <div style={resultTitleStyle}>🧠 动机分析</div>
            <div style={{ marginBottom: '12px' }}>
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>😨 恐惧驱动</span>
                  <span>{Math.round(motive_analysis.fear_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.fear_driven_score * 100}%`, background: '#ff3b30' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>😤 骄傲驱动</span>
                  <span>{Math.round(motive_analysis.pride_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.pride_driven_score * 100}%`, background: '#ff9500' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>❤️ 爱驱动</span>
                  <span>{Math.round(motive_analysis.love_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.love_driven_score * 100}%`, background: '#34c759' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>🔥 欲望驱动</span>
                  <span>{Math.round(motive_analysis.desire_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.desire_driven_score * 100}%`, background: '#af52de' }} />
                </div>
              </div>
            </div>
            
            <div style={{ 
              background: 'rgba(0,122,255,0.15)', 
              borderRadius: '8px', 
              padding: '12px',
              fontSize: '13px',
            }}>
              <strong>主导动机：</strong>
              <span style={{ color: '#007aff', fontWeight: 600 }}>
                {motive_analysis.dominant_motive === 'fear' && '😨 恐惧'}
                {motive_analysis.dominant_motive === 'pride' && '😤 骄傲'}
                {motive_analysis.dominant_motive === 'love' && '❤️ 爱'}
                {motive_analysis.dominant_motive === 'desire' && '🔥 欲望'}
                {motive_analysis.dominant_motive === 'duty' && '📋 责任'}
                {motive_analysis.dominant_motive === 'ambition' && '🎯 雄心'}
              </span>
            </div>
          </div>
        )}

        {/* 来源辨识 */}
        {discernment_result && (
          <div style={resultCardStyle}>
            <div style={resultTitleStyle}>🔮 来源辨识</div>
            
            <div style={{ 
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '10px',
              padding: '12px',
              marginBottom: '12px',
            }}>
              <div style={{ 
                display: 'inline-block',
                padding: '4px 12px',
                borderRadius: '16px',
                fontSize: '12px',
                fontWeight: 600,
                marginBottom: '8px',
                ...getSourceStyle(discernment_result.primary_source),
              }}>
                {discernment_result.primary_source === 'holy_spirit' && '✨ 圣灵感动'}
                {discernment_result.primary_source === 'conscience' && '🤔 良心/理性'}
                {discernment_result.primary_source === 'fear_response' && '😨 恐惧反应'}
                {discernment_result.primary_source === 'pride_response' && '😤 骄傲反应'}
                {discernment_result.primary_source === 'trauma_response' && '💔 创伤反应'}
                {discernment_result.primary_source === 'worldly_value' && '🌍 世俗价值观'}
                {discernment_result.primary_source === 'flesh_desire' && '🔥 肉体欲望'}
                {discernment_result.primary_source === 'uncertain' && '❓ 不确定'}
              </div>
              
              <div style={{ fontSize: '13px', lineHeight: 1.5, marginBottom: '8px' }}>
                {discernment_result.explanation}
              </div>
              
              <div style={{ display: 'flex', gap: '16px', fontSize: '12px' }}>
                <span>置信度: {Math.round(discernment_result.confidence * 100)}%</span>
                <span>长期果实: {discernment_result.long_term_fruit_score > 0 ? '+' : ''}{discernment_result.long_term_fruit_score}</span>
              </div>
            </div>
          </div>
        )}

        {/* 指导建议 */}
        {guidance && (
          <div style={resultCardStyle}>
            <div style={resultTitleStyle}>📖 指导建议</div>
            
            <div style={{ 
              background: 'rgba(52,199,89,0.15)',
              borderRadius: '10px',
              padding: '12px',
              marginBottom: '16px',
              fontSize: '13px',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}>
              {guidance.structured_advice}
            </div>
            
            {/* 风险 */}
            {guidance.risks && guidance.risks.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#ff3b30' }}>
                  ⚠️ 潜在风险
                </div>
                {guidance.risks.map((risk, i) => (
                  <div key={i} style={{
                    padding: '8px 12px',
                    background: 'rgba(255,59,48,0.1)',
                    borderRadius: '8px',
                    marginBottom: '6px',
                    fontSize: '13px',
                  }}>
                    • {risk}
                  </div>
                ))}
              </div>
            )}
            
            {/* 替代解释 */}
            {guidance.alternative_interpretations && guidance.alternative_interpretations.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#ff9500' }}>
                  💭 替代视角
                </div>
                {guidance.alternative_interpretations.map((alt, i) => (
                  <div key={i} style={{
                    padding: '8px 12px',
                    background: 'rgba(255,149,0,0.1)',
                    borderRadius: '8px',
                    marginBottom: '6px',
                    fontSize: '13px',
                  }}>
                    • {alt}
                  </div>
                ))}
              </div>
            )}
            
            {/* 建议行动 */}
            {guidance.recommended_actions && guidance.recommended_actions.length > 0 && (
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#007aff' }}>
                  ✅ 建议行动
                </div>
                {guidance.recommended_actions.map((action, i) => (
                  <div key={i} style={{
                    padding: '10px 12px',
                    background: 'rgba(0,122,255,0.1)',
                    borderRadius: '8px',
                    marginBottom: '8px',
                    fontSize: '13px',
                    borderLeft: '3px solid #007aff',
                  }}>
                    {i + 1}. {action}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 灵性原则引用 */}
        <div style={resultCardStyle}>
          <div style={resultTitleStyle}>📜 相关灵性原则</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {spiritualPrinciples.slice(0, 5).map(p => (
              <div key={p.id} style={{
                padding: '8px 12px',
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '8px',
                fontSize: '12px',
                flex: '1 1 calc(50% - 8px)',
                minWidth: '140px',
              }}>
                <div>{p.text}</div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
                  {p.ref}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 免责声明 */}
        <div style={{
          background: 'rgba(255,149,0,0.1)',
          borderRadius: '10px',
          padding: '12px',
          marginTop: '16px',
          fontSize: '12px',
          color: 'rgba(255,255,255,0.7)',
          textAlign: 'center',
        }}>
          ⚠️ 本分析仅供参考，不构成权威属灵指导。请寻求属灵导师、牧师或专业辅导的意见。
        </div>

        {/* 返回按钮 */}
        <button
          onClick={() => {
            setAnalysisResult(null)
            setFormData({
              title: '',
              description: '',
              category: '',
              urgency: 3,
              importance: 3,
              stressLevel: 5,
              anxietyLevel: 5,
              fatigueLevel: 5,
              spiritualDryness: 5,
              emotionalStability: 5,
              emotions: [],
            })
          }}
          style={{
            width: '100%',
            padding: '12px',
            marginTop: '16px',
            borderRadius: '10px',
            border: '1px solid rgba(255,255,255,0.2)',
            background: 'transparent',
            color: '#fff',
            fontSize: '14px',
            cursor: 'pointer',
          }}
        >
          开始新的辨识
        </button>
      </div>
    )
  }

  // 渲染历史记录
  const renderHistory = () => (
    <div style={{ padding: '16px' }}>
      {decisions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'rgba(255,255,255,0.5)' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📭</div>
          <div>暂无决策记录</div>
        </div>
      ) : (
        decisions.map((d, i) => (
          <div 
            key={d.id || i}
            onClick={() => setSelectedDecision(d)}
            style={{
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '12px',
              cursor: 'pointer',
              borderLeft: `4px solid ${getCategoryColor(d.category)}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div style={{ fontWeight: 600, fontSize: '15px', flex: 1, marginRight: '8px' }}>
                {d.title}
              </div>
              <span style={{
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '11px',
                background: d.status === 'guided' ? 'rgba(52,199,89,0.2)' : 'rgba(255,149,0,0.2)',
                color: d.status === 'guided' ? '#34c759' : '#ff9500',
              }}>
                {d.status === 'guided' ? '已完成' : '分析中'}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>
              {formatDate(d.created_at)}
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                {decisionCategories.find(c => c.value === d.category)?.emoji} {decisionCategories.find(c => c.value === d.category)?.label}
              </span>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
                紧急{d.urgency} • 重要{d.importance}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  )

  // 渲染灵性原则
  const renderPrinciples = () => (
    <div style={{ padding: '16px' }}>
      <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.7)', marginBottom: '16px', textAlign: 'center' }}>
        在决策中默想这些原则，帮助辨识真伪
      </div>
      
      {spiritualPrinciples.map(p => (
        <div key={p.id} style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '12px',
        }}>
          <div style={{ fontSize: '15px', fontWeight: 500, marginBottom: '8px', lineHeight: 1.5 }}>
            "{p.text}"
          </div>
          <div style={{ fontSize: '12px', color: '#007aff' }}>
            — {p.ref}
          </div>
        </div>
      ))}
    </div>
  )

  // 工具函数
  const getSourceStyle = (source) => {
    const styles = {
      holy_spirit: { background: 'rgba(52,199,89,0.2)', color: '#34c759' },
      conscience: { background: 'rgba(0,122,255,0.2)', color: '#007aff' },
      fear_response: { background: 'rgba(255,59,48,0.2)', color: '#ff3b30' },
      pride_response: { background: 'rgba(255,149,0,0.2)', color: '#ff9500' },
      trauma_response: { background: 'rgba(175,82,222,0.2)', color: '#af52de' },
      worldly_value: { background: 'rgba(120,120,128,0.2)', color: '#8e8e93' },
      flesh_desire: { background: 'rgba(255,59,48,0.2)', color: '#ff3b30' },
      uncertain: { background: 'rgba(255,204,0,0.2)', color: '#ffcc00' },
    }
    return styles[source] || styles.uncertain
  }

  const getCategoryColor = (category) => {
    const colors = {
      career: '#007aff',
      relationship: '#ff2d55',
      temptation: '#ff3b30',
      calling: '#af52de',
      financial: '#34c759',
      health: '#5ac8fa',
      ministry: '#ff9500',
      other: '#8e8e93',
    }
    return colors[category] || '#8e8e93'
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  // 样式常量
  const labelStyle = {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '8px',
    color: 'rgba(255,255,255,0.8)',
  }

  const inputStyle = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: '10px',
    border: '1px solid rgba(255,255,255,0.15)',
    background: 'rgba(120,120,128,0.18)',
    color: '#fff',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
  }

  const resultCardStyle = {
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '14px',
    padding: '16px',
    marginBottom: '16px',
  }

  const resultTitleStyle = {
    fontSize: '16px',
    fontWeight: 600,
    marginBottom: '12px',
    color: '#fff',
  }

  const progressBarContainer = {
    marginBottom: '12px',
  }

  const progressBarBg = {
    height: '6px',
    background: 'rgba(255,255,255,0.1)',
    borderRadius: '3px',
    overflow: 'hidden',
  }

  const progressBarFill = {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
  }

  const content = (
    <>
      {/* 标签导航 */}
      {renderTabs()}

      {/* 内容区域 */}
      <div style={{ paddingBottom: embedded ? '0' : '80px' }}>
        {analysisResult ? renderAnalysisResult() : (
          <>
            {activeTab === 'new' && renderNewDecisionForm()}
            {activeTab === 'history' && renderHistory()}
            {activeTab === 'principles' && renderPrinciples()}
          </>
        )}
      </div>
    </>
  )

  if (embedded) {
    return (
      <div style={{ flex: 1, overflow: 'auto' }}>
        {content}
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: '#000',
      color: '#fff',
      overflow: 'auto',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
      {/* 顶部栏 */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(28,28,30,0.9)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={onBack}
            style={{
              background: 'rgba(120,120,128,0.2)',
              border: 'none',
              borderRadius: '50%',
              width: '36px',
              height: '36px',
              color: '#fff',
              fontSize: '20px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ‹
          </button>
          <div>
            <div style={{ fontSize: '17px', fontWeight: 600 }}>决策支撑</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>灵性辨识与决策</div>
          </div>
        </div>

        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #007aff, #5e5ce6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
        }}>
          ⚖️
        </div>
      </div>

      {content}

      {/* 底部提示 */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '12px 16px',
        background: 'rgba(28,28,30,0.95)',
        borderTop: '1px solid rgba(255,255,255,0.1)',
        textAlign: 'center',
        fontSize: '11px',
        color: 'rgba(255,255,255,0.5)',
      }}>
        本系统旨在辅助属灵辨识，不取代个人自由意志或权威属灵指导
      </div>

      {/* 添加CSS动画 */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
