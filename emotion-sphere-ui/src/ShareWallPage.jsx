import { useEffect, useState } from 'react'

const STORAGE_KEY = 'devotion_notes_shared'

function getSharedNotes() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    const notes = data ? JSON.parse(data) : []
    return notes.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
  } catch {
    return []
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

export default function ShareWallPage({ user, onBack }) {
  const [notes, setNotes] = useState([])
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    setNotes(getSharedNotes())
  }, [])

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
          <div style={{ fontSize: '18px', fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>🌟 分享墙</div>
          <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginTop: '2px' }}>
            {notes.length} 篇分享
          </div>
        </div>
        <div style={{ width: '36px' }} />
      </header>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Note List */}
        <div style={{ width: selected ? '40%' : '100%', borderRight: selected ? '1px solid rgba(255,255,255,0.1)' : 'none', overflowY: 'auto', padding: '16px' }}>
          {notes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'rgba(255,255,255,0.4)' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📝</div>
              <div style={{ fontSize: '15px' }}>暂无分享</div>
              <div style={{ fontSize: '13px', marginTop: '8px', opacity: 0.7 }}>在日记页面分享你的灵修心得</div>
            </div>
          ) : (
            notes.map(note => (
              <div
                key={note.id}
                onClick={() => setSelected(note.id)}
                style={{
                  padding: '16px',
                  marginBottom: '12px',
                  background: selected === note.id ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  border: selected === note.id ? '1px solid rgba(255,255,255,0.2)' : '1px solid transparent',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                  {note.avatar ? (
                    <img src={note.avatar} alt="" style={{ width: '32px', height: '32px', borderRadius: '50%', objectFit: 'cover' }} />
                  ) : (
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>
                      {note.author?.[0] || '?'}
                    </div>
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: 500, color: 'rgba(255,255,255,0.9)' }}>{note.author || '匿名'}</div>
                    <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>{formatDate(note.date)} {note.mood}</div>
                  </div>
                </div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: 'rgba(255,255,255,0.95)', marginBottom: '6px' }}>{note.scripture}</div>
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', lineHeight: '1.5', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {note.reflection || note.observation || '暂无内容'}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Detail View */}
        {selected && selectedNote && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              {selectedNote.avatar ? (
                <img src={selectedNote.avatar} alt="" style={{ width: '44px', height: '44px', borderRadius: '50%', objectFit: 'cover' }} />
              ) : (
                <div style={{ width: '44px', height: '44px', borderRadius: '50%', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px' }}>
                  {selectedNote.author?.[0] || '?'}
                </div>
              )}
              <div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>{selectedNote.author || '匿名'}</div>
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>{formatDate(selectedNote.date)} {selectedNote.mood}</div>
              </div>
            </div>

            <div style={{ fontSize: '20px', fontWeight: 700, color: 'rgba(255,255,255,0.95)', marginBottom: '12px' }}>{selectedNote.scripture}</div>

            {selectedNote.observation && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>👁️ 观察</div>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>{selectedNote.observation}</div>
              </div>
            )}

            {selectedNote.reflection && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>💭 反思</div>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>{selectedNote.reflection}</div>
              </div>
            )}

            {selectedNote.application && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>✨ 应用</div>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>{selectedNote.application}</div>
              </div>
            )}

            {selectedNote.prayer && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>🙏 祷告</div>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.85)', lineHeight: '1.7', whiteSpace: 'pre-wrap', fontStyle: 'italic' }}>{selectedNote.prayer}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
