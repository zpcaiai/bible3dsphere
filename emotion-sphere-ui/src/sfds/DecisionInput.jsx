import React, { useState } from 'react';
import './styles.css';

const emotions = [
  { type: 'joy', label: '喜乐', category: 'positive' },
  { type: 'peace', label: '平安', category: 'positive' },
  { type: 'love', label: '爱', category: 'positive' },
  { type: 'gratitude', label: '感恩', category: 'positive' },
  { type: 'hope', label: '盼望', category: 'positive' },
  { type: 'confidence', label: '自信', category: 'positive' },
  { type: 'sadness', label: '悲伤', category: 'negative' },
  { type: 'fear', label: '恐惧', category: 'negative' },
  { type: 'anxiety', label: '焦虑', category: 'negative' },
  { type: 'anger', label: '愤怒', category: 'negative' },
  { type: 'confusion', label: '困惑', category: 'negative' },
  { type: 'guilt', label: '内疚', category: 'negative' },
  { type: 'shame', label: '羞耻', category: 'negative' },
  { type: 'loneliness', label: '孤独', category: 'negative' },
  { type: 'numbness', label: '麻木', category: 'neutral' },
  { type: 'uncertainty', label: '不确定', category: 'neutral' },
];

const categories = [
  { value: 'career', label: '职业工作' },
  { value: 'relationship', label: '人际关系' },
  { value: 'temptation', label: '面对试探' },
  { value: 'calling', label: '使命呼召' },
  { value: 'financial', label: '财务决定' },
  { value: 'health', label: '健康相关' },
  { value: 'ministry', label: '事奉相关' },
  { value: 'other', label: '其他' },
];

