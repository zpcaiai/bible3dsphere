import { useCallback, useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import usePullToRefresh from './hooks/usePullToRefresh'
import { escapeHtml, escapeHtmlWithBr } from './sanitize'
import { fetchSharedNotes, toggleShareNote, amenSharedNote } from './api'
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

function exportSelectedToTxt(note) {
  if (!note) return
  let content = `情感星球 - 灵修分享\n`
  content += `作者：${note.author || '匿名'}\n`
  content += `日期：${formatDate(note.date)}\n`
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
        作者：${escapeHtml(note.author) || '匿名'} | 日期：${formatDate(note.date)}${note.mood ? ' | ' + escapeHtml(note.mood) : ''}
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

const MAX_LINES = 8
const LINE_HEIGHT = 1.6
const FONT_SIZE = 13
const COLLAPSED_HEIGHT = MAX_LINES * FONT_SIZE * LINE_HEIGHT

function NoteDetailOverlay({ note, onClose, onUnshare, onAmen, token }) {
  const [amenLoading, setAmenLoading] = useState(false)
  const [amenCount, setAmenCount] = useState(note.amen_count || 0)
  const [amenByMe, setAmenByMe] = useState(note.amen_by_me || false)

  async function handleAmen() {
    if (amenLoading || !token) return
    setAmenLoading(true)
    try {
      const res = await amenSharedNote(note.id, token)
      setAmenCount(res.amen_count)
      setAmenByMe(res.amen_by_me)
      onAmen(note.id, res.amen_count, res.amen_by_me)
    } catch (e) {
      console.warn('[amen]', e)
    } finally {
      setAmenLoading(false)
    }
  }

  async function handleUnshare() {
    if (!window.confirm('确定要从分享墙撤回这篇内容吗？')) return
    onUnshare(note.id)
    onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      display: 'flex', flexDirection: 'column', overflowY: 'auto',
    }}>
      {/* Detail header */}
      <div style={{ position: 'sticky', top: 0, zIndex: 1, background: 'rgba(22,33,62,0.95)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 8, color: '#fff', padding: '6px 12px', cursor: 'pointer', fontSize: 13 }}>← 返回</button>
        <div style={{ flex: 1 }} />
        {/* Amen button in header */}
        <button
          onClick={handleAmen}
          disabled={amenLoading}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 14px',
            background: amenByMe ? 'rgba(52,199,89,0.25)' : 'rgba(255,255,255,0.08)',
            border: `1px solid ${amenByMe ? 'rgba(52,199,89,0.5)' : 'rgba(255,255,255,0.18)'}`,
            borderRadius: 20, color: amenByMe ? '#34c759' : 'rgba(255,255,255,0.7)',
            fontSize: 13, cursor: 'pointer', fontWeight: amenByMe ? 600 : 400,
          }}
        >
          🙌 阿们 {amenCount > 0 && <span style={{ fontWeight: 700 }}>{amenCount}</span>}
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: '20px 18px', maxWidth: 600, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        {/* Author row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, paddingBottom: 16, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          {note.avatar ? (
            <img src={note.avatar} alt="" style={{ width: 44, height: 44, borderRadius: '50%', objectFit: 'cover' }} />
          ) : (
            <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'linear-gradient(135deg,#667eea,#764ba2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
              {note.author?.[0] || '?'}
            </div>
          )}
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>{note.author || '匿名'}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>
              {note.mood && <span style={{ marginRight: 6 }}>{note.mood}</span>}
              {formatDate(note.sharedAt || note.date)}
            </div>
          </div>
        </div>

        {/* Scripture */}
        <div style={{ fontSize: 18, fontWeight: 700, color: '#fff', marginBottom: 20, lineHeight: 1.5 }}>{note.scripture}</div>

        {[['👁️ 观察', note.observation], ['💭 反思', note.reflection], ['✨ 应用', note.application], ['🙏 祷告', note.prayer]]
          .filter(([, v]) => v)
          .map(([label, text]) => (
            <div key={label} style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em' }}>{label}</div>
              <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.85)', lineHeight: 1.75, whiteSpace: 'pre-wrap', fontStyle: label.includes('祷告') ? 'italic' : 'normal' }}>{text}</div>
            </div>
          ))}

        {/* Action Buttons */}
        <div style={{ marginTop: 32, paddingTop: 20, borderTop: '1px solid rgba(255,255,255,0.08)', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {note.is_own && (
            <button
              onClick={handleUnshare}
              style={{ width: '100%', padding: '11px', marginBottom: 6, background: 'rgba(255,59,48,0.12)', border: '1px solid rgba(255,59,48,0.35)', borderRadius: 10, color: '#ff6b6b', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
            >
              ↩️ 从分享墙撤回
            </button>
          )}
          <button
            onClick={() => exportSelectedToTxt(note)}
            style={{ flex: 1, padding: '10px', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 10, color: 'rgba(255,255,255,0.8)', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            TXT
          </button>
          <button
            onClick={() => exportSelectedToPdf(note)}
            style={{ flex: 1, padding: '10px', background: 'rgba(0,122,255,0.18)', border: '1px solid rgba(0,122,255,0.35)', borderRadius: 10, color: '#5ac8fa', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15l3 3 3-3"/><path d="M12 18V9"/></svg>
            PDF
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ShareWallPage({ user, onBack }) {
  const [notes, setNotes] = useState([])
  const [selectedNote, setSelectedNote] = useState(null)
  const [expandedCards, setExpandedCards] = useState({})
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const listRef = useRef(null)
  const token = getToken()

  function toggleExpand(id) {
    setExpandedCards(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const loadNotes = useCallback(async (pg = 1) => {
    if (!user) return
    setLoading(true)
    try {
      const data = await fetchSharedNotes(token, pg, 20)
      if (data.requireLogin) { setLoading(false); return }
      const apiNotes = data.items || []

      if (pg === 1) {
        // First load: also merge legacy localStorage notes (one-time migration)
        const legacyNotes = getLegacySharedNotes()
        if (legacyNotes.length > 0) {
          const seenIds = new Set(apiNotes.map(n => n.id))
          const extra = legacyNotes.filter(n => !seenIds.has(n.id))
          setNotes([...apiNotes, ...extra])
          // Auto-clear legacy after successful API load
          localStorage.removeItem('devotion_notes_shared')
          console.log('[sharewall] migrated & cleared', extra.length, 'legacy notes')
        } else {
          setNotes(apiNotes)
        }
      } else {
        setNotes(prev => [...prev, ...data.items])
      }
      setPage(pg)
      setTotalPages(data.pages || 1)
      setTotal(data.total || 0)
    } catch (err) {
      console.error('[sharewall] load error:', err)
    } finally {
      setLoading(false)
    }
  }, [user, token])

  useEffect(() => { loadNotes(1) }, [loadNotes])

  const { indicatorStyle, indicatorText } = usePullToRefresh(() => loadNotes(1), listRef)

  async function handleUnshare(noteId) {
    const note = notes.find(n => n.id === noteId)
    if (note?._source === 'local') {
      setNotes(prev => prev.filter(n => n.id !== noteId))
      return
    }
    try {
      await toggleShareNote(noteId, token)
      setNotes(prev => prev.filter(n => n.id !== noteId))
      setTotal(t => Math.max(0, t - 1))
    } catch (err) {
      alert(err.message || '操作失败')
    }
  }

  function handleAmenUpdate(noteId, amen_count, amen_by_me) {
    setNotes(prev => prev.map(n => n.id === noteId ? { ...n, amen_count, amen_by_me } : n))
  }

  if (!user) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#1a1a2e,#16213e)' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🌟</div>
        <div style={{ fontSize: 18, color: 'rgba(255,255,255,0.9)', marginBottom: 8 }}>分享墙</div>
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', marginBottom: 24 }}>登录后查看分享墙内容</div>
        <button onClick={onBack} style={{ padding: '10px 24px', background: 'rgba(0,122,255,0.3)', border: '1px solid rgba(0,122,255,0.5)', borderRadius: 8, color: '#5ac8fa', fontSize: 14, cursor: 'pointer' }}>← 返回</button>
      </div>
    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'linear-gradient(135deg,#1a1a2e,#16213e)' }}>
      {/* Detail overlay (mobile full-screen + desktop full-screen) */}
      {selectedNote && (
        <NoteDetailOverlay
          note={selectedNote}
          onClose={() => setSelectedNote(null)}
          onUnshare={handleUnshare}
          onAmen={handleAmenUpdate}
          token={token}
        />
      )}

      {/* Header */}
      <header style={{ padding: '14px 18px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.7)', cursor: 'pointer', padding: 8 }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <div style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: 17, fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>🌟 分享墙</div>
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>{total > 0 ? `${total} 篇分享` : ''}</div>
        </div>
        <button
          onClick={() => loadNotes(1)}
          style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', padding: 8, fontSize: 16 }}
          title="刷新"
        >↻</button>
      </header>

      {/* Note list */}
      <div ref={listRef} style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', position: 'relative' }}>
        <div style={indicatorStyle}>{indicatorText}</div>

        {loading && notes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'rgba(255,255,255,0.4)' }}>加载中...</div>
        ) : notes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'rgba(255,255,255,0.4)' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📝</div>
            <div style={{ fontSize: 15 }}>暂无分享</div>
            <div style={{ fontSize: 13, marginTop: 8, opacity: 0.6 }}>在日记页面分享你的灵修心得</div>
          </div>
        ) : (
          <>
            {notes.map(note => {
              const text = note.reflection || note.observation || ''
              const lines = text.split('\n')
              const isLong = lines.length > MAX_LINES || text.length > MAX_LINES * 38
              const expanded = expandedCards[note.id]
              return (
                <div
                  key={note.id}
                  onClick={() => setSelectedNote(note)}
                  style={{
                    padding: '14px 14px 10px',
                    marginBottom: 10,
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: 14,
                    cursor: 'pointer',
                    border: '1px solid rgba(255,255,255,0.08)',
                    transition: 'background 0.15s',
                  }}
                >
                  {/* Author row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 9 }}>
                    {note.avatar ? (
                      <img src={note.avatar} alt="" style={{ width: 30, height: 30, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
                    ) : (
                      <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'linear-gradient(135deg,#667eea,#764ba2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>
                        {note.author?.[0] || '?'}
                      </div>
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, color: 'rgba(255,255,255,0.9)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{note.author || '匿名'}</div>
                      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{note.mood && <span style={{ marginRight: 5 }}>{note.mood}</span>}{formatDate(note.sharedAt || note.date)}</div>
                    </div>
                    {/* Inline amen count badge */}
                    {(note.amen_count > 0) && (
                      <span style={{ fontSize: 11, color: note.amen_by_me ? '#34c759' : 'rgba(255,255,255,0.4)', flexShrink: 0 }}>🙌 {note.amen_count}</span>
                    )}
                  </div>

                  {/* Scripture */}
                  {note.scripture && (
                    <div style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.95)', marginBottom: 6, lineHeight: 1.5 }}>{note.scripture}</div>
                  )}

                  {/* Preview text */}
                  {text ? (
                    <div style={{ position: 'relative' }}>
                      <div style={{
                        fontSize: FONT_SIZE, color: 'rgba(255,255,255,0.65)', lineHeight: LINE_HEIGHT,
                        whiteSpace: 'pre-wrap', overflow: 'hidden',
                        maxHeight: (!expanded && isLong) ? `${COLLAPSED_HEIGHT}px` : 'none',
                      }}>
                        {text}
                        {!expanded && isLong && (
                          <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 40, background: 'linear-gradient(transparent, rgba(26,26,46,0.95))' }} />
                        )}
                      </div>
                      {isLong && (
                        <button
                          onClick={e => { e.stopPropagation(); toggleExpand(note.id) }}
                          style={{ background: 'none', border: 'none', padding: '4px 0', color: '#5ac8fa', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}
                        >
                          {expanded ? '收起 ▲' : '展开全文 ▼'}
                        </button>
                      )}
                    </div>
                  ) : null}
                </div>
              )
            })}

            {/* Load more */}
            {page < totalPages && (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <button
                  onClick={() => loadNotes(page + 1)}
                  disabled={loading}
                  style={{ padding: '10px 28px', background: 'rgba(0,122,255,0.2)', border: '1px solid rgba(0,122,255,0.35)', borderRadius: 20, color: '#5ac8fa', fontSize: 13, cursor: 'pointer' }}
                >
                  {loading ? '加载中...' : '加载更多'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
