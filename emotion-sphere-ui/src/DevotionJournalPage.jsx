import { useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { deleteJournal, fetchJournals, saveJournal } from './api'
import usePullToRefresh from './hooks/usePullToRefresh'
import { escapeHtml, escapeHtmlWithBr } from './sanitize'
import EmojiTextarea from './EmojiTextarea'

// 读取旧的 localStorage 灵修笔记（来自 ChatPage / DevotionNotePage）
function getLegacyLocalJournals() {
  try {
    const personal = localStorage.getItem('devotion_notes_personal')
    const items = personal ? JSON.parse(personal) : []
    return items.map(n => ({
      id: `local_${n.id || n.createdAt || Date.now()}`,
      date: n.date || new Date().toISOString().slice(0, 10),
      title: n.title || '',
      scripture: n.scripture || '',
      observation: n.observation || '',
      reflection: n.reflection || '',
      application: n.application || '',
      prayer: n.prayer || '',
      mood: n.mood || '',
      updated_at: n.createdAt ? new Date(n.createdAt).toISOString() : null,
      created_at: n.createdAt ? new Date(n.createdAt).toISOString() : null,
      _source: 'local',
    }))
  } catch {
    return []
  }
}

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
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  if (isNaN(d.getTime())) return dateStr
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

function timeAgo(ts) {
  if (!ts) return ''
  const d = typeof ts === 'string' ? new Date(ts) : (ts > 1e12 ? new Date(ts) : new Date(ts * 1000))
  if (isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

const EMPTY_FORM = { date: today(), title: '', scripture: '', observation: '', reflection: '', application: '', prayer: '', mood: '' }

// ── List Card ────────────────────────────────────────────────
function JournalCard({ journal, onOpen, onEdit, onDelete }) {
  const mood = MOODS.find(m => m.label === journal.mood)
  const preview = journal.observation || journal.reflection || journal.scripture || '（空白）'

  const btnStyle = {
    padding: '6px',
    background: 'rgba(255,255,255,0.08)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '6px',
    color: 'rgba(255,255,255,0.7)',
    fontSize: '14px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '32px',
    minHeight: '32px',
  }
  const delBtnStyle = {
    ...btnStyle,
    background: 'rgba(239,68,68,0.15)',
    border: '1px solid rgba(239,68,68,0.3)',
    color: '#ef4444',
  }

  return (
    <div className="dj-card glass" onClick={() => onOpen(journal)}>
      <div className="dj-card-header">
        <div className="dj-card-date">{formatDate(journal.date)}</div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {mood && <span className="dj-card-mood">{mood.emoji} {mood.label}</span>}
          <button onClick={e => { e.stopPropagation(); onEdit(journal) }} title="编辑" style={btnStyle}>✏️</button>
          <button onClick={e => { e.stopPropagation(); onDelete(journal) }} title="删除" style={delBtnStyle}>🗑️</button>
        </div>
      </div>
      {journal.title && <div className="dj-card-title">{journal.title}</div>}
      <div className="dj-card-preview" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', WebkitLineClamp: 'none', maxHeight: 'none', overflow: 'visible' }}>{preview}</div>
      <div className="dj-card-footer">
        <span className="dj-card-time">更新于 {timeAgo(journal.updated_at)}</span>
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
          {saving ? '…' : saved ? '✓' : '💾'}
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
            value={form.title || ''}
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
            {f.key === 'scripture' ? (
              <textarea
                className="dj-textarea"
                placeholder={f.placeholder}
                rows={f.rows}
                value={form[f.key] || ''}
                onChange={e => set(f.key, e.target.value)}
              />
            ) : (
              <EmojiTextarea
                className="dj-textarea"
                placeholder={f.placeholder}
                rows={f.rows}
                value={form[f.key] || ''}
                onChange={v => set(f.key, v)}
              />
            )}
          </div>
        ))}

        {error && <div className="dj-error">{error}</div>}

        <button
          className="primary-btn dj-submit-btn"
          disabled={saving}
          onClick={() => doSave()}
        >
          {saving ? '⏳ 保存中…' : '💾 保存'}
        </button>
      </div>
    </div>
  )
}

