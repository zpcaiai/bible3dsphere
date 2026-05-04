import { useEffect, useState } from 'react'

const STORAGE_KEY = 'devotion_notes_personal'

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

function getNotes() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    const notes = data ? JSON.parse(data) : []
    return notes.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
  } catch {
    return []
  }
}

function saveNote(note) {
  const notes = getNotes()
  const existingIndex = notes.findIndex(n => n.id === note.id)
  if (existingIndex >= 0) {
    notes[existingIndex] = note
  } else {
    notes.unshift(note)
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(notes))
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

export default function PersonalDevotionPage({ user, onBack }) {
  const [notes, setNotes] = useState([])
  const [selected, setSelected] = useState(null)
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
    setNotes(getNotes())
  }, [])

  useEffect(() => {
    if (selected) {
      const note = notes.find(n => n.id === selected)
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
    } else {
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
  }, [selected])

  function handleNew() {
    setSelected(null)
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

    saveNote(note)
    setNotes(getNotes())
    setSelected(note.id)
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

    const STORAGE_KEY_SHARED = 'devotion_notes_shared'
    const shared = JSON.parse(localStorage.getItem(STORAGE_KEY_SHARED) || '[]')
    const existingIndex = shared.findIndex(n => n.id === sharedNote.id)
    if (existingIndex >= 0) {
      shared[existingIndex] = sharedNote
    } else {
      shared.unshift(sharedNote)
    }
    localStorage.setItem(STORAGE_KEY_SHARED, JSON.stringify(shared.slice(0, 100)))

    saveNote({ ...sharedNote, shared: true })
    setNotes(getNotes())
    setForm(prev => ({ ...prev, shared: true }))
    alert('已分享到分享墙！')
  }

  function handleShareFromList(note) {
    const STORAGE_KEY_SHARED = 'devotion_notes_shared'
    
    if (note.shared) {
      // Cancel share
      const shared = JSON.parse(localStorage.getItem(STORAGE_KEY_SHARED) || '[]')
      const filtered = shared.filter(n => n.id !== note.id)
      localStorage.setItem(STORAGE_KEY_SHARED, JSON.stringify(filtered))
      
      const updatedNote = { ...note, shared: false }
      saveNote(updatedNote)
      setNotes(getNotes())
      if (selected === note.id) {
        setForm(prev => ({ ...prev, shared: false }))
      }
    } else {
      // Share
      if (!note.scripture?.trim() && !note.reflection?.trim()) {
        alert('请至少填写经文和反思内容后再分享')
        return
      }

      const sharedNote = {
        ...note,
        author: user?.nickname || '弟兄/姐妹',
        avatar: user?.avatar || null,
        shared: true,
        sharedAt: Date.now(),
      }

      const shared = JSON.parse(localStorage.getItem(STORAGE_KEY_SHARED) || '[]')
      const existingIndex = shared.findIndex(n => n.id === sharedNote.id)
      if (existingIndex >= 0) {
        shared[existingIndex] = sharedNote
      } else {
        shared.unshift(sharedNote)
      }
      localStorage.setItem(STORAGE_KEY_SHARED, JSON.stringify(shared.slice(0, 100)))

      saveNote(sharedNote)
      setNotes(getNotes())
      if (selected === note.id) {
        setForm(prev => ({ ...prev, shared: true }))
      }
    }
  }

  function updateField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  function handleDelete(id) {
    if (!window.confirm('确定删除这篇日记？')) return
    const filtered = notes.filter(n => n.id !== id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
    setNotes(filtered)
    if (selected === id) {
      setSelected(null)
    }
  }

  const selectedNote = notes.find(n => n.id === selected)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }}>
      {/* Header */}
      <header style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.7)', cursor: 'pointer', padding: '8px' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>📔 我的日记</div>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginTop: '2px' }}>
            {notes.length} 篇日记
          </div>
        </div>
        <button 
          onClick={handleNew}
          style={{ 
            background: 'rgba(255,255,255,0.1)', 
            border: 'none', 
            color: 'rgba(255,255,255,0.9)', 
            cursor: 'pointer', 
            padding: '8px 12px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px'
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建
        </button>
      </header>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Note List */}
        <div style={{ width: selected ? '35%' : '100%', borderRight: selected ? '1px solid rgba(255,255,255,0.1)' : 'none', overflowY: 'auto', padding: '12px' }}>
          {notes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'rgba(255,255,255,0.4)' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📔</div>
              <div style={{ fontSize: '15px' }}>还没有日记</div>
              <div style={{ fontSize: '13px', marginTop: '8px', opacity: 0.7 }}>点击右上角新建</div>
            </div>
          ) : (
            notes.map(note => (
              <div
                key={note.id}
                onClick={() => setSelected(note.id)}
                style={{
                  padding: '14px',
                  marginBottom: '10px',
                  background: selected === note.id ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  border: selected === note.id ? '1px solid rgba(255,255,255,0.2)' : '1px solid transparent',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>{formatDate(note.date)} {note.mood}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleShareFromList(note)
                    }}
                    style={{
                      padding: '4px 10px',
                      fontSize: '11px',
                      background: note.shared ? 'rgba(239, 68, 68, 0.2)' : 'rgba(74, 222, 128, 0.2)',
                      border: note.shared ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(74, 222, 128, 0.4)',
                      borderRadius: '12px',
                      color: note.shared ? '#fca5a5' : '#86efac',
                      cursor: 'pointer',
                    }}
                  >
                    {note.shared ? '取消' : '分享'}
                  </button>
                </div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: 'rgba(255,255,255,0.95)', marginBottom: '4px' }}>{note.scripture || '（无经文）'}</div>
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', lineHeight: '1.4', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {note.reflection || note.observation || '暂无内容'}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Detail / Edit View */}
        {selected ? (
          isEditing ? (
            // Edit Form
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
              <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                <button 
                  onClick={handleSave}
                  style={{ 
                    flex: 1, 
                    padding: '10px', 
                    background: 'rgba(255,255,255,0.15)', 
                    border: '1px solid rgba(255,255,255,0.2)', 
                    borderRadius: '8px', 
                    color: 'rgba(255,255,255,0.9)',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {saveStatus === 'saving' ? '保存中...' : saveStatus === 'saved' ? '已保存 ✓' : '保存'}
                </button>
                <button 
                  onClick={() => setIsEditing(false)}
                  style={{ 
                    padding: '10px 16px', 
                    background: 'rgba(255,255,255,0.05)', 
                    border: '1px solid rgba(255,255,255,0.1)', 
                    borderRadius: '8px', 
                    color: 'rgba(255,255,255,0.6)',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  取消
                </button>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>日期</label>
                <input
                  type="date"
                  value={form.date}
                  onChange={e => updateField('date', e.target.value)}
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px' }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>心情</label>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {MOODS.map(m => (
                    <button
                      key={m.label}
                      onClick={() => updateField('mood', form.mood === m.emoji ? '' : m.emoji)}
                      style={{
                        padding: '8px 12px',
                        background: form.mood === m.emoji ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.05)',
                        border: form.mood === m.emoji ? '1px solid rgba(255,255,255,0.4)' : '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '20px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        color: 'rgba(255,255,255,0.9)',
                      }}
                    >
                      {m.emoji} {m.label}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>📖 经文</label>
                <input
                  type="text"
                  value={form.scripture}
                  onChange={e => updateField('scripture', e.target.value)}
                  placeholder="例：约翰福音 3:16"
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px' }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>👁️ 观察（经文说了什么）</label>
                <textarea
                  value={form.observation}
                  onChange={e => updateField('observation', e.target.value)}
                  rows={3}
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>💭 反思（对我有什么意义）</label>
                <textarea
                  value={form.reflection}
                  onChange={e => updateField('reflection', e.target.value)}
                  rows={4}
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>✨ 应用（我该如何行动）</label>
                <textarea
                  value={form.application}
                  onChange={e => updateField('application', e.target.value)}
                  rows={3}
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>🙏 祷告</label>
                <textarea
                  value={form.prayer}
                  onChange={e => updateField('prayer', e.target.value)}
                  rows={3}
                  placeholder="写下你的祷告..."
                  style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
                />
              </div>
            </div>
          ) : (
            // View Mode
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
              <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                <button 
                  onClick={() => setIsEditing(true)}
                  style={{ 
                    flex: 1, 
                    padding: '10px', 
                    background: 'rgba(255,255,255,0.1)', 
                    border: '1px solid rgba(255,255,255,0.2)', 
                    borderRadius: '8px', 
                    color: 'rgba(255,255,255,0.9)',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  ✏️ 编辑
                </button>
                {!form.shared && (
                  <button 
                    onClick={handleShare}
                    style={{ 
                      padding: '10px 16px', 
                      background: 'rgba(74, 222, 128, 0.15)', 
                      border: '1px solid rgba(74, 222, 128, 0.3)', 
                      borderRadius: '8px', 
                      color: '#4ade80',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    🌟 分享
                  </button>
                )}
                <button 
                  onClick={() => handleDelete(selected)}
                  style={{ 
                    padding: '10px 16px', 
                    background: 'rgba(239, 68, 68, 0.15)', 
                    border: '1px solid rgba(239, 68, 68, 0.3)', 
                    borderRadius: '8px', 
                    color: '#ef4444',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  🗑️
                </button>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>{formatDate(selectedNote?.date)} {selectedNote?.mood}</span>
              </div>

              <div style={{ fontSize: '20px', fontWeight: 700, color: 'rgba(255,255,255,0.95)', marginBottom: '20px' }}>{selectedNote?.scripture}</div>

              {selectedNote?.observation && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>👁️ 观察</div>
                  <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>{selectedNote.observation}</div>
                </div>
              )}

              {selectedNote?.reflection && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>💭 反思</div>
                  <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>{selectedNote.reflection}</div>
                </div>
              )}

              {selectedNote?.application && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>✨ 应用</div>
                  <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>{selectedNote.application}</div>
                </div>
              )}

              {selectedNote?.prayer && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>🙏 祷告</div>
                  <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap', fontStyle: 'italic' }}>{selectedNote.prayer}</div>
                </div>
              )}
            </div>
          )
        ) : (
          // New Note Form (when no selection)
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            <div style={{ marginBottom: '16px' }}>
              <button 
                onClick={handleSave}
                style={{ 
                  width: '100%',
                  padding: '12px', 
                  background: 'rgba(255,255,255,0.15)', 
                  border: '1px solid rgba(255,255,255,0.2)', 
                  borderRadius: '8px', 
                  color: 'rgba(255,255,255,0.9)',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                {saveStatus === 'saving' ? '保存中...' : saveStatus === 'saved' ? '已保存 ✓' : '💾 保存日记'}
              </button>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>日期</label>
              <input
                type="date"
                value={form.date}
                onChange={e => updateField('date', e.target.value)}
                style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px' }}
              />
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>心情</label>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {MOODS.map(m => (
                  <button
                    key={m.label}
                    onClick={() => updateField('mood', form.mood === m.emoji ? '' : m.emoji)}
                    style={{
                      padding: '8px 12px',
                      background: form.mood === m.emoji ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.05)',
                      border: form.mood === m.emoji ? '1px solid rgba(255,255,255,0.4)' : '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '20px',
                      cursor: 'pointer',
                      fontSize: '13px',
                      color: 'rgba(255,255,255,0.9)',
                    }}
                  >
                    {m.emoji} {m.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>📖 经文</label>
              <input
                type="text"
                value={form.scripture}
                onChange={e => updateField('scripture', e.target.value)}
                placeholder="例：约翰福音 3:16"
                style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px' }}
              />
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>👁️ 观察（经文说了什么）</label>
              <textarea
                value={form.observation}
                onChange={e => updateField('observation', e.target.value)}
                rows={3}
                style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
              />
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>💭 反思（对我有什么意义）</label>
              <textarea
                value={form.reflection}
                onChange={e => updateField('reflection', e.target.value)}
                rows={4}
                style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
              />
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>✨ 应用（我该如何行动）</label>
              <textarea
                value={form.application}
                onChange={e => updateField('application', e.target.value)}
                rows={3}
                style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>🙏 祷告</label>
              <textarea
                value={form.prayer}
                onChange={e => updateField('prayer', e.target.value)}
                rows={3}
                placeholder="写下你的祷告..."
                style={{ width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'rgba(255,255,255,0.9)', fontSize: '14px', resize: 'vertical' }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
