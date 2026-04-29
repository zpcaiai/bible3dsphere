import { useEffect, useRef, useState } from 'react'
import { sendChat } from './api'

const SUGGESTIONS = [
  '我最近感到很焦虑，不知道神是否在乎我',
  '我在工作中遭遇不公平，很难饶恕那个人',
  '我对祷告感到疲惫，感觉神沉默不语',
  '我和配偶之间有很深的隔阂，不知道怎么办',
  '我重复犯同样的罪，非常自责',
  '我想更亲近神，但不知从哪里开始',
]

export default function ChatPage({ user, token, onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const abortRef = useRef(false)

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
          <div className="chat-title">属灵同伴</div>
          <div className="chat-subtitle">以圣经为根基的陪伴对话</div>
        </div>
        <button
          className="chat-new-btn"
          onClick={handleNewSession}
          title="新对话"
          disabled={messages.length === 0}
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
            <div className="chat-welcome-icon">✝️</div>
            <div className="chat-welcome-title">
              {user?.nickname ? `${user.nickname}，你好` : '愿神的平安与你同在'}
            </div>
            <div className="chat-welcome-sub">
              你可以把心里的挣扎、疑问或感恩带来，我会陪你一起用圣经的光来思考。
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
