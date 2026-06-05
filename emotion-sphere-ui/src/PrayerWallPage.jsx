import { useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { amenPrayer, deletePrayer, fetchPrayers, restorePrayer, submitPrayer, updatePrayer, updatePrayerStatus, runQuery } from './api'
import { requestFriend } from './realtime/realtimeApi'
import usePullToRefresh from './hooks/usePullToRefresh'
import { escapeHtml, escapeHtmlWithBr } from './sanitize'
import HymnPlayer from './HymnPlayer'
import DiscipleFormationView from './DiscipleFormationView'

// Deepgram API Key for voice input - 支持从环境变量读取
const DEEPGRAM_API_KEY = import.meta.env.VITE_DEEPGRAM_API_KEY || 'a87cbb2d1ec9b07a456fb55319a104731924b12f'

const AMEN_KEY = 'pw-amened-v1'

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
  if (!ts) return 'unknown'
  const d = typeof ts === 'string' ? new Date(ts) : (ts > 1e12 ? new Date(ts) : new Date(ts * 1000))
  if (isNaN(d.getTime())) return 'unknown'
  const year = d.getFullYear()
  // Get week number (ISO week date)
  const startOfYear = new Date(year, 0, 1)
  const dayOfYear = Math.floor((d - startOfYear) / 86400000) + 1
  const weekNum = Math.ceil(dayOfYear / 7)
  return `${year}-W${weekNum}`
}

function formatWeekLabel(ts) {
  if (!ts) return ''
  const d = typeof ts === 'string' ? new Date(ts) : (ts > 1e12 ? new Date(ts) : new Date(ts * 1000))
  if (isNaN(d.getTime())) return ''
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  // Get week number
  const startOfYear = new Date(year, 0, 1)
  const dayOfYear = Math.floor((d - startOfYear) / 86400000) + 1
  const weekNum = Math.ceil(dayOfYear / 7)
  return `${year}年 第${weekNum}周`
}

