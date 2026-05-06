import { useEffect, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { fetchPersonalNotes, savePersonalNote, deletePersonalNote } from './api'

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

function formatDateTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function exportNoteToTxt(note) {
  if (!note) return
  let content = `情感星球 - 我的灵修日记\n`
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
  const title = (note.scripture || '灵修日记').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
  a.download = `${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportNoteToPdf(note) {
  if (!note) return

  const container = document.createElement('div')
  container.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 794px; background: #0d0d1a; padding: 40px; font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; line-height: 1.8; color: #ffffff;'
  document.body.appendChild(container)

  let content = `
    <div style="text-align: center; margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px;">
      <h1 style="color: #007aff; font-size: 22px; margin: 0 0 10px 0;">我的灵修日记</h1>
      <div style="color: rgba(255,255,255,0.5); font-size: 13px;">
        日期：${formatDateTime(note.date)}${note.mood ? ' | ' + note.mood : ''}
      </div>
    </div>

    <div style="margin: 20px 0;">
      <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">经文</div>
      <div style="font-size: 16px; color: #ffffff; font-weight: 600; margin: 12px 0;">${note.scripture || '未记录'}</div>
    </div>
  `

  if (note.observation) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">观察</div>
        <div style="background: rgba(255,255,255,0.05); padding: 14px; border-radius: 8px; color: rgba(255,255,255,0.88); white-space: pre-wrap;">${note.observation.replace(/\n/g, '<br>')}</div>
      </div>
    `
  }
  if (note.reflection) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">反思</div>
        <div style="background: rgba(255,255,255,0.05); padding: 14px; border-radius: 8px; color: rgba(255,255,255,0.88); white-space: pre-wrap;">${note.reflection.replace(/\n/g, '<br>')}</div>
      </div>
    `
  }
  if (note.application) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">应用</div>
        <div style="background: rgba(48,209,88,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(48,209,88,0.25); color: #30d158; white-space: pre-wrap;">${note.application.replace(/\n/g, '<br>')}</div>
      </div>
    `
  }
  if (note.prayer) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">祷告</div>
        <div style="background: rgba(255,159,10,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(255,159,10,0.25); color: #ff9f0a; white-space: pre-wrap; font-style: italic;">${note.prayer.replace(/\n/g, '<br>')}</div>
      </div>
    `
  }

  container.innerHTML = content

  try {
    const canvas = await html2canvas(container, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#0d0d1a'
    })

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pdfWidth = pdf.internal.pageSize.getWidth()
    const pdfHeight = pdf.internal.pageSize.getHeight()
    const imgWidth = canvas.width
    const imgHeight = canvas.height
    const scaledWidth = pdfWidth - 20
    const scaledHeight = (imgHeight * scaledWidth) / imgWidth

    let heightLeft = scaledHeight
    let position = 10

    pdf.addImage(imgData, 'PNG', 10, position, scaledWidth, scaledHeight)
    heightLeft -= (pdfHeight - 20)

    while (heightLeft > 0) {
      position = heightLeft - scaledHeight + 10
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 10, position, scaledWidth, scaledHeight)
      heightLeft -= (pdfHeight - 20)
    }

    const title = (note.scripture || '灵修日记').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
    pdf.save(`${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) {
    console.error('PDF generation failed:', err)
    alert('PDF 生成失败，请重试')
  } finally {
    document.body.removeChild(container)
  }
}

