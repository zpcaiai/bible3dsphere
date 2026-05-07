import { useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { deleteJournal, fetchJournals, saveJournal } from './api'

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

const FIELDS = [
  { key: 'scripture',    label: '📖 今日经文', placeholder: '记录今天读到的经文…', rows: 3 },
  { key: 'observation',  label: '🔍 观察默想', placeholder: '这段经文说了什么？有什么让你印象深刻？', rows: 4 },
  { key: 'reflection',   label: '💭 灵修反思', placeholder: '这段经文对你说什么？神在其中给你什么光照？', rows: 4 },
  { key: 'application',  label: '🌱 行道应用', placeholder: '你今天打算如何将这段话活出来？', rows: 3 },
  { key: 'prayer',       label: '🙏 祷告记录', placeholder: '写下你今天的祷告…', rows: 4 },
]

function today() {
  return new Date().toISOString().slice(0, 10)
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 (周${weekdays[d.getDay()]})`
}

function timeAgo(ts) {
  const diff = Math.floor(Date.now() / 1000 - ts)
  if (diff < 3600) return `${Math.floor(diff / 60) || 1} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} 天前`
  return new Date(ts * 1000).toLocaleDateString('zh-CN')
}

const EMPTY_FORM = { date: today(), title: '', scripture: '', observation: '', reflection: '', application: '', prayer: '', mood: '' }

// ── List Card ────────────────────────────────────────────────
function JournalCard({ journal, onOpen, onDelete }) {
  const mood = MOODS.find(m => m.label === journal.mood)
  const preview = journal.observation || journal.reflection || journal.scripture || '（空白）'

  return (
    <div className="dj-card glass" onClick={() => onOpen(journal)}>
      <div className="dj-card-header">
        <div className="dj-card-date">{formatDate(journal.date)}</div>
        {mood && <span className="dj-card-mood">{mood.emoji} {mood.label}</span>}
      </div>
      {journal.title && <div className="dj-card-title">{journal.title}</div>}
      <div className="dj-card-preview" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', WebkitLineClamp: 'none', maxHeight: 'none', overflow: 'visible' }}>{preview}</div>
      <div className="dj-card-footer">
        <span className="dj-card-time">更新于 {timeAgo(journal.updated_at)}</span>
        <button
          className="dj-card-del"
          onClick={e => { e.stopPropagation(); onDelete(journal) }}
          title="删除"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
          </svg>
        </button>
      </div>
    </div>
  )
}

// ── Editor ───────────────────────────────────────────────────
function JournalEditor({ initial, token, onSaved, onCancel }) {
  const [form, setForm] = useState(initial)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const autoSaveRef = useRef(null)

  function set(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
    // Auto-save debounce 3s
    if (autoSaveRef.current) clearTimeout(autoSaveRef.current)
    autoSaveRef.current = setTimeout(() => doSave({ ...form, [key]: value }, true), 3000)
  }

  async function doSave(data = form, silent = false) {
    if (!data.scripture && !data.observation && !data.reflection && !data.application && !data.prayer) return
    setSaving(true)
    setError('')
    try {
      const result = await saveJournal(data, token)
      if (!silent) {
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
        onSaved(result.journal)
      }
    } catch (e) {
      if (!silent) setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => () => { if (autoSaveRef.current) clearTimeout(autoSaveRef.current) }, [])

  const isNew = !initial.id

  return (
    <div className="dj-editor">
      {/* Editor header */}
      <div className="dj-editor-header">
        <button className="checkin-back-btn" onClick={onCancel}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="dj-editor-hcenter">
          <div className="dj-editor-htitle">{isNew ? '新建灵修日记' : '编辑灵修日记'}</div>
          <div className="dj-editor-hdate">{formatDate(form.date)}</div>
        </div>
        <button
          className="dj-save-btn"
          disabled={saving}
          onClick={() => doSave()}
        >
          {saving ? '…' : saved ? '✓' : '保存'}
        </button>
      </div>

      <div className="dj-editor-body">
        {/* Date picker */}
        <div className="dj-field">
          <label className="dj-field-label">📅 日期</label>
          <input
            type="date"
            className="dj-date-input"
            value={form.date}
            onChange={e => set('date', e.target.value)}
          />
        </div>

        {/* Title */}
        <div className="dj-field">
          <label className="dj-field-label">✏️ 标题（选填）</label>
          <input
            type="text"
            className="dj-text-input"
            placeholder="今天的主题是…"
            value={form.title}
            onChange={e => set('title', e.target.value)}
            maxLength={200}
          />
        </div>

        {/* Mood */}
        <div className="dj-field">
          <label className="dj-field-label">💝 今日心情</label>
          <div className="dj-mood-grid">
            {MOODS.map(m => (
              <button
                key={m.label}
                className={`dj-mood-chip ${form.mood === m.label ? 'active' : ''}`}
                onClick={() => set('mood', form.mood === m.label ? '' : m.label)}
              >
                <span className="dj-mood-emoji">{m.emoji}</span>
                <span className="dj-mood-text">{m.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Content fields */}
        {FIELDS.map(f => (
          <div key={f.key} className="dj-field">
            <label className="dj-field-label">{f.label}</label>
            <textarea
              className="dj-textarea"
              placeholder={f.placeholder}
              rows={f.rows}
              value={form[f.key]}
              onChange={e => set(f.key, e.target.value)}
            />
          </div>
        ))}

        {error && <div className="dj-error">{error}</div>}

        <button
          className="primary-btn dj-submit-btn"
          disabled={saving}
          onClick={() => doSave()}
        >
          {saving ? '保存中…' : '💾 保存日记'}
        </button>
      </div>
    </div>
  )
}

function formatDateTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function exportJournalToTxt(journal) {
  if (!journal) return
  let content = `情感星球 - 灵修日记\n`
  content += `日期：${formatDate(journal.date)}\n`
  if (journal.mood) content += `心情：${journal.mood}\n`
  if (journal.title) content += `标题：${journal.title}\n`
  content += `\n━━━━━━━━━━━━━━━━━━━━━━━\n  今日经文\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
  content += `${journal.scripture || '未记录'}\n\n`
  
  if (journal.observation) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  观察默想\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${journal.observation}\n\n`
  }
  if (journal.reflection) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  灵修反思\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${journal.reflection}\n\n`
  }
  if (journal.application) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  行道应用\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${journal.application}\n\n`
  }
  if (journal.prayer) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  祷告记录\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${journal.prayer}\n\n`
  }
  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const title = (journal.title || journal.scripture || '灵修日记').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
  a.download = `${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportJournalToPdf(journal) {
  if (!journal) return
  
  const container = document.createElement('div')
  container.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 794px; background: #0d0d1a; padding: 40px; font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; line-height: 1.8; color: #ffffff;'
  document.body.appendChild(container)
  
  const mood = MOODS.find(m => m.label === journal.mood)
  
  let content = `
    <div style="text-align: center; margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px;">
      <h1 style="color: #007aff; font-size: 22px; margin: 0 0 10px 0;">📔 灵修日记</h1>
      <div style="color: rgba(255,255,255,0.5); font-size: 13px;">
        ${formatDate(journal.date)}${mood ? ' | ' + mood.emoji + ' ' + mood.label : ''}${journal.title ? ' | ' + journal.title : ''}
      </div>
    </div>
    
    <div style="margin: 20px 0;">
      <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">📖 今日经文</div>
      <div style="font-size: 14px; color: #ffffff; font-weight: 500; margin: 12px 0; white-space: pre-wrap;">${journal.scripture || '未记录'}</div>
    </div>
  `
  
  if (journal.observation) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">🔍 观察默想</div>
        <div style="background: rgba(255,255,255,0.05); padding: 14px; border-radius: 8px; color: rgba(255,255,255,0.88); white-space: pre-wrap;">${journal.observation.replace(/\n/g, '<br>')}</div>
      </div>
    `
  }
  if (journal.reflection) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">💭 灵修反思</div>
        <div style="background: rgba(255,255,255,0.05); padding: 14px; border-radius: 8px; color: rgba(255,255,255,0.88); white-space: pre-wrap;">${journal.reflection.replace(/\n/g, '<br>')}</div>
      </div>
    `
  }
  if (journal.application) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">🌱 行道应用</div>
        <div style="background: rgba(48,209,88,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(48,209,88,0.25); color: #30d158; white-space: pre-wrap;">${journal.application.replace(/\n/g, '<br>')}</div>
      </div>
    `
  }
  if (journal.prayer) {
    content += `
      <div style="margin: 20px 0;">
        <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">🙏 祷告记录</div>
        <div style="background: rgba(255,159,10,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(255,159,10,0.25); color: #ff9f0a; white-space: pre-wrap; font-style: italic;">${journal.prayer.replace(/\n/g, '<br>')}</div>
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
    
    const title = (journal.title || journal.scripture || '灵修日记').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
    pdf.save(`${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) {
    console.error('PDF generation failed:', err)
    alert('PDF 生成失败，请重试')
  } finally {
    document.body.removeChild(container)
  }
}