function formatDateTime(ts) {
  if (!ts) return ''
  const d = typeof ts === 'string' ? new Date(ts) : (ts > 1e12 ? new Date(ts) : new Date(ts * 1000))
  if (isNaN(d.getTime())) return ''
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function exportAllPrayersToTxt(items) {
  if (!items || items.length === 0) return
  let content = `属灵星球 - 代祷墙\n`
  content += `导出时间：${new Date().toLocaleString('zh-CN')}\n`
  content += `共 ${items.length} 条代祷\n\n`
  
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
  a.download = `代祷墙_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportAllPrayersToPdf(items) {
  if (!items || items.length === 0) return
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
        <h1 style="color:#007aff;font-size:20px;margin:0 0 6px 0;">🙏 代祷墙</h1>
        <div style="color:#9a9a9a;font-size:13px;">导出时间：${new Date().toLocaleString('zh-CN')} | 共 ${items.length} 条代祷</div>
      </div>
    `)
    for (const prayer of items) {
      await addBlock(`
        <div style="margin:6px 0;padding:10px;background:#1a2433;border-radius:8px;border:1px solid #2e3c52;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#007aff,#5e5ce6);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0;">${escapeHtml(prayer.nickname?.[0]) || '🙏'}</div>
            <div>
              <div style="font-size:13px;font-weight:600;color:#f0f0f0;">${escapeHtml(prayer.nickname)}</div>
              <div style="font-size:11px;color:#a8a8a8;">${formatDateTime(prayer.created_at)}</div>
            </div>
          </div>
          <div style="font-size:13px;color:#e8e8e8;line-height:1.7;white-space:pre-wrap;">${escapeHtmlWithBr(prayer.content)}</div>
          ${prayer.amen_count > 0 ? `<div style="margin-top:6px;font-size:12px;color:#e8a33d;">🙏 ${prayer.amen_count} 人同心代祷</div>` : ''}
        </div>
      `)
    }
    const n = pdf.internal.getNumberOfPages()
    for (let p = 1; p <= n; p++) {
      pdf.setPage(p); pdf.setFontSize(9); pdf.setTextColor(180, 180, 180)
      pdf.text('https://holiness.uk/', PW / 2, PH - 4, { align: 'center' })
    }
    pdf.save(`代祷墙_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) { console.error('PDF generation failed:', err); alert('PDF 生成失败，请重试') }
  finally { document.body.removeChild(el) }
}

function Avatar({ nickname }) {
  const char = nickname?.[0] || '🙏'
  const colors = ['#007aff','#5e5ce6','#34c759','#ff9f0a','#ff6b6b','#32ade6','#af52de']
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

export default function PrayerWallPage({ user, token, onBack }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [amened, setAmened] = useState(loadAmened)
  const [showCompose, setShowCompose] = useState(false)
  const [subTab, setSubTab] = useState(window.__deepLink?.kind === 'hymn' ? 'hymn' : 'wall') // 'wall' | 'hymn'
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitDone, setSubmitDone] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState('')
  const [deletingId, setDeletingId] = useState(null)
  const [isPublic, setIsPublic] = useState(false)
  const [friendRequested, setFriendRequested] = useState({})
  const textareaRef = useRef(null)
  const editTextareaRef = useRef(null)
  const listRef = useRef(null)
  const PAGE = 40

  // 语音输入相关状态
  const [isRecording, setIsRecording] = useState(false)
  const [recordingError, setRecordingError] = useState(null)
  const [isPolishing, setIsPolishing] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  async function load(replace = true) {
    try {
      replace ? setLoading(true) : setLoadingMore(true)
      const data = await fetchPrayers(PAGE, replace ? 0 : items.length, token)
      setTotal(data.total || 0)
      // Sort by updated_at descending (last edited first)
      const sortedItems = (data.items || []).sort((a, b) => {
        const ta = new Date(b.updated_at || b.created_at || 0).getTime()
        const tb = new Date(a.updated_at || a.created_at || 0).getTime()
        return ta - tb
      })
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
    try { await amenPrayer(id, token) } catch { /* optimistic */ }
  }

  async function handleSubmit() {
    if (!draft.trim() || submitting) return
    if (!token) {
      setError('请先登录后再提交代祷')
      return
    }
    setSubmitting(true)
    try {
      await submitPrayer(draft.trim(), false, token, isPublic)
      setDraft('')
      setIsPublic(false)
      setSubmitDone(true)
      setShowCompose(false)
      await load(true)
      setTimeout(() => setSubmitDone(false), 3000)
    } catch (e) {
      const msg = e.message || ''
      if (msg.includes('请先加入或创建教会')) {
        setError('请先加入或创建一个教会才能提交代祷')
      } else if (msg.includes('401') || msg.includes('Unauthorized') || msg.includes('未登录')) {
        setError('请先登录后再提交代祷')
      } else {
        setError(msg || '提交失败')
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAddFriend(email) {
    if (!email || friendRequested[email]) return
    try {
      await requestFriend(email)
      setFriendRequested(prev => ({ ...prev, [email]: true }))
      window.showToast?.('好友请求已发送', 'success')
    } catch (e) {
      window.showToast?.(e.message || '发送失败', 'error')
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
      await updatePrayer(editingId, editDraft.trim(), token)
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
      await deletePrayer(deletingId, token)
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
      await restorePrayer(id, token)
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

  // 开始录音
  async function startRecording(onTranscript) {
    try {
      setRecordingError(null)
      audioChunksRef.current = []

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setRecordingError('语音功能需要 HTTPS 环境，请通过 https:// 访问本页面')
        return
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await transcribeAudio(audioBlob, onTranscript)

        // 停止所有音轨
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error('录音启动失败:', err)
      setRecordingError('无法访问麦克风，请检查权限设置')
    }
  }

  // 停止录音
  function stopRecording() {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  // 检测文本语言（中文或英文）
  function detectTextLanguage(text) {
    const chineseChars = text.match(/[\u4e00-\u9fa5]/g)?.length || 0
    const totalChars = text.replace(/\s/g, '').length
    if (totalChars === 0) return 'unknown'
    return (chineseChars / totalChars) > 0.3 ? 'zh' : 'en'
  }

  // 翻译文本
  async function translateText(text, targetLang) {
    if (!text.trim()) return ''
    try {
      const prompt = targetLang === 'zh'
        ? `请将以下英文翻译成自然流畅的中文，保持原有的情感和语气：\n\n${text}\n\n请直接返回翻译结果，不要添加解释。`
        : `请将以下中文翻译成自然流畅的英文，保持原有的情感和语气：\n\n${text}\n\nPlease return only the translation without explanation.`

      const response = await runQuery({ query: prompt, enableRerank: false })
      return response?.text?.trim() || text
    } catch (err) {
      console.error('翻译失败:', err)
      return text
    }
  }

  // 使用 Deepgram 进行语音识别（支持多语言自动检测）
  async function transcribeAudio(audioBlob, onTranscript) {
    try {
      setRecordingError('正在识别语音...')

      // 使用 Nova-2 多语言模型，自动检测语言
      const response = await fetch('https://api.deepgram.com/v1/listen?model=nova-2&punctuate=true&paragraphs=true&smart_format=true', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${DEEPGRAM_API_KEY}`,
          'Content-Type': 'audio/webm',
        },
        body: audioBlob,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.err_msg || `语音识别失败: ${response.status}`)
      }

      const data = await response.json()
      const transcript = data.results?.channels?.[0]?.alternatives?.[0]?.transcript
      const detectedLanguage = data.results?.channels?.[0]?.detected_language || 'zh'
      console.log('[transcribe] Deepgram原始结果:', transcript, '检测语言:', detectedLanguage)

      if (transcript && transcript.trim()) {
        // 检测文本语言
        const textLang = detectTextLanguage(transcript.trim())
        console.log('[transcribe] 检测到的语言:', textLang)

        // 生成双语版本
        let bilingualText = transcript.trim()
        if (textLang === 'zh') {
          // 中文转英文
          setRecordingError('正在翻译成英文...')
          const englishText = await translateText(transcript.trim(), 'en')
          bilingualText = `${transcript.trim()}\n\n[English] ${englishText}`
        } else if (textLang === 'en') {
          // 英文转中文
          setRecordingError('正在翻译成中文...')
          const chineseText = await translateText(transcript.trim(), 'zh')
          bilingualText = `[中文] ${chineseText}\n\n${transcript.trim()}`
        }

        onTranscript(bilingualText)
        setRecordingError(null)
      } else {
        setRecordingError('未能识别到语音内容，请重试')
      }
    } catch (err) {
      console.error('语音识别失败:', err)
      setRecordingError(err.message || '语音识别失败，请检查网络连接')
    }
  }

  // 润色祷告文字
  async function polishPrayerText(text, onPolished) {
    if (!text.trim()) return
    setIsPolishing(true)
    try {
      const prompt = `请帮我润色以下祷告内容，使其更加真诚、流畅、有属灵深度，同时保持原有的情感和恳求。润色后内容不要超过500字。

原文：${text}

请直接返回润色后的内容，不要添加解释或评论。`

      const response = await runQuery({ query: prompt, enableRerank: false })
      const polished = response?.text?.trim() || text
      onPolished(polished)
    } catch (err) {
      console.error('润色失败:', err)
      setRecordingError('文字润色失败，请检查网络连接')
    } finally {
      setIsPolishing(false)
    }
  }

  const { pulling, refreshing, indicatorStyle, indicatorText } = usePullToRefresh(() => load(true), listRef)

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
          <div className="pw-title">{subTab === 'hymn' ? '🎵 诗歌' : subTab === 'disciple' ? '🧬 门徒塑造' : '🙏 代祷墙'}</div>
          <div className="pw-subtitle">{subTab === 'hymn' ? '安静敬拜 · 曲谱与歌词' : subTab === 'disciple' ? '从慕道友到倍增者 · 门徒塑造引擎' : (total > 0 ? `共 ${total} 条祷告` : '众人的祷告')}</div>
        </div>
        {subTab === 'wall' && (
        <button
          className="pw-compose-btn"
          onClick={() => setShowCompose(true)}
          title="提交祷告"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
        )}
      </header>

      {/* 子标签：代祷墙 / 诗歌 */}
      <div className="ev-subtabs">
        <button className={`ev-subtab ${subTab === 'wall' ? 'active' : ''}`} onClick={() => setSubTab('wall')}>🙏 代祷墙</button>
        <button className={`ev-subtab ${subTab === 'hymn' ? 'active' : ''}`} onClick={() => setSubTab('hymn')}>🎵 诗歌</button>
        <button className={`ev-subtab ${subTab === 'disciple' ? 'active' : ''}`} onClick={() => setSubTab('disciple')}>🧬 门徒塑造</button>
      </div>

      {/* 诗歌子页 */}
      {subTab === 'hymn' && <HymnPlayer />}

      {/* 门徒塑造引擎子页 */}
      {subTab === 'disciple' && <DiscipleFormationView user={user} token={token} />}

      {/* ===== 代祷墙子页 ===== */}
      {subTab === 'wall' && (
      <>
      {/* Success toast */}
      {submitDone && (
        <div className="pw-toast">✅ 祷告已提交，愿神垂听</div>
      )}

      {/* Compose sheet */}
      {showCompose && (
        <div className="pw-compose-overlay" onClick={e => e.target === e.currentTarget && setShowCompose(false)}>
          <div className="pw-compose-sheet glass">
            <div className="pw-compose-title">📝 提交代祷</div>

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
                  background: 'linear-gradient(135deg, #007aff, #5e5ce6)',
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
                  {`以${user?.nickname || '我'}的名义提交代祷`}
                </div>
              </div>
            </div>

            <div style={{ position: 'relative' }}>
              <textarea
                ref={textareaRef}
                className="pw-compose-textarea"
                placeholder="写下你想让弟兄姊妹为你代祷的内容…（最多 500 字）"
                value={draft}
                onChange={e => setDraft(e.target.value.slice(0, 500))}
                rows={5}
                style={{ paddingRight: '80px' }}
              />
              {/* 语音输入按钮 */}
              <button
                type="button"
                onClick={isRecording ? stopRecording : () => startRecording((text) => setDraft(prev => prev ? `${prev} ${text}` : text))}
                disabled={submitting}
                style={{
                  position: 'absolute',
                  right: '44px',
                  top: '8px',
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: 'none',
                  background: isRecording
                    ? 'linear-gradient(135deg, #ff3b30, #ff6b6b)'
                    : 'linear-gradient(135deg, #007aff, #5e5ce6)',
                  color: '#fff',
                  fontSize: '14px',
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: isRecording
                    ? '0 0 12px rgba(255, 59, 48, 0.6)'
                    : '0 2px 8px rgba(0, 122, 255, 0.3)',
                  animation: isRecording ? 'pulse 1.5s ease-in-out infinite' : 'none',
                  opacity: submitting ? 0.5 : 1,
                  transition: 'all 0.2s ease',
                  zIndex: 10,
                }}
                title={isRecording ? '点击停止录音' : '点击开始语音输入'}
              >
                {isRecording ? '🔴' : '🎤'}
              </button>
              {/* 润色按钮 */}
              <button
                type="button"
                onClick={() => polishPrayerText(draft, (text) => setDraft(text.slice(0, 500)))}
                disabled={!draft.trim() || isPolishing || submitting}
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '8px',
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: 'none',
                  background: isPolishing
                    ? 'linear-gradient(135deg, #34c759, #30d158)'
                    : 'linear-gradient(135deg, #ff9500, #ff6b35)',
                  color: '#fff',
                  fontSize: '14px',
                  cursor: (!draft.trim() || isPolishing || submitting) ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 2px 8px rgba(255, 149, 0, 0.3)',
                  opacity: (!draft.trim() || isPolishing || submitting) ? 0.5 : 1,
                  transition: 'all 0.2s ease',
                  zIndex: 10,
                }}
                title="润色文字"
              >
                {isPolishing ? '✨' : '✏️'}
              </button>
            </div>
            {recordingError && (
              <div style={{
                fontSize: '12px',
                color: '#ff6b6b',
                marginTop: '6px',
                marginBottom: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                ⚠️ {recordingError}
              </div>
            )}
            <div className="pw-compose-count">{draft.length} / 500</div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'rgba(255,255,255,0.55)', cursor: 'pointer', userSelect: 'none', margin: '8px 0 4px' }}>
              <input type="checkbox" checked={isPublic} onChange={e => setIsPublic(e.target.checked)} style={{ accentColor: '#007aff' }} />
              🌍 公开请全平台代祷
            </label>
            <div className="pw-compose-actions">
              <button className="pw-cancel-btn" onClick={() => setShowCompose(false)}>
                <span style={{ fontSize: '16px', marginRight: '4px' }}>✕</span>
                取消
              </button>
              <button
                className="primary-btn"
                style={{ flex: 1, minHeight: 42, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                disabled={!draft.trim() || submitting}
                onClick={handleSubmit}
              >
                {submitting ? (
                  <>
                    <span className="spinner" style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 1s linear infinite', display: 'inline-block' }} />
                    提交中…
                  </>
                ) : (
                  <>
                    <span>🙏</span>
                    提交
                  </>
                )}
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
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <span>✕</span>
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
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <span>🗑️</span>
                删除
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List */}
      <div className="pw-list" ref={listRef} style={{ position: 'relative' }}>
        <div style={indicatorStyle}>{indicatorText}</div>
        {loading ? (
          <div className="pw-loading">
            <div className="pw-loading-dots"><span /><span /><span /></div>
            <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 13, marginTop: 12 }}>加载中…</div>
          </div>
        ) : error ? (
          <div className="pw-error">
            <div style={{ fontSize: 32 }}>⚠️</div>
            <div>{error}</div>
            <button className="pw-retry-btn" onClick={() => load()}>重试</button>
          </div>
        ) : items.length === 0 ? (
          <div className="pw-empty">
            <div className="pw-empty-icon">🕊️</div>
            <div className="pw-empty-title">还没有代祷</div>
            <div className="pw-empty-sub">成为第一个分享代祷事项的人</div>
            <button
              className="primary-btn"
              style={{ maxWidth: 200, marginTop: 20 }}
              onClick={() => setShowCompose(true)}
            >
              提交代祷
            </button>
          </div>
        ) : (
          <>
            {(() => {
              let lastWeekKey = null
              return items.map((prayer, index) => {
                const currentWeekKey = getWeekKey(prayer.created_at)
                const showDivider = lastWeekKey !== null && lastWeekKey !== currentWeekKey
                lastWeekKey = currentWeekKey
                
                return (
                  <>
                    {showDivider && (
                      <div className="pw-week-divider">
                        <div className="pw-week-line" />
                        <span className="pw-week-label">{formatWeekLabel(prayer.created_at)}</span>
                        <div className="pw-week-line" />
                      </div>
                    )}
                    <div key={prayer.id} className="pw-card glass" style={{ 
                      opacity: prayer.deleted_at ? 0.6 : 1, 
                      border: prayer.deleted_at ? '1px solid rgba(239,68,68,0.3)' : undefined 
                    }}>
                      <div className="pw-card-top">
                        <Avatar nickname={prayer.nickname} />
                        <div className="pw-card-meta">
                          <span className="pw-card-name">
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
                          </span>
                          <span className="pw-card-time">{formatDateTime(prayer.updated_at || prayer.created_at)}</span>
                        </div>
                        {/* Edit/Delete/Restore buttons for owner or admin */}
                        {user && (prayer.nickname === user.nickname || user.email === 'zpclord@sina.com') && (
                          <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto' }}>
                            {!prayer.deleted_at ? (
                              <>
                                <button
                                  onClick={() => startEdit(prayer)}
                                  title="编辑"
                                  style={{
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
                                    minHeight: '32px'
                                  }}
                                >
                                  ✏️
                                </button>
                                <button
                                  onClick={() => confirmDelete(prayer.id)}
                                  title="删除"
                                  style={{
                                    padding: '6px',
                                    background: 'rgba(239,68,68,0.15)',
                                    border: '1px solid rgba(239,68,68,0.3)',
                                    borderRadius: '6px',
                                    color: '#ef4444',
                                    fontSize: '14px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    minWidth: '32px',
                                    minHeight: '32px'
                                  }}
                                >
                                  🗑️
                                </button>
                              </>
                            ) : (
                              <>
                                {user.email === 'zpclord@sina.com' && (
                                  <button
                                    onClick={() => handleRestore(prayer.id)}
                                    title="恢复"
                                    style={{
                                      padding: '6px',
                                      background: 'rgba(34,197,94,0.15)',
                                      border: '1px solid rgba(34,197,94,0.3)',
                                      borderRadius: '6px',
                                      color: '#22c55e',
                                      fontSize: '14px',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      minWidth: '32px',
                                      minHeight: '32px'
                                    }}
                                  >
                                    ♻️
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        )}
                      </div>
                      {/* Edit Mode */}
                      {editingId === prayer.id ? (
                        <div style={{ padding: '12px 0' }}>
                          <div style={{ position: 'relative' }}>
                            <textarea
                              ref={editTextareaRef}
                              value={editDraft}
                              onChange={(e) => setEditDraft(e.target.value.slice(0, 500))}
                              rows={4}
                              style={{
                                width: '100%',
                                padding: '12px 80px 12px 12px',
                                background: 'rgba(255,255,255,0.05)',
                                border: '1px solid rgba(255,255,255,0.15)',
                                borderRadius: '10px',
                                color: 'rgba(255,255,255,0.9)',
                                fontSize: '14px',
                                resize: 'vertical',
                                lineHeight: '1.6'
                              }}
                            />
                            {/* 语音输入按钮 */}
                            <button
                              type="button"
                              onClick={isRecording ? stopRecording : () => startRecording((text) => setEditDraft(prev => prev ? `${prev} ${text}` : text))}
                              disabled={submitting}
                              style={{
                                position: 'absolute',
                                right: '44px',
                                top: '8px',
                                width: '28px',
                                height: '28px',
                                borderRadius: '50%',
                                border: 'none',
                                background: isRecording
                                  ? 'linear-gradient(135deg, #ff3b30, #ff6b6b)'
                                  : 'linear-gradient(135deg, #007aff, #5e5ce6)',
                                color: '#fff',
                                fontSize: '12px',
                                cursor: submitting ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                boxShadow: isRecording
                                  ? '0 0 12px rgba(255, 59, 48, 0.6)'
                                  : '0 2px 8px rgba(0, 122, 255, 0.3)',
                                animation: isRecording ? 'pulse 1.5s ease-in-out infinite' : 'none',
                                opacity: submitting ? 0.5 : 1,
                                transition: 'all 0.2s ease',
                                zIndex: 10,
                              }}
                              title={isRecording ? '点击停止录音' : '点击开始语音输入'}
                            >
                              {isRecording ? '🔴' : '🎤'}
                            </button>
                            {/* 润色按钮 */}
                            <button
                              type="button"
                              onClick={() => polishPrayerText(editDraft, (text) => setEditDraft(text.slice(0, 500)))}
                              disabled={!editDraft.trim() || isPolishing || submitting}
                              style={{
                                position: 'absolute',
                                right: '8px',
                                top: '8px',
                                width: '28px',
                                height: '28px',
                                borderRadius: '50%',
                                border: 'none',
                                background: isPolishing
                                  ? 'linear-gradient(135deg, #34c759, #30d158)'
                                  : 'linear-gradient(135deg, #ff9500, #ff6b35)',
                                color: '#fff',
                                fontSize: '12px',
                                cursor: (!editDraft.trim() || isPolishing || submitting) ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                boxShadow: '0 2px 8px rgba(255, 149, 0, 0.3)',
                                opacity: (!editDraft.trim() || isPolishing || submitting) ? 0.5 : 1,
                                transition: 'all 0.2s ease',
                                zIndex: 10,
                              }}
                              title="润色文字"
                            >
                              {isPolishing ? '✨' : '✏️'}
                            </button>
                          </div>
                          {recordingError && (
                            <div style={{
                              fontSize: '11px',
                              color: '#ff6b6b',
                              marginTop: '6px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}>
                              ⚠️ {recordingError}
                            </div>
                          )}
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
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                            >
                              <span>✕</span>
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
                                opacity: editDraft.trim() ? 1 : 0.5,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                            >
                              <span>💾</span>
                              保存
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="pw-card-content" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.7' }}>{prayer.content}</div>
                      )}
                      {prayer.status && (
                        <div style={{ padding: '4px 0 2px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {prayer.status === 'answered' ? (
                            <span style={{ color: '#34c759', background: 'rgba(52,199,89,0.12)', border: '1px solid rgba(52,199,89,0.3)', borderRadius: '12px', padding: '2px 9px' }}>✅ 已蒙恩答应</span>
                          ) : prayer.status === 'waiting' ? (
                            <span style={{ color: '#ffd700', background: 'rgba(255,215,0,0.1)', border: '1px solid rgba(255,215,0,0.25)', borderRadius: '12px', padding: '2px 9px' }}>⏳ 仍在等候</span>
                          ) : null}
                        </div>
                      )}
                      <div className="pw-card-footer" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <button
                          className={`pw-amen-btn ${amened.has(prayer.id) ? 'amened' : ''}`}
                          onClick={() => handleAmen(prayer.id)}
                          disabled={amened.has(prayer.id)}
                        >
                          <span className="pw-amen-icon">🙏</span>
                          <span className="pw-amen-label">
                            {amened.has(prayer.id) ? '已同心' : '同心'}
                          </span>
                          {prayer.amen_count > 0 && (
                            <span className="pw-amen-count">{prayer.amen_count}</span>
                          )}
                        </button>
                        {/* 加好友：公开跨教会、非匿名、有email、不是本人 */}
                        {prayer.is_public && !prayer.same_church && !prayer.is_own && prayer.email && user && (
                          <button
                            disabled={!!friendRequested[prayer.email]}
                            onClick={() => handleAddFriend(prayer.email)}
                            style={{ fontSize: 11, padding: '3px 8px', borderRadius: 10, border: '1px solid rgba(0,122,255,0.4)', background: friendRequested[prayer.email] ? 'rgba(0,122,255,0.15)' : 'none', color: '#60a5fa', cursor: 'pointer' }}
                          >
                            {friendRequested[prayer.email] ? '已请求 ✓' : '➕ 加好友'}
                          </button>
                        )}
                        {prayer.is_own && (
                          <>
                            <button
                              onClick={async () => {
                                const newStatus = prayer.status === 'answered' ? null : 'answered'
                                try {
                                  await updatePrayerStatus(prayer.id, newStatus, token)
                                  setItems(prev => prev.map(p => p.id === prayer.id ? { ...p, status: newStatus } : p))
                                } catch (e) { setError(e.message) }
                              }}
                              style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '10px', border: '1px solid rgba(52,199,89,0.4)', background: prayer.status === 'answered' ? 'rgba(52,199,89,0.2)' : 'none', color: '#34c759', cursor: 'pointer' }}
                            >
                              {prayer.status === 'answered' ? '↩ 取消' : '✅ 已答应'}
                            </button>
                            <button
                              onClick={async () => {
                                const newStatus = prayer.status === 'waiting' ? null : 'waiting'
                                try {
                                  await updatePrayerStatus(prayer.id, newStatus, token)
                                  setItems(prev => prev.map(p => p.id === prayer.id ? { ...p, status: newStatus } : p))
                                } catch (e) { setError(e.message) }
                              }}
                              style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '10px', border: '1px solid rgba(255,215,0,0.3)', background: prayer.status === 'waiting' ? 'rgba(255,215,0,0.15)' : 'none', color: '#ffd700', cursor: 'pointer' }}
                            >
                              {prayer.status === 'waiting' ? '↩ 取消' : '⏳ 等候中'}
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </>
                )
              })
            })()}

            {items.length < total && (
              <button
                className="pw-load-more"
                onClick={() => load(false)}
                disabled={loadingMore}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
              >
                {loadingMore ? (
                  <>
                    <span className="spinner" style={{ width: '14px', height: '14px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 1s linear infinite', display: 'inline-block' }} />
                    加载中…
                  </>
                ) : (
                  <>
                    <span>↓</span>
                    加载更多 ({total - items.length})
                  </>
                )}
              </button>
            )}
            <div className="pw-footer-tip">
              愿神垂听每一个呼求 · 以弗所书 6:18
            </div>
          </>
        )}
      </div>

      {/* Export Bar */}
      {!loading && !error && items.length > 0 && (
        <div className="sj-export-bar">
          <button className="sj-export-btn-bottom" onClick={() => exportAllPrayersToTxt(items)} title="导出TXT">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            TXT
          </button>
          <button className="sj-export-btn-bottom" onClick={e => window.busyBtn(e, () => exportAllPrayersToPdf(items), "生成 PDF 中…", "✅ PDF 已导出")} title="导出PDF">
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
      </>
      )}
    </div>
  )
}
