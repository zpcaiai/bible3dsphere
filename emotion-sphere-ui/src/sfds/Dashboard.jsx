import React, { useState, useEffect } from 'react';
import './styles.css';

// Mock data for demonstration
const mockRecentDecisions = [
  {
    id: 1,
    title: '是否应该接受新的工作机会',
    category: 'career',
    date: '2026-05-08',
    status: 'analyzing',
    primarySource: 'fear',
  },
  {
    id: 2,
    title: '饶恕曾经伤害我的朋友',
    category: 'relationship',
    date: '2026-05-05',
    status: 'guided',
    primarySource: 'love',
  },
  {
    id: 3,
    title: '是否参加这次短宣',
    category: 'calling',
    date: '2026-04-28',
    status: 'decided',
    primarySource: 'holy_spirit',
  },
];

const mockEmotionalState = {
  stress: 5,
  anxiety: 4,
  peace: 6,
  joy: 5,
  fatigue: 6,
  spiritualVitality: 5,
};

const Dashboard = ({ onNavigate }) => {
  const [currentState, setCurrentState] = useState(mockEmotionalState);
  const [recentDecisions, setRecentDecisions] = useState(mockRecentDecisions);
  const [isLoading, setIsLoading] = useState(false);

  const categoryNames = {
    career: '职业',
    relationship: '关系',
    calling: '呼召',
    temptation: '试探',
    financial: '财务',
    health: '健康',
    ministry: '事工',
    other: '其他',
  };

  const sourceNames = {
    holy_spirit: '圣灵感动',
    conscience: '良心',
    fear: '恐惧反应',
    pride: '骄傲反应',
    trauma: '创伤反应',
    worldly: '世俗影响',
    flesh: '肉体欲望',
    uncertain: '方向不明',
    mixed: '混合动机',
    love: '爱的驱动',
  };

  const sourceColors = {
    holy_spirit: 'sfds-badge-sage',
    conscience: 'sfds-badge-teal',
    fear: 'sfds-badge-warm',
    pride: 'sfds-badge-warm',
    trauma: 'sfds-badge-muted',
    worldly: 'sfds-badge-muted',
    flesh: 'sfds-badge-muted',
    uncertain: 'sfds-badge-muted',
    mixed: 'sfds-badge-muted',
    love: 'sfds-badge-sage',
  };

  const getWellbeingScore = () => {
    const { stress, anxiety, peace, joy, spiritualVitality } = currentState;
    return Math.round((peace + joy + spiritualVitality - stress - anxiety + 15) / 3);
  };

  const getWellbeingLabel = (score) => {
    if (score >= 7) return { text: '状态良好', color: '#5a9a8f' };
    if (score >= 5) return { text: '状态平稳', color: '#8fa872' };
    if (score >= 3) return { text: '需要关注', color: '#c4a77d' };
    return { text: '需要休息', color: '#c4a77d' };
  };

  const wellbeing = getWellbeingLabel(getWellbeingScore());

  return (
    <div className="sfds-page sfds-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 className="sfds-title">灵性决策陪伴</h1>
        <p className="sfds-subtitle">
          在这里，我们陪伴您分辨内心的声音，而非替您做决定
        </p>
      </div>

      {/* Current State Card */}
      <div className="sfds-card sfds-card-gentle" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <h2 className="sfds-section-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
              今日状态
            </h2>
            <p className="sfds-body" style={{ marginTop: '8px' }}>
              觉察当下的自己，是分辨的第一步
            </p>
          </div>
          <span className={`sfds-badge ${wellbeing.color === '#5a9a8f' ? 'sfds-badge-teal' : wellbeing.color === '#8fa872' ? 'sfds-badge-sage' : 'sfds-badge-warm'}`}>
            {wellbeing.text}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
          <StateIndicator label="压力" value={currentState.stress} inverse />
          <StateIndicator label="焦虑" value={currentState.anxiety} inverse />
          <StateIndicator label="平安" value={currentState.peace} />
          <StateIndicator label="喜乐" value={currentState.joy} />
          <StateIndicator label="疲劳" value={currentState.fatigue} inverse />
          <StateIndicator label="灵性活力" value={currentState.spiritualVitality} />
        </div>

        <div style={{ marginTop: '20px', padding: '16px', background: 'var(--sfds-bg-secondary)', borderRadius: '8px' }}>
          <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0 }}>
            💭 <strong>温柔的提醒：</strong>
            {currentState.stress > 6 || currentState.anxiety > 6
              ? '您现在的压力/焦虑水平较高，如果要做重要决定，或许可以先花一些时间照顾自己的情绪。'
              : currentState.spiritualVitality < 4
              ? '灵性的干涸是真实的。在这个季节，或许重建与神的关系比做任何决定都更重要。'
              : '您的状态看起来相对平稳。这是一个适合思考和分辨的时机。'}
          </p>
        </div>
      </div>

      {/* Quick Action */}
      <button
        className="sfds-btn sfds-btn-primary"
        style={{ width: '100%', marginBottom: '24px', justifyContent: 'center', padding: '16px' }}
        onClick={() => onNavigate('new-decision')}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        记录一个新的决定
      </button>

      {/* Recent Decisions */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 className="sfds-section-title" style={{ margin: 0 }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            最近的决定
          </h2>
          <button 
            className="sfds-btn sfds-btn-secondary"
            style={{ padding: '8px 16px', fontSize: '14px' }}
            onClick={() => onNavigate('history')}
          >
            查看全部
          </button>
        </div>

        {recentDecisions.length === 0 ? (
          <div className="sfds-empty">
            <div className="sfds-empty-icon">🌱</div>
            <p>还没有记录的决定</p>
            <p style={{ fontSize: '14px', marginTop: '8px' }}>
              每一个重要的决定都值得被温柔地对待
            </p>
          </div>
        ) : (
          recentDecisions.map((decision) => (
            <div
              key={decision.id}
              className="sfds-card"
              style={{ cursor: 'pointer' }}
              onClick={() => onNavigate('result', decision.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span className="sfds-badge sfds-badge-muted">
                      {categoryNames[decision.category] || decision.category}
                    </span>
                    <span style={{ fontSize: '13px', color: 'var(--sfds-text-muted)' }}>
                      {decision.date}
                    </span>
                  </div>
                  <h3 style={{ fontSize: '16px', fontWeight: 500, margin: '0 0 8px 0', color: 'var(--sfds-text-primary)' }}>
                    {decision.title}
                  </h3>
                  <span className={`sfds-badge ${sourceColors[decision.primarySource] || 'sfds-badge-muted'}`}>
                    {sourceNames[decision.primarySource] || decision.primarySource}
                  </span>
                </div>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--sfds-text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Spiritual Trend Chart Placeholder */}
      <div className="sfds-card">
        <h2 className="sfds-section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 3v18h18"/>
            <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/>
          </svg>
          灵性成长轨迹
        </h2>
        <p className="sfds-body" style={{ marginBottom: '16px' }}>
          属灵生命的成长，往往是在我们未曾察觉的时候悄然发生
        </p>
        <div className="sfds-chart-container">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '8px' }}>📈</div>
            <p>灵性健康趋势图表将在这里显示</p>
            <p style={{ fontSize: '14px', marginTop: '8px' }}>
              记录更多日常状态后，您将看到自己的成长轨迹
            </p>
          </div>
        </div>
      </div>

      {/* Daily Reflection Prompt */}
      <div className="sfds-reflection-box">
        <p className="sfds-reflection-question">
          "今天的我，比昨天更靠近神一些了吗？"
        </p>
        <button
          className="sfds-btn sfds-btn-gentle"
          onClick={() => onNavigate('journal')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          写下今日反思
        </button>
      </div>
    </div>
  );
};

const StateIndicator = ({ label, value, inverse }) => {
  const getColor = (val) => {
    if (inverse) {
      if (val <= 3) return '#5a9a8f';
      if (val <= 6) return '#8fa872';
      return '#c4a77d';
    }
    if (val >= 7) return '#5a9a8f';
    if (val >= 5) return '#8fa872';
    return '#c4a77d';
  };

  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ 
        fontSize: '24px', 
        fontWeight: 600, 
        color: getColor(value),
        marginBottom: '4px'
      }}>
        {value}
      </div>
      <div style={{ fontSize: '13px', color: 'var(--sfds-text-muted)' }}>
        {label}
      </div>
      <div style={{
        height: '4px',
        background: 'var(--sfds-border)',
        borderRadius: '2px',
        marginTop: '8px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${value * 10}%`,
          height: '100%',
          background: getColor(value),
          borderRadius: '2px',
          transition: 'width 0.3s ease'
        }} />
      </div>
    </div>
  );
};

export default Dashboard;
