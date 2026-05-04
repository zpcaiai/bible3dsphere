import { useEffect, useRef, useState } from 'react'
import { sendChat } from './api'
import jsPDF from 'jspdf'

const SUGGESTIONS = [
  '我最近感到很焦虑，不知道神是否在乎我',
  '我在工作中遭遇不公平，很难饶恕那个人',
  '我对祷告感到疲惫，感觉神沉默不语',
  '我和配偶之间有很深的隔阂，不知道怎么办',
  '我重复犯同样的罪，非常自责',
  '我想更亲近神，但不知从哪里开始',
]

const STORAGE_KEY_SHARED = 'devotion_notes_shared'

function getSharedNotes() {
  try {
    const data = localStorage.getItem(STORAGE_KEY_SHARED)
    const notes = data ? JSON.parse(data) : []
    // Sort by creation time descending (newest first)
    return notes.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
  } catch {
    return []
  }
}

export default function ChatPage({ user, token, onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [sharedNotes, setSharedNotes] = useState([])
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const abortRef = useRef(false)

  useEffect(() => {
    setSharedNotes(getSharedNotes())
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function autoResize() {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 140) + 'px'
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const userMsg = { role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setStreaming(true)
    abortRef.current = false

    const assistantPlaceholder = { role: 'assistant', content: '', pending: true }
    setMessages(prev => [...prev, assistantPlaceholder])

    try {
      let accumulated = ''
      let newSessionId = sessionId
      const stream = sendChat(
        nextMessages.map(m => ({ role: m.role, content: m.content })),
        sessionId,
        token
      )
      for await (const chunk of stream) {
        if (abortRef.current) break
        if (chunk.delta) {
          accumulated += chunk.delta
          setMessages(prev => {
            const copy = [...prev]
            copy[copy.length - 1] = { role: 'assistant', content: accumulated, pending: true }
            return copy
          })
        }
        if (chunk.done) {
          newSessionId = chunk.session_id || newSessionId
        }
      }
      setSessionId(newSessionId)
      setMessages(prev => {
        const copy = [...prev]
        copy[copy.length - 1] = { role: 'assistant', content: accumulated, pending: false }
        return copy
      })
    } catch (err) {
      setMessages(prev => {
        const copy = [...prev]
        copy[copy.length - 1] = {
          role: 'assistant',
          content: '抱歉，暂时无法回应，请稍后再试。',
          pending: false,
          error: true,
        }
        return copy
      })
    } finally {
      setStreaming(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleSuggestion(s) {
    setInput(s)
    textareaRef.current?.focus()
    setTimeout(autoResize, 0)
  }

  function handleNewSession() {
    setMessages([])
    setSessionId('')
    setInput('')
  }

  function formatDateTime() {
    const now = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    return `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  }

  function getFirstUserMessage() {
    const firstUserMsg = messages.find(m => m.role === 'user')
    return firstUserMsg ? firstUserMsg.content.slice(0, 20) : '对话'
  }

  function exportToTxt() {
    if (messages.length === 0) return
    const date = new Date().toLocaleString('zh-CN')
    let content = `属灵同伴对话记录\n${date}\n\n`
    messages.forEach((msg, i) => {
      const role = msg.role === 'user' ? '我' : '属灵同伴'
      content += `${role}：\n${msg.content}\n\n`
    })
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const datetime = formatDateTime()
    const topic = getFirstUserMessage()
    a.download = `${topic}_${datetime}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportToPdf() {
    if (messages.length === 0) return
    const date = new Date().toLocaleString('zh-CN')

    // Build HTML content for proper Chinese rendering
    let htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; padding: 40px; line-height: 1.6; max-width: 600px; margin: 0 auto; }
          h1 { font-size: 20px; color: #007aff; margin-bottom: 10px; text-align: center; }
          .date { font-size: 12px; color: #666; text-align: center; margin-bottom: 30px; }
          .message { margin: 16px 0; padding: 12px 16px; border-radius: 12px; }
          .user { background: #007aff; color: white; margin-left: 40px; }
          .assistant { background: #f0f0f0; color: #333; margin-right: 40px; }
          .role { font-size: 11px; font-weight: 600; margin-bottom: 4px; opacity: 0.8; }
          .content { font-size: 14px; white-space: pre-wrap; }
        </style>
      </head>
      <body>
        <h1>属灵同伴对话记录</h1>
        <div class="date">${date}</div>
    `

    messages.forEach((msg) => {
      const roleLabel = msg.role === 'user' ? '我' : '属灵同伴'
      const cssClass = msg.role === 'user' ? 'user' : 'assistant'
      htmlContent += `
        <div class="message ${cssClass}">
          <div class="role">${roleLabel}</div>
          <div class="content">${msg.content.replace(/\n/g, '<br>')}</div>
        </div>
      `
    })

    const datetime = formatDateTime()
    const topic = getFirstUserMessage()
    const filename = `${topic}_${datetime}.pdf`

    htmlContent += `</body></html>`

    // Open in new window for print to PDF
    const printWindow = window.open('', '_blank')
    printWindow.document.title = filename
    printWindow.document.write(htmlContent)
    printWindow.document.close()

    setTimeout(() => {
      printWindow.print()
    }, 300)
  }

  return (
    <div className="chat-page">
      {/* Header */}
      <header className="chat-header">
        <button className="checkin-back-btn" onClick={onBack} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="chat-header-center">
          <div className="chat-title">灵修分享</div>
          <div className="chat-subtitle">弟兄姐妹的灵修见证与分享</div>
        </div>
        <button
          className="chat-new-btn"
          onClick={handleNewSession}
          title="开始对话"
          style={{ opacity: messages.length === 0 ? 0.5 : 1 }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </header>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">📖</div>
            <div className="chat-welcome-title">
              灵修分享
            </div>
            <div className="chat-welcome-sub">
              在这里阅读弟兄姐妹的灵修见证，彼此激励，共同成长。
            </div>

            {/* 分享的灵修笔记 - 作为主要内容 */}
            {sharedNotes.length > 0 ? (
              <div style={{ marginTop: '24px', width: '100%', maxWidth: '600px' }}>
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}>
                  {sharedNotes.map(note => (
                    <div
                      key={note.id}
                      style={{
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: '14px',
                        padding: '16px',
                        textAlign: 'left',
                      }}
                    >
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        marginBottom: '10px',
                      }}>
                        {note.avatar ? (
                          <img
                            src={note.avatar}
                            alt={note.author}
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
                            {note.author?.[0] || '弟'}
                          </div>
                        )}
                        <div style={{ flex: 1 }}>
                          <div style={{
                            fontSize: '13px',
                            color: 'rgba(255,255,255,0.9)',
                            fontWeight: 600,
                          }}>
                            {note.author}
                          </div>
                          <div style={{
                            fontSize: '11px',
                            color: 'rgba(255,255,255,0.4)',
                          }}>
                            {note.date ? new Date(note.date).toLocaleDateString('zh-CN') : ''}
                          </div>
                        </div>
                        {note.mood && (
                          <span style={{
                            fontSize: '12px',
                            color: 'rgba(255,255,255,0.5)',
                            background: 'rgba(255,255,255,0.1)',
                            padding: '4px 10px',
                            borderRadius: '12px',
                          }}>
                            {note.mood}
                          </span>
                        )}
                      </div>
                      {note.scripture && (
                        <div style={{
                          fontSize: '13px',
                          color: 'rgba(255,255,255,0.7)',
                          marginBottom: '10px',
                          padding: '10px',
                          background: 'rgba(0, 122, 255, 0.1)',
                          borderRadius: '8px',
                          borderLeft: '3px solid rgba(0, 122, 255, 0.5)',
                        }}>
                          📖 {note.scripture}
                        </div>
                      )}
                      <div style={{
                        fontSize: '14px',
                        color: 'rgba(255,255,255,0.85)',
                        lineHeight: 1.6,
                        whiteSpace: 'pre-wrap',
                      }}>
                        {note.reflection || note.observation || note.application || '（灵修笔记）'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{
                marginTop: '40px',
                padding: '30px',
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '14px',
                textAlign: 'center',
              }}>
                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)', marginBottom: '10px' }}>
                  暂无分享的灵修笔记
                </div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
                  成为第一位分享灵修心得的弟兄姐妹吧
                </div>
              </div>
            )}

            {/* 开始对话入口 */}
            <div style={{ marginTop: '32px' }}>
              <div style={{
                fontSize: '12px',
                color: 'rgba(255,255,255,0.4)',
                marginBottom: '12px',
              }}>
                需要属灵陪伴？
              </div>
              <div className="chat-suggestions">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    className="chat-suggestion-chip"
                    onClick={() => handleSuggestion(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`chat-bubble-wrap ${msg.role === 'user' ? 'user' : 'assistant'}`}
            >
              {msg.role === 'assistant' && (
                <div className="chat-avatar">✝</div>
              )}
              <div className={`chat-bubble ${msg.role} ${msg.error ? 'error' : ''}`}>
                <MessageContent content={msg.content} pending={msg.pending} />
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Export Buttons - Above Input */}
      {messages.length > 0 && (
        <div className="chat-export-bar">
          <button className="chat-export-btn-bottom" onClick={exportToTxt} title="导出TXT">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            导出TXT
          </button>
          <button className="chat-export-btn-bottom" onClick={exportToPdf} title="导出PDF">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <path d="M9 15l3 3 3-3"/>
              <path d="M12 18V9"/>
            </svg>
            导出PDF
          </button>
        </div>
      )}

      {/* Input */}
      <div className="chat-input-bar glass">
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder="说说你的想法或困惑…"
          value={input}
          rows={1}
          onChange={e => { setInput(e.target.value); autoResize() }}
          onKeyDown={handleKeyDown}
          disabled={streaming}
        />
        <button
          className={`chat-send-btn ${streaming ? 'loading' : ''}`}
          onClick={streaming ? () => { abortRef.current = true } : handleSend}
          aria-label={streaming ? '停止' : '发送'}
        >
          {streaming ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}

function MessageContent({ content, pending }) {
  if (!content && pending) {
    return <span className="chat-typing"><span /><span /><span /></span>
  }
  return (
    <span className="chat-text">
      {content}
      {pending && content && <span className="chat-cursor" />}
    </span>
  )
}
