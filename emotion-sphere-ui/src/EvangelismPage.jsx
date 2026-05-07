import { useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { amenEvangelismPrayer, deleteEvangelismPrayer, fetchEvangelismPrayers, restoreEvangelismPrayer, submitEvangelismPrayer, updateEvangelismPrayer } from './api'

const AMEN_KEY = 'evangelism-amened-v1'

function loadAmened() {
  try { return new Set(JSON.parse(localStorage.getItem(AMEN_KEY) || '[]')) }
  catch { return new Set() }
}
function saveAmened(set) {
  localStorage.setItem(AMEN_KEY, JSON.stringify([...set]))
}

function timeAgo(ts) {
  const diff = Math.floor(Date.now() / 1000 - ts)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} 天前`
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function getWeekKey(ts) {
  const d = new Date(ts * 1000)
  const year = d.getFullYear()
  const startOfYear = new Date(year, 0, 1)
  const dayOfYear = Math.floor((d - startOfYear) / 86400000) + 1
  const weekNum = Math.ceil(dayOfYear / 7)
  return `${year}-W${weekNum}`
}

function formatWeekLabel(ts) {
  const d = new Date(ts * 1000)
  const year = d.getFullYear()
  const startOfYear = new Date(year, 0, 1)
  const dayOfYear = Math.floor((d - startOfYear) / 86400000) + 1
  const weekNum = Math.ceil(dayOfYear / 7)
  return `${year}年 第${weekNum}周`
}

function formatDateTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function exportAllPrayersToTxt(items) {
  if (!items || items.length === 0) return
  let content = `情感星球 - 传FY祷告墙\n`
  content += `导出时间：${new Date().toLocaleString('zh-CN')}\n`
  content += `共 ${items.length} 条传福音祷告\n\n`
  
  items.forEach((prayer, i) => {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n`
    content += `  第 ${i + 1} 条\n`
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `作者：${prayer.nickname}\n`
    content += `时间：${formatDateTime(prayer.created_at)}\n\n`
    content += `${prayer.content}\n\n`
    if (prayer.amen_count > 0) {
      content += `🙏 ${prayer.amen_count} 人同心代祷\n\n`
    }
  })
  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `传FY祷告墙_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportAllPrayersToPdf(items) {
  if (!items || items.length === 0) return
  
  const container = document.createElement('div')
  container.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 794px; background: #0d0d1a; padding: 40px; font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; line-height: 1.8; color: #ffffff;'
  document.body.appendChild(container)
  
  let content = `
    <div style="text-align: center; margin-bottom: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px;">
      <h1 style="color: #ff6b6b; font-size: 22px; margin: 0 0 10px 0;">🌍 传FY祷告墙</h1>
      <div style="color: rgba(255,255,255,0.5); font-size: 13px;">
        导出时间：${new Date().toLocaleString('zh-CN')} | 共 ${items.length} 条传福音祷告
      </div>
    </div>
  `
  
  items.forEach((prayer, i) => {
    content += `
      <div style="margin: 24px 0; padding: 16px; background: rgba(255,255,255,0.05); border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #ff6b6b, #ff9f0a); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; color: #fff;">
            ${prayer.nickname?.[0] || '🌍'}
          </div>
          <div>
            <div style="font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.9);">${prayer.nickname}</div>
            <div style="font-size: 11px; color: rgba(255,255,255,0.4);">${formatDateTime(prayer.created_at)}</div>
          </div>
        </div>
        <div style="font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.7; white-space: pre-wrap;">${prayer.content.replace(/\n/g, '<br>')}</div>
        ${prayer.amen_count > 0 ? `<div style="margin-top: 10px; font-size: 12px; color: #ff9f0a;">🙏 ${prayer.amen_count} 人同心代祷</div>` : ''}
      </div>
    `
  })
  
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
    
    pdf.save(`传FY祷告墙_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) {
    console.error('PDF generation failed:', err)
    alert('PDF 生成失败，请重试')
  } finally {
    document.body.removeChild(container)
  }
}

function Avatar({ nickname }) {
  const char = nickname?.[0] || '🌍'
  const colors = ['#ff6b6b','#ff9f0a','#34c759','#007aff','#5e5ce6','#af52de']
  const idx = (nickname?.charCodeAt(0) || 0) % colors.length
  return (
    <div style={{
      width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
      background: `linear-gradient(135deg, ${colors[idx]}, ${colors[(idx+2)%colors.length]})`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 15, fontWeight: 700, color: '#fff',
    }}>
      {char}
    </div>
  )
}

