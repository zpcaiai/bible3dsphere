import { useEffect, useRef, useState } from 'react'
import { fetchDailySoulQuestion, saveSoulAnswer, fetchSoulQuestionHistory } from './api'

const LOOP_LABELS = {
  fear_control_loop: '🔒 恐惧控制',
  shame_avoidance_loop: '🙈 羞耻回避',
  pride_comparison_loop: '🏆 骄傲比较',
  desire_impulse_loop: '🌊 欲望冲动',
  truth_stability_loop: '✨ 真理稳固',
}

const TRAJ_LABELS = {
  stabilizing: '🌱 稳定成长',
  improving_clarity: '✨ 清晰提升',
  fragmenting: '🌊 内心挣扎',
  increasing_volatility: '⚡ 情绪波动',
  cyclical: '🔄 循环中',
}

export default function DailySoulQuestionPage({ user, token, onBack }) {
  const [loading, setLoading] = useState(true)
  const [questionData, setQuestionData] = useState(null)
  const [answer, setAnswer] = useState('')
  const [saveToJournal, setSaveToJournal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [view, setView] = useState('today') // 'today' | 'history'
  const [history, setHistory] = useState([])
  const [histLoading, setHistLoading] = useState(false)
  const [error, setError] = useState('')
  const textareaRef = useRef(null)

  useEffect(() => {
    if (!user) return
    setLoading(true)
    fetchDailySoulQuestion(token)
      .then(d => {
        setQuestionData(d)
        if (d.already_answered) {
          setAnswer(d.answer || '')
          setSubmitted(true)
        }
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [user, token])

  useEffect(() => {
    if (view === 'history' && history.length === 0) {
      setHistLoading(true)
      fetchSoulQuestionHistory(token)
        .then(items => { setHistory(items); setHistLoading(false) })
        .catch(() => setHistLoading(false))
    }
  }, [view, token, history.length])

  async function handleSubmit() {
    if (!answer.trim() || submitting) return
    setSubmitting(true)
    try {
      await saveSoulAnswer(answer.trim(), saveToJournal, token)
      setSubmitted(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="pw-page">
      <header className="pw-header">
        <button className="checkin-back-btn" onClick={onBack} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="pw-header-center">
          <div className="pw-title">🔍 每日灵魂一问</div>
          <div className="pw-subtitle">每天一个诚实的问题，是属灵成长的开始</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setView('today')} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 8, border: 'none', background: view === 'today' ? 'rgba(88,86,214,0.4)' : 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer' }}>今日</button>
          <button onClick={() => setView('history')} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 8, border: 'none', background: view === 'history' ? 'rgba(88,86,214,0.4)' : 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer' }}>回顾</button>
        </div>
      </header>

      <div style={{ padding: '20px 16px', maxWidth: 600, margin: '0 auto' }}>
        {error && <div style={{ color: '#ff3b30', fontSize: 13, marginBottom: 16, textAlign: 'center' }}>{error}</div>}

        {view === 'today' && (
          <>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '60px 0', color: 'rgba(255,255,255,0.5)' }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>✨</div>
                <div>正在为你生成今日的问题...</div>
              </div>
            ) : questionData ? (
              <>
                {/* Context chips */}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
                  {questionData.dominant_loop && (
                    <span style={{ fontSize: 11, background: 'rgba(88,86,214,0.2)', border: '1px solid rgba(88,86,214,0.4)', borderRadius: 20, padding: '3px 10px', color: '#c4b5fd' }}>
                      {LOOP_LABELS[questionData.dominant_loop] || questionData.dominant_loop}
                    </span>
                  )}
                  {questionData.trajectory && (
                    <span style={{ fontSize: 11, background: 'rgba(0,122,255,0.15)', border: '1px solid rgba(0,122,255,0.3)', borderRadius: 20, padding: '3px 10px', color: '#5eb0ff' }}>
                      {TRAJ_LABELS[questionData.trajectory] || questionData.trajectory}
                    </span>
                  )}
                </div>

                {/* The question */}
                <div style={{
                  background: 'linear-gradient(135deg, rgba(88,86,214,0.15), rgba(0,122,255,0.1))',
                  border: '1px solid rgba(88,86,214,0.3)',
                  borderRadius: 16, padding: '28px 24px', marginBottom: 24, textAlign: 'center',
                }}>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 14, letterSpacing: '0.06em' }}>
                    {questionData.date} · 今日一问
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', lineHeight: 1.5 }}>
                    {questionData.question}
                  </div>
                </div>

                {/* Answer area */}
                {submitted ? (
                  <div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 8 }}>你的回答</div>
                    <div style={{
                      background: 'rgba(52,199,89,0.08)', border: '1px solid rgba(52,199,89,0.25)',
                      borderRadius: 12, padding: '16px', fontSize: 15, color: 'rgba(255,255,255,0.85)',
                      lineHeight: 1.7, whiteSpace: 'pre-wrap',
                    }}>
                      {answer}
                    </div>
                    <div style={{ marginTop: 12, fontSize: 12, color: 'rgba(52,199,89,0.8)', textAlign: 'center' }}>
                      ✅ 已记录，明日再见
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 8 }}>
                      诚实地回答这个问题（无需完美，只需真实）
                    </div>
                    <textarea
                      ref={textareaRef}
                      value={answer}
                      onChange={e => setAnswer(e.target.value)}
                      placeholder="在这里写下你真实的回应..."
                      style={{
                        width: '100%', minHeight: 120, background: 'rgba(255,255,255,0.07)',
                        border: '1px solid rgba(255,255,255,0.15)', borderRadius: 12, color: '#fff',
                        fontSize: 15, padding: '14px 16px', resize: 'vertical', outline: 'none',
                        fontFamily: 'inherit', lineHeight: 1.7, boxSizing: 'border-box',
                      }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>
                        <input type="checkbox" checked={saveToJournal} onChange={e => setSaveToJournal(e.target.checked)} />
                        同步到今日灵修日记
                      </label>
                      <button
                        onClick={handleSubmit}
                        disabled={!answer.trim() || submitting}
                        style={{
                          background: answer.trim() ? 'linear-gradient(135deg,#5856d6,#007aff)' : 'rgba(255,255,255,0.1)',
                          border: 'none', borderRadius: 10, color: '#fff', fontSize: 14, fontWeight: 600,
                          padding: '10px 24px', cursor: answer.trim() ? 'pointer' : 'default',
                        }}
                      >
                        {submitting ? '记录中...' : '✅ 记录回答'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Reflection note */}
                <div style={{ marginTop: 28, padding: '14px 16px', background: 'rgba(255,255,255,0.04)', borderRadius: 10, fontSize: 12, color: 'rgba(255,255,255,0.4)', lineHeight: 1.6, textAlign: 'center' }}>
                  「省察自己是否在信仰中站立得稳」— 哥林多后书 13:5
                </div>
              </>
            ) : null}
          </>
        )}

        {view === 'history' && (
          <div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 16 }}>
              你的灵魂省察记录 · 30天内对比成长
            </div>
            {histLoading ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: 'rgba(255,255,255,0.4)' }}>加载中...</div>
            ) : history.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: 'rgba(255,255,255,0.3)', fontSize: 14 }}>
                还没有回答记录，从今天开始吧 🌱
              </div>
            ) : (
              history.map((item, i) => (
                <div key={i} style={{
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 12, padding: '16px', marginBottom: 12,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{item.date}</span>
                    {item.dominant_loop && (
                      <span style={{ fontSize: 10, color: '#c4b5fd', background: 'rgba(88,86,214,0.15)', borderRadius: 10, padding: '2px 8px' }}>
                        {LOOP_LABELS[item.dominant_loop] || item.dominant_loop}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#e0d4ff', marginBottom: 8, lineHeight: 1.5 }}>
                    {item.question}
                  </div>
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', lineHeight: 1.65, whiteSpace: 'pre-wrap', borderLeft: '2px solid rgba(88,86,214,0.4)', paddingLeft: 10 }}>
                    {item.answer}
                  </div>
                  {item.saved_to_journal && (
                    <div style={{ marginTop: 6, fontSize: 11, color: '#34c759' }}>📔 已存入灵修日记</div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
