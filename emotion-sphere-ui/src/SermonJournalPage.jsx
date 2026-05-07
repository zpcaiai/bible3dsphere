import { useEffect, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { fetchSermonJournals, saveSermonJournal, deleteSermonJournal } from './api'

function getLastSunday() {
  const d = new Date()
  const day = d.getDay()
  const diff = day === 0 ? 0 : day
  const sunday = new Date(d)
  sunday.setDate(d.getDate() - diff)
  return sunday.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

function getWeekNumber(date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + 4 - (d.getDay() || 7))
  const yearStart = new Date(d.getFullYear(), 0, 1)
  const weekNo = Math.ceil(((d - yearStart) / 86400000 + 1) / 7)
  return weekNo
}

function formatDateWithWeek(dateStr) {
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  const day = d.getDate()
  const week = getWeekNumber(d)
  return `${year}年${month}月${day}日,第${week}周`
}

function parseDateFromFormat(formatStr) {
  if (!formatStr) return ''
  const match = formatStr.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/)
  if (!match) return formatStr
  const [, year, month, day] = match
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function getPreviousSunday(dateStr) {
  const d = new Date(dateStr)
  d.setDate(d.getDate() - 7)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

function getNextSunday(dateStr) {
  const d = new Date(dateStr)
  d.setDate(d.getDate() + 7)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

function emptyJournal() {
  return {
    id: Date.now().toString(),
    date: getLastSunday(),
    title: '',
    preacher: '',
    scripture: '',
    summary: '',
    questions: ['', '', ''],
    bibleStudy: '',
    practices: ['', '', ''],
    reflection: '',
    lesson: '',
    conclusion: '',
    encouragement: '',
    phase: 'active',
    createdAt: Date.now(),
  }
}

const SECTION_CONFIG = [
  { key: 'summary',      icon: '📖', label: '信息主要内容',   placeholder: '本次信息的核心内容、主题经文、主要论点…', type: 'textarea', rows: 4 },
  { key: 'bibleStudy',   icon: '🔍', label: '查经心得',        placeholder: '本周围绕信息经文的个人查经反思、新发现…', type: 'textarea', rows: 3 },
  { key: 'reflection',   icon: '🪞', label: '行道反思',        placeholder: '本周实践行道的过程中，哪里做到了？哪里仍然挣扎？', type: 'textarea', rows: 3 },
  { key: 'lesson',       icon: '🌱', label: '生命功课',        placeholder: '神借这段经历在我生命中刻下的功课…', type: 'textarea', rows: 3 },
  { key: 'conclusion',   icon: '⚖️',  label: '总结得失',        placeholder: '这一周的得与失，坦诚面对自己…', type: 'textarea', rows: 3 },
  { key: 'encouragement',icon: '🌟', label: '鼓励与感恩',      placeholder: '一句话鼓励自己，或记录一个感恩的时刻…', type: 'textarea', rows: 2 },
]

const ADMIN_EMAIL = 'zpclord@sina.com'

export default function SermonJournalPage({ user, token, onBack }) {
  const [journals, setJournals] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [view, setView] = useState('list') // 'list' | 'edit' | 'detail'
  const [saveStatus, setSaveStatus] = useState('') // 'saving' | 'saved' | ''
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [total, setTotal] = useState(0)
  const [isAdmin, setIsAdmin] = useState(false)

  const current = journals.find(j => j.id === activeId)

  // Load journals from API
  async function load() {
    if (!user) return
    setLoading(true)
    setError('')
    try {
      const data = await fetchSermonJournals(token, 50, 0)
      setJournals(data.items || [])
      setTotal(data.total || 0)
      setIsAdmin(data.is_admin || false)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [user, token])

  // 权限检查：非管理员不能访问编辑视图
  useEffect(() => {
    if (view === 'edit' && !isAdmin && activeId) {
      setView('detail')
    }
  }, [view, isAdmin, activeId])

  async function newJournal() {
    const j = emptyJournal()
    setJournals(prev => [j, ...prev])
    setActiveId(j.id)
    setView('edit')
    // Save to API
    try {
      await saveSermonJournal(j, token)
    } catch (e) {
      console.error('Failed to create journal:', e)
    }
  }

  function updateField(field, value) {
    setJournals(prev => prev.map(j => j.id === activeId ? { ...j, [field]: value } : j))
  }

  function updateListField(field, idx, value) {
    setJournals(prev => prev.map(j => {
      if (j.id !== activeId) return j
      const arr = [...j[field]]
      arr[idx] = value
      return { ...j, [field]: arr }
    }))
  }

  function addListItem(field) {
    setJournals(prev => prev.map(j =>
      j.id === activeId ? { ...j, [field]: [...j[field], ''] } : j
    ))
  }

  function removeListItem(field, idx) {
    setJournals(prev => prev.map(j => {
      if (j.id !== activeId) return j
      const arr = j[field].filter((_, i) => i !== idx)
      return { ...j, [field]: arr.length ? arr : [''] }
    }))
  }

  async function deleteJournal(id) {
    try {
      await deleteSermonJournal(id, token)
      const next = journals.filter(j => j.id !== id)
      setJournals(next)
      if (activeId === id) {
        setActiveId(null)
        setView('list')
      }
    } catch (e) {
      console.error('Failed to delete journal:', e)
    }
  }

  function openDetail(id) {
    setActiveId(id)
    setView('detail')
  }

  function openEdit(id) {
    if (!isAdmin) {
      // 非管理员只能查看详情
      openDetail(id)
      return
    }
    setActiveId(id)
    setView('edit')
  }

  async function handleSave() {
    if (!current) return
    setSaveStatus('saving')
    try {
      const result = await saveSermonJournal(current, token)
      // Update local state with server response (includes ID)
      if (result.journal) {
        setJournals(prev => prev.map(j => j.id === current.id ? { ...j, ...result.journal } : j))
      }
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus(''), 2000)
    } catch (e) {
      console.error('Failed to save:', e)
      setSaveStatus('')
    }
  }

  function exportToTxt() {
    if (!current) return
    let content = `主日信息\n\n`
    content += `日期：${current.date}\n`
    content += `讲题：${current.title || '（未填写）'}\n`
    if (current.scripture) content += `经文：${current.scripture}\n`
    if (current.preacher) content += `讲道者：${current.preacher}\n`
    content += `\n`
    
    SECTION_CONFIG.forEach(({ key, label }) => {
      if (current[key]?.trim()) {
        content += `${label}\n${current[key]}\n\n`
      }
    })
    
    if (current.questions.some(q => q.trim())) {
      content += `思考题\n`
      current.questions.filter(q => q.trim()).forEach((q, i) => {
        content += `${i + 1}. ${q}\n`
      })
      content += `\n`
    }
    
    if (current.practices.some(p => p.trim())) {
      content += `本周实践行道\n`
      current.practices.filter(p => p.trim()).forEach((p, i) => {
        content += `${i + 1}. ${p}\n`
      })
      content += `\n`
    }
    
    if (current.encouragement?.trim()) {
      content += `鼓励与感恩\n${current.encouragement}\n`
    }
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const now = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const datetime = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
    const title = (current.title || '主日信息').replace(/[\\/:*?"<>|]/g, '')
    a.download = `${title}_${datetime}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function exportToPdf() {
    if (!current) return

    // Create a hidden container for PDF generation
    const container = document.createElement('div')
    container.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 794px; background: #0d0d1a; padding: 40px; font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; line-height: 1.8; color: #ffffff;'
    document.body.appendChild(container)

    // Build content with dark theme matching the app
    let content = `
      <div style="text-align: center; margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px;">
        <h1 style="color: #007aff; font-size: 24px; margin: 0 0 10px 0;">主日信息</h1>
        <div style="color: rgba(255,255,255,0.5); font-size: 14px;">日期：${current.date}${current.preacher ? ' | 讲道者：' + current.preacher : ''}</div>
      </div>
    `

    if (current.title) {
      content += `<div style="text-align: center; font-size: 18px; font-weight: bold; color: #ffffff; margin: 20px 0 10px;">${current.title}</div>`
    }
    if (current.scripture) {
      content += `<div style="text-align: center; font-style: italic; color: rgba(255,255,255,0.6); margin-bottom: 30px; font-size: 14px;">${current.scripture}</div>`
    }

    // Sections
    SECTION_CONFIG.forEach(({ key, label }) => {
      if (current[key]?.trim()) {
        content += `
          <div style="margin: 25px 0;">
            <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); border-bottom: 1px solid rgba(0,122,255,0.4); padding-bottom: 6px; margin-bottom: 10px;">${label}</div>
            <div style="font-size: 14px; white-space: pre-wrap; color: rgba(255,255,255,0.88); background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px;">${current[key].replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
          </div>
        `
      }
    })

    // Questions
    if (current.questions.some(q => q.trim())) {
      content += `
          <div style="margin: 20px 0;">
            <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); border-bottom: 1px solid rgba(0,122,255,0.4); padding-bottom: 6px; margin-bottom: 10px;">思考题</div>
            <ol style="padding-left: 25px; color: rgba(255,255,255,0.88);">
              ${current.questions.filter(q => q.trim()).map(q => `<li style="margin: 10px 0; font-size: 14px;">${q.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')}</li>`).join('')}
            </ol>
          </div>
        `
    }

    // Practices
    if (current.practices.some(p => p.trim())) {
      content += `
          <div style="margin: 20px 0;">
            <div style="font-size: 15px; font-weight: bold; color: rgba(255,255,255,0.78); border-bottom: 1px solid rgba(0,122,255,0.4); padding-bottom: 6px; margin-bottom: 10px;">本周实践行道</div>
            <ol style="padding-left: 25px; color: rgba(255,255,255,0.88);">
              ${current.practices.filter(p => p.trim()).map(p => `<li style="margin: 10px 0; font-size: 14px;">${p.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')}</li>`).join('')}
            </ol>
          </div>
        `
    }

    // Encouragement
    if (current.encouragement?.trim()) {
      content += `
          <div style="margin-top: 30px; background: rgba(255,149,0,0.15); padding: 20px; border-radius: 8px; border-left: 4px solid #ff9500;">
            <div style="font-weight: bold; margin-bottom: 10px; color: #ff9500;">鼓励与感恩</div>
            <div style="color: rgba(255,255,255,0.88);">${current.encouragement.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')}</div>
          </div>
        `
    }

    container.innerHTML = content

    // Generate filename
    const now = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const datetime = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`
    const filename = `${current.title ? current.title.replace(/[\\/:*?"<>|]/g, '') : '主日信息'}_${datetime}.pdf`

    // Generate PDF using html2canvas + jsPDF
    try {
      const canvas = await html2canvas(container, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff'
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

      // Add first page
      pdf.addImage(imgData, 'PNG', 10, position, scaledWidth, scaledHeight)
      heightLeft -= (pdfHeight - 20)

      // Add more pages if content is long
      while (heightLeft > 0) {
        position = heightLeft - scaledHeight + 10
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 10, position, scaledWidth, scaledHeight)
        heightLeft -= (pdfHeight - 20)
      }

      pdf.save(filename)
    } catch (err) {
      console.error('PDF generation failed:', err)
      alert('PDF 生成失败，请重试')
    } finally {
      document.body.removeChild(container)
    }
  }

  const progress = current ? (() => {
    const fields = ['title', 'summary', 'bibleStudy', 'reflection', 'lesson', 'conclusion', 'encouragement']
    const filled = fields.filter(f => current[f]?.trim()).length
    const qFilled = current.questions.filter(q => q.trim()).length > 0 ? 1 : 0
    const pFilled = current.practices.filter(p => p.trim()).length > 0 ? 1 : 0
    return Math.round(((filled + qFilled + pFilled) / (fields.length + 2)) * 100)
  })() : 0

  return (
    <div className="sj-page">
      {/* Header */}
      <header className="sj-header">
        <button className="checkin-back-btn" onClick={view === 'list' ? onBack : () => setView('list')} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="sj-header-center">
          <div className="sj-title">
            {view === 'list' ? '📖 主日信息' : view === 'edit' ? '✏️ 编辑信息' : '📖 主日信息'}
          </div>
          {view === 'list' && (
            <div className="sj-subtitle">{journals.length > 0 ? `共 ${journals.length} 篇` : '记录你的属灵成长'}</div>
          )}
          {view === 'edit' && current && (
            <div className="sj-progress-bar">
              <div className="sj-progress-fill" style={{ width: `${progress}%` }} />
            </div>
          )}
        </div>
        {view === 'list' ? (
          isAdmin && (
            <button className="sj-new-btn" onClick={newJournal} title="新建信息">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
          )
        ) : (
          view === 'edit' ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {saveStatus === 'saving' && (
                <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>保存中…</span>
              )}
              {saveStatus === 'saved' && (
                <span style={{ fontSize: '12px', color: '#34c759' }}>✓ 已保存</span>
              )}
              <button className="sj-new-btn" onClick={handleSave} title="保存">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                  <polyline points="17 21 17 13 7 13 7 21"/>
                  <polyline points="7 3 7 8 15 8"/>
                </svg>
              </button>
              <button className="sj-new-btn" onClick={() => setView('detail')} title="预览">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          ) : (
            isAdmin && (
              <button className="sj-new-btn" onClick={() => setView('edit')} title="编辑">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            )
          )
        )}
      </header>

      {/* LIST VIEW */}
      {view === 'list' && (
        <div className="sj-list">
          {journals.length === 0 ? (
            <div className="sj-empty">
              <div className="sj-empty-icon">📖</div>
              <div className="sj-empty-title">还没有主日信息</div>
              <div className="sj-empty-sub">{isAdmin ? '点击右上角 + 开始记录本周信息' : '暂无主日信息'}</div>
              {isAdmin && (
                <button className="checkin-submit-btn" style={{ maxWidth: 220, marginTop: 20 }} onClick={newJournal}>
                  新建第一篇信息
                </button>
              )}
            </div>
          ) : (
            journals.slice().reverse().map(j => (
              <div key={j.id} className="sj-card glass" onClick={() => openDetail(j.id)}>
                <div className="sj-card-top">
                  <div className="sj-card-date">{j.date}</div>
                  <div className="sj-card-progress">{(() => {
                    const fields = ['title', 'summary', 'bibleStudy', 'reflection', 'lesson', 'conclusion', 'encouragement']
                    const filled = fields.filter(f => j[f]?.trim()).length
                    const qFilled = j.questions?.filter(q => q.trim()).length > 0 ? 1 : 0
                    const pFilled = j.practices?.filter(p => p.trim()).length > 0 ? 1 : 0
                    return Math.round(((filled + qFilled + pFilled) / (fields.length + 2)) * 100)
                  })()}%</div>
                </div>
                <div className="sj-card-title">{j.title || '（未填写讲题）'}</div>
                {j.scripture && <div className="sj-card-scripture">📜 {j.scripture}</div>}
                {j.preacher && <div className="sj-card-preacher">🎙 {j.preacher}</div>}
                {j.summary && <div className="sj-card-preview">{j.summary.slice(0, 60)}{j.summary.length > 60 ? '…' : ''}</div>}
                {isAdmin && (
                  <div className="sj-card-actions" onClick={e => e.stopPropagation()}>
                    <button className="sj-card-btn" onClick={() => openEdit(j.id)}>编辑</button>
                    <button className="sj-card-btn danger" onClick={() => {
                      if (window.confirm('确定删除此信息？')) deleteJournal(j.id)
                    }}>删除</button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* EDIT VIEW - 仅管理员可访问 */}
      {view === 'edit' && current && isAdmin && (
        <div className="sj-edit-scroll">
          <div className="sj-form">
            {/* Meta info */}
            <section className="sj-section glass">
              <div className="sj-section-title">🗓 主日基本信息</div>
              <div className="sj-field-group">
                <div className="sj-field">
                  <label className="sj-label">主日日期</label>
                  <div className="sj-date-picker">
                    <button
                      className="sj-date-btn"
                      onClick={() => updateField('date', getPreviousSunday(current.date))}
                      title="上一周"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="15 18 9 12 15 6" />
                      </svg>
                    </button>
                    <div className="sj-date-display">
                      {formatDateWithWeek(current.date)}
                    </div>
                    <button
                      className="sj-date-btn"
                      onClick={() => updateField('date', getNextSunday(current.date))}
                      title="下一周"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="9 18 15 12 9 6" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div className="sj-field">
                  <label className="sj-label">讲题</label>
                  <input
                    className="sj-input"
                    value={current.title}
                    onChange={e => updateField('title', e.target.value)}
                    placeholder="本次信息的题目"
                  />
                </div>
                <div className="sj-field">
                  <label className="sj-label">主要经文</label>
                  <input
                    className="sj-input"
                    value={current.scripture}
                    onChange={e => updateField('scripture', e.target.value)}
                    placeholder="如：约翰福音 15:1-17"
                  />
                </div>
                <div className="sj-field">
                  <label className="sj-label">讲道者</label>
                  <input
                    className="sj-input"
                    value={current.preacher}
                    onChange={e => updateField('preacher', e.target.value)}
                    placeholder="牧师 / 传道人姓名"
                  />
                </div>
              </div>
            </section>

            {/* Main content sections */}
            {SECTION_CONFIG.map(({ key, icon, label, placeholder, rows }) => (
              <section key={key} className="sj-section glass">
                <div className="sj-section-title">{icon} {label}</div>
                <textarea
                  className="sj-textarea"
                  placeholder={placeholder}
                  value={current[key]}
                  onChange={e => updateField(key, e.target.value)}
                  rows={rows}
                />
              </section>
            ))}

            {/* Questions */}
            <section className="sj-section glass">
              <div className="sj-section-title">💬 思考题</div>
              <div className="sj-list-fields">
                {current.questions.map((q, i) => (
                  <div key={i} className="sj-list-row">
                    <span className="sj-list-num">{i + 1}</span>
                    <textarea
                      className="sj-textarea sj-list-input"
                      placeholder={`思考题 ${i + 1}…`}
                      value={q}
                      onChange={e => updateListField('questions', i, e.target.value)}
                      rows={2}
                    />
                    {current.questions.length > 1 && (
                      <button className="sj-list-del" onClick={() => removeListItem('questions', i)}>×</button>
                    )}
                  </div>
                ))}
                <button className="sj-add-btn" onClick={() => addListItem('questions')}>+ 增加思考题</button>
              </div>
            </section>

            {/* Practices */}
            <section className="sj-section glass">
              <div className="sj-section-title">🚶 本周实践行道</div>
              <div className="sj-list-fields">
                {current.practices.map((p, i) => (
                  <div key={i} className="sj-list-row">
                    <span className="sj-list-num">{i + 1}</span>
                    <input
                      className="sj-input sj-list-input"
                      placeholder={`实践 ${i + 1}：具体可执行的行动…`}
                      value={p}
                      onChange={e => updateListField('practices', i, e.target.value)}
                    />
                    {current.practices.length > 1 && (
                      <button className="sj-list-del" onClick={() => removeListItem('practices', i)}>×</button>
                    )}
                  </div>
                ))}
                <button className="sj-add-btn" onClick={() => addListItem('practices')}>+ 增加实践</button>
              </div>
            </section>

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button
                onClick={handleSave}
                disabled={saveStatus === 'saving'}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  borderRadius: '10px',
                  border: 'none',
                  background: saveStatus === 'saved' ? '#34c759' : 'linear-gradient(135deg, #007aff, #5e5ce6)',
                  color: '#fff',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: saveStatus === 'saving' ? 'wait' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  boxShadow: '0 2px 8px rgba(0,122,255,0.3)',
                  transition: 'all 0.2s ease',
                }}
              >
                {saveStatus === 'saving' ? (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 1s linear infinite' }}>
                      <polyline points="23 4 23 10 17 10"/>
                      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                    保存中…
                  </>
                ) : saveStatus === 'saved' ? (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    已保存
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                      <polyline points="17 21 17 13 7 13 7 21"/>
                      <polyline points="7 3 7 8 15 8"/>
                    </svg>
                    保存ujj
                  </>
                )}
              </button>
            </div>

            <div className="sj-export-bar">
              <button className="sj-export-btn-bottom" onClick={exportToTxt} title="导出TXT">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
                导出TXT
              </button>
              <button className="sj-export-btn-bottom" onClick={exportToPdf} title="导出PDF（打印为PDF）">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <path d="M9 15l3 3 3-3"/>
                  <path d="M12 18V9"/>
                </svg>
                导出PDF
              </button>
            </div>
            <div style={{ height: 40 }} />
          </div>
        </div>
      )}

      {/* DETAIL VIEW */}
      {view === 'detail' && current && (
        <div className="sj-detail-scroll">
          <div className="sj-detail">
            {/* Title block */}
            <div className="sj-detail-hero glass">
              <div className="sj-detail-date">{current.date}</div>
              <div className="sj-detail-title">{current.title || '（未填写讲题）'}</div>
              {current.scripture && <div className="sj-detail-scripture">📜 {current.scripture}</div>}
              {current.preacher && <div className="sj-detail-preacher">🎙 {current.preacher}</div>}
              <div className="sj-detail-progress-wrap">
                <div className="sj-detail-progress-bar">
                  <div className="sj-progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <span className="sj-detail-progress-label">完成度 {progress}%</span>
              </div>
            </div>

            {SECTION_CONFIG.map(({ key, icon, label }) => current[key]?.trim() ? (
              <div key={key} className="sj-detail-block glass">
                <div className="sj-detail-block-title">{icon} {label}</div>
                <div className="sj-detail-block-text">{current[key]}</div>
              </div>
            ) : null)}

            {current.questions.some(q => q.trim()) && (
              <div className="sj-detail-block glass">
                <div className="sj-detail-block-title">💬 思考题</div>
                {current.questions.filter(q => q.trim()).map((q, i) => (
                  <div key={i} className="sj-detail-q-row">
                    <span className="sj-detail-q-num">Q{i + 1}</span>
                    <span className="sj-detail-q-text">{q}</span>
                  </div>
                ))}
              </div>
            )}

            {current.practices.some(p => p.trim()) && (
              <div className="sj-detail-block glass">
                <div className="sj-detail-block-title">🚶 本周实践行道</div>
                {current.practices.filter(p => p.trim()).map((p, i) => (
                  <div key={i} className="sj-detail-practice-row">
                    <span className="sj-detail-check">○</span>
                    <span>{p}</span>
                  </div>
                ))}
              </div>
            )}

            {current.encouragement?.trim() && (
              <div className="sj-detail-encourage">
                <span className="sj-detail-encourage-icon">🌟</span>
                <span className="sj-detail-encourage-text">{current.encouragement}</span>
              </div>
            )}

            <div className="sj-export-bar">
              <button className="sj-export-btn-bottom" onClick={exportToTxt} title="导出TXT">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
                导出TXT
              </button>
              <button className="sj-export-btn-bottom" onClick={exportToPdf} title="导出PDF（打印为PDF）">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <path d="M9 15l3 3 3-3"/>
                  <path d="M12 18V9"/>
                </svg>
                导出PDF
              </button>
            </div>
            <div style={{ height: 32 }} />
          </div>
        </div>
      )}
    </div>
  )
}