// ── Detail View ──────────────────────────────────────────────
function JournalDetail({ journal, onEdit, onBack }) {
  const mood = MOODS.find(m => m.label === journal.mood)
  const sections = FIELDS.filter(f => journal[f.key]?.trim())
  return (
    <div className="dj-detail">
      <div className="dj-editor-header">
        <button className="checkin-back-btn" onClick={onBack}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="dj-editor-hcenter">
          <div className="dj-editor-htitle">{journal.title || '灵修日记'}</div>
          <div className="dj-editor-hdate">{formatDate(journal.date)}</div>
        </div>
        <button className="dj-save-btn" onClick={onEdit}>编辑</button>
      </div>

      <div className="dj-detail-body">
        {mood && (
          <div className="dj-detail-mood-badge">
            {mood.emoji} <span>{mood.label}</span>
          </div>
        )}

        {sections.map(f => (
          <div key={f.key} className="dj-detail-section glass">
            <div className="dj-detail-section-title">{f.label}</div>
            <div className="dj-detail-section-content" style={{ whiteSpace: 'pre-wrap' }}>{journal[f.key]}</div>
          </div>
        ))}

        {sections.length === 0 && (
          <div className="dj-empty" style={{ marginTop: 40 }}>
            <div className="dj-empty-icon">📝</div>
            <div>这篇日记还没有内容</div>
            <button className="primary-btn" style={{ maxWidth: 160, marginTop: 16 }} onClick={onEdit}>立即填写</button>
          </div>
        )}

        {/* Export Buttons */}
        <div style={{ marginTop: '30px', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', gap: '12px' }}>
          <button
            onClick={() => exportJournalToTxt(journal)}
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
            onClick={() => exportJournalToPdf(journal)}
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

        <div className="dj-detail-footer">
          最后更新于 {timeAgo(journal.updated_at)}
        </div>
      </div>
    </div>
  )
}

// ── Main Page ────────────────────────────────────────────────
export default function DevotionJournalPage({ user, token, onBack }) {
  const [view, setView] = useState('list')   // 'list' | 'editor' | 'detail'
  const [journals, setJournals] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [current, setCurrent] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  async function load(replace = true) {
    setLoading(true)
    setError('')
    try {
      const data = await fetchJournals(token, 50, replace ? 0 : journals.length)
      setTotal(data.total)
      setJournals(prev => replace ? data.items : [...prev, ...data.items])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function openNew() {
    setCurrent(null)
    setView('editor')
  }

  function openEdit(journal) {
    setCurrent(journal)
    setView('editor')
  }

  function openDetail(journal) {
    setCurrent(journal)
    setView('detail')
  }

  function onSaved(journal) {
    setJournals(prev => {
      const idx = prev.findIndex(j => j.id === journal.id)
      if (idx >= 0) {
        const next = [...prev]
        next[idx] = journal
        return next
      }
      return [journal, ...prev]
    })
    setTotal(t => t + (journals.findIndex(j => j.id === journal.id) >= 0 ? 0 : 1))
    setCurrent(journal)
    setView('detail')
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteJournal(deleteTarget.id, token)
      setJournals(prev => prev.filter(j => j.id !== deleteTarget.id))
      setTotal(t => t - 1)
      setDeleteTarget(null)
      if (current?.id === deleteTarget.id) { setCurrent(null); setView('list') }
    } catch (e) {
      setError(e.message)
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  // ── Not logged in ───────────────────────────────────────────
  if (!user) {
    return (
      <div className="dj-page">
        <header className="dj-header">
          <button className="checkin-back-btn" onClick={onBack}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <div className="dj-header-center">
            <div className="dj-page-title">📔 灵修日记</div>
          </div>
          <div style={{ width: 32 }} />
        </header>
        <div className="dj-empty" style={{ flex: 1 }}>
          <div className="dj-empty-icon">🔒</div>
          <div className="dj-empty-title">请先登录</div>
          <div className="dj-empty-sub">灵修日记需要登录后才能使用</div>
        </div>
      </div>
    )
  }

  // ── Delete confirmation dialog ───────────────────────────────
  const deleteDialog = deleteTarget && (
    <div className="dj-overlay" onClick={() => setDeleteTarget(null)}>
      <div className="dj-dialog glass" onClick={e => e.stopPropagation()}>
        <div className="dj-dialog-title" style={{ textAlign: 'center', fontSize: '18px' }}>⚠️ 确定要删除这条日记吗？</div>
        <div className="dj-dialog-body" style={{ textAlign: 'center', color: 'rgba(255,255,255,0.6)' }}>
          删除 <strong>{formatDate(deleteTarget.date)}</strong> 的日记<br />
          删除后无法恢复，请谨慎操作
        </div>
        <div className="dj-dialog-actions">
          <button className="pw-cancel-btn" onClick={() => setDeleteTarget(null)}>取消</button>
          <button
            className="dj-del-confirm-btn"
            disabled={deleting}
            onClick={confirmDelete}
          >
            {deleting ? '删除中…' : '确认删除'}
          </button>
        </div>
      </div>
    </div>
  )

  // ── Editor view ──────────────────────────────────────────────
  if (view === 'editor') {
    const initialForm = current
      ? { date: current.date, title: current.title, scripture: current.scripture, observation: current.observation, reflection: current.reflection, application: current.application, prayer: current.prayer, mood: current.mood, id: current.id }
      : { ...EMPTY_FORM }
    return (
      <div className="dj-page">
        {deleteDialog}
        <JournalEditor
          initial={initialForm}
          token={token}
          onSaved={onSaved}
          onCancel={() => setView(current ? 'detail' : 'list')}
        />
      </div>
    )
  }

  // ── Detail view ──────────────────────────────────────────────
  if (view === 'detail' && current) {
    return (
      <div className="dj-page">
        {deleteDialog}
        <JournalDetail
          journal={current}
          onEdit={() => openEdit(current)}
          onBack={() => setView('list')}
        />
      </div>
    )
  }

  // ── List view ────────────────────────────────────────────────
  return (
    <div className="dj-page">
      {deleteDialog}

      <header className="dj-header">
        <button className="checkin-back-btn" onClick={onBack}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="dj-header-center">
          <div className="dj-page-title">📔 灵修日记</div>
          <div className="dj-page-sub">{total > 0 ? `共 ${total} 篇` : '每日与神同行'}</div>
        </div>
        <button className="pw-compose-btn" onClick={openNew} title="新建">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </header>

      {error && <div className="dj-error" style={{ margin: '12px 14px' }}>{error}</div>}

      <div className="dj-list">
        {loading ? (
          <div className="pw-loading">
            <div className="pw-loading-dots"><span /><span /><span /></div>
            <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 13, marginTop: 12 }}>加载中…</div>
          </div>
        ) : journals.length === 0 ? (
          <div className="dj-empty">
            <div className="dj-empty-icon">📔</div>
            <div className="dj-empty-title">还没有日记</div>
            <div className="dj-empty-sub">每天与神同行，记录灵命成长</div>
            <button className="primary-btn" style={{ maxWidth: 200, marginTop: 20 }} onClick={openNew}>
              写第一篇日记
            </button>
          </div>
        ) : (
          <>
            {/* Today shortcut */}
            {!journals.find(j => j.date === today()) && (
              <button className="dj-today-btn glass" onClick={openNew}>
                <span className="dj-today-icon">✨</span>
                <span className="dj-today-text">记录今天的灵修 — {formatDate(today())}</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            )}

            {journals.map(j => (
              <JournalCard
                key={j.id}
                journal={j}
                onOpen={openDetail}
                onDelete={j => setDeleteTarget(j)}
              />
            ))}

            {journals.length < total && (
              <button className="pw-load-more" onClick={() => load(false)}>
                加载更多（还有 {total - journals.length} 篇）
              </button>
            )}

            <div className="pw-footer-tip">诗篇 119:105 · 你的话是我脚前的灯，是我路上的光</div>
          </>
        )}
      </div>
    </div>
  )
}
