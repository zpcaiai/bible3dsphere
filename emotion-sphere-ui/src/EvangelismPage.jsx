import { useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { amenEvangelismPrayer, deleteEvangelismPrayer, fetchEvangelismPrayers, restoreEvangelismPrayer, submitEvangelismPrayer, updateEvangelismPrayer, runQuery, fetchSeekersClassCourses } from './api'
import usePullToRefresh from './hooks/usePullToRefresh'
import { escapeHtml, escapeHtmlWithBr } from './sanitize'
import BibleMapPage from './BibleMapPage'

// Deepgram API Key for voice input - 支持从环境变量读取
const DEEPGRAM_API_KEY = import.meta.env.VITE_DEEPGRAM_API_KEY || 'a87cbb2d1ec9b07a456fb55319a104731924b12f'

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
  if (!ts) return 'unknown'
  const d = typeof ts === 'string' ? new Date(ts) : (ts > 1e12 ? new Date(ts) : new Date(ts * 1000))
  if (isNaN(d.getTime())) return 'unknown'
  const year = d.getFullYear()
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
  let content = `属灵星球 - 传FY祷告墙\n`
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
        <h1 style="color:#ff6b6b;font-size:20px;margin:0 0 6px 0;">🌍 传FY祷告墙</h1>
        <div style="color:#9a9a9a;font-size:13px;">导出时间：${new Date().toLocaleString('zh-CN')} | 共 ${items.length} 条传福音祷告</div>
      </div>
    `)
    for (const prayer of items) {
      await addBlock(`
        <div style="margin:6px 0;padding:10px;background:#1a2433;border-radius:8px;border:1px solid #2e3c52;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#ff6b6b,#ff9f0a);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0;">${escapeHtml(prayer.nickname?.[0]) || '🌍'}</div>
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
    pdf.save(`传FY祷告墙_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) { console.error('PDF generation failed:', err); alert('PDF 生成失败，请重试') }
  finally { document.body.removeChild(el) }
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

// ── SeekersClassView — 慕道班课程列表（文字 / PPT / 视频） ─────────────────────
function fmtSeekersDate(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const SEEKERS_META = {
  video: { emoji: '🎬', label: '视频', color: 'rgba(90,200,250,0.85)' },
  ppt:   { emoji: '📊', label: 'PPT',  color: 'rgba(255,179,64,0.9)' },
  text:  { emoji: '📄', label: '文字', color: 'rgba(120,220,160,0.9)' },
}

// 慕道班视频课程改为 R2 (cdn.holiness.uk/seekers-class/) 动态列表，后端按固定课程顺序排列

const SEEKERS_SHARE_URL = 'https://holiness.uk/seekers'

function SeekersShareButton() {
  const [copied, setCopied] = useState(false)
  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: '慕道班课程', url: SEEKERS_SHARE_URL }); return } catch (e) {
        if (e && e.name === 'AbortError') return
      }
    }
    try {
      await navigator.clipboard.writeText(SEEKERS_SHARE_URL)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { window.prompt('复制链接分享给慕道朋友：', SEEKERS_SHARE_URL) }
  }
  return (
    <button type="button" onClick={share} style={{
      background: copied ? 'rgba(120,220,160,0.16)' : 'rgba(90,200,250,0.12)',
      border: copied ? '1px solid rgba(120,220,160,0.45)' : '1px solid rgba(90,200,250,0.35)',
      color: copied ? 'rgba(120,220,160,0.95)' : 'rgba(90,200,250,0.95)',
      borderRadius: 999, padding: '5px 14px', fontSize: 12.5, cursor: 'pointer',
    }}>
      {copied ? '✅ 已复制链接' : '🔗 分享本页'}
    </button>
  )
}

export function SeekersClassView() {
  const [courses, setCourses] = useState(null)
  const [err, setErr] = useState('')
  const [playing, setPlaying] = useState(null)   // url of currently playing video

  useEffect(() => {
    fetchSeekersClassCourses()
      .then(d => setCourses(d.courses || []))
      .catch(() => setErr('课程加载失败，请稍后重试'))
  }, [])

  if (err) return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,100,100,0.7)', fontSize: 14, padding: 32 }}>
      {err}
    </div>
  )

  if (!courses) return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 14 }}>
      加载中…
    </div>
  )

  const allCourses = courses

  if (allCourses.length === 0) return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 12 }}>
      <div style={{ fontSize: 44 }}>📚</div>
      <div style={{ fontSize: 16, color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>暂无慕道班课程</div>
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.35)', textAlign: 'center', lineHeight: 1.7 }}>
        课程文件（文字 / PPT / 视频）上传到<br />cdn.holiness.uk/seekers-class/ 后将自动显示
      </div>
    </div>
  )

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
        <SeekersShareButton />
      </div>
      {allCourses.map(c => {
        const meta = SEEKERS_META[c.media_type] || SEEKERS_META.text
        const isVideo = c.media_type === 'video'
        const isYoutube = c.media_type === 'youtube'
        const isPlaying = (isVideo || isYoutube) && playing === c.url
        return (
          <div key={c.url} style={{
            marginBottom: 14, borderRadius: 14,
            background: 'rgba(255,255,255,0.04)',
            border: isPlaying ? '1px solid rgba(90,200,250,0.45)' : '1px solid rgba(255,255,255,0.08)',
            overflow: 'hidden', transition: 'border 0.2s',
          }}>
            {/* Video → inline player; PPT/Text → open link */}
            {(isVideo || isYoutube) ? (
              isPlaying ? (
                isYoutube ? (
                  <iframe
                    src={`https://www.youtube.com/embed/${c.youtubeId}?autoplay=1&rel=0`}
                    title={c.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    style={{ width: '100%', height: 210, display: 'block', border: 'none', background: '#000' }}
                  />
                ) : (
                  <video
                    src={c.url}
                    controls autoPlay playsInline
                    style={{ width: '100%', display: 'block', background: '#000', maxHeight: 280 }}
                    onEnded={() => setPlaying(null)}
                  />
                )
              ) : (
                <div
                  onClick={() => setPlaying(c.url)}
                  style={{
                    position: 'relative', cursor: 'pointer',
                    background: 'linear-gradient(135deg,#12122a,#0d0d20)',
                    height: 150, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  <div style={{ fontSize: 36, opacity: 0.25 }}>{meta.emoji}</div>
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{
                      width: 56, height: 56, borderRadius: '50%',
                      background: meta.color,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: '0 4px 22px rgba(90,200,250,0.38)',
                    }}>
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff"><polygon points="6,3 20,12 6,21" /></svg>
                    </div>
                  </div>
                </div>
              )
            ) : (
              <a
                href={c.url} target="_blank" rel="noopener noreferrer"
                style={{
                  textDecoration: 'none',
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '18px 16px',
                  background: 'linear-gradient(135deg,#14142c,#0e0e22)',
                }}
              >
                <div style={{
                  width: 48, height: 48, borderRadius: 12, flexShrink: 0,
                  background: 'rgba(255,255,255,0.06)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24,
                }}>{meta.emoji}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: meta.color, marginBottom: 2 }}>
                    {meta.label} · 点击打开
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {c.filename}
                  </div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
                </svg>
              </a>
            )}

            {/* Meta row */}
            <div style={{ padding: '10px 14px 12px', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <div style={{
                flexShrink: 0, fontSize: 11, fontWeight: 600, color: meta.color,
                background: 'rgba(255,255,255,0.06)', borderRadius: 6, padding: '2px 8px',
              }}>{meta.emoji} {meta.label}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.92)', lineHeight: 1.4, marginBottom: 3 }}>
                  {c.title || c.filename || '未命名'}
                </div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                  {c.filename}
                  {c.modified_ts > 0 && <span style={{ marginLeft: 8 }}>📅 {fmtSeekersDate(c.modified_ts)}</span>}
                </div>
              </div>
              {isPlaying && (
                <button
                  onClick={() => setPlaying(null)}
                  style={{ flexShrink: 0, background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 6, color: 'rgba(255,255,255,0.45)', fontSize: 12, padding: '4px 10px', cursor: 'pointer' }}
                >✕</button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function EvangelismPage({ user, token, onBack, onPrayerWall }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [amened, setAmened] = useState(loadAmened)
  const [showCompose, setShowCompose] = useState(false)
  const [subTab, setSubTab] = useState('fy') // 'fy' | 'map'
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitDone, setSubmitDone] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState('')
  const [deletingId, setDeletingId] = useState(null)
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
      const data = await fetchEvangelismPrayers(PAGE, replace ? 0 : items.length, token)
      setTotal(data.total || 0)
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
      const prompt = `请帮我润色以下传福音祷告内容，使其更加真诚、流畅、有属灵深度，同时保持原有的情感和恳求。润色后内容不要超过500字。

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

  // Group items by week
  const grouped = items.reduce((acc, item) => {
    const week = getWeekKey(item.created_at)
    if (!acc[week]) acc[week] = []
    acc[week].push(item)
    return acc
  }, {})
  const sortedWeeks = Object.keys(grouped).sort((a, b) => b.localeCompare(a))

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
          <div className="pw-title">{subTab === 'map' ? '🗺️ 圣经地图' : subTab === 'seekers' ? '📚 慕道班' : '🌍 传FY'}</div>
          <div className="pw-subtitle">{subTab === 'map' ? '圣经世界地理与宣教足迹' : subTab === 'seekers' ? '慕道班课程 · 文字 / PPT / 视频' : (total > 0 ? `共 ${total} 条祷告` : '为福音传遍天下祷告')}</div>
        </div>
        {subTab === 'fy' && onPrayerWall && (
          <button
            onClick={onPrayerWall}
            style={{
              background: 'rgba(255,215,0,0.15)', border: '1px solid rgba(255,215,0,0.35)',
              borderRadius: 8, color: '#ffd700', fontSize: 12, fontWeight: 600,
              padding: '5px 12px', cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            🙏 代祷墙
          </button>
        )}
        {subTab === 'fy' && (
        <button
          className="pw-compose-btn"
          onClick={() => setShowCompose(true)}
          title="提交传FY祷告"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
        )}
      </header>

      {/* 子标签：传FY / 圣经地图 */}
      <div className="ev-subtabs">
        <button
          className={`ev-subtab ${subTab === 'fy' ? 'active' : ''}`}
          onClick={() => setSubTab('fy')}
        >
          🌍 传FY
        </button>
        <button
          className={`ev-subtab ${subTab === 'map' ? 'active' : ''}`}
          onClick={() => setSubTab('map')}
        >
          🗺️ 圣经地图
        </button>
        <button
          className={`ev-subtab ${subTab === 'seekers' ? 'active' : ''}`}
          onClick={() => setSubTab('seekers')}
        >
          📚 慕道班
        </button>
      </div>

      {/* Success toast */}
      {submitDone && (
        <div className="pw-toast">✅ 祷告已提交，愿福音广传</div>
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

            <div style={{ position: 'relative' }}>
              <textarea
                ref={textareaRef}
                className="pw-compose-textarea"
                placeholder="为传福音祷告...（例如：为家人信主祷告、为福音事工祷告、为宣教士祷告等）"
                value={draft}
                onChange={(e) => setDraft(e.target.value.slice(0, 500))}
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
                    <span>🌍</span>
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

      {/* List (传FY) */}
      {subTab === 'fy' && (
      <div className="pw-list" ref={listRef} style={{ position: 'relative' }}>
        <div style={indicatorStyle}>{indicatorText}</div>
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
                        <div className="pw-card-time">{formatDateTime(prayer.updated_at || prayer.created_at)}</div>
                      </div>
                      {/* Edit/Delete/Restore buttons for owner or admin */}
                      {user && (prayer.nickname === user.nickname || user.email === 'zpclord@sina.com') && (
                        <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto', marginRight: '12px' }}>
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
                  </div>
                ))}
              </div>
            ))}
            {items.length < total && (
              <div className="pw-load-more">
                <button 
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
              </div>
            )}
          </>
        )}
      </div>
      )}

      {/* 圣经地图：出埃及/保罗/耶路撒冷/支派与王国 */}
      {subTab === 'map' && <BibleMapPage />}

      {/* 慕道班课程列表 */}
      {subTab === 'seekers' && <SeekersClassView />}

      {/* Export Bar */}
      {subTab === 'fy' && !loading && !error && items.length > 0 && (
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
    </div>
  )
}
