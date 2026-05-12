import React, { useState } from 'react';
import './styles.css';

// Mock data
const mockEntries = [
  {
    id: 1,
    date: '2026-05-10',
    type: 'daily',
    content: '今天是一个平静的日子。在灵修时读了诗篇23篇，关于"耶和华是我的牧者"，给了我很大的安慰。工作压力虽然还在，但内心有一种超越环境的平安。',
    emotions: ['peace', 'gratitude'],
    decisionId: null,
  },
  {
    id: 2,
    date: '2026-05-08',
    type: 'decision_review',
    content: '关于新工作机会的决定，已经过去一周了。回想起来，虽然过程很挣扎，但最终选择等待是一个正确的决定。这周身体好一些了，看待这个问题的角度也不同了。',
    emotions: ['peace', 'confidence'],
    decisionId: 1,
    decisionTitle: '是否应该接受新的工作机会',
    outcome: 'delayed',
  },
  {
    id: 3,
    date: '2026-05-05',
    type: 'daily',
    content: '今天感到特别疲惫。早上起来就没有力气，灵修也很难专注。也许这就是身体在告诉我需要休息了吧。决定今天早点休息，不强求自己。',
    emotions: ['fatigue', 'sadness'],
    decisionId: null,
  },
  {
    id: 4,
    date: '2026-05-01',
    type: 'decision_review',
    content: '最终选择饶恕了那位朋友。不是因为感觉好了，而是因为选择释放自己。这个过程比想象中难，但也比想象中有释放。关系还在恢复中，但至少不再被 bitterness 捆绑。',
    emotions: ['peace', 'hope'],
    decisionId: 2,
    decisionTitle: '饶恕曾经伤害我的朋友',
    outcome: 'positive',
  },
];

const prompts = [
  '今天的我，比昨天更靠近神一些了吗？',
  '今天我经历了什么挑战？从中我学到了什么？',
  '如果用一个词形容今天的情绪，会是什么？为什么？',
  '今天有什么值得感恩的事，即使是很小的？',
  '我今天是否对自己太苛刻了？如果是，我想对自己说什么？',
  '今天有什么决定让我感到挣扎？',
  '如果耶稣今天与我同行，祂会如何看待我今天的处境？',
];

