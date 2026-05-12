import React, { useState } from 'react';
import './styles.css';

// Mock result for demonstration
const mockResult = {
  decision: {
    title: '是否应该接受新的工作机会',
    category: 'career',
    date: '2026-05-10',
  },
  source: {
    primary: 'fear',
    name: '恐惧反应',
    confidence: 'medium',
    score: 0.68,
  },
  explanation: '动机分析显示，恐惧因素在这个决策中占有较大比重（68%）。这很常见，人在不确定时自然会寻求安全。这个决定很大程度上受"避免损失"的心理驱动，而非"追求成长"的渴望。',
  humility: '分析显示了相对清晰的方向，但这只是基于有限信息的推断。真正的确据需要来自神的话语、祷告中的平安，以及属灵群体的印证。',
  alternatives: [
    '另一种可能：这不是危险信号，而是信心成长的邀请。恐惧可能只是需要跨越的边界。',
    '也值得考虑：如果完全不怕，您会如何选择？恐惧有时是价值重估的信号。',
    '从另一角度看：这个决定的时机是否合适？或许需要更多准备。',
  ],
  risk: {
    level: 'elevated',
    factors: [
      { name: '高压力状态', message: '当前压力水平较高，可能影响判断的客观性。' },
      { name: '高焦虑状态', message: '焦虑水平显著升高，决策可能过度聚焦于风险规避。' },
      { name: '恐惧驱动', message: '恐惧驱动的决定往往过度保守，可能错失成长机会。' },
    ],
  },
  motiveBreakdown: [
    { name: '恐惧', score: 0.68, color: '#c4a77d' },
    { name: '欲望', score: 0.55, color: '#8fa872' },
    { name: '爱', score: 0.25, color: '#5a9a8f' },
    { name: '骄傲', score: 0.20, color: '#9a9a9a' },
    { name: '责任', score: 0.15, color: '#9a9a9a' },
  ],
  principles: [
    { text: '不要恐惧，因为我与你同在；不要惊惶，因为我是你的神', source: '以赛亚书 41:10', relevance: 0.92 },
    { text: '凡事察验，善美的要持守', source: '帖撒罗尼迦前书 5:21', relevance: 0.85 },
    { text: '你们这小群，不要惧怕，因为你们的父乐意把国赐给你们', source: '路加福音 12:32', relevance: 0.78 },
  ],
  longTermFruit: {
    prediction: -0.25,
    explanation: '若维持现状，预计一年后回顾时可能会感到些许遗憾——不是因为选择本身，而是因为选择背后的动机可能限制了成长的可能性。',
  },
  nextSteps: {
    reflections: [
      '给自己24-48小时，期间不做任何相关决定，观察内心变化。',
      '写下您最害怕的具体后果。恐惧往往在具体化之后失去部分力量。',
      '与一位您最尊重的属灵导师分享这个分析，听听他们的观察。',
    ],
    questions: [
      '如果10年后的自己回看今天，会希望现在的我怎么选择？',
      '如果神的恩典够我用，我最害怕的后果还那么可怕吗？',
      '我能否在神面前完全坦诚这个决定的动机？',
      '如果完全不需要考虑他人怎么看，我会怎么选？',
    ],
    timeline: '建议给自己48小时的"静默期"，期间不主动思考这个决定，专注于与神的关系和休息。',
  },
};

