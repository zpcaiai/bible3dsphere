import { useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import usePullToRefresh from './hooks/usePullToRefresh'
import { escapeHtml, escapeHtmlWithBr } from './sanitize'
import { fetchSharedNotes, toggleShareNote } from './api'
import { getToken } from './auth'

// 读取旧的 localStorage 分享记录（来自 ChatPage / DevotionNotePage / SermonJournalPage）
function getLegacySharedNotes() {
  try {
    const data = localStorage.getItem('devotion_notes_shared')
    const notes = data ? JSON.parse(data) : []
    // 标记来源并转换为 ShareWallPage 所期望的格式
    return notes
      .filter(n => n.shared !== false)
      .map(n => ({
        id: n.id || String(n.createdAt || Date.now()),
        email: '',
        date: n.date || '',
        scripture: n.scripture || '',
        observation: n.observation || '',
        reflection: n.reflection || '',
        application: n.application || '',
        prayer: n.prayer || '',
        mood: n.mood || '',
        shared: true,
        author: n.author || '匿名',
        avatar: n.avatar || '',
        createdAt: n.createdAt ? new Date(n.createdAt).toISOString() : null,
        updatedAt: n.sharedAt ? new Date(n.sharedAt).toISOString() : null,
        is_own: false,
        _source: 'local',
      }))
  } catch {
    return []
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function formatDateTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function exportSelectedToTxt(note) {
  if (!note) return
  let content = `情感星球 - 灵修分享\n`
  content += `作者：${note.author || '匿名'}\n`
  content += `日期：${formatDateTime(note.date)}\n`
  if (note.mood) content += `心情：${note.mood}\n`
  content += `\n━━━━━━━━━━━━━━━━━━━━━━━\n  经文\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
  content += `${note.scripture || '未记录'}\n\n`
  
  if (note.observation) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  观察\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.observation}\n\n`
  }
  if (note.reflection) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  反思\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.reflection}\n\n`
  }
  if (note.application) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  应用\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.application}\n\n`
  }
  if (note.prayer) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  祷告\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.prayer}\n\n`
  }
  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const title = (note.scripture || '灵修分享').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
  a.download = `${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportSelectedToPdf(note) {
  if (!note) return
  
  const container = document.createElement('div')
  container.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 794px; background: #0d0d1a; padding: 40px; font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; line-height: 1.8; color: #ffffff;'
  document.body.appendChild(container)
  
  let content = `
    <div style="text-align: center; margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px;">
      <h1 style="color: #007aff; font-size: 22px; margin: 0 0 10px 0;">情感星球 - 灵修分享</h1>
      <div style="color: rgba(255,255,255,0.5); font-size: 13px;">
        作者：${escapeHtml(note.author) || '匿名'} | 日期：${formatDateTime(note.date)}${note.mood ? ' | ' + escapeHtml(note.mood) : ''}
      </div>
    </div>
    
    <div style="margin: 20px 0;">
      <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">经文</div>
      <div style="font-size: 16px; color: #ffffff; font-weight: 600; margin: 12px 0;">${escapeHtml(note.scripture) || '未记录'}</div>
    </div>
  `
  
  if (note.observation) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">观察</div>
        <div style="background: rgba(255,255,255,0.05); padding: 14px; border-radius: 8px; color: rgba(255,255,255,0.88); white-space: pre-wrap;">${escapeHtmlWithBr(note.observation)}</div>
      </div>
    `
  }
  if (note.reflection) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">反思</div>
        <div style="background: rgba(255,255,255,0.05); padding: 14px; border-radius: 8px; color: rgba(255,255,255,0.88); white-space: pre-wrap;">${escapeHtmlWithBr(note.reflection)}</div>
      </div>
    `
  }
  if (note.application) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">应用</div>
        <div style="background: rgba(48,209,88,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(48,209,88,0.25); color: #30d158; white-space: pre-wrap;">${escapeHtmlWithBr(note.application)}</div>
      </div>
    `
  }
  if (note.prayer) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">祷告</div>
        <div style="background: rgba(255,159,10,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(255,159,10,0.25); color: #ff9f0a; white-space: pre-wrap; font-style: italic;">${escapeHtmlWithBr(note.prayer)}</div>
      </div>
    `
  }
  
  container.innerHTML = content
  
  try {
    const canvas = await html2canvas(container, {
      scale: 1,
      useCORS: true,
      logging: false,
      backgroundColor: '#0d0d1a'
    })
    
    const imgData = canvas.toDataURL('image/jpeg', 0.85)
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pdfWidth = pdf.internal.pageSize.getWidth()
    const pdfHeight = pdf.internal.pageSize.getHeight()
    const imgWidth = canvas.width
    const imgHeight = canvas.height
    const scaledWidth = pdfWidth - 20
    const scaledHeight = (imgHeight * scaledWidth) / imgWidth
    
    let heightLeft = scaledHeight
    let position = 10
    
    pdf.addImage(imgData, 'JPEG', 10, position, scaledWidth, scaledHeight)
    heightLeft -= (pdfHeight - 20)
    
    while (heightLeft > 0) {
      position = heightLeft - scaledHeight + 10
      pdf.addPage()
      pdf.addImage(imgData, 'JPEG', 10, position, scaledWidth, scaledHeight)
      heightLeft -= (pdfHeight - 20)
    }
    
    const title = (note.scripture || '灵修分享').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
    pdf.save(`${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) {
    console.error('PDF generation failed:', err)
    alert('PDF 生成失败，请重试')
  } finally {
    document.body.removeChild(container)
  }
}

const MAX_LINES = 10
const LINE_HEIGHT = 1.6
const FONT_SIZE = 13
const COLLAPSED_HEIGHT = MAX_LINES * FONT_SIZE * LINE_HEIGHT

export default function ShareWallPage({ user, onBack }) {
  const [notes, setNotes] = useState([])
  const [selected, setSelected] = useState(null)
  const [expandedCards, setExpandedCards] = useState({})
  const [loading, setLoading] = useState(true)
  const listRef = useRef(null)

  function toggleExpand(id) {
    setExpandedCards(prev => ({ ...prev, [id]: !prev[id] }))
  }

  async function loadNotes() {
    try {
      setLoading(true)
      const token = getToken()

      // 1. 先读 localStorage 旧数据（来自 ChatPage/DevotionNotePage/SermonJournalPage）
      const legacyNotes = getLegacySharedNotes()

      // 2. 再读后端数据库
      let apiNotes = []
      try {
        const data = await fetchSharedNotes(token)
        apiNotes = data.items || []
      } catch (apiErr) {
        console.warn('[sharewall] API fetch failed, falling back to local only:', apiErr)
      }

      // 3. 合并去重：后端数据优先（id 以后端为准），旧 localStorage 补充
      const seenIds = new Set(apiNotes.map(n => n.id))
      const merged = [
        ...apiNotes,
        ...legacyNotes.filter(n => !seenIds.has(n.id)),
      ]

      // 4. 按 updatedAt / createdAt 降序排列
      merged.sort((a, b) => {
        const ta = new Date(a.updatedAt || a.createdAt || 0).getTime()
        const tb = new Date(b.updatedAt || b.createdAt || 0).getTime()
        return tb - ta
      })

      console.log(`[sharewall] loaded ${apiNotes.length} from API + ${legacyNotes.length} legacy = ${merged.length} total`)
      setNotes(merged)
    } catch (err) {
      console.error('[sharewall] load error:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleUnshare(noteId) {
    const note = notes.find(n => n.id === noteId)
    // 旧 localStorage 数据：只从本地删除
    if (note?._source === 'local') {
      try {
        const raw = localStorage.getItem('devotion_notes_shared')
        const arr = raw ? JSON.parse(raw) : []
        const updated = arr.filter(n => n.id !== noteId)
        localStorage.setItem('devotion_notes_shared', JSON.stringify(updated))
        setNotes(prev => prev.filter(n => n.id !== noteId))
        if (selected === noteId) setSelected(null)
      } catch (err) {
        console.error('[sharewall] local unshare error:', err)
      }
      return
    }
    // 后端数据：调用 API
    try {
      const token = getToken()
      await toggleShareNote(noteId, token)
      setNotes(prev => prev.filter(n => n.id !== noteId))
      if (selected === noteId) setSelected(null)
    } catch (err) {
      alert(err.message || '操作失败')
    }
  }

  useEffect(() => {
    if (user) loadNotes()
  }, [user])

  const selectedNote = notes.find(n => n.id === selected)
  const { pulling, refreshing, indicatorStyle, indicatorText } = usePullToRefresh(loadNotes, listRef)

  // If not logged in, show login prompt
  if (!user) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>🌟</div>
        <div style={{ fontSize: '18px', color: 'rgba(255,255,255,0.9)', marginBottom: '8px' }}>分享墙</div>
        <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', marginBottom: '24px' }}>登录后查看分享墙内容</div>
        <button onClick={onBack} style={{ padding: '10px 24px', background: 'rgba(0,122,255,0.3)', border: '1px solid rgba(0,122,255,0.5)', borderRadius: '8px', color: '#5ac8fa', fontSize: '14px', cursor: 'pointer' }}>
          ← 返回
        </button>
      </div>
    )
  }

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
        <div ref={listRef} style={{ width: selected ? '40%' : '100%', borderRight: selected ? '1px solid rgba(255,255,255,0.1)' : 'none', overflowY: 'auto', overflowX: 'hidden', padding: '16px', position: 'relative' }}>
          <div style={indicatorStyle}>{indicatorText}</div>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'rgba(255,255,255,0.4)' }}>
              <div style={{ fontSize: '15px' }}>加载中...</div>
            </div>
          ) : notes.length === 0 ? (
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
                {(() => {
                  const text = note.reflection || note.observation || '暂无内容'
                  const lines = text.split('\n')
                  const isLong = lines.length > MAX_LINES || text.length > MAX_LINES * 40
                  const expanded = expandedCards[note.id]
                  return (
                    <>
                      <div style={{
                        fontSize: `${FONT_SIZE}px`,
                        color: 'rgba(255,255,255,0.7)',
                        lineHeight: `${LINE_HEIGHT}`,
                        whiteSpace: 'pre-wrap',
                        overflow: 'hidden',
                        maxHeight: (!expanded && isLong) ? `${COLLAPSED_HEIGHT}px` : 'none',
                        position: 'relative',
                      }}>
                        {text}
                        {!expanded && isLong && (
                          <div style={{
                            position: 'absolute', bottom: 0, left: 0, right: 0, height: '48px',
                            background: 'linear-gradient(transparent, rgba(26,26,46,0.95))',
                          }} />
                        )}
                      </div>
                      {isLong && (
                        <button
                          onClick={e => { e.stopPropagation(); toggleExpand(note.id) }}
                          style={{
                            background: 'none', border: 'none', padding: '6px 0', marginTop: '4px',
                            color: '#5ac8fa', fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit',
                          }}
                        >
                          {expanded ? '收起 ▲' : '更多 ▼'}
                        </button>
                      )}
                    </>
                  )
                })()}
              </div>
            ))
          )}
        </div>

        {/* Detail View */}
        {selected && selectedNote && (
          <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: '20px' }}>
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

            {/* Action Buttons */}
            <div style={{ marginTop: '30px', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              {selectedNote.is_own && (
                <button
                  onClick={() => handleUnshare(selectedNote.id)}
                  style={{
                    width: '100%',
                    padding: '10px 16px',
                    marginBottom: '8px',
                    background: 'rgba(255,59,48,0.15)',
                    border: '1px solid rgba(255,59,48,0.4)',
                    borderRadius: '8px',
                    color: '#ff6b6b',
                    fontSize: '13px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  ↩️ 撤回
                </button>
              )}
              <button
                onClick={() => exportSelectedToTxt(selectedNote)}
                style={{
                  flex: 1,
                  padding: '10px 16px',
                  background: 'rgba(255,255,255,0.1)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  borderRadius: '8px',
                  color: 'rgba(255,255,255,0.9)',
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                TXT
              </button>
              <button
                onClick={() => exportSelectedToPdf(selectedNote)}
                style={{
                  flex: 1,
                  padding: '10px 16px',
                  background: 'rgba(0,122,255,0.2)',
                  border: '1px solid rgba(0,122,255,0.4)',
                  borderRadius: '8px',
                  color: '#5ac8fa',
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <path d="M9 15l3 3 3-3"/>
                  <path d="M12 18V9"/>
                </svg>
                PDF
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