export default function EvangelismPage({ user, token, onBack }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [amened, setAmened] = useState(loadAmened)
  const [showCompose, setShowCompose] = useState(false)
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitDone, setSubmitDone] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState('')
  const [deletingId, setDeletingId] = useState(null)
  const textareaRef = useRef(null)
  const editTextareaRef = useRef(null)
  const PAGE = 40

  async function load(replace = true) {
    try {
      replace ? setLoading(true) : setLoadingMore(true)
      const data = await fetchEvangelismPrayers(PAGE, replace ? 0 : items.length, token)
      setTotal(data.total || 0)
      const sortedItems = (data.items || []).sort((a, b) => (b.created_at || 0) - (a.created_at || 0))
      setItems(prev => replace ? sortedItems : [...prev, ...sortedItems])
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (showCompose) setTimeout(() => textareaRef.current?.focus(), 100)
  }, [showCompose])

  async function handleAmen(id) {
    if (amened.has(id)) return
    const next = new Set(amened)
    next.add(id)
    setAmened(next)
    saveAmened(next)
    setItems(prev => prev.map(p => p.id === id ? { ...p, amen_count: p.amen_count + 1 } : p))
    try { await amenEvangelismPrayer(id, token) } catch { /* optimistic */ }
  }

  async function handleSubmit() {
    if (!draft.trim() || submitting) return
    setSubmitting(true)
    try {
      await submitEvangelismPrayer(draft.trim(), false, token)
      setDraft('')
      setSubmitDone(true)
      setShowCompose(false)
      await load(true)
      setTimeout(() => setSubmitDone(false), 3000)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  function startEdit(prayer) {
    setEditingId(prayer.id)
    setEditDraft(prayer.content)
  }

  function cancelEdit() {
    setEditingId(null)
    setEditDraft('')
  }

  async function handleUpdate() {
    if (!editDraft.trim() || !editingId) return
    try {
      await updateEvangelismPrayer(editingId, editDraft.trim(), token)
      setItems(prev => prev.map(p => p.id === editingId ? { ...p, content: editDraft.trim() } : p))
      setEditingId(null)
      setEditDraft('')
    } catch (e) {
      setError(e.message)
    }
  }

  function confirmDelete(id) {
    setDeletingId(id)
  }

  function cancelDelete() {
    setDeletingId(null)
  }

  async function handleDelete() {
    if (!deletingId) return
    try {
      await deleteEvangelismPrayer(deletingId, token)
      // Mark as deleted in the list instead of removing
      setItems(prev => prev.map(p => p.id === deletingId ? { ...p, deleted_at: new Date().toISOString() } : p))
      setTotal(prev => prev - 1)
      setDeletingId(null)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleRestore(id) {
    try {
      await restoreEvangelismPrayer(id, token)
      // Mark as restored in the list
      setItems(prev => prev.map(p => p.id === id ? { ...p, deleted_at: null } : p))
      setTotal(prev => prev + 1)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    if (editingId) setTimeout(() => editTextareaRef.current?.focus(), 100)
  }, [editingId])

  // Group items by week
  const grouped = items.reduce((acc, item) => {
    const week = getWeekKey(item.created_at)
    if (!acc[week]) acc[week] = []
    acc[week].push(item)
    return acc
  }, {})
  const sortedWeeks = Object.keys(grouped).sort((a, b) => b.localeCompare(a))

  return (
    <div className="pw-page">
      {/* Header */}
      <header className="pw-header">
        <button className="checkin-back-btn" onClick={onBack} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="pw-header-center">
          <div className="pw-title">🌍 传FY</div>
          <div className="pw-subtitle">{total > 0 ? `共 ${total} 条祷告` : '为福音传遍天下祷告'}</div>
        </div>
        <button
          className="pw-compose-btn"
          onClick={() => setShowCompose(true)}
          title="提交传FY祷告"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </header>

      {/* Success toast */}
      {submitDone && (
        <div className="pw-toast">✅ 祷告已提交，愿福音广传</div>
      )}

      {/* Export Bar */}
      {!loading && !error && items.length > 0 && (
        <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={() => exportAllPrayersToTxt(items)}
            style={{
              padding: '8px 14px',
              background: 'rgba(255,255,255,0.08)',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '6px',
              color: 'rgba(255,255,255,0.8)',
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
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
            onClick={() => exportAllPrayersToPdf(items)}
            style={{
              padding: '8px 14px',
              background: 'rgba(0,122,255,0.15)',
              border: '1px solid rgba(0,122,255,0.3)',
              borderRadius: '6px',
              color: '#5ac8fa',
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
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
      )}

      {/* Compose Overlay */}
      {showCompose && (
        <div className="pw-compose-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowCompose(false) }}>
          <div className="pw-compose-sheet glass">
            <div className="pw-compose-title">🌍 提交传FY祷告</div>

            {/* Current User Info */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginBottom: '12px',
              padding: '10px 12px',
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '10px',
            }}>
              {user?.avatar ? (
                <img
                  src={user.avatar}
                  alt={user.nickname}
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    objectFit: 'cover',
                  }}
                />
              ) : (
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #ff6b6b, #ff9f0a)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  color: '#fff',
                  fontWeight: 600,
                }}>
                  {user?.nickname?.[0] || '弟'}
                </div>
              )}
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: '13px',
                  color: 'rgba(255,255,255,0.9)',
                  fontWeight: 600,
                }}>
                  {user?.nickname || '弟兄/姐妹'}
                </div>
                <div style={{
                  fontSize: '11px',
                  color: 'rgba(255,255,255,0.4)',
                }}>
                  {`以${user?.nickname || '我'}的名义提交祷告`}
                </div>
              </div>
            </div>

            <textarea
              ref={textareaRef}
              className="pw-compose-textarea"
              placeholder="为传福音祷告...（例如：为家人信主祷告、为福音事工祷告、为宣教士祷告等）"
              value={draft}
              onChange={(e) => setDraft(e.target.value.slice(0, 500))}
              rows={5}
            />
            <div className="pw-compose-count">{draft.length} / 500</div>
            <div className="pw-compose-actions">
              <button className="pw-cancel-btn" onClick={() => setShowCompose(false)}>取消</button>
              <button
                className="primary-btn"
                style={{ flex: 1, minHeight: 42 }}
                disabled={!draft.trim() || submitting}
                onClick={handleSubmit}
              >
                {submitting ? '提交中…' : `🌍 以${user?.nickname || '我'}的名义提交`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deletingId && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(4px)',
          zIndex: 300,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '360px',
            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
            borderRadius: '16px',
            border: '1px solid rgba(255,255,255,0.1)',
            padding: '24px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>⚠️</div>
            <div style={{ fontSize: '17px', fontWeight: 600, color: 'rgba(255,255,255,0.95)', marginBottom: '8px' }}>
              确定要删除这条祷告吗？
            </div>
            <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)', marginBottom: '20px' }}>
              删除后无法恢复，请谨慎操作
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={cancelDelete}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: '10px',
                  color: 'rgba(255,255,255,0.8)',
                  fontSize: '14px',
                  cursor: 'pointer'
                }}
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: 'rgba(239,68,68,0.2)',
                  border: '1px solid rgba(239,68,68,0.4)',
                  borderRadius: '10px',
                  color: '#ef4444',
                  fontSize: '14px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                确定删除
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List */}
      <div className="pw-list">
        {loading ? (
          <div className="pw-loading">加载中...</div>
        ) : error ? (
          <div className="pw-error">{error}</div>
        ) : items.length === 0 ? (
          <div className="pw-empty">还没有人提交传FY祷告<br />点击右上角 + 开始祷告</div>
        ) : (
          <>
            {sortedWeeks.map(week => (
              <div key={week} className="pw-week-group">
                <div className="pw-week-label">{formatWeekLabel(grouped[week][0]?.created_at)}</div>
                {grouped[week].map(prayer => (
                  <div key={prayer.id} className="pw-card" style={{ 
                    opacity: prayer.deleted_at ? 0.6 : 1, 
                    border: prayer.deleted_at ? '1px solid rgba(239,68,68,0.3)' : undefined 
                  }}>
                    <div className="pw-card-header">
                      <Avatar nickname={prayer.nickname} />
                      <div className="pw-card-meta">
                        <div className="pw-card-name">
                          {prayer.nickname}
                          {prayer.deleted_at && (
                            <span style={{ 
                              marginLeft: '8px', 
                              fontSize: '11px', 
                              color: '#ef4444',
                              background: 'rgba(239,68,68,0.15)',
                              padding: '2px 6px',
                              borderRadius: '4px'
                            }}>
                              已删除
                            </span>
                          )}
                        </div>
                        <div className="pw-card-time">{timeAgo(prayer.updated_at || prayer.created_at)}</div>
                      </div>
                      {/* Edit/Delete/Restore buttons for owner or admin */}
                      {user && (prayer.nickname === user.nickname || user.email === 'zpclord@sina.com') && (
                        <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto', marginRight: '12px' }}>
                          {!prayer.deleted_at ? (
                            <>
                              <button
                                onClick={() => startEdit(prayer)}
                                style={{
                                  padding: '4px 10px',
                                  background: 'rgba(255,255,255,0.08)',
                                  border: '1px solid rgba(255,255,255,0.15)',
                                  borderRadius: '6px',
                                  color: 'rgba(255,255,255,0.7)',
                                  fontSize: '12px',
                                  cursor: 'pointer'
                                }}
                              >
                                编辑
                              </button>
                              <button
                                onClick={() => confirmDelete(prayer.id)}
                                style={{
                                  padding: '4px 10px',
                                  background: 'rgba(239,68,68,0.15)',
                                  border: '1px solid rgba(239,68,68,0.3)',
                                  borderRadius: '6px',
                                  color: '#ef4444',
                                  fontSize: '12px',
                                  cursor: 'pointer'
                                }}
                              >
                                删除
                              </button>
                            </>
                          ) : (
                            <>
                              {user.email === 'zpclord@sina.com' && (
                                <button
                                  onClick={() => handleRestore(prayer.id)}
                                  style={{
                                    padding: '4px 10px',
                                    background: 'rgba(34,197,94,0.15)',
                                    border: '1px solid rgba(34,197,94,0.3)',
                                    borderRadius: '6px',
                                    color: '#22c55e',
                                    fontSize: '12px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  恢复
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      )}
                      <button
                        className={`pw-amen-btn${amened.has(prayer.id) ? ' amened' : ''}`}
                        onClick={() => handleAmen(prayer.id)}
                        disabled={amened.has(prayer.id) || prayer.deleted_at}
                      >
                        🙏 {prayer.amen_count || ''}
                      </button>
                    </div>
                    {/* Edit Mode */}
                    {editingId === prayer.id ? (
                      <div style={{ padding: '12px 0' }}>
                        <textarea
                          ref={editTextareaRef}
                          value={editDraft}
                          onChange={(e) => setEditDraft(e.target.value.slice(0, 500))}
                          rows={4}
                          style={{
                            width: '100%',
                            padding: '12px',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.15)',
                            borderRadius: '10px',
                            color: 'rgba(255,255,255,0.9)',
                            fontSize: '14px',
                            resize: 'vertical',
                            lineHeight: '1.6'
                          }}
                        />
                        <div style={{ display: 'flex', gap: '10px', marginTop: '10px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={cancelEdit}
                            style={{
                              padding: '8px 16px',
                              background: 'rgba(255,255,255,0.08)',
                              border: '1px solid rgba(255,255,255,0.15)',
                              borderRadius: '8px',
                              color: 'rgba(255,255,255,0.7)',
                              fontSize: '13px',
                              cursor: 'pointer'
                            }}
                          >
                            取消
                          </button>
                          <button
                            onClick={handleUpdate}
                            disabled={!editDraft.trim()}
                            style={{
                              padding: '8px 16px',
                              background: 'rgba(0,122,255,0.2)',
                              border: '1px solid rgba(0,122,255,0.4)',
                              borderRadius: '8px',
                              color: '#5ac8fa',
                              fontSize: '13px',
                              cursor: editDraft.trim() ? 'pointer' : 'not-allowed',
                              opacity: editDraft.trim() ? 1 : 0.5
                            }}
                          >
                            保存
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="pw-card-content" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.7' }}>{prayer.content}</div>
                    )}
                  </div>
                ))}
              </div>
            ))}
            {items.length < total && (
              <div className="pw-load-more">
                <button onClick={() => load(false)} disabled={loadingMore}>
                  {loadingMore ? '加载中...' : `加载更多 (${total - items.length})`}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
