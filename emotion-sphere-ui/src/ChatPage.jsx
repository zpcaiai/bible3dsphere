import { useEffect, useState } from 'react'

const STORAGE_KEY_SHARED = 'devotion_notes_shared'
const STORAGE_KEY_PERSONAL = 'devotion_notes_personal'

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

function getSharedNotes() {
  try {
    const data = localStorage.getItem(STORAGE_KEY_SHARED)
    const notes = data ? JSON.parse(data) : []
    return notes.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
  } catch {
    return []
  }
}

function getPersonalNotes() {
  try {
    const data = localStorage.getItem(STORAGE_KEY_PERSONAL)
    const notes = data ? JSON.parse(data) : []
    return notes.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
  } catch {
    return []
  }
}

function savePersonalNote(note) {
  const notes = getPersonalNotes()
  const existingIndex = notes.findIndex(n => n.id === note.id)
  if (existingIndex >= 0) {
    notes[existingIndex] = note
  } else {
    notes.unshift(note)
  }
  localStorage.setItem(STORAGE_KEY_PERSONAL, JSON.stringify(notes))
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

export default function ChatPage({ user, onBack }) {
  const [sharedNotes, setSharedNotes] = useState([])
  const [personalNotes, setPersonalNotes] = useState([])
  const [selectedShared, setSelectedShared] = useState(null)
  const [selectedPersonal, setSelectedPersonal] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [saveStatus, setSaveStatus] = useState('')

  const [form, setForm] = useState({
    id: '',
    date: today(),
    scripture: '',
    observation: '',
    reflection: '',
    application: '',
    prayer: '',
    mood: '',
    shared: false,
    createdAt: null,
  })

  useEffect(() => {
    setSharedNotes(getSharedNotes())
    setPersonalNotes(getPersonalNotes())
  }, [])

  // Load note into form when selecting personal note
  useEffect(() => {
    if (selectedPersonal) {
      const note = personalNotes.find(n => n.id === selectedPersonal)
      if (note) {
        setForm({
          id: note.id,
          date: note.date || today(),
          scripture: note.scripture || '',
          observation: note.observation || '',
          reflection: note.reflection || '',
          application: note.application || '',
          prayer: note.prayer || '',
          mood: note.mood || '',
          shared: note.shared || false,
          createdAt: note.createdAt,
        })
        setIsEditing(false)
      }
    } else if (!selectedPersonal && !selectedShared) {
      // Reset form when creating new
      setForm({
        id: '',
        date: today(),
        scripture: '',
        observation: '',
        reflection: '',
        application: '',
        prayer: '',
        mood: '',
        shared: false,
        createdAt: null,
      })
      setIsEditing(true)
    }
  }, [selectedPersonal, personalNotes])

  function handleNewNote() {
    setSelectedShared(null)
    setSelectedPersonal(null)
    setForm({
      id: generateId(),
      date: today(),
      scripture: '',
      observation: '',
      reflection: '',
      application: '',
      prayer: '',
      mood: '',
      shared: false,
      createdAt: Date.now(),
    })
    setIsEditing(true)
  }

  function handleSave() {
    if (!form.scripture.trim() && !form.reflection.trim()) {
      alert('请至少填写经文和反思内容')
      return
    }

    setSaveStatus('saving')

    const note = {
      ...form,
      author: user?.nickname || '我',
      avatar: user?.avatar || null,
    }

    savePersonalNote(note)
    setPersonalNotes(getPersonalNotes())
    setSelectedPersonal(note.id)
    setIsEditing(false)
    setSaveStatus('saved')
    setTimeout(() => setSaveStatus(''), 2000)
  }

  function handleShare() {
    if (!form.scripture.trim() && !form.reflection.trim()) {
      alert('请至少填写经文和反思内容后再分享')
      return
    }

    const sharedNote = {
      ...form,
      id: form.id || generateId(),
      author: user?.nickname || '弟兄/姐妹',
      avatar: user?.avatar || null,
      shared: true,
      sharedAt: Date.now(),
      createdAt: form.createdAt || Date.now(),
    }

    // Save to shared
    const shared = getSharedNotes()
    const existingIndex = shared.findIndex(n => n.id === sharedNote.id)
    if (existingIndex >= 0) {
      shared[existingIndex] = sharedNote
    } else {
      shared.unshift(sharedNote)
    }
    localStorage.setItem(STORAGE_KEY_SHARED, JSON.stringify(shared.slice(0, 100)))
    setSharedNotes(getSharedNotes())

    // Update personal note
    savePersonalNote({ ...sharedNote, shared: true })
    setPersonalNotes(getPersonalNotes())

    setForm(prev => ({ ...prev, shared: true }))
    alert('已分享到灵修分享墙！')
  }

  function handleEdit() {
    setIsEditing(true)
  }

  function updateField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  function formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr + 'T00:00:00')
    const weekdays = ['日', '一', '二', '三', '四', '五', '六']
    return `${d.getMonth() + 1}月${d.getDate()}日 周${weekdays[d.getDay()]}`
  }

  function NoteCard({ note, isSelected, onClick, isShared = false }) {
    return (
      <div
        onClick={onClick}
        className={`note-card ${isSelected ? 'selected' : ''}`}
        style={{
          padding: '12px',
          borderRadius: '12px',
          background: isSelected ? 'rgba(0,122,255,0.15)' : 'rgba(255,255,255,0.05)',
          border: isSelected ? '1px solid rgba(0,122,255,0.3)' : '1px solid rgba(255,255,255,0.08)',
          cursor: 'pointer',
          marginBottom: '8px',
          transition: 'all 0.2s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          {isShared ? (
            note.avatar ? (
              <img src={note.avatar} alt={note.author} style={{ width: '24px', height: '24px', borderRadius: '50%' }} />
            ) : (
              <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'linear-gradient(135deg, #007aff, #5e5ce6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: '#fff' }}>
                {note.author?.[0] || '弟'}
              </div>
            )
          ) : null}
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)', fontWeight: 500 }}>
              {isShared ? note.author : formatDate(note.date)}
            </div>
          </div>
          {note.mood && <span style={{ fontSize: '11px' }}>{note.mood}</span>}
          {!isShared && note.shared && <span style={{ fontSize: '10px', color: '#34c759', background: 'rgba(52,199,89,0.15)', padding: '2px 6px', borderRadius: '4px' }}>已分享</span>}
        </div>
        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.9)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {note.scripture || note.reflection || '（无标题）'}
        </div>
      </div>
    )
  }

  function NoteDetail({ note, isShared }) {
    if (!note) return null

    return (
      <div style={{ padding: '20px', height: '100%', overflowY: 'auto' }}>
        <div style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            {isShared && note.avatar ? (
              <img src={note.avatar} alt={note.author} style={{ width: '40px', height: '40px', borderRadius: '50%' }} />
            ) : isShared ? (
              <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'linear-gradient(135deg, #007aff, #5e5ce6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', color: '#fff' }}>
                {note.author?.[0] || '弟'}
              </div>
            ) : null}
            <div>
              {isShared && <div style={{ fontSize: '16px', fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>{note.author}</div>}
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>{formatDate(note.date)}</div>
            </div>
            {note.mood && <span style={{ marginLeft: 'auto', fontSize: '14px', background: 'rgba(255,255,255,0.1)', padding: '4px 12px', borderRadius: '12px', color: 'rgba(255,255,255,0.7)' }}>{note.mood}</span>}
          </div>
        </div>

        {note.scripture && (
          <div style={{ marginBottom: '20px', padding: '16px', background: 'rgba(0,122,255,0.1)', borderRadius: '12px', borderLeft: '3px solid rgba(0,122,255,0.5)' }}>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>📖 经文</div>
            <div style={{ fontSize: '15px', color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>{note.scripture}</div>
          </div>
        )}

        {note.observation && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'rgba(255,255,255,0.8)', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px' }}>👁️ 观察</div>
            <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{note.observation}</div>
          </div>
        )}

        {note.reflection && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'rgba(255,255,255,0.8)', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px' }}>💭 反思</div>
            <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{note.reflection}</div>
          </div>
        )}

        {note.application && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'rgba(255,255,255,0.8)', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px' }}>✨ 应用</div>
            <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{note.application}</div>
          </div>
        )}

        {note.prayer && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'rgba(255,255,255,0.8)', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px' }}>🙏 祷告</div>
            <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: 1.7, whiteSpace: 'pre-wrap', fontStyle: 'italic' }}>{note.prayer}</div>
          </div>
        )}

        {!isShared && (
          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <button onClick={handleEdit} className="primary-btn" style={{ flex: 1 }}>编辑</button>
            <button onClick={handleShare} className="primary-btn" style={{ flex: 1, background: form.shared ? '#34c759' : undefined }}>{form.shared ? '已分享' : '分享'}</button>
          </div>
        )}
      </div>
    )
  }

  function EditForm() {
    return (
      <div style={{ padding: '20px', height: '100%', overflowY: 'auto' }}>
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>日期</label>
          <input
            type="date"
            value={form.date}
            onChange={e => updateField('date', e.target.value)}
            style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)' }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>心情</label>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {MOODS.map(m => (
              <button
                key={m.label}
                onClick={() => updateField('mood', m.emoji)}
                style={{
                  padding: '8px 12px',
                  borderRadius: '20px',
                  border: 'none',
                  background: form.mood === m.emoji ? 'rgba(0,122,255,0.3)' : 'rgba(255,255,255,0.05)',
                  color: form.mood === m.emoji ? '#fff' : 'rgba(255,255,255,0.7)',
                  cursor: 'pointer',
                  fontSize: '13px',
                }}
              >
                {m.emoji} {m.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>📖 经文</label>
          <input
            type="text"
            value={form.scripture}
            onChange={e => updateField('scripture', e.target.value)}
            placeholder="例：约翰福音 3:16"
            style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)' }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>👁️ 观察（经文说了什么）</label>
          <textarea
            value={form.observation}
            onChange={e => updateField('observation', e.target.value)}
            rows={3}
            style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', resize: 'vertical' }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>💭 反思（对我有什么意义）</label>
          <textarea
            value={form.reflection}
            onChange={e => updateField('reflection', e.target.value)}
            rows={4}
            style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', resize: 'vertical' }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>✨ 应用（我该如何行动）</label>
          <textarea
            value={form.application}
            onChange={e => updateField('application', e.target.value)}
            rows={3}
            style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', resize: 'vertical' }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '13px', color: 'rgba(255,255,255,0.6)', marginBottom: '6px' }}>🙏 祷告</label>
          <textarea
            value={form.prayer}
            onChange={e => updateField('prayer', e.target.value)}
            rows={3}
            placeholder="写下你的祷告..."
            style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', resize: 'vertical' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleSave}
            disabled={saveStatus === 'saving'}
            style={{
              flex: 1,
              padding: '12px',
              borderRadius: '10px',
              border: 'none',
              background: saveStatus === 'saved' ? '#34c759' : 'linear-gradient(135deg, #007aff, #5e5ce6)',
              color: '#fff',
              fontSize: '15px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {saveStatus === 'saving' ? '保存中...' : saveStatus === 'saved' ? '✓ 已保存' : '保存'}
          </button>
          <button
            onClick={handleShare}
            style={{
              flex: 1,
              padding: '12px',
              borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.2)',
              background: 'transparent',
              color: 'rgba(255,255,255,0.8)',
              fontSize: '15px',
              cursor: 'pointer',
            }}
          >
            {form.shared ? '已分享' : '分享'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-page" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header className="chat-header">
        <button className="checkin-back-btn" onClick={onBack} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="chat-header-center">
          <div className="chat-title">灵修分享</div>
          <div className="chat-subtitle">弟兄姐妹的灵修见证与分享</div>
        </div>
        <button className="chat-new-btn" onClick={handleNewNote} title="新建日记">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </header>

      {/* Main Content - Two Columns */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left Column - Shared Notes */}
        <div style={{ width: '50%', borderRight: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>📖 灵修分享墙</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '2px' }}>{sharedNotes.length} 篇分享</div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            {sharedNotes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: 'rgba(255,255,255,0.4)' }}>
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>📖</div>
                <div style={{ fontSize: '14px' }}>暂无分享的灵修笔记</div>
                <div style={{ fontSize: '12px', marginTop: '8px' }}>成为第一位分享者吧</div>
              </div>
            ) : (
              sharedNotes.map(note => (
                <NoteCard
                  key={note.id}
                  note={note}
                  isSelected={selectedShared === note.id}
                  onClick={() => {
                    setSelectedShared(note.id)
                    setSelectedPersonal(null)
                    setIsEditing(false)
                  }}
                  isShared={true}
                />
              ))
            )}
          </div>
          {/* Detail View for Shared */}
          {selectedShared && (
            <div style={{ height: '50%', borderTop: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.15)' }}>
              <NoteDetail note={sharedNotes.find(n => n.id === selectedShared)} isShared={true} />
            </div>
          )}
        </div>

        {/* Right Column - Personal Notes */}
        <div style={{ width: '50%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>✍️ 我的灵修日记</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '2px' }}>{personalNotes.length} 篇日记</div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            {personalNotes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: 'rgba(255,255,255,0.4)' }}>
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>✍️</div>
                <div style={{ fontSize: '14px' }}>还没有日记</div>
                <div style={{ fontSize: '12px', marginTop: '8px' }}>点击右上角 + 开始记录</div>
              </div>
            ) : (
              personalNotes.map(note => (
                <NoteCard
                  key={note.id}
                  note={note}
                  isSelected={selectedPersonal === note.id}
                  onClick={() => {
                    setSelectedPersonal(note.id)
                    setSelectedShared(null)
                  }}
                  isShared={false}
                />
              ))
            )}
          </div>
          {/* Edit/Detail View for Personal */}
          <div style={{ height: '50%', borderTop: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.15)' }}>
            {isEditing ? <EditForm /> : selectedPersonal ? <NoteDetail note={personalNotes.find(n => n.id === selectedPersonal)} isShared={false} /> : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'rgba(255,255,255,0.4)' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>✍️</div>
                <div style={{ fontSize: '14px' }}>选择一篇日记查看或点击 + 新建</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