function formatDateTime(ts) {
  if (!ts) return ''
  const d = typeof ts === 'string' ? new Date(ts) : (ts > 1e12 ? new Date(ts) : new Date(ts * 1000))
  if (isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function exportJournalToTxt(journal) {
  if (!journal) return
  let content = `属灵星球 - 灵修日记\n`
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
  const pdf = new jsPDF('p', 'mm', 'a4')
  const PW = pdf.internal.pageSize.getWidth()
  const PH = pdf.internal.pageSize.getHeight()
  const M = 12, cw = PW - M * 2
  let curY = M
  pdf.setFillColor(14, 23, 38); pdf.rect(0, 0, PW, PH, 'F')

  const el = document.createElement('div')
  el.style.cssText = `position:fixed;left:-9999px;top:0;width:${Math.round(cw * 3.78)}px;background:#0e1726;padding:0;font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#e8e8e8;`
  document.body.appendChild(el)

  async function addBlock(html) {
    el.innerHTML = html
    const canvas = await html2canvas(el, { scale: 2, useCORS: true, logging: false, backgroundColor: '#0e1726' })
    const imgH = (canvas.height / canvas.width) * cw
    if (curY + imgH > PH - 10 && curY > M + 5) { pdf.addPage(); pdf.setFillColor(14, 23, 38); pdf.rect(0, 0, PW, PH, 'F'); curY = M }
    pdf.addImage(canvas.toDataURL('image/jpeg', 0.92), 'JPEG', M, curY, cw, imgH)
    curY += imgH + 3
  }

  const mood = MOODS.find(m => m.label === journal.mood)
  try {
    await addBlock(`
      <div style="text-align:center;margin-bottom:10px;border-bottom:1px solid #2e3c52;padding-bottom:10px;">
        <h1 style="color:#007aff;font-size:20px;margin:0 0 6px 0;">📔 灵修日记</h1>
        <div style="color:#9a9a9a;font-size:13px;">${formatDate(journal.date)}${mood ? ' | ' + mood.emoji + ' ' + mood.label : ''}${journal.title ? ' | ' + escapeHtml(journal.title) : ''}</div>
      </div>
    `)
    await addBlock(`
      <div style="margin:6px 0;">
        <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">📖 今日经文</div>
        <div style="font-size:14px;color:#f0f0f0;font-weight:500;margin:5px 0;white-space:pre-wrap;">${escapeHtml(journal.scripture) || '未记录'}</div>
      </div>
    `)
    if (journal.observation) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">🔍 观察默想</div>
          <div style="background:#1a2433;padding:10px;border-radius:6px;color:#e8e8e8;white-space:pre-wrap;">${escapeHtmlWithBr(journal.observation)}</div>
        </div>
      `)
    }
    if (journal.reflection) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">💭 灵修反思</div>
          <div style="background:#1a2433;padding:10px;border-radius:6px;color:#e8e8e8;white-space:pre-wrap;">${escapeHtmlWithBr(journal.reflection)}</div>
        </div>
      `)
    }
    if (journal.application) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">🌱 行道应用</div>
          <div style="background:rgba(48,209,88,0.1);padding:10px;border-radius:6px;border:1px solid rgba(48,209,88,0.3);color:#1a6b2a;white-space:pre-wrap;">${escapeHtmlWithBr(journal.application)}</div>
        </div>
      `)
    }
    if (journal.prayer) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">🙏 祷告记录</div>
          <div style="background:rgba(255,159,10,0.1);padding:10px;border-radius:6px;border:1px solid rgba(255,159,10,0.3);color:#7a4800;white-space:pre-wrap;font-style:italic;">${escapeHtmlWithBr(journal.prayer)}</div>
        </div>
      `)
    }
    const n = pdf.internal.getNumberOfPages()
    for (let p = 1; p <= n; p++) {
      pdf.setPage(p); pdf.setFontSize(9); pdf.setTextColor(180, 180, 180)
      pdf.text('https://holiness.uk/', PW / 2, PH - 4, { align: 'center' })
    }
    const title = (journal.title || journal.scripture || '灵修日记').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
    pdf.save(`${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) { console.error('PDF generation failed:', err); alert('PDF 生成失败，请重试') }
  finally { document.body.removeChild(el) }
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
        <button className="dj-save-btn" onClick={onEdit}>✏️</button>
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
            <button className="primary-btn" style={{ maxWidth: 160, marginTop: 16 }} onClick={onEdit}>✏️ 填写</button>
          </div>
        )}

        <div className="dj-detail-footer">
          最后更新于 {timeAgo(journal.updated_at)}
        </div>
      </div>
    </div>
  )
}

function exportAllJournalsToTxt(journals) {
  if (!journals || journals.length === 0) return
  let content = `属灵星球 - 灵修日记汇总\n共 ${journals.length} 篇\n\n`
  journals.forEach((journal, i) => {
    content += `${'═'.repeat(40)}\n第 ${i + 1} 篇：${journal.title || '灵修日记'}\n日期：${formatDate(journal.date)}\n${'─'.repeat(40)}\n`
    if (journal.scripture) content += `📖 今日经文\n${journal.scripture}\n\n`
    if (journal.observation) content += `🔍 观察默想\n${journal.observation}\n\n`
    if (journal.reflection) content += `💭 灵修反思\n${journal.reflection}\n\n`
    if (journal.application) content += `✅ 行道应用\n${journal.application}\n\n`
    if (journal.prayer) content += `🙏 祷告记录\n${journal.prayer}\n\n`
  })
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `灵修日记汇总_${new Date().toISOString().slice(0,10)}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportAllJournalsToPdf(journals) {
  if (!journals || journals.length === 0) return
  const { default: jsPDF } = await import('jspdf')
  const { default: html2canvas } = await import('html2canvas')
  const pdf = new jsPDF('p', 'mm', 'a4')
  const PW = pdf.internal.pageSize.getWidth()
  const PH = pdf.internal.pageSize.getHeight()
  const M = 12, cw = PW - M * 2
  let curY = M
  pdf.setFillColor(14, 23, 38); pdf.rect(0, 0, PW, PH, 'F')

  const el = document.createElement('div')
  el.style.cssText = `position:fixed;left:-9999px;top:0;width:${Math.round(cw * 3.78)}px;background:#0e1726;padding:0;font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#e8e8e8;`
  document.body.appendChild(el)

  async function addBlock(html) {
    el.innerHTML = html
    const canvas = await html2canvas(el, { scale: 2, useCORS: true, logging: false, backgroundColor: '#0e1726' })
    const imgH = (canvas.height / canvas.width) * cw
    if (curY + imgH > PH - 10 && curY > M + 5) { pdf.addPage(); pdf.setFillColor(14, 23, 38); pdf.rect(0, 0, PW, PH, 'F'); curY = M }
    pdf.addImage(canvas.toDataURL('image/jpeg', 0.92), 'JPEG', M, curY, cw, imgH)
    curY += imgH + 3
  }

  try {
    await addBlock(`
      <div style="text-align:center;margin-bottom:10px;border-bottom:1px solid #2e3c52;padding-bottom:10px;">
        <h1 style="color:#007aff;font-size:20px;margin:0 0 4px 0;">📔 灵修日记汇总</h1>
        <div style="color:#9a9a9a;font-size:13px;">共 ${journals.length} 篇</div>
      </div>
    `)
    for (let i = 0; i < journals.length; i++) {
      const j = journals[i]
      let html = `<div style="margin:6px 0;border-top:1px solid #2e3c52;padding-top:10px;"><h2 style="color:#f0f0f0;font-size:15px;margin:0 0 4px 0;">${i+1}. ${escapeHtml(j.title||'灵修日记')} <span style="color:#9a9a9a;font-size:12px;">${formatDate(j.date)}</span></h2>`
      if (j.scripture) html += `<p style="color:#007aff;font-size:13px;margin:3px 0;">${escapeHtml(j.scripture)}</p>`
      if (j.reflection) html += `<p style="color:#444;font-size:13px;margin:3px 0;">${escapeHtml(j.reflection)}</p>`
      html += `</div>`
      await addBlock(html)
    }
    const n = pdf.internal.getNumberOfPages()
    for (let p = 1; p <= n; p++) {
      pdf.setPage(p); pdf.setFontSize(9); pdf.setTextColor(180, 180, 180)
      pdf.text('https://holiness.uk/', PW / 2, PH - 4, { align: 'center' })
    }
    pdf.save(`灵修日记汇总_${new Date().toISOString().slice(0,10)}.pdf`)
  } catch(err) { console.error('PDF生成失败', err); alert('PDF 生成失败，请重试') }
  finally { document.body.removeChild(el) }
}

// ── Main Page ────────────────────────────────────────────────
export default function DevotionJournalPage({ user, token, onBack, contained = false }) {
  const [view, setView] = useState('list')   // 'list' | 'editor' | 'detail'
  const [journals, setJournals] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [current, setCurrent] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const listRef = useRef(null)

  async function load(replace = true) {
    setLoading(true)
    setError('')
    try {
      const data = await fetchJournals(token, 50, replace ? 0 : journals.length)
      setTotal(data.total)
      const apiItems = data.items || []

      if (replace) {
        // 合并 localStorage 旧数据（仅在首次加载时合并）
        const legacy = getLegacyLocalJournals()
        const seenIds = new Set(apiItems.map(j => j.id))
        const merged = [
          ...apiItems,
          ...legacy.filter(j => !seenIds.has(j.id)),
        ]
        merged.sort((a, b) => {
          const ta = new Date(b.updated_at || b.created_at || 0).getTime()
          const tb = new Date(a.updated_at || a.created_at || 0).getTime()
          return ta - tb
        })
        console.log(`[devotion] loaded ${apiItems.length} from API + ${legacy.length} legacy = ${merged.length}`)
        setJournals(merged)
      } else {
        setJournals(prev => [...prev, ...apiItems])
      }
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
      if (deleteTarget._source === 'local') {
        // 旧 localStorage 数据：直接从本地删除
        const saved = localStorage.getItem('devotion_notes_personal')
        const arr = saved ? JSON.parse(saved) : []
        // local id 格式为 local_<原id>
        const origId = deleteTarget.id.replace(/^local_/, '')
        const updated = arr.filter(n => String(n.id) !== origId && String(n.createdAt) !== origId)
        localStorage.setItem('devotion_notes_personal', JSON.stringify(updated))
      } else {
        await deleteJournal(deleteTarget.id, token)
      }
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

  // Hooks must be called before any conditional returns
  const { pulling, refreshing, indicatorStyle, indicatorText } = usePullToRefresh(() => load(true), listRef)

  // When rendered inside a tab container, override position:fixed to keep within bounds
  const pageStyle = contained ? { position: 'relative', height: '100%', zIndex: 1 } : {}
  const safeHeaderStyle = contained ? { paddingTop: '14px', paddingBottom: '14px' } : {}

  // ── Not logged in ───────────────────────────────────────────
  if (!user) {
    return (
      <div className="dj-page" style={pageStyle}>
        <header className="dj-header" style={safeHeaderStyle}>
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
      ? { date: current.date || today(), title: current.title || '', scripture: current.scripture || '', observation: current.observation || '', reflection: current.reflection || '', application: current.application || '', prayer: current.prayer || '', mood: current.mood || '', id: current.id }
      : { ...EMPTY_FORM }
    return (
      <div className="dj-page" style={pageStyle}>
        {deleteDialog}
        <JournalEditor
          key={initialForm.id || 'new'}
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
      <div className="dj-page" style={pageStyle}>
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
    <div className="dj-page" style={pageStyle}>
      {deleteDialog}

      <header className="dj-header" style={safeHeaderStyle}>
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

      <div className="dj-list" ref={listRef} style={{ position: 'relative' }}>
        <div style={indicatorStyle}>{indicatorText}</div>
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
              ✏️ 开始写
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
                onEdit={openEdit}
                onDelete={j => setDeleteTarget(j)}
              />
            ))}

            {journals.length < total && (
              <button className="pw-load-more" onClick={() => load(false)}>
                ⬇️ 加载更多 ({total - journals.length})
              </button>
            )}

            <div className="pw-footer-tip">诗篇 119:105 · 你的话是我脚前的灯，是我路上的光</div>
          </>
        )}
      </div>

      {/* Export Bar */}
      {!loading && journals.length > 0 && (
        <div className="sj-export-bar">
          <button className="sj-export-btn-bottom" onClick={e => window.busyBtn(e, () => exportAllJournalsToTxt(journals), "导出 TXT 中…", "✅ TXT 已导出")} title="导出TXT">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            TXT
          </button>
          <button className="sj-export-btn-bottom" onClick={e => window.busyBtn(e, () => exportAllJournalsToPdf(journals), "生成 PDF 中…", "✅ PDF 已导出")} title="导出PDF">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <path d="M9 15l3 3 3-3"/>
              <path d="M12 18V9"/>
            </svg>
            PDF
          </button>
        </div>
      )}
    </div>
  )
}