export default function PersonalDevotionPage({ user, token, onBack }) {
  const [notes, setNotes] = useState([])
  const [selected, setSelected] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [saveStatus, setSaveStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isComposeOpen, setIsComposeOpen] = useState(false)

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

  // Load notes from API
  async function loadNotes() {
    if (!user) return
    setLoading(true)
    setError('')
    try {
      const data = await fetchPersonalNotes(token)
      setNotes(data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotes()
  }, [user, token])

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
    setIsComposeOpen(true)
  }

  function handleCloseCompose() {
    setIsComposeOpen(false)
    setIsEditing(false)
  }

  async function handleSave() {
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

    try {
      const result = await savePersonalNote(note, token)
      if (result.note) {
        setNotes(prev => {
          const existing = prev.findIndex(n => n.id === result.note.id)
          if (existing >= 0) {
            const updated = [...prev]
            updated[existing] = result.note
            return updated
          }
          return [result.note, ...prev]
        })
        setSelected(result.note.id)
      }
      setIsComposeOpen(false)
      setIsEditing(false)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus(''), 2000)
    } catch (e) {
      alert('保存失败: ' + e.message)
      setSaveStatus('')
    }
  }

  async function handleShare() {
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

    try {
      // Save to personal notes first with shared=true
      const result = await savePersonalNote(sharedNote, token)
      if (result.note) {
        setNotes(prev => {
          const existing = prev.findIndex(n => n.id === result.note.id)
          if (existing >= 0) {
            const updated = [...prev]
            updated[existing] = result.note
            return updated
          }
          return [result.note, ...prev]
        })
        setForm(prev => ({ ...prev, shared: true }))
      }
      alert('已分享到分享墙！')
    } catch (e) {
      alert('分享失败: ' + e.message)
    }
  }

  async function handleShareFromList(note) {
    if (note.shared) {
      // Cancel share - just update the shared flag
      const updatedNote = { ...note, shared: false }
      try {
        const result = await savePersonalNote(updatedNote, token)
        if (result.note) {
          setNotes(prev => prev.map(n => n.id === note.id ? result.note : n))
          if (selected === note.id) {
            setForm(prev => ({ ...prev, shared: false }))
          }
        }
      } catch (e) {
        alert('取消分享失败: ' + e.message)
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

      try {
        const result = await savePersonalNote(sharedNote, token)
        if (result.note) {
          setNotes(prev => prev.map(n => n.id === note.id ? result.note : n))
          if (selected === note.id) {
            setForm(prev => ({ ...prev, shared: true }))
          }
        }
        alert('已分享到分享墙！')
      } catch (e) {
        alert('分享失败: ' + e.message)
      }
    }
  }

  function updateField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  async function handleDelete(id) {
    if (!window.confirm('确定删除这篇日记？')) return
    try {
      await deletePersonalNote(id, token)
      const filtered = notes.filter(n => n.id !== id)
      setNotes(filtered)
      if (selected === id) {
        setSelected(null)
      }
    } catch (e) {
      alert('删除失败: ' + e.message)
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
          className="pw-compose-btn"
          onClick={handleNew}
          title="新建日记"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
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
              <div style={{ fontSize: '13px', marginTop: '8px', opacity: 0.7 }}>点击右上角 + 新建日记</div>
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
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
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

              {/* Export Buttons */}
              <div style={{ marginTop: '30px', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => exportNoteToTxt(selectedNote)}
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
                  导出TXT
                </button>
                <button
                  onClick={() => exportNoteToPdf(selectedNote)}
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
                  导出PDF
                </button>
              </div>
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

      {/* Compose Overlay - 像代祷页面一样的撰写框 */}
      {isComposeOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(4px)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '600px',
            maxHeight: '90vh',
            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
            borderRadius: '16px',
            border: '1px solid rgba(255,255,255,0.1)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Compose Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ fontSize: '17px', fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>
                ✏️ 新建日记
              </div>
              <button
                onClick={handleCloseCompose}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'rgba(255,255,255,0.6)',
                  cursor: 'pointer',
                  padding: '4px',
                  fontSize: '20px'
                }}
              >
                ×
              </button>
            </div>

            {/* Compose Form */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
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

            {/* Compose Footer */}
            <div style={{
              padding: '16px 20px',
              borderTop: '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              gap: '12px'
            }}>
              <button
                onClick={handleSave}
                style={{
                  flex: 1,
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
              <button
                onClick={handleCloseCompose}
                style={{
                  padding: '12px 20px',
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
          </div>
        </div>
      )}
    </div>
  )
}
