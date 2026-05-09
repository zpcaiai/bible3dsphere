import { useEffect, useState } from 'react'

const STORAGE_KEY = 'devotion_notes_shared'

const MOODS = [
  { emoji: '🌟', label: '感恩' },
  { emoji: '🕊️', label: '平安' },
  { emoji: '🙏', label: '渴慕' },
  { emoji: '💪', label: '刚强' },
  { emoji: '😔', label: '软弱' },
  { emoji: '😢', label: '哀恸' },
  { emoji: '🌧️', label: '挣扎' },
  { emoji: '🔥', label: '复兴' },
]

function today() {
  return new Date().toISOString().slice(0, 10)
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 (周${weekdays[d.getDay()]})`
}

function getSharedNotes() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveSharedNote(note) {
  const notes = getSharedNotes()
  notes.unshift(note)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(notes.slice(0, 50)))
}

export default function DevotionNotePage({ user, onBack }) {
  const [notes, setNotes] = useState([])
  const [isWriting, setIsWriting] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [form, setForm] = useState({
    date: today(),
    scripture: '',
    observation: '',
    reflection: '',
    application: '',
    prayer: '',
    mood: '',
    shared: false,
  })

  useEffect(() => {
    const saved = localStorage.getItem('devotion_notes_draft')
    if (saved) {
      try {
        const draft = JSON.parse(saved)
        setForm(prev => ({ ...prev, ...draft }))
      } catch {}
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('devotion_notes_draft', JSON.stringify(form))
  }, [form])

  function handleChange(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  function handleSubmit() {
    const note = {
      ...form,
      id: Date.now().toString(),
      createdAt: Date.now(),
      author: user?.nickname || '匿名弟兄',
      avatar: user?.avatar || null,
    }
    
    const saved = localStorage.getItem('devotion_notes_personal')
    const personalNotes = saved ? JSON.parse(saved) : []
    personalNotes.unshift(note)
    localStorage.setItem('devotion_notes_personal', JSON.stringify(personalNotes.slice(0, 100)))
    
    setNotes(personalNotes)
    setIsWriting(false)
    setForm({
      date: today(),
      scripture: '',
      observation: '',
      reflection: '',
      application: '',
      prayer: '',
      mood: '',
      shared: false,
    })
    setShowSuccess(true)
    setTimeout(() => setShowSuccess(false), 2000)
  }

  function handleShare() {
    const note = {
      ...form,
      id: Date.now().toString(),
      createdAt: Date.now(),
      author: user?.nickname || '匿名弟兄',
      avatar: user?.avatar || null,
      shared: true,
    }
    
    // 保存到个人笔记
    const saved = localStorage.getItem('devotion_notes_personal')
    const personalNotes = saved ? JSON.parse(saved) : []
    personalNotes.unshift(note)
    localStorage.setItem('devotion_notes_personal', JSON.stringify(personalNotes.slice(0, 100)))
    
    // 分享到公共空间
    saveSharedNote(note)
    
    setNotes(personalNotes)
    setIsWriting(false)
    setForm({
      date: today(),
      scripture: '',
      observation: '',
      reflection: '',
      application: '',
      prayer: '',
      mood: '',
      shared: false,
    })
    setShowSuccess(true)
    setTimeout(() => setShowSuccess(false), 3000)
  }

  function handleDelete(id) {
    const saved = localStorage.getItem('devotion_notes_personal')
    const personalNotes = saved ? JSON.parse(saved) : []
    const filtered = personalNotes.filter(n => n.id !== id)
    localStorage.setItem('devotion_notes_personal', JSON.stringify(filtered))
    setNotes(filtered)
  }

  useEffect(() => {
    const saved = localStorage.getItem('devotion_notes_personal')
    if (saved) {
      setNotes(JSON.parse(saved))
    }
  }, [isWriting])

  return (
    <div className="devotion-note-page">
      {/* Header */}
      <header className="chat-header">
        <button className="checkin-back-btn" onClick={onBack} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="chat-header-center">
          <div className="chat-title">灵修笔记</div>
          <div className="chat-subtitle">记录神的话语与恩典</div>
        </div>
        <button
          className="chat-new-btn"
          onClick={() => setIsWriting(true)}
          title="新建笔记"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </header>

      {/* Success Toast */}
      {showSuccess && (
        <div style={{
          position: 'fixed',
          top: '80px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(76, 175, 80, 0.9)',
          color: '#fff',
          padding: '12px 24px',
          borderRadius: '24px',
          fontSize: '14px',
          zIndex: 1000,
          backdropFilter: 'blur(10px)',
        }}>
          ✓ 笔记已保存{form.shared ? '并分享' : ''}
        </div>
      )}

      {/* Main Content */}
      <div className="chat-messages" style={{ padding: '16px' }}>
        {isWriting ? (
          <div className="dn-form-container">
            <div className="dn-date">{formatDate(form.date)}</div>
            
            {/* Mood Selection */}
            <div className="dn-mood-section">
              <div className="dn-label">今日灵修心情</div>
              <div className="dn-mood-grid">
                {MOODS.map(m => (
                  <button
                    key={m.label}
                    type="button"
                    className={`dn-mood-btn ${form.mood === m.label ? 'active' : ''}`}
                    onClick={() => handleChange('mood', m.label)}
                  >
                    <span className="dn-mood-emoji">{m.emoji}</span>
                    <span className="dn-mood-label">{m.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Form Fields */}
            <div className="dn-field">
              <div className="dn-label">📖 今日经文</div>
              <textarea
                className="dn-textarea"
                rows={2}
                placeholder="记录今天读到的经文…"
                value={form.scripture}
                onChange={e => handleChange('scripture', e.target.value)}
              />
            </div>

            <div className="dn-field">
              <div className="dn-label">🔍 观察默想</div>
              <textarea
                className="dn-textarea"
                rows={3}
                placeholder="这段经文说了什么？有什么让你印象深刻？"
                value={form.observation}
                onChange={e => handleChange('observation', e.target.value)}
              />
            </div>

            <div className="dn-field">
              <div className="dn-label">💭 灵修反思</div>
              <textarea
                className="dn-textarea"
                rows={3}
                placeholder="这段经文对你说什么？神在其中给你什么光照？"
                value={form.reflection}
                onChange={e => handleChange('reflection', e.target.value)}
              />
            </div>

            <div className="dn-field">
              <div className="dn-label">🌱 行道应用</div>
              <textarea
                className="dn-textarea"
                rows={2}
                placeholder="你今天打算如何将这段话活出来？"
                value={form.application}
                onChange={e => handleChange('application', e.target.value)}
              />
            </div>

            <div className="dn-field">
              <div className="dn-label">🙏 祷告记录</div>
              <textarea
                className="dn-textarea"
                rows={3}
                placeholder="写下你今天的祷告…"
                value={form.prayer}
                onChange={e => handleChange('prayer', e.target.value)}
              />
            </div>

            {/* Action Buttons */}
            <div className="dn-actions">
              <button
                className="dn-btn dn-btn-secondary"
                onClick={() => setIsWriting(false)}
              >
                取消
              </button>
              <button
                className="dn-btn dn-btn-primary"
                onClick={handleSubmit}
              >
                保存笔记
              </button>
              <button
                className="dn-btn dn-btn-share"
                onClick={handleShare}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                  <circle cx="18" cy="5" r="3" />
                  <circle cx="6" cy="12" r="3" />
                  <circle cx="18" cy="19" r="3" />
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                </svg>
                保存并分享
              </button>
            </div>
          </div>
        ) : notes.length === 0 ? (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">📖</div>
            <div className="chat-welcome-title">
              {user?.nickname ? `${user.nickname}，开始灵修吧` : '开始你的灵修之旅'}
            </div>
            <div className="chat-welcome-sub">
              记录每日的读经心得、祷告与神的带领，让灵命不断成长。
            </div>
            <button
              className="chat-suggestion-chip"
              onClick={() => setIsWriting(true)}
              style={{ marginTop: '20px' }}
            >
              ✍️ 写第一篇灵修笔记
            </button>
          </div>
        ) : (
          <div className="dn-list">
            {notes.map(note => (
              <div key={note.id} className="dn-card glass">
                <div className="dn-card-header">
                  <div className="dn-card-date">{formatDate(note.date)}</div>
                  {note.mood && (
                    <div className="dn-card-mood">
                      {MOODS.find(m => m.label === note.mood)?.emoji}
                      {note.mood}
                    </div>
                  )}
                </div>
                {note.scripture && (
                  <div className="dn-card-scripture">📖 {note.scripture}</div>
                )}
                <div className="dn-card-preview">
                  {note.reflection || note.observation || note.application || '（暂无内容）'}
                </div>
                <div className="dn-card-footer">
                  <span className={`dn-card-badge ${note.shared ? 'shared' : ''}`}>
                    {note.shared ? '🌐 已分享' : '🔒 私密'}
                  </span>
                  <button
                    className="dn-card-delete"
                    onClick={() => handleDelete(note.id)}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