const ReflectionJournal = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState('entries');
  const [entries, setEntries] = useState(mockEntries);
  const [showNewEntry, setShowNewEntry] = useState(false);
  const [newEntry, setNewEntry] = useState({
    content: '',
    emotions: [],
    type: 'daily',
  });
  const [selectedPrompt, setSelectedPrompt] = useState('');

  const emotionOptions = [
    { value: 'joy', label: '喜乐' },
    { value: 'peace', label: '平安' },
    { value: 'gratitude', label: '感恩' },
    { value: 'hope', label: '盼望' },
    { value: 'confidence', label: '自信' },
    { value: 'sadness', label: '悲伤' },
    { value: 'fear', label: '恐惧' },
    { value: 'anxiety', label: '焦虑' },
    { value: 'anger', label: '愤怒' },
    { value: 'confusion', label: '困惑' },
    { value: 'guilt', label: '内疚' },
    { value: 'shame', label: '羞耻' },
    { value: 'loneliness', label: '孤独' },
    { value: 'fatigue', label: '疲惫' },
    { value: 'numbness', label: '麻木' },
  ];

  const handleSaveEntry = () => {
    if (!newEntry.content.trim()) return;
    
    const entry = {
      id: Date.now(),
      date: new Date().toISOString().split('T')[0],
      type: newEntry.type,
      content: newEntry.content,
      emotions: newEntry.emotions,
      decisionId: null,
    };
    
    setEntries([entry, ...entries]);
    setNewEntry({ content: '', emotions: [], type: 'daily' });
    setShowNewEntry(false);
    setSelectedPrompt('');
  };

  const handleEmotionToggle = (emotion) => {
    setNewEntry(prev => {
      const emotions = prev.emotions;
      if (emotions.includes(emotion)) {
        return { ...prev, emotions: emotions.filter(e => e !== emotion) };
      }
      if (emotions.length >= 3) return prev;
      return { ...prev, emotions: [...emotions, emotion] };
    });
  };

  const usePrompt = (prompt) => {
    setSelectedPrompt(prompt);
    setNewEntry(prev => ({ ...prev, content: prompt + '\n\n' }));
    setShowNewEntry(true);
  };

  const getEmotionLabel = (value) => {
    return emotionOptions.find(e => e.value === value)?.label || value;
  };

  const getEmotionColor = (emotion) => {
    const positive = ['joy', 'peace', 'gratitude', 'hope', 'confidence'];
    const negative = ['sadness', 'fear', 'anxiety', 'anger', 'confusion', 'guilt', 'shame', 'loneliness', 'fatigue'];
    
    if (positive.includes(emotion)) return 'sfds-badge-teal';
    if (negative.includes(emotion)) return 'sfds-badge-warm';
    return 'sfds-badge-muted';
  };

  const renderEntries = () => (
    <div className="sfds-fade-in">
      {/* New Entry Button */}
      <button
        className="sfds-btn sfds-btn-primary"
        style={{ width: '100%', marginBottom: '24px', justifyContent: 'center' }}
        onClick={() => setShowNewEntry(true)}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        写新的反思
      </button>

      {/* Entries List */}
      {entries.length === 0 ? (
        <div className="sfds-empty">
          <div className="sfds-empty-icon">📔</div>
          <p>还没有反思记录</p>
          <p style={{ fontSize: '14px', marginTop: '8px' }}>
            定期反思是灵性成长的重要部分
          </p>
        </div>
      ) : (
        <div className="sfds-timeline">
          {entries.map((entry) => (
            <div key={entry.id} className="sfds-timeline-item">
              <div className="sfds-timeline-date">
                {entry.date}
                {entry.type === 'decision_review' && (
                  <span className="sfds-badge sfds-badge-sage" style={{ marginLeft: '8px' }}>
                    决策回顾
                  </span>
                )}
              </div>
              <div className="sfds-timeline-content">
                {entry.decisionTitle && (
                  <p style={{ fontSize: '13px', color: 'var(--sfds-accent-teal)', marginBottom: '8px', fontWeight: 500 }}>
                    关于: {entry.decisionTitle}
                    {entry.outcome && (
                      <span style={{ marginLeft: '8px' }}>
                        {entry.outcome === 'positive' ? '✓ 积极结果' : 
                         entry.outcome === 'negative' ? '✗ 挑战' : 
                         entry.outcome === 'delayed' ? '⏸ 推迟决定' : '↻ 进行中'}
                      </span>
                    )}
                  </p>
                )}
                <p style={{ fontSize: '15px', color: 'var(--sfds-text-primary)', lineHeight: '1.7', marginBottom: '12px' }}>
                  {entry.content}
                </p>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {entry.emotions.map(emotion => (
                    <span key={emotion} className={`sfds-badge ${getEmotionColor(emotion)}`} style={{ fontSize: '11px' }}>
                      {getEmotionLabel(emotion)}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderPrompts = () => (
    <div className="sfds-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h2 className="sfds-section-title">反思 prompts</h2>
        <p className="sfds-body">
          不知道写什么？这些 prompts 可以帮助您开始。不需要回答所有问题——选择触动您的那个即可。
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {prompts.map((prompt, idx) => (
          <div
            key={idx}
            className="sfds-card"
            style={{ cursor: 'pointer' }}
            onClick={() => usePrompt(prompt)}
          >
            <p style={{ fontSize: '16px', color: 'var(--sfds-text-primary)', fontStyle: 'italic', margin: 0, lineHeight: '1.6' }}>
              "{prompt}"
            </p>
            <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
              <span className="sfds-btn sfds-btn-gentle" style={{ padding: '6px 12px', fontSize: '13px' }}>
                以此为题目
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  if (showNewEntry) {
    return (
      <div className="sfds-page sfds-fade-in">
        <div style={{ marginBottom: '24px' }}>
          <button 
            className="sfds-btn sfds-btn-secondary"
            style={{ padding: '8px' }}
            onClick={() => setShowNewEntry(false)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            取消
          </button>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h1 className="sfds-title">写反思</h1>
          <p className="sfds-subtitle">
            这是一个只属于自己的空间。这里没有评判，只有倾听。
          </p>
        </div>

        {selectedPrompt && (
          <div className="sfds-card sfds-card-gentle" style={{ marginBottom: '20px' }}>
            <p style={{ fontSize: '15px', color: 'var(--sfds-text-secondary)', fontStyle: 'italic', margin: 0 }}>
              今日题目: "{selectedPrompt}"
            </p>
          </div>
        )}

        <div style={{ marginBottom: '20px' }}>
          <label className="sfds-label">今天的类型</label>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className={`sfds-btn ${newEntry.type === 'daily' ? 'sfds-btn-primary' : 'sfds-btn-secondary'}`}
              style={{ flex: 1 }}
              onClick={() => setNewEntry({ ...newEntry, type: 'daily' })}
            >
              日常反思
            </button>
            <button
              className={`sfds-btn ${newEntry.type === 'decision_review' ? 'sfds-btn-primary' : 'sfds-btn-secondary'}`}
              style={{ flex: 1 }}
              onClick={() => setNewEntry({ ...newEntry, type: 'decision_review' })}
            >
              决策回顾
            </button>
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label className="sfds-label">此刻的情绪</label>
          <p className="sfds-hint" style={{ marginBottom: '12px' }}>选择最多3个</p>
          <div className="sfds-emotion-grid">
            {emotionOptions.map(emotion => (
              <button
                key={emotion.value}
                className={`sfds-emotion-chip ${newEntry.emotions.includes(emotion.value) ? 'selected' : ''}`}
                onClick={() => handleEmotionToggle(emotion.value)}
              >
                {emotion.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label className="sfds-label">写下您的反思</label>
          <textarea
            className="sfds-input"
            rows={8}
            placeholder="此刻，您的心在想什么..."
            value={newEntry.content}
            onChange={(e) => setNewEntry({ ...newEntry, content: e.target.value })}
          />
        </div>

        <div className="sfds-reflection-box" style={{ marginBottom: '24px' }}>
          <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0, lineHeight: '1.7' }}>
            💭 <strong>温柔的提醒：</strong>
            <br /><br />
            您不需要写出"正确"或"属灵"的内容。诚实地面对自己——包括那些不那么光鲜的想法——本身就是信心的体现。
            <br /><br />
            神已经知道您心里的一切。祂要的不是完美的文字，而是真实的您。
          </p>
        </div>

        <div style={{ 
          position: 'fixed', 
          bottom: 0, 
          left: 0, 
          right: 0, 
          background: 'var(--sfds-bg-card)',
          borderTop: '1px solid var(--sfds-border)',
          padding: '16px 24px',
          display: 'flex',
          gap: '12px'
        }}>
          <button
            className="sfds-btn sfds-btn-secondary"
            style={{ flex: 1 }}
            onClick={() => setShowNewEntry(false)}
          >
            取消
          </button>
          <button
            className="sfds-btn sfds-btn-primary"
            style={{ flex: 2 }}
            onClick={handleSaveEntry}
            disabled={!newEntry.content.trim()}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            保存
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="sfds-page sfds-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 className="sfds-title">反思日记</h1>
        <p className="sfds-subtitle">
          记录灵魂的足迹，不是为了完美，而是为了真实
        </p>
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
        <button
          className={`sfds-btn ${activeTab === 'entries' ? 'sfds-btn-primary' : 'sfds-btn-secondary'}`}
          style={{ 
            flex: 1, 
            padding: '10px',
            fontSize: '14px',
            background: activeTab === 'entries' ? 'var(--sfds-accent-teal)' : 'transparent',
            border: 'none'
          }}
          onClick={() => setActiveTab('entries')}
        >
          我的记录
        </button>
        <button
          className={`sfds-btn ${activeTab === 'prompts' ? 'sfds-btn-primary' : 'sfds-btn-secondary'}`}
          style={{ 
            flex: 1, 
            padding: '10px',
            fontSize: '14px',
            background: activeTab === 'prompts' ? 'var(--sfds-accent-teal)' : 'transparent',
            border: 'none'
          }}
          onClick={() => setActiveTab('prompts')}
        >
          反思 prompts
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'entries' && renderEntries()}
      {activeTab === 'prompts' && renderPrompts()}
    </div>
  );
};

export default ReflectionJournal;