const DecisionInput = ({ onNavigate, onSubmit }) => {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    urgency: 3,
    importance: 3,
    selectedEmotions: [],
    stateSnapshot: {
      stress: 5,
      anxiety: 5,
      fatigue: 5,
      spiritualDryness: 5,
      emotionalStability: 5,
    },
  });

  const handleEmotionToggle = (emotionType) => {
    setFormData(prev => {
      const selected = prev.selectedEmotions;
      if (selected.includes(emotionType)) {
        return { ...prev, selectedEmotions: selected.filter(e => e !== emotionType) };
      }
      if (selected.length >= 3) {
        return prev; // Max 3 emotions
      }
      return { ...prev, selectedEmotions: [...selected, emotionType] };
    });
  };

  const handleSliderChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      stateSnapshot: {
        ...prev.stateSnapshot,
        [field]: parseInt(value)
      }
    }));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    onSubmit?.(formData);
    onNavigate('result');
  };

  const canProceed = () => {
    if (step === 1) {
      return formData.title.trim() && formData.category;
    }
    if (step === 2) {
      return formData.selectedEmotions.length > 0;
    }
    return true;
  };

  const renderStep1 = () => (
    <div className="sfds-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h2 className="sfds-section-title">描述您的情况</h2>
        <p className="sfds-body">
          没有"正确"或"错误"的描述方式。用您觉得自然的语言即可。
        </p>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label className="sfds-label">这个决定是关于什么的？</label>
        <input
          type="text"
          className="sfds-input"
          placeholder="例如：是否应该接受新的工作机会"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
        />
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label className="sfds-label">属于哪一类？</label>
        <select
          className="sfds-select"
          value={formData.category}
          onChange={(e) => setFormData({ ...formData, category: e.target.value })}
        >
          <option value="">请选择类别...</option>
          {categories.map(cat => (
            <option key={cat.value} value={cat.value}>{cat.label}</option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label className="sfds-label">
          详细描述
          <span style={{ fontWeight: 'normal', color: 'var(--sfds-text-muted)' }}>（可选）</span>
        </label>
        <textarea
          className="sfds-input"
          rows={4}
          placeholder="描述一下具体情况，您现在的想法，以及可能的选项..."
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
        />
        <p className="sfds-hint">
          💡 小贴士：描述您感受到的张力、顾虑，以及任何已经考虑的选项
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
        <div>
          <label className="sfds-label">紧急程度</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            {[1, 2, 3, 4, 5].map(level => (
              <button
                key={level}
                className={`sfds-btn ${formData.urgency === level ? 'sfds-btn-primary' : 'sfds-btn-secondary'}`}
                style={{ flex: 1, padding: '12px 8px' }}
                onClick={() => setFormData({ ...formData, urgency: level })}
              >
                {level}
              </button>
            ))}
          </div>
          <p className="sfds-hint">
            {formData.urgency <= 2 ? '不急，有时间思考' : formData.urgency >= 4 ? '需要较快回应' : '中等紧急'}
          </p>
        </div>

        <div>
          <label className="sfds-label">重要程度</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            {[1, 2, 3, 4, 5].map(level => (
              <button
                key={level}
                className={`sfds-btn ${formData.importance === level ? 'sfds-btn-primary' : 'sfds-btn-secondary'}`}
                style={{ flex: 1, padding: '12px 8px' }}
                onClick={() => setFormData({ ...formData, importance: level })}
              >
                {level}
              </button>
            ))}
          </div>
          <p className="sfds-hint">
            {formData.importance <= 2 ? '影响较小' : formData.importance >= 4 ? '影响深远' : '中等影响'}
          </p>
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="sfds-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h2 className="sfds-section-title">当下的情绪</h2>
        <p className="sfds-body">
          选择最多3个最能描述您此刻感受的情绪。所有的情绪都值得被看见。
        </p>
      </div>

      <div className="sfds-emotion-grid" style={{ marginBottom: '24px' }}>
        {emotions.map(emotion => (
          <button
            key={emotion.type}
            className={`sfds-emotion-chip ${formData.selectedEmotions.includes(emotion.type) ? 'selected' : ''}`}
            onClick={() => handleEmotionToggle(emotion.type)}
          >
            {emotion.label}
          </button>
        ))}
      </div>

      {formData.selectedEmotions.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <p className="sfds-hint" style={{ marginBottom: '12px' }}>
            已选择 {formData.selectedEmotions.length}/3：
          </p>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {formData.selectedEmotions.map(type => {
              const emotion = emotions.find(e => e.type === type);
              return (
                <span key={type} className="sfds-badge sfds-badge-teal">
                  {emotion?.label}
                </span>
              );
            })}
          </div>
        </div>
      )}

      <div className="sfds-card sfds-card-gentle">
        <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0 }}>
          🌿 <strong> gentle reminder：</strong>
          情绪不是敌人，它们是内心深处的信使。
          愤怒可能指向未满足的需要，恐惧可能守护着重要的边界。
        </p>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="sfds-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h2 className="sfds-section-title">此刻的状态</h2>
        <p className="sfds-body">
          用滑动条标记您当前的状态。没有"应该"的数值——诚实面对自己就是最好的起点。
        </p>
      </div>

      <div className="sfds-card">
        <StateSlider
          label="压力水平"
          value={formData.stateSnapshot.stress}
          onChange={(v) => handleSliderChange('stress', v)}
          lowLabel="轻松"
          highLabel="压力很大"
        />
        <StateSlider
          label="焦虑水平"
          value={formData.stateSnapshot.anxiety}
          onChange={(v) => handleSliderChange('anxiety', v)}
          lowLabel="平静"
          highLabel="焦虑很高"
        />
        <StateSlider
          label="疲劳程度"
          value={formData.stateSnapshot.fatigue}
          onChange={(v) => handleSliderChange('fatigue', v)}
          lowLabel="精力充沛"
          highLabel="非常疲惫"
        />
        <StateSlider
          label="灵性状态"
          value={formData.stateSnapshot.spiritualDryness}
          onChange={(v) => handleSliderChange('spiritualDryness', v)}
          lowLabel="与神亲近"
          highLabel="灵性干涸"
          inverse
        />
        <StateSlider
          label="情绪稳定"
          value={formData.stateSnapshot.emotionalStability}
          onChange={(v) => handleSliderChange('emotionalStability', v)}
          lowLabel="波动很大"
          highLabel="非常稳定"
        />
      </div>

      <div className="sfds-reflection-box" style={{ marginTop: '24px' }}>
        <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0 }}>
          💭 您知道吗？
          <br /><br />
          研究表明，在压力大或焦虑时做出的决定，往往更偏向"避免损失"而非"追求成长"。
          <br /><br />
          这不是软弱——这是人类大脑保护我们的方式。觉察这一点，本身就是智慧的开始。
        </p>
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="sfds-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h2 className="sfds-section-title">准备开始辨识</h2>
        <p className="sfds-body">
          让我们回顾一下您提供的信息，然后开启这段分辨之旅。
        </p>
      </div>

      <div className="sfds-card" style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 500, marginBottom: '12px' }}>决定概况</h3>
        <p style={{ marginBottom: '8px' }}><strong>{formData.title}</strong></p>
        <p style={{ fontSize: '14px', color: 'var(--sfds-text-muted)', marginBottom: '12px' }}>
          {categories.find(c => c.value === formData.category)?.label} · 
          紧急度 {formData.urgency} · 重要度 {formData.importance}
        </p>
        {formData.description && (
          <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)' }}>
            {formData.description.slice(0, 100)}{formData.description.length > 100 ? '...' : ''}
          </p>
        )}
      </div>

      <div className="sfds-card" style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 500, marginBottom: '12px' }}>情绪状态</h3>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {formData.selectedEmotions.map(type => {
            const emotion = emotions.find(e => e.type === type);
            return (
              <span key={type} className="sfds-badge sfds-badge-teal">
                {emotion?.label}
              </span>
            );
          })}
        </div>
      </div>

      <div className="sfds-card" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 500, marginBottom: '12px' }}>身心状态</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 600, color: 'var(--sfds-accent-teal)' }}>
              {formData.stateSnapshot.stress}/10
            </div>
            <div style={{ fontSize: '13px', color: 'var(--sfds-text-muted)' }}>压力</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 600, color: 'var(--sfds-accent-teal)' }}>
              {formData.stateSnapshot.anxiety}/10
            </div>
            <div style={{ fontSize: '13px', color: 'var(--sfds-text-muted)' }}>焦虑</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 600, color: 'var(--sfds-accent-teal)' }}>
              {formData.stateSnapshot.emotionalStability}/10
            </div>
            <div style={{ fontSize: '13px', color: 'var(--sfds-text-muted)' }}>情绪稳定</div>
          </div>
        </div>
      </div>

      <div className="sfds-card sfds-card-gentle">
        <p style={{ fontSize: '14px', color: 'var(--sfds-text-secondary)', margin: 0 }}>
          ✨ 在我们开始之前，请记得：
          <br /><br />
          这个工具不是来替您做决定的，而是帮助您看见自己可能忽略的角度。
          <br /><br />
          最终的选择权始终在您手中——而这正是神的恩赐：自由意志。
        </p>
      </div>
    </div>
  );

  return (
    <div className="sfds-page sfds-fade-in">
      {/* Progress Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '24px' }}>
        <button 
          className="sfds-btn sfds-btn-secondary"
          style={{ padding: '8px', marginRight: '16px' }}
          onClick={() => step > 1 ? setStep(step - 1) : onNavigate('dashboard')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
            {[1, 2, 3, 4].map(s => (
              <div
                key={s}
                style={{
                  flex: 1,
                  height: '4px',
                  background: s <= step ? 'var(--sfds-accent-teal)' : 'var(--sfds-border)',
                  borderRadius: '2px',
                  transition: 'background 0.3s ease'
                }}
              />
            ))}
          </div>
          <p style={{ fontSize: '13px', color: 'var(--sfds-text-muted)', margin: 0 }}>
            步骤 {step} / 4
          </p>
        </div>
      </div>

      {/* Step Content */}
      {step === 1 && renderStep1()}
      {step === 2 && renderStep2()}
      {step === 3 && renderStep3()}
      {step === 4 && renderStep4()}

      {/* Navigation Buttons */}
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
        {step < 4 ? (
          <button
            className="sfds-btn sfds-btn-primary"
            style={{ flex: 1, justifyContent: 'center' }}
            onClick={() => setStep(step + 1)}
            disabled={!canProceed()}
          >
            继续
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        ) : (
          <button
            className="sfds-btn sfds-btn-primary"
            style={{ flex: 1, justifyContent: 'center' }}
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <div className="sfds-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                分析中...
              </>
            ) : (
              <>
                开始辨识
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

const StateSlider = ({ label, value, onChange, lowLabel, highLabel, inverse }) => {
  const getColor = (val) => {
    if (inverse) {
      if (val <= 3) return '#5a9a8f';
      if (val <= 6) return '#8fa872';
      return '#c4a77d';
    }
    if (val >= 7) return '#5a9a8f';
    if (val >= 4) return '#8fa872';
    return '#c4a77d';
  };

  return (
    <div className="sfds-slider-container">
      <div className="sfds-slider-header">
        <span className="sfds-slider-label">{label}</span>
        <span className="sfds-slider-value" style={{ color: getColor(value) }}>{value}</span>
      </div>
      <input
        type="range"
        min="1"
        max="10"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="sfds-slider"
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
        <span style={{ fontSize: '12px', color: 'var(--sfds-text-muted)' }}>{lowLabel}</span>
        <span style={{ fontSize: '12px', color: 'var(--sfds-text-muted)' }}>{highLabel}</span>
      </div>
    </div>
  );
};

export default DecisionInput;
