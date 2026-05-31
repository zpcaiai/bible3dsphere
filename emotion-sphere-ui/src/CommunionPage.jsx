// 圣徒相通 (Communion) — 好友 + 1对1聊天 (QQ式)。
// 实时连接与来电弹窗由全局 realtimeStore / RealtimeRoot 负责（App 顶层挂载），
// 本页只订阅消息流处理好友/聊天，并通过 store 发起 1对1 语音通话。
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchFriends, requestFriend, acceptFriend, removeFriend,
  fetchChatHistory, markRead,
} from './realtime/realtimeApi'
import realtimeStore from './realtime/realtimeStore'
import { useRealtimeState, useRealtimeMessages } from './realtime/useRealtimeStore'

const showToast = (m) => window.showToast?.(m, 'info')
function shortName(email, nickname) {
  return nickname || (email ? email.split('@')[0] : '弟兄姐妹')
}
function timeLabel(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
}
function dedupe(arr) {
  const seen = new Set(); const out = []
  for (const m of arr) {
    const k = m.id ? `s${m.id}` : m.key
    if (seen.has(k)) continue
    seen.add(k); out.push(m)
  }
  return out
}

export default function CommunionPage({ user, onBack, onOpenVoice }) {
  const myEmail = (user?.email || '').toLowerCase()
  const [friends, setFriends] = useState([])
  const [incoming, setIncoming] = useState([])
  const [activePeer, setActivePeer] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [addEmail, setAddEmail] = useState('')
  const [typingFrom, setTypingFrom] = useState(null)

  const { connected, onlineFriends } = useRealtimeState()

  const activePeerRef = useRef(null)
  activePeerRef.current = activePeer
  const friendsRef = useRef([])
  friendsRef.current = friends
  const messagesEndRef = useRef(null)

  const isOnline = useCallback((email) => !!onlineFriends?.has?.(email), [onlineFriends])

  function normMsg(m) {
    return {
      key: m.id ? `s${m.id}` : (m.client_id || `${m.from}-${m.created_at}-${Math.random()}`),
      id: m.id,
      body: m.body,
      mine: (m.sender || m.from) === myEmail || m.self === true,
      created_at: m.created_at,
    }
  }

  // ---------------- Friends ----------------
  const loadFriends = useCallback(async () => {
    try {
      const data = await fetchFriends()
      setFriends(data.friends || [])
      setIncoming(data.incoming || [])
    } catch (e) { /* ignore */ }
  }, [])

  // ---------------- Message stream (chat/typing/friend; presence+call are global) ----------------
  useRealtimeMessages(useCallback((msg) => {
    switch (msg.type) {
      case 'friend_request':
      case 'friend_added':
        loadFriends()
        break
      case 'chat': {
        const peer = msg.self ? msg.to : msg.from
        const active = activePeerRef.current
        if (active && active.email === peer) {
          setMessages((m) => dedupe([...m, normMsg(msg)]))
          if (!msg.self) markRead(peer).catch(() => {})
        } else if (!msg.self) {
          setFriends((fs) => fs.map((f) => f.email === peer
            ? { ...f, unread: (f.unread || 0) + 1, last_message: msg.body } : f))
        }
        break
      }
      case 'typing': {
        const active = activePeerRef.current
        if (active && active.email === msg.from) {
          setTypingFrom(msg.from)
          setTimeout(() => setTypingFrom(null), 2500)
        }
        break
      }
      case 'error':
        if (msg.code === 'not_friends') showToast('仅好友之间可以聊天')
        break
      default:
        break
    }
  }, [loadFriends]))

  useEffect(() => { if (myEmail) loadFriends() }, [myEmail, loadFriends])
  useEffect(() => {
    // let the global incoming-call modal label the caller with a nickname
    realtimeStore.setFriendNicknameResolver((email) => {
      const f = friendsRef.current.find((x) => x.email === email)
      return f?.nickname
    })
  }, [])
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typingFrom])

  async function onAddFriend() {
    const email = addEmail.trim().toLowerCase()
    if (!email) return
    try {
      const r = await requestFriend(email)
      showToast(r.status === 'accepted' ? '已成为好友' : '好友请求已发送')
      setAddEmail(''); loadFriends()
    } catch (e) { showToast(e.message || '添加失败') }
  }
  async function onAccept(email) {
    try { await acceptFriend(email); showToast('已添加好友'); loadFriends() }
    catch (e) { showToast(e.message) }
  }
  async function onRemove(email) {
    if (!window.confirm('确定删除该好友？')) return
    try { await removeFriend(email); if (activePeer?.email === email) setActivePeer(null); loadFriends() }
    catch (e) { showToast(e.message) }
  }

  // ---------------- Chat ----------------
  async function openChat(friend) {
    setActivePeer(friend); setMessages([]); setTypingFrom(null)
    try {
      const data = await fetchChatHistory(friend.email, { limit: 50 })
      setMessages((data.messages || []).map(normMsg))
      await markRead(friend.email)
      setFriends((fs) => fs.map((f) => f.email === friend.email ? { ...f, unread: 0 } : f))
    } catch (e) { /* ignore */ }
  }
  function sendChat() {
    const body = draft.trim()
    if (!body || !activePeer) return
    const ok = realtimeStore.send({ type: 'chat', to: activePeer.email, body, client_id: 'c-' + Date.now() })
    if (!ok) { showToast('连接断开，正在重连…'); return }
    setDraft('')
  }
  function onDraftChange(v) {
    setDraft(v)
    if (activePeer) realtimeStore.send({ type: 'typing', to: activePeer.email })
  }
  function dial(friend) {
    realtimeStore.startDirectCall({ ...friend, online: isOnline(friend.email) })
  }
  function openGroupVoice() {
    if (typeof onOpenVoice === 'function') onOpenVoice()
    else showToast('语音通话请前往「语音通话」页')
  }

  // ---------------- Render ----------------
  return (
    <div className="communion-page">
      <header className="communion-header glass">
        <button className="communion-back" onClick={onBack}>← 返回</button>
        <div className="communion-title">
          圣徒相通
          <span className={`communion-conn ${connected ? 'on' : 'off'}`}>
            {connected ? '● 在线' : '○ 连接中'}
          </span>
        </div>
        <div style={{ width: 56 }} />
      </header>

      <div className="communion-body">
        <aside className={`communion-sidebar ${activePeer ? 'has-active' : ''}`}>
          <div className="communion-add">
            <input
              value={addEmail}
              onChange={(e) => setAddEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onAddFriend()}
              placeholder="输入好友邮箱添加"
            />
            <button onClick={onAddFriend}>添加</button>
          </div>

          {incoming.length > 0 && (
            <div className="communion-incoming">
              <div className="communion-section-title">好友请求</div>
              {incoming.map((r) => (
                <div key={r.email} className="communion-req">
                  <span>{shortName(r.email, r.nickname)}</span>
                  <button onClick={() => onAccept(r.email)}>接受</button>
                </div>
              ))}
            </div>
          )}

          <div className="communion-section-title">好友 ({friends.length})</div>
          <div className="communion-friends">
            {friends.length === 0 && <div className="communion-empty">还没有好友，添加邮箱开始相通</div>}
            {friends.map((f) => {
              const online = isOnline(f.email)
              return (
                <div
                  key={f.email}
                  className={`communion-friend ${activePeer?.email === f.email ? 'active' : ''}`}
                  onClick={() => openChat(f)}
                  onContextMenu={(e) => { e.preventDefault(); onRemove(f.email) }}
                >
                  <div className="communion-avatar">
                    {f.avatar ? <img src={f.avatar} alt="" /> : shortName(f.email, f.nickname)[0]}
                    <span className={`communion-dot ${online ? 'online' : ''}`} />
                  </div>
                  <div className="communion-finfo">
                    <div className="communion-fname">{shortName(f.email, f.nickname)}</div>
                    <div className="communion-flast">{f.last_message || (online ? '在线' : '离线')}</div>
                  </div>
                  {f.unread > 0 && <span className="communion-badge">{f.unread}</span>}
                  <button className="communion-call-btn" title="语音通话"
                    onClick={(e) => { e.stopPropagation(); dial(f) }}>📞</button>
                </div>
              )
            })}
          </div>
        </aside>

        <main className={`communion-chat ${activePeer ? 'open' : ''}`}>
          {!activePeer ? (
            <div className="communion-placeholder">
              <div style={{ fontSize: 40 }}>🕊️</div>
              <p>选择一位弟兄姊妹开始聊天</p>
              <button className="communion-head-call" onClick={openGroupVoice}>🎙 多人语音通话</button>
            </div>
          ) : (
            <>
              <div className="communion-chat-head glass">
                <button className="communion-back-mobile" onClick={() => setActivePeer(null)}>←</button>
                <div className="communion-chat-name">
                  {shortName(activePeer.email, activePeer.nickname)}
                  <span className={`communion-dot ${isOnline(activePeer.email) ? 'online' : ''}`} />
                </div>
                <button className="communion-head-call" onClick={() => dial(activePeer)}>📞 语音通话</button>
              </div>

              <div className="communion-messages">
                {messages.map((m) => (
                  <div key={m.key} className={`communion-msg ${m.mine ? 'mine' : ''}`}>
                    <div className="communion-bubble">{m.body}</div>
                    <div className="communion-msg-time">{timeLabel(m.created_at)}</div>
                  </div>
                ))}
                {typingFrom && <div className="communion-typing">对方正在输入…</div>}
                <div ref={messagesEndRef} />
              </div>

              <div className="communion-compose glass">
                <textarea
                  value={draft}
                  onChange={(e) => onDraftChange(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
                  placeholder="输入消息，Enter 发送"
                  rows={1}
                />
                <button onClick={sendChat} disabled={!draft.trim()}>发送</button>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
