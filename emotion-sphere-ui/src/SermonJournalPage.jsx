import { useState } from 'react'
import jsPDF from 'jspdf'

const STORAGE_KEY = 'sermon-journals-v1'

function loadJournals() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

function saveJournals(list) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

function getLastSunday() {
  const d = new Date()
  const day = d.getDay()
  const diff = day === 0 ? 0 : day
  const sunday = new Date(d)
  sunday.setDate(d.getDate() - diff)
  return sunday.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
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
  { key: 'summary',      icon: '📖', label: '讲道主要内容',   placeholder: '本次讲道的核心信息、主题经文、主要论点…', type: 'textarea', rows: 4 },
  { key: 'bibleStudy',   icon: '🔍', label: '查经心得',        placeholder: '本周围绕讲道经文的个人查经反思、新发现…', type: 'textarea', rows: 3 },
  { key: 'reflection',   icon: '🪞', label: '行道反思',        placeholder: '本周实践行道的过程中，哪里做到了？哪里仍然挣扎？', type: 'textarea', rows: 3 },
  { key: 'lesson',       icon: '🌱', label: '生命功课',        placeholder: '神借这段经历在我生命中刻下的功课…', type: 'textarea', rows: 3 },
  { key: 'conclusion',   icon: '⚖️',  label: '总结得失',        placeholder: '这一周的得与失，坦诚面对自己…', type: 'textarea', rows: 3 },
  { key: 'encouragement',icon: '🌟', label: '鼓励与感恩',      placeholder: '一句话鼓励自己，或记录一个感恩的时刻…', type: 'textarea', rows: 2 },
]