const DiscernmentResult = ({ onNavigate, resultId }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [showFullDisclaimer, setShowFullDisclaimer] = useState(false);
  
  const result = mockResult; // In real app, fetch by resultId

  const sourceColors = {
    holy_spirit: { bg: '#e8f4f2', text: '#5a9a8f', border: '#5a9a8f' },
    fear: { bg: '#faf6f0', text: '#c4a77d', border: '#c4a77d' },
    pride: { bg: '#faf6f0', text: '#c4a77d', border: '#c4a77d' },
    trauma: { bg: '#f5f3f0', text: '#9a9a9a', border: '#9a9a9a' },
    worldly: { bg: '#f5f3f0', text: '#9a9a9a', border: '#9a9a9a' },
    mixed: { bg: '#f0f5eb', text: '#8fa872', border: '#8fa872' },
    uncertain: { bg: '#f5f3f0', text: '#9a9a9a', border: '#9a9a9a' },
  };

  const riskLabels = {
    low: { text: '低风险', color: '#5a9a8f' },
    moderate: { text: '中等风险', color: '#8fa872' },
    elevated: { text: '较高风险', color: '#c4a77d' },
    high: { text: '高风险', color: '#c4a77d' },
  };

  const getFruitEmoji = (score) => {
    if (score >= 0.5) return '🌳';
    if (score >= 0) return '🌱';
    if (score >= -0.5) return '🍂';
    return '⚠️';
  };

  const getFruitText = (score) => {
    if (score >= 0.5) return '预计结出好果子';
    if (score >= 0) return '结果中性，取决于后续行动';
    if (score >= -0.5) return '可能面临挑战';
    return '需要谨慎考虑';
  };

  const renderOverview = () => (
    <div className="sfds-fade-in">
      {/* Primary Source Card */}
      <div 
        className="sfds-card"
        style={{ 
          borderLeft: `4px solid ${sourceColors[result.source.primary]?.border || '#9a9a9a'}`,
          background: sourceColors[result.source.primary]?.bg || '#f5f3f0'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
          <div>
            <p style={{ fontSize: '13px', color: 'var(--sfds-text-muted)', marginBottom: '4px' }}>
              主要辨识来源
            </p>
            <h2 style={{ fontSize: '24px', fontWeight: 600, color: sourceColors[result.source.primary]?.text || '#9a9a9a' }}>
              {result.source.name}
            </h2>
          </div>
          <span className="sfds-badge sfds-badge-muted">
            置信度: {result.source.confidence}
          </span>
        </div>
        
        <div style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '13px', color: 'var(--sfds-text-muted)' }}>匹配度</span>
            <span style={{ fontSize: '13px', fontWeight: 500 }}>{Math.round(result.source.score * 100)}%</span>
          </div>
          <div className="sfds-progress-bar">
            <div 
              className="sfds-progress-fill" 
              style={{ width: `${result.source.score * 100}%` }}
            />
          </div>
        </div>

        <p className="sfds-body" style={{ marginBottom: '12px' }}>
          {result.explanation}
        </p>

        <div 
          style={{ 
            padding: '12px', 
            background: 'rgba(255,255,255,0.6)', 
            borderRadius: '8px',
            fontSize: '14px',
            color: 'var(--sfds-text-secondary)',
            fontStyle: 'italic'
          }}
        >
          🙏 {result.humility}
        </div>
      </div>

      {/* Risk Assessment */}
      <div className="sfds-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 className="sfds-section-title" style={{ margin: 0 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            风险评估
          </h3>
          <span 
            className="sfds-badge"
            style={{ 
              background: `${riskLabels[result.risk.level].color}20`,
              color: riskLabels[result.risk.level].color
            }}
          >
            {riskLabels[result.risk.level].text}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {result.risk.factors.map((factor, idx) => (
            <div 
              key={idx}
              style={{ 
                padding: '12px', 
                background: 'var(--sfds-bg-secondary)', 
                borderRadius: '8px',
                borderLeft: '3px solid #c4a77d'
              }}
            >
              <p style={{ fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>
                {factor.name}
              </p>
              <p style={{ fontSize: '13px', color: 'var(--sfds-text-secondary)', margin: 0 }}>
                {factor.message}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Alternative Interpretations */}
      <div className="sfds-card">
        <h3 className="sfds-section-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          其他可能的视角
        </h3>
        <p className="sfds-body" style={{ marginBottom: '16px' }}>
          真相往往是多面的。以下是其他同样合理的解释角度：
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {result.alternatives.map((alt, idx) => (
            <div 
              key={idx}
              style={{ 
                padding: '16px', 
                background: 'var(--sfds-accent-teal-light)', 
                borderRadius: '8px',
                fontSize: '14px',
                color: 'var(--sfds-text-secondary)',
                position: 'relative'
              }}
            >
              <span 
                style={{ 
                  position: 'absolute', 
                  top: '8px', 
                  right: '12px',
                  fontSize: '12px',
                  color: 'var(--sfds-accent-teal)',
                  fontWeight: 500
                }}
              >
                视角 {idx + 1}
              </span>
              <p style={{ margin: 0, paddingRight: '60px' }}>{alt}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <div 
        className="sfds-card"
        style={{ background: 'var(--sfds-bg-secondary)', borderStyle: 'dashed' }}
      >
        <div 
          style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            cursor: 'pointer'
          }}
          onClick={() => setShowFullDisclaimer(!showFullDisclaimer)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--sfds-text-muted)" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <span style={{ fontSize: '14px', color: 'var(--sfds-text-muted)' }}>
              关于这个分析的局限性
            </span>
          </div>
          <svg 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="var(--sfds-text-muted)" 
            strokeWidth="2"
            style={{ transform: showFullDisclaimer ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
        
        {showFullDisclaimer && (
          <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--sfds-border)' }}>
            <p style={{ fontSize: '13px', color: 'var(--sfds-text-muted)', lineHeight: '1.7', margin: 0 }}>
              • 本分析基于算法对您提供信息的解读，可能存在偏差。<br/><br/>
              • 这不是权威的属灵判断，不能替代祷告、圣经真理和属灵导师的建议。<br/><br/>
              • 最终的决定权在于您——这正是神赋予您的宝贵自由。<br/><br/>
              • 如果您感到迷茫，寻求专业的牧者或基督徒心理咨询师的帮助是智慧的选择。
            </p>
          </div>
        )}
      </div>
    </div>
  );

  const renderMotive = () => (
    <div className="sfds-fade-in">
      <div className="sfds-card">
        <h3 className="sfds-section-title">动机分解</h3>
        <p className="sfds-body" style={{ marginBottom: '24px' }}>
          每一个决定背后都有多重动机的交织。这不是"好"与"坏"的评判，而是对您内心世界的温柔映照。
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {result.motiveBreakdown.map((motive, idx) => (
            <div key={idx}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '14px', fontWeight: 500 }}>{motive.name}</span>
                <span style={{ fontSize: '14px', color: motive.color, fontWeight: 600 }}>
                  {Math.round(motive.score * 100)}%
                </span>
              </div>
              <div className="sfds-progress-bar" style={{ height: '12px' }}>
                <div 
                  className="sfds-progress-fill" 
                  style={{ 
                    width: `${motive.score * 100}%`,
                    background: motive.color,
                    borderRadius: '6px'
                  }}
                />
              </div>
              <p style={{ fontSize: '12px', color: 'var(--sfds-text-muted)', marginTop: '4px', marginBottom: 0 }}>
                {motive.name === '恐惧' && '对不确定性的自然防御反应'}
                {motive.name === '欲望' && '对更好生活的渴望'}
                {motive.name === '爱' && '对他人或神的关心'}
                {motive.name === '骄傲' && '对自我价值证明的需要'}
                {motive.name === '责任' && '对义务和承诺的重视'}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="sfds-card sfds-card-gentle">
        <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0, lineHeight: '1.7' }}>
          💭 <strong>反思邀请：</strong>
          <br /><br />
          动机的"纯度"不是目标。神使用各种动机——甚至包括不完全的动机——来完成祂的工作。
          <br /><br />
          重要的是觉察，而非完美。觉察让您有选择的空间，而完美主义只会带来疲惫。
        </p>
      </div>
    </div>
  );

  const renderPrinciples = () => (
    <div className="sfds-fade-in">
      <div className="sfds-card">
        <h3 className="sfds-section-title">相关的灵性原则</h3>
        <p className="sfds-body" style={{ marginBottom: '20px' }}>
          这些圣经原则与您的情况有较高的相关性。它们不是"答案"，而是陪伴您思考的光。
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {result.principles.map((principle, idx) => (
            <div key={idx} className="sfds-principle-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span className="sfds-badge sfds-badge-sage" style={{ fontSize: '11px' }}>
                  相关度 {Math.round(principle.relevance * 100)}%
                </span>
              </div>
              <p className="sfds-principle-text">"{principle.text}"</p>
              <p className="sfds-principle-source">— {principle.source}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="sfds-reflection-box">
        <p className="sfds-reflection-question">
          如何将这些原则应用到我的处境中？
        </p>
        <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0 }}>
          这是值得您用几天甚至几周时间去祷告和思考的问题。
          不要急于找到一个"方便"的答案——真理往往需要时间来沉淀。
        </p>
      </div>
    </div>
  );

  const renderFruit = () => (
    <div className="sfds-fade-in">
      <div className="sfds-card">
        <h3 className="sfds-section-title">长期果实预测</h3>
        <p className="sfds-body" style={{ marginBottom: '24px' }}>
          基于当前的动机模式，这是一个关于未来的温柔提醒——不是预言，而是基于模式的推测。
        </p>

        <div 
          style={{ 
            textAlign: 'center', 
            padding: '32px', 
            background: result.longTermFruit.prediction >= 0 ? 'var(--sfds-accent-sage-light)' : '#faf6f0',
            borderRadius: '12px',
            marginBottom: '24px'
          }}
        >
          <div style={{ fontSize: '64px', marginBottom: '16px' }}>
            {getFruitEmoji(result.longTermFruit.prediction)}
          </div>
          <h4 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px', color: 'var(--sfds-text-primary)' }}>
            {getFruitText(result.longTermFruit.prediction)}
          </h4>
          <p style={{ fontSize: '14px', color: 'var(--sfds-text-muted)', margin: 0 }}>
            预测分数: {result.longTermFruit.prediction > 0 ? '+' : ''}{result.longTermFruit.prediction}
          </p>
        </div>

        <div style={{ padding: '16px', background: 'var(--sfds-bg-secondary)', borderRadius: '8px' }}>
          <p style={{ fontSize: '15px', color: 'var(--sfds-text-primary)', lineHeight: '1.7', margin: 0 }}>
            {result.longTermFruit.explanation}
          </p>
        </div>
      </div>

      <div className="sfds-card sfds-card-gentle">
        <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0, lineHeight: '1.7' }}>
          🌱 <strong>关于预测的说明：</strong>
          <br /><br />
          这个预测基于统计模式，但神总是可以在任何时候介入，带来转机。
          <br /><br />
          负面的预测不是定罪，而是温柔的提醒；正面的预测也不是保证，而是鼓励。
          <br /><br />
          最重要的是：无论预测如何，祂的恩典够您用。
        </p>
      </div>
    </div>
  );

  const renderNextSteps = () => (
    <div className="sfds-fade-in">
      <div className="sfds-card">
        <h3 className="sfds-section-title">建议的下一步</h3>
        <p className="sfds-body" style={{ marginBottom: '24px' }}>
          这些不是"指令"，而是一些可能帮助您获得更清晰视野的建议。选择那些对您此刻最有意义的。
        </p>

        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ fontSize: '16px', fontWeight: 500, marginBottom: '16px' }}>反思练习</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {result.nextSteps.reflections.map((step, idx) => (
              <div 
                key={idx}
                style={{ 
                  padding: '16px', 
                  background: 'var(--sfds-bg-secondary)', 
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px'
                }}
              >
                <span style={{ 
                  width: '24px', 
                  height: '24px', 
                  background: 'var(--sfds-accent-teal)', 
                  color: 'white',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 600,
                  flexShrink: 0
                }}>
                  {idx + 1}
                </span>
                <p style={{ margin: 0, fontSize: '14px', color: 'var(--sfds-text-primary)', lineHeight: '1.6' }}>
                  {step}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ fontSize: '16px', fontWeight: 500, marginBottom: '16px' }}>值得思考的问题</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {result.nextSteps.questions.map((question, idx) => (
              <div 
                key={idx}
                style={{ 
                  padding: '16px', 
                  background: 'var(--sfds-accent-teal-light)', 
                  borderRadius: '8px',
                  borderLeft: '4px solid var(--sfds-accent-teal)'
                }}
              >
                <p style={{ margin: 0, fontSize: '15px', color: 'var(--sfds-text-primary)', fontStyle: 'italic' }}>
                  "{question}"
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="sfds-reflection-box">
          <h4 style={{ fontSize: '16px', fontWeight: 500, marginBottom: '12px' }}>时间建议</h4>
          <p style={{ fontSize: '15px', color: 'var(--sfds-text-secondary)', margin: 0, lineHeight: '1.7' }}>
            {result.nextSteps.timeline}
          </p>
        </div>
      </div>

      <button
        className="sfds-btn sfds-btn-primary"
        style={{ width: '100%', marginBottom: '16px' }}
        onClick={() => onNavigate('journal')}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
        记录我的反思
      </button>

      <button
        className="sfds-btn sfds-btn-secondary"
        style={{ width: '100%' }}
        onClick={() => onNavigate('dashboard')}
      >
        返回首页
      </button>
    </div>
  );

  return (
    <div className="sfds-page sfds-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <button 
          className="sfds-btn sfds-btn-secondary"
          style={{ padding: '8px', marginBottom: '16px' }}
          onClick={() => onNavigate('dashboard')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回
        </button>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span className="sfds-badge sfds-badge-muted" style={{ marginBottom: '8px', display: 'inline-block' }}>
              {categoryNames[result.decision.category] || result.decision.category}
            </span>
            <h1 className="sfds-title" style={{ marginBottom: '4px' }}>
              {result.decision.title}
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--sfds-text-muted)', margin: 0 }}>
              分析日期: {result.decision.date}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ 
        display: 'flex', 
        gap: '4px', 
        marginBottom: '24px',
        background: 'var(--sfds-bg-secondary)',
        padding: '4px',
        borderRadius: '10px'
      }}>
        {[
          { id: 'overview', label: '概览' },
          { id: 'motive', label: '动机' },
          { id: 'principles', label: '原则' },
          { id: 'fruit', label: '果实' },
          { id: 'next', label: '下一步' },
        ].map(tab => (
          <button
            key={tab.id}
            className={`sfds-btn ${activeTab === tab.id ? 'sfds-btn-primary' : 'sfds-btn-secondary'}`}
            style={{ 
              flex: 1, 
              padding: '10px 8px',
              fontSize: '14px',
              background: activeTab === tab.id ? 'var(--sfds-accent-teal)' : 'transparent',
              border: 'none'
            }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && renderOverview()}
      {activeTab === 'motive' && renderMotive()}
      {activeTab === 'principles' && renderPrinciples()}
      {activeTab === 'fruit' && renderFruit()}
      {activeTab === 'next' && renderNextSteps()}
    </div>
  );
};

const categoryNames = {
  career: '职业',
  relationship: '关系',
  calling: '呼召',
  temptation: '试探',
  financial: '财务',
  health: '健康',
  ministry: '事奉',
  other: '其他',
};

export default DiscernmentResult;