export default function SermonJournalPage({ user, onBack }) {
  const [journals, setJournals] = useState(loadJournals)
  const [activeId, setActiveId] = useState(null)
  const [view, setView] = useState('list') // 'list' | 'edit' | 'detail'

  const current = journals.find(j => j.id === activeId)

  function newJournal() {
    const j = emptyJournal()
    const updated = [j, ...journals]
    setJournals(updated)
    saveJournals(updated)
    setActiveId(j.id)
    setView('edit')
  }

  function updateField(field, value) {
    setJournals(prev => {
      const next = prev.map(j => j.id === activeId ? { ...j, [field]: value } : j)
      saveJournals(next)
      return next
    })
  }

  function updateListField(field, idx, value) {
    setJournals(prev => {
      const next = prev.map(j => {
        if (j.id !== activeId) return j
        const arr = [...j[field]]
        arr[idx] = value
        return { ...j, [field]: arr }
      })
      saveJournals(next)
      return next
    })
  }

  function addListItem(field) {
    setJournals(prev => {
      const next = prev.map(j =>
        j.id === activeId ? { ...j, [field]: [...j[field], ''] } : j
      )
      saveJournals(next)
      return next
    })
  }

  function removeListItem(field, idx) {
    setJournals(prev => {
      const next = prev.map(j => {
        if (j.id !== activeId) return j
        const arr = j[field].filter((_, i) => i !== idx)
        return { ...j, [field]: arr.length ? arr : [''] }
      })
      saveJournals(next)
      return next
    })
  }

  function deleteJournal(id) {
    const next = journals.filter(j => j.id !== id)
    setJournals(next)
    saveJournals(next)
    if (activeId === id) {
      setActiveId(null)
      setView('list')
    }
  }

  function openDetail(id) {
    setActiveId(id)
    setView('detail')
  }

  function openEdit(id) {
    setActiveId(id)
    setView('edit')
  }

  function exportToTxt() {
    if (!current) return
    let content = `讲道日志\n\n`
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
    a.download = `讲道日志_${current.date.replace(/\//g, '-')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportToPdf() {
    if (!current) return
    const doc = new jsPDF()
    
    let y = 20
    const lineHeight = 7
    const pageHeight = 280
    const maxWidth = 170
    
    // Title
    doc.setFontSize(18)
    doc.text('讲道日志', 20, y)
    y += 12
    
    // Date
    doc.setFontSize(11)
    doc.text(`日期：${current.date}`, 20, y)
    y += 8
    
    if (current.title) {
      doc.text(`讲题：${current.title}`, 20, y)
      y += 8
    }
    if (current.scripture) {
      doc.text(`经文：${current.scripture}`, 20, y)
      y += 8
    }
    if (current.preacher) {
      doc.text(`讲道者：${current.preacher}`, 20, y)
      y += 8
    }
    y += 5
    
    // Sections
    SECTION_CONFIG.forEach(({ key, label }) => {
      if (current[key]?.trim()) {
        if (y > pageHeight - 20) {
          doc.addPage()
          y = 20
        }
        doc.setFontSize(12)
        doc.setFont(undefined, 'bold')
        doc.text(label, 20, y)
        y += 6
        doc.setFont(undefined, 'normal')
        doc.setFontSize(10)
        
        const lines = doc.splitTextToSize(current[key], maxWidth)
        lines.forEach((line) => {
          if (y > pageHeight) {
            doc.addPage()
            y = 20
          }
          doc.text(line, 20, y)
          y += lineHeight
        })
        y += 4
      }
    })
    
    // Questions
    if (current.questions.some(q => q.trim())) {
      if (y > pageHeight - 20) {
        doc.addPage()
        y = 20
      }
      doc.setFontSize(12)
      doc.setFont(undefined, 'bold')
      doc.text('思考题', 20, y)
      y += 6
      doc.setFont(undefined, 'normal')
      doc.setFontSize(10)
      
      current.questions.filter(q => q.trim()).forEach((q, i) => {
        if (y > pageHeight) {
          doc.addPage()
          y = 20
        }
        const lines = doc.splitTextToSize(`${i + 1}. ${q}`, maxWidth)
        lines.forEach((line) => {
          if (y > pageHeight) {
            doc.addPage()
            y = 20
          }
          doc.text(line, 20, y)
          y += lineHeight
        })
      })
      y += 4
    }
    
    // Practices
    if (current.practices.some(p => p.trim())) {
      if (y > pageHeight - 20) {
        doc.addPage()
        y = 20
      }
      doc.setFontSize(12)
      doc.setFont(undefined, 'bold')
      doc.text('本周实践行道', 20, y)
      y += 6
      doc.setFont(undefined, 'normal')
      doc.setFontSize(10)
      
      current.practices.filter(p => p.trim()).forEach((p, i) => {
        if (y > pageHeight) {
          doc.addPage()
          y = 20
        }
        const lines = doc.splitTextToSize(`${i + 1}. ${p}`, maxWidth)
        lines.forEach((line) => {
          if (y > pageHeight) {
            doc.addPage()
            y = 20
          }
          doc.text(line, 20, y)
          y += lineHeight
        })
      })
      y += 4
    }
    
    // Encouragement
    if (current.encouragement?.trim()) {
      if (y > pageHeight - 20) {
        doc.addPage()
        y = 20
      }
      doc.setFontSize(12)
      doc.setFont(undefined, 'bold')
      doc.text('鼓励与感恩', 20, y)
      y += 6
      doc.setFont(undefined, 'normal')
      doc.setFontSize(10)
      
      const lines = doc.splitTextToSize(current.encouragement, maxWidth)
      lines.forEach((line) => {
        if (y > pageHeight) {
          doc.addPage()
          y = 20
        }
        doc.text(line, 20, y)
        y += lineHeight
      })
    }
    
    doc.save(`讲道日志_${current.date.replace(/\//g, '-')}.pdf`)
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
            {view === 'list' ? '📖 讲道日志' : view === 'edit' ? '✏️ 编辑日志' : '📖 日志详情'}
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
          <button className="sj-new-btn" onClick={newJournal} title="新建日志">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
        ) : (
          <div className="sj-header-actions">
            {(view === 'edit' || view === 'detail') && (
              <>
                <button className="sj-export-btn" onClick={exportToTxt} title="导出TXT">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                  </svg>
                  导出TXT
                </button>
                <button className="sj-export-btn" onClick={exportToPdf} title="导出PDF">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <path d="M9 15l3 3 3-3"/>
                    <path d="M12 18V9"/>
                  </svg>
                  导出PDF
                </button>
              </>
            )}
            {view === 'edit' ? (
              <button className="sj-new-btn" onClick={() => setView('detail')} title="预览">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            ) : (
              <button className="sj-new-btn" onClick={() => setView('edit')} title="编辑">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            )}
          </div>
        )}
      </header>

      {/* LIST VIEW */}
      {view === 'list' && (
        <div className="sj-list">
          {journals.length === 0 ? (
            <div className="sj-empty">
              <div className="sj-empty-icon">📖</div>
              <div className="sj-empty-title">还没有讲道日志</div>
              <div className="sj-empty-sub">点击右上角 + 开始记录本周讲道</div>
              <button className="checkin-submit-btn" style={{ maxWidth: 220, marginTop: 20 }} onClick={newJournal}>
                新建第一篇日志
              </button>
            </div>
          ) : (
            journals.map(j => (
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
                <div className="sj-card-actions" onClick={e => e.stopPropagation()}>
                  <button className="sj-card-btn" onClick={() => openEdit(j.id)}>编辑</button>
                  <button className="sj-card-btn danger" onClick={() => {
                    if (window.confirm('确定删除此日志？')) deleteJournal(j.id)
                  }}>删除</button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* EDIT VIEW */}
      {view === 'edit' && current && (
        <div className="sj-edit-scroll">
          <div className="sj-form">
            {/* Meta info */}
            <section className="sj-section glass">
              <div className="sj-section-title">🗓 主日基本信息</div>
              <div className="sj-field-group">
                <div className="sj-field">
                  <label className="sj-label">主日日期</label>
                  <input
                    className="sj-input"
                    value={current.date}
                    onChange={e => updateField('date', e.target.value)}
                    placeholder={getLastSunday()}
                  />
                </div>
                <div className="sj-field">
                  <label className="sj-label">讲题</label>
                  <input
                    className="sj-input"
                    value={current.title}
                    onChange={e => updateField('title', e.target.value)}
                    placeholder="本次讲道的题目"
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

            <div style={{ height: 32 }} />
          </div>
        </div>
      )}
    </div>
  )
}
